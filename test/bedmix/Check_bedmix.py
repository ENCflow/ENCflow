#!/usr/bin/env python3
# bedmix 検定(混合粒径 f_bedmix。developer.md §84.19、docs/mixed_sediment_plan.md §6)
#   save_*/state.dat(h, z, rsh, hg, sd, hs の順。RLE)、save_*/geomorph_bedmix.dat(粒径階の数・粒径・L_a の
#   見出しと、交換層の組成 N 面・下層の組成 N 面。RLE)、result_*/ の出力、screen_*.log の台帳を読む。
#     (1) equal(3 つの粒径階がすべて 3 mm、交換層厚 > 土層厚)と single(単一粒径 3 mm)の河床が一致し、
#         組成が変わらない(等移動度の極限)。開境界の正味の流出の合計も一致する。芦田・道上の有効掃流力
#         (f_taupart = 2。developer.md §121)を足した equal_te と single_te も同じく一致し、開境界の流出が
#         有効掃流力なしより小さい(粒径階の d_m で求めた係数 (u*e/u*)^3 が単一粒径の係数と同じに効く)
#     (2) armor(1 mm と 20 mm、遮蔽なし、給砂なし、粗粒は限界以下): 上流端の列の低下量が静的アーマーの
#         理論値 L_a F0 / (1 − f_sub) に一致し、細粒の割合が単調に減って 0 に近づく。細粒の割合の減衰率が、
#         出力の水理量から求めた 1 セルの式 dF/dt = −(1 − f_sub) Q F / L_a の率に一致する
#     (3) hide2(0.5・2・8 mm、修正 Egiazaroff): 100〜160 s に下流端の開境界を出た粒径階ごとの量(台帳)が、
#         下流端のセルの水深・流速・組成から芦田・道上(1972)式 (31)・(32) で求めた値に一致する
#     (4) bcfeed(容量給砂): 流入セルの河床と組成が変わらない
#     (5) bank(動く河岸・側岸侵食・安息角崩落・合計の給砂 + 一定の組成): 粒径階ごとの収支が閉じ、給砂が
#         合計 × 組成 × 時間に一致し、組成が 0〜1 で和が 1、河岸が動いている
#     (6) qbmix(粒径階ごとの給砂の時系列): 台帳の給砂が時系列の積分に一致し、収支が閉じる
#   組成の指定のない給砂(nofrac)が止まること、リスタート往復(rt1 → rt2 と bank)・MPI の一致は Run.sh /
#   Run_MPI.sh が見る
import sys, struct, os, math, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, J1, J2, GEOM, QBMIX, z_of

PORO, SGRAV, GRAV, RN, TAUSC = 0.4, 1.65, 9.81, 0.03, 0.05
TOL_EQ, TOL_COMP, TOL_RES, TOL_FEED = 1.0e-10, 1.0e-12, 1.0e-10, 1.0e-9
TOL_ARMOR, TOL_RATE, TOL_FORM, TOL_SERIES = 1.0e-6, 0.03, 0.005, 2.0e-3
R2 = math.sqrt(0.5)                       # 斜め方向の方向余弦(dx = dy)
WL = math.sqrt(2.0) - 1.0                 # 通過幅(既定の fluv_diagratio = 2/(2+√2)、dx = dy = 1 m)


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


def load_state(tag):
    ntot = NX * NY
    with open("save_%s/state.dat" % tag, "rb") as f:
        h = read_rle_array(f, ntot); z = read_rle_array(f, ntot); read_rle_array(f, ntot)
        read_rle_array(f, ntot); sd = read_rle_array(f, ntot)
    return h, z, sd


def load_bedmix(tag):
    ntot = NX * NY
    with open("save_%s/geomorph_bedmix.dat" % tag, "rb") as f:
        nc = struct.unpack("<i", read_rec(f))[0]
        hdr = struct.unpack("<%dd" % (nc + 1), read_rec(f))
        fa = [read_rle_array(f, ntot) for _ in range(nc)]
        fs = [read_rle_array(f, ntot) for _ in range(nc)]
    return nc, list(hdr[:nc]), hdr[nc], fa, fs


def idx(i, j):
    return (j - 1) * NX + (i - 1)


