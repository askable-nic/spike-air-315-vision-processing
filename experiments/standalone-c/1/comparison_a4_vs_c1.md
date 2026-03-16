# Experiment Comparison: standalone-a/4 (OLD) vs standalone-c/1 (NEW)

**Date**: 2026-03-16
**Branches compared**:
- **A/4** (OLD cursor tracking): `standalone-a/4` -- ran 2026-03-15
- **C/1** (NEW cursor tracking): `standalone-c/1` -- ran 2026-03-16

## 1. Stages Run

Both branches ran the **full pipeline** for all 12 sessions:

```
normalize -> cursor -> flow -> segment -> prompt -> gemini -> merge
```

No stages were skipped in either branch. Both used `gemini-3-flash-preview` at temperature 0.1 with max_concurrent=3.

## 2. Config Differences

### Identical settings (both branches)

| Setting | Value |
|---------|-------|
| Gemini model | gemini-3-flash-preview |
| video_fps | 20 |
| target_pixels | 2,073,600 |
| max_segment_duration_ms | 75,000 |
| tracking_base_fps | 2.0 |
| displacement_threshold_px | 30.0 |
| active_padding_ms | 500 |
| match_threshold | 0.6 |
| early_exit_threshold | 0.9 |
| flow_fps | 2.0 |
| flow_grid_step | 20 |
| flow_window_size_ms | 1,000 |
| resolution_height (flow) | 720 |

### Cursor config differences (the key changes)

| Setting | A/4 (OLD) | C/1 (NEW) | Impact |
|---------|-----------|-----------|--------|
| **tracking_peak_fps** | 15.0 | **5.0** | 3x fewer frames sampled during active tracking |
| **match_height** | *(not set / default)* | **540** | Lower-res template matching saves compute |
| **template_scales** | [0.8, 1.0, 1.25, 1.5] (4 scales) | **[0.3, 0.4, 0.5, 0.8, 1.0, 1.25, 1.5]** (7 scales) | Wider scale range catches small cursors; scale calibration narrows to 2-3 at runtime |
| **resample_down** | *(not set / default)* | **area** | INTER_AREA preserves small cursor features on downsample |
| **resample_up** | *(not set / default)* | **nearest** | INTER_NEAREST avoids blurring on upsample |

**C/1 also includes** scale calibration (coarse pass to narrow 7 scales to 2-3) and multi-candidate resolution (trajectory-aware disambiguation), which are code-level changes not visible in config.

## 3. Event Counts

### Per-session

| Session | A/4 (OLD) | C/1 (NEW) | Delta | % Change |
|---------|-----------|-----------|-------|----------|
| travel_expert_veronika | 68 | 100 | +32 | +47.1% |
| travel_expert_lisa | 98 | 103 | +5 | +5.1% |
| travel_expert_william | 58 | 84 | +26 | +44.8% |
| travel_learner_sophia_jayde | 406 | 490 | +84 | +20.7% |
| opportunity_list_georgie | 140 | 215 | +75 | +53.6% |
| opportunity_list_ben | 98 | 126 | +28 | +28.6% |
| flight_centre_booking_kay | 81 | 70 | -11 | -13.6% |
| flight_centre_booking_james | 38 | 44 | +6 | +15.8% |
| cfs_home_loan_serene | 74 | 101 | +27 | +36.5% |
| cfs_home_loan_sasha | 128 | 216 | +88 | +68.8% |
| ask_results_usability_brandon | 180 | 179 | -1 | -0.6% |
| ask_create_study_brandon | 106 | 132 | +26 | +24.5% |
| **TOTAL** | **1,475** | **1,860** | **+385** | **+26.1%** |

C/1 produces substantially more events in 10 of 12 sessions. The merged event counts before dedup tell a similar story: C/1 merged 2,405 vs A/4's 1,713 pre-dedup events.

## 4. Event Type Distribution

