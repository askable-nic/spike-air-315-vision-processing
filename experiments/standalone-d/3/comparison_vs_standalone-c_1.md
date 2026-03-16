# Cursor Experiment Comparison: standalone-c_1 vs standalone-d_3

## 1. Trajectory Comparison (aggregate)

| Session | standalone-c_1 det | standalone-d_3 det | Common | Identical | Both det | Disagree | Mean drift | Max drift |
|---------|---:|---:|---:|---:|---:|---:|---:|---:|
| ask_create_study_brandon | 38 | 63 | 218 | 214 | 16 | 4 | 0.0 | 0.0 |
| ask_results_usability_brandon | 73 | 72 | 290 | 283 | 16 | 7 | 0.0 | 0.0 |
| cfs_home_loan_sasha | 1247 | 1366 | 829 | 696 | 664 | 32 | 115.9 | 1759.5 |
| cfs_home_loan_serene | 684 | 766 | 358 | 243 | 238 | 88 | 119.6 | 2165.5 |
| flight_centre_booking_james | 189 | 209 | 65 | 35 | 22 | 29 | 31.4 | 690.1 |
| flight_centre_booking_kay | 829 | 966 | 417 | 342 | 299 | 45 | 91.4 | 1643.0 |
| opportunity_list_ben | 1269 | 1364 | 502 | 368 | 363 | 58 | 145.6 | 1823.7 |
| opportunity_list_georgie | 2463 | 2665 | 1322 | 936 | 972 | 181 | 121.2 | 2017.9 |
| travel_expert_lisa | 991 | 1033 | 904 | 803 | 502 | 60 | 46.7 | 1580.1 |
| travel_expert_veronika | 813 | 731 | 561 | 394 | 388 | 98 | 97.5 | 1581.9 |
| travel_expert_william | 579 | 562 | 704 | 587 | 444 | 47 | 103.0 | 1533.1 |
| travel_learner_sophia_jayde | 551 | 559 | 1765 | 1679 | 213 | 71 | 63.7 | 1934.3 |
| **TOTAL** | **9726** | **10356** | — | **6580** | **4137** | — | **102.7** | **2165.5** |

### Position accuracy (where both detected)
- Samples: 4137
- Identical (0px): 3502
- Within 1px: 3525
- Within 5px: 3535
- Median: 0.0px
- Mean: 102.7px
- Max: 2165.5px

## 2. Cursor Summary Diffs (per segment)

Identical: 22/107 segments
Changed: 85/107 segments

### ask_create_study_brandon / segment_001
- standalone-c_1: 4 lines, standalone-d_3: 4 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,4 +1,4 @@
-38105-38772ms: stationary pos=(1651,76)

-39005-39605ms: moved from (80,537) to (80,585)

-39805-40038ms: moved from (80,537) to (80,617)

-52605-54538ms: stationary pos=(1651,74)
+38205-38805ms: stationary pos=(1651,76)

+39038-39505ms: moved from (80,537) to (80,617)

+39705-40105ms: moved from (80,537) to (80,617)

+52872-54538ms: stationary pos=(1651,74)
```

### ask_create_study_brandon / segment_002
- standalone-c_1: 0 lines, standalone-d_3: 2 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -0,0 +1,2 @@
+32444-34111ms: stationary pos=(1651,74)

+66344-68044ms: stationary pos=(1651,76)
```

### ask_create_study_brandon / segment_004
- standalone-c_1: 1 lines, standalone-d_3: 1 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_3)
@@ -1 +1 @@
-80922-82922ms: stationary pos=(1651,76)
+81088-82722ms: stationary pos=(1651,76)
```

### ask_create_study_brandon / segment_005
- standalone-c_1: 1 lines, standalone-d_3: 4 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_3)
@@ -1 +1,4 @@
-7027-9027ms: stationary pos=(1651,76)
+7194-8827ms: stationary pos=(1651,76)

+55861-56694ms: stationary pos=(1651,74)

+56894-57094ms: stationary pos=(382,936)

+57327-57527ms: stationary pos=(1651,74)
```

### ask_results_usability_brandon / segment_000
- standalone-c_1: 4 lines, standalone-d_3: 8 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -1,4 +1,8 @@
-1000-3000ms: stationary pos=(708,12)

-7200-7433ms: moved from (1683,706) to (1391,65)

-8000-9000ms: stationary pos=(414,14)

-9500-10900ms: stationary pos=(1391,65)
+666-2333ms: stationary pos=(708,12)

+2566-2566ms: stationary pos=(1389,65)

+6100-6266ms: moved from (710,14) to (57,1080)

+6466-6666ms: moved from (1568,215) to (1406,215)

+6899-7100ms: moved from (1650,76) to (1458,424)

+7300-7500ms: moved from (1650,76) to (10,808)

+7766-9166ms: stationary pos=(414,14)

+9333-10600ms: stationary pos=(1391,65)
```

### ask_results_usability_brandon / segment_001
- standalone-c_1: 0 lines, standalone-d_3: 1 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -0,0 +1 @@
+10544-12177ms: stationary pos=(1391,65)
```

### ask_results_usability_brandon / segment_002
- standalone-c_1: 3 lines, standalone-d_3: 1 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -1,3 +1 @@
-45555-46155ms: stationary pos=(1391,65)

-46355-46755ms: moved from (319,513) to (1391,65)

-46955-47555ms: stationary pos=(946,1107)
+48322-49955ms: stationary pos=(1391,65)
```

### ask_results_usability_brandon / segment_003
- standalone-c_1: 2 lines, standalone-d_3: 1 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_3)
@@ -1,2 +1 @@
-58833-60833ms: stationary pos=(1391,65)

-70333-72333ms: stationary pos=(1391,65)
+59000-60633ms: stationary pos=(1391,65)
```

### ask_results_usability_brandon / segment_004
- standalone-c_1: 3 lines, standalone-d_3: 3 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_3)
@@ -1,3 +1,3 @@
-32111-34111ms: stationary pos=(1391,65)

-39611-41011ms: stationary pos=(1391,65)

-41211-41611ms: moved from (612,651) to (1391,65)
+32444-34111ms: stationary pos=(1391,65)

+39777-41011ms: stationary pos=(1391,65)

+41211-41411ms: moved from (612,651) to (1391,65)
```

### cfs_home_loan_sasha / segment_000
- standalone-c_1: 23 lines, standalone-d_3: 30 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -1,23 +1,30 @@
-1000-3800ms: stationary pos=(1055,381)

-4000-4600ms: stationary pos=(148,148)

-4800-5000ms: moved from (20,981) to (148,148)

-5200-5600ms: moved from (1166,503) to (148,148)

-5800-6000ms: moved from (20,88) to (148,148)

-6200-6600ms: stationary pos=(20,76)

-6800-7000ms: moved from (16,556) to (148,148)

-7200-11000ms: moved from (16,556) to (16,518)

-11500-12100ms: stationary pos=(987,837)

-12300-12900ms: stationary pos=(1143,398)

-28000-28833ms: stationary pos=(1881,1066)

-29033-29466ms: stationary pos=(955,612)

-36500-37900ms: stationary pos=(955,612)

-45000-45400ms: stationary pos=(955,612)
... (73 more lines)
```

### cfs_home_loan_sasha / segment_001
- standalone-c_1: 25 lines, standalone-d_3: 29 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,25 +1,29 @@
-12275-12675ms: stationary pos=(691,146)

+12041-12675ms: stationary pos=(691,146)

 12875-13075ms: moved from (1616,37) to (950,674)

 13275-13475ms: moved from (1024,513) to (1618,37)

 13675-13675ms: stationary pos=(619,603)

-57275-57475ms: moved from (762,999) to (897,200)

-57708-57941ms: moved from (762,999) to (397,825)

-58174-58575ms: stationary pos=(1660,776)

-58775-59208ms: moved from (1722,584) to (1072,216)

-59441-59674ms: moved from (1720,712) to (1072,216)

-59875-60075ms: moved from (1624,919) to (1072,216)

-60275-60275ms: stationary pos=(1722,879)

-64075-64508ms: stationary pos=(1618,37)

-64708-66775ms: moved from (864,140) to (313,54)
... (67 more lines)
```

### cfs_home_loan_sasha / segment_002
- standalone-c_1: 30 lines, standalone-d_3: 45 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -1,30 +1,45 @@
-150-550ms: moved from (222,341) to (971,253)

-1050-1850ms: stationary pos=(198,327)

+50-450ms: moved from (222,341) to (971,253)

+716-1850ms: stationary pos=(198,327)

 2050-2250ms: moved from (491,437) to (555,1031)

 2450-3450ms: moved from (251,784) to (377,126)

 3650-4250ms: moved from (1886,135) to (1889,234)

-4450-5050ms: stationary pos=(1888,135)

-5550-6150ms: stationary pos=(1670,105)

-6350-9350ms: moved from (1670,101) to (739,650)

-16550-17950ms: moved from (1209,603) to (1669,51)

-18550-20450ms: stationary pos=(728,791)

-43050-43250ms: stationary pos=(739,911)

-53550-53950ms: stationary pos=(869,453)
... (112 more lines)
```

### cfs_home_loan_sasha / segment_003
- standalone-c_1: 88 lines, standalone-d_3: 85 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_3)
@@ -1,31 +1,31 @@
-325-725ms: stationary pos=(1881,185)

-925-1325ms: stationary pos=(1678,123)

-1525-2325ms: stationary pos=(604,823)

-2825-5325ms: stationary pos=(662,319)

-5825-6225ms: stationary pos=(604,823)

+158-791ms: moved from (1884,202) to (1881,185)

+991-1425ms: moved from (887,970) to (1678,123)

+1625-6191ms: stationary pos=(604,823)

 6425-8358ms: moved from (604,556) to (604,300)

-8591-8991ms: stationary pos=(568,273)

-9191-9425ms: moved from (1744,498) to (1198,529)

+8591-9025ms: stationary pos=(568,273)

+9225-9425ms: moved from (1881,874) to (1198,529)

 9658-10091ms: stationary pos=(931,1060)
