#!/usr/bin/env python3
"""debris_fan の図と数表(事前に make run で全ケースを計算しておく)。

  figs/setup.png       模式地形(崩壊斜面・谷・扇状地・住宅地)、谷筋の縦断、谷の横断、格子に対する谷の向き
  figs/grid.png        格子 40・20 m の谷底のセルのつながり方(入力だけ。計算結果を使わない)
  figs/mechanism.png   崩壊から扇状地までの仕組みと、崩壊土塊・水・堆積の量の内訳(入力だけ)
  figs/laws.png        高橋・中川 (1991) の抵抗則の切り替え・慣性走行・平衡濃度(param.txt の値で式を評価)
  figs/maps_40m.png    格子 40 m の 3 つの向きの堆積厚と最大流動深(左: ENC の 8 近傍、右: 4 近傍)
  figs/maps_20m.png    同じく格子 20 m
  figs/maps_5m.png     同じく格子 5 m
  figs/overlay.png     扇状地の堆積厚 0.5 m と最大流動深 1 m の線を、向き・格子間隔ごとに重ねた図(上 8 近傍、下 4 近傍)
  figs/dependence.png  格子間隔に対する、向きによる地図の差と主な指標(8 近傍と 4 近傍)
  figs/series.png      前縁の位置の時間変化、谷と扇状地の堆積の縦断分布、扇状地での堆積の広がり
数表(標準出力): 各ケースの指標、向きの差と格子の差のまとめ、地図の差。
ケースの座標はすべて谷沿いの座標 (s, n)(make_init.py)。体積・面積は各ケースの格子のセルで数え、
向きの比較の地図の差(L1)は谷沿いの共通の 5 m 格子へ双一次補間して求める。
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。計算結果がなければ説明図
(setup・grid・mechanism・laws)だけを描く。
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
from matplotlib.lines import Line2D
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


# ---------------------------------------------------------------- 図: 格子と谷底のセル(入力だけ)
GRID_CASES = [(40.0, 0.0), (40.0, 22.5), (40.0, 45.0), (20.0, 45.0)]
GRID_BOX = (560.0, 860.0, -75.0, 75.0)        # 描く範囲 (s0, s1, n0, n1)
REL_CMAP = plt.get_cmap("YlOrBr")


def floor_cells(dx, th):
    """make_init.py の格子で、中心が谷底(|n| ≤ WF/2)にある陸のセルと、谷底からの高さ。"""
    nx, ny, ox, oy, out = M.grid(dx, th)
    s, n = M.to_sn(dx, th)
    land = (out["mask"] > 0) & (out["sw"] == 0)
    rel = np.where(land, out["z"] - M.z_axis(np.clip(s, 0.0, M.L_V)), np.nan)   # 同じ s の谷底からの高さ
    floor = land & (np.abs(n) <= M.WF / 2) & (s <= M.L_V)
    return s, n, rel, floor, (nx, ny, ox, oy)


def _cell_poly(dx, th, ox, oy, i, j):
    t = math.radians(th)
    c, sn = math.cos(t), math.sin(t)
    xs = np.array([i, i + 1, i + 1, i]) * dx - ox
    ys = np.array([j, j, j + 1, j + 1]) * dx - oy
    return np.c_[xs * c - ys * sn, xs * sn + ys * c]


def grid_panel(ax, dx, th, box=GRID_BOX):
    s, n, rel, floor, (nx, ny, ox, oy) = floor_cells(dx, th)
    s0, s1, n0, n1 = box
    near = (s > s0 - dx) & (s < s1 + dx) & (n > n0 - dx) & (n < n1 + dx) & np.isfinite(rel)
    for j, i in np.argwhere(near):
        col = REL_CMAP(min(rel[j, i], 24.0) / 24.0 * 0.85)
        ax.add_patch(Polygon(_cell_poly(dx, th, ox, oy, i, j), closed=True, facecolor=col, edgecolor="0.55",
                             lw=0.5, zorder=1))
        if rel[j, i] < 7.5:
            ax.text(s[j, i], n[j, i] - 0.16 * dx, f"{rel[j, i]:.1f}", fontsize=6.6 if dx > 30 else 6.0, ha="center",
                    va="top", color="0.2", zorder=6, clip_on=True)
    # the true valley floor and the foot of the walls
    ax.axhspan(-M.WF / 2, M.WF / 2, color="#1f5f8b", alpha=0.10, zorder=2, lw=0)
    for y in (-M.WF / 2, M.WF / 2):
        ax.axhline(y, color="#1f5f8b", lw=0.9, ls="--", zorder=3)
    fl = [tuple(q) for q in np.argwhere(floor & near)]
    fset = set(fl)
    for j, i in fl:
        ax.plot(s[j, i], n[j, i], "o", color="#1f5f8b", ms=5, zorder=7)
    others = np.argwhere(near & ~floor)
    ax.plot(s[others[:, 0], others[:, 1]], n[others[:, 0], others[:, 1]], ".", color="0.45", ms=2.5, zorder=6)
    # edges between floor cells: axis edges (both stencils) and diagonal edges (eight neighbours only)
    n_diag_only = 0
    for j, i in fl:
        for dj, di in ((0, 1), (1, 0)):
            q = (j + dj, i + di)
            if q in fset:
                ax.plot([s[j, i], s[q]], [n[j, i], n[q]], color="0.15", lw=2.2, zorder=5, solid_capstyle="round")
        for dj, di in ((1, 1), (1, -1)):
            q = (j + dj, i + di)
            if q in fset:
                ax.plot([s[j, i], s[q]], [n[j, i], n[q]], color="#d9480f", lw=1.8, ls=(0, (3, 1.6)), zorder=5)
                c1, c2 = (j, i + di), (j + dj, i)
                if c1 not in fset and c2 not in fset:      # 角でしかつながらない: 4 近傍は低い方の共通の軸の隣を通る
                    cb = c1 if rel[c1] <= rel[c2] else c2
                    ax.plot([s[j, i], s[cb], s[q]], [n[j, i], n[cb], n[q]], color="#6a3d9a", lw=1.3, zorder=4)
                    ax.plot(s[cb], n[cb], "s", color="#6a3d9a", ms=4, zorder=6)
    for j, i in fl:
        ax_n = [(j, i + 1), (j, i - 1), (j + 1, i), (j - 1, i)]
        if not any(q in fset for q in ax_n):
            n_diag_only += 1
    ax.set_xlim(s0, s1)
    ax.set_ylim(n0, n1)
    ax.set_aspect("equal")
    ax.tick_params(labelsize=7.5)
    return len(fl), n_diag_only


def fig_grid():
    fig, axs = plt.subplots(2, 2, figsize=(13.6, 8.6))
    fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.17, wspace=0.12, hspace=0.38)
    fig.suptitle(T("谷底と格子のセル: 谷の向きと格子の大きさで、谷底のセルのつながり方が変わる(入力から描いた図)",
                   "Valley floor and grid cells: how the floor cells connect depends on the valley orientation and the cell size "
                   "(drawn from the inputs)"), fontsize=11, x=0.06, ha="left")
    notes = {
        (40.0, 0.0): T("谷底(破線の間)にセルの中心がない。谷は谷底より 3.5 m 高い 2 列(幅 80 m)で表される",
                       "no cell centre on the floor (between the dashes); the valley is two rows 3.5 m above it (80 m wide)"),
        (40.0, 22.5): T("軸でつながる 2 個ずつの組。組の間は角でつながるか、谷底の外のセル(5〜7 m 高い)をはさむ",
                        "pairs joined along an axis; between pairs a corner link or a cell outside the floor (5–7 m higher)"),
        (40.0, 45.0): T("谷底のセルは角でしかつながらない。4 近傍は谷底より 2.7 m 高いセルを通る",
                        "floor cells touch only at corners; four neighbours pass through cells 2.7 m above the floor"),
        (20.0, 45.0): T("谷底のセルは軸のエッジでつながる 2 列の階段。8 近傍は谷に沿う斜めのエッジでもつながる",
                        "a two-row staircase of axis edges; eight neighbours also link the floor cells along the valley"),
    }
    for ax, (dx, th) in zip(axs.ravel(), GRID_CASES):
        nf, nd = grid_panel(ax, dx, th)
        ax.set_title(T(f"格子 {dx:g} m・谷の向き {th:g}°", f"{dx:g} m grid, valley at {th:g}°"), fontsize=10, loc="left")
        ax.text(0.0, -0.17, notes[(dx, th)], transform=ax.transAxes, fontsize=8.4, va="top")
        ax.set_xlabel(T("s (m)  谷を下る向き", "s (m)  down the valley"), fontsize=8.5)
        ax.set_ylabel("n (m)", fontsize=8.5)
    handles = [Line2D([], [], color="#1f5f8b", marker="o", ls="none", ms=5, label=T("谷底のセル(中心が谷底)", "floor cell (centre on the floor)")),
               Line2D([], [], color="0.15", lw=2.2, label=T("谷底のセルの間の軸のエッジ(8 近傍・4 近傍とも)", "axis edge between floor cells (both)")),
               Line2D([], [], color="#d9480f", lw=1.8, ls=(0, (3, 1.6)), label=T("谷底のセルの間の斜めのエッジ(8 近傍だけ)", "diagonal edge between floor cells (eight neighbours only)")),
               Line2D([], [], color="#6a3d9a", lw=1.3, marker="s", ms=4, label=T("角でしかつながらない所の 4 近傍の回り道", "four-neighbour detour where cells touch only at corners")),
               Line2D([], [], color="#1f5f8b", lw=0.9, ls="--", label=T("谷底(幅 30 m)の縁", "edges of the floor (30 m wide)"))]
    fig.legend(handles=handles, loc="lower left", ncol=3, fontsize=8.3, frameon=False, bbox_to_anchor=(0.05, 0.0))
    sm = plt.cm.ScalarMappable(cmap=ListedColormap(REL_CMAP(np.linspace(0, 0.85, 256))), norm=plt.Normalize(0, 24))
    cax = fig.add_axes([0.74, 0.085, 0.17, 0.018])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_label(T("同じ s の谷底からの高さ (m)\n数字は 7.5 m 未満のセルの値", "height above the floor at the same s (m)\nnumbers: cells below 7.5 m"), fontsize=7.8)
    cb.ax.tick_params(labelsize=7)
    fig.savefig(f"{FIGDIR}/grid.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 図: 仕組み(入力と設定だけ)
C_SOL, C_WAT, C_DEB, C_DEP2, C_GRD = "#8c5a2b", "#7fb3d5", "#c8a17a", "#e0b070", "#d8cdb8"


def _stack(ax, x, parts, w=0.62):
    y = 0.0
    for v, col, lab, tc in parts:
        ax.bar([x], [v], bottom=[y], width=w, color=col, edgecolor="white", lw=0.8)
        if lab:
            ax.text(x, y + v / 2, lab, ha="center", va="center", fontsize=8.2, color=tc)
        y += v
    return y


def fig_mechanism():
    lam, c0, v0 = M.LAMBDA, M.C0, M.V0 / 1e4                 # 空隙率、流れ出す濃度、崩壊土量(万 m³)
    sol, pore = (1 - lam) * v0, lam * v0
    extra = v0 * ((1 - lam) / c0 - 1)                         # 崩壊域に置く水(make_init.py の h)
    water = pore + extra
    dep_pore = sol * lam / (1 - lam)                          # 固体がすべて空隙率 λ で積もったときの間隙水
    fig = plt.figure(figsize=(14, 8.8))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.05, 1.6, 1.1], height_ratios=[1, 1], hspace=0.42, wspace=0.28,
                          left=0.05, right=0.98, top=0.9, bottom=0.07)
    fig.suptitle(T("崩壊から扇状地まで(模式)。量は入力(make_init.py)から求めた値、時間の区切りは結果の節の基準のケース",
                   "From the collapse to the fan (schematic). Volumes are from the inputs (make_init.py); the time ranges are "
                   "those of the reference case in the results"), fontsize=10.5, x=0.05, ha="left")
    # (a) composition of the released mass
    ax = fig.add_subplot(gs[:, 0])
    _stack(ax, 0, [(sol, C_SOL, T(f"固体\n{sol:.0f} 万", f"solid\n{sol:.0f}"), "white"),
                   (pore, C_WAT, T(f"間隙水\n{pore:.0f} 万", f"pore water\n{pore:.0f}"), "black")])
    _stack(ax, 1, [(extra, C_WAT, T(f"水\n{extra:.1f} 万", f"water\n{extra:.1f}"), "black")])
    _stack(ax, 2, [(sol, C_SOL, T(f"固体\n{sol:.0f} 万", f"solid\n{sol:.0f}"), "white"),
                   (water, C_WAT, T(f"水\n{water:.1f} 万", f"water\n{water:.1f}"), "black")])
    _stack(ax, 3, [(sol, C_SOL, T("固体", "solid"), "white"),
                   (dep_pore, C_WAT, T(f"間隙\n{dep_pore:.0f} 万", f"pores\n{dep_pore:.0f}"), "black"),
                   (water - dep_pore, "#d6e9f5", T(f"余る水\n{water - dep_pore:.1f} 万", f"excess\n{water - dep_pore:.1f}"), "#1f5f8b")])
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels([T("崩壊土塊\n(飽和)", "collapse\nmass\n(saturated)"), T("崩壊域に\n置く水", "water placed\non the\ncollapse"),
                        T("流れ出す\n土石流", "debris flow\nreleased"), T("固体がすべて\n積もると", "if all solid\ndeposits")],
                       fontsize=8.2)
    ax.set_ylabel(T("体積(万 m³)", "volume (10⁴ m³)"))
    ax.set_ylim(0, 15.5)
    ax.text(2, sol + water + 0.3, T(f"濃度 {c0:.2f}", f"C = {c0:.2f}"), ha="center", fontsize=8.6, weight="bold")
    ax.text(0, v0 + 0.3, T(f"{v0:.0f} 万 m³", f"{M.V0:,.0f} m³"), ha="center", fontsize=8.4)
    ax.set_title(T("(a) 量の内訳", "(a) Volumes"), fontsize=10, loc="left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    # (b) cross-section at the collapse: slide and run-up on the opposite bank
    ax = fig.add_subplot(gs[0, 1])
    nl = np.linspace(-230, 230, 921)
    zl = M.terrain(np.full_like(nl, M.S_C), nl)
    dl = M.collapse_shape(np.full_like(nl, M.S_C), nl) * (M.V0 / (math.pi / 2 * M.A_S * M.A_N))
    zmin = zl.min()
    ax.fill_between(nl, zmin - 25, zl, color=C_GRD, lw=0)
    ax.plot(nl, zl, color="#6b4f2a", lw=1.3)
    ax.fill_between(nl, zl - dl, zl, where=dl > 0, color="#c0392b", alpha=0.45, lw=0)
    run = (nl > -60) & (nl < -8)
    runup = np.where(run, 9.0 * np.clip(np.sin(np.pi * (nl + 60) / 52), 0, None) ** 0.7, 0.0)
    ax.fill_between(nl, zl, zl + runup, where=run, color=C_DEP2, lw=0)
    ax.annotate("", xy=(-35, zmin + 26), xytext=(95, zmin + 62), arrowprops=dict(arrowstyle="-|>", color="#c0392b", lw=1.8,
                                                                                connectionstyle="arc3,rad=0.25"))
    ax.text(30, zmin + 166, T("① 北岸の斜面が崩れる\n   (崩壊深は中心で約 20 m)", "① the north wall collapses\n   (about 20 m deep at the centre)"),
            fontsize=8.2, color="#8b1a10", va="top")
    ax.text(-150, zmin + 166, T("② 勢いのまま谷底を横切り、\n   対岸の斜面を駆け上がる。\n   一部が対岸の脚に残る",
                                "② it crosses the floor and\n   runs up the far wall;\n   part stays at its foot"),
            fontsize=8.2, color="0.15", va="top")
    ax.set_xlim(-230, 230)
    ax.set_ylim(zmin - 25, zmin + 170)
    ax.set_aspect("equal")
    ax.set_xlabel(T("n (m)  谷を横切る向き(北岸が正)", "n (m)  across the valley (north bank +)"), fontsize=8.5)
    ax.set_ylabel(T("標高 (m)", "elevation (m)"), fontsize=8.5)
    ax.set_title(T(f"(b) 崩壊の中心の横断(s = {M.S_C:g} m)。崩壊直後(0〜20 秒)",
                   f"(b) Section at the collapse centre (s = {M.S_C:g} m), 0–20 s"),
                 fontsize=10, loc="left")
    ax.tick_params(labelsize=7.5)
    # (c) longitudinal sketch: valley run and fan deposition
    ax = fig.add_subplot(gs[1, 1:])
    xi = np.linspace(0, M.L_V + M.L_F, 1200)
    zb = M.z_axis(xi)
    ax.fill_between(xi, -10, zb, color=C_GRD, lw=0)
    ax.plot(xi, zb, color="#6b4f2a", lw=1.3)
    vf = (xi > 380) & (xi < 960)
    thk = np.where(vf, 14 * np.clip(np.sin(np.pi * (xi - 380) / 580), 0, None) ** 0.5, 0)
    ax.fill_between(xi, zb, zb + thk, where=vf, color=C_DEB, lw=0)
    dep = (xi > M.L_V) & (xi < M.L_V + 270)
    dth = np.where(dep, 10 * np.clip(np.sin(np.pi * (xi - M.L_V) / 270), 0, None) ** 0.6, 0)
    ax.fill_between(xi, zb, zb + dth, where=dep, color=C_DEP2, lw=0)
    mud = (xi > M.L_V + 120) & (xi < M.L_V + 380)
    ax.fill_between(xi, zb + np.where(xi < M.L_V + 270, dth, 0), zb + np.where(xi < M.L_V + 270, dth, 0) + 2.5, where=mud,
                    color=C_WAT, alpha=0.8, lw=0)
    ax.annotate("", xy=(930, M.z_axis(930) + 24), xytext=(560, M.z_axis(560) + 30),
                arrowprops=dict(arrowstyle="-|>", color="0.2", lw=1.6))
    ax.axvline(M.L_V, color="k", lw=0.8, ls="--")
    ax.text(M.L_V + 6, 352, T("谷の出口 = 扇頂", "valley mouth = fan apex"), fontsize=8.2, va="top")
    ax.text(330, 300, T("③ 谷の流下(20〜50 秒): 濃い土石流が速く流れ、\n    慣性で走る間は堆積しない",
                        "③ down the valley (20–50 s): the dense flow runs fast\n    and does not deposit while it runs on inertia"),
            fontsize=8.4, color="0.15")
    ax.text(M.L_V + 60, 180, T("④ 扇状地での堆積(1〜10 分): 広がって遅くなり、\n    舌状に堆積する",
                               "④ deposition on the fan (1–10 min): it spreads, slows\n    down and leaves a tongue-shaped deposit"),
            fontsize=8.4, color="0.15")
    ax.text(M.L_V + 300, 95, T("⑤ 余った水が薄い泥の流れになり、\n    堆積の先へ広がる", "⑤ the excess water becomes a thin mud\n    that spreads beyond the deposit"),
            fontsize=8.4, color="#1f5f8b")
    ax.axvspan(M.L_V + M.R_H1, M.L_V + M.R_H2, color="#1f5f8b", alpha=0.07, lw=0)
    ax.text(M.L_V + 0.5 * (M.R_H1 + M.R_H2), 12, T("住宅地", "houses"), ha="center", fontsize=8.2, color="#1f5f8b")
    ax.axvspan(M.S_C - M.A_S, M.S_C + M.A_S, color="#c0392b", alpha=0.12, lw=0)
    ax.text(M.S_C, 12, T("崩壊", "collapse"), ha="center", fontsize=8.2, color="#8b1a10")
    ax.set_xlim(0, M.L_V + M.L_F)
    ax.set_ylim(-10, 360)
    ax.set_xlabel(T("谷筋〜扇状地の軸に沿う距離 (m)(縦は 1.5 倍に誇張、流れの厚さは誇張)",
                    "distance along the valley and fan axis (m) (vertical ×1.5; flow thickness exaggerated)"), fontsize=8.5)
    ax.set_ylabel(T("標高 (m)", "elevation (m)"), fontsize=8.5)
    ax.set_title(T("(c) 谷筋と扇状地の縦断", "(c) Long profile of the valley and the fan"), fontsize=10, loc="left")
    ax.tick_params(labelsize=7.5)
    # (d) note on the settings
    ax = fig.add_subplot(gs[0, 2])
    ax.axis("off")
    ax.set_title(T("(d) 対応する設定", "(d) Settings"), fontsize=10, loc="left")
    rows = [(T("崩壊と流動化", "collapse, mobilization"), "fn_dbinit, db_reltime = 0, db_relsat = 1"),
            (T("崩壊域の水", "water on the collapse"), "f_htype = 1, fn_hinit"),
            (T("流れの抵抗", "resistance"), T("f_dbres = 3(高橋・中川の石礫型)", "f_dbres = 3 (Takahashi–Nakagawa stony)")),
            (T("侵食・堆積", "erosion, deposition"), T("f_dbed = 3(慣性で走る間は堆積しない)", "f_dbed = 3 (no deposition while running on inertia)")),
            (T("止まった土砂", "stopped sediment"), "f_dbstop = 1"),
            (T("堆積の間隙水", "pore water of deposits"), "f_dbwet = 1"),
            (T("侵食できる層", "erodible layer"), T("sd = 崩壊深(ほかは不侵食の基盤)", "sd = release depth (bedrock elsewhere)"))]
    y = 0.95
    for k, v in rows:
        ax.text(0.0, y, k, fontsize=8.4, transform=ax.transAxes, va="top")
        ax.text(0.0, y - 0.065, v, fontsize=8.0, transform=ax.transAxes, va="top", color="0.3")
        y -= 0.14
    ax.text(0.0, y - 0.03, T(f"(a) の見方: 空隙率 λ = {lam:g}(C* = {1 - lam:g})。崩壊域の初期水深は\n"
                             "h = D((1 − λ)/C0 − 1)。積もった土砂の間隙を流れの水が満たす\n"
                             "(f_dbwet = 1)ので、余った水が後続の薄い泥の流れになる。",
                             f"Reading (a): porosity λ = {lam:g} (C* = {1 - lam:g});\n"
                             "initial depth on the collapse h = D((1 − λ)/C0 − 1).\n"
                             "The flow's water fills the pores of the deposit\n"
                             "(f_dbwet = 1); the excess becomes the trailing mud."),
            fontsize=8.0, transform=ax.transAxes, va="top", color="0.2")
    fig.savefig(f"{FIGDIR}/mechanism.png", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- 図: 高橋・中川の則(式だけ)
TANPHI = math.tan(math.radians(35.0))       # param.txt の db_phi
SGRAV, D50, CMIN = 1.65, 0.3, 0.02          # fluv_sgrav(既定)、db_d50、db_cmin(既定)
TANA, AB, P_TN, HDMUD, CBL = 0.45, 0.02, 1.0 / 3.0, 30.0, 0.4   # m_swflow_enc・m_geomorph_debris の定数


def c_inf_tn(tn):
    """f_dbed = 3 の平衡濃度(石礫型の導出式。上限 0.9 C*。ceq_egashira)。"""
    tn = np.asarray(tn, float)
    out = np.where(tn > 0, tn / (SGRAV * (TANPHI - tn)), 0.0)
    return np.where(tn >= TANPHI, 0.9 * CSTAR, np.minimum(out, 0.9 * CSTAR))


def p_vc(h, c):
    """堆積が始まる速さ p v_c(高橋・中川 1991 の式 (15)(27)。m_geomorph_debris の f_dbed = 3)。"""
    tc = SGRAV * c / (SGRAV * c + 1) * TANPHI
    sc = tc / math.sqrt(1 + tc * tc)
    vc = 0.4 / D50 * math.sqrt(9.8 * sc / AB * (c + (1 - c) / (SGRAV + 1))) * ((CSTAR / c) ** (1 / 3) - 1) * h ** 1.5
    return P_TN * vc


def fig_laws():
    fig, axs = plt.subplots(1, 3, figsize=(14, 5.8))
    fig.subplots_adjust(left=0.05, right=0.98, top=0.85, bottom=0.33, wspace=0.3)
    fig.suptitle(T("高橋・中川 (1991) の則がこの例題で働く範囲(param.txt の値で式を評価。計算結果ではない)",
                   "Where the Takahashi–Nakagawa (1991) laws act in this example (expressions with the values of param.txt; "
                   "not computed results)"), fontsize=10.5, x=0.05, ha="left")
    note = dict(fontsize=7.9, va="top", linespacing=1.45)
    # (a) regimes of the resistance law
    ax = axs[0]
    hmax = 20.0
    ax.add_patch(plt.Rectangle((CBL * CSTAR, 0), 0.6 - CBL * CSTAR, HDMUD * D50, color="#e8d5bf", lw=0))
    ax.add_patch(plt.Rectangle((CMIN, 0), CBL * CSTAR - CMIN, HDMUD * D50, color="#d6e4ef", lw=0))
    ax.add_patch(plt.Rectangle((0, HDMUD * D50), 0.6, hmax - HDMUD * D50, color="#eeeeee", lw=0))
    ax.add_patch(plt.Rectangle((0, 0), CMIN, HDMUD * D50, color="#eeeeee", lw=0))
    ax.text(0.345, 4.6, T("石礫型\n(ダイラタント項)", "stony\n(dilatant term)"), ha="center", fontsize=8.6, color=C_SOL)
    ax.text(0.13, 4.6, T("掃流状\n集合流動", "collective\nform"), ha="center", fontsize=8.6, color="#1f5f8b")
    ax.text(0.2, 15.2, T("Manning 則\n(h_t ≥ 30 d。泥流域の規定)\n降伏の項は残る", "Manning\n(h_t ≥ 30 d; mud-flow rule)\nthe yield term remains"),
            ha="center", fontsize=8.2, color="0.3")
    ax.axhline(HDMUD * D50, color="0.4", lw=0.9, ls="--")
    ax.text(0.02, HDMUD * D50 + 0.2, "h_t = 30 d = 9 m", fontsize=7.8, color="0.3", va="bottom")
    ax.plot([0.45, 0.45], [9.0, 18.0], color="#c0392b", lw=3.0, solid_capstyle="butt")
    ax.text(0.465, 17.6, T("崩壊直後\nの土塊と、\n谷の上流\n側の前縁", "collapse\nmass and\nthe front\nin the\nupper\nvalley"),
            fontsize=7.6, color="#c0392b", va="top")
    ax.plot([0.45, 0.45], [0.5, 9.0], color=C_SOL, lw=3.0, solid_capstyle="butt")
    ax.text(0.465, 8.6, T("谷を下る\n土石流", "debris\nflow\ndown the\nvalley"), fontsize=7.6, color=C_SOL, va="top")
    ax.annotate("", xy=(0.1, 0.7), xytext=(0.36, 1.1), arrowprops=dict(arrowstyle="-|>", color="#1f5f8b", lw=1.2))
    ax.text(0.03, 1.5, T("後続の泥(薄まる)", "trailing mud (diluting)"), fontsize=7.6, color="#1f5f8b")
    ax.set_xlim(0, 0.6)
    ax.set_ylim(0, hmax)
    ax.set_xlabel(T("混合体積濃度 C", "mixture volume concentration C"), fontsize=8.8)
    ax.set_ylabel(T("流動深 h_t (m)(d = 0.3 m)", "flow depth h_t (m) (d = 0.3 m)"), fontsize=8.8)
    ax.set_title(T("(a) 抵抗則の切り替え(f_dbres = 3)", "(a) Regimes of the resistance law (f_dbres = 3)"), fontsize=9.5, loc="left")
    ax.text(0.0, -0.17, T("境は C = 0.4 C* = 0.24、c_min = 0.02、h_t = 30 d。\n"
                          "谷を下る流れの大半は石礫型で、深さ 9 m を超えるのは\n"
                          "崩壊直後の土塊と、谷の上流側を前縁が通る間だけ。\n"
                          "後続の泥は薄まると掃流状集合流動の式に移る。",
                          "Boundaries: C = 0.4 C* = 0.24, c_min = 0.02, h_t = 30 d.\n"
                          "Most of the valley flow is stony; it is deeper than 9 m\n"
                          "only in the collapse mass and while the front passes\n"
                          "the upper valley. The trailing mud moves to the\n"
                          "collective form as it dilutes."),
            transform=ax.transAxes, **note)
    # (b) inertial run and deposition
    ax = axs[1]
    hh = np.linspace(0.02, 12, 500)
    for c, ls, lab in ((0.45, "-", "C = 0.45"), (0.30, "--", "C = 0.30")):
        ax.plot(hh, [p_vc(h, c) for h in hh], color=C_SOL, lw=2.0, ls=ls, label=f"p v_c ({lab})")
    pv = np.array([p_vc(h, 0.45) for h in hh])
    ax.fill_between(hh, pv, 30, color="#f4f3ee", lw=0)
    ax.text(0.4, 27.5, T("V > p v_c: 慣性で走り、堆積しない", "V > p v_c: runs on inertia, no deposition"), fontsize=8.4,
            va="top")
    ax.text(11.8, 1.0, T("V < p v_c: 堆積する\n(率に (1 − V/(p v_c))⁴ を掛ける)", "V < p v_c: deposits\n(rate × (1 − V/(p v_c))⁴)"),
            fontsize=8.0, color=C_SOL, ha="right")
    h23 = (23.0 / p_vc(1.0, 0.45)) ** (2.0 / 3.0)
    ax.axhline(23.0, color="#c0392b", lw=0.9, ls=":")
    ax.text(11.8, 23.4, T(f"谷の中の最大流速 23 m/s(結果の節)。\n深さ {h23:.0f} m より浅ければ線より上",
                          f"max speed in the valley 23 m/s (results);\nabove the curve if shallower than {h23:.0f} m"),
            fontsize=7.6, color="#c0392b", va="bottom", ha="right")
    for h0 in (2.0, 5.0):
        v0 = p_vc(h0, 0.45)
        ax.plot(h0, v0, "o", color=C_SOL, ms=4)
        ax.text(h0 + 0.15, v0 - 0.3, f"{v0:.1f} m/s", fontsize=7.6, color=C_SOL, va="top")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 30)
    ax.set_xlabel(T("流動深 h_t (m)", "flow depth h_t (m)"), fontsize=8.8)
    ax.set_ylabel(T("流速 V (m/s)", "speed V (m/s)"), fontsize=8.8)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.72), fontsize=7.8, frameon=False)
    ax.set_title(T("(b) 慣性で走る間は堆積しない(f_dbed = 3)", "(b) No deposition while running on inertia (f_dbed = 3)"),
                 fontsize=9.5, loc="left")
    ax.text(0.0, -0.17, T("p = 1/3、d = 0.3 m、φ = 35°。堆積が始まる速さ p v_c は\n"
                          "流動深の 1.5 乗に比例し、濃度が低いほど大きい。\n"
                          "速く深い谷の流れは堆積せず、扇状地で薄く遅く\n"
                          "なると線より下に入って堆積する。",
                          "p = 1/3, d = 0.3 m, φ = 35°. The speed below which\n"
                          "deposition starts, p v_c, grows with depth to the 1.5\n"
                          "power and is larger for lower concentration. The fast,\n"
                          "deep valley flow does not deposit; on the fan it thins,\n"
                          "slows, falls below the curve and deposits."),
            transform=ax.transAxes, **note)
    # (c) equilibrium concentration along the path
    ax = axs[2]
    xi = np.linspace(0, M.L_V + M.L_F, 900)
    ci = c_inf_tn(M.slope_axis(xi))
    ax.plot(xi, ci, color=C_SOL, lw=2.0, label=T("平衡濃度 C∞(谷底・扇状地の軸の勾配)", "equilibrium C∞ (slope of the axis)"))
    ax.axhline(M.C0, color="#1f5f8b", lw=1.4, ls="--", label=T(f"流れ出す濃度 {M.C0:g}", f"released concentration {M.C0:g}"))
    ax.fill_between(xi, ci, M.C0, where=ci < M.C0, color="#f6e3c8", lw=0)
    ax.axvline(M.L_V, color="k", lw=0.8, ls="--")
    ax.axvspan(M.S_C - M.A_S, M.S_C + M.A_S, color="#c0392b", alpha=0.12, lw=0)
    ax.text(M.S_C, 0.03, T("崩壊", "collapse"), ha="center", fontsize=8, color="#8b1a10")
    ax.text(M.L_V + 10, 0.03, T("扇頂", "apex"), fontsize=8)
    ax.text(520, 0.33, T("C∞ < C: 遅くなれば\n堆積する側", "C∞ < C: deposits\nonce it slows"), fontsize=8.2, color=C_SOL)
    for x0 in (M.L_V, M.L_V + M.L_F):
        cv = float(c_inf_tn(M.slope_axis(x0)))
        ax.plot(x0, cv, "o", color=C_SOL, ms=4)
        ax.text(x0 - 15, cv + 0.02, f"{cv:.2f}", fontsize=8, ha="right")
    ax.set_xlim(0, M.L_V + M.L_F)
    ax.set_ylim(0, 0.7)
    ax.set_xlabel(T("谷筋〜扇状地の軸に沿う距離 (m)", "distance along the valley and fan axis (m)"), fontsize=8.8)
    ax.set_ylabel(T("濃度", "concentration"), fontsize=8.8)
    ax.legend(loc="upper right", fontsize=7.6, frameon=False)
    ax.set_title(T("(c) 平衡濃度と流れの濃度", "(c) Equilibrium and flow concentration"), fontsize=9.5, loc="left")
    ax.text(0.0, -0.17, T("崩壊地より下流では C∞ が 0.45 を下回り、流れは\n"
                          "堆積する側にある(侵食できるのは崩壊域の土層と\n"
                          "積もった土砂だけ)。勾配は流動面の勾配\n"
                          "(等流では谷底の勾配)。",
                          "Downstream of the collapse C∞ is below 0.45, so the\n"
                          "flow is on the depositing side (only the collapse soil\n"
                          "and the deposits are erodible). The slope is that of\n"
                          "the flow surface (the bed slope for uniform flow)."),
            transform=ax.transAxes, **note)
    for a in axs:
        a.tick_params(labelsize=7.8)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.savefig(f"{FIGDIR}/laws.png", dpi=100)
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
    handles = [Line2D([], [], color=COL_DX[dx], lw=1.4, label=f"{dx:g} m") for dx in DXS_ALL]
    handles += [Line2D([], [], color="k", ls=ls, lw=1.2, label=th_label(th)) for th, ls in ((0.0, "-"), (22.5, "--"), (45.0, ":"))]
    axs[0, 2].legend(handles=handles, fontsize=8, loc="upper right")
    fig.savefig(f"{FIGDIR}/series.png", dpi=100)
    plt.close(fig)


def main():
    fig_setup()
    fig_grid()
    fig_mechanism()
    fig_laws()
    if "setup" in sys.argv[1:]:
        return
    cases = load_all()
    if not cases:
        print("計算結果がないので、説明図(setup・grid・mechanism・laws)だけを描いた")
        return
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
