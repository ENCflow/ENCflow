#!/usr/bin/env python3
"""nhwave: README 用の図を figs/ に描く(走査 scan/ と test/nhwave_nh/result を読む)

  使い方: ./Dispersion.py と ../nhwave_nh/Run.sh の後に ./Fig.py
  figs/standing_wave.png  プローブ 1 の水位 η(t)/a0(静水圧 vs 非静水圧、h0 = 8 m、kH = 1)
  figs/dispersion.png     位相速度比 c/c_cont 対 kH(計測値と理論曲線)
  計算本体の外(方針 10)。numpy + matplotlib。
"""
import os, math, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from Dispersion import measure_period, enc_lambda_walls, G, LX, NX, M

plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e3e2dd", "grid.linewidth": 0.6,
                     "lines.linewidth": 1.6})
C_NH, C_HY, C_TH = "#2a78d6", "#eb6834", "#6b6a66"

def probe(csv):
    t, h = [], []
    for line in open(csv):
        if line.startswith("#"): continue
        c = [float(x) for x in line.split(",")]
        t.append(c[0] * 3600.0); h.append(c[3])
    t = np.array(t); h = np.array(h)
    return t, h - h.mean()

def fig_standing(out):
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    for csv, lab, col in [("result/probes/probe0001.csv", "静水圧(T = 5.66 s)", C_HY),
                          ("../nhwave_nh/result/probes/probe0001.csv", "非静水圧 1 層(T = 6.33 s)", C_NH)]:
        if not os.path.exists(csv): continue
        t, eta = probe(csv)
        a0 = np.abs(eta[:5]).max()
        ax.plot(t, eta / a0, color=col, label=lab)
    ax.set_xlim(0, 40); ax.set_ylim(-1.3, 1.9)
    ax.set_yticks([-1, -0.5, 0, 0.5, 1])
    ax.set_xlabel("t (s)"); ax.set_ylabel("η / a₀(プローブ 1、隅)")
    ax.set_title("正方水槽の定在波(h₀ = 8 m、波長 50 m、kH = 1.0)", fontsize=10, loc="left")
    ax.legend(loc="upper left", ncol=2, frameon=False, fontsize=9)
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)

def fig_dispersion(out):
    dx = LX / NX
    kx = M * math.pi / LX
    pts = {"hydro": [], "nh": []}
    for d in sorted(glob.glob("scan/*")):
        name = os.path.basename(d)
        csv = os.path.join(d, "result", "probes", "probe0001.csv")
        if not os.path.exists(csv): continue
        nh = name.startswith("nh_")
        core = name[3:] if nh else name
        parts = core.split("_")
        if nh:
            if len(parts) != 3 or parts[2] != "s2": continue          # nh_{mode}_h{h0}_s2 だけ
        else:
            if not name.endswith("_dt0.02_rk1_hc0"): continue         # 既定 dt・適応 RK あり
        mode = parts[0]; h0 = float(parts[1][1:])
        ky = kx if mode == "xy" else 0.0
        k = math.hypot(kx, ky)
        T, _, n = measure_period(csv)
        if not np.isfinite(T): continue
        Tc = 2 * math.pi / (math.sqrt(G * h0) * k)
        pts["nh" if nh else "hydro"].append((mode, k * h0, Tc / T))
    kH = np.linspace(0.05, 3.0, 300)
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.plot(kH, np.sqrt(np.tanh(kH) / kH), color=C_TH, lw=1.4, label="厳密 ω² = gk tanh kH")
    ax.plot(kH, 1.0 / np.sqrt(1.0 + kH**2 / 4.0), color=C_NH, lw=1.2, ls="--", label="1 層 NH の目標 ω² = gHk²/(1+k²H²/4)")
    ax.axhline(1.0, color=C_HY, lw=1.2, ls="--", label="静水圧(分散なし)")
    for key, col, lab in [("hydro", C_HY, "計測: 静水圧 ENC"), ("nh", C_NH, "計測: 非静水圧 ENC")]:
        for mode, mk in [("x", "o"), ("xy", "s")]:
            p = [(a, b) for m, a, b in pts[key] if m == mode]
            if not p: continue
            p = np.array(sorted(p))
            ax.plot(p[:, 0], p[:, 1], mk, ms=7, mfc=col, mec="white", mew=1.2, ls="none",
                    label=f"{lab}({'x' if mode == 'x' else '対角'}モード)")
    ax.set_xlim(0, 3.0); ax.set_ylim(0.45, 1.08)
    ax.set_xlabel("kH"); ax.set_ylabel("位相速度比  c / √(gH)")
    ax.set_title("分散関係(Δx = 1 m、kΔx = 0.13〜0.18。h₀ を変えて kH を振る)", fontsize=10, loc="left")
    ax.legend(loc="lower left", frameon=False, fontsize=8, ncol=2)
    fig.tight_layout(); fig.savefig(out, dpi=150); plt.close(fig)

if __name__ == "__main__":
    os.makedirs("figs", exist_ok=True)
    fig_standing("figs/standing_wave.png")
    fig_dispersion("figs/dispersion.png")
    print("written: figs/standing_wave.png figs/dispersion.png")
