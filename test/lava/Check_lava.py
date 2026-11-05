#!/usr/bin/env python3
# lava(溶岩流 = Bingham 粘性重力流)検定
#   使い方: Check_lava.py <savedir> <huppert|bingham|dome|wall|bury|cool|adv|run|runnz|heat|xdiff|xdiff8|chan> [画面出力のログ ...]
#
#   huppert モード(構成1: Newton 極限の相似解。param.txt と対):
#     (1) 台帳    : |Σhl − V_in/A_cell| < TOL_SUM(注入は厳密加算・
#                   拡散はエッジ反対称 = 機械精度で保存)
#     (2) 解析解  : 面積等価半径 r_A = √(N_wet dx dy/π)(N_wet は hl > HL_EPS = 1 cm のセル数)が
#                   r_N = 0.715 (g Q³/3ν)^{1/8} √t に相対 TOL_ANA 以内
#     (3) 成長則  : r_A(tt)/r_A(tt/2) が √2 に相対 TOL_GROW 以内
#   bingham モード(構成2: 停止・固化。param_ty.txt と対):
#     (1) 台帳    : |Σhl + Σ(z−z0) − V_in/A_cell| < TOL_SUM(固化は
#                   z への内部移転)
#     (2) 停止厚  : 検定窓の hl+dz の平均が h∞ = τ_y/(ρg tanθ) に
#                   相対 TOL_HINF 以内、変動係数 < TOL_CV
#     (3) 固化    : Σdz / 注入 > FRAC_SOL かつ max dz > MIN_DZ
#   dome モード(構成4: 塑性ドームの静止形。param_dome.txt と対):
#     (1) 台帳    : |Σhl − V_in/A_cell| < TOL_SUM(固化なし)
#     (2) 等方性  : 格子軸の方向(±22.5°)と斜めの方向(±22.5°)の扇形の
#                   面積等価半径の比が 1 に相対 TOL_ISO 以内
#     (3) 解析解  : h(r)² = a(R − r)(a = 2τ_y/ρg、V = (8π/15)√a R^{5/2})
#                   に対し、中心厚が H = √(aR) に相対 TOL_H4、面積等価
#                   半径が R に相対 TOL_R4 以内、r < R の RMS 誤差 < TOL_RMS4·H
#   wall モード(構成5: 壁の前の溶岩だまりの固化。param_wall.txt と対):
#     (1) 台帳    : |Σhl + Σ(z−z0) − V_in/A_cell| < TOL_SUM
#     (2) 全量固化: Σdz / 注入 > FRAC_SOL5
#     (3) 壁際    : 壁に接する列(i = IW5)の全行で hl = 0 かつ
#                   dz > FRAC_WALL5 × max dz
#   bury モード(構成6: 固化した溶岩の下の土層の埋没。param_bury.txt と対):
#     (1) 台帳    : |Σhl + Σ(z−z0) − V_in/A_cell| < TOL_SUM
#     (2) 埋没    : dz > 0 の全セルで sd = 0 かつ hg = 0、それ以外の sd = SD06
#     (3) 水の保存: |Σ(h + hrs + hg) − H06·N| < TOL_W6 × H06·N(しみ込んでいた水は
#                   地表へ移り、総量は変わらない)
#   cool モード(構成7: 静止した層の冷却。温度モード。param_cool.txt と対。
#   第3引数 = 画面出力のログ):
#     (1) 後退 Euler: 分布出力 Tl の全セルが一様で、冷却の常微分方程式の後退
#                   Euler(刻み DTW7)の漸化式と TOL_BE7 (°C) 以内(出力は小数 4 桁)
#     (2) 精度    : 温度の低下 T_v − T が厳密解(RK4、刻み 0.5 s)に相対 TOL_EX7 以内
#     (3) 固化    : 漸化式で T ≤ T_sol となる更新より前の出力は hl = H7、後の出力と
#                   最終状態は全セルが hl = 0・dz = H7(・Tl = 0)
#     (4) 熱の台帳: 画面出力の残差が噴出の相対 TOL_HB 以内、噴出・固化・放射・対流の
#                   熱量が漸化式の値に相対 TOL_PR(表示 5 桁)以内
#   adv モード(構成8: 熱の移流。温度モード・冷却なし。param_adv.txt と対。
#   第3引数 = 画面出力のログ):
#     (1) 台帳    : |Σhl − V_in/A_cell| < TOL_SUM
#     (2) 熱の保存: Σhl·Tl·A が Σ_k V_k T_k に相対 TOL_HEAT8 以内、画面出力の残差が
#                   噴出の相対 TOL_HB 以内
#     (3) 範囲    : 溶岩のある全セルで T_lo ≤ Tl ≤ T_hi(相対 1e-12 の余裕)、溶岩の
#                   ないセルは Tl = 0、両方の噴出温度から 1 K 以上離れたセルがある
#   run モード(構成9: 冷えて止まる流れ。param_run*.txt と対。<savedir> = save_run で、
#   save_run4・save_runi・save_runi4 も読む。第3・4引数 = 温度モード 2 本の画面出力のログ):
#     (1) 台帳    : 4 つの計算で |Σhl + Σdz − V_in/A_cell| < TOL_SUM、全量の固化
#                   (温度モードは hl = 0、等温は Σdz/V_in > FRAC_SOL5)
#     (2) 熱の台帳: 温度モード 2 本の画面出力の残差が噴出の相対 TOL_HB 以内
#     (3) 温度モード: 流れの長さ L(4Q)/L(Q) > RATIO_T9(同じ体積。L は噴火口から、
#                   行平均の堆積厚 > DZ_RUN の最も下流のセルまで)
#     (4) 等温    : |L(4Q)/L(Q) − 1| ≤ TOL_I9(長さは体積で決まり噴出率によらない)
#   heat モード(構成9r: リスタートした計算の熱の台帳。<savedir> は使わない。第3引数 = ログ):
#     (1) 画面出力の残差(開始時 + 噴出 − 放射 − 対流 − 固化 − 残存)が相対 TOL_HB 以内
#   xdiff モード(構成10: 熱の横断の数値拡散。param_x*.txt と対。<savedir> は使わず、
#   save_x0・save_x0m・save_x45・save_x45m と Screen_x*.log を読む):
#     (1) 台帳    : 4 つの計算で |Σhl − V_in/A_cell| < TOL_SUM、Σhl·Tl·A が Σ V_k T_k に
#                   相対 TOL_HEAT8 以内、画面出力の残差が相対 TOL_HB 以内
#     (2) 0°      : 検定の列 IST0 の全セルが自分の側の噴出温度に TOL_T0 (°C) 以内
#                   (1 次風上・MUSCL とも。格子軸に沿う流れでは横断の数値拡散が出ない)
#     (3) 45° 1 次: 反対角線 i + j = m の上の温度 θ = (Tl − T_c)/(T_h − T_c) から境目の幅
#                   σ = √π ∫ θ(1 − θ) dn(誤差関数の形なら標準偏差)を求め、検定の線
#                   MST45 の最初と最後の σ² の増え方 D⊥ = u Δσ²/(2 Δs) が
#                   (√2/4)·u·Δx = 0.354·u·Δx に相対 TOL_D45 以内(u = q/h、h は境目の両側の
#                   セルの厚さの平均)
#     (4) 45° MUSCL: 同じ D⊥ が 1 次の RATIO_M45 倍未満、溶岩のある全セルで
#                   T_c ≤ Tl ≤ T_h(相対 1e-12 の余裕)
#   xdiff8 モード(構成10d: 構成10 を流動の 8 近傍の 9 点 d = 1/3 で。param_x*d.txt と対。<savedir> は使わず、
#   save_x0d・save_x0dm・save_x45d・save_x45dm と Screen_x*d.log を読む):
#     (1) 台帳    : xdiff (1) と同じ
#     (2) 1 次風上: 0° と 45° の横断の拡散係数 D⊥/(u Δx) が (1 − d)F(φ) + d√2 F(φ − 45°)(F は 4 近傍の
#                   1 次風上の (|cos φ| sin²φ + |sin φ| cos²φ)/2。d = 1/3 で 0° 0.1667、45° 0.2357。§99)に
#                   相対 TOL_D45 以内。0° の σ は検定の列 IST0 の上の行の向きの θ から、45° は xdiff と同じ
#     (3) MUSCL   : 0° と 45° の D⊥ が同じ向きの 1 次の RATIO_M45 倍未満、溶岩のある全セルで T_c ≤ Tl ≤ T_h
#   runnz モード(構成9n: 構成9 の温度モードの 2 本を、地盤に ±1 mm の決まった乱れを加えて。param_run*nz.txt と対。
#   <savedir> は使わず save_runnz・save_run4nz と画面出力のログ 2 本(第3・4引数)を読む):
#     (1) 台帳と全量の固化、(2) 熱の台帳、(3) L(4Q)/L(Q) > RATIO_T9(run と同じ)。横に一様な構成9 の流れは
#     乱れがあると流れの筋に分かれて長く伸びる(熱と粘度の正の帰還。§97 の訂正)ので、行の間の堆積厚の
#     ばらつきも表示する
#   chan モード(構成11: 谷の通水能の向きによる差。8 近傍の 9 点と塞がれた配分の振り替え。
#   param_ch*.txt と対。<savedir> は使わず、save_ch0w1・ch45w1・ch0w3・ch45w3・ch45w3q を読む):
#     通水能の比 k = Q/(W·(ρg/3η)·h³·S)(h は谷の中ほどの検定の範囲の溶岩厚の平均、W は谷の幅
#     = 0° でセル数 × Δx、45° で本数 × Δx/√2。浅い流れの幅あたりの流量 (ρg/3η) h³ S と
#     比べる。側壁の抵抗はモデルにないので、向きによらず k = 1 が正しい)
#     (1) 台帳    : 5 つの計算で |Σhl − V_in/A_cell| < TOL_SUM
#     (2) 0°      : 1 セル・3 セルの谷で |k − 1| < TOL_K0
#     (3) 45° 1 本: |k − 1| < TOL_K1(4 近傍では斜めの 1 セル幅の谷はつながらず流れない)
#     (4) 45° 3 本: |k − 1| < TOL_K3(帯の縁の振り替えの規則で通水能が多めに出る分を許す)、
#                   4 近傍の対照(ch45w3q)は k < KQ3(検定がこの差を検出できること)
import sys, struct, math, re

