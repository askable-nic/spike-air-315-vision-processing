# Adaptive Video Event Extraction — Project Spec

## Context

We have a previous Python pipeline (`video_events/`) that extracts behavioural events from screen recordings using Gemini's vision API. It has a versioning system (`pipelines/v0/`, `pipelines/v1-3fps/`, etc.) but pipeline iterations share the same core logic — only config values, prompts, and minor post-processing scripts vary between versions.

This project is a **new, standalone Python project** that replaces the analysis stage with an experiment framework designed for rapid pipeline iteration. Each experiment branch encapsulates its own pipeline logic, prompts, and config — so iterations can diverge structurally, not just parametrically.

The existing pipeline's **Prepare** stage (SSIM scene detection → clip splitting) is reused as-is. This project consumes its output.

### Language choice

Python 3.10+. The pipeline relies heavily on OpenCV and NumPy for frame-level computer vision — frame diffs, bounding box computation, and (in future iterations) cursor template matching and optical flow. These are native-speed operations with mature, well-maintained libraries. The existing pipeline is also Python, so there's no ecosystem mismatch when referencing its code or reusing patterns.

## Problem

The existing Analyse stage sends every scene clip to Gemini at a uniform FPS. Most screen recording time is idle. Uniform sampling wastes tokens on low-activity frames and may under-sample high-activity regions when FPS is reduced to control cost.

We need both cost efficiency and event fidelity — and we need to iterate quickly on the approach, comparing different strategies side-by-side on the same source videos.

Consider that video input may or may not be a better option than sending individual frames to Gemini as images.

## Goals

1. **Adaptive analysis** — high FPS during dense interactions, low FPS during idle periods
2. **Experiment framework** — each pipeline iteration is a self-contained branch with its own logic, prompts, config, and output
3. **Comparable results** — all iterations run against the same source videos, producing the same output schema, so results can be diffed
4. **LLM token usage** - Aim to keep total Gemini input token usage under 150,000 tokens per minute of source video

---

## Experiment Framework

### Concepts

- **Source videos** are shared across all experiments. They live in a single location and are never modified.
- **Prepared scenes** (from the existing Prepare stage) are also shared — scene clips + `manifest.json` are the common input to all experiments.
- **Experiment branch** — a named collection of pipeline iterations (e.g. `adaptive`, `uniform-baseline`, `cursor-tracking`). Each branch represents a distinct approach or hypothesis.
- **Iteration** — a numbered run within a branch (e.g. `adaptive/1`, `adaptive/2`). Each iteration is a self-contained snapshot: its own config, prompts, pipeline logic, and output. Iterations are append-only — you never modify a completed iteration, you create a new one.

### What lives inside a pipeline iteration

Each iteration should be self-contained enough that you can understand exactly what it did by looking at its directory alone. This means the iteration owns:

- **Config** — all parameters that control pipeline behaviour (thresholds, FPS mappings, model selection, concurrency limits, etc.)
- **Prompts** — the full text of every LLM prompt used during the run (system, user, idle, narrative)
- **Pipeline logic** — if this iteration's approach differs structurally from the default, the iteration contains the custom stage implementations
- **Output** — all artefacts produced by the run (triage results, analysis results, run metadata), organised per recording

The key principle: if you delete everything except the iteration directory and the shared input data, you should be able to understand and reproduce the run.

### What lives outside (shared utilities)

Some code is genuinely shared infrastructure that doesn't change between experiments. This code lives outside the experiment directories:

- **Framework orchestration** — the runner that loads config, resolves prompts, dispatches to stage functions, and writes output. This is the "engine" that all iterations run on.
- **Config loading and merging** — the logic for deep-merging defaults → branch → iteration → CLI overrides.
- **Video utilities** — OpenCV frame extraction, ffprobe metadata, JPEG encoding. These are mechanical operations that don't embody any experimental hypothesis.
- **Gemini API client** — auth, retry logic, rate limiting, response parsing. The wrapper around the API, not the prompts or model selection (which are per-iteration config).
- **String similarity** — dedup helper for the merge stage. A pure utility.
- **Manifest parser** — reads the existing Prepare stage's `manifest.json`. This is a fixed input format, not something that varies per experiment.
- **Data models / types** — shared dataclasses and type definitions.
- **CLI** — the command-line interface for running, listing, and comparing experiments.

The boundary is: **if changing it would change experimental results, it belongs inside the iteration. If it's plumbing, it's shared.**

Note that some stages (triage, analyse, merge) have a **default implementation** in shared code that most iterations will use as-is. An iteration that only changes config and prompts doesn't need any custom pipeline code — it just inherits the default. Custom `pipeline.py` files in an iteration directory are the exception for when an iteration needs to structurally change a stage.

### Branch config

Each branch has a config file that defines default settings for all its iterations. This includes parameters for each pipeline stage — triage thresholds, FPS mappings, model selection, concurrency, deduplication settings, etc.