def ledger(tag):
    """screen_<tag>.log の台帳: {class: (initial, final, feed, out, residual)}"""
    txt = open("screen_%s.log" % tag, encoding="utf-8", errors="replace").read()
    led = {}
    for m in re.finditer(r"ledger class (\d+) \(d = .*?\): stock initial\s+(\S+) final\s+(\S+) feed\s+(\S+) out\s+(\S+)", txt):
        led[int(m.group(1))] = [float(m.group(k)) for k in range(2, 6)]
    for m in re.finditer(r"ledger class (\d+) residual\s+(\S+)", txt):
        led[int(m.group(1))].append(float(m.group(2)))
    return led


def read_matrix(path):
    with open(path) as f:
        return [[float(v) for v in line.split()] for line in f if line.strip()]


def outputs(tag):
    """result_<tag>/FILENUMBER.csv: [(番号, 時刻 s)](9998・9999 の期間集計は除く)"""
    res = []
    with open("result_%s/FILENUMBER.csv" % tag) as f:
        for line in f:
            if line.startswith("#"):
                continue
            c = [v.strip() for v in line.split(",")]
            if int(c[0]) < 9998:
                res.append((int(c[0]), float(c[2])))
    return res


def xi(r):
    """修正 Egiazaroff(芦田・道上 1972 式 (31))"""
    return 0.85 / r if r < 0.4 else (math.log10(19.0) / math.log10(19.0 * r)) ** 2


def qb_class(h, v, d, f, dm, hiding):
    """粒径階の単位幅流砂量(芦田・道上 式 (32)。マニング閉じ)"""
    ts = RN ** 2 * v ** 2 / (SGRAV * d * h ** (1.0 / 3.0))
    tsc = TAUSC * (xi(d / dm) if hiding else 1.0)
    if ts <= tsc:
        return 0.0
    phi = 17.0 * ts ** 1.5 * (1.0 - tsc / ts) * (1.0 - math.sqrt(tsc / ts))
    return f * phi * math.sqrt(SGRAV * GRAV * d ** 3)


ok = True


def rep(label, cond, detail):
    global ok
    ok = ok and cond
    print("%s %s : %s" % (label, detail, "PASS" if cond else "FAIL"))


# (1) equal と single
_, z_s, _ = load_state("single")
_, z_e, _ = load_state("equal")
dz = max(abs(a - b) for a, b in zip(z_s, z_e))
z0 = [z_of("std", i, j) for j in range(1, NY + 1) for i in range(1, NX + 1)]
moved = max(abs(a - b) for a, b in zip(z_s, z0))
rep("(1a) equal = single の河床", dz < TOL_EQ and moved > 1.0e-3, "max|z_equal - z_single| = %.2e m(河床の変化 %.3f m)" % (dz, moved))
nc, d, la, fa, fs = load_bedmix("equal")
f0 = [0.2, 0.3, 0.5]
dev = max(abs(fa[k][n] - f0[k]) for k in range(nc) for n in range(NX * NY))
rep("(1b) equal の組成が変わらない", dev < TOL_COMP, "max|F - F0| = %.2e" % dev)
led = ledger("equal")
out_e = sum(led[k][3] for k in led)
txt = open("screen_single.log", encoding="utf-8", errors="replace").read()
out_s = float(re.search(r"net bed load out through open boundaries \(out - in\)\s+(\S+)", txt).group(1))
rep("(1c) 開境界の正味の流出の合計", abs(out_e - out_s) <= 1.0e-8 * abs(out_s),
    "equal %.9e、single %.9e m3" % (out_e, out_s))
# (1d)(1e) 芦田・道上の有効掃流力(f_taupart = 2)の equal_te と single_te
_, z_st, _ = load_state("single_te")
_, z_et, _ = load_state("equal_te")
dzt = max(abs(a - b) for a, b in zip(z_st, z_et))
movedt = max(abs(a - b) for a, b in zip(z_st, z0))
rep("(1d) equal_te = single_te の河床", dzt < TOL_EQ and movedt > 1.0e-4,
    "max|z_equal_te - z_single_te| = %.2e m(河床の変化 %.4f m)" % (dzt, movedt))
