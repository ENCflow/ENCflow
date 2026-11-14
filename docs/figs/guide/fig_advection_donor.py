"""1 セル幅の河道と移流項の風上供給元(docs/users_guide/advection_donor.md)の図。

Regenerate only this page with make_guide_figs.py advection_donor.
模式図(図 1・2)はデータ不要。図 3 の数値は tutorials/chichibu の 200 m 格子(Step 3 の設定)を
f_advection_donor = 0・0 で dd = dv = 0.0001・3(既定)で回した結果(測線 4 の 1 分値と、30 分ごとの
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
    132, 177, 235, 299, 366, 432, 494, 548, 595, 638, 679, 716, 751, 783, 812, 839, 865, 891, 919, 951, 989, 1040, 1090, 1130,
    1166, 1204, 1250, 1300, 1353, 1405, 1458, 1513, 1570, 1628, 1688, 1750, 1814, 1880, 1948, 2019, 2089, 2167, 2250, 2329, 2409, 2499, 2601, 2710,
    2826, 2948, 3075, 3199, 3316, 3424, 3522, 3609, 3685, 3759, 3828, 3893, 3952, 4007, 4057, 4103, 4144, 4181, 4213, 4243, 4270, 4295, 4318, 4338,
    4355, 4371, 4385, 4410, 4526, 4564, 4522, 4491, 4480, 4480, 4484, 4478, 4463, 4451, 4444, 4437, 4425, 4410, 4397, 4387, 4378, 4366, 4357, 4355,
    4358, 4363, 4369, 4384, 4410, 4446, 4487, 4528, 4577, 4631, 4685, 4737, 4789, 4868, 4902, 4952, 5059, 5122, 5188, 5236, 5275, 5311, 5338, 5363,
    5394, 5426, 5443, 5445, 5444, 5456, 5478, 5490, 5480, 5457, 5443, 5449, 5457, 5443, 5403, 5355, 5326, 5318, 5304, 5263, 5202, 5152, 5132, 5123,
    5089, 5024, 4962, 4930, 4924, 4889, 4800, 4705, 4635, 4595, 4546, 4469, 4392, 4350, 4326, 4286, 4224, 4171, 4138, 4060, 3980, 3950, 3925, 3893,
    3842, 3793, 3758, 3721, 3679, 3639, 3600, 3555, 3513, 3476, 3436, 3392, 3351, 3313, 3272, 3232, 3193, 3153, 3114, 3076, 3037, 2999, 2961, 2924,
    2886, 2850, 2814, 2779, 2744, 2710, 2676, 2643, 2610, 2577, 2544, 2512, 2481, 2450, 2419, 2390, 2362, 2334, 2307, 2279, 2251, 2224, 2198, 2172,
    2146, 2120, 2094, 2069, 2045, 2021, 1997, 1973, 1950, 1928, 1922, 2037, 2130, 1977, 1817, 1782, 1787, 1799, 1778, 1742, 1716, 1764, 1891, 1736,
    1741, 1682, 1671, 1641, 1620, 1583, 1564, 1538, 1523, 1501, 1488, 1464, 1454, 1431, 1422, 1399, 1390, 1369, 1359, 1340, 1328, 1313, 1299, 1287,
    1271, 1261, 1244, 1235, 1220, 1211, 1196, 1188, 1174, 1165, 1152, 1143, 1130, 1122, 1110, 1102, 1091, 1083, 1073, 1065, 1055, 1047, 1037, 1030,
    1021, 1014, 1004, 996, 987, 980, 972, 964, 956, 948, 940, 933, 925, 918, 910, 903, 896, 889, 882, 875, 866, 859, 851, 843,
    837,
], dtype=float)
Q_O0DD = np.array([
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -2, -2, -2, -3, -3, -3, -4, -4, -4, -4,
    -4, -4, -4, -4, -4, -3, -2, -1, 0, 1, 2, 4, 6, 10, 14, 18, 24, 31, 38, 45, 54, 66, 81, 101,
    132, 177, 235, 299, 366, 432, 494, 548, 595, 638, 679, 716, 751, 783, 812, 839, 865, 891, 919, 951, 989, 1040, 1090, 1130,
    1166, 1204, 1250, 1300, 1352, 1405, 1458, 1513, 1570, 1628, 1688, 1750, 1814, 1880, 1949, 2019, 2089, 2167, 2250, 2329, 2409, 2499, 2601, 2710,
    2826, 2948, 3075, 3199, 3316, 3424, 3522, 3609, 3685, 3759, 3828, 3893, 3952, 4007, 4058, 4103, 4144, 4181, 4214, 4243, 4270, 4295, 4318, 4338,
    4356, 4371, 4385, 4405, 4518, 4566, 4528, 4492, 4481, 4481, 4483, 4475, 4460, 4449, 4442, 4432, 4417, 4402, 4389, 4377, 4363, 4347, 4335, 4330,
    4326, 4321, 4319, 4325, 4340, 4359, 4381, 4410, 4451, 4499, 4548, 4597, 4651, 4711, 4771, 4853, 4871, 4920, 5026, 5091, 5147, 5173, 5190, 5224,
    5264, 5283, 5289, 5298, 5319, 5342, 5346, 5333, 5317, 5318, 5331, 5330, 5301, 5261, 5237, 5235, 5231, 5200, 5149, 5106, 5088, 5079, 5049, 4994,
    4941, 4914, 4907, 4877, 4795, 4706, 4644, 4607, 4560, 4489, 4418, 4375, 4348, 4307, 4249, 4202, 4177, 4150, 4043, 3955, 3940, 3943, 3901, 3837,
    3793, 3775, 3747, 3699, 3653, 3623, 3592, 3547, 3504, 3472, 3437, 3395, 3354, 3318, 3283, 3244, 3204, 3166, 3131, 3095, 3056, 3017, 2983, 2947,
    2908, 2872, 2838, 2803, 2768, 2733, 2700, 2667, 2634, 2601, 2569, 2536, 2503, 2473, 2442, 2412, 2383, 2354, 2325, 2297, 2269, 2242, 2215, 2189,
    2163, 2137, 2112, 2087, 2063, 2038, 2014, 1991, 1968, 1945, 1923, 1902, 1881, 1860, 1840, 1820, 1801, 1781, 1763, 1745, 1727, 1710, 1693, 1675,
    1658, 1641, 1624, 1607, 1590, 1573, 1557, 1542, 1527, 1512, 1496, 1481, 1466, 1452, 1438, 1424, 1410, 1396, 1382, 1369, 1356, 1343, 1330, 1318,
    1305, 1293, 1281, 1269, 1257, 1245, 1234, 1222, 1211, 1200, 1190, 1179, 1168, 1158, 1147, 1137, 1127, 1118, 1108, 1098, 1089, 1079, 1070, 1061,
    1052, 1044, 1035, 1026, 1018, 1009, 1001, 993, 985, 977, 969, 961, 954, 946, 938, 931, 924, 916, 909, 902, 895, 888, 880, 872,
    864,
], dtype=float)
Q_O3 = np.array([
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -2, -2, -2, -3, -3, -3, -4, -4, -4, -4,
    -4, -4, -4, -4, -4, -3, -2, -1, 0, 1, 2, 4, 6, 10, 14, 18, 23, 30, 37, 45, 54, 66, 82, 103,
    137, 189, 257, 326, 393, 460, 524, 579, 632, 685, 736, 784, 831, 870, 905, 937, 968, 1001, 1037, 1078, 1133, 1196, 1260, 1314,
    1369, 1428, 1496, 1571, 1647, 1724, 1799, 1873, 1946, 2019, 2095, 2171, 2249, 2334, 2428, 2529, 2638, 2772, 2942, 3125, 3315, 3515, 3699, 3853,
    3981, 4087, 4186, 4288, 4382, 4462, 4536, 4600, 4641, 4679, 4740, 4792, 4835, 4875, 4910, 4946, 4980, 5009, 5033, 5052, 5067, 5077, 5082, 5086,
    5087, 5088, 5090, 5095, 5105, 5122, 5150, 5186, 5229, 5277, 5326, 5371, 5327, 5326, 5420, 5489, 5559, 5602, 5645, 5708, 5780, 5847, 5911, 5976,
    6031, 6072, 6107, 6139, 6163, 6180, 6194, 6204, 6208, 6206, 6203, 6196, 6184, 6167, 6149, 6127, 6102, 6073, 6042, 6008, 5970, 5930, 5888, 5844,
    5795, 5744, 5692, 5638, 5584, 5533, 5483, 5427, 5372, 5318, 5264, 5212, 5160, 5108, 5063, 5009, 4940, 4870, 4796, 4725, 4653, 4581, 4509, 4438,
    4367, 4296, 4226, 4158, 4092, 4027, 3964, 3901, 3840, 3781, 3724, 3668, 3614, 3561, 3508, 3457, 3408, 3359, 3311, 3263, 3217, 3172, 3127, 3083,
    3039, 2997, 2955, 2916, 2877, 2838, 2799, 2761, 2724, 2692, 2664, 2636, 2608, 2578, 2548, 2517, 2487, 2457, 2427, 2398, 2370, 2342, 2314, 2286,
    2259, 2232, 2205, 2178, 2152, 2126, 2101, 2077, 2053, 2030, 2007, 1984, 1963, 1941, 1920, 1899, 1879, 1859, 1839, 1819, 1800, 1780, 1761, 1742,
    1723, 1705, 1687, 1669, 1651, 1633, 1616, 1599, 1581, 1565, 1548, 1531, 1514, 1498, 1483, 1467, 1452, 1437, 1422, 1408, 1394, 1379, 1365, 1351,
    1337, 1324, 1311, 1298, 1285, 1277, 1270, 1260, 1249, 1236, 1223, 1210, 1199, 1188, 1176, 1165, 1154, 1143, 1132, 1122, 1111, 1100, 1090, 1080,
    1070, 1061, 1051, 1041, 1032, 1023, 1014, 1005, 996, 987, 978, 970, 962, 953, 945, 937, 929, 921, 914, 906, 899, 891, 884, 877,
    870, 863, 856, 849, 842, 836, 829, 823, 816, 810, 803, 797, 791, 785, 779, 772, 766, 761, 755, 749, 744, 738, 733, 727,
    722,
], dtype=float)
PATH_CELLS = [(207, 39), (208, 39), (209, 40), (210, 40), (211, 40), (212, 40), (213, 40), (214, 39), (215, 39), (216, 39), (217, 39), (218, 39), (219, 39), (220, 38), (221, 38), (222, 37), (222, 36), (222, 35), (222, 34)]
PATH_DIST = np.array([0.0, 200.0, 482.8, 682.8, 882.8, 1082.8, 1282.8, 1565.7, 1765.7, 1965.7, 2165.7, 2365.7, 2565.7, 2848.5, 3048.5, 3331.4, 3531.4, 3731.4, 3931.4])
PATH_Z = np.array([176.59, 168.22, 164.75, 158.71, 149.57, 142.54, 142.54, 141.21, 141.21, 141.21, 141.21, 141.21, 141.21, 141.21, 141.21, 138.69, 138.69, 138.69, 141.42])
ETA_O0_180 = np.array([176.64, 168.3, 164.82, 158.76, 150.46, 150.46, 150.21, 150.18, 148.97, 148.89, 148.83, 148.75, 148.73, 147.18, 146.8, 146.45, 144.87, 144.37, 144.16])
ETA_O3_180 = np.array([176.64, 168.3, 164.82, 158.76, 149.71, 149.02, 148.6, 148.16, 148.04, 147.94, 147.82, 147.67, 147.5, 147.15, 145.93, 145.3, 143.9, 142.73, 143.52])
ETA_O0_300 = np.array([176.61, 168.25, 164.79, 158.73, 149.6, 145.82, 145.69, 145.44, 145.39, 145.37, 145.32, 145.27, 145.24, 144.43, 143.82, 142.97, 142.55, 142.48, 142.66])
ETA_O3_300 = np.array([176.61, 168.25, 164.79, 158.73, 149.6, 145.1, 144.89, 144.35, 144.27, 144.2, 144.1, 144.0, 143.88, 143.57, 143.15, 142.25, 142.18, 142.14, 142.43])
FILM_MM = {0: 0.0, 30: 19.2, 60: 16.4, 90: 6.3, 120: 3.8, 150: 2.6, 180: 2.0, 210: 1.6, 240: 1.3, 270: 1.1, 300: 0.9, 330: 0.7, 360: 0.5}

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
 'r_note_b': 'dd(限界水深。既定 1 mm)以上では 0 と同じ値。dd 以上の水膜が平行なリンクに入るときの側方面の減速は、3 でも残る(§7)。',
 # 図 3
 'h_a': '(a) 測線 4 のハイドログラフ(秩父 200 m 格子)',
 'h_b': '(b) 池の入口付近の本川の水位(縦断)',
 'h_x': '時間 (min)', 'h_y': '流量 (m³/s)',
 'h_o0': '0(2026-11-09 までの既定)', 'h_o0dd': '0 で dd = dv = 0.0001(1/10)', 'h_o3': '3(既定)',
 'h_jump': '跳ね', 'h_pk3': '6,208 m³/s(152 分)', 'h_pk0': '5,490 m³/s(175 分)',
 'p_x': '本川に沿う距離 (km)', 'p_y': '標高・水位 (m)',
 'p_o0_180': '0、180 分', 'p_o3_180': '3、180 分', 'p_o0_300': '0、300 分', 'p_bed': '河床',
 'p_step': '① 0 の 180 分:池の入口の辺で 1.21 m の水面の段差ができている(線 k の上流の河岸のセルに 2.0 mm の水膜)。',
 'p_gone': '② 0 の 300 分:水膜が 0.9 mm と dd を割り、段差が外れている。外れた瞬間が (a) の 276 分の跳ね。',
 'p_pond': '平坦区間(池)', 'p_edge': '池の入口の辺', 'p_t4': '測線 4',
 'p_note': '窪地除去でできた平坦区間(池)の入口の辺の風上値は、線 k の上流の河岸のセル(池より 27 m 高く、雨の後に 1〜4 mm の水膜が残る)から取られる。',
 # 図 4
 'w_title': 'test/wetbank:雨で濡れた河岸による余分な水深 E(理論値 0)',
 'w_y': 'E (%)', 'w_o0': '0', 'w_o3': '3(既定)', 'w_cells': 'セル', 'w_cell1': 'セル',
 'w_note': ['格子に斜めの直線水路(ラスタでは階段)の河岸を雨で濡らし、雨の流入による増分を差し引いた余分な水深を測る。',
            '格子に沿う水路(0°)は 0・3 とも 0.2 %。斜めの水路では 0 が 10〜40 %、3 が 6〜17 %。',
            '1 セル幅のまま格子を細かくすると 0 は増える(段が増えるため)。3 で残る分の主な原因は側方面(§7)。'],
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
 'r_note_b': 'At or above dd (threshold depth, default 1 mm) the value is the same as 0. The lateral-face braking by films of dd or more on the parallel link remains with 3 (§7).',
 'h_a': '(a) Hydrograph at transect 4 (Chichibu, 200 m grid)',
 'h_b': '(b) Water level along the main river near the pond entrance',
 'h_x': 'time (min)', 'h_y': 'discharge (m³/s)',
 'h_o0': '0 (default until 2026-11-09)', 'h_o0dd': '0 with dd = dv = 0.0001 (1/10)', 'h_o3': '3 (default)',
 'h_jump': 'jump', 'h_pk3': '6,208 m³/s (152 min)', 'h_pk0': '5,490 m³/s (175 min)',
 'p_x': 'distance along the main river (km)', 'p_y': 'elevation, water level (m)',
 'p_o0_180': '0, 180 min', 'p_o3_180': '3, 180 min', 'p_o0_300': '0, 300 min', 'p_bed': 'bed',
 'p_step': '① 0 at 180 min: a 1.21 m step in the water surface at the pond-entrance edge (a 2.0 mm film on the upstream bank cell on line k).',
 'p_gone': '② 0 at 300 min: the film is 0.9 mm, below dd, and the step has been released. The moment of release is the jump at 276 min in (a).',
 'p_pond': 'flat reach (pond)', 'p_edge': 'pond-entrance edge', 'p_t4': 'transect 4',
 'p_note': 'The upwind value at the entrance edge of the flat reach (pond) left by pit filling is taken from the upstream bank cell on line k (27 m above the pond, keeping a 1-4 mm film after the rain).',
 'w_title': 'test/wetbank: extra depth E caused by rain-wetted banks (theory: 0)',
 'w_y': 'E (%)', 'w_o0': '0', 'w_o3': '3 (default)', 'w_cells': 'cells', 'w_cell1': 'cell',
 'w_note': ['A straight channel oblique to the grid (a staircase on the raster) with banks wetted by rain; the extra depth after removing the rise due to the rain inflow.',
            'Grid-aligned channel (0°): 0.2 % for both 0 and 3. Oblique channels: 10-40 % with 0 and 6-17 % with 3.',
            'Refining the grid with the channel kept one cell wide increases E for 0 (more steps). What remains with 3 comes mainly from the lateral faces (§7).'],
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
    for n, tj in enumerate((276, 286)):     # 2 つの跳ねに、同じ位置のラベルから矢印を引く
        ax.annotate(t['h_jump'] if n == 0 else '', xy=(tj, Q_O0[tj] + 80), xytext=(292, Q_O0[276] + 1250), fontsize=9, color=ORANGE,
                    arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=1))
    ax.annotate(t['h_pk3'], xy=(150, Q_O3[150] + 10), xytext=(22, 6620), fontsize=8.8, color=BLUE, va='center',
                arrowprops=dict(arrowstyle='-', color=BLUE, lw=.8))
    ax.annotate(t['h_pk0'], xy=(175, 5490), xytext=(203, 5020), fontsize=8.8, color=ORANGE,
                arrowprops=dict(arrowstyle='-', color=ORANGE, lw=.8))
    ax.set(xlim=(0, 360), ylim=(-200, 7200))
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
WB = [('0°', '50 m', 1, .2, .2), ('10°', '50 m', 1, 13.7, 8.5), ('22.5°', '50 m', 1, 32.4, 10.9),
      ('30°', '50 m', 1, 37.9, 17.0), ('45°', '50 m', 1, 9.6, 8.6), ('22.5°', '100 m', 1, 23.1, 10.4),
      ('22.5°', '25 m', 1, 40.4, 5.9), ('22.5°', '50 m', 2, 18.7, 8.4), ('22.5°', '25 m', 4, 12.2, 6.6)]


def build_wetbank(lang):
    t = T[lang]; fig, base = canvas(650)
    text(base, 48, 32, t['w_title'], 12.5, weight='bold')
    ax = plot_axes(fig, 110, 96, 1080, 440)
    xs = np.arange(len(WB))
    ax.bar(xs - .19, [r[3] for r in WB], .36, color=ORANGE, label=t['w_o0'])
    ax.bar(xs + .19, [r[4] for r in WB], .36, color=BLUE, label=t['w_o3'])
    for x, r in zip(xs, WB):
        ax.text(x - .19, r[3] + .8, f'{r[3]:g}', fontsize=7.8, ha='center', color=ORANGE)
        ax.text(x + .19, r[4] + .8, f'{r[4]:g}', fontsize=7.8, ha='center', color=BLUE)
    ax.set_xticks(xs)
    ax.set_xticklabels([f'{a}\n{b}\n{n} {t["w_cell1" if n == 1 else "w_cells"]}' for a, b, n, _, _ in WB], fontsize=8.6)
    ax.axvline(4.5, color=RULE, lw=1)
    ax.set(ylim=(0, 45)); ax.set_ylabel(t['w_y'], fontsize=9)
    ax.legend(loc='upper right', fontsize=9, frameon=False)
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