TOL_SUM = 1.0e-8
GG = 9.8
# --- 構成1(param.txt と対で保守)---
NX1, NY1, DX1 = 61, 61, 1.0
Q1, T1, DT1 = 0.5, 600.0, 0.5    # 噴出率 (m3/s), 継続 (s), dt (s)
RHO1, VISC1 = 2600.0, 2.0e4
HL_EPS = 0.01                    # 広がりの判定厚 (m)。1e-6 m で数えると、数値の先行の薄膜(相似解にない
                                 #   裾)まで数えて 8 近傍の 9 点では +10.9 %(4 近傍 +8.5 %)になるので、
                                 #   相似解の先端に当たる 1 cm で数える(4 近傍 +2.8 %、9 点 +3.7 %。§99)
TOL_ANA, TOL_GROW = 0.10, 0.05
# --- 構成2(param_ty.txt と対で保守)---
NX2, NY2, DX2 = 100, 8, 1.0
ST2, LX2 = 0.2, 100.0            # 斜面 tanθ, 全長(make_init.py と対)
Q2, TSUP, DT2, TT2 = 0.5, 300.0, 0.5, 1200.0
RHO2, TAUY2 = 2600.0, 2000.0
IW1, IW2 = 15, 35                # 検定窓(セル番号 i。噴火口の下流・前縁の後方)
TOL_HINF, TOL_CV = 0.20, 0.15
FRAC_SOL, MIN_DZ = 0.7, 0.2
# --- 構成4(param_dome.txt と対で保守)---
NX4, NY4, DX4 = 61, 61, 1.0
IC4, JC4 = 31, 31                # 噴火口のセル(1 始まり)
Q4, TSUP4, DT4, TT4 = 2.0, 900.0, 1.0, 6000.0
RHO4, TAUY4 = 2600.0, 1.0e4
HL_EPS4 = 0.01                   # 広がりの判定厚 (m)
TOL_ISO, TOL_H4, TOL_R4, TOL_RMS4 = 0.05, 0.05, 0.05, 0.05
# --- 構成5(param_wall.txt・make_init.py wall と対で保守)---
NX5, NY5, DX5 = 40, 8, 1.0
IWALL5, ZWALL5 = 31, 10.0        # 段(壁)の始まりの列と高さ
IW5 = IWALL5 - 1                 # 壁に接する列
Q5, TSUP5, DT5, TT5 = 0.2, 300.0, 0.5, 4800.0
FRAC_SOL5, FRAC_WALL5 = 0.999, 0.5
# --- 構成6(param_bury.txt と対で保守。地形は構成5 と同じ zwall.txt)---
SD06, H06 = 1.0, 0.05            # 初期の土層厚 (m)・初期の地表水 (m)
Q6, TON6, TOFF6, DT6, TT6 = 0.2, 900.0, 1200.0, 0.5, 6000.0
TOL_W6 = 1.0e-9
# --- 温度モード共通(m_lavaflow と同じ定数)---
SIGMA, TK0 = 5.670374419e-8, 273.15
TOL_HB, TOL_PR = 1.0e-12, 2.0e-4
# --- 構成7(param_cool.txt・make_init.py cool と対で保守)---
NX7, NY7, DX7 = 4, 8, 1.0
Q7, DTW7, DTF7, TT7 = 3.2, 10.0, 600.0, 7200.0   # 総噴出率(最初の更新だけ), 更新・出力の間隔, 計算時間
RHO7, CP7, EPS7, HC7 = 2600.0, 1150.0, 0.95, 70.0
TA7, TV7, TSOL7 = 20.0, 1100.0, 800.0
H7 = Q7 * DTW7 / (NX7 * NY7 * DX7 * DX7)          # 層の厚さ (m) = 1
RES7 = "result_cool"
TOL_BE7, TOL_EX7 = 2.0e-4, 0.01
# --- 構成8(param_adv.txt と対で保守)---
NX8, NY8, DX8 = 41, 21, 1.0
Q8, TSUP8, DT8 = 0.5, 600.0, 0.5                 # 噴火口ごとの噴出率・継続・dt
TV8 = (1150.0, 1050.0)                           # 噴出温度(噴火口1・2)
TOL_HEAT8 = 1.0e-9
# --- 構成9(param_run*.txt・make_init.py run と対で保守)---
NX9, NY9, DX9 = 64, 8, 5.0
ST9, LX9 = 0.1, 320.0
IV9 = 3                                          # 噴火口の列
RUNS9 = {"": (2.0, 2400.0), "4": (8.0, 600.0)}   # 接尾辞: (総噴出率 m3/s, 継続 s)
DT9 = 1.0
DZ_RUN = 0.05                                    # 流れの先端の判定厚 (m)
RATIO_T9, TOL_I9 = 1.5, 0.1
# --- 構成10(param_x*.txt・make_init.py x0/x45/x0c*/x45c* と対で保守)---
NX10, NY10, NB10, DX10 = 60, 20, 60, 5.0         # 0° は 60 × 20、45° は 60 × 60
TT10, DT10 = 3000.0, 2.0
Q10 = {"x0": 5.0, "x45": 9.9}                    # 噴火口ごとの噴出率 (m3/s)
QW10 = {"x0": 5.0 / (10 * DX10),                 # 幅あたりの流量 q (m2/s)
        "x45": 9.9 / (14 * math.sqrt(2.0) * DX10)}
