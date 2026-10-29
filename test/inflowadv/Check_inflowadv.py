#!/usr/bin/env python3
# inflowadv 検定(区間流入の外縁セルに接するエッジの移流項の規則。developer.md §68.40)
#   (1) 振動なし(osc5・osc3): j = 30 の流量(1 分ごと)の、11 分移動平均からの残差の標準偏差が
#       60〜120 分で平均流量の TOL_OSC 未満、最大が TOL_OSC_MAX 未満。平均流量は流入量に TOL_Q で一致。
#       流入セルから内側へ向かうエッジの移流項を 0 にしないと、幅 5 列で 6.3 %、幅 3 列で 15.5 % の
#       限界周期振動が出る(2026-10-29 の再構成)
#   (2) 横溢でエネルギーを作らない(side): 最終出力で、側溝の最初のセル (1, J2+1) のエネルギー水頭
#       η + V²/2g が、流入区間の中ほどのセル (1, (J1+J2)/2) を TOL_E より上回らない。面に沿うエッジと
#       区間の外へ出るエッジの移流項を 0 にすると上回る(流入セルに接するエッジをすべて 0 にした
#       2026-10-24〜29 の規則で +1.22 m、区間の外へ出るエッジだけ戻すと +0.26 m)
#   (3) 流入直下でエネルギーを作らない(osc5・osc3・jet3。緩勾配): 最終出力で、流入側の行 2〜J_JET の
#       セルのエネルギー水頭 z + h + V²/2g の最大が、流入行(行 1)の最大を TOL_EJ より上回らない。
#       内側エッジの流速にエネルギー上限がないと、流入直下に射流のジェットが立つ(幅 3 列で水深
#       1.0〜1.3 m・13 m/s。行 1 より +5.2 m。幅 5 列でも +0.23 m。jet3 は 39 秒で Courant 数 1 超)。
#       上限の基準を流入セルの今のフルード数で切り替えると jet3 にジェットが残る(+2.4 m。§68.40 の
#       改定 2)
#   (4) 射流の区間流入を絞らない(steep。等流のフルード数 1.95): 最終出力で、流入側の J_JET 列が
#       すべて射流(Fr > 1)、流入列(列 1)の平均水深が Manning の等流水深の TOL_HIN 以内、下流
#       (列 31〜50)の平均水深が等流水深に TOL_HN で一致。上限の基準を流入セルの速さだけにすると、
#       上限で絞られた流入セルが深くなる(+6.1 %)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import Q_PER_COL, J1, J2, hn_steep, z_osc

TOL_OSC, TOL_OSC_MAX, TOL_Q, TOL_E = 0.002, 0.005, 1.0e-3, 0.05
TOL_EJ, TOL_FR, TOL_HIN, TOL_HN, J_JET = 0.1, 1.0, 0.045, 0.02, 10
G = 9.81


def flux_series(rdir):
    t, q = [], []
    for line in open(rdir + "/fluxes/flux0001.csv"):
        if line.startswith("#") or not line.strip():
            continue
        f = [x.strip() for x in line.split(",")]
        t.append(float(f[1])); q.append(float(f[2]))
    return t, q


def load(rdir, name, k):
    return [[float(v) for v in line.split()] for line in open("%s/%s%04d.txt" % (rdir, name, k))]


ok = True
for case, w in (("osc5", 5), ("osc3", 3)):
    t, q = flux_series("result_" + case)
    qin = Q_PER_COL * w
    res = [q[n] - sum(q[n - 5:n + 6]) / 11 for n in range(5, len(q) - 5) if t[n] >= 60.0]
    late = [q[n] for n in range(len(q)) if t[n] >= 60.0]
    qm = sum(late) / len(late)
    sd = (sum(x * x for x in res) / len(res)) ** 0.5 / qm
    mx = max(abs(x) for x in res) / qm
    good = t[-1] >= 120.0 and sd < TOL_OSC and mx < TOL_OSC_MAX and abs(qm / qin - 1) < TOL_Q
    ok &= good
    print("(1) %s 幅 %d 列: 60〜120 分の残差 標準偏差 %.3f %%、最大 %.3f %%(上限 %.1f %%・%.1f %%)、"
          "平均流量 %.1f m3/s(流入 %.0f) : %s" % (case, w, 100 * sd, 100 * mx, 100 * TOL_OSC,
                                                 100 * TOL_OSC_MAX, qm, qin, "PASS" if good else "FAIL"))

