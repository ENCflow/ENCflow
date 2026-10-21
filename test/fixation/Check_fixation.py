#!/usr/bin/env python3
# fixation 検定(developer.md §84.6)
#   off / on / weak の 3 構成(低水 0〜10 分で砂州が乾き、出水 11 分〜で水没)の
#   result_*(Fx・Z・H のテキスト出力)と save_*(state.dat の z、
#   geomorph_fixation.dat の a・zref。RLE 形式)を読む。検定区間は土層厚の
#   ランプを除く I_RAMP < i < I_END。
#     (1) 成長則: 低水期を通して乾いた砂州・河岸セルの a(t = 600 s) が
#         1 − exp(−600/T_fix) に一致(save_rt1 = on の前半の保存値で 1e-9、
#         テキスト出力で印字精度 1e-4)
#     (2) 常に湿潤な河道セルの a は厳密に 0(全出力)
#     (3) 効果: on(c_τ = 100)の砂州は出水で全セル Δz >= 0(定着セルからの
#         流出はゼロ)、off の砂州は NMIN セル以上が Δz < −DZ_ERO
#     (4) リセット: weak(c_τ = 0.5, dz_reset = 0.002)の砂州で a = 0 に
#         戻ったセルが 1 以上あり、終了時の全セルで zref − z <= dz_reset
#         (リセットの不変条件)
#     (5) 0 <= a <= 1(全構成・全出力)
#     (6) 無効時の痕跡なし: result_off に Fx 出力がない(配列未確保)
#     (7) 粗度(rough: c_n = 2): 出水時(1800 s)の定着砂州上の流速が on の
#         RATIO_V 倍未満、断面流量 Σ V h dy は両構成とも Q_in に ±TOL_QSEC(セル中心の
#         V・h による近似。壁際の行の通水能補正 f_opening_dynamic = 2 で +3.3 %)
#     (8) 浮遊砂(susp_off / susp_on / susp_on2: 出水時に濃度 0.002 で給砂):
#         定着ありの砂州は出水で全セル正味堆積(Δz > 0)、平均 Δz が定着なしより
#         DZ_SUSP 以上大きい(f_esform = 1 と 2 の両方)
#     (9) 冠水減衰(decay: on + T_dec = 0.1 h = 360 s。§84.12): 出水で水没した砂州の
#         a(1800) = a_on·exp(−(1800 − t_w)/T_dec)。a_on は on の保存値(水没時刻 t_w で
#         凍結した値)で t_w = −T_fix ln(1 − a_on)。保存値どうしで相対 1e-3(乾湿の
#         切り替わりの数ステップ分を許す)。乾いたままの河岸の a は on と同一
#         (減衰は湿潤セルだけ)、河道セルの a は厳密に 0
#   リスタート往復(rough と同じ設定の rt1 → rt2)と MPI の一致は Run.sh /
#   Run_MPI.sh が cmp で見る
import sys, struct, os, math, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, J1, J2, JB1, JB2, I_RAMP, I_END

T1, TFIX = 600.0, 0.1 * 3600.0
DZRESET_WEAK = 0.002
TOL_A, TOL_TXT, DZ_ERO, NMIN = 1.0e-9, 1.0e-4, 0.005, 10
RATIO_V, TOL_QSEC, DZ_SUSP, Q_IN = 0.7, 0.05, 0.02, 1.7   # Σ V h dy はセル中心値の近似。f_opening_dynamic = 2(2026-10-18 既定)で壁際の行の V が Manning に揃い +3.3 %


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


def load_state_z(tag):
    with open("save_%s/state.dat" % tag, "rb") as f:
        ntot = NX * NY
        read_rle_array(f, ntot)
        z = read_rle_array(f, ntot)
    return [[z[(j - 1) * NX + (i - 1)] for i in range(1, NX + 1)] for j in range(1, NY + 1)]


def load_fix(tag):
    with open("save_%s/geomorph_fixation.dat" % tag, "rb") as f:
        ntot = NX * NY
        a = read_rle_array(f, ntot)
        zr = read_rle_array(f, ntot)
    g = lambda v: [[v[(j - 1) * NX + (i - 1)] for i in range(1, NX + 1)] for j in range(1, NY + 1)]
    return g(a), g(zr)


