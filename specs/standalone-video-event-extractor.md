# Standalone Video Event Extractor — Technical Spec

## Overview

A self-contained CLI application that extracts user interaction events from screen recording videos. It combines local computer vision (cursor tracking, optical flow) with Gemini video analysis to produce timestamped, structured event annotations.

The app lives entirely in `candidates/2026-03-14/` with its own venv, config, prompts, assets, and dependencies — no references to files outside that directory.

## CLI Interface

```bash
# From candidates/2026-03-14/
source .venv/bin/activate

python -m vex_extract \
  --video /path/to/screen_track.mp4 \
  --offset 29690 \
  [--config config.yaml]
```

### Arguments

| Argument | Required | Description |
|---|---|---|
| `--video` | Yes | File path to a screen track video |
| `--offset` | Yes | `screenTrackStartOffset` in milliseconds — offset between screen track start and full session start |
| `--config` | No | Path to config file (default: `config.yaml` in app root) |

### Output

Each run produces a timestamped output directory:

```
candidates/2026-03-14/output/2026-03-14_153045/
├── events.json                    # Final event output
├── run.log                        # Full run log (stdout mirror)
├── segments/
│   └── segment_000/
│       ├── video.mp4              # Extracted video segment
│       ├── prompt.txt             # Rendered Gemini prompt
│       ├── cv_summary.txt         # CV context sent to Gemini
│       ├── request.json           # Gemini client arguments
│       └── response.json          # Gemini response + token usage
├── cv/
│   ├── cursor_trajectory.json     # Frame-by-frame cursor positions
│   └── flow_windows.json          # Optical flow timeline
├── merged_events.json             # All segment events before dedup
└── run_metadata.json              # Config snapshot, timing, token totals
```

Temporary video files (normalised video, segment extractions for reuse) are saved to `candidates/2026-03-14/tmp/` so they persist between runs.

## Directory Structure

```
candidates/2026-03-14/
├── .venv/                         # Standalone Python virtual environment
├── vex_extract/                   # Application package
│   ├── __init__.py
│   ├── __main__.py                # CLI entrypoint (python -m vex_extract)
│   ├── cli.py                     # Click CLI definition
│   ├── config.py                  # Config loading + defaults
│   ├── pipeline.py                # Top-level orchestrator
│   ├── video.py                   # Video normalization, metadata, segment extraction
│   ├── cursor.py                  # Cursor tracking (template matching, interpolation)
│   ├── flow.py                    # Optical flow analysis
│   ├── cv_summary.py              # CV summary text generation for prompts
│   ├── gemini.py                  # Gemini API client + request logic
│   ├── analysis.py                # Segment analysis (prompt rendering, Gemini calls)
│   ├── merge.py                   # Event merging, dedup, cursor enrichment
│   ├── similarity.py              # String similarity + duplicate detection
│   └── models.py                  # Pydantic data models
├── prompts/
│   └── system.txt                 # Gemini prompt template (copied from cv_augmented.txt, modified)
├── cursor_templates/              # Cursor template PNGs + metadata.json
│   ├── metadata.json
│   ├── default.png
│   ├── pointer.png
│   └── ...
├── config.yaml                    # User-editable configuration
├── tmp/                           # Reusable temporary files (normalised video, etc.)
├── output/                        # Run outputs (one subdirectory per run)
├── requirements.txt               # Pinned dependencies
└── setup.sh                       # One-command setup script (creates venv, installs deps)
```

## Configuration

`config.yaml` — all parameters with sensible defaults, easily editable:

```yaml
# --- Gemini API ---
gemini:
  api_key_env: "GEMINI_API_KEY"       # Environment variable name for API key
  model: "gemini-2.5-flash"
  temperature: 0.1
  max_concurrent: 3                    # Max parallel Gemini requests

# --- Video ---
video:
  target_pixels: 2073600               # Normalization target (1920x1080 equivalent)
  video_fps: 20                        # FPS for Gemini video input

# --- Segmentation ---
segmentation:
  max_segment_duration_ms: 75000       # 75s max segment length
  segment_overlap_ms: 5000             # 5s overlap between segments

# --- Cursor Tracking ---
cursor:
  tracking_base_fps: 2.0               # Coarse pass frame rate
  tracking_peak_fps: 15.0              # Fine pass frame rate (active regions)
  tracking_displacement_threshold_px: 30  # Min displacement to trigger fine pass
  tracking_active_padding_ms: 500      # Padding around active regions
  template_scales: [0.8, 1.0, 1.25, 1.5]
  match_threshold: 0.6                 # Minimum confidence for cursor detection
  early_exit_threshold: 0.9            # Stop searching at this confidence
  max_interpolation_gap_ms: 500        # Max gap for linear interpolation
  smooth_window: 3                     # Moving average window size
  smooth_displacement_threshold: 10.0  # Max displacement for smoothing

# --- Optical Flow ---
flow:
  flow_fps: 2.0                        # Frame rate for flow extraction
  flow_grid_step: 20                   # Grid spacing in pixels
  flow_window_size_ms: 1000            # Sliding window duration
  flow_window_step_ms: 500             # Sliding window step

# --- CV Summary ---
cv_summary:
  summary_window_ms: 250               # Window size for CV summary generation

# --- Merge & Dedup ---
merge:
  time_tolerance_ms: 2000              # Max time difference for duplicate detection
  similarity_threshold: 0.7            # Min description similarity for duplicates
  cursor_event_types:                  # Event types that get cursor coordinates
    - click
    - hover
    - dwell
    - cursor_thrash
    - select
    - drag
```

