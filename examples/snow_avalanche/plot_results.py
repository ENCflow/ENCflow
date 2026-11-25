#!/usr/bin/env python3
"""snow_avalanche の図と数表(事前に make run、補足の図には make extra で計算しておく)。

  figs/setup.png       模式地形(発生区・走路の雪の帯・扇状地・誘導堤・家屋)、沢筋の縦断、横断
  figs/mechanism.png   雪の読み替えとキャリア、Voellmy 則の等流の速さ、連行の速さ(入力と式だけ)
  figs/flow.png        基本ケースの流動深の時間変化、最大流動深、最終の侵食・堆積
  figs/entrain.png     走路の雪 0・1・2 m の最大流動深と堆積、流れている雪の量・先頭の位置・沢筋の最大流速
  figs/runout.png      到達距離: 沢筋の縦断と先端、見通し角 α と α–β の式(走路の雪と摩擦係数)
  figs/dam.png         誘導堤なし・ありの最大流動深と堆積、家屋
  figs/grid.png        格子間隔・沢の向き・時間刻みへの依存(堆積と最大流動深の線の重ね描きと指標)
  figs/limits.png      限界水深への依存と、全面に雪を置いた計算の横への広がり
数表(標準出力): 各ケースの指標、家屋、誘導堤、台帳の閉じ。
ケースの座標はすべて沢沿いの座標 (s, n)(make_init.py)。体積・面積は各ケースの格子のセルで数える。
引数 en で英語ラベル版を en/figs/ に描く(データと描画処理は共通)。計算結果がないケースの図は飛ばす
(setup・mechanism は入力と式だけで描ける)。
"""
import math
import os
import re
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import make_init as M

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["font.size"] = 9
os.makedirs(FIGDIR, exist_ok=True)

G = 9.80665
H_THR = 0.1                     # 先頭・到達・堆積の範囲を数える雪の厚さ (m)
H_VEL = 0.5                     # 最大流速を読むセルの最大流動深の下限 (m)
H_HOUSE = 0.5                   # 家屋に届いたと数える最大流動深 (m)
RHO = 300.0                     # 流れている雪の密度の目安 (kg/m³。圧力の目安 ρV² にだけ使う)
S_CROWN = M.S_C - M.A_S         # 発生区の上端(見通し角の起点)
COL = {"nosnow": "#7a7a7a", "base": "#1f5f8b", "deep": "#c0392b", "mu155": "#2b8a3e", "mu340": "#d08c00",
       "dam": "#1f5f8b", "deep_dam": "#c0392b"}
DEPTH_CMAP = ListedColormap(plt.get_cmap("YlGnBu")(np.linspace(0.12, 1.0, 256)))
DZ_CMAP = plt.get_cmap("RdBu")


def label(name):
    return {"nosnow": T("走路の雪なし", "no snow on the track"), "base": T("走路の雪 1 m(基本)", "1 m of track snow (base)"),
            "deep": T("走路の雪 2 m", "2 m of track snow"), "dam": T("基本 + 誘導堤", "base + deflecting dam"),
            "deep_dam": T("雪 2 m + 誘導堤", "2 m snow + deflecting dam"),
            "mu155": "μ = 0.155, ξ = 3000", "mu340": "μ = 0.34, ξ = 1350"}.get(name, name)


# ---------------------------------------------------------------- 地形と経験則
def beta_point():
    """勾配が 10° になる沢筋の位置(β 点)と β 角。"""
    sb = M.L_P * (M.S_TOP - math.tan(math.radians(10.0))) / (M.S_TOP - M.S_END)
    beta = math.degrees(math.atan((float(M.z_axis(S_CROWN)) - float(M.z_axis(sb))) / (sb - S_CROWN)))
    return sb, beta


def tip_of_angle(alpha):
    """発生区の上端からの見通し角が alpha (deg) になる沢筋の位置。"""
    lo, hi = S_CROWN + 1.0, M.L_S
    f = lambda s: (float(M.z_axis(S_CROWN)) - float(M.z_axis(s))) / (s - S_CROWN) - math.tan(math.radians(alpha))
    if f(hi) > 0:
        return float("nan")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
    return 0.5 * (lo + hi)


def angle_of_tip(s, n=0.0):
    r = M.S_A + math.hypot(s - M.S_A, max(abs(n) - M.N_A, 0.0)) if s > M.S_A else s
    return math.degrees(math.atan((float(M.z_axis(S_CROWN)) - float(M.z_axis(r))) / (s - S_CROWN)))


ALPHA_A, ALPHA_B, ALPHA_SD = 0.96, -1.4, 2.3     # Bakkehøi ら (1983): α = 0.96 β − 1.4°、標準偏差 2.3°


# ---------------------------------------------------------------- ケース
def param_of(name):
    return "param.txt" if name == M.BASE else f"param_{name}.txt"


def pval(txt, key):
    m = re.search(rf"^\s*{key}\s*=\s*'?([^'!\n]+?)'?\s*(!.*)?$", txt, re.M)
    return m.group(1).strip()


def have(name):
    if name not in M.CASES or not os.path.exists(param_of(name)):
        return False
    return os.path.exists(os.path.join(pval(open(param_of(name)).read(), "dir_result"), "D9999.bil"))


