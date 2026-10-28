#!/usr/bin/env python3
# test/hillsoil の検定(make_init.py・param*.txt と定数を対で保守)
#   python3 Check_hillsoil.py wthr    W1 風化の分布(save_wthr_none・save_wthr_map の z・sd)
#   python3 Check_hillsoil.py c2      C2 定常斜面(save_c2_w3・save_c2_w6 の z・sd、result の Z、
#                                     Screen_c2_*.log の開境界の台帳)
# W1: 生成速度 W = W0 m(i, j)、dsd/dt = W exp(−sd/sd*) の解析解
#   sd(T) = sd* ln(e^{sd0/sd*} + W T/sd*)
# は、更新式 sd += sd* ln(1 + (W dts/sd*) e^{−sd/sd*})(指数の厳密積分)と刻みによらず
# 一致する(u = e^{sd/sd*} が毎回 W dts/sd* ずつ増える)。全セルで丸めの水準の一致、倍率 0 の
# セルの不変(ln 1 = 0)、z の不変(風化は岩盤面 z − sd を下げるだけ)を確かめる。
# C2: 隆起 U・風化 W0 e^{−H/sd*}・深さ依存クリープ q = −D (1 − e^{−H/H_c}) ∇z の斜面は、定常で
#   岩盤面が動かない(W(H) = U)ので土層厚 H_ss = sd* ln(W0/U)、z が動かない(∇·q = U)ので
#   横断の曲率 ∇²z = −U/D_eff(D_eff = D (1 − e^{−H_ss/H_c}))。分水界(壁)の流束 0 と合わせ、
#   渓流から k セル目の高さは (U/D_eff)(k L − k(k−1)/2)(離散でも 2 階差分が厳密に −U/D_eff)。
import sys, os, math, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, Z0, wmult, C2_NX, C2_NY, C2_IC, C2_L, c2_z

KYR_S = 1000.0 * 365.25 * 86400.0    # m_geomorph の kyr_s
# 構成 wthr(param_wthr_*.txt)
WT_P0, WT_SDS = 50.0, 0.5            # wthr_p0 (mm/kyr)、wthr_sdstar (m)
WT_DT, WT_TT, WT_MORF = 1.0, 100.0, 1.0e10
TOL_WTHR = 1.0e-12                   # 相対(倍精度の丸めの累積は 1e-15 程度)
# 構成 c2(param_c2_*.txt)
YR_S = 365.25 * 86400.0              # m_geomorph の yr_s
C2_UP0, C2_SDS, C2_D, C2_HC, C2_LAM = 63115.2, 0.5, 2.3817e-5, 0.3, 0.4   # uplift0 (mm/yr) ほか
C2_CFGS = (("c2_w3", 1.893456e8), ("c2_w6", 3.786912e8))                 # (構成, wthr_p0 mm/kyr)
C2_TT, C2_DTF, C2_MORF, C2_NOUT = 12500.0, 1250.0, 400.0, 10
C2_J1, C2_J2 = 7, 18                 # 検定する行(南北の端の壁の境界層を避けた中央の半分)
TOL_C2_STEADY, TOL_C2_HSS, TOL_C2_CURV, TOL_C2_BUDGET, TOL_C2_ROCK = 0.01, 0.01, 0.05, 1.0e-8, 1.0e-9


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


def load_text(fn):
    return [[float(v) for v in line.split()] for line in open(fn) if line.strip()]


def report(label, ok, detail):
    print("%s: %s : %s" % (label, detail, "PASS" if ok else "FAIL"))
    return ok


def check_wthr():
    w0 = WT_P0 * 1.0e-3 / KYR_S                     # m/s
    tgeo = round(WT_TT / WT_DT) * WT_DT * WT_MORF   # 地形の時間(毎ステップ更新)
    sd0 = load_text("sdinit.txt")
    ok = True
    for c, mult in (("wthr_none", lambda i, j: 1.0), ("wthr_map", wmult)):
        _, z, sd = load_state("save_" + c, NX, NY)
        emax, nzero, zbad, zerobad = 0.0, 0, 0, 0
        for j in range(NY):
            for i in range(NX):
                m = mult(i + 1, j + 1)
                if z[j][i] != Z0:
                    zbad += 1
                if m == 0.0:
                    nzero += 1
                    if sd[j][i] != sd0[j][i]:
                        zerobad += 1
                    continue
                sa = WT_SDS * math.log(math.exp(sd0[j][i] / WT_SDS) + m * w0 * tgeo / WT_SDS)
                emax = max(emax, abs(sd[j][i] - sa) / sa)
        ok &= report("(W1) %s" % c, emax < TOL_WTHR,
                     "解析解との max 相対誤差 %.2e (許容 %.0e)" % (emax, TOL_WTHR))
        ok &= report("(W1) %s" % c, zbad == 0, "z の変わったセル %d" % zbad)
        if nzero > 0:
            ok &= report("(W1) %s" % c, zerobad == 0,
                         "倍率 0 のセル %d のうち土層厚の変わったセル %d" % (nzero, zerobad))
    return ok


def load_bil(resdir, name, k, nx, ny):
    data = open("%s/%s%04d.bil" % (resdir, name, k), "rb").read()
    return grid(list(struct.unpack("<%df" % (nx * ny), data)), nx)


