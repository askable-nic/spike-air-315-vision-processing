# Multi-config FPS Experiment: opportunity_list_ben

Video duration: 463s

## 1. Processing Time

| Config | Time (s) | Samples | Detected | Det/sec | Speedup vs base2_peak15 |
|--------|--------:|--------:|---------:|--------:|------:|
| base2_peak15 | 205.0 | 3096 | 716 | 1.55 | — |
| base3_peak6 | 164.0 | 1965 | 377 | 0.81 | 20% |
| base2_peak5 | 119.8 | 1502 | 331 | 0.71 | 42% |

## 2. Trajectory Quality

### base2_peak15
- Detection gaps: median=67ms, p95=567ms, max=65267ms
- Non-detection runs >5s: 20

### base3_peak6
- Detection gaps: median=200ms, p95=4600ms, max=65333ms
- Non-detection runs >5s: 16

### base2_peak5
- Detection gaps: median=200ms, p95=6333ms, max=65400ms
- Non-detection runs >5s: 17

## 3. CV Summary Size (lines per segment)

| Segment | base2_peak15 | base3_peak6 | base2_peak5 |
|------:||------:|------:|------:|
| 0 | 18 | 12 | 12 |
| 1 | 23 | 15 | 13 |
| 2 | 8 | 5 | 4 |
| 3 | 14 | 19 | 20 |
| 4 | 21 | 16 | 29 |
| 5 | 3 | 2 | 2 |
| 6 | 9 | 7 | 6 |

## 4. Impact on Final Event Cursor Positions

All comparisons are against **base2_peak15** as reference.

### base3_peak6 vs base2_peak15

| Metric | Value |
|--------|------:|
| Cursor events | 68 |
| Both have position | 17 |
| Coverage lost | 2 |
| Neither has position | 46 |
| Mean distance | 249.9px |
| Median distance | 3.0px |
| Max distance | 1632.7px |
| Within 5px | 10/17 |
| Within 50px | 10/17 |

**Events that lost coverage:**

- 319748ms click: User clicks on the 'Smart Filters Mobile App' browser tab.
- 319753ms click: User clicks on the 'Smart Filters Mobile App' browser tab.

**Events with >5px drift:**

| Time (ms) | Type | base2_peak15 | base3_peak6 | Drift |
|----------:|------|-----------|----------|------:|
| 255803 | hover | (31,310) | (31,807) | 497.0px |
| 413094 | click | (1202,907) | (1063,638) | 302.8px |
| 441694 | click | (1202,907) | (370,455) | 946.9px |
| 450394 | click | (1836,893) | (228,610) | 1632.7px |
| 486089 | click | (150,270) | (228,496) | 239.1px |
| 492689 | hover | (13,526) | (13,424) | 102.0px |
| 498289 | hover | (13,152) | (13,673) | 521.0px |

### base2_peak5 vs base2_peak15

| Metric | Value |
|--------|------:|
| Cursor events | 68 |
| Both have position | 19 |
| Coverage lost | 0 |
| Neither has position | 44 |
| Mean distance | 267.9px |
| Median distance | 12.0px |
| Max distance | 1804.8px |
| Within 5px | 9/19 |
| Within 50px | 11/19 |

**Events with >5px drift:**

| Time (ms) | Type | base2_peak15 | base2_peak5 | Drift |
|----------:|------|-----------|----------|------:|
| 255803 | hover | (31,310) | (31,807) | 497.0px |
| 276903 | hover | (25,367) | (25,355) | 12.0px |
| 319748 | click | (953,912) | (476,662) | 538.5px |
| 319753 | click | (953,912) | (476,662) | 538.5px |
| 441694 | click | (1202,907) | (344,485) | 956.2px |
| 450394 | click | (1836,893) | (150,249) | 1804.8px |
| 452689 | hover | (42,695) | (242,368) | 383.3px |
| 482989 | click | (150,234) | (150,222) | 12.0px |
| 486089 | click | (150,270) | (228,496) | 239.1px |
| 492689 | hover | (13,526) | (13,424) | 102.0px |

## 5. Summary

| Config | Time | Speedup | Coverage lost | Mean drift | Max drift |
|--------|-----:|--------:|--------------:|-----------:|----------:|
| base2_peak15 | 205.0s | — | — | — | — |
| base3_peak6 | 164.0s | 20% | 2 | 249.9px | 1632.7px |
| base2_peak5 | 119.8s | 42% | 0 | 267.9px | 1804.8px |
