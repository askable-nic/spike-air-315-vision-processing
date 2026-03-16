# Experiment Comparison: standalone-b/2 vs standalone-c/1

**Date:** 2026-03-16
**Branch B run date:** 2026-03-15 (run 2)
**Branch C run date:** 2026-03-16 (run 1)
**Model:** gemini-3-flash-preview (both branches)
**Sessions:** 12

---

## 1. Stages Run

| Stage | standalone-c/1 | standalone-b/2 |
|-------|:--------------:|:--------------:|
| normalize | Yes | Yes |
| cursor | Yes | **Skipped** |
| flow | Yes | **Skipped** |
| segment | Yes | Yes |
| prompt | Yes | Yes |
| gemini | Yes | Yes |
| merge | Yes | Yes |

**Key difference:** standalone-b/2 skipped both `cursor` and `flow` stages entirely, running Gemini-only analysis. standalone-c/1 ran the full pipeline including CV-based cursor tracking and optical flow.

---

## 2. Event Counts

### Per-Session

| Session | Video Duration | C/1 Events | B/2 Events | Delta | C/1 Merged | B/2 Merged |
|---------|---------------|:----------:|:----------:|:-----:|:----------:|:----------:|
| travel_expert_veronika | 5m 15s | 100 | 83 | +17 | 119 | 94 |
| travel_expert_lisa | 10m 56s | 103 | 121 | -18 | 124 | 148 |
| travel_expert_william | 5m 58s | 84 | 83 | +1 | 99 | 107 |
| travel_learner_sophia_jayde | 37m 0s | 490 | 412 | +78 | 692 | 468 |
| opportunity_list_georgie | 18m 9s | 215 | 224 | -9 | 311 | 319 |
| opportunity_list_ben | 7m 43s | 126 | 154 | -28 | 154 | 186 |
| flight_centre_booking_kay | 6m 31s | 70 | 75 | -5 | 84 | 91 |
| flight_centre_booking_james | 2m 57s | 44 | 61 | -17 | 50 | 73 |
| cfs_home_loan_serene | 4m 0s | 101 | 90 | +11 | 118 | 104 |
| cfs_home_loan_sasha | 9m 10s | 216 | 184 | +32 | 266 | 229 |
| ask_results_usability_brandon | 10m 59s | 179 | 204 | -25 | 224 | 274 |
| ask_create_study_brandon | 7m 23s | 132 | 132 | 0 | 164 | 173 |
| **TOTAL** | **2h 16m** | **1,860** | **1,823** | **+37** | **2,405** | **2,266** |

- **Final events:** C/1 produced 37 more events overall (+2.0%)
- **Pre-merge events:** C/1 produced 139 more pre-merge events (+6.1%), but more were deduplicated by the merge stage
- 5 sessions have more events in C/1; 6 have more in B/2; 1 is tied

### Segment-Level Errors (failed Gemini JSON parses)

| Session | C/1 Errors | B/2 Errors |
|---------|:----------:|:----------:|
| travel_expert_lisa | 1 (seg 3) | 1 (seg 4) |
| travel_learner_sophia_jayde | 1 (seg 15) | 3 (seg 7, 15, 19) |
| opportunity_list_georgie | 1 (seg 2) | 0 |
| cfs_home_loan_sasha | 0 | 1 (seg 6) |
| ask_results_usability_brandon | 1 (seg 8) | 0 |
| **Total failed segments** | **4** | **5** |

---

## 3. Event Type Distribution

### Aggregate Across All Sessions

| Event Type | C/1 Count | C/1 % | B/2 Count | B/2 % | Delta |
|------------|:---------:|:-----:|:---------:|:-----:|:-----:|
| change_ui_state | 406 | 21.8% | 418 | 22.9% | -12 |
| click | 397 | 21.3% | 411 | 22.5% | -14 |
| hover | 410 | 22.0% | 373 | 20.5% | +37 |
| scroll | 260 | 14.0% | 246 | 13.5% | +14 |
| navigate | 189 | 10.2% | 200 | 11.0% | -11 |
| input_text | 91 | 4.9% | 77 | 4.2% | +14 |
| select | 80 | 4.3% | 67 | 3.7% | +13 |
| drag | 21 | 1.1% | 19 | 1.0% | +2 |
| hesitate | 6 | 0.3% | 11 | 0.6% | -5 |
| cursor_thrash | 0 | 0.0% | 1 | 0.1% | -1 |
| **TOTAL** | **1,860** | **100%** | **1,823** | **100%** | **+37** |

Notable:
- C/1 detects 37 more **hover** events (10% more) -- likely driven by cursor tracking data enriching the Gemini prompt
- C/1 detects more **input_text**, **select**, and **scroll** events
- B/2 detects more **click**, **change_ui_state**, **navigate**, and **hesitate** events
- B/2 has 1 **cursor_thrash** event that C/1 does not