... (170 more lines)
```

### cfs_home_loan_sasha / segment_004
- standalone-c_1: 102 lines, standalone-d_3: 106 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_3)
@@ -16,15 +16,15 @@
 7800-8800ms: moved from (449,204) to (1887,122)

 9000-9400ms: moved from (16,170) to (463,797)

 9600-9800ms: stationary pos=(1887,122)

-10000-11800ms: stationary pos=(1895,987)

-12000-12200ms: moved from (1704,712) to (704,361)

-12400-12800ms: moved from (224,682) to (524,1041)

-13000-13200ms: moved from (273,1047) to (656,564)

-13400-13600ms: stationary pos=(1443,383)

-13800-14400ms: moved from (1443,469) to (1443,513)

-14600-14800ms: moved from (524,999) to (993,196)

-15000-15200ms: moved from (991,265) to (991,251)

-15400-15600ms: moved from (273,242) to (509,325)

+10000-11000ms: stationary pos=(1895,987)

+11266-11833ms: moved from (991,182) to (1895,987)
... (144 more lines)
```

### cfs_home_loan_sasha / segment_005
- standalone-c_1: 113 lines, standalone-d_3: 115 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_3)
@@ -1,8 +1,9 @@
 175-375ms: moved from (1232,855) to (164,536)

 575-975ms: stationary pos=(166,570)

 1175-1575ms: moved from (1096,784) to (166,503)

-1775-2375ms: moved from (1096,784) to (166,503)

-2575-2975ms: moved from (1096,784) to (560,1027)

+1775-2175ms: moved from (1096,784) to (560,1027)

+2375-2575ms: moved from (166,503) to (1096,784)

+2775-2975ms: stationary pos=(560,1027)

 3175-3375ms: stationary pos=(784,281)

 3575-4175ms: stationary pos=(780,265)

 4375-4575ms: stationary pos=(618,977)

@@ -17,7 +18,8 @@
 8975-9175ms: stationary pos=(855,1047)

 9375-9775ms: moved from (1882,1061) to (495,459)

... (301 more lines)
```

### cfs_home_loan_sasha / segment_006
- standalone-c_1: 27 lines, standalone-d_3: 30 lines
```diff
--- segment_006 (standalone-c_1)
+++ segment_006 (standalone-d_3)
@@ -2,26 +2,29 @@
 550-750ms: moved from (291,809) to (720,391)

 950-1150ms: moved from (1497,899) to (1664,136)

 1350-1550ms: moved from (1656,134) to (1784,232)

-1750-3616ms: moved from (301,160) to (97,1002)

-3816-4016ms: stationary pos=(97,1049)

-4216-4450ms: moved from (993,971) to (97,1049)

-4650-5550ms: stationary pos=(875,929)

-5783-6616ms: stationary pos=(341,598)

-6816-7016ms: stationary pos=(1497,640)

-7216-8050ms: stationary pos=(50,887)

-8283-8483ms: stationary pos=(50,997)

-9150-9550ms: stationary pos=(50,887)

-9783-11216ms: moved from (957,554) to (957,528)

-11450-11850ms: moved from (1465,584) to (863,55)
... (73 more lines)
```

### cfs_home_loan_sasha / segment_007
- standalone-c_1: 23 lines, standalone-d_3: 31 lines
```diff
--- segment_007 (standalone-c_1)
+++ segment_007 (standalone-d_3)
@@ -1,23 +1,31 @@
-9425-9625ms: stationary pos=(1084,840)

-9825-10058ms: stationary pos=(1084,843)

-10258-10891ms: moved from (1536,585) to (823,330)

-11425-11925ms: stationary pos=(787,339)

-12425-13058ms: stationary pos=(1351,439)

-13258-13458ms: stationary pos=(780,535)

-13658-13891ms: moved from (95,420) to (32,730)

-14091-14925ms: moved from (212,903) to (208,889)

-15425-16425ms: moved from (200,895) to (212,903)

-16625-17258ms: moved from (200,905) to (212,903)

-17458-18725ms: moved from (80,1037) to (200,905)

-18925-19325ms: moved from (200,216) to (313,56)

-19558-20925ms: moved from (807,405) to (807,383)

-21425-24758ms: stationary pos=(313,56)
... (79 more lines)
```

### cfs_home_loan_serene / segment_000
- standalone-c_1: 47 lines, standalone-d_3: 50 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -1,47 +1,50 @@
 400-600ms: moved from (893,1627) to (90,1664)

-800-2700ms: moved from (898,1071) to (898,1070)

-2900-3100ms: stationary pos=(898,1071)

-3300-3733ms: moved from (898,1008) to (282,66)

-3966-4400ms: stationary pos=(894,1248)

+800-2766ms: moved from (898,1071) to (898,1070)

+2966-3200ms: stationary pos=(898,1071)

+3400-3600ms: stationary pos=(282,66)

+3800-4400ms: moved from (710,1004) to (894,1248)

 4600-4600ms: stationary pos=(894,1354)

-15866-18000ms: moved from (576,718) to (319,53)

-23700-24300ms: moved from (686,1632) to (733,1507)

-24500-24500ms: stationary pos=(686,1632)

-28133-28333ms: moved from (733,1844) to (863,313)
... (147 more lines)
```

### cfs_home_loan_serene / segment_001
- standalone-c_1: 44 lines, standalone-d_3: 51 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,18 +1,18 @@
-16-250ms: stationary pos=(164,1393)

-483-2216ms: stationary pos=(620,1754)

+216-2216ms: moved from (164,1393) to (620,1754)

 2416-2816ms: moved from (192,1950) to (72,2034)

 3016-3250ms: stationary pos=(72,2032)

-3483-3916ms: moved from (70,2076) to (72,2059)

-4516-6016ms: stationary pos=(612,1744)

-6516-7916ms: moved from (498,1927) to (612,1744)

-8116-9416ms: moved from (879,2089) to (463,854)

-10016-11116ms: stationary pos=(733,1507)

+3483-4550ms: moved from (70,2076) to (72,2051)

+4750-6016ms: stationary pos=(612,1744)

+6350-7050ms: stationary pos=(498,1927)

+7250-7916ms: stationary pos=(612,1744)
... (120 more lines)
```

### cfs_home_loan_serene / segment_002
- standalone-c_1: 53 lines, standalone-d_3: 59 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -1,18 +1,23 @@
-3466-3700ms: moved from (781,1944) to (856,1995)

-3933-5433ms: stationary pos=(31,75)

-6033-6533ms: stationary pos=(402,492)

-7033-8200ms: moved from (401,490) to (211,199)

-8433-10533ms: moved from (211,294) to (211,199)

-10733-11633ms: moved from (35,835) to (211,199)

-11833-12933ms: moved from (302,1169) to (211,199)

-13133-14000ms: moved from (35,863) to (35,902)

-14233-14633ms: stationary pos=(427,321)

-14833-15066ms: moved from (19,1770) to (19,1782)

-15300-15500ms: moved from (952,818) to (27,1106)

-16033-18033ms: stationary pos=(199,50)

-18533-20533ms: stationary pos=(319,53)

-21033-21033ms: stationary pos=(575,1796)
... (136 more lines)
```

### cfs_home_loan_serene / segment_003
- standalone-c_1: 44 lines, standalone-d_3: 47 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_3)
@@ -1,44 +1,47 @@
 150-350ms: moved from (38,462) to (325,1483)

-550-1550ms: moved from (42,435) to (765,196)

-7050-9550ms: stationary pos=(765,196)

-10050-10850ms: stationary pos=(903,1029)

-11050-11250ms: stationary pos=(899,177)

-11450-13450ms: moved from (687,1467) to (899,177)

-14050-14850ms: stationary pos=(319,53)

-15050-16850ms: stationary pos=(711,835)

-20850-21050ms: moved from (79,945) to (319,53)

-21250-21450ms: stationary pos=(947,53)

-22050-23550ms: stationary pos=(890,1884)

-24050-24450ms: moved from (267,1870) to (263,1863)

-24650-26450ms: moved from (173,1848) to (730,413)

-27050-28050ms: stationary pos=(70,1526)
... (147 more lines)
```

### flight_centre_booking_james / segment_000
- standalone-c_1: 11 lines, standalone-d_3: 14 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -1,11 +1,14 @@
 0-2100ms: moved from (144,17) to (980,712)

-10000-12000ms: stationary pos=(500,31)

-12500-15966ms: moved from (1636,21) to (500,31)

-16500-17100ms: stationary pos=(646,580)

-30500-31966ms: stationary pos=(500,29)

-32500-33100ms: stationary pos=(560,606)

-37000-39600ms: stationary pos=(1246,29)

-39800-40800ms: stationary pos=(1935,1001)

-41000-41400ms: moved from (1048,29) to (734,504)

-42000-43000ms: stationary pos=(1414,21)

-43500-45500ms: stationary pos=(1048,29)
+2300-4433ms: stationary pos=(1636,21)

+4600-5600ms: stationary pos=(280,647)

+5800-6200ms: stationary pos=(1303,376)

... (19 more lines)
```

### flight_centre_booking_james / segment_001
- standalone-c_1: 10 lines, standalone-d_3: 12 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,10 +1,12 @@
-16544-17344ms: stationary pos=(23,569)

-17544-17944ms: stationary pos=(1048,29)

-18544-19044ms: stationary pos=(557,514)

-19544-19744ms: moved from (1048,29) to (47,168)

-19944-21344ms: stationary pos=(1048,29)

-21544-24544ms: moved from (557,31) to (1327,21)

-25044-25644ms: moved from (871,1016) to (1399,1032)

-25844-27044ms: stationary pos=(221,29)

-27544-28144ms: stationary pos=(901,303)

-56044-57977ms: stationary pos=(439,29)
+11-11ms: stationary pos=(1048,29)

+16811-17444ms: stationary pos=(23,569)

+17644-19044ms: stationary pos=(1048,29)

+19311-19644ms: stationary pos=(558,515)

... (15 more lines)
```

### flight_centre_booking_james / segment_002
- standalone-c_1: 8 lines, standalone-d_3: 9 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -1,8 +1,9 @@
-20089-21489ms: stationary pos=(1160,808)

-22089-22589ms: stationary pos=(1361,478)

-23089-23889ms: stationary pos=(1160,808)

-24089-24489ms: moved from (439,29) to (547,29)

-31089-33089ms: stationary pos=(547,29)

-47089-48889ms: stationary pos=(765,29)

-52789-52989ms: stationary pos=(512,410)

-53189-53989ms: stationary pos=(439,29)
+3189-4689ms: stationary pos=(439,29)

+20089-21289ms: stationary pos=(1160,808)

+21622-23355ms: stationary pos=(1361,478)

+23522-23955ms: stationary pos=(1160,808)

+24189-24789ms: stationary pos=(547,29)

+47422-48889ms: stationary pos=(765,29)

+49089-51889ms: stationary pos=(221,29)

+52089-52422ms: stationary pos=(1245,594)

+52622-53889ms: moved from (221,29) to (439,29)
```

