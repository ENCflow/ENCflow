#!/usr/bin/env python3
# 深さ依存クリープ(creep_hstar。developer.md §88.8)の検定
#   save_hstar_<tag>/state.dat(倍精度)の z・sd を読み、初期地形(ガウス丘。param.txt・
#   gaussian_hill・Check_analytic.py と対で保守)と比べる。土層だけが動くので、
#     (a) 岩盤面 z − sd が初期の z0 − sd0 のまま(TOL_ROCK m)
#     (b) 土層の総量 Σ sd A が保存(四周は壁。相対 TOL_VOL)
#     (c) sd >= 0
#   を全構成で確かめ、構成ごとに次を加える:
#     thick(sd0 = 10 m、H_c = 0.05 m): 全セルの z が従来の線形拡散(param.txt の
#           save/state.dat)に TOL_ROCK 以内(利用可能率 = 1 の極限。解析解との比較は
#           Check_analytic.py)
#     thin(sd0 = 0.02 m、H_c = 0.1 m)・lim(sd0 = H_c = 2 mm。供給量制限が働く):
#           頂部の土層が剥がれ(sd < THIN_TOP × sd0)、脚部に溜まる(max sd > sd0)
#     bare(土層厚 0 の分布): z が初期のまま、sd = 0 のまま
#   使い方: Check_hstar.py <tag>   終了コード 0 = PASS
import sys, math, struct

A, SIGMA2 = 1.0, 100.0                      # param*.txt / gaussian_hill と対で保守する
NX, NY, IC, JC, DX = 101, 101, 51, 51, 1.0
TOL_ROCK, TOL_VOL, THIN_TOP = 1.0e-12, 1.0e-12, 0.1
SD0 = {"thick": 10.0, "thin": 0.02, "lim": 0.002, "bare": 0.0}   # param_hstar_*.txt と対で保守する


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


def load_state(dsave):
    # 書き並びは h, z, hrs, hg, sd, hs(m_state の save_state)
    with open(dsave + "/state.dat", "rb") as f:
        ntot = NX * NY
        read_rle_array(f, ntot)
        z = read_rle_array(f, ntot)
        read_rle_array(f, ntot)
        read_rle_array(f, ntot)
        sd = read_rle_array(f, ntot)
    return z, sd


def z_init(i, j):
    r2 = ((i - IC) * DX) ** 2 + ((j - JC) * DX) ** 2
    return A * math.exp(-r2 / (2.0 * SIGMA2))


tag = sys.argv[1]
sd0 = SD0[tag]
z, sd = load_state("save_hstar_" + tag)
z0 = [z_init(i, j) for j in range(1, NY + 1) for i in range(1, NX + 1)]
ok = True

drock = max(abs((zz - ss) - (z00 - sd0)) for zz, ss, z00 in zip(z, sd, z0))
vol, vol0 = sum(sd) * DX * DX, sd0 * NX * NY * DX * DX
dvol = abs(vol - vol0) / vol0 if vol0 > 0.0 else abs(vol)
sdmin = min(sd)
g = drock < TOL_ROCK and dvol < TOL_VOL and sdmin >= 0.0
print("[%s] (a) max|(z − sd) − (z0 − sd0)| = %.2e m (< %.0e)、(b) 土層の総量の相対変化 %.2e (< %.0e)、"
      "(c) min sd = %.3e m (>= 0) : %s"
      % (tag, drock, TOL_ROCK, dvol, TOL_VOL, sdmin, "PASS" if g else "FAIL"))
ok = ok and g

kc = (JC - 1) * NX + (IC - 1)
if tag == "thick":
    zl, _ = load_state("save")
    dz = max(abs(zz - zz2) for zz, zz2 in zip(z, zl))
    g = dz < TOL_ROCK
    print("[%s] 従来の線形拡散(param.txt)との max|Δz| = %.2e m (< %.0e) : %s"
          % (tag, dz, TOL_ROCK, "PASS" if g else "FAIL"))
    ok = ok and g
elif tag in ("thin", "lim"):
    sdmax = max(sd)
    g = sd[kc] < THIN_TOP * sd0 and sdmax > sd0 and z[kc] >= z0[kc] - sd0
    print("[%s] 頂部の sd = %.3e m (< %.1f sd0)、max sd = %.4f m (> sd0 = %.3f m)、頂部の低下 %.4f m "
          "(<= sd0) : %s"
          % (tag, sd[kc], THIN_TOP, sdmax, sd0, z0[kc] - z[kc], "PASS" if g else "FAIL"))
    ok = ok and g
elif tag == "bare":
    dz = max(abs(zz - z00) for zz, z00 in zip(z, z0))
    sdmax = max(abs(v) for v in sd)
    g = dz < TOL_ROCK and sdmax == 0.0
    print("[%s] max|z − z0| = %.2e m (< %.0e)、max|sd| = %.1e : %s"
          % (tag, dz, TOL_ROCK, sdmax, "PASS" if g else "FAIL"))
    ok = ok and g

print("== creep_hstar %s : %s ==" % (tag, "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