---

## 4. Timing

### Per-Session Breakdown (milliseconds)

| Session | C/1 cursor_ms | C/1 flow_ms | C/1 gemini_ms | C/1 total_ms | B/2 gemini_ms | B/2 total_ms |
|---------|-------------:|------------:|--------------:|-------------:|--------------:|-------------:|
| travel_expert_veronika | 48,229 | 2,737 | 149,257 | 200,385 | 156,838 | 156,907 |
| travel_expert_lisa | 116,377 | 6,185 | 422,841 | 545,555 | 438,042 | 438,116 |
| travel_expert_william | 43,826 | 3,342 | 155,241 | 202,600 | 186,061 | 186,128 |
| travel_learner_sophia_jayde | 164,040 | 19,720 | 836,842 | 1,020,853 | 1,203,353 | 1,203,451 |
| opportunity_list_georgie | 360,087 | 14,289 | 369,797 | 744,389 | 594,475 | 594,652 |
| opportunity_list_ben | 111,517 | 6,415 | 165,352 | 283,409 | 177,477 | 177,573 |
| flight_centre_booking_kay | 82,954 | 5,314 | 122,450 | 210,828 | 353,607 | 353,684 |
| flight_centre_booking_james | 18,161 | 2,342 | 73,876 | 94,480 | 77,141 | 77,233 |
| cfs_home_loan_serene | 38,916 | 2,199 | 126,916 | 168,130 | 139,365 | 139,430 |
| cfs_home_loan_sasha | 129,496 | 8,199 | 238,669 | 376,490 | 486,353 | 486,427 |
| ask_results_usability_brandon | 32,973 | 9,578 | 482,974 | 525,661 | 265,409 | 265,510 |
| ask_create_study_brandon | 24,532 | 5,094 | 193,963 | 223,712 | 156,896 | 156,975 |

### Totals

| Metric | C/1 | B/2 | Delta |
|--------|----:|----:|------:|
| Cursor tracking (ms) | 1,171,108 | 0 | +1,171,108 |
| Optical flow (ms) | 85,414 | 0 | +85,414 |
| Gemini analysis (ms) | 3,338,176 | 4,235,017 | -896,841 |
| **Total (ms)** | **4,596,491** | **4,236,585** | **+359,906** |
| **Total (min)** | **76.6** | **70.6** | **+6.0** |

### Timing as Minutes

| Metric | C/1 | B/2 |
|--------|----:|----:|
| Cursor tracking | 19.5 min | 0 min |
| Optical flow | 1.4 min | 0 min |
| Gemini analysis | 55.6 min | 70.6 min |
| **Total wall time** | **76.6 min** | **70.6 min** |

**Key observations:**
- C/1 is **8.5% slower** overall (76.6 min vs 70.6 min), adding ~6 min for 2h16m of video
- CV overhead (cursor + flow) adds **20.9 min** to C/1
- However, C/1 Gemini analysis is **15 min faster** (55.6 vs 70.6 min), likely because CV context in the prompt helps Gemini parse faster / with fewer retries
- Net cost of adding CV: +6 minutes for 12 sessions (30s per session average)

### Per-Session: C/1 Faster vs B/2 Faster

| C/1 Faster | B/2 Faster |
|------------|------------|
| travel_learner_sophia_jayde (-3.0 min) | travel_expert_veronika (+0.7 min) |
| ask_results_usability_brandon (-4.3 min) | travel_expert_lisa (+1.8 min) |
| flight_centre_booking_kay (+2.4 min) | travel_expert_william (+0.3 min) |
| | opportunity_list_georgie (+2.5 min) |
| | opportunity_list_ben (+1.8 min) |
| | flight_centre_booking_james (+0.3 min) |
| | cfs_home_loan_serene (+0.5 min) |
| | cfs_home_loan_sasha (+1.8 min, but Gemini much slower in B/2) |
| | ask_create_study_brandon (+1.1 min) |

C/1 was faster in only 2 of 12 sessions (those where B/2 Gemini was anomalously slow).

---

## 5. Token Usage

### Per-Session

