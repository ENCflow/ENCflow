#!/usr/bin/env python3
"""test/bendloss の主要 2 実験を図にする。

  python3 Fig.py        → figs/bendloss.png

前提: ./Run.sh "" _s3 で result_{straight,zigzag}{,_s3} が、
      python3 Make_channel.py wave10 と ./encflow param_wave_{nolev,dyn}_s{1,3}.txt
      で result_wave_* があること(README の「実行」参照)。
左: 直線 / 折れ線水路の定常水深の路長分布(スキーム 1 と 3)。屈曲位置を縦線で示す。
右: 直線 rw 河道の洪水波(40 → 200 → 40 m³/s)の 3.8 km でのハイドログラフ。
    開口補正なし(nolev)と動的開口補正(dyn)× スキーム 1 / 3。
"""
import csv, glob, math, os, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
here = os.path.dirname(os.path.abspath(__file__))
G, DX, S, N, Q = 9.8, 10.0, 0.005, 0.03, 4.0
hn = (Q * N / math.sqrt(S)) ** 0.6

def last(d, pre):
    fs = sorted(f for f in glob.glob(os.path.join(here, d, pre + "[0-9][0-9][0-9][0-9].txt"))
                if int(re.findall(r"(\d{4})\.txt", f)[0]) < 9000)
    return np.loadtxt(fs[-1])

def profile(kind, suf):
    H = last(f"result_{kind}{suf}", "H")
    path = list(csv.DictReader(open(os.path.join(here, f"path_{kind}.csv"))))
    s = np.array([int(r["k"]) * DX for r in path]); h = np.array([H[int(r["j"]) - 1][int(r["i"]) - 1] for r in path])
    return s / 1000, h

fig, axs = plt.subplots(1, 2, figsize=(14, 4.6))
ax = axs[0]
for suf, lab, col in [("", "スキーム 1", "C0"), ("_s3", "スキーム 3(既定)", "C3")]:
    try:
        s, h = profile("straight", suf); ax.plot(s, h, "-", color=col, lw=1.5, label=f"直線 {lab}")
        s, h = profile("zigzag", suf); ax.plot(s, h, "--", color=col, lw=1.5, label=f"折れ線 {lab}")
    except (IndexError, FileNotFoundError):
        pass
for k in range(1, 5):
    ax.axvline(k * 0.8, color="gray", lw=0.8, ls=":")
ax.axhline(hn, color="k", lw=1, ls="-.", label=f"Manning 等流 h_n = {hn:.3f} m")
ax.set_xlabel("路長 s (km)"); ax.set_ylabel("水深 h (m)"); ax.set_xlim(0, 4); ax.set_ylim(1.0, 2.2)
ax.grid(alpha=0.4); ax.legend(fontsize=8.5, ncol=2, loc="lower center")
ax.set_title("1 セル幅水路: 直線 vs 90° 屈曲 4 回(点線 = 屈曲位置)")

ax = axs[1]
peaks = {}
for d, lab, ls, col in [("result_wave_nolev_s1", "開口補正なし, スキーム 1", "--", "C0"), ("result_wave_nolev_s3", "開口補正なし, スキーム 3", "--", "C3"),
                        ("result_wave_dyn_s1", "動的開口補正, スキーム 1", "-", "C0"), ("result_wave_dyn_s3", "動的開口補正, スキーム 3", "-", "C3")]:
    f = os.path.join(here, d, "fluxes", "flux0003.csv")
    if not os.path.exists(f): continue
    t, q = np.loadtxt(f, delimiter=",", comments="#", usecols=(1, 2), unpack=True, ndmin=1)
    if t.size < 2: continue
    ax.plot(t, q, ls, color=col, lw=1.6, label=lab); peaks[lab] = q.max()
f0 = os.path.join(here, "result_wave_dyn_s1", "fluxes", "flux0001.csv")
if os.path.exists(f0):
    t, q = np.loadtxt(f0, delimiter=",", comments="#", usecols=(1, 2), unpack=True)
    ax.plot(t, q, "k:", lw=1.2, label="0.4 km(上流端近く)")
ax.set_xlabel("時間 (min)"); ax.set_ylabel("流量 Q (m³/s)"); ax.set_xlim(55, 120)
ax.grid(alpha=0.4); ax.legend(fontsize=8.5)
ax.set_title("直線 rw 河道の洪水波: x = 3.8 km のハイドログラフ")
fig.suptitle("test/bendloss — ラスタ河道の移流スキームと開口補正", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(here, "figs", "bendloss.png"), dpi=110, bbox_inches="tight")
print("figs/bendloss.png")
for k, v in peaks.items(): print(f"peak at 3.8 km: {k}: {v:.1f}")
