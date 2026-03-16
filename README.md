# VEX — Video Event Extraction

Experiment framework for extracting behavioural events from screen recordings using Gemini's vision API. Supports rapid pipeline iteration through branches and numbered iterations, each with their own config, prompts, and optional custom pipeline logic.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Copy `.env.example` to `.env` and add your Gemini API key:

```bash
cp .env.example .env
```

Requires `ffmpeg` and `ffprobe` on PATH.

## Usage

### Run a pipeline iteration

```bash
vex run --branch adaptive --iteration 1
```

Process specific sessions:

```bash
vex run -b adaptive -i 1 --session travel_expert_lisa --session travel_expert_william
```

Override config values from the CLI:

```bash
vex run -b adaptive -i 1 -o triage.sample_fps=3 -o analyse.temperature=0.2
```

Enable the observe stage (triage-driven, with ROI cropping):

```bash
vex run -b adaptive -i 1 -o observe.enabled=true
```

Run observe-driven mode (triage disabled, adaptive frame selection):

```bash
vex run -b observe-driven -i 1
```

Run visual-change-driven mode (screen content changes as primary signal):

```bash
vex run -b visual-change-driven -i 1
```

Or enable it ad-hoc on any branch:

```bash
vex run -b adaptive -i 1 -o triage.enabled=false -o observe.enabled=true
```

Enable visual-change-driven ad-hoc:

```bash
vex run -b adaptive -i 1 -o triage.enabled=false -o observe.enabled=true -o observe.visual_change_driven=true
```

### List experiments

```bash
vex list
vex list --branch adaptive
```

### Compare iterations

```bash
vex compare                                        # all branches and iterations
vex compare --branch adaptive                      # all iterations in a branch
vex compare --branch adaptive --iterations 1,2     # specific iterations
vex compare --iterations 1                         # iteration 1 across all branches
vex compare -b adaptive -i 1,2 -s travel_expert_lisa  # with session detail
```

## Pipeline

Three pipeline modes are available:

### Triage-driven (default)

The original path. Triage segments the video by activity level, analyse samples frames uniformly per segment.

1. **Triage** — Samples frames from the screen track, computes frame-to-frame diffs, classifies segments by activity level (idle/low/medium/high), and assigns per-segment FPS. No API calls.
2. **Observe** *(optional)* — Tracks the cursor via multi-scale template matching, computes sparse optical flow, synthesizes local events (hover, dwell, scroll, thrash, click candidates, hesitation), and produces ROI crop coordinates for the analyse stage. No API calls. Enable with `observe.enabled=true`.
3. **Analyse** — Extracts frames at the assigned FPS, sends them to Gemini with interleaved labels and images, parses structured event responses. Context frames from adjacent segments provide continuity. When observe is enabled, frames are ROI-cropped around the cursor (~6x token reduction), frame labels include cursor coordinates, and local event candidates are injected into the prompt for LLM confirmation/rejection.
4. **Merge** — Resolves frame-indexed events to absolute millisecond timestamps (offset by `screenTrackStartOffset`), discards context-only events, deduplicates overlapping events, and writes final output. When observe is enabled, high-confidence local events (scroll, thrash) are added directly to the event pool before dedup.

### Observe-driven (adaptive)

Event-driven path. Triage is disabled; observe selects only the frames the LLM needs. Enable with `triage.enabled=false` and `observe.enabled=true`.

```
observe (adaptive FPS)  →  frame selection  →  analyse (event-driven batches)  →  merge
```

1. **Observe** — Adaptive two-pass cursor tracking: a coarse pass at `tracking_base_fps` (default 2) across the full video identifies active regions where cursor displacement exceeds a threshold, then a fine pass at `tracking_peak_fps` (default 15) fills in detail within those regions. Optical flow and local event synthesis run as before. After event synthesis, `select_frames_for_analysis()` picks frames using four rules:
   - **Event frames** — start/end (or midpoint for dwells) of each local event, ROI-cropped around the cursor
   - **Visual change frames** — in gaps between events longer than `visual_scan_gap_ms`, extract at `visual_scan_fps` and select frames where `compute_frame_diff()` exceeds `visual_change_threshold` (full frame, no ROI — these are where navigate and change_ui_state events are discovered)
   - **Baseline frames** — one frame at the midpoint of any remaining gap longer than `baseline_max_gap_ms`, ensuring temporal coverage
   - **Deduplication** — frames within `frame_dedup_ms` of each other are merged, keeping higher-priority frames (event > visual_change > baseline)
