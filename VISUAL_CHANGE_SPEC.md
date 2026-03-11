# Visual-Change-Driven Analysis — Technical Spec

## Motivation

The current observe-driven pipeline infers user interaction events from cursor motion patterns (brief stops → click candidates, stationary periods → hovers, etc.) and sends frames around those inferred events to the LLM for confirmation. This produces a high volume of false positives — the travel_expert_veronika session generated 989 "click" candidates from what were mostly cursor decelerations and pauses. The LLM receives hundreds of frames with low signal, wastes tokens, and hallucinates event descriptions for non-events.

The core problem: **cursor motion alone cannot distinguish a click from a hover from a pause**. The missing signal is what happened on screen as a result.

### Design principles

1. **Visual change is the primary signal.** If the screen didn't change, there's probably nothing worth sending to the LLM. If it did change, that's a moment worth analysing regardless of cursor behaviour.
2. **Cursor position is metadata, not the driver.** Cursor tracking provides context ("the user was pointing here when this happened") but doesn't determine which frames to send.
3. **Do as much cheap local computation as possible.** Every frame diff, connected component analysis, and cursor lookup is essentially free compared to an LLM call. Spend local CPU to send fewer, higher-signal frames to the LLM.
4. **The LLM classifies, not confirms.** Instead of "here are 989 click candidates, confirm or reject each", the prompt becomes "here are 25 moments where something visually changed — describe what the user did."

---

## Architecture overview

```
┌─────────────────────────────────────────────────────┐
│                   Local compute                     │
│                                                     │
│  1. Cursor timeline  (existing, unchanged)          │
│  2. Visual change timeline  (new)                   │
│  3. Optical flow timeline  (existing, reworked)     │
│                                                     │
│  4. Moment detection  (new, replaces event synth)   │
│                                                     │
├─────────────────────────────────────────────────────┤
│                   LLM analysis                      │
│                                                     │
│  Pass 1: Scene + context descriptions               │
│  Pass 2: Interaction analysis                       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 1. Cursor timeline

**No changes.** The existing two-pass adaptive cursor tracking (`track_cursor()`) produces a `tuple[CursorDetection, ...]` with per-frame (timestamp, x, y, confidence, template_id, detected). This is consumed as read-only metadata by moment detection and frame annotation.

When cursor tracking is not applicable (recordings without a visible cursor), this step is skipped and downstream stages operate without cursor metadata. The `ObserveConfig.cursor_tracking_enabled` flag (new, default `True`) controls this.

---

## 2. Visual change timeline (new)

### Purpose

Detect when and where the screen content changed between consecutive frames. Produces a timeline of `VisualChange` events, each describing a spatially localised change with its bounding box, area, and magnitude.

### Algorithm

1. Extract frames at `change_detect_fps` (default 4.0 FPS) across the full video. Higher than the current flow FPS (2.0) for better temporal resolution on fast transitions.

2. For each consecutive frame pair (A, B):
   a. Convert to grayscale.
   b. Compute `cv2.absdiff(A, B)`.
   c. Apply Gaussian blur (small kernel, e.g. 5x5) to suppress compression noise.
   d. Threshold at `change_pixel_threshold` (default 20, range 0–255) to produce a binary mask.
   e. Apply morphological close (small kernel) to merge nearby changed pixels.
   f. Run `cv2.connectedComponentsWithStats` on the binary mask.
   g. For each connected component with area >= `change_min_area_px` (default 1000):
      - Record bounding box (x, y, w, h)
      - Record area (pixel count)
      - Record mean magnitude (mean of `absdiff` values within the component)
   h. Compute the total changed area (sum of all qualifying component areas).

3. Emit a `VisualChangeFrame` for each frame pair that has at least one qualifying region:

```python
class ChangeRegion(BaseModel, frozen=True):
    x: int
    y: int
    width: int
    height: int
    area_px: int                # pixel count of the connected component
    mean_magnitude: float       # mean absdiff value within region (0–255)

