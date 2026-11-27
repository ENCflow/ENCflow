#!/usr/bin/env python3
# dbmix: 土石流(f_debris)と混合粒径(f_bedmix)の併用の検定(developer.md §139)
#   保存(save_<構成>/state.dat・geomorph_bedmix.dat。ゼロ抑制 RLE)と画面出力(screen_<構成>.log)の
#   終了時の台帳を読み、次を判定する。定数は make_init.py・param_*.txt と対で保守する。標準ライブラリだけ。
#   (1) 等粒径の極限: 全粒径階を同じ粒径・一様な組成にした e3 が、単一粒径の e1 と丸めの範囲で一致し、
#       流れと河床の組成が変わらない(柱を 1 本ずつ運んだ和 = 1 本で運んだ結果)
#   (2) 札つき・1 次風上: 交換層と下層に別の粒径階(同じ粒径)を置いた u3 が、単一粒径の u1 と丸めの範囲で
#       一致する(組成が場所で変わっても、1 次風上は線形なので和が変わらない)
#   (3) 札つき・MUSCL: 同じ m3 と e1 の差は制限関数の水準(地形の変化の TOL_MUSCL 倍以内)
#   (4) 粒径階ごとの保存(w3・tk3・s3): 河床の台帳と流れの台帳の残差、河床の側と流れの側の交換の一致、
#       保存から数えた粒径階ごとの総量(河床 + 流れ)= 初期の総量、柱の和 = hs、組成の和 = 1
#   (5) 全層の流動化(r3): 流動化した柱の組成 φ* = {L_a A + (D − L_a) B}/D が、流れと積もった河床の
#       どこでも保たれる(侵食される土層がほかにない)。単一粒径の r1 との地形の差は緩い許容(TOL_R)で
#       比べる。流れが止まる判定(降伏・低速凝集)をまたぐ構成で、丸めの差が拡大するため(単一粒径の r1
#       そのものが、最適化のビルドと境界検査つきのビルドで 2 cm 違う。厳密な一致は (1)・(2) で確かめる)
#   (6) 上半分の流動化(rp3。1 ステップ): 崩壊域のセルの柱が (1 − λ){L_a A + (D − L_a) B}、残った土層の
#       交換層と下層の組成が B(交換層は下層から作り直される)
#   (7) 境界から入る土石流(b3): 流入と流出の粒径階の比 = inflow_csfrac、流れと堆積の組成 = 同じ、
#       流入の総量 = Q · cs · T
#   (8) 組成の時系列(bt3): 粒径階ごとの流入 = Q · cs · Σ f_k(t_n) Δt(各ステップの終わりの時刻の割合)
#   (9) 交互計算(rt1 → alt2・alt3): 土石流のない構成に復元すると、流れの土砂の柱がその組成で河床に入る
#       (alt2 の河床の初期の在庫 = rt1 の河床 + 流れ。alt3 は粒径階 1 が浮遊砂として流れに残る)。保存から
#       数えた粒径階ごとの総量は、復元の前後で変わらない(閉領域なので初期の総量のまま)
#   (10) 極薄の土層(film3。1 ステップ): 倍精度の下限に近い厚さ(4.6e-308 m)の膜の半分を流動化しても、
#       交換層の組成が有効なまま(0 以上で和が 1)。最適化のビルド(-Ofast)は正規化数より小さい積を 0 に
#       するので、組成の更新の積がすべて 0 に落ちる。割合がすべて 0 になると平均粒径が 0 になり、掃流砂の
#       遮蔽係数が 0 除算になる(developer.md §139.7 の不具合の再発防止)
import re
import struct
import sys

