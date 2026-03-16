# Experiment: base1_peak5 vs base2_peak15

## 1. Processing Time

| Metric | base2_peak15 | base1_peak5 | Ratio |
|--------|------:|-----:|------:|
| Cursor tracking (ms) | 132,360 | 77,764 | 0.59x |
| Cursor tracking (s) | 132.4 | 77.8 | |
| Time saved | | | **41%** |

## 2. Trajectory Statistics

| Metric | base2_peak15 | base1_peak5 |
|--------|------:|-----:|
| Total samples | 1811 | 966 |
| Detected samples | 584 | 336 |
| Detection rate | 32.2% | 34.8% |
| Detections/sec | 1.63 | 0.94 |

## 3. Coarse Pass & Active Region Impact

The coarse pass (base FPS) determines which time ranges are scanned at peak FPS.
A lower base FPS means fewer coarse samples, which can cause the system to
miss brief cursor movements that fall between coarse samples.

## 4. Trajectory Quality (dropout check)

### base2_peak15 baseline
- Gap stats (between detected frames): median=133.0ms, p95=985.0ms, max=63690.0ms
- Large gaps (>10x expected interval): 47
- Long non-detection runs (>5s):
  - 17.9s - 23.3s (5.4s)
  - 28.3s - 34.6s (6.2s)
  - 38.6s - 44.5s (5.9s)
  - 47.4s - 76.6s (29.2s)
  - 93.4s - 104.9s (11.5s)
  - 105.6s - 168.7s (63.0s)
  - 221.8s - 227.0s (5.2s)
  - 233.0s - 247.9s (14.9s)
  - 280.7s - 289.3s (8.6s)
  - 293.8s - 308.1s (14.3s)

### base1_peak5 experiment
- Gap stats (between detected frames): median=277.0ms, p95=3154.0ms, max=68251.0ms
- Large gaps (>10x expected interval): 22
- Long non-detection runs (>5s):
  - 17.9s - 23.2s (5.3s)
  - 28.4s - 35.5s (7.0s)
  - 47.4s - 76.6s (29.2s)
  - 93.5s - 104.7s (11.2s)
  - 106.8s - 172.9s (66.2s)
  - 220.3s - 226.9s (6.6s)
  - 279.5s - 289.7s (10.3s)
  - 293.6s - 307.9s (14.3s)
  - 315.3s - 320.6s (5.3s)
  - 324.9s - 349.5s (24.6s)

## 5. Impact on CV Summary (Gemini prompt)

Segments with identical summaries: 0/5

### Segment 0
- base2_peak15: 26 lines, base1_peak5: 19 lines
- Diff:
```diff
--- segment_000 (base2_peak15)
+++ segment_000 (base1_peak5)
@@ -1,26 +1,19 @@
-2524-2591ms: moved from (218,203) to (221,492)

-2724-2940ms: moved from (221,286) to (218,624)

-3007-4140ms: moved from (218,203) to (218,209)

-4408-4741ms: moved from (218,168) to (218,166)

-4808-6813ms: stationary pos=(218,168)

+2724-3340ms: moved from (221,286) to (218,618)

+3540-4008ms: moved from (218,298) to (218,215)

+4408-6745ms: stationary pos=(218,168)

 6946-7879ms: stationary pos=(218,386)

 10961-10961ms: stationary pos=(682,824)

-11694-11694ms: stationary pos=(716,759)

-12522-12769ms: stationary pos=(1239,976)

+12522-12722ms: stationary pos=(1239,976)

 13431-13431ms: stationary pos=(955,861)

-14225-14225ms: stationary pos=(482,763)

-14959-14959ms: stationary pos=(799,775)

-15325-15525ms: stationary pos=(603,856)

+14158-14158ms: stationary pos=(912,809)

+15325-15325ms: stationary pos=(603,856)

 15851-15851ms: stationary pos=(603,847)

-17518-17651ms: stationary pos=(274,871)

-17784-17784ms: stationary pos=(815,951)

+17651-17651ms: stationary pos=(274,871)

 23378-23378ms: stationary pos=(1061,973)

 26532-26532ms: stationary pos=(912,809)

-28175-28175ms: stationary pos=(826,938)

-34677-34677ms: stationary pos=(682,824)

+28241-28241ms: stationary pos=(823,938)

 35736-35736ms: stationary pos=(1816,194)

-36114-36114ms: stationary pos=(1782,194)

 38489-38489ms: stationary pos=(387,990)

-44632-44632ms: stationary pos=(731,987)

+41173-41173ms: stationary pos=(713,759)

 45672-45672ms: stationary pos=(618,766)

-46786-47104ms: stationary pos=(603,853)
+46917-46917ms: stationary pos=(603,853)
```

