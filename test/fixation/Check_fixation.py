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
#   リスタート往復と MPI の一致は Run.sh / Run_MPI.sh が cmp で見る
import sys, struct, os, math, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, J1, J2, JB1, JB2, I_RAMP, I_END

T1, TFIX = 600.0, 0.1 * 3600.0
DZRESET_WEAK = 0.002
TOL_A, TOL_TXT, DZ_ERO, NMIN = 1.0e-9, 1.0e-4, 0.005, 10


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

print("=== fixation checks %s ===" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
