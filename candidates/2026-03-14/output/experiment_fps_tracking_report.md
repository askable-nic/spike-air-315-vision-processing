# Cursor Tracking FPS & Fidelity Experiments

**Date**: 2026-03-16
**Branch**: `stanalone-direct-video`
**Sessions tested**: `travel_expert_william` (358s), `opportunity_list_ben` (463s)

## 1. Peak FPS Experiment (base:2 held constant)

Baseline: `base:2, peak:15` on travel_expert_william (output/2026-03-15_030547, 58 final events).

| Config | Time | Speedup | Coverage lost | Mean drift | Max drift |
|--------|-----:|--------:|--------------:|-----------:|----------:|
| base:2, peak:15 | 132.4s | — | — | — | — |
| base:3, peak:6 | 105.9s | 20% | 0 | 0.0px | 0.0px |
| **base:2, peak:5** | **88.5s** | **33%** | **0** | **0.1px** | **1.0px** |
| base:2, peak:4 | 83.1s | 37% | 0 | 44.1px | **445.3px** |
| base:1, peak:5 | 77.8s | 41% | 1 | 0.0px | 0.0px |

**Recommendation**: `base:2, peak:5` — 33% speedup with near-zero fidelity loss. Peak:4 introduces a 445px outlier on a click event. Base:1 saves an extra 8% but misses an active region entirely (24.6s gap at 324-349s).

### Cross-session validation (opportunity_list_ben)

| Config | Time | Speedup |
|--------|-----:|--------:|
| base:2, peak:15 | 205.0s | — |
| base:3, peak:6 | 164.0s | 20% |
| base:2, peak:5 | 119.8s | 42% |

Speedup ratios held consistent across sessions. However, event-level cursor position comparison on this session revealed large drifts (up to 1800px) — investigation showed these were **false positives in the baseline** rather than regressions in the experiment configs.

## 2. False Positive Investigation (opportunity_list_ben)

### The (1202,907) problem

The `hand` template matched a static UI element at pixel (1202,907) across **91 separate detections in 15 distinct time clusters**. These individually stayed below the `static_filter_duration_ms` threshold (3000ms) and were not filtered. The position kept winning over real cursor candidates because it scored 0.65-0.67 confidence.

### Root cause: single-best template matching

`match_cursor_in_frame` uses `cv2.minMaxLoc` per template/scale combo, returning only the single global maximum. When a UI icon scores 0.67 and the real cursor scores 0.63, the real cursor is silently discarded.

### Visual inspection findings

At t=136.8s the user confirmed a real arrow cursor at (890,35). Template matcher scores at that position:
- **Best score: 0.226** (hand@0.8x) — far below the 0.6 threshold
- All 5 candidates returned were at random UI positions, none near the real cursor
- The cursor at full resolution is ~15px tall, but at 360p match resolution it's only ~5px — smaller than the smallest template (25px at 0.8x scale)

## 3. Multi-Candidate Resolution (implemented)

Added to `cursor.py`:

### `match_cursor_in_frame_multi()`
Returns all spatially-distinct candidates within `confidence_range` (default 0.05) of the best match. Deduplicates by position (>20px apart). Each template/scale combo still contributes at most one peak via `minMaxLoc`.

### `resolve_candidates()`
Two-pass resolution for frames with multiple candidates:

1. **Pass 1**: Resolve unambiguous frames (0 or 1 candidate) as anchors
2. **Pass 2**: For multi-candidate frames, score each using:
   - **Trajectory proximity** (+0.03 to -0.02): linear interpolation between nearest resolved anchors before and after
   - **Flow independence** (up to -0.03): penalises candidates whose displacement aligns with optical flow direction (UI element riding a scroll)
   - **Position frequency** (up to -0.02): penalises positions appearing in >3 separated time clusters (likely static UI elements)

### `track_cursor()` changes
New keyword args: `confidence_range: float = 0.0` and `flow_windows: tuple[FlowWindow, ...] = ()`. When `confidence_range > 0`, uses multi-candidate matching in the fine pass. Original behaviour preserved when `confidence_range == 0`.

### Results on opportunity_list_ben (base:2, peak:15, 360p, confidence_range=0.05 + flow)

| Metric | Original | Multi-candidate |
|--------|----------|-----------------|
| (1202,907) detections | 91 | 28 (70% reduction) |
| Events with cursor position | 19 | 24 (+5 gained) |
| Processing time | 205s | 143s (same config) |

The remaining 28 detections at (1202,907) occur in frames where no competing candidate exists — the resolver can only choose from what the template matcher finds.