2. **Analyse** — `run_analyse_from_observe()` groups selected frames into batches by time proximity (`batch_gap_ms`) and token budget. Each batch is sent to Gemini with frame annotations explaining the non-uniform sampling (reason, cursor position). The `observe_driven.txt` prompt instructs the LLM to confirm/reject cursor events, identify navigate/change_ui_state at visual transitions, and note anything in baseline frames.
3. **Merge** — Same as triage-driven, but `triage_result` is `None`. Triage metrics fall back to empty defaults.

See `experiments/observe-driven/` for a ready-to-run experiment using this mode.

### Visual-change-driven

Uses screen content changes as the primary signal instead of cursor motion. Sends ~30-60 high-signal moments to the LLM instead of 500+ low-signal frames. Token usage drops from ~750k to ~33k-67k per 5-minute session. Enable with `observe.visual_change_driven=true` (triage disabled, observe enabled).

```
observe (visual change + flow + cursor)  →  moment detection  →  Pass 1 (scenes)  →  Pass 2 (interactions)  →  merge
```

1. **Observe** — Runs three detection passes in local compute (no API calls):
   - **Visual change detection** — Extracts frames at `change_detect_fps` (default 4), computes per-pair absdiff → blur → threshold → morphological close → connected components. Clusters contiguous change frames into `VisualChangeEvent`s classified as `scene_change` (≥30% of frame changed), `local_change` (small, short), or `continuous_change` (long duration, stable area).
   - **Flow event detection** — Converts existing `FlowWindow` summaries into discrete `FlowEvent`s (scroll, pan, mixed) by finding runs of 2+ consecutive windows with high uniformity and magnitude.
   - **Cursor tracking** — Same adaptive two-pass tracking as observe-driven (optional, controlled by `cursor_tracking_enabled`). Cursor stops (stationary ≥ `cursor_stop_min_ms`) are detected separately. Dwells and thrashes reuse existing detectors.
   - **Moment detection** — Combines the three timelines into `Moment`s via a 9-step algorithm: visual changes become candidates → scrolls are subtracted (visual changes overlapping flow events) → remaining classified by category → cursor context attached → cursor stops added (not overlapping visual changes) → dwells/thrashes added → adjacent moments merged → budget-based selection by priority → baseline moments inserted in gaps.
2. **Pass 1 (Scene Descriptions)** — Scene change, scroll, continuous, and baseline moments each get one full frame sent to Gemini. Returns `SceneDescription`s (page title, location, description, interactive elements) that serve as reusable text context for Pass 2.
3. **Pass 2 (Interaction Analysis)** — Interaction, cursor_stop, and cursor_only moments are batched by time proximity. Each batch includes ROI-cropped before/after frames (for interactions) or a single cursor-centered frame (for stops), plus the most recent scene description as a text preamble (not an image). Returns `RawEvent`s in the same format as other modes.
4. **Merge** — Same as other modes. Scroll moments from the visual-change-driven pipeline are injected directly as `ResolvedEvent`s (self-describing, no LLM needed) with page title from scene descriptions.

See `experiments/visual-change-driven/` for a ready-to-run experiment using this mode. See `VISUAL_CHANGE_SPEC.md` for the full technical design.

## Experiment Structure

```
experiments/
  adaptive/                      # branch (triage-driven)
    config.yaml                  # branch-level defaults
    prompts/                     # branch-level prompt overrides (optional)
    1/                           # iteration
      config.yaml                # iteration overrides
      prompts/                   # iteration prompt overrides (optional)
      pipeline.py                # custom stage functions (optional)
      output/{session_id}/       # triage.json, events.json, session.json
  observe-driven/                # branch (observe-driven, triage disabled)
    config.yaml
    1/
      config.yaml
      output/{session_id}/       # observe.json, analysis.json, events.json, session.json
  visual-change-driven/          # branch (visual-change-driven, triage disabled)
    config.yaml
    1/
      config.yaml
      output/{session_id}/       # observe.json, analysis.json, events.json, session.json
```

