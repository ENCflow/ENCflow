#!/usr/bin/env python3
"""模式実験 C1〜C4(f_salt_exch)の検定。事前に ./Run_exch.sh(または各 param の実行)が必要。

終状態は倍精度の保存ファイル(save_exch_*/state.dat と saltwater.dat)から読む。
  C1(浸透 = 底層の塩水から先): 解析終状態 H = 0.7、Hss = 0.1、Hg = Hgs = 0.3(全セル)。
      判定は相対 1e-12(浮動小数点の加算の丸めのみ)。塩水体積 Hss + Hgs = 0.4 の保存も見る。
  C2(湧出 = 淡水から先、淡水がなければ塩水): 帯水層は全層が塩水なので、窪地に
      湧き出た地表水はほぼ全量が塩水(Hss/H >= 0.99。f_salt_exch=0 なら 0)、閉領域の
      塩水体積 Σ(Hss + Hgs) は相対 1e-3 以内で保存(塩水 zone を側方流の直前の状態で
      評価する。developer.md §47.7。それ以前は湧出面で 16 % 減った)。
  C3: C2 を地下水の更新間隔 dt_gwflow = 2 s(4 ステップ)で。判定は C2 と同じ
      (地下の塩水の処理が側方流と同じ刻みで同期していること)。
  C4a・C4b: 下部 4 割が塩水の帯水層から窪地へ湧出(a = f_salt_exch=1 = 淡水から先、
      b = 2 = 湧出前の塩水の割合で)。どちらも塩水体積を相対 1e-9 で保存し、窪地の水の
      塩水割合は b のほうが大きい(developer.md §47.9)。
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


def main():
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

    # --- C2・C3: 湧出の淡塩配分(窪地の水の塩水割合と塩水体積の保存) ---
    with open("data_salt/hgs0_slope.txt") as f:
        hgs0 = [float(x) for x in f.read().split()]
    for tag, savedir in (("C2", "save_exch_out"), ("C3", "save_exch_dtg")):
        s = load(savedir)
        pond = [i for i, z in enumerate(s["z"]) if z < -0.25]      # 窪地(z = −0.5)
        hp = sum(s["h"][i] for i in pond)
        sp = sum(s["hss"][i] for i in pond)
        frac = sp / hp
        good = frac >= 0.99
        ok &= good
        print(f"{tag} pond: H {hp / len(pond):.4f} m, Hss {sp / len(pond):.4f} m, "
              f"Hss/H = {frac:.4f} (>= 0.99; 0 without f_salt_exch)  {'PASS' if good else 'FAIL'}")
        v0 = sum(hgs0)
        v1 = sum(s["hss"]) + sum(s["hgs"])
        good = abs(v1 / v0 - 1.0) < 1e-3
        ok &= good
        print(f"{tag} salt volume: initial {v0:.6f}, final {v1:.6f} (ratio {v1 / v0:.6f}; "
              f"|ratio - 1| < 1e-3)  {'PASS' if good else 'FAIL'}")

    # --- C4a・C4b: 一部が塩水の帯水層からの湧出(配分の規則の違いと保存) ---
    with open("data_salt/hgs0_slope_half.txt") as f:
        v0 = sum(float(x) for x in f.read().split())
    frac = {}
    for tag, savedir in (("C4a", "save_exch_mix1"), ("C4b", "save_exch_mix2")):
        s = load(savedir)
        pond = [i for i, z in enumerate(s["z"]) if z < -0.25]
        frac[tag] = sum(s["hss"][i] for i in pond) / sum(s["h"][i] for i in pond)
        v1 = sum(s["hss"]) + sum(s["hgs"])
        good = abs(v1 / v0 - 1.0) < 1e-9
        ok &= good
        print(f"{tag} salt volume: initial {v0:.9f}, final {v1:.9f} (|ratio - 1| = "
              f"{abs(v1 / v0 - 1.0):.1e} < 1e-9)  pond Hss/H = {frac[tag]:.4f}  {'PASS' if good else 'FAIL'}")
    good = frac["C4b"] > frac["C4a"]
    ok &= good
    print(f"C4 pond Hss/H: C4b (mixing) {frac['C4b']:.4f} > C4a (fresh first) {frac['C4a']:.4f}  "
          f"{'PASS' if good else 'FAIL'}")

    print("=== Check_exch PASS ===" if ok else "=== Check_exch FAIL ===")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