### flight_centre_booking_kay / segment_000
- standalone-c_1: 54 lines, standalone-d_3: 60 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -1,54 +1,60 @@
-200-600ms: moved from (209,248) to (1706,366)

-800-1000ms: moved from (48,360) to (147,255)

-1200-1400ms: moved from (209,215) to (139,215)

-1600-1800ms: moved from (64,408) to (17,618)

+166-366ms: moved from (209,248) to (1706,366)

+566-966ms: stationary pos=(1937,375)

+1166-1366ms: moved from (143,521) to (139,215)

+1566-1800ms: moved from (64,408) to (17,618)

 2000-2200ms: moved from (1956,525) to (552,619)

 2400-2800ms: moved from (1377,25) to (29,248)

-3000-3800ms: moved from (480,1017) to (1935,457)

-4000-8300ms: moved from (1935,521) to (1935,904)

-8500-8700ms: moved from (790,585) to (209,935)

-8900-9300ms: moved from (352,991) to (209,931)
... (175 more lines)
```

### flight_centre_booking_kay / segment_001
- standalone-c_1: 43 lines, standalone-d_3: 47 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,43 +1,47 @@
-261-961ms: stationary pos=(870,1031)

-1161-1761ms: stationary pos=(1927,84)

-2261-4394ms: stationary pos=(1416,952)

-4594-4794ms: stationary pos=(228,304)

-4994-5194ms: stationary pos=(1153,857)

-5427-5661ms: moved from (1070,869) to (225,398)

-5861-6061ms: moved from (228,304) to (1493,590)

-9761-9961ms: stationary pos=(1288,840)

-10161-10361ms: moved from (403,360) to (536,319)

-10561-10761ms: moved from (1416,439) to (17,1001)

-10961-11161ms: moved from (1416,439) to (1235,745)

-11361-11561ms: moved from (1929,920) to (1970,904)

-11761-11961ms: moved from (1638,935) to (1203,745)

-12161-13261ms: moved from (147,457) to (228,304)
... (149 more lines)
```

### flight_centre_booking_kay / segment_002
- standalone-c_1: 39 lines, standalone-d_3: 57 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -1,39 +1,57 @@
-5522-6022ms: stationary pos=(1122,303)

-6522-6922ms: stationary pos=(1129,968)

-7122-7322ms: moved from (1325,503) to (1129,968)

-7522-7722ms: moved from (1385,968) to (1129,968)

-7922-8122ms: moved from (697,585) to (1385,968)

-8322-8522ms: stationary pos=(1129,968)

-14522-15122ms: stationary pos=(432,747)

-15322-15522ms: stationary pos=(1236,802)

-15722-16922ms: moved from (1013,1027) to (1592,907)

-28522-29922ms: stationary pos=(1667,945)

-36522-39122ms: stationary pos=(1667,945)

+122-522ms: stationary pos=(918,34)

+788-1622ms: stationary pos=(599,948)

+1822-2022ms: moved from (263,834) to (1122,303)
... (127 more lines)
```

### flight_centre_booking_kay / segment_003
- standalone-c_1: 28 lines, standalone-d_3: 29 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_3)
@@ -1,28 +1,29 @@
-283-683ms: stationary pos=(75,879)

+83-683ms: stationary pos=(75,879)

 883-1083ms: moved from (1958,840) to (1832,552)

 1283-2083ms: moved from (1919,439) to (1832,426)

 2283-2483ms: moved from (1490,1018) to (627,678)

 2683-2883ms: stationary pos=(958,334)

 3083-3283ms: moved from (1832,666) to (77,114)

 3483-3683ms: stationary pos=(178,416)

-4283-5783ms: stationary pos=(618,714)

-6283-6483ms: moved from (1096,306) to (120,922)

-6683-7683ms: moved from (1096,306) to (120,922)

-13783-15650ms: stationary pos=(918,34)

-16283-18283ms: stationary pos=(1593,656)

-18783-19616ms: stationary pos=(1079,835)
... (73 more lines)
```

### flight_centre_booking_kay / segment_004
- standalone-c_1: 41 lines, standalone-d_3: 59 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_3)
@@ -1,12 +1,24 @@
-6044-6844ms: stationary pos=(656,695)

-7044-7444ms: moved from (1824,585) to (1553,693)

-7644-10044ms: moved from (1553,676) to (1461,303)

-10544-10744ms: moved from (1553,664) to (1962,197)

-10944-13144ms: moved from (1553,664) to (77,114)

-13344-14144ms: moved from (1299,871) to (1295,408)

-14344-14744ms: stationary pos=(1390,842)

-14944-17544ms: stationary pos=(1299,726)

-18044-19344ms: moved from (1347,625) to (1299,726)

+6377-6777ms: stationary pos=(656,695)

+7011-7211ms: stationary pos=(958,336)

+7411-7611ms: stationary pos=(1553,693)

+7844-8044ms: stationary pos=(1553,664)

+8211-10211ms: stationary pos=(1461,303)
... (106 more lines)
```

### flight_centre_booking_kay / segment_005
- standalone-c_1: 35 lines, standalone-d_3: 37 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_3)
@@ -1,35 +1,37 @@
-1805-2305ms: stationary pos=(481,762)

+139-1372ms: stationary pos=(1815,465)

+1639-2639ms: stationary pos=(481,762)

 2805-3805ms: stationary pos=(1815,465)

 4005-4205ms: moved from (1073,753) to (77,114)

 4405-4605ms: stationary pos=(184,342)

-4805-5205ms: moved from (184,344) to (77,114)

-17805-18005ms: moved from (794,858) to (883,875)

-18205-18605ms: moved from (881,863) to (736,347)

-18805-19005ms: moved from (868,925) to (1222,698)

-19205-19605ms: moved from (868,607) to (897,744)

-19805-19805ms: stationary pos=(1224,702)

-26305-27305ms: stationary pos=(701,478)

+4805-5005ms: moved from (184,344) to (77,114)
... (99 more lines)
```

### opportunity_list_ben / segment_000
- standalone-c_1: 27 lines, standalone-d_3: 25 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -1,27 +1,25 @@
-500-2000ms: stationary pos=(1185,888)

-2500-2500ms: stationary pos=(1182,890)

-6500-7399ms: stationary pos=(1179,896)

-7600-8000ms: stationary pos=(1261,836)

-27200-27633ms: stationary pos=(1251,850)

-27833-31000ms: moved from (1251,820) to (1254,808)

-48300-48900ms: stationary pos=(1290,818)

-49100-49500ms: stationary pos=(861,426)

-54500-54966ms: stationary pos=(1353,995)

+666-2700ms: stationary pos=(1185,888)

+6933-7399ms: stationary pos=(1179,896)

+7600-8200ms: stationary pos=(1261,836)

+16733-16733ms: stationary pos=(1262,834)

+27400-27733ms: moved from (1250,848) to (1250,828)
... (63 more lines)
```

### opportunity_list_ben / segment_001
- standalone-c_1: 82 lines, standalone-d_3: 80 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,82 +1,80 @@
-4-204ms: moved from (502,1065) to (1185,417)

-804-2304ms: stationary pos=(1837,81)

-2804-3438ms: moved from (1535,1019) to (1012,135)

+38-271ms: stationary pos=(1185,417)

+504-2971ms: stationary pos=(1837,81)

+3204-3438ms: stationary pos=(1012,135)

 3638-4038ms: moved from (1288,194) to (888,645)

 4238-4471ms: moved from (727,939) to (801,939)

-4704-6504ms: stationary pos=(1140,551)

-6704-8704ms: stationary pos=(1176,772)

-8904-9104ms: moved from (778,1036) to (1102,341)

-9304-9504ms: moved from (878,335) to (951,814)

-9704-9904ms: stationary pos=(1835,81)

-10104-10904ms: moved from (847,524) to (939,738)
... (281 more lines)
```

### opportunity_list_ben / segment_002
- standalone-c_1: 58 lines, standalone-d_3: 60 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -1,58 +1,60 @@
-42-276ms: moved from (630,640) to (153,10)

-509-709ms: moved from (494,482) to (854,585)

-909-1142ms: moved from (838,598) to (494,482)

-1376-2642ms: moved from (854,585) to (1104,646)

-2876-3076ms: moved from (1201,169) to (854,585)

-3309-3709ms: stationary pos=(1104,646)

-3909-4109ms: moved from (854,585) to (1104,646)

-4309-4709ms: moved from (854,585) to (1104,646)

-4909-5509ms: moved from (854,585) to (1104,646)

-5709-8109ms: stationary pos=(494,482)

-8609-9009ms: moved from (834,616) to (494,482)

-9209-9409ms: moved from (834,616) to (494,482)

-9609-10009ms: moved from (1271,151) to (175,768)

-10209-11009ms: stationary pos=(34,443)
... (197 more lines)
```

### opportunity_list_ben / segment_003
- standalone-c_1: 51 lines, standalone-d_3: 54 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_3)
@@ -1,51 +1,54 @@
-414-1214ms: stationary pos=(287,1068)

-1414-1814ms: stationary pos=(1155,553)

-2014-2614ms: stationary pos=(1678,297)

-2814-5214ms: stationary pos=(1561,153)

-5414-5614ms: moved from (1399,329) to (1856,800)

-5814-5814ms: stationary pos=(1720,327)

-10414-11414ms: stationary pos=(1193,866)

-20414-21014ms: stationary pos=(732,345)

+680-1280ms: stationary pos=(287,1068)

+1514-2714ms: stationary pos=(1678,297)

+2914-5314ms: stationary pos=(1561,153)

+5514-5514ms: stationary pos=(1399,329)

+10314-11314ms: moved from (1193,824) to (1193,866)

+20380-21014ms: stationary pos=(732,345)
... (179 more lines)
```

### opportunity_list_ben / segment_004
- standalone-c_1: 52 lines, standalone-d_3: 52 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_3)
@@ -1,52 +1,52 @@
-219-652ms: stationary pos=(1266,616)

-885-1085ms: stationary pos=(862,585)

-1319-1552ms: stationary pos=(1266,598)

-1752-1952ms: moved from (862,585) to (169,441)

-2152-2385ms: moved from (1266,598) to (862,585)

-2585-2785ms: moved from (862,600) to (862,585)

-3019-3819ms: stationary pos=(1266,598)