ledt = ledger("equal_te")
out_et = sum(ledt[k][3] for k in ledt)
txt = open("screen_single_te.log", encoding="utf-8", errors="replace").read()
out_st = float(re.search(r"net bed load out through open boundaries \(out - in\)\s+(\S+)", txt).group(1))
rep("(1e) 有効掃流力の開境界の流出(equal_te = single_te、有効掃流力なしより小さい)",
    abs(out_et - out_st) <= 1.0e-8 * abs(out_st) and 0.0 < out_st < 0.95 * out_s,
    "equal_te %.9e、single_te %.9e m3(有効掃流力なしの %.3f 倍)" % (out_et, out_st, out_st / out_s))

# (2) armor
h, z, sd = load_state("armor")
nc, d, la, fa, fs = load_bedmix("armor")
fsub = 0.5
expect = la * 0.5 / (1.0 - fsub)
low = [z_of("deep", 1, j) - z[idx(1, j)] for j in range(J1, J2 + 1)]
rep("(2a) armor 上流端の低下量 = L_a F0/(1 - f_sub)", max(abs(x - expect) for x in low) < TOL_ARMOR,
    "低下 %s m、理論 %.6f m(L_a = %.6f m)" % (" ".join("%.6f" % x for x in low), expect, la))
ffine = [fa[0][idx(1, j)] for j in range(J1, J2 + 1)]
rep("(2b) armor 上流端の細粒が抜けた(静的アーマー)", max(ffine) < 1.0e-6, "max F_fine = %.2e" % max(ffine))
outs = outputs("armor")
seq, tt, hh, vv = [], [], [], []
for no, t in outs:
    fm = read_matrix("result_armor/Fa1_%04d.txt" % no)
    seq.append(fm[4][0])
    if 60.0 <= t <= 120.0:
        hm = read_matrix("result_armor/H%04d.txt" % no)
        vm = read_matrix("result_armor/V%04d.txt" % no)
        tt.append(t)
        hh.append(0.5 * (hm[4][0] + hm[4][1]))
        vv.append(0.5 * (vm[4][0] + vm[4][1]))
mono = all(b <= a + 1.0e-4 for a, b in zip(seq, seq[1:]))
rep("(2c) armor 細粒の割合が単調に減る", mono and seq[0] > 0.49, "F_fine(1,5) = %s …" % " ".join("%.4f" % x for x in seq[:8]))
sel = [(t, f) for (no, t), f in zip(outs, seq) if 60.0 <= t <= 120.0 and f > 1.0e-3]
n = len(sel)
mt = sum(t for t, _ in sel) / n
ml = sum(math.log(f) for _, f in sel) / n
fit = -sum((t - mt) * (math.log(f) - ml) for t, f in sel) / sum((t - mt) ** 2 for t, _ in sel)
q = sum(qb_class(a, b, d[0], 1.0, d[0], False) for a, b in zip(hh, vv)) / len(hh)
pred = q * 1.0 / (1.0 - PORO) * (1.0 - fsub) / la    # 上流端のセルの流出の幅は 1 m(軸 + 斜め 2 辺の通過幅の和)
rep("(2d) armor 細粒の割合の減衰率", abs(fit / pred - 1.0) < TOL_RATE, "fit %.5f 1/s、式 %.5f 1/s(60〜120 s)" % (fit, pred))

# (3) hide2
led = ledger("hide2")
nc, d, la, fa, fs = load_bedmix("hide")     # hide1 と hide2 は save_hide を共有する
outs = outputs("hide2")
rates = []
for no, t in outs:
    hm = read_matrix("result_hide2/H%04d.txt" % no)
    vm = read_matrix("result_hide2/V%04d.txt" % no)
    um = read_matrix("result_hide2/u%04d.txt" % no)
    wm = read_matrix("result_hide2/v%04d.txt" % no)
    fm = [read_matrix("result_hide2/Fa%d_%04d.txt" % (k + 1, no)) for k in range(nc)]
    r = [0.0] * nc
    for j in range(J1, J2 + 1):
        f = [fm[k][j - 1][NX - 1] for k in range(nc)]
        dm = sum(f[k] * d[k] for k in range(nc))
        uu, ww, vv = um[j - 1][NX - 1], wm[j - 1][NX - 1], vm[j - 1][NX - 1]
        # 東の開境界の 3 面(軸 1・斜め 2。通過幅はどれも 2^(1/2) - 1 = 0.4142)の流出の幅 Σ max(0, ue_k / |V|) wl_k
        wsum = sum(WL * max(0.0, (ex * uu + ey * ww) / vv) for ex, ey in ((1.0, 0.0), (R2, -R2), (R2, R2)))
        for k in range(nc):
            r[k] += qb_class(hm[j - 1][NX - 1], vv, d[k], f[k], dm, True) * wsum
    rates.append((t, r))