### Segment 1
- base2_peak15: 10 lines, base1_peak5: 7 lines
- Diff:
```diff
--- segment_001 (base2_peak15)
+++ segment_001 (base1_peak5)
@@ -1,10 +1,7 @@
 10447-16446ms: moved from (1420,558) to (1420,619)

-16948-17446ms: stationary pos=(1420,558)

-17947-22093ms: moved from (1420,619) to (1420,798)

-22221-22484ms: moved from (1386,1019) to (1401,808)

-22812-23463ms: stationary pos=(1403,574)

-23574-23756ms: moved from (1386,1019) to (1386,1010)

-23833-24098ms: moved from (1386,1019) to (1386,1018)

-24601-26112ms: stationary pos=(1386,1018)

+16948-22155ms: moved from (1420,558) to (1420,798)

+22484-22484ms: stationary pos=(1401,808)

+22941-23463ms: stationary pos=(1403,574)

+24037-26112ms: stationary pos=(1386,1019)

 26658-26658ms: stationary pos=(1386,662)

-38374-38945ms: stationary pos=(1432,302)
+38374-38811ms: stationary pos=(1432,302)
```

### Segment 2
- base2_peak15: 19 lines, base1_peak5: 12 lines
- Diff:
```diff
--- segment_002 (base2_peak15)
+++ segment_002 (base1_peak5)
@@ -1,19 +1,12 @@
-31008-31008ms: stationary pos=(624,701)

 35435-38891ms: moved from (624,560) to (624,342)

-39663-39799ms: stationary pos=(680,871)

-39964-42853ms: moved from (680,850) to (680,1031)

-43069-52117ms: moved from (624,535) to (624,793)

-52239-52353ms: stationary pos=(680,592)

-52426-53849ms: moved from (680,591) to (680,573)

-53902-56345ms: moved from (624,775) to (624,766)

-57073-57589ms: moved from (624,775) to (680,590)

-57673-59636ms: moved from (680,595) to (680,1031)

-59753-59871ms: moved from (765,221) to (624,544)

-59965-71463ms: moved from (624,581) to (624,661)

-71666-71794ms: stationary pos=(680,460)

-72131-73090ms: moved from (680,459) to (680,324)

-73268-73465ms: moved from (1355,712) to (680,248)

+39663-42743ms: moved from (680,871) to (680,1025)

+43069-56013ms: moved from (624,535) to (624,756)

+57073-57318ms: stationary pos=(680,573)

+57589-59636ms: moved from (680,589) to (680,1031)

+59871-65090ms: moved from (624,544) to (624,489)

+65832-66329ms: stationary pos=(680,1016)

+66568-72923ms: moved from (680,967) to (680,324)

+73268-74202ms: moved from (1355,712) to (680,248)

 78715-79199ms: stationary pos=(680,248)

 79927-80144ms: stationary pos=(624,698)

-80334-80808ms: moved from (802,393) to (955,975)

-81609-81609ms: stationary pos=(504,761)
+80617-80617ms: stationary pos=(955,971)
```

