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
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import Q_PER_COL, J1, J2

TOL_OSC, TOL_OSC_MAX, TOL_Q, TOL_E = 0.002, 0.005, 1.0e-3, 0.05
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

print("=== inflowadv checks %s ===" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
