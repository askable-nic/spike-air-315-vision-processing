# Local Event Synthesis Stage — Technical Spec

## Context

The current pipeline has three stages: triage → analyse → merge. The analyse stage sends frames to Gemini for event detection, but the LLM has no information about cursor position, movement trajectory, or interaction patterns that are detectable locally from the video pixels alone. This means:

1. **Gemini guesses at cursor position** — it can sometimes see the cursor in a frame, but has no tracking across frames, misses small/fast movements, and can't reliably distinguish hover from click from thrash.
2. **Full frames waste tokens** — most of the frame is irrelevant background. If we knew where the cursor was, we could crop to the region of interest.
3. **Some events are detectable locally** — hover, dwell, cursor thrash, and scroll can be derived from cursor trajectory + optical flow without any API call. These cost zero tokens and can run at higher FPS than the LLM analysis.

This spec adds a new **observe** stage that runs between triage and analyse. It uses OpenCV to track the cursor, compute optical flow, synthesize local events, and produce ROI crop coordinates. Its output feeds into analyse (as prompt context and frame crops) and into merge (as additional events).

## Goals

1. **Cursor tracking** — detect and track cursor position across frames using template matching, producing a trajectory with per-frame (x, y) coordinates.
2. **Local event synthesis** — derive hover, dwell, cursor_thrash, scroll, and click-candidate events from the cursor trajectory and optical flow, with no API calls.
3. **ROI cropping** — use cursor position to crop frames sent to Gemini, reducing tokens per frame while preserving the interaction region.
4. **LLM enrichment** — feed local events and cursor data into the analyse stage as structured context, so Gemini can confirm, enrich, or reject them.
5. **Raw data persistence** — save all intermediate observe data (cursor trajectory, optical flow summary, raw local events) to `observe.json` per session for debugging and analysis.

---

## Pipeline Position

Two modes are supported:

**Triage-driven (original):**
```
triage → observe → analyse → merge
```

**Observe-driven (adaptive):** Triage is disabled. Observe gets video duration from `get_video_metadata()` directly.
```
observe (adaptive FPS) → frame selection → analyse (event-driven batches) → merge
```

The observe stage receives either a `TriageResult` or `None` (when triage is disabled). When `triage_result` is `None`, observe uses `get_video_metadata(video_path).duration_ms` for the total recording duration.

- **Analyse (triage-driven)** uses observe data for: ROI crop coordinates per frame, local event context in prompts, cursor position annotations on frame labels.
- **Analyse (observe-driven)** uses `ObserveResult.selected_frames` to extract only the frames needed. `run_analyse_from_observe()` batches frames by time proximity and sends them to Gemini with per-frame annotations explaining the non-uniform sampling.
- **Merge** uses observe data for: local events added to the event pool before dedup. When `triage_result` is `None`, triage metrics fall back to empty defaults.

---

## Stage Design

### Input

- `SessionManifest` — session metadata
- `PipelineConfig` — observe config section
- `TriageResult | None` — segments with tiers and time ranges (None when triage is disabled)
- `video_path` — path to screen track video

### Output

`ObserveResult` (frozen pydantic model) containing:

- `recording_id: str`
- `cursor_trajectory: tuple[CursorDetection, ...]` — per-frame cursor positions across the entire video
- `flow_summary: tuple[FlowWindow, ...]` — optical flow summaries per time window
- `local_events: tuple[LocalEvent, ...]` — synthesized events
- `roi_rects: tuple[ROIRect, ...]` — crop rectangles per analysis frame timestamp (legacy, for triage-driven mode)
- `selected_frames: tuple[SelectedFrame, ...]` — frames selected for observe-driven analysis
- `processing_time_ms: float`
- `frames_analysed: int`
- `cursor_detection_rate: float` — fraction of frames where cursor was found (0–1)

Persisted to `output/{session_id}/observe.json` with the same cache/resume logic as other stages.

---

## Data Models

All frozen pydantic models, added to `src/models.py`.

### CursorDetection

Per-frame cursor detection result.

