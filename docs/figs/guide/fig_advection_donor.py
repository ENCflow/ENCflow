"""1 セル幅の河道と移流項の風上供給元(docs/users_guide/advection_donor.md)の図。

Regenerate only this page with make_guide_figs.py advection_donor.
模式図(図 1・2)はデータ不要。図 3 の数値は tutorials/chichibu の 200 m 格子(Step 3 の設定)を
f_advection_donor = 0・0 で dd = dv = 0.0001・3(2026-11-21 までの既定)で回した結果(測線 4 の 1 分値と、30 分ごとの
分布出力の本川の水位)、図 4 の数値は test/wetbank の Check_wetbank.py の表を写したもので、
結果ファイルなしで描ける。計算やその検定が変わったら写し直す。
"""
from _terms import *
from _schematic import paragraph
from matplotlib.colors import LinearSegmentedColormap

LAND, CHAN, FILM, VALLEY = '#f1ece3', '#8fb9ea', '#e6f0fb', '#b7d1f1'
CVFILL, CVEDGE = '#fdf1dc', '#d9922a'
Q_O0 = np.array([
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -2, -2, -2, -3, -3, -3, -4, -4, -4, -4,
    -4, -4, -4, -4, -4, -3, -2, -1, 0, 1, 2, 4, 6, 10, 14, 18, 24, 31, 38, 45, 54, 66, 81, 101,
    132, 177, 235, 300, 366, 432, 494, 548, 595, 638, 678, 715, 751, 783, 812, 839, 864, 889, 917, 951, 989, 1029, 1070, 1110,
    1151, 1195, 1241, 1290, 1340, 1392, 1446, 1501, 1558, 1618, 1679, 1743, 1806, 1871, 1936, 2003, 2074, 2147, 2224, 2305, 2388, 2477, 2576, 2682,
    2792, 2909, 3031, 3150, 3266, 3374, 3474, 3566, 3651, 3730, 3800, 3862, 3917, 3966, 4008, 4043, 4079, 4119, 4182, 4254, 4284, 4297, 4320, 4351,
    4375, 4392, 4405, 4418, 4429, 4436, 4440, 4444, 4446, 4447, 4444, 4440, 4436, 4431, 4423, 4413, 4403, 4393, 4384, 4372, 4361, 4352, 4346, 4342,
    4340, 4344, 4355, 4369, 4385, 4404, 4428, 4460, 4498, 4540, 4587, 4645, 4712, 4778, 4836, 4888, 4941, 4993, 5020, 5014, 5046, 5097, 5153, 5199,
    5235, 5263, 5291, 5323, 5354, 5375, 5385, 5391, 5404, 5423, 5437, 5436, 5421, 5405, 5404, 5413, 5408, 5377, 5334, 5300, 5286, 5280, 5254, 5203,
    5143, 5102, 5082, 5059, 5009, 4939, 4883, 4857, 4825, 4772, 4693, 4616, 4567, 4536, 4486, 4413, 4343, 4298, 4261, 4205, 4134, 4075, 4036, 3997,
    3961, 3871, 3766, 3738, 3729, 3680, 3624, 3585, 3541, 3502, 3460, 3416, 3373, 3333, 3292, 3251, 3211, 3172, 3133, 3094, 3056, 3019, 2981, 2944,
    2908, 2871, 2836, 2801, 2766, 2732, 2699, 2666, 2633, 2601, 2569, 2538, 2508, 2477, 2448, 2419, 2391, 2363, 2335, 2308, 2280, 2253, 2226, 2200,
    2174, 2148, 2123, 2098, 2073, 2049, 2024, 2001, 1977, 1957, 2001, 2174, 2094, 1888, 1803, 1830, 1839, 1811, 1776, 1750, 1854, 1897, 1848, 1781,
    1751, 1740, 1685, 1662, 1624, 1600, 1574, 1555, 1534, 1515, 1496, 1478, 1462, 1445, 1428, 1412, 1396, 1380, 1365, 1350, 1335, 1320, 1306, 1293,
    1279, 1266, 1253, 1240, 1228, 1216, 1204, 1193, 1181, 1169, 1158, 1147, 1137, 1126, 1117, 1107, 1097, 1088, 1078, 1069, 1059, 1050, 1042, 1033,
    1025, 1017, 1008, 1000, 992, 983, 975, 967, 959, 951, 942, 934, 926, 919, 911, 904, 897, 890, 883, 876, 868, 861, 854, 848,
    841,
], dtype=float)
Q_O0DD = np.array([
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -2, -2, -2, -3, -3, -3, -4, -4, -4, -4,
    -4, -4, -4, -4, -4, -3, -2, -1, 0, 1, 2, 4, 6, 10, 14, 18, 24, 31, 38, 45, 54, 66, 81, 101,
    132, 177, 235, 300, 366, 432, 494, 548, 595, 638, 678, 715, 751, 783, 812, 839, 864, 889, 917, 951, 989, 1029, 1070, 1110,
    1151, 1195, 1241, 1289, 1340, 1392, 1446, 1501, 1558, 1618, 1679, 1743, 1806, 1871, 1936, 2003, 2074, 2147, 2224, 2305, 2388, 2477, 2576, 2682,
    2792, 2909, 3031, 3150, 3265, 3374, 3474, 3566, 3651, 3730, 3800, 3862, 3917, 3966, 4008, 4043, 4079, 4120, 4182, 4255, 4284, 4297, 4321, 4352,
    4376, 4392, 4405, 4418, 4429, 4436, 4440, 4443, 4446, 4446, 4443, 4438, 4433, 4428, 4419, 4408, 4397, 4387, 4376, 4363, 4349, 4338, 4330, 4322,
    4316, 4313, 4316, 4324, 4335, 4349, 4368, 4395, 4428, 4463, 4503, 4550, 4607, 4671, 4732, 4788, 4841, 4892, 4937, 4977, 4995, 4989, 5020, 5063,
    5101, 5133, 5163, 5193, 5217, 5231, 5237, 5243, 5255, 5264, 5264, 5254, 5242, 5239, 5244, 5241, 5216, 5181, 5153, 5139, 5125, 5094, 5047, 5001,
    4971, 4952, 4923, 4884, 4829, 4776, 4744, 4706, 4648, 4581, 4530, 4496, 4458, 4401, 4338, 4291, 4255, 4210, 4151, 4094, 4052, 4013, 3965, 3914,
    3867, 3781, 3723, 3708, 3684, 3638, 3593, 3553, 3520, 3483, 3443, 3404, 3365, 3324, 3287, 3251, 3212, 3173, 3138, 3101, 3064, 3029, 2993, 2957,
    2922, 2887, 2852, 2819, 2785, 2751, 2719, 2686, 2654, 2623, 2591, 2560, 2530, 2500, 2470, 2440, 2412, 2383, 2355, 2327, 2300, 2273, 2246, 2220,
    2194, 2168, 2143, 2118, 2093, 2069, 2045, 2021, 1998, 1975, 1952, 1930, 1908, 1887, 1865, 1845, 1824, 1804, 1785, 1765, 1746, 1727, 1709, 1691,
    1674, 1657, 1640, 1623, 1606, 1589, 1573, 1556, 1540, 1524, 1509, 1495, 1480, 1465, 1450, 1436, 1422, 1408, 1394, 1380, 1367, 1354, 1341, 1328,
    1316, 1303, 1291, 1279, 1267, 1255, 1244, 1232, 1221, 1210, 1199, 1189, 1178, 1167, 1157, 1147, 1137, 1127, 1117, 1107, 1098, 1089, 1080, 1071,
    1061, 1052, 1044, 1035, 1026, 1018, 1010, 1002, 994, 985, 977, 969, 962, 954, 946, 939, 931, 924, 916, 909, 902, 895, 887, 881,
    874,
], dtype=float)
Q_O3 = np.array([
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -2, -2, -2, -3, -3, -3, -4, -4, -4, -4,
    -4, -4, -4, -4, -4, -3, -2, -1, 0, 1, 2, 4, 6, 10, 14, 18, 24, 30, 38, 46, 56, 69, 86, 112,
    155, 216, 287, 355, 424, 496, 564, 627, 687, 742, 789, 832, 870, 904, 935, 966, 1000, 1039, 1086, 1139, 1195, 1254, 1318, 1390,
    1472, 1560, 1651, 1740, 1827, 1910, 1991, 2071, 2152, 2227, 2292, 2364, 2472, 2625, 2835, 3061, 3270, 3477, 3675, 3840, 3980, 4091, 4187, 4278,
    4358, 4421, 4477, 4546, 4625, 4702, 4773, 4839, 4901, 4959, 5009, 5051, 5085, 5112, 5135, 5155, 5172, 5190, 5211, 5238, 5276, 5325, 5406, 5542,
    5595, 5645, 5734, 5726, 5681, 5711, 5811, 5915, 6017, 6122, 6240, 6367, 6409, 6455, 6579, 6675, 6763, 6828, 6879, 6914, 6938, 6954, 6960, 6959,
    6950, 6936, 6915, 6889, 6858, 6821, 6779, 6733, 6682, 6629, 6572, 6513, 6453, 6391, 6328, 6266, 6203, 6140, 6081, 6034, 5949, 5869, 5788, 5705,
    5625, 5542, 5472, 5429, 5350, 5233, 5202, 5186, 5086, 5033, 4971, 4880, 4783, 4694, 4599, 4508, 4424, 4344, 4269, 4196, 4126, 4059, 3994, 3931,
    3870, 3811, 3755, 3701, 3646, 3589, 3530, 3472, 3417, 3364, 3311, 3260, 3209, 3159, 3109, 3062, 3016, 2972, 2930, 2891, 2853, 2817, 2781, 2747,
    2714, 2680, 2649, 2620, 2592, 2565, 2538, 2510, 2482, 2453, 2422, 2392, 2363, 2334, 2304, 2275, 2245, 2215, 2185, 2156, 2129, 2103, 2077, 2052,
    2028, 2005, 1982, 1960, 1938, 1917, 1896, 1876, 1855, 1835, 1815, 1796, 1776, 1757, 1738, 1719, 1700, 1681, 1663, 1644, 1626, 1608, 1591, 1573,
    1556, 1539, 1522, 1506, 1490, 1474, 1458, 1444, 1430, 1415, 1400, 1386, 1372, 1358, 1344, 1331, 1317, 1304, 1291, 1278, 1265, 1253, 1240, 1228,
    1216, 1204, 1193, 1181, 1170, 1158, 1148, 1137, 1126, 1116, 1105, 1095, 1085, 1075, 1065, 1055, 1046, 1036, 1027, 1018, 1009, 1001, 992, 983,
    974, 966, 958, 949, 941, 933, 926, 918, 910, 903, 895, 888, 881, 874, 867, 862, 857, 851, 844, 837, 830, 823, 817, 810,
    804, 797, 791, 785, 778, 772, 766, 761, 755, 749, 744, 738, 732, 726, 721, 716, 711, 706, 701, 696, 691, 687, 682, 677,
    672,
], dtype=float)
PATH_CELLS = [(207, 39), (208, 39), (209, 40), (210, 40), (211, 40), (212, 40), (213, 40), (214, 39), (215, 39), (216, 39), (217, 39), (218, 39), (219, 39), (220, 38), (221, 38), (222, 37), (222, 36), (222, 35), (222, 34)]
PATH_DIST = np.array([0.0, 200.0, 482.8, 682.8, 882.8, 1082.8, 1282.8, 1565.7, 1765.7, 1965.7, 2165.7, 2365.7, 2565.7, 2848.5, 3048.5, 3331.4, 3531.4, 3731.4, 3931.4])
PATH_Z = np.array([176.59, 168.22, 164.75, 158.71, 149.57, 142.54, 142.54, 141.21, 141.21, 141.21, 141.21, 141.21, 141.21, 141.21, 141.21, 138.69, 138.69, 138.69, 141.42])
ETA_O0_180 = np.array([176.64, 168.3, 164.82, 158.76, 150.45, 150.47, 150.24, 150.3, 149.14, 149.07, 148.99, 148.93, 148.95, 147.26, 147.03, 146.44, 144.94, 144.39, 144.14])
ETA_O3_180 = np.array([176.64, 168.3, 164.83, 158.76, 149.67, 148.28, 148.23, 147.65, 147.73, 147.65, 147.52, 147.37, 147.23, 146.68, 145.32, 144.17, 143.64, 142.99, 143.49])
ETA_O0_300 = np.array([176.61, 168.25, 164.79, 158.73, 149.6, 145.82, 145.68, 145.43, 145.48, 145.45, 145.41, 145.37, 145.32, 144.56, 143.94, 143.05, 142.63, 142.57, 142.62])
ETA_O3_300 = np.array([176.61, 168.25, 164.79, 158.73, 149.6, 144.84, 144.77, 144.16, 144.2, 144.14, 144.05, 143.96, 143.87, 143.51, 143.04, 142.12, 142.27, 142.24, 142.39])
FILM_MM = {0: 0.0, 30: 19.2, 60: 16.4, 90: 6.2, 120: 3.8, 150: 2.6, 180: 1.9, 210: 1.6, 240: 1.3, 270: 1.1, 300: 0.9, 330: 0.6, 360: 0.5}

