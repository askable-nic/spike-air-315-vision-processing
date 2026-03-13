# VEX Production System Requirements Report

This document describes the runtime dependencies, computational profile, and resource requirements for a production VEX service — a stateless video event extraction pipeline that detects user interaction events from screen recordings.

---

## 1. Python Dependencies

**Python**: >= 3.10


| Package                  | Version   | Purpose                                                                             |
| ------------------------ | --------- | ----------------------------------------------------------------------------------- |
| `google-genai`           | >= 1.0.0  | Gemini Vision API client for frame analysis                                         |
| `opencv-python-headless` | >= 4.8.0  | Frame extraction, diffing, optical flow, template matching, visual change detection |
| `numpy`                  | >= 1.24.0 | Array operations on decoded frames                                                  |
| `pydantic`               | >= 2.0.0  | Configuration and data model validation (frozen BaseModel throughout)               |


**System dependency**: `ffmpeg` and `ffprobe` must be available. Used for video probing (`ffprobe` for metadata/dimensions) and re-encoding (`ffmpeg` with libx264).

Note: `click`, `pyyaml`, and `python-dotenv` are current CLI/config dependencies that would not be required in a production service with its own API layer and config management.

---

## 2. Container Image

### Base image

Use a **Debian-based** Python image (e.g. `python:3.12-slim`), not Alpine. `opencv-python-headless` and `numpy` ship pre-built manylinux wheels that install instantly on Debian. On Alpine, these must be compiled from source — slow, fragile, and not worth the smaller base image.

`ffmpeg` is not included in slim images and must be installed via `apt-get install ffmpeg` or copied as a static binary in a multi-stage build.

Expected image size: ~500MB–1GB with all dependencies.

### Architecture

**ARM64 (Graviton) is preferred.** All dependencies — OpenCV, numpy, ffmpeg, google-genai — have mature ARM64 support. Graviton instances are ~20% cheaper for equivalent CPU, and the observe stage is CPU-bound array math that runs equally well on either architecture.

If multi-arch builds are needed, produce both `linux/amd64` and `linux/arm64` manifests.

---

## 3. Request Interface

The service is stateless. Each request contains everything needed to process a single session and returns the extracted events.

### Request inputs


| Field                          | Type            | Description                                                                                                                                                                  |
| ------------------------------ | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `screen_track_url`             | string (S3 URL) | URL to the screen recording video (MP4 or WebM)                                                                                                                              |
| `screen_track_start_offset_ms` | integer         | Offset in milliseconds from the start of the full session to the start of the screen track. Used to resolve event timestamps to absolute session time.                       |
| `source_type`                  | enum            | Recording context: `unmod_website_test_video`, `ai_mod_website_test_video`, `moderated_screen_recording`, `unmod_figma_prototype_test`, `unmod_tree_test`, `unmod_card_sort` |


### Response output

A list of event objects (type defined in shared Postgres models package), plus processing metrics (per-stage durations, token usage, event counts).

---

## 4. Key Functions & Processes

VEX is a 4-stage sequential pipeline processing a single screen recording per request.

### Video Normalisation (pre-pipeline)

The input video is downloaded and normalised to a consistent-resolution H.264 MP4. The output resolution is derived from a 2,073,600 pixel budget (equivalent to 1920x1080) preserving the source aspect ratio. Frames with a different aspect ratio are letterboxed. This uses ffmpeg with `-c:v libx264 -preset fast -crf 23`.

The normalised video is the primary intermediate artifact. It must be written to local storage (an `emptyDir` volume in Kubernetes) for OpenCV to read frames from it.

### Stage 1: Triage

Classifies temporal regions of the video by activity level to assign adaptive frame extraction rates.

1. Extract frames at low FPS and reduced resolution
2. Compute pairwise grayscale `absdiff` magnitude between consecutive frames
3. Apply a sliding window to compute mean activity per window
4. Classify each window into an activity tier (idle, low, medium, high) based on configurable thresholds
5. Merge adjacent same-tier windows into segments, absorb short segments into neighbours
6. Assign a target FPS per segment based on its activity tier

### Stage 2: Observe

