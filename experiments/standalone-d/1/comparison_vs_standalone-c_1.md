# Cursor Experiment Comparison: standalone-c_1 vs standalone-d_1

## 1. Trajectory Comparison (aggregate)

| Session | standalone-c_1 det | standalone-d_1 det | Common | Identical | Both det | Disagree | Mean drift | Max drift |
|---------|---:|---:|---:|---:|---:|---:|---:|---:|
| ask_create_study_brandon | 38 | 30 | 875 | 875 | 9 | 0 | 0.0 | 0.0 |
| ask_results_usability_brandon | 73 | 54 | 1298 | 1298 | 25 | 0 | 0.0 | 0.0 |
| cfs_home_loan_sasha | 1247 | 976 | 801 | 797 | 344 | 1 | 0.0 | 1.0 |
| cfs_home_loan_serene | 684 | 574 | 287 | 272 | 185 | 11 | 0.0 | 3.0 |
| flight_centre_booking_james | 189 | 144 | 307 | 307 | 55 | 0 | 0.0 | 0.0 |
| flight_centre_booking_kay | 829 | 655 | 588 | 567 | 255 | 19 | 3.5 | 725.9 |
| opportunity_list_ben | 1269 | 1016 | 639 | 631 | 375 | 4 | 0.0 | 1.0 |
| opportunity_list_georgie | 2463 | 1932 | 1530 | 1488 | 665 | 23 | 1.1 | 432.4 |
| travel_expert_lisa | 991 | 770 | 973 | 941 | 401 | 22 | 0.0 | 3.0 |
| travel_expert_veronika | 813 | 665 | 495 | 481 | 354 | 10 | 0.0 | 1.0 |
| travel_expert_william | 579 | 515 | 593 | 588 | 323 | 0 | 0.0 | 3.0 |
| travel_learner_sophia_jayde | 551 | 439 | 3317 | 3315 | 215 | 1 | 8.5 | 1828.0 |
| **TOTAL** | **9726** | **7770** | — | **11560** | **3206** | — | **1.1** | **1828.0** |

### Position accuracy (where both detected)
- Samples: 3206
- Identical (0px): 3154
- Within 1px: 3191
- Within 5px: 3201
- Median: 0.0px
- Mean: 1.1px
- Max: 1828.0px

## 2. Cursor Summary Diffs (per segment)

Identical: 22/107 segments
Changed: 85/107 segments

### ask_create_study_brandon / segment_001
- standalone-c_1: 4 lines, standalone-d_1: 3 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,4 +1,3 @@
-38105-38772ms: stationary pos=(1651,76)

-39005-39605ms: moved from (80,537) to (80,585)

-39805-40038ms: moved from (80,537) to (80,617)

-52605-54538ms: stationary pos=(1651,74)
+38105-38905ms: stationary pos=(1651,76)

+39172-39972ms: moved from (80,585) to (80,617)

+52605-54472ms: stationary pos=(1651,74)
```

### ask_create_study_brandon / segment_004
- standalone-c_1: 1 lines, standalone-d_1: 1 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_1)
@@ -1 +1 @@
-80922-82922ms: stationary pos=(1651,76)
+80922-82788ms: stationary pos=(1651,76)
```

### ask_create_study_brandon / segment_005
- standalone-c_1: 1 lines, standalone-d_1: 1 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_1)
@@ -1 +1 @@
-7027-9027ms: stationary pos=(1651,76)
+7027-8894ms: stationary pos=(1651,76)
```

### ask_results_usability_brandon / segment_000
- standalone-c_1: 4 lines, standalone-d_1: 3 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,4 +1,3 @@
 1000-3000ms: stationary pos=(708,12)

-7200-7433ms: moved from (1683,706) to (1391,65)

 8000-9000ms: stationary pos=(414,14)

-9500-10900ms: stationary pos=(1391,65)
+9500-10833ms: stationary pos=(1391,65)
```

### ask_results_usability_brandon / segment_002
- standalone-c_1: 3 lines, standalone-d_1: 3 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -1,3 +1,3 @@
-45555-46155ms: stationary pos=(1391,65)

-46355-46755ms: moved from (319,513) to (1391,65)

-46955-47555ms: stationary pos=(946,1107)
+45555-46088ms: stationary pos=(1391,65)

+46355-46622ms: moved from (319,513) to (249,619)

+46888-47422ms: stationary pos=(946,1107)
```

### ask_results_usability_brandon / segment_003
- standalone-c_1: 2 lines, standalone-d_1: 2 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_1)
@@ -1,2 +1,2 @@
-58833-60833ms: stationary pos=(1391,65)

-70333-72333ms: stationary pos=(1391,65)
+58833-60700ms: stationary pos=(1391,65)

+70333-72200ms: stationary pos=(1391,65)
```

### ask_results_usability_brandon / segment_004
- standalone-c_1: 3 lines, standalone-d_1: 3 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_1)
@@ -1,3 +1,3 @@
-32111-34111ms: stationary pos=(1391,65)

-39611-41011ms: stationary pos=(1391,65)

-41211-41611ms: moved from (612,651) to (1391,65)
+32111-33977ms: stationary pos=(1391,65)

+39611-40944ms: stationary pos=(1391,65)

+41211-41477ms: moved from (612,651) to (1391,65)
```

### cfs_home_loan_sasha / segment_000
- standalone-c_1: 23 lines, standalone-d_1: 22 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,23 +1,22 @@
 1000-3800ms: stationary pos=(1055,381)

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
... (57 more lines)
```

### cfs_home_loan_sasha / segment_001
- standalone-c_1: 25 lines, standalone-d_1: 23 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,25 +1,23 @@
-12275-12675ms: stationary pos=(691,146)

-12875-13075ms: moved from (1616,37) to (950,674)

-13275-13475ms: moved from (1024,513) to (1618,37)

-13675-13675ms: stationary pos=(619,603)

-57275-57475ms: moved from (762,999) to (897,200)

-57708-57941ms: moved from (762,999) to (397,825)

-58174-58575ms: stationary pos=(1660,776)

-58775-59208ms: moved from (1722,584) to (1072,216)

-59441-59674ms: moved from (1720,712) to (1072,216)

-59875-60075ms: moved from (1624,919) to (1072,216)

-60275-60275ms: stationary pos=(1722,879)

-64075-64508ms: stationary pos=(1618,37)

-64708-66775ms: moved from (864,140) to (313,54)

-67275-67675ms: moved from (457,22) to (24,122)
... (67 more lines)
```

### cfs_home_loan_sasha / segment_002
- standalone-c_1: 30 lines, standalone-d_1: 33 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -1,30 +1,33 @@
-150-550ms: moved from (222,341) to (971,253)

+150-416ms: moved from (222,341) to (971,253)

 1050-1850ms: stationary pos=(198,327)

-2050-2250ms: moved from (491,437) to (555,1031)

-2450-3450ms: moved from (251,784) to (377,126)

-3650-4250ms: moved from (1886,135) to (1889,234)

-4450-5050ms: stationary pos=(1888,135)

-5550-6150ms: stationary pos=(1670,105)

-6350-9350ms: moved from (1670,101) to (739,650)

-16550-17950ms: moved from (1209,603) to (1669,51)

-18550-20450ms: stationary pos=(728,791)

-43050-43250ms: stationary pos=(739,911)

-53550-53950ms: stationary pos=(869,453)

+2116-2383ms: moved from (461,429) to (251,784)
... (91 more lines)
```

### cfs_home_loan_sasha / segment_003
- standalone-c_1: 88 lines, standalone-d_1: 77 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_1)
@@ -1,88 +1,77 @@
-325-725ms: stationary pos=(1881,185)

-925-1325ms: stationary pos=(1678,123)

-1525-2325ms: stationary pos=(604,823)

+325-858ms: stationary pos=(1881,185)

+1125-1391ms: stationary pos=(1678,123)

+1658-2191ms: stationary pos=(604,823)

 2825-5325ms: stationary pos=(662,319)

-5825-6225ms: stationary pos=(604,823)

-6425-8358ms: moved from (604,556) to (604,300)

-8591-8991ms: stationary pos=(568,273)

-9191-9425ms: moved from (1744,498) to (1198,529)

-9658-10091ms: stationary pos=(931,1060)

-10291-10491ms: moved from (1871,842) to (1140,686)

-10691-11158ms: moved from (1522,514) to (1172,779)
... (291 more lines)
```

### cfs_home_loan_sasha / segment_004
- standalone-c_1: 102 lines, standalone-d_1: 87 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_1)
@@ -1,102 +1,87 @@
-0-400ms: stationary pos=(257,636)

-600-1000ms: moved from (176,698) to (1893,841)

-1200-1400ms: stationary pos=(160,361)

-1600-2000ms: moved from (160,359) to (1019,433)

-2200-3000ms: moved from (1282,204) to (1182,728)

-3200-3400ms: moved from (1296,742) to (257,158)

-3600-3800ms: moved from (242,242) to (180,281)

-4000-4200ms: stationary pos=(175,173)

-4400-4600ms: moved from (1241,870) to (1361,186)

-4800-5000ms: moved from (192,393) to (686,265)

-5200-5600ms: moved from (1150,281) to (1200,311)

-5800-6000ms: moved from (32,200) to (385,281)

-6200-6800ms: moved from (417,232) to (1159,179)

-7000-7200ms: moved from (421,520) to (1225,173)
... (341 more lines)
```