### Config precedence

```
Built-in defaults → branch config.yaml → iteration config.yaml → CLI --override flags
```

Each layer deep-merges into the previous. CLI flags always win.

### Prompt resolution

```
iteration/prompts/ → branch/prompts/ → prompts/ (root defaults)
```

### Custom pipeline logic

An iteration can override stages by placing a `pipeline.py` in its directory with `run_triage`, `run_observe`, `run_analyse`, or `run_merge` functions. Missing functions fall through to the defaults.

## Output

Per-session output in `experiments/{branch}/{iteration}/output/{session_id}/`:

- `events.json` — final events matching `event-schema.json`
- `session.json` — full session output with per-stage metrics and token usage
- `triage.json` — triage segments (only when triage is enabled)
- `observe.json` — observe stage result (only when observe is enabled; used for cache/resume). In observe-driven mode: cursor trajectory, flow summary, local events, selected frames, ROI rects. In visual-change-driven mode: cursor trajectory, visual change events, flow events, moments, and scene descriptions (populated after Pass 1).
- `observe_summary.json` — human-readable summary (only when observe is enabled). In observe-driven mode: detection rate, template match counts, event counts by type, selected frame counts by reason. In visual-change-driven mode: moment counts by category, visual change event count, flow event count, estimated tokens, and per-moment details.

Run-level metadata in `experiments/{branch}/{iteration}/output/metadata.json`.

## CLI Reference

### `vex run`

Run a pipeline iteration.

| Flag | Short | Type | Default | Description |
|---|---|---|---|---|
| `--branch` | `-b` | string | *required* | Experiment branch name |
| `--iteration` | `-i` | int | *required* | Iteration number |
| `--session` | `-s` | string (repeatable) | all | Session ID(s) to process |
| `--override` | `-o` | string (repeatable) | — | Config override as `dotted.key=value` |
| `--force` | `-f` | flag | false | Re-run all stages, ignoring cached outputs |
| `--base-dir` | | path | `.` | Project base directory |

### `vex list`

List experiment branches and iterations.

| Flag | Short | Type | Default | Description |
|---|---|---|---|---|
| `--branch` | `-b` | string | all | Filter by branch name |
| `--base-dir` | | path | `.` | Project base directory |

### `vex compare`

Compare event counts between iterations. With no flags, compares all branches and iterations that have output.

| Flag | Short | Type | Default | Description |
|---|---|---|---|---|
| `--branch` | `-b` | string | all | Branch name |
| `--iterations` | | string | all | Comma-separated iteration numbers |
| `--session` | `-s` | string | all | Filter by session ID |
| `--base-dir` | | path | `.` | Project base directory |

## Config Reference

All options can be set in `config.yaml` or via CLI overrides (`-o triage.sample_fps=3`).

### `triage`

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the triage stage |
| `sample_fps` | float | `5.0` | Frame sampling rate for activity detection |
| `resolution_height` | int | `480` | Scale frames to this height for diff computation |
| `window_size_ms` | int | `3000` | Sliding window size for activity classification |
| `window_step_ms` | int | `1000` | Sliding window step size |
| `min_segment_duration_ms` | int | `5000` | Minimum segment length after merging |
| `thresholds` | dict | `{idle: 0.005, low: 0.02, medium: 0.08}` | Activity magnitude thresholds per tier |
| `fps_mapping` | dict | `{idle: 0.5, low: 2.0, medium: 4.0, high: 10.0}` | FPS assigned to each activity tier |

### `observe`

Disabled by default. Enable with `observe.enabled=true`.

**Pipeline mode**

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the observe stage |
| `visual_change_driven` | bool | `false` | Use visual-change-driven pipeline (screen content changes as primary signal) |
| `cursor_tracking_enabled` | bool | `true` | Enable cursor tracking (can be disabled for recordings without a visible cursor) |

**Visual change detection** (visual-change-driven mode)