```
timestamp_ms: float
x: float                    # cursor tip x in source resolution
y: float                    # cursor tip y in source resolution
confidence: float           # template match confidence (0–1)
template_id: str            # which template matched (e.g. "arrow", "hand", "ibeam")
detected: bool              # false if position was interpolated from neighbours
```

When the cursor is not found in a frame (`detected=False`), position is linearly interpolated from the nearest detected frames on either side. Confidence is set to 0 for interpolated positions.

### FlowWindow

Optical flow summary over a time window (aligned with triage windows).

```
start_ms: float
end_ms: float
mean_flow_magnitude: float          # mean pixel displacement per frame
dominant_direction: str             # "up" | "down" | "left" | "right" | "mixed" | "none"
flow_uniformity: float              # 0–1, how uniform the flow field is (1 = all pixels moving same direction = scroll)
cursor_flow_divergence: float       # difference between cursor motion and background flow (high = cursor moving independently)
```

`flow_uniformity` near 1.0 with a dominant direction strongly indicates scrolling. `cursor_flow_divergence` near 0 means the cursor is moving with the page (scroll), while high divergence means the cursor is moving independently over a static or scrolling page.

### LocalEvent

An event synthesized locally from cursor trajectory and/or optical flow. Uses the same `EventType` as the rest of the pipeline.

```
type: EventType                     # hover, dwell, cursor_thrash, scroll, hesitate, click (candidate)
time_start_ms: float                # relative to screen track start
time_end_ms: float
cursor_positions: tuple[CursorPosition, ...]    # key positions during the event
confidence: float                   # local detection confidence
synthesis_method: str               # "trajectory" | "optical_flow" | "combined"
description: str                    # auto-generated description (e.g. "Cursor stationary at (450, 320) for 2.1s")
needs_enrichment: bool              # whether this event should be sent to Gemini for label enrichment
```

### ROIRect

A crop rectangle for a specific frame timestamp, for use by the analyse stage.

```
timestamp_ms: float
x: int
y: int
width: int
height: int
cursor_x: float                     # cursor position within the crop
cursor_y: float
```

### SelectedFrame

A frame selected for observe-driven LLM analysis.

```
timestamp_ms: float
reason: str                     # "event_start", "event_end", "event_mid", "visual_change", "baseline"
event_index: int | None         # index into local_events (None for visual_change/baseline)
roi: ROIRect | None             # ROI crop for event frames (None for visual_change/baseline)
```

Frame selection rules:
- **Event frames**: start/end (or midpoint for dwells) of each local event. ROI-cropped for cursor events, full-frame for scroll.
- **Visual change frames**: in gaps >visual_scan_gap_ms, frames where compute_frame_diff() exceeds visual_change_threshold. Full-frame. Used to discover navigate and change_ui_state events.
- **Baseline frames**: midpoint of any remaining gap >baseline_max_gap_ms. Full-frame.
- **Deduplication**: within frame_dedup_ms, keep highest priority (event > visual_change > baseline).

### ObserveConfig

New section in `PipelineConfig`.

```
enabled: bool = True
tracking_fps: float = 10.0          # FPS for cursor tracking (independent of triage FPS)
resolution_height: int = 720        # higher than triage for better template matching

# Cursor detection
cursor_templates_dir: str = ""      # path to custom templates (empty = built-in)
template_scales: tuple[float, ...] = (0.8, 1.0, 1.2)   # multi-scale matching
match_threshold: float = 0.65       # min confidence for a template match
max_interpolation_gap_ms: int = 500  # max gap to interpolate across

# Optical flow
flow_sample_fps: float = 5.0        # FPS for optical flow computation
flow_window_ms: int = 2000          # window size for flow summaries
flow_grid_step: int = 20            # pixel spacing for flow sample points

# Event synthesis thresholds
hover_min_ms: int = 300              # cursor stationary for >= this = hover
hover_max_ms: int = 2000             # longer than this = dwell instead
dwell_min_ms: int = 2000
stationary_radius_px: int = 15      # cursor within this radius = "stationary"
thrash_window_ms: int = 1500        # window for detecting thrash
thrash_min_direction_changes: int = 4
thrash_min_speed_px_per_sec: float = 500.0
click_stop_duration_ms: int = 150   # brief stop that may indicate click
click_stop_radius_px: int = 8
scroll_flow_uniformity_min: float = 0.7
scroll_min_duration_ms: int = 300
hesitate_min_ms: int = 500          # pause before action
hesitate_max_ms: int = 2000

# ROI cropping
roi_enabled: bool = True
roi_size: int = 512                 # crop size in pixels (square, at source resolution)
roi_padding: int = 64               # extra padding around ROI
roi_fallback: str = "full"          # "full" | "center" — what to do when cursor not detected
```

