#!/usr/bin/env python3
# rockinc 検定(流水による岩盤下刻 f_rockinc。developer.md §88、docs/mountain_stream_plan.md §4.9)
#   Check_rockinc.py cover    T2: 自己被覆の解析解 e^{H/H*} = 1 + E_p0 t/H*(構成 cover)と、
#                                 更新間隔・加速係数を変えた構成(cover_dtg・cover_mf)の一致
#   Check_rockinc.py pluck    T3: 剥離物による被覆の準定常が、局所の水理から解いた漸化式
#                                 q_j = q_{j-1} + a_j (1 − q_j/q_c)、F_s(H_j) = q_j/q_c に一致。
#                             T7: morfac = 5・20 の構成(pluck_mf5・mf20)の累積下刻量が O(dts) で一致
#   Check_rockinc.py hump     T3: 研磨だけの構成で、給砂比 r = q_in/q_c ごとの定常の下刻速度が
#                                 β q_in (1 − q_in/q_c)(山形)、被覆率が q_in/q_c に一致。r >= 1 は全被覆
#   Check_rockinc.py box LOG  T4: 閉じた箱の保存(Σ(z − z0) A = −研磨量、Σ(sd − sd0) A = 剥離量、
#                                 Σ Ri A = 剥離量 + 研磨量。台帳と比べる)
#   Check_rockinc.py uplift   T8: 隆起(出口固定)の下で定常になった縦断の勾配が、各セルで
#                                 E_p0(S) (1 − q_j/q_c(S)) = U(q_j = (1 − λ) U Δy j。等流の水理)を
#                                 解いた準解析解に近い。定常性と、局所の釣り合い B_p/dts = U も見る
#   Check_rockinc.py t11      T11(C1): 谷頭の給砂 q_in の下の定常縦断形。各セルで
#                                 (E_p0(S) + β q_j)(1 − q_j/q_c(S)) = U、
#                                 q_j = q_{j−1} + (1 − λ) Δy E_p0(S)(1 − q_j/q_c(S))(q_0 = q_in)を
#                                 等流の水理で解いた準解析解と勾配を比べ、隆起・研磨・給砂・開境界の
#                                 流出の台帳で土砂収支を閉じる
#   Check_rockinc.py steep    T9: 急勾配の等流で、セル値の Manning 閉じの τ_b と等流の釣り合いの比を
#                                 記録する(合否なし。動的振り替えの影響の記録。README の所見)
# 水理(h、|V|、v)は最終時刻の分布出力(bil = 単精度)、H = sd・z・Ri は save(倍精度)から読む。
# 定数は param*.txt・make_init.py と対で保守する。
import sys, os, math, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, DX, I1, I2, S, N, Q_UNIT, NX_ST, I1_ST, I2_ST, SLOPES_ST, BX_NX, BX_NY, fr_box, z_of

