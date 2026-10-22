#!/usr/bin/env python3
# wave_river 検定(developer.md §84.15 河口の規則 wave_vmax)
#   西の陸地を貫く河道(幅 10 m、河床 −1.2 m、流速 ≈ 0.8 m/s)が東の海(海浜勾配 0.02)に出る。
#   沖波 H0 = 0.5 m・T = 5 s(砕波水深 h_b/γ = 0.86 m < 河道の水深)を河道軸に正面(西向き)に
#   当てる。河道は砕波帯より深いので規則が無いと「波の源」になり、露出度が河口から河道を
#   遡って河道内の浅い所に沿岸漂砂が働く。
#     (1) vmax(wave_vmax = 0.5 m/s。河道の流速は 0.76 m/s 以上): 河口から XM 以上上流の河道の
#         河床が、波なし(nowave)と TOL 以内で一致し、かつ novmax の差の RATIO 倍未満
#         (波は河道に入らない。残る数 mm〜cm は河口砂州の変化が早瀬の侵食 に及ぶ水理的な帰還)
#     (2) novmax(規則なし): 同じ区間の差が DEMO 以上(問題の再現 = 規則が要ることの確認)
#     (3) vmax でも海側(河口砂州・海浜)では波が働く: 波なしとの差の総量が VSEA 以上
#     (4) 無効時のビット一致と MPI の一致は Run.sh / Run_MPI.sh の cmp
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, DX, XL, JC1, JC2

XM = 15.0        # 河口からこれ以上上流の河道を見る (m)(河口直近は水理的な帰還で数 cm 動く)
TOL = 0.05       # (1) の許容 (m)(実測 0.014 m。規則なしは 1.1 m)
RATIO = 0.05     # (1) の novmax に対する比の上限(実測 0.012)
DEMO = 0.5       # (2) の下限 (m)
VSEA = 10.0      # (3) の下限 (m3)

x = (np.arange(NX) + 0.5) * DX
X = np.broadcast_to(x[None, :], (NY, NX))
ch = np.zeros((NY, NX), bool); ch[JC1:JC2, :] = True; ch &= (X < XL - XM)
sea = (X >= XL)

def last(tag):
    d = "result_%s" % tag
    n = max(int(f[1:5]) for f in os.listdir(d) if f.startswith("Z") and f[1:5].isdigit() and int(f[1:5]) < 9000)
    return np.loadtxt(os.path.join(d, "Z%04d.txt" % n))

zn = last("nowave"); za = last("novmax"); zv = last("vmax")
ok = True
d1 = np.abs(zv - zn)[ch].max()
d2 = np.abs(za - zn)[ch].max()
g1 = d1 < TOL and d1 < RATIO * d2
print("(1) vmax: 河口から %.0f m 以上上流の河道で |Z − Z_nowave| 最大 %.4f m (許容 %.2f、規則なしの %.3f 倍 < %.2f) : %s"
      % (XM, d1, TOL, d1 / max(d2, 1e-12), RATIO, "PASS" if g1 else "FAIL"))
ok = ok and g1
g2 = d2 > DEMO
print("(2) novmax: 同区間で最大 %.3f m (> %.1f。規則なしでは河道の淵が波の源になり早瀬に沿岸漂砂が働く) : %s" % (d2, DEMO, "PASS" if g2 else "FAIL"))
ok = ok and g2
v3 = np.abs(zv - zn)[sea].sum() * DX * DX
g3 = v3 > VSEA
print("(3) vmax: 海側で波による地形変化 Σ|Z − Z_nowave| dA = %.1f m³ (> %.0f) : %s" % (v3, VSEA, "PASS" if g3 else "FAIL"))
ok = ok and g3
print("== wave_river 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