class Case:
    """1 ケースの入力と出力(配列は行 0 が南端。make_init.py の to_sn と同じ並び)。"""

    def __init__(self, name):
        self.name = name
        self.cfg = M.CASES[name]
        txt = open(param_of(name)).read()
        self.ddir, self.rdir = pval(txt, "dir_data"), pval(txt, "dir_result")
        self.mu, self.xi = float(pval(txt, "db_mu")), float(pval(txt, "db_xi"))
        self.dd, self.dt = float(pval(txt, "dd")), float(pval(txt, "dt"))
        nx, ny, _, _, dx, th = open(f"{self.ddir}/size.txt").read().split()
        self.nx, self.ny, self.dx, self.th = int(nx), int(ny), float(dx), float(th)
        self.s, self.n = M.to_sn(self.dx, self.th)
        self.mask = self.txt("mask") > 0
        self.d0, self.sd0 = self.txt("dbinit"), self.txt("sd")
        self.area = self.dx ** 2
        self.times = {}
        for line in open(f"{self.rdir}/FILENUMBER.csv"):
            if line.startswith("#"):
                continue
            f = line.split(",")
            if int(f[0]) < 9000:
                self.times[int(f[0])] = float(f[2])
        self.ks = sorted(self.times)
        self.kend = self.ks[-1]
        self.z0 = self.bil("Z", 0)
        self.zb = self.z0 - self.sd0                          # 連行されない面
        self.dz = np.where(self.mask, self.bil("Z", self.kend) - self.z0, 0.0)   # 雪面の変化(正が堆積)
        self.D = np.where(self.mask, self.bil("D", 9999), 0.0)                   # 最大流動深 h + hs
        self.V = np.where(self.D >= H_VEL, self.bil("V", 9999), 0.0)             # 最大流速(深い流れが通ったセル)
        self.fan = self.mask & (self.s > M.S_A)
        self.rel = self.d0 > 0.0
        self.track = self.mask & (self.s <= M.S_A) & ~self.rel
        self.dam = M.dam_height(self.s, self.n) if self.cfg["dam"] else np.zeros_like(self.z0)
        self._st = None

    def txt(self, name):
        return np.loadtxt(f"{self.ddir}/{name}.txt")[::-1]

    def bil(self, name, k):
        a = np.fromfile(f"{self.rdir}/{name}{k:04d}.bil", "<f4").reshape(self.ny, self.nx)
        return a[::-1].astype(float)

    def depth(self, k):
        """流れている雪の厚さ h + hs。"""
        return np.where(self.mask, self.bil("H", k) + self.bil("Hs", k), 0.0)

    def behind_dam(self):
        """誘導堤の線(終点の先は延長)より右岸側の扇状地(堤が守る側)。堤体のセルは除く。"""
        (s1, n1), (s2, n2) = M.DAM_A, M.DAM_B
        side = (s2 - s1) * (self.n - n1) - (n2 - n1) * (self.s - s1)
        return self.fan & (side < 0.0) & (M.dam_height(self.s, self.n) <= 0.0)

    def stats(self):
        if self._st is not None:
            return self._st
        t, vol, front = [], [], []
        zmin = self.z0.copy()
        for k in self.ks:
            d = self.depth(k)
            t.append(self.times[k])
            vol.append(d.sum() * self.area)
            m = d > H_THR
            front.append(self.s[m].max() if m.any() else 0.0)
            zmin = np.minimum(zmin, self.bil("Z", k))
        t, vol, front = np.array(t), np.array(vol), np.array(front)
        dep = (self.dz > H_THR) & self.fan
        st = dict(t=t, vol=vol, front=front)
        st["rel"] = self.d0.sum() * self.area
        st["snow"] = np.where(self.rel, 0.0, self.sd0).sum() * self.area         # 連行できる雪の量
        st["ent"] = np.where(self.track, self.z0 - zmin, 0.0).sum() * self.area  # 連行された雪(雪面の最大の低下)
        st["peak"] = vol.max()
        st["remain"] = vol[-1]
        st["tip"] = self.s[dep].max() if dep.any() else float("nan")
        st["tip_n"] = self.n[dep][np.argmax(self.s[dep])] if dep.any() else 0.0
        st["rtip"] = np.hypot(self.s[dep] - M.S_A, self.n[dep]).max() if dep.any() else float("nan")
        st["alpha"] = angle_of_tip(st["tip"], st["tip_n"]) if dep.any() else float("nan")
        st["area"] = dep.sum() * self.area
        st["depvol"] = np.where(self.fan, np.clip(self.dz, 0.0, None), 0.0).sum() * self.area
        st["depmax"] = np.where(self.fan, self.dz, 0.0).max()
        st["trackdep"] = np.where(self.mask & ~self.fan, np.clip(self.dz, 0.0, None), 0.0).sum() * self.area
        st["width"] = (self.n[dep].max() - self.n[dep].min()) if dep.any() else 0.0
        st["vmax"] = self.V.max()
        mouth = self.mask & (np.abs(self.s - M.S_A) <= self.dx)
        st["dmouth"] = self.D[mouth].max()
        st["vmouth"] = self.V[mouth].max()
        st["vfan"] = np.where(self.fan, self.V, 0.0).max()
        gully = self.mask & (self.s >= 500.0) & (self.s <= 900.0)                 # 沢の中(横断形が沢になった区間)
        st["vgully"] = self.V[gully].max()
        st["dgully"] = self.D[gully].max()
        over = front > M.S_A
        if over.any():
            i = int(np.argmax(over))
            st["tapex"] = t[i - 1] + (t[i] - t[i - 1]) * (M.S_A - front[i - 1]) / (front[i] - front[i - 1])
        else:
            st["tapex"] = float("nan")
        st["tstop"] = t[np.argmax(front >= front.max() - self.dx)]
        fa = np.maximum.accumulate(front)
        st["vfront"] = (np.interp(30.0, t, fa) - np.interp(20.0, t, fa)) / 10.0   # 先頭の速さ(発生から 20〜30 秒の平均)
        st["ledger"] = (self.depth(self.kend).sum() + self.dz.sum()) * self.area   # 流れている雪 + 雪面の変化 = 0
        self._st = st
        return st

    def at(self, pts):
        """点 (s, n) の最寄りのセルの添字。"""
        idx = []
        for sp, npt in pts:
            d2 = np.where(self.mask, (self.s - sp) ** 2 + (self.n - npt) ** 2, 1e30)
            idx.append(np.unravel_index(np.argmin(d2), d2.shape))
        return idx

    def houses(self):
        idx = self.at(M.houses())
        D = np.array([self.D[i] for i in idx])
        V = np.array([self.V[i] for i in idx])
        dep = np.array([self.dz[i] for i in idx])
        return dict(n=len(idx), hit=int((D >= H_HOUSE).sum()), buried=int((dep >= H_HOUSE).sum()),
                    dmax=D.max(), vmax=V.max(), D=D, V=V, dep=dep)


_cache = {}


def get(name):
    if name not in _cache:
        _cache[name] = Case(name)
    return _cache[name]


# ---------------------------------------------------------------- 描画の部品
def relief(ax, s, n, zb, mask=None, levels=20.0, alpha=1.0):
    """陰影と等高線の下絵。"""
    ls = LightSource(azdeg=315, altdeg=45)
    shade = ls.hillshade(zb, vert_exag=1.0, dx=abs(s[0, 1] - s[0, 0]) or 5.0, dy=abs(n[1, 0] - n[0, 0]) or 5.0)
    if mask is not None:
        shade = np.ma.masked_where(~mask, shade)
    ax.pcolormesh(s, n, shade, cmap="gray", vmin=-0.6, vmax=1.1, shading="nearest", rasterized=True, alpha=alpha)
    zz = np.ma.masked_where(~mask, zb) if mask is not None else zb
    ax.contour(s, n, zz, levels=np.arange(0.0, 800.0, levels), colors="k", linewidths=0.25, alpha=0.5)


XMAP = (0.0, 1500.0)            # 全体の地図の s の範囲(雪崩が届かない下流側は描かない)
YMAP = (-250.0, 250.0)


def base_map(ax, c, xlim=None, ylim=None):
    relief(ax, c.s, c.n, c.zb, c.mask)
    ax.set_aspect("equal")
    ax.set_xlim(xlim or XMAP)
    ax.set_ylim(ylim or YMAP)


def outline(ax, c, arr, level, **kw):
    ax.contour(c.s, c.n, np.where(c.mask, arr, 0.0), levels=[level], **kw)


def panel_label(ax, text, loc="upper left"):
    x, ha = (0.012, "left") if "left" in loc else (0.988, "right")
    y, va = (0.96, "top") if "upper" in loc else (0.04, "bottom")
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va, fontsize=9,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.5", lw=0.5, alpha=0.9))


def save(fig, name):
    path = os.path.join(FIGDIR, name)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("wrote", path)


