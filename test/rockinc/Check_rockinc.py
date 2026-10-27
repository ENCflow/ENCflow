#!/usr/bin/env python3
# rockinc 検定(流水による岩盤下刻 f_rockinc。developer.md §88、docs/mountain_stream_plan.md §4.9)
#   Check_rockinc.py cover    T2: 自己被覆の解析解 e^{H/H*} = 1 + E_p0 t/H*(構成 cover)と、
#                                 更新間隔・加速係数を変えた構成(cover_dtg・cover_mf)の一致
#   Check_rockinc.py pluck    T3: 剥離物による被覆の準定常が、局所の水理から解いた漸化式
#                                 q_j = q_{j-1} + a_j (1 − q_j/q_c)、F_s(H_j) = q_j/q_c に一致。
#                             T7: morfac = 5・20 の構成(pluck_mf5・mf20)の累積下刻量が O(dts) で一致
#   Check_rockinc.py box LOG  T4: 閉じた箱の保存(Σ(z − z0) = 0、Σ(sd − sd0) = Σ Ri = 台帳の剥離量)
#   Check_rockinc.py steep    T9: 急勾配の等流で、セル値の Manning 閉じの τ_b と等流の釣り合いの比を
#                                 記録する(合否なし。動的振り替えの影響の記録。README の所見)
# 水理(h、|V|、v)は最終時刻の分布出力(bil = 単精度)、H = sd・z・Ri は save(倍精度)から読む。
# 定数は param*.txt・make_init.py と対で保守する。
import sys, os, math, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, DX, I1, I2, S, N, NX_ST, I1_ST, I2_ST, SLOPES_ST, BX_NX, BX_NY, fr_box, z_of

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
# 構成 box(T4)
BX_SD0, BX_Z0 = 0.005, 0.0
TOL_SUMZ, TOL_LEDGER, MIN_VP, MIN_DZ = 1.0e-9, 1.0e-7, 1.0e-3, 1.0e-4


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


def ledger(logfile):
    """dispose の台帳行(剥離のかさ体積)を読む(ファイル中の最後の行)"""
    vp = None
    pat = re.compile(r"rock incision: plucked\s+(\S+) m3")
    for line in open(logfile, encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if m:
            vp = float(m.group(1))
    if vp is None:
        sys.exit("FAIL: ledger line not found in %s" % logfile)
    return vp


def check_box(logfile):
    """T4: 閉じた箱の保存(剥離は z を動かさず sd を増やす。掃流砂は反対称)"""
    _, z, sd = load_state("save_box", BX_NX, BX_NY)
    ri = load_ri("save_box", BX_NX, BX_NY)
    vp = ledger(logfile)
    area = 1.0 * 1.0
    sum_dz = sum(z[j][i] - BX_Z0 for j in range(BX_NY) for i in range(BX_NX)) * area
    sum_dsd = sum(sd[j][i] - BX_SD0 for j in range(BX_NY) for i in range(BX_NX)) * area
    sum_ri = sum(ri[j][i] for j in range(BX_NY) for i in range(BX_NX)) * area
    max_dz = max(abs(z[j][i] - BX_Z0) for j in range(BX_NY) for i in range(BX_NX))
    ok = report("(T4-1) 全固体", abs(sum_dz) < TOL_SUMZ, "Σ(z − z0) A = %.3e m3 (tol %.0e)" % (sum_dz, TOL_SUMZ))
    ok = report("(T4-2) 可動層", abs(sum_dsd / vp - 1.0) < TOL_LEDGER,
                "Σ(sd − sd0) A = %.9e m3、台帳の剥離量 %.9e m3 (相対 tol %.0e)" % (sum_dsd, vp, TOL_LEDGER)) and ok
    ok = report("(T4-3) 累積下刻", abs(sum_ri / vp - 1.0) < TOL_LEDGER,
                "Σ Ri A = %.9e m3 (相対 tol %.0e)" % (sum_ri, TOL_LEDGER)) and ok
    ok = report("(T4-4) 活性", vp > MIN_VP and max_dz > MIN_DZ,
                "剥離量 %.3e m3 (min %.0e)、max|z − z0| = %.3e m (min %.0e)" % (vp, MIN_VP, max_dz, MIN_DZ)) and ok
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
    elif what == "box":
        ok = check_box(sys.argv[2])
    elif what == "steep":
        ok = check_steep()
    else:
        sys.exit("usage: Check_rockinc.py cover|pluck|box LOG|steep")
    sys.exit(0 if ok else 1)
