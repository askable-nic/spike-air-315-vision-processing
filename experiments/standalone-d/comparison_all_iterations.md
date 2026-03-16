# Standalone-D FPS Comparison (vs C1 baseline)

Baseline: **standalone-c/1** (base:2 / peak:5) — full pipeline run with events.json.

## Config Matrix

| | C1 (baseline) | D1 | D2 | D3 |
|---|---|---|---|---|
| `base_fps` | 2 | 2 | **1** | **3** |
| `peak_fps` | 5 | **4** | 5 | 5 |

---

## 1. Processing Time (isolated sequential runs)

| Config | Cursor time | vs C1 |
|--------|------------|-------|
| C1: base:2 / peak:5 | 1171.1s | baseline |
| D1: base:2 / peak:4 | 1128.8s | **-3.6%** |
| D2: base:1 / peak:5 | 905.3s | **-22.7%** |
| D3: base:3 / peak:5 | 1383.3s | **+18.1%** |

**Base FPS dominates processing time.** Halving base (2→1) saves 23%. Increasing base (2→3) adds 18%. Peak FPS has minimal impact on time (D1 vs C1: only 3.6% difference from peak:4 vs peak:5).

## 2. Detection Coverage

| Config | Total detections | vs C1 |
|--------|-----------------|-------|
| C1: base:2 / peak:5 | 9726 | baseline |
| D1: base:2 / peak:4 | 7770 | **-20.1%** |
| D2: base:1 / peak:5 | 9296 | **-4.4%** |
| D3: base:3 / peak:5 | 10356 | **+6.5%** |

**Peak FPS drives detection count more than base FPS.** Dropping peak from 5→4 loses 20% of detections (D1). Dropping base from 2→1 only loses 4.4% (D2) because the higher peak:5 compensates during active regions.

## 3. Trajectory Accuracy (where both detected)

| Config | Samples | Identical (0px) | Within 5px | Mean drift | Max drift |
|--------|--------:|----------------:|-----------:|-----------:|----------:|
| D1: base:2 / peak:4 | 3206 | 3154 (98.4%) | 3201 (99.8%) | 1.1px | 1828px |
| D2: base:1 / peak:5 | 4423 | 3768 (85.2%) | 3830 (86.6%) | 100.1px | 2024px |
| D3: base:3 / peak:5 | 4137 | 3502 (84.7%) | 3535 (85.5%) | 102.7px | 2166px |

**D1 has the highest agreement rate** (98.4% identical) because base:2 matches C1's coarse pass exactly — only the peak pass differs. D2 and D3 change the base rate, producing different coarse pass timestamps and more false-positive outliers in the ~15% tail.

## 4. Event Cursor Enrichment (908 cursor events from C1)

C1 has cursor position data for 242 of 908 cursor events (26.7% coverage). The remaining 666 events had no cursor detection near the event timestamp in any iteration.

### Coverage summary

| Config | Events with pos | Coverage lost | Coverage gained | Net | Within 5px | >20px drift |
|--------|----------------:|--------------:|----------------:|----:|-----------:|------------:|
| C1 (baseline) | 242 | — | — | — | — | — |
| D1: base:2 / peak:4 | 241 | **4** | 3 | -1 | 193 (81%) | **44 (18%)** |
| D2: base:1 / peak:5 | 238 | **24** | 20 | -4 | 158 (72%) | **58 (27%)** |
| D3: base:3 / peak:5 | 245 | **19** | 22 | +3 | 153 (69%) | **68 (30%)** |

### Drift analysis

The high mean drift values (~100px) are misleading — they're driven by a tail of false-positive matches where the cursor was matched to a UI element (webcam thumbnail, button icon, etc.) instead of the actual cursor. The pattern is bimodal:

- **~70-80% of events**: identical or within 5px (correct detections)
- **~20-30% of events**: 100-2000px drift (false positive in one or both runs)

The false positives cluster in specific sessions:
- **cfs_home_loan_sasha/serene**: long scrolling pages with many small UI elements that template-match as cursors
- **opportunity_list_georgie**: dense card layouts where cursor icons in UI match the template
- **travel_expert_veronika/lisa**: fast interaction sequences where the nearest detection is from a different moment

### Events that lost cursor coverage

**D1 (base:2/peak:4) — 4 events lost:**
These are all during brief interactions where peak:4 missed the cursor at the exact event timestamp:
- opportunity_list_ben: hover over AI Interview card (t=455s)
- opportunity_list_georgie: hover over AI Interview task card (t=1031s)
- travel_expert_lisa: click Webjet logo (t=546s)
- travel_expert_veronika: hover over skyscanner suggestion (t=104s)

**D2 (base:1/peak:5) — 24 events lost:**
Mostly during periods where the coarser base rate (1 FPS vs 2 FPS) missed detections between active regions. Heavy losses in:
- cfs_home_loan_sasha: 7 events lost (t=324s-514s — late-session browsing)
- cfs_home_loan_serene: 2 events lost (radio button/next button clicks)
- opportunity_list_georgie: 5 events lost (filter/hover interactions)
- travel_expert_lisa: 4 events lost (input field clicks, search interactions)
- travel_expert_veronika: 2 events lost (From input field, dropdown selection)

**D3 (base:3/peak:5) — 19 events lost:**
Despite having the most detections overall (+6.5%), D3 still loses 19 events. The different coarse-pass timestamps (every 333ms vs 500ms) shift which frames are sampled, causing some event-adjacent detections to fall outside the 500ms lookup window:
- opportunity_list_georgie: 8 events lost (filter chips, hover cards)
- travel_expert_veronika: 6 events lost (input fields, card hovers)
- cfs_home_loan: 4 events lost (clicks, hovers)

---

## 5. Summary

| | Time | Detections | Events lost | Accuracy |
|---|---|---|---|---|
| **D2: base:1 / peak:5** | **-23% fastest** | -4.4% | 24 lost | 85% identical |
| **D1: base:2 / peak:4** | -3.6% | -20.1% | 4 lost | **98% identical** |
| **D3: base:3 / peak:5** | +18% slowest | +6.5% | 19 lost | 85% identical |

### Recommendations

- **If optimizing for speed:** D2 (base:1/peak:5) is 23% faster with only 4.4% detection loss and 4 net events lost. Good trade-off.
- **If optimizing for coverage:** D3 (base:3/peak:5) finds 6.5% more detections but costs 18% more time. Diminishing returns.
- **Avoid reducing peak FPS:** D1 (peak:4) loses 20% of detections for only 3.6% time savings. Peak FPS has the worst cost/benefit ratio to reduce.
- **C1 (base:2/peak:5) remains a strong default** — balanced speed and coverage.