### cfs_home_loan_sasha / segment_005
- standalone-c_1: 113 lines, standalone-d_1: 87 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_1)
@@ -1,113 +1,87 @@
-175-375ms: moved from (1232,855) to (164,536)

-575-975ms: stationary pos=(166,570)

-1175-1575ms: moved from (1096,784) to (166,503)

-1775-2375ms: moved from (1096,784) to (166,503)

-2575-2975ms: moved from (1096,784) to (560,1027)

-3175-3375ms: stationary pos=(784,281)

-3575-4175ms: stationary pos=(780,265)

-4375-4575ms: stationary pos=(618,977)

-4775-4975ms: moved from (1561,56) to (1706,712)

-5175-5375ms: moved from (1035,196) to (805,56)

-5575-5775ms: stationary pos=(1712,505)

-5975-6175ms: moved from (409,568) to (1712,505)

-6375-7375ms: stationary pos=(1724,40)

-7575-7775ms: moved from (752,939) to (954,326)
... (359 more lines)
```

### cfs_home_loan_sasha / segment_006
- standalone-c_1: 27 lines, standalone-d_1: 24 lines
```diff
--- segment_006 (standalone-c_1)
+++ segment_006 (standalone-d_1)
@@ -1,27 +1,24 @@
-150-350ms: stationary pos=(1577,249)

-550-750ms: moved from (291,809) to (720,391)

-950-1150ms: moved from (1497,899) to (1664,136)

-1350-1550ms: moved from (1656,134) to (1784,232)

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
... (69 more lines)
```

### cfs_home_loan_sasha / segment_007
- standalone-c_1: 23 lines, standalone-d_1: 22 lines
```diff
--- segment_007 (standalone-c_1)
+++ segment_007 (standalone-d_1)
@@ -1,23 +1,22 @@
-9425-9625ms: stationary pos=(1084,840)

-9825-10058ms: stationary pos=(1084,843)

-10258-10891ms: moved from (1536,585) to (823,330)

+9425-9691ms: stationary pos=(1084,840)

+9958-10225ms: moved from (1084,844) to (1536,585)

+10491-10758ms: stationary pos=(823,330)

 11425-11925ms: stationary pos=(787,339)

-12425-13058ms: stationary pos=(1351,439)

-13258-13458ms: stationary pos=(780,535)

-13658-13891ms: moved from (95,420) to (32,730)

-14091-14925ms: moved from (212,903) to (208,889)

-15425-16425ms: moved from (200,895) to (212,903)

-16625-17258ms: moved from (200,905) to (212,903)

-17458-18725ms: moved from (80,1037) to (200,905)
... (54 more lines)
```

### cfs_home_loan_serene / segment_000
- standalone-c_1: 47 lines, standalone-d_1: 40 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,47 +1,40 @@
-400-600ms: moved from (893,1627) to (90,1664)

-800-2700ms: moved from (898,1071) to (898,1070)

-2900-3100ms: stationary pos=(898,1071)

-3300-3733ms: moved from (898,1008) to (282,66)

-3966-4400ms: stationary pos=(894,1248)

-4600-4600ms: stationary pos=(894,1354)

-15866-18000ms: moved from (576,718) to (319,53)

-23700-24300ms: moved from (686,1632) to (733,1507)

-24500-24500ms: stationary pos=(686,1632)

-28133-28333ms: moved from (733,1844) to (863,313)

-28533-30400ms: moved from (427,1314) to (918,1978)

-30633-31666ms: stationary pos=(188,2092)

-31866-32100ms: moved from (918,1978) to (961,2005)

-32333-32566ms: moved from (918,1978) to (50,1994)
... (143 more lines)
```

### cfs_home_loan_serene / segment_001
- standalone-c_1: 44 lines, standalone-d_1: 36 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,44 +1,36 @@
-16-250ms: stationary pos=(164,1393)

-483-2216ms: stationary pos=(620,1754)

-2416-2816ms: moved from (192,1950) to (72,2034)

-3016-3250ms: stationary pos=(72,2032)

-3483-3916ms: moved from (70,2076) to (72,2059)

-4516-6016ms: stationary pos=(612,1744)

-6516-7916ms: moved from (498,1927) to (612,1744)

-8116-9416ms: moved from (879,2089) to (463,854)

-10016-11116ms: stationary pos=(733,1507)

-11316-11516ms: moved from (733,1974) to (918,1978)

-11716-11916ms: moved from (286,2005) to (957,1169)

-12116-13416ms: stationary pos=(639,2056)

-13616-13816ms: moved from (957,1165) to (164,1464)

-14016-14216ms: stationary pos=(945,773)
... (127 more lines)
```

### cfs_home_loan_serene / segment_002
- standalone-c_1: 53 lines, standalone-d_1: 46 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -1,53 +1,46 @@
-3466-3700ms: moved from (781,1944) to (856,1995)

-3933-5433ms: stationary pos=(31,75)

+3533-5400ms: moved from (432,1858) to (31,75)

 6033-6533ms: stationary pos=(402,492)

-7033-8200ms: moved from (401,490) to (211,199)

-8433-10533ms: moved from (211,294) to (211,199)

-10733-11633ms: moved from (35,835) to (211,199)

-11833-12933ms: moved from (302,1169) to (211,199)

-13133-14000ms: moved from (35,863) to (35,902)

-14233-14633ms: stationary pos=(427,321)

-14833-15066ms: moved from (19,1770) to (19,1782)

-15300-15500ms: moved from (952,818) to (27,1106)

+7033-8333ms: moved from (401,490) to (211,243)

+8600-10466ms: moved from (211,207) to (42,1201)
... (160 more lines)
```

### cfs_home_loan_serene / segment_003
- standalone-c_1: 44 lines, standalone-d_1: 39 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_1)
@@ -1,44 +1,39 @@
-150-350ms: moved from (38,462) to (325,1483)

-550-1550ms: moved from (42,435) to (765,196)

+216-483ms: moved from (325,1483) to (42,435)

+1050-1550ms: stationary pos=(765,196)

 7050-9550ms: stationary pos=(765,196)

 10050-10850ms: stationary pos=(903,1029)

-11050-11250ms: stationary pos=(899,177)

-11450-13450ms: moved from (687,1467) to (899,177)

+11116-11383ms: moved from (899,177) to (569,770)

+11650-12716ms: stationary pos=(687,1471)

+12983-13516ms: stationary pos=(899,177)

 14050-14850ms: stationary pos=(319,53)

-15050-16850ms: stationary pos=(711,835)

-20850-21050ms: moved from (79,945) to (319,53)
... (125 more lines)
```

### flight_centre_booking_james / segment_000
- standalone-c_1: 11 lines, standalone-d_1: 11 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,11 +1,11 @@
-0-2100ms: moved from (144,17) to (980,712)

-10000-12000ms: stationary pos=(500,31)

-12500-15966ms: moved from (1636,21) to (500,31)

-16500-17100ms: stationary pos=(646,580)

-30500-31966ms: stationary pos=(500,29)

-32500-33100ms: stationary pos=(560,606)

-37000-39600ms: stationary pos=(1246,29)

-39800-40800ms: stationary pos=(1935,1001)

-41000-41400ms: moved from (1048,29) to (734,504)

+0-2033ms: moved from (144,17) to (980,712)

+10000-11866ms: stationary pos=(500,31)

+12500-15933ms: moved from (1636,21) to (500,31)

+16500-17033ms: stationary pos=(646,580)

+30500-31833ms: stationary pos=(500,29)
... (13 more lines)
```

### flight_centre_booking_james / segment_001
- standalone-c_1: 10 lines, standalone-d_1: 10 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,10 +1,10 @@
 16544-17344ms: stationary pos=(23,569)

-17544-17944ms: stationary pos=(1048,29)

+17611-17877ms: stationary pos=(1048,29)

 18544-19044ms: stationary pos=(557,514)

-19544-19744ms: moved from (1048,29) to (47,168)

-19944-21344ms: stationary pos=(1048,29)

-21544-24544ms: moved from (557,31) to (1327,21)

-25044-25644ms: moved from (871,1016) to (1399,1032)

-25844-27044ms: stationary pos=(221,29)

-27544-28144ms: stationary pos=(901,303)

-56044-57977ms: stationary pos=(439,29)
+19544-21411ms: stationary pos=(1048,29)

+21677-21944ms: stationary pos=(439,31)

+22544-24544ms: stationary pos=(1327,21)

+25044-25577ms: moved from (871,1016) to (1399,1032)

+25844-26911ms: stationary pos=(221,29)

+27544-28077ms: stationary pos=(901,303)

+56044-57911ms: stationary pos=(439,29)
```

### flight_centre_booking_james / segment_002
- standalone-c_1: 8 lines, standalone-d_1: 7 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -1,8 +1,7 @@
-20089-21489ms: stationary pos=(1160,808)

+20089-21422ms: stationary pos=(1160,808)

 22089-22589ms: stationary pos=(1361,478)

 23089-23889ms: stationary pos=(1160,808)

-24089-24489ms: moved from (439,29) to (547,29)

-31089-33089ms: stationary pos=(547,29)

-47089-48889ms: stationary pos=(765,29)

-52789-52989ms: stationary pos=(512,410)

-53189-53989ms: stationary pos=(439,29)
+24155-24422ms: stationary pos=(547,29)

+31089-32955ms: stationary pos=(547,29)

+47089-48689ms: stationary pos=(765,29)

+52855-53922ms: stationary pos=(439,29)
```