T = {'ja': {
 # 図 1
 'c_a': '(a) 河岸の薄い水膜が供給元になる(人工的な減速)',
 'c_b': '(b) 深い谷底の水が実際に流れ込む(現実の減速)',
 'cell_c': 'c', 'cell_n': 'n', 'cell_b': 'B',
 'face_c': '面 c', 'line_k': '線 k', 'u_e': '$u_e$', 'u_m': '$u_m$',
 'main': '本流(斜めのリンク)', 'film': '水膜:流量ほぼ 0', 'valley': '谷底の水:流量あり',
 'notes_a': ['面 c の質量流束 q_c:セル c に入る水の全量(大部分は斜めのリンクから入る本流)',
             '面 c の風上の流速:線 k 上の上流のリンク B → c の流速 u_m(水膜なのでほぼ 0)',
             '0:q_c (u_m − u_e) が本流に大きな減速を掛ける(水のやり取りのない、計算のうえだけのブレーキ)',
             '3:B は水をほとんど運ばず薄いので中立に扱う(風上値を u_e に寄せる。減速しない)'],
 'notes_b': ['B は深く、実際に c へ水を運ぶ(浸水した谷底・高水敷。合流する支川も同じ)',
             '0 も 3 も:遅い水が混ざって本流が減速する(運動量の保存による現実の減速)',
             '3 の判定は「河道か」ではなく「水を運ぶか・深いか」なので、河道マスクは使わない'],
 'legend_c': ['河道のセル', '水膜の乗った河岸のセル', '谷底の水', '乾いた陸', 'エッジ e の検査体積(セル c の中心から n の中心まで)'],
 # 図 2
 'r_a': '(a) 流向面:線 k の供給元を使う重み w',
 'r_b': '(b) 側方面:横から入る水の流速に平行なリンクを使う重み',
 'r_x': '$Q_k/Q_{max}$(線 k の供給元が面のセルへ運ぶ流量 / 面のセルへ入る最大のリンクの流量)',
 'r_y': '$h_d/h_c$(供給元の水深 / 面のセルの水深)',
 'r_use': 'そのまま使う(w ≥ 1。0 と同じ)', 'r_neu': '中立へ寄せる\n(w < 1)',
 'r_film': '河岸の水膜\n(秩父の池の入口)',
 'r_valley': '実際に流れ込む谷底・\n合流する支川', 'r_pool': '深い淀み(流入は小さい。\n窪地除去でできた平坦部など)',
 'r_note_a': 'w = max(Q_k/Q_max, h_d/h_c) / ε(ε = p_adv_donor_eps、既定 0.1)。w ≥ 1 なら線 k の風上値 ū_k をそのまま使い、'
             'w < 1 なら ū = u_e + w (ū_k − u_e) と検査体積の流速 u_e へ寄せる。w は連続なので、切り替わりの瞬間の跳ねが出ない。'
             '秩父の池の入口の河岸の水膜は、流量の比が 10⁻⁶、水深の比が 2×10⁻⁴ で、原点のすぐそばにある。',
 'r_bx': '平行なリンクの両端のセルの水深 h / dd', 'r_by': '重み',
 'r_b0': '0:dd を割った瞬間に 1 → 0', 'r_b3': '3:w = min(1, h/dd)',
 'r_note_b': 'dd(限界水深。既定 1 mm)以上では 0 と同じ値。dd 以上の水膜が平行なリンクに入るときの側方面の減速は、3 は変えない(f_advection_lateral が扱う。§7)。',
 # 図 3
 'h_a': '(a) 測線 4 のハイドログラフ(秩父 200 m 格子)',
 'h_b': '(b) 池の入口付近の本川の水位(縦断)',
 'h_x': '時間 (min)', 'h_y': '流量 (m³/s)',
 'h_o0': '0(2026-11-09 までの既定)', 'h_o0dd': '0 で dd = dv = 0.0001(1/10)', 'h_o3': '3(2026-11-21 までの既定)',
 'h_jump': '跳ね', 'h_pk3': '6,960 m³/s(142 分)', 'h_pk0': '5,437 m³/s(178 分)',
 'p_x': '本川に沿う距離 (km)', 'p_y': '標高・水位 (m)',
 'p_o0_180': '0、180 分', 'p_o3_180': '3、180 分', 'p_o0_300': '0、300 分', 'p_bed': '河床',
 'p_step': '① 0 の 180 分:池の入口の辺で 1.16 m の水面の段差ができている(線 k の上流の河岸のセルに 1.9 mm の水膜)。',
 'p_gone': '② 0 の 300 分:水膜が 0.9 mm と dd を割り、段差が外れている。外れた瞬間が (a) の 275 分の跳ね。',
 'p_pond': '平坦区間(池)', 'p_edge': '池の入口の辺', 'p_t4': '測線 4',
 'p_note': '窪地除去でできた平坦区間(池)の入口の辺の風上値は、線 k の上流の河岸のセル(池より 27 m 高く、雨の後に 1〜4 mm の水膜が残る)から取られる。',
 # 図 4
 'w_title': 'test/wetbank:雨で濡れた河岸による余分な水深 E(理論値 0)',
 'w_y': 'E (%)', 'w_o0': '0', 'w_o3l0': '3 と f_advection_lateral = 0', 'w_o3': '3 と f_advection_lateral = 1(2026-11-21 までの既定)', 'w_cells': 'セル', 'w_cell1': 'セル',
 'w_note': ['格子に斜めの直線水路(ラスタでは階段)の河岸を雨で濡らし、雨の流入による増分を差し引いた余分な水深を測る。',
            '格子に沿う水路(0°)はどれも 0.2 %。斜めの水路では、0 が 10〜40 %、3 に f_advection_lateral = 0 を組み合わせると 4〜17 %、'
            '2026-11-21 までの既定の組み合わせ(3 と f_advection_lateral = 1)は −0.4〜3.7 %。',
            '1 セル幅のまま格子を細かくすると 0 は増える(段が増えるため)。3 だけで残る分の主な原因は側方面で、f_advection_lateral = 1 が外す(§7)。'],
}, 'en': {
 'c_a': '(a) A thin film on the bank becomes the donor (artificial braking)',
 'c_b': '(b) Deep valley-floor water actually flows in (physical braking)',
 'cell_c': 'c', 'cell_n': 'n', 'cell_b': 'B',
 'face_c': 'face c', 'line_k': 'line k', 'u_e': '$u_e$', 'u_m': '$u_m$',
 'main': 'main flow (diagonal link)', 'film': 'film: tiny flow', 'valley': 'valley: flows in',
 'notes_a': ['Mass flux q_c through face c: all the water entering cell c (mostly the main flow through the diagonal link)',
             'Upwind velocity at face c: velocity u_m of the upstream link B → c on line k (a film, so nearly 0)',
             '0: q_c (u_m − u_e) puts a large brake on the main flow (a brake that exists only in the computation; no water is exchanged)',
             '3: B carries almost no water and is thin, so it is treated as neutral (the upwind value moves to u_e; no braking)'],
 'notes_b': ['B is deep and really carries water into c (an inundated valley floor or floodplain; a joining tributary is the same)',
             '0 and 3 alike: slow water mixes in and slows the main flow (physical braking from momentum conservation)',
             'Option 3 asks "does it carry water / is it deep", not "is it a channel", so no channel mask is used'],
 'legend_c': ['channel cell', 'bank cell with a film', 'valley water', 'dry land', 'control volume of edge e (from the centre of c to that of n)'],
 'r_a': '(a) Flow-direction face: weight w of the line-k donor',
 'r_b': '(b) Lateral face: weight of the parallel link',
 'r_x': '$Q_k/Q_{max}$ (flow the donor on line k carries into the face cell / largest link inflow)',
 'r_y': '$h_d/h_c$ (donor depth / face-cell depth)',
 'r_use': 'use as is (w ≥ 1; same as 0)', 'r_neu': 'move to neutral\n(w < 1)',
 'r_film': 'film on a bank\n(Chichibu pond)',
 'r_valley': 'valley floor\nflowing in;\njoining tributary', 'r_pool': 'deep still water (small inflow;\ne.g. flats left by pit filling)',
 'r_note_a': 'w = max(Q_k/Q_max, h_d/h_c) / ε (ε = p_adv_donor_eps, default 0.1). For w ≥ 1 the upwind value ū_k on line k is used as is; '
             'for w < 1 it moves towards the control-volume velocity u_e: ū = u_e + w (ū_k − u_e). w is continuous, so no jump appears at the switch. '
             'The film on the bank at the Chichibu pond entrance has a flow ratio of 10⁻⁶ and a depth ratio of 2×10⁻⁴, right next to the origin.',
 'r_bx': 'depth h of the cells at both ends of the parallel link / dd', 'r_by': 'weight',
 'r_b0': '0: 1 → 0 when h drops below dd', 'r_b3': '3: w = min(1, h/dd)',
 'r_note_b': 'At or above dd (threshold depth, default 1 mm) the value is the same as 0. The lateral-face braking by films of dd or more on the parallel link is not changed by 3 (f_advection_lateral handles it; §7).',
 'h_a': '(a) Hydrograph at transect 4 (Chichibu, 200 m grid)',
 'h_b': '(b) Water level along the main river near the pond entrance',
 'h_x': 'time (min)', 'h_y': 'discharge (m³/s)',
 'h_o0': '0 (default until 2026-11-09)', 'h_o0dd': '0 with dd = dv = 0.0001 (1/10)', 'h_o3': '3 (default until 2026-11-21)',
 'h_jump': 'jump', 'h_pk3': '6,960 m³/s (142 min)', 'h_pk0': '5,437 m³/s (178 min)',
 'p_x': 'distance along the main river (km)', 'p_y': 'elevation, water level (m)',
 'p_o0_180': '0, 180 min', 'p_o3_180': '3, 180 min', 'p_o0_300': '0, 300 min', 'p_bed': 'bed',
 'p_step': '① 0 at 180 min: a 1.16 m step in the water surface at the pond-entrance edge (a 1.9 mm film on the upstream bank cell on line k).',
 'p_gone': '② 0 at 300 min: the film is 0.9 mm, below dd, and the step has been released. The moment of release is the jump at 275 min in (a).',
 'p_pond': 'flat reach (pond)', 'p_edge': 'pond-entrance edge', 'p_t4': 'transect 4',
 'p_note': 'The upwind value at the entrance edge of the flat reach (pond) left by pit filling is taken from the upstream bank cell on line k (27 m above the pond, keeping a 1-4 mm film after the rain).',
 'w_title': 'test/wetbank: extra depth E caused by rain-wetted banks (theory: 0)',
 'w_y': 'E (%)', 'w_o0': '0', 'w_o3l0': '3 with f_advection_lateral = 0', 'w_o3': '3 with f_advection_lateral = 1 (default until 2026-11-21)', 'w_cells': 'cells', 'w_cell1': 'cell',
 'w_note': ['A straight channel oblique to the grid (a staircase on the raster) with banks wetted by rain; the extra depth after removing the rise due to the rain inflow.',
            'Grid-aligned channel (0°): 0.2 % for all three. Oblique channels: 10-40 % with 0, 4-17 % with 3 combined with f_advection_lateral = 0, '
            'and -0.4 to 3.7 % with the default combination until 2026-11-21 (3 with f_advection_lateral = 1).',
            'Refining the grid with the channel kept one cell wide increases E for 0 (more steps). What remains with 3 alone comes mainly from the lateral faces, which f_advection_lateral = 1 removes (§7).'],
}}


