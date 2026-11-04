#!/usr/bin/env python3
"""debris_fan の図と数表(事前に make run で全ケースを計算しておく)。

  figs/setup.png       模式地形(崩壊斜面・谷・扇状地・住宅地)、谷筋の縦断、谷の横断、格子に対する谷の向き
  figs/maps_40m.png    格子 40 m の 3 つの向きの堆積厚と最大流動深(左: ENC の 8 近傍、右: 4 近傍)
  figs/maps_20m.png    同じく格子 20 m
  figs/maps_5m.png     同じく格子 5 m
  figs/overlay.png     扇状地の堆積厚 0.5 m と最大流動深 1 m の線を、向き・格子間隔ごとに重ねた図(上 8 近傍、下 4 近傍)
  figs/dependence.png  格子間隔に対する、向きによる地図の差と主な指標(8 近傍と 4 近傍)
  figs/series.png      前縁の位置の時間変化、谷と扇状地の堆積の縦断分布、扇状地での堆積の広がり
数表(標準出力): 各ケースの指標、向きの差と格子の差のまとめ、地図の差。
ケースの座標はすべて谷沿いの座標 (s, n)(make_init.py)。体積・面積は各ケースの格子のセルで数え、
向きの比較の地図の差(L1)は谷沿いの共通の 5 m 格子へ双一次補間して求める。
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。
"""
import math
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, ListedColormap
from matplotlib.patches import Polygon, Ellipse
import make_init as M

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

CSTAR = 1.0 - M.LAMBDA          # 堆積物の固体濃度 C*
H_FRONT = 0.5                   # 前縁の判定の流動深 (m)
DEP_THR = (0.1, 0.5, 1.0)       # 土砂の厚さの範囲の閾値 (m)
F_THR = 10.0                    # 最大流体力の範囲の閾値 (m³/s²。× ρw で 10 kN/m)
DXS = M.DXS                     # 3 つの向きで比べる格子間隔
DXS_ALL = M.DXS + (M.DX_REF,)   # 収束の確認の 2.5 m(0° だけ)を含む
THETAS = M.THETAS
REF_KEY = (M.DX_REF, 0.0, 8)    # 比の基準(最も細かい格子・0°・8 近傍)
COL_TH = {0.0: "#1f5f8b", 22.5: "#d08c00", 45.0: "#2b8a3e"}
COL_DX = {40.0: "#7b2d8e", 20.0: "#c0392b", 10.0: "#d08c00", 5.0: "#2b8a3e", 2.5: "#1f5f8b"}
TERRAIN = ListedColormap(plt.get_cmap("gist_earth")(np.linspace(0.35, 0.95, 256)))   # 低地(緑)〜山(茶・白)


def th_label(th):
    return f"{th:g}°"


def nb_label(nb):
    return T(f"{nb} 近傍", f"{nb} neighbours")