| Session | C/1 Input | B/2 Input | C/1 Output | B/2 Output |
|---------|----------:|----------:|-----------:|-----------:|
| travel_expert_veronika | 489,261 | 481,482 | 14,763 | 11,023 |
| travel_expert_lisa | 806,613 | 796,761 | 17,077 | 22,971 |
| travel_expert_william | 493,137 | 487,020 | 12,453 | 19,569 |
| travel_learner_sophia_jayde | 2,984,717 | 2,778,429 | 97,413 | 70,939 |
| opportunity_list_georgie | 1,564,604 | 1,655,196 | 42,290 | 41,913 |
| opportunity_list_ben | 716,662 | 706,320 | 22,416 | 27,251 |
| flight_centre_booking_kay | 603,802 | 595,947 | 12,917 | 13,797 |
| flight_centre_booking_james | 267,378 | 266,478 | 7,007 | 12,015 |
| cfs_home_loan_serene | 338,334 | 332,553 | 15,172 | 12,199 |
| cfs_home_loan_sasha | 849,396 | 729,684 | 30,838 | 25,576 |
| ask_results_usability_brandon | 811,453 | 906,348 | 29,526 | 43,259 |
| ask_create_study_brandon | 605,616 | 605,127 | 26,799 | 23,522 |

### Totals

| Metric | C/1 | B/2 | Delta | % Change |
|--------|----:|----:|------:|---------:|
| Input tokens | 10,530,973 | 10,341,345 | +189,628 | +1.8% |
| Output tokens | 328,671 | 324,034 | +4,637 | +1.4% |
| **Total tokens** | **10,859,644** | **10,665,379** | **+194,265** | **+1.8%** |

### Estimated Cost (gemini-3-flash-preview pricing)

| Metric | C/1 | B/2 | Delta |
|--------|-----:|-----:|------:|
| Input cost ($0.50/M) | $5.27 | $5.17 | +$0.10 |
| Output cost ($3.00/M) | $0.99 | $0.97 | +$0.02 |
| **Total cost** | **$6.25** | **$6.14** | **+$0.11** |

Token usage is nearly identical (+1.8%). The CV context injected into prompts accounts for the small input token increase.

---

## 6. Cursor Coverage

### standalone-c/1 (cursor tracking enabled)

| Session | Total Events | Events with cursor_position | Coverage % |
|---------|:-----------:|:---------------------------:|:----------:|
| travel_expert_veronika | 100 | 22 | 22.0% |
| travel_expert_lisa | 103 | 42 | 40.8% |
| travel_expert_william | 84 | 19 | 22.6% |
| travel_learner_sophia_jayde | 490 | 37 | 7.6% |
| opportunity_list_georgie | 215 | 92 | 42.8% |
| opportunity_list_ben | 126 | 43 | 34.1% |
| flight_centre_booking_kay | 70 | 18 | 25.7% |
| flight_centre_booking_james | 44 | 4 | 9.1% |
| cfs_home_loan_serene | 101 | 34 | 33.7% |
| cfs_home_loan_sasha | 216 | 59 | 27.3% |
| ask_results_usability_brandon | 179 | 6 | 3.4% |
| ask_create_study_brandon | 132 | 4 | 3.0% |
| **TOTAL** | **1,860** | **380** | **20.4%** |

### standalone-b/2 (cursor tracking skipped -- cursor from Gemini vision only)

| Session | Total Events | Events with cursor_position | Coverage % |
|---------|:-----------:|:---------------------------:|:----------:|
| travel_expert_veronika | 83 | 26 | 31.3% |
| travel_expert_lisa | 121 | 70 | 57.9% |
| travel_expert_william | 83 | 40 | 48.2% |
| travel_learner_sophia_jayde | 412 | 205 | 49.8% |
| opportunity_list_georgie | 224 | 121 | 54.0% |
| opportunity_list_ben | 154 | 64 | 41.6% |
| flight_centre_booking_kay | 75 | 32 | 42.7% |
| flight_centre_booking_james | 61 | 28 | 45.9% |
| cfs_home_loan_serene | 90 | 22 | 24.4% |
| cfs_home_loan_sasha | 184 | 82 | 44.6% |
| ask_results_usability_brandon | 204 | 108 | 52.9% |
| ask_create_study_brandon | 132 | 71 | 53.8% |
| **TOTAL** | **1,823** | **869** | **47.7%** |

**Surprising result:** B/2 has **higher** cursor coverage (47.7%) than C/1 (20.4%), despite skipping the cursor tracking stage. This means Gemini is populating cursor_position fields from its own vision analysis more aggressively when it does NOT receive CV cursor data in the prompt. When CV cursor data is provided, Gemini may defer to the CV system and only attach cursor positions where CV confirmed one, resulting in sparser cursor annotations.

### CV Detection Stats (standalone-c/1 only)