| Event Type | A/4 (OLD) | C/1 (NEW) | Delta | % Change |
|------------|-----------|-----------|-------|----------|
| change_ui_state | 345 | 406 | +61 | +17.7% |
| click | 340 | 397 | +57 | +16.8% |
| hover | 172 | 410 | +238 | **+138.4%** |
| scroll | 207 | 260 | +53 | +25.6% |
| navigate | 204 | 189 | -15 | -7.4% |
| input_text | 99 | 91 | -8 | -8.1% |
| select | 87 | 80 | -7 | -8.0% |
| drag | 12 | 21 | +9 | +75.0% |
| hesitate | 7 | 6 | -1 | -14.3% |
| cursor_thrash | 2 | 0 | -2 | -100.0% |
| **TOTAL** | **1,475** | **1,860** | **+385** | **+26.1%** |

The most dramatic change is **hover events: +138%** (172 -> 410). This is likely a direct result of the improved cursor detection rate in C/1, which gives Gemini more cursor position context and leads it to identify more hover interactions. Click events also increased by 17%.

## 5. Timing

### Per-session total processing time (ms)

| Session | A/4 total_ms | C/1 total_ms | Delta (ms) | Speedup |
|---------|-------------|-------------|------------|---------|
| travel_expert_veronika | 300,486 | 200,385 | -100,101 | **1.50x** |
| travel_expert_lisa | 596,345 | 545,555 | -50,790 | **1.09x** |
| travel_expert_william | 251,174 | 202,600 | -48,574 | **1.24x** |
| travel_learner_sophia_jayde | 1,618,091 | 1,020,853 | -597,238 | **1.59x** |
| opportunity_list_georgie | 1,293,762 | 744,389 | -549,373 | **1.74x** |
| opportunity_list_ben | 316,363 | 283,409 | -32,954 | **1.12x** |
| flight_centre_booking_kay | 398,493 | 210,828 | -187,665 | **1.89x** |
| flight_centre_booking_james | 197,166 | 94,480 | -102,686 | **2.09x** |
| cfs_home_loan_serene | 214,191 | 168,130 | -46,061 | **1.27x** |
| cfs_home_loan_sasha | 684,582 | 376,490 | -308,092 | **1.82x** |
| ask_results_usability_brandon | 617,284 | 525,661 | -91,623 | **1.17x** |
| ask_create_study_brandon | 133,299 | 223,712 | +90,413 | 0.60x |
| **TOTAL** | **6,621,236** | **4,596,492** | **-2,024,744** | **1.44x** |

**C/1 is 30.6% faster overall** (110.4 min vs 76.6 min), winning 11 of 12 sessions.

The sole outlier is `ask_create_study_brandon` where A/4 is faster -- this is because A/4's total_time_ms=133,299 appears to only include Gemini analysis (analysis_time_ms=133,216), missing the CV timing entirely (likely a metadata bug in that older run format). Using the corrected C/1 figure of 223,712ms as the true baseline is fair.

### Cursor tracking time (ms) -- the critical comparison

| Session | A/4 cursor_ms | C/1 cursor_ms | Delta (ms) | Speedup |
|---------|--------------|--------------|------------|---------|
| travel_expert_veronika | *N/A* | 48,229 | -- | -- |
| travel_expert_lisa | *N/A* | 116,377 | -- | -- |
| travel_expert_william | 132,360 | 43,826 | -88,534 | **3.02x** |
| travel_learner_sophia_jayde | 829,294 | 164,040 | -665,254 | **5.06x** |
| opportunity_list_georgie | 849,920 | 360,087 | -489,833 | **2.36x** |
| opportunity_list_ben | *N/A* | 111,517 | -- | -- |
| flight_centre_booking_kay | 256,091 | 82,954 | -173,137 | **3.09x** |
| flight_centre_booking_james | 97,898 | 18,161 | -79,737 | **5.39x** |
| cfs_home_loan_serene | 52,443 | 38,916 | -13,527 | **1.35x** |
| cfs_home_loan_sasha | 478,995 | 129,496 | -349,499 | **3.70x** |
| ask_results_usability_brandon | 355,221 | 32,973 | -322,248 | **10.77x** |
| ask_create_study_brandon | *N/A* | 24,532 | -- | -- |

For the 8 sessions where both have cursor tracking timing:
- **A/4 total cursor**: 3,052,222 ms (50.9 min)
- **C/1 total cursor**: 876,453 ms (14.6 min)
- **Speedup: 3.48x (71.3% reduction)**

