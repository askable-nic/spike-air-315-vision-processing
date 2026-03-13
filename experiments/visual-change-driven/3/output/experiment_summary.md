# Experiment: visual-change-driven/3

**Sessions**: 12/12
**Early break**: No

## Aggregate Metrics

| Metric | Value |
|--------|-------|
| F1 | 0.124 |
| Recall | 0.082 |
| Precision | 0.257 |

## Pipeline Scores

| Score | Value |
|-------|-------|
| Overall | 0.15 |
| Coverage | 0.09 |
| Type Accuracy | 0.40 |
| Timing | 0.50 |

## Per-Session Results

| Session | F1 | Recall | Precision | Severity |
|---------|------|--------|-----------|----------|
| ask_create_study_brandon | 0.183 | 0.121 | 0.382 | acceptable |
| ask_results_usability_brandon | 0.089 | 0.066 | 0.137 | systematic |
| cfs_home_loan_sasha | 0.220 | 0.150 | 0.418 | acceptable |
| cfs_home_loan_serene | 0.089 | 0.051 | 0.357 | critical |
| flight_centre_booking_james | 0.114 | 0.088 | 0.161 | systematic |
| flight_centre_booking_kay | 0.182 | 0.141 | 0.256 | systematic |
| opportunity_list_ben | 0.242 | 0.171 | 0.414 | systematic |
| opportunity_list_georgie | 0.089 | 0.064 | 0.147 | systematic |
| travel_expert_lisa | 0.020 | 0.011 | 0.105 | critical |
| travel_expert_veronika | 0.124 | 0.087 | 0.214 | systematic |
| travel_expert_william | 0.144 | 0.089 | 0.375 | systematic |
| travel_learner_sophia_jayde | 0.089 | 0.054 | 0.260 | systematic |

## Qualitative Session Summaries

### ask_create_study_brandon (acceptable)
Captures major workflow steps (create study, set title, configure research method, set location, add screener questions, submit) with reasonable fidelity, but misses many granular interactions (hover events, loading transitions, hesitations) and has moderate timing offsets of 1-6s on matched events.

### ask_results_usability_brandon (systematic)
Captures core user journey (searching studies, navigating results, switching tasks, exploring filters, viewing heatmaps) with reasonable accuracy. Generates excessive scroll events and misses fine-grained hover/dwell interactions. Scroll detection over-triggers significantly.

### cfs_home_loan_sasha (acceptable)
Accurately captures the multi-site browsing journey (Google, Unloan, Lendi, Mortgage Choice, Compare the Market, ANZ, Moneysmart) with correct event ordering and reasonable timing. Key form fills, button clicks, and navigations well-detected. Main gaps are missing hesitate events and detailed hovers.

### cfs_home_loan_serene (critical)
Only 14 events vs ~67 baseline events, missing the vast majority of the user journey through Aussie refinance flow, Google searches, St. George calculator, ubank, and Macquarie Bank. Large time gaps with zero coverage and several events describe low-level visual changes rather than meaningful interactions.

### flight_centre_booking_james (systematic)
Captures the overall booking flow shape but over-generates change_ui_state and dwell events where baseline has hover/click sequences. Consistently uses dwell instead of hover for cursor pause events. Several key click interactions (Search flights, Select fare, CONTINUE) are missing.

### flight_centre_booking_kay (systematic)
Captures general flow shape with reasonable timing but systematically uses dwell instead of hover/click for key interactions. Pre-task phase well-covered. Fare selection and return flight selection partially captured, but critical click events on fare buttons are missing.

### opportunity_list_ben (systematic)
Captures only 41% of baseline events (58 vs 140), systematically missing all 14 input_text events and majority of click/navigate tab-switching events. Core prototype interactions (scrolling, filter use) present but at substantially reduced granularity with multiple 20s+ coverage gaps.

### opportunity_list_georgie (systematic)
Captures 44% of baseline events (116 vs 264) with reasonable scroll and filter coverage, but systematically misses drag events, most hover events (11 of 107 baseline hovers captured), and has multiple 30-40s coverage gaps in later session where filter modal is repeatedly opened.

