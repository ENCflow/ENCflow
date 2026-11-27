#!/usr/bin/env python3
"""examples/coarse_channel: 図(figs/*.png)と数表を描く

  python3 plot_results.py        日本語の図を figs/ に描き、README 用の数表を標準出力に書く
  python3 plot_results.py en     英語の図を en/figs/ に描く(数表も英語)

計算していない系列の図は飛ばす(make が呼ぶ)。
"""
import math
import os
import sys
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

HERE = os.path.dirname(os.path.abspath(__file__))
EN = "en" in sys.argv[1:]
os.environ["ENCFLOW_LANG"] = "en" if EN else "ja"
sys.path.insert(0, HERE)
import make_cases as mc
import analyze as A


def T(ja, en):
    return en if EN else ja


FIGDIR = os.path.join(HERE, "en", "figs") if EN else os.path.join(HERE, "figs")
os.makedirs(FIGDIR, exist_ok=True)
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# 色: 文字は 2 段の墨、目盛り・枠は薄い灰。表し方の色は全部の図で同じ(色は表し方に付く)
INK, INK2, GRID, AXIS, BAND = "#191919", "#666666", "#e7e7e7", "#c2c2c2", "#efefef"
C = {"lo": "#257de0", "hi": "#f47230", "mix": "#00b894", "split": "#f2a600", "k2": "#ee7fac", "sub1": "#008a17",
     "k1": "#6a4ce2", "fine": "#666666", "t50": "#6a4ce2", "t50s": "#ec4647", "all": "#008a17"}
MK = {"lo": "o", "hi": "s", "mix": "D", "split": "v", "k2": "^", "sub1": "P", "k1": "X", "fine": "h",
      "t50": "o", "t50s": "s", "all": "D"}
REPL = {"lo": T("解像 n 列", "n resolved rows"), "hi": T("解像 n+1 列", "n+1 resolved rows"),
        "mix": T("解像 n 列 + 残りのサブグリッド 1 列", "n resolved + 1 remainder subgrid row"),
        "split": T("n+1 列のサブグリッドに等分", "n+1 subgrid rows, equal split"),
        "k1": T("段で 1 行を共有", "1 row shared at steps"), "k2": T("段で 2 行を共有", "2 rows shared at steps"),
        "k2w": T("段で 2 行を共有 + 幅を縮める", "2 rows shared + widths scaled"),
        "sub1": T("サブグリッド 1 列", "one subgrid row"),
        "d8": T("1 列に 1 セル(8 連結)", "one cell per column (8-connected)"),
        "st4": T("4 連結の階段", "4-connected staircase"), "fine": T("Δx = 20 m", "Δx = 20 m"),
        "t50": T("占有率 50 % 以上を解像", "cells ≥ 50 % covered resolved"),
        "t50s": T("50 % 以上を解像 + 残りを占有率の幅", "≥ 50 % resolved + rest at covered width"),
        "all": T("全セルを占有率の幅", "all cells at covered width"),
        "t30s": T("30 % 以上を解像 + 残りを占有率の幅", "≥ 30 % resolved + rest at covered width"),
        "t70s": T("70 % 以上を解像 + 残りを占有率の幅", "≥ 70 % resolved + rest at covered width")}
# 縮図の見出し(英語は短く)
REPS = dict(REPL)
if EN:
    REPS.update({"mix": "n resolved + remainder", "split": "equal-split subgrid", "k2w": "2 rows shared, widths scaled",
                 "d8": "one cell per column", "k2": "2 rows shared at steps", "t50": "≥ 50 % resolved",
                 "t50s": "≥ 50 % resolved + rest", "all": "all at covered width"})
# 縮図の色: 河道でない・サブグリッド河道・解像した河道・太らせて足したセル(段で行を共有する表し方の色)
CMAP = ListedColormap(["#ffffff", "#9dc8f7", "#1757ac", "#ee7fac"])
ANG = list(mc.ANGLES)
ANGX = [mc.ANGLE_DEG[a] for a in ANG]
YLAB = T("通水の幅 ÷ 川幅", "conveyance width ÷ channel width")


def style(ax, xlabel=None, ylabel=None):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=8.5)
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK2, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK2, fontsize=9)


def band(ax):
    """±10 % の帯と 1 の線"""
    ax.axhspan(0.9, 1.1, color=BAND, zorder=0, lw=0)
    ax.axhline(1.0, color=AXIS, lw=1.0, zorder=0.5)


def title(ax, s, loc="left"):
    ax.set_title(s, loc=loc, fontsize=9.5, color=INK)


def line(ax, x, y, rep, label=None, top=None, color=None, marker=None):
    """表し方ごとの折れ線。上限 top を超える点は枠の上端に印を描いて値を添える"""
    x, y = np.asarray(x, float), np.asarray(y, float)
    col = color or C[rep]
    ax.plot(x, y, color=col, lw=1.6, marker=marker or MK[rep], ms=6.5, mec="white", mew=1.0,
            label=label if label is not None else REPL[rep], zorder=3, solid_capstyle="round", clip_on=True)
    if top is not None:
        for xi, yi in zip(x, y):
            if np.isfinite(yi) and yi > top:
                ax.plot([xi], [top], marker=marker or MK[rep], ms=6.5, color=col, mec="white", mew=1.0, clip_on=False,
                        zorder=4)
                ax.annotate(f"{yi:.2f}", (xi, top), xytext=(4, -3), textcoords="offset points", fontsize=7.5,
                            color=INK2, annotation_clip=False)


def rowmajor(items, ncol):
    """凡例を行の順に読めるように並べ替える(matplotlib は列の順に詰める)"""
    nrow = -(-len(items) // ncol)
    out = []
    for c in range(ncol):
        for r in range(nrow):
            k = r * ncol + c
            if k < len(items):
                out.append(items[k])
    return out


def legend(fig, ax=None, ncol=3, y=1.0, x=0.5, **kw):
    src = ax if ax is not None else fig.axes[0]
    h, lab = src.get_legend_handles_labels()
    h, lab = rowmajor(h, ncol), rowmajor(lab, ncol)
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(x, y), ncol=ncol, frameon=False, fontsize=8.5,
               handlelength=2.2, **kw)


def save(fig, name):
    fig.savefig(os.path.join(FIGDIR, name), dpi=130, facecolor="white")
    plt.close(fig)
    print(f"  {os.path.relpath(os.path.join(FIGDIR, name), HERE)}")