An iteration's config overrides specific fields from the branch config. Only changed fields need to be specified — everything else is inherited.

### Config precedence

```
Built-in defaults → branch config → iteration config → CLI flags
```

Each layer deep-merges into the previous. CLI flags always win.

### Prompt resolution

Each iteration can have its own prompt files. Prompts are resolved with the same precedence as config: an iteration's prompts override the branch's prompts, which override the built-in defaults. If an iteration doesn't provide a particular prompt file, it inherits from the branch or falls back to the default.

### Custom pipeline logic

Most iterations only change config and prompts. But when structural changes are needed (e.g. adding a new triage signal, changing how context frames work, or experimenting with a completely different analysis approach), an iteration can include custom pipeline code that overrides specific stages.

The runner checks for custom stage functions in the iteration directory. If present, they're used instead of the default implementations. Missing functions fall through to the defaults. This means an iteration can override just triage while using the default analyse and merge, or override all three.

### Run metadata

Every run produces metadata alongside its output, capturing: branch/iteration/recording identifiers, timestamps, the full resolved config snapshot (so you know exactly what ran), token usage totals, per-stage timing and statistics, and any errors. This enables comparison between iterations without re-running them.

---

## Pipeline Stages

The default pipeline has three stages. An iteration can override any stage, but the default implementations described here handle the common case.

### Stage 1: Triage

**Purpose:** Classify segments within each scene by activity level using local computation. No API calls.

**Input:** Scene clips + `manifest.json` from Prepare.
**Output:** Triage results (segments with activity tiers + assigned FPS).

#### Activity signal

For each scene clip, sample frames and compute frame-to-frame differences:

1. **Frame diff magnitude** — Extract consecutive frames with OpenCV, convert to 480p grayscale, compute the mean absolute pixel difference normalised to 0–1. This is the primary signal for detecting any visual change: scrolling, navigation, cursor movement, typing.
2. **Region-of-change bounding box** — Threshold the diff image and find the bounding rect of non-zero pixels. A small bounding box indicates localised change (cursor movement, single element updating), while a large bounding box indicates page-level change (navigation, scroll). Stored as metadata per frame pair.

#### Segment classification

Apply a sliding window over the activity signal to produce a smoothed score per window. Classify each window into a tier based on configurable thresholds:


| Tier     | Description                                                    | Typical FPS |
| -------- | -------------------------------------------------------------- | ----------- |
| `idle`   | No meaningful visual change — user is reading, waiting, or AFK | 0.5         |
| `low`    | Mostly idle with minor activity                                | 1–2         |
| `medium` | Moderate interaction — some clicks, scrolling, form filling    | 3–5         |
| `high`   | Dense interaction — rapid clicking, navigation, thrashing      | 8–15        |


Adjacent windows with the same tier are merged into contiguous segments. Very short segments are absorbed into their neighbours to avoid fragmenting the video into too many tiny pieces.

The tier thresholds, FPS mappings, window size, and minimum segment duration are all configurable per-iteration.

#### Triage bypass

When triage is disabled in config, the entire video is treated as a single segment per scene at a uniform FPS. This lets you create a "uniform baseline" branch that uses the same framework and output format but without adaptive sampling — useful for comparison.

### Stage 2: Analyse

**Purpose:** Send frames to Gemini for event detection, with per-segment FPS based on Triage output.

**Input:** Scene clips + triage results.
**Output:** Per-segment raw events (intermediate), passed to Merge.

#### Frame extraction

For each segment, extract JPEG frames from the source scene clip at the segment's assigned FPS, bounded to the segment's time range. Honour the token budget constraint: if a segment would exceed the token limit at its assigned FPS, reduce FPS for that segment.

#### Context bridging

When a scene contains multiple segments, include a small number of context frames from adjacent segments so the model understands what happened immediately before and after. The prompt must label these clearly so the model doesn't report events from context frames.

#### Idle segment handling

For idle-tier segments, use a lightweight prompt variant that captures UI state (what page is visible, any error states, the URL) without trying to detect interaction events. This provides scene context at minimal token cost.

The alternative (skipping idle segments entirely and synthesising dwell/hesitation events locally) can be implemented as a later optimisation after validating that idle segments genuinely produce no interaction events.

#### Prompts

Each iteration has its own set of prompt templates:

- **System prompt** — instructs the model on its role, event types to detect, output format, and rules
- **User prompt template** — provides scene/segment context (indices, timestamps, frame count, FPS, tier). Uses placeholder variables filled at runtime
- **Idle prompt** — simplified prompt for idle segments
- **Narrative prompt** — optional summary generation prompt

#### Gemini API

- Use the `google-genai` Python SDK
- Request structured JSON output
- Use high media resolution (~1,548 tokens per 1080p frame)
- Low temperature for deterministic output
- Retry with exponential backoff
- Bounded concurrency via semaphore

#### Event schema