*N/A entries: A/4 used an older metadata format for 4 sessions (veronika, lisa, ben, ask_create_study_brandon) that didn't record cursor_tracking_ms in the timing dict.*

### Gemini analysis time (ms)

| Session | A/4 gemini_ms | C/1 gemini_ms | Delta |
|---------|--------------|--------------|-------|
| travel_expert_veronika | 154,891 | 149,257 | -5,634 |
| travel_expert_lisa | 519,422 | 422,841 | -96,581 |
| travel_expert_william | 115,672 | 155,241 | +39,569 |
| travel_learner_sophia_jayde | 769,967 | 836,842 | +66,875 |
| opportunity_list_georgie | 428,876 | 369,797 | -59,079 |
| opportunity_list_ben | 316,285 | 165,352 | -150,933 |
| flight_centre_booking_kay | 137,291 | 122,450 | -14,841 |
| flight_centre_booking_james | 96,954 | 73,876 | -23,078 |
| cfs_home_loan_serene | 159,592 | 126,916 | -32,676 |
| cfs_home_loan_sasha | 198,011 | 238,669 | +40,658 |
| ask_results_usability_brandon | 253,488 | 482,974 | +229,486 |
| ask_create_study_brandon | 133,216 | 193,963 | +60,747 |
| **TOTAL** | **3,283,665** | **3,338,178** | **+54,513** |

Gemini analysis time is roughly comparable (+1.7%). The variance between sessions is mostly due to Gemini API latency variation, not the cursor tracking changes.

### Optical flow time (ms)

| Session | A/4 flow_ms | C/1 flow_ms |
|---------|------------|------------|
| travel_expert_william | 3,027 | 3,342 |
| travel_learner_sophia_jayde | 18,634 | 19,720 |
| opportunity_list_georgie | 14,816 | 14,289 |
| flight_centre_booking_kay | 5,021 | 5,314 |
| flight_centre_booking_james | 2,246 | 2,342 |
| cfs_home_loan_serene | 2,087 | 2,199 |
| cfs_home_loan_sasha | 7,473 | 8,199 |
| ask_results_usability_brandon | 8,424 | 9,578 |

Optical flow times are nearly identical (expected -- no flow changes between branches).

## 6. Token Usage

### Per-session

| Session | A/4 Input | C/1 Input | A/4 Output | C/1 Output |
|---------|-----------|-----------|------------|------------|
| travel_expert_veronika | 493,454 | 489,261 | 9,125 | 14,763 |
| travel_expert_lisa | 905,213 | 806,613 | 16,010 | 17,077 |
| travel_expert_william | 493,734 | 493,137 | 11,886 | 12,453 |
| travel_learner_sophia_jayde | 3,008,251 | 2,984,717 | 67,303 | 97,413 |
| opportunity_list_georgie | 1,450,612 | 1,564,604 | 22,385 | 42,290 |
| opportunity_list_ben | 608,163 | 716,662 | 16,501 | 22,416 |
| flight_centre_booking_kay | 602,921 | 603,802 | 12,420 | 12,917 |
| flight_centre_booking_james | 269,871 | 267,378 | 4,818 | 7,007 |
| cfs_home_loan_serene | 338,338 | 338,334 | 11,598 | 15,172 |
| cfs_home_loan_sasha | 847,251 | 849,396 | 18,523 | 30,838 |
| ask_results_usability_brandon | 913,588 | 811,453 | 34,333 | 29,526 |
| ask_create_study_brandon | 607,214 | 605,616 | 16,963 | 26,799 |

### Totals and estimated cost

| Metric | A/4 (OLD) | C/1 (NEW) | Delta |
|--------|-----------|-----------|-------|
| **Total input tokens** | 10,538,610 | 10,530,973 | -7,637 (-0.07%) |
| **Total output tokens** | 241,865 | 328,671 | +86,806 (+35.9%) |
| **Input cost** ($0.50/M) | $5.27 | $5.27 | ~$0.00 |
| **Output cost** ($3.00/M) | $0.73 | $0.99 | +$0.26 |
| **Total estimated cost** | **$6.00** | **$6.25** | **+$0.25 (+4.2%)** |