# ------------------------------------------------------------------ 縮図
def raster(ax, width, dx, ly, xw, yw, edge="#d0d0d0", base=None):
    """河道の幅の配列を、窓 xw = (x0, x1)・yw = (y0, y1) の範囲だけ描く(行 0 が北端)。base を渡すと、base で河道
    でないセルを「太らせて足したセル」の色で描く"""
    ny, nx = width.shape
    i0, i1 = max(0, int(xw[0] // dx)), min(nx, int(math.ceil(xw[1] / dx)))
    j0, j1 = max(0, int((ly - yw[1]) // dx)), min(ny, int(math.ceil((ly - yw[0]) / dx)))
    sub = width[j0:j1, i0:i1][::-1, :]
    v = np.where(sub >= mc.RESOLVED, 2, np.where(sub > 0, 1, 0))
    if base is not None:
        v = np.where((sub > 0) & (base[j0:j1, i0:i1][::-1, :] <= 0), 3, v)
    xe = np.arange(i0, i1 + 1) * dx
    ye = (ly - np.arange(j0, j1 + 1) * dx)[::-1]
    ax.pcolormesh(xe, ye, v, cmap=CMAP, vmin=-0.5, vmax=3.5, edgecolors=edge, linewidth=0.4 if dx > 50 else 0.0)
    ax.set_xlim(*xw)
    ax.set_ylim(*yw)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color(AXIS)


def straight_window(g, size=(1000.0, 760.0), s0=4000.0):
    dmid = 0.5 * (g["out"][0] + g["out"][1])
    xc = g["ct"] * s0 - g["st"] * dmid
    yc = g["y0"] + g["st"] * s0 + g["ct"] * dmid
    return (xc - size[0] / 2, xc + size[0] / 2), (yc - size[1] / 2, yc + size[1] / 2)


def straight_outline(ax, g, xw):
    xs = np.array([xw[0] - 200.0, xw[1] + 200.0])
    for dn in g["out"]:
        ax.plot(xs, g["y0"] + (dn + g["st"] * xs) / g["ct"], color=INK, lw=1.1, zorder=5)


def thumb(ax, an, b, rep, dx=mc.DX, label=None, value=None, size=(1000.0, 760.0)):
    g = mc.straight(an, b, rep, dx)
    xw, yw = straight_window(g, size)
    base = mc.straight(an, b, "lo", dx)["width"] if rep in ("k1", "k2", "k2w") else None
    raster(ax, g["width"], dx, g["ly"], xw, yw, base=base)
    straight_outline(ax, g, xw)
    if label:
        ax.set_title(label, fontsize=8.3, color=INK, pad=3)
    if value is not None and np.isfinite(value):
        ax.text(0.03, 0.04, f"{value:.2f}", transform=ax.transAxes, fontsize=8.5, color=INK,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9), zorder=6)


def rel(val, name):
    v = val.get(name)
    return v["rel"] if v else np.nan


# ------------------------------------------------------------------ 図 1: 確かめ方
def fig_setup():
    fig = plt.figure(figsize=(10.0, 4.4))
    ax = fig.add_axes([0.04, 0.08, 0.55, 0.80])
    g = mc.straight("a27", 200.0, "k2", mc.DX)
    raster(ax, g["width"], mc.DX, g["ly"], (0, g["lx"]), (0, g["ly"]), edge="#ececec")
    straight_outline(ax, g, (0, g["lx"]))
    # 測る区間(中心線の距離 3〜5 km)
    for s0 in (mc.S1, mc.S2):
        xc, yc = g["ct"] * s0, g["y0"] + g["st"] * s0
        nx_, ny_ = -g["st"], g["ct"]
        ax.plot([xc - 450 * nx_, xc + 450 * nx_], [yc - 450 * ny_, yc + 450 * ny_], color=INK2, lw=1.2)
    xm, ym = g["ct"] * 4000, g["y0"] + g["st"] * 4000
    ax.annotate(T("測る区間(中心線の距離 3〜5 km)", "measured reach (3–5 km along the centreline)"), (xm, ym),
                xytext=(xm - 3300, ym + 1500), fontsize=8.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.annotate(T("流入 8.5 m²/s × 川幅", "inflow 8.5 m²/s × width"), (0, g["y0"]), xytext=(150, g["y0"] + 1300),
                fontsize=8.5, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ye = g["y0"] + g["lx"] * g["st"] / g["ct"]
    ax.annotate(T("水位を規定\n(等流水深 3.50 m)", "stage prescribed\n(uniform depth 3.50 m)"), (g["lx"], ye),
                xytext=(g["lx"] - 1500, ye - 2300), fontsize=8.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    title(ax, T("(a) 直線の河道の等流(26.6°・川幅 200 m・Δx = 100 m)",
                "(a) Uniform flow in a straight channel (26.6°, 200 m wide, Δx = 100 m)"))
    # (b) セルの中心が並ぶ列
    ax = fig.add_axes([0.63, 0.08, 0.35, 0.80])
    g = mc.straight("a27", 120.0, "lo", mc.DX)
    xw, yw = straight_window(g, (700.0, 560.0))
    raster(ax, g["width"], mc.DX, g["ly"], xw, yw)
    X, Y = np.meshgrid((np.arange(g["nx"]) + 0.5) * mc.DX, g["ly"] - (np.arange(g["ny"]) + 0.5) * mc.DX)
    sel = (X > xw[0]) & (X < xw[1]) & (Y > yw[0]) & (Y < yw[1])
    ax.plot(X[sel], Y[sel], "o", ms=2.6, color=INK2, zorder=6)
    xs = np.array([xw[0] - 100, xw[1] + 100])
    for k in range(-6, 7):
        ax.plot(xs, g["y0"] + (k * g["d"] + g["st"] * xs) / g["ct"], color=AXIS, lw=0.6, zorder=4)
    straight_outline(ax, g, xw)
    xc = 0.5 * (xw[0] + xw[1])
    yb = g["y0"] + (g["out"][0] + g["st"] * xc) / g["ct"]
    ax.annotate("", (xc - g["st"] * g["d"] * 2, yb + g["ct"] * g["d"] * 2),
                (xc - g["st"] * g["d"] * 3, yb + g["ct"] * g["d"] * 3),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9, shrinkA=0, shrinkB=0))
    ax.text(xc - g["st"] * g["d"] * 2.5 + 30, yb + g["ct"] * g["d"] * 2.5 - 10, "δ = 44.7 m", fontsize=8.5, color=INK,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9), zorder=7)
    title(ax, T("(b) セルの中心は間隔 δ の列に並ぶ(川幅 120 m)", "(b) Cell centres lie on rows δ apart (120 m wide)"))
    save(fig, "setup.png")


# ------------------------------------------------------------------ 図 2: 表し方の一覧
def fig_reps():
    va, vo, vm = A.results("axis"), A.results("oblique"), A.results("mask")
    fig, axs = plt.subplots(3, 5, figsize=(10.0, 6.6))
    rows = [[("a00", 60.0, "sub1"), ("a00", 140.0, "lo"), ("a00", 140.0, "hi"), ("a00", 140.0, "mix"),
             ("a00", 140.0, "split")],
            [("a27", 120.0, "lo"), ("a27", 120.0, "hi"), ("a27", 120.0, "mix"), ("a27", 120.0, "split"),
             ("a27", 120.0, "k2")],
            [("a27", 120.0, "k2w"), ("a27", 60.0, "d8"), ("a27", 60.0, "st4"), ("a27", 120.0, "fine"), None]]
    for r, row in enumerate(rows):
        for c, spec in enumerate(row):
            ax = axs[r, c]
            if spec is None:
                ax.axis("off")
                continue
            an, b, rep = spec
            if rep in ("d8", "st4"):
                v = rel(vm, f"mask_{an}_b{int(b):04d}_{rep}")
            elif an == "a00":
                v = rel(va, f"axis_b{int(b):04d}_{rep}")
            else:
                v = rel(vo, f"obl_{an}_b{int(b):04d}_{rep}")
            dx = mc.DXF if rep == "fine" else mc.DX
            lab = f"{REPS[rep]}\n{mc.ANGLE_DEG[an]:.1f}°" + T(f"・川幅 {b:.0f} m", f", {b:.0f} m wide")
            thumb(axs[r, c], an, b, rep, dx=dx, label=lab, value=v)
    # 凡例(色の意味)
    ax = axs[2, 4]
    for k, (col, txt) in enumerate([("#1757ac", T("解像したセル", "resolved cell")),
                                    ("#9dc8f7", T("サブグリッド河道のセル", "subgrid-channel cell")),
                                    ("#ee7fac", T("段で太らせて足したセル", "cell added at a step")),
                                    (None, T("本当の河道の岸", "true banks"))]):
        y = 0.80 - 0.17 * k
        if col:
            ax.add_patch(plt.Rectangle((0.02, y - 0.05), 0.12, 0.1, transform=ax.transAxes, fc=col, ec="#d0d0d0"))
        else:
            ax.plot([0.02, 0.14], [y, y], color=INK, lw=1.1, transform=ax.transAxes)
        ax.text(0.2, y, txt, transform=ax.transAxes, va="center", fontsize=8.3, color=INK)
    ax.text(0.02, 0.06, T("左下の数字: 通水の幅 ÷ 川幅", "number: conveyance width\n÷ channel width"),
            transform=ax.transAxes, fontsize=8.0, color=INK2)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.01, wspace=0.06, hspace=0.42)
    save(fig, "reps.png")


# ------------------------------------------------------------------ 図 3: 格子に沿う河道
def fig_axis():
    val = A.results("axis")
    if not val:
        return
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    band(ax)
    for rep in ("sub1", "lo", "hi", "mix", "split"):
        xs, ys = [], []
        for b in mc.AXIS_W:
            v = val.get(f"axis_b{int(b):04d}_{rep}")
            if v:
                xs.append(b / mc.DX)
                ys.append(v["rel"])
        line(ax, xs, ys, rep, top=1.8)
    ax.set_ylim(0.0, 1.8)
    ax.set_xlim(0.1, 3.1)
    style(ax, T("川幅 ÷ セル幅 B/Δx", "channel width ÷ cell size B/Δx"), YLAB)
    legend(fig, ax, ncol=3, y=1.0)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.84, bottom=0.13)
    save(fig, "axis.png")


# ------------------------------------------------------------------ 図 4: 斜めの河道
def fig_oblique():
    val = A.results("oblique")
    if not val:
        return
    fig, axs = plt.subplots(1, 3, figsize=(11.0, 4.3), sharey=True)
    for ax, b in zip(axs, mc.OBL_W):
        band(ax)
        for rep in ("lo", "hi", "mix", "split", "k2", "fine"):
            ys = [rel(val, f"obl_{an}_b{int(b):04d}_{rep}") for an in ANG]
            if rep == "k2":         # 0° は段がないので、太らせる表し方は解像 n 列と同じ
                ys[0] = rel(val, f"obl_a00_b{int(b):04d}_lo")
            line(ax, ANGX, ys, rep, top=1.6)
        ax.set_ylim(0.0, 1.6)
        ax.set_xticks(ANGX)
        ax.set_xticklabels([f"{a:.0f}" if a in (0, 45) else f"{a:.1f}" for a in ANGX])
        style(ax, T("格子の軸からの向き (°)", "angle from the grid axis (°)"), YLAB if b == mc.OBL_W[0] else None)
        title(ax, T(f"川幅 {b:.0f} m({b / mc.DX:.1f} セル)", f"{b:.0f} m wide ({b / mc.DX:.1f} cells)"))
    legend(fig, axs[0], ncol=3 if EN else 6, y=1.0)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.78 if EN else 0.82, bottom=0.13, wspace=0.08)
    save(fig, "oblique.png")


# ------------------------------------------------------------------ 図 5: くびれ
def fig_waists():
    val = A.results("oblique")
    if not val:
        return
    angs = ANG[1:]
    reps = ("lo", "hi", "k2")
    fig, axs = plt.subplots(len(reps), len(angs), figsize=(10.0, 6.0))
    for r, rep in enumerate(reps):
        for c, an in enumerate(angs):
            ax = axs[r, c]
            thumb(ax, an, 120.0, rep, value=rel(val, f"obl_{an}_b0120_{rep}"), size=(900.0, 700.0))
            if r == 0:
                ax.set_title(f"{mc.ANGLE_DEG[an]:.1f}°", fontsize=9, color=INK)
            if c == 0:
                ax.set_ylabel(REPS[rep], fontsize=8.5, color=INK)
    fig.suptitle(T("川幅 120 m(1.2 セル)の帯の形。左下の数字は通水の幅 ÷ 川幅",
                   "Band shapes for a 120 m (1.2-cell) channel. Number: conveyance width ÷ width"),
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.subplots_adjust(left=0.04, right=0.99, top=0.9, bottom=0.01, wspace=0.05, hspace=0.08)
    save(fig, "waists.png")


# ------------------------------------------------------------------ 図 6: 1 セル幅の河道マスク
def fig_mask():
    val = A.results("mask")
    if not val:
        return
    fig = plt.figure(figsize=(10.0, 4.6))
    shades = ["#84b9f3", "#338ced", "#1b64be", "#0e3d7e"]       # 幅の順(青の濃淡)
    marks = ["o", "s", "D", "^"]
    axs = [fig.add_axes([0.07, 0.13, 0.30, 0.68]), fig.add_axes([0.42, 0.13, 0.30, 0.68])]
    for ax, rep in zip(axs, ("d8", "st4")):
        band(ax)
        for b, col, m in zip(mc.MASK_W, shades, marks):
            ys = [rel(val, f"mask_{an}_b{int(b):04d}_{rep if an != 'a00' else 'd8'}") for an in ANG]
            lab = T(f"川幅 {b / mc.DX:.1f} セル", f"{b / mc.DX:.1f} cell wide")
            line(ax, ANGX, ys, rep, label=lab, color=col, marker=m, top=2.8)
        ax.set_ylim(0.4, 2.8)
        ax.set_xticks(ANGX)
        ax.set_xticklabels([f"{a:.0f}" if a in (0, 45) else f"{a:.1f}" for a in ANGX])
        style(ax, T("向き (°)", "angle (°)"), YLAB if rep == "d8" else None)
        title(ax, T("(a) 1 列に 1 セル(8 連結)", "(a) one cell per column (8-connected)") if rep == "d8" else
              T("(b) 4 連結の階段", "(b) 4-connected staircase"))
    h, lab = axs[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", bbox_to_anchor=(0.4, 1.0), ncol=4, frameon=False, fontsize=8.5)
    for k, rep in enumerate(("d8", "st4")):
        ax = fig.add_axes([0.76, 0.50 - 0.46 * k, 0.23, 0.33])
        thumb(ax, "a27", 60.0, rep, value=rel(val, f"mask_a27_b0060_{rep}"), size=(900.0, 560.0))
        ax.set_title(f"({'cd'[k]}) " + REPS[rep] + T("\n26.6°・川幅 0.6 セル", "\n26.6°, 0.6 cell wide"),
                     fontsize=8.3, color=INK, loc="left")
    save(fig, "mask.png")


# ------------------------------------------------------------------ 図 7: 広い川
def fig_wide():
    vw, vo = A.results("wide"), A.results("oblique")
    if not vw:
        return
    fig = plt.figure(figsize=(11.0, 4.3))
    axs = [fig.add_axes([0.055, 0.13, 0.27, 0.67]), fig.add_axes([0.37, 0.13, 0.27, 0.67]),
           fig.add_axes([0.72, 0.13, 0.27, 0.67])]
    for ax, b, bf in zip(axs[:2], mc.WIDE_W, (120.0, 200.0)):
        band(ax)
        for rep in ("lo", "hi", "mix"):
            line(ax, ANGX, [rel(vw, f"wide_{an}_b{int(b):04d}_{rep}") for an in ANG], rep, top=1.3)
        line(ax, ANGX, [rel(vo, f"obl_{an}_b{int(bf):04d}_fine") for an in ANG], "fine",
             label=T("Δx = 20 m(同じセル数)", "Δx = 20 m (same number of cells)"))
        ax.set_ylim(0.8, 1.3)
        ax.set_xticks(ANGX)
        ax.set_xticklabels([f"{a:.0f}" if a in (0, 45) else f"{a:.1f}" for a in ANGX])
        style(ax, T("向き (°)", "angle (°)"), YLAB if b == mc.WIDE_W[0] else None)
        title(ax, T(f"({'ab'[mc.WIDE_W.index(b)]}) 川幅 {b / mc.DX:.0f} セル", f"({'ab'[mc.WIDE_W.index(b)]}) "
                    f"{b / mc.DX:.0f} cells wide"))
    h, lab = axs[0].get_legend_handles_labels()
    nc = 2 if EN else 4
    fig.legend(rowmajor(h, nc), rowmajor(lab, nc), loc="upper center", bbox_to_anchor=(0.35, 1.0), ncol=nc,
               frameon=False, fontsize=8.5)
    # (c) 失われる幅 = 表した面積の幅 − 通水の幅(セル)
    ax = axs[2]
    ax.axhline(0.0, color=AXIS, lw=1.0)
    sets = [("wide_{an}_b0600_lo", 600.0, mc.DX, "#338ced", "o", T("Δx = 100 m・6 セル", "Δx = 100 m, 6 cells"), vw),
            ("wide_{an}_b1000_lo", 1000.0, mc.DX, "#0e3d7e", "s", T("Δx = 100 m・10 セル", "Δx = 100 m, 10 cells"), vw),
            ("obl_{an}_b0120_fine", 120.0, mc.DXF, "#9c9c9c", "o", T("Δx = 20 m・6 セル", "Δx = 20 m, 6 cells"), vo),
            ("obl_{an}_b0200_fine", 200.0, mc.DXF, "#666666", "s", T("Δx = 20 m・10 セル", "Δx = 20 m, 10 cells"), vo)]
    for pat, b, dx, col, m, lab, val in sets:
        ys = []
        for an in ANG:
            v = val.get(pat.format(an=an))
            if v is None:
                ys.append(np.nan)
                continue
            g = mc.straight(an, b, "fine" if dx == mc.DXF else "lo", dx)
            ys.append((g["area"] - v["beff"]) / dx)      # g["area"] は表した面積の幅 (m)
        ax.plot(ANGX, ys, color=col, marker=m, lw=1.6, ms=6.5, mec="white", mew=1.0, label=lab)
    ax.set_xticks(ANGX)
    ax.set_xticklabels([f"{a:.0f}" if a in (0, 45) else f"{a:.1f}" for a in ANGX])
    ax.set_ylim(-0.3, 1.15)
    style(ax, T("向き (°)", "angle (°)"), T("表した面積の幅 − 通水の幅(セル)", "area width − conveyance width (cells)"))
    title(ax, T("(c) 岸の階段で失われる幅(解像 n 列)", "(c) Width lost to the staircase banks"))
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    save(fig, "wide.png")


# ------------------------------------------------------------------ 図 8: 屈曲
def bend_outline(ax, g, b):
    ts = np.linspace(0.0, g["ltot"], 800)
    pts = np.array([mc.centerline_point(g, t) for t in ts])
    for sgn in (-1, 1):
        ax.plot(pts[:, 0] - sgn * b / 2 * pts[:, 3], pts[:, 1] + sgn * b / 2 * pts[:, 2], color=INK, lw=1.1, zorder=5)


def fig_bend():
    val = A.results("bend")
    if not val:
        return
    fig = plt.figure(figsize=(11.0, 6.4))
    thumbs = [(500.0, "lo"), (500.0, "k2"), (1500.0, "lo"), (1500.0, "k2")]
    for k, (r, rep) in enumerate(thumbs):
        ax = fig.add_axes([0.01 + 0.245 * k, 0.53, 0.235, 0.40])
        g = mc.bend(r, mc.BEND_W, rep, mc.DX)
        gg = g["g"]
        xw = (gg["xa"] - 600.0, gg["xc"] + r + 400.0)
        yw = (gg["yc"] - 500.0, gg["ya"] + 400.0)
        base = mc.bend(r, mc.BEND_W, "lo", mc.DX)["width"] if rep != "lo" else None
        raster(ax, g["width"], mc.DX, gg["ly"], xw, yw, base=base)
        bend_outline(ax, gg, mc.BEND_W)
        v = val.get(f"bend_r{int(r):04d}_{rep}")
        if v:
            ax.text(0.03, 0.04, T(f"背水 {100 * v['rise']:+.1f} cm", f"backwater {100 * v['rise']:+.1f} cm"),
                    transform=ax.transAxes, fontsize=8.5, color=INK,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9))
        ax.set_title(f"({'abcd'[k]}) " + T(f"半径 {r:.0f} m・{REPS[rep]}", f"radius {r:.0f} m, {REPS[rep]}"),
                     fontsize=8.5, color=INK, loc="left")
    # (e) 背水の高さと半径
    ax = fig.add_axes([0.07, 0.08, 0.38, 0.33])
    rs = list(mc.BEND_R)
    for rep in ("lo", "k2", "t50s", "all", "fine"):
        ys = [val[f"bend_r{int(r):04d}_{rep}"]["rise"] * 100 if f"bend_r{int(r):04d}_{rep}" in val else np.nan for r in rs]
        lab = REPL[rep] + (T("(= 段で 1 行を共有・50 % 以上を解像)", " (= 1 row shared, ≥ 50 % resolved)")
                           if rep == "lo" else "")
        ax.plot([r / mc.BEND_W for r in rs], ys, color=C[rep], marker=MK[rep], lw=1.6, ms=6.5, mec="white", mew=1.0,
                label=lab, zorder=3)
    ax.axhline(0.0, color=AXIS, lw=1.0)
    ax.set_ylim(-2.0, 18.0)
    ax.set_xticks([r / mc.BEND_W for r in rs])
    style(ax, T("曲率半径 ÷ 川幅", "bend radius ÷ channel width"), T("上流の直線区間の背水 (cm)", "backwater upstream (cm)"))
    title(ax, T("(e) 屈曲の上流の水位の上がり(等流の水位から)", "(e) Rise of the level upstream of the bend"))
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    # (f) 中心線に沿う水位(半径 500 m)
    ax = fig.add_axes([0.56, 0.08, 0.42, 0.33])
    for rep in ("lo", "k2", "t50s", "all", "fine"):
        name = f"bend_r0500_{rep}"
        if name not in val:
            continue
        dx = mc.DXF if rep == "fine" else mc.DX
        g = mc.bend(500.0, mc.BEND_W, rep, dx)
        e = A.load_e(name, A.last_out(dict(rep=rep)))
        chan = g["width"] > 0
        dev = e - (mc.Z0 - mc.S * g["s"] + mc.hn(mc.QB))
        edges = np.arange(0.0, g["g"]["ltot"] + 200.0, 200.0)
        mid, mean = [], []
        for a, b2 in zip(edges[:-1], edges[1:]):
            sel = chan & (g["s"] >= a) & (g["s"] < b2)
            if sel.any():
                mid.append(0.5 * (a + b2) / 1000.0)
                mean.append(100.0 * float(dev[sel].mean()))
        ax.plot(mid, mean, color=C[rep], lw=1.6, label=REPS[rep])
    gg = mc.bend_geom(500.0)
    ax.axvspan(gg["l1"] / 1000.0, (gg["l1"] + gg["larc"]) / 1000.0, color=BAND, lw=0, zorder=0)
    ax.text((gg["l1"] + 0.5 * gg["larc"]) / 1000.0, 0.97, T("屈曲", "bend"), transform=ax.get_xaxis_transform(),
            ha="center", va="top", fontsize=8, color=INK2)
    ax.axhline(0.0, color=AXIS, lw=1.0)
    style(ax, T("中心線の距離 (km)", "distance along the centreline (km)"),
          T("等流の水位からの差 (cm)", "level above uniform flow (cm)"))
    title(ax, T("(f) 中心線に沿う水位(半径 500 m)", "(f) Level along the centreline (radius 500 m)"))
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    save(fig, "bend.png")


# ------------------------------------------------------------------ 図 9: 河道の脇の水
def fig_wet():
    val = A.results("wet")
    if not val:
        return
    fig = plt.figure(figsize=(10.5, 4.4))
    # (a) 横断の模式図(5 つの構成)
    ax = fig.add_axes([0.01, 0.06, 0.48, 0.84])
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.4, 10.2)
    ax.axis("off")
    labels = [("dry", T("地形の河岸・乾いている", "terrain banks, dry")),
              ("rain", T("地形の河岸・雨の水膜(1〜2 cm)", "terrain banks, rain film (1–2 cm)")),
              ("wall_dry", T("仮想壁面・乾いている", "virtual walls, dry")),
              ("wall_rain", T("仮想壁面・雨(壁の向こうに 16 cm)", "virtual walls, rain (16 cm behind)")),
              ("wall_pond", T("仮想壁面・壁の向こうに湛水 1.5 m", "virtual walls, 1.5 m pond behind"))]
    for k, (var, lab) in enumerate(labels):
        y0 = 8.2 - 2.0 * k
        wall = var.startswith("wall")
        ground = "#c9b79c"
        # 河道(中央)と河岸・堤内地
        ax.fill([3.0, 3.0, 4.6, 4.6], [y0, y0 + 0.45, y0 + 0.45, y0], color="#9dc8f7", lw=0)   # 河道の水
        ax.plot([3.0, 4.6], [y0, y0], color="#7a6a55", lw=1.2)
        if wall:
            for xw in (3.0, 4.6):
                ax.plot([xw, xw], [y0, y0 + 1.1], color=INK, lw=2.0)
            for xs, xe in ((1.6, 3.0), (4.6, 6.0)):
                ax.fill([xs, xs, xe, xe], [y0 + 0.0, y0 + 0.2, y0 + 0.2, y0 + 0.0], color=ground, lw=0)
                if var == "wall_pond":
                    ax.fill([xs, xs, xe, xe], [y0 + 0.2, y0 + 0.62, y0 + 0.62, y0 + 0.2], color="#cce3fd", lw=0)
                elif var == "wall_rain":
                    ax.fill([xs, xs, xe, xe], [y0 + 0.2, y0 + 0.28, y0 + 0.28, y0 + 0.2], color="#84b9f3", lw=0)
        else:
            for xs, xe, s_ in ((1.6, 3.0, -1), (4.6, 6.0, 1)):
                xa, xb = (xe, xs) if s_ < 0 else (xs, xe)
                ax.fill([xa, xa, xb, xb], [y0, y0 + 0.6, y0 + 0.75, y0], color=ground, lw=0)
                if var == "rain":
                    ax.plot([xa, xb], [y0 + 0.64, y0 + 0.79], color="#338ced", lw=2.0)
        ax.text(6.3, y0 + 0.3, lab, fontsize=8.5, color=INK, va="center")
        ax.text(0.0, y0 + 0.3, f"({k + 1})", fontsize=8.5, color=INK2, va="center")
    ax.set_title(T("(a) 河道(26.6°・川幅 200 m を段で 2 行を共有する帯)の脇", "(a) What lies beside the channel "
                   "(26.6°, 200 m, 2 rows shared at steps)"), fontsize=9.5, color=INK, loc="left")
    # (b) 通水の幅 ÷ 川幅
    ax = fig.add_axes([0.60, 0.13, 0.38, 0.72])
    ys = np.arange(len(labels))[::-1]
    vals = [val[f"wet_{var}"]["rel"] if f"wet_{var}" in val else np.nan for var, _ in labels]
    ax.axvspan(0.9, 1.1, color=BAND, lw=0, zorder=0)
    ax.axvline(1.0, color=AXIS, lw=1.0, zorder=0.5)
    ax.hlines(ys, 0.85, vals, color=GRID, lw=1.0, zorder=1)
    ax.plot(vals, ys, "o", ms=8, color="#257de0", mec="white", mew=1.2, zorder=3)
    for y, v in zip(ys, vals):
        ax.text(v + 0.006, y + 0.18, f"{v:.3f}", fontsize=8.5, color=INK)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"({k + 1})" for k in range(len(labels))])
    ax.set_xlim(0.85, 1.1)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=8.5)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel(T("通水の幅 ÷ 川幅(雨は流入した流量を足して数える)",
                    "conveyance width ÷ width (rain counted in the discharge)"), color=INK2, fontsize=9)
    ax.set_title(T("(b) 河道の通水", "(b) Conveyance of the channel"), fontsize=9.5, color=INK, loc="left")
    save(fig, "wet.png")