-4019-4219ms: stationary pos=(111,920)

-4719-6219ms: stationary pos=(142,197)

-6719-7319ms: moved from (838,585) to (1266,598)

-7519-8119ms: moved from (233,153) to (1082,441)

-14719-15319ms: stationary pos=(185,816)

+85-752ms: moved from (581,622) to (1793,34)

+952-1152ms: moved from (148,239) to (801,484)
... (163 more lines)
```

### opportunity_list_ben / segment_005
- standalone-c_1: 38 lines, standalone-d_3: 51 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_3)
@@ -1,38 +1,51 @@
-523-1523ms: stationary pos=(360,1043)

-2023-4623ms: moved from (702,199) to (1485,1070)

-4823-5223ms: stationary pos=(1064,409)

-5423-5823ms: stationary pos=(1485,1070)

-6023-6223ms: stationary pos=(604,251)

-6423-9023ms: stationary pos=(1183,281)

-9523-10623ms: stationary pos=(618,211)

+23-190ms: moved from (409,1040) to (360,1043)

+357-2023ms: stationary pos=(409,1040)

+2190-3523ms: stationary pos=(360,1043)

+3690-5523ms: stationary pos=(409,1040)

+5723-6123ms: stationary pos=(569,110)

+6323-6723ms: moved from (775,887) to (1837,80)

+6923-7123ms: moved from (1070,843) to (1837,80)
... (131 more lines)
```

### opportunity_list_ben / segment_006
- standalone-c_1: 39 lines, standalone-d_3: 45 lines
```diff
--- segment_006 (standalone-c_1)
+++ segment_006 (standalone-d_3)
@@ -1,39 +1,45 @@
-28-228ms: moved from (633,915) to (1837,80)

-428-1228ms: stationary pos=(407,1037)

-1828-5128ms: stationary pos=(940,513)

+195-395ms: moved from (1837,80) to (810,319)

+628-1028ms: stationary pos=(407,1037)

+4495-5128ms: stationary pos=(942,515)

 5328-6728ms: moved from (940,183) to (1000,471)

-7328-8328ms: stationary pos=(983,786)

-8828-9828ms: stationary pos=(1910,281)

+6928-7728ms: moved from (664,892) to (1082,379)

+7995-9828ms: moved from (983,786) to (1910,281)

 10028-11028ms: moved from (1469,1048) to (1910,281)

 11228-11828ms: stationary pos=(788,794)

-12328-12828ms: stationary pos=(983,786)
... (123 more lines)
```

### opportunity_list_georgie / segment_000
- standalone-c_1: 72 lines, standalone-d_3: 79 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -16,57 +16,64 @@
 9300-9500ms: moved from (1433,902) to (1812,84)

 9700-10100ms: stationary pos=(81,939)

 10300-10500ms: stationary pos=(1812,84)

-10700-10900ms: moved from (1830,733) to (1812,84)

-11100-11300ms: moved from (968,839) to (408,823)

-16000-16600ms: stationary pos=(350,695)

-22500-24000ms: stationary pos=(1812,84)

-24500-25300ms: stationary pos=(1145,322)

-25500-26133ms: moved from (1444,896) to (1145,322)

-26333-26966ms: moved from (1732,951) to (1145,322)

-27166-27366ms: moved from (1815,85) to (1145,322)

-27566-28000ms: moved from (1872,394) to (1107,774)

-28200-28833ms: stationary pos=(1815,85)

-29033-29233ms: stationary pos=(1255,930)
... (203 more lines)
```

### opportunity_list_georgie / segment_001
- standalone-c_1: 22 lines, standalone-d_3: 26 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,22 +1,26 @@
-3906-5906ms: stationary pos=(1103,545)

-6406-7206ms: stationary pos=(1204,1001)

-7406-7806ms: moved from (1073,313) to (1073,344)

-8006-8206ms: stationary pos=(1073,313)

-8406-8606ms: moved from (1343,603) to (469,713)

-8806-8806ms: stationary pos=(1343,605)

-14906-15506ms: stationary pos=(1300,815)

+6-206ms: moved from (1332,864) to (1876,935)

+406-606ms: moved from (997,282) to (1698,693)

+806-1006ms: moved from (1876,935) to (1698,693)

+1206-1406ms: moved from (1060,279) to (1698,693)

+1606-1806ms: moved from (981,374) to (217,854)

+2006-2206ms: moved from (1698,693) to (1186,379)

+2406-2606ms: moved from (1698,693) to (1876,935)
... (61 more lines)
```

### opportunity_list_georgie / segment_002
- standalone-c_1: 57 lines, standalone-d_3: 52 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -1,57 +1,52 @@
-6313-7113ms: stationary pos=(1795,698)

-7313-9313ms: stationary pos=(906,107)

-9513-10313ms: moved from (906,107) to (1844,104)

+6646-7080ms: stationary pos=(1795,698)

+7280-9513ms: stationary pos=(906,107)

+9713-10313ms: stationary pos=(1844,104)

 10513-10713ms: stationary pos=(1795,698)

 10913-11513ms: stationary pos=(1696,820)

-11713-11913ms: stationary pos=(1060,480)

-12113-13313ms: stationary pos=(1696,820)

-17813-18613ms: stationary pos=(1135,725)

-18813-19213ms: stationary pos=(31,23)

-26313-27713ms: stationary pos=(1795,698)

-34813-35413ms: stationary pos=(1113,439)
... (183 more lines)
```

### opportunity_list_georgie / segment_003
- standalone-c_1: 49 lines, standalone-d_3: 56 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_3)
@@ -1,49 +1,56 @@
-186-386ms: stationary pos=(1184,376)

-586-1253ms: moved from (1184,360) to (1184,374)

-1486-3186ms: stationary pos=(1721,103)

-3720-4220ms: stationary pos=(1104,322)

-4720-6820ms: stationary pos=(1844,107)

-7053-7686ms: stationary pos=(1872,759)

-8220-10586ms: moved from (1697,821) to (1854,700)

-15486-18186ms: stationary pos=(1894,954)

-23720-24320ms: moved from (1795,127) to (1698,818)

+53-886ms: stationary pos=(1184,376)

+1086-1320ms: moved from (1722,104) to (1184,380)

+1553-3253ms: stationary pos=(1721,103)

+3453-4820ms: stationary pos=(1104,322)

+5019-5820ms: stationary pos=(1844,107)
... (165 more lines)
```

### opportunity_list_georgie / segment_004
- standalone-c_1: 62 lines, standalone-d_3: 70 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_3)
@@ -1,17 +1,21 @@
-1226-1426ms: moved from (867,409) to (1071,457)

-1626-1826ms: moved from (798,376) to (1255,551)

-2026-2026ms: stationary pos=(748,394)

-21726-22326ms: stationary pos=(1060,222)

-22526-23126ms: stationary pos=(932,220)

-23626-24626ms: stationary pos=(1080,714)

-25126-25926ms: moved from (758,344) to (817,43)

-26126-26526ms: moved from (752,551) to (1073,445)

-26726-26926ms: moved from (1068,536) to (1073,445)

-27126-27326ms: moved from (1067,395) to (861,358)

-27526-29626ms: moved from (756,457) to (1047,701)

-30126-32126ms: stationary pos=(964,620)

-32626-33126ms: stationary pos=(1047,701)

-33626-34026ms: stationary pos=(746,335)
... (185 more lines)
```

### opportunity_list_georgie / segment_005
- standalone-c_1: 41 lines, standalone-d_3: 48 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_3)
@@ -1,41 +1,48 @@
-33-833ms: stationary pos=(897,394)

-1033-1433ms: stationary pos=(1161,387)

-2033-2833ms: moved from (1072,441) to (938,517)

-3033-3233ms: moved from (1017,492) to (936,691)

-3433-3633ms: moved from (936,845) to (879,488)

-3833-4033ms: moved from (1177,452) to (879,488)

-4233-4433ms: moved from (959,447) to (905,781)

-4633-4833ms: moved from (779,488) to (1165,488)

-5033-5233ms: stationary pos=(936,370)

-5433-7533ms: moved from (808,466) to (936,370)

+366-766ms: stationary pos=(897,394)

+1000-1600ms: stationary pos=(1161,387)

+1866-2033ms: stationary pos=(1072,441)

+2233-2633ms: stationary pos=(1072,444)
... (129 more lines)
```

### opportunity_list_georgie / segment_006
- standalone-c_1: 46 lines, standalone-d_3: 50 lines
```diff
--- segment_006 (standalone-c_1)
+++ segment_006 (standalone-d_3)
@@ -1,16 +1,18 @@
-440-2340ms: stationary pos=(1025,913)

-2573-2973ms: stationary pos=(743,955)

-3173-3406ms: stationary pos=(1024,910)

-3606-3606ms: stationary pos=(1192,789)

-9440-10273ms: stationary pos=(900,96)

-10473-10673ms: moved from (897,96) to (890,96)

-10906-11740ms: moved from (912,651) to (969,651)

-11940-12773ms: stationary pos=(883,363)

-12973-13173ms: moved from (881,363) to (967,454)

-13406-13806ms: stationary pos=(816,119)

-14440-15940ms: stationary pos=(789,488)

-16440-18940ms: stationary pos=(1060,995)

-19440-19940ms: stationary pos=(879,488)

+273-1606ms: stationary pos=(1025,913)
... (140 more lines)
```

### opportunity_list_georgie / segment_007
- standalone-c_1: 28 lines, standalone-d_3: 25 lines
```diff
--- segment_007 (standalone-c_1)
+++ segment_007 (standalone-d_3)
@@ -1,28 +1,25 @@
-4346-4746ms: stationary pos=(744,987)

-4980-5813ms: stationary pos=(1202,102)

-6346-6846ms: stationary pos=(921,772)

-7346-8580ms: stationary pos=(20,86)

-8813-12980ms: moved from (21,88) to (1017,666)

-13180-14046ms: stationary pos=(898,402)

-14279-15779ms: stationary pos=(1129,779)

-16346-17846ms: stationary pos=(1120,429)

-18346-23346ms: stationary pos=(1060,220)

-37346-38146ms: stationary pos=(1060,220)

-38346-39146ms: stationary pos=(932,220)

-39346-39746ms: stationary pos=(1060,220)

-45346-46146ms: stationary pos=(1159,779)

-46346-46546ms: moved from (812,767) to (906,402)
... (72 more lines)
```

