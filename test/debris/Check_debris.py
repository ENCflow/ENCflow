#!/usr/bin/env python3
# debris(土石流 E-D)疎通・保存則検定
#   save/state.dat(ゼロ抑制 RLE。developer.md §7)から z, sd, hs を読み、
#     (1) 固体総量保存: |Σhs + (1-λ)Σ(z-z0)| < TOL_SUM(E-D 反対称の帰結)
#     (2) 共動更新恒等: max|(sd - sd0) - (z - z0)| < TOL_SD
#     (3) 活性確認: 斜面部の侵食 min(dz) < -MIN_ERO かつ
#         遷緩点(i>=30)下流の堆積 max(dz) > MIN_DEP
#   を検定する。z0 は slope_break(tanθ=0.4, 遷緩点 x=30m)、sd0, λ は
#   param.txt と対で保守する。
#   使い方: Check_debris.py <savedir> [eg|wet|gw|fluv]
#   eg モード(江頭則構成): (3) を「斜面侵食 + 平坦部への土砂到達
#   (max hs)」に替える。希薄なシート流では θe ≈ 0 のため平坦部の
#   河床堆積は遅く(物理的に正しい)、短時間の疎通検定では hs の到達を
#   活性の証拠とする。
#   wet モード(f_dbwet=1 構成): eg の検定に加えて
#     (4) 水台帳: |Σh − 降雨総量 + λ・s_b・Σdz| < TOL_SUM
#   を検定する(間隙水連行の反対称交換の帰結。閉領域・クランプ不発火が
#   前提。降雨総量・s_b は param_tkwet.txt と対で保守する)。
#   gw モード(構成6 = param_gw.txt。構成1 + 地下水計算 + f_dbwet=2): 可動層を
#   斜面(i <= 30)5 m・平坦部 0 m(sd_gw.txt と対)に替えて (1)〜(3) に加え
#     (4) 水台帳: |Σh + Σhg − 降雨総量| < TOL_SUM(引き渡しは水を保存する。
#         浸透能はほぼ 0 = 地下貯留は堆積の間隙水だけ)
#     (5) 堆積の間隙: 平坦部(i >= 31)で max|hg − sy0・sd| < TOL_SD かつ
#         Σhg > MIN_HG(平坦部の土層は堆積物だけ。堆積で満たし侵食で放す
#         引き渡しの下で hg = sy0・sd が常に成り立つ)
#   を検定する。
#   fluv モード(構成5 = param_fluv.txt。土石流 E-D + 掃流砂): 地形を転置した
#   斜面(20 × 60、y < 40 m で tanθ = 0.4。make_fluv.py と対)、sd0 = 2 mm に
#   替えて (1)〜(3) を検定する((3) は斜面 y < 40 m の侵食と下流の平坦部の堆積)。
import sys, struct

SD0, PORO = 5.0, 0.4
NX, NY = 60, 20
DX = 1.0
ST, XB = 0.4, 30.0          # slope_break のパラメータ(user_geoinfo と対)
TOL_SUM, TOL_SD = 1.0e-9, 1.0e-10
MIN_ERO, MIN_DEP = 1.0e-3, 1.0e-3
RAIN = NX * NY * (200.0 / 1000.0 / 3600.0) * 60.0   # 降雨総量 (m*cell)。param_tkwet と対
SATBED = 1.0                                        # db_satbed(wet モード)
RAIN_GW = NX * NY * (200.0 / 1000.0 / 3600.0) * 30.0  # 降雨総量 (m*cell)。param_gw と対
SY0, I_SLOPE, MIN_HG = 0.2, 30, 1.0e-4             # gw モード: sy0、可動層のある列、Σhg の下限


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
    hdr = read_rec(f)
    n, nrun = struct.unpack("<2q", hdr)
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    packed_raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(packed_raw) // 8), packed_raw)
    out = [0.0] * n
    i = 0
    k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def z0_of(idx):
    i = idx % NX + 1
    x = (i - 0.5) * DX
    return ST * (XB - x) if x < XB else 0.0


def upslope(idx):
    """斜面部(遷緩点より上流)のセルか"""
    return (idx % NX + 1) < 30


def sd0_of(idx):
    return SD0


