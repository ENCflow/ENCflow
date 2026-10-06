#!/usr/bin/env python3
"""test/dambreak の図を figs/*.png に描く。

事前に各ケースを実行し、Check_stoker.py で stoker.csv を書いておく
(README の「実行」節。result/ は ./Run.sh が、他は
RESDIR=<dir> PARAM=<param> python3 Check_stoker.py が書く)。

  python3 Fig.py

- figs/profile.png : t = 30 s の中央行の h, u。既定(スキーム 3)と旧スキーム 1、
                     動的振り替え f_opening_dynamic=2 の有無、Stoker 解析解
- figs/incised.png : 1 セル幅・2 セル幅水路(マスク壁・掘込地形)の段波位置誤差と
                     段波背後の越え高さ(result_{m1,m2,ch1,ch2,...}_s{1,3}_d{0,2}[_c1])
"""
import csv, glob, os, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

HL, HR = 10.0, 1.0
os.makedirs("figs", exist_ok=True)


def load(d):
    p = os.path.join(d, "stoker.csv")
    if not os.path.isfile(p):
        return None
    rows = list(csv.DictReader(open(p)))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def bore_x(x, h, hm):
    """段波位置: 右から見て h が (hm + hr)/2 を初めて超える位置(線形補間)"""
    lev = 0.5 * (hm + HR)
    idx = np.where(h > lev)[0]
    if len(idx) == 0:
        return np.nan
    i = idx[-1]
    if i + 1 >= len(x):
        return x[i]
    return x[i] + (lev - h[i]) * (x[i + 1] - x[i]) / (h[i + 1] - h[i])


def plateau(h_ana):
    """解析解の平坦区間の水深 hm(最頻値)"""
    v = h_ana[(h_ana > HR + 0.5) & (h_ana < HL - 0.5)]
    return np.median(v)


# ---- 図 1: 広い水路の断面 ----
cases = [("result_scheme1", "スキーム 1(旧既定: セル中心勾配、非保存形)", "C0", "-"),
         ("result_dyn_s1", "スキーム 1 + 動的振り替え(全エッジ)", "C0", "--"),
         ("result", "スキーム 3(既定: 運動量保存形 + MUSCL)= param.txt", "C3", "-"),
         ("result_dyn_s3", "スキーム 3 + 動的振り替え(全エッジ)", "C3", "--")]
data = [(load(d), lab, c, ls) for d, lab, c, ls in cases]
ref = next(dd for dd, *_ in data if dd is not None)
fig, axes = plt.subplots(3, 1, figsize=(9, 10))
for ax, key, akey, ylab, xr, yr in [
        (axes[0], "h_num", "h_ana", "水深 h (m)", (150, 850), None),
        (axes[1], "u_num", "u_ana", "流速 u (m/s)", (150, 850), None),
        (axes[2], "h_num", "h_ana", "水深 h (m)、段波付近の拡大", (640, 840), (0.5, 7.5))]:
    ax.plot(ref["x"], ref[akey], "k", lw=2.2, label="Stoker 解析解", zorder=5)
    for dd, lab, c, ls in data:
        if dd is not None:
            ax.plot(dd["x"], dd[key], color=c, ls=ls, lw=1.4, label=lab)
    ax.set_xlim(*xr)
    if yr:
        ax.set_ylim(*yr)
    ax.set_ylabel(ylab)
    ax.grid(alpha=0.3)
axes[0].set_title("湿潤床ダム破壊(hl = 10 m、hr = 1 m、Δx = 2 m)の t = 30 s の中央行", fontsize=11)
axes[0].legend(fontsize=8, loc="upper right")
axes[2].set_xlabel("x (m)")
fig.tight_layout()
fig.savefig("figs/profile.png", dpi=110)
plt.close(fig)

# ---- 図 2: 1 セル・2 セル水路 ----
# 数値は Check_stoker.py の出力(段波位置の誤差 %、段波背後の越え高さ)をそのまま使う
import subprocess
rows = []
for d in sorted(glob.glob("result_m[12]_s[13]_d[02]*") + glob.glob("result_ch[12]*_s[13]_d[02]*")):
    m = re.match(r"result_(\w+?)_s(\d)_d(\d)(_c1)?$", d)
    p = "param_%s_s%s_d%s%s.txt" % (m.group(1), m.group(2), m.group(3), m.group(4) or "")
    if not os.path.isfile(os.path.join(d, "H0003.txt")) and not glob.glob(os.path.join(d, "H*.txt")):
        continue
    out = subprocess.run(["python3", "Check_stoker.py"], env={**os.environ, "RESDIR": d, "PARAM": p},
                         capture_output=True, text=True).stdout
    me = re.search(r"err [+-][\d.]+ m = ([+-][\d.]+)% of travel", out)
    mo = re.search(r"overshoot h-hm : ([+-][\d.]+) m", out)
    if not (me and mo):
        continue
    rows.append((m.group(1), int(m.group(2)), int(m.group(3)), bool(m.group(4)), float(me.group(1)), float(mo.group(1))))
if rows:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    geoms = [g for g in ["m1", "m2", "ch1", "ch2", "ch1z12", "ch2z12"] if any(r[0] == g for r in rows)]
    labels = {"m1": "1 セル\nマスク壁", "m2": "2 セル\nマスク壁", "ch1": "1 セル\n掘込 z=20",
              "ch2": "2 セル\n掘込 z=20", "ch1z12": "1 セル\n掘込 z=12", "ch2z12": "2 セル\n掘込 z=12"}
    combos = [(1, 0, False, "スキーム 1", "C0", 0.6), (1, 2, False, "1 + 振り替え", "C0", 1.0),
              (3, 0, False, "スキーム 3", "C3", 0.6), (3, 2, False, "3 + 振り替え", "C3", 1.0)]
    w = 0.2
    for k, (s, dyn, cap, lab, c, al) in enumerate(combos):
        for ax, col in zip(axes, [4, 5]):
            vals = []
            for g in geoms:
                r = [r for r in rows if r[0] == g and r[1] == s and r[2] == dyn and r[3] == cap]
                if not r:   # 掘込は発散するケースがあり、cap 付きだけ揃っていることがある
                    r = [r for r in rows if r[0] == g and r[1] == s and r[2] == dyn and r[3]]
                vals.append(r[0][col] if r else np.nan)
            ax.bar(np.arange(len(geoms)) + (k - 1.5) * w, vals, w, color=c, alpha=al, label=lab)
    axes[0].axhline(0, color="k", lw=0.8)
    axes[0].set_ylabel("段波位置の誤差 (%、進行距離に対して)")
    axes[1].set_ylabel("段波背後の越え高さ h_max − hm (m)")
    for ax in axes:
        ax.set_xticks(np.arange(len(geoms)))
        ax.set_xticklabels([labels[g] for g in geoms], fontsize=9)
        ax.grid(alpha=0.3, axis="y")
    axes[0].legend(fontsize=8)
    fig.suptitle("1 セル幅・2 セル幅水路でのダム破壊(§68.15。広い水路: スキーム 1 −15.5% / 3.2 m、スキーム 3 +1.1% / 0.04 m)", fontsize=10)
    fig.tight_layout()
    fig.savefig("figs/incised.png", dpi=110)
    plt.close(fig)
    print("geom  scheme dyn cap  bore_err%  overshoot_m")
    for r in rows:
        print("%-7s %d %d %d  %+7.2f  %6.2f" % r)