### flight_centre_booking_kay / segment_000
- standalone-c_1: 54 lines, standalone-d_1: 39 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,54 +1,39 @@
-200-600ms: moved from (209,248) to (1706,366)

-800-1000ms: moved from (48,360) to (147,255)

-1200-1400ms: moved from (209,215) to (139,215)

-1600-1800ms: moved from (64,408) to (17,618)

-2000-2200ms: moved from (1956,525) to (552,619)

-2400-2800ms: moved from (1377,25) to (29,248)

-3000-3800ms: moved from (480,1017) to (1935,457)

-4000-8300ms: moved from (1935,521) to (1935,904)

-8500-8700ms: moved from (790,585) to (209,935)

-8900-9300ms: moved from (352,991) to (209,931)

-9500-9500ms: stationary pos=(771,776)

-17500-19300ms: moved from (273,1017) to (771,751)

-19500-19700ms: moved from (153,966) to (592,871)

-19900-21000ms: stationary pos=(771,751)
... (155 more lines)
```

### flight_centre_booking_kay / segment_001
- standalone-c_1: 43 lines, standalone-d_1: 35 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,43 +1,35 @@
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

+261-794ms: stationary pos=(870,1031)
... (111 more lines)
```

### flight_centre_booking_kay / segment_002
- standalone-c_1: 39 lines, standalone-d_1: 28 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -1,39 +1,28 @@
 5522-6022ms: stationary pos=(1122,303)

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

-39322-39522ms: moved from (1954,840) to (1958,807)

-39722-39922ms: moved from (1600,960) to (1958,807)

-40122-40322ms: moved from (1954,840) to (1958,807)
... (97 more lines)
```

### flight_centre_booking_kay / segment_003
- standalone-c_1: 28 lines, standalone-d_1: 25 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_1)
@@ -1,28 +1,25 @@
-283-683ms: stationary pos=(75,879)

-883-1083ms: moved from (1958,840) to (1832,552)

-1283-2083ms: moved from (1919,439) to (1832,426)

-2283-2483ms: moved from (1490,1018) to (627,678)

-2683-2883ms: stationary pos=(958,334)

-3083-3283ms: moved from (1832,666) to (77,114)

-3483-3683ms: stationary pos=(178,416)

+283-816ms: stationary pos=(75,879)

+1083-1350ms: moved from (1832,552) to (958,334)

+1616-2150ms: moved from (1838,982) to (1832,426)

+2416-2950ms: stationary pos=(958,334)

+3216-3750ms: moved from (1489,836) to (178,416)

 4283-5783ms: stationary pos=(618,714)

-6283-6483ms: moved from (1096,306) to (120,922)
... (66 more lines)
```

### flight_centre_booking_kay / segment_004
- standalone-c_1: 41 lines, standalone-d_1: 28 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_1)
@@ -1,41 +1,28 @@
 6044-6844ms: stationary pos=(656,695)

-7044-7444ms: moved from (1824,585) to (1553,693)

+7111-7377ms: moved from (1553,697) to (162,525)

 7644-10044ms: moved from (1553,676) to (1461,303)

-10544-10744ms: moved from (1553,664) to (1962,197)

-10944-13144ms: moved from (1553,664) to (77,114)

-13344-14144ms: moved from (1299,871) to (1295,408)

-14344-14744ms: stationary pos=(1390,842)

-14944-17544ms: stationary pos=(1299,726)

+10544-10811ms: moved from (1553,664) to (1962,197)

+11077-12944ms: stationary pos=(77,114)

+13211-13477ms: stationary pos=(1299,871)

+13744-14277ms: moved from (1299,840) to (1299,687)

+14544-14811ms: moved from (1390,842) to (1390,827)
... (97 more lines)
```

### flight_centre_booking_kay / segment_005
- standalone-c_1: 35 lines, standalone-d_1: 33 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_1)
@@ -1,35 +1,33 @@
+172-1239ms: stationary pos=(1815,465)

 1805-2305ms: stationary pos=(481,762)

-2805-3805ms: stationary pos=(1815,465)

-4005-4205ms: moved from (1073,753) to (77,114)

-4405-4605ms: stationary pos=(184,342)

-4805-5205ms: moved from (184,344) to (77,114)

-17805-18005ms: moved from (794,858) to (883,875)

-18205-18605ms: moved from (881,863) to (736,347)

-18805-19005ms: moved from (868,925) to (1222,698)

-19205-19605ms: moved from (868,607) to (897,744)

-19805-19805ms: stationary pos=(1224,702)

-26305-27305ms: stationary pos=(701,478)

-27505-28305ms: moved from (1001,629) to (327,499)

-28505-29105ms: stationary pos=(950,601)
... (99 more lines)
```

### opportunity_list_ben / segment_000
- standalone-c_1: 27 lines, standalone-d_1: 24 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,27 +1,24 @@
 500-2000ms: stationary pos=(1185,888)

 2500-2500ms: stationary pos=(1182,890)

-6500-7399ms: stationary pos=(1179,896)

-7600-8000ms: stationary pos=(1261,836)

-27200-27633ms: stationary pos=(1251,850)

-27833-31000ms: moved from (1251,820) to (1254,808)

-48300-48900ms: stationary pos=(1290,818)

-49100-49500ms: stationary pos=(861,426)

-54500-54966ms: stationary pos=(1353,995)

-55199-55400ms: stationary pos=(870,170)

-55600-56233ms: stationary pos=(1737,74)

-56466-56699ms: stationary pos=(52,1032)

-56900-57100ms: moved from (822,290) to (1837,80)

-57300-57966ms: stationary pos=(1535,1019)
... (69 more lines)
```

### opportunity_list_ben / segment_001
- standalone-c_1: 82 lines, standalone-d_1: 59 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,82 +1,59 @@
-4-204ms: moved from (502,1065) to (1185,417)

-804-2304ms: stationary pos=(1837,81)

-2804-3438ms: moved from (1535,1019) to (1012,135)

-3638-4038ms: moved from (1288,194) to (888,645)

-4238-4471ms: moved from (727,939) to (801,939)

-4704-6504ms: stationary pos=(1140,551)

-6704-8704ms: stationary pos=(1176,772)

-8904-9104ms: moved from (778,1036) to (1102,341)

-9304-9504ms: moved from (878,335) to (951,814)

-9704-9904ms: stationary pos=(1835,81)

-10104-10904ms: moved from (847,524) to (939,738)

-11104-11504ms: stationary pos=(1005,656)

-11704-12104ms: moved from (1671,1045) to (1120,235)

-12304-12504ms: stationary pos=(871,335)
... (247 more lines)
```

### opportunity_list_ben / segment_002
- standalone-c_1: 58 lines, standalone-d_1: 54 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -1,58 +1,54 @@
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
... (173 more lines)
```

### opportunity_list_ben / segment_003
- standalone-c_1: 51 lines, standalone-d_1: 46 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_1)
@@ -1,51 +1,46 @@
 414-1214ms: stationary pos=(287,1068)

-1414-1814ms: stationary pos=(1155,553)

-2014-2614ms: stationary pos=(1678,297)

+1480-2547ms: moved from (1155,553) to (1678,297)

 2814-5214ms: stationary pos=(1561,153)

-5414-5614ms: moved from (1399,329) to (1856,800)

-5814-5814ms: stationary pos=(1720,327)

-10414-11414ms: stationary pos=(1193,866)

-20414-21014ms: stationary pos=(732,345)

-21247-21880ms: moved from (778,152) to (1165,780)

-22080-22514ms: moved from (238,769) to (374,717)

-22747-25914ms: moved from (1625,806) to (1298,718)

-26414-26814ms: stationary pos=(225,816)

-27014-28947ms: stationary pos=(1485,1070)
... (157 more lines)
```

### opportunity_list_ben / segment_004
- standalone-c_1: 52 lines, standalone-d_1: 47 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_1)
@@ -1,52 +1,47 @@
-219-652ms: stationary pos=(1266,616)

-885-1085ms: stationary pos=(862,585)

-1319-1552ms: stationary pos=(1266,598)

-1752-1952ms: moved from (862,585) to (169,441)

-2152-2385ms: moved from (1266,598) to (862,585)

-2585-2785ms: moved from (862,600) to (862,585)

-3019-3819ms: stationary pos=(1266,598)

-4019-4219ms: stationary pos=(111,920)

+219-485ms: stationary pos=(1266,616)

+752-1552ms: moved from (862,585) to (1266,598)

+1819-2085ms: stationary pos=(169,441)

+2352-2619ms: moved from (1266,598) to (862,600)

+2885-3685ms: stationary pos=(1266,598)

