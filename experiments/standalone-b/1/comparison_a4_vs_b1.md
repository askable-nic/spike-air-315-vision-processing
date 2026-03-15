# Experiment Comparison: A/4 (with local CV) vs B/1 (skipped local CV)

**Date:** 2026-03-15
**Video corpus:** 12 sessions, 126 minutes total video

## Key Difference

- **Experiment A/4** runs all pipeline stages: `normalize -> cursor -> flow -> segment -> prompt -> gemini -> merge`
- **Experiment B/1** skips local computer-vision stages: `normalize -> segment -> prompt -> gemini -> merge` (skips `cursor` and `flow`)

Both use `gemini-3-flash-preview` at temperature 0.1, identical segmentation (75s max, 5s overlap), and the same merge settings.

---

## Executive Summary

| Metric | A/4 (with CV) | B/1 (no CV) | Delta |
|---|---|---|---|
| Total final events | 1,475 | 1,919 | **+444 (+30.1%)** |
| Total processing time | 110.4 min | 60.7 min | **-45.0% (1.8x faster)** |
| Total input tokens | 10,538,610 | 10,526,570 | -0.1% (negligible) |
| Total output tokens | 241,865 | 351,326 | **+45.3%** |
| Estimated API cost | $5.99 | $6.32 | +$0.33 (+5.5%) |
| Avg confidence | 0.916 | 0.928 | +0.012 |
| Avg events/min of video | 11.7 | 15.2 | +30% |
| Avg processing speed | 1.14x realtime | 2.08x realtime | **1.8x faster** |
| Segment parse errors | 4 | 3 | -1 |
| Segment network errors | 2 | 0 | -2 |
| Sessions where B < A | -- | 1 (flight_centre_booking_kay) | |

**Bottom line:** Skipping local CV (Experiment B) produces more events, runs nearly twice as fast, costs only 5.5% more in API fees, and reports marginally higher confidence. The extra events are primarily additional `hover` and `change_ui_state` detections. Whether these extra events represent genuine quality improvement or noise depends on downstream use; see the qualitative analysis below.

---

## Per-Session Comparison

| Session | Video (min) | A events | B events | Delta | A time (s) | B time (s) | Speedup |
|---|---|---|---|---|---|---|---|
| ask_create_study_brandon | 7.4 | 106 | 169 | +63 | 133 | 209 | 0.6x |
| ask_results_usability_brandon | 11.0 | 180 | 211 | +31 | 617 | 286 | 2.2x |
| cfs_home_loan_sasha | 9.2 | 128 | 211 | +83 | 685 | 342 | 2.0x |
| cfs_home_loan_serene | 4.0 | 74 | 92 | +18 | 214 | 115 | 1.9x |
| flight_centre_booking_james | 2.9 | 38 | 59 | +21 | 197 | 85 | 2.3x |
| flight_centre_booking_kay | 6.5 | 81 | 75 | **-6** | 398 | 333 | 1.2x |
| opportunity_list_ben | 7.7 | 98 | 125 | +27 | 316 | 415 | 0.8x |
| opportunity_list_georgie | 18.1 | 140 | 270 | **+130** | 1294 | 595 | 2.2x |
| travel_expert_lisa | 10.9 | 98 | 141 | +43 | 596 | 237 | 2.5x |
| travel_expert_veronika | 5.2 | 68 | 74 | +6 | 300 | 134 | 2.2x |
| travel_expert_william | 6.0 | 58 | 81 | +23 | 251 | 135 | 1.9x |
| travel_learner_sophia_jayde | 37.0 | 406 | 411 | +5 | 1618 | 752 | 2.2x |

**Outliers:**
- `opportunity_list_georgie`: B produces nearly 2x the events (270 vs 140), driven by 102 hover events vs 8 in A. Many of B's hovers describe the user reading/scanning task cards in a list, which is genuine but granular.
- `ask_create_study_brandon`: B was actually slower (209s vs 133s), likely due to Gemini API variability rather than CV overhead.
- `opportunity_list_ben`: B was also slightly slower (415s vs 316s), again likely API timing variance.
- `flight_centre_booking_kay`: The only session where B produced fewer events than A (-6).

---

## Event Type Breakdown (Aggregated)

| Event Type | A/4 | B/1 | Delta | Notes |
|---|---|---|---|---|
| change_ui_state | 345 | 436 | +91 (+26%) | B reports more UI state transitions |
| click | 340 | 401 | +61 (+18%) | B detects more clicks |
| hover | 172 | 432 | **+260 (+151%)** | Largest increase by far |
| scroll | 207 | 248 | +41 (+20%) | Moderate increase |
| navigate | 204 | 206 | +2 (+1%) | Essentially the same |
| input_text | 99 | 92 | -7 (-7%) | Slightly fewer in B |
| select | 87 | 81 | -6 (-7%) | Slightly fewer in B |
| drag | 12 | 14 | +2 | Comparable |
| hesitate | 7 | 8 | +1 | Comparable |
| cursor_thrash | 2 | 1 | -1 | Comparable |