| Session | Cursor Detections | Cursor Detected | Detection Rate | Flow Windows |
|---------|:-----------------:|:---------------:|:--------------:|:------------:|
| travel_expert_veronika | 1,008 | 813 | 80.7% | 405 |
| travel_expert_lisa | 1,714 | 991 | 57.8% | 757 |
| travel_expert_william | 923 | 579 | 62.7% | 421 |
| travel_learner_sophia_jayde | 3,813 | 551 | 14.4% | 2,317 |
| opportunity_list_georgie | 3,698 | 2,463 | 66.6% | 2,176 |
| opportunity_list_ben | 1,634 | 1,269 | 77.7% | 925 |
| flight_centre_booking_kay | 1,273 | 829 | 65.1% | 781 |
| flight_centre_booking_james | 465 | 189 | 40.6% | 352 |
| cfs_home_loan_serene | 930 | 684 | 73.5% | 478 |
| cfs_home_loan_sasha | 1,846 | 1,247 | 67.6% | 1,098 |
| ask_results_usability_brandon | 1,363 | 73 | 5.4% | 1,317 |
| ask_create_study_brandon | 907 | 38 | 4.2% | 885 |
| **TOTAL** | **19,574** | **9,726** | **49.7%** | **11,912** |

Low detection rates on `ask_*` and `travel_learner_sophia_jayde` sessions explain the low cursor coverage in C/1 for those sessions.

---

## 7. Config Differences

| Config Key | standalone-c/1 | standalone-b/2 |
|------------|----------------|----------------|
| cursor.tracking_peak_fps | 5.0 | 15.0 |
| cursor.match_height | 540 | *(not present)* |
| cursor.template_scales | [0.3, 0.4, 0.5, 0.8, 1.0, 1.25, 1.5] | [0.8, 1.0, 1.25, 1.5] |
| cursor.resample_down | "area" | *(not present)* |
| cursor.resample_up | "nearest" | *(not present)* |
| *(all other config)* | identical | identical |

Key cursor config differences (moot for B/2 since cursor stage was skipped):
- C/1 uses 7 template scales (including small 0.3-0.5 for distant cursors) vs B/2's config listing only 4
- C/1 uses peak_fps=5 vs B/2's config listing peak_fps=15
- C/1 adds match_height=540 and resampling strategy (area/nearest) not present in B/2 config

All non-cursor config is identical: same Gemini model, temperature, segmentation, flow, merge, and token cost settings.

---

## 8. Summary and Conclusions

### At a Glance

| Metric | standalone-c/1 (full CV) | standalone-b/2 (Gemini-only) | Winner |
|--------|:------------------------:|:----------------------------:|:------:|
| Total events | 1,860 | 1,823 | C/1 (+2.0%) |
| Pre-merge events | 2,405 | 2,266 | C/1 (+6.1%) |
| Failed segments | 4 | 5 | C/1 |
| Total time | 76.6 min | 70.6 min | B/2 (-8.5%) |
| Gemini time | 55.6 min | 70.6 min | C/1 (-21.3%) |
| CV overhead | 20.9 min | 0 min | B/2 |
| Input tokens | 10.53M | 10.34M | B/2 (-1.8%) |
| Output tokens | 329K | 324K | B/2 (-1.4%) |
| Est. cost | $6.25 | $6.14 | B/2 (-1.8%) |
| Cursor coverage | 20.4% | 47.7% | B/2 |

### Key Findings

1. **CV adds modest event yield (+2%) at modest time cost (+8.5%).** The full pipeline (C/1) produces 37 more final events across 12 sessions. The merge stage deduplicates more aggressively in C/1 (2,405 -> 1,860 = 22.7% reduction vs 2,266 -> 1,823 = 19.6% in B/2).

2. **CV context accelerates Gemini by 21%.** Gemini analysis alone is 15 minutes faster in C/1 (55.6 vs 70.6 min). The CV data (cursor positions, flow summaries) in the prompt likely helps Gemini converge faster, reducing internal retries and output verbosity.

3. **Cursor coverage is paradoxically lower with CV tracking.** C/1 only achieves 20.4% cursor coverage vs B/2's 47.7%. This suggests that when CV cursor data is provided, Gemini relies on it and only attaches positions where CV confirmed a detection. Without CV data, Gemini estimates cursor positions from visual analysis, giving broader but potentially less precise coverage.

4. **Token cost is nearly identical.** The CV context injected into prompts adds only 1.8% more input tokens. The marginal cost of running the full pipeline is negligible in API terms.

5. **Event type mix shifts slightly.** C/1 detects 37 more hover events and 14 more scroll events, while B/2 detects 14 more click events and 12 more change_ui_state events. The CV data appears to help distinguish hover/dwell behavior from state changes.

6. **Wall-time cost per session is ~30s.** The average additional time for running cursor + flow is (76.6 - 70.6) / 12 = 0.5 min per session, or about 30 seconds of compute overhead for a ~11-minute average video.

7. **Reliability is comparable.** Both branches experience Gemini JSON parse failures at similar rates (4 vs 5 failed segments out of ~108 total segments).
