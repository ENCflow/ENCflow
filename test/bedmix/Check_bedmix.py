#!/usr/bin/env python3
# bedmix 検定(混合粒径 f_bedmix。developer.md §84.19、docs/mixed_sediment_plan.md §6)
#   save_*/state.dat(h, z, rsh, hg, sd, hs の順。RLE)、save_*/geomorph_bedmix.dat(粒径階の数・粒径・L_a の
#   見出しと、交換層の組成 N 面・下層の組成 N 面。RLE)、result_*/ の出力、screen_*.log の台帳を読む。
#     (1) equal(3 つの粒径階がすべて 3 mm、交換層厚 > 土層厚)と single(単一粒径 3 mm)の河床が一致し、
#         組成が変わらない(等移動度の極限)。開境界の正味の流出の合計も一致する。芦田・道上の有効掃流力
#         (f_taupart = 2。developer.md §121)を足した equal_te と single_te も同じく一致し、開境界の流出が
#         有効掃流力なしより小さい(粒径階の d_m で求めた係数 (u*e/u*)^3 が単一粒径の係数と同じに効く)。
#         急勾配礫床の抵抗分割(f_taupart = 1)で D84 を交換層の組成から求める equal_tp と、D84 = 3 mm を与える
#         single_tp も一致し、開境界の流出が抵抗分割なしより小さい(段 2。§122)。0.5・2・8 mm の混合では、
#         組成からの D84(tpmix)が初期の組成の D84 を固定で与えた tpfix に 1 ステップ目で一致し、組成が変わる
#         100 s 後には違う(粗粒化で D84 が大きくなり流出が小さい)
#     (2) armor(1 mm と 20 mm、遮蔽なし、給砂なし、粗粒は限界以下): 上流端の列の低下量が静的アーマーの
#         理論値 L_a F0 / (1 − f_sub) に一致し、細粒の割合が単調に減って 0 に近づく。細粒の割合の減衰率が、
#         出力の水理量から求めた 1 セルの式 dF/dt = −(1 − f_sub) Q F / L_a の率に一致する
#     (3) hide2(0.5・2・8 mm、修正 Egiazaroff): 100〜160 s に下流端の開境界を出た粒径階ごとの量(台帳)が、
#         下流端のセルの水深・流速・組成から芦田・道上(1972)式 (31)・(32) で求めた値に一致する
#     (4) bcfeed(容量給砂): 流入セルの河床と組成が変わらない
#     (4b) bclim(容量給砂 + 流入セルで粒径階ごとの供給量制限が働く。§123.7): 給砂は制限の後の正味流出で作るので、
#         流入セルの河床と組成が変わらない
#     (5) bank(動く河岸・側岸侵食・安息角崩落・合計の給砂 + 一定の組成): 粒径階ごとの収支が閉じ、給砂が
#         合計 × 組成 × 時間に一致し、組成が 0〜1 で和が 1、河岸が動いている
#     (6) qbmix(粒径階ごとの給砂の時系列): 台帳の給砂が時系列の積分に一致し、収支が閉じる
#     (7) equal_su(3 粒径階がすべて 0.5 mm、組成 1・0・0、浮遊砂 = 粒径階 1)と single_su(単一粒径 0.5 mm の
#         掃流砂と浮遊砂)の河床・浮遊砂が一致し、組成が変わらない(浮遊砂の結合の単一粒径の極限。段 2。§122)
#     (8) susp(0.3・2・8 mm、粒径階 1 が浮遊砂、開境界): 粒径階 1 の河床の台帳(浮遊砂へ出た分を含む)と
#         浮遊砂の台帳(在庫・交換・系外との出入り)が閉じ、交換を河床の側と浮遊砂の側で数えた値が一致する。
#         プローブの最後の列が交換層の平均粒径 Dm(mm)で、最初と最後の記録が組成から求めた値に一致する。
#         水路の中央の行をサブグリッド河道幅 0.6 m にした suw でも(河道平面積率の重み)台帳が閉じ、交換の両側が一致する
#         掃流砂の容量給砂と浮遊砂の平衡濃度給砂を与えた sueq では、平衡濃度に流入セルの交換層の粒径階 1 の割合を
#         掛けるので(§123.7)、流入セルの粒径階 1 の割合と河床がほとんど変わらない
#     (9) 崩落と崖錐(台地。段 2b。§123): 土層だけが崩れる形(rfs)・基岩の崩落(rfb)・海セルへの崩落(rfsea)で、
#         混合粒径の z・sd・崖錐 ht が単一粒径と一致(崩落は粒径を選ばない)、粒径階ごとの収支が基岩からの生成と
#         海セルへの流出を含めて閉じ、基岩からの生成が基岩の低下 × rf_frac に一致し、崖錐に深い所(下層)の組成が出る
#     (10) 深さ依存クリープ(cr)と (11) 波浪による沿岸漂砂(ls): 混合粒径の z・sd が単一粒径と一致し、収支が閉じる
#   組成の指定のない給砂(nofrac)・浮遊砂の粒径の食い違い(su_d50)・斜面浸食との併用(su_wash)・崩落の河岸モード
#   との併用(rfstop_bank)・基岩の崩落で岩屑の組成がない(rfstop_frac)が止まること、
#   リスタート往復(rt1 → rt2 と bank、surt1 → surt2 と susp)・MPI の一致は Run.sh / Run_MPI.sh が見る
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