# ---------------------------------------------------------------- 説明図(入力だけ)
def fig_setup():
    dx = 5.0
    s, n = M.to_sn(dx, 0.0)
    inside = (s >= 0) & (s < M.L_S) & (n >= -M.W / 2) & (n < M.W / 2)
    zb = M.ground(s, n)
    dam = M.dam_height(s, n)
    fig = plt.figure(figsize=(11.5, 9.8))
    gs = fig.add_gridspec(3, 3, height_ratios=[1.15, 1.0, 0.8], hspace=0.36, wspace=0.28,
                          left=0.065, right=0.985, top=0.965, bottom=0.055)
    # (a) 平面
    ax = fig.add_subplot(gs[0, :])
    relief(ax, s, n, zb + dam, inside, levels=20.0)
    ax.contourf(s, n, np.where(inside, M.release_shape(s, n), 0), levels=[0.5, 1.5], colors=["#c0392b"], alpha=0.6)
    band = M.track_snow(s, n, 1.0)
    ax.contourf(s, n, np.where(inside, band, 0), levels=[0.02, 0.5, 1.01], colors=["#9ecae1", "#3182bd"], alpha=0.8)
    ax.contourf(s, n, dam, levels=[0.5, 100], colors=["#8c5a2b"], alpha=0.95)
    H = M.houses()
    ax.plot(H[:, 0], H[:, 1], "s", ms=3, mfc="w", mec="k", mew=0.6)
    sb, beta = beta_point()
    ax.axvline(M.S_A, color="k", lw=0.8, ls=":")
    ax.text(M.S_A - 8, -M.W / 2 + 12, T("扇頂(沢の出口)", "fan apex (gully mouth)"), fontsize=8, va="bottom", ha="right")
    for x, txt in ((150, T("発生区", "starting zone")), (640, T("走路(沢)", "track (gully)")),
                   (1520, T("堆積区(扇状地)", "runout zone (fan)"))):
        ax.text(x, M.W / 2 - 22, txt, ha="center", va="top", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.5", lw=0.5, alpha=0.9))
    kw = dict(fontsize=8, ha="center", arrowprops=dict(arrowstyle="-", lw=0.6),
              bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
    ax.annotate(T("破断深 1 m、1.7 万 m³", "1 m slab, 17,000 m³"), (150, -68), (150, -175), **kw)
    ax.annotate(T("走路の雪の帯(幅 40 m)", "track snow band (40 m wide)"), (700, -14), (700, -140), **kw)
    ax.annotate(T("誘導堤(高さ 18 → 10 m)", "deflecting dam (18 → 10 m high)"), (1150, 45), (1230, 190), **kw)
    ax.annotate(T("家屋(32 戸)", "houses (32)"), (1205, -112), (1330, -215), **kw)
    for sx, lab in ((150, "A"), (600, "B"), (1100, "C")):
        ax.plot([sx, sx], [-M.W / 2 + 60, M.W / 2 - 75], color="#333", lw=0.7, ls="--")
        ax.text(sx, -M.W / 2 + 52, f"{lab}–{lab}'", ha="center", va="top", fontsize=8, color="#333")
    ax.set_aspect("equal")
    ax.set_xlim(0, M.L_S)
    ax.set_ylim(-M.W / 2, M.W / 2)
    ax.set_xlabel(T("沢筋に沿う水平距離 s (m)", "horizontal distance along the gully axis s (m)"))
    ax.set_ylabel("n (m)")
    ax.set_title(T("(a) 地形(等高線 20 m)と、発生区・走路の雪・誘導堤・家屋", "(a) terrain (20 m contours), starting zone, track snow, deflecting dam and houses"),
                 fontsize=9.5, loc="left")
    # (b) 縦断
    ax = fig.add_subplot(gs[1, :2])
    xs = np.linspace(0, M.L_S, 721)
    za = M.z_axis(xs)
    ax.fill_between(xs, za, za.min() - 30, color="#d9d2c5")
    ax.plot(xs, za, "k", lw=1.2)
    m = (xs >= S_CROWN) & (xs <= M.S_C + M.A_S)
    ax.plot(xs[m], za[m] + 7, color="#c0392b", lw=4, solid_capstyle="butt")
    m = (xs >= M.S_E0) & (xs <= M.S_A)
    ax.plot(xs[m], za[m] + 7, color="#3182bd", lw=4, solid_capstyle="butt")
    for sx in (150, 400, 650, 900, 1050, 1500):
        ang = math.degrees(math.atan(float(M.slope_axis(sx))))
        ax.text(sx + 12, float(M.z_axis(sx)) + 30, f"{ang:.0f}°", ha="center", fontsize=8)
    ax.axvline(M.S_A, color="k", lw=0.8, ls=":")
    ax.text(M.S_A + 8, za.max() + 5, T("扇頂", "fan apex"), fontsize=8)
    zc = float(M.z_axis(S_CROWN))
    ax.plot([S_CROWN, sb], [zc, float(M.z_axis(sb))], color="#555", lw=0.8, ls="--")
    ax.plot(sb, float(M.z_axis(sb)), "o", ms=5, mfc="w", mec="k", zorder=5)
    ax.annotate(T(f"β 点(勾配 10°)\nβ = {beta:.1f}°", f"β point (10° slope)\nβ = {beta:.1f}°"),
                (sb, float(M.z_axis(sb))), (sb - 40, float(M.z_axis(sb)) + 190), fontsize=8, ha="center",
                arrowprops=dict(arrowstyle="-", lw=0.6))
    a0 = ALPHA_A * beta + ALPHA_B
    s0, s1, s2 = tip_of_angle(a0), tip_of_angle(a0 + ALPHA_SD), tip_of_angle(a0 - ALPHA_SD)
    ax.plot([S_CROWN, s0], [zc, float(M.z_axis(s0))], color="#2b8a3e", lw=0.9)
    ax.plot([s1, s2], [float(M.z_axis(s1)), float(M.z_axis(s2))], color="#2b8a3e", lw=5, alpha=0.45, solid_capstyle="butt")
    ax.plot(s0, float(M.z_axis(s0)), "o", ms=5, color="#2b8a3e", zorder=5)
    ax.annotate(T(f"α–β の式の先端\nα = {a0:.1f}° ± {ALPHA_SD}°", f"tip by the α–β relation\nα = {a0:.1f}° ± {ALPHA_SD}°"),
                (s0, float(M.z_axis(s0))), (s0 + 60, float(M.z_axis(s0)) + 260), fontsize=8, ha="center", color="#2b8a3e",
                arrowprops=dict(arrowstyle="-", lw=0.6, color="#2b8a3e"))
    s18 = tip_of_angle(18.0)
    ax.plot(s18, float(M.z_axis(s18)), "v", ms=6, color="#7b2d8e")
    ax.annotate(T("見通し角 18°", "18° sight angle"), (s18, float(M.z_axis(s18))), (s18 - 30, float(M.z_axis(s18)) + 110),
                fontsize=8, ha="center", color="#7b2d8e", arrowprops=dict(arrowstyle="-", lw=0.6, color="#7b2d8e"))
    ax.set_xlim(0, M.L_S)
    ax.set_ylim(za.min() - 30, za.max() + 40)
    ax.set_xlabel("s (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.legend(handles=[Line2D([], [], color="#c0392b", lw=4, label=T("発生区", "starting zone")),
                       Line2D([], [], color="#3182bd", lw=4, label=T("走路の雪の帯", "track snow band"))],
              loc="upper right", fontsize=8, frameon=False)
    ax.set_title(T("(b) 沢筋の縦断(数字は勾配)と、到達距離の経験則", "(b) profile along the axis (numbers: slope angle) and empirical runout rules"),
                 fontsize=9.5, loc="left")
    # (c) 格子に対する沢の向き
    ax = fig.add_subplot(gs[1, 2])
    for th, col in ((0.0, "#1f5f8b"), (22.5, "#d08c00"), (45.0, "#2b8a3e")):
        c, sn = M.frame(dx, th)[4:]
        Pp = [(0, -M.W / 2), (M.L_S, -M.W / 2), (M.L_S, M.W / 2), (0, M.W / 2), (0, -M.W / 2)]
        X = [sp * c + npt * sn for sp, npt in Pp]
        Y = [-sp * sn + npt * c for sp, npt in Pp]
        ax.plot(X, Y, color=col, lw=1.2, label=f"{th:g}°")
        ax.plot([0, M.L_S * c], [0, -M.L_S * sn], color=col, lw=0.7, ls="--")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.legend(title=T("沢の向き", "gully direction"), fontsize=8, title_fontsize=8, frameon=False, loc="lower left")
    ax.set_title(T("(c) 格子に対する沢の向き", "(c) gully direction on the grid"), fontsize=9.5, loc="left")
    # (d)〜(f) 横断
    for k, (sx, lab, ttl, xl) in enumerate(((150.0, "A", T("ボウル(発生区)", "bowl (starting zone)"), 200.0),
                                            (600.0, "B", T("沢底と走路の雪", "gully floor and track snow"), 45.0),
                                            (1100.0, "C", T("扇状地と誘導堤", "fan and deflecting dam"), 200.0))):
        ax = fig.add_subplot(gs[2, k])
        nn = np.linspace(-xl, xl, 801)
        ss = np.full_like(nn, sx)
        zg = M.ground(ss, nn)
        zref = zg.min()
        ax.fill_between(nn, zg - zref, -5, color="#d9d2c5")
        ax.plot(nn, zg - zref, "k", lw=1.0)
        if lab == "A":
            d = M.release_shape(ss, nn)
            ax.fill_between(nn, zg - zref, zg - zref + d * 1.0, color="#c0392b", alpha=0.75, lw=0)
            ax.set_ylim(-1, 34)
        elif lab == "B":
            for thick, col in ((2.0, "#9ecae1"), (1.0, "#3182bd")):
                ax.fill_between(nn, zg - zref, zg - zref + M.track_snow(ss, nn, thick), color=col, lw=0)
            ax.legend(handles=[Patch(color="#3182bd", label=T("基本(沢筋で 1 m)", "base (1 m on the axis)")),
                               Patch(color="#9ecae1", label=T("沢筋で 2 m", "2 m on the axis"))],
                      fontsize=7.5, frameon=False, loc="upper center")
            ax.set_ylim(-0.5, 17)
        else:
            dm = M.dam_height(ss, nn)
            ax.fill_between(nn, zg - zref, zg - zref + dm, color="#8c5a2b", lw=0)
            ax.set_ylim(-1, 40)
        ax.set_xlim(-xl, xl)
        ax.set_xlabel("n (m)")
        if k == 0:
            ax.set_ylabel(T("最も低い点からの高さ (m)", "height above the lowest point (m)"))
        ax.set_title(f"({'def'[k]}) {lab}–{lab}' (s = {sx:.0f} m): {ttl}", fontsize=9.5, loc="left")
    save(fig, "setup.png")


def fig_mechanism():
    txt = open("param.txt").read()
    mu, xi, de, lam = (float(pval(txt, k)) for k in ("db_mu", "db_xi", "db_delte", "fluv_porosity"))
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 3.9), gridspec_kw=dict(left=0.03, right=0.985, top=0.9, bottom=0.14, wspace=0.24,
                                                                         width_ratios=[1.25, 1, 1]))
    # (a) 読み替え
    ax = axs[0]
    x = np.linspace(0, 10, 501)
    zg = 3.4 * np.exp(-x / 3.2) + 0.35
    ax.fill_between(x, zg, 0, color="#d9d2c5")
    ax.plot(x, zg, "k", lw=1.0)
    slab = np.where((x > 0.25) & (x < 1.5), 0.42, 0.0)
    ax.plot(x[slab > 0], (zg + slab)[slab > 0], color="#c0392b", lw=1.0, ls="--")
    ax.plot([0.25, 0.25], [np.interp(0.25, x, zg), np.interp(0.25, x, zg) + 0.42], color="#c0392b", lw=1.0, ls="--")
    ax.plot([1.5, 1.5], [np.interp(1.5, x, zg), np.interp(1.5, x, zg) + 0.42], color="#c0392b", lw=1.0, ls="--")
    snow = np.where((x > 4.75) & (x < 7.3), 0.3, 0.0)
    ax.fill_between(x, zg, zg + snow, color="#9ecae1", lw=0)
    flow = 1.15 * np.exp(-((x - 4.0) / 0.55) ** 2) * (x < 4.8)
    ax.fill_between(x, zg, zg + flow * (1 - 2.5 * lam), color="#3182bd", lw=0)
    ax.fill_between(x, zg + flow * (1 - 2.5 * lam), zg + flow, color="#c6dbef", lw=0)
    dep = 0.45 * np.clip(1 - ((x - 8.9) / 0.9) ** 2, 0, None)
    ax.fill_between(x, zg, zg + dep, color="#6baed6", lw=0)
    ax.annotate("", (5.5, np.interp(5.5, x, zg) + 1.25), (4.2, np.interp(4.2, x, zg) + 1.75), arrowprops=dict(arrowstyle="-|>", lw=1.2, color="k"))
    kw = dict(fontsize=8, ha="center", arrowprops=dict(arrowstyle="-", lw=0.6))
    ax.annotate(T("発生区の破断深 D\n(fn_dbinit)", "slab depth D in the\nstarting zone (fn_dbinit)"), (0.9, np.interp(0.9, x, zg) + 0.42), (1.6, 4.35), color="#c0392b", **kw)
    ax.annotate(T("流れている雪 h + hs\n(固体 hs とキャリア h)", "flowing snow h + hs\n(solids hs and carrier h)"), (4.0, np.interp(4.0, x, zg) + 1.1), (4.6, 3.55), **kw)
    ax.annotate(T("連行できる雪 sd\n(土層厚)", "erodible snow sd\n(soil depth)"), (6.4, np.interp(6.4, x, zg) + 0.3), (7.0, 2.45), **kw)
    ax.annotate(T("止まった雪\n(雪面 z に固定)", "stopped snow\n(fixed to the surface z)"), (8.9, np.interp(8.9, x, zg) + 0.45), (8.7, 1.75), **kw)
    ax.text(3.3, 0.38, T("連行されない面 z − sd(地山・古い積雪)", "surface that is not eroded, z − sd (ground, old snow)"), fontsize=8, ha="center")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.9)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(T("(a) 土砂の入れ物を雪として読む", "(a) reading the sediment containers as snow"), fontsize=9.5, loc="left")
    # (b) Voellmy 則の等流の速さ
    ax = axs[1]
    th = np.radians(np.linspace(0, 40, 401))
    for h, col in ((1.0, "#9ecae1"), (3.0, "#3182bd"), (6.0, "#08306b")):
        v2 = xi * h * np.cos(th) * (np.sin(th) - mu * np.cos(th))
        ax.plot(np.degrees(th), np.sqrt(np.clip(v2, 0, None)), color=col, lw=1.6, label=T(f"厚さ {h:g} m", f"depth {h:g} m"))
    th0 = math.degrees(math.atan(mu))
    ax.axvline(th0, color="k", lw=0.8, ls=":")
    ax.text(th0 - 0.5, 40, T(f"勾配が μ = {mu:g}\n({th0:.0f}°)より\n緩いと止まる", f"stops where the\nslope is below\nμ = {mu:g} ({th0:.0f}°)"), fontsize=8, va="center", ha="right")
    for a0, a1, lab, col in ((3, 16, T("扇状地", "fan"), "#bdbdbd"), (16, 33, T("沢", "gully"), "#969696"), (34, 37, T("発生区", "start"), "#636363")):
        ax.axvspan(a0, a1, ymin=0, ymax=0.045, color=col)
        ax.text((a0 + a1) / 2, 4.2, lab, ha="center", fontsize=7.5)
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 70)
    ax.set_xlabel(T("斜面の傾き (°)", "slope angle (°)"))
    ax.set_ylabel(T("等流の速さ (m/s。斜面に沿う)", "steady speed (m/s, along the slope)"))
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    ax.set_title(T(f"(b) Voellmy 則(μ = {mu:g}、ξ = {xi:g} m/s²)", f"(b) Voellmy law (μ = {mu:g}, ξ = {xi:g} m/s²)"), fontsize=9.5, loc="left")
    # (c) 連行の速さ(質量で)
    ax = axs[2]
    v = np.linspace(0, 50, 200)
    for rho, col in ((100.0, "#fcae91"), (200.0, "#fb6a4a"), (300.0, "#a50f15")):
        ax.plot(v, rho * de * v, color=col, lw=1.6, label=T(f"雪の密度 {rho:g} kg/m³", f"snow density {rho:g} kg/m³"))
    ax.axhline(350.0, color="k", lw=0.8, ls="--")
    ax.text(1, 362, T("観測された先頭の取り込みの上限 350", "observed upper bound of frontal ploughing, 350"), fontsize=7.5)
    ax.axhline(10.0, color="k", lw=0.8, ls=":")
    ax.text(49, 22, T("底面の侵食の上限 10", "upper bound of basal erosion, 10"), fontsize=7.5, ha="right")
    ax.set_xlim(0, 50)
    ax.set_ylim(0, 800)
    ax.set_xlabel(T("流れの速さ |V| (m/s)", "flow speed |V| (m/s)"))
    ax.set_ylabel(T("取り込む速さ ρs δe |V| (kg m⁻² s⁻¹)", "entrainment rate ρs δe |V| (kg m⁻² s⁻¹)"))
    ax.legend(fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(0.0, 0.93))
    ax.set_title(T(f"(c) 連行 E = δe |V|(δe = {de:g})", f"(c) entrainment E = δe |V| (δe = {de:g})"), fontsize=9.5, loc="left")
    save(fig, "mechanism.png")