## Pipeline Steps

### Step 1: Normalize Video

**Input**: Raw screen track video from `--video` argument.

**Logic**: Port `src/video.py:normalize_video()`. Probe video dimensions from a reference frame near the end. Compute output dimensions to match `target_pixels` while preserving aspect ratio. Re-encode with ffmpeg (libx264, CRF 23, no audio, even dimensions with letterboxing).

**Output**: Normalised video saved to `tmp/<video_stem>_normalized.mp4`. Skip normalization if the file already exists in `tmp/` (reuse between runs).

**Also**: Extract `VideoMetadata` (duration_ms, fps, width, height) from the normalised video using ffprobe. The width and height are used later as `viewport_width` and `viewport_height` in the final events.

### Step 2: Cursor Tracking

**Input**: Normalised video, cursor templates from `cursor_templates/`.

**Logic**: Port the two-pass adaptive cursor tracking from `stages/observe.py`:

1. **Load templates** from `cursor_templates/metadata.json` + PNG files
2. **Pre-scale templates** at configured scale factors
3. **Pass 1 (coarse)**: Sample at `tracking_base_fps` across full video at 360p height. Run `cv2.matchTemplate` with TM_CCOEFF_NORMED for each frame against all templates at all scales. Record detections above `match_threshold`.
4. **Identify active regions**: Find intervals where cursor displacement exceeds `tracking_displacement_threshold_px`. Merge overlapping intervals with `tracking_active_padding_ms`.
5. **Pass 2 (fine)**: Re-sample active regions at `tracking_peak_fps`. Replace coarse detections with fine detections in those intervals.
6. **Interpolate**: Fill gaps shorter than `max_interpolation_gap_ms` with linear interpolation between detected positions.
7. **Smooth**: Apply moving average (window size `smooth_window`) for small displacements below `smooth_displacement_threshold`.

**Output**: `cursor_trajectory.json` — array of `CursorDetection` objects:
```json
{
  "timestamp_ms": 1500.0,
  "x": 432.5,
  "y": 287.3,
  "confidence": 0.82,
  "template_id": "pointer",
  "detected": true
}
```

This is the **raw timeline**. No analysis, filtering, or event synthesis is performed. Low-confidence (`detected: false`, interpolated) and missing entries are excluded from the saved output — only entries where the cursor was detected or successfully interpolated are retained.

### Step 3: Optical Flow Analysis

**Input**: Normalised video.

**Logic**: Port `stages/observe.py:compute_flow_summaries()`:

1. Extract consecutive frame pairs at `flow_fps`
2. For each pair, compute sparse Lucas-Kanade optical flow on a regular grid (`flow_grid_step` spacing)
3. Aggregate into sliding windows (`flow_window_size_ms` duration, `flow_window_step_ms` step):
   - Mean flow magnitude
   - Dominant direction (8-bin compass: N, NE, E, SE, S, SW, W, NW)
   - Flow uniformity (fraction of points moving in dominant direction)
   - Cursor-flow divergence (if cursor data available for that window)

**Output**: `flow_windows.json` — array of `FlowWindow` objects:
```json
{
  "start_ms": 1000.0,
  "end_ms": 2000.0,
  "mean_flow_magnitude": 4.2,
  "dominant_direction": "S",
  "flow_uniformity": 0.78,
  "cursor_flow_divergence": 1.3
}
```

This is the **raw timeline**. No event synthesis or classification is performed.

### Step 4: Create Video Segments

**Input**: Normalised video, duration from metadata.

**Logic**: Port `stages/generate_baselines.py:compute_segments()`:

1. Compute number of segments: `ceil(duration_ms / max_segment_duration_ms)`
2. Divide duration evenly: `base_duration = duration_ms / n_segments`
3. Each segment spans `[i * base_duration - overlap, (i+1) * base_duration + overlap]`, clamped to `[0, duration_ms]`
4. Track overlap boundaries for later dedup
5. Extract each segment using ffmpeg (`-c copy` with fallback to re-encode)

