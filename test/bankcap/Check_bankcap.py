#!/usr/bin/env python3
# test/bankcap の検定(標準ライブラリだけ)。エッジ水深のエネルギー頭による頭打ち f_dry_head_cap = 2
# (developer.md §108): 受け手が濡れていても、受け手の地盤が送り手の水位より高ければ頭打ちする
#   Check_bankcap.py
#   構成 1(result_wet2。薄く濡れた河岸、f_dry_head_cap = 2):
#     (1) 河岸の列(河道に接する氾濫原の行)の期間最大水深 H9999 が、初期の水膜 FILM を超えない
#         (河道の水位は河岸の地盤より 1 m 低く、流速水頭 0.4 m を足しても届かないので、河道の水は
#         河岸へ登れない)
#     (2) 終了時の河岸の列の水深が FILM の半分未満(水膜は河道へ抜ける)
#     (3) 氾濫原の水量が、出力のたびに減る(増えない)
#   構成 2(result_wet1。同じ配置で f_dry_head_cap = 1):
#     (4) 河岸の列の期間最大水深が FILM の 2 倍を超える(受け手が濡れていると 1 の頭打ちは掛からず、
#         河道の水が登る。(1) がこの違いを見分けていることの確認)
#   構成 3・4(result_dry2・result_dry1。乾いた河岸):
#     (5) 氾濫原が乾いたまま(H9999 = 0)
#     (6) 終了時の河道の水深(流入と下流端から離れた区間の平均)が等流水深 H0 に ±TOL_H
#   構成 3 と 4 の結果のバイト比較は Run.sh が行う(乾いた受け手では 1 と 2 は同じ)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_bankcap import NX, DX, J_FP2, J_CH1, J_CH2, H0, U0, FILM, D_BANK, G

TOL_FILM = 1.0e-4                 # (1) 水膜を超えないことの許容 (m)
TOL_H = 0.01                      # (6) 等流水深との一致
I1, I2 = 21, 60                   # (6) 河道の水深を平均する列(x = 100〜300 m)


def load(rdir, name):
    return [[float(v) for v in line.split()] for line in open("%s/%s.txt" % (rdir, name))]


def frames(rdir):
    ks = sorted(int(ln.split(",")[0]) for ln in open(rdir + "/FILENUMBER.csv")
                if not ln.startswith("#") and int(ln.split(",")[0]) < 9000)
    return [load(rdir, "H%04d" % k) for k in ks]


def fp_volume(h):
    return sum(sum(h[j]) for j in range(J_FP2)) * DX * DX


def bank_max(h):
    return max(h[J_FP2 - 1])


def channel_depth(h):
    vals = [h[j - 1][i - 1] for j in range(J_CH1, J_CH2 + 1) for i in range(I1, I2 + 1)]
    return sum(vals) / len(vals)


def main():
    ok = True
    print("河道: 等流水深 H0 = %.3f m、流速 %.3f m/s(流速水頭 %.2f m)。河岸の地盤は河道の水位より %.2f m 高い。"
          "水膜 FILM = %g m" % (H0, U0, U0 * U0 / (2.0 * G), D_BANK - H0, FILM))
    res = {}
    for tag in ("wet2", "wet1"):
        fr = frames("result_" + tag)
        hm = load("result_" + tag, "H9999")
        res[tag] = dict(bmax=bank_max(hm), bend=bank_max(fr[-1]), vol=[fp_volume(h) for h in fr],
                        hch=channel_depth(fr[-1]))
    r = res["wet2"]
    g1 = r["bmax"] <= FILM + TOL_FILM
    g2 = r["bend"] < 0.5 * FILM
    g3 = all(b <= a for a, b in zip(r["vol"][:-1], r["vol"][1:]))
    print("(1) f_dry_head_cap = 2: 河岸の列の期間最大水深 %.4f m (<= %.4f) : %s"
          % (r["bmax"], FILM + TOL_FILM, "PASS" if g1 else "FAIL"))
    print("(2) f_dry_head_cap = 2: 終了時の河岸の列の水深 %.4f m (< %.4f) : %s"
          % (r["bend"], 0.5 * FILM, "PASS" if g2 else "FAIL"))
    print("(3) f_dry_head_cap = 2: 氾濫原の水量 %s m3(増えない) : %s"
          % (" → ".join("%.1f" % v for v in r["vol"]), "PASS" if g3 else "FAIL"))
    r1 = res["wet1"]
    g4 = r1["bmax"] > 2.0 * FILM
    print("(4) f_dry_head_cap = 1: 河岸の列の期間最大水深 %.4f m、終了時 %.4f m (期間最大 > %.4f = 河道の水が登る) : %s"
          % (r1["bmax"], r1["bend"], 2.0 * FILM, "PASS" if g4 else "FAIL"))
    print("    参考: 河道の水深(x = 100〜300 m の平均) f_dry_head_cap = 2 で %.3f m、1 で %.3f m"
          "(濡れた河岸に接する河道は等流水深より深く出る。developer.md §50.9 の 2 つ目の性質で、この検定の対象外)"
          % (r["hch"], r1["hch"]))
    ok = ok and g1 and g2 and g3 and g4
    for tag in ("dry2", "dry1"):
        fr = frames("result_" + tag)
        hm = load("result_" + tag, "H9999")
        fpmax = max(max(hm[j]) for j in range(J_FP2))
        hch = channel_depth(fr[-1])
        g5 = fpmax == 0.0
        g6 = abs(hch / H0 - 1.0) < TOL_H
        print("(5)(6) %s: 氾濫原の期間最大水深 %.1e m (= 0)、河道の水深 %.4f m / H0 = %.4f (1 ± %.2f) : %s"
              % (tag, fpmax, hch, hch / H0, TOL_H, "PASS" if (g5 and g6) else "FAIL"))
        ok = ok and g5 and g6
    print("== bankcap 検定: %s ==" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