rdir = "result_side"
k = max(int(f[1:5]) for f in os.listdir(rdir) if f.startswith("H") and f[1:5].isdigit() and int(f[1:5]) < 9000)
h, v, z = load(rdir, "H", k), load(rdir, "V", k), load(rdir, "Z", 0)
jm = (J1 + J2) // 2


def energy(i, j):
    return z[j - 1][i - 1] + h[j - 1][i - 1] + v[j - 1][i - 1] ** 2 / (2 * G)


de = energy(1, J2 + 1) - energy(1, jm)
good = de <= TOL_E
ok &= good
print("(2) side 出力 %d: 側溝の最初のセル (1,%d) のエネルギー水頭 %.3f m − 流入区間の中ほど (1,%d) %.3f m"
      " = %+.3f m(V = %.2f m/s、上限 %+.2f m) : %s" % (k, J2 + 1, energy(1, J2 + 1), jm, energy(1, jm), de,
                                                     v[J2][0], TOL_E, "PASS" if good else "FAIL"))



def last_output(rdir):
    return max(int(f[1:5]) for f in os.listdir(rdir) if f.startswith("H") and f[1:5].isdigit() and int(f[1:5]) < 9000)


def froude(hh, vv):
    return vv / (G * max(hh, 1.0e-3)) ** 0.5


for case in ("osc5", "osc3", "jet3"):
    rdir = "result_" + case
    k = last_output(rdir)
    h, v = load(rdir, "H", k), load(rdir, "V", k)

    def head(i, j):
        return z_osc(i + 1, j + 1) + h[j][i] + v[j][i] ** 2 / (2 * G)

    e1 = max(head(i, 0) for i in range(len(h[0])))
    e2 = max(head(i, j) for j in range(1, J_JET) for i in range(len(h[0])))
    vmax = max(v[j][i] for j in range(J_JET) for i in range(len(h[0])))
    good = k >= 1 and e2 - e1 <= TOL_EJ      # k >= 1: 最後まで計算した(途中で止まると出力 0 だけ)
    ok &= good
    print("(3) %s 出力 %d: 流入側の行 2〜%d のエネルギー水頭の最大 %.3f m − 流入行 %.3f m = %+.3f m"
          "(上限 %+.2f m。流速の最大 %.2f m/s) : %s"
          % (case, k, J_JET, e2, e1, e2 - e1, TOL_EJ, vmax, "PASS" if good else "FAIL"))

rdir = "result_steep"
k = last_output(rdir)
h, v = load(rdir, "H", k), load(rdir, "V", k)
frmin = min(froude(h[j][i], v[j][i]) for j in range(len(h)) for i in range(J_JET))
hin = sum(h[j][0] for j in range(len(h))) / len(h)
hd = [h[j][i] for j in range(len(h)) for i in range(30, 50)]
hu = sum(hd) / len(hd)
hn = hn_steep()
good = k >= 1 and frmin > TOL_FR and abs(hin / hn - 1) < TOL_HIN and abs(hu / hn - 1) < TOL_HN
ok &= good
print("(4) steep 出力 %d: 流入側の %d 列の最小フルード数 %.3f(下限 %.1f)、流入列の平均水深 %.4f m"
      "(等流水深 %.4f m の %.4f 倍。許容 ±%.1f %%)、下流の平均水深の比 %.4f(許容 ±%.0f %%) : %s"
      % (k, J_JET, frmin, TOL_FR, hin, hn, hin / hn, 100 * TOL_HIN, hu / hn, 100 * TOL_HN,
         "PASS" if good else "FAIL"))

print("=== inflowadv checks %s ===" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