---

## Cursor Tracking

### Adaptive Two-Pass Approach

Cursor tracking uses an adaptive two-pass strategy to balance speed and temporal precision:

1. **Pass 1 (coarse):** Extract frames at `tracking_base_fps` (default 2) across the full video. Template match every frame. Produces a coarse trajectory.
2. **Identify active regions:** Scan consecutive detected frames. Where Euclidean displacement exceeds `tracking_displacement_threshold_px` (default 30), mark the interval as active. Merge overlapping intervals and pad each side by `tracking_active_padding_ms` (default 500ms).
3. **Pass 2 (fine):** For each active region, extract frames at `tracking_peak_fps` (default 15). Template match. Produces fine detections.
4. **Merge:** In active regions, replace pass-1 detections with pass-2 detections. Sort by timestamp.
5. **Interpolate + smooth:** Apply existing `interpolate_trajectory()` and `smooth_trajectory()`.

This avoids wasting computation on idle regions (mouse not moving) while achieving high temporal resolution during cursor activity. A 10-minute recording might have 1200 coarse frames and ~2000 fine frames in active regions, compared to 3000 frames at a fixed 5 FPS.

Key functions:
- `_match_frames()` — extracted template-matching loop, reused by both passes
- `_identify_active_regions()` — scans detections for displacement above threshold, returns merged/padded intervals
- `track_cursor()` — orchestrates the two-pass flow

### Template Matching

Cursor detection uses `cv2.matchTemplate` with normalised cross-correlation (`cv2.TM_CCOEFF_NORMED`).

**Built-in templates:** Ship a small set of common cursor images as PNGs in `cursor_templates/` at the project root:
- `arrow.png` — default pointer (light and dark variants)
- `arrow_shadow.png` — pointer with drop shadow (macOS style)
- `hand.png` — link/pointer cursor
- `ibeam.png` — text input cursor
- `wait.png` — loading/spinner cursor

Templates should be RGBA PNGs at native resolution (typically 32x32 or 48x48 for retina). The alpha channel is used as a mask during matching (`cv2.matchTemplate` with mask parameter).

**Multi-scale matching:** Screen recordings may be at various resolutions, and cursor size varies. Match at multiple scales (configurable, default 0.8x, 1.0x, 1.2x) and take the best match across all templates and scales.

**Algorithm per frame:**
1. Convert frame to grayscale
2. For each template at each scale:
   a. Resize template
   b. Run `cv2.matchTemplate` with mask
   c. Find max correlation and its location via `cv2.minMaxLoc`
3. Take the best (template, scale, location, confidence) across all combinations
4. If confidence >= `match_threshold`: record detection with cursor tip position (adjusted for template hotspot)
5. If confidence < threshold: mark frame as undetected

**Template hotspot:** Each template has a hotspot offset — the pixel within the template that represents the cursor's "tip" (e.g., top-left corner of the arrow). This is stored as metadata alongside the template PNG. The reported (x, y) is the hotspot position, not the template corner.

**Interpolation:** For frames where the cursor is not detected, linearly interpolate position from the nearest detected frames on either side. Do not interpolate across gaps longer than `max_interpolation_gap_ms` — those frames get no cursor position.