RHO, G = 1000.0, 9.8                 # m_geomorph_rockinc の rhow、既定の重力加速度
DD, DVIRT = 0.001, 0.001             # list_sysparam の dd・dv(既定)
LAM, SGRAV, TAUSC = 0.4, 1.65, 0.05  # fluv_porosity・fluv_sgrav・fluv_tausc
# 構成 cover(T2)
CV_KP, CV_TAUC, CV_M, CV_HS, CV_T = 6.0e-5, 10.0, 1.5, 0.05, 1800.0
TOL_COVER, TOL_SAME = 1.0e-5, 1.0e-9
# TOL_SAME: 露出率の厳密積分なので更新間隔・morfac を変えた差は、水理が倍精度で
# 続ける緩やかな調整(出口側で 1e-11 程度)の分しか出ない(陽解法なら 1e-1 規模の差)
# 構成 pluck(T3)
PL_KP, PL_TAUC, PL_M, PL_HS, PL_D50, PL_DTS = 3.0e-6, 10.0, 1.5, 0.01, 0.01, 1.0
TOL_PLUCK = 5.0e-3
TOL_MF_HALF, TOL_MF_DOUBLE = 2.0e-3, 4.0e-3   # T7: morfac = 5 / 20(dts の半分 / 倍。一次精度)
# 構成 hump(T3 の山形)
HU_BETA, HU_HS, HU_D50, HU_MORF, HU_QC = 0.005, 0.01, 0.01, 10.0, 1.810e-3
HU_R = (0.2, 0.5, 0.8, 1.2)          # 給砂比(inflow_qb = r HU_QC。HU_QC は等流の容量の概算)
HU_J1, HU_J2 = 21, 50                # 検定する内部のセル(入口の盛り上がり・出口の影響を避ける)
TOL_HUMP, MAX_FULL = 5.0e-3, 0.05    # r < 1 の相対差 / r >= 1 の下刻速度の上限(山の頂点に対する比)
# 構成 uplift(T8)
UP_KP, UP_TAUC, UP_M, UP_HS, UP_D50, UP_U, UP_MORF = 6.0e-6, 10.0, 1.5, 0.05, 0.01, 1.0e-5, 50.0
UP_J1, UP_J2 = 15, 58                # 検定するセル(流入セル直下の減衰する段差を避ける)
TOL_UP_STEADY, TOL_UP_BAL, TOL_UP_SLOPE, TOL_UP_TREND = 0.02, 0.02, 0.05, 0.02
# 構成 t11_*(T11 = C1。T8 と同じ水路・隆起・剥離に谷頭の給砂 q_in = r T11_QC0。地形の時間 1.5e5 s、
# 出力は 600 s(地形の時間 3e4 s)ごと)
T11_CFGS = (("t11_r02", 0.2, 0.0), ("t11_r05", 0.5, 0.0), ("t11_r08", 0.8, 0.0), ("t11_r05a", 0.5, 0.005))
T11_QC0, T11_TT, T11_DTF = 1.81e-3, 3000.0, 600.0
TOL_T11_STEADY, TOL_T11_SLOPE, TOL_T11_BUDGET = 0.02, 0.05, 1.0e-8
# 構成 box(T4)
BX_SD0, BX_Z0 = 0.005, 0.0
TOL_LEDGER, MIN_VP, MIN_DZ = 1.0e-7, 1.0e-3, 1.0e-4


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    packed_raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(packed_raw) // 8), packed_raw)
    out = [0.0] * n
    i = k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def grid(a, nx):
    return [a[j * nx:(j + 1) * nx] for j in range(len(a) // nx)]


def load_state(savedir, nx, ny):
    """state.dat の h, z, sd(倍精度。並びは h, z, hrs, hg, sd, hs)"""
    with open(savedir + "/state.dat", "rb") as f:
        h = read_rle_array(f, nx * ny)
        z = read_rle_array(f, nx * ny)
        read_rle_array(f, nx * ny)
        read_rle_array(f, nx * ny)
        sd = read_rle_array(f, nx * ny)
    return grid(h, nx), grid(z, nx), grid(sd, nx)


def load_ri(savedir, nx, ny):
    with open(savedir + "/geomorph_rockinc.dat", "rb") as f:
        return grid(read_rle_array(f, nx * ny), nx)


def load_bil(resdir, name, k, nx, ny):
    data = open("%s/%s%04d.bil" % (resdir, name, k), "rb").read()
    return grid(list(struct.unpack("<%df" % (nx * ny), data)), nx)


def taub(vv, h):
    """セル値の底面せん断応力(m_geomorph_rockinc と同じ Manning 閉じ。h_e = max(h, d_v))"""
    return RHO * G * N ** 2 * vv ** 2 / max(h, DVIRT) ** (1.0 / 3.0)


def ep0(vv, h, kp, tauc, m):
    tb = taub(vv, h)
    return kp * (tb / tauc - 1.0) ** m if tb > tauc else 0.0


def qcap(vv, h, d50):
    """単位幅の掃流砂容量(芦田・道上。m_geomorph_fluvial と同じ式。g は τ* で相殺)"""
    taus = N ** 2 * vv ** 2 / (SGRAV * d50 * max(h, DVIRT) ** (1.0 / 3.0))
    if taus <= TAUSC:
        return 0.0
    qbs = 17.0 * taus ** 1.5 * (1.0 - TAUSC / taus) * (1.0 - math.sqrt(TAUSC / taus))
    return qbs * math.sqrt(SGRAV * G * d50 ** 3)


def report(label, ok, detail):
    print("%s: %s : %s" % (label, detail, "PASS" if ok else "FAIL"))
    return ok


def check_cover():
    """T2: e^{H/H*} = 1 + E_p0 T/H*(全更新が同じ定常の水理を見る)と、更新間隔・morfac 不変"""
    hh = load_bil("result_cover", "H", 1, NX, NY)
    vv = load_bil("result_cover", "V", 1, NX, NY)
    _, _, sd = load_state("save_cover", NX, NY)
    worst, ncell, hmin, hmax = 0.0, 0, 1.0e30, 0.0
    for j in range(NY):
        for i in range(NX):
            if hh[j][i] <= DD:
                continue
            e = ep0(vv[j][i], hh[j][i], CV_KP, CV_TAUC, CV_M)
            ha = CV_HS * math.log1p(e * CV_T / CV_HS)
            worst = max(worst, abs(sd[j][i] / ha - 1.0))
            ncell += 1
            hmin, hmax = min(hmin, ha), max(hmax, ha)
    ok = report("(T2) 自己被覆の解析解", ncell == NY * (I2 - I1 + 1) and worst < TOL_COVER,
                "%d セル、H = %.4f〜%.4f m、max|H/H_a − 1| = %.2e (tol %.0e)"
                % (ncell, hmin, hmax, worst, TOL_COVER))
    for tag, tol, what in (("cover_dtg", TOL_SAME, "更新間隔 600 s(3 回)"),
                           ("cover_mf", TOL_SAME, "morfac = 2(流れの時間 900 s)")):
        _, _, sd2 = load_state("save_" + tag, NX, NY)
        d = max(abs(sd2[j][i] / sd[j][i] - 1.0) for j in range(NY) for i in range(NX) if sd[j][i] > 0.0)
        ok = report("(T2/T7) %s" % what, d < tol, "cover との max|ΔH/H| = %.2e (tol %.0e)" % (d, tol)) and ok
    return ok


def check_pluck():
    """T3: 剥離物による被覆の準定常。最終時刻の水理でエッジ容量 q_c と E_p0 を求め、
    北端(q_0 = 0)から q_j = (q_{j-1} + a_j)/(1 + a_j/q_c) を解いて F_s(H*_j) = q_j/q_c と比べる。
    H*_j = H_j + B_p(H_j) は掃流砂が見る剥離直後の厚さ(岩盤源 → 掃流砂の順。plan §4.4)"""
    hh = load_bil("result_pluck", "H", 5, NX, NY)
    vv = load_bil("result_pluck", "V", 5, NX, NY)
    vy = load_bil("result_pluck", "v", 5, NX, NY)
    _, _, sd = load_state("save_pluck", NX, NY)
    i = I1 - 1
    q, worst, fs_out = 0.0, 0.0, 0.0
    for j in range(NY):
        if j < NY - 1:      # 南隣とのエッジ(両セル平均の水理。流砂方向 = v の平均 / |V| の平均)
            vve = (vv[j][i] + vv[j + 1][i]) / 2.0
            hhe = (hh[j][i] + hh[j + 1][i]) / 2.0
            dirp = (vy[j][i] + vy[j + 1][i]) / 2.0 / vve
        else:               # 南辺の開境界面(自セルの水理)
            vve, hhe, dirp = vv[j][i], hh[j][i], vy[j][i] / vv[j][i]
        qc = qcap(vve, hhe, PL_D50) * dirp
        e = ep0(vv[j][i], hh[j][i], PL_KP, PL_TAUC, PL_M)
        a = (1.0 - LAM) * DX * e
        q = (q + a) / (1.0 + a / qc)
        bp = PL_HS * math.log1p(e * PL_DTS / PL_HS * math.exp(-sd[j][i] / PL_HS))
        fs = 1.0 - math.exp(-(sd[j][i] + bp) / PL_HS)
        worst = max(worst, abs(fs / (q / qc) - 1.0))
        fs_out = q / qc
    ok = report("(T3) 被覆の準定常(漸化式)", worst < TOL_PLUCK and fs_out > 0.1,
                "出口の被覆率 q/q_c = %.4f、max|F_s/(q/q_c) − 1| = %.2e (tol %.0e)"
                % (fs_out, worst, TOL_PLUCK))
    # T7: 加速係数の等価性(同じ地形の時間 3000 s。累積の下刻量 z − z0 が O(dts) の差で一致)
    _, z, _ = load_state("save_pluck", NX, NY)
    dz = [z[j][i] - z_of(i + 1, j + 1) for j in range(NY)]
    for tag, tol in (("pluck_mf5", TOL_MF_HALF), ("pluck_mf20", TOL_MF_DOUBLE)):
        _, z2, _ = load_state("save_" + tag, NX, NY)
        d = max(abs((z2[j][i] - z_of(i + 1, j + 1)) / dz[j] - 1.0) for j in range(NY))
        ok = report("(T7) %s" % tag, d < tol, "累積の下刻量の pluck(morfac = 10)との max 相対差 %.2e (tol %.0e)"
                    % (d, tol)) and ok
    return ok


def check_hump():
    """T3(研磨の山形): 剥離なし・研磨だけで、北端に一定の給砂 q_in = r q_c。内部のセルの定常で
    F_s(H) = q_in/q_c(エッジ容量)、E = β q_c,cell F_s (1 − F_s) = β q_in (1 − q_in/q_c)。
    E は最後の出力間隔(流れの 100 s = 地形の 1000 s)の Ri の増分から求める"""
    ok = True
    emax = 0.0
    rows = []
    for r in HU_R:
        tag = "hump_r%02d" % round(r * 10)
        hh = load_bil("result_" + tag, "H", 6, NX, NY)
        vv = load_bil("result_" + tag, "V", 6, NX, NY)
        vy = load_bil("result_" + tag, "v", 6, NX, NY)
        r5 = load_bil("result_" + tag, "Ri", 5, NX, NY)
        r6 = load_bil("result_" + tag, "Ri", 6, NX, NY)
        _, _, sd = load_state("save_" + tag, NX, NY)
        i, qin = I1 - 1, r * HU_QC
        em, eth, werr, ferr = [], [], 0.0, 0.0
        for j in range(HU_J1 - 1, HU_J2):
            vve = (vv[j][i] + vv[j + 1][i]) / 2.0
            hhe = (hh[j][i] + hh[j + 1][i]) / 2.0
            dirp = (vy[j][i] + vy[j + 1][i]) / 2.0 / vve
            f = qin / (qcap(vve, hhe, HU_D50) * dirp)
            e_model = (r6[j][i] - r5[j][i]) / (100.0 * HU_MORF)
            em.append(e_model)
            if f < 1.0:
                e_th = HU_BETA * qcap(vv[j][i], hh[j][i], HU_D50) * f * (1.0 - f)
                eth.append(e_th)
                werr = max(werr, abs(e_model / e_th - 1.0))
                ferr = max(ferr, abs((1.0 - math.exp(-sd[j][i] / HU_HS)) / f - 1.0))
        e_mean = sum(em) / len(em)
        rows.append((r, e_mean, sum(eth) / len(eth) if eth else 0.0, werr, ferr, len(eth) == len(em)))
        emax = max(emax, e_mean)
    for r, e_mean, e_th, werr, ferr, under in rows:
        if under:
            ok = report("(T3) 研磨の山形 r = %.1f" % r, werr < TOL_HUMP and ferr < TOL_HUMP,
                        "E = %.4e m/s(理論 %.4e)、max|E/E_th − 1| = %.2e、max|F_s/(q_in/q_c) − 1| = %.2e (tol %.0e)"
                        % (e_mean, e_th, werr, ferr, TOL_HUMP)) and ok
        else:
            ok = report("(T3) 研磨の山形 r = %.1f(全被覆)" % r, e_mean < MAX_FULL * emax,
                        "E = %.3e m/s = 山の頂点の %.3f 倍 (max %.2f)" % (e_mean, e_mean / emax, MAX_FULL)) and ok
    return ok


def check_uplift():
    """T8: 隆起下の定常縦断形。最後の 2 回の出力(地形の時間 1.5e4 s 間隔)で定常性を見て、
    勾配を等流の準解析解 E_p0(S) (1 − q_j/q_c(S)) = U と比べる(勾配が下流ほど急になる傾きも)。
    局所の釣り合いは 1 回の更新の剥離 B_p(H)= U dts(剥離だけの定常)"""
    z4 = load_bil("result_uplift", "Z", 4, NX, NY)
    z5 = load_bil("result_uplift", "Z", 5, NX, NY)
    hh = load_bil("result_uplift", "H", 5, NX, NY)
    vv = load_bil("result_uplift", "V", 5, NX, NY)
    _, _, sd = load_state("save_uplift", NX, NY)
    i, dts = I1 - 1, 0.1 * UP_MORF

    def uniform(slope):
        h = (Q_UNIT * N / math.sqrt(slope)) ** 0.6
        return h, Q_UNIT / h

    def slope_analytic(q):
        lo, hi = 1.0e-4, 0.05
        for _ in range(100):
            mid = math.sqrt(lo * hi)
            h, v = uniform(mid)
            if ep0(v, h, UP_KP, UP_TAUC, UP_M) * (1.0 - q / qcap(v, h, UP_D50)) > UP_U:
                hi = mid
            else:
                lo = mid
        return math.sqrt(lo * hi)

    steady = bal = sl = 0.0
    sm, sa = {}, {}
    for j in range(UP_J1 - 1, UP_J2):
        steady = max(steady, abs((z5[j][i] - z4[j][i]) / (300.0 * UP_MORF)) / UP_U)
        e = ep0(vv[j][i], hh[j][i], UP_KP, UP_TAUC, UP_M)
        bp = UP_HS * math.log1p(e * dts / UP_HS * math.exp(-sd[j][i] / UP_HS))
        bal = max(bal, abs(bp / (UP_U * dts) - 1.0))
        sm[j] = (z5[j - 1][i] - z5[j + 1][i]) / (2.0 * DX)
        sa[j] = slope_analytic((1.0 - LAM) * UP_U * DX * (j + 1))
        sl = max(sl, abs(sm[j] / sa[j] - 1.0))
    j1, j2 = UP_J1 - 1, UP_J2 - 1
    trend = (sm[j2] / sm[j1]) / (sa[j2] / sa[j1]) - 1.0
    ok = report("(T8) 定常性", steady < TOL_UP_STEADY, "max|dz/dt| / U = %.2e (tol %.0e)" % (steady, TOL_UP_STEADY))
    ok = report("(T8) 局所の釣り合い", bal < TOL_UP_BAL,
                "max|B_p/(U dts) − 1| = %.2e (tol %.0e)" % (bal, TOL_UP_BAL)) and ok
    ok = report("(T8) 勾配と準解析解", sl < TOL_UP_SLOPE,
                "j = %d〜%d で S = %.5f〜%.5f(準解析解 %.5f〜%.5f)、max|S/S_a − 1| = %.2e (tol %.0e)"
                % (UP_J1, UP_J2, sm[j1], sm[j2], sa[j1], sa[j2], sl, TOL_UP_SLOPE)) and ok
    ok = report("(T8) 下流ほど急になる傾き", abs(trend) < TOL_UP_TREND,
                "S(%d)/S(%d) の準解析解との比 − 1 = %.2e (tol %.0e)" % (UP_J2, UP_J1, trend, TOL_UP_TREND)) and ok
    return ok


def uniform_flow(slope):
    """幅一様の等流(Manning)の水深と流速(水路の単位幅流量 Q_UNIT)"""
    h = (Q_UNIT * N / math.sqrt(slope)) ** 0.6
    return h, Q_UNIT / h


def t11_profile(qin, beta):
    """T11 の準解析解: 北端から各セルの勾配 S_j と流出 q_j を解く。q_j は剥離の釣り合い
    q_j = (q_{j−1} + a)/(1 + a/q_c)(a = (1 − λ) Δy E_p0(S))で S_j から決まり、S_j は
    (E_p0(S) + β q_j)(1 − q_j/q_c(S)) = U の根(S について単調。二分法)"""
    def resid(s, qprev):
        h, v = uniform_flow(s)
        e = ep0(v, h, UP_KP, UP_TAUC, UP_M)
        qc = qcap(v, h, UP_D50)
        a = (1.0 - LAM) * DX * e
        q = (qprev + a) / (1.0 + a / qc)
        return (e + beta * q) * (1.0 - q / qc) - UP_U, q
    sa, q = [], qin
    for _ in range(NY):
        lo, hi = 1.0e-4, 0.2
        for _ in range(200):
            mid = math.sqrt(lo * hi)
            if resid(mid, q)[0] > 0.0:
                hi = mid
            else:
                lo = mid
        s = math.sqrt(lo * hi)
        q = resid(s, q)[1]
        sa.append(s)
    return sa


def net_out(logfile):
    """開境界を通った掃流砂の正味の固体体積(dispose の台帳。developer.md §88.12)"""
    v = None
    pat = re.compile(r"open boundaries \(out - in\)\s+(\S+) m3")
    for line in open(logfile, encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if m:
            v = float(m.group(1))
    if v is None:
        sys.exit("FAIL: open-boundary ledger line not found in %s" % logfile)
    return v


def check_t11():
    """T11(C1): 谷頭の給砂の下の定常縦断形。最後の 2 回の出力(地形の時間 3e4 s 間隔)で定常性、
    j = UP_J1〜UP_J2 の勾配を準解析解(t11_profile)と比べる。土砂収支は
    Σ(z − z0) A = U T N_up A − 研磨量 + (給砂 − 開境界の正味の流出)/(1 − λ)
    (剥離は z を動かさず可動層へ。N_up は隆起するセルの数 = 出口のセル以外)"""
    i = I1 - 1
    tg = T11_TT * UP_MORF
    ok = True
    smid = {}
    for c, r, beta in T11_CFGS:
        z4 = load_bil("result_" + c, "Z", 4, NX, NY)
        z5 = load_bil("result_" + c, "Z", 5, NX, NY)
        _, z, _ = load_state("save_" + c, NX, NY)
        qin = r * T11_QC0
        sa = t11_profile(qin, beta)
        steady = sl = 0.0
        sm = {}
        for j in range(UP_J1 - 1, UP_J2):
            steady = max(steady, abs((z5[j][i] - z4[j][i]) / (T11_DTF * UP_MORF)) / UP_U)
            sm[j] = (z5[j - 1][i] - z5[j + 1][i]) / (2.0 * DX)
            sl = max(sl, abs(sm[j] / sa[j] - 1.0))
        log = "Screen_%s.log" % c
        _, va = ledger(log)
        vout = net_out(log)
        vfeed = qin * tg                            # inflow_qb の固体体積(給砂は全時間一定)
        nup = NX * NY - 1
        sum_dz = sum(z[j][ii] - z_of(ii + 1, j + 1) for j in range(NY) for ii in range(NX)) * DX * DX
        pred = UP_U * tg * nup * DX * DX - va + (vfeed - vout) / (1.0 - LAM)
        bud = abs(sum_dz - pred) / abs(pred)
        j1, j2 = UP_J1 - 1, UP_J2 - 1
        smid[c] = (sm[j1], sm[j2], sa[j1], sa[j2])
        ok = report("(T11) %s 定常性" % c, steady < TOL_T11_STEADY,
                    "max|dz/dt| / U = %.2e (tol %.0e)" % (steady, TOL_T11_STEADY)) and ok
        ok = report("(T11) %s 勾配と準解析解" % c, sl < TOL_T11_SLOPE,
                    "r = %.1f、β = %g: j = %d〜%d で S = %.5f〜%.5f(準解析解 %.5f〜%.5f)、max|S/S_a − 1| = %.2e (tol %.0e)"
                    % (r, beta, UP_J1, UP_J2, sm[j1], sm[j2], sa[j1], sa[j2], sl, TOL_T11_SLOPE)) and ok
        ok = report("(T11) %s 土砂収支" % c, bud < TOL_T11_BUDGET,
                    "Σ(z − z0)A = %.4f m3、隆起 − 研磨 %.4f + (給砂 %.4f − 流出 %.4f)/(1 − λ) = %.4f、相対差 %.1e (tol %.0e)"
                    % (sum_dz, UP_U * tg * nup - va, vfeed, vout, pred, bud, TOL_T11_BUDGET)) and ok
    return ok


def ledger(logfile):
    """dispose の台帳行(剥離・研磨のかさ体積)を読む(ファイル中の最後の行)"""
    vp = va = None
    pat = re.compile(r"rock incision: plucked\s+(\S+) m3 .* abraded\s+(\S+) m3")
    for line in open(logfile, encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if m:
            vp, va = float(m.group(1)), float(m.group(2))
    if vp is None:
        sys.exit("FAIL: ledger line not found in %s" % logfile)
    return vp, va


def check_box(logfile):
    """T4: 閉じた箱の保存(剥離は z を動かさず sd を増やす。研磨は z を下げ系外へ。掃流砂は反対称)"""
    _, z, sd = load_state("save_box", BX_NX, BX_NY)
    ri = load_ri("save_box", BX_NX, BX_NY)
    vp, va = ledger(logfile)
    area = 1.0 * 1.0
    sum_dz = sum(z[j][i] - BX_Z0 for j in range(BX_NY) for i in range(BX_NX)) * area
    sum_dsd = sum(sd[j][i] - BX_SD0 for j in range(BX_NY) for i in range(BX_NX)) * area
    sum_ri = sum(ri[j][i] for j in range(BX_NY) for i in range(BX_NX)) * area
    max_dz = max(abs(z[j][i] - BX_Z0) for j in range(BX_NY) for i in range(BX_NX))
    ok = report("(T4-1) 全固体", abs(sum_dz / va + 1.0) < TOL_LEDGER,
                "Σ(z − z0) A = %.9e m3、台帳の研磨量 %.9e m3 (相対 tol %.0e)" % (sum_dz, va, TOL_LEDGER))
    ok = report("(T4-2) 可動層", abs(sum_dsd / vp - 1.0) < TOL_LEDGER,
                "Σ(sd − sd0) A = %.9e m3、台帳の剥離量 %.9e m3 (相対 tol %.0e)" % (sum_dsd, vp, TOL_LEDGER)) and ok
    ok = report("(T4-3) 累積下刻", abs(sum_ri / (vp + va) - 1.0) < TOL_LEDGER,
                "Σ Ri A = %.9e m3、剥離量 + 研磨量 %.9e m3 (相対 tol %.0e)" % (sum_ri, vp + va, TOL_LEDGER)) and ok
    ok = report("(T4-4) 活性", vp > MIN_VP and va > MIN_VP and max_dz > MIN_DZ,
                "剥離量 %.3e m3、研磨量 %.3e m3 (min %.0e)、max|z − z0| = %.3e m (min %.0e)"
                % (vp, va, MIN_VP, max_dz, MIN_DZ)) and ok
    ri0 = max(ri[j][i] for j in range(BX_NY) for i in range(BX_NX) if fr_box(i + 1, j + 1) == 0.0)
    ri1 = max(ri[j][i] for j in range(BX_NY) for i in range(BX_NX) if fr_box(i + 1, j + 1) > 0.0)
    ok = report("(T4-5) 侵食性倍率 0 の行", ri0 == 0.0 and ri1 > 0.0,
                "max Ri = %.3e m(倍率 > 0 のセルは %.3e m)" % (ri0, ri1)) and ok
    return ok


def check_steep():
    """T9(記録): 等流の中央部(j = 20〜40)のセル値の τ_b と釣り合いの比。合否は出力の有無だけ"""
    ok = True
    rows = [("steep_s%03d" % round(s * 100), s) for s in SLOPES_ST] + [("steep_s020_od0", 0.2)]
    print("(T9) 急勾配の等流: τ_b = ρ g n² V²/h^(1/3) と等流の釣り合いの比(j = 20〜40 の平均。記録)")
    print("      構成            勾配   水路中央 τ_b/ρghtanθ  τ_b/ρgh sinθcosθ   壁際 τ_b/ρghtanθ   中央 V/V_Manning(h)")
    for tag, s in rows:
        try:
            hh = load_bil("result_" + tag, "H", 1, NX_ST, NY)
            vv = load_bil("result_" + tag, "V", 1, NX_ST, NY)
        except OSError:
            print("FAIL: result_%s not found" % tag)
            ok = False
            continue
        th = math.atan(s)
        rc, rs, rw, rv = [], [], [], []
        for j in range(19, 40):
            for i, acc in ((I1_ST - 1 + (I2_ST - I1_ST) // 2, "c"), (I1_ST - 1, "w")):
                h, v = hh[j][i], vv[j][i]
                tb = taub(v, h)
                if acc == "c":
                    rc.append(tb / (RHO * G * h * s))
                    rs.append(tb / (RHO * G * h * math.sin(th) * math.cos(th)))
                    rv.append(v / (h ** (2.0 / 3.0) * math.sqrt(s) / N))
                else:
                    rw.append(tb / (RHO * G * h * s))
        vals = [sum(x) / len(x) for x in (rc, rs, rw, rv)]
        if not all(math.isfinite(x) for x in vals):
            ok = False
        print("      %-15s %5.2f   %8.4f            %8.4f            %8.4f            %8.4f" % ((tag, s) + tuple(vals)))
    print("(T9) 記録のみ(合否なし): %s" % ("出力あり" if ok else "出力なし"))
    return ok


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "cover":
        ok = check_cover()
    elif what == "pluck":
        ok = check_pluck()
    elif what == "hump":
        ok = check_hump()
    elif what == "uplift":
        ok = check_uplift()
    elif what == "box":
        ok = check_box(sys.argv[2])
    elif what == "t11":
        ok = check_t11()
    elif what == "steep":
        ok = check_steep()
    else:
        sys.exit("usage: Check_rockinc.py cover|pluck|hump|uplift|box LOG|t11|steep")
    sys.exit(0 if ok else 1)
