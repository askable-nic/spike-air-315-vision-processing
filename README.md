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

Three stages run per session:

1. **Triage** — Samples frames from the screen track, computes frame-to-frame diffs, classifies segments by activity level (idle/low/medium/high), and assigns per-segment FPS. No API calls.
2. **Analyse** — Extracts frames at the assigned FPS, sends them to Gemini with interleaved labels and images, parses structured event responses. Context frames from adjacent segments provide continuity.
3. **Merge** — Resolves frame-indexed events to absolute millisecond timestamps (offset by `screenTrackStartOffset`), discards context-only events, deduplicates overlapping events, and writes final output.

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

An iteration can override stages by placing a `pipeline.py` in its directory with `run_triage`, `run_analyse`, or `run_merge` functions. Missing functions fall through to the defaults.

## Output

Per-session output in `experiments/{branch}/{iteration}/output/{session_id}/`:

- `events.json` — final events matching `event-schema.json`
- `session.json` — full session output with per-stage metrics and token usage

Run-level metadata in `experiments/{branch}/{iteration}/output/metadata.json`.

## Input Data

12 sessions in `input_data/` with screen track videos, full session videos, and transcripts. Described in `input_data/manifest.json`. Input data is read-only and shared across all experiments.

## Project Layout

```
src/
  models.py       Pydantic data models (all frozen)
  config.py       Config loading, deep merge, defaults
  manifest.py     Manifest parser
  video.py        OpenCV frame extraction, diffs, JPEG encoding
  gemini.py       Gemini API client wrapper
  prompts.py      Prompt resolution + template filling
  similarity.py   String similarity for dedup
  runner.py       Pipeline orchestration
  cli.py          Click CLI

stages/
  triage.py       Activity signal → segment classification
  analyse.py      Gemini API calls per segment
  merge.py        Timestamp resolution + dedup
```
