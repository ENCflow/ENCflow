"""chichibu_flood の図(事前に ./run_cases.sh で計算しておく。無い結果の図は飛ばす)。
  figs/setup.png       流域の地形・河道・測線・プローブ・流域出口と、与えた雨
  figs/bed.png         本川の河床の縦断(窪地除去済みの標高と、河床を整えた標高)
  figs/transects.png   各解像度の河道マスクに重ねた測線とプローブ(測線のまわりの拡大)
  figs/base.png        基本ケース(200 m)の測線 1〜4 のハイドログラフと、t = 2 時間の水深分布
  figs/dem.png         地形の扱いを変えた 6 時間後の水深分布(元の DEM・窪地除去済み・河床を整えた標高・4 近傍)
  figs/bed_effect.png  河床を整えた効果(200 m・100 m の測線 1〜4)
  figs/loss.png        降雨遮断と地下浸透の効果(ハイドログラフと流域の水量)
  figs/outlet.png      流域出口を閉じた計算と開けた計算(測線 4 の流量とプローブ 4 の水深、閉じたときの水深分布)
  figs/resolution.png  格子の解像度(上段 ENC、下段 4 近傍。測線 1 と 4)
  figs/width.png       河道幅を 50 m に揃えた比較(測線 3・4)
  figs/advection.png   移流項の扱いと解像度(測線 1 と 4)
  figs/roughness.png   河道の粗度と移流項(測線 4)
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
os.makedirs(FIGDIR, exist_ok=True)
DATA = "../../tutorials/chichibu/data_chichibu"
DX = 200.0
TRANSECTS = [(82, 107, 82, 103), (107, 103, 107, 100), (147, 105, 147, 102), (216, 43, 216, 37)]
PROBES = [(82, 105), (107, 102), (147, 104), (216, 39)]
OUTLET = [(239, 19), (240, 19)]
SOURCE = (54, 113)                     # 縦断の起点(本川の源頭の河道セル)
C_TR = ["#86b6ef", "#2a78d6", "#1c5cab", "#0d366b"]      # 測線 1〜4(上流 → 下流。1 色相の淡 → 濃)
C_RES = {"200m": "#9467bd", "100m": "#2ca02c", "50m": "#1f9fd0"}
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
matplotlib.rcParams.update({
    "font.family": ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"],
    "axes.unicode_minus": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "font.size": 10, "axes.titlesize": 10.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False, "legend.fontsize": 8.5, "lines.linewidth": 1.6,
})


def have(case):
    return os.path.exists(f"result_{case}/fluxes/flux0004.csv")


def flux(case, n):
    a = np.loadtxt(f"result_{case}/fluxes/flux{n:04d}.csv", delimiter=",", comments="#", ndmin=2)
    return a[:, 1], a[:, 2]                         # 分、流量 (m3/s)


def probe(case, n):
    a = np.loadtxt(f"result_{case}/probes/probe{n:04d}.csv", delimiter=",", comments="#", ndmin=2)
    return a[:, 1], a[:, 3]                         # 分、水深 (m)


def grid(path):
    return np.loadtxt(path)


def storage(case):
    """Log.txt の時刻(分)と水量の列(S、または S_surf・S_grnd・S_total)"""
    t, rows, head = [], [], None
    for line in open(f"result_{case}/Log.txt"):
        if line.startswith("time,"):
            head = [h.strip() for h in line.split(",")]
            continue
        p = line.split()
        if head and p and ":" in p[0] and p[0][0].isdigit():
            h, m, s = p[0].split(":")
            t.append(int(h) * 60 + int(m) + float(s) / 60)
            rows.append([float(x.rstrip("%")) for x in p[1:]])
    return np.array(t), np.array(rows), head


def save(fig, name):
    fig.savefig(f"{FIGDIR}/{name}", dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"{FIGDIR}/{name}")


basin = grid(f"{DATA}/Chichibu_200m_basin.txt") > 0
river = grid(f"{DATA}/Chichibu_200m_river_flowline.txt") > 0
zc = grid(f"{DATA}/Chichibu_200m_cond.txt")
zf = grid(f"{DATA}/Chichibu_200m_filled.txt")
NY, NX = basin.shape
EXT = [0, NX * DX / 1000, NY * DX / 1000, 0]       # km。行 1 が北(上)


def cxy(i, j):
    """セル番号(1 始まり)のセル中心の座標 (km)"""
    return (i - 0.5) * DX / 1000, (j - 0.5) * DX / 1000


def depth_map(ax, h, title, vmax=10.0):
    """水深の分布(乾いたセルは白、流域外は淡灰)"""
    hm = np.where(basin, h, np.nan)
    ax.imshow(np.where(basin, 1.0, np.nan), extent=EXT, cmap=ListedColormap(["#f6f5f2"]), interpolation="nearest")
    hm = np.where(hm > 0.01, hm, np.nan)
    im = ax.imshow(hm, extent=EXT, cmap="YlOrRd", vmin=0, vmax=vmax, interpolation="nearest")
    ax.set_title(title)
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    return im


def bed_path():
    """本川の源頭から流域出口まで、河道セルの 8 近傍のうち整えた河床の勾配が最も急なセルへ順に下る
    (同じ高さが続く所は、河道セルをつないだ出口までの道のりが短くなる向き)。教材の Fig_chichibu.sh と同じ手順"""
    INF = 1e30
    d = np.full((NY, NX), INF)
    jo, io = OUTLET[1][1] - 1, OUTLET[1][0] - 1
    d[jo, io] = 0.0
    queue = [(jo, io)]
    k = 0
    while k < len(queue):
        j, i = queue[k]; k += 1
        for b in (-1, 0, 1):
            for a in (-1, 0, 1):
                if (a or b) and 0 <= j + b < NY and 0 <= i + a < NX and river[j + b, i + a]:
                    w = np.sqrt(2.0) if a and b else 1.0
                    if d[j, i] + w < d[j + b, i + a] - 1e-9:
                        d[j + b, i + a] = d[j, i] + w
                        queue.append((j + b, i + a))
    j, i = SOURCE[1] - 1, SOURCE[0] - 1
    path, L = [(j, i, 0.0)], 0.0
    while (j, i) != (jo, io):
        best, nxt = -1.0, None
        for b in (-1, 0, 1):
            for a in (-1, 0, 1):
                if (a or b) and river[j + b, i + a]:
                    w = np.sqrt(2.0) if a and b else 1.0
                    s = (zc[j, i] - zc[j + b, i + a]) / w
                    if s < 0 or (s == 0 and d[j + b, i + a] >= d[j, i]):
                        continue
                    if s > best or (s == best and d[j + b, i + a] < bd):
                        best, nxt, bw, bd = s, (j + b, i + a), w, d[j + b, i + a]
        if nxt is None or len(path) > 5000:
            raise RuntimeError(f"bed profile: no way down at cell {i + 1}, {j + 1}")
        L += bw
        j, i = nxt
        path.append((j, i, L))
    return [(j, i, (L - l) * DX / 1000) for j, i, l in path]       # 出口からの距離 (km)


def setup():
    fig = plt.figure(figsize=(11.5, 4.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[3.0, 1.0], wspace=0.12)
    ax = fig.add_subplot(gs[0])
    zm = np.where(basin, zc, np.nan)
    im = ax.imshow(zm, extent=EXT, cmap="terrain", vmin=0, vmax=2500, interpolation="nearest")
    ax.imshow(np.where(river, 1.0, np.nan), extent=EXT, cmap=ListedColormap(["#1f5fbf"]), interpolation="nearest")
    for n, (ir, jr, il, jl) in enumerate(TRANSECTS, 1):
        x0, y0 = cxy(ir, jr); x1, y1 = cxy(il, jl)
        ax.plot([x0, x1], [y0, y1], color="#d62728", lw=2.2)
        ax.text(x1, y1 - 0.8, T(f"測線 {n}", f"T{n}"), color="#d62728", fontsize=9, ha="center", va="bottom", fontweight="bold")
    for n, (i, j) in enumerate(PROBES, 1):
        x, y = cxy(i, j)
        ax.plot(x, y, "o", ms=5, mfc="white", mec=INK, mew=1.2)
    x, y = cxy(*OUTLET[1])
    ax.plot(x, y, "s", ms=8, mfc="#ffbf00", mec=INK)
    ax.annotate(T("流域出口", "outlet"), (x, y), xytext=(x - 6.5, y - 1.8), fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTED))
    ax.set_xlabel("x (km)"); ax.set_ylabel("y (km)")
    ax.set_title(T("(a) 河床を整えた標高(流域内)・河道セル(青)・測線(赤)・プローブ(○)",
                   "(a) Conditioned-bed elevation, channels, transects (red), probes (o)"))
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.01)
    cb.set_label(T("標高 (m)", "elevation (m)"))
    ax = fig.add_subplot(gs[1])
    ax.fill_between([0, 30, 60], [0, 200, 0], color="#5598e7", alpha=0.8)
    ax.set_xlim(0, 120); ax.set_ylim(0, 230)
    ax.set_xlabel(T("時間 (分)", "time (min)")); ax.set_ylabel(T("雨量強度 (mm/h)", "rainfall intensity (mm/h)"))
    ax.set_title(T("(b) 与えた雨(流域に一様。計 100 mm)", "(b) Rainfall (uniform; 100 mm in total)"))
    save(fig, "setup.png")


def bed():
    path = bed_path()
    s = np.array([p[2] for p in path])
    f = np.array([zf[p[0], p[1]] for p in path])
    c = np.array([zc[p[0], p[1]] for p in path])
    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    ax.plot(s, f, color=MUTED, lw=1.4, label=T("窪地除去済みの標高(河道セルの値)", "depression-filled elevation (channel cells)"))
    ax.plot(s, c, color="#2a78d6", lw=1.6, label=T("河床を整えた標高", "conditioned bed"))
    for n, (i, j) in enumerate(PROBES, 1):
        k = int(np.argmin([(p[1] + 1 - i) ** 2 + (p[0] + 1 - j) ** 2 for p in path]))
        ax.axvline(s[k], color="#d62728", lw=0.8, ls=":")
        ax.text(s[k], 1450, T(f"測線 {n}", f"T{n}"), color="#d62728", fontsize=8.5, ha="center")
    ax.set_xlim(s.max(), 0)
    ax.set_ylim(80, 1500)
    ax.set_xlabel(T("流域出口からの距離 (km)", "distance from the outlet (km)"))
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T("本川の河床の縦断(源頭から流域出口まで。河道セルを整えた河床の勾配の最も急な向きにたどる)",
                   "Bed profile along the main stem (from the head to the outlet, following the steepest conditioned-bed descent)"))
    ax.legend(loc="lower left")
    save(fig, "bed.png")


def read_record(path):
    """設定ファイルの pbxy・flxy(セル番号)を読む"""
    pb, fl = {}, {}
    for line in open(path, encoding="utf-8"):
        t = line.split("!")[0].strip()
        for key, store in (("pbxy(:,", pb), ("flxy(:,", fl)):
            if t.startswith(key):
                n = int(t[len(key):].split(")")[0])
                store[n] = [int(v) for v in t.split("=")[1].split(",")]
    return pb, fl


def transects():
    sets = [("200m", "param.txt", f"{DATA}/Chichibu_200m_river_flowline.txt", 200.0),
            ("100m", "param_100m.txt", "../../test/chichibu/data_chichibu/Chichibu_100m_river_flowline.txt", 100.0),
            ("50m", "param_50m.txt", "../../test/chichibu/data_chichibu_50m/Chichibu_50m_river_flowline.txt", 50.0)]
    sets = [x for x in sets if os.path.exists(x[1]) and os.path.exists(x[2])]
    fig, axs = plt.subplots(len(sets), 4, figsize=(12, 3.0 * len(sets)), squeeze=False)
    for r, (res, par, rwf, dx) in enumerate(sets):
        rw = grid(rwf) > 0
        pb, fl = read_record(par)
        half = int(round(1200.0 / dx))                     # 拡大の範囲(プローブから ±1.2 km)
        for n in range(1, 5):
            ax = axs[r, n - 1]
            i0, j0 = pb[n]
            ii = np.arange(i0 - half, i0 + half + 1); jj = np.arange(j0 - half, j0 + half + 1)
            sub = rw[np.clip(jj - 1, 0, rw.shape[0] - 1)][:, np.clip(ii - 1, 0, rw.shape[1] - 1)]
            ax.imshow(np.where(sub, 1.0, np.nan), extent=[ii[0] - 0.5, ii[-1] + 0.5, jj[-1] + 0.5, jj[0] - 0.5],
                      cmap=ListedColormap(["#5598e7"]), interpolation="nearest")
            a, b, c, d = fl[n]
            ax.annotate("", xy=(c, d), xytext=(a, b), arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.8))
            ax.plot(i0, j0, "o", ms=6, mfc="white", mec=INK, mew=1.3)
            ax.set_xlim(ii[0] - 0.5, ii[-1] + 0.5); ax.set_ylim(jj[-1] + 0.5, jj[0] - 0.5)
            ax.set_aspect("equal"); ax.tick_params(labelsize=7.5); ax.grid(False)
            ax.set_title(f"{res.replace('m', ' m')}: " + T(f"測線 {n}", f"transect {n}"), fontsize=9.5)
    fig.suptitle(T("各解像度の河道マスク(青)に重ねた測線(赤。右岸 → 左岸)とプローブ(○)。軸はセル番号",
                   "Transects (red; right bank to left bank) and probes (o) over the channel mask (blue) on each grid; axes are cell numbers"),
                 fontsize=11)
    fig.tight_layout()
    save(fig, "transects.png")


def hydro_axes(ax, title, xmax=360, ymax=None):
    ax.set_xlim(0, xmax)
    if ymax:
        ax.set_ylim(0, ymax)
    ax.set_xlabel(T("時間 (分)", "time (min)")); ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    ax.set_title(title)


def base():
    if not have("200m"):
        return
    fig = plt.figure(figsize=(12, 4.3))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.25], wspace=0.15)
    ax = fig.add_subplot(gs[0])
    for n in range(1, 5):
        t, q = flux("200m", n)
        ax.plot(t, q, color=C_TR[n - 1], label=T(f"測線 {n}", f"transect {n}"))
    hydro_axes(ax, T("(a) 測線 1〜4 のハイドログラフ(200 m 格子)", "(a) Hydrographs at transects 1-4 (200 m grid)"), ymax=9500)
    ax.legend(loc="upper right")
    ax = fig.add_subplot(gs[1])
    im = depth_map(ax, grid("result_200m/H0002.txt"), T("(b) t = 2 時間の水深", "(b) Depth at t = 2 h"))
    cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.01); cb.set_label(T("水深 (m)", "depth (m)"))
    save(fig, "base.png")


def dem():
    cases = [("200m_raw", T("元の DEM(窪地除去なし)", "original DEM (no depression filling)")),
             ("200m_filled", T("窪地除去済みの標高", "depression-filled elevation")),
             ("200m", T("河床を整えた標高(基本)", "conditioned bed (base)")),
             ("200m_4nb", T("河床を整えた標高・4 近傍", "conditioned bed, 4 neighbours"))]
    cases = [(c, l) for c, l in cases if have(c)]
    if len(cases) < 2:
        return
    fig, axs = plt.subplots(2, 2, figsize=(12, 6.2))
    for ax, (c, lab) in zip(axs.flat, cases):
        im = depth_map(ax, grid(f"result_{c}/H9998.txt"), lab, vmax=10.0)
    for ax in list(axs.flat)[len(cases):]:
        ax.axis("off")
    fig.colorbar(im, ax=axs, shrink=0.7, pad=0.01).set_label(T("6 時間後の水深 (m)", "depth after 6 h (m)"))
    fig.suptitle(T("地形の扱いを変えた計算の 6 時間後の水深(200 m 格子。流域出口は開けてある)",
                   "Depth after 6 hours with different terrain treatments (200 m grid; the outlet is open)"), fontsize=11)
    save(fig, "dem.png")


def bed_effect():
    pairs = [(r, f"{r}_filled") for r in ("200m", "100m") if have(r) and have(f"{r}_filled")]
    if not pairs:
        return
    fig, axs = plt.subplots(1, len(pairs), figsize=(6.0 * len(pairs), 4.0), squeeze=False)
    for ax, (c, cf) in zip(axs[0], pairs):
        for n in range(1, 5):
            t, q = flux(c, n); ax.plot(t, q, color=C_TR[n - 1], label=T(f"測線 {n}", f"transect {n}"))
            t, q = flux(cf, n); ax.plot(t, q, color=C_TR[n - 1], ls="--", lw=1.2)
        hydro_axes(ax, T(f"{c[:-1]} m 格子(実線: 河床を整えた標高、破線: 窪地除去済み)",
                         f"{c[:-1]} m (solid: conditioned bed; dashed: filled)"), ymax=9500)
        ax.legend(loc="upper right")
    save(fig, "bed_effect.png")


def loss():
    if not (have("200m") and have("200m_loss")):
        return
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.0))
    ax = axs[0]
    for n in range(1, 5):
        t, q = flux("200m", n); ax.plot(t, q, color=C_TR[n - 1], label=T(f"測線 {n}", f"transect {n}"))
        t, q = flux("200m_loss", n); ax.plot(t, q, color=C_TR[n - 1], ls="--", lw=1.2)
    hydro_axes(ax, T("(a) ハイドログラフ(実線: 損失なし、破線: 遮断と浸透あり)", "(a) Hydrographs (solid: no losses; dashed: with losses)"), ymax=9500)
    ax.legend(loc="upper right")
    ax = axs[1]
    t, a, h = storage("200m")
    ax.plot(t, a[:, h.index("S(m)") - 1] * 1000, color=INK, label=T("損失なし: 流域の水", "no losses: water in the catchment"))
    t, a, h = storage("200m_loss")
    ax.plot(t, a[:, h.index("S_total(m)") - 1] * 1000, color="#2a78d6", label=T("遮断と浸透あり: 地表 + 地下", "with losses: surface + ground"))
    ax.plot(t, a[:, h.index("S_grnd(m)") - 1] * 1000, color="#2a78d6", ls="--", lw=1.2, label=T("遮断と浸透あり: 地下", "with losses: ground"))
    ax.set_xlim(0, 360); ax.set_ylim(0, 110)
    ax.set_xlabel(T("時間 (分)", "time (min)")); ax.set_ylabel(T("流域平均の水深換算 (mm)", "catchment-mean depth (mm)"))
    ax.set_title(T("(b) 流域の水量(画面の S 列。出口から出た分だけ減る)", "(b) Water in the catchment (screen S columns)"))
    ax.legend(loc="upper right")
    save(fig, "loss.png")


def outlet():
    if not (have("200m") and have("200m_closed")):
        return
    fig = plt.figure(figsize=(12.5, 7.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.15], hspace=0.32, wspace=0.18)
    ax = fig.add_subplot(gs[0, 0])
    for c, ls, lab in (("200m", "-", T("出口を開ける(基本)", "outlet open (base)")), ("200m_closed", "--", T("出口を閉じる", "outlet closed"))):
        t, q = flux(c, 4); ax.plot(t, q, color=C_TR[3], ls=ls, label=lab)
    hydro_axes(ax, T("(a) 測線 4 の流量", "(a) Discharge at transect 4"), ymax=9500)
    ax.legend(loc="upper right")
    ax = fig.add_subplot(gs[0, 1])
    for c, ls, lab in (("200m", "-", T("出口を開ける(基本)", "outlet open (base)")), ("200m_closed", "--", T("出口を閉じる", "outlet closed"))):
        t, h = probe(c, 4); ax.plot(t, h, color=C_TR[3], ls=ls, label=lab)
    ax.set_xlim(0, 360); ax.set_xlabel(T("時間 (分)", "time (min)")); ax.set_ylabel(T("水深 (m)", "depth (m)"))
    ax.set_title(T("(b) プローブ 4 の水深", "(b) Depth at probe 4")); ax.legend(loc="upper left")
    for k, (c, lab) in enumerate((("200m_closed", T("(c) 出口を閉じたときの 6 時間後の水深", "(c) Depth after 6 h with the outlet closed")),
                                  ("200m", T("(d) 出口を開けたときの 6 時間後の水深", "(d) Depth after 6 h with the outlet open")))):
        ax = fig.add_subplot(gs[1, k])
        im = depth_map(ax, grid(f"result_{c}/H9998.txt"), lab, vmax=30.0)
    fig.colorbar(im, ax=fig.axes[2:], shrink=0.75, pad=0.01).set_label(T("水深 (m)", "depth (m)"))
    save(fig, "outlet.png")


def resolution():
    rows = [("", T("ENC(8 方向の交換)", "ENC (8-direction exchange)")), ("_4nb", T("4 近傍(p_diagratio = 0)", "4 neighbours (p_diagratio = 0)"))]
    fig, axs = plt.subplots(2, 2, figsize=(12, 7.0))
    for r_i, (sfx, lab) in enumerate(rows):
        for c_i, (n, ymax) in enumerate(((1, (1600, 100)), (4, (10000, 100)))):
            ax = axs[r_i, c_i]
            for res in ("200m", "100m", "50m"):
                if have(res + sfx):
                    t, q = flux(res + sfx, n); ax.plot(t, q, color=C_RES[res], label=res.replace("m", " m"))
            up = T("上流", "upstream") if n == 1 else T("下流", "downstream")
            hydro_axes(ax, f"{lab}: {up} " + T(f"測線 {n}", f"transect {n}"), xmax=150 if n == 1 else 360, ymax=ymax[r_i])
            ax.legend(loc="upper right")
    fig.tight_layout()
    save(fig, "resolution.png")


def width():
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
    for ax, n in zip(axs, (3, 4)):
        for case, color, ls, lab in (("200m", C_RES["200m"], "--", T("200 m 幅なし", "200 m, no width")), ("200m_w50", C_RES["200m"], "-", "200 m W = 50"),
                                     ("100m", C_RES["100m"], "--", T("100 m 幅なし", "100 m, no width")), ("100m_w50", C_RES["100m"], "-", "100 m W = 50"),
                                     ("50m", C_RES["50m"], "-", T("50 m(解像河道)", "50 m (resolved channel)")), ("50m_w50", C_RES["50m"], ":", "50 m W = 50")):
            if have(case):
                t, q = flux(case, n); ax.plot(t, q, color=color, ls=ls, lw=1.2 if ls != "-" else 1.6, label=lab)
        hydro_axes(ax, T(f"測線 {n}", f"Transect {n}"), xmax=240 if n == 3 else 360, ymax=10000)
        ax.legend(loc="upper right")
    fig.suptitle(T("河道幅を 50 m に揃えた比較(実線: W = 50 m のサブグリッド河道、破線: 幅なし)",
                   "Channel width equalized to 50 m (solid: subgrid channel W = 50 m; dashed: no width)"), fontsize=11)
    save(fig, "width.png")


def advection():
    rows = [("_noadv", T("移流項なし(拡散波)", "no advection term (diffusion wave)")),
            ("_s1u", T("スキーム 1(風上化 0.1)", "scheme 1 (upwind 0.1)")),
            ("_s1", T("スキーム 1(風上化 0.5)", "scheme 1 (upwind 0.5)")),
            ("_s1f", T("スキーム 1(風上化 1.0)", "scheme 1 (upwind 1.0)")),
            ("", T("スキーム 3(既定)", "scheme 3 (default)"))]
    fig, axs = plt.subplots(len(rows), 2, figsize=(12, 2.6 * len(rows)), sharex="col")
    for r_i, (sfx, lab) in enumerate(rows):
        for c_i, n in enumerate((1, 4)):
            ax = axs[r_i, c_i]
            for res in ("200m", "100m", "50m"):
                if have(res + sfx):
                    t, q = flux(res + sfx, n); ax.plot(t, q, color=C_RES[res], label=res.replace("m", " m"))
            ax.set_xlim(0, 150 if n == 1 else 360); ax.set_ylim(0, 1700 if n == 1 else 15000)
            ax.set_title(f"{lab}: " + T(f"測線 {n}", f"transect {n}"))
            ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
            if r_i == len(rows) - 1:
                ax.set_xlabel(T("時間 (分)", "time (min)"))
            if r_i == 0:
                ax.legend(loc="upper right")
    fig.tight_layout()
    save(fig, "advection.png")


def roughness():
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
    for ax, res in zip(axs, ("200m", "100m")):
        for sfx, color, ls, lab in (("", "#444444", "-", T("粗度 0.04・スキーム 3", "roughness 0.04, scheme 3")),
                                    ("_noadv", "#444444", "--", T("粗度 0.04・移流項なし", "roughness 0.04, no advection")),
                                    ("_n02", "#e08a00", "-", T("粗度 0.02・スキーム 3", "roughness 0.02, scheme 3")),
                                    ("_n02_noadv", "#e08a00", "--", T("粗度 0.02・移流項なし", "roughness 0.02, no advection"))):
            if have(res + sfx):
                t, q = flux(res + sfx, 4); ax.plot(t, q, color=color, ls=ls, label=lab)
        hydro_axes(ax, T(f"{res[:-1]} m 格子の測線 4", f"Transect 4 on the {res[:-1]} m grid"), ymax=30000)
        ax.legend(loc="upper right")
    save(fig, "roughness.png")


if __name__ == "__main__":
    for f in (setup, bed, transects, base, dem, bed_effect, loss, outlet, resolution, width, advection, roughness):
        f()