### Segment 3
- base2_peak15: 42 lines, base1_peak5: 33 lines
- Diff:
```diff
--- segment_003 (base2_peak15)
+++ segment_003 (base1_peak5)
@@ -1,42 +1,33 @@
-39-167ms: stationary pos=(680,460)

-504-1463ms: moved from (680,459) to (680,324)

-1641-1838ms: moved from (1355,712) to (680,248)

+39-504ms: stationary pos=(680,460)

+853-1296ms: moved from (680,457) to (680,324)

+1641-2575ms: moved from (1355,712) to (680,248)

 7088-7572ms: stationary pos=(680,248)

 8300-8517ms: stationary pos=(624,698)

-8707-9181ms: moved from (802,393) to (955,975)

-9982-10511ms: stationary pos=(504,761)

-10832-10832ms: stationary pos=(621,741)

-11817-11817ms: stationary pos=(584,839)

-17236-20675ms: moved from (1671,996) to (1671,520)

-20747-20833ms: moved from (356,268) to (977,268)

-21615-21695ms: stationary pos=(1671,517)

-21839-21971ms: moved from (409,335) to (382,498)

-22125-22365ms: stationary pos=(409,335)

-22498-22964ms: stationary pos=(909,351)

-38047-38655ms: stationary pos=(680,862)

-39482-39482ms: stationary pos=(531,406)

-40032-40032ms: stationary pos=(944,678)

-40353-40631ms: moved from (968,286) to (1671,1021)

-40952-42013ms: stationary pos=(1671,818)

-42234-42365ms: moved from (633,600) to (1671,818)

-42493-43572ms: moved from (637,581) to (1671,759)

+8990-8990ms: stationary pos=(955,971)

+10118-10118ms: stationary pos=(504,761)

+17236-20491ms: moved from (1671,996) to (1671,609)

+20747-21615ms: moved from (356,268) to (1671,517)

+21839-22365ms: stationary pos=(409,335)

+22661-22893ms: stationary pos=(909,351)

+23142-24086ms: stationary pos=(1671,517)

+24254-24555ms: moved from (680,186) to (637,168)

+24911-26213ms: moved from (637,162) to (637,198)

+26437-27198ms: moved from (680,134) to (680,303)

+27758-28484ms: moved from (1671,517) to (680,432)

+28962-31344ms: moved from (680,438) to (680,862)

+37434-38655ms: stationary pos=(680,862)

+40631-42013ms: moved from (1671,1021) to (1671,818)

+42234-42493ms: moved from (633,600) to (637,581)

+42955-43449ms: stationary pos=(1671,759)

 48978-49272ms: moved from (323,925) to (519,1021)

-49408-50905ms: stationary pos=(323,925)

-51125-51258ms: moved from (538,741) to (323,925)

-51660-51859ms: moved from (323,925) to (1671,858)

-51993-52342ms: moved from (1155,154) to (1671,720)

-52526-54285ms: moved from (1155,154) to (1671,720)

-59874-60027ms: stationary pos=(1671,720)

-60169-61220ms: stationary pos=(624,729)

+49540-51258ms: stationary pos=(323,925)

+51660-51993ms: moved from (323,925) to (1155,154)

+52342-54285ms: stationary pos=(1671,720)

+59874-61220ms: moved from (1671,720) to (624,729)

 61931-62484ms: moved from (1124,974) to (860,1005)

-62671-62804ms: moved from (1287,907) to (1355,990)

-62930-63055ms: moved from (1429,756) to (1287,907)

-63302-63819ms: stationary pos=(1287,907)

-64057-64057ms: stationary pos=(1436,774)

-64316-64316ms: stationary pos=(860,750)

-68468-68620ms: moved from (860,382) to (255,382)

-68860-68927ms: moved from (1671,812) to (725,931)

-69093-69616ms: moved from (848,369) to (725,892)

-69803-69803ms: stationary pos=(851,369)

-79947-81097ms: moved from (725,870) to (725,1036)

-81233-81483ms: moved from (1671,944) to (1316,825)
+62804-63819ms: moved from (1355,990) to (1287,907)

+64057-64316ms: moved from (1436,774) to (860,750)

+68468-68860ms: moved from (860,382) to (1671,812)

+69093-69093ms: stationary pos=(848,369)

+80070-80926ms: moved from (725,799) to (725,1011)

+81233-81483ms: moved from (1671,944) to (1315,824)
```