# ------------------------------------------------------------------ 図 1: セル配置
def cell_xy(x0, y0, d, i, j):
    return np.array([x0 + (i + .5) * d, y0 + (j + .5) * d])


def panel_cells(ax, t, x0, y0, d, mode):
    """5 列 × 3 行。河道 A0(0,2)→A1(1,2)→斜め→c(2,1)→n(3,1)→斜め→(4,0)。B(1,1) は c の西隣(線 k の上流)。"""
    chan = [(0, 2), (1, 2), (2, 1), (3, 1), (4, 0)]
    for i in range(5):
        for j in range(3):
            col = CHAN if (i, j) in chan else LAND
            if (i, j) == (1, 1):
                col = FILM if mode == 'a' else VALLEY
            rect(ax, x0 + i * d, y0 + j * d, d, d, col)
    grid(ax, x0, y0, 5, 3, d)
    if mode == 'a':   # 水膜の印(細い破線の枠)
        rect(ax, x0 + d + 6, y0 + d + 6, d - 12, d - 12, 'none', BLUE, .9, ls=(0, (3, 3)))
    # 検査体積(c の中心から n の中心まで)
    rect(ax, x0 + 2.5 * d, y0 + d, d, d, CVFILL, CVEDGE, 1.8, alpha=.9, zorder=3)
    line(ax, [(x0 + 2.5 * d, y0 + d), (x0 + 2.5 * d, y0 + 2 * d)], CVEDGE, 1.6, ls='--', z=4)
    text(ax, x0 + 2.5 * d + 6, y0 + d + 6, t['face_c'], 9.5, color='#b2791a')
    # 線 k
    line(ax, [(x0 - 10, y0 + 1.5 * d), (x0 + 5 * d + 10, y0 + 1.5 * d)], MUTED, .9, ls=':', z=4)
    text(ax, x0 + 5 * d + 16, y0 + 1.5 * d, t['line_k'], 9.5, color=MUTED, va='center')
    # 流れ(本流)
    for p, q in [((0, 2), (1, 2)), ((1, 2), (2, 1)), ((2, 1), (3, 1)), ((3, 1), (4, 0))]:
        a = cell_xy(x0, y0, d, *p); b = cell_xy(x0, y0, d, *q)
        v = (b - a) / np.linalg.norm(b - a)
        arrow(ax, [a + v * 16, b - v * 18], BLUE, 3.0 if p == (1, 2) else 2.0, size=14)
    m = (cell_xy(x0, y0, d, 1, 2) + cell_xy(x0, y0, d, 2, 1)) / 2
    text(ax, m[0] + 26, m[1] + 14, t['main'], 9.5, color=BLUE)
    # B → c
    a = cell_xy(x0, y0, d, 1, 1); b = cell_xy(x0, y0, d, 2, 1)
    if mode == 'a':
        arrow(ax, [a + [16, -26], b - [70, 26]], MUTED, .9, size=8)
        text(ax, a[0] - 58, a[1] - 56, t['film'], 9.2, color=MUTED, bbox=dict(fc=FILM, ec='none', pad=1))
    else:
        arrow(ax, [a + [16, -26], b - [50, 26]], BLUE, 2.2, size=12)
        text(ax, a[0] - 58, a[1] - 56, t['valley'], 9.2, color=BLUE, bbox=dict(fc=VALLEY, ec='none', pad=1))
    # セル中心と名前
    for i in range(5):
        for j in range(3):
            dot(ax, cell_xy(x0, y0, d, i, j))
    for (i, j), key in [((2, 1), 'cell_c'), ((3, 1), 'cell_n'), ((1, 1), 'cell_b')]:
        p = cell_xy(x0, y0, d, i, j)
        text(ax, p[0] + 8, p[1] + 14, t[key], 12, weight='bold', ha='left', color=INK)
    # エッジの印
    edge(ax, (x0 + 3 * d, y0 + 1.5 * d), ORANGE)
    text(ax, x0 + 3 * d + 6, y0 + 1.5 * d - 34, t['u_e'], 11, color=ORANGE)
    edge(ax, (x0 + 2 * d, y0 + 1.5 * d), GREEN)
    text(ax, x0 + 2 * d - 6, y0 + 1.5 * d + 12, t['u_m'], 11, color=GREEN, ha='right')