class VisualChangeFrame(BaseModel, frozen=True):
    timestamp_a_ms: float       # timestamp of frame A
    timestamp_b_ms: float       # timestamp of frame B
    regions: tuple[ChangeRegion, ...]
    total_changed_area_px: int  # sum of all region areas
    frame_area_fraction: float  # total_changed_area / (frame_width * frame_height)
```

4. Cluster contiguous `VisualChangeFrame`s into `VisualChangeEvent`s. Two consecutive change frames are "contiguous" if:
   - They are adjacent in time (no gap between them at the extraction FPS), AND
   - Their change regions overlap spatially (IoU > 0 between any pair of bounding boxes across the two frames), OR
   - Their total changed area fraction both exceed `scene_change_area_threshold` (see below)

```python
class VisualChangeEvent(BaseModel, frozen=True):
    time_start_ms: float
    time_end_ms: float
    frames: tuple[VisualChangeFrame, ...]
    peak_changed_area_fraction: float   # max frame_area_fraction across frames
    bounding_box: tuple[int, int, int, int]  # union bbox of all regions across all frames
    category: str  # "scene_change", "local_change", or "continuous_change"
```

### Classification

A `VisualChangeEvent` is classified based on two signals — area and duration:

- **scene_change**: `peak_changed_area_fraction >= scene_change_area_threshold` (default 0.3, meaning 30% of the frame changed) AND duration is short (below `continuous_change_max_duration_ms`). These are page navigations, tab switches, modal overlays, large UI transitions.
- **local_change**: Below the area threshold AND short duration. These are button state changes, dropdown opens, form field updates, small UI animations.
- **continuous_change**: Duration exceeds `continuous_change_max_duration_ms` (default 3000ms) AND the change region stays roughly the same area throughout (area standard deviation across frames is low relative to mean). These are embedded videos, auto-rotating carousels, chat feeds receiving messages, stock tickers, or other live-updating content. A continuous change gets a single frame description (like a scroll) rather than before/after interaction analysis.

The distinction between continuous change and a slow page load: a page load typically has a *growing* change area (elements rendering in progressively) while continuous content has a *stable* change area. If the area variance across frames in the event is high relative to the mean, it's more likely a load/transition; if stable, it's continuous content.

### Config additions to ObserveConfig

```python
# Visual change detection
change_detect_fps: float = 4.0
change_pixel_threshold: int = 20              # absdiff threshold (0–255)
change_min_area_px: int = 1000                # minimum connected component area
change_blur_kernel: int = 5                   # Gaussian blur kernel size
change_morph_kernel: int = 5                  # morphological close kernel size
scene_change_area_threshold: float = 0.3      # fraction of frame for scene vs local
continuous_change_max_duration_ms: int = 3000  # beyond this, classify as continuous
```

### Noise handling

Video compression (H.264/H.265) introduces block-level artifacts that shift between frames, especially in areas with gradients or fine detail. The combination of Gaussian blur + pixel threshold + minimum area filters these out:
- Gaussian blur smooths block boundaries
- Pixel threshold (20) is above typical compression noise (~5-10)
- Minimum area (1000px) rejects scattered noise pixels that pass the threshold

If a recording has unusually high compression noise, `change_pixel_threshold` and `change_min_area_px` can be tuned upward per-experiment.

---

## 3. Optical flow timeline (reworked)

### Current state

Flow is computed between 2 FPS frames and aggregated into 1-second sliding windows (`FlowWindow`) with mean magnitude, dominant direction, and uniformity. Only used for scroll detection.

### Changes

Keep the computation as-is but rework the output from sliding-window summaries to **discrete flow events**:

```python
class FlowEvent(BaseModel, frozen=True):
    time_start_ms: float
    time_end_ms: float
    dominant_direction: str         # N, S, E, W, NE, etc.
    mean_magnitude: float
    flow_uniformity: float
    category: str                   # "scroll", "pan", "mixed"