class Case:
    """1 ケースの入力と出力(配列は行 0 が南端。make_init.py の to_sn と同じ並び)。"""

    def __init__(self, dx, th, nb=8):
        self.dx, self.th, self.nb = dx, th, nb
        self.name = M.case_name(dx, th, nb)
        self.ddir = "data_" + M.case_name(dx, th)
        self.rdir = "result_" + self.name
        nx, ny, ox, oy, _, _ = open(f"{self.ddir}/size.txt").read().split()
        self.nx, self.ny, self.ox, self.oy = int(nx), int(ny), float(ox), float(oy)
        t = math.radians(th)
        self.c, self.sn = math.cos(t), math.sin(t)
        self.s, self.n = M.to_sn(dx, th)
        self.mask = self.txt("mask") > 0
        self.land = self.mask & ~(self.txt("sw") > 0)
        self.d0 = self.txt("dbinit")
        self.area = dx * dx
        self.times = {}
        for line in open(f"{self.rdir}/FILENUMBER.csv"):
            if line.startswith("#"):
                continue
            f = line.split(",")
            if int(f[0]) < 9000:
                self.times[int(f[0])] = float(f[2])
        self.kend = max(self.times)
        self.z0 = self.bil("Z", 0)
        self.zend = self.bil("Z", self.kend)
        self.zbase = self.z0 - self.d0                       # 崩壊後の地表(崩壊域の外は元の地表)
        self.dep = np.where(self.land, self.zend - self.zbase, 0.0)          # 堆積厚(崩壊地では残った土砂)
        self.hs_end = np.where(self.land, self.bil("Hs", self.kend), 0.0)
        self.mov = self.hs_end / CSTAR                                       # 流動中の土砂のかさ厚
        self.thick = self.dep + self.mov                                     # 土砂の厚さ = 堆積 + 流動中
        self.D = np.where(self.land, self.bil("D", 9999), 0.0)               # 最大流動深 h + hs
        self.F = np.where(self.land, self.bil("F", 9999), 0.0)               # 最大流体力 (m³/s²)
        self.r = np.hypot(self.s - M.L_V, self.n)            # 扇頂からの距離
        self.fan = self.land & (self.s > M.L_V)
        self.scar = self.d0 > 0.0
        self.valley = self.land & (self.s <= M.L_V) & ~self.scar
        self._front = None

    def txt(self, name):
        return np.loadtxt(f"{self.ddir}/{name}.txt")[::-1]

    def bil(self, name, k):
        a = np.fromfile(f"{self.rdir}/{name}{k:04d}.bil", "<f4").reshape(self.ny, self.nx)
        return a[::-1].astype(float)

    def to_index(self, s, n):
        """谷沿いの座標 → 格子のセルの実数添字(セル中心が整数)。"""
        x = s * self.c + n * self.sn + self.ox
        y = -s * self.sn + n * self.c + self.oy
        return x / self.dx - 0.5, y / self.dx - 0.5

    def sample(self, a, s, n):
        """場 a を谷沿いの座標の点 (s, n) で双一次補間する。"""
        fi, fj = self.to_index(s, n)
        i0 = np.clip(np.floor(fi).astype(int), 0, self.nx - 2)
        j0 = np.clip(np.floor(fj).astype(int), 0, self.ny - 2)
        a1, b1 = fi - i0, fj - j0
        return (a[j0, i0] * (1 - a1) * (1 - b1) + a[j0, i0 + 1] * a1 * (1 - b1)
                + a[j0 + 1, i0] * (1 - a1) * b1 + a[j0 + 1, i0 + 1] * a1 * b1)

    def cell(self, s, n):
        """点 (s, n) を含むセルの添字。"""
        fi, fj = self.to_index(s, n)
        return np.round(fj).astype(int), np.round(fi).astype(int)

    def corners(self):
        """pcolormesh 用のセルの角の谷沿いの座標。"""
        x = np.arange(self.nx + 1) * self.dx - self.ox
        y = np.arange(self.ny + 1) * self.dx - self.oy
        X, Y = np.meshgrid(x, y)
        return X * self.c - Y * self.sn, X * self.sn + Y * self.c

    def front(self):
        """時刻ごとの前縁の位置: 流動深 h + hs ≥ H_FRONT のセルの、谷筋〜扇状地の軸に沿う距離の最大
        (谷の中は s、扇状地は扇頂 + 扇頂からの距離 r)。"""
        if self._front is None:
            xi = np.where(self.s > M.L_V, M.L_V + self.r, self.s)
            out = []
            for k in sorted(self.times):
                d = self.bil("H", k) + self.bil("Hs", k)
                w = self.land & (d >= H_FRONT)
                out.append((self.times[k], xi[w].max() if w.any() else np.nan))
            self._front = np.array(out)
        return self._front

    def arrival(self, xi0):
        """前縁が軸に沿う距離 xi0 に達した時刻(出力の時刻の間は前縁の位置を線形補間)。"""
        fr = self.front()
        x = np.nan_to_num(fr[:, 1], nan=-1e9)
        ok = x >= xi0
        if not ok.any():
            return np.nan
        k = int(np.argmax(ok))
        if k == 0:
            return fr[0, 0]
        t0, t1, x0, x1 = fr[k - 1, 0], fr[k, 0], x[k - 1], x[k]
        return t0 + (t1 - t0) * (xi0 - x0) / (x1 - x0)

    def ledger(self):
        """固体の台帳の閉合 Σhs + (1 − λ)Σ(z − z0)(m³。下流端の吸い込みへの流出があれば負)。"""
        return (self.hs_end[self.land].sum() + CSTAR * (self.zend - self.z0)[self.land].sum()) * self.area

    def metrics(self):
        A, dep, th_ = self.area, self.dep, self.thick
        m = {}
        m["V_scar"] = dep[self.scar].sum() * A                       # 崩壊地に残った土砂(かさ体積)
        m["V_valley"] = dep[self.valley & (dep > 0)].sum() * A       # 谷の中の堆積(崩壊地の外)
        m["V_fan"] = dep[self.fan & (dep > 0)].sum() * A             # 扇状地の堆積
        m["M_valley"] = self.mov[self.land & (self.s <= M.L_V)].sum() * A   # 10 分後も流れている土砂(かさ)
        m["M_fan"] = self.mov[self.fan].sum() * A
        m["T_fan"] = m["V_fan"] + m["M_fan"]                          # 扇状地の土砂(堆積 + 流動中)
        for t in DEP_THR:
            m[f"A_{t:g}"] = (self.fan & (dep >= t)).sum() * A          # 扇状地の堆積厚 ≥ t の面積
        w = self.fan & (dep >= DEP_THR[0])
        m["R_max"] = self.r[w].max() if w.any() else 0.0              # 堆積の到達距離(扇頂から。0.1 m 以上)
        wf = self.fan & (dep > 0)
        m["R_mean"] = (self.r[wf] * dep[wf]).sum() / dep[wf].sum()   # 扇状地の堆積の重心の距離
        m["T_max"] = dep[self.fan].max()                              # 扇状地の最大堆積厚
        m["D1_fan"] = (self.fan & (self.D >= 1.0)).sum() * A          # 最大流動深 1 m 以上の範囲
        m["F10_fan"] = (self.fan & (self.F >= F_THR)).sum() * A       # 最大流体力 F_THR 以上の範囲
        hs = M.houses()
        jj, ii = self.cell(hs[:, 0], hs[:, 1])
        m["n_house_D1"] = int((self.D[jj, ii] >= 1.0).sum())          # 1 m 以上の深さで流れが達した家屋
        m["n_house_T05"] = int((dep[jj, ii] >= 0.5).sum())            # 0.5 m 以上埋まった家屋
        m["t_mouth"] = self.arrival(M.L_V)                             # 前縁が扇頂に達した時刻
        m["t_town"] = self.arrival(M.L_V + M.R_H1)                     # 住宅地の端(扇頂から R_H1)に達した時刻
        m["V_peak"] = self.bil("V", 9999)[self.land & (self.s > 500) & (self.s < M.L_V)
                                          & (np.abs(self.n) < M.WF)].max()   # 谷の中の最大流速
        ang, v = angle_profile(self)
        m["ang_std"] = math.sqrt((v * ang ** 2).sum() / v.sum())        # 扇状地の堆積の横への広がり(扇頂から見た角度の標準偏差)
        m["ledger"] = self.ledger()
        return m


def load_all():
    keys = [(dx, th, nb) for nb in (8, 4) for dx in DXS for th in THETAS] + [(M.DX_REF, 0.0, 8), (M.DX_REF, 0.0, 4)]
    return {k: Case(*k) for k in keys if os.path.exists(f"result_{M.case_name(*k)}/D9999.bil")}