### opportunity_list_georgie / segment_008
- standalone-c_1: 58 lines, standalone-d_3: 68 lines
```diff
--- segment_008 (standalone-c_1)
+++ segment_008 (standalone-d_3)
@@ -1,42 +1,53 @@
-53-653ms: stationary pos=(1060,220)

-6253-7253ms: stationary pos=(1182,784)

-7453-8253ms: stationary pos=(955,841)

+153-353ms: stationary pos=(1060,220)

+6586-7020ms: stationary pos=(1182,784)

+7220-8253ms: stationary pos=(955,841)

 8453-9053ms: stationary pos=(1105,737)

 9253-9453ms: stationary pos=(932,220)

 9653-9853ms: moved from (1042,536) to (750,295)

 10053-10453ms: stationary pos=(932,220)

-10653-11653ms: moved from (1060,218) to (932,220)

-12253-14253ms: stationary pos=(1007,693)

-14753-15353ms: moved from (1207,404) to (932,220)

-15553-16553ms: stationary pos=(1060,220)
... (138 more lines)
```

### opportunity_list_georgie / segment_009
- standalone-c_1: 57 lines, standalone-d_3: 71 lines
```diff
--- segment_009 (standalone-c_1)
+++ segment_009 (standalone-d_3)
@@ -1,14 +1,13 @@
 160-360ms: moved from (964,634) to (1064,426)

 560-2360ms: moved from (1072,692) to (930,698)

 2560-2760ms: moved from (1161,394) to (930,698)

-2960-3160ms: moved from (979,377) to (930,698)

-3660-5560ms: stationary pos=(871,573)

-14160-15660ms: stationary pos=(944,533)

-16160-16960ms: stationary pos=(1072,863)

-17160-17560ms: stationary pos=(940,527)

-18160-20060ms: moved from (887,677) to (940,527)

-20660-21160ms: stationary pos=(1167,338)

-21660-22060ms: stationary pos=(1099,336)

+3060-5660ms: stationary pos=(871,573)

+10060-10260ms: moved from (865,364) to (755,395)

+10460-10460ms: stationary pos=(1207,344)
... (145 more lines)
```

### opportunity_list_georgie / segment_010
- standalone-c_1: 57 lines, standalone-d_3: 63 lines
```diff
--- segment_010 (standalone-c_1)
+++ segment_010 (standalone-d_3)
@@ -12,46 +12,52 @@
 5866-6866ms: moved from (1092,515) to (1086,515)

 7066-7466ms: moved from (1186,251) to (1086,515)

 7666-8466ms: stationary pos=(20,89)

-19566-21566ms: stationary pos=(750,472)

-39066-39866ms: stationary pos=(1205,587)

+8666-9466ms: moved from (967,570) to (20,89)

+15300-15766ms: moved from (1255,518) to (1202,650)

+15966-16166ms: stationary pos=(1255,504)

+16366-16966ms: stationary pos=(750,472)

+17266-19400ms: stationary pos=(1024,910)

+19633-21266ms: stationary pos=(750,472)

+39266-39866ms: stationary pos=(1205,587)

 40066-40266ms: moved from (1255,632) to (1255,616)

-40466-42066ms: stationary pos=(748,248)
... (149 more lines)
```

### opportunity_list_georgie / segment_011
- standalone-c_1: 45 lines, standalone-d_3: 43 lines
```diff
--- segment_011 (standalone-c_1)
+++ segment_011 (standalone-d_3)
@@ -1,45 +1,43 @@
-73-273ms: moved from (1255,488) to (1024,407)

-473-673ms: stationary pos=(1255,488)

-873-2073ms: moved from (1255,616) to (1255,488)

-2273-3273ms: moved from (1255,616) to (1255,614)

-3473-3673ms: moved from (1255,616) to (1255,488)

-3873-4073ms: moved from (1255,616) to (1255,488)

-4273-4673ms: moved from (1255,616) to (1255,488)

-4873-6073ms: moved from (1255,616) to (1255,488)

-6273-6673ms: moved from (1178,599) to (1178,593)

-6873-7073ms: moved from (1109,608) to (1178,634)

-7273-7473ms: moved from (1178,654) to (949,841)

-7673-8073ms: moved from (1178,841) to (1178,892)

-8273-8473ms: moved from (752,246) to (1255,553)

-8673-8873ms: moved from (1111,530) to (1253,504)
... (135 more lines)
```

### opportunity_list_georgie / segment_012
- standalone-c_1: 11 lines, standalone-d_3: 18 lines
```diff
--- segment_012 (standalone-c_1)
+++ segment_012 (standalone-d_3)
@@ -1,11 +1,18 @@
-1780-3280ms: moved from (1173,683) to (874,128)

-9380-10079ms: stationary pos=(758,457)

-10280-10880ms: moved from (1255,522) to (1073,344)

-11113-11579ms: moved from (1255,496) to (1255,480)

-11780-12613ms: moved from (827,571) to (1255,441)

-12846-12846ms: stationary pos=(1200,977)

-17880-18346ms: stationary pos=(792,150)

-18579-19380ms: stationary pos=(18,11)

-25880-26579ms: stationary pos=(15,12)

-58579-59180ms: stationary pos=(951,461)

-59380-61380ms: stationary pos=(1024,910)
+180-380ms: moved from (1007,397) to (930,673)

+613-1680ms: stationary pos=(1007,397)

+1880-2346ms: stationary pos=(887,630)

... (29 more lines)
```

### opportunity_list_georgie / segment_013
- standalone-c_1: 36 lines, standalone-d_3: 42 lines
```diff
--- segment_013 (standalone-c_1)
+++ segment_013 (standalone-d_3)
@@ -1,36 +1,42 @@
-34986-36253ms: stationary pos=(1087,277)

-36486-37286ms: stationary pos=(1192,829)

-37520-37986ms: stationary pos=(1024,910)

-38186-38386ms: moved from (1024,1012) to (871,900)

-38586-38786ms: moved from (944,622) to (1072,21)

-39020-39686ms: stationary pos=(944,622)

-39886-40286ms: moved from (930,545) to (968,324)

-40520-40753ms: moved from (1161,352) to (1031,259)

-40986-41186ms: moved from (1112,797) to (951,605)

-41386-41586ms: stationary pos=(1172,768)

-41786-42020ms: moved from (1137,878) to (1104,614)

-42253-42486ms: moved from (936,419) to (986,421)

-42686-42886ms: moved from (1191,335) to (1112,515)

-43086-43520ms: moved from (976,886) to (944,590)
... (125 more lines)
```

### opportunity_list_georgie / segment_014
- standalone-c_1: 60 lines, standalone-d_3: 75 lines
```diff
--- segment_014 (standalone-c_1)
+++ segment_014 (standalone-d_3)
@@ -1,60 +1,75 @@
-2093-2293ms: moved from (1037,285) to (1161,642)

-2493-2693ms: moved from (921,326) to (1066,324)

-2926-3160ms: moved from (1159,908) to (944,261)

-3393-3593ms: stationary pos=(1189,494)

-3793-3993ms: stationary pos=(921,393)

-4193-4660ms: moved from (944,261) to (927,443)

-4893-6593ms: stationary pos=(1053,222)

-6793-6993ms: moved from (1120,452) to (743,630)

-7193-7660ms: moved from (938,846) to (1104,758)

-7893-8093ms: moved from (856,573) to (856,669)

-8293-8693ms: moved from (928,474) to (936,326)

-8926-10893ms: stationary pos=(928,356)

-11093-11293ms: moved from (928,407) to (1057,389)

-11493-11493ms: stationary pos=(923,374)
... (221 more lines)
```

### travel_expert_lisa / segment_000
- standalone-c_1: 22 lines, standalone-d_3: 21 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -1,22 +1,21 @@
-0-509ms: stationary pos=(40,265)

-577-781ms: stationary pos=(40,360)

-985-1393ms: moved from (39,899) to (37,393)

-1597-1801ms: stationary pos=(32,152)

-38651-40521ms: stationary pos=(1610,6)

-40725-42866ms: stationary pos=(945,782)

-42934-45790ms: stationary pos=(1610,6)

-45994-48475ms: stationary pos=(1200,422)

-48713-49121ms: moved from (1664,1035) to (470,1116)

-49325-49529ms: stationary pos=(986,448)

-49733-50175ms: moved from (274,57) to (609,564)

-50379-50787ms: stationary pos=(986,446)

-50991-50991ms: stationary pos=(609,564)

-61019-62447ms: stationary pos=(1610,6)
... (55 more lines)
```

### travel_expert_lisa / segment_001
- standalone-c_1: 41 lines, standalone-d_3: 35 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,12 +1,12 @@
-70-614ms: stationary pos=(1737,182)

+206-886ms: stationary pos=(1737,182)

 2008-2654ms: stationary pos=(1610,6)

-3028-3538ms: stationary pos=(531,834)

-3606-5067ms: stationary pos=(1610,6)

-5135-6359ms: stationary pos=(1025,626)

-6563-8331ms: stationary pos=(19,368)

-9283-10541ms: stationary pos=(19,386)

-10745-11152ms: stationary pos=(561,416)

-11356-13532ms: stationary pos=(19,386)

+3028-3742ms: stationary pos=(531,834)

+3946-5203ms: stationary pos=(1610,6)

+5475-6291ms: stationary pos=(1025,626)

+6495-8229ms: moved from (1234,395) to (19,368)
... (102 more lines)
```

### travel_expert_lisa / segment_002
- standalone-c_1: 44 lines, standalone-d_3: 64 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -1,44 +1,64 @@
-2484-4456ms: moved from (150,313) to (1509,677)

+2348-2552ms: moved from (150,313) to (1095,368)

+2790-4456ms: moved from (568,1014) to (1509,677)

 4660-5475ms: moved from (154,802) to (1025,626)

-5679-6699ms: stationary pos=(757,624)

-14144-17679ms: stationary pos=(1561,988)

-17883-18087ms: stationary pos=(1580,1055)

-18325-18529ms: moved from (1561,984) to (353,1016)

-22031-22269ms: moved from (1666,265) to (1561,988)

-22473-22677ms: moved from (1520,497) to (113,761)

-22881-23084ms: stationary pos=(1520,497)

-23288-23492ms: moved from (1561,988) to (113,521)

-23696-24546ms: moved from (1561,988) to (1582,647)