+3952-4219ms: stationary pos=(111,920)
... (148 more lines)
```

### opportunity_list_ben / segment_005
- standalone-c_1: 38 lines, standalone-d_1: 37 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_1)
@@ -1,38 +1,37 @@
 523-1523ms: stationary pos=(360,1043)

-2023-4623ms: moved from (702,199) to (1485,1070)

-4823-5223ms: stationary pos=(1064,409)

-5423-5823ms: stationary pos=(1485,1070)

-6023-6223ms: stationary pos=(604,251)

-6423-9023ms: stationary pos=(1183,281)

-9523-10623ms: stationary pos=(618,211)

+2023-2290ms: moved from (702,199) to (1485,1070)

+2557-4690ms: moved from (1183,810) to (1485,1070)

+4957-5223ms: stationary pos=(1064,409)

+5490-5757ms: stationary pos=(1485,1070)

+6023-8957ms: moved from (604,251) to (1183,281)

+9523-10557ms: stationary pos=(618,211)

 10823-11623ms: moved from (724,167) to (983,786)
... (103 more lines)
```

### opportunity_list_ben / segment_006
- standalone-c_1: 39 lines, standalone-d_1: 40 lines
```diff
--- segment_006 (standalone-c_1)
+++ segment_006 (standalone-d_1)
@@ -1,39 +1,40 @@
-28-228ms: moved from (633,915) to (1837,80)

-428-1228ms: stationary pos=(407,1037)

+161-1228ms: moved from (633,915) to (407,1037)

 1828-5128ms: stationary pos=(940,513)

-5328-6728ms: moved from (940,183) to (1000,471)

+5395-6728ms: moved from (940,183) to (1000,471)

 7328-8328ms: stationary pos=(983,786)

-8828-9828ms: stationary pos=(1910,281)

-10028-11028ms: moved from (1469,1048) to (1910,281)

-11228-11828ms: stationary pos=(788,794)

+8828-9628ms: stationary pos=(1910,281)

+9895-10961ms: moved from (1469,1048) to (1910,281)

+11228-11761ms: stationary pos=(788,794)

 12328-12828ms: stationary pos=(983,786)
... (117 more lines)
```

### opportunity_list_georgie / segment_000
- standalone-c_1: 72 lines, standalone-d_1: 67 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,72 +1,67 @@
-0-1200ms: moved from (10,13) to (1813,86)

-1400-1600ms: moved from (1133,285) to (1909,750)

-1800-2000ms: moved from (1263,870) to (1812,84)

-2200-3400ms: moved from (7,78) to (1812,84)

-3600-4000ms: moved from (1224,774) to (1812,84)

-4200-4600ms: stationary pos=(840,293)

-4800-5000ms: moved from (1812,84) to (1760,955)

-5200-5400ms: stationary pos=(1812,84)

-5600-5800ms: moved from (1104,781) to (1768,821)

-6000-6600ms: moved from (312,876) to (1072,813)

-6800-7000ms: stationary pos=(1455,863)

-7200-7433ms: moved from (184,908) to (128,910)

-7666-7899ms: moved from (1812,84) to (288,809)

-8100-8300ms: moved from (999,781) to (519,372)
... (241 more lines)
```

### opportunity_list_georgie / segment_001
- standalone-c_1: 22 lines, standalone-d_1: 19 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,22 +1,19 @@
 3906-5906ms: stationary pos=(1103,545)

 6406-7206ms: stationary pos=(1204,1001)

-7406-7806ms: moved from (1073,313) to (1073,344)

-8006-8206ms: stationary pos=(1073,313)

-8406-8606ms: moved from (1343,603) to (469,713)

-8806-8806ms: stationary pos=(1343,605)

-14906-15506ms: stationary pos=(1300,815)

-15706-16106ms: moved from (1698,823) to (1842,815)

-16306-16306ms: stationary pos=(1846,107)

-23906-25906ms: moved from (1846,107) to (1872,759)

+7473-7740ms: stationary pos=(1073,311)

+8006-8273ms: moved from (1073,313) to (1054,313)

+8540-8806ms: stationary pos=(1343,606)

+14906-15440ms: stationary pos=(1300,815)
... (45 more lines)
```

### opportunity_list_georgie / segment_002
- standalone-c_1: 57 lines, standalone-d_1: 50 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -1,57 +1,50 @@
 6313-7113ms: stationary pos=(1795,698)

-7313-9313ms: stationary pos=(906,107)

-9513-10313ms: moved from (906,107) to (1844,104)

-10513-10713ms: stationary pos=(1795,698)

-10913-11513ms: stationary pos=(1696,820)

-11713-11913ms: stationary pos=(1060,480)

-12113-13313ms: stationary pos=(1696,820)

+7380-8813ms: stationary pos=(906,107)

+9313-10380ms: moved from (906,107) to (1844,104)

+10646-11446ms: moved from (1795,698) to (1696,820)

+11713-13313ms: moved from (1060,480) to (1696,820)

 17813-18613ms: stationary pos=(1135,725)

-18813-19213ms: stationary pos=(31,23)

-26313-27713ms: stationary pos=(1795,698)
... (173 more lines)
```

### opportunity_list_georgie / segment_003
- standalone-c_1: 49 lines, standalone-d_1: 45 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_1)
@@ -1,49 +1,45 @@
-186-386ms: stationary pos=(1184,376)

-586-1253ms: moved from (1184,360) to (1184,374)

-1486-3186ms: stationary pos=(1721,103)

+53-320ms: stationary pos=(1184,376)

+586-1120ms: moved from (1184,360) to (1184,378)

+1386-2986ms: moved from (1708,90) to (1721,103)

 3720-4220ms: stationary pos=(1104,322)

-4720-6820ms: stationary pos=(1844,107)

-7053-7686ms: stationary pos=(1872,759)

+4720-5786ms: stationary pos=(1844,107)

+6053-6853ms: moved from (889,601) to (1844,107)

+7120-7653ms: stationary pos=(1872,759)

 8220-10586ms: moved from (1697,821) to (1854,700)

-15486-18186ms: stationary pos=(1894,954)
... (149 more lines)
```

### opportunity_list_georgie / segment_004
- standalone-c_1: 62 lines, standalone-d_1: 51 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_1)
@@ -1,62 +1,51 @@
-1226-1426ms: moved from (867,409) to (1071,457)

-1626-1826ms: moved from (798,376) to (1255,551)

-2026-2026ms: stationary pos=(748,394)

-21726-22326ms: stationary pos=(1060,222)

-22526-23126ms: stationary pos=(932,220)

+1226-1493ms: moved from (867,409) to (1024,472)

+1760-2026ms: moved from (794,376) to (748,394)

+21726-21993ms: stationary pos=(1060,222)

+22260-23060ms: moved from (1060,220) to (932,220)

 23626-24626ms: stationary pos=(1080,714)

 25126-25926ms: moved from (758,344) to (817,43)

-26126-26526ms: moved from (752,551) to (1073,445)

-26726-26926ms: moved from (1068,536) to (1073,445)

-27126-27326ms: moved from (1067,395) to (861,358)
... (177 more lines)
```

### opportunity_list_georgie / segment_005
- standalone-c_1: 41 lines, standalone-d_1: 40 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_1)
@@ -1,41 +1,40 @@
 33-833ms: stationary pos=(897,394)

-1033-1433ms: stationary pos=(1161,387)

+1100-1366ms: stationary pos=(1161,387)

 2033-2833ms: moved from (1072,441) to (938,517)

-3033-3233ms: moved from (1017,492) to (936,691)

-3433-3633ms: moved from (936,845) to (879,488)

-3833-4033ms: moved from (1177,452) to (879,488)

-4233-4433ms: moved from (959,447) to (905,781)

-4633-4833ms: moved from (779,488) to (1165,488)

-5033-5233ms: stationary pos=(936,370)

-5433-7533ms: moved from (808,466) to (936,370)

-8033-9233ms: stationary pos=(1152,723)

-9433-10233ms: stationary pos=(1255,285)

-10433-11233ms: moved from (928,488) to (1255,285)
... (119 more lines)
```

### opportunity_list_georgie / segment_006
- standalone-c_1: 46 lines, standalone-d_1: 38 lines
```diff
--- segment_006 (standalone-c_1)
+++ segment_006 (standalone-d_1)
@@ -1,46 +1,38 @@
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

+440-2206ms: stationary pos=(1025,913)

+2473-2740ms: stationary pos=(743,957)

+3006-3273ms: moved from (743,955) to (1024,910)

+3539-3539ms: stationary pos=(1192,789)
... (127 more lines)
```

### opportunity_list_georgie / segment_007
- standalone-c_1: 28 lines, standalone-d_1: 26 lines
```diff
--- segment_007 (standalone-c_1)
+++ segment_007 (standalone-d_1)
@@ -1,28 +1,26 @@
-4346-4746ms: stationary pos=(744,987)

-4980-5813ms: stationary pos=(1202,102)

+4346-4613ms: stationary pos=(744,987)

+4880-5680ms: stationary pos=(1202,102)

 6346-6846ms: stationary pos=(921,772)

-7346-8580ms: stationary pos=(20,86)

-8813-12980ms: moved from (21,88) to (1017,666)

-13180-14046ms: stationary pos=(898,402)

-14279-15779ms: stationary pos=(1129,779)

+7346-8413ms: stationary pos=(20,86)

+8680-12880ms: moved from (21,88) to (1017,666)

+13146-13946ms: stationary pos=(898,402)

+14213-15813ms: stationary pos=(1129,779)

 16346-17846ms: stationary pos=(1120,429)
... (69 more lines)
```