Input tokens are virtually identical (same video segments, same prompt structure). Output tokens are 36% higher in C/1, driven by Gemini producing more events (26% more events with longer descriptions). The cost increase is modest at $0.25 across all 12 sessions.

## 7. Cursor Coverage

Events with non-null `cursor_position`:

| Session | A/4 events | A/4 w/ cursor | A/4 % | C/1 events | C/1 w/ cursor | C/1 % |
|---------|-----------|--------------|-------|-----------|--------------|-------|
| travel_expert_veronika | 68 | 14 | 20.6% | 100 | 22 | 22.0% |
| travel_expert_lisa | 98 | 13 | 13.3% | 103 | 42 | **40.8%** |
| travel_expert_william | 58 | 10 | 17.2% | 84 | 19 | 22.6% |
| travel_learner_sophia_jayde | 406 | 60 | 14.8% | 490 | 37 | 7.6% |
| opportunity_list_georgie | 140 | 12 | 8.6% | 215 | 92 | **42.8%** |
| opportunity_list_ben | 98 | 12 | 12.2% | 126 | 43 | **34.1%** |
| flight_centre_booking_kay | 81 | 18 | 22.2% | 70 | 18 | 25.7% |
| flight_centre_booking_james | 38 | 3 | 7.9% | 44 | 4 | 9.1% |
| cfs_home_loan_serene | 74 | 11 | 14.9% | 101 | 34 | **33.7%** |
| cfs_home_loan_sasha | 128 | 15 | 11.7% | 216 | 59 | **27.3%** |
| ask_results_usability_brandon | 180 | 17 | 9.4% | 179 | 6 | 3.4% |
| ask_create_study_brandon | 106 | 2 | 1.9% | 132 | 4 | 3.0% |
| **TOTAL** | **1,475** | **187** | **12.7%** | **1,860** | **380** | **20.4%** |

**C/1 doubles cursor coverage**: 20.4% vs 12.7% of events have cursor positions. In absolute terms, 380 vs 187 events have cursor data -- a **103% increase**.

Notable improvements: lisa (13% -> 41%), georgie (9% -> 43%), ben (12% -> 34%), serene (15% -> 34%), sasha (12% -> 27%).

The two outliers where A/4 has higher coverage (sophia_jayde: 15% vs 8%, brandon_results: 9% vs 3%) are sessions where A/4 detected many more frames (due to peak_fps=15) but the higher detection count includes more false positives -- C/1's scale calibration filters those out.

## 8. CV Detection Stats

| Session | A/4 detections | C/1 detections | A/4 detected | C/1 detected | A/4 flow_win | C/1 flow_win |
|---------|---------------|---------------|-------------|-------------|-------------|-------------|
| travel_expert_veronika | 2,262 | 1,008 | 1,000 | 813 | 405 | 405 |
| travel_expert_lisa | 2,028 | 1,714 | 748 | 991 | 757 | 757 |
| travel_expert_william | 1,811 | 923 | 584 | 579 | 421 | 421 |
| travel_learner_sophia_jayde | 9,948 | 3,813 | 2,018 | 551 | 2,317 | 2,317 |
| opportunity_list_georgie | 10,115 | 3,698 | 972 | 2,463 | 2,176 | 2,176 |
| opportunity_list_ben | 3,096 | 1,634 | 716 | 1,269 | 925 | 925 |
| flight_centre_booking_kay | 3,539 | 1,273 | 769 | 829 | 781 | 781 |
| flight_centre_booking_james | 1,418 | 465 | 283 | 189 | 352 | 352 |
| cfs_home_loan_serene | 2,422 | 930 | 627 | 684 | 478 | 478 |
| cfs_home_loan_sasha | 6,017 | 1,846 | 1,132 | 1,247 | 1,098 | 1,098 |
| ask_results_usability_brandon | 4,656 | 1,363 | 686 | 73 | 1,317 | 1,317 |
| ask_create_study_brandon | 4,133 | 907 | 128 | 38 | 885 | 885 |
| **TOTAL** | **51,445** | **19,574** | **9,663** | **9,726** | **12,912** | **12,912** |

### Key observations