TV10 = (1150.0, 1050.0)                          # 噴出温度(噴火口1・2)
IST0 = (10, 20, 30)                              # 0° の検定の列
MV45, MST45 = 33, (37, 43, 53, 63)               # 45° の噴火口の反対角線 i + j と検定の線
NWIN45 = 70.0                                    # 横断の積分範囲 |n| (m)
TOL_T0 = 1.0e-9
DTH45, TOL_D45 = math.sqrt(2.0) / 4.0, 0.15      # 1 次風上の D⊥/(u Δx) の理論値と許容
RATIO_M45 = 0.25
# --- 構成11(param_ch*.txt・make_init.py ch* と対で保守)---
RHO11, VISC11, ST11, DX11, TT11 = 2600.0, 1.0e3, 0.1, 5.0, 500.0
C11 = RHO11 * GG / (3.0 * VISC11)                # 幅あたりの流量 = C11·h³·S (m2/s)
CH11 = {"ch0w1": (100, 11, 1), "ch45w1": (72, 72, 1), "ch0w3": (100, 11, 3),
        "ch45w3": (72, 72, 3), "ch45w3q": (72, 72, 3)}   # (nx, ny, 谷の幅のセル数・本数)
J011, IST11, PST11 = 6, (40, 60), (64, 80)       # 0° の谷の中心の行・検定の列、45° の検定の i + j
TOL_K0, TOL_K1, TOL_K3, KQ3 = 0.01, 0.02, 0.10, 0.80
# --- 構成10d(param_x*d.txt と対で保守。格子・噴出は構成10 と同じ)---
D10D = 1.0 / 3.0                                 # 流動の斜めの配分
# --- 構成9n(param_run*nz.txt・make_init.py runnz と対で保守。格子・噴出は構成9 と同じ)---
RUNS9N = {"nz": (2.0, 2400.0), "4nz": (8.0, 600.0)}


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
    hdr = read_rec(f)
    n, nrun = struct.unpack("<2q", hdr)
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    packed_raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(packed_raw) // 8), packed_raw)
    out = [0.0] * n
    i = 0
    k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def load_hl(savedir, nx, ny):
    with open(savedir + "/lavaflow.dat", "rb") as f:
        return read_rle_array(f, nx * ny)


def load_tl(savedir, nx, ny):
    with open(savedir + "/lavaflow_temp.dat", "rb") as f:
        return read_rle_array(f, nx * ny)


def heat_ledger(logname):
    # 画面出力の熱の台帳(m_lavaflow_dispose)の最後の組を読む
    txt = open(logname, encoding="utf-8", errors="replace").read()
    num = r"([-+0-9.Ee]+)"
    m1 = re.findall(r"heat erupted\s+" + num + r" J, radiated\s+" + num + r" J, convected\s+" + num, txt)
    m2 = re.findall(r"heat in solidified lava\s+" + num + r" J, in molten lava\s+" + num, txt)
    m3 = re.findall(r"heat balance residual\s+" + num + r" J \(\s*" + num, txt)
    assert m1 and m2 and m3, "heat ledger not found in " + logname
    e = [float(v) for v in m1[-1]]
    e += [float(v) for v in m2[-1]]
    return e, float(m3[-1][1])


def cool_flux(t, ta, eps, hc):
    # 表面の熱流束 F = ε σ (T_K⁴ − Ta_K⁴) + h_c (T − Ta) の放射・対流の成分 (W/m2)
    return eps * SIGMA * ((t + TK0) ** 4 - (ta + TK0) ** 4), hc * (t - ta)


def cool_be(t0, h, dtw, rhocp, ta, eps, hc):
    # m_lavaflow の cool_be と同じ後退 Euler の 1 段(ニュートン法)
    c = dtw / rhocp
    t = t0
    for _ in range(50):
        tk = t + TK0
        hv = h * (t - t0) + c * (eps * SIGMA * (tk ** 4 - (ta + TK0) ** 4) + hc * (t - ta))
        hd = h + c * (4.0 * eps * SIGMA * tk ** 3 + hc)
        d = hv / hd
        t = max(t - d, ta)
        if abs(d) <= 4.0 * 2.220446049250313e-16 * tk:
            break
    return min(t, t0)


def load_z(savedir, nx, ny):
    ntot = nx * ny
    with open(savedir + "/state.dat", "rb") as f:
        read_rle_array(f, ntot)     # h
        z = read_rle_array(f, ntot)
    return z


def load_state_all(savedir, nx, ny):
    # state.dat の並び h, z, hrs, hg, sd, hs(m_state の save_state と対)
    ntot = nx * ny
    with open(savedir + "/state.dat", "rb") as f:
        return {k: read_rle_array(f, ntot) for k in ("h", "z", "hrs", "hg", "sd", "hs")}


def load_txt(fname, nx, ny):
    out = []
    with open(fname) as f:
        for line in f:
            out.extend(float(v) for v in line.split())
    assert len(out) == nx * ny, "unexpected matrix size in " + fname
    return out


def r_area(hl, eps, dxdy):
    nwet = sum(1 for v in hl if v > eps)
    return (nwet * dxdy / 3.141592653589793) ** 0.5


savedir = sys.argv[1]
mode = sys.argv[2]
ok = True