### Segment 4
- base2_peak15: 24 lines, base1_peak5: 12 lines
- Diff:
```diff
--- segment_004 (base2_peak15)
+++ segment_004 (base1_peak5)
@@ -1,24 +1,12 @@
-8320-9470ms: moved from (725,870) to (725,1036)

-9606-10576ms: moved from (1671,944) to (1315,824)

-10729-10825ms: moved from (1671,978) to (1315,824)

-11150-11343ms: moved from (1671,981) to (1671,1018)

-11460-11460ms: stationary pos=(1315,824)

+8443-9299ms: moved from (725,799) to (725,1011)

+9606-10379ms: moved from (1671,944) to (1315,824)

+10729-11460ms: moved from (1671,978) to (1315,824)

 11845-11845ms: stationary pos=(1465,151)

-12141-12141ms: stationary pos=(1465,154)

 26709-30303ms: moved from (1671,1027) to (1671,913)

-30424-30506ms: stationary pos=(725,1039)

-30766-32555ms: moved from (725,990) to (725,627)

-32697-33267ms: moved from (1238,563) to (725,584)

-33378-33598ms: stationary pos=(1238,563)

-33708-33708ms: stationary pos=(725,560)

-39208-43126ms: moved from (725,529) to (725,136)

-67642-67642ms: stationary pos=(839,1021)

-68237-68345ms: moved from (603,856) to (713,861)

-69141-69141ms: stationary pos=(554,896)

-70839-71106ms: stationary pos=(1045,951)

-72106-72106ms: stationary pos=(1382,778)

-72989-72989ms: stationary pos=(197,410)

-73202-73202ms: stationary pos=(187,881)

-73534-73601ms: moved from (845,371) to (860,408)

-73867-75504ms: stationary pos=(860,408)

-75636-76097ms: stationary pos=(849,371)
+30506-33267ms: moved from (725,1039) to (725,584)

+33598-33598ms: stationary pos=(1238,563)

+39351-43126ms: moved from (725,471) to (725,136)

+68237-68237ms: stationary pos=(603,856)

+70773-70973ms: stationary pos=(1045,951)

+72989-73202ms: moved from (197,410) to (187,881)

+74171-75430ms: stationary pos=(860,408)
```

## 6. Impact on Final Event Cursor Positions

| Category | Count |
|----------|------:|
| Cursor events total | 27 |
| Both have position | 10 |
| Coverage lost (base2_peak15 had, base1_peak5 doesn't) | 1 |
| Coverage gained (base1_peak5 has, base2_peak15 didn't) | 1 |
| Neither has position | 15 |

### Position accuracy (where both have data)
- Mean distance: 0.0px
- Median distance: 0.0px
- Max distance: 0.0px
- Within 5px: 10/10
- Within 20px: 10/10
- Within 50px: 10/10

### Events that lost cursor coverage

| Time (ms) | Type | Description | base2_peak15 pos |
|----------:|------|-------------|-----------|
| 206388 | hover | Cursor hovers over the hotel card for 'The Drey - Kensington, Earl's Court'. | (624,343) |

### All cursor position comparisons

| Time (ms) | Type | base2_peak15 pos | base1_peak5 pos | Distance (px) |
|----------:|------|-----------|----------|-------------:|
| 76670 | hover | (603,853) | (603,853) | 0.0 |
| 119911 | click | (1403,574) | (1403,574) | 0.0 |
| 203488 | hover | (624,560) | (624,560) | 0.0 |
| 241014 | click | (680,324) | (680,324) | 0.0 |
| 246853 | hover | (680,248) | (680,248) | 0.0 |
| 247314 | select | (680,248) | (680,248) | 0.0 |
| 248138 | click | (624,698) | (624,698) | 0.0 |
| 271014 | drag | (680,862) | (680,862) | 0.0 |
| 288714 | click | (323,925) | (323,925) | 0.0 |
| 385258 | hover | (860,408) | (860,408) | 0.0 |

## 7. Conclusion

- **Processing speedup**: 41% faster cursor tracking
- **Summary fidelity**: 0/5 segments produced identical Gemini prompts
- **Coverage impact**: 1 events lost cursor position data
- **Position accuracy**: Mean 0.0px drift where both have data