| Key | Type | Default | Description |
|---|---|---|---|
| `change_detect_fps` | float | `4.0` | Frame rate for visual change detection |
| `change_pixel_threshold` | int | `20` | Absdiff threshold (0–255) for change detection |
| `change_min_area_px` | int | `1000` | Minimum connected component area (px) to qualify as a change |
| `change_blur_kernel` | int | `5` | Gaussian blur kernel size for noise suppression |
| `change_morph_kernel` | int | `5` | Morphological close kernel size for merging nearby pixels |
| `scene_change_area_threshold` | float | `0.3` | Fraction of frame area to classify as scene_change vs local_change |
| `continuous_change_max_duration_ms` | int | `3000` | Duration beyond which a sustained change is classified as continuous |

**Moment detection** (visual-change-driven mode)

| Key | Type | Default | Description |
|---|---|---|---|
| `cursor_stop_min_ms` | int | `300` | Minimum stationary duration (ms) for cursor stop detection |
| `cursor_stop_radius_px` | float | `15.0` | Max cursor drift (px) during a stop |
| `moment_merge_gap_ms` | int | `500` | Adjacent moments within this gap are merged |
| `token_budget_per_minute` | int | `50000` | Token budget per minute of screen track for moment selection |
| `tokens_full_frame` | int | `1600` | Estimated tokens per full-frame moment (scene_change, scroll, continuous, baseline) |
| `tokens_roi_pair` | int | `750` | Estimated tokens per ROI before/after pair (interaction moments) |
| `tokens_roi_single` | int | `300` | Estimated tokens per single ROI crop (cursor_stop, cursor_only moments) |
| `roi_min_size` | int | `256` | Minimum ROI crop size (px) for Pass 2 frames |

**Cursor tracking**

| Key | Type | Default | Description |
|---|---|---|---|
| `tracking_fps` | float | `5.0` | Legacy single-pass FPS (used when not using adaptive two-pass) |
| `tracking_base_fps` | float | `2.0` | Coarse pass FPS for adaptive tracking |
| `tracking_peak_fps` | float | `15.0` | Fine pass FPS within active regions |
| `tracking_displacement_threshold_px` | float | `30.0` | Cursor displacement (px) between coarse frames to mark region as active |
| `tracking_active_padding_ms` | int | `500` | Padding (ms) added to each side of active regions |
| `resolution_height` | int | `720` | Scale frames to this height for template matching |
| `template_scales` | list | `[0.8, 1.0, 1.25, 1.5]` | Scales to try during multi-scale template matching |
| `match_threshold` | float | `0.6` | Minimum confidence to accept a cursor match |
| `early_exit_threshold` | float | `0.9` | Stop searching templates once confidence reaches this |
| `max_interpolation_gap_ms` | int | `500` | Max gap to interpolate between detected cursor positions |
| `smooth_window` | int | `3` | Moving average window size for trajectory smoothing |
| `smooth_displacement_threshold` | float | `50.0` | Max displacement (px) to apply smoothing |

**Optical flow**

| Key | Type | Default | Description |
|---|---|---|---|
| `flow_fps` | float | `2.0` | Frame rate for optical flow computation |
| `flow_grid_step` | int | `20` | Grid spacing (px) for sparse Lucas-Kanade flow |
| `flow_window_size_ms` | int | `1000` | Sliding window size for flow aggregation |
| `flow_window_step_ms` | int | `500` | Sliding window step for flow aggregation |

**Event synthesis — hover**

| Key | Type | Default | Description |
|---|---|---|---|
| `hover_min_ms` | int | `300` | Minimum stationary duration to detect a hover |
| `hover_max_ms` | int | `2000` | Maximum duration (beyond this becomes a dwell) |
| `hover_radius_px` | float | `15.0` | Max cursor drift (px) to still count as stationary |

**Event synthesis — dwell**

| Key | Type | Default | Description |
|---|---|---|---|
| `dwell_min_ms` | int | `2000` | Minimum stationary duration to detect a dwell |
| `dwell_radius_px` | float | `20.0` | Max cursor drift (px) to still count as stationary |

**Event synthesis — thrash**