def swatch_row(ax, x, y, items, size=9.4):
    """items: (fill, edge, linestyle, label)。色見本の四角と名前を 1 行に並べる(名前の幅は実測)。"""
    renderer = ax.figure.canvas.get_renderer()
    for fill, ec, ls, label in items:
        rect(ax, x, y + 3, 20, 15, fill, ec, 1.2, ls=ls, zorder=21)
        tt = text(ax, x + 28, y, label, size, color=MUTED)
        bb = tt.get_window_extent(renderer)
        x += 28 + bb.width + 36


def fit_height(fig, ax, h):
    """説明用キャンバスの高さを h ピクセルに詰める(1 データ単位 = 1 ピクセルのまま)。
    グラフの軸は上端からの位置と高さ(ピクセル)を保つ。"""
    h0 = fig.get_size_inches()[1] * fig.dpi
    boxes = [(a, a.get_position()) for a in fig.axes if a is not ax]
    fig.set_size_inches(fig.get_size_inches()[0], h / fig.dpi)
    ax.set_ylim(h, 0)
    for a, bx in boxes:
        top = (1 - bx.y1) * h0; hp = bx.height * h0
        a.set_position([bx.x0, 1 - (top + hp) / h, bx.width, hp / h])


def build_cells(lang):
    t = T[lang]; fig, ax = canvas(900)
    d = 128; y_end = 0
    for mode, x0, title, notes in [('a', 92, t['c_a'], t['notes_a']), ('b', 982, t['c_b'], t['notes_b'])]:
        text(ax, x0 - 44, 32, title, 12.5, weight='bold')
        panel_cells(ax, t, x0, 100, d, mode)
        y = 100 + 3 * d + 34
        for k, s in enumerate(notes):
            col = ORANGE if s.startswith('0') else (BLUE if s.startswith('3') else INK)
            y = paragraph(ax, x0 - 44, y, s, 800, 9.6, col) + 16
        y_end = max(y_end, y)
    sw = [(CHAN, RULE, '-'), (FILM, BLUE, (0, (3, 3))), (VALLEY, RULE, '-'), (LAND, RULE, '-'), (CVFILL, CVEDGE, '-')]
    swatch_row(ax, 48, y_end + 14, [(f, e, ls, lab) for (f, e, ls), lab in zip(sw, t['legend_c'])])
    fit_height(fig, ax, y_end + 62)
    return fig


