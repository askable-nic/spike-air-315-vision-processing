# LLM-as-Judge Validation Spec

## Context

The VEX pipeline uses Gemini to extract user interaction events from screen recordings. Currently there's no way to assess output quality — whether events are real, correctly typed, accurately timed, or if scene changes are being missed. This spec adds a `vex validate` command that uses an LLM judge to verify pipeline output against the source video.

## Approach

A separate CLI command (not a pipeline stage) that loads existing output and the source video, extracts frames at event timestamps, and asks a judge LLM to verify each event. Uses Claude as the default judge for cross-model validation (pipeline uses Gemini). Also runs ffmpeg scene detection as an independent scene count baseline.

## Files to create/modify

| File | Action |
|---|---|
| `src/models.py` | Add `ValidateConfig`, `EventVerdict`, `SceneCountResult`, `ValidationReport` |
| `src/config.py` | Add `validate` defaults + `resolve_validate_config()` |
| `src/claude.py` | New — Anthropic API wrapper (mirrors `src/gemini.py` interface) |
| `stages/validate.py` | New — core validation logic |
| `prompts/validate_system.txt` | New — judge system prompt |
| `prompts/validate_events.txt` | New — judge user prompt template |
| `src/cli.py` | Add `validate` command |
| `pyproject.toml` | Add `anthropic` dependency |

## Models (`src/models.py`)

```python
VerdictRating = Literal["correct", "partially_correct", "incorrect", "unverifiable"]

class ValidateConfig(BaseModel, frozen=True):
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.0
    max_concurrent: int = 3
    jpeg_quality: int = 85
    resolution_height: int = 720
    frames_per_event: int = 3             # before, start, end
    frame_offset_ms: int = 500            # offset for before/after
    token_budget: int = 500_000
    tokens_per_frame: int = 1600
    max_events_to_validate: int = 0       # 0 = all
    sample_strategy: Literal["all", "low_confidence", "stratified"] = "all"
    scene_detect_threshold: float = 0.3
    events_per_batch: int = 5

class EventVerdict(BaseModel, frozen=True):
    event_index: int
    event_type: EventType
    event_time_start: float
    event_time_end: float
    event_description: str
    type_verdict: VerdictRating
    type_reasoning: str
    description_verdict: VerdictRating
    description_reasoning: str
    timing_verdict: VerdictRating
    timing_reasoning: str
    target_verdict: VerdictRating
    target_reasoning: str
    overall_verdict: VerdictRating
    overall_reasoning: str
    suggested_type: EventType | None = None
    suggested_description: str | None = None

class SceneCountResult(BaseModel, frozen=True):
    ffmpeg_scene_count: int
    ffmpeg_scene_timestamps_ms: tuple[float, ...]
    pipeline_scene_count: int
    pipeline_scene_timestamps_ms: tuple[float, ...]
    matched_count: int
    unmatched_ffmpeg: tuple[float, ...]
    unmatched_pipeline: tuple[float, ...]

class ValidationReport(BaseModel, frozen=True):
    recording_id: str
    validated_at: str
    judge_model: str
    event_verdicts: tuple[EventVerdict, ...]
    events_validated: int
    events_total: int
    type_accuracy: float
    description_accuracy: float
    timing_accuracy: float
    target_accuracy: float
    overall_accuracy: float
    scene_count: SceneCountResult | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    processing_time_ms: float = 0
```

`ValidateConfig` is **not** added to `PipelineConfig` — it's resolved independently via `resolve_validate_config()` using the same 4-layer merge (defaults → branch YAML → iteration YAML → CLI overrides) but reading only the `validate:` key.

## CLI command (`src/cli.py`)

```
vex validate -b BRANCH -i ITERATION [-s SESSION...] [-o validate.model=...] [--skip-scene-count]
```

Same option pattern as `vex run`. Loads events.json + session.json from existing output, resolves video path from manifest.

## Judge prompt design

### System prompt (`prompts/validate_system.txt`)