# ---------------------------------------------------------------- 結果の図
def depth_map(ax, c, d, vmax=6.0, thr=0.05):
    return ax.pcolormesh(c.s, c.n, np.ma.masked_where(d < thr, d), cmap=DEPTH_CMAP, vmin=0.0, vmax=vmax,
                         shading="nearest", rasterized=True)


def dz_map(ax, c, vmax=2.0):
    return ax.pcolormesh(c.s, c.n, np.ma.masked_where(np.abs(c.dz) < 0.02, c.dz), cmap=DZ_CMAP, vmin=-vmax, vmax=vmax,
                         shading="nearest", rasterized=True)


def fig_flow():
    c = get("base")
    fig, axs = plt.subplots(4, 2, figsize=(11.5, 8.6), gridspec_kw=dict(left=0.055, right=0.93, top=0.985, bottom=0.055, hspace=0.07, wspace=0.05))
    times = (10, 20, 30, 40, 50, 70)
    for ax, tt in zip(axs.ravel()[:6], times):
        k = min(c.ks, key=lambda q: abs(c.times[q] - tt))
        base_map(ax, c)
        im = depth_map(ax, c, c.depth(k))
        panel_label(ax, f"t = {c.times[k]:.0f} s")
    ax = axs[3, 0]
    base_map(ax, c)
    depth_map(ax, c, c.D)
    panel_label(ax, T("最大流動深", "maximum flow depth"))
    ax = axs[3, 1]
    base_map(ax, c)
    im2 = dz_map(ax, c)
    panel_label(ax, T(f"雪面の変化(t = {c.times[c.kend]:.0f} s)", f"change of the snow surface (t = {c.times[c.kend]:.0f} s)"))
    for ax in axs[:, 1]:
        ax.set_yticklabels([])
    for ax in axs[:3].ravel():
        ax.set_xticklabels([])
    for ax in axs[3]:
        ax.set_xlabel("s (m)")
    for ax in axs[:, 0]:
        ax.set_ylabel("n (m)")
    cb = fig.colorbar(im, cax=fig.add_axes([0.94, 0.33, 0.012, 0.62]), extend="max")
    cb.set_label(T("流れている雪の厚さ h + hs (m)", "depth of flowing snow h + hs (m)"))
    cb = fig.colorbar(im2, cax=fig.add_axes([0.94, 0.065, 0.012, 0.2]), extend="both")
    cb.set_label(T("堆積(+)・連行(−) (m)", "deposit (+), erosion (−) (m)"))
    save(fig, "flow.png")