def load_txt(tag, name, k):
    return [[float(v) for v in line.split()] for line in open("result_%s/%s%04d.txt" % (tag, name, k))]


mid = range(I_RAMP + 1, I_END)                       # 1 始まりの列
bar = [(i, j) for j in range(JB1, JB2 + 1) for i in mid]
chan = [(i, j) for j in range(J1, JB1) for i in mid]
bank = [(i, j) for j in (J1 - 1, J2 + 1) for i in mid]
at = lambda m, ij: m[ij[1] - 1][ij[0] - 1]

ok = True
a1 = 1.0 - math.exp(-T1 / TFIX)

# (1) 成長則(save_rt1 = rt1 の t = 600 s の保存値、および on のテキスト出力)
a_rt, _ = load_fix("rt1")
err_rt = max(abs(at(a_rt, ij) - a1) for ij in bar + bank)
fx1 = load_txt("on", "Fx", 1)
err_txt = max(abs(at(fx1, ij) - a1) for ij in bar + bank)
g1 = err_rt < TOL_A and err_txt < TOL_TXT
print("(1) 成長則 a(600 s) = 1 − exp(−600/360) = %.9f: save 誤差 %.2e (tol %.0e), 出力誤差 %.2e (tol %.0e) : %s"
      % (a1, err_rt, TOL_A, err_txt, TOL_TXT, "PASS" if g1 else "FAIL"))
ok = ok and g1

# (2) 常に湿潤な河道セルの a は厳密に 0
amax = 0.0
for tag in ("on", "weak"):
    for k in (1, 2, 3):
        fx = load_txt(tag, "Fx", k)
        amax = max(amax, max(abs(at(fx, ij)) for ij in chan))
    a_end, _ = load_fix(tag)
    amax = max(amax, max(abs(at(a_end, ij)) for ij in chan))
g2 = amax == 0.0
print("(2) 湿潤河道セルの a: max = %.1e (厳密に 0) : %s" % (amax, "PASS" if g2 else "FAIL"))
ok = ok and g2

# (3) 効果: on の砂州は出水で浸食なし、off の砂州は浸食あり
z1_on, z3_on = load_txt("on", "Z", 1), load_txt("on", "Z", 3)
z1_off, z3_off = load_txt("off", "Z", 1), load_txt("off", "Z", 3)
dz_on = [at(z3_on, ij) - at(z1_on, ij) for ij in bar]
dz_off = [at(z3_off, ij) - at(z1_off, ij) for ij in bar]
n_ero = sum(1 for v in dz_off if v < -DZ_ERO)
g3 = min(dz_on) >= 0.0 and n_ero >= NMIN
print("(3) 効果: on の砂州 min Δz = %.2e (>= 0), off の砂州 Δz < −%.3f が %d セル (>= %d; mean %.4f m) : %s"
      % (min(dz_on), DZ_ERO, n_ero, NMIN, sum(dz_off) / len(dz_off), "PASS" if g3 else "FAIL"))
ok = ok and g3

# (4) リセット(weak)
a_w, zr_w = load_fix("weak")
z_w = load_state_z("weak")
n_reset = sum(1 for ij in bar if at(a_w, ij) == 0.0)
excess = max(at(zr_w, ij) - at(z_w, ij) for ij in bar + chan)
g4 = n_reset >= 1 and excess <= DZRESET_WEAK
print("(4) リセット: weak の砂州で a = 0 のセル %d (>= 1), max(zref − z) = %.4e (<= dz_reset %.3f) : %s"
      % (n_reset, excess, DZRESET_WEAK, "PASS" if g4 else "FAIL"))
ok = ok and g4

# (5) 0 <= a <= 1
lo, hi = 1.0, 0.0
for tag in ("on", "weak"):
    for k in (0, 1, 2, 3):
        fx = load_txt(tag, "Fx", k)
        lo = min(lo, min(min(r) for r in fx)); hi = max(hi, max(max(r) for r in fx))
g5 = lo >= 0.0 and hi <= 1.0
print("(5) 範囲: a ∈ [%.4f, %.4f] ⊂ [0, 1] : %s" % (lo, hi, "PASS" if g5 else "FAIL"))
ok = ok and g5