NX, NY, DX = 20, 60, 1.0
N = NX * NY
PORO = 0.4
CSTAR = 1.0 - PORO
ST, YB = 0.4, 40.0
RI1, RI2, RJ1, RJ2 = 5, 16, 5, 16
SD_REL, D_HALF = 1.0, 0.5
TOL_EQ = 1.0e-12        # 等粒径の極限の差 (m)
TOL_FRAC = 1.0e-11      # 組成の差
TOL_LED = 1.0e-9        # 台帳の残差・総量の差 (m3)
TOL_PRINT = 1.0e-6      # 画面の台帳の在庫どうしの差 (m3。在庫は 10 桁の表示なので、100 m3 の在庫で 1e-7 まで)
TOL_MUSCL = 0.02        # MUSCL の札つきの差の、地形の変化に対する比の上限
TOL_R = 1.0e-2          # r1 と r3 の地形の差 (m。堆積の最大厚 0.7 m の 1.5 %。同じビルドの中では 3e-5〜1e-3 m)
SD_FILM = 4.6e-308      # film3 の膜の厚さ (m。崩壊深はその半分)
MIN_ACT = 1.0e-2        # 交換の活性の下限 (m3)

rc = 0


def check(ok, msg):
    global rc
    print(("PASS: " if ok else "FAIL: ") + msg)
    if not ok:
        rc = 1


def read_rec(f):
    b = f.read(4)
    if len(b) < 4:
        return None
    n = struct.unpack("<i", b)[0]
    payload = f.read(n)
    assert struct.unpack("<i", f.read(4))[0] == n, "record marker mismatch"
    return payload


def read_rle(f):
    n, nrun = struct.unpack("<2q", read_rec(f))
    assert n == N, "unexpected array size %d" % n
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(raw) // 8), raw)
    out = [0.0] * n
    i = k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def state(tag):
    """save_<tag>/state.dat: h・z・hrs・hg・sd・hs"""
    with open("save_%s/state.dat" % tag, "rb") as f:
        return {name: read_rle(f) for name in ("h", "z", "hrs", "hg", "sd", "hs")}


def bedmix(tag):
    """save_<tag>/geomorph_bedmix.dat: (粒径, 交換層厚, 交換層の組成, 下層の組成, 流れの柱 or None)"""
    with open("save_%s/geomorph_bedmix.dat" % tag, "rb") as f:
        nc = struct.unpack("<i", read_rec(f))[0]
        hdr = struct.unpack("<%dd" % (nc + 1), read_rec(f))
        fa = [read_rle(f) for _ in range(nc)]
        fs = [read_rle(f) for _ in range(nc)]
        hk = None
        tail = read_rec(f)
        if tail is not None:
            assert struct.unpack("<i", tail)[0] == nc
            hk = [read_rle(f) for _ in range(nc)]
    return hdr[:nc], hdr[nc], fa, fs, hk


def ledgers(tag):
    """screen_<tag>.log の台帳: bed[k] = (initial, final, feed, out, to_flow, residual)、
    flow[k] = (initial, final, from_bed, in, out, residual)"""
    txt = open("screen_%s.log" % tag, encoding="utf-8", errors="replace").read()
    num = r"\s+(\S+)"
    bed, flow = {}, {}
    for m in re.finditer(r"bed mixture ledger class (\d+) \(d = .*?\): stock initial" + num + " final" + num
                         + " feed" + num + " out" + num, txt):
        bed[int(m.group(1))] = [float(v) for v in m.groups()[1:]] + [0.0, None]
    for m in re.finditer(r"bed mixture ledger class (\d+) to debris flow \(.*?\)" + num, txt):
        bed[int(m.group(1))][4] = float(m.group(2))
    for m in re.finditer(r"bed mixture ledger class (\d+) residual" + num, txt):
        bed[int(m.group(1))][5] = float(m.group(2))
    for m in re.finditer(r"debris-flow solids ledger class (\d+): stock initial" + num + " final" + num
                         + " from bed" + num + " in" + num + " out" + num, txt):
        flow[int(m.group(1))] = [float(v) for v in m.groups()[1:]] + [None]
    for m in re.finditer(r"debris-flow solids ledger class (\d+) residual" + num, txt):
        flow[int(m.group(1))][5] = float(m.group(2))
    return bed, flow, txt