| Key | Type | Default | Description |
|---|---|---|---|
| `thrash_window_ms` | int | `1000` | Sliding window size for thrash detection |
| `thrash_min_direction_changes` | int | `4` | Min direction reversals to trigger thrash |
| `thrash_min_speed_px_per_sec` | float | `500.0` | Min cursor speed to trigger thrash |
| `thrash_angle_threshold_deg` | float | `90.0` | Min angle between segments to count as a direction change |

**Event synthesis — click candidate**

| Key | Type | Default | Description |
|---|---|---|---|
| `click_stop_max_ms` | int | `200` | Max duration of a brief stop to consider a click |
| `click_stop_radius_px` | float | `5.0` | Max cursor drift during the stop |
| `click_min_confidence` | float | `0.3` | Confidence assigned to click candidates |

**Event synthesis — scroll**

| Key | Type | Default | Description |
|---|---|---|---|
| `scroll_min_flow_uniformity` | float | `0.6` | Min flow uniformity to detect a scroll |
| `scroll_min_magnitude` | float | `3.0` | Min flow magnitude to detect a scroll |

**Event synthesis — hesitation**

| Key | Type | Default | Description |
|---|---|---|---|
| `hesitation_min_ms` | int | `500` | Min pause duration to detect a hesitation |
| `hesitation_max_ms` | int | `2000` | Max pause duration |
| `hesitation_radius_px` | float | `10.0` | Max cursor drift during the pause |

**ROI**

| Key | Type | Default | Description |
|---|---|---|---|
| `roi_size` | int | `512` | Base ROI crop size (px) |
| `roi_padding` | int | `64` | Padding added around the ROI |

**Frame selection** (observe-driven mode)

| Key | Type | Default | Description |
|---|---|---|---|
| `visual_scan_gap_ms` | int | `3000` | Min gap (ms) between event frames to trigger visual change scanning |
| `visual_scan_fps` | float | `1.0` | FPS for extracting frames during visual change scanning |
| `visual_change_threshold` | float | `0.03` | Min frame diff magnitude (0–1) to flag a visual transition |
| `baseline_max_gap_ms` | int | `5000` | Max gap (ms) before inserting a baseline frame at midpoint |
| `frame_dedup_ms` | int | `200` | Frames within this many ms are deduplicated (keep highest priority) |

### `analyse`

| Key | Type | Default | Description |
|---|---|---|---|
| `model` | string | `"gemini-3-flash-preview"` | Gemini model ID |
| `temperature` | float | `0.1` | Sampling temperature |
| `max_concurrent` | int | `5` | Max concurrent Gemini requests |
| `token_budget_per_segment` | int | `50000` | Max tokens per segment (FPS is reduced to fit) |
| `tokens_per_frame` | int | `1548` | Estimated tokens per frame (258 when ROI-cropped) |
| `context_frames` | int | `2` | Frames to include from adjacent segments |
| `jpeg_quality` | int | `85` | JPEG encoding quality |
| `source` | string | `"unmod_website_test_video"` | Source type tag written to events |
| `batch_gap_ms` | int | `5000` | Max time gap (ms) between selected frames before starting a new batch (observe-driven mode) |

### `merge`

| Key | Type | Default | Description |
|---|---|---|---|
| `time_tolerance_ms` | int | `2000` | Max time gap (ms) to consider events duplicates |
| `similarity_threshold` | float | `0.7` | Min description similarity to consider events duplicates |
| `discard_context_events` | bool | `true` | Drop events detected only in context frames |

## Standalone Pipeline (`candidates/2026-03-14`)

A self-contained extraction pipeline in `candidates/2026-03-14/vex_extract/` that runs independently of the `vex` CLI framework above. Uses `run_standalone.py` to orchestrate runs across all 12 sessions and save results into experiment branches.

### Pipeline stages

```
normalize → cursor → flow → segment → prompt → gemini → merge
```

- **normalize** — Re-encode video to consistent resolution via ffmpeg
- **cursor** — Adaptive two-pass cursor tracking (coarse at base FPS, fine at peak FPS in active regions), with scale calibration and multi-candidate resolution
- **flow** — Sparse optical flow analysis
- **segment** — Split video into overlapping segments for Gemini
- **prompt** — Render prompts with CV summaries (no API calls)
- **gemini** — Send segments to Gemini for event detection
- **merge** — Merge, deduplicate, and enrich events with cursor positions