# ------------------------------------------------------------------ 図 2: 判定
def build_rule(lang):
    t = T[lang]; fig, base = canvas(800)
    text(base, 48, 32, t['r_a'], 12.5, weight='bold')
    text(base, 960, 32, t['r_b'], 12.5, weight='bold')
    ax = plot_axes(fig, 120, 96, 640, 470)
    eps, top = .1, .2
    x = np.linspace(0, top, 401); y = np.linspace(0, top, 401)
    X, Y = np.meshgrid(x, y)
    W = np.minimum(1.0, np.maximum(X, Y) / eps)
    cmap = LinearSegmentedColormap.from_list('w', ['#ffffff', '#dbe8fa'])
    ax.imshow(W, origin='lower', extent=(0, top, 0, top), cmap=cmap, vmin=0, vmax=1, aspect='auto', zorder=0)
    ax.contour(X, Y, W, levels=[.25, .5, .75], colors=[MUTED], linewidths=.6, linestyles=':')
    for lv in (.25, .5, .75):
        ax.text(.0015, lv * eps + .0012, f'w = {lv:g}', fontsize=7.3, color=MUTED, va='bottom')
    ax.plot([0, eps, eps], [eps, eps, 0], color=BLUE, lw=1.8)
    ax.text(.15, .15, t['r_use'], fontsize=10, color=BLUE, ha='center', va='center')
    ax.text(.062, .089, t['r_neu'], fontsize=9.5, color=INK, ha='center', va='center')
    ax.plot([.003], [.003], 'o', color=ORANGE, ms=6, zorder=5, clip_on=False)
    ax.annotate(t['r_film'], xy=(.0045, .0045), xytext=(.096, .006), fontsize=8.4, color=ORANGE,
                ha='right', va='bottom', bbox=dict(fc='white', ec='none', alpha=.85, pad=1.5),
                arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=1, shrinkA=2))
    ax.plot([.17], [.03], 's', color=BLUE, ms=6)
    ax.text(.16, .042, t['r_valley'], fontsize=8.6, color=BLUE, ha='center', va='bottom')
    ax.plot([.02], [.175], 'D', color=GREEN, ms=6)
    ax.text(.028, .175, t['r_pool'], fontsize=8.6, color=GREEN, ha='left', va='center')
    ax.set(xlim=(0, top), ylim=(0, top))
    ax.set_xlabel(t['r_x'], fontsize=9); ax.set_ylabel(t['r_y'], fontsize=9)
    block(base, 48, 640, t['r_note_a'], 830, 9.4)
    ax = plot_axes(fig, 1040, 96, 680, 470)
    hh = np.linspace(0, 2.5, 501)
    ax.plot(hh, np.minimum(1, hh), color=BLUE, lw=2.2, label=t['r_b3'])
    ax.step([0, 1, 2.5], [0, 1, 1], where='post', color=ORANGE, lw=1.6, ls='--', label=t['r_b0'])
    ax.axvline(1, color=MUTED, lw=.8, ls=':')
    ax.text(1.03, .3, 'h = dd', fontsize=8.6, color=MUTED)
    ax.set(xlim=(0, 2.5), ylim=(-.05, 1.15))
    ax.set_xlabel(t['r_bx'], fontsize=9); ax.set_ylabel(t['r_by'], fontsize=9)
    ax.legend(loc='center left', bbox_to_anchor=(.43, .45), fontsize=9, frameon=False)
    block(base, 960, 640, t['r_note_b'], 792, 9.4)
    return fig