### opportunity_list_georgie / segment_008
- standalone-c_1: 58 lines, standalone-d_1: 49 lines
```diff
--- segment_008 (standalone-c_1)
+++ segment_008 (standalone-d_1)
@@ -1,58 +1,49 @@
-53-653ms: stationary pos=(1060,220)

-6253-7253ms: stationary pos=(1182,784)

-7453-8253ms: stationary pos=(955,841)

-8453-9053ms: stationary pos=(1105,737)

-9253-9453ms: stationary pos=(932,220)

-9653-9853ms: moved from (1042,536) to (750,295)

-10053-10453ms: stationary pos=(932,220)

-10653-11653ms: moved from (1060,218) to (932,220)

+53-586ms: stationary pos=(1060,220)

+6253-7053ms: stationary pos=(1182,784)

+7320-8120ms: stationary pos=(955,841)

+8386-8920ms: stationary pos=(1105,733)

+9186-9453ms: stationary pos=(932,220)

+9720-11586ms: moved from (750,295) to (932,220)
... (179 more lines)
```

### opportunity_list_georgie / segment_009
- standalone-c_1: 57 lines, standalone-d_1: 49 lines
```diff
--- segment_009 (standalone-c_1)
+++ segment_009 (standalone-d_1)
@@ -1,57 +1,49 @@
-160-360ms: moved from (964,634) to (1064,426)

-560-2360ms: moved from (1072,692) to (930,698)

-2560-2760ms: moved from (1161,394) to (930,698)

-2960-3160ms: moved from (979,377) to (930,698)

-3660-5560ms: stationary pos=(871,573)

-14160-15660ms: stationary pos=(944,533)

+226-493ms: moved from (977,763) to (816,119)

+760-2360ms: moved from (1032,696) to (930,698)

+2626-2893ms: moved from (1080,410) to (979,377)

+3160-5426ms: moved from (930,698) to (871,573)

+5693-5693ms: stationary pos=(1135,695)

+14226-15660ms: stationary pos=(944,533)

 16160-16960ms: stationary pos=(1072,863)

-17160-17560ms: stationary pos=(940,527)
... (177 more lines)
```

### opportunity_list_georgie / segment_010
- standalone-c_1: 57 lines, standalone-d_1: 44 lines
```diff
--- segment_010 (standalone-c_1)
+++ segment_010 (standalone-d_1)
@@ -1,57 +1,44 @@
-66-466ms: moved from (1090,335) to (948,235)

-666-866ms: moved from (918,306) to (747,316)

-1066-1266ms: moved from (1090,290) to (814,119)

-1466-1866ms: stationary pos=(871,657)

-2066-2666ms: stationary pos=(1076,450)

-2866-3066ms: moved from (877,712) to (1107,368)

-3266-3666ms: stationary pos=(1096,515)

-3866-4066ms: moved from (1176,306) to (877,712)

-4266-4866ms: moved from (1206,192) to (877,712)

-5066-5266ms: moved from (924,232) to (877,712)

-5466-5666ms: moved from (967,328) to (877,712)

-5866-6866ms: moved from (1092,515) to (1086,515)

-7066-7466ms: moved from (1186,251) to (1086,515)

-7666-8466ms: stationary pos=(20,89)
... (167 more lines)
```

### opportunity_list_georgie / segment_011
- standalone-c_1: 45 lines, standalone-d_1: 31 lines
```diff
--- segment_011 (standalone-c_1)
+++ segment_011 (standalone-d_1)
@@ -1,45 +1,31 @@
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
... (121 more lines)
```

### opportunity_list_georgie / segment_012
- standalone-c_1: 11 lines, standalone-d_1: 11 lines
```diff
--- segment_012 (standalone-c_1)
+++ segment_012 (standalone-d_1)
@@ -1,11 +1,11 @@
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
+1846-3180ms: moved from (1173,683) to (874,128)

+9380-9913ms: stationary pos=(758,457)

+10180-10713ms: moved from (1255,427) to (1073,344)

... (15 more lines)
```

### opportunity_list_georgie / segment_013
- standalone-c_1: 36 lines, standalone-d_1: 30 lines
```diff
--- segment_013 (standalone-c_1)
+++ segment_013 (standalone-d_1)
@@ -1,36 +1,30 @@
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
... (101 more lines)
```

### opportunity_list_georgie / segment_014
- standalone-c_1: 60 lines, standalone-d_1: 54 lines
```diff
--- segment_014 (standalone-c_1)
+++ segment_014 (standalone-d_1)
@@ -1,60 +1,54 @@
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
... (190 more lines)
```

### travel_expert_lisa / segment_000
- standalone-c_1: 22 lines, standalone-d_1: 20 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,22 +1,20 @@
 0-509ms: stationary pos=(40,265)

-577-781ms: stationary pos=(40,360)

-985-1393ms: moved from (39,899) to (37,393)

-1597-1801ms: stationary pos=(32,152)

-38651-40521ms: stationary pos=(1610,6)

+577-1121ms: stationary pos=(40,360)

+1393-1393ms: stationary pos=(37,393)

+38651-40589ms: stationary pos=(1610,6)

 40725-42866ms: stationary pos=(945,782)

 42934-45790ms: stationary pos=(1610,6)

 45994-48475ms: stationary pos=(1200,422)

-48713-49121ms: moved from (1664,1035) to (470,1116)

-49325-49529ms: stationary pos=(986,448)

-49733-50175ms: moved from (274,57) to (609,564)
... (38 more lines)
```

### travel_expert_lisa / segment_001
- standalone-c_1: 41 lines, standalone-d_1: 37 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,41 +1,37 @@
 70-614ms: stationary pos=(1737,182)

-2008-2654ms: stationary pos=(1610,6)

+2008-2586ms: stationary pos=(1610,6)

 3028-3538ms: stationary pos=(531,834)

-3606-5067ms: stationary pos=(1610,6)

-5135-6359ms: stationary pos=(1025,626)

+3606-5000ms: stationary pos=(1610,6)

+5135-6291ms: stationary pos=(1025,626)

 6563-8331ms: stationary pos=(19,368)

-9283-10541ms: stationary pos=(19,386)

-10745-11152ms: stationary pos=(561,416)

-11356-13532ms: stationary pos=(19,386)

-13736-13940ms: moved from (470,1116) to (737,744)

-14144-14348ms: moved from (470,1116) to (784,742)
... (115 more lines)
```

### travel_expert_lisa / segment_002
- standalone-c_1: 44 lines, standalone-d_1: 40 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -1,44 +1,40 @@
-2484-4456ms: moved from (150,313) to (1509,677)

-4660-5475ms: moved from (154,802) to (1025,626)

-5679-6699ms: stationary pos=(757,624)

+2552-2824ms: moved from (1095,368) to (568,1014)

+3164-4456ms: stationary pos=(1509,677)

+4728-5543ms: stationary pos=(1025,626)

+5815-6699ms: stationary pos=(757,624)

 14144-17679ms: stationary pos=(1561,988)

-17883-18087ms: stationary pos=(1580,1055)

-18325-18529ms: moved from (1561,984) to (353,1016)

-22031-22269ms: moved from (1666,265) to (1561,988)

-22473-22677ms: moved from (1520,497) to (113,761)

-22881-23084ms: stationary pos=(1520,497)

-23288-23492ms: moved from (1561,988) to (113,521)
... (124 more lines)
```

### travel_expert_lisa / segment_003
- standalone-c_1: 28 lines, standalone-d_1: 21 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_1)
@@ -1,28 +1,21 @@
 342-886ms: stationary pos=(137,148)

-1056-2416ms: stationary pos=(1610,6)

-2484-3878ms: moved from (49,182) to (1610,6)

+1056-2246ms: stationary pos=(1610,6)

+2484-3776ms: moved from (49,182) to (1610,6)

 4048-5067ms: stationary pos=(1612,390)

 5135-6903ms: stationary pos=(1610,6)

-7515-8773ms: stationary pos=(1478,959)

-9045-9487ms: moved from (1610,6) to (1478,869)

+7515-8603ms: stationary pos=(1478,959)

+9045-9351ms: moved from (1610,6) to (1478,884)

 9725-9997ms: moved from (1610,6) to (1478,867)

-10235-12512ms: moved from (1610,6) to (1478,805)

+10303-12512ms: moved from (1610,6) to (1478,805)
... (55 more lines)
```

### travel_expert_lisa / segment_004
- standalone-c_1: 51 lines, standalone-d_1: 41 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_1)
@@ -1,51 +1,41 @@
-6427-6631ms: stationary pos=(566,523)

-6835-6835ms: stationary pos=(1385,1016)

-15776-17679ms: stationary pos=(1610,6)

+15776-17747ms: stationary pos=(1610,6)

 26416-27232ms: stationary pos=(1610,6)

-27436-27844ms: stationary pos=(1478,700)

-28048-28456ms: moved from (1478,762) to (1478,963)

-28660-29849ms: moved from (1610,6) to (1478,875)

-30053-30563ms: stationary pos=(1610,6)

-30665-30665ms: stationary pos=(1667,220)

-40286-40966ms: moved from (1076,988) to (1610,6)

-41169-44331ms: moved from (455,665) to (1610,6)