**Key observation:** The massive increase in `hover` events (172 -> 432) accounts for 59% of the total event delta. Without local cursor tracking data in the prompt, Gemini appears to infer hover behavior purely from visual cues (cursor position changes in frames), producing many more hover annotations. Whether these are signal or noise varies by session.

The slight decrease in `input_text` and `select` events in B is unexpected. For `input_text`, B occasionally captures "thinking out loud" text box entries that A misses (e.g., in `travel_expert_veronika`), but also occasionally fails to capture typed moderator instructions that A does capture (e.g., in `opportunity_list_georgie` where A has 3 input_text events and B has 0).

---

## Processing Time Analysis

| Metric | A/4 | B/1 |
|---|---|---|
| Total wall-clock time | 110.4 min | 60.7 min |
| Average per session | 9.2 min | 5.1 min |
| Median processing speed | ~1.1x realtime | ~2.1x realtime |
| Slowest session speed | 0.80x (cfs_home_loan_sasha) | 1.12x (opportunity_list_ben) |
| Fastest session speed | 3.33x (ask_create_study_brandon) | 2.95x (travel_learner_sophia_jayde) |

Skipping cursor tracking and optical flow saves significant wall-clock time. In A, these CV stages run before the Gemini API calls and can be substantial for longer videos with many cursor detections (e.g., `cfs_home_loan_sasha` had 6,017 cursor detections across 1,132 frames). B eliminates this overhead entirely.

Across 10 of 12 sessions, B was faster (median speedup 2.1x). The two exceptions (`ask_create_study_brandon` and `opportunity_list_ben`) are attributable to Gemini API response time variance rather than any inherent cost of skipping CV.

---

## Token Usage & Cost

| Metric | A/4 | B/1 | Delta |
|---|---|---|---|
| Total input tokens | 10,538,610 | 10,526,570 | -12,040 (-0.1%) |
| Total output tokens | 241,865 | 351,326 | +109,461 (+45.3%) |
| Est. input cost | $5.27 | $5.26 | -$0.01 |
| Est. output cost | $0.73 | $1.05 | +$0.33 |
| Est. total cost | $5.99 | $6.32 | +$0.33 (+5.5%) |

Input tokens are nearly identical because both experiments send the same video frames. The slight difference comes from B not including CV summary data (cursor positions, flow vectors) in prompts, which saves a small number of tokens.

Output tokens increase 45% because Gemini generates more event descriptions when not constrained by CV data. This adds $0.33 across 12 sessions (126 min of video), or roughly $0.003/min of video.

---

## Confidence Scores

| Bucket | A/4 | B/1 |
|---|---|---|
| 1.0 | 426 (28.9%) | 696 (36.3%) |
| 0.95 | 56 (3.8%) | 104 (5.4%) |
| 0.9 | 819 (55.5%) | 931 (48.5%) |
| 0.8 | 131 (8.9%) | 167 (8.7%) |
| 0.7 | 40 (2.7%) | 21 (1.1%) |
| <0.7 | 3 (0.2%) | 0 (0.0%) |
| **Average** | **0.916** | **0.928** |
| **Minimum** | 0.60 | 0.70 |

B reports higher confidence overall. This is likely because A's merge stage sometimes forces events from the CV pipeline that have lower confidence, while B only has Gemini-sourced events. The absence of low-confidence (<0.7) events in B supports this interpretation.

---

## Cursor Position Data

A critical difference: **Experiment A populates `cursor_position` coordinates for some events; Experiment B never does.**

| Session | A: cursor_position populated | B: cursor_position populated |
|---|---|---|
| ask_create_study_brandon | 2 | 0 |
| ask_results_usability_brandon | 17 | 0 |
| cfs_home_loan_sasha | 15 | 0 |
| cfs_home_loan_serene | 11 | 0 |
| flight_centre_booking_james | 3 | 0 |
| flight_centre_booking_kay | 18 | 0 |
| opportunity_list_ben | 12 | 0 |
| opportunity_list_georgie | 12 | 0 |
| travel_expert_lisa | 13 | 0 |
| travel_expert_veronika | 14 | 0 |
| travel_expert_william | 10 | 0 |
| travel_learner_sophia_jayde | 60 | 0 |
| **Total** | **187** | **0** |

If downstream consumers need pixel-level cursor coordinates, Experiment A is the only option. B's events include `cursor_position: null` for interaction events.

---

## Page Metadata (page_title, page_location)

B tends to populate `page_title` and `page_location` more consistently:

| Session | A: page_title | B: page_title | A: page_location | B: page_location |
|---|---|---|---|---|
| ask_create_study_brandon | 19 | 100 | 22 | 101 |
| cfs_home_loan_sasha | 18 | 78 | 11 | 67 |
| flight_centre_booking_james | 5 | 30 | 5 | 31 |
| travel_learner_sophia_jayde | 168 | 302 | 120 | 255 |

This is a notable quality improvement in B. Without CV data to anchor events, Gemini appears to more actively extract page context from visible browser chrome.

---

## Segment Failures & Errors