```

**Detection:** Scan consecutive flow windows. When `flow_uniformity >= scroll_min_flow_uniformity` and `mean_magnitude >= scroll_min_magnitude` persist across 2+ consecutive windows, emit a `FlowEvent`. Merge contiguous events with the same direction.

**Categories:**
- `scroll`: High uniformity (>0.6), vertical direction (N/S)
- `pan`: High uniformity (>0.6), horizontal direction (E/W)
- `mixed`: Below uniformity threshold but above magnitude threshold — general motion

---

## 4. Moment detection (new, replaces synthesize_local_events + select_frames_for_analysis)

### Purpose

Combine the three timelines (cursor, visual change, flow) into a set of **moments** — discrete time intervals where something potentially significant happened. Each moment carries enough metadata for the frame selection and LLM request stages to do their job.

### Algorithm

#### Step 1: Visual change events become moment candidates

Every `VisualChangeEvent` becomes a moment candidate. This is the primary source of moments — if the screen changed, something happened.

#### Step 2: Subtract scrolls

If a visual change event overlaps in time with a `FlowEvent` (high uniformity, consistent direction), the visual change is *explained by* the scroll. The whole page moved — that's not a discrete interaction, it's scrolling. Emit a `scroll` moment directly and remove the visual change from the interaction candidate list.

Scroll moments are self-describing — no LLM analysis needed for the event itself. However, they are eligible for a frame description in Pass 1 (see below).

#### Step 3: Classify remaining candidates

Based on the `VisualChangeEvent.category`:
- `scene_change` → `scene_change` moment (priority 0). Goes to Pass 1.
- `local_change` → `interaction` moment (priority 1). Goes to Pass 2.
- `continuous_change` → `continuous` moment (priority 2). Gets a single frame description in Pass 1, not interaction analysis.

#### Step 4: Attach cursor context

For each remaining candidate, look up the cursor position from the cursor timeline:
- Where was the cursor ~500ms before the change?
- Where was it during/after?
- Was it near the change region (within the change bounding box + padding)?

This doesn't filter candidates — it enriches them. The cursor position goes into the frame annotation so the LLM knows "the user was pointing here when this happened." A change with no cursor nearby is still a valid moment (could be an autonomous UI change like a notification or loading state).

#### Step 5: Add cursor-stop moments

Scan the cursor trajectory for **significant stops** — positions where the cursor was stationary for >= `cursor_stop_min_ms` (default 300ms) within `cursor_stop_radius_px`. These are potentially hovers or clicks that didn't produce a detected visual change (the UI element might have a subtle hover state, or the click target might not have changed visually yet, or the change was below the detection threshold).

For each significant stop:
- If it already overlaps with a visual-change moment (i.e. the cursor was near a detected change), skip it — the visual change moment already captures this.
- Otherwise, emit a `cursor_stop` moment (priority 3). These go to Pass 2 with a single ROI-cropped frame around the cursor position. The LLM's job is to identify what UI element is under the cursor, not to confirm a click.

#### Step 6: Add cursor-only behavioural moments

- **Long dwells** (stationary > `dwell_min_ms`): The user stared at something. Worth noting even without a visual change. Priority 4.
- **Thrash** (rapid direction changes): Indicates confusion. Detected the same way as today. Priority 4.

These are lower priority than all other moment types.

#### Step 7: Merge adjacent candidates

Adjacent moments within `moment_merge_gap_ms` (default 500ms) are merged into a single moment. This collapses multi-step transitions (e.g. click → dropdown opens → user selects item) into a coherent sequence rather than separate moments.

#### Step 8: Budget-based selection

Not all candidates make it to the LLM. Moments are selected based on a **per-session token budget**, filled from highest priority down.

**Budget calculation:**

```
session_budget = screen_track_duration_minutes × token_budget_per_minute
```

The budget is based on the **screen track duration**, not the full session video (which may include webcam, audio-only segments, or other non-screen content). `token_budget_per_minute` is configurable (default 50,000 input tokens/min). A 5-minute screen track gets ~250,000 tokens total across both passes.

**Token cost estimates per moment type:**

| Moment type | Frames sent | Est. tokens per moment |
|---|---|---|
| `scene_change` (Pass 1) | 1 full frame | ~1,600 |
| `scroll` (Pass 1) | 1 full frame | ~1,600 |
| `continuous` (Pass 1) | 1 full frame | ~1,600 |
| `interaction` (Pass 2) | 2–3 ROI crops | ~600–900 |
| `cursor_stop` (Pass 2) | 1 ROI crop | ~300 |
| `cursor_only` (Pass 2) | 1 ROI crop | ~300 |
| `baseline` | 1 full frame | ~1,600 |

**Selection process:**

1. All `scene_change` moments are always included (Pass 1 — needed for context). Reserve their token cost from the budget.
2. Fill remaining budget with `interaction` moments in chronological order (Pass 2).
3. If budget remains, add `scroll` and `continuous` moments for frame descriptions (Pass 1).
4. If budget remains, add `cursor_stop` moments (Pass 2).
5. If budget remains, add `cursor_only` moments (Pass 2).
6. After all candidates, if any temporal gap exceeds `baseline_max_gap_ms`, insert baseline moments in those gaps.
7. If the budget is exhausted before all candidates are included, drop lowest-priority moments. Log what was dropped.

**Minimum guarantee:** Scene changes are always included regardless of budget (they're cheap and essential for context). If even scene changes exceed the budget, warn but proceed — this would indicate an unusually fragmented recording.

#### Step 9: Add baseline moments for gaps

After budget selection, if there's a temporal gap > `baseline_max_gap_ms` (default 10,000ms) with no moments, insert a baseline moment at the midpoint. This ensures the LLM has temporal coverage. Baseline moments get a single full frame and go to Pass 1 for a scene/context description.

### Output

```python
class Moment(BaseModel, frozen=True):
    time_start_ms: float
    time_end_ms: float
    visual_change: VisualChangeEvent | None
    flow_event: FlowEvent | None
    cursor_before: CursorPosition | None    # cursor position just before the moment
    cursor_after: CursorPosition | None     # cursor position just after
    cursor_associated: bool                 # cursor was near the change region
    category: str                           # "scene_change", "interaction", "scroll",
                                            # "continuous", "cursor_stop", "cursor_only", "baseline"
    priority: int                           # 0 = scene_change, 1 = interaction, 2 = scroll/continuous,
                                            # 3 = cursor_stop, 4 = cursor_only, 5 = baseline
    estimated_tokens: int                   # token cost estimate for budget tracking