+27504-27776ms: stationary pos=(1478,700)

+28048-28320ms: moved from (1478,762) to (1610,6)
... (151 more lines)
```

### travel_expert_lisa / segment_005
- standalone-c_1: 34 lines, standalone-d_1: 28 lines
```diff
--- segment_005 (standalone-c_1)
+++ segment_005 (standalone-d_1)
@@ -1,34 +1,28 @@
-172-376ms: moved from (36,169) to (409,1048)

-580-3300ms: stationary pos=(36,169)

-3504-3708ms: stationary pos=(448,1016)

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

+240-2722ms: moved from (409,1048) to (36,169)
... (88 more lines)
```

### travel_expert_lisa / segment_006
- standalone-c_1: 6 lines, standalone-d_1: 5 lines
```diff
--- segment_006 (standalone-c_1)
+++ segment_006 (standalone-d_1)
@@ -1,6 +1,5 @@
 77917-78801ms: stationary pos=(1478,541)

-79039-79243ms: moved from (1478,652) to (974,176)

-79311-80331ms: stationary pos=(120,332)

-80705-81351ms: stationary pos=(1610,6)

-81555-81759ms: moved from (974,260) to (1478,899)

-82269-82915ms: stationary pos=(1610,6)
+79107-80331ms: moved from (1072,502) to (120,332)

+80705-81113ms: stationary pos=(1610,6)

+81419-81691ms: moved from (974,271) to (1478,903)

+82269-82847ms: stationary pos=(1610,6)
```

### travel_expert_lisa / segment_007
- standalone-c_1: 52 lines, standalone-d_1: 40 lines
```diff
--- segment_007 (standalone-c_1)
+++ segment_007 (standalone-d_1)
@@ -1,52 +1,40 @@
 5000-5883ms: stationary pos=(1478,541)

-6121-6325ms: moved from (1478,652) to (974,176)

-6393-7413ms: stationary pos=(120,332)

-7787-8433ms: stationary pos=(1610,6)

-8637-8841ms: moved from (974,260) to (1478,899)

+6189-7413ms: moved from (1072,502) to (120,332)

+7787-8195ms: stationary pos=(1610,6)

+8501-8773ms: moved from (974,271) to (1478,903)

 9351-10201ms: stationary pos=(1610,6)

 10405-11458ms: stationary pos=(1220,1001)

-18427-18869ms: stationary pos=(341,1007)

-19073-20093ms: stationary pos=(259,980)

-20331-20535ms: moved from (257,937) to (448,712)

-20739-20943ms: moved from (1460,896) to (564,937)
... (141 more lines)
```

### travel_expert_lisa / segment_008
- standalone-c_1: 13 lines, standalone-d_1: 13 lines
```diff
--- segment_008 (standalone-c_1)
+++ segment_008 (standalone-d_1)
@@ -1,11 +1,11 @@
 172-1770ms: stationary pos=(739,596)

-1804-3606ms: stationary pos=(1610,6)

+1804-3368ms: stationary pos=(1610,6)

 3810-5815ms: stationary pos=(171,317)

-6053-7175ms: moved from (171,328) to (143,233)

-7413-7617ms: moved from (143,345) to (143,184)

-7855-8263ms: moved from (1614,905) to (143,345)

-8467-8977ms: stationary pos=(634,995)

-9215-16116ms: moved from (1616,842) to (1610,6)

+6121-7175ms: moved from (1764,881) to (143,233)

+7617-7923ms: moved from (143,184) to (143,233)

+8195-8977ms: moved from (143,184) to (634,995)

+10099-13124ms: stationary pos=(1616,836)

+14144-16116ms: stationary pos=(1610,6)

 17135-18121ms: stationary pos=(1616,838)

 19141-19141ms: stationary pos=(1616,834)

 23832-24444ms: stationary pos=(1095,1125)

```

### travel_expert_veronika / segment_000
- standalone-c_1: 62 lines, standalone-d_1: 56 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,62 +1,56 @@
-0-1001ms: stationary pos=(956,326)

-1234-1434ms: stationary pos=(569,344)

-1685-1885ms: moved from (656,698) to (441,1003)

-2085-2535ms: moved from (263,813) to (656,698)

-2736-2936ms: stationary pos=(646,358)

-3136-3336ms: moved from (1666,947) to (1211,873)

-3536-3737ms: moved from (1736,1051) to (863,366)

-3937-5405ms: stationary pos=(837,380)

-5605-6006ms: stationary pos=(759,749)

-6206-6406ms: moved from (1310,328) to (933,747)

-6606-7674ms: stationary pos=(1506,858)

-7941-8208ms: stationary pos=(1361,826)

-8475-8725ms: moved from (1025,826) to (1073,842)

-8925-9125ms: moved from (512,954) to (175,874)
... (188 more lines)
```

### travel_expert_veronika / segment_001
- standalone-c_1: 51 lines, standalone-d_1: 39 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,51 +1,39 @@
-151-952ms: stationary pos=(974,520)

+85-885ms: stationary pos=(974,520)

 5390-7242ms: stationary pos=(515,338)

 7442-9044ms: stationary pos=(978,626)

-9110-9511ms: stationary pos=(515,338)

-9961-10195ms: moved from (1079,357) to (1088,312)

-10562-11329ms: stationary pos=(1079,357)

+9110-9644ms: stationary pos=(515,338)

+9961-11329ms: stationary pos=(1079,357)

 11830-12330ms: stationary pos=(1110,336)

 12430-12747ms: stationary pos=(869,352)

-13048-13998ms: stationary pos=(769,1034)

+13048-13898ms: stationary pos=(769,1034)

 14199-14983ms: moved from (604,500) to (769,1034)
... (130 more lines)
```

### travel_expert_veronika / segment_002
- standalone-c_1: 38 lines, standalone-d_1: 35 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -3,36 +3,33 @@
 10485-10485ms: stationary pos=(988,246)

 19077-23648ms: stationary pos=(1304,971)

 24382-24749ms: moved from (1252,793) to (128,713)

-25050-25717ms: stationary pos=(1190,344)

-26134-26334ms: moved from (264,326) to (929,521)

+25050-25583ms: stationary pos=(1190,344)

+26134-26401ms: stationary pos=(264,326)

 26735-27786ms: stationary pos=(988,246)

 28019-28370ms: moved from (352,12) to (264,326)

-28703-29487ms: moved from (1148,713) to (1795,376)

-33792-34626ms: stationary pos=(1707,136)

+28703-29003ms: moved from (1148,713) to (1795,378)

+29320-34626ms: stationary pos=(1705,136)

 34943-35510ms: moved from (416,971) to (1346,408)
... (85 more lines)
```

### travel_expert_veronika / segment_003
- standalone-c_1: 49 lines, standalone-d_1: 44 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_1)
@@ -1,49 +1,44 @@
 4886-5670ms: stationary pos=(945,825)

-5904-6104ms: moved from (945,585) to (1667,140)

-6304-6721ms: moved from (256,1068) to (1394,793)

+5970-6237ms: moved from (1108,537) to (1280,845)

+6504-6771ms: moved from (256,1064) to (1394,793)

 6938-7439ms: stationary pos=(1667,664)

 7505-7756ms: moved from (1394,793) to (256,1064)

-7956-8156ms: moved from (1394,793) to (1891,170)

-8373-8573ms: moved from (1891,134) to (1891,202)

-8773-8973ms: moved from (1522,837) to (1891,218)

-9174-9391ms: stationary pos=(915,214)

-9607-10675ms: moved from (915,216) to (1891,198)

-10875-12127ms: moved from (915,218) to (721,280)

+8023-8306ms: stationary pos=(1891,170)
... (140 more lines)
```

### travel_expert_veronika / segment_004
- standalone-c_1: 50 lines, standalone-d_1: 46 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_1)
@@ -1,11 +1,10 @@
-3525-3758ms: moved from (242,621) to (288,280)

-3975-4376ms: stationary pos=(1042,472)

-4592-6027ms: stationary pos=(1079,263)

+3525-3825ms: moved from (242,621) to (356,743)

+4109-4376ms: stationary pos=(1042,472)

+4642-6027ms: stationary pos=(1079,263)

 7028-8480ms: moved from (585,500) to (731,503)

-10098-12367ms: stationary pos=(289,363)

+10098-12167ms: stationary pos=(289,363)

 12417-13201ms: moved from (350,122) to (289,363)

-13401-13752ms: stationary pos=(793,281)

-14769-14769ms: stationary pos=(289,363)

+13752-14769ms: moved from (793,281) to (289,363)

 19040-20025ms: moved from (557,621) to (495,126)
... (126 more lines)
```

### travel_expert_william / segment_000
- standalone-c_1: 37 lines, standalone-d_1: 34 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,37 +1,34 @@
 0-1158ms: stationary pos=(934,452)

-1524-1724ms: moved from (542,456) to (1782,155)

-1924-2124ms: moved from (615,452) to (809,20)

-2324-2524ms: stationary pos=(1782,155)

-2724-2940ms: moved from (88,93) to (1782,155)

-3140-3340ms: moved from (93,83) to (1782,155)

-3540-3807ms: moved from (1831,1068) to (1182,925)

-4008-4674ms: moved from (446,852) to (1784,155)

-4874-6049ms: moved from (1080,483) to (1784,153)