# ------------------------------------------------------------------ 図 3: 秩父
def build_chichibu(lang):
    t = T[lang]; fig, base = canvas(860)
    text(base, 48, 32, t['h_a'], 12.5, weight='bold')
    text(base, 960, 32, t['h_b'], 12.5, weight='bold')
    ax = plot_axes(fig, 110, 96, 760, 470)
    tm = np.arange(361.0)
    ax.plot(tm, Q_O0, color=ORANGE, lw=1.6, label=t['h_o0'])
    ax.plot(tm, Q_O0DD, color=MUTED, lw=1.3, ls='--', label=t['h_o0dd'])
    ax.plot(tm, Q_O3, color=BLUE, lw=1.8, label=t['h_o3'])
    for n, tj in enumerate((275, 285)):     # 2 つの跳ねに、同じ位置のラベルから矢印を引く
        ax.annotate(t['h_jump'] if n == 0 else '', xy=(tj, Q_O0[tj] + 80), xytext=(292, Q_O0[275] + 1250), fontsize=9, color=ORANGE,
                    arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=1))
    ax.annotate(t['h_pk3'], xy=(142, Q_O3[142] + 10), xytext=(14, 6970), fontsize=8.8, color=BLUE, va='center',
                arrowprops=dict(arrowstyle='-', color=BLUE, lw=.8))
    ax.annotate(t['h_pk0'], xy=(178, 5437), xytext=(206, 5020), fontsize=8.8, color=ORANGE,
                arrowprops=dict(arrowstyle='-', color=ORANGE, lw=.8))
    ax.set(xlim=(0, 360), ylim=(-200, 7500))
    ax.set_xlabel(t['h_x'], fontsize=9); ax.set_ylabel(t['h_y'], fontsize=9)
    ax.grid(alpha=.3)
    ax.legend(loc='upper right', fontsize=8.8, frameon=False)
    ax = plot_axes(fig, 1050, 96, 690, 470)
    i0 = 4   # (211,40) から
    xs = PATH_DIST[i0:] / 1000.0
    ax.fill_between(xs, 130, PATH_Z[i0:], color='#e4d9c8', step=None, zorder=1)
    ax.plot(xs, PATH_Z[i0:], color='#8c7b63', lw=1.2, label=t['p_bed'], zorder=2)
    ax.plot(xs, ETA_O0_180[i0:], color=ORANGE, lw=1.8, marker='o', ms=3.5, label=t['p_o0_180'], zorder=4)
    ax.plot(xs, ETA_O3_180[i0:], color=BLUE, lw=1.8, marker='o', ms=3.5, label=t['p_o3_180'], zorder=4)
    ax.plot(xs, ETA_O0_300[i0:], color=ORANGE, lw=1.3, ls=':', marker='.', ms=4, label=t['p_o0_300'], zorder=3)
    k1 = PATH_CELLS.index((214, 39)); k2 = PATH_CELLS.index((215, 39)); kt = PATH_CELLS.index((216, 39))
    xe = (PATH_DIST[k1] + PATH_DIST[k2]) / 2000.0
    ax.axvline(xe, color=MUTED, lw=.8, ls=':')
    ax.axvline(PATH_DIST[kt] / 1000.0, color=MUTED, lw=.8, ls=':')
    ax.annotate('①', xy=(xe, (ETA_O0_180[k1] + ETA_O0_180[k2]) / 2 + .15), xytext=(xe - .3, 152.6),
                fontsize=11, color=ORANGE, ha='center', va='center',
                arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=1, shrinkA=6))
    ax.annotate('②', xy=(xe + .02, ETA_O0_300[k1] - .15), xytext=(xe + .38, 143.4),
                fontsize=11, color=ORANGE, ha='center', va='center',
                arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=1, shrinkA=6))
    kp = PATH_CELLS.index((221, 38))
    ax.text((PATH_DIST[k1] + PATH_DIST[kp]) / 2000.0, 139.6, t['p_pond'], fontsize=8.4, color='#6b5a44', ha='center')
    ax.text(xe, 138.3, t['p_edge'], fontsize=8, color=MUTED, ha='right', va='bottom', rotation=90)
    ax.text(PATH_DIST[kt] / 1000.0, 138.3, t['p_t4'], fontsize=8, color=MUTED, ha='right', va='bottom', rotation=90)
    ax.set(xlim=(xs[0] - .05, xs[-1] + .05), ylim=(138, 156))
    ax.set_xlabel(t['p_x'], fontsize=9); ax.set_ylabel(t['p_y'], fontsize=9)
    ax.legend(loc='upper right', fontsize=8.6, frameon=False)
    y = 646
    for s, col in [(t['p_step'], ORANGE), (t['p_gone'], ORANGE), (t['p_note'], MUTED)]:
        y = paragraph(base, 960, y, s, 792, 9.2, col) + 12
    fit_height(fig, base, max(y, 640) + 24)
    return fig