savedir = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "tk"
if mode == "fluv":
    # 構成5: 転置した斜面(make_fluv.py の NX・NY・ST・YB と対)と薄い可動層
    NX, NY, SD0, YB = 20, 60, 0.002, 40.0

    def z0_of(idx):
        y = (idx // NX + 1 - 0.5) * DX
        return ST * (YB - y) if y < YB else 0.0

    def upslope(idx):
        return (idx // NX + 1 - 0.5) * DX < YB
elif mode == "gw":
    # 構成6: 可動層は斜面(i <= I_SLOPE)だけ(sd_gw.txt と対)
    def sd0_of(idx):
        return SD0 if idx % NX + 1 <= I_SLOPE else 0.0
with open(savedir + "/state.dat", "rb") as f:
    ntot = NX * NY
    h = read_rle_array(f, ntot)
    z = read_rle_array(f, ntot)
    hrs = read_rle_array(f, ntot)
    hg = read_rle_array(f, ntot)
    sd = read_rle_array(f, ntot)
    hs = read_rle_array(f, ntot)

dz = [zi - z0_of(idx) for idx, zi in enumerate(z)]
solids = sum(hs) + (1.0 - PORO) * sum(dz)
max_ident = max(abs((sdi - sd0_of(idx)) - d) for idx, (sdi, d) in enumerate(zip(sd, dz)))
ero = min(dz[idx] for idx in range(ntot) if upslope(idx))
dep = max(dz[idx] for idx in range(ntot) if not upslope(idx))
arr = max(hs[idx] for idx in range(ntot) if not upslope(idx))

ok1 = abs(solids) < TOL_SUM
ok2 = max_ident < TOL_SD
if mode in ("eg", "wet"):
    ok3 = ero < -MIN_ERO and arr > 1.0e-4
else:
    ok3 = ero < -MIN_ERO and dep > MIN_DEP
print("(1) 固体総量保存: sum(hs)+(1-λ)sum(dz) = %.3e m*cell (tol %.0e) : %s"
      % (solids, TOL_SUM, "PASS" if ok1 else "FAIL"))
print("(2) 共動更新    : max|(sd-sd0)-(z-z0)| = %.3e m (tol %.0e) : %s"
      % (max_ident, TOL_SD, "PASS" if ok2 else "FAIL"))
if mode in ("eg", "wet"):
    print("(3) 活性確認    : 斜面侵食 min dz = %.3e m, 平坦部到達 max hs = %.3e m : %s"
          % (ero, arr, "PASS" if ok3 else "FAIL"))
else:
    print("(3) 活性確認    : 斜面侵食 min dz = %.3e m, 遷緩点下堆積 max dz = %.3e m : %s"
          % (ero, dep, "PASS" if ok3 else "FAIL"))

ok = ok1 and ok2 and ok3
if mode == "wet":
    wres = sum(h) - RAIN + PORO * SATBED * sum(dz)
    ok4 = abs(wres) < TOL_SUM
    print("(4) 水台帳      : sum(h)-rain+λ・s_b・sum(dz) = %.3e m*cell (tol %.0e) : %s"
          % (wres, TOL_SUM, "PASS" if ok4 else "FAIL"))
    ok = ok and ok4
if mode == "gw":
    wres = sum(h) + sum(hg) - RAIN_GW
    ok4 = abs(wres) < TOL_SUM
    print("(4) 水台帳      : sum(h)+sum(hg)-rain = %.3e m*cell (tol %.0e) : %s"
          % (wres, TOL_SUM, "PASS" if ok4 else "FAIL"))
    flat = [idx for idx in range(ntot) if idx % NX + 1 > I_SLOPE]
    pres = max(abs(hg[idx] - SY0 * sd[idx]) for idx in flat)
    hgf = sum(hg[idx] for idx in flat)
    ok5 = pres < TOL_SD and hgf > MIN_HG
    print("(5) 堆積の間隙  : 平坦部 max|hg-sy0*sd| = %.3e m (tol %.0e), sum hg = %.3e m*cell (> %.0e) : %s"
          % (pres, TOL_SD, hgf, MIN_HG, "PASS" if ok5 else "FAIL"))
    ok = ok and ok4 and ok5
print("== debris 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
