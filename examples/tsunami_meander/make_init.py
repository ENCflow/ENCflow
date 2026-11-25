#!/usr/bin/env python3
"""tsunami_meander: 蛇行水路の段波実験(小林ら 2019・2021)の入力を作る

  使い方: python3 make_init.py [--dx 0.02] [--rot 0] [--smooth 0] [--suffix ""] [--channels s110,s125,str]

  水路ごと(tag = s110・s125・str。--suffix を付けると tag の末尾に付く)に次を書く。
    mask_<tag>.txt        領域マスク(1 = 水路と上流水槽、0 = 外。側壁は格子の階段で表す)
    z_<tag>.txt           地盤高 (m)。ゲートの位置を 0 とする平面(水路の軸方向に一様勾配)
    e_<tag>_<bore>.txt    初期水位 (m)。ゲートの上流 h0、下流 h1(bore = bk: 砕波段波、ub: 波状段波)。--smooth δ (m) を
                          与えると、段差を h1 + (h0 - h1) (1 - tanh(s / δ)) / 2 のなだらかな水面にする(s はゲートからの距離)
    geoinfo_<tag>.txt     &list_geoinfo(格子・地形・マスク・粗度)
    initial_<tag>_<bore>.txt  &list_initial
    record_<tag>.txt      &list_record(プローブ)
    probes_<tag>.csv      プローブの番号・位置と、どの測定点のものか(plot_results.py が読む)

  プローブは点を含むセルの値を記録する(補間しない)。測定点の値は、測定点を囲む 4 つのセル中心(そのうち水路の中に
  あるもの)にプローブを置いて、後処理で双 1 次補間の重みで平均する(重みは probes_<tag>.csv)。プローブはいつもセル中心に
  あるので、どのセルの値になるかが丸めで変わらない。測定点がセル中心に当たるときは 1 点、セルの境界の上なら 2 点になる。
"""
import argparse, math
import numpy as np

H0 = 0.285                              # ゲート上流の水深 (m)
BORES = {"bk": 0.107, "ub": 0.147}      # ゲート下流の水深 (m): 砕波段波(F = 1.53)、波状段波(F = 1.32)
RN = 0.014                              # Manning の粗度係数(小林ら 2021 の平面 2 次元計算と同じ値)
NWAVE = 2                               # 蛇行の波数(その下流は直線)
# B: 水路幅、Lm: 蛇行長(中心線に沿う 1 波長)、thmax: 最大偏角 (°)、slope: 水路の軸方向の勾配、
# Lup: ゲートより上流の直線部の長さ、Ldown: ゲートより下流の長さ(蛇行 2 波長 + 下流の直線部。直線水路は全長 15.76 m から)、
# tank: 上流水槽 (長さ, 水路の中心からの右端, 左端)。None は上流端が壁、bores: 計算する段波
CHANNELS = {
    "s110": dict(B=0.80, Lm=7.50, thmax=35.0, slope=1.0 / 600.0, Lup=1.50, Ldown=2 * 7.50 + 1.10, tank=(1.45, -1.26, 2.70), bores=("bk", "ub")),
    "s125": dict(B=0.39, Lm=8.06, thmax=53.0, slope=0.0, Lup=1.66, Ldown=2 * 8.06 + 1.20, tank=None, bores=("ub",)),
    "str":  dict(B=0.40, Lm=8.06, thmax=0.0, slope=0.0, Lup=1.68, Ldown=15.76 - 1.68, tank=None, bores=("ub",)),
}
NBANK = 80                              # 岸沿いのプローブの間隔 = Lm / NBANK
BANK_OFF = 0.02                         # 岸沿いのプローブの、側壁からの距離 (m)(実験の波高計と同じ)

def centerline(c, ds=0.0005):
    """中心線の点列 (s, X, Y, θ)。s = 0 がゲート(X = Y = 0)。前後の直線部を含む"""
    th = math.radians(c["thmax"]); s_end = NWAVE * c["Lm"]
    s = np.arange(-c["Lup"] - 0.5, max(s_end, c["Ldown"]) + 0.5 + ds / 2, ds)
    theta = np.where((s >= 0) & (s <= s_end), th * np.sin(2 * np.pi * s / c["Lm"]), 0.0)
    X = np.concatenate([[0.0], np.cumsum(0.5 * (np.cos(theta[1:]) + np.cos(theta[:-1])) * ds)])
    Y = np.concatenate([[0.0], np.cumsum(0.5 * (np.sin(theta[1:]) + np.sin(theta[:-1])) * ds)])
    i0 = int(np.argmin(np.abs(s)))
    return s, X - X[i0], Y - Y[i0], theta