# (6) 無効時は Fx を出さない(配列未確保)
g6 = len(glob.glob("result_off/Fx*.txt")) == 0 and not os.path.exists("save_off/geomorph_fixation.dat")
print("(6) 無効時の痕跡: result_off に Fx 出力なし・save_off に私有ファイルなし : %s" % ("PASS" if g6 else "FAIL"))
ok = ok and g6

# (7) 粗度: 定着砂州上の流速が下がり、断面流量は保存
def section_q(tag, k=3):
    h = load_txt(tag, "H", k); v = load_txt(tag, "V", k)
    qs = []
    for i in mid:
        qs.append(sum(h[j - 1][i - 1] * v[j - 1][i - 1] for j in range(J1, J2 + 1)) * 1.0)
    return sum(qs) / len(qs)
v_on = load_txt("on", "V", 3); v_rough = load_txt("rough", "V", 3)
vb_on = sum(at(v_on, ij) for ij in bar) / len(bar); vb_rough = sum(at(v_rough, ij) for ij in bar) / len(bar)
q_on, q_rough = section_q("on"), section_q("rough")
g7 = vb_rough / vb_on < RATIO_V and abs(q_on / Q_IN - 1.0) < TOL_QSEC and abs(q_rough / Q_IN - 1.0) < TOL_QSEC
print("(7) 粗度: 砂州上の V rough/on = %.3f/%.3f = %.3f (< %.1f), 断面流量 on %.3f, rough %.3f (Q_in %.1f ± %.0f%%) : %s"
      % (vb_rough, vb_on, vb_rough / vb_on, RATIO_V, q_on, q_rough, Q_IN, 100 * TOL_QSEC, "PASS" if g7 else "FAIL"))
ok = ok and g7

# (8) 浮遊砂: 定着した砂州は出水で正味堆積
z1_so, z3_so = load_txt("susp_off", "Z", 1), load_txt("susp_off", "Z", 3)
dz_off = [at(z3_so, ij) - at(z1_so, ij) for ij in bar]
for tag in ("susp_on", "susp_on2"):
    z1s, z3s = load_txt(tag, "Z", 1), load_txt(tag, "Z", 3)
    dzs = [at(z3s, ij) - at(z1s, ij) for ij in bar]
    g8 = min(dzs) > 0.0 and sum(dzs) / len(dzs) > sum(dz_off) / len(dz_off) + DZ_SUSP
    print("(8) 浮遊砂 %-8s: 砂州 Δz min %.4f (> 0), mean %.4f vs 定着なし %.4f (差 > %.2f m) : %s"
          % (tag, min(dzs), sum(dzs) / len(dzs), sum(dz_off) / len(dz_off), DZ_SUSP, "PASS" if g8 else "FAIL"))
    ok = ok and g8

# (9) 冠水減衰(decay): 水没した砂州の a は水没時刻から exp(−t/T_dec) で落ち、乾いた河岸は on と同じ
TDEC = 0.1 * 3600.0
a_on, _ = load_fix("on")
a_dc, _ = load_fix("decay")
dev = 0.0
for ij in bar:
    ao = at(a_on, ij)
    tw = -TFIX * math.log(1.0 - ao)                     # on は水没時刻で a が凍結する
    pred = ao * math.exp(-(1800.0 - tw) / TDEC)
    dev = max(dev, abs(at(a_dc, ij) / pred - 1.0))
bank_d = max(abs(at(a_dc, ij) - at(a_on, ij)) for ij in bank)
chan_d = max(abs(at(a_dc, ij)) for ij in chan)
g9 = dev < 1.0e-3 and bank_d == 0.0 and chan_d == 0.0
print("(9) 冠水減衰: 砂州 a(1800) の a_on·exp(−(1800 − t_w)/360) からの相対ずれ %.2e (< 1e-3), 河岸の a は on と差 %.1e (= 0), 河道 %.1e (= 0) : %s"
      % (dev, bank_d, chan_d, "PASS" if g9 else "FAIL"))
ok = ok and g9

print("=== fixation checks %s ===" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