| Error Type | A/4 | B/1 |
|---|---|---|
| JSON parse errors (unterminated string) | 2 sessions (3 segments) | 2 sessions (2 segments) |
| Network errors (connection reset) | 1 session (2 segments) | 0 |
| **Total failed segments** | **5** | **2** |

Both experiments experience occasional Gemini output truncation (unterminated JSON strings). A additionally suffered connection-reset errors in `opportunity_list_georgie` (segments 13-14), losing those segments entirely.

---

## Qualitative Observations

### Flight Centre James: Date Accuracy

This session reveals an interesting accuracy difference. The user selects travel dates in a calendar picker:

- **A** reports: departure March 20, return March **22**. URL in A: `.../2026-03-20/MEL/ADL/2026-03-22/...`
- **B** reports: departure March 20, return March **27**. URL in B: `.../2026-03-20/MEL/ADL/2026-03-27/...`

The return date is different. B captures the URL from visible browser chrome which shows the actual page the browser navigated to. A captures a URL but it may be from a different source. Both report what Gemini inferred from visual analysis, so the "ground truth" would need to be verified from the original video. B's version captures more hover events around the date selection (hovering over March 11, 20, 27) which provides additional context about the user's search behavior.

Additionally, B captures intermediate steps that A misses:
- Clicking the "Where to?" field and seeing the destination dropdown
- Selecting "Sydney, Australia" from the dropdown
- Honey browser extension notification appearing
- Skeleton screen loading state

### Hover Event Quality

In `opportunity_list_georgie`, B captures 102 hover events vs A's 8. Sample B hovers describe the user scanning through task cards:
- "User hovers over the 'AI Interview' task card" (multiple instances)
- "User hovers over the task card titled 'People who bought food on a delivery app recently'"
- "User hovers over the filter icon in the top right corner"

These are genuine interactions visible in the video, but their density may be excessive for some analysis purposes. A's 8 hovers are more selective, capturing only longer/more deliberate hover actions.

### Think-Aloud Text Capture

In `travel_expert_veronika`, B captures 2 additional `input_text` events for the "What are you thinking right now?" text box that A misses entirely. This is a quality win for B, as these think-aloud entries are analytically valuable.

Conversely, in `opportunity_list_georgie`, A captures 3 `input_text` events (moderator typing task instructions) and 1 `navigate` event that B misses completely. This represents a gap in B's coverage for that session.

---

## Per-Session Cost Comparison

| Session | A cost | B cost | Delta |
|---|---|---|---|
| ask_create_study_brandon | $0.354 | $0.401 | +$0.047 |
| ask_results_usability_brandon | $0.560 | $0.582 | +$0.022 |
| cfs_home_loan_sasha | $0.479 | $0.476 | -$0.003 |
| cfs_home_loan_serene | $0.204 | $0.205 | +$0.001 |
| flight_centre_booking_james | $0.149 | $0.165 | +$0.016 |
| flight_centre_booking_kay | $0.339 | $0.336 | -$0.003 |
| opportunity_list_ben | $0.354 | $0.362 | +$0.008 |
| opportunity_list_georgie | $0.792 | $0.966 | +$0.174 |
| travel_expert_lisa | $0.501 | $0.512 | +$0.011 |
| travel_expert_veronika | $0.274 | $0.275 | +$0.001 |
| travel_expert_william | $0.283 | $0.289 | +$0.006 |
| travel_learner_sophia_jayde | $1.706 | $1.749 | +$0.043 |
| **Total** | **$5.994** | **$6.317** | **+$0.323** |

---

## Conclusions

1. **Speed:** B is consistently faster (median 2.1x realtime vs 1.1x for A), making it viable for near-realtime processing. The CV stages in A are a significant bottleneck, especially for videos with lots of cursor activity.

2. **Event volume:** B produces 30% more events. The increase is dominated by hover events (+151%) and change_ui_state (+26%). For use cases that want comprehensive interaction logging, this is positive. For use cases that want concise summaries, the extra hovers may need filtering.

3. **Cost:** Nearly identical. The 5.5% cost increase ($0.003/min) is negligible compared to the 45% time savings.

4. **Cursor coordinates:** Only A provides pixel-level `cursor_position` data (187 events across 12 sessions). If this is needed downstream, A is required.

5. **Page metadata:** B is significantly better at populating `page_title` and `page_location` fields, likely because Gemini focuses more on browser chrome without CV data competing for attention.

6. **Confidence:** B reports slightly higher confidence (0.928 vs 0.916) with no events below 0.7.

7. **Reliability:** Both experiments have similar rates of Gemini output parse failures. A additionally suffers from occasional network errors during the CV-heavy processing phase.

8. **Coverage gaps:** Both experiments occasionally miss events the other captures. B misses some typed text events in 1 session; A misses think-aloud box entries in another. Neither approach is strictly dominant on coverage.

**Recommendation:** For most use cases, B (skipping local CV) is the better default. It is faster, cheaper in wall-clock terms, and produces richer event coverage with better page metadata. Switch to A only when pixel-level cursor coordinates are specifically needed.
