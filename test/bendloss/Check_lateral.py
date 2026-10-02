#!/usr/bin/env python3
"""横流入つき 1 セル水路の定常水面形を、空間変化流(Chow 1959, Ch.12)の
常微分方程式と比べる(developer.md §68.17)。

  python3 Check_lateral.py lat2 [_s1 _s3 ...]
最終出力の H, m を河道行で読み、Q(x) = m·dy から横流入 q_L を測り、
  dh/dx = (S0 − Sf − c·Q·q_L/(g A²)) / (1 − Fr²)
を上流側 x0 の ENC 水深を初期値として下流へ積分する(超臨界)。
  c = 2: 横流入が流下方向の運動量を持たない(物理的に正しい)
  c = 1: 横流入が局所流速で合流する(運動量の損失なし。非保存形の挙動)
"""
import glob, math, os, re, sys
import numpy as np
G, DX, S0, N = 9.8, 10.0, 0.02, 0.03
kind = sys.argv[1]; sufs = sys.argv[2:] or ['_s1', '_s3']
jc = {'lat1': 3, 'lat2': 11, 'lat1r': 3, 'lat2r': 11}[kind]

def last(d, pre):
    fs = sorted(f for f in glob.glob(os.path.join(d, pre + "[0-9][0-9][0-9][0-9].txt")) if int(re.findall(r"(\d{4})\.txt", f)[0]) < 9000)
    return np.loadtxt(fs[-1])

def ode(h0, x, Q, qL, c):
    """RK4 で dh/dx を積分(超臨界: 下流へ)。Q(x), qL は配列/定数"""
    h = np.empty_like(x); h[0] = h0
    def f(xx, hh, QQ):
        A = DX * hh; Fr2 = QQ**2 / (G * DX**2 * hh**3); Sf = N**2 * QQ**2 / (DX**2 * hh**(10/3))
        return (S0 - Sf - c * QQ * qL / (G * A**2)) / (1 - Fr2)
    for i in range(1, len(x)):
        dx = x[i] - x[i-1]; Qm = 0.5 * (Q[i-1] + Q[i])
        k1 = f(x[i-1], h[i-1], Q[i-1]); k2 = f(x[i-1]+dx/2, h[i-1]+dx/2*k1, Qm)
        k3 = f(x[i-1]+dx/2, h[i-1]+dx/2*k2, Qm); k4 = f(x[i], h[i-1]+dx*k3, Q[i])
        h[i] = h[i-1] + dx/6 * (k1 + 2*k2 + 2*k3 + k4)
    return h

for suf in sufs:
    d = f'result_{kind}{suf}'
    H = last(d, 'H')[jc-1]; M = last(d, 'm')[jc-1]
    x = (np.arange(400) + 0.5) * DX
    Q = M * DX
    i0, i1 = 20, 380                       # 流入境界・下流端の影響を避けた区間
    qL = np.polyfit(x[i0:i1], Q[i0:i1], 1)[0]
    Qf = Q[i0] + qL * (x[i0:i1] - x[i0])   # 線形フィットした Q(x)
    print(f'=== {d}: Q {Q[i0]:.1f} → {Q[i1-1]:.1f} m³/s, q_L = {qL:.4f} m²/s (fit), '
          f'Q(x) linear-fit rms {np.sqrt(np.mean((Q[i0:i1]-Qf)**2)):.2f} m³/s')
    for c, lab in ((2, 'c=2 zero-momentum inflow (physical)'), (1, 'c=1 inflow at local velocity')):
        ha = ode(H[i0], x[i0:i1], Qf, qL, c)
        rel = (H[i0:i1] - ha) / ha
        print(f'  vs ODE {lab:40s}: mean rel. depth error {100*rel.mean():+6.2f}%  (x=1 km {100*rel[80]:+6.2f}%, 2 km {100*rel[180]:+6.2f}%, 3 km {100*rel[280]:+6.2f}%)')
    hn0 = (Q[i0] / DX * N / math.sqrt(S0))**0.6
    print(f'  ENC h at x0 {H[i0]:.3f} (normal depth for Q(x0): {hn0:.3f}); h at 1/2/3 km: {H[i0+80]:.3f} / {H[i0+180]:.3f} / {H[i0+280]:.3f}; Fr at 3 km {Q[i0+280]/DX/H[i0+280]/math.sqrt(G*H[i0+280]):.2f}')
    # ENC の状態によらない参照: x0 の等流水深から c=2 で積分した物理解に対する比
    hp = ode(hn0, x[i0:i1], Qf, qL, 2)
    print(f'  ENC/physical(c=2 from normal depth) depth ratio at 1/2/3 km: {H[i0+80]/hp[80]:.3f} / {H[i0+180]/hp[180]:.3f} / {H[i0+280]/hp[280]:.3f}; physical h {hp[80]:.3f} / {hp[180]:.3f} / {hp[280]:.3f}')
