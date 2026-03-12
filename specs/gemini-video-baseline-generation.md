# Gemini Video-Input Baseline Generation — Technical Spec

## Problem

Manual baseline annotation is too time-intensive. A single 5-minute session (`travel_expert_veronika`) required watching the full recording in real time, pausing to tag each event, picking cursor coordinates, and writing descriptions — producing ~100 events over several hours of annotation work. This doesn't scale to the 12 sessions in the manifest, let alone new studies.

## Approach

Use Gemini's native video input capability to generate comprehensive draft baselines. Instead of extracting frames and sending images (the existing pipeline approach), upload the normalised screen track video directly and ask Gemini to produce a complete event annotation in a single pass (or small number of segment passes).

This is explicitly **not token-optimised**. The goal is maximum recall and description quality — a thorough analysis that can be quickly reviewed and corrected in the annotation tool, rather than built from scratch.

### Why native video input

Gemini's video understanding processes temporal sequences natively — it can track cursor motion, detect transitions, read on-screen text, and observe timing relationships that are lost when sampling individual frames. For baseline generation where we want comprehensive coverage, this is ideal: we trade tokens for completeness.

### Why not the existing pipeline

The existing pipeline (triage → observe → analyse → merge) is designed for production efficiency — it spends local compute to minimise API tokens. For baseline generation, the priorities are inverted: we want maximum coverage and rich descriptions even at higher token cost, because a human will review the output once rather than running it repeatedly.

## Design

### New CLI command

```bash
vex generate-baselines
vex generate-baselines -s travel_expert_veronika    # single session
vex generate-baselines --dry-run                    # preview segments, estimate tokens
vex generate-baselines --force                      # overwrite existing baselines
```

This is a standalone command (like `enrich-baselines`), not a pipeline branch. It writes directly to `baselines/{sessionId}/events.json`.

### Pipeline

```
video segmentation (local) → Gemini video analysis (per segment) → merge & deduplicate → write baseline
```

#### Step 1: Video segmentation

Split the normalised screen track into close-to-equal-length segments with a maximum of 90 seconds each, plus 5-second overlaps. Compute the number of segments as `ceil(duration / max_segment_duration)`, then divide the video evenly.

For example, a 4:52 video → `ceil(292s / 90s) = 4` segments → each ~73s (1:13), with 5s overlaps.

```python
class VideoSegment(BaseModel, frozen=True):
    index: int
    start_ms: float
    end_ms: float
    overlap_start_ms: float   # start of overlap with previous segment
    overlap_end_ms: float     # end of overlap with next segment
    path: Path                # path to extracted segment file
```

Implementation:
- `n_segments = ceil(duration_ms / max_segment_duration_ms)`
- `base_duration = duration_ms / n_segments`
- Each segment spans `[i * base_duration - overlap, (i+1) * base_duration + overlap]` (clamped to video bounds)
- Use ffmpeg to extract segments as MP4 files to the output directory (see Artifact storage below)
- No re-encoding needed — `ffmpeg -ss {start} -to {end} -c copy` for speed
- Overlap ensures events at segment boundaries are captured by at least one segment

#### Step 2: Gemini video analysis

Upload each segment and request comprehensive event extraction.

**Model**: `gemini-3-flash-preview` — same model as the existing pipeline stages for consistency.

**Input per request**:
- The video segment file (native video upload via `genai.types.Part.from_uri` or inline bytes)
- System prompt with event type definitions, output schema, and session context
- Segment metadata: absolute time offset, session identifier, study context

**Video FPS**: `video_fps: 15` — Gemini 3 supports configurable FPS for video input. Default to 15 FPS for thorough coverage of fast interactions. At 15 FPS a 90-second segment ≈ 1,350 frames × 263 tokens ≈ 355k tokens — comfortably within the 1M context window.

**Resolution**: Use the normalised screen track as-is (typically 1920×1080). No downscaling — we want the model to read all on-screen text, button labels, URLs, etc.

**Temperature**: 0.2 — slightly above zero for natural descriptions, low enough for consistency.

**Output**: Structured JSON array of events using Gemini's response_schema, matching the existing `RawEvent` shape but with absolute timestamps (not frame indices, since we're using video input).

```python
class VideoAnalysisEvent(BaseModel, frozen=True):
    """Event detected from video segment analysis."""
    type: str                           # EventType value
    time_start_ms: float                # absolute ms from video start
    time_end_ms: float                  # absolute ms from video start
    description: str                    # detailed description of user action
    confidence: float                   # 0-1
    interaction_target: str | None      # UI element label
    cursor_position_x: int | None       # pixel x
    cursor_position_y: int | None       # pixel y
    page_title: str | None
    page_location: str | None
    frame_description: str | None       # visual context at this moment
```

**Concurrency**: `max_concurrent: 3` — limited by Gemini rate limits for video input, configurable.

#### Step 3: Merge & deduplicate

Combine events from all segments, handling overlaps:

1. Adjust timestamps: add segment's `start_ms` offset to convert segment-relative → absolute video timestamps, then add `screenTrackStartOffset` to convert → transcript timestamps
2. Deduplicate overlap events: within overlap windows, match events by type + temporal proximity (same logic as `stages/merge.py`'s `similarity_threshold` and `time_tolerance_ms`). Keep the version with higher confidence.
3. Sort by `time_start`
4. Inject session metadata: `transcript_id`, `study_id`, `source: "gemini_video_baseline"`

#### Step 4: Write baseline

Write the merged event list to `baselines/{sessionId}/events.json`. If a baseline already exists, refuse unless `--force` is passed — prompt the user to use the annotation tool to review differences instead.

### Configuration

```yaml
generate_baselines:
  model: "gemini-3-flash-preview"
  temperature: 0.2
  max_concurrent: 3
  video_fps: 15                       # FPS for Gemini video input sampling
  max_segment_duration_ms: 90000      # 90s max, segments split evenly
  segment_overlap_ms: 5000            # 5s overlap
  source: "gemini_video_baseline"
  merge:
    time_tolerance_ms: 2000
    similarity_threshold: 0.6
```

Added to `DEFAULTS` in `src/config.py`, overridable via `-o` flags.

### Prompt design

A single prompt template at `prompts/generate_baseline.txt`. The prompt must:

1. **Define all 11 event types** with examples and boundary cases (reuse from `prompts/system.txt`)
2. **Request exhaustive coverage** — "report every user interaction, UI state change, and navigation event, even minor ones like scrolls and brief hovers"
3. **Request rich descriptions** — "describe what the user did, what they were looking at, and what changed on screen"
4. **Request frame descriptions** — "for each event, describe the visual state of the screen at that moment"
5. **Specify timestamp format** — milliseconds from video start, with instruction to use the video timeline
6. **Provide session context** — study name, task description (if available from transcript), participant info
7. **Handle cursor position** — "report cursor pixel coordinates when visible and relevant to the interaction"
8. **Set confidence calibration** — "use 0.9+ for clearly visible interactions, 0.7-0.9 for likely interactions, 0.5-0.7 for inferred or partially visible events"

The prompt should also include guidance on temporal granularity:
- Clicks: mark the exact moment
- Navigations: start when initiated, end when new page is fully loaded
- Dwells: full duration of the pause
- Input text: start of first keystroke to end of last
- Scrolls: full scroll duration, not individual scroll increments

### Artifact storage

Every intermediate artifact is saved for debugging and iteration. All artifacts for a session live under `baselines/{sessionId}/artifacts/`.

```
baselines/
  {sessionId}/
    events.json                              # final baseline output
    artifacts/
      segment_000/
        video.mp4                            # video segment file
        prompt.txt                           # full rendered prompt sent to Gemini
        response.json                        # raw Gemini response (text + token counts)
        events.json                          # parsed VideoAnalysisEvent list
      segment_001/
        video.mp4
        prompt.txt
        response.json
        events.json
      ...
      merged_events.json                     # all segment events combined, before dedup
      deduplicated_events.json               # after overlap dedup, before metadata injection
      run_metadata.json                      # config used, timestamps, token totals, segment info
```

**`run_metadata.json`** captures:
- Config snapshot (model, FPS, segment settings)
- Per-segment: start/end times, input/output tokens, event count
- Total tokens and processing time
- Timestamp of the run

This makes it possible to inspect exactly what Gemini saw and returned for any segment, and to trace how raw responses became the final baseline.

## Files to create/modify

| File | Action |
|---|---|
| `stages/generate_baselines.py` | New — core logic: segmentation, API calls, merge |
| `prompts/generate_baseline.txt` | New — video analysis prompt |
| `src/cli.py` | Add `generate-baselines` command |
| `src/config.py` | Add `generate_baselines` defaults |
| `src/models.py` | Add `GenerateBaselinesConfig`, `VideoSegment`, `VideoAnalysisEvent` |

## CLI interface

```python
@cli.command()
@click.option("-s", "--session", help="Process single session by identifier")
@click.option("--dry-run", is_flag=True, help="Show segments and estimated tokens without calling API")
@click.option("--force", is_flag=True, help="Overwrite existing baselines")
@click.option("-o", "--override", multiple=True, help="Config overrides (e.g. generate_baselines.model=gemini-3-flash-preview)")
def generate_baselines(session, dry_run, force, override):
    """Generate draft baselines from video using Gemini video input."""
```

**Dry run output**:
```
Session: travel_expert_veronika
  Duration: 4:52
  Segments: 4 (~1:13 each, 5s overlaps)
  Estimated tokens: ~180,000

Session: travel_expert_lisa
  Duration: 6:14
  ...

Total estimated tokens: ~1,200,000
Estimated cost: ~$X.XX (gemini-3-flash-preview)
```

## Output format

The output is the same `events.json` format used by the annotation tool and evaluation system — a flat JSON array of event objects. The only difference from manual baselines is `source: "gemini_video_baseline"` instead of `"manual_annotation"`.

This means generated baselines can immediately be:
- Loaded in the annotation tool for review/correction
- Used with `vex evaluate` to score pipeline iterations
- Enriched with `vex enrich-baselines` if needed

## Review workflow

The intended workflow is:

1. `vex generate-baselines` — produce draft baselines for all sessions
2. Open each session in the annotation tool — review events, correct timestamps, fix misclassifications, add missed events
3. Save corrected baselines — now you have high-quality ground truth created in a fraction of the manual annotation time

The annotation tool already supports loading, editing, and saving `events.json` files, so no viewer changes are needed.

## Evaluation bootstrapping

Once baselines exist for all 12 sessions, `vex evaluate` can score any pipeline branch/iteration against them. Currently only `travel_expert_veronika` has a baseline. This command unblocks evaluation across the full dataset.