def fig_entrain():
    names = ("nosnow", "base", "deep")
    cs = [get(nm) for nm in names]
    fig = plt.figure(figsize=(11.5, 7.6))
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 1, 1.75], left=0.06, right=0.93, top=0.955, bottom=0.075, hspace=0.3, wspace=0.05)
    for j, c in enumerate(cs):
        ax = fig.add_subplot(gs[0, j])
        base_map(ax, c)
        im = depth_map(ax, c, c.D)
        ax.set_title(label(c.name), fontsize=9.5, color=COL[c.name])
        ax.set_xticklabels([])
        if j:
            ax.set_yticklabels([])
        else:
            ax.set_ylabel("n (m)")
            panel_label(ax, T("最大流動深", "maximum flow depth"), "lower left")
        ax = fig.add_subplot(gs[1, j])
        base_map(ax, c)
        im2 = dz_map(ax, c)
        ax.set_xlabel("s (m)")
        if j:
            ax.set_yticklabels([])
        else:
            ax.set_ylabel("n (m)")
            panel_label(ax, T("雪面の変化", "change of the snow surface"), "lower left")
    cb = fig.colorbar(im, cax=fig.add_axes([0.94, 0.77, 0.012, 0.18]), extend="max")
    cb.set_label(T("最大流動深 (m)", "max. depth (m)"))
    cb = fig.colorbar(im2, cax=fig.add_axes([0.94, 0.535, 0.012, 0.18]), extend="both")
    cb.set_label(T("堆積(+)・連行(−) (m)", "deposit (+), erosion (−) (m)"))
    sub = gs[2, :].subgridspec(1, 3, wspace=0.3)
    ax = fig.add_subplot(sub[0])
    for c in cs:
        st = c.stats()
        ax.plot(st["t"], st["vol"] / 1e3, color=COL[c.name], lw=1.6, label=label(c.name))
    ax.set_xlabel(T("時間 (s)", "time (s)"))
    ax.set_ylabel(T("流れている雪の量 (千 m³)", "volume of flowing snow (10³ m³)"))
    ax.set_xlim(0, 180)
    ax.set_ylim(0, None)
    ax.legend(fontsize=8, frameon=False)
    ax.set_title(T("(a) 流れている雪の量", "(a) volume of flowing snow"), fontsize=9.5, loc="left")
    ax = fig.add_subplot(sub[1])
    for c in cs:
        st = c.stats()
        ax.plot(st["t"], np.maximum.accumulate(st["front"]), color=COL[c.name], lw=1.6)
    ax.axhline(M.S_A, color="k", lw=0.7, ls=":")
    ax.text(118, M.S_A + 12, T("扇頂", "fan apex"), fontsize=8)
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 1400)
    ax.set_xlabel(T("時間 (s)", "time (s)"))
    ax.set_ylabel(T("先頭の位置 s (m)", "front position s (m)"))
    ax.set_title(T("(b) 先頭の位置(最遠)", "(b) front position (farthest)"), fontsize=9.5, loc="left")
    ax = fig.add_subplot(sub[2])
    for c in cs:
        sv, vv, dv = along_axis(c)
        ax.plot(sv, vv, color=COL[c.name], lw=1.6)
        ax.plot(sv, dv, color=COL[c.name], lw=1.0, ls="--")
    ax.axvline(M.S_A, color="k", lw=0.7, ls=":")
    ax.set_xlim(0, 1400)
    ax.set_ylim(0, None)
    ax.set_xlabel("s (m)")
    ax.set_ylabel(T("最大流速 (m/s)・最大流動深 (m)", "maximum speed (m/s), maximum depth (m)"))
    ax.legend(handles=[Line2D([], [], color="k", lw=1.6, label=T("最大流速", "maximum speed")),
                       Line2D([], [], color="k", lw=1.0, ls="--", label=T("最大流動深", "maximum depth"))], fontsize=8, frameon=False)
    ax.set_title(T("(c) 横断の最大値の縦断", "(c) cross-sectional maxima along the path"), fontsize=9.5, loc="left")
    save(fig, "entrain.png")


def along_axis(c, ds=10.0):
    """s の区間ごとの、横断の最大流速と最大流動深。"""
    edges = np.arange(0.0, M.L_S + ds, ds)
    idx = np.digitize(c.s, edges) - 1
    sv, vv, dv = [], [], []
    for i in range(len(edges) - 1):
        m = c.mask & (idx == i)
        if m.any():
            sv.append(0.5 * (edges[i] + edges[i + 1]))
            vv.append(c.V[m].max())
            dv.append(c.D[m].max())
    return np.array(sv), np.array(vv), np.array(dv)