rates.sort()
form = [0.0] * nc
for (t0, r0), (t1, r1) in zip(rates, rates[1:]):
    for k in range(nc):
        form[k] += 0.5 * (r0[k] + r1[k]) * (t1 - t0)
ratios = [led[k + 1][3] / form[k] for k in range(nc)]
rep("(3) hide2 粒径階ごとの流出 = 芦田・道上 式 (31)・(32)", all(abs(x - 1.0) < TOL_FORM for x in ratios),
    "台帳/式 = %s(%s m3)" % (" ".join("%.4f" % x for x in ratios), " ".join("%.4e" % led[k + 1][3] for k in range(nc))))

# (4) bcfeed
h, z, sd = load_state("bcfeed")
nc, d, la, fa, fs = load_bedmix("bcfeed")
f0 = [0.3, 0.4, 0.3]
dzin = max(abs(z[idx(1, j)] - z_of("std", 1, j)) for j in range(J1, J2 + 1))
dfin = max(abs(fa[k][idx(1, j)] - f0[k]) for k in range(nc) for j in range(J1, J2 + 1))
moved = max(abs(z[idx(i, j)] - z_of("std", i, j)) for j in range(J1, J2 + 1) for i in range(2, NX + 1))
rep("(4) bcfeed 流入セルの河床と組成が固定", dzin < TOL_COMP and dfin < TOL_COMP and moved > 1.0e-4,
    "max|dz| = %.2e m、max|dF| = %.2e(下流の河床の変化 %.4f m)" % (dzin, dfin, moved))

# (5) bank
led = ledger("bank")
nc, d, la, fa, fs = load_bedmix("bank")
h, z, sd = load_state("bank")
res = max(abs(led[k][4]) for k in led)
rep("(5a) bank 粒径階ごとの収支", res < TOL_RES, "max|残差| = %.2e m3(在庫 %.1f m3)" % (res, sum(led[k][1] for k in led)))
frac = [0.2, 0.5, 0.3]
fe = max(abs(led[k + 1][2] - 1.0e-3 * frac[k] * 300.0) / (1.0e-3 * frac[k] * 300.0) for k in range(nc))
rep("(5b) bank 給砂 = 合計 × 組成 × 時間", fe < TOL_FEED, "最大の相対誤差 %.2e" % fe)
bad = 0.0
for arr in (fa, fs):
    for n in range(NX * NY):
        s = sum(arr[k][n] for k in range(nc))
        bad = max(bad, abs(s - 1.0), max(-arr[k][n] for k in range(nc)))
rep("(5c) bank 組成が 0〜1 で和が 1(交換層・下層)", bad < TOL_COMP, "max(|ΣF - 1|, -min F) = %.2e" % bad)
bmove = max(abs(z[idx(i, j)] - z_of("bank", i, j)) for j in (J1 - 1, J2 + 1) for i in range(1, NX + 1))
rep("(5d) bank 河岸が動いている", bmove > 1.0e-3, "河岸の行の max|dz| = %.4f m" % bmove)

# (6) qbmix
led = ledger("qbmix")
nc = 3


def series_integral(k, t_end):
    pts = [(row[0] * 60.0, row[k + 1]) for row in QBMIX]
    s = 0.0
    for (t0, q0), (t1, q1) in zip(pts, pts[1:]):
        if t0 >= t_end:
            break
        tb = min(t1, t_end)
        qb = q0 + (q1 - q0) * (tb - t0) / (t1 - t0)
        s += 0.5 * (q0 + qb) * (tb - t0)
    return s


errs = []
for k in range(nc):
    ex = series_integral(k, 300.0)
    errs.append(abs(led[k + 1][2] - ex) / ex)
res = max(abs(led[k][4]) for k in led)
rep("(6) qbmix 給砂 = 時系列の積分、収支", max(errs) < TOL_SERIES and res < TOL_RES,
    "相対誤差 %s、max|残差| = %.2e m3" % (" ".join("%.1e" % e for e in errs), res))

print("== bedmix 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
