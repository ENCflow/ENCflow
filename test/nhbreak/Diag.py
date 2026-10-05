#!/usr/bin/env python3
"""nhbreak: 砕波遡上の過大の原因切り分け(developer.md §69.6)

  使い方: ./Diag.py --run [case ...]   param.txt / param_h.txt から派生ケースを作って走らせる
                                         (result_x_<case>/。u, v も出力。引数なしで全ケース)
          ./Diag.py [case ...]          既存の result_x_<case>/ を解析して表を出す
          ./Diag.py --fig               figs/runup_diag.png を描く(dt 収束・エネルギー履歴)
  各ケースについて、最大遡上高 R_max/H と、水面上のエネルギー E = Σ[½g((z+h−H)² − max(z−H,0)²)
  + ½h(u²+v²)]Δx/ny(単位幅、ρ = 1)の履歴を出す(前縁が汀線に達した時刻、遡上最大の時刻)。
  計算本体の外(方針 10)。numpy(+ matplotlib)。
"""
import sys, os, re, glob, subprocess
import numpy as np
from Runup import z_of, H, HTHR
G = 9.8

# ケース名: (元 param, 置換{namelist 変数: 値}, 説明)。dt は 0.02(Courant ≈ 0.28)が既定
CASES = {
    "base_nh":   ("param.txt",   {}, "NH + 砕波スイッチ(param.txt)"),
    "base_h":    ("param_h.txt", {}, "静水圧(param_h.txt)"),
    "base_ns":   ("param.txt",   {"f_nh_breaking": 0}, "NH、スイッチなし"),
    "flat_nh":   ("param.txt",   {"f_nh_breaking": 0, "nh_hmin": 0.98}, "NH は平坦部のみ(斜面は静水圧)"),
    "x120_h":    ("param_h.txt", {"f_user_routine": '"wave_solitary28_toe"', "tt": 40}, "静水圧、波を脚の 30 m 手前に置く"),
    "x120_nh":   ("param.txt",   {"f_user_routine": '"wave_solitary28_toe"', "tt": 40}, "NH + スイッチ、同上"),
    "dt01_nh":   ("param.txt",   {"dt": 0.01}, "NH + スイッチ、dt/2"),
    "dt005_nh":  ("param.txt",   {"dt": 0.005}, "NH + スイッチ、dt/4"),
    "dt01_h":    ("param_h.txt", {"dt": 0.01}, "静水圧、dt/2"),
    "dt005_h":   ("param_h.txt", {"dt": 0.005}, "静水圧、dt/4"),
    "dt01_ns":   ("param.txt",   {"dt": 0.01, "f_nh_breaking": 0}, "NH スイッチなし、dt/2"),
    "ns005_nh":  ("param.txt",   {"dt": 0.005, "f_nh_breaking": 0}, "NH スイッチなし、dt/4"),
    "dt01_flat": ("param.txt",   {"dt": 0.01, "f_nh_breaking": 0, "nh_hmin": 0.98}, "NH 平坦部のみ、dt/2"),
    "x120_005h": ("param_h.txt", {"dt": 0.005, "f_user_routine": '"wave_solitary28_toe"', "tt": 40}, "静水圧、脚の手前、dt/4"),
    "fric_h":    ("param_h.txt", {"rn0": 0.01}, "静水圧、Manning n = 0.01"),
    "fric_nh":   ("param.txt",   {"rn0": 0.01}, "NH + スイッチ、n = 0.01"),
    "fric2_nh":  ("param.txt",   {"rn0": 0.02}, "NH + スイッチ、n = 0.02"),
    "fricns_nh": ("param.txt",   {"rn0": 0.01, "f_nh_breaking": 0}, "NH スイッチなし、n = 0.01"),
    "fric005_nh":("param.txt",   {"rn0": 0.01, "dt": 0.005}, "NH + スイッチ、n = 0.01、dt/4"),
    "x120f_h":   ("param_h.txt", {"rn0": 0.01, "f_user_routine": '"wave_solitary28_toe"', "tt": 40}, "静水圧、脚の手前、n = 0.01"),
    "fine_h":    ("param_h.txt", {"nx": 2080, "ny": 64, "dt": 0.01}, "静水圧、Δx/2(Courant 同じ)"),
    "fine_nh":   ("param.txt",   {"nx": 2080, "ny": 64, "dt": 0.01}, "NH + スイッチ、Δx/2(Courant 同じ)"),
    "finef_nh":  ("param.txt",   {"nx": 2080, "ny": 64, "dt": 0.01, "rn0": 0.01}, "NH + スイッチ、Δx/2、n = 0.01"),
    "fine0025_h":("param_h.txt", {"nx": 2080, "ny": 64, "dt": 0.0025}, "静水圧、Δx/2、dt/8(Courant 0.07)"),
    "fine0025_nh":("param.txt",  {"nx": 2080, "ny": 64, "dt": 0.0025}, "NH + スイッチ、Δx/2、dt/8(Courant 0.07)"),
}