Roles the judge as a video analysis QA reviewer. Defines the four assessment dimensions (type, description, timing, target) and the rating scale (correct / partially_correct / incorrect / unverifiable). Instructs the judge to provide brief reasoning and suggest corrections where applicable.

### User prompt per batch (`prompts/validate_events.txt`)

For each event in the batch:
```
### Event {index}: {type} at {time_start}ms–{time_end}ms
Description: {description}
Interaction target: {interaction_target}
Page: {page_title}

[Frame E{index}_BEFORE | {before_ts}ms]
<image>
[Frame E{index}_START | {start_ts}ms]
<image>
[Frame E{index}_END | {end_ts}ms]
<image>
```

The question is flipped from detection: instead of "what events do you see?" it's "the pipeline claims X happened here — do the frames support that?" This is a much easier and more reliable task for the judge.

## Frame extraction strategy

For each event, extract 3 frames:
1. **BEFORE** — `time_start - frame_offset_ms` (state before the event)
2. **START** — `time_start` (event beginning)
3. **END** — `time_end` (or `time_start + frame_offset_ms` if start == end)

Timestamps in `ResolvedEvent` include `screenTrackStartOffset` — subtract it to get video-relative timestamps for extraction.

All timestamps for a batch are collected and extracted in a single `extract_frames_at_timestamps()` call to avoid multiple video walks. Frames scaled to `resolution_height` (default 720) to manage token cost.

## Scene count validation

Independent of the LLM judge — uses ffmpeg scene detection:
```
ffmpeg -i video.mp4 -vf "select='gt(scene,{threshold})',showinfo" -vsync vfr -f null -
```

Parse `showinfo` output for scene change timestamps. Compare against pipeline's `navigate` events using a time tolerance (2000ms). Report: matched count, unmatched from each side, delta.

## Token budget management

Before making calls, estimate total cost:
```
frames_needed = events_to_validate * frames_per_event
estimated_tokens = frames_needed * tokens_per_frame
```

If over budget, reduce event set based on `sample_strategy`:
- **all** — validate every event; auto-switch to stratified if over budget
- **low_confidence** — prioritise events with lowest confidence scores
- **stratified** — proportional sample by event type, fill remaining by lowest confidence

Batches of `events_per_batch` (default 5) events per LLM request. ~24.5k input tokens per batch (5 events x 3 frames x 1600 tokens). Batches run concurrently up to `max_concurrent` using `asyncio.Semaphore`.

## Anthropic client (`src/claude.py`)

Mirrors `src/gemini.py` interface:
- `create_client()` — reads `ANTHROPIC_API_KEY`
- `async make_request(client, model, system_prompt, content_parts, temperature, max_retries)` — async call with retry, returns `{"text": ..., "input_tokens": ..., "output_tokens": ...}`
- Images sent as base64 content blocks per Anthropic vision API

Model dispatch in validate stage: `claude-*` → Anthropic client, `gemini-*` → Gemini client.

## Output

Written to `experiments/{branch}/{iteration}/output/{session_id}/validation/`:
```
report.json       — full ValidationReport
verdicts.json     — EventVerdict array only
scene_count.json  — SceneCountResult (if run)
frames/           — extracted judge frames as JPEGs (debug)
```

Console summary:
```
Validation: travel_expert_veronika
  Events: 33/33 validated
  Type accuracy:        90.9%
  Description accuracy: 84.8%
  Timing accuracy:      78.8%
  Target accuracy:      87.9%
  Overall accuracy:     81.8%
  Scene count: pipeline=5, ffmpeg=7, matched=4
  Tokens: 45,000 in / 8,200 out
```

## Implementation order

1. Models in `src/models.py`
2. Config defaults + `resolve_validate_config()` in `src/config.py`
3. `src/claude.py` — Anthropic API wrapper
4. `stages/validate.py` — core logic: frame extraction, batching, judge calls, scene count, scoring
5. Prompts — `prompts/validate_system.txt`, `prompts/validate_events.txt`
6. CLI command in `src/cli.py`
7. Test against existing `visual-change-driven/2` output