```

---

## 5. LLM Pass 1: Scene and context descriptions

### Purpose

Establish the "where are we" context at each point in the recording. For scene changes, describe the new page. For scrolls and continuous changes, describe what the user is looking at. This creates a timeline of **scene descriptions** that Pass 2 references as text context.

### Which moments go to Pass 1

- All `scene_change` moments (always included)
- `scroll` moments that were selected by the budget
- `continuous` moments that were selected by the budget
- `baseline` moments

These all share the same need: one full frame, described in text.

### Frame selection

For each Pass 1 moment:
- **scene_change**: One frame after the change settles (`time_end_ms + settle_buffer_ms`). Full frame.
- **scroll**: One frame at the midpoint of the scroll event. Full frame.
- **continuous**: One frame at the start of the continuous change. Full frame.
- **baseline**: One frame at the moment timestamp. Full frame.

### Request format

Batch all Pass 1 moments into a single request (or a few requests if frame count is large). Each frame is labelled with its timestamp and moment type.

**Prompt:**

```
Describe the page or screen shown in each frame. These frames are taken from a
screen recording at key moments (page navigations, scroll positions, and periodic
baselines).

For each frame, provide:
- page_title: The title or heading of the page
- page_location: The URL or path visible in the browser (if any)
- page_description: A brief description of the page layout, content, and
  key UI elements visible
- visible_interactive_elements: List of buttons, links, form fields, or other
  interactive elements visible on the page

Return a JSON array with one entry per frame.
```

**Response schema:**

```python
class SceneDescription(BaseModel, frozen=True):
    frame_index: int
    timestamp_ms: float
    page_title: str
    page_location: str
    page_description: str
    visible_interactive_elements: tuple[str, ...] = ()