def make_param(name):
    src, rep, _ = CASES[name]
    s = open(src, encoding="utf-8").read()
    def sub(s, pat, val):
        s2, n = re.subn(pat, val, s, flags=re.M); assert n == 1, (name, pat); return s2
    s = sub(s, r"^\s*f_out_hmax = .*$", "  f_out_hmax = 1\n  f_out_u = 1\n  f_out_v = 1")
    s = sub(s, r"^\s*dir_result = .*$", f"  dir_result = 'result_x_{name}'")
    for k, v in rep.items():
        if k == "f_user_routine":
            s = sub(s, r'"wave_solitary28"', v)          # list_initial 側だけ(geoinfo の beach_slope は不変)
        else:
            s = sub(s, rf"^\s*{k} = .*$", f"  {k} = {v}")
    if rep.get("nx") == 2080:                               # プローブの格子番号も倍に
        for a, b in [("560, 16", "1120, 32"), ("640, 16", "1280, 32"), ("680, 16", "1360, 32")]:
            assert a in s; s = s.replace(a, b)
    pf = f"param_x_{name}.txt"
    open(pf, "w", encoding="utf-8").write(s)
    return pf

def run(name):
    pf = make_param(name)
    with open(f"Screen_x_{name}.log", "w") as log:
        subprocess.run(["./encflow", pf], stdout=log, stderr=subprocess.STDOUT, check=True)
    os.remove(pf)

def times(resdir):
    t = {}
    for l in open(os.path.join(resdir, "FILENUMBER.csv")):
        if l.startswith("#"): continue
        c = l.split(","); t[int(c[0])] = float(c[2])
    return t

