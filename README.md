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

Enable the observe stage:

```bash
vex run -b adaptive -i 1 -o observe.enabled=true
```

### List experiments

```bash
vex list
vex list --branch adaptive
```

### Compare iterations

```bash
vex compare --branch adaptive --iterations 1,2
vex compare --branch adaptive --iterations 1,2 --session travel_expert_lisa
```

## Pipeline

Four stages run per session (observe is opt-in):

1. **Triage** — Samples frames from the screen track, computes frame-to-frame diffs, classifies segments by activity level (idle/low/medium/high), and assigns per-segment FPS. No API calls.
2. **Observe** *(optional)* — Tracks the cursor via multi-scale template matching, computes sparse optical flow, synthesizes local events (hover, dwell, scroll, thrash, click candidates, hesitation), and produces ROI crop coordinates for the analyse stage. No API calls. Disabled by default; enable with `observe.enabled=true`.
3. **Analyse** — Extracts frames at the assigned FPS, sends them to Gemini with interleaved labels and images, parses structured event responses. Context frames from adjacent segments provide continuity. When observe is enabled, frames are ROI-cropped around the cursor (~6x token reduction), frame labels include cursor coordinates, and local event candidates are injected into the prompt for LLM confirmation/rejection.
4. **Merge** — Resolves frame-indexed events to absolute millisecond timestamps (offset by `screenTrackStartOffset`), discards context-only events, deduplicates overlapping events, and writes final output. When observe is enabled, high-confidence local events (scroll, thrash) are added directly to the event pool before dedup.

## Experiment Structure

```
experiments/
  adaptive/                      # branch
    config.yaml                  # branch-level defaults
    prompts/                     # branch-level prompt overrides (optional)
    1/                           # iteration
      config.yaml                # iteration overrides
      prompts/                   # iteration prompt overrides (optional)
      pipeline.py                # custom stage functions (optional)
      output/{session_id}/       # triage.json, events.json, session.json
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
- `observe.json` — observe stage result with cursor trajectory, flow summary, local events, and ROI rects (only when observe is enabled; used for cache/resume)
- `observe_summary.json` — human-readable summary: detection rate, template match counts, event counts by type, event details (only when observe is enabled)

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

Compare event counts between iterations.

| Flag | Short | Type | Default | Description |
|---|---|---|---|---|
| `--branch` | `-b` | string | *required* | Branch name |
| `--iterations` | | string | *required* | Comma-separated iteration numbers |
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

**Cursor tracking**

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the observe stage |
| `tracking_fps` | float | `5.0` | Frame rate for cursor tracking |
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

### `merge`

| Key | Type | Default | Description |
|---|---|---|---|
| `time_tolerance_ms` | int | `2000` | Max time gap (ms) to consider events duplicates |
| `similarity_threshold` | float | `0.7` | Min description similarity to consider events duplicates |
| `discard_context_events` | bool | `true` | Drop events detected only in context frames |

## Input Data

12 sessions in `input_data/` with screen track videos, full session videos, and transcripts. Described in `input_data/manifest.json`. Input data is read-only and shared across all experiments.

## Project Layout

```
src/
  models.py       Pydantic data models (all frozen)
  config.py       Config loading, deep merge, defaults
  manifest.py     Manifest parser
  video.py        OpenCV frame extraction, diffs, optical flow, cropping
  gemini.py       Gemini API client wrapper
  prompts.py      Prompt resolution + template filling
  similarity.py   String similarity for dedup
  runner.py       Pipeline orchestration
  cli.py          Click CLI

stages/
  triage.py       Activity signal → segment classification
  observe.py      Cursor tracking, optical flow, local event synthesis, ROI
  analyse.py      Gemini API calls per segment
  merge.py        Timestamp resolution + dedup

cursor_templates/
  templates.json  Cursor template metadata (template_id, file, hotspot)
  *.png           Cursor template images (RGBA, used for template matching)
```