def susp_ledger(tag):
    """screen_<tag>.log の浮遊砂との結合の台帳: (河床の側の交換, 浮遊砂の在庫の初期, 最終, 浮遊砂の側の交換,
    流入, 流出, 浮遊砂の残差)"""
    txt = open("screen_%s.log" % tag, encoding="utf-8", errors="replace").read()
    ex = float(re.search(r"ledger class 1 to suspended load \(pickup - deposition\)\s+(\S+)", txt).group(1))
    m = re.search(r"suspended load \(class 1\) ledger: stock initial\s+(\S+) final\s+(\S+) pickup - deposition\s+(\S+) "
                  r"in\s+(\S+) out\s+(\S+)", txt)
    r = float(re.search(r"suspended load \(class 1\) ledger residual\s+(\S+)", txt).group(1))
    return (ex,) + tuple(float(m.group(k)) for k in range(1, 6)) + (r,)


def load_grid(tag, ntot):
    """save_<tag>/state.dat の z・sd(格子の大きさを指定)"""
    with open("save_%s/state.dat" % tag, "rb") as f:
        arrs = [read_rle_array(f, ntot) for _ in range(5)]
    return arrs[1], arrs[4]


def load_ht(tag, ntot):
    """save_<tag>/geomorph_rockfall.dat の崖錐の厚さ ht"""
    with open("save_%s/geomorph_rockfall.dat" % tag, "rb") as f:
        return read_rle_array(f, ntot)


def load_bedmix_n(tag, ntot):
    with open("save_%s/geomorph_bedmix.dat" % tag, "rb") as f:
        nc = struct.unpack("<i", read_rec(f))[0]
        read_rec(f)
        fa = [read_rle_array(f, ntot) for _ in range(nc)]
        fs = [read_rle_array(f, ntot) for _ in range(nc)]
    return nc, fa, fs


def rf_ledger(tag):
    """screen_<tag>.log の崩落の台帳: {class: (基岩から, 海セルへ)}"""
    txt = open("screen_%s.log" % tag, encoding="utf-8", errors="replace").read()
    return {int(m.group(1)): (float(m.group(2)), float(m.group(3))) for m in
            re.finditer(r"ledger class (\d+) rockfall: from bedrock\s+(\S+) to sea cells\s+(\S+)", txt)}


def read_txt(path):
    return [float(v) for line in open(path) for v in line.split()]


def maxdiff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def comp_dev(fa, nc, ntot):
    return max(max(abs(sum(fa[k][n] for k in range(nc)) - 1.0), -min(fa[k][n] for k in range(nc)))
               for n in range(ntot) if sum(fa[k][n] for k in range(nc)) > 0.0)


def read_hs(tag):
    ntot = NX * NY
    with open("save_%s/state.dat" % tag, "rb") as f:
        arrs = [read_rle_array(f, ntot) for _ in range(6)]
    return arrs[5]


def dpct(d, f, pct):
    """粒径階の累積の割合を粒径の対数で補間した百分位の粒径(src の bmix_dpct と同じ式)"""
    cum = 0.0
    for k in range(len(d)):
        cprev, cum = cum, cum + f[k]
        if cum >= pct:
            if k == 0 or cum <= cprev:
                return d[k]
            w = (pct - cprev) / (cum - cprev)
            return math.exp(math.log(d[k - 1]) + w * (math.log(d[k]) - math.log(d[k - 1])))
    return d[-1]


