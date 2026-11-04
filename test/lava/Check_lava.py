#!/usr/bin/env python3
# lava(溶岩流 = Bingham 粘性重力流)検定
#   使い方: Check_lava.py <savedir> <huppert|bingham|dome|wall|bury|cool|adv|run|heat> [画面出力のログ ...]
#
#   huppert モード(構成1: Newton 極限の相似解。param.txt と対):
#     (1) 台帳    : |Σhl − V_in/A_cell| < TOL_SUM(注入は厳密加算・
#                   拡散はエッジ反対称 = 機械精度で保存)
#     (2) 解析解  : 面積等価半径 r_A = √(N_wet dx dy/π) が
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
import sys, struct, math, re

TOL_SUM = 1.0e-8
GG = 9.8
# --- 構成1(param.txt と対で保守)---
NX1, NY1, DX1 = 61, 61, 1.0
Q1, T1, DT1 = 0.5, 600.0, 0.5    # 噴出率 (m3/s), 継続 (s), dt (s)
RHO1, VISC1 = 2600.0, 2.0e4
HL_EPS = 1.0e-6                  # wet 判定の溶岩厚閾値 (m)
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