def fig_runout():
    names = [nm for nm in ("nosnow", "base", "deep", "mu155", "mu340") if have(nm)]
    sb, beta = beta_point()
    a0 = ALPHA_A * beta + ALPHA_B
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.3), gridspec_kw=dict(width_ratios=[1.75, 1], left=0.06, right=0.985, top=0.93, bottom=0.13, wspace=0.2))
    ax = axs[0]
    xs = np.linspace(850, 1800, 400)
    za = M.z_axis(xs)
    ax.fill_between(xs, za, 0, color="#d9d2c5")
    ax.plot(xs, za, "k", lw=1.2)
    s1, s2 = tip_of_angle(a0 + ALPHA_SD), tip_of_angle(a0 - ALPHA_SD)
    ax.axvspan(s1, s2, color="#2b8a3e", alpha=0.15, lw=0)
    ax.axvline(tip_of_angle(a0), color="#2b8a3e", lw=1.0)
    ax.text(s2 - 6, 137, T(f"α–β の式\nα = {a0:.1f}° ± {ALPHA_SD}°", f"α–β relation\nα = {a0:.1f}° ± {ALPHA_SD}°"), fontsize=8, color="#2b8a3e", va="top", ha="right")
    ax.plot(sb, float(M.z_axis(sb)), "o", ms=5, mfc="w", mec="k")
    ax.text(sb, float(M.z_axis(sb)) + 7, T("β 点", "β point"), ha="center", fontsize=8)
    s18 = tip_of_angle(18.0)
    ax.plot(s18, float(M.z_axis(s18)), "v", ms=6, color="#7b2d8e")
    ax.text(s18, float(M.z_axis(s18)) + 7, T("見通し角 18°", "18° sight angle"), ha="center", fontsize=8, color="#7b2d8e")
    ax.axvline(M.S_A, color="k", lw=0.7, ls=":")
    ax.text(M.S_A + 4, 4, T("扇頂", "fan apex"), fontsize=8)
    order = sorted(names, key=lambda nm: -get(nm).stats()["tip"])
    for i, nm in enumerate(order):
        st = get(nm).stats()
        zt = float(M.z_axis(st["tip"]))
        yl = 52.0 + 13.0 * i
        ax.plot([st["tip"]] * 2, [zt, yl], color=COL[nm], lw=1.0)
        ax.plot(st["tip"], zt, "o", ms=5, color=COL[nm], zorder=5)
        ax.text(st["tip"] + 6, yl, f"{label(nm)}: {st['tip']:.0f} m", fontsize=8, color=COL[nm], va="center",
                bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.75))
    ax.set_xlim(850, 1800)
    ax.set_ylim(0, 140)
    ax.set_xlabel("s (m)")
    ax.set_ylabel(T("標高 (m)", "elevation (m)"))
    ax.set_title(T("(a) 堆積の先端(厚さ 0.1 m 以上)の位置", "(a) position of the deposit tip (thickness ≥ 0.1 m)"), fontsize=9.5, loc="left")
    ax = axs[1]
    ax.axhspan(a0 - ALPHA_SD, a0 + ALPHA_SD, color="#2b8a3e", alpha=0.15, lw=0)
    ax.axhline(a0, color="#2b8a3e", lw=1.0)
    ax.axhline(beta, color="k", lw=0.7, ls="--")
    ax.text(len(names) - 0.55, beta + 0.06, "β", fontsize=8, ha="right")
    ax.axhline(18.0, color="#7b2d8e", lw=0.8, ls=":")
    ax.text(len(names) - 0.55, 18.08, T("見通し角 18°", "18° sight angle"), fontsize=8, ha="right", color="#7b2d8e")
    ax.text(-0.5, a0 + 0.08, T("α–β の式", "α–β relation"), fontsize=8, color="#2b8a3e")
    for i, nm in enumerate(names):
        st = get(nm).stats()
        ax.plot(i, st["alpha"], "o", ms=7, color=COL[nm])
        ax.text(i, st["alpha"] + 0.22, f"{st['alpha']:.1f}°", ha="center", fontsize=8, color=COL[nm])
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([{"nosnow": T("雪なし", "no snow"), "base": T("基本", "base"), "deep": T("雪 2 m", "2 m snow"),
                         "mu155": "μ 0.155\nξ 3000", "mu340": "μ 0.34\nξ 1350"}[nm] for nm in names], fontsize=8)
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.set_ylim(17, 27)
    ax.set_ylabel(T("見通し角 α (°)", "sight angle α (°)"))
    ax.set_title(T("(b) 見通し角(小さいほど遠くへ届く)", "(b) sight angle (smaller = longer runout)"), fontsize=9.5, loc="left")
    save(fig, "runout.png")


def fig_dam():
    names = ("base", "dam", "deep", "deep_dam")
    cs = [get(nm) for nm in names]
    xlim, ylim = (880.0, 1420.0), (-240.0, 300.0)
    fig, axs = plt.subplots(2, 4, figsize=(11.5, 6.2), gridspec_kw=dict(left=0.05, right=0.93, top=0.95, bottom=0.07, hspace=0.08, wspace=0.05))
    H = M.houses()
    for j, c in enumerate(cs):
        hs = c.houses()
        for i in (0, 1):
            ax = axs[i, j]
            relief(ax, c.s, c.n, c.zb, c.mask, levels=10.0)
            if i == 0:
                im = depth_map(ax, c, c.D, vmax=6.0)
                hit = hs["D"] >= H_HOUSE
            else:
                im2 = ax.pcolormesh(c.s, c.n, np.ma.masked_where(c.dz < 0.05, c.dz), cmap=DEPTH_CMAP, vmin=0, vmax=4.0,
                                    shading="nearest", rasterized=True)
                hit = hs["dep"] >= H_HOUSE
            if c.cfg["dam"]:
                ax.contour(c.s, c.n, c.dam, levels=[0.5], colors=["#8c5a2b"], linewidths=1.0)
            ax.plot(H[~hit, 0], H[~hit, 1], "s", ms=3, mfc="w", mec="k", mew=0.5)
            ax.plot(H[hit, 0], H[hit, 1], "s", ms=3, mfc="#c0392b", mec="k", mew=0.5)
            ax.set_aspect("equal")
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            if j:
                ax.set_yticklabels([])
            else:
                ax.set_ylabel("n (m)")
            if i == 0:
                ax.set_xticklabels([])
                ax.set_title(label(c.name), fontsize=9.5)
            else:
                ax.set_xlabel("s (m)")
    panel_label(axs[0, 0], T("最大流動深", "maximum flow depth"), "lower left")
    panel_label(axs[1, 0], T("堆積の厚さ", "deposit thickness"), "lower left")
    cb = fig.colorbar(im, cax=fig.add_axes([0.94, 0.54, 0.012, 0.38]), extend="max")
    cb.set_label(T("最大流動深 (m)", "maximum flow depth (m)"))
    cb = fig.colorbar(im2, cax=fig.add_axes([0.94, 0.09, 0.012, 0.38]), extend="max")
    cb.set_label(T("堆積の厚さ (m)", "deposit thickness (m)"))
    save(fig, "dam.png")


def fig_grid():
    sets = ((T("(a) 格子間隔(沢の向き 0°)", "(a) grid spacing (gully direction 0°)"),
             [("dx10", "10 m", "#d08c00"), ("base", "5 m", "#1f5f8b"), ("dx2p5", "2.5 m", "#2b8a3e")]),
            (T("(b) 沢の向き(格子 5 m)", "(b) gully direction (5 m grid)"),
             [("base", "0°", "#1f5f8b"), ("r22p5", "22.5°", "#d08c00"), ("r45", "45°", "#2b8a3e")]),
            (T("(c) 時間刻み(格子 5 m)", "(c) time step (5 m grid)"),
             [("dt2", "0.05 s", "#d08c00"), ("base", "0.025 s", "#1f5f8b"), ("dthalf", "0.0125 s", "#2b8a3e")]))
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 4.5), gridspec_kw=dict(left=0.055, right=0.99, top=0.92, bottom=0.12, wspace=0.08))
    cb = get("base")
    for ax, (ttl, items) in zip(axs, sets):
        relief(ax, cb.s, cb.n, cb.zb, cb.mask, levels=10.0, alpha=0.6)
        hand = []
        for nm, lab, col in items:
            if not have(nm):
                continue
            c = get(nm)
            outline(ax, c, c.dz, 0.5, colors=[col], linewidths=1.3)
            outline(ax, c, c.D, 0.5, colors=[col], linewidths=0.9, linestyles="--")
            hand.append(Line2D([], [], color=col, lw=1.3, label=lab))
        hand += [Line2D([], [], color="k", lw=1.3, label=T("堆積 0.5 m", "deposit 0.5 m")),
                 Line2D([], [], color="k", lw=0.9, ls="--", label=T("最大流動深 0.5 m", "max. depth 0.5 m"))]
        ax.legend(handles=hand, fontsize=7.5, frameon=True, loc="lower left", ncol=2)
        ax.set_aspect("equal")
        ax.set_xlim(880, 1380)
        ax.set_ylim(-250, 250)
        ax.set_xlabel("s (m)")
        ax.set_title(ttl, fontsize=9.5, loc="left")
    axs[0].set_ylabel("n (m)")
    for ax in axs[1:]:
        ax.set_yticklabels([])
    save(fig, "grid.png")