```

### Output

A `tuple[SceneDescription, ...]` timeline. Each scene description is valid from its timestamp until the next scene description. Pass 2 looks up the most recent scene description for each interaction moment and injects it as text.

### Token cost

Typically 10–25 frames for a 5-minute screen track (5-15 scene changes + a few scroll/baseline frames). At ~1,600 tokens per full frame + minimal prompt overhead: ~18,000–42,000 tokens. This is the largest single cost but provides reusable context for all Pass 2 moments.

---

## 6. LLM Pass 2: Interaction analysis

### Purpose

For each `interaction`, `cursor_stop`, and `cursor_only` moment, determine what the user did. The LLM receives a small number of targeted frames with rich text context from Pass 1.

### Which moments go to Pass 2

- `interaction` moments (visual change + short duration)
- `cursor_stop` moments (cursor stationary, no detected visual change)
- `cursor_only` moments (dwell, thrash — if budget allows)

### Frame selection per moment

For each `interaction` moment:
- **Before frame**: One frame from just before the visual change (`time_start_ms - before_buffer_ms`, default 250ms). ROI-cropped to the change region + padding.
- **After frame**: One frame from just after the visual change settles (`time_end_ms + settle_buffer_ms`, default 250ms). ROI-cropped to the same region.
- If the change spans multiple frames, optionally include one **during** frame.

For `cursor_stop` moments:
- One frame at the midpoint of the stop, ROI-cropped to cursor position.
- The LLM's job: identify the UI element under the cursor. Is it a button, a link, a form field? This provides hover/click context even without a detected visual change.

For `cursor_only` moments (dwell, thrash):
- One frame at the midpoint of the event, ROI-cropped to cursor position.

### ROI crop strategy

For `interaction` moments: the ROI is centered on the **change region bounding box** (not the cursor). This ensures the LLM sees the actual UI element that changed. The crop size is the union bounding box of the change regions + `roi_padding` on each side, clamped to a minimum of `roi_min_size` and maximum of full frame.

For `cursor_stop` and `cursor_only` moments: the ROI is centered on the **cursor position**, sized at `roi_size` + padding (same as current behaviour).

If cursor is associated with an interaction moment, annotate the cursor position within the crop.

### Request format

Batch nearby moments into a single request (gap > `batch_gap_ms` or frame count exceeds budget). Each batch includes:

1. **Scene context as text** — the most recent scene description from Pass 1 that covers this batch's time range. Injected as a text preamble, not as an image. This is the key token saving: instead of sending full-frame screenshots for context, we send a text paragraph.

2. **Moment frames** — the before/after (and optionally during) frames for each moment, ROI-cropped.

3. **Frame annotations** — per-frame metadata:
   - Timestamp
   - "before" / "during" / "after" label (for interaction moments)
   - "cursor at (x, y)" label (for cursor_stop/cursor_only moments)
   - Change region bounding box relative to crop (for interaction moments)
   - Cursor position relative to crop (if detected)
   - Moment index (to group before/after pairs)

**Prompt:**

```
You are analysing a screen recording for user interaction events.

## Current page context
{scene_description}

## Moments to analyse

The following frames show moments where either the screen content changed or the
cursor was positioned over a UI element.

For interaction moments (before/after pairs), determine:
1. What event type best describes what happened (click, hover, navigate, input_text,
   select, change_ui_state, drag, etc.)
2. What UI element was involved (button label, link text, form field, etc.)
3. A clear description of the user action

For cursor position moments (single frame), determine:
1. What UI element is under or near the cursor
2. Whether this appears to be a hover, a click (if context suggests it), or
   just the cursor resting
3. A brief description of the element and its context

If a moment shows no meaningful interaction (e.g. a minor visual artifact or the
cursor resting in a non-interactive area), omit it from the results.

{frame_annotations}