if mode == "huppert":
    hl = load_hl(savedir, NX1, NY1)
    # (1) 台帳(注入は毎ステップ q0*dt の厳密加算)
    vin = Q1 * DT1 * round(T1 / DT1)          # m3(一定噴出率)
    res = sum(hl) * DX1 * DX1 - vin
    ok1 = abs(res) < TOL_SUM * vin
    print("(1) 台帳  : sum(hl)*A - V_in = %.3e m3 (tol %.0e 相対) : %s"
          % (res, TOL_SUM, "PASS" if ok1 else "FAIL"))
    # (2) 先端半径(面積等価)vs Huppert 相似解
    nu = VISC1 / RHO1
    rana = 0.715 * (GG * Q1 ** 3 / (3.0 * nu)) ** 0.125 * T1 ** 0.5
    ra = r_area(hl, HL_EPS, DX1 * DX1)
    err = abs(ra - rana) / rana
    ok2 = err < TOL_ANA
    print("(2) 解析解: r_A = %.2f m vs r_N = %.2f m (err %.1f%%, tol %.0f%%) : %s"
          % (ra, rana, 100 * err, 100 * TOL_ANA, "PASS" if ok2 else "FAIL"))
    # (3) 成長則 r ∝ t^{1/2}(中間時刻の分布出力 Hl0002 = tt/2)
    hl2 = load_txt("result/Hl0002.txt", NX1, NY1)
    ratio = ra / r_area(hl2, HL_EPS, DX1 * DX1)
    err = abs(ratio - 2.0 ** 0.5) / 2.0 ** 0.5
    ok3 = err < TOL_GROW
    print("(3) 成長則: r(tt)/r(tt/2) = %.3f vs √2 (err %.1f%%, tol %.0f%%) : %s"
          % (ratio, 100 * err, 100 * TOL_GROW, "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3
elif mode == "dome":
    hl = load_hl(savedir, NX4, NY4)
    area = DX4 * DX4
    # (1) 台帳(注入は t < TSUP4 の tick ごとに Q4*dt の厳密加算。固化なし)
    nt = round(TT4 / DT4)
    vin = sum(Q4 * DT4 for it in range(1, nt + 1) if it * DT4 < TSUP4)
    res = sum(hl) * area - vin
    ok1 = abs(res) < TOL_SUM * vin
    print("(1) 台帳  : sum(hl)*A - V_in = %.3e m3 (V_in = %.1f, tol %.0e 相対) : %s"
          % (res, vin, TOL_SUM, "PASS" if ok1 else "FAIL"))
    # セルの中心から噴火口までの距離と方位(0〜90°に畳む)
    cells = []
    for idx, h in enumerate(hl):
        i = idx % NX4 + 1
        j = idx // NX4 + 1
        dx_ = (i - IC4) * DX4
        dy_ = (j - JC4) * DX4
        r = math.hypot(dx_, dy_)
        th = math.degrees(math.atan2(abs(dy_), abs(dx_)))
        cells.append((h, r, th))
    # (2) 等方性: 扇形群(4 扇形 × 45° = π)の面積等価半径 √(2 N A/π)
    nax = sum(1 for h, r, th in cells if h > HL_EPS4 and r > 0.0 and (th < 22.5 or th > 67.5))
    ndg = sum(1 for h, r, th in cells if h > HL_EPS4 and 22.5 <= th <= 67.5)
    rax = (2.0 * nax * area / math.pi) ** 0.5
    rdg = (2.0 * ndg * area / math.pi) ** 0.5
    ratio = rdg / rax
    ok2 = abs(ratio - 1.0) < TOL_ISO
    print("(2) 等方性: 面積等価半径 斜め %.2f m / 格子軸 %.2f m = %.3f (tol 1±%.2f) : %s"
          % (rdg, rax, ratio, TOL_ISO, "PASS" if ok2 else "FAIL"))
    # (3) 塑性ドームの解析解
    a = 2.0 * TAUY4 / (RHO4 * GG)
    rr = (vin / ((8.0 * math.pi / 15.0) * a ** 0.5)) ** 0.4
    hh = (a * rr) ** 0.5
    hc = hl[(JC4 - 1) * NX4 + (IC4 - 1)]
    ra = r_area(hl, HL_EPS4, area)
    sq = [(h - (a * (rr - r)) ** 0.5) ** 2 for h, r, th in cells if r < rr]
    rms = (sum(sq) / len(sq)) ** 0.5
    eh = (hc - hh) / hh
    er = (ra - rr) / rr
    ok3 = abs(eh) < TOL_H4 and abs(er) < TOL_R4 and rms < TOL_RMS4 * hh
    print("(3) 解析解: 中心厚 %.3f m vs H = %.3f m (err %+.1f%%)、r_A = %.2f m vs R = %.2f m "
          "(err %+.1f%%)、RMS = %.3f m (%.1f%% of H)(tol %.0f%%) : %s"
          % (hc, hh, 100 * eh, ra, rr, 100 * er, rms, 100 * rms / hh, 100 * TOL_H4,
             "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3
elif mode == "cool":
    logname = sys.argv[3]
    rhocp = RHO7 * CP7
    ncell = NX7 * NY7
    # 後退 Euler の漸化式(1 回目の更新で注入して冷やす。以後は更新ごとに 1 段)。
    # 台帳用に放射・対流の内訳も m_lavaflow と同じ分け方(新しい温度での比)で足す
    nmax = round(TT7 / DTW7)
    tbe = [TV7]
    erad = econ = 0.0
    nsol = None
    for n in range(1, nmax + 1):
        t0 = tbe[-1]
        t1 = cool_be(t0, H7, DTW7, rhocp, TA7, EPS7, HC7)
        dl = H7 * (t0 - t1)
        fr, fc = cool_flux(t1, TA7, EPS7, HC7)
        wr = dl * (fr / (fr + fc))
        erad += wr
        econ += dl - wr
        tbe.append(t1)
        if t1 <= TSOL7:
            nsol = n
            break
    assert nsol is not None, "the layer does not reach T_sol within tt (check the setup)"

    def rk4(tend, h=0.5):
        t, tt_ = TV7, 0.0
        f = lambda x: -sum(cool_flux(x, TA7, EPS7, HC7)) / (rhocp * H7)
        while tt_ < tend - 1e-9:
            k1 = f(t); k2 = f(t + 0.5 * h * k1); k3 = f(t + 0.5 * h * k2); k4 = f(t + h * k3)
            t += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
            tt_ += h
        return t
    # (1)(2)(3) 出力の各時刻
    nfr = round(TT7 / DTF7)
    ok1 = ok2 = ok3 = True
    emax1 = emax2 = 0.0
    for k in range(1, nfr + 1):
        n = round(k * DTF7 / DTW7)                     # この出力までの更新回数
        tl = load_txt("%s/Tl%04d.txt" % (RES7, k), NX7, NY7)
        hl = load_txt("%s/Hl%04d.txt" % (RES7, k), NX7, NY7)
        if n < nsol:
            uni = max(tl) - min(tl)
            e1 = max(abs(v - tbe[n]) for v in tl)
            emax1 = max(emax1, e1)
            ok1 = ok1 and uni <= TOL_BE7 and e1 <= TOL_BE7
            tex = rk4(n * DTW7)
            e2 = abs((TV7 - tbe[n]) - (TV7 - tex)) / (TV7 - tex)
            emax2 = max(emax2, e2)
            ok2 = ok2 and e2 < TOL_EX7
            ok3 = ok3 and min(hl) == H7 and max(hl) == H7
            print("    t = %5.0f s: Tl = %.4f °C(漸化式 %.4f、厳密解 %.4f)、hl = %.4f m"
                  % (k * DTF7, tl[0], tbe[n], tex, hl[0]))
        else:
            ok3 = ok3 and max(hl) == 0.0 and max(abs(v) for v in tl) == 0.0
            print("    t = %5.0f s: 固化済み(max hl = %.4f m、max |Tl| = %.4f)" % (k * DTF7, max(hl), max(abs(v) for v in tl)))
    print("(1) 後退 Euler: 出力 Tl と漸化式の差の最大 %.1e °C(一様、tol %.0e °C) : %s"
          % (emax1, TOL_BE7, "PASS" if ok1 else "FAIL"))
    print("(2) 精度  : 温度の低下の厳密解(RK4)との相対差の最大 %.2e(tol %.0e) : %s"
          % (emax2, TOL_EX7, "PASS" if ok2 else "FAIL"))
    hl = load_hl(savedir, NX7, NY7)
    z = load_z(savedir, NX7, NY7)
    tl = load_tl(savedir, NX7, NY7)
    ok3 = ok3 and max(hl) == 0.0 and min(z) == H7 and max(z) == H7 and max(abs(v) for v in tl) == 0.0
    print("(3) 固化  : 漸化式で更新 %d 回目(t = %.0f s、T = %.2f °C ≤ %.0f °C)に固まる。最終 max hl = %.1e m、"
          "dz = %.4f〜%.4f m(H = %.1f m) : %s"
          % (nsol, nsol * DTW7, tbe[nsol], TSOL7, max(hl), min(z), max(z), H7, "PASS" if ok3 else "FAIL"))
    # (4) 熱の台帳(J。0 °C 基準の顕熱)
    e, rres = heat_ledger(logname)
    fac = rhocp * ncell * DX7 * DX7
    exp_ = [H7 * TV7 * fac, erad * fac, econ * fac, H7 * tbe[nsol] * fac, 0.0]
    names = ["噴出", "放射", "対流", "固化", "残存"]
    ok4 = abs(rres) < TOL_HB
    for nm, v, x in zip(names, e, exp_):
        good = abs(v - x) <= TOL_PR * max(abs(x), 1.0)
        ok4 = ok4 and good
        print("    %s %.4e J(漸化式 %.4e J)%s" % (nm, v, x, "" if good else "  <- ずれ"))
    print("(4) 熱の台帳: 残差 %.2e(噴出の相対。tol %.0e)、内訳は漸化式に相対 %.0e 以内 : %s"
          % (rres, TOL_HB, TOL_PR, "PASS" if ok4 else "FAIL"))
    ok = ok1 and ok2 and ok3 and ok4
elif mode == "adv":
    logname = sys.argv[3]
    hl = load_hl(savedir, NX8, NY8)
    tl = load_tl(savedir, NX8, NY8)
    area = DX8 * DX8
    nt = round(TSUP8 / DT8)
    v1 = sum(Q8 * DT8 for it in range(1, nt + 1) if it * DT8 < TSUP8)   # 噴火口ごと (m3)
    vin = v1 * len(TV8)
    # (1) 溶岩の台帳
    res = sum(hl) * area - vin
    ok1 = abs(res) < TOL_SUM * vin
    print("(1) 台帳  : sum(hl)*A - V_in = %.3e m3 (V_in = %.2f, tol %.0e 相対) : %s"
          % (res, vin, TOL_SUM, "PASS" if ok1 else "FAIL"))
    # (2) 熱の保存(冷却なし)
    ein = sum(v1 * t for t in TV8)
    eh = sum(h * t for h, t in zip(hl, tl)) * area
    rel = (eh - ein) / ein
    e, rres = heat_ledger(logname)
    ok2 = abs(rel) < TOL_HEAT8 and abs(rres) < TOL_HB
    print("(2) 熱    : sum(hl*Tl)*A = %.6f vs sum(V_k T_k) = %.6f m3·°C(相対 %.1e、tol %.0e)、"
          "画面の残差 %.1e(tol %.0e) : %s"
          % (eh, ein, rel, TOL_HEAT8, rres, TOL_HB, "PASS" if ok2 else "FAIL"))
    # (3) 範囲と混合
    tlo, thi = min(TV8), max(TV8)
    tw = [t for h, t in zip(hl, tl) if h > 0.0]
    t0 = [t for h, t in zip(hl, tl) if h <= 0.0]
    nmix = sum(1 for t in tw if tlo + 1.0 < t < thi - 1.0)
    ok3 = (min(tw) >= tlo * (1.0 - 1e-12) and max(tw) <= thi * (1.0 + 1e-12)
           and (len(t0) == 0 or max(abs(t) for t in t0) == 0.0) and nmix > 0)
    print("(3) 範囲  : 溶岩のある %d セルの Tl = %.6f〜%.6f °C(噴出温度 %.0f〜%.0f)、混ざった帯 %d セル、"
          "溶岩のないセルの max |Tl| = %.1e : %s"
          % (len(tw), min(tw), max(tw), tlo, thi, nmix, max([abs(t) for t in t0] + [0.0]),
             "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3
elif mode == "run":
    logs = {"": sys.argv[3], "4": sys.argv[4]}
    area = DX9 * DX9
    ntot = NX9 * NY9

    def z0_9(idx):
        return ST9 * (LX9 - (idx % NX9 + 0.5) * DX9)

    def runout(sd):
        hl = load_hl(sd, NX9, NY9)
        z = load_z(sd, NX9, NY9)
        dz = [zi - z0_9(idx) for idx, zi in enumerate(z)]
        col = [sum(dz[j * NX9 + i] + hl[j * NX9 + i] for j in range(NY9)) / NY9 for i in range(NX9)]
        front = max(i + 1 for i in range(NX9) if col[i] > DZ_RUN)
        return hl, dz, (front - IV9) * DX9, max(col)
    ok1 = ok2 = True
    lens = {}
    for kind in ("", "i"):
        for suf, (q, tsup) in RUNS9.items():
            sd = savedir + kind + suf
            hl, dz, ll, cmax = runout(sd)
            vin = sum(q * DT9 for it in range(1, round(tsup / DT9) + 1) if it * DT9 < tsup)
            res = (sum(hl) + sum(dz)) * area - vin
            frac = sum(dz) * area / vin
            good = abs(res) < TOL_SUM * vin and (max(hl) == 0.0 if kind == "" else frac > FRAC_SOL5)
            ok1 = ok1 and good
            lens[kind + suf] = ll
            line = ("    %-10s Q = %.0f m3/s × %4.0f s: V_in = %.0f m3、台帳の差 %.1e m3、固化率 %.4f、"
                    "流れの長さ L = %.0f m(行平均の最大厚 %.2f m)"
                    % (sd, q, tsup, vin, res, frac, ll, cmax))
            if kind == "":
                e, rres = heat_ledger(logs[suf])
                ok2 = ok2 and abs(rres) < TOL_HB
                line += "、熱の台帳の残差 %.1e" % rres
            print(line + ("" if good else "  <- FAIL"))
    print("(1) 台帳と全量の固化(4 つの計算) : %s" % ("PASS" if ok1 else "FAIL"))
    print("(2) 熱の台帳(温度モード 2 本。tol %.0e) : %s" % (TOL_HB, "PASS" if ok2 else "FAIL"))
    rt = lens["4"] / lens[""]
    ri = lens["i4"] / lens["i"]
    ok3 = rt > RATIO_T9
    ok4 = abs(ri - 1.0) <= TOL_I9
    print("(3) 温度モード: L(4Q)/L(Q) = %.0f/%.0f m = %.2f(tol > %.1f。同じ体積で噴出率の高い流れが長い) : %s"
          % (lens["4"], lens[""], rt, RATIO_T9, "PASS" if ok3 else "FAIL"))
    print("(4) 等温    : L(4Q)/L(Q) = %.0f/%.0f m = %.2f(tol 1±%.1f。長さは体積で決まる) : %s"
          % (lens["i4"], lens["i"], ri, TOL_I9, "PASS" if ok4 else "FAIL"))
    ok = ok1 and ok2 and ok3 and ok4
elif mode == "xdiff":
    hl10, tl10 = {}, {}
    ok1 = True
    for tag in ("x0", "x0m", "x45", "x45m"):
        base = tag.rstrip("m")
        nx, ny = (NB10, NB10) if base == "x45" else (NX10, NY10)
        hl = load_hl("save_" + tag, nx, ny)
        tl = load_tl("save_" + tag, nx, ny)
        hl10[tag], tl10[tag] = hl, tl
        area = DX10 * DX10
        vin = 2 * Q10[base] * TT10
        res = sum(hl) * area - vin
        ein = sum(Q10[base] * TT10 * t for t in TV10)
        rel = (sum(h * t for h, t in zip(hl, tl)) * area - ein) / ein
        e, rres = heat_ledger("Screen_%s.log" % tag)
        okt = abs(res) < TOL_SUM * vin and abs(rel) < TOL_HEAT8 and abs(rres) < TOL_HB
        ok1 = ok1 and okt
        print("(1) %-4s台帳: sum(hl)*A - V_in = %.2e m3(V_in %.0f)、熱 相対 %.1e、画面の残差 %.1e : %s"
              % (tag, res, vin, rel, rres, "PASS" if okt else "FAIL"))
    # (2) 0°: 検定の列の全セルが自分の側の噴出温度のまま
    ok2 = True
    for tag in ("x0", "x0m"):
        hl, tl = hl10[tag], tl10[tag]
        dmax, nlv = 0.0, 0
        for i in IST0:
            for j in range(1, NY10 + 1):
                idx = (j - 1) * NX10 + i - 1
                if hl[idx] <= 0.0:
                    continue
                nlv += 1
                dmax = max(dmax, abs(tl[idx] - (TV10[0] if j <= NY10 // 2 else TV10[1])))
        okt = nlv == len(IST0) * NY10 and dmax <= TOL_T0
        ok2 = ok2 and okt
        print("(2) %-4s0°: 列 i = %s の %d セルの噴出温度との差 max %.1e °C(tol %.0e) : %s"
              % (tag, ",".join(str(i) for i in IST0), nlv, dmax, TOL_T0, "PASS" if okt else "FAIL"))
    # (3)(4) 45°: 境目の幅 σ と横断の拡散係数
    dn = math.sqrt(2.0) * DX10                   # 反対角線の上のセルの間隔
    def sigma45(tag, m):
        hl, tl = hl10[tag], tl10[tag]
        acc, hb = 0.0, []
        for i in range(1, NB10 + 1):
            j = m - i
            if j < 1 or j > NB10:
                continue
            idx = (j - 1) * NB10 + i - 1
            n = (i - j) * DX10 / math.sqrt(2.0)
            if hl[idx] <= 0.0 or abs(n) > NWIN45:
                continue
            th = (tl[idx] - TV10[1]) / (TV10[0] - TV10[1])
            acc += th * (1.0 - th) * dn
            if abs(i - j) == 1:
                hb.append(hl[idx])
        return math.sqrt(math.pi) * acc, sum(hb) / len(hb)
    dd = {}
    for tag in ("x45", "x45m"):
        sg, hs = zip(*[sigma45(tag, m) for m in MST45])
        ss = [(m - MV45) * DX10 / math.sqrt(2.0) for m in MST45]
        u = QW10["x45"] / (sum(hs) / len(hs))
        dd[tag] = u * (sg[-1] ** 2 - sg[0] ** 2) / (2.0 * (ss[-1] - ss[0])) / (u * DX10)
        print("    %-4s45°: s = %s m で σ = %s m(u = %.4f m/s)、D⊥/(u·Δx) = %.3f"
              % (tag, "/".join("%.0f" % v for v in ss), "/".join("%.2f" % v for v in sg), u, dd[tag]))
    ok3 = abs(dd["x45"] - DTH45) <= TOL_D45 * DTH45
    print("(3) x45 1 次: D⊥/(u·Δx) = %.3f vs 修正方程式 √2/4 = %.3f(相対 %.1f%%、tol %.0f%%) : %s"
          % (dd["x45"], DTH45, 100 * (dd["x45"] / DTH45 - 1), 100 * TOL_D45, "PASS" if ok3 else "FAIL"))
    tw = [t for h, t in zip(hl10["x45m"], tl10["x45m"]) if h > 0.0]
    okr = min(tw) >= TV10[1] * (1.0 - 1e-12) and max(tw) <= TV10[0] * (1.0 + 1e-12)
    ok4 = dd["x45m"] < RATIO_M45 * dd["x45"] and okr
    print("(4) x45m MUSCL: D⊥/(u·Δx) = %.3f(1 次の %.2f 倍、tol < %.2f)、Tl = %.6f〜%.6f °C : %s"
          % (dd["x45m"], dd["x45m"] / dd["x45"], RATIO_M45, min(tw), max(tw), "PASS" if ok4 else "FAIL"))
    ok = ok1 and ok2 and ok3 and ok4
elif mode == "xdiff8":
    def fcross(phi):
        # 4 近傍の 1 次風上の横断の拡散係数 D⊥/(u Δx)(正方セル。修正方程式。§97)
        c, sn = abs(math.cos(phi)), abs(math.sin(phi))
        return 0.5 * (c * sn * sn + sn * c * c)
    th0 = (1.0 - D10D) * fcross(0.0) + D10D * math.sqrt(2.0) * fcross(-math.pi / 4.0)
    th45 = (1.0 - D10D) * fcross(math.pi / 4.0) + D10D * math.sqrt(2.0) * fcross(0.0)
    hl10, tl10 = {}, {}
    ok1 = True
    for tag in ("x0d", "x0dm", "x45d", "x45dm"):
        base = tag[:3] if tag.startswith("x45") else tag[:2]
        nx, ny = (NB10, NB10) if base == "x45" else (NX10, NY10)
        hl = load_hl("save_" + tag, nx, ny)
        tl = load_tl("save_" + tag, nx, ny)
        hl10[tag], tl10[tag] = hl, tl
        area = DX10 * DX10
        vin = 2 * Q10[base] * TT10
        res = sum(hl) * area - vin
        ein = sum(Q10[base] * TT10 * t for t in TV10)
        rel = (sum(h * t for h, t in zip(hl, tl)) * area - ein) / ein
        e, rres = heat_ledger("Screen_%s.log" % tag)
        okt = abs(res) < TOL_SUM * vin and abs(rel) < TOL_HEAT8 and abs(rres) < TOL_HB
        ok1 = ok1 and okt
        print("(1) %-5s台帳: sum(hl)*A - V_in = %.2e m3(V_in %.0f)、熱 相対 %.1e、画面の残差 %.1e : %s"
              % (tag, res, vin, rel, rres, "PASS" if okt else "FAIL"))
    dd = {}
    # 0°: 検定の列の上の行の向きの θ から σ
    for tag in ("x0d", "x0dm"):
        hl, tl = hl10[tag], tl10[tag]
        sg, hs, ss = [], [], []
        for i in IST0:
            acc = 0.0
            for j in range(1, NY10 + 1):
                idx = (j - 1) * NX10 + i - 1
                th = (tl[idx] - TV10[1]) / (TV10[0] - TV10[1])
                acc += th * (1.0 - th) * DX10
            sg.append(math.sqrt(math.pi) * acc)
            hs.append(0.5 * (hl[(NY10 // 2 - 1) * NX10 + i - 1] + hl[(NY10 // 2) * NX10 + i - 1]))
            ss.append((i - 3) * DX10)
        u = QW10["x0"] / (sum(hs) / len(hs))
        dd[tag] = u * (sg[-1] ** 2 - sg[0] ** 2) / (2.0 * (ss[-1] - ss[0])) / (u * DX10)
        print("    %-5s 0°: s = %s m で σ = %s m(u = %.4f m/s)、D⊥/(u·Δx) = %.4f"
              % (tag, "/".join("%.0f" % v for v in ss), "/".join("%.2f" % v for v in sg), u, dd[tag]))
    # 45°: xdiff と同じ反対角線の σ
    dn = math.sqrt(2.0) * DX10
    for tag in ("x45d", "x45dm"):
        hl, tl = hl10[tag], tl10[tag]
        sg, hs = [], []
        for m in MST45:
            acc, hb = 0.0, []
            for i in range(1, NB10 + 1):
                j = m - i
                if j < 1 or j > NB10:
                    continue
                idx = (j - 1) * NB10 + i - 1
                n = (i - j) * DX10 / math.sqrt(2.0)
                if hl[idx] <= 0.0 or abs(n) > NWIN45:
                    continue
                th = (tl[idx] - TV10[1]) / (TV10[0] - TV10[1])
                acc += th * (1.0 - th) * dn
                if abs(i - j) == 1:
                    hb.append(hl[idx])
            sg.append(math.sqrt(math.pi) * acc)
            hs.append(sum(hb) / len(hb))
        ss = [(m - MV45) * DX10 / math.sqrt(2.0) for m in MST45]
        u = QW10["x45"] / (sum(hs) / len(hs))
        dd[tag] = u * (sg[-1] ** 2 - sg[0] ** 2) / (2.0 * (ss[-1] - ss[0])) / (u * DX10)
        print("    %-5s45°: s = %s m で σ = %s m(u = %.4f m/s)、D⊥/(u·Δx) = %.4f"
              % (tag, "/".join("%.0f" % v for v in ss), "/".join("%.2f" % v for v in sg), u, dd[tag]))
    ok2 = abs(dd["x0d"] - th0) <= TOL_D45 * th0 and abs(dd["x45d"] - th45) <= TOL_D45 * th45
    print("(2) 1 次風上: 0° D⊥/(u·Δx) = %.4f vs %.4f(相対 %+.1f%%)、45° %.4f vs %.4f(相対 %+.1f%%)(tol %.0f%%) : %s"
          % (dd["x0d"], th0, 100 * (dd["x0d"] / th0 - 1), dd["x45d"], th45, 100 * (dd["x45d"] / th45 - 1),
             100 * TOL_D45, "PASS" if ok2 else "FAIL"))
    okr = True
    for tag in ("x0dm", "x45dm"):
        tw = [t for h, t in zip(hl10[tag], tl10[tag]) if h > 0.0]
        okr = okr and min(tw) >= TV10[1] * (1.0 - 1e-12) and max(tw) <= TV10[0] * (1.0 + 1e-12)
    ok3 = dd["x0dm"] < RATIO_M45 * dd["x0d"] and dd["x45dm"] < RATIO_M45 * dd["x45d"] and okr
    print("(3) MUSCL   : 0° %.4f(1 次の %.2f 倍)、45° %.4f(%.2f 倍)(tol < %.2f)、温度の範囲 : %s"
          % (dd["x0dm"], dd["x0dm"] / dd["x0d"], dd["x45dm"], dd["x45dm"] / dd["x45d"], RATIO_M45,
             "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3
elif mode == "runnz":
    logs = sys.argv[3:5]
    ok1, ok2 = True, True
    lens, var = {}, {}
    for (tag, (qq, tsup)), logname in zip(RUNS9N.items(), logs):
        hl = load_hl("save_run" + tag, NX9, NY9)
        z = load_z("save_run" + tag, NX9, NY9)
        z0 = load_txt("wrk_zrunnz.txt", NX9, NY9)
        dz = [zi - z0i for zi, z0i in zip(z, z0)]
        vin = sum(qq * DT9 for it in range(1, round(tsup / DT9) + 1) if it * DT9 < tsup)
        res = (sum(hl) + sum(dz)) * DX9 * DX9 - vin
        okv = abs(res) < TOL_SUM * vin and max(hl) <= 0.0
        ok1 = ok1 and okv
        e, rres = heat_ledger(logname)
        ok2 = ok2 and abs(rres) < TOL_HB
        row = [sum(dz[(j - 1) * NX9 + i - 1] for j in range(1, NY9 + 1)) / NY9 for i in range(1, NX9 + 1)]
        imax = max(i for i in range(NX9) if row[i] > DZ_RUN)
        lens[tag] = (imax + 1) * DX9 - IV9 * DX9
        im = max(range(NX9), key=lambda i: row[i])
        col = [dz[(j - 1) * NX9 + im] for j in range(1, NY9 + 1)]
        var[tag] = (min(col), max(col), max(row))
        print("    save_run%-4s Q = %g m3/s × %4.0f s: 台帳の差 %.1e m3、残る溶岩 %.1e m、流れの長さ L = %.0f m、"
              "行平均の最大厚 %.2f m(その列の行の間 %.2f〜%.2f m)、熱の台帳の残差 %.1e"
              % (tag, qq, tsup, res, max(hl), lens[tag], var[tag][2], var[tag][0], var[tag][1], rres))
    print("(1) 台帳と全量の固化(乱れあり 2 計算) : %s" % ("PASS" if ok1 else "FAIL"))
    print("(2) 熱の台帳(tol %.0e) : %s" % (TOL_HB, "PASS" if ok2 else "FAIL"))
    ratio = lens["4nz"] / lens["nz"]
    ok3 = ratio > RATIO_T9
    print("(3) 温度モード: L(4Q)/L(Q) = %.0f/%.0f m = %.2f(tol > %.1f) : %s"
          % (lens["4nz"], lens["nz"], ratio, RATIO_T9, "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3
elif mode == "chan":
    kk = {}
    ok1 = True
    for tag, (nx, ny, w) in CH11.items():
        hl = load_hl("save_" + tag, nx, ny)
        m = (w - 1) // 2
        if tag.startswith("ch0"):
            weff = w * DX11
            st = [hl[(j - 1) * nx + i - 1] for i in range(IST11[0], IST11[1] + 1)
                  for j in range(J011 - m, J011 + m + 1)]
        else:
            weff = w * DX11 / math.sqrt(2.0)
            st = [hl[(j - 1) * nx + i - 1] for i in range(1, nx + 1) for j in range(1, ny + 1)
                  if abs(i - j) <= m and PST11[0] <= i + j <= PST11[1]]
        qq = float("%.6f" % (C11 * 1.0 ** 3 * ST11 * weff))   # param_ch*.txt の噴出率(厚さ 1 m の一様流)
        vin = qq * TT11
        res = sum(hl) * DX11 * DX11 - vin
        okv = abs(res) < TOL_SUM * vin
        ok1 = ok1 and okv
        h = sum(st) / len(st)
        kk[tag] = qq / (weff * C11 * h ** 3 * ST11)
        print("    %-7s: Q = %.4f m3/s、W = %.3f m、検定の %d セルの h = %.4f m(%.4f〜%.4f)、k = %.4f、"
              "台帳の差 %.1e m3 : %s" % (tag, qq, weff, len(st), h, min(st), max(st), kk[tag], res,
                                       "PASS" if okv else "FAIL"))
    print("(1) 台帳  : 5 つの計算で |sum(hl)*A - V_in| < %.0e 相対 : %s" % (TOL_SUM, "PASS" if ok1 else "FAIL"))
    ok2 = abs(kk["ch0w1"] - 1.0) < TOL_K0 and abs(kk["ch0w3"] - 1.0) < TOL_K0
    print("(2) 0°    : k = %.4f(1 セル)・%.4f(3 セル)(tol 1±%.2f) : %s"
          % (kk["ch0w1"], kk["ch0w3"], TOL_K0, "PASS" if ok2 else "FAIL"))
    ok3 = abs(kk["ch45w1"] - 1.0) < TOL_K1
    print("(3) 45° 1 本: k = %.4f(tol 1±%.2f。4 近傍では流れない) : %s"
          % (kk["ch45w1"], TOL_K1, "PASS" if ok3 else "FAIL"))
    ok4 = abs(kk["ch45w3"] - 1.0) < TOL_K3 and kk["ch45w3q"] < KQ3
    print("(4) 45° 3 本: k = %.4f(tol 1±%.2f)、4 近傍の対照 k = %.4f(tol < %.2f) : %s"
          % (kk["ch45w3"], TOL_K3, kk["ch45w3q"], KQ3, "PASS" if ok4 else "FAIL"))
    ok = ok1 and ok2 and ok3 and ok4
elif mode == "heat":
    e, rres = heat_ledger(sys.argv[3])
    ok = abs(rres) < TOL_HB
    print("(1) 熱の台帳: 残差 %.2e(開始時 + 噴出の相対。tol %.0e) : %s"
          % (rres, TOL_HB, "PASS" if ok else "FAIL"))
elif mode == "wall":
    hl = load_hl(savedir, NX5, NY5)
    z = load_z(savedir, NX5, NY5)
    area = DX5 * DX5
    dz = [zi - (ZWALL5 if idx % NX5 + 1 >= IWALL5 else 0.0) for idx, zi in enumerate(z)]
    nt = round(TT5 / DT5)
    vin = sum(Q5 * DT5 for it in range(1, nt + 1) if it * DT5 < TSUP5)
    # (1) 台帳(固化は hl → z の内部移転)
    res = (sum(hl) + sum(dz)) * area - vin
    ok1 = abs(res) < TOL_SUM * vin
    print("(1) 台帳  : (sum(hl)+sum(dz))*A - V_in = %.3e m3 (V_in = %.2f, tol %.0e 相対) : %s"
          % (res, vin, TOL_SUM, "PASS" if ok1 else "FAIL"))
    # (2) 全量の固化
    frac = sum(dz) * area / vin
    ok2 = frac > FRAC_SOL5
    print("(2) 固化  : sum(dz)*A/V_in = %.4f (tol > %.3f)、残る溶岩 max hl = %.3e m : %s"
          % (frac, FRAC_SOL5, max(hl), "PASS" if ok2 else "FAIL"))
    # (3) 壁に接する列の全行が固化して地形になった
    dzmax = max(dz)
    hw = [hl[(j - 1) * NX5 + (IW5 - 1)] for j in range(1, NY5 + 1)]
    dw = [dz[(j - 1) * NX5 + (IW5 - 1)] for j in range(1, NY5 + 1)]
    ok3 = max(hw) <= 0.0 and min(dw) > FRAC_WALL5 * dzmax
    print("(3) 壁際  : 列 i = %d の max hl = %.3e m、min dz = %.3f m(max dz %.3f m の %.0f%% 超) : %s"
          % (IW5, max(hw), min(dw), dzmax, 100 * FRAC_WALL5, "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3
elif mode == "bury":
    hl = load_hl(savedir, NX5, NY5)
    st = load_state_all(savedir, NX5, NY5)
    area = DX5 * DX5
    ntot = NX5 * NY5
    dz = [zi - (ZWALL5 if idx % NX5 + 1 >= IWALL5 else 0.0) for idx, zi in enumerate(st["z"])]
    nt = round(TT6 / DT6)
    vin = sum(Q6 * DT6 for it in range(1, nt + 1) if TON6 <= it * DT6 < TOFF6)
    # (1) 溶岩の台帳
    res = (sum(hl) + sum(dz)) * area - vin
    ok1 = abs(res) < TOL_SUM * vin
    print("(1) 台帳  : (sum(hl)+sum(dz))*A - V_in = %.3e m3 (V_in = %.2f, tol %.0e 相対) : %s"
          % (res, vin, TOL_SUM, "PASS" if ok1 else "FAIL"))
    # (2) 埋没: 溶岩の下の土層と地下水は 0、ほかの土層は初期値のまま
    foot = [idx for idx in range(ntot) if dz[idx] > 0.0]
    rest = [idx for idx in range(ntot) if dz[idx] <= 0.0]
    sdf = max(st["sd"][idx] for idx in foot)
    hgf = max(st["hg"][idx] for idx in foot)
    sdr = (min(st["sd"][idx] for idx in rest), max(st["sd"][idx] for idx in rest))
    ok2 = len(foot) > 0 and sdf == 0.0 and hgf == 0.0 and sdr[0] == SD06 and sdr[1] == SD06
    print("(2) 埋没  : 溶岩の下 %d セルの max sd = %.3e m・max hg = %.3e m、ほかの sd = %.3f〜%.3f m"
          "(初期 %.1f m) : %s" % (len(foot), sdf, hgf, sdr[0], sdr[1], SD06, "PASS" if ok2 else "FAIL"))
    # (3) 水の保存(しみ込んでいた水は地表へ移る)
    w0 = H06 * ntot * area
    w1 = (sum(st["h"]) + sum(st["hrs"]) + sum(st["hg"])) * area
    ok3 = abs(w1 - w0) < TOL_W6 * w0
    print("(3) 水    : sum(h + hrs + hg)*A = %.10f m3 vs 初期 %.10f m3(差 %.2e、tol %.0e 相対) : %s"
          % (w1, w0, w1 - w0, TOL_W6, "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3
else:
    hl = load_hl(savedir, NX2, NY2)
    z = load_z(savedir, NX2, NY2)
    ntot = NX2 * NY2

    def z0_of(idx):
        x = (idx % NX2 + 0.5) * DX2
        return ST2 * (LX2 - x)
    dz = [zi - z0_of(idx) for idx, zi in enumerate(z)]
    # 注入量: interp_series は重複時刻 (5,0.5),(5,0.0) で t=300s から 0
    #   → q = Q2 (t < TSUP), 0 (t >= TSUP)。tick 時刻 t = it*dt で厳密再現
    nt = round(TT2 / DT2)
    vin = sum(Q2 * DT2 for it in range(1, nt + 1) if it * DT2 < TSUP)
    # (1) 台帳(固化は hl → z の内部移転)
    res = (sum(hl) + sum(dz)) * DX2 * DX2 - vin
    ok1 = abs(res) < TOL_SUM * vin
    print("(1) 台帳  : (sum(hl)+sum(dz))*A - V_in = %.3e m3 (V_in = %.2f, "
          "tol %.0e 相対) : %s" % (res, vin, TOL_SUM, "PASS" if ok1 else "FAIL"))
    # (2) 停止厚 h∞ = τ_y/(ρg tanθ)(検定窓の hl+dz)
    hinf = TAUY2 / (RHO2 * GG * ST2)
    win = [idx for idx in range(ntot) if IW1 <= idx % NX2 + 1 <= IW2]
    ht = [hl[idx] + dz[idx] for idx in win]
    mean = sum(ht) / len(ht)
    cv = (sum((x - mean) ** 2 for x in ht) / len(ht)) ** 0.5 / mean
    err = abs(mean - hinf) / hinf
    ok2 = err < TOL_HINF and cv < TOL_CV
    print("(2) 停止厚: <hl+dz> = %.4f m vs h∞ = %.4f m (err %.1f%%, tol %.0f%%), "
          "CV = %.3f : %s"
          % (mean, hinf, 100 * err, 100 * TOL_HINF, cv, "PASS" if ok2 else "FAIL"))
    # (3) 固化の活性
    frac = sum(dz) * DX2 * DX2 / vin
    dzmax = max(dz)
    ok3 = frac > FRAC_SOL and dzmax > MIN_DZ
    print("(3) 固化  : sum(dz)*A/V_in = %.3f (tol > %.2f), max dz = %.3f m "
          "(tol > %.1f) : %s"
          % (frac, FRAC_SOL, dzmax, MIN_DZ, "PASS" if ok3 else "FAIL"))
    ok = ok1 and ok2 and ok3

print("== lava 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
