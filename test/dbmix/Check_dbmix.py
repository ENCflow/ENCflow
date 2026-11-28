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
#   (11) 濡れた基盤の上を進む流れ(tkb3。高橋・中川則。土層は斜面だけで、平坦部は基盤): 粒径階ごとの収支が閉じ、
#       保存から数えた総量が初期の総量に一致し、平坦部の基盤に土砂が届いて計算が終わる。雨で全域が濡れているので、
#       流れの先端は、侵食できない基盤の上を、ごく小さい土砂の柱を先に立てて進む。非正規化数を残すビルド
#       (-Og -fcheck=all)では、その柱の濃度が非正規化数になったセルで、堆積の式の C*/C がオーバーフローして
#       止まった(developer.md §142 の不具合の再発防止。最適化のビルドは非正規化数を 0 に落とすので起きない)
#   侵食を動ける粒径階に限る f_dbsel = 1・2(高橋ら 2000 の式 (21)・2001 の式 (26) と型の区分。developer.md §143):
#   (12) 動けない粒径階(sel3 = f_dbsel 1、sel3b = f_dbsel 2。粒径 1 m > 流動深): 流れに入らない(台帳も柱も 0)。
#       その粒径階の量はどのセルでも変わらない。侵食だけを受けたセルの表層の割合は F_3 = F_3(0) + F_sub,3 Δ / L_a
#       (Δ は侵食深)で増え、F_3 = 1 で侵食が止まる(Δ <= (1 − F_3(0)) L_a / F_sub,3)。堆積にその粒径階は入らない
#   (13) はじめの侵食速度(selp0・selp1・selp2。水深 2 cm から 1 ステップ): 動ける粒径階が流れに入る量は、粒径を
#       選ばない計算の量に対して f_dbsel = 1 が K3 倍(式の印字どおり。斜面のかさの侵食量は K3² 倍)、f_dbsel = 2 が
#       同じ(かさの侵食量は K3 倍)。K3 は動ける粒径階の交換層の割合の和。動けない粒径階は 0。平坦部(掃流の型)は、
#       限界掃流力を超える粒径階がなく侵食しない
#   (14) 全粒径階が動ける(sela1。粒径 <= 限界水深): 粒径を選ばない sela0 とビット一致
#   (15) 全域を掃流の型に(db_seltan = 10)、限界掃流力をほぼ 0 に(selb1): 粒径を選ばない selb0 と丸めの範囲で
#       一致(流速がほぼ 0 の流れの先端のセルだけで判定が働く)
#   (16) 全域を掃流の型に、限界掃流力を非常に大きく(selc3): 土石流の式は何も侵食しない
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


def conservation(tag, sd0, f0, fsub0, la, need_dep=False, no="(4)"):
    """粒径階ごとの保存(4)。no は表示する判定の番号"""
    st = state(tag)
    d, lar, fa, fs, hk = bedmix(tag)
    bed, flow, txt = ledgers(tag)
    nc = len(d)
    res = max(max(abs(bed[k][5]), abs(flow[k][5])) for k in range(1, nc + 1))
    side = max(abs(bed[k][4] - flow[k][2]) for k in range(1, nc + 1))
    act = sum(abs(bed[k][4]) for k in range(1, nc + 1))
    check(res < TOL_LED, "%s %s: ledger residuals (bed, flow) max %.1e m3" % (no, tag, res))
    check(side < TOL_LED, "%s %s: exchange counted on the bed side = on the flow side (max diff %.1e m3)" % (no, tag, side))
    tot = class_totals(st, la, fa, fs, hk)
    tot0 = [CSTAR * (min(la, sd0) * f0[k] + (sd0 - min(la, sd0)) * fsub0[k]) * N * DX * DX for k in range(nc)]
    dtot = max(abs(a - b) for a, b in zip(tot, tot0))
    check(dtot < TOL_LED, "%s %s: class totals from the save (bed + flow) = initial totals (max diff %.1e of %.1f m3)"
          % (no, tag, dtot, sum(tot0)))
    dsum = max(abs(sum(hk[k][i] for k in range(nc)) - st["hs"][i]) for i in range(N))
    fsum = max(abs(sum(fa[k][i] for k in range(nc)) - 1.0) for i in range(N))
    fmin = min(min(fa[k]) for k in range(nc))
    check(dsum < TOL_EQ, "%s %s: sum of the class columns = hs (max diff %.1e m)" % (no, tag, dsum))
    check(fsum < TOL_FRAC and fmin >= 0.0, "%s %s: exchange-layer fractions sum to 1 (%.1e) and are >= 0" % (no, tag, fsum))
    check(act > MIN_ACT, "%s %s: exchange with the debris flow is active (%.3f m3 net per class sum)" % (no, tag, act))
    if need_dep:
        dep = max(z - z0_of(i) for i, z in enumerate(st["z"]))
        check(dep > 1.0e-3, "%s %s: deposition occurred (max rise %.4f m)" % (no, tag, dep))
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