**Output**: Segment video files in `tmp/segments/segment_000.mp4`, etc. Reused between runs if they exist. Segment metadata (boundaries, overlap zones) is computed fresh each run.

### Step 5: Generate Gemini Prompts

**Input**: Prompt template from `prompts/system.txt`, cursor trajectory, flow windows, segment metadata.

**Logic**: For each segment, render the prompt template with:

- Session context (segment index, total segments, time range)
- **CV context block**: Generate a text summary of cursor activity and optical flow for the segment's time range, using the logic from `stages/generate_cv_augmented.py:generate_cv_summary()`:
  - Divide segment into windows (`summary_window_ms`)
  - Classify cursor activity per window: "stationary", "moving", or "not-detected"
  - Add representative cursor coordinates when available
  - Add scroll annotations from flow data (scroll-up/down/left/right)
  - Merge consecutive identical windows into ranges

**Prompt modifications vs existing `cv_augmented.txt`**:
- Remove `cursor_position_x` and `cursor_position_y` from the **output schema** section (step 6 handles cursor coordinates via timeline lookup instead)
- Keep all other instructions: event types, classification rules, hover detection guidance, UI state change detection, confidence calibration, temporal granularity

**Output**: Rendered prompt string per segment (saved to `segments/segment_NNN/prompt.txt`).

### Step 6: Gemini Analysis

**Input**: Video segment + rendered prompt per segment.

**Logic**: Port from `stages/generate_cv_augmented.py:analyse_segment_with_cv()` and `src/gemini.py:make_request()`:

1. Create Gemini client using API key from env var specified in config
2. For each segment (up to `max_concurrent` in parallel):
   - Read segment video bytes
   - Build `types.Part` with video data, fps from config
   - Call `client.models.generate_content()` with system prompt, video part, response schema, temperature
   - Parse JSON response into event array
   - Retry with exponential backoff on failure (max 3 retries)
3. **Response schema** enforces structured output:
   - Required: `type` (enum of 11 event types), `time_start_ms`, `time_end_ms`, `description`, `confidence`
   - Optional: `interaction_target`, `page_title`, `page_location`, `frame_description`
   - **No** `cursor_position_x`/`cursor_position_y` in schema (cursor coordinates come from CV timeline in step 8)

**Logging**: For each segment, save to `output/<run_id>/segments/segment_NNN/`:
- `request.json` — model, temperature, video_fps, segment boundaries, schema, video size
- `prompt.txt` — full rendered system prompt
- `cv_summary.txt` — CV context block
- `response.json` — full Gemini response including `input_tokens`, `output_tokens`, raw text

**Output**: List of raw events per segment with segment-relative timestamps.

### Step 7: Merge Events

**Input**: Raw events from all segments, segment metadata, `screenTrackStartOffset`.

**Logic**: Port from `stages/generate_baselines.py` and `stages/merge.py`:

1. **Adjust timestamps**: For each segment's events, convert segment-relative timestamps to absolute:
   - `absolute_ms = segment_relative_ms + segment.start_ms + screenTrackStartOffset`
2. **Combine** all events from all segments into a single list, sort by `time_start`
3. **Overlap-aware dedup**: For events near segment boundaries (within overlap zones), match by type + temporal proximity + description similarity. Keep higher-confidence version. Uses `similarity_threshold` from config.
4. **General dedup**: Second pass over all events using `time_tolerance_ms` and `similarity_threshold`. Same logic — same type, overlapping time (within tolerance), similar description → keep higher confidence.
5. **Add viewport dimensions**: Set `viewport_width` and `viewport_height` on every event from the normalised video metadata.

**Output**: Deduplicated, timestamp-resolved event list. Intermediate `merged_events.json` saved before dedup for debugging.

### Step 8: Cursor Coordinate Enrichment

**Input**: Merged events from step 7, cursor trajectory from step 2.

**Logic**: For each event whose type is in `merge.cursor_event_types` (click, hover, dwell, cursor_thrash, select, drag):

1. Look up the cursor trajectory at the event's `time_start` (adjusted back to screen-track-relative time by subtracting `screenTrackStartOffset`)
2. **Click/hover/dwell/select**: Find the closest cursor detection within ±500ms of event start. Use that position.
3. **cursor_thrash/drag**: Average cursor positions across the event's time range.
4. If a matching cursor position is found, set `cursor_position: {x, y}` on the event.
5. If no match is found, set `cursor_position: null`.

**Output**: Final enriched event list.

### Step 9: Save Output

**Input**: Enriched events, run metadata.

**Logic**:
1. Generate run ID: `YYYY-MM-DD_HHMMSS` from current time
2. Write `events.json` — array of event objects conforming to the output schema
3. Write `run_metadata.json`:
   - Config snapshot
   - Video path, duration, normalised dimensions
   - Per-segment: boundaries, event count, token usage
   - CV stats: cursor detections count, flow windows count
   - Totals: events before/after dedup, total tokens, processing time