def read_probe(path):
    """プローブの CSV: (列の見出しの並び, [[値, ...], ...])"""
    hdr, rows = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("# t(hour)"):
                hdr = [c.strip() for c in line[1:].split(",")]
            elif line.strip() and not line.startswith("#"):
                rows.append([float(v) for v in line.split(",")])
    return hdr, rows


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
# (1f)(1g) 抵抗分割(f_taupart = 1)の D84 を組成から求める equal_tp と、D84 を与える single_tp(段 2。§122)。
#   3 mm・水深約 0.1 m では φ ≈ 0.985 で流出は 0.2 % ほどしか減らないので、効いていることは 0.1 % 以上の減少で見る
_, z_sp, _ = load_state("single_tp")
_, z_ep, _ = load_state("equal_tp")
dzp = max(abs(a - b) for a, b in zip(z_sp, z_ep))
movedp = max(abs(a - b) for a, b in zip(z_sp, z0))
rep("(1f) equal_tp = single_tp の河床", dzp < TOL_EQ and movedp > 1.0e-4,
    "max|z_equal_tp - z_single_tp| = %.2e m(河床の変化 %.4f m)" % (dzp, movedp))
ledp = ledger("equal_tp")
out_ep = sum(ledp[k][3] for k in ledp)
txt = open("screen_single_tp.log", encoding="utf-8", errors="replace").read()
out_sp = float(re.search(r"net bed load out through open boundaries \(out - in\)\s+(\S+)", txt).group(1))
rep("(1g) 抵抗分割の開境界の流出(equal_tp = single_tp、抵抗分割なしより小さい)",
    abs(out_ep - out_sp) <= 1.0e-8 * abs(out_sp) and 0.0 < out_sp < (1.0 - 1.0e-3) * out_s,
    "equal_tp %.9e、single_tp %.9e m3(抵抗分割なしの %.3f 倍)" % (out_ep, out_sp, out_sp / out_s))
# (1h)(1i) 0.5・2・8 mm(0.3・0.4・0.3)の混合で、D84 を組成から求める tpmix と、初期の組成の D84 を固定で与える
#   tpfix(段 2。§122)。1 ステップ目は組成が初期のままなので一致し、100 s 後は上流の粗粒化で違う
d84_0 = dpct([0.0005, 0.002, 0.008], [0.3, 0.4, 0.3], 0.84)
d84_in = float(re.search(r"^\s*fluv_d84\s*=\s*(\S+)", open("param_tpfix1.txt", encoding="utf-8").read(), re.M).group(1))
z0f = [z_of("free", i, j) for j in range(1, NY + 1) for i in range(1, NX + 1)]
_, z_m1, _ = load_state("tpmix1")
_, z_f1, _ = load_state("tpfix1")
dz1 = max(abs(a - b) for a, b in zip(z_m1, z_f1))
mv1 = max(abs(a - b) for a, b in zip(z_m1, z0f))
rep("(1h) 混合の組成からの D84 = 初期の組成の D84(1 ステップ)",
    dz1 < TOL_EQ and mv1 > 1.0e-7 and abs(d84_in - d84_0) <= 1.0e-15,
    "max|z_tpmix1 - z_tpfix1| = %.2e m(河床の変化 %.2e m)、D84 = %.10f mm(式)/ %.10f mm(fluv_d84)"
    % (dz1, mv1, 1000.0 * d84_0, 1000.0 * d84_in))
_, z_m, _ = load_state("tpmix")
_, z_f, _ = load_state("tpfix")
dzm = max(abs(a - b) for a, b in zip(z_m, z_f))
mvm = max(abs(a - b) for a, b in zip(z_m, z0f))
ledm, ledf = ledger("tpmix"), ledger("tpfix")
out_m, out_f = sum(ledm[k][3] for k in ledm), sum(ledf[k][3] for k in ledf)
rep("(1i) 組成が変わると D84 が変わる(100 s。粗粒化で流出が小さい)", dzm > 1.0e-6 and out_m < out_f,
    "max|z_tpmix - z_tpfix| = %.2e m(河床の変化 %.3f m)、流出 tpmix %.6e、tpfix %.6e m3" % (dzm, mvm, out_m, out_f))

# (7) 浮遊砂の結合の単一粒径の極限(段 2。§122)
_, z_s7, _ = load_state("single_su")
_, z_e7, _ = load_state("equal_su")
dz7 = max(abs(a - b) for a, b in zip(z_s7, z_e7))
moved7 = max(abs(a - b) for a, b in zip(z_s7, z0))
rep("(7a) equal_su = single_su の河床", dz7 < TOL_EQ and moved7 > 1.0e-3,
    "max|z_equal_su - z_single_su| = %.2e m(河床の変化 %.3f m)" % (dz7, moved7))
