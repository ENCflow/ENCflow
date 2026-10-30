#!/usr/bin/env python3
"""test/gwtani の図を figs/gwtani.png に描く(事前に ./Run.sh を実行しておく。引数 en で英語版を en/figs/ に)。
谷(Tani)型のシナリオ: 一定の雨を受ける急勾配の斜面で、(左)各セルの飽和の時刻と鉛直到達時間
T_v = d·sy/r、(中)定常の地下水の飽和帯厚と運動学的な予測 h = g·x・土層厚、(右)飽和したセルの
割合の時間変化。値は Check_gwtani.py と同じ読み方・定数。
"""
import math, os, struct, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
EN = "en" in sys.argv[1:]
def T(ja, en): return en if EN else ja
FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

NY, NT, DY, SB, SY, R, DT = 40, 41, 5.0, 0.5, 0.2, 10.0 / 1000 / 3600, 2.0
CASES = [("uni_thin", "uni_thin", 1e-3, "C0", "o", T("1: 一様に薄い d = 0.38 m", "1: uniformly thin d = 0.38 m")),
         ("uni_thick", "uni_thick", 1e-3, "C2", "s", T("2: 一様に厚い d = 2 m", "2: uniformly thick d = 2 m")),
         ("thin_toe", "thin_toe", 1e-3, "C3", "^", T("3: 下端へ薄く d = 3 → 0.3 m", "3: thinning downslope d = 3 → 0.3 m")),
         ("thin_toe_k2", "thin_toe", 5e-4, "C1", "v", T("4: 3 で K を半分", "4: case 3 with K halved"))]


def frames(resdir):
    out = []
    for line in open(os.path.join(resdir, "FILENUMBER.csv")):
        if line.startswith("#"):
            continue
        c = [v.strip() for v in line.split(",")]
        k, t = int(c[0]), float(c[2])
        if 0 < k < 9000:
            out.append((k, t))
    return out


def load(name):
    data = []
    for k, t in frames("result_" + name):
        with open(os.path.join("result_" + name, "Hg%04d.bil" % k), "rb") as f:
            data.append((t, np.array(struct.unpack("<%df" % NT, f.read()))[:NY]))
    return data


fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
x = (np.arange(NY) + 1) * DY                       # セル i の下流側の辺までの分水界からの距離(定常解の x)
xc = (np.arange(NY) + 0.5) * DY                    # セル中心
for name, geom, k, col, mk, lab in CASES:
    sd = np.loadtxt(os.path.join("data_gwtani", "sd_%s.txt" % geom))[:NY]
    cap = sd * SY
    data = load(name)
    g = (SB - math.sqrt(SB * SB - 4 * R / k)) / 2
    # (左)飽和の時刻: 飽和の直前の出力から速度 r で延ばした時刻(セル 1〜39)
    ts = np.full(NY, np.nan)
    for i in range(NY - 1):
        prev = None
        for t, a in data:
            if a[i] >= cap[i] - R * DT:
                if prev is not None:
                    ts[i] = min(max(prev[0] + (cap[i] - prev[1]) / R, prev[0]), t)
                break
            prev = (t, a[i])
    axes[0].plot(xc, ts / 3600, mk, color=col, ms=5, label=lab)
    if name in ("uni_thin", "thin_toe"):
        axes[0].plot(xc, cap / R / 3600, "-", color=col, lw=1, alpha=0.7)
    # (中)定常の飽和帯厚と予測
    a = data[-1][1]
    axes[1].plot(xc, a / SY, mk, color=col, ms=4, label=lab)
    if name in ("uni_thin", "thin_toe"):
        axes[1].plot(xc, sd, "-", color=col, lw=1, alpha=0.6)
    if name in ("thin_toe", "thin_toe_k2"):
        axes[1].plot(x, g * x, ":", color=col, lw=1.2)
    # (右)飽和したセル(1〜39)の割合
    frac = [np.mean(v[:NY - 1] >= cap[:NY - 1] - R * DT) for t, v in data]
    axes[2].plot([t / 3600 for t, v in data], frac, "-", color=col, lw=1.6, label=lab)

axes[0].set_xlabel(T("分水界からの距離 (m)", "distance from the divide (m)"))
axes[0].set_ylabel(T("飽和の時刻 (h)", "time of saturation (h)"))
axes[0].set_title(T("飽和の時刻(記号)と鉛直到達時間 T_v = d·sy/r(線)", "time of saturation (markers) and T_v = d·sy/r (lines)"), fontsize=9)
axes[0].set_xlim(0, 200); axes[0].set_ylim(0, 40); axes[0].grid(alpha=0.3); axes[0].legend(fontsize=7, loc="upper left")
axes[1].set_xlabel(T("分水界からの距離 (m)", "distance from the divide (m)"))
axes[1].set_ylabel(T("飽和帯厚 h = hg/sy (m)", "saturated thickness h = hg/sy (m)"))
axes[1].set_title(T("66.7 h(定常): 記号 = 計算、点線 = 予測 h = g·x、実線 = 土層厚", "66.7 h (steady): markers = model, dotted = h = g·x, solid = soil depth"), fontsize=9)
axes[1].set_xlim(0, 200); axes[1].set_ylim(0, 2.2); axes[1].grid(alpha=0.3)
axes[2].set_xlabel(T("経過時間 (h)", "time (h)"))
axes[2].set_ylabel(T("飽和したセルの割合(セル 1〜39)", "fraction of saturated cells (1-39)"))
axes[2].set_title(T("飽和域の広がり(地表に雨が出る範囲)", "growth of the saturated area (where rain runs off)"), fontsize=9)
axes[2].set_xlim(0, 66.7); axes[2].set_ylim(-0.02, 0.75); axes[2].grid(alpha=0.3); axes[2].legend(fontsize=7, loc="upper left")
fig.suptitle(T("谷(Tani)型のシナリオ(gwtani): 基盤の勾配 0.5・長さ 200 m の斜面に一定の雨 10 mm/h。"
               "飽和の時刻は鉛直浸透で、飽和の範囲は側方流で決まる",
               "Tani-type scenario (gwtani): constant rain of 10 mm/h on a 200 m slope with bedrock gradient 0.5. "
               "Vertical infiltration sets when cells saturate; lateral flow sets where"), fontsize=10)
fig.tight_layout()
fig.savefig(f"{FIGDIR}/gwtani.png", dpi=110)
plt.close(fig)
print("wrote", f"{FIGDIR}/gwtani.png")