def net_out(logfile):
    """開境界を通った掃流砂の正味の固体体積(dispose の台帳。developer.md §89.12)"""
    v = None
    pat = re.compile(r"open boundaries \(out - in\)\s+(\S+) m3")
    for line in open(logfile, encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if m:
            v = float(m.group(1))
    if v is None:
        sys.exit("FAIL: open-boundary ledger line not found in %s" % logfile)
    return v


def check_c2():
    """C2: 中央の行(C2_J1〜C2_J2)の斜面で H_ss・曲率、全セルの定常性、土砂収支、渓流の岩盤面の不変"""
    u = C2_UP0 * 1.0e-3 / YR_S
    tg = C2_TT * C2_MORF
    ic = C2_IC - 1
    ok = True
    for c, p0 in C2_CFGS:
        w0 = p0 * 1.0e-3 / KYR_S
        hss = C2_SDS * math.log(w0 / u)
        deff = C2_D * (1.0 - math.exp(-hss / C2_HC))
        curv_a = -u / deff
        _, z, sd = load_state("save_" + c, C2_NX, C2_NY)
        za = load_bil("result_" + c, "Z", C2_NOUT - 1, C2_NX, C2_NY)
        zb = load_bil("result_" + c, "Z", C2_NOUT, C2_NX, C2_NY)
        steady = max(abs(zb[j][i] - za[j][i]) for j in range(C2_NY) for i in range(C2_NX)) \
            / (C2_DTF * C2_MORF) / u
        eh = ec = 0.0
        for j in range(C2_J1 - 1, C2_J2):
            for side in (1, -1):
                prof = [z[j][ic + side * k] for k in range(0, C2_L + 1)]
                prof.append(prof[C2_L])                  # 分水界(壁)の鏡像 = 流束 0
                for k in range(1, C2_L + 1):
                    eh = max(eh, abs(sd[j][ic + side * k] / hss - 1.0))
                    d2 = prof[k + 1] - 2.0 * prof[k] + prof[k - 1]
                    ec = max(ec, abs(d2 / curv_a - 1.0))
        z0 = [[c2_z(i + 1, j + 1) for i in range(C2_NX)] for j in range(C2_NY)]
        rock = max(abs((z[j][ic] - sd[j][ic]) - z0[j][ic]) for j in range(C2_NY))
        vout = net_out("Screen_%s.log" % c)
        nhill = (C2_NX - 1) * C2_NY
        sum_dz = sum(z[j][i] - z0[j][i] for j in range(C2_NY) for i in range(C2_NX))
        pred = u * tg * nhill - vout / (1.0 - C2_LAM)
        bud = abs(sum_dz - pred) / (u * tg * nhill)     # 隆起量に対する比(正味の Σ は差が小さく、
                                                        # 台帳の表示 10 桁の丸めが 5e-9 に拡大する)
        jm = (C2_J1 + C2_J2) // 2 - 1
        rel = " ".join("%.4f" % (z[jm][ic + k] - z[jm][ic]) for k in range(1, C2_L + 1))
        rel_a = " ".join("%.4f" % (u / deff * (k * C2_L - k * (k - 1) / 2.0)) for k in range(1, C2_L + 1))
        print("(C2) %s: H_ss = %.4f m、D_eff = %.4e m2/s、U/D_eff = %.4f 1/m。行 %d の渓流からの高さ %s"
              "(解析解 %s)" % (c, hss, deff, u / deff, jm + 1, rel, rel_a))
        ok = report("(C2) %s 定常性" % c, steady < TOL_C2_STEADY,
                    "max|dz/dt| / U = %.2e (許容 %.0e)" % (steady, TOL_C2_STEADY)) and ok
        ok = report("(C2) %s 土層厚" % c, eh < TOL_C2_HSS,
                    "行 %d〜%d の斜面で max|H/H_ss − 1| = %.2e (許容 %.0e)" % (C2_J1, C2_J2, eh, TOL_C2_HSS)) and ok
        ok = report("(C2) %s 曲率" % c, ec < TOL_C2_CURV,
                    "行 %d〜%d の斜面で max|∇²z/(−U/D_eff) − 1| = %.2e (許容 %.0e)"
                    % (C2_J1, C2_J2, ec, TOL_C2_CURV)) and ok
        ok = report("(C2) %s 土砂収支" % c, bud < TOL_C2_BUDGET,
                    "Σ(z − z0)A = %.4f m3、隆起 %.4f − 流出 %.4f/(1 − λ) = %.4f、差/隆起量 %.1e (許容 %.0e)"
                    % (sum_dz, u * tg * nhill, vout, pred, bud, TOL_C2_BUDGET)) and ok
        ok = report("(C2) %s 渓流の岩盤面" % c, rock < TOL_C2_ROCK,
                    "max|(z − sd) − z0| = %.1e m (許容 %.0e。隆起・風化しない固定床)" % (rock, TOL_C2_ROCK)) and ok
    return ok


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "wthr"
    if kind == "wthr":
        ok = check_wthr()
    elif kind == "c2":
        ok = check_c2()
    else:
        sys.exit("unknown check: " + kind)
    sys.exit(0 if ok else 1)