Return events as a JSON array.
```

**Response schema:** Same `RawEvent` schema as today (frame_index_start, frame_index_end, type, description, confidence, interaction_target, etc.)

### Token cost

Per interaction moment: ~2-3 ROI-cropped frames at ~258 tokens each = ~500-750 tokens.
Per cursor_stop/cursor_only moment: ~1 ROI crop at ~258 tokens.
Scene description text preamble: ~100-200 tokens per batch.

A session with 25 interaction moments + 10 cursor stops in 5 batches: ~15,000–25,000 tokens total.

Combined with Pass 1: ~33,000–67,000 tokens for a 5-minute screen track.

---

## Changes to existing code

### New files

| File | Purpose |
|---|---|
| (none) | All new code goes into existing files |

### Modified files

| File | Changes |
|---|---|
| `src/models.py` | Add `ChangeRegion`, `VisualChangeFrame`, `VisualChangeEvent`, `FlowEvent`, `Moment`, `SceneDescription`. Add visual change config fields to `ObserveConfig`. Add `cursor_tracking_enabled` to `ObserveConfig`. |
| `src/video.py` | Add `detect_visual_changes()` — the localized frame diffing function returning `tuple[VisualChangeFrame, ...]`. |
| `stages/observe.py` | Add `detect_visual_change_events()` — clusters `VisualChangeFrame`s into `VisualChangeEvent`s. Add `detect_flow_events()` — converts flow windows to discrete events. Add `detect_cursor_stops()` — simplified stop detection (replaces click/hover/dwell). Add `detect_moments()` — combines timelines and applies budget. Replace `synthesize_local_events()` and `select_frames_for_analysis()`. Update `run_observe()` orchestration. |
| `stages/analyse.py` | Add `run_scene_description_pass()` — Pass 1. Rework `run_analyse_from_observe()` → `run_interaction_analysis()` — Pass 2 using moments + scene context. Update batching and frame selection logic. |
| `prompts/` | Add `scene_describe.txt` (Pass 1 prompt). Rewrite `observe_driven.txt` (Pass 2 prompt). Update `system.txt` if needed. |

### Deleted code (in stages/observe.py)

- `_detect_click_candidates()` — replaced by visual change detection + cursor stops
- `_detect_hovers()` — replaced by cursor stop detection
- `_detect_hesitations()` — removed (hesitation is inferred by the LLM from cursor position + timing context)
- `_detect_scrolls()` — replaced by `detect_flow_events()`
- `synthesize_local_events()` — replaced by `detect_moments()`
- `select_frames_for_analysis()` — replaced by moment-based frame selection in analyse
- `format_local_events_for_prompt()` — replaced by new prompt formatting
- `compute_roi_rects()` — replaced by change-region-based and cursor-based ROI

### Kept unchanged

- `track_cursor()` and all cursor tracking code
- `_detect_dwells()` — kept, feeds into cursor-only moments
- `_detect_thrash()` — kept, feeds into cursor-only moments
- `_detect_stationary_windows()` — kept (used by dwell/thrash/cursor stops)
- `compute_flow_summaries()` — raw flow computation unchanged; `detect_flow_events()` consumes its output
- `_lookup_cursor_at_timestamp()`
- `extract_frames()`, `extract_frames_at_timestamps()`, `encode_jpeg()`, `crop_frame()`
- `src/gemini.py` — API client unchanged
- `stages/merge.py` — receives events in the same format
- `src/runner.py` — calls observe then analyse; internal changes are transparent

---

## ObserveResult changes

```python
class ObserveResult(BaseModel, frozen=True):
    recording_id: str
    cursor_trajectory: tuple[CursorDetection, ...] = ()
    visual_changes: tuple[VisualChangeEvent, ...] = ()   # new
    flow_events: tuple[FlowEvent, ...] = ()              # was flow_summary
    moments: tuple[Moment, ...] = ()                     # new, replaces local_events + selected_frames
    scene_descriptions: tuple[SceneDescription, ...] = () # populated after Pass 1
    processing_time_ms: float = 0
    frames_analysed: int = 0
    cursor_detection_rate: float = 0.0
    # Removed: local_events, roi_rects, selected_frames, flow_summary