# 指標: キー、表の見出し(日・英)、小数桁
KEYS = [("V_scar", "崩壊地に残る", "left in scar", 0),
        ("V_valley", "谷の堆積", "valley dep.", 0),
        ("V_fan", "扇状地の堆積", "fan deposit", 0),
        ("M_fan", "扇状地の流動中", "fan moving", 0),
        ("T_fan", "扇状地の土砂", "fan sediment", 0),
        ("A_0.1", "堆積≥0.1m 面積", "dep ≥0.1 m", 0),
        ("A_1", "堆積≥1m 面積", "dep ≥1 m", 0),
        ("R_max", "到達距離", "runout", 0),
        ("R_mean", "重心距離", "centroid", 0),
        ("T_max", "最大堆積厚", "max dep.", 2),
        ("D1_fan", "流動深≥1m 面積", "depth≥1m area", 0),
        ("F10_fan", "流体力≥10 面積", "F≥10 area", 0),
        ("n_house_D1", "家屋 流動深≥1m", "houses D≥1m", 0),
        ("n_house_T05", "家屋 堆積≥0.5m", "houses dep≥0.5m", 0),
        ("t_mouth", "扇頂到達 s", "t apex s", 1),
        ("t_town", "住宅地到達 s", "t town s", 1),
        ("V_peak", "谷の最大流速", "peak speed", 1),
        ("ang_std", "広がり 角度°", "spread deg", 1),
        ("ledger", "固体の台帳", "solid ledger", 3)]
CMP = ("V_valley", "T_fan", "A_0.1", "A_1", "R_max", "R_mean", "D1_fan", "F10_fan", "n_house_D1", "n_house_T05", "ang_std")


def print_table(cases, mets):
    print(T("指標(10 分後。体積はかさ体積 m³、面積 m²、距離 m、時刻 s)",
            "metrics (at 10 min; bulk volume m³, area m², distance m, time s)"))
    print(f"{'case':16s}" + "".join(f"{T(ja, en):>15s}" for _, ja, en, _ in KEYS))
    for key, c in cases.items():
        m = mets[key]
        print(f"{c.name:16s}" + "".join(f"{m[k]:15.{nd}f}" for k, _, _, nd in KEYS))


def spread(vals, ref):
    """(最大 − 最小)/ 基準値(8 近傍・2.5 m・0°)。"""
    v = np.array(vals, dtype=float)
    return (v.max() - v.min()) / abs(ref)


def print_summary(cases, mets):
    ref = mets.get(REF_KEY)
    if ref is None:
        return
    print()
    print(T("向きの差((最大 − 最小)/ 基準。同じ格子間隔の 3 つの向き。基準 = 8 近傍・2.5 m・0°。%)",
            "spread over the orientations ((max − min) / reference over the three orientations of one spacing; "
            "reference = 8 neighbours, 2.5 m, 0°; %)"))
    print(f"{'':14s}" + "".join(f"{k:>12s}" for k in CMP))
    for nb in (8, 4):
        for dx in DXS:
            ks = [(dx, th, nb) for th in THETAS if (dx, th, nb) in mets]
            if len(ks) < 3:
                continue
            print(f"  {nb}nb {dx:5g} m" + "".join(f"{100 * spread([mets[c][k] for c in ks], ref[k]):12.1f}" for k in CMP))
    print(T("格子の差(谷の向き 0° の各格子の、基準に対する比)", "spacing (ratio to the reference at 0°)"))
    print(f"{'':14s}" + "".join(f"{k:>12s}" for k in CMP))
    for nb in (8, 4):
        for dx in DXS_ALL:
            if (dx, 0.0, nb) in mets:
                print(f"  {nb}nb {dx:5g} m" + "".join(f"{mets[(dx, 0.0, nb)][k] / ref[k]:12.3f}" for k in CMP))
    for nb in (8, 4):
        for dmax in (10.0, 20.0, 40.0):
            ks = [k for k in mets if k[2] == nb and k[0] <= dmax and k[0] in DXS]
            if not ks:
                continue
            dmin = min(k[0] for k in ks)
            print(T(f"{nb} 近傍の {dmin:g}〜{dmax:g} m の {len(ks)} ケースの幅((最大 − 最小)/ 基準。%)",
                    f"spread over the {len(ks)} cases of {dmin:g}-{dmax:g} m with {nb} neighbours ((max − min) / reference; %)"))
            print(f"{'':14s}" + "".join(f"{100 * spread([mets[c][k] for c in ks], ref[k]):12.1f}" for k in CMP))


RANGE_KEYS = [("T_fan", "扇状地に届いた土砂", "sediment reaching the fan"),
              ("A_0.1", "堆積の面積(≥ 0.1 m)", "deposit area (≥ 0.1 m)"),
              ("R_max", "堆積の到達距離", "runout of the deposit"),
              ("D1_fan", "最大流動深 ≥ 1 m の面積", "area of max flow depth ≥ 1 m"),
              ("F10_fan", f"最大流体力 ≥ {F_THR:g} の面積", f"area of max force ≥ {F_THR:g}"),
              ("n_house_D1", "流動深 ≥ 1 m の家屋", "houses with flow depth ≥ 1 m"),
              ("t_mouth", "扇頂への到達時刻", "arrival at the apex"),
              ("ang_std", "堆積の横への広がり", "lateral spreading of the deposit")]


def print_ranges(mets):
    """README 用の表(Markdown): 各格子間隔の 3 つの向きの、基準(8 近傍・2.5 m・0°)に対する比の範囲。"""
    ref = mets.get(REF_KEY)
    if ref is None:
        return
    print()
    print(T("基準に対する比の範囲(3 つの向きの最小〜最大。Markdown)", "range of the ratio to the reference (min-max over the three orientations; Markdown)"))
    head = [T("指標", "indicator")] + [f"{nb_label(nb)} {dx:g} m" for nb in (8, 4) for dx in DXS
                                       if all((dx, th, nb) in mets for th in THETAS)]
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" + "---:|" * (len(head) - 1))
    for key, ja, en in RANGE_KEYS:
        row = [T(ja, en)]
        for nb in (8, 4):
            for dx in DXS:
                ks = [(dx, th, nb) for th in THETAS]
                if not all(k in mets for k in ks):
                    continue
                v = [mets[k][key] / ref[key] for k in ks]
                row.append(f"{min(v):.2f}〜{max(v):.2f}" if not EN else f"{min(v):.2f}-{max(v):.2f}")
        print("| " + " | ".join(row) + " |")
    print()
    print(T("扇状地に届いた土砂(堆積 + 流動中。千 m³。0° / 22.5° / 45°)", "sediment reaching the fan (deposit + moving; 1,000 m³; 0° / 22.5° / 45°)"))
    for dx in DXS_ALL:
        cells = []
        for nb in (8, 4):
            ks = [(dx, th, nb) for th in THETAS if (dx, th, nb) in mets]
            cells.append(" / ".join(f"{mets[k]['T_fan'] / 1000:.1f}" for k in ks) if ks else "—")
        print(f"| {dx:g} m | " + " | ".join(cells) + " |")


