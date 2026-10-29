#!/usr/bin/env python3
"""模式実験 C1・C2(f_salt_exch)の検定。事前に ./Run_exch.sh(または両 param の実行)が必要。

終状態は倍精度の保存ファイル(save_exch_*/state.dat と saltwater.dat)から読む。
  C1(浸透 = 底層の塩水から先): 解析終状態 H = 0.7、Hss = 0.1、Hg = Hgs = 0.3(全セル)。
      判定は相対 1e-12(浮動小数点の加算の丸めのみ)。塩水体積 Hss + Hgs = 0.4 の保存も見る。
  C2(湧出 = 淡水から先、淡水がなければ塩水): 帯水層は全層が塩水なので、窪地に
      湧き出た地表水は塩水を含む(Hss/H >= 0.1 を合格とする定性判定。f_salt_exch=0 なら 0)。
      塩水体積の収支は表示のみ(湧出面で層1の水頭が地表水深ぶん切り替わる場所では
      加算方式の逐次分割で塩水が減る。developer.md §47.5 の既知の数値特性)。
"""
import struct
import sys


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    p = f.read(n)
    f.read(4)
    return p


def read_rle(f):
    n, nrun = struct.unpack("<2q", read_rec(f))
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


def load(savedir):
    with open(f"{savedir}/state.dat", "rb") as f:
        st = {k: read_rle(f) for k in ["h", "z", "hrs", "hg", "sd", "hs"]}
    with open(f"{savedir}/saltwater.dat", "rb") as f:
        st["hss"] = read_rle(f)
        st["hgs"] = read_rle(f)
    return st


def relerr(a, v):
    return max(abs(x - v) for x in a) / v


ok = True

# --- C1: 浸透の淡塩配分(解析終状態) ---
s = load("save_exch_in")
expect = {"h": 0.7, "hss": 0.1, "hg": 0.3, "hgs": 0.3}
for k, v in expect.items():
    err = relerr(s[k], v)
    good = err < 1e-12
    ok &= good
    print(f"C1 {k:4s}: min {min(s[k]):.15f} max {max(s[k]):.15f} (analytical {v})"
          f"  rel.err {err:.1e}  {'PASS' if good else 'FAIL'}")
tot = [a + b for a, b in zip(s["hss"], s["hgs"])]
err = relerr(tot, 0.4)
good = err < 1e-12
ok &= good
print(f"C1 salt volume Hss+Hgs = {max(tot):.15f} (initial 0.4)  rel.err {err:.1e}  {'PASS' if good else 'FAIL'}")

# --- C2: 湧出の淡塩配分(定性判定+収支の表示) ---
s = load("save_exch_out")
with open("data_salt/hgs0_slope.txt") as f:
    hgs0 = [float(x) for x in f.read().split()]
pond = [i for i, z in enumerate(s["z"]) if z < -0.25]      # 窪地(z = −0.5)
hp = sum(s["h"][i] for i in pond)
sp = sum(s["hss"][i] for i in pond)
frac = sp / hp
good = frac >= 0.1
ok &= good
print(f"C2 pond: H {hp / len(pond):.4f} m, Hss {sp / len(pond):.4f} m, "
      f"Hss/H = {frac:.3f} (>= 0.1; 0 without f_salt_exch)  {'PASS' if good else 'FAIL'}")
v0 = sum(hgs0)
v1 = sum(s["hss"]) + sum(s["hgs"])
print(f"C2 salt volume: initial {v0:.6f}, final {v1:.6f} (ratio {v1 / v0:.4f}; "
      f"loss at the seepage face is a known property, developer.md §47.5)")

print("=== Check_exch PASS ===" if ok else "=== Check_exch FAIL ===")
sys.exit(0 if ok else 1)
