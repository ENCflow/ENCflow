#!/usr/bin/env python3
# berode 検定(developer.md §84.4)
#   save_kb1 / save_kb2(K_b と 2 K_b)の state.dat から z, sd を読み、
#     (1) 土砂体積保存: |Σ(z − z0)| < TOL_SUM(閉領域。河岸→脚部の移動は保存)
#     (2) 侵食される河岸は水路に接する 2 列だけ: 接する河岸セルの Δz < 0 がすべて、
#         接しない河岸セルの Δz は厳密に 0
#     (3) 侵食則の線形性: 河岸の損失体積の比 loss(2K_b)/loss(K_b) が 2 ± TOL_RATIO
#         (脚部の水深・掃流力が同じ間は後退量 ∝ K_b)
#     (4) 共動更新恒等: max|(sd − sd0) − (z − z0)| < TOL_SD
#     (5) 定着の河岸係数(§84.13): fix0(fix_ctau_bank = 0)の z は kb1 と厳密に一致
#         (河岸の a > 0 でも閾値は不変、水路の a = 0)。fix1(既定 = c_τ = 100)の
#         河岸損失は kb1 の RATIO_FIX 未満(定着した河岸は削られない)
#     (6) 崩落土塊(§84.17。slump = kb1 + f_rockfall の河岸モード rf_bank、H_c = 1.5 m、
#         berode_hcover = 0.1 m / slump0 = 遮蔽なし): 体積保存・共動更新は (1)(4) と同じ、
#         崖錐 ht(result_*/Ht9998.txt)は >= 0 で水路の行(脚部)にだけ積もる
#     (7) 遮蔽: slump の側岸侵食の台帳(Screen.log「bank erosion moved」)が slump0 の
#         RATIO_COVER 未満(崖錐 ht >= h_cover の脚部では河岸面に掃流力が届かない)
#     (8) 搬出: 終端の崖錐の総量 Σht·ΔxΔy が崩落の台帳「rockfall moved」(かさ)より小さい
#         (掃流砂が崖錐を運び去った分)かつ > 0
#   使い方: Check_berode.py(カレントの save_kb1, save_kb2, …, result_slump*, Screen.log を読む)
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, J1, J2, h_of

SD0 = 10.0
TOL_SUM, TOL_SD, TOL_RATIO, RATIO_FIX, RATIO_COVER = 1.0e-9, 1.0e-10, 0.02, 0.05, 0.1
DX = 1.0


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


z0 = [[float(v) for v in line.split()] for line in open("zinit.txt")]


def load(tag):
    with open("save_%s/state.dat" % tag, "rb") as f:
        ntot = NX * NY
        read_rle_array(f, ntot)
        z = read_rle_array(f, ntot)
        read_rle_array(f, ntot)
        read_rle_array(f, ntot)
        sd = read_rle_array(f, ntot)
    dz = [[z[(j - 1) * NX + (i - 1)] - z0[j - 1][i - 1] for i in range(1, NX + 1)] for j in range(1, NY + 1)]
    ident = max(abs((sd[(j - 1) * NX + (i - 1)] - SD0) - dz[j - 1][i - 1]) for j in range(1, NY + 1) for i in range(1, NX + 1))
    return dz, ident


ok = True
loss = {}
for tag in ("kb1", "kb2"):
    dz, ident = load(tag)
    sum_dz = sum(sum(r) for r in dz)
    adj = [dz[j - 1][i - 1] for j in (J1 - 1, J2 + 1) for i in range(1, NX + 1)]       # 水路に接する河岸
    far = [dz[j - 1][i - 1] for j in range(1, NY + 1) if h_of(1, j) <= 0.0 and j not in (J1 - 1, J2 + 1) for i in range(1, NX + 1)]
    loss[tag] = -sum(adj)
    g1 = abs(sum_dz) < TOL_SUM
    g2 = all(v < 0.0 for v in adj) and max(abs(v) for v in far) == 0.0
    g4 = ident < TOL_SD
    print("(1) %s 体積保存     : sum(z - z0) = %.3e m*cell (tol %.0e) : %s" % (tag, sum_dz, TOL_SUM, "PASS" if g1 else "FAIL"))
    print("(2) %s 河岸の選択性 : 接する河岸 %d セルすべて Δz < 0 (min %.2e), 接しない河岸 max|Δz| = %.1e : %s"
          % (tag, len(adj), max(adj), max(abs(v) for v in far), "PASS" if g2 else "FAIL"))
    print("(4) %s 共動更新     : max|(sd-sd0)-(z-z0)| = %.3e m : %s" % (tag, ident, "PASS" if g4 else "FAIL"))
    ok = ok and g1 and g2 and g4