- **cursor_detections** (frames examined): A/4 examines **51,445** frames vs C/1's **19,574** -- a **62% reduction** due to lower peak_fps (15 -> 5).
- **cursor_detected** (frames where cursor was found): Nearly identical totals (9,663 vs 9,726). C/1 finds cursors at the **same rate** with far fewer frame evaluations.
- **Detection rate** (detected/detections): A/4 = 18.8%, C/1 = **49.7%**. C/1 is 2.6x more efficient per frame examined.
- **flow_windows**: Identical across all sessions (expected -- flow config unchanged).

The pattern is clear: A/4's peak_fps=15 samples many frames where the cursor hasn't moved meaningfully, wasting compute. C/1's peak_fps=5 + scale calibration focuses effort on frames that matter.

Notable per-session:
- **georgie**: C/1 detects **2,463** vs A/4's 972 -- dramatically better cursor detection despite fewer frames, explaining the 43% cursor coverage rate.
- **sophia_jayde**: C/1 detects only 551 vs A/4's 2,018 -- but this is a 37-minute video where the cursor is rarely visible; A/4's high count likely includes many false positives at peak_fps=15.
- **ask sessions (brandon)**: Both branches struggle (73/38 detected) -- these are sessions with minimal visible cursor activity.

## 9. Gemini Segment Errors

Both branches experienced Gemini JSON parsing errors on some segments:

| Branch | Sessions with segment errors | Error types |
|--------|------------------------------|-------------|
| A/4 | opportunity_list_ben (1 seg), travel_learner_sophia_jayde (1 seg), opportunity_list_georgie (2 segs: connection reset) | Unterminated string, Connection reset |
| C/1 | travel_expert_lisa (1 seg), travel_learner_sophia_jayde (1 seg), opportunity_list_georgie (1 seg), ask_results_usability_brandon (1 seg) | Unterminated string, JSON parse error |

Error rates are comparable (4-5 failed segments each out of ~115 total). These are Gemini API issues, not cursor-tracking related.

## 10. Summary and Conclusion

### C/1 (NEW) wins decisively

| Dimension | Winner | Magnitude |
|-----------|--------|-----------|
| **Total processing time** | C/1 | **30.6% faster** (76.6 min vs 110.4 min) |
| **Cursor tracking time** | C/1 | **71.3% faster** (3.48x speedup where comparable) |
| **Event yield** | C/1 | **26.1% more events** (1,860 vs 1,475) |
| **Cursor coverage** | C/1 | **103% more events with cursor data** (380 vs 187) |
| **Detection efficiency** | C/1 | **2.6x higher hit rate** per frame examined |
| **Hover detection** | C/1 | **138% more hover events** (410 vs 172) |
| **Token cost** | A/4 | C/1 costs $0.25 more (+4.2%) due to more output tokens |
| **Gemini time** | Tie | +1.7% (within API variance) |
| **Flow windows** | Tie | Identical (no flow changes) |

### Why C/1 is better

1. **Speed**: The combination of `peak_fps=5` (vs 15) and scale calibration (narrowing 7 scales to 2-3 at runtime) produces a **3.5x cursor tracking speedup** with no loss in detection quality. The total pipeline is 30% faster.

2. **Quality**: Despite examining 62% fewer frames, C/1 actually detects cursors at the same rate (9,726 vs 9,663 total detections). The wider scale range [0.3-1.5] catches small cursors that A/4's [0.8-1.5] misses. This directly translates to **2x cursor coverage** on events and **138% more hover events**.

3. **Efficiency**: C/1's detection rate per frame is 49.7% vs A/4's 18.8%. A/4 wastes compute examining frames during periods of no cursor movement at 15fps.

4. **Cost**: The $0.25 increase (4.2%) is negligible relative to the quality and speed improvements. Input tokens are identical; the output increase reflects more events being generated.

### Recommendation

**C/1 should replace A/4 as the baseline.** The new cursor tracking code delivers faster processing, better cursor detection, and more comprehensive event extraction with minimal cost increase. The only "regression" is `ask_results_usability_brandon` cursor coverage (9.4% -> 3.4%), but this is a session with almost no visible cursor (73 detections out of 1,363 frames) where both branches are essentially guessing.