4. Write `run.log` — full pipeline log

## Output Event Schema

Based on `event-schema.json`, minus `source`, `transcript_id`, `study_id`, `task_id`:

```json
{
  "type": "click",
  "time_start": 30690,
  "time_end": 30890,
  "description": "User clicks the Search button in the top navigation bar",
  "confidence": 0.92,
  "interaction_target": "Search button",
  "cursor_position": { "x": 432, "y": 87 },
  "page_title": "Home - Travel Expert",
  "page_location": "https://example.com/home",
  "viewport_width": 1920,
  "viewport_height": 1080,
  "frame_description": "Homepage with navigation bar at top, hero image, and search panel in center"
}
```

**Required fields**: `type`, `time_start`, `time_end`, `description`, `confidence`

**Optional fields**: `interaction_target`, `cursor_position` (object with x, y or null), `page_title`, `page_location`, `viewport_width`, `viewport_height`, `frame_description`

**Cursor position rule**: `cursor_position` is set for cursor-based event types (click, hover, dwell, cursor_thrash, select, drag) when a matching cursor detection exists in the timeline. Set to `null` when no match is found. Omitted for non-cursor events (navigate, input_text, scroll, hesitate, change_ui_state).

## Dependencies

```
# requirements.txt
google-genai>=1.0.0
opencv-python-headless>=4.8.0
numpy>=1.24.0
click>=8.1.0
pydantic>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
```

**System requirements**: `ffmpeg` and `ffprobe` must be available on PATH. Python 3.10+.

## Setup

```bash
cd candidates/2026-03-14
./setup.sh
```

`setup.sh`:
1. Creates `.venv` if it doesn't exist
2. Installs dependencies from `requirements.txt`
3. Verifies `ffmpeg` and `ffprobe` are available
4. Prints instructions for setting `GEMINI_API_KEY`

## Caching & Reuse

The `tmp/` directory enables reuse between runs:

| Artifact | Location | Reuse condition |
|---|---|---|
| Normalised video | `tmp/<stem>_normalized.mp4` | Same source video path & stem |
| Video segments | `tmp/segments/segment_NNN.mp4` | Same normalised video + same segmentation config |

CV analysis (cursor tracking, optical flow) is **not** cached in `tmp/` — it runs fresh each invocation since it's fast and config changes affect results. Results are saved per-run in `output/<run_id>/cv/`.

## Error Handling

- **Missing API key**: Exit with clear message naming the expected env var from config
- **ffmpeg not found**: Exit with install instructions
- **Gemini API failure**: Retry with exponential backoff (3 attempts). On final failure, log the error, skip the segment, and continue with remaining segments. Final output notes which segments failed.
- **No cursor detections**: Pipeline continues — CV summary shows "not-detected" throughout, events get `cursor_position: null`
- **Invalid video**: Exit with ffprobe error details

## Source Code Porting Notes

The following functions/logic should be ported from the existing codebase into the standalone app. Each should be self-contained with no imports from outside `candidates/2026-03-14/`.

| Standalone module | Source | Functions/logic to port |
|---|---|---|
| `video.py` | `src/video.py` | `normalize_video()`, `get_video_metadata()`, `extract_frames()`, `compute_optical_flow()` |
| `cursor.py` | `stages/observe.py` | `load_templates()`, `_prescale_templates()`, `match_cursor_in_frame()`, `_identify_active_regions()`, `track_cursor()`, `interpolate_trajectory()`, `smooth_trajectory()` |
| `flow.py` | `stages/observe.py` | `compute_flow_summaries()`, `_aggregate_flow_window()`, `_angle_to_direction()` |
| `cv_summary.py` | `stages/generate_cv_augmented.py` | `generate_cv_summary()`, `_classify_cursor_activity()`, `_find_scroll_annotation()` |
| `analysis.py` | `stages/generate_baselines.py` | `compute_segments()`, `extract_segment()`, `analyse_segment()` (modified for CV context) |
| `gemini.py` | `src/gemini.py` | `create_client()`, `make_request()` |
| `merge.py` | `stages/generate_baselines.py` + `stages/merge.py` | `adjust_timestamps()`, `deduplicate_overlap_events()`, `deduplicate_events()`, cursor position lookup logic |
| `similarity.py` | `src/similarity.py` | `string_similarity()`, `events_are_duplicates()` |
| `models.py` | `src/models.py` | `VideoMetadata`, `VideoSegment`, `CursorDetection`, `FlowWindow`, `ResolvedEvent` (subset) |
| `prompts/system.txt` | `prompts/cv_augmented.txt` | Full prompt template, modified to remove cursor coordinates from output schema |
