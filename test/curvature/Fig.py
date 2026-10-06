#!/usr/bin/env python3
"""test/curvature の図を figs/*.png に描く(事前に ./Run.sh を実行しておく)。

  python3 Fig.py

- figs/profile.png : 地形(直線斜面 A → 凹円弧 → 直線斜面 B)と、定常の混合体流動深 h_t
                     (全行平均)の縦断。曲率項 off / on と、定常 1 次元 ODE の解(off / on)、
                     直線部の Voellmy 等流深。下段は on − off の厚化
Check_curvature.py の読み込み・ODE 関数を使う(検定の出力も一緒に表示される)。
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs("figs", exist_ok=True)

sys.argv = [sys.argv[0], "save_off", "save_on"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Check_curvature.py は読み込み時に検定を実行して sys.exit するので、exit を一時的に無効にして取り込む
from types import SimpleNamespace
_here = os.path.dirname(os.path.abspath(__file__))
_ns = {"__name__": "Check_curvature", "__file__": os.path.join(_here, "Check_curvature.py")}
_exit = sys.exit
sys.exit = lambda *a: None
exec(compile(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Check_curvature.py"), encoding="utf-8").read(), "Check_curvature.py", "exec"), _ns)
sys.exit = _exit
cc = SimpleNamespace(**_ns)
import make_init as mi                # noqa: E402

x = (np.arange(mi.NX) + 0.5) * mi.DX
z = np.array([mi.z_of(xx) for xx in x])
ht_off = np.array(cc.load_ht("save_off"))
ht_on = np.array(cc.load_ht("save_on"))
hnA, hnB = cc.hnorm(mi.ST1), cc.hnorm(mi.ST2)
# ODE: 窓 WA の等流深から下流へ(Check_curvature と同じ出発点の流儀)
xs0, hs0 = cc.ode_profile(False, cc.WA[0], hnA, mi.LX)
xs1, hs1 = cc.ode_profile(True, cc.WA[0], hnA, mi.LX)

fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True, gridspec_kw={"height_ratios": [1.2, 1.4, 1]})
ax = axes[0]
ax.plot(x, z, "k", lw=1.5, label="地形 z")
ax.axvspan(mi.XA, mi.XB, color="0.9", label=f"凹円弧 R = {mi.R:.0f} m")
ax.set_ylabel("z (m)")
ax.set_title(f"直線斜面 A (tanθ = {mi.ST1}) → 凹円弧 → 直線斜面 B (tanθ = {mi.ST2})。Voellmy μ = {cc.MU}, ξ = {cc.XI:.0f}、q_m = {cc.QM:.2f} m²/s", fontsize=10)
ax.legend(fontsize=8)
ax.grid(alpha=0.3)
ax = axes[1]
ax.axvspan(mi.XA, mi.XB, color="0.9")
ax.plot(x, ht_off, "C0o", ms=2.5, label="ENCflow 曲率項 off(全行平均)")
ax.plot(x, ht_on, "C3o", ms=2.5, label="ENCflow 曲率項 on")
ax.plot(xs0, hs0, "C0-", lw=1, label="定常 ODE off")
ax.plot(xs1, hs1, "C3-", lw=1, label="定常 ODE on")
ax.axhline(hnA, color="0.5", ls=":", lw=1); ax.axhline(hnB, color="0.5", ls=":", lw=1)
ax.text(2, hnA, f"等流深 A {hnA:.3f} m", fontsize=8, va="bottom", color="0.4")
ax.text(mi.LX - 60, hnB, f"等流深 B {hnB:.3f} m", fontsize=8, va="bottom", color="0.4")
ax.set_ylabel("混合体流動深 h_t (m)")
ax.set_ylim(0, max(ht_off.max(), ht_on.max()) * 1.3)
ax.legend(fontsize=8, ncol=2)
ax.grid(alpha=0.3)
ax = axes[2]
ax.axvspan(mi.XA, mi.XB, color="0.9")
ax.plot(x, ht_on - ht_off, "C2o-", ms=2.5, lw=0.8, label="ENCflow on − off")
ax.plot(xs0, np.interp(xs0, xs1, hs1) - np.array(hs0), "k-", lw=1, label="ODE on − off")
ax.set_xlabel("x (m)")
ax.set_ylabel("厚化 (m)")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("figs/profile.png", dpi=110)
plt.close(fig)
print("figs/profile.png written")