def fig_limits():
    fig = plt.figure(figsize=(11.5, 8.8))
    gsl = fig.add_gridspec(3, 1, left=0.055, right=0.6, top=0.955, bottom=0.065, hspace=0.1)
    gs = fig.add_gridspec(3, 1, left=0.68, right=0.985, top=0.955, bottom=0.065, hspace=0.5)
    rows = (("allsnow_dd3", "1 mm"), ("allsnow", "0.1 mm"), ("allsnow_dd5", "0.01 mm"))
    for i, (nm, lab) in enumerate(rows):
        ax = fig.add_subplot(gsl[i, 0])
        if have(nm):
            c = get(nm)
            base_map(ax, c, ylim=(-M.W / 2, M.W / 2))
            depth_map(ax, c, c.D)
            st = c.stats()
            panel_label(ax, T(f"限界水深 {lab}: 流れた雪は発生の {st['peak'] / st['rel']:.1f} 倍",
                              f"threshold depth {lab}: flowing volume {st['peak'] / st['rel']:.1f} × the release"), "lower left")
        ax.set_ylabel("n (m)")
        if i < 2:
            ax.set_xticklabels([])
        else:
            ax.set_xlabel("s (m)")
        if i == 0:
            ax.set_title(T("(a) 扇頂より上の全面に雪 0.5 m を置いた計算の最大流動深", "(a) maximum flow depth with 0.5 m of snow everywhere above the apex"), fontsize=9.5, loc="left")
    # (b) 限界水深と流れた雪の量
    ax = fig.add_subplot(gs[0, 0])
    dds = (1e-3, 1e-4, 1e-5)
    for nms, col, lab in ((("dd3", "base", "dd5"), "#1f5f8b", T("走路の雪の帯(基本)", "track snow band (base)")),
                          (("allsnow_dd3", "allsnow", "allsnow_dd5"), "#c0392b", T("全面に雪 0.5 m", "0.5 m of snow everywhere"))):
        xy = [(d, get(nm).stats()["peak"] / get(nm).stats()["rel"]) for d, nm in zip(dds, nms) if have(nm)]
        if xy:
            ax.plot(*zip(*xy), "o-", color=col, lw=1.4, label=lab)
    ax.set_xscale("log")
    ax.set_xlim(3e-3, 3e-6)
    ax.set_ylim(0, None)
    ax.set_xlabel(T("限界水深 dd (m)", "threshold depth dd (m)"))
    ax.set_ylabel(T("流れた雪の最大量 / 発生量", "peak flowing volume / release"))
    ax.legend(fontsize=8, frameon=False)
    ax.set_title(T("(b) 限界水深と雪崩の大きさ", "(b) threshold depth and avalanche size"), fontsize=9.5, loc="left")
    # (c) 時間刻みへの依存(限界水深 1 mm と 0.1 mm)
    ax = fig.add_subplot(gs[1, 0])
    for nms, col, lab in ((("dd3", "dd3_dthalf"), "#d08c00", "dd = 1 mm"), (("dt2", "base", "dthalf"), "#1f5f8b", "dd = 0.1 mm")):
        xy = [(get(nm).dt, get(nm).stats()["area"] / 1e4) for nm in nms if have(nm)]
        if xy:
            ax.plot(*zip(*sorted(xy)), "o-", color=col, lw=1.4, label=lab)
    ax.set_xscale("log")
    ax.set_xticks([0.0125, 0.025, 0.05])
    ax.set_xticklabels(["0.0125", "0.025", "0.05"])
    ax.minorticks_off()
    ax.set_ylim(0, None)
    ax.set_xlabel(T("時間刻み (s)", "time step (s)"))
    ax.set_ylabel(T("扇状地の堆積の面積 (ha)", "deposit area on the fan (ha)"))
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.set_title(T("(c) 時間刻みと堆積の面積(走路の雪の帯)", "(c) time step and deposit area (track snow band)"), fontsize=9.5, loc="left")
    # (d) 連行が流れを減速しないこと(一様な斜面の一斉発生の常微分方程式)
    ax = fig.add_subplot(gs[2, 0])
    txt = open("param.txt").read()
    mu, xi = float(pval(txt, "db_mu")), float(pval(txt, "db_xi"))
    for de, col in ((0.0, "#7a7a7a"), (0.02, "#1f5f8b")):
        for inertia, ls in ((False, "-"), (True, "--")):
            if de == 0.0 and inertia:
                continue
            tt, uu, _ = sheet_ode(0.5, mu, xi, de, inertia)
            ax.plot(tt, uu, color=col, lw=1.4, ls=ls)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, None)
    ax.set_xlabel(T("時間 (s)", "time (s)"))
    ax.set_ylabel(T("水平の流速 (m/s)", "horizontal speed (m/s)"))
    ax.legend(handles=[Line2D([], [], color="#7a7a7a", lw=1.4, label=T("連行なし", "no entrainment")),
                       Line2D([], [], color="#1f5f8b", lw=1.4, label=T("連行あり(ENCflow の扱い)", "with entrainment (as in ENCflow)")),
                       Line2D([], [], color="#1f5f8b", lw=1.4, ls="--", label=T("連行あり(運動量を保存する扱い)", "with entrainment (momentum-conserving)"))],
              fontsize=7.5, frameon=False, loc="lower right")
    ax.set_title(T("(d) 一様な斜面で一斉に動き出す雪の速さ", "(d) sheet released on a uniform slope"), fontsize=9.5, loc="left")
    save(fig, "limits.png")


def sheet_ode(h0, mu, xi, de, inertia, slope=0.5, tmax=10.0, dt=1.0e-3):
    """一様な斜面で一斉に動き出す一様な厚さの雪(勾配なし)の水平流速 u と厚さ h。
    du/dt = g cos²θ (tanθ − μ) − g u²/(ξ h cos²θ) [− u (dh/dt)/h]、dh/dt = δe u。
    最後の項は連行した雪を加速する運動量で、ENCflow は持たない(流速を変数に解き、連行は厚さだけを増やす)。"""
    c2 = 1.0 / (1.0 + slope ** 2)
    t, u, h = 0.0, 0.0, h0
    tt, uu, hh = [], [], []
    while t <= tmax + 1e-9:
        tt.append(t), uu.append(u), hh.append(h)
        e = de * u
        a = G * c2 * (slope - mu) - G * u * u / (xi * h * c2) - (u * e / h if inertia else 0.0)
        u, h, t = u + a * dt, h + e * dt, t + dt
    return np.array(tt), np.array(uu), np.array(hh)