hs_s7, hs_e7 = read_hs("single_su"), read_hs("equal_su")
dhs7 = max(abs(a - b) for a, b in zip(hs_s7, hs_e7))
rep("(7b) equal_su = single_su の浮遊砂", dhs7 < TOL_EQ and max(hs_s7) > 1.0e-5,
    "max|hs_equal_su - hs_single_su| = %.2e m(最大の hs %.2e m)" % (dhs7, max(hs_s7)))
nc7, d7, la7, fa7, fs7 = load_bedmix("equal_su")
dev7 = max(max(abs(fa7[0][n] - 1.0), fa7[1][n], fa7[2][n]) for n in range(NX * NY))
rep("(7c) equal_su の組成が粒径階 1 だけのまま", dev7 < TOL_COMP, "max(|F1 - 1|, F2, F3) = %.2e" % dev7)

# (8) 浮遊砂の結合の台帳(段 2。§122)
led8 = ledger("susp")
res8 = max(abs(led8[k][4]) for k in led8)
ex8, s0, s1, es8, vin8, vout8, rs8 = susp_ledger("susp")
rep("(8a) susp 粒径階ごとの河床の台帳(粒径階 1 は浮遊砂へ出た分を含む)", res8 < TOL_RES and ex8 > 1.0e-3,
    "max|残差| = %.2e m3(粒径階 1 から浮遊砂へ %.4f m3)" % (res8, ex8))
rep("(8b) susp 浮遊砂の台帳", abs(rs8) < TOL_RES and vout8 > 0.0,
    "残差 %.2e m3(在庫 %.4f → %.4f、交換 %.4f、流入 %.4f、流出 %.4f m3)" % (rs8, s0, s1, es8, vin8, vout8))
rep("(8c) susp 交換の河床の側と浮遊砂の側", abs(ex8 - es8) <= 1.0e-10 * abs(ex8),
    "河床の側 %.12e、浮遊砂の側 %.12e m3" % (ex8, es8))
nc8, d8, la8, fa8, fs8 = load_bedmix("susp")
dev8 = max(max(abs(sum(fa8[k][n] for k in range(nc8)) - 1.0), -min(fa8[k][n] for k in range(nc8))) for n in range(NX * NY))
rep("(8d) susp 組成が 0〜1 で和が 1", dev8 < TOL_COMP, "max(|ΣF - 1|, -min F) = %.2e" % dev8)
# (8e) プローブの Dm の列(最後の列。最初の記録 = 初期の組成、最後の記録 = 保存した最終の組成。f14.5 の丸め)
f08 = [0.3, 0.4, 0.3]
dm0 = 1000.0 * sum(f08[k] * d8[k] for k in range(nc8))
err8, ncol8, dch8, last8 = 0.0, set(), 0.0, set()
for npb, (ip, jp) in enumerate(((30, 5), (50, 5)), start=1):
    hdr8, rows8 = read_probe("result_susp/probes/probe%04d.csv" % npb)
    ncol8 |= {len(r) for r in rows8} | {len(hdr8)}
    dm1 = 1000.0 * sum(fa8[k][idx(ip, jp)] * d8[k] for k in range(nc8))
    err8 = max(err8, abs(rows8[0][-1] - dm0), abs(rows8[-1][-1] - dm1))
    dch8 = max(dch8, abs(dm1 - dm0))
    last8.add(hdr8[-1] if hdr8 else "")
rep("(8e) susp プローブの最後の列 Dm(mm)", ncol8 == {12} and last8 == {"Dm(mm)"} and err8 < 1.0e-5 and dch8 > 1.0e-3,
    "列の数 %s、最後の見出し %s、組成からの値との差 %.1e mm(Dm の変化 %.3f mm)" % (sorted(ncol8), sorted(last8), err8, dch8))

