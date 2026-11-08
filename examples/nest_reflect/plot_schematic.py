#!/usr/bin/env python3
"""nest_reflect の説明図(計算結果を使わない。make_inputs.py・param_*.txt・nest_*.txt の値と式だけ)。

  figs/setup.png      構成: 領域・初期水位・子(と孫)の足元、子の足元の角の拡大(親セル・子セル・帯・
                      置換される親セル・誤差を数える範囲)、格子と時間刻みの一覧
  figs/mechanism.png  仕組み: 線形理論で見た波と子の界面の位置関係、時間比 r_t による親子の時間刻み、
                      非静水圧の分散とガウス波の波数の分布(σ = 5 m と 2 m)
引数 en で英語ラベル版を en/figs/ に描く(形・値・描画処理は共通で、ラベルだけが切り替わる)。
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
FIGDIR = "en/figs" if EN else "figs"
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAPGothic", "IPAGothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

C_INK, C_MUTED = "#1f1f1f", "#8a8983"
C_P, C_C, C_G = "#6b6a66", "#2a78d6", "#7b4fb3"          # 親・子・孫
C_BAND, C_REPL, C_CORE = "#f6d27a", "#3f7a2a", "#eb6834"
# make_inputs.py・param_*.txt の値
A, SIG, SIG_NH, H0, G = 0.2, 5.0, 2.0, 1.0, 9.8
LX, NP = 100.0, 385
DXP = LX / NP                                            # 親の刻み 0.2597 m
I0, NF = 160, 67                                         # 子の足元(親セル 160..226)
X1, X2 = (I0 - 1) * DXP, (I0 - 1 + NF) * DXP             # 41.30 .. 58.70 m
G0, NGF = 61, 81                                         # 孫の足元(比 3 の子のセル 61..141)
XG1, XG2 = X1 + (G0 - 1) * DXP / 3, X1 + (G0 - 1 + NGF) * DXP / 3
C0 = np.sqrt(G * H0)                                     # 長波の速さ 3.13 m/s
RF, RC = (X2 - X1) / 2, (X2 - X1) / 2 * np.sqrt(2)       # 中心から界面の辺・角まで 8.70 / 12.30 m


def style(ax, grid=True):
    if grid:
        ax.grid(color="#eceae6", lw=0.6)
        ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8.5)


def panel_title(ax, s, y=1.02):
    ax.text(0.0, y, s, transform=ax.transAxes, fontsize=10.5, ha="left", va="bottom", color=C_INK)


def J0(x):
    """第 1 種 0 次の Bessel 関数(Abramowitz & Stegun 9.4.1・9.4.3。誤差 1e-7 程度)"""
    x = np.abs(np.asarray(x, float))
    out = np.empty_like(x)
    s = x <= 3.0
    y = (x[s] / 3.0) ** 2
    out[s] = 1 + y * (-2.2499997 + y * (1.2656208 + y * (-0.3163866 + y * (0.0444479 + y * (-0.0039444 + y * 0.0002100)))))
    xl = x[~s]
    u = 3.0 / xl
    f0 = 0.79788456 + u * (-0.00000077 + u * (-0.00552740 + u * (-0.00009512 + u * (0.00137237 + u * (-0.00072805 + u * 0.00014476)))))
    t0 = xl - 0.78539816 + u * (-0.04166397 + u * (-0.00003954 + u * (0.00262573 + u * (-0.00054125 + u * (-0.00029333 + u * 0.00013558)))))
    out[~s] = f0 * np.cos(t0) / np.sqrt(xl)
    return out


def radial(r, t, sig):
    """線形の浅水波(静水圧)で、静止から放したガウス型の水位 a·exp(−r²/σ²) の解(Hankel 変換)"""
    k = np.linspace(1e-6, 12.0 / sig, 3000)
    w = A * sig ** 2 / 2 * np.exp(-k ** 2 * sig ** 2 / 4) * np.cos(C0 * k * t) * k * (k[1] - k[0])
    return np.array([np.dot(J0(k * rr), w) for rr in np.atleast_1d(r)])


# ============================== figs/setup.png ==============================
def fig_setup():
    fig = plt.figure(figsize=(13.4, 6.3), facecolor="white")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 0.86, 0.62], wspace=0.22, left=0.05, right=0.99, top=0.86, bottom=0.1)

    # ---- (a) 平面 ----
    ax = fig.add_subplot(gs[0, 0])
    xx = np.linspace(0, LX, 501)
    X, Y = np.meshgrid(xx, xx)
    eta0 = A * np.exp(-((X - 50) ** 2 + (Y - 50) ** 2) / SIG ** 2)
    im = ax.imshow(eta0, extent=(0, LX, 0, LX), origin="lower", cmap="Blues", vmin=0, vmax=0.2, interpolation="bilinear")
    ax.add_patch(Rectangle((X1, X1), X2 - X1, X2 - X1, fill=False, ec=C_C, lw=1.6, ls="--", zorder=4))
    ax.add_patch(Rectangle((XG1, XG1), XG2 - XG1, XG2 - XG1, fill=False, ec=C_G, lw=1.1, ls=":", zorder=4))
    rr = np.linspace(0, 30, 601)
    for t in (2, 4, 6):
        rp = rr[int(np.argmax(radial(rr, t, SIG)))]
        ax.add_patch(Circle((50, 50), rp, fill=False, ec=C_MUTED, lw=0.9, zorder=3))
        ax.text(50 + (rp + 0.4) * np.cos(np.radians(-40)), 50 + (rp + 0.4) * np.sin(np.radians(-40)), "%d s" % t, fontsize=8.3, color="#555",
                ha="left", va="top", zorder=5)
    ax.text(X1, X2 + 0.6, T("子の足元(親セル 160..226、17.4 m 四方)", "child footprint (cells 160..226, 17.4 m)"),
            fontsize=8.3, color=C_C, va="bottom", ha="left")
    ax.text(50, XG1 - 0.4, T("孫の足元(2 段の例)", "grandchild footprint (2-level case)"), fontsize=7.5, color=C_G, ha="center", va="top", zorder=6,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    ax.text(25.6, 74.6, T("灰色の円 = 山の位置(線形理論の目安)\n領域は 100 m 四方で周りは壁(10 s では\n波は届かない)",
                          "grey circles = crest position (linear theory,\napproximate); the domain is 100 m square with\nwalls (not reached by the wave within 10 s)"),
            fontsize=7.8, color="#555", va="top")
    ax.set_xlim(25, 75)
    ax.set_ylim(25, 75)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)", fontsize=9)
    ax.set_ylabel("y (m)", fontsize=9)
    style(ax, grid=False)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label(T("初期水位 η (m)", "initial water level η (m)"), fontsize=8.5)
    cb.ax.tick_params(labelsize=8)
    panel_title(ax, T("(a) 中央部(水深 1 m)。ガウス波 a = 0.2 m、σ = 5 m",
                      "(a) Central part (1 m deep); Gaussian a = 0.2 m, σ = 5 m"))

    # ---- (b) 子の足元の北西の角の拡大 ----
    axz = fig.add_subplot(gs[0, 1])
    i1, i2 = I0 - 3, I0 + 5                               # 親セル 157..164
    xa, xb = (i1 - 1) * DXP, i2 * DXP
    ya, yb = LX - xb, LX - xa                             # 北西の角(y は北が上。足元は対称)
    YT = LX - X1                                          # 足元の北の辺 y = 58.70 m
    # 範囲の塗り: 帯(子 3 セル = 親 1 セル)と置換される親セル
    axz.add_patch(Rectangle((X1, ya), xb - X1, YT - ya, facecolor="#eef5fc", edgecolor="none", zorder=0))
    axz.add_patch(Rectangle((X1, ya), DXP, YT - ya, facecolor=C_BAND, edgecolor="none", alpha=0.85, zorder=1))
    axz.add_patch(Rectangle((X1, YT - DXP), xb - X1, DXP, facecolor=C_BAND, edgecolor="none", alpha=0.85, zorder=1))
    axz.add_patch(Rectangle((X1 + DXP, ya), xb - X1 - DXP, YT - DXP - ya, facecolor="none", edgecolor=C_REPL, hatch="///",
                            lw=0, alpha=0.55, zorder=2))
    # 格子線: 子(足元の中)と親
    for k in range(0, int(round((xb - X1) / (DXP / 3))) + 1):
        xv = X1 + k * DXP / 3
        axz.plot([xv, xv], [ya, YT], color=C_C, lw=0.35, alpha=0.6, zorder=3)
    for k in range(0, int(round((YT - ya) / (DXP / 3))) + 1):
        yv = YT - k * DXP / 3
        axz.plot([X1, xb], [yv, yv], color=C_C, lw=0.35, alpha=0.6, zorder=3)
    for i in range(i1 - 1, i2 + 1):
        axz.plot([i * DXP] * 2, [ya, yb], color=C_P, lw=0.9, zorder=4)
        axz.plot([xa, xb], [LX - i * DXP] * 2, color=C_P, lw=0.9, zorder=4)
    axz.plot([X1, X1, xb], [ya, YT, YT], color=C_C, lw=2.0, zorder=5)
    xcore, ycore = X1 + 2 * DXP, YT - 2 * DXP
    axz.plot([xcore, xcore, xb], [ya, ycore, ycore], color=C_CORE, lw=1.4, ls="--", zorder=6)
    axz.set_xlim(xa, xb)
    axz.set_ylim(ya, yb)
    axz.set_aspect("equal")
    axz.set_xticks([])
    axz.set_yticks([])
    for s in axz.spines.values():
        s.set_visible(False)
    lab = dict(fontsize=8.0, zorder=8, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9))
    axz.text(xa + 0.07, yb - 0.07, T("外側(out)", "outside (out)"), color=C_INK, va="top", **lab)
    axz.text(X1 + DXP * 0.5, YT - 4.3 * DXP, T("帯: 子 3 セル\n= 親 1 セル", "band: 3 child\ncells = 1 parent"), color="#8a6a00",
             ha="center", va="top", rotation=0, **lab)
    axz.text(X1 + DXP * 3.6, YT - DXP * 3.6, T("置換される親セル\n(帯を含まない)", "parent cells replaced\n(no band in them)"), color=C_REPL,
             ha="center", va="center", **lab)
    axz.text(xb - 0.04, ycore - 0.04, T("core の境(外周 2 親セルを除く)", "core boundary\n(outer 2 parent cells excluded)"), color=C_CORE,
             ha="right", va="top", **lab)
    axz.text(X1 + 0.03, YT + 0.05, T("子の足元(in)の北西の角", "NW corner of the child footprint (in)"), color=C_C, va="bottom", ha="left", **lab)
    panel_title(axz, T("(b) 足元の角の拡大(比 3。太線 = 親セル、細線 = 子セル)", "(b) Footprint corner (ratio 3; thick: parent, thin: child)"))

    # ---- (c) 格子と時間刻み ----
    axn = fig.add_subplot(gs[0, 2])
    axn.axis("off")
    rows = [(T("格子", "grid"), "Δx", "dt"),
            (T("粗格子単独 385²", "coarse alone 385²"), "0.260 m", T("1/60・0.05 s", "1/60, 0.05 s")),
            (T("一様細格子 1155²(基準)", "uniform fine 1155² (ref.)"), "0.087 m", "1/60 s"),
            (T("比 3 の子 201²", "ratio-3 child 201²"), "0.087 m", "1/60 s"),
            (T("比 5 の子 335²", "ratio-5 child 335²"), "0.052 m", "1/100 s"),
            (T("2 段の孫 243²", "2-level grandchild 243²"), "0.029 m", "1/180 s")]
    for k, (a_, b_, c_) in enumerate(rows):
        yv = 0.97 - k * 0.052
        col = C_MUTED if k == 0 else C_INK
        axn.text(0.0, yv, a_, transform=axn.transAxes, fontsize=8.2, va="top", color=col)
        axn.text(0.62, yv, b_, transform=axn.transAxes, fontsize=8.2, va="top", color=col)
        axn.text(0.85, yv, c_, transform=axn.transAxes, fontsize=8.2, va="top", color=col)
    notes = T(
        "親の dt: r_t = 1 では子と同じ(1/60・1/100 s)、\nr_t = r では自分の 0.05 s(子は dt/r_t)\n\n"
        "長波の速さ $\\sqrt{gH}$ = 3.13 m/s\n子の界面まで 8.7 m(角まで 12.3 m)\n\n"
        "誤差 = η − η_fine(細格子を親セルごとに\n3×3 平均)。in = 足元の内側、out = 外側、\n"
        "子の誤差は子を親格子へ平均し、\ncore(外周 2 親セルを除く)と\nfull(足元全体)で数える\n\n"
        "非静水圧の版は σ = 2 m(kH ≈ 0.5)",
        "parent dt: equal to the child's with r_t = 1\n(1/60, 1/100 s); its own 0.05 s with r_t = r\n(the child uses dt/r_t)\n\n"
        "long-wave speed $\\sqrt{gH}$ = 3.13 m/s\n8.7 m to the child interface (12.3 m\nto the corners)\n\n"
        "error = η − η_fine (fine grid averaged 3×3\nper parent cell); in = inside the footprint,\nout = outside; the child's error is taken\n"
        "after averaging onto the parent grid, over\nthe core (outer 2 parent cells excluded)\nand full (whole footprint)\n\n"
        "non-hydrostatic version: σ = 2 m (kH ≈ 0.5)")
    axn.text(0.0, 0.60, notes, transform=axn.transAxes, fontsize=8.2, va="top", color=C_INK, linespacing=1.35)
    panel_title(axn, T("(c) 格子と時間刻み", "(c) Grids and time steps"))

    fig.suptitle(T("nest_reflect の構成(入力ファイルと式から描いた図で、計算結果ではない)",
                   "Setup of nest_reflect (drawn from the input files and formulas; not computed results)"), fontsize=12.5, x=0.02, ha="left", y=0.985)
    out = os.path.join(FIGDIR, "setup.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)


# ============================== figs/mechanism.png ==============================
def fig_mechanism():
    fig = plt.figure(figsize=(13.0, 8.6), facecolor="white")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.95], hspace=0.42, wspace=0.24, top=0.91)

    # ---- (a) 線形理論の断面 ----
    ax = fig.add_subplot(gs[0, :])
    r = np.linspace(0, 32, 641)
    cols = {0: "#9a9890", 1: "#7fb2e8", 2: "#2a78d6", 3: "#1b4f99", 4: "#eb6834", 6: "#b04a1f", 8: "#7b4fb3"}
    ax.axvspan(0, RF, color="#eef5fc", lw=0, zorder=0)
    ax.axvspan(RF, RC, color="#f6f3ea", lw=0, zorder=0)
    for t, c in cols.items():
        ax.plot(r, radial(r, t, SIG), color=c, lw=1.6 if t else 1.2, ls="-" if t else "--", label="t = %d s" % t)
    ax.axhline(0, color=C_MUTED, lw=0.6)
    ax.axvline(RF, color=C_C, lw=1.2, ls="--")
    ax.axvline(RC, color=C_C, lw=0.8, ls=":")
    amp = radial(RF, 2.1, SIG)[0]
    ax.annotate(T("界面での山の高さ %.3f m(t ≈ 2 s)" % amp, "crest height at the interface %.3f m (t ≈ 2 s)" % amp), xy=(RF, amp),
                xytext=(RF + 4.0, 0.105), fontsize=8.5, color=C_INK, arrowprops=dict(arrowstyle="-", color=C_MUTED, lw=0.7))
    ax.text(RF / 2, 0.205, T("子の中(辺まで 8.7 m)", "inside the child (8.7 m to the edges)"), fontsize=8.5, color=C_C, ha="center")
    ax.text((RF + RC) / 2, 0.205, T("角まで\n12.3 m", "to the\ncorners\n12.3 m"), fontsize=8, color=C_C, ha="center", va="center")
    ax.text(16.5, -0.042, T("t = 4 s: 山は外へ出て、後ろの谷が界面を横切る", "t = 4 s: the crest is outside; the trailing trough is crossing the interface"),
            fontsize=8.5, color="#b04a1f", ha="left")
    ax.set_xlim(0, 32)
    ax.set_ylim(-0.06, 0.22)
    ax.set_xlabel(T("中心からの距離 r (m)", "distance from the centre r (m)"), fontsize=9)
    ax.set_ylabel(T("水位 η (m)", "water level η (m)"), fontsize=9)
    ax.legend(fontsize=8, frameon=False, ncol=7, loc="upper right", bbox_to_anchor=(1.0, 0.93))
    style(ax)
    panel_title(ax, T("(a) 線形理論(静水圧)で見た波と子の界面: 山は 2〜3 s で界面を越え、6 s には子を出ている",
                      "(a) The wave and the child interface by linear theory (hydrostatic): the crest crosses at 2–3 s and has left by 6 s"))

    # ---- (b) 時間比 r_t ----
    axb = fig.add_subplot(gs[1, 0])
    tmax = 0.1
    rows = [(3.0, T("r_t = 1 の親(dt = 1/60 s)", "parent, r_t = 1 (dt = 1/60 s)"), 1 / 60, C_P, "Cn 0.20"),
            (2.2, T("r_t = 1 の子(1/60 s)", "child, r_t = 1 (1/60 s)"), 1 / 60, C_C, "Cn 0.60"),
            (1.0, T("r_t = 3 の親(0.05 s)", "parent, r_t = 3 (0.05 s)"), 0.05, C_P, "Cn 0.60"),
            (0.2, T("r_t = 3 の子(1/60 s)", "child, r_t = 3 (1/60 s)"), 1 / 60, C_C, "Cn 0.60")]
    for yv, lab, dt, c, cn in rows:
        tt = np.arange(0, tmax + 1e-9, dt)
        axb.plot([0, tmax], [yv, yv], color=c, lw=1.6)
        axb.plot(tt, np.full_like(tt, yv), "o", color=c, ms=5)
        axb.text(-0.004, yv, lab, fontsize=8.3, ha="right", va="center", color=c)
        axb.text(tmax + 0.003, yv, cn, fontsize=8.3, ha="left", va="center", color=C_INK)
    for tk in (1 / 60, 2 / 60):
        axb.annotate("", xy=(tk, 0.32), xytext=(tk, 0.88), arrowprops=dict(arrowstyle="-|>", color="#c4682f", lw=1.0, ls="--"))
    axb.text(0.037, 0.6, T("子の帯の値は親の 2 時刻(t = 0 と 0.05 s)の時間補間", "the child's band values: interpolated in time\nbetween the parent's t = 0 and 0.05 s"),
             fontsize=7.8, color="#c4682f", ha="left", va="center")
    axb.text(0.05, 3.55, T("Cn = $\\sqrt{gH}$·dt/Δx(親 Δx = 0.26 m、子 0.087 m)", "Cn = $\\sqrt{gH}$·dt/Δx (parent Δx = 0.26 m, child 0.087 m)"),
             fontsize=8, color=C_MUTED, ha="center")
    axb.set_xlim(-0.002, tmax + 0.002)
    axb.set_ylim(-0.3, 3.8)
    axb.set_yticks([])
    axb.set_xlabel(T("時刻 t (s)", "time t (s)"), fontsize=9)
    style(axb, grid=False)
    axb.spines["left"].set_visible(False)
    panel_title(axb, T("(b) 時間比 r_t(比 3): r_t = 1 は親も子の dt で進む", "(b) Time ratio r_t (ratio 3): with r_t = 1 the parent uses the child's dt"))

    # ---- (c) 非静水圧の分散と波数の分布 ----
    axc = fig.add_subplot(gs[1, 1])
    kh = np.linspace(1e-3, 2.0, 400)
    axc.plot(kh, np.ones_like(kh), color=C_MUTED, lw=1.5, label=T("静水圧(分散なし)", "hydrostatic (no dispersion)"))
    axc.plot(kh, 1 / np.sqrt(1 + kh ** 2 / 4), color=C_C, lw=2.0, label=T("1 層非静水圧", "one-layer non-hydrostatic"))
    axc.plot(kh, np.sqrt(np.tanh(kh) / kh), color=C_INK, lw=1.1, ls=":", label=T("厳密(線形の水面波)", "exact (linear water waves)"))
    axc.set_xlim(0, 2.0)
    axc.set_ylim(0.6, 1.05)
    axc.set_xlabel("kH(H = 1 m)", fontsize=9)
    axc.set_ylabel(T("波の速さ / $\\sqrt{gH}$", "wave speed / $\\sqrt{gH}$"), fontsize=9)
    style(axc)
    ax2 = axc.twinx()
    for sig, c, lab in ((SIG, "#9a9890", T("σ = 5 m(静水圧の版)", "σ = 5 m (hydrostatic version)")),
                        (SIG_NH, "#eb6834", T("σ = 2 m(非静水圧の版)", "σ = 2 m (non-hydrostatic version)"))):
        e = kh * np.exp(-kh ** 2 * sig ** 2 / 2)            # 2 次元のガウス波のエネルギーの波数分布 ∝ k·Â(k)²
        ax2.fill_between(kh, e / e.max(), color=c, alpha=0.18, lw=0)
        ax2.plot(kh, e / e.max(), color=c, lw=1.0, label=lab)
    ax2.set_ylim(0, 2.6)
    ax2.set_yticks([])
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    h1, l1 = axc.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    axc.legend(h1 + h2, l1 + l2, fontsize=7.8, frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.9))
    axc.text(0.04, 0.80, T("塗り = ガウス波のエネルギーの\n波数の分布(相対)", "shaded = energy of the Gaussian\nover wavenumber (relative)"), fontsize=7.8, color=C_MUTED)
    panel_title(axc, T("(c) σ = 2 m の波は分散が効く(kH ≈ 0.5 で 3 % 遅い)", "(c) The σ = 2 m wave is dispersive (3 % slower at kH ≈ 0.5)"))

    fig.suptitle(T("nest_reflect の仕組み(入力と式から描いた図で、計算結果ではない)",
                   "How nest_reflect works (drawn from the inputs and formulas; not computed results)"), fontsize=12.5, x=0.02, ha="left", y=0.99)
    out = os.path.join(FIGDIR, "mechanism.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved", out)


if __name__ == "__main__":
    fig_setup()
    fig_mechanism()