### Running experiments

Full pipeline run across all sessions:

```bash
python run_standalone.py \
    --candidate 2026-03-14 \
    --branch standalone-c \
    --iteration 1
```

Skip cursor or flow stages:

```bash
python run_standalone.py \
    --candidate 2026-03-14 \
    --branch standalone-b \
    --iteration 2 \
    --no-cursor --no-flow
```

Stop after prompt generation (no Gemini cost) with custom cursor FPS:

```bash
python run_standalone.py \
    --candidate 2026-03-14 \
    --branch standalone-c \
    --iteration 2 \
    -- --cursor-base-fps 3 --cursor-peak-fps 10 --stop-after prompt
```

Run specific sessions:

```bash
python run_standalone.py \
    --candidate 2026-03-14 \
    --branch standalone-c \
    --iteration 2 \
    --sessions travel_expert_william,opportunity_list_ben \
    -- --stop-after prompt
```

### Comparing cursor tracking experiments

`compare_cursor_experiments.py` compares cursor trajectories, per-segment cursor summaries, and event cursor enrichment between two experiment iterations. Designed for rapid iteration on cursor tracking parameters without Gemini cost.

```bash
python compare_cursor_experiments.py \
    --base standalone-c/1 \
    --experiment standalone-c/2
```

The report covers:
- **Trajectory comparison** — detection counts, per-frame agreement, position drift
- **Cursor summary diffs** — unified diffs of cursor text injected into each segment's Gemini prompt
- **Event enrichment** — re-enriches base events with the experimental trajectory to show which events gain/lose cursor positions and how positions shift

### Standalone experiment output

Results are saved to `experiments/{branch}/{iteration}/output/{session_id}/`:

- `events.json` — final merged events
- `run_metadata.json` — config, timing, token usage, segment details
- `cv/cursor_trajectory.json` — per-frame cursor detections
- `cv/flow_windows.json` — optical flow summaries
- `segments/segment_NNN/cursor_summary.txt` — cursor summary text injected into Gemini prompt
- `segments/segment_NNN/flow_summary.txt` — flow summary text injected into Gemini prompt
- `segments/segment_NNN/prompt.txt` — full rendered prompt

### Standalone CLI reference

Pass-through args after `--` are forwarded to `vex_extract`:

| Flag | Type | Description |
|---|---|---|
| `--cursor-base-fps` | float | Override coarse pass FPS (default: from config.yaml) |
| `--cursor-peak-fps` | float | Override fine pass FPS (default: from config.yaml) |
| `--stop-after` | choice | Stop after a stage: `normalize`, `cursor`, `flow`, `segment`, `prompt`, `gemini`, `merge` |
| `--skip` | choice (repeatable) | Skip a stage (downstream stages degrade gracefully) |
| `--no-cursor` | flag | Skip cursor tracking |
| `--no-flow` | flag | Skip optical flow |
| `--config` | path | Use an alternative config YAML |

## Input Data

12 sessions in `input_data/` with screen track videos, full session videos, and transcripts. Described in `input_data/manifest.json`. Input data is read-only and shared across all experiments.

## Project Layout

```
src/
  models.py       Pydantic data models (all frozen)
  config.py       Config loading, deep merge, defaults
  manifest.py     Manifest parser
  video.py        OpenCV frame extraction, diffs, optical flow, cropping, visual change detection
  gemini.py       Gemini API client wrapper
  prompts.py      Prompt resolution + template filling
  similarity.py   String similarity for dedup
  runner.py       Pipeline orchestration
  cli.py          Click CLI

stages/
  triage.py       Activity signal → segment classification
  observe.py      Cursor tracking, optical flow, local event synthesis, frame selection,
                  visual change detection, flow events, cursor stops, moment detection
  analyse.py      Gemini API calls per segment (triage-driven), per batch (observe-driven),
                  or per moment (visual-change-driven: Pass 1 scenes + Pass 2 interactions)
  merge.py        Timestamp resolution + dedup + scroll moment injection

cursor_templates/
  templates.json  Cursor template metadata (template_id, file, hotspot)
  *.png           Cursor template images (RGBA, used for template matching)
```

