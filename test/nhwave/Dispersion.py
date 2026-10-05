#!/usr/bin/env python3
"""nhwave: 閉じた正方水槽の定在波で ENC の分散関係を計測する(docs/nonhydrostatic_plan.md §11 Phase 1)

  使い方:  ./Dispersion.py            既定の走査(h0 × モード × 適応 RK)を実行して表を出す
           ./Dispersion.py --quick    h0=8 だけ
  出力:    scan/<case>/ に各ケースの結果、Dispersion_result.md に表

  計測: プローブ 1(南西隅 = 腹)の h(t) − H のゼロ交差時刻を線形回帰して周期 T を求める。
  比較: T_cont(連続・静水圧 √(gH)k)、T_ENC(8 近傍 ENC の半離散固有値 Λ。壁つき格子の
        Rayleigh 商)、T_ENC+FB(前進後退 Euler の時間離散化込み)、T_NH(1 層 NH の目標
        ω² = gHΛ/(1+βΛ))、T_exact(ω² = gk tanh kH)。
  計算本体の外(方針 10)。numpy のみ。
"""
import os, re, subprocess, sys, math
import numpy as np

G = 9.8
LX = 100.0
NX = 100
M = 4                      # モード数(user_initial の wave_standing_* と同期)
PD = 2.0 / (2.0 + math.sqrt(2.0))   # p_diagratio の既定

def enc_lambda_plane(kx, ky, dx):
    """8 近傍 ENC の半離散ラプラシアン固有値 Λ(kx, ky)(無限格子)"""
    lp = 1.0 - PD
    ld = PD / 2.0
    return 2.0 * (lp * (1 - math.cos(kx * dx)) + lp * (1 - math.cos(ky * dx))
                  + ld * ((1 - math.cos((kx + ky) * dx)) + (1 - math.cos((kx - ky) * dx)))) / dx**2

def enc_lambda_walls(mode, nx, dx):
    """壁つき nx×nx 格子で、初期モードベクトルの Rayleigh 商 vᵀ(−DG)v / vᵀv を返す"""
    lp = 1.0 - PD
    ld = PD / 2.0
    i = (np.arange(nx) + 0.5) * dx
    if mode == "x":
        v = np.cos(M * math.pi * i / LX)[:, None] * np.ones((1, nx))
    else:
        v = np.cos(M * math.pi * i / LX)[:, None] * np.cos(M * math.pi * i / LX)[None, :]
    av = np.zeros_like(v)
    # 軸方向(重み lp/dx²)と対角方向(ld/dx²)。壁の外の近傍はエッジなし(寄与 0)
    for (di, dj, w) in [(1, 0, lp), (-1, 0, lp), (0, 1, lp), (0, -1, lp),
                        (1, 1, ld), (1, -1, ld), (-1, 1, ld), (-1, -1, ld)]:
        nb = np.zeros_like(v)
        src = v[max(0, -di):nx - max(0, di), max(0, -dj):nx - max(0, dj)]
        nb[max(0, di):nx - max(0, -di), max(0, dj):nx - max(0, -dj)] = src
        mask = np.zeros_like(v)
        mask[max(0, di):nx - max(0, -di), max(0, dj):nx - max(0, -dj)] = 1.0
        av += w * (nb - v * mask)
    return -float(np.sum(v * av) / np.sum(v * v)) / dx**2

def measure_period(csv):
    t, h = [], []
    with open(csv) as f:
        for line in f:
            if line.startswith("#"):
                continue
            c = [float(x) for x in line.split(",")]
            t.append(c[0] * 3600.0)
            h.append(c[3])
    t = np.array(t)
    h = np.array(h)
    eta = h - h.mean()
    # ゼロ交差(符号変化)の時刻を線形補間
    s = np.sign(eta)
    idx = np.where(s[:-1] * s[1:] < 0)[0]
    tc = t[idx] - eta[idx] * (t[idx + 1] - t[idx]) / (eta[idx + 1] - eta[idx])
    if len(tc) < 4:
        return float("nan"), float("nan"), len(tc)
    n = np.arange(len(tc))
    slope = np.polyfit(n, tc, 1)[0]      # 半周期
    # 振幅減衰: 最初と最後の全周期の |η| 最大の比
    nper = len(tc) // 2
    a0 = np.max(np.abs(eta[(t >= tc[0]) & (t <= tc[2])]))
    a1 = np.max(np.abs(eta[(t >= tc[-3]) & (t <= tc[-1])]))
    return 2.0 * slope, a1 / a0, len(tc)

