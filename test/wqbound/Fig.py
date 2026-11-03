#!/usr/bin/env python3
"""test/wqbound の図を figs/wqbound.png に描く(事前に ./Run.sh を実行しておく)。
左: param.txt の台帳(系外との出入りの累積と地表の質量、閉合残差)。
右: param_rev.txt の水路の濃度の縦断(水位規定セルからの逆流の前後)。
引数 en で英語版を en/figs/wqbound.png に描く。
"""
import csv
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)


def ledger(d):
    rows = list(csv.reader(open(os.path.join(d, "wq.csv"))))
    head = rows[0]
    return {k: np.array([float(r[i]) for r in rows[1:]]) for i, k in enumerate(head)}


fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))

w = ledger("result")
t = w["time_s"] / 60.0
for col, lab, st in [("in_edge_g", T("区間流入から (in_edge)", "from the inflow segment (in_edge)"), "-"),
                     ("in_point_g", T("点源 (in_point)", "point source (in_point)"), "-"),
                     ("out_stage_g", T("水位規定セルへ (out_stage)", "to the water-level cell (out_stage)"), "--"),
                     ("out_sea_g", T("海セルへ (out_sea)", "to sea cells (out_sea)"), "--"),
                     ("out_edge_g", T("北の辺から (out_edge)", "through the north edge (out_edge)"), "--"),
                     ("mass_surface_g", T("地表の質量 (mass_surface)", "surface mass (mass_surface)"), ":")]:
    ax[0].plot(t, w[col] / 1000.0, st, lw=1.6, label=lab)
res = (w["in_point_g"] + w["in_edge_g"] + w["in_stage_g"] - w["out_sea_g"] - w["out_edge_g"]
       - w["out_stage_g"] - w["mass_surface_g"])
scale = max((w["in_point_g"] + w["in_edge_g"]).max(), 1.0)
ax[0].set_xlabel(T("時間 (分)", "time (min)"))
ax[0].set_ylabel(T("累積・現在の質量 (kg)", "cumulative / current mass (kg)"))
ax[0].set_title(T("(a) 台帳の閉合(param.txt)", "(a) ledger closure (param.txt)"), fontsize=10)
ax[0].text(0.02, 0.97, T(f"閉合残差 / 入力 ≤ {np.abs(res).max() / scale:.1e}",
                         f"closure residual / input ≤ {np.abs(res).max() / scale:.1e}"),
           transform=ax[0].transAxes, va="top", fontsize=8.5)
ax[0].legend(fontsize=8, loc="center left", bbox_to_anchor=(0.0, 0.62))
ax[0].grid(alpha=0.3)

x = (np.arange(30) + 0.5) * 10.0
for n, lab, st in [(0, T("0 分(初期)", "0 min (initial)"), ":"),
                   (6, T("60 分(押し出した後)", "60 min (after the push)"), "--"),
                   (8, T("80 分(逆流中)", "80 min (reverse flow)"), "-"),
                   (12, T("120 分", "120 min"), "-")]:
    c = np.loadtxt(os.path.join("result_rev", f"C{n:04d}.txt")).ravel()
    ax[1].plot(x[:29], c[:29], st, lw=1.6, label=lab)
ax[1].axhline(0.5, color="0.5", lw=0.8)
ax[1].text(5, 0.52, T("境界濃度 0.5 mg/L", "boundary concentration 0.5 mg/L"), fontsize=8.5, color="0.4")
ax[1].set_xlabel(T("西端からの距離 (m)(東端 300 m が水位規定セル)",
                   "distance from the west end (m; the water-level cell is at 300 m)"))
ax[1].set_ylabel(T("濃度 C (mg/L)", "concentration C (mg/L)"))
ax[1].set_ylim(0, 1.1)
ax[1].set_title(T("(b) 水位規定セルからの逆流(param_rev.txt)",
                  "(b) reverse flow from the water-level cell (param_rev.txt)"), fontsize=10)
ax[1].legend(fontsize=8, loc="lower left")
ax[1].grid(alpha=0.3)
fig.tight_layout()
out = os.path.join(FIGDIR, "wqbound.png")
fig.savefig(out, dpi=110)
print("wrote", out)