Computer-vision-only analysis producing structured "moments" that guide API frame selection.

- **Visual change detection**: Frame pairs analysed via grayscale diff, Gaussian blur, threshold, morphological close, and `connectedComponentsWithStats`. Qualifying change regions are emitted. Contiguous changes are grouped into `VisualChangeEvent`s categorised as scene changes, local changes, or continuous changes.
- **Cursor template matching**: Multi-scale normalised cross-correlation against cursor template PNGs. Two-pass adaptive tracking: low FPS base pass, then high FPS refinement around movement periods. Detections are smoothed and interpolated.
- **Optical flow**: Sparse Lucas-Kanade on a regular grid to detect scroll direction and magnitude.
- **Event synthesis**: Cursor trajectory and flow data are combined to synthesise local events — hover, dwell, click candidates, scroll, cursor thrash, hesitation — using temporal and spatial thresholds.
- **Moment assembly**: Visual changes, flow events, and cursor events are fused into prioritised `Moment` objects. Each moment carries a token budget estimate so the analyse stage can pack API requests within budget.

### Stage 3: Analyse

Sends JPEG-encoded frames to the Gemini Vision API with structured prompts requesting event detection.

- Frames are selected based on triage segments (uniform FPS) or observe moments (targeted frames around visual changes and cursor activity)
- Each API request includes JPEG frames and a system prompt specifying the event schema
- Responses use Gemini structured output (`response_mime_type: application/json`) returning typed events with frame index references
- Concurrency is semaphore-gated
- Token budget management: a per-segment token budget determines how many frames can be included per request, based on estimated image token cost (Gemini's 768x768 tiling model)
- In visual-change-driven mode, runs two passes: (1) scene description pass for context, (2) interaction analysis pass using moments + scene context

### Stage 4: Merge

Combines results from analyse (and optionally observe) into a deduplicated final event timeline.

- Resolves frame-index-based timestamps to absolute millisecond timestamps using `FrameRef` lookups and the `screen_track_start_offset_ms`
- Optionally discards events originating entirely from context frames
- Adds locally-synthesised events from observe (scroll, thrash) that don't need LLM enrichment
- Sorts all events by start time
- **Greedy deduplication**: for each event, checks existing kept events — if same type, within temporal tolerance, and description similarity above threshold (`SequenceMatcher`), keeps the higher-confidence one

---

## 5. Computational Profile

### CPU-bound stages

- **Triage**: OpenCV frame extraction + grayscale diff. Lightweight — processes at reduced resolution. Completes in seconds per session.
- **Observe**: The most CPU-intensive stage. Runs visual change detection, multi-scale template matching, optical flow, and event synthesis all via OpenCV/numpy.
- **Merge**: Pure Python comparisons and `SequenceMatcher` string similarity. Negligible.

### API-bound stages

- **Analyse**: Dominated by Gemini Vision API latency. Requests are dispatched via `asyncio.to_thread` and gated by an `asyncio.Semaphore`. Each request includes multiple JPEG frames. Retry with exponential backoff on failure.

### Memory

Decoded frames are held in-memory as numpy arrays during processing. A single 1920x1080 BGR frame is ~6MB uncompressed. Frames are extracted per-segment/per-moment and consumed immediately; peak memory is one segment's worth of frames (tens to low hundreds of frames). JPEG-encoded bytes (100-200KB each) are created transiently for API payloads.

### GPU

No GPU required. All CV operations use CPU-only OpenCV (`opencv-python-headless`).

### Concurrency model

- **One request per pod** — given the memory profile (decoded frames held in RAM) and CPU demands of the observe stage, each pod should process a single request at a time
- Within a request, stages run sequentially (triage -> observe -> analyse -> merge)
- Within the analyse stage, API calls use async concurrency with a semaphore gate
- No multiprocessing or threading beyond `asyncio.to_thread` for blocking Gemini SDK calls

---

## 6. External Service Dependencies

### Google Gemini via Vertex AI


| Item            | Detail                                                                                  |
| --------------- | --------------------------------------------------------------------------------------- |
| Model           | `gemini-3-flash-preview`                                                                |
| Access          | Vertex AI API                                                                           |
| Authentication  | GCP service account / workload identity (standard Vertex AI auth)                       |
| SDK             | `google-genai` Python client (`genai.Client(vertexai=True, project=..., location=...)`) |
| Request pattern | Synchronous SDK call wrapped in `asyncio.to_thread`                                     |
| Rate limiting   | Application-side semaphore                                                              |
| Retry           | Exponential backoff                                                                     |


**Required configuration:**

- `GOOGLE_CLOUD_PROJECT` — GCP project ID
- `GOOGLE_CLOUD_LOCATION` — Vertex AI region (e.g. `us-central1`)
- Service account with Vertex AI User role (or equivalent)

Note: The current spike uses API key auth (`GEMINI_API_KEY`). Production requires switching the client initialisation to `genai.Client(vertexai=True, project=..., location=...)`.

### AWS S3

The input screen recording is fetched from S3. The pod's service account requires read access to the recordings bucket.


| Item           | Detail                                                    |
| -------------- | --------------------------------------------------------- |
| Access pattern | Single `GET` per request to download the screen recording |
| Authentication | IAM Roles for Service Accounts (IRSA) on EKS              |
| Bucket access  | Read-only to the recordings bucket                        |


---

## 7. I/O & Storage Profile

### Input

- **Screen recording**: single MP4 or WebM file fetched from S3, typically 100s of MB

### Local storage required during processing


| Artifact             | Lifecycle                    | Size                               | Notes                                                                                                                                    |
| -------------------- | ---------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Downloaded video** | Duration of request          | 100s of MB                         | Fetched from S3 to an `emptyDir` volume                                                                                                  |
| **Normalised video** | Duration of request          | ~same size as input (H.264 CRF 23) | Written to the same `emptyDir` volume. Candidate for object-storage caching keyed by source URL to avoid re-encoding on repeat requests. |
| **Cursor templates** | Static, bundled with service | ~100KB total                       | PNG files + metadata JSON. Loaded once at startup or per-request.                                                                        |


### In-memory transients (not persisted)


| Artifact                | Size per unit             | Peak volume                      | Notes                            |
| ----------------------- | ------------------------- | -------------------------------- | -------------------------------- |
| **Decoded frames**      | ~6MB each (1920x1080 BGR) | Tens to low hundreds per segment | Consumed immediately per-segment |
| **JPEG-encoded frames** | ~100-200KB each           | Same as decoded frames           | Created for Gemini API payloads  |


### Output

JSON response payload containing the event list and processing metrics. Typical size ~10-55KB per session.

---

## 8. Kubernetes Deployment

### Pod resource requirements


| Resource          | Request | Limit | Notes                                                                                    |
| ----------------- | ------- | ----- | ---------------------------------------------------------------------------------------- |
| CPU               | 2       | 2     | Observe stage is CPU-intensive; analyse stage mostly idles waiting on API                |
| Memory            | 4Gi     | 4Gi   | Peak: one segment's worth of decoded frames (~6MB each x tens to low hundreds of frames) |
| Ephemeral storage | 2Gi     | 4Gi   | Downloaded video + normalised copy via `emptyDir`. Size depends on recording length.     |


These are starting-point estimates and should be validated with production workloads.

### Graceful shutdown

Set `terminationGracePeriodSeconds` to accommodate in-flight processing. Video processing for a long session can take minutes. The pipeline is stateless so an interrupted request can be safely retried, but allowing completion avoids wasted compute.

### Scaling

With one request per pod, scaling is driven by request volume:

- **Queue-driven (async)**: Scale on queue depth using KEDA or a custom HPA metric
- **Synchronous API**: Scale on request concurrency or CPU utilisation via HPA

### Networking

Pods require egress to:

- **AWS S3** — to download input screen recordings
- **Vertex AI (GCP)** — for Gemini Vision API calls

If running in a restricted namespace, NetworkPolicy must permit these outbound connections.

### Service account

The Kubernetes service account must be configured with:

- **IRSA (EKS)** — for S3 read access to the recordings bucket
- **GCP Workload Identity or service account key** — for Vertex AI access

