#!/usr/bin/env python3
"""test/vchannel の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py        # 日本語版 → figs/
  python3 Fig.py en     # 英語版   → en/figs/

- figs/vchannel.png : 20 秒後の、沢筋方向の流速の横断分布(流動深で重み付けた 5 m 幅の平均)。厳密解と、
                      3 つの向き(0°・22.5°・45°)の計算。Voellmy 則・既定、Voellmy 則・f_opening_dynamic = 0、水・既定
"""
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import make_init as M
import Check_vchannel as C   # 読み込み・厳密解・流量の比

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

N, DX = M.N, M.DX


def lateral(cfg, name, theta, dn=5.0):
    """区間の中央の、横断方向の分布: (n のビンの中心, 流動深の平均, 沢筋方向の流速)。"""
    rdir = "result_%s_%s" % (cfg, name)
    k, t = C.last_output(rdir)

    def grid(nm):
        a = np.fromfile(os.path.join(rdir, "%s%04d.bil" % (nm, k)), "<f4").reshape(N, N)
        return a[::-1].astype(float)          # 行 0 を南端に
    d = grid("H") + (0.0 if cfg.startswith("w") else np.maximum(grid("Hs"), 0.0))
    u, v = grid("u"), grid("v")
    x = (np.arange(N) + 0.5) * DX - M.LDOM / 2
    X, Y = np.meshgrid(x, x)
    c, si = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    s, n = X * c + Y * si, -X * si + Y * c
    us = u * c - v * si                        # 出力の v は南向きが正
    m = (s >= C.WIN[0]) & (s <= C.WIN[1])
    edges = np.arange(-40.0, 40.0 + dn, dn)
    idx = np.digitize(n[m], edges) - 1
    ok = (idx >= 0) & (idx < len(edges) - 1)
    cnt = np.maximum(np.bincount(idx[ok], minlength=len(edges) - 1), 1)
    dm = np.bincount(idx[ok], weights=d[m][ok], minlength=len(edges) - 1) / cnt
    qm = np.bincount(idx[ok], weights=(d * us)[m][ok], minlength=len(edges) - 1) / cnt
    return edges[:-1] + dn / 2, dm, np.where(dm > 0.02, qm / np.maximum(dm, 1e-9), np.nan), t


RES = C.collect()
fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), sharey=False)
panels = (("vo", T("Voellmy 則・既定", "Voellmy law, default")),
          ("vo0", T("Voellmy 則・f_opening_dynamic = 0", "Voellmy law, f_opening_dynamic = 0")),
          ("w", T("水(マニング則)・既定", "water (Manning), default")))
marks = (("r0", 0.0, "o", "#1f77b4"), ("r22p5", 22.5, "s", "#2ca02c"), ("r45", 45.0, "^", "#d62728"))
for ax, (cfg, title) in zip(axes, panels):
    nn = np.linspace(-40.0, 40.0, 401)
    h0 = np.maximum(M.D - M.WALL * (np.sqrt(nn ** 2 + M.A ** 2) - M.A), 0.0)
    ue = np.array([C.u_exact(h, M.TEND, cfg) for h in h0])
    ax.plot(nn, np.where(h0 > 0, ue, np.nan), "k-", lw=1.6, label=T("厳密解", "exact"))
    for name, theta, mk, col in marks:
        nc, dm, us, t = lateral(cfg, name, theta)
        q = RES[(cfg, name)][0]
        ax.plot(nc, us, mk, color=col, ms=6, mfc="none", mew=1.4,
                label=T("%g°(流量の比 %.3f)" % (theta, q), "%g° (discharge ratio %.3f)" % (theta, q)))
    ax.set_title(title, fontsize=11)
    ax.set_xlabel(T("横断方向の距離 n (m)", "cross-channel distance n (m)"))
    ax.set_xlim(-40, 40)
    ax.set_ylim(0, None)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8.5, loc="lower center")
axes[0].set_ylabel(T("沢筋方向の流速 (m/s)", "along-channel velocity (m/s)"))
fig.suptitle(T("一様な V 字水路の、20 秒後の流速の横断分布(Δx = 5 m。線: 厳密解、印: 計算)",
               "Cross-channel velocity profile in a uniform V-channel after 20 s (Δx = 5 m; line: exact, symbols: computed)"),
             fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.94))
out = os.path.join(FIGDIR, "vchannel.png")
fig.savefig(out, dpi=130)
print("wrote", out)