# (8f) サブグリッド河道幅の行を持つ suw(河道平面積率 0.6 の重みが河床と浮遊砂の両方に掛かる。段 2。§122)
led8w = ledger("suw")
res8w = max(abs(led8w[k][4]) for k in led8w)
ex8w, s0w, s1w, es8w, vin8w, vout8w, rs8w = susp_ledger("suw")
rep("(8f) suw(河道幅 0.6 m の行)の台帳と交換の両側",
    res8w < TOL_RES and abs(rs8w) < TOL_RES and abs(ex8w - es8w) <= 1.0e-10 * abs(ex8w) and led8w[1][0] < led8[1][0] - 1.0,
    "粒径階ごとの残差 max %.2e、浮遊砂の残差 %.2e m3、交換 %.10e / %.10e m3(粒径階 1 の初期の在庫 %.3f m3、susp は %.3f)"
    % (res8w, rs8w, ex8w, es8w, led8w[1][0], led8[1][0]))

# (8g) sueq: 掃流砂の容量給砂 + 浮遊砂の平衡濃度給砂(§123.7)。平衡濃度に流入セルの交換層の粒径階 1 の割合を掛けるので、
#      流入と河床が釣り合い、流入セルの粒径階 1 の割合と河床はほとんど変わらない(残るのは流れ始めに浮遊砂が満ちるまでの
#      巻き上げの分。割合を掛けない以前の実装では、160 s で割合が 0.3 → 0.8、河床が 1.3 cm 上がった)
h, z, sd = load_state("sueq")
nc, d, la, fa, fs = load_bedmix("sueq")
dzq = max(abs(z[idx(1, j)] - z_of("free", 1, j)) for j in range(J1, J2 + 1))
df1q = max(abs(fa[0][idx(1, j)] - 0.3) for j in range(J1, J2 + 1))
ledq = ledger("sueq")
resq = max(abs(ledq[k][4]) for k in ledq)
exq, s0q, s1q, esq, vinq, voutq, rsq = susp_ledger("sueq")
rep("(8g) sueq 平衡濃度給砂で流入セルの粒径階 1 の割合と河床がほぼ固定", df1q < 0.02 and dzq < 1.0e-3 and vinq > 0.1
    and resq < TOL_RES and abs(rsq) < TOL_RES,
    "流入セルの max|dF1| = %.4f、max|dz| = %.2e m(浮遊砂の流入 %.4f m3、粒径階ごとの残差 max %.1e、浮遊砂の残差 %.1e m3)"
    % (df1q, dzq, vinq, resq, rsq))

# (9) 崩落と崖錐(台地 41 × 41。段 2b。§123)
NM = 41 * 41
zm0 = read_txt("zinit_mesa.txt")
for lab, a, b in (("(9a) 土層だけが崩れる形", "rfs1", "rfs3"), ("(9c) 基岩の崩落", "rfb1", "rfb3"),
                  ("(9e) 海セルへの崩落", "rfsea1", "rfsea3")):
    za, sa = load_grid(a, NM)
    zb, sb = load_grid(b, NM)
    dzr, dsr, dhr = maxdiff(za, zb), maxdiff(sa, sb), maxdiff(load_ht(a, NM), load_ht(b, NM))
    mvr = maxdiff(za, read_txt("zinit_mesa_sea.txt") if a == "rfsea1" else zm0)
    rep(lab + ": 混合粒径の z・sd・崖錐 = 単一粒径", max(dzr, dsr, dhr) < TOL_EQ and mvr > 1.0,
        "max|dz| %.1e、|dsd| %.1e、|dht| %.1e m(地形の変化 %.2f m)" % (dzr, dsr, dhr, mvr))
# (9b) 土層だけが崩れる形の収支と、崖錐に下層の組成が出る(交換層厚で頭打ちにしない = 柱の深い所まで運ぶ)
ld = ledger("rfs3")
res9 = max(abs(ld[k][4]) for k in ld)
z3, s3 = load_grid("rfs3", NM)
nc9, fa9, fs9 = load_bedmix_n("rfs3", NM)
tal = [n for n in range(NM) if z3[n] > zm0[n] + 0.1]
f3t = sum(fa9[2][n] for n in tal) / len(tal)
dev9 = comp_dev(fa9, nc9, NM)
rep("(9b) rfs3 の収支・組成・崖錐の組成", res9 < TOL_RES and dev9 < TOL_COMP and f3t > 0.5,
    "max|残差| %.1e m3、組成の誤差 %.1e、崖錐の粗粒(8 mm)の割合の平均 %.3f(交換層 0.3、下層 0.6)" % (res9, dev9, f3t))
