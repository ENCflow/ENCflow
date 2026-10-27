#!/usr/bin/env python3
# sedfeed 検定(developer.md §84.9)
#   直線水路(幅 5 セル、全域可動)の区間流入への給砂 3 方式を検定する。
#     (1) 無給砂(nofeed): 上流端の河床が DZ_NOFEED 以上低下する(河床低下波)
#     (2) 容量給砂 倍率 1(feed1): 入口セルの河床変動が厳密に 0(供給 = 正味流出)、
#         上流区間 x = X1〜X2 の平均 |Δz| < DZ_FEED1
#     (3) 容量給砂 倍率 0.5(feed05): 入口セルの低下量が無給砂より小さい
#         (非線形: 入口に穴ができると正味流出が減って供給も減る。比例はしない)
#     (4) 掃流砂流砂量 inflow_qb(qb。東辺は壁): 台帳 (1 − λ) Σ(z − z0) A =
#         ∫Qb dt × morfac が TOL_LEDGER(save_qb/state.dat の z を読む)
#     (5) 浮遊砂の平衡濃度給砂 inflow_cs_eq(cseq): 流入列の濃度 hs/h が流入セルの
#         τ* から評価した C_eq に ±TOL_CEQ で一致
#     (6) クリープとの併用(nofeed_creep。creep_d = 1e-30 で 1 回の更新の変化は z の ULP 未満):
#         河床が nofeed とビット一致
#         (クリープが開境界の掃流砂の流出を再集計しないこと。developer.md §19.10)
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, DX, J1, J2, X1, X2, S, N

DZ_NOFEED, DZ_FEED1, TOL_LEDGER, TOL_CEQ = 0.2, 0.03, 1.0e-9, 0.01
LAMBDA, MORFAC_QB, QB, TT_QB = 0.4, 10.0, 0.0005, 1200.0
ESA, STAUSC, SGRAV, DSUSP = 1.0e-4, 0.05, 1.65, 0.0002


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


def load_txt(tag, name, k):
    return [[float(v) for v in line.split()] for line in open("result_%s/%s%04d.txt" % (tag, name, k))]


z0 = [[float(v) for v in line.split()] for line in open("zinit.txt")]


def channel_profile(z):
    return [sum(z[j - 1][i] - z0[j - 1][i] for j in range(J1, J2 + 1)) / (J2 - J1 + 1) for i in range(NX)]


ok = True
p_no = channel_profile(load_txt("nofeed", "Z", 3))
p_f1 = channel_profile(load_txt("feed1", "Z", 3))
p_f05 = channel_profile(load_txt("feed05", "Z", 3))

g1 = p_no[0] < -DZ_NOFEED
print("(1) 無給砂: 入口セルの Δz = %.3f m (< −%.1f) : %s" % (p_no[0], DZ_NOFEED, "PASS" if g1 else "FAIL"))
ok = ok and g1

zf1 = load_state_z("feed1")
dz_inlet = max(abs(zf1[j - 1][0] - z0[j - 1][0]) for j in range(J1, J2 + 1))
reach = sum(abs(v) for v in p_f1[X1:X2]) / (X2 - X1)
g2 = dz_inlet < 1.0e-9 and reach < DZ_FEED1
print("(2) 容量給砂 fac=1: 入口セルの max|Δz| = %.1e (< 1e-9), x=%d-%d の平均|Δz| = %.4f m (< %.2f; 無給砂 %.4f) : %s"
      % (dz_inlet, X1, X2, reach, DZ_FEED1, sum(abs(v) for v in p_no[X1:X2]) / (X2 - X1), "PASS" if g2 else "FAIL"))
ok = ok and g2

g3 = p_no[0] < p_f05[0] < 0.0
print("(3) 容量給砂 fac=0.5: 入口セルの Δz = %.3f m (無給砂 %.3f より小さい低下、比例はしない) : %s"
      % (p_f05[0], p_no[0], "PASS" if g3 else "FAIL"))
ok = ok and g3

zq = load_state_z("qb")
vol = sum((zq[j - 1][i] - z0[j - 1][i]) for j in range(1, NY + 1) for i in range(NX)) * DX * DX * (1.0 - LAMBDA)
fed = QB * TT_QB * MORFAC_QB
g4 = abs(vol / fed - 1.0) < TOL_LEDGER
print("(4) inflow_qb 台帳: (1−λ)Σ(z−z0)A = %.9f m3, ∫Qb dt × morfac = %.9f m3, 相対差 %.1e (< %.0e) : %s"
      % (vol, fed, abs(vol / fed - 1.0), TOL_LEDGER, "PASS" if g4 else "FAIL"))
ok = ok and g4

h = load_txt("cseq", "H", 1); hs = load_txt("cseq", "Hs", 1); v = load_txt("cseq", "V", 1)
cc = []; ce = []
for j in range(J1, J2 + 1):
    hh = max(h[j - 1][0], 1.0e-3)
    taus = N ** 2 * v[j - 1][0] ** 2 / (SGRAV * DSUSP * hh ** (1.0 / 3.0))
    ce.append(ESA * (taus / STAUSC - 1.0) if taus > STAUSC else 0.0)
    cc.append(hs[j - 1][0] / h[j - 1][0])
ratio = (sum(cc) / len(cc)) / (sum(ce) / len(ce))
g5 = abs(ratio - 1.0) < TOL_CEQ
print("(5) inflow_cs_eq: 流入列の hs/h = %.5f, C_eq(流入セルの τ*) = %.5f, 比 %.4f (1 ± %.2f) : %s"
      % (sum(cc) / len(cc), sum(ce) / len(ce), ratio, TOL_CEQ, "PASS" if g5 else "FAIL"))
ok = ok and g5

zc = load_state_z("nofeed_creep")
zn = load_state_z("nofeed")
dzc = max(abs(zc[j][i] - zn[j][i]) for j in range(NY) for i in range(NX))
g6 = dzc == 0.0
print("(6) クリープ併用(creep_d = 1e-30): nofeed との max|Δz| = %.2e m (ビット一致) : %s"
      % (dzc, "PASS" if g6 else "FAIL"))
ok = ok and g6

print("=== sedfeed checks %s ===" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