-6172-8163ms: stationary pos=(620,465)

+1524-1791ms: moved from (542,456) to (807,5)

+2057-2324ms: stationary pos=(1782,155)

+2591-2873ms: moved from (232,947) to (1148,766)

+3140-3407ms: moved from (93,83) to (1231,958)
... (93 more lines)
```

### travel_expert_william / segment_001
- standalone-c_1: 16 lines, standalone-d_1: 17 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,16 +1,17 @@
 22616-22890ms: stationary pos=(336,355)

 23162-23463ms: moved from (1415,469) to (197,781)

-23699-23904ms: moved from (1299,431) to (760,338)

-24166-24384ms: moved from (662,1072) to (760,338)

-24601-24907ms: moved from (563,854) to (752,514)

-25166-25987ms: moved from (578,765) to (1423,929)

-26658-33814ms: stationary pos=(1388,553)

-37526-38110ms: stationary pos=(856,619)

-38374-38811ms: moved from (1507,319) to (1161,814)

-52480-52702ms: moved from (1472,335) to (1767,678)

-52903-53777ms: moved from (1472,335) to (1767,680)

+23756-24037ms: moved from (514,863) to (723,1070)

+24384-24664ms: moved from (760,338) to (690,1074)

+25045-25166ms: moved from (752,514) to (578,765)
... (28 more lines)
```

### travel_expert_william / segment_002
- standalone-c_1: 48 lines, standalone-d_1: 45 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -1,48 +1,45 @@
 6220-7660ms: stationary pos=(1767,680)

 7750-8273ms: stationary pos=(184,718)

-8434-8903ms: stationary pos=(1767,680)

-9333-9790ms: stationary pos=(133,303)

+8434-8753ms: stationary pos=(1767,680)

+9333-9895ms: stationary pos=(133,303)

 9962-11548ms: stationary pos=(383,28)

-11664-12097ms: stationary pos=(133,303)

-12298-12546ms: stationary pos=(114,303)

-12746-12946ms: moved from (915,157) to (114,303)

+11664-11926ms: moved from (133,303) to (915,157)

+12196-12479ms: stationary pos=(114,303)

+12746-13012ms: stationary pos=(915,157)

 13147-13679ms: stationary pos=(1215,571)
... (121 more lines)
```

### travel_expert_william / segment_003
- standalone-c_1: 44 lines, standalone-d_1: 42 lines
```diff
--- segment_003 (standalone-c_1)
+++ segment_003 (standalone-d_1)
@@ -1,44 +1,42 @@
-39-504ms: stationary pos=(793,732)

+167-504ms: stationary pos=(793,731)

 853-1296ms: moved from (793,728) to (793,597)

 1641-1641ms: stationary pos=(184,456)

 7088-7572ms: stationary pos=(843,333)

-8300-8517ms: stationary pos=(596,770)

-8990-9300ms: moved from (114,700) to (833,1038)

-9524-12291ms: moved from (1701,489) to (1689,252)

-12586-24721ms: moved from (1689,1083) to (1689,264)

+8300-8990ms: moved from (596,770) to (114,700)

+9300-9524ms: moved from (833,1038) to (1701,489)

+9585-11709ms: stationary pos=(1689,303)

+12018-24911ms: moved from (1689,292) to (1689,264)

 25033-25739ms: moved from (543,909) to (395,452)
... (109 more lines)
```

### travel_expert_william / segment_004
- standalone-c_1: 34 lines, standalone-d_1: 35 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_1)
@@ -1,34 +1,35 @@
 5239-7252ms: stationary pos=(1847,483)

 7589-7781ms: moved from (1667,190) to (543,368)

-8320-8677ms: moved from (543,347) to (1667,190)

-8936-9299ms: moved from (1847,483) to (1081,1073)

-9606-10379ms: moved from (934,1073) to (1847,483)

+8320-8813ms: moved from (543,347) to (1667,190)

+9299-9606ms: moved from (1081,1073) to (934,1073)

+9856-10379ms: stationary pos=(1847,483)

 10729-10729ms: stationary pos=(1325,153)

 18027-19310ms: stationary pos=(543,900)

 19502-20617ms: stationary pos=(1847,483)

 27973-29377ms: stationary pos=(543,571)

-33832-34610ms: moved from (313,548) to (313,524)

-35639-35921ms: stationary pos=(1847,483)
... (89 more lines)
```

### travel_learner_sophia_jayde / segment_000
- standalone-c_1: 31 lines, standalone-d_1: 26 lines
```diff
--- segment_000 (standalone-c_1)
+++ segment_000 (standalone-d_1)
@@ -1,31 +1,26 @@
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

-9552-9756ms: moved from (695,533) to (695,501)

-9994-10232ms: stationary pos=(695,533)

-10470-10674ms: stationary pos=(695,501)

-10912-11150ms: stationary pos=(695,533)
... (79 more lines)
```

### travel_learner_sophia_jayde / segment_001
- standalone-c_1: 31 lines, standalone-d_1: 28 lines
```diff
--- segment_001 (standalone-c_1)
+++ segment_001 (standalone-d_1)
@@ -1,31 +1,28 @@
-201-2070ms: stationary pos=(1763,12)

+201-2138ms: stationary pos=(1763,12)

 14546-15600ms: stationary pos=(938,841)

 15668-18150ms: stationary pos=(1763,12)

 18252-19849ms: stationary pos=(938,841)

-29028-30388ms: stationary pos=(1763,12)

+29028-30218ms: stationary pos=(1763,12)

 30524-33685ms: stationary pos=(286,217)

-37186-39566ms: moved from (1498,955) to (1763,12)

+37186-39498ms: moved from (1498,955) to (1763,12)

 39702-40246ms: stationary pos=(413,1078)

-48609-48813ms: stationary pos=(761,423)

-49016-49220ms: moved from (830,423) to (761,423)

-49424-49662ms: moved from (830,423) to (761,423)
... (77 more lines)
```

### travel_learner_sophia_jayde / segment_002
- standalone-c_1: 16 lines, standalone-d_1: 12 lines
```diff
--- segment_002 (standalone-c_1)
+++ segment_002 (standalone-d_1)
@@ -1,16 +1,12 @@
-5532-6110ms: stationary pos=(23,232)

-6212-7640ms: stationary pos=(1763,12)

+5600-6110ms: stationary pos=(23,232)

+6212-7708ms: stationary pos=(1763,12)

 7776-8796ms: stationary pos=(23,393)

 8864-11345ms: stationary pos=(1763,12)

-11481-12127ms: stationary pos=(23,361)

-12331-12637ms: stationary pos=(286,297)

-12875-13079ms: moved from (23,361) to (286,297)

-13283-14099ms: moved from (23,361) to (139,959)

-34427-34903ms: moved from (327,454) to (1763,12)

-35447-35447ms: stationary pos=(303,1112)

-57339-58155ms: stationary pos=(1414,673)

-58393-59277ms: stationary pos=(1763,12)
... (23 more lines)
```

### travel_learner_sophia_jayde / segment_004
- standalone-c_1: 3 lines, standalone-d_1: 3 lines
```diff
--- segment_004 (standalone-c_1)
+++ segment_004 (standalone-d_1)
@@ -1,3 +1,3 @@
-34756-35266ms: stationary pos=(119,14)

+34858-35266ms: stationary pos=(119,14)

 35334-36184ms: stationary pos=(30,10)

-36388-36388ms: stationary pos=(1765,9)
+36456-36456ms: stationary pos=(1765,9)
```

### travel_learner_sophia_jayde / segment_010
- standalone-c_1: 6 lines, standalone-d_1: 6 lines
```diff
--- segment_010 (standalone-c_1)
+++ segment_010 (standalone-d_1)
@@ -1,6 +1,6 @@
 29249-29691ms: stationary pos=(1736,505)

-29929-30541ms: moved from (1549,710) to (1568,305)

-30813-31016ms: moved from (462,727) to (606,1000)

-31220-31458ms: moved from (22,844) to (897,598)

-31662-31866ms: moved from (309,871) to (998,888)

-32070-32274ms: moved from (1432,825) to (1446,824)
+29997-30269ms: moved from (1568,305) to (1549,710)

+30541-30813ms: moved from (1568,305) to (462,727)

+31084-31390ms: moved from (1291,966) to (606,1032)

+31662-31934ms: moved from (309,871) to (1432,827)

+32206-32206ms: stationary pos=(1654,538)
```

### travel_learner_sophia_jayde / segment_011
- standalone-c_1: 5 lines, standalone-d_1: 4 lines
```diff
--- segment_011 (standalone-c_1)
+++ segment_011 (standalone-d_1)
@@ -1,5 +1,4 @@
-56099-57594ms: stationary pos=(1654,785)

-78909-79589ms: stationary pos=(1654,785)

-79827-80031ms: moved from (1050,680) to (1758,264)

-80235-80235ms: stationary pos=(794,1110)

+56099-57526ms: stationary pos=(1654,785)

+78909-79521ms: stationary pos=(1654,785)

+79827-80235ms: moved from (1050,680) to (794,1110)

 83974-83974ms: stationary pos=(1065,712)
```