# ------------------------------------------------------------------ 図 4: test/wetbank
# 列: 向き、格子幅、河道のセル数、E(0)、E(3 と f_advection_lateral = 0)、E(3 と f_advection_lateral = 1 = 2026-11-21 までの既定)
WB = [('0°', '50 m', 1, .2, .2, .2), ('10°', '50 m', 1, 12.5, 7.4, -.2), ('22.5°', '50 m', 1, 32.7, 10.2, 1.4),
      ('30°', '50 m', 1, 38.9, 17.2, 3.7), ('45°', '50 m', 1, 9.6, 8.6, 2.4), ('22.5°', '100 m', 1, 23.9, 10.3, 2.3),
      ('22.5°', '25 m', 1, 39.6, 4.3, -.4), ('22.5°', '50 m', 2, 18.9, 8.4, 1.4), ('22.5°', '25 m', 4, 12.3, 6.6, .8)]


def build_wetbank(lang):
    t = T[lang]; fig, base = canvas(650)
    text(base, 48, 32, t['w_title'], 12.5, weight='bold')
    ax = plot_axes(fig, 110, 96, 1080, 440)
    xs = np.arange(len(WB))
    for k, (dx, col, key) in enumerate(((-.27, ORANGE, 'w_o0'), (0, BLUE, 'w_o3l0'), (.27, GREEN, 'w_o3'))):
        ax.bar(xs + dx, [r[3 + k] for r in WB], .25, color=col, label=t[key])
        for x, r in zip(xs, WB):
            ax.text(x + dx, max(r[3 + k], 0) + .8, f'{r[3 + k]:g}'.replace('-', '−'), fontsize=7.4, ha='center', color=INK)
    ax.axhline(0, color=RULE, lw=.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f'{a}\n{b}\n{n} {t["w_cell1" if n == 1 else "w_cells"]}' for a, b, n, _, _, _ in WB], fontsize=8.6)
    ax.axvline(4.5, color=RULE, lw=1)
    ax.set(ylim=(-3, 45)); ax.set_ylabel(t['w_y'], fontsize=9)
    ax.legend(loc='lower left', bbox_to_anchor=(0.0, 1.0), ncol=3, fontsize=9, frameon=False, borderaxespad=.3, columnspacing=1.8)
    y = 120
    for s in t['w_note']:
        y = paragraph(base, 1250, y, s, 502, 9.4) + 22
    return fig


def draw(lang):
    out = []
    with drawing_style():
        out.append(export(build_cells(lang), 'advection_donor_cells', lang))
        out.append(export(build_rule(lang), 'advection_donor_rule', lang))
        out.append(export(build_chichibu(lang), 'advection_donor_chichibu', lang))
        out.append(export(build_wetbank(lang), 'advection_donor_wetbank', lang))
    return out[-1]