```
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "type",
    "source",
    "time_start",
    "time_end",
    "description",
    "confidence",
    "transcript_id"
  ],
  "properties": {
    "type": {
      "type": "string",
      "enum": [
        "click",
        "hover",
        "navigate",
        "input_text",
        "select",
        "dwell",
        "cursor_thrash",
        "scroll",
        "drag",
        "hesitate",
        "change_ui_state"
      ]
    },
    "source": {
      "type": "string",
      "enum": [
        "unmod_website_test_video",
        "ai_mod_website_test_video",
        "moderated_screen_recording",
        "unmod_figma_prototype_test",
        "unmod_tree_test",
        "unmod_card_sort"
      ]
    },
    "time_start": {
      "type": "number",
      "description": "The time the user action started in milliseconds, relative to the start of the transcript."
    },
    "time_end": {
      "type": "number",
      "description": "The time the user action ended in milliseconds, relative to the start of the transcript."
    },
    "description": {
      "type": "string",
      "description": "A description of the user action (e.g. \"User clicked on the home button\")"
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "The confidence that the user action occurred"
    },
    "interaction_target": {
      "type": "string",
      "description": "Description of the element that was interacted with (eg. a button label)"
    },
    "interaction_region_of_interest": {
      "type": "object",
      "description": "The region of interest in the video where the user action occurred (if applicable)",
      "properties": {
        "x": {
          "type": "number",
          "description": "The x-coordinate of the region of interest in the video"
        },
        "y": {
          "type": "number",
          "description": "The y-coordinate of the region of interest in the video"
        },
        "width": {
          "type": "number",
          "description": "The width of the region of interest in the video"
        },
        "height": {
          "type": "number",
          "description": "The height of the region of interest in the video"
        }
      },
      "additionalProperties": false
    },
    "cursor_position": {
      "type": "object",
      "description": "The position of the cursor in the video (if applicable)",
      "properties": {
        "x": {
          "type": "number",
          "description": "The x-coordinate of the cursor position in the video"
        },
        "y": {
          "type": "number",
          "description": "The y-coordinate of the cursor position in the video"
        }
      },
      "additionalProperties": false
    },
    "page_title": {
      "type": "string",
      "description": "The title of the page/screen/section the user action occurred on"
    },
    "page_location": {
      "type": "string",
      "description": "The URL/path/title of the page/screen/section the user action occurred on"
    },
    "frame_description": {
      "type": "string",
      "description": "Description of the visual information associated with the action (eg. what's on the page)"
    },
    "transcript_id": {
      "type": "string",
      "description": "The ID of the transcript where the user action occurred"
    },
    "study_id": {
      "type": "string",
      "description": "The ID of the study where the user action occurred"
    },
    "task_id": {
      "type": "string",
      "description": "The ID of the task where the user action occurred"
    }
  },
  "additionalProperties": false
}
```


### Stage 3: Merge

**Purpose:** Convert frame-indexed events to absolute timestamps, deduplicate across segments and scene overlaps, produce the final event timeline.

#### Timestamp resolution

Convert each event's frame index to an absolute timestamp in the source video, accounting for segment start time, analysis FPS, and any prepended context frames. Events originating from context frames are discarded.

#### Deduplication

Two sources of duplicate events:

1. **Scene overlap** — adjacent scenes from the Prepare stage share ~1.5 seconds. Events close in time with the same type and similar labels are merged, keeping the higher-confidence observation.
2. **Segment context overlap** — context frames from adjacent segments within a scene. Same dedup logic applies.

#### Output

One output file json file per session. Each output to contain:

- Session metadata
- Per-stage metrics: duration, artifacts created
- Final event output (matching prescribed schema)

---

## Shared input data

Source videos and prepared scenes are NOT copied per-iteration. All experiments read from the same shared input directory. This directory can be a symlink to the existing pipeline's clipped scenes output.

---

## Dependencies

- **google-genai** — Gemini API SDK
- **opencv-python-headless** — frame extraction, frame diffs, bounding box, template matching
- **numpy** — pixel-level arithmetic for activity signal computation
- **scikit-image** — SSIM computation (if needed for comparison with Prepare stage)
- **click** — CLI framework
- **pydantic** — runtime validation for config, manifest, API responses
- **python-dotenv** — environment variable loading

Python 3.10+. ffmpeg and ffprobe on PATH for video metadata.

---

## Future enhancements (not in initial scope)

- **Cursor tracking** in Triage via OpenCV template matching (`cv2.matchTemplate`) for better activity classification and ROI cropping
- **ROI cropping** — crop frames around cursor position to reduce tokens/frame
- **Optical flow** — `cv2.calcOpticalFlowPyrLK` for cursor trajectory tracking, enabling local event synthesis
- **Local event synthesis** — detect hover/dwell/thrash from cursor trajectory without API
- **Skip idle (Option B)** — synthesise events locally instead of sending idle frames
- **Resumability** — progress tracking + restart for interrupted runs
- **Web dashboard** — visualise triage activity signals, compare iteration results