# ---- (11) 濡れた基盤の上を進む流れ(高橋・中川則。土層は斜面だけ)
tb = state("tkb3")
dd, la, fa, fs, hk = bedmix("tkb3")
bed, flow, txt = ledgers("tkb3")
res = max(max(abs(bed[k][5]), abs(flow[k][5])) for k in (1, 2, 3))
check(res < TOL_LED, "(11) tkb3: class ledgers close (max residual %.1e m3)" % res)
JSOIL = int(YB / DX)                                      # 土層のある行(斜面)
SD_SLOPE = 0.3
tot = class_totals(tb, la, fa, fs, hk)
tot0 = [CSTAR * (LA_W * F0[k] + (SD_SLOPE - LA_W) * FS0[k]) * NX * JSOIL * DX * DX for k in range(3)]
dtot = max(abs(a - b) for a, b in zip(tot, tot0))
check(dtot < TOL_LED, "(11) tkb3: class totals from the save (bed + flow) = initial totals (max diff %.1e of %.1f m3)"
      % (dtot, sum(tot0)))
ndep = sum(1 for i in range(N) if i // NX + 1 > JSOIL and tb["sd"][i] > 1.0e-9)
check(ndep > 0 and "program terminated normally" in txt, "(11) tkb3: the flow crossed the wet bedrock of the flat "
      "part and the run completed (%d bedrock cells with deposit)" % ndep)

# ---- (12) 侵食を動ける粒径階に限る(f_dbsel = 1・2): 流動深より大きい粒径階は河床に残り、表層を覆って侵食を止める
SD_E = 0.3                                                # 雛形 e の土層厚 (m)
C30 = LA_W * F0[2] + (SD_E - LA_W) * FS0[2]               # セルごとの粒径階 3 のかさの厚さ(はじめ)
DMAX = (1.0 - F0[2]) * LA_W / FS0[2]                      # 侵食深の上限 (m)


def armour(tag, f3th):
    """動けない粒径階 3(1 m)の検定。f3th は「表層を覆った」とみなす割合(侵食速度がかさで K3² に比例する
    f_dbsel = 1 は 1 への近づき方が遅いので 0.9、K3 に比例する f_dbsel = 2 は 0.99)"""
    bed, flow, txt = conservation(tag, SD_E, F0, FS0, LA_W, need_dep=True, no="(12)")
    st = state(tag)
    dd, la, fa, fs, hk = bedmix(tag)
    check(bed[3][4] == 0.0 and flow[3][1] == 0.0 and max(abs(v) for v in hk[2]) == 0.0,
          "(12) %s: the class larger than the flow depth (%.1f m) never enters the flow (ledger %.1e m3, columns "
          "%.1e m)" % (tag, dd[2], bed[3][4], max(abs(v) for v in hk[2])))
    check(bed[1][4] > MIN_ACT and bed[2][4] > MIN_ACT, "(12) %s: the classes smaller than the flow depth are eroded "
          "(%.3f and %.3f m3)" % (tag, bed[1][4], bed[2][4]))
    dc3 = 0.0
    for i in range(N):
        sd = max(st["sd"][i], 0.0)
        le = min(la, sd)
        dc3 = max(dc3, abs(le * fa[2][i] + (sd - le) * fs[2][i] - C30))
    check(dc3 < TOL_EQ, "(12) %s: the content of the immobile class is unchanged in every cell (max diff %.1e m)"
          % (tag, dc3))
    # 侵食だけを受けたセル(下層の組成がはじめのまま)では、交換層は下がった分だけ下層を取り込み、動けない粒径階は
    # 出ていかない: F_3 = F_3(0) + F_sub,3 Δ / L_a(Δ は侵食深)。F_3 = 1 で侵食が止まる: Δ <= (1 − F_3(0)) L_a / F_sub,3
    dev = emax = 0.0
    nero = narm = 0
    for i in range(N):
        ero = SD_E - st["sd"][i]
        if ero > 1.0e-9 and all(abs(fs[k][i] - FS0[k]) < 1.0e-15 for k in range(3)):
            nero += 1
            emax = max(emax, ero)
            dev = max(dev, abs(fa[2][i] - (F0[2] + FS0[2] * ero / LA_W)))
            if fa[2][i] > f3th:
                narm += 1
    check(nero > 400 and dev < TOL_FRAC, "(12) %s: the surface fraction of the immobile class follows "
          "F3 = F3(0) + Fsub3 * erosion / La (max diff %.1e over %d eroded cells)" % (tag, dev, nero))
    check(emax <= DMAX * (1.0 + 1.0e-9) and narm > 400, "(12) %s: the erosion stops as the immobile class covers "
          "the surface (max erosion %.6f m <= (1 - F3(0)) La / Fsub3 = %.6f m; F3 > %.2f in %d cells)"
          % (tag, emax, DMAX, f3th, narm))
    ithick = max(range(N), key=lambda i: st["sd"][i])
    rise = st["sd"][ithick] - SD_E
    check(rise > 10.0 * LA_W and fa[2][ithick] < 1.0e-3, "(12) %s: the deposit carries no immobile class "
          "(thickest deposit %.3f m, F3 of its surface %.1e)" % (tag, rise, fa[2][ithick]))
    m = re.search(r"debris-law erosion was reduced to the movable classes in (\d+) cell-updates", txt)
    check(m is not None and int(m.group(1)) > 0, "(12) %s: the run reports the reduced erosion (%s cell-updates)"
          % (tag, m.group(1) if m else "none"))


armour("sel3", 0.9)
armour("sel3b", 0.99)

# ---- (13) はじめの侵食速度(1 ステップ): 動けない粒径階は 0。動ける粒径階 k が流れに入る量は、粒径を選ばない式の
#      量 i F_k に対して、f_dbsel = 1 が K3 倍(粒径階ごとの侵食速度 i K3 F_k。式の印字どおり。かさでは K3² 倍)、
#      f_dbsel = 2 が同じ(i F_k。かさでは K3 倍)。K3 は動ける粒径階の交換層の割合の和
p0 = state("selp0")
d0, la0, fa0, fs0, hk0 = bedmix("selp0")
KMOV = F0[0] + F0[1]                                      # 動ける粒径階(1・2)の交換層の割合の和 K3
JSTEEP = int(YB / DX)                                     # 勾配 0.4 の斜面の行(流動面の勾配 > db_seltan = 0.03)
e0 = [SD_E - v for v in p0["sd"]]
steep = [i for i in range(N) if i // NX + 1 <= JSTEEP]
flat = [i for i in range(N) if i // NX + 1 > JSTEEP]
e0min = min(e0[i] for i in steep if 2 <= i // NX + 1 <= JSTEEP - 2)
f0max = max(e0[i] for i in flat)
check(e0min > 1.0e-5 and max(hk0[2]) > 1.0e-6 and f0max > 0.0, "(13) selp0: the size-blind law erodes every class "
      "in one step (erosion on the slope >= %.2e m, class 3 in the flow up to %.2e m, on the flat part up to %.1e m)"
      % (e0min, max(hk0[2]), f0max))
for tag, kbulk, kcls, form in (("selp1", KMOV * KMOV, KMOV, "K3^2 (class rate i K3 F_k)"),
                               ("selp2", KMOV, 1.0, "K3 (class rate i F_k)")):
    p1 = state(tag)
    d1, la1, fa1, fs1, hk1 = bedmix(tag)
    e1 = [SD_E - v for v in p1["sd"]]
    dpr = max(abs(e1[i] - kbulk * e0[i]) for i in steep)
    check(dpr < TOL_EQ, "(13) %s: the bulk erosion of one step = %s x that of the size-blind law on the slope "
          "(max diff %.1e m)" % (tag, form.split(" (")[0], dpr))
    dh12 = max(max(abs(hk1[k][i] - kcls * hk0[k][i]) for i in steep) for k in (0, 1))
    check(dh12 < TOL_EQ and max(abs(v) for v in hk1[2]) == 0.0,
          "(13) %s: the movable classes enter the flow at %.2f x the size-blind amount i F_k (max diff %.1e m), "
          "the immobile class not at all" % (tag, kcls, dh12))
    df3 = max(abs(fa1[2][i] - (LA_W * F0[2] + e1[i] * FS0[2]) / LA_W) for i in range(N))
    df1 = max(abs(fa1[0][i] - (LA_W * F0[0] - e1[i] * F0[0] / KMOV + e1[i] * FS0[0]) / LA_W) for i in range(N))
    check(df3 < TOL_FRAC and df1 < TOL_FRAC, "(13) %s: the exchange layer after the step = the movable classes "
          "removed, the substrate taken in (F3 %.1e, F1 %.1e)" % (tag, df3, df1))
    # 平坦部(流動面の勾配 <= db_seltan)は掃流の型: 粒径を選ばない式はわずかに侵食するが、限界掃流力を超える
    # 粒径階がないので侵食しない
    f1max = max(abs(e1[i]) for i in flat)
    check(f1max == 0.0, "(13) %s: on the flat part (bed-load type) no class exceeds the critical shear stress and "
          "nothing is eroded (0 vs up to %.1e m in selp0)" % (tag, f0max))


def same_run(a, b):
    """2 つの構成の保存(流れ・河床・組成・粒径階ごとの柱)がすべて同じ値か"""
    return state(a) == state(b) and bedmix(a) == bedmix(b)


def run_diff(a, b):
    """2 つの構成の保存の差の最大: (流れと河床の h・z・sd・hs と粒径階ごとの柱 (m), 交換層と下層の組成)"""
    sa, sb = state(a), state(b)
    da, la_a, faa, fsa, hka = bedmix(a)
    db, la_b, fab, fsb, hkb = bedmix(b)
    dst = max(maxdiff(sa, sb), max(max(abs(x - y) for x, y in zip(p, q)) for p, q in zip(hka, hkb)))
    dfr = max(max(max(abs(x - y) for x, y in zip(p, q)) for p, q in zip(u, v)) for u, v in ((faa, fab), (fsa, fsb)))
    return dst, dfr


def reduced_count(tag):
    t = open("screen_%s.log" % tag, encoding="utf-8", errors="replace").read()
    mm = re.search(r"debris-law erosion was reduced to the movable classes in (\d+) cell-updates", t)
    return int(mm.group(1)) if mm else -1


# ---- (14) 全粒径階が動ける(粒径 <= 限界水深 <= 流動深): 粒径を選ばない計算とビット一致
bed, flow, txt = ledgers("sela1")
act = sum(bed[k][4] for k in (1, 2, 3))
check(same_run("sela0", "sela1") and reduced_count("sela1") == 0 and act > MIN_ACT,
      "(14) sela1 (all classes not larger than the flow depth) = sela0 without the selection, bit for bit "
      "(%d reduced cell-updates; %.3f m3 eroded)" % (reduced_count("sela1"), act))

# ---- (15) 全域を掃流の型に(db_seltan = 10)、限界掃流力をほぼ 0 に(1e-30): 全粒径階が動けて、粒径を選ばない
#      計算と丸めの範囲で一致。ビット一致にはならない: 動き始めの流れの先端には流速が 1e-15 m/s より小さいセルが
#      あり(流速の裾)、そこでは無次元掃流力(流速の 2 乗に比例)が 1e-30 も下回って「動けない」になる。粒径を
#      選ばない式はそのセルでも流速に比例するごく小さい量(1e-18 m 以下)を侵食するので、その分だけ違う。判定が
#      働く数は、侵食するセル × 更新の数(何も動けない selc3 の数で代表させる)の 1 % 未満
bed, flow, txt = ledgers("selb1")
act = sum(bed[k][4] for k in (1, 2, 3))
dst, dfr = run_diff("selb0", "selb1")
nb, nc_all = reduced_count("selb1"), reduced_count("selc3")
check(dst < TOL_EQ and dfr < TOL_FRAC and 0 <= nb < 0.01 * nc_all and act > MIN_ACT,
      "(15) selb1 (bed-load type everywhere, critical shear stress ~ 0) = selb0 without the selection within "
      "round-off (max diff %.1e m, fractions %.1e; %d reduced cell-updates at the front of the flow, %.2f %% of "
      "those of selc3; %.3f m3 eroded)" % (dst, dfr, nb, 100.0 * nb / max(nc_all, 1), act))

# ---- (16) 全域を掃流の型に、限界掃流力を非常に大きく: どの粒径階も動けず、土石流の式は何も侵食しない
sc = state("selc3")
dd, la, fa, fs, hk = bedmix("selc3")
bed, flow, txt = ledgers("selc3")
tof = max(abs(bed[k][4]) for k in (1, 2, 3))
dsd = max(abs(v - SD_E) for v in sc["sd"])
dfa = max(max(abs(fa[k][i] - F0[k]) for i in range(N)) for k in range(3))
check(tof == 0.0 and max(abs(v) for v in sc["hs"]) == 0.0 and dsd == 0.0 and dfa < TOL_FRAC and reduced_count("selc3") > 0,
      "(16) selc3 (bed-load type everywhere, no class above the critical shear stress): nothing is eroded "
      "(to flow %.1e m3, bed change %.1e m, %d reduced cell-updates)" % (tof, dsd, reduced_count("selc3")))

print("=== dbmix check %s ===" % ("PASS" if rc == 0 else "FAIL"))
sys.exit(rc)