def history(name):
    """(t, PE, KE, R/H, eta_max, x_crest) の履歴"""
    resdir = f"result_x_{name}"
    dx = 0.125 if CASES[name][1].get("nx") == 2080 else 0.25
    tm = times(resdir); rows = []
    for f in sorted(glob.glob(os.path.join(resdir, "H[0-9][0-9][0-9][0-9].txt"))):
        if f.endswith(("H9998.txt", "H9999.txt")): continue
        k = int(os.path.basename(f)[1:5])
        h = np.loadtxt(f); ny, nx = h.shape
        x = (np.arange(nx) + 0.5) * dx
        z = np.broadcast_to(z_of(x), h.shape)
        wet = h > HTHR
        pe = 0.5 * G * ((z + h - H) ** 2 - np.maximum(z - H, 0.0) ** 2) * wet
        fu, fv = f.replace("/H", "/u"), f.replace("/H", "/v")
        if os.path.exists(fu):
            u = np.loadtxt(fu); v = np.loadtxt(fv) if os.path.exists(fv) else 0.0 * u
            ke = 0.5 * h * (u ** 2 + v ** 2) * wet
        else:
            ke = np.zeros_like(h)
        mid = h[ny // 2, :]; wetm = np.where(mid > HTHR)[0]
        xf = x[wetm[-1]] if len(wetm) else 0.0
        etam = np.where(mid > HTHR, mid + z[0] - H, -np.inf)
        rows.append((tm.get(k, np.nan), pe.sum() * dx / ny, ke.sum() * dx / ny, (z_of(xf) - H) / H,
                     etam.max(), x[int(np.argmax(etam))]))
    return np.array(rows)

def table(names):
    print(f"{'case':11s} {'R_max/H':>7s} {'t':>5s} {'E_toe':>6s} {'E_shore':>7s} {'E_Rmax':>6s} (E/E0; E0 = 2.29)  説明")
    for n in names:
        if not os.path.isdir(f"result_x_{n}"): print(f"{n:11s} (未実行)"); continue
        r = history(n); E = r[:, 1] + r[:, 2]
        i_toe = int(np.argmax(r[:, 5] >= 150.0)) if (r[:, 5] >= 150.0).any() else 0   # 波頂が脚に達した最初の出力
        i_sh = int(np.argmax(r[:, 3] > 0)) if (r[:, 3] > 0).any() else 0
        i_max = int(np.argmax(r[:, 3]))
        print(f"{n:11s} {r[i_max,3]:7.3f} {r[i_max,0]:5.1f} {E[i_toe]/E[0]:6.2f} {E[i_sh]/E[0]:7.2f} {E[i_max]/E[0]:6.2f}   {CASES[n][2]}")

def fig():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": ["IPAGothic", "DejaVu Sans"], "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "#e3e2dd", "grid.linewidth": 0.6, "lines.linewidth": 1.5})
    C_NH, C_HY, C_NS, C_FR = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"
    os.makedirs("figs", exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.2))
    series = [("NH + スイッチ", ["base_nh", "dt01_nh", "dt005_nh"], C_NH, "o", "-"),
              ("NH、スイッチなし", ["base_ns", "dt01_ns", "ns005_nh"], C_NS, "s", "--"),
              ("静水圧", ["base_h", "dt01_h", "dt005_h"], C_HY, "o", "-"),
              ("NH + スイッチ、n = 0.01", ["fric_nh", None, "fric005_nh"], C_FR, "^", "-")]
    dts = [0.02, 0.01, 0.005]
    for lab, names, col, mk, ls in series:
        pts = [(dt, history(n)[:, 3].max()) for dt, n in zip(dts, names) if n and os.path.isdir(f"result_x_{n}")]
        if pts:
            p = np.array(pts); ax1.plot(p[:, 0], p[:, 1], marker=mk, ls=ls, color=col, mec="white", mew=0.8, ms=7, label=lab)
    ax1.axhline(0.918 * 0.28 ** 0.606, color="#6b6a66", ls=":", lw=1.0, label="実験則 0.42")
    ax1.set_xscale("log"); ax1.set_xticks(dts); ax1.set_xticklabels([str(d) for d in dts]); ax1.minorticks_off()
    ax1.set_xlim(0.025, 0.004); ax1.set_ylim(0.2, 0.9)
    ax1.set_xlabel("dt (s)  (Δx = 0.25 m)"); ax1.set_ylabel("R_max / H")
    ax1.set_title("最大遡上高の dt 収束", fontsize=10, loc="left")
    ax1.legend(loc="upper right", frameon=False, fontsize=7)
    for lab, n, col, ls in [("NH + スイッチ dt 0.02", "base_nh", C_NH, "-"), ("同 dt 0.005", "dt005_nh", C_NH, "--"),
                            ("静水圧 dt 0.02", "base_h", C_HY, "-"), ("同 dt 0.005", "dt005_h", C_HY, "--")]:
        if not os.path.isdir(f"result_x_{n}"): continue
        r = history(n); ax2.plot(r[:, 0], (r[:, 1] + r[:, 2]) / (r[0, 1] + r[0, 2]), color=col, ls=ls, label=lab)
    ax2.axvspan(28.5, 36, color="#9c9a94", alpha=0.15, lw=0)
    ax2.text(32.2, 0.98, "斜面上", ha="center", fontsize=8, color="#52514e")
    ax2.set_xlim(0, 50); ax2.set_ylim(0.3, 1.02)
    ax2.set_xlabel("t (s)"); ax2.set_ylabel("E / E₀(水面上の全エネルギー)")
    ax2.set_title("エネルギー履歴", fontsize=10, loc="left")
    ax2.legend(loc="lower left", frameon=False, fontsize=7)
    fig.tight_layout(); fig.savefig("figs/runup_diag.png", dpi=150)
    print("written: figs/runup_diag.png")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--run" in sys.argv:
        for n in (args or list(CASES)):
            print(f"running {n} ...", flush=True); run(n)
    if "--fig" in sys.argv:
        fig()
    if "--run" not in sys.argv and "--fig" not in sys.argv or args:
        table(args or list(CASES))