# ------------------------------------------------------------------ 占有率の作り方
OCC_CLASSES = [(("a00",), T("(a) 格子に沿う川(0°)", "(a) Along a grid axis (0°)")),
               (("a11", "a18", "a27", "a34"), T("(b) 斜めの川(11.3〜33.7°)", "(b) Oblique (11.3–33.7°)")),
               (("a45",), T("(c) 45°", "(c) 45°"))]


def occ_stats(val, angs, b, rep, offs=None):
    """向き angs・ずれ offs の全ケースの 通水の幅 ÷ 川幅 の中央値・最小・最大(計算していない・途切れるケースは除く)"""
    offs = mc.OCC_OFF if offs is None else offs
    v = [val[n]["rel"] for an in angs for o in offs if (n := mc.occ_name(an, b, o, rep)) in val]
    if not v:
        return np.nan, np.nan, np.nan
    return float(np.median(v)), float(min(v)), float(max(v))


def fig_occ_reps():
    vo, vb = A.results("occ"), A.results("bend")
    fig, axs = plt.subplots(2, 4, figsize=(10.0, 5.2))
    blues = matplotlib.colormaps["Blues"]
    # 上の段: 26.6°・川幅 1.2 セル(ずれ 0)
    an, b = "a27", 120.0
    g = mc.straight(an, b, "lo", mc.DX)
    f = mc.occupancy_straight(an, b, g["dn"], mc.DX)
    xw, yw = straight_window(dict(g, out=(-b / 2, b / 2)), (900.0, 640.0))
    gg = dict(g, out=(-b / 2, b / 2))
    for k, rep in enumerate(("f",) + mc.OCC_RULES):
        ax = axs[0, k]
        if rep == "f":
            ny, nx = f.shape
            i0, i1 = max(0, int(xw[0] // mc.DX)), min(nx, int(math.ceil(xw[1] / mc.DX)))
            j0, j1 = max(0, int((g["ly"] - yw[1]) // mc.DX)), min(ny, int(math.ceil((g["ly"] - yw[0]) / mc.DX)))
            xe = np.arange(i0, i1 + 1) * mc.DX
            ye = (g["ly"] - np.arange(j0, j1 + 1) * mc.DX)[::-1]
            ax.pcolormesh(xe, ye, f[j0:j1, i0:i1][::-1, :], cmap=blues, vmin=0, vmax=1, edgecolors="#d0d0d0", linewidth=0.4)
            for jj in range(j0, j1):
                for ii in range(i0, i1):
                    xc, yc = (ii + 0.5) * mc.DX, g["ly"] - (jj + 0.5) * mc.DX
                    inside = xw[0] + 0.3 * mc.DX < xc < xw[1] - 0.3 * mc.DX and yw[0] + 0.3 * mc.DX < yc < yw[1] - 0.3 * mc.DX
                    if f[jj, ii] > 0.004 and inside:   # 窓の端で切れるセルには書かない
                        ax.text(xc, yc, f"{100 * f[jj, ii]:.0f}", ha="center", va="center", fontsize=6.5,
                                color="white" if f[jj, ii] > 0.6 else INK, clip_on=True)
            ax.set_xlim(*xw); ax.set_ylim(*yw); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_color(AXIS)
            straight_outline(ax, gg, xw)
            ax.set_title(T("占有率 f (%)・26.6°・川幅 1.2 セル", "covered fraction f (%), 26.6°, 1.2 cells"),
                         fontsize=8.3, color=INK, pad=3)
            continue
        g2 = mc.straight(an, b, rep, mc.DX)
        raster(ax, g2["width"], mc.DX, g2["ly"], xw, yw)
        straight_outline(ax, gg, xw)
        v = vo.get(mc.occ_name(an, b, 0.0, rep))
        if v:
            ax.text(0.03, 0.04, f"{v['rel']:.2f}", transform=ax.transAxes, fontsize=8.5, color=INK,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9), zorder=6)
        ax.set_title(REPS[rep], fontsize=8.3, color=INK, pad=3)
    # 下の段: 屈曲(半径 500 m)
    r = 500.0
    gb = mc.bend(r, mc.BEND_W, "lo", mc.DX)
    geo = gb["g"]
    xw = (geo["xa"] - 600.0, geo["xc"] + r + 400.0)
    yw = (geo["yc"] - 500.0, geo["ya"] + 400.0)
    ny, nx = gb["width"].shape
    X = (np.arange(nx)[None, :] + 0.5) * mc.DX + np.zeros((ny, 1))
    Y = geo["ly"] - (np.arange(ny)[:, None] + 0.5) * mc.DX + np.zeros((1, nx))
    fb = mc.occupancy_bend(geo, mc.BEND_W, mc.DX, X, Y, gb["dn"])
    fine = vb.get(f"bend_r{int(r):04d}_fine")
    for k, rep in enumerate(("f",) + mc.OCC_RULES):
        ax = axs[1, k]
        if rep == "f":
            i0, i1 = max(0, int(xw[0] // mc.DX)), min(nx, int(math.ceil(xw[1] / mc.DX)))
            j0, j1 = max(0, int((geo["ly"] - yw[1]) // mc.DX)), min(ny, int(math.ceil((geo["ly"] - yw[0]) / mc.DX)))
            xe = np.arange(i0, i1 + 1) * mc.DX
            ye = (geo["ly"] - np.arange(j0, j1 + 1) * mc.DX)[::-1]
            ax.pcolormesh(xe, ye, fb[j0:j1, i0:i1][::-1, :], cmap=blues, vmin=0, vmax=1, edgecolors="#d0d0d0",
                          linewidth=0.4)
            ax.set_xlim(*xw); ax.set_ylim(*yw); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_color(AXIS)
            bend_outline(ax, geo, mc.BEND_W)
            ax.set_title(T("占有率 f・屈曲(半径 500 m)", "covered fraction f, bend (radius 500 m)"), fontsize=8.3,
                         color=INK, pad=3)
            continue
        g2 = mc.bend(r, mc.BEND_W, rep, mc.DX)
        raster(ax, g2["width"], mc.DX, geo["ly"], xw, yw)
        bend_outline(ax, geo, mc.BEND_W)
        v = vb.get(f"bend_r{int(r):04d}_{rep}")
        if v and fine:
            ax.text(0.03, 0.04, T(f"背水の差 {100 * (v['rise'] - fine['rise']):+.1f} cm",
                                  f"backwater diff. {100 * (v['rise'] - fine['rise']):+.1f} cm"),
                    transform=ax.transAxes, fontsize=8.3, color=INK,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9), zorder=6)
        ax.set_title(REPS[rep], fontsize=8.3, color=INK, pad=3)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.01, wspace=0.06, hspace=0.18)
    save(fig, "occ_reps.png")


def fig_occ():
    val, vm = A.results("occ"), A.results("mask")
    if not val:
        return
    xs = [b / mc.DX for b in mc.OCC_W]
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 4.6), sharey=True)
    for ax, (angs, ttl) in zip(axs, OCC_CLASSES):
        band(ax)
        for rep in mc.OCC_RULES:
            # 閾値だけの作り方は、川幅 1 セル未満では河道マスクが途切れるケースが多いので描かない
            st = np.array([occ_stats(val, angs, b, rep) if (rep != "t50" or b > mc.DX) else (np.nan,) * 3
                           for b in mc.OCC_W])
            ax.fill_between(xs, st[:, 1], st[:, 2], color=C[rep], alpha=0.12, lw=0, zorder=1)
            line(ax, xs, st[:, 0], rep, top=2.0)
        d8 = [np.median([vm[n]["rel"] for an in angs if (n := f"mask_{an}_b{int(b):04d}_d8") in vm] or [np.nan])
              for b in mc.MASK_W]
        ax.plot([b / mc.DX for b in mc.MASK_W], d8, color=INK2, lw=1.4, ls="--", marker="o", ms=5, mec="white",
                mew=1.0, zorder=3, label=T("中心線の 1 列(8 連結)+ 川幅", "one cell per column on the centreline + width"))
        ax.set_xscale("log")
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{x:g}" for x in xs])
        ax.minorticks_off()
        ax.set_ylim(0.3, 2.0)
        style(ax, T("川幅 ÷ セル幅 B/Δx", "channel width ÷ cell size B/Δx"), YLAB if angs == ("a00",) else None)
        title(ax, ttl)
    legend(fig, axs[0], ncol=2 if EN else 4, y=1.0)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.80 if EN else 0.84, bottom=0.13, wspace=0.08)
    save(fig, "occ.png")


def fig_occ_sens():
    val = A.results("occ")
    if not val:
        return
    ws = mc.OCC_SENS_W
    xs = np.array([b / mc.DX for b in ws])
    angs = ("a11", "a18", "a27", "a34")
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.3), sharey=True)
    groups = [
        [("t30s", T("閾値 30 %", "threshold 30 %"), "#f5a3a3", "v"), ("t50s", T("閾値 50 %", "threshold 50 %"), C["t50s"], "s"),
         ("t70s", T("閾値 70 %", "threshold 70 %"), "#8f1d1d", "^")],
        [("t50s_c0", T("50 % + 残り・下限なし", "50 % + rest, no cutoff"), "#f5a3a3", "v"),
         ("t50s", T("50 % + 残り・下限 5 %", "50 % + rest, cutoff 5 %"), C["t50s"], "s"),
         ("t50s_c15", T("50 % + 残り・下限 15 %", "50 % + rest, cutoff 15 %"), "#8f1d1d", "^"),
         ("all_c0", T("全セル・下限なし", "all cells, no cutoff"), "#7fcf8b", "v"),
         ("all", T("全セル・下限 5 %", "all cells, cutoff 5 %"), C["all"], "D"),
         ("all_c15", T("全セル・下限 15 %", "all cells, cutoff 15 %"), "#00500d", "^")]]
    for ax, grp, ttl in zip(axs, groups, (T("(a) 解像にする閾値", "(a) Threshold for resolved cells"),
                                          T("(b) 河道にする占有率の下限", "(b) Cutoff of the covered fraction"))):
        band(ax)
        n = len(grp)
        for k, (rep, lab, col, m) in enumerate(grp):
            st = np.array([occ_stats(val, angs, b, rep, offs=(0.0,)) for b in ws])
            dx_ = xs * (1.0 + 0.035 * (k - (n - 1) / 2))
            ax.errorbar(dx_, st[:, 0], yerr=[st[:, 0] - st[:, 1], st[:, 2] - st[:, 0]], fmt=m, color=col, ms=6.5,
                        mec="white", mew=1.0, elinewidth=1.4, capsize=0, label=lab, zorder=3)
        ax.set_xscale("log")
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{x:g}" for x in xs])
        ax.minorticks_off()
        ax.set_ylim(0.7, 1.4)
        style(ax, T("川幅 ÷ セル幅 B/Δx", "channel width ÷ cell size B/Δx"), YLAB if ax is axs[0] else None)
        title(ax, ttl)
        ax.legend(frameon=False, fontsize=7.8, loc="upper right", ncol=1 if ax is axs[0] else 2)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.9, bottom=0.13, wspace=0.06)
    save(fig, "occ_sens.png")