-24750-25192ms: stationary pos=(1561,988)
... (168 more lines)
```

### travel_expert_lisa / segment_003
- standalone-c_1: 28 lines, standalone-d_3: 28 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_3)
@@ -1,12 +1,12 @@
-342-886ms: stationary pos=(137,148)

-1056-2416ms: stationary pos=(1610,6)

-2484-3878ms: moved from (49,182) to (1610,6)

-4048-5067ms: stationary pos=(1612,390)

-5135-6903ms: stationary pos=(1610,6)

+172-886ms: stationary pos=(137,148)

+1090-2620ms: stationary pos=(1610,6)

+2892-3776ms: stationary pos=(49,182)

+3980-4762ms: stationary pos=(1612,390)

+5067-6903ms: stationary pos=(1610,6)

 7515-8773ms: stationary pos=(1478,959)

 9045-9487ms: moved from (1610,6) to (1478,869)

 9725-9997ms: moved from (1610,6) to (1478,867)

-10235-12512ms: moved from (1610,6) to (1478,805)
... (46 more lines)
```

### travel_expert_lisa / segment_004
- standalone-c_1: 51 lines, standalone-d_3: 53 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_3)
@@ -1,23 +1,23 @@
-6427-6631ms: stationary pos=(566,523)

-6835-6835ms: stationary pos=(1385,1016)

-15776-17679ms: stationary pos=(1610,6)

-26416-27232ms: stationary pos=(1610,6)

+16014-17475ms: stationary pos=(1610,6)

+26212-27232ms: stationary pos=(1610,6)

 27436-27844ms: stationary pos=(1478,700)

 28048-28456ms: moved from (1478,762) to (1478,963)

 28660-29849ms: moved from (1610,6) to (1478,875)

-30053-30563ms: stationary pos=(1610,6)

-30665-30665ms: stationary pos=(1667,220)

-40286-40966ms: moved from (1076,988) to (1610,6)

-41169-44331ms: moved from (455,665) to (1610,6)

-44501-45045ms: stationary pos=(443,973)
... (110 more lines)
```

### travel_expert_lisa / segment_005
- standalone-c_1: 34 lines, standalone-d_3: 33 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_3)
@@ -1,27 +1,26 @@
 172-376ms: moved from (36,169) to (409,1048)

 580-3300ms: stationary pos=(36,169)

 3504-3708ms: stationary pos=(448,1016)

-3912-5441ms: stationary pos=(403,971)

-5645-5849ms: stationary pos=(742,504)

-6121-6359ms: moved from (319,313) to (311,1048)

-6563-8195ms: stationary pos=(448,1016)

-8399-8603ms: stationary pos=(201,248)

-8807-9045ms: stationary pos=(448,1016)

-9249-9453ms: moved from (25,570) to (1548,817)

-9657-9861ms: stationary pos=(609,250)

-16116-16762ms: moved from (1548,892) to (25,362)

-16830-17441ms: moved from (242,1010) to (25,362)

+3912-5373ms: stationary pos=(403,971)
... (66 more lines)
```

### travel_expert_lisa / segment_006
- standalone-c_1: 6 lines, standalone-d_3: 5 lines
```diff
--- segment_006 (standalone-c_1)
+++ segment_006 (standalone-d_3)
@@ -1,6 +1,5 @@
 77917-78801ms: stationary pos=(1478,541)

 79039-79243ms: moved from (1478,652) to (974,176)

-79311-80331ms: stationary pos=(120,332)

-80705-81351ms: stationary pos=(1610,6)

+79447-81351ms: moved from (1478,912) to (1610,6)

 81555-81759ms: moved from (974,260) to (1478,899)

 82269-82915ms: stationary pos=(1610,6)
```

### travel_expert_lisa / segment_007
- standalone-c_1: 52 lines, standalone-d_3: 44 lines
```diff
--- segment_007 (standalone-c_1)
+++ segment_007 (standalone-d_3)
@@ -1,50 +1,42 @@
 5000-5883ms: stationary pos=(1478,541)

 6121-6325ms: moved from (1478,652) to (974,176)

-6393-7413ms: stationary pos=(120,332)

-7787-8433ms: stationary pos=(1610,6)

+6529-8433ms: moved from (1478,912) to (1610,6)

 8637-8841ms: moved from (974,260) to (1478,899)

-9351-10201ms: stationary pos=(1610,6)

-10405-11458ms: stationary pos=(1220,1001)

-18427-18869ms: stationary pos=(341,1007)

-19073-20093ms: stationary pos=(259,980)

-20331-20535ms: moved from (257,937) to (448,712)

-20739-20943ms: moved from (1460,896) to (564,937)

-21147-21351ms: moved from (448,712) to (1460,896)

-21589-21793ms: moved from (639,694) to (1460,896)
... (126 more lines)
```

### travel_expert_lisa / segment_008
- standalone-c_1: 13 lines, standalone-d_3: 13 lines
```diff
--- segment_008 (standalone-c_1)
+++ segment_008 (standalone-d_3)
@@ -1,13 +1,13 @@
-172-1770ms: stationary pos=(739,596)

-1804-3606ms: stationary pos=(1610,6)

-3810-5815ms: stationary pos=(171,317)

+36-1804ms: stationary pos=(739,596)

+2042-3606ms: stationary pos=(1610,6)

+4150-5815ms: stationary pos=(171,317)

 6053-7175ms: moved from (171,328) to (143,233)

 7413-7617ms: moved from (143,345) to (143,184)

 7855-8263ms: moved from (1614,905) to (143,345)

 8467-8977ms: stationary pos=(634,995)

 9215-16116ms: moved from (1616,842) to (1610,6)

 17135-18121ms: stationary pos=(1616,838)

-19141-19141ms: stationary pos=(1616,834)

-23832-24444ms: stationary pos=(1095,1125)
... (11 more lines)
```

### travel_expert_veronika / segment_000
- standalone-c_1: 62 lines, standalone-d_3: 78 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -1,14 +1,14 @@
-0-1001ms: stationary pos=(956,326)

-1234-1434ms: stationary pos=(569,344)

-1685-1885ms: moved from (656,698) to (441,1003)

-2085-2535ms: moved from (263,813) to (656,698)

+0-1134ms: stationary pos=(956,326)

+1368-1568ms: moved from (569,344) to (1671,75)

+1818-2085ms: moved from (369,981) to (263,813)

+2335-2535ms: stationary pos=(656,698)

 2736-2936ms: stationary pos=(646,358)

 3136-3336ms: moved from (1666,947) to (1211,873)

 3536-3737ms: moved from (1736,1051) to (863,366)

-3937-5405ms: stationary pos=(837,380)

-5605-6006ms: stationary pos=(759,749)

-6206-6406ms: moved from (1310,328) to (933,747)
... (180 more lines)
```

### travel_expert_veronika / segment_001
- standalone-c_1: 51 lines, standalone-d_3: 53 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,37 +1,39 @@
-151-952ms: stationary pos=(974,520)

-5390-7242ms: stationary pos=(515,338)

-7442-9044ms: stationary pos=(978,626)

-9110-9511ms: stationary pos=(515,338)

+18-1619ms: stationary pos=(974,520)

+1886-3938ms: stationary pos=(513,842)

+4205-4856ms: stationary pos=(516,844)

+5056-5590ms: moved from (691,893) to (517,845)

+5857-6324ms: moved from (565,827) to (805,620)

+6574-6841ms: stationary pos=(469,715)

+7042-8710ms: moved from (469,717) to (978,626)

+8910-9511ms: stationary pos=(515,338)

 9961-10195ms: moved from (1079,357) to (1088,312)

-10562-11329ms: stationary pos=(1079,357)
... (159 more lines)
```

### travel_expert_veronika / segment_002
- standalone-c_1: 38 lines, standalone-d_3: 29 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -5,34 +5,25 @@
 24382-24749ms: moved from (1252,793) to (128,713)

 25050-25717ms: stationary pos=(1190,344)

 26134-26334ms: moved from (264,326) to (929,521)

-26735-27786ms: stationary pos=(988,246)

-28019-28370ms: moved from (352,12) to (264,326)

-28703-29487ms: moved from (1148,713) to (1795,376)

+27235-28019ms: stationary pos=(988,246)

+28370-29487ms: stationary pos=(351,1022)

 33792-34626ms: stationary pos=(1707,136)

 34943-35510ms: moved from (416,971) to (1346,408)

-35710-37028ms: moved from (521,679) to (397,131)

-37112-38363ms: stationary pos=(495,1050)

+35710-36828ms: moved from (521,679) to (1346,408)

+37028-38363ms: stationary pos=(495,1050)
... (65 more lines)
```

### travel_expert_veronika / segment_003
- standalone-c_1: 49 lines, standalone-d_3: 47 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_3)
@@ -1,49 +1,47 @@
-4886-5670ms: stationary pos=(945,825)

 5904-6104ms: moved from (945,585) to (1667,140)

-6304-6721ms: moved from (256,1068) to (1394,793)

-6938-7439ms: stationary pos=(1667,664)

-7505-7756ms: moved from (1394,793) to (256,1064)

-7956-8156ms: moved from (1394,793) to (1891,170)

-8373-8573ms: moved from (1891,134) to (1891,202)

-8773-8973ms: moved from (1522,837) to (1891,218)

-9174-9391ms: stationary pos=(915,214)

-9607-10675ms: moved from (915,216) to (1891,198)

-10875-12127ms: moved from (915,218) to (721,280)

-12193-14879ms: stationary pos=(1275,125)

-14946-15563ms: stationary pos=(721,280)

+6304-6938ms: moved from (256,1068) to (1394,793)
... (137 more lines)
```

### travel_expert_veronika / segment_004
- standalone-c_1: 50 lines, standalone-d_3: 31 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_3)
@@ -1,50 +1,31 @@
 3525-3758ms: moved from (242,621) to (288,280)

 3975-4376ms: stationary pos=(1042,472)

-4592-6027ms: stationary pos=(1079,263)

-7028-8480ms: moved from (585,500) to (731,503)

-10098-12367ms: stationary pos=(289,363)

-12417-13201ms: moved from (350,122) to (289,363)

+4592-5026ms: stationary pos=(1079,263)

+6027-7028ms: stationary pos=(579,511)

+8046-8480ms: stationary pos=(731,503)

 13401-13752ms: stationary pos=(793,281)

-14769-14769ms: stationary pos=(289,363)

-19040-20025ms: moved from (557,621) to (495,126)

-20642-21693ms: moved from (1252,569) to (537,561)