def build(name, c, dx, rot_deg, suffix, smooth=0.0):
    tag = name + suffix; B = c["B"]
    s, X, Y, th = centerline(c)
    s_lo = -c["Lup"]; s_hi = c["Ldown"]
    rot = math.radians(rot_deg); cr, sr = math.cos(rot), math.sin(rot)
    # ---- 格子の範囲(水路座標 (X, Y) を rot だけ回して格子座標にする)
    sel = (s >= s_lo) & (s <= s_hi); pts = []
    for sg in (-1, 1):
        pts.append(np.c_[X[sel] - sg * 0.5 * B * np.sin(th[sel]), Y[sel] + sg * 0.5 * B * np.cos(th[sel])])
    if c["tank"]:
        tl, ylo, yhi = c["tank"]
        pts.append(np.array([[s_lo - tl, ylo], [s_lo - tl, yhi], [s_lo, ylo], [s_lo, yhi]]))
    Pt = np.vstack(pts)
    gx = cr * Pt[:, 0] - sr * Pt[:, 1]; gy = sr * Pt[:, 0] + cr * Pt[:, 1]
    mrg = 3 * dx          # 外周に 3 セルの余白。原点は dx の倍数(回転なしならゲートがセルの境界に来る)
    x0 = math.floor((gx.min() - mrg) / dx) * dx; y0 = math.floor((gy.min() - mrg) / dx) * dx
    nx = int(math.ceil((gx.max() + mrg - x0) / dx)); ny = int(math.ceil((gy.max() + mrg - y0) / dx))
    xc = x0 + (np.arange(nx) + 0.5) * dx
    yc = y0 + (ny - np.arange(ny) - 0.5) * dx          # 行 0 が北端
    GX, GY = np.meshgrid(xc, yc)
    FX = cr * GX + sr * GY; FY = -sr * GX + cr * GY     # セル中心の水路座標
    # ---- セル中心ごとに、中心線の最も近い点の s と、中心線からの符号付き距離 n(左岸側が正)を求める
    flat = np.c_[FX.ravel(), FY.ravel()]; order = np.argsort(flat[:, 0]); srt = flat[order]
    Sf = np.full(len(flat), np.nan); Nf = np.full(len(flat), np.nan); reach = 0.5 * B + 2 * dx
    for a0 in range(0, len(srt), 400):
        p = srt[a0:a0 + 400]
        lo = np.searchsorted(X, p[:, 0].min() - reach); hi = np.searchsorted(X, p[:, 0].max() + reach)
        if hi <= lo: continue
        k = np.argmin((p[:, 0:1] - X[None, lo:hi]) ** 2 + (p[:, 1:2] - Y[None, lo:hi]) ** 2, axis=1) + lo
        ddx = p[:, 0] - X[k]; ddy = p[:, 1] - Y[k]
        ok = np.abs(np.cos(th[k]) * ddx + np.sin(th[k]) * ddy) <= 0.002      # 中心線の端より外の点は除く
        ii = order[a0:a0 + 400][ok]
        Sf[ii] = s[k][ok]; Nf[ii] = (-np.sin(th[k]) * ddx + np.cos(th[k]) * ddy)[ok]
    S = Sf.reshape(GX.shape); N = Nf.reshape(GX.shape)
    with np.errstate(invalid="ignore"):
        mask = (np.abs(N) <= 0.5 * B) & (S >= s_lo) & (S <= s_hi)
        up = mask & (S < 0)                               # ゲートより上流
    if c["tank"]:
        tl, ylo, yhi = c["tank"]
        tank = (FX >= s_lo - tl) & (FX < s_lo) & (FY >= ylo) & (FY <= yhi)
        mask |= tank; up |= tank
    z = -c["slope"] * FX
    np.savetxt(f"mask_{tag}.txt", mask.astype(int), fmt="%d")
    np.savetxt(f"z_{tag}.txt", z, fmt="%.5f")
    for bore in c["bores"]:
        lev = np.where(up, H0, BORES[bore]); note = "水面は水平"
        if smooth > 0:      # 段差をなだらかにする(上流と下流の水の量の和は変わらない。水槽は h0 のまま)
            with np.errstate(invalid="ignore"):
                lev = np.where(np.isnan(S), lev, BORES[bore] + 0.5 * (H0 - BORES[bore]) * (1.0 - np.tanh(S / smooth)))
            note = f"段差は tanh(s / {smooth} m) のなだらかな水面"
        np.savetxt(f"e_{tag}_{bore}.txt", np.where(mask, lev, 0.0), fmt="%.5f" if smooth > 0 else "%.3f")
        with open(f"initial_{tag}_{bore}.txt", "w") as f:
            f.write(f"! make_init.py が書いた初期条件。ゲートの上流 h0 = {H0} m、下流 h1 = {BORES[bore]} m(ゲートの位置の水深。{note})\n"
                    f"&list_initial\n  f_htype = 3                    ! 水位の分布ファイル(h = max(E - z, 0))\n"
                    f"  fn_hinit = 'e_{tag}_{bore}.txt'\n/\n")
    with open(f"geoinfo_{tag}.txt", "w") as f:
        f.write(f"! make_init.py が書いた地理情報({name}、dx = {dx} m、回転 {rot_deg}°、有効セル {int(mask.sum())})\n"
                f"&list_geoinfo\n  nx = {nx}\n  ny = {ny}\n  dx = {dx}\n  dy = {dx}\n"
                f"  f_ztype = 1\n  fn_z = 'z_{tag}.txt'\n  f_masktype = 1\n  fn_mask = 'mask_{tag}.txt'   ! 水路の外は計算しない(側壁)\n"
                f"  f_rntype = 0\n  rn0 = {RN}                    ! Manning の粗度係数\n/\n")
    # ---- プローブ: 測定断面 k = 1〜8(s = k Lm / 8)の 5 点と、岸沿い(蛇行水路)か中心線沿い(直線水路)の点列。
    #      測定点を囲む 4 つのセル中心のうち、水路の中にあって重みが 0 でないものに置く
    probes = []; ngauge = 0
    def add(kind, sec, sv, nv):
        nonlocal ngauge
        ngauge += 1; i = int(np.argmin(np.abs(s - sv)))
        fx = X[i] - nv * math.sin(th[i]); fy = Y[i] + nv * math.cos(th[i])
        ax = (cr * fx - sr * fy - x0) / dx - 0.5; ay = (sr * fx + cr * fy - y0) / dx - 0.5      # セル中心を単位とする位置
        i0 = math.floor(ax + 1e-9); j0 = math.floor(ay + 1e-9); wx = ax - i0; wy = ay - j0
        cand = [(i0, j0, (1 - wx) * (1 - wy)), (i0 + 1, j0, wx * (1 - wy)), (i0, j0 + 1, (1 - wx) * wy), (i0 + 1, j0 + 1, wx * wy)]
        keep = [(ii, jj, w) for ii, jj, w in cand if w > 1e-6 and 0 <= ii < nx and 0 <= jj < ny and mask[ny - 1 - jj, ii]]
        wsum = sum(w for _, _, w in keep)
        for ii, jj, w in keep:
            probes.append((ngauge, kind, sec, sv, nv, w / wsum, (ii + 0.5) * dx, (jj + 0.5) * dx))
    for k in range(1, 9):
        for d in (BANK_OFF, B / 4, B / 2, 3 * B / 4, B - BANK_OFF):    # 右岸からの距離
            add("sec", k, k * c["Lm"] / 8, -0.5 * B + d)
    for ib in range(1, int(1.25 * NBANK) + 1):
        sv = ib * c["Lm"] / NBANK
        if c["thmax"] > 0: add("right", 0, sv, -0.5 * B + BANK_OFF); add("left", 0, sv, 0.5 * B - BANK_OFF)
        else: add("center", 0, sv, 0.0)
    with open(f"record_{tag}.txt", "w") as f:
        f.write("! make_init.py が書いたプローブ(実座標 = 南西端を原点とする格子座標 m)。番号と測定点の対応は probes_*.csv\n"
                "&list_record\n  pbxytype = 1\n")
        for i, p in enumerate(probes, 1): f.write(f"  pbxy(:,{i}) = {p[6]:.5f}, {p[7]:.5f}\n")
        f.write("/\n")
    with open(f"probes_{tag}.csv", "w") as f:
        f.write(f"# channel={name} B={B} Lm={c['Lm']} thmax={c['thmax']} slope={c['slope']} Lup={c['Lup']} h0={H0} dx={dx} rot={rot_deg} "
                f"nx={nx} ny={ny} x0={x0:.5f} y0={y0:.5f}\n")
        f.write("# gauge = 測定点の番号(同じ番号のプローブを重み w で平均する)。kind: sec = 測定断面の点、right / left / center =\n"
                "# 右岸沿い・左岸沿い・中心線沿い。s = ゲートからの中心線に沿う距離 (m)、n = 測定点の中心線からの距離 (m。左岸側が正)、\n"
                "# w = 双 1 次補間の重み、x・y = プローブ(セル中心)の格子座標 (m。南西端が原点)\n")
        f.write("no,gauge,kind,section,s,n,w,x,y\n")
        for i, p in enumerate(probes, 1):
            f.write(f"{i},{p[0]},{p[1]},{p[2]},{p[3]:.5f},{p[4]:.5f},{p[5]:.6f},{p[6]:.5f},{p[7]:.5f}\n")
    assert len(probes) <= 1000, "プローブは 1000 点まで"
    print(f"{tag}: nx = {nx}, ny = {ny}, valid cells = {int(mask.sum())}, gauges = {ngauge}, probes = {len(probes)}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dx", type=float, default=0.02, help="格子間隔 (m)")
    ap.add_argument("--rot", type=float, default=0.0, help="格子に対して水路を回す角度 (°)")
    ap.add_argument("--smooth", type=float, default=0.0, help="初期水位の段差をなだらかにする幅 δ (m)。0 は段差のまま")
    ap.add_argument("--suffix", default="", help="出力ファイルの tag の末尾に付ける文字列")
    ap.add_argument("--channels", default="s110,s125,str")
    a = ap.parse_args()
    for name in a.channels.split(","):
        build(name, CHANNELS[name], a.dx, a.rot, a.suffix, a.smooth)

if __name__ == "__main__":
    main()