## 4. Match Resolution & Template Scale Investigation

### Template scale mismatch

The cursor in `opportunity_list_ben.mp4` is ~15px at full resolution (1922x1078). At 360p match height, it's ~5px. The template scales (0.8x-1.5x of 32px templates = 25-48px) are **4-5x larger** than the cursor.

| Match height | Cursor size | Needed scale | Best score at cursor |
|---:|---:|---:|---:|
| 360p | ~5px | 0.2x | 0.352 |
| 540p | ~8px | 0.3x | 0.593 |
| 720p | ~10px | 0.3x | 0.536 |

At 540p with 0.3x scale, the cursor scores 0.593 — near the 0.6 threshold. But small templates (6-9px) match random UI texture at 0.85+, creating far more false positives than they solve.

### Test: 540p + scales [0.3, 0.4, 0.5, 0.8, 1.0, 1.25, 1.5]

| Metric | 360p, scales 0.8-1.5 | 540p, scales 0.3-1.5 |
|--------|---:|---:|
| Detected samples | 716 | 1235 |
| (1202,907) false positives | 91 | 0 |
| Processing time | 205s | 515s |
| False positive noise | Moderate | Severe (small templates) |

The small scales eliminated the (1202,907) problem (it no longer dominated) but replaced it with widespread high-confidence noise from tiny templates matching random texture. At t=136.8s, the system picked (494,482) ibeam at 0.849 confidence instead of the real cursor at (890,35).

### Resampling strategy

Added configurable resampling (`resample_down`, `resample_up` in CursorConfig):
- Frame downscaling: `cv2.INTER_AREA` (was `INTER_LINEAR`) — proper anti-aliased averaging
- Template upscaling: `cv2.INTER_NEAREST` (was `INTER_LINEAR`) — preserves sharp cursor edges

Impact: +0.04 score improvement at 360p. Marginal on its own but free (no perf cost).

### Template gap

Visual inspection confirmed the cursor in `opportunity_list_ben.mp4` is a standard macOS arrow (white fill, black outline). The existing `arrow` template has the correct shape and colors, but at the video's compression quality and the small pixel size, the correlation is poor. This is not a missing template — it's a **resolution/compression limitation** of template matching on small cursors.

## 5. Open Questions for Next Session

1. **Scale-dependent thresholds**: Should smaller template scales require higher confidence to count as a match? (e.g. 0.8 for scales < 0.5 vs 0.6 for scales >= 0.8)

2. **Candidate count as a no-detection signal**: When 4-5 candidates all score within 0.03 of each other, it likely means none are real. Could reject these frames as no-detection.

3. **Match height selection**: Could inspect cursor size early (e.g. from a few high-confidence detections) and choose match_height adaptively.

4. **Pipeline integration for flow-based resolution**: Currently cursor runs before flow. Full flow-informed resolution would need either: (a) reorder to flow→cursor, or (b) cursor→flow→refine-cursor as a third pass.

5. **The `opportunity_list_ben` (1202,907) position**: User should verify at t=124.9s, t=258.8s, t=437.2s whether a real cursor is ever present there alongside the UI element.

## 6. Config Changes Made

`config.yaml` was updated to:
```yaml
cursor:
  match_height: 540
  template_scales: [0.3, 0.4, 0.5, 0.8, 1.0, 1.25, 1.5]
  resample_down: area
  resample_up: nearest
```

**Note**: The small scales (0.3-0.5) produce excessive false positives at this threshold. For production use, either revert to `[0.8, 1.0, 1.25, 1.5]` or implement scale-dependent thresholds.

## 7. Files Modified

- `vex_extract/config.py` — Added `match_height`, `resample_down`, `resample_up` to CursorConfig
- `vex_extract/video.py` — Added `resample` parameter to `extract_frames()`, `_INTERPOLATION_FLAGS` dict
- `vex_extract/cursor.py` — Added `MatchCandidate`, `match_cursor_in_frame_multi()`, `_match_frames_multi()`, `resolve_candidates()` with helpers; modified `track_cursor()` to accept `confidence_range` and `flow_windows`
- `config.yaml` — Updated cursor section with new fields

## 8. Experiment Scripts

- `experiment_5fps.py` — Original peak FPS comparison (hardcoded baseline)
- `experiment_fps.py` — Parameterized single-config runner (`--base-fps`, `--peak-fps`)
- `experiment_multi.py` — Multi-config runner (`--gemini-run` for event enrichment comparison)