def run_case(name, h0, mode, dt, runge, hcap, tt):
    wd = os.path.join("scan", name)
    os.makedirs(wd, exist_ok=True)
    src = open("param.txt", encoding="utf-8").read()
    rep = {
        r"^\s*dt = .*$": f"  dt = {dt}",
        r"^\s*tt = .*$": f"  tt = {tt}",
        r"^\s*dt_recrd = .*$": f"  dt_recrd = {dt}",
        r"^\s*dt_file = .*$": f"  dt_file = {tt}",
        r"^\s*h0 = .*$": f"  h0 = {h0}",
        r"^\s*f_user_routine = .*$": f'  f_user_routine = "wave_standing_{mode}"',
        r"^\s*f_adaptive_runge = .*$": f"  f_adaptive_runge = {runge}",
        r"^\s*f_hcap_upwind = .*$": f"  f_hcap_upwind = {hcap}",
        r"^\s*dir_result = .*$": f"  dir_result = '{wd}/result'",
    }
    for pat, val in rep.items():
        src, n = re.subn(pat, val, src, flags=re.M)
        assert n == 1, pat
    pf = os.path.join(wd, "param.txt")
    open(pf, "w", encoding="utf-8").write(src)
    with open(os.path.join(wd, "Screen.log"), "w") as log:
        subprocess.run(["./encflow", pf], stdout=log, stderr=subprocess.STDOUT, check=True)
    return measure_period(os.path.join(wd, "result", "probes", "probe0001.csv"))

def main():
    quick = "--quick" in sys.argv
    dx = LX / NX
    cases = []
    depths = [8.0] if quick else [1.0, 2.0, 4.0, 8.0, 16.0]
    for mode in ["x", "xy"]:
        for h0 in depths:
            for runge in [1, 0]:
                cases.append((mode, h0, 0.02, runge, 0))
    if not quick:
        cases += [("x", 8.0, 0.005, 1, 0), ("x", 8.0, 0.05, 1, 0), ("x", 8.0, 0.02, 1, 1)]
    rows = []
    for (mode, h0, dt, runge, hcap) in cases:
        kx = M * math.pi / LX
        ky = kx if mode == "xy" else 0.0
        k = math.hypot(kx, ky)
        H = h0
        w_cont = math.sqrt(G * H) * k
        tt = math.ceil(8 * 2 * math.pi / w_cont)
        name = f"{mode}_h{h0:g}_dt{dt:g}_rk{runge}_hc{hcap}"
        T, decay, ncross = run_case(name, h0, mode, dt, runge, hcap, tt)
        lam_p = enc_lambda_plane(kx, ky, dx)
        lam_w = enc_lambda_walls(mode, NX, dx)
        w_enc = math.sqrt(G * H * lam_w)
        w_fb = 2.0 / dt * math.asin(min(1.0, w_enc * dt / 2.0))
        beta = H * H / 4.0
        w_nh = math.sqrt(G * H * lam_w / (1.0 + beta * lam_w))
        w_ex = math.sqrt(G * k * math.tanh(k * H))
        rows.append(dict(name=name, mode=mode, h0=h0, dt=dt, runge=runge, hcap=hcap,
                         kH=k * H, kdx=k * dx, T=T, decay=decay, ncross=ncross,
                         Tc=2 * math.pi / w_cont, Tenc=2 * math.pi / w_enc, Tfb=2 * math.pi / w_fb,
                         Tnh=2 * math.pi / w_nh, Tex=2 * math.pi / w_ex,
                         lamratio=lam_w / lam_p))
        print(f"{name:28s} kH={k*H:5.2f} kdx={k*dx:5.3f} T={T:8.4f} Tc={2*math.pi/w_cont:8.4f} "
              f"Tenc={2*math.pi/w_enc:8.4f} Tfb={2*math.pi/w_fb:8.4f} Tnh={2*math.pi/w_nh:8.4f} "
              f"decay={decay:6.3f} n={ncross}", flush=True)
    with open("Dispersion_result.md", "w", encoding="utf-8") as f:
        f.write("# nhwave: 静水圧 ENC の分散関係の計測結果\n\n")
        f.write("周期 (s)。c/c_cont = T_cont/T(位相速度比)。T_ENC は壁つき格子の Rayleigh 商による半離散値、"
                "T_ENC+FB は前進後退 Euler の時間離散化込み、T_NH は 1 層 NH の目標、T_exact は ω²=gk tanh kH。\n\n")
        f.write("| case | kH | kΔx | T_meas | T_cont | T_ENC | T_ENC+FB | T_NH | T_exact | c/c_cont | c/c_ENC+FB | 振幅比(最終/最初) | Λ_wall/Λ_plane |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for r in rows:
            f.write(f"| {r['name']} | {r['kH']:.3f} | {r['kdx']:.3f} | {r['T']:.4f} | {r['Tc']:.4f} | {r['Tenc']:.4f} | "
                    f"{r['Tfb']:.4f} | {r['Tnh']:.4f} | {r['Tex']:.4f} | {r['Tc']/r['T']:.4f} | {r['Tfb']/r['T']:.4f} | "
                    f"{r['decay']:.3f} | {r['lamratio']:.4f} |\n")
    print("written: Dispersion_result.md")

if __name__ == "__main__":
    main()