# ------------------------------------------------------------------ 下限を上げる作り方(氾濫原の面積と河道の通水)
OBL = ("a11", "a18", "a27", "a34")
FMIN_RULES = [("all", 5), ("all_c15", 15), ("all_c30", 30), ("all_c50", 50)]
FMIN_SHOW = (120.0, 200.0, 300.0, 600.0)
FMIN_COL = {120.0: "#f47230", 200.0: "#257de0", 300.0: "#00b894", 600.0: "#6a4ce2"}


def fmin_values():
    """fmin 系列と、同じ名前の occ 系列のケース(下限 5 % の all、閾値だけの t50)の結果"""
    val = A.results("occ")
    val.update(A.results("fmin"))
    return val


def fmin_area(angs, b, rep):
    """向き angs・ずれ 3 つの面積の勘定の平均(fp_bias はセル幅、ch_bias は割合)と、fp_bias の最小・最大"""
    a = [A.occ_area(an, b, o, rep) for an in angs for o in mc.OCC_OFF]
    fb = [x["fp_bias"] for x in a]
    return float(np.mean(fb)), float(min(fb)), float(max(fb)), float(np.mean([x["ch_bias"] for x in a]))


def fig_fmin():
    val = fmin_values()
    if not any(n.endswith("_c30") for n in val):
        return
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.3))
    xs = np.array([c for _, c in FMIN_RULES], dtype=float)
    for k, b in enumerate(FMIN_SHOW):
        col = FMIN_COL[b]
        sh = 1.2 * (k - (len(FMIN_SHOW) - 1) / 2)
        st = np.array([occ_stats(val, OBL, b, r) for r, _ in FMIN_RULES])
        lab = T(f"川幅 {b / mc.DX:g} セル", f"{b / mc.DX:g} cells wide")
        axs[0].plot(xs + sh, st[:, 0], "-", color=col, lw=1.4, zorder=2)
        axs[0].errorbar(xs + sh, st[:, 0], yerr=[st[:, 0] - st[:, 1], st[:, 2] - st[:, 0]], fmt="o", color=col, ms=6,
                        mec="white", mew=1.0, elinewidth=1.4, capsize=0, label=lab, zorder=3)
        md, lo, hi = occ_stats(val, OBL, b, "t50")
        axs[0].errorbar([58.0 + sh], [md], yerr=[[md - lo], [hi - md]], fmt="o", color=col, mfc="white", ms=6, mew=1.4,
                        elinewidth=1.0, capsize=0, zorder=3)
        ar = np.array([fmin_area(OBL, b, r)[:3] for r, _ in FMIN_RULES])
        axs[1].plot(xs + sh, ar[:, 0], "-", color=col, lw=1.4, zorder=2)
        axs[1].errorbar(xs + sh, ar[:, 0], yerr=[ar[:, 0] - ar[:, 1], ar[:, 2] - ar[:, 0]], fmt="o", color=col, ms=6,
                        mec="white", mew=1.0, elinewidth=1.4, capsize=0, label=lab, zorder=3)
    band(axs[0])
    axs[0].set_xticks(list(xs) + [58.0])
    axs[0].set_xticklabels([f"{c:g} %" for c in xs] + [T("閾値\n50 %", "threshold\n50 %")])
    axs[0].set_xlim(0, 65)
    axs[1].axhline(0.0, color=AXIS, lw=1.0, zorder=1)
    axs[1].set_xticks(xs)
    axs[1].set_xticklabels([f"{c:g} %" for c in xs])
    axs[1].set_xlim(0, 57)
    axs[0].set_ylim(0.35, 1.12)
    style(axs[0], T("河道にする占有率の下限(幅は占有率 × セル幅)", "cutoff of the covered fraction (width = fraction × cell)"), YLAB)
    style(axs[1], T("河道にする占有率の下限", "cutoff of the covered fraction"),
          T("氾濫原の幅の偏り(セル幅。両岸の合計)", "error in floodplain width (cells, both banks)"))
    title(axs[0], T("(a) 河道の通水(斜めの川 11.3〜33.7°)", "(a) Conveyance of the channel (oblique, 11.3–33.7°)"))
    title(axs[1], T("(b) 氾濫原の面積(同じケース。閾値 50 % は下限 50 % と同じ)",
                    "(b) Floodplain area (same cases; threshold 50 % = cutoff 50 %)"))
    axs[0].legend(frameon=False, fontsize=7.8, loc="lower left")
    axs[0].text(58.0, 1.085, T("白: 解像", "open: resolved"), fontsize=7.5, color=INK2, ha="center")
    fig.subplots_adjust(left=0.07, right=0.99, top=0.9, bottom=0.17, wspace=0.22)
    save(fig, "fmin.png")


