#!/usr/bin/env python3
"""debris_dam の図と数表(事前に make run で全ケースを、make perturb で結果の幅を見るケースを計算しておく)。

  figs/setup.png      地形(本川・盆地・支流・崩壊斜面・集落)と縦断(入力だけ。計算結果を使わない)
  figs/sequence.png   基本ケースの経過(崩壊の前 → 土石流 → 天然ダム → 湛水 → 越流 → 決壊の後)
  figs/series.png     基本ケースの時系列(雨と崩壊、土砂の行き先、湖の水位と堤体の高さ、流量)
  figs/profile.png    基本ケースの本川の縦断(堤体と水面の時間変化)
  figs/chain.png      連鎖のケースの比較(基本・仮排水路・粗い土砂・流量 2 倍)
  figs/village.png    集落の最大流動深と家屋の破壊率(基本・粗い土砂・仮排水路)
  figs/spread.png     流入量を少し変えた計算の流量(結果の幅。連鎖の基本ケース、天端が水平な堤体、天端が傾いた堤体の
                      10 m 格子と 5 m 格子)と、天端の横断形
  figs/formation.png  堤体のできかたの比較(間隙水の扱い・斜面安定判定の選択子・格子間隔・判定する深さ)
  figs/breach.png     堤体をはじめから置く系列の流量(湛水量・堤体の形・粒径・流入量・下流の勾配と格子・式)
  figs/breach_sum.png 同じ系列のピーク流量と立ち上がりの時間、経験式との比較
  figs/mixed.png      粒度の幅を持つ堤体(混合粒径と土石流の併用)の決壊と、決壊のあとの 6 時間(掃流砂だけ)
数表(標準出力): 各ケースの指標。README の表はここから写す。
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。計算結果のないケースは飛ばす。
引数 mixed で、mixed.png とその数表だけを作る(make mixed の 4 ケースだけを計算したとき)。
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, ListedColormap

import make_init as M

EN = "en" in sys.argv[1:]
ONLY_MIXED = "mixed" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

CSTAR = 1.0 - M.LAMBDA
GRAV = 9.8
TERRAIN = ListedColormap(plt.get_cmap("gist_earth")(np.linspace(0.35, 0.95, 256)))
COL = {"water": "#1f5f8b", "dep": "#8b4a10", "mix": "#c0392b", "rain": "#4a7fb5", "crest": "#5b3a1a"}
CHAIN = ("base", "drain", "coarse", "q80")
TDAM = 60.0     # 堤体を置く系列で、残った堤体の高さと水位を比べる時刻(分。最も短いケースの計算時間)
FORM = ("base", "wet0", "wet2", "slide0", "noflow0", "g5", "dmax15", "dmax15_dx5")
LAB = {   # ケースの呼び名
    "base": ("基本", "base"), "drain": ("仮排水路", "drain"), "coarse": ("粗い土砂(10 cm)", "coarse (10 cm)"),
    "q80": ("流量 2 倍(80 m³/s)", "double inflow (80 m³/s)"),
    "norain": ("雨なし", "no rain"), "wet0": ("間隙水を連行しない", "no pore-water entrainment"),
    "wet2": ("保持水を授受しない", "no retained water"), "slide0": ("安定判定の選択子なし", "no stability options"),
    "noflow0": ("濃い混合体の下も判定", "judged under a dense mixture"),
    "g5": ("5 m 格子", "5 m grid"), "dmax15": ("slide_dmax = 1.5 m", "slide_dmax = 1.5 m"),
    "dmax15_dx5": ("slide_dmax = 1.5 m、5 m 格子", "slide_dmax = 1.5 m, 5 m grid"),
    "dam_ref": ("基準(法面 0.12、盆地 150 m)", "reference (faces 0.12, basin 150 m)"),
    "dam_face25": ("法面 0.25(1:4)", "faces 0.25 (1:4)"), "dam_crest40": ("法面 0.25、天端 40 m", "faces 0.25, crest 40 m"),
    "dam_small": ("湛水量 小(峡谷だけ)", "small lake (gorge only)"), "dam_large": ("湛水量 大(盆地 300 m)", "large lake (basin 300 m)"),
    "dam_d1cm": ("粒径 1 cm", "grain 1 cm"), "dam_d10cm": ("粒径 10 cm", "grain 10 cm"),
    "dam_delte": ("侵食係数 δe = 0.0001", "erosion coefficient δe = 0.0001"),
    "dam_q20": ("流入 20 m³/s", "inflow 20 m³/s"), "dam_q80": ("流入 80 m³/s", "inflow 80 m³/s"),
    "dam_steep": ("下流の勾配 0.10", "downstream slope 0.10"), "dam_nofluv": ("掃流砂なし", "no bed load"),
    "dam_tau1": ("掃流砂の有効掃流力の比 1", "bed load with full shear stress"),
    "dam_imm0": ("緩勾配の式なし(f_dbimm = 0)", "no gentle-slope law (f_dbimm = 0)"),
    "dam_unsat": ("不飽和の堤体", "unsaturated dam"), "dam_unsat0": ("不飽和の堤体、飽和床の式", "unsaturated dam, saturated-bed law"),
    "dam_dx5": ("5 m 格子(slide_dmax = 1.5 m)", "5 m grid (slide_dmax = 1.5 m)"),
    "dam_dx5d3": ("5 m 格子、slide_dmax = 3 m のまま", "5 m grid, slide_dmax kept at 3 m"),
    "dam_tilt": ("天端が傾いた堤体(支流の側が高い)", "tilted crest (higher on the tributary side)"),
    "dam_tilt_dx5": ("天端が傾いた堤体、5 m 格子", "tilted crest, 5 m grid"),
    "mix_breach": ("粒度の幅を持つ堤体(0.5・2・8 cm)", "graded dam (0.5, 2, 8 cm)"),
    "mix_after": ("粒度の幅、掃流砂だけ", "graded, bed load only"),
    "one_after": ("単一粒径、掃流砂だけ", "single size, bed load only"),
    "mix_after_debris": ("粒度の幅、土石流の式を有効にしたまま", "graded, debris-flow laws kept on"),
    "one_after_debris": ("単一粒径、土石流の式を有効にしたまま", "single size, debris-flow laws kept on"),
}


def lab(name):
    """ケースの呼び名。流入量を少し変えたケース(M.PERT_OF)は、流入量と、もとのケースからの差で呼ぶ。"""
    if name in M.PERT_OF:
        q, q0 = M.case_inflow(name), M.case_inflow(M.PERT_OF[name])
        pc = f"{(q / q0 - 1.0) * 100.0:+.5f}".rstrip("0").rstrip(".").replace("-", "−")
        return T(f"流入 {q:g} m³/s({pc} %)", f"inflow {q:g} m³/s ({pc} %)")
    return T(*LAB[name])


# ---------------------------------------------------------------- 読み込み
class Case:
    """1 ケースの結果(分布は bil、時系列は計測点・流量測線の CSV)。"""

    def __init__(self, name):
        self.name = name
        self.geom, self.rep, self.add = M.CASES[name]
        self.qin = M.case_inflow(name)
        self.rdir = f"result_{name}"
        self.g, self.x, self.y, self.z0, self.zini, self.sdini = M.fields(self.geom)   # z0: 堤体のない地盤
        self.dx, self.sk = self.g["dx"], self.g["sk"]
        self.nx, self.ny, self.xc, self.yc = M.grid(self.dx)
        self.slab = M.slab_mask(self.x, self.y) & (self.g["dam"] is None)
        self.ok = os.path.exists(f"{self.rdir}/Z9998.bil")
        self.frames = []
        if self.ok:
            for ln in open(f"{self.rdir}/FILENUMBER.csv"):
                if ln.startswith("#"):
                    continue
                a = ln.split(",")
                if int(a[0]) < 9000:
                    self.frames.append((int(a[0]), float(a[2])))
        self._hyd = None

    def bil(self, name):
        return np.fromfile(f"{self.rdir}/{name}.bil", dtype="<f4").reshape(self.ny, self.nx).astype(float)

    def frame(self, key, k):
        return self.bil(f"{key}{k:04d}")

    def nearest(self, tmin):
        """時刻 tmin (分) に最も近いフレーム (番号, 時刻 s)。"""
        return min(self.frames, key=lambda f: abs(f[1] - 60.0 * tmin))

    def csv(self, kind, n):
        rows = []
        sub = {"flux": "fluxes", "probe": "probes"}[kind]
        for ln in open(f"{self.rdir}/{sub}/{kind}{n:04d}.csv"):
            if ln.startswith("#") or not ln.strip():
                continue
            try:
                rows.append([float(v) for v in ln.replace(",", " ").split()])
            except ValueError:
                pass
        m = min(len(r) for r in rows)
        return np.array([r[:m] for r in rows])

    def hydro(self):
        """時系列 (時刻 分, 堤体の直下 x = 1100 m の流量, 集落 x = 2400 m の流量, 湖の水位 = x = 800 m の水位)。
        x = 800 m は堤体のすぐ上流で、せき止めの前は川の水位、湖が引いたあとは残った水たまりの水位になる。"""
        if self._hyd is None:
            f2, f4, p1 = self.csv("flux", 2), self.csv("flux", 4), self.csv("probe", 2)
            n = min(len(f2), len(f4), len(p1))
            self._hyd = (f2[:n, 1], f2[:n, 2], f4[:n, 2], p1[:n, 2] + p1[:n, 3])
        return self._hyd

    # ---- 地形から求める量
    def thalweg(self, z):
        """本川の縦断: 各 x で、谷を横切る向きの最低の地盤高(谷底と、堆積で埋まった谷壁の脚を含む)。"""
        band = (self.y > -(M.WG / 2 + 30.0)) & (self.y < M.WG / 2 + 30.0 + M.basin_north(self.x, self.g["wb"]))
        return np.where(band, z, 1.0e9).min(axis=0)

    def dam(self, z):
        """堤体の天端: 縦断(各 x の最低点)の元の河床からの高さが最大の点。戻り値は (x, 天端の標高, 高さ)。"""
        prof = self.thalweg(z)
        prof0 = self.thalweg(self.z0)
        seg = (self.xc > M.XT - 150.0) & (self.xc < M.XT + 250.0)
        rise = np.where(seg, prof - prof0, -1.0)
        i = int(np.argmax(rise))
        return self.xc[i], prof[i], rise[i]

    def storage(self, z, level, xdam):
        """湛水量: 堤体の天端より上流で、水位 level の下にある谷の体積 (m³)。"""
        up = (self.x < xdam) & (self.y < M.WG / 2 + 30.0 + M.basin_north(self.x, self.g["wb"]) + 60.0)
        return float(np.clip(level - z, 0.0, None)[up].sum() * self.dx ** 2)


def series(c):
    """フレームごとの量(時刻 分、崩積土の残り、本川・支流の堆積、流動中の固体、堤体の高さ・天端・位置)。"""
    area = c.dx * c.dx
    main = c.y < M.WG / 2
    out = []
    for k, t in c.frames:
        z = c.frame("Z", k)
        sd = c.frame("Sd", k)
        hs = c.frame("Hs", k)
        dz = z - c.z0
        xd, zc, hd = c.dam(z)
        out.append((t / 60.0, sd[c.slab].sum() * area,
                    dz[main & (dz > 0)].sum() * area,
                    dz[~main & ~c.slab & (dz > 0)].sum() * area,
                    hs.sum() * area / CSTAR, hd, zc, xd))
    return np.array(out)


def metrics(c):
    """越流・決壊の指標。時刻は分、流量は m³/s、標高は m。値のない項目は None。"""
    t, q2, q4, lake = c.hydro()
    qin = c.qin
    m = dict(qin=qin, tov=None, tpk=None, qpk=None, qpk_v=None, rise=None, lake_max=None, lake_end=lake[-1],
             drop10=None, hdam0=None, hdam1=None, vlake=None, xdam=None)
    i0 = 0
    if c.g["dam"] is None:                                     # 連鎖: せき止めで下流の流量がほぼ 0 になった後
        blocked = (t > 5.0) & (q2 < 0.1 * qin)
        if not blocked.any():
            return m
        i0 = int(np.argmax(blocked))
    k0, t0 = c.nearest(t[i0] + (15.0 if c.g["dam"] is None else 0.0))    # 堤体のできた時点(連鎖はせき止めの 15 分後)
    xd, zc, hd = c.dam(c.frame("Z", k0))
    m.update(hdam0=hd, xdam=xd, zc0=zc, vlake=c.storage(c.frame("Z", k0), zc, xd))
    kend = c.frames[-1][0] if c.g["dam"] is None else c.nearest(TDAM)[0]     # 系列は TDAM 分の時点でそろえる
    m["hdam1"] = c.dam(c.frame("Z", kend))[2]
    m["lake_max"] = lake[i0:].max()
    if c.g["dam"] is not None:
        m["lake_end"] = lake[int(np.argmin(np.abs(t - TDAM)))]
    over = (np.arange(len(t)) > i0) & (q2 > 0.25 * qin)        # 越流で下流の流量が戻る
    if not over.any():
        return m
    iov = int(np.argmax(over))
    m["tov"] = t[iov]
    ipk = iov + int(np.argmax(q2[iov:]))
    m.update(tpk=t[ipk], qpk=q2[ipk], qpk_v=q4[iov:].max())
    eq = (np.arange(len(t)) >= iov) & (q2 >= qin)              # 流出が流入を超える
    if eq.any():
        m["rise"] = t[ipk] - t[int(np.argmax(eq))]
    n10 = int(round(10.0 / (t[1] - t[0])))
    if len(t) > iov + n10:
        m["drop10"] = float((lake[iov:-n10] - lake[iov + n10:]).max())
    return m


def dip_ratio(c, m):
    """決壊の途中の流量の落ち込み: 越流の開始からピークまでの間の、(流量)/(それまでの最大の流量)の最小。
    0.5 より小さければ、流量がいったん半分以下に落ちてからピークになった(決壊口がふさがれた)ことを表す。"""
    if m["tov"] is None:
        return None
    t, q2, q4, lake = c.hydro()
    seg = q2[(t >= m["tov"]) & (t <= m["tpk"])]
    run = np.maximum.accumulate(seg)
    ok = run >= 2.0 * c.qin                      # 流量が流入量の 2 倍を超えてから数える
    return float((seg[ok] / run[ok]).min()) if ok.any() else 1.0


def costa(v, h):
    """Costa (1988) の経験式のピーク流量 Q = 181 (V h / 10⁶)^0.43(土木研究所 2008 の引用による)。"""
    return 181.0 * (v * h / 1.0e6) ** 0.43


def tabata(h, qin, slope=M.S0, width=M.WG):
    """田畑らの式のピーク流量(土木研究所 2008 の表記のとおり。q/q_in = 0.542 [(g h³)^0.5 / (tanθ q_in 1000)]^0.565、
    q・q_in は単位幅の流量 m²/s)。谷底幅 width を掛けて m³/s で返す。"""
    q_in = qin / width
    return 0.542 * ((GRAV * h ** 3) ** 0.5 / (slope * q_in * 1000.0)) ** 0.565 * q_in * width


def ishikawa(v, h, width=M.WG):
    """石川ら (1992) の推定式(単位幅流入量 1.0 m²/s の場合。q = 0.960 (S H / 10⁴)^0.283、S は単位幅の貯水量 m²)。
    S = 貯水量 / 谷底幅 とし、谷底幅を掛けて m³/s で返す。"""
    return 0.960 * ((v / width) * h / 1.0e4) ** 0.283 * width


def houses(c):
    """家屋の被害: (家屋のセル数, 破壊率の平均, 破壊率 0.5 以上のセル数, 破壊率 0.05 以上のセル数)。"""
    hm = M.house_mask(c.x, c.y, c.dx)
    bs = c.bil("Bs9998")[hm]
    return int(hm.sum()), float(bs.mean()), int((bs >= 0.5).sum()), int((bs >= 0.05).sum())


def house_rows(c):
    """家屋の列ごとの破壊率の平均(岸に近い列から)。"""
    hm = M.house_mask(c.x, c.y, c.dx)
    bs = c.bil("Bs9998")
    d = c.y - M.channel_half(c.x)
    return [float(bs[hm & (np.abs(d - yy) < M.HOUSE_W / 2)].mean()) for yy in M.HOUSE_ROWS]


def f(v, fmt="%.0f"):
    return "—" if v is None else fmt % v


# ---------------------------------------------------------------- 図: 地形
def hillshade(z, dx):
    return LightSource(azdeg=315, altdeg=45).hillshade(z, vert_exag=1.0, dx=dx, dy=dx)


def fig_setup():
    dx = 10.0
    nx, ny, xc, yc = M.grid(dx)
    x, y = np.meshgrid(xc, yc)
    z = M.terrain(x, y)
    ext = [0, M.LX, M.Y0, M.Y1]
    fig = plt.figure(figsize=(13.0, 8.8))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1.0], hspace=0.28, wspace=0.2)
    ax = fig.add_subplot(gs[0, :])
    ax.imshow(hillshade(z, dx), cmap="gray", extent=ext, vmin=0, vmax=1, alpha=0.9)
    ax.imshow(z, cmap=TERRAIN, extent=ext, alpha=0.55)
    cs = ax.contour(x, y, z, levels=np.arange(0, 330, 20), colors="k", linewidths=0.35, alpha=0.6)
    ax.clabel(cs, levels=np.arange(0, 330, 60), fontsize=7, fmt="%d m")
    slab = M.slab_mask(x, y)
    ax.contourf(x, y, slab.astype(float), levels=[0.5, 1.5], colors=["#c0392b"], alpha=0.45)
    rain = M.rain_mask(x, y)
    ax.contour(x, y, rain.astype(float), levels=[0.5], colors=[COL["rain"]], linewidths=1.2, linestyles="--")
    hm = M.house_mask(x, y, dx)
    ax.plot(x[hm], y[hm], "s", ms=2.2, color="#1f3f6b")
    for xx in M.FLUX_X:
        ax.plot([xx, xx], [-60, 60], color="k", lw=1.0)
        ax.text(xx, 70, f"Q {xx:g}", fontsize=7, ha="center")
    ax.plot([M.CULV_XIN, M.CULV_XOUT], [-8, -8], color="#7d3c98", lw=1.6, ls=":")
    ax.text(0.5 * (M.CULV_XIN + M.CULV_XOUT) - 180, -75, T("仮排水路(ケース drain)", "drain pipe (case drain)"), fontsize=8, color="#7d3c98")
    ax.annotate(T("崩壊斜面(崩積土 3 m・15 万 m³)", "failure slope (colluvium 3 m, 150,000 m³)"),
                xy=(M.XT + 60, M.YH + M.LF + 150), xytext=(M.XT + 260, M.YH + 250), fontsize=9, color="#8b1a10",
                arrowprops=dict(arrowstyle="-", color="#8b1a10", lw=0.8))
    ax.annotate(T("雨域(破線)", "rain area (dashed)"), xy=(M.XT - 100, M.YH + 120), xytext=(M.XT - 520, M.YH + 200),
                fontsize=9, color=COL["rain"], arrowprops=dict(arrowstyle="-", color=COL["rain"], lw=0.8))
    ax.text(M.XT + 40, 170, T("支流(勾配 0.20 → 0.40)", "tributary (slope 0.20 → 0.40)"), fontsize=9)
    ax.text(420, 60, T("盆地(谷底幅 150 m)", "basin (floor 150 m wide)"), fontsize=9, ha="center")
    ax.text(1150, -105, T("本川(流量 40 m³/s、勾配 0.02、峡谷の谷底幅 40 m)→", "main river (40 m³/s, slope 0.02, gorge floor 40 m) →"), fontsize=9)
    ax.text(2500, 230, T("集落(氾濫原の家屋)", "village (houses on the floodplain)"), fontsize=9, ha="center", color="#1f3f6b")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(T("地形(等高線 20 m おき。赤 = 崩積土、青の点 = 家屋、縦線 = 流量測線)",
                   "Terrain (contours every 20 m; red = colluvium, blue dots = houses, bars = discharge lines)"), fontsize=10)
    ax.set_aspect("equal")

    ax = fig.add_subplot(gs[1, 0])
    xs = np.linspace(0, M.LX, 601)
    ax.plot(xs, M.zf_axis(xs), color="k", lw=1.6, label=T("本川の河床", "main river bed"))
    xd = np.linspace(M.XT - 130, M.XT + 130, 200)
    hd, lc, sup, sdn = M.geom("d12")["dam"]
    top = M.zf_axis(M.XT) + hd - sup * np.clip(M.XT - lc / 2 - xd, 0, None) - sdn * np.clip(xd - M.XT - lc / 2, 0, None)
    ax.plot(xd, np.maximum(top, M.zf_axis(xd)), color="#8b4a10", lw=1.2, ls="--",
            label=T("はじめから置く堤体(高さ 13 m、法面 0.12。系列 dam_*)", "pre-built dam (13 m high, faces 0.12; series dam_*)"))
    ax.axvspan(M.XB0 + M.LB, M.XB1, color=COL["water"], alpha=0.08)
    ax.text(0.5 * (M.XB0 + M.LB + M.XB1), 12.0, T("盆地", "basin"), fontsize=8, ha="center", color=COL["water"])
    ax.axvline(M.XT, color="gray", lw=0.6)
    ax.text(M.XT + 15, 20.0, T("合流点", "junction"), fontsize=8)
    ax.axvspan(M.HOUSE_X[0], M.HOUSE_X[1], color="#1f3f6b", alpha=0.08)
    ax.text(0.5 * sum(M.HOUSE_X), 40.0, T("集落", "village"), fontsize=8, ha="center", color="#1f3f6b")
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.legend(fontsize=8, loc="upper right")
    ax.set_title(T("本川の縦断", "Long profile of the main river"), fontsize=10)

    ax = fig.add_subplot(gs[1, 1])
    ys = np.linspace(M.WG / 2, M.Y1, 400)
    ax.plot(ys, M.trib_axis(ys), color="k", lw=1.6)
    y1, y2 = M.YH + M.LF, M.YH + M.LF + M.LS
    seg = (ys >= y1) & (ys <= y2)
    ax.plot(ys[seg], M.trib_axis(ys[seg]) + M.DS, color="#c0392b", lw=2.2, label=T("崩積土(厚さ 3 m)", "colluvium (3 m thick)"))
    for yy in (60.0, 250.0):
        sl = M.SA + (M.SB - M.SA) * (yy - M.WG / 2) / (M.YH - M.WG / 2)
        ax.text(yy, M.trib_axis(yy) + 14, f"{sl:.2f}", fontsize=8, ha="center")
    ax.text(500.0, M.trib_axis(500.0) + 14, f"{M.SR:.2f}", fontsize=8, ha="center")
    ax.axvline(M.YH, color="gray", lw=0.6)
    ax.text(M.YH + 5, ax.get_ylim()[0] + 6, T("谷頭", "valley head"), fontsize=8)
    ax.text(M.WG / 2 + 10, 250, T("数字 = 勾配", "numbers = slope"), fontsize=8)
    ax.set_xlabel(T("y (m)  合流点から支流を上る向き", "y (m)  up the tributary from the junction"))
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.legend(fontsize=8, loc="lower right")
    ax.set_title(T("支流と崩壊斜面の縦断", "Long profile of the tributary and the failure slope"), fontsize=10)
    fig.savefig(f"{FIGDIR}/setup.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 基本ケースの経過
def fail_time(s):
    """崩積土が半分を切る時刻(分。分布出力の間隔の精度)。"""
    t, v = s[:, 0], s[:, 1]
    return float(t[np.argmax(v < 0.5 * v[0])]) if (v < 0.5 * v[0]).any() else None


def arrival_time(c):
    """土石流が合流点に届く時刻(分。合流点のすぐ上流の計測点 x = 880 m に土砂が現れる時刻。10 秒の精度)。"""
    p = c.csv("probe", 3)
    return float(p[np.argmax(p[:, 9] > 0.05), 1]) if (p[:, 9] > 0.05).any() else None


def fig_sequence(c, s, tf, m):
    """基本ケースの経過の 6 コマ(盆地から合流点の下流まで)。"""
    tov, tpk = m["tov"], m["tpk"]
    times = [tf - 2.0, tf + 1.0, tf + 8.0, 0.5 * (tf + 8.0 + tov), tpk, c.frames[-1][1] / 60.0]
    labels = [T("崩壊の直前(雨で地下水位が上がる)", "just before the failure (rain raises the groundwater)"),
              T("崩壊 → 土石流が支流を下る", "failure → debris flow runs down the tributary"),
              T("本川をせき止める(天然ダム)", "the main river is blocked (natural dam)"),
              T("上流の盆地に水がたまる", "water ponds in the basin upstream"),
              T("越流が堤体を削り、流量がピークになる", "overtopping erodes the dam; peak discharge"),
              T("決壊の後", "after the breach")]
    x0, x1, y0, y1 = 100.0, 1500.0, -100.0, 620.0
    ii = (c.xc >= x0) & (c.xc <= x1)
    jj = (c.yc >= y0) & (c.yc <= y1)
    ext = [c.xc[ii][0] - c.dx / 2, c.xc[ii][-1] + c.dx / 2, c.yc[jj][-1] - c.dx / 2, c.yc[jj][0] + c.dx / 2]
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 7.4), gridspec_kw=dict(hspace=0.22, wspace=0.14))
    for ax, tm, lb in zip(axes.flat, times, labels):
        k, t = c.nearest(tm)
        z = c.frame("Z", k)[np.ix_(jj, ii)]
        h = c.frame("H", k)[np.ix_(jj, ii)]
        hs = c.frame("Hs", k)[np.ix_(jj, ii)]
        sd = c.frame("Sd", k)[np.ix_(jj, ii)]
        dz = z - c.z0[np.ix_(jj, ii)]
        ax.imshow(hillshade(z, c.dx), cmap="gray", extent=ext, vmin=0, vmax=1)
        soil = np.ma.masked_where(~(c.slab[np.ix_(jj, ii)] & (sd > 0.5)), sd)
        ax.imshow(soil, cmap=ListedColormap(["#d9a441"]), extent=ext, alpha=0.75)
        dep = np.ma.masked_less(dz, 0.3)
        im_d = ax.imshow(dep, cmap="YlOrBr", extent=ext, vmin=0, vmax=14, alpha=0.9)
        wat = np.ma.masked_less(h, 0.1)
        im_w = ax.imshow(wat, cmap="Blues", extent=ext, vmin=0, vmax=12, alpha=0.8)
        mix = np.ma.masked_less(hs / CSTAR, 0.2)
        im_m = ax.imshow(mix, cmap="Reds", extent=ext, vmin=0, vmax=6, alpha=0.9)
        ax.set_title(f"{t / 60:.0f} " + T("分: ", "min: ") + lb, fontsize=10)
        ax.set_xlabel("x (m)", fontsize=8)
        ax.set_ylabel("y (m)", fontsize=8)
        ax.tick_params(labelsize=7)
    cax = fig.add_axes([0.92, 0.66, 0.012, 0.22])
    fig.colorbar(im_d, cax=cax).set_label(T("堆積の厚さ (m)", "deposit thickness (m)"), fontsize=8)
    cax = fig.add_axes([0.92, 0.39, 0.012, 0.22])
    fig.colorbar(im_w, cax=cax).set_label(T("水深 (m)", "water depth (m)"), fontsize=8)
    cax = fig.add_axes([0.92, 0.12, 0.012, 0.22])
    fig.colorbar(im_m, cax=cax).set_label(T("流動中の土砂の厚さ (m)", "thickness of moving sediment (m)"), fontsize=8)
    fig.suptitle(T("基本ケースの経過(黄 = 崩積土、赤 = 流動中の土砂、茶 = 堆積、青 = 水)",
                   "Sequence of the base case (yellow = colluvium, red = moving sediment, brown = deposit, blue = water)"),
                 fontsize=11, y=0.96)
    fig.savefig(f"{FIGDIR}/sequence.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


def fig_series(c, s, tf, m):
    """基本ケースの時系列。"""
    t = s[:, 0]
    th, q2, q4, lake = c.hydro()
    fig, axes = plt.subplots(4, 1, figsize=(10.5, 12.0), gridspec_kw=dict(hspace=0.3))
    ax = axes[0]
    sat, fsm = [], []
    for k, tt in c.frames:
        sd = c.frame("Sd", k)
        hg = c.frame("Hg", k)
        mk = c.slab & (sd > 0.9 * M.DS)
        many = mk.sum() > 0.2 * c.slab.sum()
        sat.append(np.mean(hg[mk] / (M.SY0 * sd[mk])) if many else np.nan)
        fs = c.frame("Fs", k)
        mm = mk & (fs > 0)
        fsm.append(np.median(fs[mm]) if many and mm.any() else np.nan)
    ax.plot(t, sat, color=COL["water"], lw=1.8, marker="o", ms=3, label=T("崩積土の飽和度(崩れる前。平均)", "saturation of the colluvium (before the failure; mean)"))
    ax.plot(t, fsm, color="#c0392b", lw=1.8, marker="o", ms=3, label=T("崩積土の安全率 Fs(崩れる前。中央値)", "safety factor Fs of the colluvium (before the failure; median)"))
    ax.axhline(1.0, color="#c0392b", lw=0.6, ls=":")
    ax.set_ylim(0.7, 1.15)
    ax.set_ylabel(T("飽和度、Fs", "saturation, Fs"))
    ax.set_xlim(0, 30)
    ax.set_xlabel(T("時刻 (分)。はじめの 30 分だけ", "time (min); first 30 minutes only"), fontsize=8)
    ax2 = ax.twinx()
    ax2.fill_between([0, 60.0], [80, 80], color=COL["rain"], alpha=0.15, step="post")
    ax2.set_ylim(0, 400)
    ax2.set_yticks([0, 80])
    ax2.set_ylabel(T("雨 (mm/h)", "rain (mm/h)"), color=COL["rain"])
    ax.legend(fontsize=8, loc="upper right")
    ax.set_title(T("(a) 雨の浸透と崩壊(雨は 60 分まで続く)", "(a) Rain infiltration and the failure (the rain lasts 60 minutes)"), fontsize=10, loc="left")

    ax = axes[1]
    ax.plot(t, s[:, 1] / 1e3, color="#d9a441", lw=1.8, label=T("斜面に残る崩積土", "colluvium left on the slope"))
    ax.plot(t, s[:, 4] / 1e3, color=COL["mix"], lw=1.8, label=T("流動中の土砂", "moving sediment"))
    ax.plot(t, s[:, 2] / 1e3, color=COL["dep"], lw=1.8, label=T("本川の堆積(堤体と、下流へ出た土砂)", "deposit in the main river (dam and sediment carried downstream)"))
    ax.plot(t, s[:, 3] / 1e3, color="#b08a5a", lw=1.4, ls="--", label=T("支流の堆積", "deposit in the tributary"))
    ax.set_ylabel(T("かさ体積 (千 m³)", "bulk volume (10³ m³)"))
    ax.legend(fontsize=8, ncol=2)
    ax.set_title(T("(b) 土砂の行き先", "(b) Where the sediment goes"), fontsize=10, loc="left")

    ax = axes[2]
    bed = float(M.zf_axis(M.XT, c.sk))
    ax.plot(th, lake, color=COL["water"], lw=1.8, label=T("堤体のすぐ上流の水位(x = 800 m)", "water level just upstream of the dam (x = 800 m)"))
    ax.plot(t, np.where(s[:, 5] > 0.5, s[:, 6], np.nan), color=COL["crest"], lw=1.8, label=T("堤体の天端(谷を横切る最低点)", "dam crest (lowest point across the valley)"))
    ax.axhline(bed, color="k", lw=0.6, ls=":")
    ax.text(0.45 * t[-1], bed + 0.3, T("合流点の元の河床", "original bed at the junction"), fontsize=8, ha="center")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.legend(fontsize=8, loc="lower center", bbox_to_anchor=(0.45, 0.12))     # 湖の水位の曲線の下の空いた所
    ax.set_title(T("(c) 湖の水位と堤体の高さ", "(c) Lake level and dam crest"), fontsize=10, loc="left")

    ax = axes[3]
    f1 = c.csv("flux", 1)
    ax.plot(f1[:, 1], f1[:, 2], color="gray", lw=1.2, label=T("上流端 x = 80 m(流入)", "upstream end x = 80 m (inflow)"))
    ax.plot(th, q2, color="#c0392b", lw=1.9, label=T("堤体の直下 x = 1100 m", "just below the dam x = 1100 m"))
    ax.plot(th, q4, color="#1f3f6b", lw=1.4, label=T("集落 x = 2400 m", "village x = 2400 m"))
    ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.legend(fontsize=8, loc="upper left")
    ax.set_title(T("(d) 流量", "(d) Discharge"), fontsize=10, loc="left")
    ta = arrival_time(c)
    for ax in axes:
        for tv in (ta, m["tov"]):
            if tv is not None:
                ax.axvline(tv, color="k", lw=0.6, ls="--")
        ax.grid(alpha=0.25)
    for ax in axes[1:]:
        ax.set_xlim(0, t[-1] * 1.02)
    axes[0].text(ta + 0.3, 0.72, T("崩壊した土砂が合流点に届く", "the failed mass reaches the junction"), fontsize=8)
    y0, y1 = axes[1].get_ylim()
    axes[1].text(ta + 2.0, y0 + 0.3 * (y1 - y0), T("崩壊", "failure"), fontsize=8)
    if m["tov"] is not None:
        axes[1].text(m["tov"] + 2.0, y0 + 0.3 * (y1 - y0), T("越流の開始", "overtopping starts"), fontsize=8)
    fig.savefig(f"{FIGDIR}/series.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def water_surface(c, k):
    """本川の縦断の水面(各 x で、谷を横切る最低点のセルの水位。水のないセルは欠測)。"""
    band = (c.y > -(M.WG / 2 + 30.0)) & (c.y < M.WG / 2 + 30.0 + M.basin_north(c.x, c.g["wb"]))
    z = c.frame("Z", k)
    h = c.frame("H", k) + c.frame("Hs", k) / CSTAR
    j = np.where(band, z, 1.0e9).argmin(axis=0)
    i = np.arange(c.nx)
    return np.where(h[j, i] > 0.05, z[j, i] + h[j, i], np.nan)


def fig_profile(c, tf, m):
    """基本ケースの本川の縦断(堤体と水面)。"""
    tov = m["tov"]
    times = [tf + 8.0, tov, m["tpk"] - 4.0, m["tpk"], m["tpk"] + 6.0, m["tpk"] + 16.0, c.frames[-1][1] / 60.0]
    cols = plt.get_cmap("viridis")(np.linspace(0.0, 0.92, len(times)))
    fig, ax = plt.subplots(figsize=(11.0, 5.4))
    sel = (c.xc > 300) & (c.xc < 1500)
    ax.plot(c.xc[sel], c.thalweg(c.z0)[sel], color="k", lw=1.2, label=T("元の河床", "original bed"))
    for tm, col in zip(times, cols):
        k, t = c.nearest(tm)
        prof = c.thalweg(c.frame("Z", k))
        ax.plot(c.xc[sel], prof[sel], color=col, lw=1.8, label=f"{t / 60:.0f} " + T("分", "min"))
        ax.plot(c.xc[sel], water_surface(c, k)[sel], color=col, lw=0.9, ls="--")
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.legend(fontsize=8, ncol=2, title=T("実線 = 河床(谷を横切る最低点)、破線 = 水面", "solid = bed (lowest point across the valley), dashed = water surface"), title_fontsize=8)
    ax.set_title(T("本川の縦断: 堤体の形と水面の変化", "Long profile of the main river: dam shape and water surface"), fontsize=10)
    ax.grid(alpha=0.25)
    fig.savefig(f"{FIGDIR}/profile.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 連鎖のケースの比較
CCOL = {"base": "#c0392b", "drain": "#7d3c98", "coarse": "#8b6a10", "q80": "#1f5f8b"}


def fig_chain(cases):
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 9.6), sharex=True)
    for c in cases:
        t, q2, q4, lake = c.hydro()
        col = CCOL[c.name]
        axes[0].plot(t, lake, color=col, lw=1.6, label=lab(c.name))
        axes[1].plot(t, q2, color=col, lw=1.6, label=lab(c.name))
        axes[2].plot(t, q4, color=col, lw=1.6, label=lab(c.name))
    axes[0].set_ylabel(T("水位 (m)", "water level (m)"))
    axes[0].set_title(T("(a) 堤体のすぐ上流の水位(x = 800 m)", "(a) Water level just upstream of the dam (x = 800 m)"), fontsize=10, loc="left")
    axes[1].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    axes[1].set_title(T("(b) 堤体の直下(x = 1100 m)の流量", "(b) Discharge just below the dam (x = 1100 m)"), fontsize=10, loc="left")
    axes[2].set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
    axes[2].set_title(T("(c) 集落(x = 2400 m)の流量", "(c) Discharge at the village (x = 2400 m)"), fontsize=10, loc="left")
    axes[2].set_xlabel(T("時刻 (分)", "time (min)"))
    axes[0].legend(fontsize=8, ncol=3, loc="lower right")
    for ax in axes:
        ax.grid(alpha=0.25)
    fig.savefig(f"{FIGDIR}/chain.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


PERT_COL = {"m2": "#2c7bb6", "m1": "#74add1", "eps": "#7d3c98", "p05": "#f4a340", "p1": "#d95f02", "p2": "#8b4a10"}


def crest_section(c, k):
    """フレーム k の、堤体の天端の位置(谷を横切る最低点が最も高い x)の横断: (y, 地盤高)。谷底と谷壁の脚の範囲。"""
    z = c.frame("Z", k)
    xd, zc, hd = c.dam(z)
    i = int(np.argmin(np.abs(c.xc - xd)))
    band = np.abs(c.yc) < M.WG / 2 + 10.0
    o = np.argsort(c.yc[band])
    return c.yc[band][o], z[band, i][o]


def fig_spread(done, mets):
    """流入量を少し変えた計算(結果の幅)。連鎖の基本ケースは越流の開始にそろえて重ねる。"""
    def group(base):
        return [n for n in M.PERT if M.PERT_OF[n] == base and n in done and mets[n]["tov"] is not None]
    members = group("base")
    pairs = [(n, M.PERT_OF[n]) for n in ("dam_ref_p1", "dam_face25_p1") if n in done and M.PERT_OF[n] in done]
    if "base" not in done or mets["base"]["tov"] is None or not (members or pairs):
        return False
    fig, axes = plt.subplots(3, 2, figsize=(14.0, 11.6), gridspec_kw=dict(hspace=0.36, wspace=0.16))

    def kw_of(n, base, blabel):
        if n == base:
            return dict(color="k", lw=2.2, zorder=5, label=blabel)
        return dict(color=PERT_COL[n.rsplit("_", 1)[1]], lw=1.3, label=lab(n))

    # (a)(b) 連鎖の基本ケース
    for n in sorted(members + ["base"], key=M.case_inflow):
        t, q2, q4, lake = done[n].hydro()
        kw = kw_of(n, "base", T("基本ケース(流入 40 m³/s)", "base case (inflow 40 m³/s)"))
        axes[0, 0].plot(t - mets[n]["tov"], q2, **kw)
        axes[0, 1].plot(t - mets[n]["tov"], q4, **kw)
    for ax, ttl in zip(axes[0], (T("(a) 連鎖の基本ケース: 堤体の直下(x = 1100 m)の流量",
                                   "(a) Base case of the chain: discharge just below the dam (x = 1100 m)"),
                                 T("(b) 連鎖の基本ケース: 集落(x = 2400 m)の流量",
                                   "(b) Base case of the chain: discharge at the village (x = 2400 m)"))):
        ax.set_xlim(-5.0, 50.0)
        ax.set_title(ttl, fontsize=10, loc="left")
        ax.set_xlabel(T("越流の開始からの時間 (分)", "time since the start of overtopping (min)"), fontsize=9)
    axes[0, 0].legend(fontsize=7.5, ncol=2, loc="upper right")

    # (c) 天端が水平な堤体(系列の 2 ケース)
    ax = axes[1, 0]
    for (pn, bn), col in zip(pairs, ("#1f5f8b", "#c0392b")):
        for n, ls in ((bn, "-"), (pn, "--")):
            t, q2, q4, lake = done[n].hydro()
            ax.plot(t, q2, color=col if ls == "-" else "k", lw=2.0 if ls == "-" else 1.0, ls=ls,
                    label=f"{lab(bn)}: " + T(f"流入 {M.case_inflow(n):g} m³/s", f"inflow {M.case_inflow(n):g} m³/s"))
    ax.set_title(T("(c) 天端が水平な堤体(系列の 2 ケース): 堤体の直下の流量",
                   "(c) Level crest (two cases of the series): discharge just below the dam"),
                 fontsize=10, loc="left")
    if pairs:
        ax.legend(fontsize=7.5)

    # (d)(e) 天端が傾いた堤体(10 m 格子と 5 m 格子)
    tend = {}
    for ax, base, ttl in ((axes[1, 1], "dam_tilt", T("(d) 天端が傾いた堤体、10 m 格子: 堤体の直下の流量",
                                                      "(d) Tilted crest, 10 m grid: discharge just below the dam")),
                          (axes[2, 0], "dam_tilt_dx5", T("(e) 天端が傾いた堤体、5 m 格子: 堤体の直下の流量",
                                                         "(e) Tilted crest, 5 m grid: discharge just below the dam"))):
        if base in done and mets[base]["tov"] is not None:
            for n in sorted(group(base) + [base], key=M.case_inflow):
                t, q2, q4, lake = done[n].hydro()
                ax.plot(t, q2, **kw_of(n, base, T("流入 40 m³/s", "inflow 40 m³/s")))
                tend[ax] = max(tend.get(ax, TDAM), t[-1])
            ax.legend(fontsize=7.5, loc="upper left")
        ax.set_title(ttl, fontsize=10, loc="left")
    for ax in (axes[1, 0], axes[1, 1], axes[2, 0]):
        ax.set_xlim(0.0, tend.get(ax, TDAM))          # 計算の終わりまで(5 m 格子は 120 分)
        ax.set_xlabel(T("時刻 (分)", "time (min)"), fontsize=9)
    ymax = max(a.get_ylim()[1] for a in (axes[1, 1], axes[2, 0]))
    for ax in (axes[1, 1], axes[2, 0]):
        ax.set_ylim(0.0, ymax)
    for ax in axes.flat[:5]:
        ax.set_ylim(0.0, ax.get_ylim()[1] * (1.3 if ax in (axes[0, 0], axes[1, 1], axes[2, 0]) else 1.0))   # (a)(d)(e) は凡例の分を空ける
        ax.set_ylabel(T("流量 (m³/s)", "discharge (m³/s)"))
        ax.grid(alpha=0.25)

    # (f) 越流の前の天端の横断形
    ax = axes[2, 1]
    base = done["base"]
    k = base.nearest(mets["base"]["tov"] - 2.0)[0]
    for c, kk, kw in ((base, k, dict(color="k", lw=2.2, label=T("連鎖の基本ケース(土石流がつくった堤体)", "base case of the chain (dam built by the debris flow)"))),
                      (done.get("dam_ref"), 0, dict(color="#1f5f8b", lw=1.6, label=T("天端が水平な堤体(dam_ref)", "level crest (dam_ref)"))),
                      (done.get("dam_tilt"), 0, dict(color="#d95f02", lw=1.6, label=T("天端が傾いた堤体、10 m 格子", "tilted crest, 10 m grid"))),
                      (done.get("dam_tilt_dx5"), 0, dict(color="#d95f02", lw=1.0, ls="--", label=T("天端が傾いた堤体、5 m 格子", "tilted crest, 5 m grid")))):
        if c is not None:
            yy, zz = crest_section(c, kk)
            ax.step(yy, zz, where="mid", **kw)
    ax.set_title(T("(f) 越流の前の天端の横断形(y が大きい側が支流)",
                   "(f) Crest across the valley before overtopping (tributary on the large-y side)"),
                 fontsize=10, loc="left")
    ax.set_xlabel("y (m)", fontsize=9)
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_ylim(64.0, 72.0)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7.5, loc="upper left")
    fig.savefig(f"{FIGDIR}/spread.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return True


def fig_village(cases):
    """集落の最大流動深と家屋の破壊率。"""
    fig, axes = plt.subplots(len(cases), 1, figsize=(11.0, 2.9 * len(cases)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, c in zip(axes, cases):
        ii = (c.xc >= 2000.0) & (c.xc <= M.LX)
        jj = (c.yc >= -60.0) & (c.yc <= 230.0)
        ext = [c.xc[ii][0] - c.dx / 2, c.xc[ii][-1] + c.dx / 2, c.yc[jj][-1] - c.dx / 2, c.yc[jj][0] + c.dx / 2]
        z = c.z0[np.ix_(jj, ii)]
        d = c.bil("D9999")[np.ix_(jj, ii)]
        ax.imshow(hillshade(z, c.dx), cmap="gray", extent=ext, vmin=0, vmax=1, alpha=0.6)
        im = ax.imshow(np.ma.masked_less(d, 0.05), cmap="Blues", extent=ext, vmin=0, vmax=2.5, alpha=0.9)
        hm = M.house_mask(c.x, c.y, c.dx)
        bs = c.bil("Bs9998")
        sc = ax.scatter(c.x[hm], c.y[hm], c=bs[hm], cmap="RdYlGn_r", vmin=0, vmax=1, s=16, marker="s", edgecolors="k", linewidths=0.3)
        n, mean, n50, n05 = houses(c)
        ax.set_title(f"{lab(c.name)}: " + T(f"家屋 {n} セルのうち破壊率 0.5 以上 {n50}、0.05 以上 {n05}(平均 {mean:.2f})",
                                           f"of {n} house cells, damage ratio ≥ 0.5 in {n50}, ≥ 0.05 in {n05} (mean {mean:.2f})"), fontsize=9, loc="left")
        ax.set_ylabel("y (m)", fontsize=8)
        ax.set_aspect("equal")
        ax.tick_params(labelsize=7)
    axes[-1].set_xlabel("x (m)", fontsize=8)
    cax = fig.add_axes([0.92, 0.55, 0.012, 0.3])
    fig.colorbar(im, cax=cax).set_label(T("最大流動深 (m)", "maximum flow depth (m)"), fontsize=8)
    cax = fig.add_axes([0.92, 0.15, 0.012, 0.3])
    fig.colorbar(sc, cax=cax).set_label(T("家屋の破壊率", "damage ratio of houses"), fontsize=8)
    fig.savefig(f"{FIGDIR}/village.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig_formation(cases, tmin=28.0):
    """堤体のできかたの比較(堤体ができた後の縦断と、堆積の平面)。"""
    fig = plt.figure(figsize=(max(13.0, 1.9 * len(cases)), 7.6))
    gs = fig.add_gridspec(2, len(cases), height_ratios=[1.0, 1.15], hspace=0.3, wspace=0.12)
    ax = fig.add_subplot(gs[0, :])
    cols = ["#c0392b", "#1f5f8b", "#2e8b57", "#8b6a10", "#e67e22", "#4d4d4d", "#7d3c98", "#17becf"]
    c0 = cases[0]
    sel = (c0.xc > 650) & (c0.xc < 1200)
    ax.plot(c0.xc[sel], c0.thalweg(c0.z0)[sel], color="k", lw=1.0, label=T("元の河床", "original bed"))
    for c, col in zip(cases, cols):
        k, t = c.nearest(tmin)
        sel = (c.xc > 650) & (c.xc < 1200)
        ax.plot(c.xc[sel], c.thalweg(c.frame("Z", k))[sel], color=col, lw=1.6, label=lab(c.name))
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[1] + 5.0)       # 凡例を線の上に置く分を空ける
    ax.legend(fontsize=8, ncol=3, loc="upper right")
    ax.grid(alpha=0.25)
    ax.set_title(T(f"(a) {tmin:.0f} 分の本川の縦断(谷を横切る最低点)", f"(a) Long profile of the main river at {tmin:.0f} min (lowest point across the valley)"), fontsize=10, loc="left")
    for n, c in enumerate(cases):
        ax = fig.add_subplot(gs[1, n])
        k, t = c.nearest(tmin)
        ii = (c.xc >= 650.0) & (c.xc <= 1150.0)
        jj = (c.yc >= -70.0) & (c.yc <= 330.0)
        ext = [c.xc[ii][0] - c.dx / 2, c.xc[ii][-1] + c.dx / 2, c.yc[jj][-1] - c.dx / 2, c.yc[jj][0] + c.dx / 2]
        z = c.frame("Z", k)[np.ix_(jj, ii)]
        dz = z - c.z0[np.ix_(jj, ii)]
        ax.imshow(hillshade(z, c.dx), cmap="gray", extent=ext, vmin=0, vmax=1)
        im = ax.imshow(np.ma.masked_less(dz, 0.3), cmap="YlOrBr", extent=ext, vmin=0, vmax=14, alpha=0.9)
        ttl = lab(c.name)                        # 長い呼び名は 2 行に(隣のパネルの題と重ならないように)
        for sep in ("、", ", "):
            if len(ttl) > 14 and sep in ttl:
                head, tail = ttl.rsplit(sep, 1)
                ttl = head + sep.strip() + "\n" + tail
                break
        else:
            if len(ttl) > 20 and " " in ttl:       # 区切りのない英語の長い呼び名は、中ほどの空白で
                k = min((i for i, ch in enumerate(ttl) if ch == " "), key=lambda i: abs(i - len(ttl) / 2))
                ttl = ttl[:k] + "\n" + ttl[k + 1:]
        ax.set_title(ttl, fontsize=9)
        ax.tick_params(labelsize=6)
        if n:
            ax.set_yticklabels([])
        ax.set_xlabel("x (m)", fontsize=7)
    cax = fig.add_axes([0.92, 0.12, 0.012, 0.32])
    fig.colorbar(im, cax=cax).set_label(T("堆積の厚さ (m)", "deposit thickness (m)"), fontsize=8)
    fig.text(0.125, 0.475, T("(b) 堆積の厚さ", "(b) Deposit thickness"), fontsize=10)
    fig.savefig(f"{FIGDIR}/formation.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 堤体をはじめから置く系列
PANELS = (
    (("湛水量", "Lake volume"), ("dam_small", "dam_ref", "dam_large")),
    (("堤体の形", "Dam shape"), ("dam_ref", "dam_face25", "dam_crest40", "dam_tilt")),
    (("粒径と侵食係数", "Grain size and erosion coefficient"), ("dam_d1cm", "dam_ref", "dam_d10cm", "dam_delte")),
    (("流入量", "Inflow"), ("dam_q20", "dam_ref", "dam_q80")),
    (("下流の勾配", "Downstream slope"), ("dam_ref", "dam_steep")),
    (("格子間隔", "Grid spacing"), ("dam_ref", "dam_dx5", "dam_dx5d3")),
    (("土砂を運ぶ式の選び方", "Choice of transport laws"), ("dam_ref", "dam_nofluv", "dam_tau1", "dam_imm0")),
    (("堤体の飽和と侵食式", "Dam saturation and erosion law"), ("dam_ref", "dam_unsat", "dam_unsat0")),
)
PCOL = ["#1f5f8b", "#c0392b", "#2e8b57", "#8b6a10", "#7d3c98"]


def fig_breach(dams):
    fig, axes = plt.subplots(4, 2, figsize=(12.5, 15.0), gridspec_kw=dict(hspace=0.32))
    for ax, (title, names) in zip(axes.flat, PANELS):
        k = 0
        for name in names:
            if name not in dams:
                continue
            c = dams[name]
            t, q2, q4, lake = c.hydro()
            col = "k" if name == "dam_ref" else PCOL[k]
            k += name != "dam_ref"
            ax.plot(t, q2, color=col, lw=1.9 if name == "dam_ref" else 1.5, label=lab(name))
        ax.set_yscale("log")
        ax.set_ylim(8, 4000)
        ax.set_xlim(0, max([dams[n].frames[-1][1] / 60.0 for n in names if n in dams] + [60.0]))
        ax.grid(alpha=0.25, which="both")
        if ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=8)
        ax.set_title(T(*title), fontsize=10, loc="left")
        ax.set_xlabel(T("時刻 (分)", "time (min)"), fontsize=8)
        ax.set_ylabel(T("堤体の直下の流量 (m³/s)", "discharge just below the dam (m³/s)"), fontsize=8)
    fig.suptitle(T("堤体をはじめから置き、湖を天端まで満たした系列: 堤体の直下(x = 1100 m)の流量",
                   "Series with a pre-built dam and a lake filled to the crest: discharge just below the dam (x = 1100 m)"),
                 fontsize=11, y=0.92)
    fig.savefig(f"{FIGDIR}/breach.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig_breach_sum(dams, mets, base=None):
    """ピーク流量(流入量との比)と、流出が流入を超えてからピークまでの時間。番号は 2 つのパネルで共通。"""
    names = [n for n in M.DAMS if n in dams and mets[n]["qpk"] is not None]
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.6), gridspec_kw=dict(width_ratios=[1.3, 1.0], wspace=0.22))
    ax = axes[0]
    yy = np.arange(len(names))[::-1]
    qp = np.array([mets[n]["qpk"] for n in names])
    ax.barh(yy, qp, color=["#333333" if n == "dam_ref" else "#8fb4d9" for n in names], height=0.62)
    for k, (y, n) in enumerate(zip(yy, names), 1):
        mm = mets[n]
        ax.plot(costa(mm["vlake"], mm["hdam0"]), y, "D", color="#c0392b", ms=5)
        ax.text(5200, y, f"{mm['qpk'] / mm['qin']:.1f}×", va="center", ha="right", fontsize=8)
    ax.plot([], [], "D", color="#c0392b", ms=5, label=T("Costa (1988) の経験式 181 (V h / 10⁶)^0.43", "Costa (1988) regression 181 (V h / 10⁶)^0.43"))
    ax.set_yticks(yy)
    ax.set_yticklabels([f"{k}  {lab(n)}" for k, n in enumerate(names, 1)], fontsize=8)
    ax.set_xscale("log")
    ax.set_xlim(30, 6000)
    ax.set_ylim(-1.7, len(names) - 0.4)
    ax.set_xticks([50, 100, 200, 500, 1000, 2000])
    ax.set_xticklabels(["50", "100", "200", "500", "1000", "2000"])
    ax.set_xlabel(T("ピーク流量 (m³/s)。右端の数字は流入量との比", "peak discharge (m³/s); numbers at the right = ratio to the inflow"))
    ax.grid(alpha=0.25, axis="x", which="both")
    ax.legend(fontsize=8, loc="lower right")
    ax.set_title(T("(a) 堤体の直下のピーク流量", "(a) Peak discharge just below the dam"), fontsize=10, loc="left")
    ax = axes[1]
    for k, n in enumerate(names, 1):
        mm = mets[n]
        if mm["rise"] is None:
            continue
        ax.plot(max(mm["rise"], 0.3), mm["qpk"] / mm["qin"], "o", color="#333333" if n == "dam_ref" else "#8fb4d9", ms=13,
                mec="#1f3f6b", mew=0.6)
        ax.text(max(mm["rise"], 0.3), mm["qpk"] / mm["qin"], str(k), fontsize=7, ha="center", va="center",
                color="w" if n == "dam_ref" else "k")
    if base is not None and base["qpk"] is not None and base["rise"] is not None:
        ax.plot(base["rise"], base["qpk"] / base["qin"], "*", color="#c0392b", ms=15)
        ax.annotate(T("基本ケース(連鎖)", "base case (chain)"), (base["rise"], base["qpk"] / base["qin"]), fontsize=8,
                    color="#c0392b", xytext=(8, -12), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([3, 4, 5, 7, 10, 15, 20, 30, 50])
    ax.set_xticklabels(["3", "4", "5", "7", "10", "15", "20", "30", "50"])
    ax.set_yticks([4, 5, 7, 10, 15, 20, 30])
    ax.set_yticklabels(["4", "5", "7", "10", "15", "20", "30"])
    ax.minorticks_off()
    ax.set_xlim(2.8, 60)          # 法面 0.25 は 3.5 分。5 m 格子の決壊口がふさがるケースは、ふさがっていた時間を含んで 50 分近く
    ax.set_ylim(3.6, 34)
    ax.set_xlabel(T("流出が流入を超えてからピークまでの時間 (分)", "time from outflow = inflow to the peak (min)"))
    ax.set_ylabel(T("ピーク流量 / 流入量", "peak discharge / inflow"))
    ax.grid(alpha=0.25, which="both")
    ax.set_title(T("(b) 立ち上がりの時間とピークの大きさ(番号は (a) と同じ)", "(b) Rise time and peak size (numbers as in (a))"), fontsize=10, loc="left")
    fig.savefig(f"{FIGDIR}/breach_sum.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- 数表
def thalweg_dm(c, k):
    """本川の谷筋(各 x の最低点)の表層の平均粒径 (m)(混合粒径のケース)。土層のない所は NaN。"""
    z = c.frame("Z", k)
    band = (c.y > -(M.WG / 2 + 30.0)) & (c.y < M.WG / 2 + 30.0 + M.basin_north(c.x, c.g["wb"]))
    j = np.where(band, z, 1.0e9).argmin(axis=0)
    i = np.arange(c.nx)
    dm = c.frame("Dm", k)[j, i]
    sd = c.frame("Sd", k)[j, i]
    return np.where(sd > 0.01, dm, np.nan)


def after_series(c):
    """決壊のあとの計算の時系列: 時刻 (時間)、残った堤体の高さ (m)、本川の堆積の体積 (m3。かさ。元の河床より上)。"""
    area = c.dx * c.dx
    main = c.y < M.WG / 2 + 30.0 + M.basin_north(c.x, c.g["wb"])
    out = []
    for k, t in c.frames:
        z = c.frame("Z", k)
        dz = z - c.z0
        out.append((t / 3600.0, c.dam(z)[2], dz[main & (dz > 0)].sum() * area))
    return np.array(out)


def fig_mixed(done, mets):
    """粒度の幅を持つ堤体: 決壊のハイドログラフ(単一粒径と同じ)と、決壊のあとの 6 時間(掃流砂だけ)。"""
    one, mix = done["dam_ref"], done["mix_breach"]
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 8.6), gridspec_kw=dict(hspace=0.3, wspace=0.22))
    ax = axes[0, 0]
    for c, col, lw in ((one, "k", 2.4), (mix, "#c0392b", 1.3)):
        t, q2, q4, lake = c.hydro()
        ax.plot(t, q2, color=col, lw=lw, label=lab(c.name) + T("(ピーク %.0f m³/s)", " (peak %.0f m³/s)") % mets[c.name]["qpk"])
    ax.set_xlim(0, 60)
    ax.set_xlabel(T("時刻 (分)", "time (min)"))
    ax.set_ylabel(T("堤体の直下の流量 (m³/s)", "discharge just below the dam (m³/s)"))
    ax.set_title(T("(a) 決壊のハイドログラフ(土石流 + 掃流砂)", "(a) Breach hydrograph (debris flow + bed load)"), fontsize=10, loc="left")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    after = [(n, done[n]) for n in ("one_after", "mix_after") if n in done]
    xs = one.xc
    seg = (xs > 700.0) & (xs < 1700.0)
    prof0 = one.thalweg(one.z0)
    ax = axes[0, 1]
    k60 = one.nearest(TDAM)[0]
    ax.plot(xs[seg], (one.thalweg(one.frame("Z", k60)) - prof0)[seg], color="k", lw=1.2, ls="--", label=T("単一粒径、決壊の 60 分後", "single size, 60 min after the start"))
    ax.plot(xs[seg], (mix.thalweg(mix.frame("Z", mix.nearest(TDAM)[0])) - prof0)[seg], color="#c0392b", lw=1.2, ls="--",
            label=T("粒度の幅、決壊の 60 分後", "graded, 60 min after the start"))
    for (n, c), col in zip(after, ("k", "#c0392b")):
        ax.plot(xs[seg], (c.thalweg(c.frame("Z", c.frames[-1][0])) - prof0)[seg], color=col, lw=1.8,
                label=T("同、そのあと %g 時間", "same, %g h later") % (c.frames[-1][1] / 3600.0))
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("元の河床からの高さ (m)", "height above the original bed (m)"))
    ax.set_title(T("(b) 本川の谷筋の縦断(残った堤体と下流の堆積)", "(b) Long profile of the main valley (remaining dam and deposit downstream)"), fontsize=10, loc="left")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    ax = axes[1, 0]
    ax.plot(xs[seg], thalweg_dm(mix, mix.nearest(TDAM)[0])[seg] * 100, color="#c0392b", lw=1.2, ls="--", label=T("決壊の 60 分後", "60 min after the start"))
    if "mix_after" in done:
        c = done["mix_after"]
        for hh, lw in ((1.0, 1.0), (c.frames[-1][1] / 3600.0, 1.8)):
            ax.plot(xs[seg], thalweg_dm(c, c.nearest(hh * 60.0)[0])[seg] * 100, color="#c0392b", lw=lw, label=T("そのあと %g 時間", "%g h later") % hh)
    ax.axhline(100 * sum(d * f for d, f in zip(M.MIX_D, M.MIX_F)), color="#999999", lw=0.8, ls=":")
    ax.set_xlabel("x (m)")
    ax.set_ylabel(T("谷筋の表層の平均粒径 (cm)", "surface mean grain size along the valley (cm)"))
    ax.set_title(T("(c) 表層の平均粒径(粒度の幅を持つ堤体。点線は材料の平均)", "(c) Surface mean grain size (graded dam; dots: mean of the material)"), fontsize=10, loc="left")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    ax = axes[1, 1]
    for n, col, ls, lw in (("one_after", "k", "-", 1.8), ("mix_after", "#c0392b", "-", 1.8),
                           ("one_after_debris", "k", ":", 1.4), ("mix_after_debris", "#c0392b", ":", 1.4)):
        if n in done:
            s = after_series(done[n])
            ax.plot(s[:, 0], s[:, 1], color=col, ls=ls, lw=lw, label=lab(n))
    ax.set_xlabel(T("決壊の計算の終わりからの時間 (h)", "time after the end of the breach run (h)"))
    ax.set_ylabel(T("残った堤体の高さ (m)", "height of the remaining dam (m)"))
    ax.set_title(T("(d) 決壊のあとの堤体の高さ(流量 40 m³/s、掃流砂だけ)", "(d) Dam height after the breach (40 m³/s, bed load only)"), fontsize=10, loc="left")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.savefig(f"{FIGDIR}/mixed.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def table_mixed(done, mets):
    print("\n粒度の幅を持つ堤体(mix_breach)と単一粒径(dam_ref)の決壊、決壊のあとの計算(掃流砂だけ)")
    print("ケース, ピーク (m³/s), ピークの時刻 (分), 60 分後の堤体の高さ (m), 60 分後の湖の水位 (m)")
    for n in ("dam_ref", "mix_breach"):
        m = mets[n]
        print(f"{n}, {m['qpk']:.1f}, {m['tpk']:.1f}, {m['hdam1']:.2f}, {m['lake_end']:.2f}")
    print("ケース, 時刻 (h), 残った堤体の高さ (m), 本川の堆積 (m³。かさ)")
    for n in M.AFTER:
        if n not in done:
            continue
        s = after_series(done[n])
        for hh in (0.0, 1.0, 2.0, 4.0, 6.0):
            r = s[np.argmin(np.abs(s[:, 0] - hh))]
            print(f"{n}, {r[0]:.1f}, {r[1]:.2f}, {r[2]:.0f}")
    for n in ("mix_after", "mix_after_debris"):
        if n not in done:
            continue
        c = done[n]
        seg = (c.xc > 800.0) & (c.xc < 1000.0)
        for hh in (0.0, 1.0, 6.0):
            dm = thalweg_dm(c, c.nearest(hh * 60.0)[0])
            print(f"{n} {hh:g} h: 堤体(x = 800〜1000 m)の谷筋の表層の平均粒径 {np.nanmean(dm[seg]) * 100:.2f} cm、最大 {np.nanmax(dm[seg]) * 100:.2f} cm")


def table_chain(cases, mets, tfs):
    print("\n| ケース | 崩壊 (分) | 堤体の高さ (m) | 湛水量 (万 m³) | 越流の開始 (分) | ピーク流量 直下 / 集落 (m³/s) | 流入との比 | 立ち上がり (分) | 10 分間の水位低下の最大 (m) | 残った堤体 (m) | 家屋: 破壊率 ≥ 0.5 / ≥ 0.05 / 平均 | 列ごとの破壊率の平均(岸から) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in cases:
        m = mets[c.name]
        n, mean, n50, n05 = houses(c)
        ratio = None if m["qpk"] is None else m["qpk"] / m["qin"]
        print(f"| {c.name} | {f(tfs.get(c.name), '%.0f')} | {f(m['hdam0'], '%.1f')} | {f(None if m['vlake'] is None else m['vlake'] / 1e4, '%.0f')} | "
              f"{f(m['tov'])} | {f(m['qpk'])} / {f(m['qpk_v'])} | {f(ratio, '%.1f')} | {f(m['rise'], '%.0f')} | {f(m['drop10'], '%.1f')} | "
              f"{f(m['hdam1'], '%.1f')} | {n50} / {n05} / {mean:.2f} | {' / '.join('%.2f' % v for v in house_rows(c))} |")


def table_dams(dams, mets):
    print("\n| ケース | 変えた条件 | 流入 (m³/s) | 湛水量 (万 m³) | ピーク流量 直下 / 集落 (m³/s) | 流入との比 | ピークの時刻 (分) | 立ち上がり (分) | "
          "10 分間の水位低下の最大 (m) | %.0f 分後の堤体の高さ (m) | 家屋の破壊率の平均 | Costa の式 (m³/s) |" % TDAM)
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for n in M.DAMS:
        if n not in dams:
            continue
        m = mets[n]
        ratio = None if m["qpk"] is None else m["qpk"] / m["qin"]
        print(f"| {n} | {T(*LAB[n])} | {m['qin']:.0f} | {m['vlake'] / 1e4:.0f} | {f(m['qpk'])} / {f(m['qpk_v'])} | {f(ratio, '%.1f')} | {f(m['tpk'])} | "
              f"{f(m['rise'], '%.1f')} | {f(m['drop10'], '%.1f')} | {f(m['hdam1'], '%.1f')} | {houses(dams[n])[1]:.2f} | {costa(m['vlake'], m['hdam0']):.0f} |")


def table_spread(done, mets):
    """流入量を少し変えた計算の指標(もとのケースを先頭に、流入量の順)。"""
    print("\n| ケース | 流入 (m³/s) | 越流の開始 (分) | ピーク流量 直下 / 集落 (m³/s) | 越流の開始からピークまで (分) | "
          "途中の落ち込み(流量 / それまでの最大 の最小) | 家屋: 列ごとの破壊率の平均(岸から) | 家屋の破壊率の平均 |")
    print("|---|---|---|---|---|---|---|---|")
    for b in dict.fromkeys(M.PERT_OF.values()):
        for n in sorted([b] + [p for p, o in M.PERT_OF.items() if o == b], key=M.case_inflow):
            if n not in done or mets[n]["tov"] is None:
                continue
            m = mets[n]
            print(f"| {n} | {m['qin']:g} | {m['tov']:.1f} | {m['qpk']:.0f} / {m['qpk_v']:.0f} | {m['tpk'] - m['tov']:.1f} | "
                  f"{dip_ratio(done[n], m):.2f} | {' / '.join('%.2f' % v for v in house_rows(done[n]))} | {houses(done[n])[1]:.2f} |")


def table_formation(cases, tmin=28.0):
    print("\n| ケース | 崩壊 (分) | 堤体の高さ (m) | 天端の x (m) | 本川の堆積 (万 m³) | 支流の堆積 (万 m³) | 斜面に残る崩積土 (万 m³) |")
    print("|---|---|---|---|---|---|---|")
    for c in cases:
        s = series(c)
        i = int(np.argmin(np.abs(s[:, 0] - tmin)))
        print(f"| {c.name} | {f(fail_time(s), '%.0f')} | {s[i, 5]:.1f} | {s[i, 7]:.0f} | {s[i, 2] / 1e4:.1f} | {s[i, 3] / 1e4:.1f} | {s[i, 1] / 1e4:.1f} |")


def main():
    if ONLY_MIXED:
        done = {n: c for n, c in ((n, Case(n)) for n in M.MIXED) if c.ok}
        if "dam_ref" in done and "mix_breach" in done:
            mets = {n: metrics(c) for n, c in done.items()}
            fig_mixed(done, mets)
            table_mixed(done, mets)
        else:
            print("dam_ref と mix_breach の計算結果がありません(make mixed)")
        return
    fig_setup()
    cases = {n: Case(n) for n in M.CASES}
    done = {n: c for n, c in cases.items() if c.ok}
    print("計算済み:", " ".join(done) if done else "なし(setup.png だけを描きました)")
    mets = {n: metrics(c) for n, c in done.items()}
    tfs = {}
    if "base" in done:
        base = done["base"]
        s = series(base)
        tfs["base"] = tf = fail_time(s)
        m = mets["base"]
        print("base:", {k: (round(float(v), 2) if v is not None else None) for k, v in m.items()})
        if m["tov"] is not None:
            fig_sequence(base, s, tf, m)
            fig_profile(base, tf, m)
        fig_series(base, s, tf, m)
    chain = [done[n] for n in CHAIN if n in done]
    for c in chain:
        if c.name not in tfs:
            tfs[c.name] = fail_time(series(c))
    if chain:
        fig_chain(chain)
        table_chain(chain, mets, tfs)
        fig_village([done[n] for n in ("base", "coarse", "drain") if n in done])
    if fig_spread(done, mets):
        table_spread(done, mets)
    if "norain" in done:
        c = done["norain"]
        t, q2, q4, lake = c.hydro()
        n, mean, n50, n05 = houses(c)
        print(f"\nnorain: 集落の流量 {q4[-1]:.1f} m³/s、最大流動深(氾濫原) "
              f"{c.bil('D9999')[(c.x > 2100) & (c.y > M.WC / 2 + 5) & (c.y < 170)].max():.2f} m、家屋の破壊率の平均 {mean:.3f}")
    form = [done[n] for n in FORM if n in done]
    if len(form) > 1:
        fig_formation(form)
        table_formation(form)
    if "dam_ref" in done and "mix_breach" in done:
        fig_mixed(done, mets)
        table_mixed(done, mets)
    dams = {n: done[n] for n in M.DAMS if n in done}
    if dams:
        fig_breach(dams)
        fig_breach_sum(dams, mets, mets.get("base"))
        table_dams(dams, mets)
        print("\n経験式との比較(m³/s): ケース、計算、Costa (1988)、田畑ら、石川ら (1992。流入 1 m²/s の式)")
        for n in ("base", "dam_small", "dam_ref", "dam_large", "dam_face25", "dam_q20", "dam_q80"):
            if n in mets and mets[n]["qpk"] is not None:
                m = mets[n]
                print(f"  {n}: {m['qpk']:.0f}, {costa(m['vlake'], m['hdam0']):.0f}, {tabata(m['hdam0'], m['qin']):.0f}, "
                      f"{ishikawa(m['vlake'], m['hdam0']):.0f}")


if __name__ == "__main__":
    main()