ratio = loss["kb2"] / loss["kb1"]
g3 = abs(ratio - 2.0) < 2.0 * TOL_RATIO
print("(3) 線形性 loss(2Kb)/loss(Kb) = %.4f (2 ± %.0f%%) [loss = %.4f, %.4f m*cell] : %s"
      % (ratio, 100 * TOL_RATIO, loss["kb1"], loss["kb2"], "PASS" if g3 else "FAIL"))
ok = ok and g3

# (5) 定着の河岸係数: fix0 は kb1 と厳密一致、fix1 は河岸がほぼ削られない
dz_kb1, _ = load("kb1")
dz_f0, _ = load("fix0")
dz_f1, _ = load("fix1")
diff0 = max(abs(dz_f0[j][i] - dz_kb1[j][i]) for j in range(NY) for i in range(NX))
loss_f1 = -sum(dz_f1[j - 1][i - 1] for j in (J1 - 1, J2 + 1) for i in range(1, NX + 1))
g5 = diff0 == 0.0 and loss_f1 < RATIO_FIX * loss["kb1"]
print("(5) 定着の河岸係数: fix0 (c_tau_bank = 0) の z は kb1 と max|Δ| = %.1e (= 0), fix1 (既定 = c_tau) の河岸損失 %.5f = kb1 の %.3f 倍 (< %.2f) : %s"
      % (diff0, loss_f1, loss_f1 / loss["kb1"], RATIO_FIX, "PASS" if g5 else "FAIL"))
ok = ok and g5

# (6)〜(8) 崩落土塊(f_rockfall の河岸モード)
import re
# 台帳は Screen.log の各実行(「reading list_sysparam in param_<tag>.txt」で区切る)の
# 最初の行から取る(MPI ではランクごとに同じ全域値を印字するので重複を 1 つにする)
vbank, vrock, cur = {}, {}, None
for line in open("Screen.log", encoding="utf-8", errors="replace"):
    m = re.search(r"reading list_sysparam in param_(\w+)\.txt", line)
    if m: cur = m.group(1); continue
    m = re.search(r"bank erosion moved\s+([0-9.Ee+-]+)\s*m3", line)
    if m and cur and cur not in vbank: vbank[cur] = float(m.group(1))
    m = re.search(r"rockfall moved\s+([0-9.Ee+-]+)\s*m3", line)
    if m and cur and cur not in vrock: vrock[cur] = float(m.group(1))
for tag in ("slump", "slump0"):
    dz, ident = load(tag)
    sum_dz = sum(sum(r) for r in dz)
    ht = [[float(v) for v in line.split()] for line in open("result_%s/Ht9998.txt" % tag)]
    htmin = min(min(r) for r in ht)
    out_rows = max(max(ht[j - 1]) for j in range(1, NY + 1) if not (J1 <= j <= J2))
    g6 = abs(sum_dz) < TOL_SUM and ident < TOL_SD and htmin >= 0.0 and out_rows == 0.0
    print("(6) %s 崩落土塊: sum(z - z0) = %.2e, 共動 %.1e, min ht = %.1e, 水路外の max ht = %.1e : %s"
          % (tag, sum_dz, ident, htmin, out_rows, "PASS" if g6 else "FAIL"))
    ok = ok and g6
    if tag == "slump":
        httot = sum(sum(r) for r in ht) * DX * DX
g7 = vbank["slump"] < RATIO_COVER * vbank["slump0"]
print("(7) 遮蔽: 側岸侵食 slump %.5f m3 = slump0 %.5f m3 の %.3f 倍 (< %.1f) : %s"
      % (vbank["slump"], vbank["slump0"], vbank["slump"] / vbank["slump0"], RATIO_COVER, "PASS" if g7 else "FAIL"))
g8 = 0.0 < httot < vrock["slump"]
print("(8) 搬出: 終端の崖錐 %.3f m3 < 崩落の台帳 %.3f m3 (bulk) : %s" % (httot, vrock["slump"], "PASS" if g8 else "FAIL"))
ok = ok and g7 and g8
print("== berode 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