# ------------------------------------------------------------------ 数表
def tables():
    vo, va, vw, vm, vb, vt = (A.results(s) for s in ("oblique", "axis", "wide", "mask", "bend", "wet"))

    def f(v, d=2):
        return "—" if v is None or not np.isfinite(v) else f"{v:.{d}f}"

    if va:
        print(T("== 格子に沿う河道(通水の幅 ÷ 川幅)", "== Along a grid axis (conveyance width ÷ width)"))
        print("| B/Δx | " + " | ".join(REPL[r] for r in ("sub1", "lo", "hi", "mix", "split")) + " |")
        print("|---:|" + "---:|" * 5)
        for b in mc.AXIS_W:
            print(f"| {b / mc.DX:.1f} | " + " | ".join(f(rel(va, f"axis_b{int(b):04d}_{r}")) for r in
                                                       ("sub1", "lo", "hi", "mix", "split")) + " |")
        print()
    if vo:
        for b in mc.OBL_W:
            print(T(f"== 斜めの河道・川幅 {b:.0f} m", f"== Oblique channel, {b:.0f} m wide"))
            reps = ("lo", "hi", "mix", "split", "k1", "k2", "k2w", "fine")
            print(T("| 向き | ", "| Angle | ") + " | ".join(REPL[r] for r in reps) + " |")
            print("|---|" + "---:|" * len(reps))
            for an in ANG:
                print(f"| {mc.ANGLE_DEG[an]:.1f}° | " + " | ".join(f(rel(vo, f"obl_{an}_b{int(b):04d}_{r}")) for r in reps)
                      + " |")
            print()
    if vw:
        for b in mc.WIDE_W:
            print(T(f"== 広い川・川幅 {b:.0f} m", f"== Wide channel, {b:.0f} m wide"))
            reps = ("lo", "hi", "mix", "k1", "k2")
            print(T("| 向き | ", "| Angle | ") + " | ".join(REPL[r] for r in reps) + " |")
            print("|---|" + "---:|" * len(reps))
            for an in ANG:
                print(f"| {mc.ANGLE_DEG[an]:.1f}° | " + " | ".join(f(rel(vw, f"wide_{an}_b{int(b):04d}_{r}")) for r in reps)
                      + " |")
            print()
    if vm:
        print(T("== 1 セル幅の河道マスク(通水の幅 ÷ 川幅。8 連結 / 4 連結)", "== One-cell masks (8-connected / 4-connected)"))
        print(T("| 向き | ", "| Angle | ") + " | ".join(f"{b / mc.DX:.1f}" for b in mc.MASK_W) + " |")
        print("|---|" + "---:|" * len(mc.MASK_W))
        for an in ANG:
            cells = []
            for b in mc.MASK_W:
                d8 = rel(vm, f"mask_{an}_b{int(b):04d}_d8")
                st = rel(vm, f"mask_{an}_b{int(b):04d}_st4")
                cells.append(f(d8) + (" / " + f(st) if np.isfinite(st) else ""))
            print(f"| {mc.ANGLE_DEG[an]:.1f}° | " + " | ".join(cells) + " |")
        print()
    if vb:
        print(T("== 屈曲(上流の直線区間の背水 cm)", "== Bends (backwater upstream, cm)"))
        reps = ("lo", "k1", "k2", "t50", "t50s", "all", "t50s_c0", "all_c0", "t50s_c15", "all_c15", "all_c30",
                "all_c50", "fine")
        vb.update({k: v for k, v in A.results("fmin").items() if k.startswith("bend_")})
        print(T("| 半径 | ", "| Radius | ") + " | ".join(REPL.get(r, r) for r in reps) + " |")
        print("|---|" + "---:|" * len(reps))
        for r in mc.BEND_R:
            print(f"| {r:.0f} m | " + " | ".join(f(100 * vb[f'bend_r{int(r):04d}_{x}']['rise'], 1)
                                                 if f"bend_r{int(r):04d}_{x}" in vb else "—" for x in reps) + " |")
        print()
    vc = A.results("occ")
    if vc:
        print(T("== 占有率で作る河道マスク(通水の幅 ÷ 川幅。中央値 [最小〜最大]。ずれ 3 つ、斜めの川は向き 4 つも込み)",
                "== Masks from the covered fraction (conveyance width ÷ width; median [min–max] over 3 offsets, and the 4 "
                "angles for oblique rivers)"))
        print(T("| 向き | 作り方 | ", "| Angle | Rule | ") + " | ".join(f"{b / mc.DX:g}" for b in mc.OCC_W) + " |")
        print("|---|---|" + "---:|" * len(mc.OCC_W))
        for angs, ttl in OCC_CLASSES:
            lab = {"a00": "0°", "a45": "45°"}.get(angs[0], "11.3〜33.7°" if not EN else "11.3–33.7°")
            for rep in mc.OCC_RULES:
                cells = []
                for b in mc.OCC_W:
                    md, lo, hi = occ_stats(vc, angs, b, rep)
                    cells.append("—" if not np.isfinite(md) else (f"{md:.2f}" if abs(hi - lo) < 0.005 else
                                                                   f"{md:.2f} [{lo:.2f}〜{hi:.2f}]" if not EN else
                                                                   f"{md:.2f} [{lo:.2f}–{hi:.2f}]"))
                print(f"| {lab} | {REPL[rep]} | " + " | ".join(cells) + " |")
        print()
        print(T("== 閾値と下限の感度(ずれ 0、11.3〜33.7°。中央値 [最小〜最大])", "== Threshold and cutoff (offset 0, 11.3–33.7°)"))
        reps = ("t30s", "t50s", "t70s", "t50s_c0", "t50s_c15", "all_c0", "all", "all_c15")
        print("| B/Δx | " + " | ".join(reps) + " |")
        print("|---:|" + "---:|" * len(reps))
        for b in mc.OCC_SENS_W:
            cells = []
            for rep in reps:
                md, lo, hi = occ_stats(vc, ("a11", "a18", "a27", "a34"), b, rep, offs=(0.0,))
                cells.append("—" if not np.isfinite(md) else f"{md:.2f} [{lo:.2f}〜{hi:.2f}]")
            print(f"| {b / mc.DX:g} | " + " | ".join(cells) + " |")
        skipped = os.path.join(mc.RUNS, "skipped_occ.txt")
        if os.path.exists(skipped):
            names = open(skipped).read().split()
            print(T(f"  河道マスクが途切れて作らなかったケース: {len(names)}", f"  cases not made (mask broken): {len(names)}"))
        print()
    vf = A.results("fmin")
    if vf:
        val = fmin_values()
        reps = [r for r, _ in FMIN_RULES] + ["t50"]
        labs = [f"{c} %" for _, c in FMIN_RULES] + [T("閾値 50 % を解像", "threshold 50 %, resolved")]
        print(T("== 河道にする占有率の下限(通水の幅 ÷ 川幅。中央値 [最小〜最大]。ずれ 3 つ、斜めの川は向き 4 つも込み)",
                "== Cutoff of the covered fraction (conveyance width ÷ width; median [min–max] over 3 offsets, and the 4 "
                "angles for oblique rivers)"))
        print(T("| 向き | B/Δx | ", "| Angle | B/Δx | ") + " | ".join(labs) + " |")
        print("|---|---:|" + "---:|" * len(reps))
        for angs, _ in OCC_CLASSES:
            lab = {"a00": "0°", "a45": "45°"}.get(angs[0], "11.3〜33.7°" if not EN else "11.3–33.7°")
            for b in mc.FMIN_W:
                cells = []
                for rep in reps:
                    md, lo, hi = occ_stats(val, angs, b, rep)
                    cells.append("—" if not np.isfinite(md) else (f"{md:.2f}" if abs(hi - lo) < 0.005 else
                                                                   f"{md:.2f} [{lo:.2f}〜{hi:.2f}]" if not EN else
                                                                   f"{md:.2f} [{lo:.2f}–{hi:.2f}]"))
                print(f"| {lab} | {b / mc.DX:g} | " + " | ".join(cells) + " |")
        print()
        print(T("== 面積の勘定(斜めの川 11.3〜33.7°、ずれ 3 つの平均。氾濫原の幅の偏りはセル幅で両岸の合計、"
                "河道の面積は表した ÷ 本当 − 1)",
                "== Area accounting (oblique 11.3–33.7°, mean over 3 offsets; floodplain width error in cells, both "
                "banks; channel area = represented ÷ true − 1)"))
        print("| B/Δx | " + " | ".join(labs) + " |")
        print("|---:|" + "---:|" * len(reps))
        for b in mc.FMIN_W:
            cells = []
            for rep in reps:
                fb, _, _, cb = fmin_area(OBL, b, rep)
                cells.append(f"{fb:+.2f} / {100 * cb:+.0f} %")
            print(f"| {b / mc.DX:g} | " + " | ".join(cells) + " |")
        print()
    if vt:
        print(T("== 河道の脇の水", "== Water beside the channel"))
        for name, v in vt.items():
            print(f"  {name:14s} rel {v['rel']:.3f}  h {v['h']:.3f} m  I/I0 {v['slope']:.4f}  q {v['q']:.1f}  "
                  f"h_bank {v['hbank']:.4f}  h_near {v['hnear']:.4f}")


def main():
    print(T("図:", "Figures:"))
    fig_setup()
    fig_reps()
    fig_axis()
    fig_oblique()
    fig_waists()
    fig_mask()
    fig_wide()
    fig_bend()
    fig_wet()
    fig_occ_reps()
    fig_occ()
    fig_occ_sens()
    fig_fmin()
    print()
    tables()


if __name__ == "__main__":
    main()