**Performance:** Template matching on 720p grayscale frames with 5 templates at 3 scales = 15 matchTemplate calls per frame. At 10 FPS for a 10-minute video, that's ~90,000 calls. Each call on 720p takes ~1-3ms on a modern CPU, so total is ~90-270 seconds. Acceptable, but consider:
- Processing segments in parallel (they're independent)
- Only running at `tracking_fps`, not source FPS
- Early exit: if a high-confidence match is found, skip remaining templates

### Cursor Trail Smoothing

Raw detections may have frame-to-frame jitter. Apply a small moving-average filter (window of 3 frames) to smooth the trajectory, while preserving genuine rapid movements (only smooth when displacement between frames is below a threshold).

---

## Optical Flow

Computed separately from cursor tracking, at a potentially different FPS (`flow_sample_fps`). Uses sparse Lucas-Kanade optical flow (`cv2.calcOpticalFlowPyrLK`) on a grid of sample points.

**Algorithm:**
1. Extract frames at `flow_sample_fps`
2. For each consecutive frame pair:
   a. Generate sample points on a regular grid (spacing = `flow_grid_step` pixels)
   b. Compute optical flow with `cv2.calcOpticalFlowPyrLK`
   c. Filter out points where tracking failed (status = 0)
   d. Compute per-point displacement vectors
3. Aggregate into `FlowWindow` summaries:
   - `mean_flow_magnitude`: mean displacement across all tracked points
   - `dominant_direction`: direction with the most flow energy (8-direction binning, or "mixed"/"none")
   - `flow_uniformity`: ratio of flow in the dominant direction to total flow. High uniformity = coherent motion (scroll). Low = mixed motion (cursor moving over static page).
   - `cursor_flow_divergence`: if cursor was detected in both frames, compute the difference between cursor displacement and mean background flow. High divergence = cursor moving independently.

**Why sparse flow over dense flow:** Sparse LK is ~10x faster than dense Farneback, and we only need aggregate statistics (direction, magnitude, uniformity), not per-pixel flow. The grid sampling gives sufficient spatial coverage.

---

## Local Event Synthesis

Pure functions that take the cursor trajectory and flow summaries and produce `LocalEvent` instances. No API calls. All thresholds are configurable.

### Hover Detection

Scan the cursor trajectory for periods where the cursor is stationary (within `stationary_radius_px` of a centre point) for between `hover_min_ms` and `hover_max_ms`.

```
for each maximal stationary window:
    duration = end_ms - start_ms
    if hover_min_ms <= duration < hover_max_ms:
        emit hover event
        needs_enrichment = True  (we want to know what element is under the cursor)
```

### Dwell Detection

Same as hover but for durations >= `dwell_min_ms`. The cursor may drift slightly — use a larger radius or allow slow drift. Dwell events replace any overlapping hover event at the same position.

```
for each maximal stationary window:
    if duration >= dwell_min_ms:
        emit dwell event (replacing any hover at this position)
        needs_enrichment = True
```

### Cursor Thrash Detection

Scan for rapid direction changes within a sliding window.

```
for each window of thrash_window_ms:
    compute cursor velocity vectors between consecutive detections
    count direction changes (angle between consecutive velocity vectors > 90°)
    compute mean speed
    if direction_changes >= thrash_min_direction_changes AND mean_speed >= thrash_min_speed_px_per_sec:
        emit cursor_thrash event
        confidence = min(1.0, direction_changes / (thrash_min_direction_changes * 2))
```

### Click Candidate Detection

A click typically manifests as: cursor moving → brief stop (cursor stationary for ~100-300ms) → cursor continues. This is a weak signal — clicks cannot be confirmed locally since there's no mouse event data. Marked with `needs_enrichment = True` so Gemini can check whether the UI changed.

```
for each brief stationary period (click_stop_duration_ms ± tolerance):
    if preceded by movement AND followed by movement:
        emit click candidate (type="click", low confidence ~0.3)
        needs_enrichment = True
```

### Scroll Detection

Derived from optical flow, not cursor trajectory.

```
for each FlowWindow:
    if flow_uniformity >= scroll_flow_uniformity_min AND mean_flow_magnitude > threshold:
        if window duration >= scroll_min_duration_ms:
            direction = dominant_direction  (up/down for vertical scroll)
            emit scroll event
            confidence = flow_uniformity
```

### Hesitate Detection

A pause that occurs immediately before a detected movement or click candidate. Indicates uncertainty.

```
for each movement onset (cursor starts moving after being stationary):
    stationary_duration = time since cursor was last moving
    if hesitate_min_ms <= stationary_duration <= hesitate_max_ms:
        if followed by a click candidate or rapid movement:
            emit hesitate event
```

---

## ROI Cropping

When `roi_enabled` is True, the observe stage produces an `ROIRect` for each frame timestamp that the analyse stage will extract. The analyse stage uses these to crop frames before encoding as JPEG.

**Crop computation:**
1. Look up cursor position at the frame's timestamp (from cursor trajectory, interpolated if needed)
2. Centre a `roi_size × roi_size` crop on the cursor position
3. Add `roi_padding` on all sides
4. Clamp to frame boundaries
5. If cursor position is unknown: use `roi_fallback` strategy ("full" = don't crop, "center" = crop centre of frame)

**Token impact:** A 512×512 crop at JPEG quality 85 is roughly 258 tokens (vs 1,548 for a full 1080p frame). This is a ~6x reduction in tokens per frame, enabling either:
- Higher FPS at the same token budget
- Same FPS at ~6x lower cost
- Or a mix: increase FPS in high-activity segments while staying under budget

The analyse stage must adjust `tokens_per_frame` in its budget calculation when ROI cropping is active. The observe config's `roi_size` determines the effective tokens per frame.

**Cursor position annotation:** When building the Gemini request, the frame label includes cursor position within the crop: `[Frame 3 | 4500ms | cursor at (256, 180)]`. This helps the model understand where the cursor is without needing to visually locate it.

---

## Event-Driven Frame Selection

When triage is disabled, `select_frames_for_analysis()` replaces the uniform sampling approach with targeted frame selection based on observe results.

### Selection rules

**A. Event frames** — for each `LocalEvent`:

| Event type | Frames selected | ROI crop? |
|---|---|---|
| `click` | start, end | Yes |
| `hover` | start, end | Yes |
| `hesitate` | start, end | Yes |
| `dwell` | midpoint | Yes |
| `cursor_thrash` | start, end | Yes |
| `scroll` | start, end | No (full frame) |

ROI computation reuses `compute_roi_rects()` / `_lookup_cursor_at_timestamp()`.

**B. Visual change frames** — scan gaps between event frames longer than `visual_scan_gap_ms` (default 3000ms):
- Extract frames in gap at `visual_scan_fps` (default 1.0 FPS)
- Compute pairwise `compute_frame_diff()`
- Where magnitude exceeds `visual_change_threshold` (default 0.03): select frame before and after transition, full frame (no ROI)
- These are where the LLM discovers `navigate` and `change_ui_state` events

**C. Baseline frames** — after A+B, if any remaining gap exceeds `baseline_max_gap_ms` (default 5000ms), insert one frame at midpoint. Ensures LLM always has temporal context.

**D. Deduplication** — frames within `frame_dedup_ms` (default 200ms) of each other: keep highest-priority (event > visual_change > baseline).

### Observe-driven analyse path

`run_analyse_from_observe()` in `stages/analyse.py` processes selected frames:

1. **Batching** — `_batch_selected_frames()` groups frames by time proximity. New batch when gap > `batch_gap_ms` (default 5000ms) or frame count × `tokens_per_frame` exceeds `token_budget_per_segment`.
2. **Frame extraction** — `extract_frames_at_timestamps()` in `src/video.py` decodes only at target timestamps using sequential grab/retrieve with seek optimization.
3. **ROI cropping** — frames with `roi` set are cropped; visual_change and baseline frames are sent full-frame.
4. **Prompt** — `observe_driven.txt` template with variables: `{batch_index}`, `{start_time}`, `{end_time}`, `{frame_count}`, `{frame_annotations}`, `{local_events}`. Frame labels include reason and cursor position. Local events filtered to batch time range.
5. **Response** — same `_RESPONSE_SCHEMA` and `_parse_events()` as the triage-driven path.

---

## LLM Enrichment Flow

Local events marked with `needs_enrichment = True` are candidates for LLM confirmation. Rather than making separate API calls per local event, the enrichment happens within the existing analyse stage:

1. The analyse prompt template gains a new `{local_events}` placeholder
2. For each segment, local events overlapping that segment's time range are formatted as structured text and injected into the prompt
3. The system prompt is updated to instruct Gemini to:
   - Confirm or reject each local event candidate
   - Add `interaction_target`, `page_title`, and `frame_description` to confirmed events
   - Report any events the local stage missed

This approach requires no additional API calls — the local event context is included in the same requests the analyse stage already makes.

**Prompt injection format:**
```
The following events were detected locally from cursor tracking and optical flow.
Please confirm, reject, or modify each one, and add any events that were missed.

Local event candidates:
- [4500ms–4800ms] hover at (450, 320), confidence 0.6 — confirm and identify the UI element
- [6200ms–6200ms] click candidate at (380, 510), confidence 0.3 — confirm if a click occurred
- [8000ms–9500ms] cursor_thrash in region (200,100)–(600,400), confidence 0.8
```

Gemini's structured response already includes event type, frame indices, and description — so confirmed local events naturally merge into the same output format.

---

## Integration with Existing Stages

### Runner Changes

`_process_session` in `src/runner.py` supports both pipeline modes:

**Triage-driven:** `triage → observe → analyse → merge`

**Observe-driven:** `observe → analyse_from_observe → merge` (triage skipped)

Logic:
1. If `config.triage.enabled`: run triage as before. Otherwise: `triage_result = None`.
2. If `config.observe.enabled`: run observe (passing `triage_result`, which may be `None`).
3. If `observe_result.selected_frames` is non-empty: use `run_analyse_from_observe()`. Otherwise: use `run_analyse()` (requires `triage_result`).
4. `run_merge()` accepts `triage_result: TriageResult | None`.

Same cache/resume pattern for all stages.

### Analyse Changes

`run_analyse` in `stages/analyse.py` receives `ObserveResult` as an optional parameter:

- If ROI is enabled and observe result has ROI rects: use cropped frames instead of full frames, adjust token budget accordingly
- Inject local events into the user prompt via `{local_events}` placeholder
- Add cursor position to frame labels
- When ROI cropping is active, set `tokens_per_frame` to the cropped frame token count (~258 for 512×512)

### Merge Changes

`run_merge` in `stages/merge.py` receives `ObserveResult` as an optional parameter:

- Local events with `needs_enrichment = False` (i.e., high-confidence events like scroll and clear thrash) are added directly to the event pool as `ResolvedEvent` instances
- Local events with `needs_enrichment = True` that were confirmed by the LLM are already in the analyse output — no special handling needed
- Dedup naturally handles any overlap between locally-synthesized and LLM-detected events

### Config Changes

`PipelineConfig` gains an `observe: ObserveConfig` field with sensible defaults. The observe stage is disabled by default (`enabled: False`) so existing branches are unaffected.

---

## Output Artifacts

Per-session, saved in `output/{session_id}/`:

```
observe.json              Full ObserveResult (trajectory, flow, local events, ROI rects)
observe_trajectory.json   Cursor trajectory only (compact, for visualisation tools)
```

`observe.json` is the resumable stage cache (same as `triage.json` and `analysis.json`).

`observe_trajectory.json` is a flat array of `{timestamp_ms, x, y, confidence, detected}` for easy plotting/debugging without loading the full observe result.

---

## File Changes Summary

| File | Change |
|---|---|
| `src/models.py` | Add `CursorDetection`, `FlowWindow`, `LocalEvent`, `ROIRect`, `SelectedFrame`, `ObserveResult`, `ObserveConfig`. Add `observe` field to `PipelineConfig`. Add `observe_metrics` to `SessionOutput`. Add `selected_frames` to `ObserveResult`. Add `batch_gap_ms` to `AnalyseConfig`. Add adaptive tracking + frame selection fields to `ObserveConfig`. |
| `src/config.py` | Add `observe` section to `DEFAULTS`. Add `batch_gap_ms` to analyse defaults. Add adaptive tracking + frame selection defaults. |
| `src/video.py` | Add `compute_optical_flow(frame_a, frame_b, grid_step)`. Add `crop_frame(frame, roi)`. Add `extract_frames_at_timestamps(path, timestamps_ms)` for targeted frame extraction. |
| `stages/observe.py` | Adaptive two-pass cursor tracking (`_match_frames`, `_identify_active_regions`). `select_frames_for_analysis()` with event/visual_change/baseline/dedup rules. `triage_result` optional throughout. |
| `stages/analyse.py` | Accept optional `ObserveResult`. Use ROI crops when available. Inject local events into prompt. Add `run_analyse_from_observe()` and `_batch_selected_frames()` for observe-driven path. |
| `stages/merge.py` | Accept optional `ObserveResult`. Accept optional `TriageResult`. Add high-confidence local events to event pool before dedup. |
| `src/runner.py` | Conditional triage. Choose analyse path based on `selected_frames`. Pass `triage_result=None` when skipped. |
| `prompts/system.txt` | Add instructions for handling local event candidates. |
| `prompts/user.txt` | Add `{local_events}` placeholder. |
| `prompts/observe_driven.txt` | **New file.** Prompt template for event-driven batches with non-uniform sampling. |
| `cursor_templates/` | Built-in cursor template PNGs + `templates.json` metadata (hotspot offsets). |
| `experiments/observe-driven/` | **New experiment branch.** Triage disabled, observe-driven flow. |

---

## Implementation Order

1. **Models + config** — Add all new pydantic models and config fields. Non-breaking: `ObserveConfig.enabled` defaults to `False`.
2. **Cursor templates** — Create `cursor_templates/` with initial set of arrow/hand/ibeam PNGs and metadata.
3. **Cursor tracking** — Implement template matching + interpolation in `stages/observe.py`. Test on one session, inspect `observe_trajectory.json`.
4. **Optical flow** — Add flow computation and `FlowWindow` summaries. Validate scroll detection on sessions with obvious scrolling.
5. **Local event synthesis** — Implement hover/dwell/thrash/scroll/hesitate/click-candidate detection. Compare against LLM-detected events from existing runs.
6. **ROI cropping** — Implement `ROIRect` computation and integrate into analyse stage. Measure token savings.
7. **LLM enrichment** — Update prompts to include local event context. Update analyse to inject local events and cursor positions.
8. **Merge integration** — Add local events to merge event pool.
9. **Runner integration** — Wire observe into the pipeline with cache/resume.

Steps 1–5 can be tested independently of the LLM (local computation only). Steps 6–9 integrate with the existing pipeline.

---

## Risks and Mitigations

**Cursor not visible in recordings.** Some screen recordings don't render the cursor into the video frames (the cursor is captured as a separate overlay by the recording software). Mitigation: the observe stage reports `cursor_detection_rate`. If it's near zero, the stage effectively becomes a no-op — flow summaries are still produced, but no cursor-dependent events or ROI crops are emitted. The pipeline falls back to full-frame analysis.

**Template mismatch.** The built-in cursor templates may not match the actual cursor in some recordings (different OS, custom theme, high-DPI). Mitigation: multi-scale matching helps, and custom templates can be added per-branch via `cursor_templates_dir` config. A future iteration could auto-detect the cursor template from the first few seconds of video.

**False positive local events.** Cursor trajectory analysis can misidentify events (e.g., a brief network-induced stutter looks like a hover). Mitigation: local events carry their own confidence scores, and the enrichment flow lets Gemini confirm or reject them. High-confidence-only local events (like scroll from uniform flow) can be added directly; ambiguous ones go through enrichment.

**ROI crops miss important context.** Cropping to cursor region may cut off relevant UI elements (notifications, status bars, nearby elements). Mitigation: configurable `roi_size` and `roi_padding`. The system prompt instructs Gemini that it's seeing a cropped region and should focus on elements near the cursor. For idle segments, ROI cropping is disabled (no cursor activity to centre on).

**Processing time.** Template matching at 10 FPS on 720p adds significant CPU time. Mitigation: segments can be processed in parallel. Template matching early-exits on high-confidence matches. The stage is optional and disabled by default.

**Duplicate events.** Events returned from local observations may be treated as separate events by the LLM analysis