# ---------------------------------------------------------------- 誘導堤の設計式(Jóhannesson ら 2009)
def dam_design(u1, h1, phi_h, psi, alpha):
    """堤に当たる流れ(速さ u1、厚さ h1)に対する、Jóhannesson ら (2009) の 2 つの高さ (m)。
    phi_h 平面での偏向角、psi 地形の傾き、alpha 堤の上流側ののり面の傾き(いずれも rad)。
    返り値: フルード数 Fr、堤に直角な成分 Fr⊥、射流のまま越えない高さ H_cr + h_cr(式 (5.9)。
    k^(3/2) Fr⊥ <= 1 では条件にならないので nan)、衝撃波の下流の厚さ h2(式 (5.10)・(5.11))。"""
    g = 9.8                                                   # 同書の値
    phi = math.atan(math.tan(phi_h) * math.cos(psi))           # 式 (6.1)
    fr = u1 / math.sqrt(g * math.cos(psi) * h1)                # 式 (4.1)
    fp = fr * math.sin(phi)                                    # 式 (5.8)
    a = math.degrees(alpha)
    k = 0.75 if a > 60.0 else 0.75 + 0.1 * (60.0 - a) / 30.0   # 式 (5.14)
    hcr = h1 * (1.0 / k + 0.5 * (k * fp) ** 2 - 0.5 * fp ** (2.0 / 3.0)) if k ** 1.5 * fp > 1.0 else float("nan")
    delta = (math.pi / 2 - math.atan((9 * fp ** 2 - 8) / (fp * math.sqrt(27 * (16 + 13 * fp ** 2 + 8 * fp ** 4))))) / 3
    h2 = h1 * (2 * math.sqrt(6 * fp ** 2 + 4) * math.cos(delta) + 1) / 3
    return fr, fp, hcr, h2


# ---------------------------------------------------------------- 数表
def table():
    sb, beta = beta_point()
    a0 = ALPHA_A * beta + ALPHA_B
    print(f"\nβ 点 s = {sb:.0f} m, β = {beta:.2f}°, α–β の式 α = {a0:.2f}° ± {ALPHA_SD}°"
          f"(先端 s = {tip_of_angle(a0):.0f} m、{tip_of_angle(a0 + ALPHA_SD):.0f}〜{tip_of_angle(a0 - ALPHA_SD):.0f} m)、"
          f"見通し角 18° の位置 s = {tip_of_angle(18.0):.0f} m")
    print("\ncase         rel   snow    ent   peak  x-rel | tapex tstop vfront | Dgully Vgully Dmouth Vmouth Vmax Vfan |  tip   rtip alpha |  area  depvol depmax width trackdep | remain ledger")
    for nm in M.CASES:
        if not have(nm):
            continue
        st = get(nm).stats()
        print(f"{nm:11s} {st['rel']:6.0f} {st['snow']:6.0f} {st['ent']:6.0f} {st['peak']:6.0f} {st['peak'] / st['rel']:5.2f} | "
              f"{st['tapex']:5.1f} {st['tstop']:5.0f} {st['vfront']:6.1f} | {st['dgully']:6.2f} {st['vgully']:6.1f} {st['dmouth']:6.2f} {st['vmouth']:6.1f} {st['vmax']:4.1f} {st['vfan']:4.1f} | "
              f"{st['tip']:6.1f} {st['rtip']:5.1f} {st['alpha']:5.2f} | {st['area']:6.0f} {st['depvol']:6.0f} {st['depmax']:6.2f} {st['width']:5.0f} {st['trackdep']:8.0f} | "
              f"{st['remain']:6.0f} {st['ledger']:6.2f}")
    print(f"\n家屋({len(M.houses())} 戸): 最大流動深 {H_HOUSE} m 以上 / 堆積 {H_HOUSE} m 以上 / 最大流動深の最大 / 最大流速の最大 / 圧力の目安 ρV²(ρ = {RHO:.0f} kg/m³)")
    for nm in ("nosnow", "base", "deep", "dam", "deep_dam"):
        if not have(nm):
            continue
        c = get(nm)
        hs = c.houses()
        bd = c.behind_dam()
        vb = (np.where(bd, np.clip(c.dz, 0, None), 0).sum() + np.where(bd, c.depth(c.kend), 0).sum()) * c.area
        ab = (bd & (c.D >= H_THR)).sum() * c.area
        print(f"{nm:9s} {hs['hit']:3d} / {hs['buried']:3d} / {hs['dmax']:5.2f} m / {hs['vmax']:5.1f} m/s / {RHO * hs['vmax'] ** 2 / 1e3:6.1f} kPa"
              f" | 堤の線より右岸側: 雪 {vb:6.0f} m³、流れた範囲 {ab:6.0f} m²")
    (s1, n1), (s2, n2) = M.DAM_A, M.DAM_B
    L = math.hypot(s2 - s1, n2 - n1)
    phi_h = math.atan2(n2 - n1, s2 - s1)
    psi = math.atan(float(M.slope_axis(M.S_A)))
    alpha = math.atan(1.0 / M.DAM_SLOPE)
    t0 = dam_design(29.5, 2.0, math.radians(34.0), 0.0, math.radians(90.0))
    print(f"\n誘導堤の長さ {L:.0f} m、平面での偏向角 {math.degrees(phi_h):.1f}°。設計式の確かめ(Jóhannesson ら 2009 の表 C3: "
          f"H_cr + h_cr = 8.1 m、h2 = 11.7 m): {t0[2]:.1f} m、{t0[3]:.1f} m")
    for nm, dm_name in (("base", "dam"), ("deep", "deep_dam")):
        if not have(nm):
            continue
        c = get(nm)
        mouth = c.mask & (np.abs(c.s - M.S_A) <= c.dx) & (c.D >= H_VEL)
        u1, hmax = c.V[mouth].max(), c.D[mouth].max()
        hmean = c.D[mouth].sum() / mouth.sum()
        wid = mouth.sum() * c.dx / 2.0
        print(f"{nm}: 沢の出口の流れ(堤なし): 最大流速 {u1:.1f} m/s、最大流動深 {hmax:.2f} m、幅 {wid:.0f} m の平均 {hmean:.2f} m")
        for lab, h1 in (("沢筋の最大流動深", hmax), ("幅の平均の流動深", hmean)):
            fr, fp, hcr, h2 = dam_design(u1, h1, phi_h, psi, alpha)
            hu = h1 + (u1 * math.sin(phi_h)) ** 2 / (2 * G)
            print(f"   {lab} {h1:5.2f} m: Fr = {fr:.2f}, Fr⊥ = {fp:.2f}, H_cr + h_cr = {hcr:5.1f} m, 衝撃波の下流の厚さ h2 = {h2:5.1f} m, "
                  f"従来の式 h1 + (u sinφ)²/2g = {hu:5.1f} m")
        if not have(dm_name):
            continue
        c = get(dm_name)
        tpar = ((c.s - s1) * (s2 - s1) + (c.n - n1) * (n2 - n1)) / L
        dist = ((s2 - s1) * (c.n - n1) - (n2 - n1) * (c.s - s1)) / L       # 正が上流(左岸)側
        print(f"{dm_name}: 堤の上流側ののり面の駆け上がり(堤の盛土の高さ + 最大流動深。流動深 0.5 m 以上)と天端の最大流動深")
        for a in np.arange(0, L, 50.0):
            seg = c.mask & (tpar >= a) & (tpar < a + 50.0)
            face = seg & (dist > 0) & (c.dam > 0.2) & (c.D >= H_VEL)
            crest = seg & (np.abs(dist) <= M.DAM_CREST / 2 + c.dx / 2)
            hd = M.DAM_H[0] + (M.DAM_H[1] - M.DAM_H[0]) * min(a + 25.0, L) / L
            run = (c.dam[face] + c.D[face]).max() if face.any() else 0.0
            print(f"  {a:3.0f}-{min(a + 50, L):3.0f} m: 堤高 {hd:4.1f} m, 駆け上がり {run:5.1f} m, 天端の最大流動深 {c.D[crest].max() if crest.any() else 0:5.2f} m")


def main():
    fig_setup()
    fig_mechanism()
    if have("base"):
        fig_flow()
    if all(have(nm) for nm in ("nosnow", "base", "deep")):
        fig_entrain()
        fig_runout()
    if all(have(nm) for nm in ("base", "dam", "deep", "deep_dam")):
        fig_dam()
    if all(have(nm) for nm in ("base", "dx10", "r45")):
        fig_grid()
    if all(have(nm) for nm in ("base", "allsnow")):
        fig_limits()
    table()


if __name__ == "__main__":
    main()