### travel_learner_sophia_jayde / segment_012
- standalone-c_1: 19 lines, standalone-d_1: 14 lines
```diff
--- segment_012 (standalone-c_1)
+++ segment_012 (standalone-d_1)
@@ -1,19 +1,14 @@
-4898-5577ms: stationary pos=(1654,785)

-5815-6019ms: moved from (1050,680) to (1758,264)

-6223-6223ms: stationary pos=(794,1110)

-9963-11254ms: stationary pos=(1065,712)

-11492-14076ms: stationary pos=(1763,12)

-14348-14552ms: moved from (1020,901) to (1554,901)

-14790-14994ms: stationary pos=(1128,793)

-15198-15606ms: moved from (1554,901) to (1128,793)

-15810-16014ms: moved from (1554,901) to (1128,793)

-16218-16218ms: stationary pos=(1128,780)

-25260-26280ms: stationary pos=(23,600)

-26484-27130ms: moved from (1325,617) to (23,600)

+4898-5509ms: stationary pos=(1654,785)

+5815-6223ms: moved from (1050,680) to (794,1110)
... (33 more lines)
```

### travel_learner_sophia_jayde / segment_014
- standalone-c_1: 3 lines, standalone-d_1: 2 lines
```diff
--- segment_014 (standalone-c_1)
+++ segment_014 (standalone-d_1)
@@ -1,3 +1,2 @@
-78552-78756ms: stationary pos=(119,14)

-78960-79402ms: stationary pos=(377,341)

-79640-79640ms: stationary pos=(1647,14)
+78552-78824ms: stationary pos=(119,14)

+79402-79402ms: stationary pos=(377,341)
```

### travel_learner_sophia_jayde / segment_015
- standalone-c_1: 5 lines, standalone-d_1: 4 lines
```diff
--- segment_015 (standalone-c_1)
+++ segment_015 (standalone-d_1)
@@ -1,5 +1,4 @@
-4541-4745ms: stationary pos=(119,14)

-4949-5390ms: stationary pos=(377,341)

-5628-5628ms: stationary pos=(1647,14)

+4541-4813ms: stationary pos=(119,14)

+5390-5390ms: stationary pos=(377,341)

 56552-57572ms: moved from (870,531) to (1763,12)

 58558-58558ms: stationary pos=(870,531)
```

### travel_learner_sophia_jayde / segment_016
- standalone-c_1: 5 lines, standalone-d_1: 5 lines
```diff
--- segment_016 (standalone-c_1)
+++ segment_016 (standalone-d_1)
@@ -1,5 +1,5 @@
-21362-21804ms: moved from (533,753) to (619,712)

-22008-22824ms: moved from (587,116) to (604,585)

+21362-21634ms: moved from (533,753) to (727,716)

+21940-22756ms: moved from (619,712) to (604,585)

 22892-23946ms: stationary pos=(926,946)

-24014-25067ms: stationary pos=(736,414)

-25271-25475ms: moved from (1095,362) to (1618,487)
+24014-24830ms: stationary pos=(736,414)

+25135-25407ms: stationary pos=(1095,362)
```

### travel_learner_sophia_jayde / segment_021
- standalone-c_1: 1 lines, standalone-d_1: 0 lines
```diff
--- segment_021 (standalone-c_1)
+++ segment_021 (standalone-d_1)
@@ -1 +0,0 @@
-32450-32450ms: stationary pos=(1647,580)
```

### travel_learner_sophia_jayde / segment_022
- standalone-c_1: 12 lines, standalone-d_1: 11 lines
```diff
--- segment_022 (standalone-c_1)
+++ segment_022 (standalone-d_1)
@@ -1,12 +1,11 @@
-28433-29419ms: stationary pos=(119,14)

-29657-29861ms: moved from (1498,955) to (452,414)

-30065-30065ms: stationary pos=(1033,759)

-41181-41589ms: stationary pos=(452,414)

-41861-42065ms: moved from (11,404) to (119,14)

-42303-42779ms: moved from (11,404) to (119,14)

-42983-43288ms: moved from (447,798) to (766,942)

-43594-43798ms: moved from (119,14) to (1066,899)

-44036-44444ms: stationary pos=(472,580)

+28297-29419ms: stationary pos=(119,14)

+29725-29725ms: stationary pos=(1498,955)

+40603-40875ms: moved from (893,791) to (1763,12)

+41181-41725ms: stationary pos=(452,414)

+41997-42303ms: moved from (119,14) to (11,404)
... (15 more lines)
```

### travel_learner_sophia_jayde / segment_023
- standalone-c_1: 8 lines, standalone-d_1: 7 lines
```diff
--- segment_023 (standalone-c_1)
+++ segment_023 (standalone-d_1)
@@ -1,8 +1,7 @@
-52257-53821ms: stationary pos=(1069,873)

-54025-54229ms: stationary pos=(1403,615)

-54467-55045ms: stationary pos=(830,264)

+52257-53957ms: stationary pos=(1069,873)

+54229-55215ms: moved from (1403,615) to (830,264)

 55419-55487ms: moved from (909,791) to (1403,615)

-55691-56133ms: stationary pos=(830,264)

-56337-56541ms: moved from (1324,636) to (830,264)

-56745-56949ms: moved from (55,562) to (830,264)

-57152-57356ms: moved from (1168,652) to (830,262)
+55793-56065ms: stationary pos=(830,264)

+56337-56609ms: stationary pos=(1324,636)

+56881-57152ms: moved from (1366,1084) to (1168,652)

+57424-57424ms: stationary pos=(830,262)
```

### travel_learner_sophia_jayde / segment_024
- standalone-c_1: 4 lines, standalone-d_1: 4 lines
```diff
--- segment_024 (standalone-c_1)
+++ segment_024 (standalone-d_1)
@@ -1,4 +1,4 @@
-42869-43311ms: stationary pos=(1669,234)

-43515-43923ms: stationary pos=(1775,557)

-44331-46099ms: moved from (119,14) to (1775,557)

-46303-46303ms: stationary pos=(464,766)
+42869-43175ms: stationary pos=(1669,234)

+43447-43991ms: stationary pos=(1775,557)

+44331-46065ms: moved from (119,14) to (1775,557)

+46371-46371ms: stationary pos=(464,766)
```

### travel_learner_sophia_jayde / segment_025
- standalone-c_1: 4 lines, standalone-d_1: 3 lines
```diff
--- segment_025 (standalone-c_1)
+++ segment_025 (standalone-d_1)
@@ -1,4 +1,3 @@
-17810-18932ms: stationary pos=(464,766)

-41368-41368ms: stationary pos=(1307,864)

-64994-65606ms: moved from (1307,1006) to (1763,12)

-65810-65810ms: stationary pos=(1307,511)
+17810-19033ms: stationary pos=(464,766)

+41368-41640ms: moved from (1307,864) to (1307,918)

+65062-65674ms: moved from (1307,967) to (1307,552)
```

### travel_learner_sophia_jayde / segment_029
- standalone-c_1: 5 lines, standalone-d_1: 5 lines
```diff
--- segment_029 (standalone-c_1)
+++ segment_029 (standalone-d_1)
@@ -1,5 +1,5 @@
-38796-40053ms: stationary pos=(1256,794)

-40257-40461ms: moved from (621,936) to (1568,462)

-40699-40903ms: moved from (1432,812) to (1432,806)

-41107-41311ms: moved from (226,839) to (1432,821)

-73504-75373ms: stationary pos=(413,234)
+38796-39917ms: stationary pos=(1256,794)

+40189-40461ms: moved from (1422,791) to (1568,462)

+40767-41039ms: moved from (1432,806) to (1648,600)

+41311-41311ms: stationary pos=(1432,821)

+73504-75441ms: stationary pos=(413,234)
```

## 3. Event Cursor Enrichment

| Category | Count |
|----------|------:|
| Cursor events total | 908 |
| Both have position | 238 |
| Coverage lost (standalone-d_1 missing) | 4 |
| Coverage gained (standalone-d_1 new) | 3 |
| Neither has position | 663 |

### Position accuracy on events
- Mean: 111.1px
- Median: 0.0px
- Max: 1585.4px
- Within 5px: 193/238
- Within 20px: 194/238

### Events that lost cursor coverage (4)

| Time (ms) | Type | Description | standalone-c_1 pos |
|----------:|------|-------------|-----------|
| 455439 | hover | User hovers over the 'AI Interview' card again. | (710.0,553.0) |
| 1030502 | hover | User hovers over the 'AI Interview' task card. | (1015.0,726.0) |
| 546315 | click | User clicks on the Webjet logo in the header. | (536.0,1016.0) |
| 103832 | hover | User hovers over the 'skyscanner' search suggestion in the autocomplete dropdown | (937.0,891.0) |

### Events that gained cursor coverage (3)

| Time (ms) | Type | Description | standalone-d_1 pos |
|----------:|------|-------------|-----------|
| 13350 | click | User clicks the 'Start task' button. | (725.0,718.0) |
| 531642 | hover | User hovers over the AI interview card titled 'Evaluate new AI chatbot for custo | (1060.0,220.0) |
| 893269 | hover | User pauses to look at a survey opportunity titled 'Review online grocery shoppi | (15.0,12.0) |

## 4. Config Comparison

| Setting | standalone-c_1 | standalone-d_1 |
|---------|-------------|------------|
| cursor.tracking_peak_fps | 5.0 | 4.0 |