```

Note: `scene_descriptions` is populated by the analyse stage (Pass 1), not by observe. It's stored here for convenience since it's consumed by Pass 2 which also receives the `ObserveResult`. Alternatively, Pass 1 output could be a separate model — this is a packaging decision, not architectural.

---

## Implementation order

1. **Models + config** — Add new data models and config fields. Non-breaking.
2. **Visual change detector** — `detect_visual_changes()` in `src/video.py` + `detect_visual_change_events()` in `stages/observe.py`. Test on travel_expert_veronika frames to validate noise filtering and scene/local/continuous classification.
3. **Flow event detection** — `detect_flow_events()`. Validate on sessions with scrolling.
4. **Cursor stop detection** — `detect_cursor_stops()`. Simplified version of current stop detection with deduplication.
5. **Moment detection + budget** — `detect_moments()`. Verify it produces a reasonable number of moments (expect 20-60 for a 5-minute screen track vs the current 1200+). Validate budget-based selection.
6. **Pass 1: Scene + context descriptions** — prompt + request builder + response parser. Test on a few sessions.
7. **Pass 2: Interaction analysis** — new prompt, moment-based frame selection, scene context injection. This is the biggest change to the analyse stage.
8. **Integration** — Wire into `run_observe()` and `run_analyse_from_observe()`. Update merge if needed.
9. **Cleanup** — Remove dead code (old event synthesis, old frame selection).

Steps 1–5 are local-only (no LLM calls) and can be validated by inspecting output JSON. Steps 6–7 require LLM calls and prompt iteration.

---

## Migration

This is a new experiment iteration, not a breaking change to the existing pipeline. The plan:

1. Create a new experiment branch (e.g. `visual-change-driven`) with its own config.
2. Implement behind the existing `observe.enabled` flag — when the new config fields are present, use the new pipeline; otherwise fall back to the existing behaviour.
3. Run both pipelines on the same sessions and compare output.
4. Once validated, the new pipeline becomes the default for future experiments.

The triage-driven pipeline path is unaffected.

---

## Expected outcomes

| Metric | Current (observe-driven) | Expected (visual-change-driven) |
|---|---|---|
| Local events per session | 1200+ (989 clicks, 109 hovers, ...) | 30–60 moments |
| Frames sent to LLM | 500+ | 40–70 (Pass 1: ~15 full, Pass 2: ~40 ROI crops) |
| Tokens per session (5 min) | ~750,000+ | ~33,000–67,000 |
| False positive rate | High (most click candidates are noise) | Low (visual evidence or cursor context required) |
| LLM task | "Confirm/reject these candidates" | "Describe what happened / what's here" |

---

## Open questions

1. **Settle buffer timing.** How long after a visual change should we wait before capturing the "after" frame? Fast UI transitions (dropdown) settle in ~100ms. Page navigations may take 500ms+. May need to be adaptive based on whether change frames are still being detected.

2. **Compression quality variation.** Different source recordings have different compression quality. The noise thresholds (`change_pixel_threshold`, `change_min_area_px`) may need per-recording or adaptive tuning. A possible approach: compute a "noise floor" from a quiet section of the video and set thresholds relative to it.

3. **ROI crop sizing.** Change regions vary widely in size (a small button vs a large content area). The ROI crop should be big enough for context but small enough for token efficiency. May need a min/max with adaptive sizing based on the change region.

4. **Continuous change boundary.** The 3-second threshold for continuous change classification is a guess. Video playback would easily exceed this, but a complex page load with many elements rendering might also take 3+ seconds. The area-variance heuristic (stable area = continuous content, growing area = page load) helps, but may need refinement.

5. **Cursor stop threshold tuning.** The 300ms minimum for cursor stops is a balance between capturing meaningful pauses and generating noise. Too low and we're back to the false-positive problem (just fewer of them). Too high and we miss genuine quick interactions. May need to vary by recording type.

6. **Pass 1 frame count scaling.** For very long recordings (30+ minutes), Pass 1 frame count could grow large. May need to subsample scroll midpoints and baselines, or cap Pass 1 at a fixed frame count and spread them evenly.