def common_grid(ds=5.0):
    ss = np.arange(M.L_V - 100, M.L_V + 600, ds) + ds / 2
    nn = np.arange(-350, 350, ds) + ds / 2
    return np.meshgrid(ss, nn)


def l1_orientation(cases):
    """同じ格子間隔の 0° に対する 22.5°・45° の地図の差(堆積厚・最大流動深の L1 の相対差)。
    谷沿いの共通の 5 m 格子へ双一次補間して、扇頂の 100 m 上流から 600 m 下流までで比べる。"""
    S, N = common_grid()
    print()
    print(T("地図の差(0° との L1 の相対差 Σ|b − a| / Σ|a|。扇頂の 100 m 上流から 600 m 下流まで。%)",
            "map difference from 0° (relative L1 Σ|b − a| / Σ|a|; 100 m above to 600 m below the apex; %)"))
    out = {}
    for nb in (8, 4):
        for dx in DXS:
            if (dx, 0.0, nb) not in cases:
                continue
            a = cases[(dx, 0.0, nb)]
            ta, Da = a.sample(a.dep, S, N), a.sample(a.D, S, N)
            for th in THETAS[1:]:
                if (dx, th, nb) not in cases:
                    continue
                b = cases[(dx, th, nb)]
                tb, Db = b.sample(b.dep, S, N), b.sample(b.D, S, N)
                r1 = np.abs(tb - ta).sum() / np.abs(ta).sum()
                r2 = np.abs(Db - Da).sum() / np.abs(Da).sum()
                out[(dx, th, nb)] = (r1, r2)
                print(f"  {nb}nb {dx:5g} m {th:4g}°: " + T(f"堆積厚 {100 * r1:5.1f}  最大流動深 {100 * r2:5.1f}",
                                                         f"deposit {100 * r1:5.1f}  max flow depth {100 * r2:5.1f}"))
    return out


# ---------------------------------------------------------------- 図: 設定
def shade(z, dx):
    return LightSource(azdeg=315, altdeg=40).hillshade(z, vert_exag=1.0, dx=dx, dy=dx)