### travel_expert_lisa (critical)
Only 19 events for 178 in baseline (11% coverage). Entire major interaction sequences missing: Google search to Webjet, flight search form filling, clicking Search Flights, browsing 12+ flight detail expansions, Brisbane departure switch. Essentially a sparse skeleton of a rich interaction session.

### travel_expert_veronika (systematic)
Captures only 28 of 69 baseline events (41%), missing most navigations (1 of 6), clicks (2 of 11), and the entire Skyscanner-to-Google-to-Trello-to-Booking.com arc. Large coverage gaps with zero events during active browsing.

### travel_expert_william (systematic)
Captures only 24 of 101 baseline events (24%), with massive coverage gaps in hotel browsing/filtering (198k-347k, 2.5 min, 30+ baseline events missing). Misses almost all scroll events (3 of 18), most hovers (4 of 29), and key filter interactions.

### travel_learner_sophia_jayde (systematic)
Captures 104 of 501 baseline events (21%) for a 37-minute dual-screen observer session. Correctly identifies video call context. Airbnb segment almost entirely missing. Observer perspective causes massive dwell events spanning periods of active participant interaction. Google Flights and CompareTheMarket segments reasonably captured.

## Systematic Patterns

1. **change_ui_state near-total loss**: ~5% recall across all sessions. Loading transitions, dropdown opens, tooltip appearances systematically missed.
2. **Hover under-detection**: Pipeline captures 10-30% of baseline hover events. Cursor-only movements without visual changes are invisible.
3. **Dwell hallucination**: Experiment generates dwell events in all sessions despite zero dwells in any baseline. Partially replaces hover/hesitate with wrong semantics.
4. **Click under-detection**: Key button clicks (Search, Submit, CONTINUE, SELECT) frequently missed even when visual change occurs.
5. **Input text blindness**: Text input events missed in 8 of 12 sessions.
6. **Navigation under-detection**: Page transitions captured at 17-71% rate. Within-flow navigations particularly affected.
7. **Scroll detection bias**: Scrolls disproportionately well-detected in some sessions, over-segmented in others.
8. **Token budget underutilization**: All sessions use only 33-43% of available budget.
9. **Cursor detection bottleneck**: Detection rates 3.7-100% across sessions, but high rates still yield poor results.
10. **Temporal coverage gaps**: 20-137s gaps during active user interaction across all sessions.

## Root Cause Analysis

Three pipeline stages contribute to F1=0.124, with Observe and Analyse as co-primary bottlenecks:

**Observe (primary)**: Cursor template matching detection rates (3.7-100%) directly limit interaction event coverage. Token budget consistently underutilized (33-43%). Scene change detection works but misses fine-grained interactions.

**Analyse (co-primary)**: Even with good observation data, LLM extraction under-extracts. travel_expert_lisa has 100% cursor detection but F1=0.020. The prompt focuses on visual changes rather than user intent, causing change_ui_state events to be described as context, clicks to be subsumed into visual consequences, and dwell events to be hallucinated.

**Merge (minor)**: time_tolerance_ms=2000 and similarity_threshold=0.7 appear reasonable.

## Recommendations

| Priority | Config Key | Current | Recommended | Confidence | Rationale |
|----------|-----------|---------|-------------|------------|-----------|
| 1 | analyse.model | gemini-3-flash-preview | gemini-2.5-pro | 0.7 | Analyse stage under-extracts even with good data. More capable model may better identify interaction events. |
| 2 | observe.token_budget_per_minute | 50000 | 80000 | 0.6 | All sessions use only 33-43% of budget. Increasing allows more moments to be processed. |
| 3 | observe.change_min_area_px | 500 | 300 | 0.5 | Many missed events involve small UI changes below 500px threshold. |
| 4 | observe.baseline_max_gap_ms | 5000 | 3000 | 0.5 | 20-137s temporal gaps suggest more frequent baseline sampling needed. |
| 5 | observe.cursor_tracking_enabled | true | true (needs pipeline improvement) | 0.9 | Template matching approach (3.7-100% range) is primary bottleneck. Needs ML-based detection. |
