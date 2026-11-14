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
#   構成 5(result_cross。流量を上げ下げして、河道の水位に河岸の高さを横切らせる。§108.9):
#     (8) 河岸の線を横切る流量(毎ステップの記録)の 2 階差分の最大が TOL_D2 未満(水位が河岸の高さに
#         あるとき、頭打ちが効く・効かないを数ステップごとに行き来しない。つなぎのない規則では
#         17〜36 m3/s 飛ぶ)
#     (9) 河道の水位が河岸の地盤より高い間は、氾濫原へ水が載る(平均の流量が Q_OVER より大きい)
#     (10) 立ち上がりで、河道の水位が河岸の地盤の MARGIN 下に届くまでは、河岸の列の水深が初期の
#          水膜を超えない(つなぎの幅は MARGIN より狭い)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_bankcap import NX, DX, J_FP2, J_CH1, J_CH2, H0, U0, FILM, D_BANK, G

TOL_FILM = 1.0e-4                 # (1) 水膜を超えないことの許容 (m)
TOL_H = 0.01                      # (6) 等流水深との一致
I1, I2 = 21, 60                   # (6) 河道の水深を平均する列(x = 100〜300 m)
TOL_D2 = 2.0                      # (8) 毎ステップの流量の 2 階差分の上限 (m3/s)
T_SKIP = 60.0                     # (8) 初めの過渡を除く時間 (s)
Q_OVER = 3.0                      # (9) 水位が河岸より高い間の平均の流量の下限 (m3/s)
MARGIN = 0.3                      # (10) 河岸の地盤からの余裕 (m)


def load(rdir, name):
    return [[float(v) for v in line.split()] for line in open("%s/%s.txt" % (rdir, name))]


def frames(rdir):
    ks = sorted(int(ln.split(",")[0]) for ln in open(rdir + "/FILENUMBER.csv")
                if not ln.startswith("#") and int(ln.split(",")[0]) < 9000)
    return [load(rdir, "H%04d" % k) for k in ks]


def fp_volume(h):
    return sum(sum(h[j]) for j in range(J_FP2)) * DX * DX


def series(fn):
    """記録の CSV(# の行は見出し)を読む。戻り値: 見出しの辞書(キー → 値の文字列)、数値の行のリスト"""
    head, rows = {}, []
    for ln in open(fn):
        if ln.startswith("#"):
            p = ln[1:].split("=,")
            if len(p) == 2:
                head[p[0].strip()] = p[1].strip()
        elif ln.strip():
            rows.append([float(v) for v in ln.split(",")])
    return head, rows


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
    # 構成 5: 河道の水位に河岸の高さを横切らせる(毎ステップの記録)
    _, fl = series("result_cross/fluxes/flux0001.csv")
    hc, pc = series("result_cross/probes/probe0001.csv")      # 河岸に接する河道のセル
    hb, pb = series("result_cross/probes/probe0002.csv")      # 河岸の列のセル
    t = [r[1] * 60.0 for r in fl]
    q = [r[2] for r in fl]
    d2 = [(abs(q[i + 1] - 2.0 * q[i] + q[i - 1]), t[i]) for i in range(1, len(q) - 1) if t[i] >= T_SKIP]
    d2max, td2 = max(d2)
    zc, zb = float(hc["z(m)"]), float(hb["z(m)"])
    gap = [zb - (zc + r[3]) for r in pc]                      # 河岸の地盤 − 河道の水位
    over = [qq for qq, g in zip(q, gap) if g < 0.0]
    qover = sum(over) / len(over) if over else 0.0
    t_over = [tt for tt, g in zip(t, gap) if g < 0.0]
    i_near = next((i for i, g in enumerate(gap) if g < MARGIN), len(gap))
    film_max = max(r[3] for r in pb[:i_near])
    g8 = d2max < TOL_D2
    g9 = len(over) > 0 and qover > Q_OVER
    g10 = film_max <= FILM + TOL_FILM
    print("(8) cross: 河岸の線を横切る流量の毎ステップの 2 階差分の最大 %.3f m3/s(%.1f 秒。< %.1f) : %s"
          % (d2max, td2, TOL_D2, "PASS" if g8 else "FAIL"))
    print("(9) cross: 河道の水位が河岸の地盤より高い間(%.0f〜%.0f 秒)の、氾濫原へ載る流量の平均 %.2f m3/s (> %.1f) : %s"
          % (t_over[0] if t_over else 0.0, t_over[-1] if t_over else 0.0, qover, Q_OVER, "PASS" if g9 else "FAIL"))
    print("(10) cross: 立ち上がりで水位が河岸の %.1f m 下に届く(%.0f 秒)までの、河岸の列の水深の最大 %.4f m (<= %.4f) : %s"
          % (MARGIN, t[i_near] if i_near < len(t) else t[-1], film_max, FILM + TOL_FILM, "PASS" if g10 else "FAIL"))
    ok = ok and g8 and g9 and g10
    print("== bankcap 検定: %s ==" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