# (9d) 基岩の崩落: 収支(基岩からの生成を含む)、生成 = 基岩の低下 × rf_frac(台帳は表示の 10 桁なので比は 1e-9 で見る)
ld = ledger("rfb3")
rl = rf_ledger("rfb3")
res9d = max(abs(ld[k][4]) for k in ld)
z3, s3 = load_grid("rfb3", NM)
sd0 = read_txt("sdinit_mesa_cap.txt")
rock = sum(max(0.0, (zm0[n] - sd0[n]) - (z3[n] - s3[n])) for n in range(NM)) * (1.0 - PORO)
gen = [rl[k][0] for k in sorted(rl)]
rfr = [0.05, 0.15, 0.8]
eg = max(abs(gen[k] / sum(gen) - rfr[k]) for k in range(3))
nc9, fa9, fs9 = load_bedmix_n("rfb3", NM)
rep("(9d) rfb3 の収支と基岩からの生成", res9d < TOL_RES and abs(sum(gen) / rock - 1.0) < 1.0e-9 and eg < 1.0e-9
    and comp_dev(fa9, nc9, NM) < TOL_COMP,
    "max|残差| %.1e m3、生成 %.6f / 基岩の低下 %.6f m3、組成の比の誤差 %.1e" % (res9d, sum(gen), rock, eg))
# (9f) 海セルへの崩落の収支(海セルへの流出を含む)
ld = ledger("rfsea3")
rl = rf_ledger("rfsea3")
res9f = max(abs(ld[k][4]) for k in ld)
rep("(9f) rfsea3 の収支(海セルへの流出を含む)", res9f < TOL_RES and min(rl[k][1] for k in rl) > 0.0,
    "max|残差| %.1e m3、海セルへ %s m3" % (res9f, " ".join("%.3f" % rl[k][1] for k in sorted(rl))))

# (10) 深さ依存クリープと (11) 沿岸漂砂(段 2b。§123)
for lab, a, b, nt, zf in (("(10) 深さ依存クリープ", "cr1", "cr3", NM, "zinit_mesa.txt"),
                          ("(11) 沿岸漂砂", "ls1", "ls3", 80 * 40, "zinit_shore.txt")):
    za, sa = load_grid(a, nt)
    zb, sb = load_grid(b, nt)
    ld = ledger(b)
    resx = max(abs(ld[k][4]) for k in ld)
    ncx, fax, fsx = load_bedmix_n(b, nt)
    mvx = maxdiff(za, read_txt(zf))
    lim = "class supply limiter" in open("screen_%s.log" % b, encoding="utf-8", errors="replace").read()
    rep(lab + ": 混合粒径の z・sd = 単一粒径、収支", max(maxdiff(za, zb), maxdiff(sa, sb)) < TOL_EQ and mvx > 0.1
        and resx < TOL_RES and comp_dev(fax, ncx, nt) < TOL_COMP and not lim,
        "max|dz| %.1e、|dsd| %.1e m(地形の変化 %.3f m)、max|残差| %.1e m3" % (maxdiff(za, zb), maxdiff(sa, sb), mvx, resx))

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

# (4b) bclim: 流入セルで粒径階ごとの供給量制限が働く容量給砂(§123.7)。制限の前の流出で給砂を作ると、制限が削った
#      分が流入セルに溜まる(以前の実装で 0.12 m)。制限の後の正味流出で作れば河床と組成は丸め誤差の範囲で固定
h, z, sd = load_state("bclim")
nc, d, la, fa, fs = load_bedmix("bclim")
dzin = max(abs(z[idx(1, j)] - z_of("std", 1, j)) for j in range(J1, J2 + 1))
dfin = max(abs(fa[k][idx(1, j)] - f0[k]) for k in range(nc) for j in range(J1, J2 + 1))
moved = max(abs(z[idx(i, j)] - z_of("std", i, j)) for j in range(J1, J2 + 1) for i in range(2, NX + 1))
ledl = ledger("bclim")
resl = max(abs(ledl[k][4]) for k in ledl)
liml = "class supply limiter" in open("screen_bclim.log", encoding="utf-8", errors="replace").read()
rep("(4b) bclim 流入セルで制限が働いても河床と組成が固定", dzin < TOL_COMP and dfin < TOL_COMP and moved > 1.0e-3
    and liml and resl < TOL_RES and abs(la - 0.002) < 1.0e-12,
    "max|dz| = %.2e m、max|dF| = %.2e(下流の河床の変化 %.4f m、制限の発動 %s、max|残差| %.1e m3)"
    % (dzin, dfin, moved, "あり" if liml else "なし", resl))

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