-22143-22644ms: moved from (1360,639) to (1220,80)
... (113 more lines)
```

### travel_expert_william / segment_000
- standalone-c_1: 37 lines, standalone-d_3: 27 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -6,32 +6,22 @@
 3140-3340ms: moved from (93,83) to (1782,155)

 3540-3807ms: moved from (1831,1068) to (1182,925)

 4008-4674ms: moved from (446,852) to (1784,155)

-4874-6049ms: moved from (1080,483) to (1784,153)

-6172-8163ms: stationary pos=(620,465)

-8213-8746ms: stationary pos=(367,28)

-9279-9813ms: moved from (383,28) to (367,28)

-9878-11818ms: stationary pos=(620,465)

-11969-14625ms: stationary pos=(367,28)

-14692-16518ms: stationary pos=(620,465)

-16784-16784ms: stationary pos=(367,28)

-31740-33407ms: stationary pos=(700,700)

+4874-5274ms: moved from (1080,483) to (1784,155)

+5657-7545ms: stationary pos=(620,465)
... (59 more lines)
```

### travel_expert_william / segment_001
- standalone-c_1: 16 lines, standalone-d_3: 14 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,16 +1,14 @@
-22616-22890ms: stationary pos=(336,355)

-23162-23463ms: moved from (1415,469) to (197,781)

-23699-23904ms: moved from (1299,431) to (760,338)

-24166-24384ms: moved from (662,1072) to (760,338)

-24601-24907ms: moved from (563,854) to (752,514)

-25166-25987ms: moved from (578,765) to (1423,929)

-26658-33814ms: stationary pos=(1388,553)

-37526-38110ms: stationary pos=(856,619)

-38374-38811ms: moved from (1507,319) to (1161,814)

-52480-52702ms: moved from (1472,335) to (1767,678)

-52903-53777ms: moved from (1472,335) to (1767,680)

-77847-79287ms: stationary pos=(1767,680)

-79377-79900ms: stationary pos=(184,718)

+23162-23699ms: moved from (456,598) to (456,759)
... (29 more lines)
```

### travel_expert_william / segment_002
- standalone-c_1: 48 lines, standalone-d_3: 52 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -1,23 +1,21 @@
-6220-7660ms: stationary pos=(1767,680)

-7750-8273ms: stationary pos=(184,718)

+7750-8151ms: stationary pos=(184,718)

 8434-8903ms: stationary pos=(1767,680)

-9333-9790ms: stationary pos=(133,303)

-9962-11548ms: stationary pos=(383,28)

-11664-12097ms: stationary pos=(133,303)

+9333-10029ms: stationary pos=(133,303)

+10497-11588ms: stationary pos=(383,28)

+11879-12097ms: stationary pos=(133,303)

 12298-12546ms: stationary pos=(114,303)

 12746-12946ms: moved from (915,157) to (114,303)

-13147-13679ms: stationary pos=(1215,571)

+13147-13414ms: moved from (915,157) to (1215,571)
... (100 more lines)
```

### travel_expert_william / segment_003
- standalone-c_1: 44 lines, standalone-d_3: 49 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_3)
@@ -1,34 +1,39 @@
-39-504ms: stationary pos=(793,732)

-853-1296ms: moved from (793,728) to (793,597)

-1641-1641ms: stationary pos=(184,456)

+39-504ms: moved from (793,732) to (717,541)

+853-1296ms: moved from (1630,963) to (717,406)

+1641-2575ms: moved from (330,603) to (717,328)

 7088-7572ms: stationary pos=(843,333)

 8300-8517ms: stationary pos=(596,770)

 8990-9300ms: moved from (114,700) to (833,1038)

-9524-12291ms: moved from (1701,489) to (1689,252)

+9524-9910ms: moved from (1627,277) to (792,784)

+10118-10439ms: moved from (1627,277) to (424,825)

+10711-10950ms: moved from (1627,277) to (768,776)

+11198-12291ms: moved from (1701,489) to (1689,252)
... (123 more lines)
```

### travel_expert_william / segment_004
- standalone-c_1: 34 lines, standalone-d_3: 35 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_3)
@@ -1,34 +1,35 @@
 5239-7252ms: stationary pos=(1847,483)

-7589-7781ms: moved from (1667,190) to (543,368)

-8320-8677ms: moved from (543,347) to (1667,190)

+7589-7910ms: stationary pos=(1667,190)

+8241-8677ms: moved from (1847,483) to (1667,190)

 8936-9299ms: moved from (1847,483) to (1081,1073)

 9606-10379ms: moved from (934,1073) to (1847,483)

 10729-10729ms: stationary pos=(1325,153)

-18027-19310ms: stationary pos=(543,900)

-19502-20617ms: stationary pos=(1847,483)

-27973-29377ms: stationary pos=(543,571)

+15933-15933ms: stationary pos=(543,1005)

+24596-27230ms: stationary pos=(1847,483)

+27799-29241ms: stationary pos=(543,571)
... (73 more lines)
```

### travel_learner_sophia_jayde / segment_000
- standalone-c_1: 31 lines, standalone-d_3: 40 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_3)
@@ -1,31 +1,40 @@
-0-67ms: moved from (23,761) to (23,697)

-271-679ms: stationary pos=(23,761)

-883-1733ms: moved from (23,794) to (1430,799)

-1937-2685ms: moved from (1381,822) to (1430,799)

-6424-6492ms: stationary pos=(695,505)

-6696-7138ms: stationary pos=(695,538)

-7342-7614ms: moved from (695,505) to (695,538)

-7818-8022ms: stationary pos=(695,505)

-8260-8498ms: moved from (695,538) to (1009,873)

-8702-9348ms: stationary pos=(695,501)

+0-203ms: moved from (23,761) to (107,649)

+407-815ms: moved from (23,729) to (23,794)

+1053-1869ms: moved from (1430,743) to (1430,799)

+2073-2277ms: moved from (32,1017) to (191,600)
... (95 more lines)
```

### travel_learner_sophia_jayde / segment_001
- standalone-c_1: 31 lines, standalone-d_3: 36 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_3)
@@ -1,31 +1,36 @@
-201-2070ms: stationary pos=(1763,12)

-14546-15600ms: stationary pos=(938,841)

-15668-18150ms: stationary pos=(1763,12)

-18252-19849ms: stationary pos=(938,841)

-29028-30388ms: stationary pos=(1763,12)

-30524-33685ms: stationary pos=(286,217)

-37186-39566ms: moved from (1498,955) to (1763,12)

-39702-40246ms: stationary pos=(413,1078)

-48609-48813ms: stationary pos=(761,423)

-49016-49220ms: moved from (830,423) to (761,423)

-49424-49662ms: moved from (830,423) to (761,423)

-49866-50274ms: moved from (830,423) to (761,423)

-50478-50682ms: stationary pos=(830,423)

-50886-51328ms: stationary pos=(761,423)
... (105 more lines)
```

### travel_learner_sophia_jayde / segment_002
- standalone-c_1: 16 lines, standalone-d_3: 11 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_3)
@@ -1,16 +1,11 @@
-5532-6110ms: stationary pos=(23,232)

-6212-7640ms: stationary pos=(1763,12)

-7776-8796ms: stationary pos=(23,393)

-8864-11345ms: stationary pos=(1763,12)

-11481-12127ms: stationary pos=(23,361)

-12331-12637ms: stationary pos=(286,297)

-12875-13079ms: moved from (23,361) to (286,297)

-13283-14099ms: moved from (23,361) to (139,959)

-34427-34903ms: moved from (327,454) to (1763,12)

-35447-35447ms: stationary pos=(303,1112)

+5600-6008ms: stationary pos=(23,232)

+6212-7402ms: stationary pos=(1763,12)

+7776-8932ms: stationary pos=(23,393)

+34427-36535ms: moved from (327,454) to (1763,12)
... (16 more lines)
```

### travel_learner_sophia_jayde / segment_004
- standalone-c_1: 3 lines, standalone-d_3: 3 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_3)
@@ -1,3 +1,3 @@
-34756-35266ms: stationary pos=(119,14)

-35334-36184ms: stationary pos=(30,10)

-36388-36388ms: stationary pos=(1765,9)
+34756-35198ms: stationary pos=(119,14)

+35470-35912ms: stationary pos=(30,10)

+36116-36524ms: moved from (28,10) to (1765,9)
```

### travel_learner_sophia_jayde / segment_010
- standalone-c_1: 6 lines, standalone-d_3: 7 lines
```diff
--- segment_010 (standalone-c_1)
+++ segment_010 (standalone-d_3)
@@ -1,3 +1,4 @@
+23130-23130ms: stationary pos=(838,935)

 29249-29691ms: stationary pos=(1736,505)

 29929-30541ms: moved from (1549,710) to (1568,305)

 30813-31016ms: moved from (462,727) to (606,1000)

```

### travel_learner_sophia_jayde / segment_011
- standalone-c_1: 5 lines, standalone-d_3: 4 lines
```diff
--- segment_011 (standalone-c_1)
+++ segment_011 (standalone-d_3)
@@ -1,5 +1,4 @@
-56099-57594ms: stationary pos=(1654,785)

-78909-79589ms: stationary pos=(1654,785)

-79827-80031ms: moved from (1050,680) to (1758,264)

-80235-80235ms: stationary pos=(794,1110)

-83974-83974ms: stationary pos=(1065,712)
+56507-57730ms: stationary pos=(1654,785)

+79283-79725ms: stationary pos=(1654,785)

+79929-80473ms: moved from (1758,264) to (794,1110)

+81254-83974ms: stationary pos=(119,14)
```

### travel_learner_sophia_jayde / segment_012
- standalone-c_1: 19 lines, standalone-d_3: 17 lines
```diff
--- segment_012 (standalone-c_1)
+++ segment_012 (standalone-d_3)
@@ -1,19 +1,17 @@
-4898-5577ms: stationary pos=(1654,785)

-5815-6019ms: moved from (1050,680) to (1758,264)

-6223-6223ms: stationary pos=(794,1110)

-9963-11254ms: stationary pos=(1065,712)

-11492-14076ms: stationary pos=(1763,12)

+5271-5713ms: stationary pos=(1654,785)

+5917-6461ms: moved from (1758,264) to (794,1110)

+7243-9963ms: stationary pos=(119,14)

+10303-11492ms: stationary pos=(1065,712)

+11832-14076ms: stationary pos=(1763,12)

 14348-14552ms: moved from (1020,901) to (1554,901)

 14790-14994ms: stationary pos=(1128,793)

 15198-15606ms: moved from (1554,901) to (1128,793)

 15810-16014ms: moved from (1554,901) to (1128,793)
... (29 more lines)
```