def z0_of(idx, sb=0.0):
    y = (idx // NX + 0.5) * DX
    return ST * (YB - y) + sb * (NY * DX - YB) if y < YB else sb * (NY * DX - y)


def in_patch(idx):
    i, j = idx % NX + 1, idx // NX + 1
    return RI1 <= i <= RI2 and RJ1 <= j <= RJ2


def maxdiff(a, b, keys=("h", "z", "sd", "hs")):
    return max(max(abs(x - y) for x, y in zip(a[k], b[k])) for k in keys)


def frac_dev(fa, fs, hk, st, target, la):
    """組成の目標からの最大のずれ(交換層は土層のあるセル、下層は土層が交換層より厚いセル、流れは hs のあるセル)"""
    dv = [0.0, 0.0, 0.0]
    for i in range(N):
        if st["sd"][i] > 1.0e-9:
            dv[0] = max(dv[0], max(abs(fa[k][i] - target[k]) for k in range(len(target))))
            if st["sd"][i] > la * (1.0 + 1.0e-9):
                dv[1] = max(dv[1], max(abs(fs[k][i] - target[k]) for k in range(len(target))))
        if hk is not None and st["hs"][i] > 1.0e-9:
            dv[2] = max(dv[2], max(abs(hk[k][i] / st["hs"][i] - target[k]) for k in range(len(target))))
    return dv


def class_totals(st, la, fa, fs, hk, hs_class=None):
    """保存から数えた粒径階ごとの総量(河床の固体 + 流れの固体。m3)。流れの固体は粒径階ごとの柱 hk、
    柱のない保存では hs を粒径階 hs_class(1 始まり。浮遊砂 = 粒径階 1)に数える"""
    tot = []
    for k in range(len(fa)):
        v = 0.0
        for i in range(N):
            sd = max(st["sd"][i], 0.0)
            le = min(la, sd)
            v += CSTAR * (le * fa[k][i] + (sd - le) * fs[k][i])
            if hk is not None:
                v += hk[k][i]
            elif hs_class == k + 1:
                v += st["hs"][i]
        tot.append(v * DX * DX)
    return tot


def conservation(tag, sd0, f0, fsub0, la, need_dep=False):
    """粒径階ごとの保存(4)"""
    st = state(tag)
    d, lar, fa, fs, hk = bedmix(tag)
    bed, flow, txt = ledgers(tag)
    nc = len(d)
    res = max(max(abs(bed[k][5]), abs(flow[k][5])) for k in range(1, nc + 1))
    side = max(abs(bed[k][4] - flow[k][2]) for k in range(1, nc + 1))
    act = sum(abs(bed[k][4]) for k in range(1, nc + 1))
    check(res < TOL_LED, "(4) %s: ledger residuals (bed, flow) max %.1e m3" % (tag, res))
    check(side < TOL_LED, "(4) %s: exchange counted on the bed side = on the flow side (max diff %.1e m3)" % (tag, side))
    tot = class_totals(st, la, fa, fs, hk)
    tot0 = [CSTAR * (min(la, sd0) * f0[k] + (sd0 - min(la, sd0)) * fsub0[k]) * N * DX * DX for k in range(nc)]
    dtot = max(abs(a - b) for a, b in zip(tot, tot0))
    check(dtot < TOL_LED, "(4) %s: class totals from the save (bed + flow) = initial totals (max diff %.1e of %.1f m3)"
          % (tag, dtot, sum(tot0)))
    dsum = max(abs(sum(hk[k][i] for k in range(nc)) - st["hs"][i]) for i in range(N))
    fsum = max(abs(sum(fa[k][i] for k in range(nc)) - 1.0) for i in range(N))
    fmin = min(min(fa[k]) for k in range(nc))
    check(dsum < TOL_EQ, "(4) %s: sum of the class columns = hs (max diff %.1e m)" % (tag, dsum))
    check(fsum < TOL_FRAC and fmin >= 0.0, "(4) %s: exchange-layer fractions sum to 1 (%.1e) and are >= 0" % (tag, fsum))
    check(act > MIN_ACT, "(4) %s: exchange with the debris flow is active (%.3f m3 net per class sum)" % (tag, act))
    if need_dep:
        dep = max(z - z0_of(i) for i, z in enumerate(st["z"]))
        check(dep > 1.0e-3, "(4) %s: deposition occurred (max rise %.4f m)" % (tag, dep))
    return bed, flow, txt


# ---- (1) 等粒径の極限
e1, e3 = state("e1"), state("e3")
d = maxdiff(e1, e3)
dz_max = max(abs(z - z0_of(i)) for i, z in enumerate(e1["z"]))
check(d < TOL_EQ, "(1) equal sizes, uniform composition: e3 = single-size e1 (max diff %.1e m; bed change %.2e m)" % (d, dz_max))
dd, la, fa, fs, hk = bedmix("e3")
dv = frac_dev(fa, fs, hk, e3, (0.3, 0.4, 0.3), la)
check(max(dv) < TOL_FRAC, "(1) e3: composition unchanged in the exchange layer, substrate and flow (%.1e, %.1e, %.1e)" % tuple(dv))
check(max(e1["hs"]) > 1.0e-4, "(1) e1: the flow carries solids (max hs %.2e m)" % max(e1["hs"]))

# ---- (2) 札つき・1 次風上
u1, u3 = state("u1"), state("u3")
d = maxdiff(u1, u3)
check(d < TOL_EQ, "(2) labelled layers, first-order upwind: u3 = single-size u1 (max diff %.1e m)" % d)
dd, la, fa, fs, hk = bedmix("u3")
mix = max(min(hk[0][i], hk[1][i]) / u3["hs"][i] for i in range(N) if u3["hs"][i] > 1.0e-6)
check(mix > 0.05, "(2) u3: the flow mixes the two labels (min share of a label up to %.2f)" % mix)
bed, flow, txt = ledgers("u3")
check(abs(bed[3][1]) + abs(flow[3][1]) < 1.0e-12, "(2) u3: the absent class stays absent (%.1e m3)"
      % (abs(bed[3][1]) + abs(flow[3][1])))

# ---- (3) 札つき・MUSCL
m3 = state("m3")
d = maxdiff(e1, m3, keys=("z",))
check(d < TOL_MUSCL * dz_max, "(3) labelled layers, MUSCL: m3 vs e1 differ at the limiter level "
      "(max |dz| %.2e m = %.2f %% of the bed change)" % (d, 100.0 * d / dz_max))
bed, flow, txt = ledgers("m3")
res = max(max(abs(bed[k][5]), abs(flow[k][5])) for k in (1, 2, 3))
check(res < TOL_LED, "(3) m3: class ledgers close with MUSCL (max residual %.1e m3)" % res)

# ---- (4) 粒径階ごとの保存
F0, FS0, LA_W = (0.2, 0.5, 0.3), (0.5, 0.3, 0.2), 0.004
conservation("w3", 0.3, F0, FS0, LA_W)
conservation("tk3", 0.3, F0, FS0, LA_W)
bed, flow, txt = conservation("s3", 0.5, F0, FS0, LA_W, need_dep=True)
m = re.search(r"fluidized cells = (\d+)", txt)
check(m is not None and int(m.group(1)) > 0, "(4) s3: slope failures fluidized cells (%s cell-updates)"
      % (m.group(1) if m else "none"))

# ---- (5) 全層の流動化
r1, r3 = state("r1"), state("r3")
A, B, LA_R = (0.6, 0.3, 0.1), (0.1, 0.3, 0.6), 0.05
phi = [(LA_R * a + (SD_REL - LA_R) * b) / SD_REL for a, b in zip(A, B)]
dd, la, fa, fs, hk = bedmix("r3")
dv = frac_dev(fa, fs, hk, r3, phi, la)
ncell = sum(1 for i in range(N) if r3["sd"][i] > 1.0e-9)
check(max(dv) < TOL_FRAC, "(5) r3: the fluidized composition (%.3f, %.3f, %.3f) is kept everywhere "
      "(exchange %.1e, substrate %.1e, flow %.1e; %d cells with deposit)" % (tuple(phi) + tuple(dv) + (ncell,)))
tot = class_totals(r3, la, fa, fs, hk)
npatch = (RI2 - RI1 + 1) * (RJ2 - RJ1 + 1)
tot0 = [CSTAR * SD_REL * p * npatch for p in phi]
dtot = max(abs(a - b) for a, b in zip(tot, tot0))
check(dtot < TOL_LED, "(5) r3: class totals = the fluidized totals (max diff %.1e of %.1f m3)" % (dtot, sum(tot0)))
d = maxdiff(r1, r3, keys=("z",))
check(d < TOL_R, "(5) r3 vs single-size r1: bed elevation within %.0e m (max diff %.1e m; deposit up to %.2f m)"
      % (TOL_R, d, max(r3["sd"][i] for i in range(N) if not in_patch(i))))

# ---- (6) 上半分の流動化(1 ステップ)
rp = state("rp3")
dd, la, fa, fs, hk = bedmix("rp3")
exp_h = [CSTAR * (LA_R * a + (D_HALF - LA_R) * b) for a, b in zip(A, B)]
dh = dfa = dfs = dsd = 0.0
out = 0.0
for i in range(N):
    if in_patch(i):
        dh = max(dh, max(abs(hk[k][i] - exp_h[k]) for k in range(3)))
        dfa = max(dfa, max(abs(fa[k][i] - B[k]) for k in range(3)))
        dfs = max(dfs, max(abs(fs[k][i] - B[k]) for k in range(3)))
        dsd = max(dsd, abs(rp["sd"][i] - (SD_REL - D_HALF)), abs(rp["z"][i] - (z0_of(i) - D_HALF)))
    else:
        out = max(out, max(abs(hk[k][i]) for k in range(3)))
check(dh < TOL_EQ, "(6) rp3: class columns of the fluidized top half = (1 - lambda){La A + (D - La) B} (max diff %.1e m)" % dh)
check(dfa < TOL_FRAC and dfs < TOL_FRAC, "(6) rp3: the remaining layer has the substrate composition "
      "(exchange %.1e, substrate %.1e)" % (dfa, dfs))
check(dsd < TOL_EQ and out == 0.0, "(6) rp3: soil depth and elevation drop by the release depth (%.1e m); nothing outside" % dsd)

# ---- (7) 境界から入る土石流(一定の組成)
Q, CS, TT, DT = 3.0, 0.3, 30.0, 0.02
CSF = (0.2, 0.3, 0.5)
b3 = state("b3")
dd, la, fa, fs, hk = bedmix("b3")
bed, flow, txt = ledgers("b3")
tin = [flow[k][0] + flow[k][3] for k in (1, 2, 3)]       # 最初の更新の前の 1 ステップの流入は初期の在庫に入る
check(abs(sum(tin) - Q * CS * TT) < TOL_LED, "(7) b3: solids in = Q cs T (%.6f vs %.6f m3)" % (sum(tin), Q * CS * TT))
dr = max(abs(tin[k] / sum(tin) - CSF[k]) for k in range(3))
tout = [flow[k][4] for k in (1, 2, 3)]
do = max(abs(tout[k] - CSF[k] * sum(tout)) for k in range(3))     # 先端のほぼ空のセルの丸めがあるので体積で比べる
check(dr < TOL_FRAC, "(7) b3: class shares of the inflow = inflow_csfrac (max diff %.1e)" % dr)
check(sum(tout) > 1.0e-3 and do < TOL_LED, "(7) b3: solids leave through the open edge with the same shares "
      "(%.4f m3, max diff %.1e m3)" % (sum(tout), do))
dv = frac_dev(fa, fs, hk, b3, CSF, la)
ndep = sum(1 for i in range(N) if b3["sd"][i] > 1.0e-9)
check(max(dv) < TOL_FRAC and ndep > 0, "(7) b3: deposit and flow keep the inflow composition "
      "(exchange %.1e, substrate %.1e, flow %.1e; %d cells with deposit)" % (tuple(dv) + (ndep,)))
res = max(max(abs(bed[k][5]), abs(flow[k][5])) for k in (1, 2, 3))
check(res < TOL_LED, "(7) b3: class ledgers close (max residual %.1e m3)" % res)

# ---- (8) 組成の時系列
T1 = 20.0                                                 # csfrac.txt: 0 s (1,0,0) → 20 s (0,0,1)、以後一定
nstep = int(round(TT / DT))
exp_in = [0.0, 0.0, 0.0]
for n in range(1, nstep + 1):
    t = n * DT
    w = min(t / T1, 1.0)
    exp_in[0] += Q * CS * DT * (1.0 - w)
    exp_in[2] += Q * CS * DT * w
bed, flow, txt = ledgers("bt3")
tin = [flow[k][0] + flow[k][3] for k in (1, 2, 3)]
dt3 = max(abs(tin[k] - exp_in[k]) for k in range(3))
check(dt3 < 1.0e-6, "(8) bt3: class inflow = Q cs sum f_k(t) dt (%.4f, %.4f, %.4f m3; max diff %.1e)"
      % (tin[0], tin[1], tin[2], dt3))
res = max(max(abs(bed[k][5]), abs(flow[k][5])) for k in (1, 2, 3))
check(res < TOL_LED, "(8) bt3: class ledgers close (max residual %.1e m3)" % res)

# ---- (9) 交互計算(土石流 → 土石流のない混合粒径の構成)
bed1, flow1, txt1 = ledgers("rt1")
fl1 = [flow1[k][1] for k in (1, 2, 3)]
check(sum(fl1) > MIN_ACT, "(9) rt1: the saved flow carries solids (%.4f m3)" % sum(fl1))
TOT0 = [CSTAR * (min(LA_W, 0.3) * F0[k] + (0.3 - min(LA_W, 0.3)) * FS0[k]) * N * DX * DX for k in range(3)]
bed2, flow2, txt2 = ledgers("alt2")
d2 = max(abs(bed2[k][0] - (bed1[k][1] + flow1[k][1])) for k in (1, 2, 3))
check(d2 < TOL_PRINT and "with their composition" in txt2, "(9) alt2: restored class columns are laid on the bed "
      "(initial bed stock = saved bed + flow; max diff %.1e m3)" % d2)
a2 = state("alt2")
dd, la, fa, fs, hk = bedmix("alt2")
dtot = max(abs(a - b) for a, b in zip(class_totals(a2, la, fa, fs, hk), TOT0))
check(max(abs(v) for v in a2["hs"]) == 0.0 and hk is None and dtot < TOL_LED,
      "(9) alt2: no solids remain in the flow; class totals of the bed = initial totals (max diff %.1e m3)" % dtot)
bed3, flow3, txt3 = ledgers("alt3")
d3 = max(abs(bed3[1][0] - bed1[1][1]), abs(bed3[2][0] - (bed1[2][1] + flow1[2][1])),
         abs(bed3[3][0] - (bed1[3][1] + flow1[3][1])))
m = re.search(r"suspended load \(class 1\) ledger: stock initial\s+(\S+)", txt3)
s0 = float(m.group(1)) if m else -1.0
check(d3 < TOL_PRINT and abs(s0 - flow1[1][1]) < TOL_PRINT, "(9) alt3 (with suspended load): classes 2 and 3 are "
      "laid on the bed, class 1 stays in the flow (bed %.1e, suspended %.1e m3)" % (d3, abs(s0 - flow1[1][1])))
a3 = state("alt3")
dd, la, fa, fs, hk = bedmix("alt3")
dtot = max(abs(a - b) for a, b in zip(class_totals(a3, la, fa, fs, hk, hs_class=1), TOT0))
check(hk is None and dtot < TOL_LED, "(9) alt3: class totals (bed + suspended class 1) = initial totals "
      "(max diff %.1e m3)" % dtot)

# ---- (10) 極薄の土層(膜)の流動化: 組成が有効なまま
fl = state("film3")
dd, la, fa, fs, hk = bedmix("film3")
dsum = max(max(abs(sum(fa[k][i] for k in range(3)) - 1.0), abs(sum(fs[k][i] for k in range(3)) - 1.0))
           for i in range(N))
fmin = min(min(min(fa[k]), min(fs[k])) for k in range(3))
nfilm = sum(1 for i in range(N) if in_patch(i) and 0.0 < fl["sd"][i] <= SD_FILM)
check(nfilm == npatch, "(10) film3: a film of %.1e m lies in the release area and its top half was released "
      "(%d cells with 0 < sd <= %.1e m)" % (SD_FILM, nfilm, SD_FILM))
check(dsum < TOL_FRAC and fmin >= 0.0, "(10) film3: the fractions stay valid in every cell "
      "(max |sum - 1| %.1e, min %.1e)" % (dsum, fmin))

print("=== dbmix check %s ===" % ("PASS" if rc == 0 else "FAIL"))
sys.exit(rc)