def fig_setup():
    ds = 5.0
    ss = np.arange(0.0, M.L_V + M.L_F, ds) + ds / 2
    nn = np.arange(-M.W / 2, M.W / 2, ds) + ds / 2
    S, N = np.meshgrid(ss, nn)
    Z = M.terrain(S, N)
    D = M.collapse_shape(S, N)
    hs = M.houses()
    fig = plt.figure(figsize=(14, 9.6), constrained_layout=True)
    gs = fig.add_gridspec(3, 3, height_ratios=[1.45, 1.0, 1.0])
    ax = fig.add_subplot(gs[0, :])
    ext = [0, M.L_V + M.L_F, -M.W / 2, M.W / 2]
    rgb = plt.get_cmap(TERRAIN)(np.clip(Z / 520.0, 0, 1))[:, :, :3]
    ax.imshow(LightSource(azdeg=315, altdeg=45).shade_rgb(rgb, Z, vert_exag=1.0, dx=ds, dy=ds, blend_mode="soft"),
              origin="lower", extent=ext)
    cs = ax.contour(S, N, Z, levels=np.arange(0, 520, 20), colors="#5a4632", linewidths=0.35, alpha=0.8)
    ax.clabel(cs, levels=np.arange(0, 520, 100), fontsize=7, fmt="%d m")
    ax.contourf(S, N, D, levels=[0.02, 1.01], colors=["#c0392b"], alpha=0.6)
    ax.contour(S, N, D, levels=[0.02], colors=["#c0392b"], linewidths=1.0)
    ax.plot(hs[:, 0], hs[:, 1], "s", ms=2.2, color="#1f3f8b", label=T("家屋(住宅地)", "houses (residential area)"))
    ax.axvline(M.L_V, color="k", ls="--", lw=0.8)
    ax.text(M.S_C + 50, M.N_C + 45, T("崩壊(10 万 m³)", "collapse (100,000 m³)"), color="#8b1a10", fontsize=9)
    ax.text(600, -45, T("谷(谷底幅 30 m・谷壁 35°)", "valley (floor 30 m, walls 35°)"), fontsize=9, ha="center")
    ax.text(M.L_V + 8, 365, T("谷の出口 = 扇頂", "valley mouth = fan apex"), fontsize=9)
    ax.text(M.L_V + 560, -330, T("扇状地(円錐)", "fan (cone)"), fontsize=9)
    ax.annotate("", xy=(760, -230), xytext=(560, -230), arrowprops=dict(arrowstyle="-|>", color="k"))
    ax.text(660, -265, T("s(谷を下る向き)", "s (down the valley)"), ha="center", fontsize=8)
    ax.annotate("", xy=(560, -130), xytext=(560, -232), arrowprops=dict(arrowstyle="-|>", color="k"))
    ax.text(570, -175, T("n(北岸が正)", "n (north bank +)"), fontsize=8)
    ax.set_xlim(0, M.L_V + M.L_F)
    ax.set_ylim(-M.W / 2, M.W / 2)
    ax.set_aspect("equal")
    ax.set_xlabel("s (m)")
    ax.set_ylabel("n (m)")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_title(T("模式地形(谷沿いの座標)。等高線 20 m おき、赤 = 崩壊域、青 = 家屋", "Schematic terrain (valley coordinates). Contours every 20 m; red = collapse, blue = houses"), fontsize=10)
    # 縦断(谷筋〜扇状地の軸)
    ax = fig.add_subplot(gs[1, :2])
    xi = np.linspace(0, M.L_V + M.L_F, 1000)
    ax.plot(xi, M.z_axis(xi), color="#6b4f2a", lw=1.6, label=T("谷底〜扇状地の軸", "valley floor to fan axis"))
    ax.axvline(M.L_V, color="k", ls="--", lw=0.8)
    for x0 in (0, 500, M.L_V, M.L_V + 400, M.L_V + M.L_F):
        ax.text(x0, M.z_axis(x0) + 12, f"{M.slope_axis(x0):.3g}", fontsize=8, ha="center")
    ax.text(M.L_V - 10, 250, T("数字 = 勾配(tan)", "numbers = slope (tan)"), ha="right", fontsize=8)
    ax.axvspan(M.S_C - M.A_S, M.S_C + M.A_S, color="#c0392b", alpha=0.15)
    ax.text(M.S_C, 30, T("崩壊の\n位置", "collapse\nreach"), ha="center", fontsize=8, color="#c0392b")
    ax.axvspan(M.L_V + M.R_H1, M.L_V + M.R_H2, color="#1f5f8b", alpha=0.10)
    ax.text(M.L_V + 0.5 * (M.R_H1 + M.R_H2), 150, T("住宅地", "residential area"), ha="center", fontsize=8, color="#1f5f8b")
    ax.set_xlabel(T("s (m)  谷筋と扇状地の軸に沿う距離", "s (m)  distance along the valley and fan axis"))
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T("谷底と扇状地の縦断", "Long profile of the valley floor and the fan"), fontsize=10)
    ax.grid(alpha=0.3)
    # 横断(崩壊の中心を通る)
    ax = fig.add_subplot(gs[1, 2])
    nl = np.linspace(-250, 250, 1001)
    zl = M.terrain(np.full_like(nl, M.S_C), nl)
    dl = M.collapse_shape(np.full_like(nl, M.S_C), nl)
    d_scale = M.V0 / (math.pi / 2 * M.A_S * M.A_N)          # 連続形の最大崩壊深
    ax.fill_between(nl, zl - dl * d_scale, zl, color="#c0392b", alpha=0.5, label=T("崩壊土塊", "collapse mass"))
    ax.plot(nl, zl, color="#6b4f2a", lw=1.4)
    ax.set_xlabel("n (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T(f"横断(s = {M.S_C:g} m、崩壊の中心)", f"Cross-section (s = {M.S_C:g} m, collapse centre)"), fontsize=10)
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower right")
    # 格子に対する谷の向き(20 m 格子の地盤高)
    for col, th in enumerate(THETAS):
        ax = fig.add_subplot(gs[2, col])
        dx = 20.0
        nx, ny, ox, oy, out = M.grid(dx, th)
        z = np.where(out["mask"] > 0, out["z"], np.nan)
        ax.imshow(z, origin="lower", cmap=TERRAIN, extent=[0, nx * dx, 0, ny * dx], vmin=0, vmax=520,
                  interpolation="nearest")
        d = np.where(out["dbinit"] > 0, 1.0, np.nan)
        ax.imshow(d, origin="lower", cmap=ListedColormap(["#c0392b"]), extent=[0, nx * dx, 0, ny * dx],
                  interpolation="nearest")
        ax.set_title(T(f"谷の向き {th:g}°(20 m 格子。{nx}×{ny})", f"valley at {th:g}° (20 m grid, {nx}×{ny})"), fontsize=9)
        ax.set_xlabel("x (m)")
        if col == 0:
            ax.set_ylabel("y (m)")
        ax.tick_params(labelsize=7)
    fig.savefig(f"{FIGDIR}/setup.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 図: 結果
from matplotlib.colors import BoundaryNorm
from matplotlib.lines import Line2D

T_LEVELS = [0.1, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0]
T_CMAP = plt.get_cmap("YlOrBr")
FAN_BOX = (M.L_V - 60, M.L_V + 440, -260, 260)         # 扇状地の図の範囲 (s0, s1, n0, n1)
ALL_BOX = (150, M.L_V + 440, -230, 230)


def terrain_bg(ax, box, ds=5.0, step=10):
    ss = np.arange(box[0], box[1], ds) + ds / 2
    nn = np.arange(box[2], box[3], ds) + ds / 2
    S, N = np.meshgrid(ss, nn)
    Z = M.terrain(S, N)
    ax.imshow(LightSource(azdeg=315, altdeg=45).hillshade(Z, dx=ds, dy=ds), origin="lower",
              extent=[box[0], box[1], box[2], box[3]], cmap="gray", vmin=-0.3, vmax=1.4, zorder=0)
    ax.contour(S, N, Z, levels=np.arange(0, 520, step), colors="0.55", linewidths=0.3, zorder=1)


def thick_map(ax, c, box, houses=True, dcont=True):
    """堆積厚(色。各ケースの格子のセルをそのまま描く)、最大流動深 1 m の線(青)、
    10 分後も流れている土砂のかさ厚 0.1 m の線(赤紫)、家屋(黒の点)。"""
    terrain_bg(ax, box)
    S, N = c.corners()
    t = np.ma.masked_where(~c.land | (c.dep < T_LEVELS[0]), c.dep)
    norm = BoundaryNorm(T_LEVELS, T_CMAP.N, extend="max")
    pm = ax.pcolormesh(S, N, t, cmap=T_CMAP, norm=norm, shading="flat", zorder=2, rasterized=True)
    if dcont:
        ax.contour(c.s, c.n, np.where(c.land, c.D, 0.0), levels=[1.0], colors="#1f3f8b", linewidths=0.9, zorder=3)
        ax.contour(c.s, c.n, np.where(c.land, c.mov, 0.0), levels=[0.1], colors="#b0249a", linewidths=0.7, zorder=3)
    if houses:
        hs = M.houses()
        ax.plot(hs[:, 0], hs[:, 1], "s", ms=1.6, color="k", zorder=4)
    ax.set_xlim(box[0], box[1])
    ax.set_ylim(box[2], box[3])
    ax.set_aspect("equal")
    ax.tick_params(labelsize=7)
    return pm


def fig_maps(cases, dx):
    """格子 dx の 3 つの向き(行)× 8 近傍・4 近傍(列)の堆積厚の地図(谷と扇状地の全体)。"""
    keys = [(dx, th, nb) for th in THETAS for nb in (8, 4)]
    if not all(k in cases for k in keys):
        return
    fig, axs = plt.subplots(3, 2, figsize=(14, 8.4), constrained_layout=True)
    for k, ax in zip(keys, axs.flat):
        pm = thick_map(ax, cases[k], ALL_BOX)
        ax.axvline(M.L_V, color="k", ls="--", lw=0.6)
        ax.set_title(T(f"{dx:g} m・谷の向き {k[1]:g}°・{nb_label(k[2])}", f"{dx:g} m, valley at {k[1]:g}°, {nb_label(k[2])}"),
                     fontsize=10)
    for ax in axs[-1]:
        ax.set_xlabel("s (m)")
    for ax in axs[:, 0]:
        ax.set_ylabel("n (m)")
    cb = fig.colorbar(pm, ax=axs, shrink=0.5, pad=0.01)
    cb.set_label(T("10 分後の堆積厚 (m)", "deposit thickness at 10 min (m)"))
    fig.suptitle(T(f"格子 {dx:g} m: 堆積厚(色)、最大流動深 1 m の線(青)、10 分後も流れている泥の先(赤紫。かさ厚 0.1 m)、"
                   "家屋(黒の点)\n左: ENC の 8 近傍、右: 4 近傍の対照。破線 = 谷の出口",
                   f"{dx:g} m grid: deposit (colour), 1 m line of the maximum flow depth (blue), edge of the mud still moving "
                   "at 10 min (magenta; 0.1 m bulk), houses (black dots)\nLeft: ENC 8 neighbours; right: 4-neighbour control. "
                   "Dashed = valley mouth"), fontsize=10)
    fig.savefig(f"{FIGDIR}/maps_{dx:g}m.png", dpi=100)
    plt.close(fig)


def contour_set(ax, c, color, ls_t="-", ls_d="--"):
    ax.contour(c.s, c.n, np.where(c.land, c.dep, 0.0), levels=[0.5], colors=[color], linewidths=1.3, linestyles=ls_t, zorder=3)
    ax.contour(c.s, c.n, np.where(c.land, c.D, 0.0), levels=[1.0], colors=[color], linewidths=1.0, linestyles=ls_d, zorder=3)


def fig_overlay(cases):
    """扇状地の堆積厚 0.5 m と最大流動深 1 m の線を重ねる。上: 8 近傍、下: 4 近傍。
    左 3 列 = 格子 40・20・5 m の 3 つの向き、右端 = 谷の向き 0° の格子間隔。"""
    cols = [(f"{dx:g} m", [(dx, th) for th in THETAS], "th") for dx in (40.0, 20.0, 5.0)]
    cols.append((T("谷の向き 0°", "valley at 0°"), [(dx, 0.0) for dx in DXS_ALL], "dx"))
    fig, axs = plt.subplots(2, 4, figsize=(19, 9.4), constrained_layout=True)
    hs = M.houses()
    for row, nb in enumerate((8, 4)):
        for col, (title, keys, by) in enumerate(cols):
            ax = axs[row, col]
            terrain_bg(ax, FAN_BOX)
            ax.plot(hs[:, 0], hs[:, 1], "s", ms=1.3, color="0.35", zorder=2)
            handles = []
            for dx, th in keys:
                k = (dx, th, nb)
                if k not in cases:
                    continue
                color = COL_TH[th] if by == "th" else COL_DX[dx]
                contour_set(ax, cases[k], color)
                handles.append(Line2D([], [], color=color, lw=1.4, label=(th_label(th) if by == "th" else f"{dx:g} m")))
            handles += [Line2D([], [], color="k", lw=1.3, label=T("堆積厚 0.5 m", "deposit 0.5 m")),
                        Line2D([], [], color="k", lw=1.0, ls="--", label=T("最大流動深 1 m", "max flow depth 1 m"))]
            ax.legend(handles=handles, fontsize=7.5, loc="lower right", framealpha=0.9)
            ax.set_xlim(FAN_BOX[0], FAN_BOX[1])
            ax.set_ylim(FAN_BOX[2], FAN_BOX[3])
            ax.set_aspect("equal")
            ax.set_title(T(f"{nb_label(nb)}・{title}" + ("" if by == "dx" else ": 谷の向き"),
                           f"{nb_label(nb)}, {title}" + ("" if by == "dx" else ": valley at")), fontsize=10)
            ax.tick_params(labelsize=7)
            if row == 1:
                ax.set_xlabel("s (m)")
        axs[row, 0].set_ylabel("n (m)")
    fig.savefig(f"{FIGDIR}/overlay.png", dpi=100)
    plt.close(fig)


DEP_KEYS = [("T_fan", "扇状地に届いた土砂(堆積 + 流動中)(m³)", "sediment that reached the fan (deposit + moving) (m³)"),
            ("A_0.1", "扇状地の堆積厚 ≥ 0.1 m の面積 (m²)", "fan area with deposit ≥ 0.1 m (m²)"),
            ("ang_std", "扇状地の堆積の横への広がり(角度の標準偏差, °)",
             "lateral spreading of the fan deposit (angle std, °)"),
            ("D1_fan", "扇状地の最大流動深 ≥ 1 m の面積 (m²)", "fan area with maximum flow depth ≥ 1 m (m²)"),
            ("t_mouth", "前縁が扇頂に達した時刻 (s)", "time the front reached the fan apex (s)"),
            ("n_house_D1", "流動深 ≥ 1 m の家屋の数", "houses reached with flow depth ≥ 1 m"),
            ("V_valley", "谷の中の堆積(崩壊地の外)(m³)", "deposit in the valley outside the scar (m³)")]


def fig_dependence(cases, mets, l1):
    """格子間隔に対する、向きによる差と主な指標(8 近傍と 4 近傍)。2.5 m は谷の向き 0° だけ。"""
    fig, axs = plt.subplots(2, 4, figsize=(19, 8.8), constrained_layout=True)
    axl = axs.flat
    xt = list(DXS_ALL)[::-1]
    off = {8: 0.94, 4: 1.06}
    mk = {0.0: "o", 22.5: "s", 45.0: "^"}
    nbcol = {8: "#1f5f8b", 4: "#c0392b"}
    # (a) 地図の差
    ax = axl[0]
    for nb in (8, 4):
        for j, (lab_ja, lab_en, ls) in enumerate([("堆積厚", "deposit", "-"), ("最大流動深", "max flow depth", "--")]):
            xs = [dx for dx in DXS if (dx, 22.5, nb) in l1 and (dx, 45.0, nb) in l1]
            ys = [100 * 0.5 * (l1[(dx, 22.5, nb)][j] + l1[(dx, 45.0, nb)][j]) for dx in xs]
            ax.plot(xs, ys, ls, marker="o", color=nbcol[nb], lw=1.5, ms=5,
                    label=T(f"{nb_label(nb)}・{lab_ja}", f"{nb_label(nb)}, {lab_en}"))
    ax.set_ylabel(T("0° との差 (%)(22.5°・45° の平均)", "difference from 0° (%) (mean of 22.5° and 45°)"))
    ax.set_title(T("(a) 谷の向きによる地図の差(L1)", "(a) Map difference due to the valley orientation (L1)"), fontsize=10)
    ax.legend(fontsize=8)
    # (b)〜(h) 指標
    ref = mets[REF_KEY]
    for ax, (key, ja, en), tag in zip(axl[1:], DEP_KEYS, "bcdefgh"):
        for nb in (8, 4):
            for th in THETAS:
                xs = [dx for dx in DXS_ALL if (dx, th, nb) in mets]
                ys = [mets[(dx, th, nb)][key] for dx in xs]
                ax.plot([x * off[nb] for x in xs], ys, mk[th], color=nbcol[nb], ms=6,
                        mfc=nbcol[nb] if nb == 8 else "none", ls="")
            xs = [dx for dx in DXS if all((dx, th, nb) in mets for th in THETAS)]
            mid = [np.median([mets[(dx, th, nb)][key] for th in THETAS]) for dx in xs]
            if (M.DX_REF, 0.0, nb) in mets:
                xs, mid = xs + [M.DX_REF], mid + [mets[(M.DX_REF, 0.0, nb)][key]]
            ax.plot([x * off[nb] for x in xs], mid, "-", color=nbcol[nb], lw=1.0, alpha=0.7)
        ax.axhspan(0.9 * ref[key], 1.1 * ref[key], color="0.88", zorder=0)
        ax.axhline(ref[key], color="k", lw=0.7)
        ax.set_title(f"({tag}) " + T(ja, en), fontsize=9.5)
        ax.set_ylim(bottom=0)
    for ax in axl:
        ax.set_xscale("log")
        ax.set_xticks(xt)
        ax.set_xticklabels([f"{x:g}" for x in xt])
        ax.minorticks_off()
        ax.set_xlabel(T("格子間隔 Δx (m)", "grid spacing Δx (m)"))
        ax.grid(alpha=0.3)
    handles = [Line2D([], [], color=nbcol[8], marker="o", ls="-", label=T("ENC の 8 近傍(塗り)", "ENC 8 neighbours (filled)")),
               Line2D([], [], color=nbcol[4], marker="o", mfc="none", ls="-", label=T("4 近傍(白抜き)", "4 neighbours (open)"))]
    handles += [Line2D([], [], color="k", marker=mk[th], ls="", mfc="none", label=T(f"谷の向き {th:g}°", f"valley at {th:g}°"))
                for th in THETAS]
    handles += [Line2D([], [], color="k", lw=0.7, label=T("基準(8 近傍・2.5 m・0°)", "reference (8 neighbours, 2.5 m, 0°)")),
                Line2D([], [], color="0.88", lw=8, label=T("基準 ±10 %", "reference ±10 %")),
                Line2D([], [], color="0.5", lw=1.0, label=T("線 = 3 つの向きの中央値(2.5 m は 0°)",
                                                           "line = median of the three orientations (0° at 2.5 m)"))]
    fig.legend(handles=handles, loc="outside lower center", ncol=4, fontsize=9, frameon=False)
    fig.savefig(f"{FIGDIR}/dependence.png", dpi=100)
    plt.close(fig)


def style(k):
    """線の色(格子間隔)と線種(向き)。"""
    dx, th, nb = k
    ls = {0.0: "-", 22.5: "--", 45.0: ":"}[th]
    return COL_DX[dx], ls


def path_profile(c, dxi=5.0):
    """堆積の、谷筋〜扇状地の軸に沿う分布 (m³/m)。各ケースの場を細かい点で双一次補間して積分する
    (格子のセルの数え方による縞を避ける)。谷(s ≤ L_V)は横断 n の積分、扇状地は扇頂を中心とする
    半径 r の半円の弧の積分。崩壊地の中は除く。"""
    t = np.where(c.scar, 0.0, c.dep)
    out_x, out_v = [], []
    nn = np.arange(-250.0, 250.0, 1.0) + 0.5
    for s0 in np.arange(150.0, M.L_V, dxi) + dxi / 2:
        out_x.append(s0)
        out_v.append(c.sample(t, np.full_like(nn, s0), nn).sum() * 1.0)
    for r0 in np.arange(0.0, 450.0, dxi) + dxi / 2:
        phi = np.radians(np.arange(-90.0, 90.0, 0.5) + 0.25)
        out_x.append(M.L_V + r0)
        out_v.append(c.sample(t, M.L_V + r0 * np.cos(phi), r0 * np.sin(phi)).sum() * r0 * np.radians(0.5))
    return np.array(out_x), np.array(out_v)


def angle_profile(c, dphi=2.0):
    """扇状地の堆積の、扇頂から見た向きごとの量 (m³/°)。半径方向の積分(0〜450 m)を双一次補間で求める。"""
    rr = np.arange(0.0, 450.0, 1.0) + 0.5
    t = np.where(c.fan, c.dep, 0.0)
    ang = np.arange(-90.0, 90.0, dphi) + dphi / 2
    v = [(c.sample(t, M.L_V + rr * math.cos(math.radians(a)), rr * math.sin(math.radians(a))) * rr).sum()
         * math.radians(1.0) for a in ang]
    return ang, np.array(v)


def fig_series(cases):
    """上: 8 近傍、下: 4 近傍。左: 前縁の位置、中: 谷と扇状地の堆積の縦断分布、右: 扇状地での堆積の広がり。"""
    fig, axs = plt.subplots(2, 3, figsize=(16, 8.8), constrained_layout=True)
    for row, nb in enumerate((8, 4)):
        sel = {k: c for k, c in cases.items() if k[2] == nb}
        ax = axs[row, 0]
        for k, c in sel.items():
            col, ls = style(k)
            fr = c.front()
            ax.plot(fr[:, 0], fr[:, 1], ls, color=col, lw=1.2)
        ax.axhline(M.L_V, color="k", lw=0.6)
        ax.axhline(M.L_V + M.R_H1, color="#1f3f8b", lw=0.6)
        ax.text(178, M.L_V - 40, T("扇頂", "fan apex"), fontsize=8, ha="right")
        ax.text(178, M.L_V + M.R_H1 + 12, T("住宅地の端", "edge of town"), fontsize=8, ha="right", color="#1f3f8b")
        ax.set_xlim(0, 180)
        ax.set_ylim(200, M.L_V + 450)
        ax.set_xlabel(T("時刻 (s)", "time (s)"))
        ax.set_ylabel(T("前縁の位置(谷筋〜扇状地の軸に沿う距離)(m)", "front position along the valley and fan axis (m)"))
        ax.set_title(T(f"{nb_label(nb)}: 前縁(流動深 ≥ {H_FRONT:g} m)の位置",
                       f"{nb_label(nb)}: front position (flow depth ≥ {H_FRONT:g} m)"), fontsize=10)
        ax.grid(alpha=0.3)
        ax = axs[row, 1]
        for k, c in sel.items():
            col, ls = style(k)
            xi, v = path_profile(c)
            ax.plot(xi, v, ls, color=col, lw=1.1)
        ax.axvline(M.L_V, color="k", lw=0.6)
        ax.set_xlim(150, M.L_V + 450)
        ax.set_xlabel(T("谷筋〜扇状地の軸に沿う距離 (m)(扇状地は扇頂 + 扇頂からの距離)",
                        "distance along the valley and fan axis (m) (apex + radius on the fan)"))
        ax.set_ylabel(T("堆積(崩壊地の外)(m³/m)", "deposit outside the scar (m³/m)"))
        ax.set_title(T(f"{nb_label(nb)}: 谷と扇状地の堆積の縦断分布(10 分後)",
                       f"{nb_label(nb)}: deposit along the path (at 10 min)"), fontsize=10)
        ax.grid(alpha=0.3)
        ax = axs[row, 2]
        for k, c in sel.items():
            col, ls = style(k)
            ang, v = angle_profile(c)
            ax.plot(ang, v, ls, color=col, lw=1.1)
        ax.set_xlabel(T("扇頂から見た向き (°)(0 = 谷の軸、正 = 北)", "direction from the apex (°) (0 = valley axis, + = north)"))
        ax.set_ylabel(T("扇状地の堆積 (m³/°)", "deposit on the fan (m³/°)"))
        ax.set_title(T(f"{nb_label(nb)}: 扇状地での堆積の広がり(10 分後)",
                       f"{nb_label(nb)}: spreading on the fan (at 10 min)"), fontsize=10)
        ax.grid(alpha=0.3)
    for row in range(2):
        ymax = max(axs[0, 1].get_ylim()[1], axs[1, 1].get_ylim()[1])
        axs[row, 1].set_ylim(0, ymax)
        ymax = max(axs[0, 2].get_ylim()[1], axs[1, 2].get_ylim()[1])
        axs[row, 2].set_ylim(0, ymax)
    handles = [Line2D([], [], color=COL_DX[dx], lw=1.4, label=f"{dx:g} m") for dx in DXS]
    handles += [Line2D([], [], color="k", ls=ls, lw=1.2, label=th_label(th)) for th, ls in ((0.0, "-"), (22.5, "--"), (45.0, ":"))]
    axs[0, 2].legend(handles=handles, fontsize=8, loc="upper right")
    fig.savefig(f"{FIGDIR}/series.png", dpi=100)
    plt.close(fig)


def main():
    if "setup" in sys.argv[1:]:
        fig_setup()
        return
    fig_setup()
    cases = load_all()
    mets = {k: c.metrics() for k, c in cases.items()}
    print_table(cases, mets)
    print_summary(cases, mets)
    print_ranges(mets)
    l1 = l1_orientation(cases)
    for dx in (40.0, 20.0, 5.0):
        fig_maps(cases, dx)
    fig_overlay(cases)
    fig_series(cases)
    if REF_KEY in mets:
        fig_dependence(cases, mets, l1)


if __name__ == "__main__":
    main()