### travel_learner_sophia_jayde / segment_014
- standalone-c_1: 3 lines, standalone-d_3: 2 lines
```diff
--- segment_014 (standalone-c_1)
+++ segment_014 (standalone-d_3)
@@ -1,3 +1,2 @@
-78552-78756ms: stationary pos=(119,14)

-78960-79402ms: stationary pos=(377,341)

-79640-79640ms: stationary pos=(1647,14)
+77940-79402ms: moved from (845,729) to (838,459)

+79640-80252ms: stationary pos=(1669,1110)
```

### travel_learner_sophia_jayde / segment_015
- standalone-c_1: 5 lines, standalone-d_3: 4 lines
```diff
--- segment_015 (standalone-c_1)
+++ segment_015 (standalone-d_3)
@@ -1,5 +1,4 @@
-4541-4745ms: stationary pos=(119,14)

-4949-5390ms: stationary pos=(377,341)

-5628-5628ms: stationary pos=(1647,14)

+3929-5390ms: moved from (845,729) to (838,459)

+5628-6240ms: stationary pos=(1669,1110)

 56552-57572ms: moved from (870,531) to (1763,12)

 58558-58558ms: stationary pos=(870,531)
```

### travel_learner_sophia_jayde / segment_016
- standalone-c_1: 5 lines, standalone-d_3: 7 lines
```diff
--- segment_016 (standalone-c_1)
+++ segment_016 (standalone-d_3)
@@ -1,5 +1,7 @@
-21362-21804ms: moved from (533,753) to (619,712)

-22008-22824ms: moved from (587,116) to (604,585)

-22892-23946ms: stationary pos=(926,946)

-24014-25067ms: stationary pos=(736,414)

-25271-25475ms: moved from (1095,362) to (1618,487)
+21634-21872ms: moved from (727,716) to (587,116)

+22076-22280ms: moved from (604,585) to (1755,458)

+22484-22892ms: stationary pos=(604,585)

+23096-24150ms: stationary pos=(926,946)

+24354-24966ms: stationary pos=(736,414)

+25203-25407ms: stationary pos=(1095,362)

+25611-25611ms: stationary pos=(1618,487)
```

### travel_learner_sophia_jayde / segment_022
- standalone-c_1: 12 lines, standalone-d_3: 20 lines
```diff
--- segment_022 (standalone-c_1)
+++ segment_022 (standalone-d_3)
@@ -1,12 +1,20 @@
-28433-29419ms: stationary pos=(119,14)

-29657-29861ms: moved from (1498,955) to (452,414)

-30065-30065ms: stationary pos=(1033,759)

-41181-41589ms: stationary pos=(452,414)

+28433-28841ms: stationary pos=(119,14)

+28977-29419ms: stationary pos=(1437,8)

+29657-29861ms: moved from (1328,573) to (30,214)

+30065-30507ms: moved from (1328,573) to (454,414)

+40603-41011ms: moved from (893,791) to (1763,12)

+41249-41657ms: stationary pos=(452,414)

 41861-42065ms: moved from (11,404) to (119,14)

 42303-42779ms: moved from (11,404) to (119,14)

 42983-43288ms: moved from (447,798) to (766,942)

 43594-43798ms: moved from (119,14) to (1066,899)
... (25 more lines)
```

### travel_learner_sophia_jayde / segment_023
- standalone-c_1: 8 lines, standalone-d_3: 5 lines
```diff
--- segment_023 (standalone-c_1)
+++ segment_023 (standalone-d_3)
@@ -1,8 +1,5 @@
-52257-53821ms: stationary pos=(1069,873)

-54025-54229ms: stationary pos=(1403,615)

-54467-55045ms: stationary pos=(830,264)

-55419-55487ms: moved from (909,791) to (1403,615)

-55691-56133ms: stationary pos=(830,264)

-56337-56541ms: moved from (1324,636) to (830,264)

-56745-56949ms: moved from (55,562) to (830,264)

-57152-57356ms: moved from (1168,652) to (830,262)
+52529-53889ms: stationary pos=(1069,873)

+54093-54297ms: stationary pos=(1403,615)

+54807-56269ms: moved from (909,791) to (830,264)

+56473-56677ms: moved from (1324,636) to (830,264)

+56881-57084ms: moved from (1366,1084) to (830,262)
```

### travel_learner_sophia_jayde / segment_024
- standalone-c_1: 4 lines, standalone-d_3: 5 lines
```diff
--- segment_024 (standalone-c_1)
+++ segment_024 (standalone-d_3)
@@ -1,4 +1,5 @@
 42869-43311ms: stationary pos=(1669,234)

 43515-43923ms: stationary pos=(1775,557)

-44331-46099ms: moved from (119,14) to (1775,557)

+44331-44705ms: stationary pos=(119,14)

+45453-46099ms: stationary pos=(1775,557)

 46303-46303ms: stationary pos=(464,766)
```

### travel_learner_sophia_jayde / segment_029
- standalone-c_1: 5 lines, standalone-d_3: 4 lines
```diff
--- segment_029 (standalone-c_1)
+++ segment_029 (standalone-d_3)
@@ -1,5 +1,4 @@
 38796-40053ms: stationary pos=(1256,794)

 40257-40461ms: moved from (621,936) to (1568,462)

 40699-40903ms: moved from (1432,812) to (1432,806)

-41107-41311ms: moved from (226,839) to (1432,821)

-73504-75373ms: stationary pos=(413,234)
+41107-41311ms: moved from (226,839) to (1432,821)
```

## 3. Event Cursor Enrichment

| Category | Count |
|----------|------:|
| Cursor events total | 908 |
| Both have position | 223 |
| Coverage lost (standalone-d_3 missing) | 19 |
| Coverage gained (standalone-d_3 new) | 22 |
| Neither has position | 644 |

### Position accuracy on events
- Mean: 211.6px
- Median: 0.0px
- Max: 1976.8px
- Within 5px: 153/223
- Within 20px: 155/223

### Events that lost cursor coverage (19)

| Time (ms) | Type | Description | standalone-c_1 pos |
|----------:|------|-------------|-----------|
| 236675 | click | User clicks 'View details' on a CBA home loan product. | (271.0,977.0) |
| 541800 | hover | Hover over 'End Task' button | (1690.0,889.0) |
| 133917 | click | User clicks on the ubank search result link. | (319.0,53.0) |
| 182000 | hover | User hovers over the 'Jump to' dropdown menu. | (765.0,196.0) |
| 278969 | hover | User hovers over the 'All Interview' card ($40). | (1060.0,220.0) |
| 356062 | select | User selects the 'Mobile Only' device filter. | (1104.0,758.0) |
| 357662 | select | User selects the 'Under 10 min' duration filter. | (1104.0,758.0) |
| 468599 | hover | Hover over a 'Survey' session card. | (1023.0,437.0) |
| 519642 | hover | User hovers over the AI interview card titled 'Test a new budgeting app interfac | (1120.0,429.0) |
| 548142 | hover | User hovers over the AI interview card titled 'Test a new budgeting app interfac | (1159.0,779.0) |
| 854316 | hover | User hovers over the 'AI Interview' filter chip. | (1015.0,677.0) |
| 855616 | click | User clicks on the 'AI Interview' filter chip. | (1015.0,677.0) |
| 173771 | click | User clicks on the 'From' input field. | (945.0,827.0) |
| 177321 | select | User selects 'Sunshine Coast (MCY)' from the location dropdown. | (945.0,585.0) |
| 188871 | click | User clicks the 'Search' button. | (945.0,825.0) |
| 256611 | hover | Hover over the 'Unko Museum' card. | (289.0,363.0) |
| 278761 | hover | Hover over the 'Lake Toyako' card. | (555.0,561.0) |
| 279561 | hover | Hover over the 'Kappabashi Street' card. | (555.0,599.0) |
| 89184 | click | User initiates the search (via Enter key). | (336.0,355.0) |

### Events that gained cursor coverage (22)

| Time (ms) | Type | Description | standalone-d_3 pos |
|----------:|------|-------------|-----------|
| 161100 | select | User selects 'ANZ Bank' from the dropdown. | (1700.0,51.0) |
| 161500 | click | User clicks the 'NEXT' button. | (915.0,498.0) |
| 180600 | select | User selects 'Excellent - No Issues'. | (730.0,391.0) |
| 185000 | click | User clicks the browser back button. | (1304.0,463.0) |
| 221450 | click | User clicks on the Google search bar to edit the query. | (733.0,1507.0) |
| 284269 | hover | User hovers over the 'Diary Study' card ($40). | (1060.0,220.0) |
| 302269 | hover | User hovers over the 'Survey' card ($15). | (817.0,47.0) |
| 489199 | hover | Hover over the 'Clear All' button in the filter modal. | (1104.0,328.0) |
| 489699 | click | Click on the 'X' close button of the filter modal. | (1104.0,328.0) |
| 738268 | hover | Hover over the 'Save these preferences' button | (1024.0,910.0) |
| 863316 | hover | User hovers over a 'Survey' task card. | (1007.0,397.0) |
| 910669 | hover | User hovers over the 'Tasks' icon in the bottom navigation bar. | (1255.0,126.0) |
| 953769 | hover | User hovers over an 'AI Interview' task card titled 'Anyone who has a personal p | (786.0,78.0) |
| 548915 | click | User clicks on the 'Leaving from' input field. | (1460.0,896.0) |
| 549615 | hover | User hovers over the 'Brisbane - London' option in the recent searches list. | (1460.0,896.0) |
| 242751 | hover | Hover over a flight result card. | (1533.0,979.0) |
| 290900 | hover | User hovers over the close button ('X') of the Genius modal. | (1252.0,328.0) |
| 292950 | click | User clicks the 'X' button in the top right corner of the Genius modal to close  | (1252.0,328.0) |
| 102684 | select | User selects a departure date. | (1039.0,437.0) |
| 118511 | select | Select the 'expedia' suggestion from the dropdown list. | (1472.0,335.0) |
| 247314 | click | User clicks the 'Very good 8+' guest rating filter. | (1276.0,970.0) |
| 75407 | hover | Hover over the right side of the screen share content. | (1763.0,12.0) |

## 4. Config Comparison

| Setting | standalone-c_1 | standalone-d_3 |
|---------|-------------|------------|
| cursor.tracking_base_fps | 2.0 | 3.0 |
