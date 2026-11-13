#!/usr/bin/env python3
"""delta のケースを並べた比較の図と指標(各ケースを計算した後に実行する)。

  python3 plot_compare.py [en]            # 下の全部(結果のあるものだけ)
  python3 plot_compare.py sandmud [en]    # 段 2: figs/sandmud.png・sandmud_timeseries.png と数表(sand・mud)
  python3 plot_compare.py fixation [en]   # 段 3: figs/fixation.png と数表(varq・fixstrong・fix)
  python3 plot_compare.py wave [en]       # 段 4: figs/wave_cmp.png と数表(baseqb・wave_lsm0・wave)
  python3 plot_compare.py ensemble [en]   # 実現ごとの違い: figs/ensemble.png と数表(make ens の 6 実現)
  python3 plot_compare.py table [en]      # 指標の数表だけ(全ケースの最終の出力)

引数 en で英語ラベルの図を en/figs/ に書く。

指標の定義(README「結果」の冒頭と同じ。河口 = 海岸線 x = LCH 上の河道の中心):
  陸化        河口より沖(x > LCH)で水深 h < 0.05 m のセルの面積
  最大半径 R  河口から最も遠い陸のセル(上と同じ判定)の中心までの距離
  汀線半径    河口から沖へ引いた方位ごと(−89.5〜89.5°、1° おき)の線で、最も遠い陸のセルまでの距離。
              陸のない方位を除いた平均と標準偏差(標準偏差 / 平均 = 凹凸比)
  分流路の本数 河口を中心とする半径 0.5 R・0.8 R の円弧に沿って、両側を陸にはさまれた水(h ≥ 0.05 m)の
              セルの連なりのうち、流速 |V| が V_CH 以上のセルを含むもの(水たまりを除く)の数。幅は連なりの
              弧の長さ
"""
import csv
import glob
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EN = "en" in sys.argv[1:]
ARGS = [a for a in sys.argv[1:] if a != "en"]
FIGDIR = "en/figs" if EN else "figs"


def T(ja, en):
    return en if EN else ja


if not EN:
    import matplotlib.font_manager as fm
    for f in ("IPAPGothic", "IPAGothic", "Noto Sans CJK JP", "WenQuanYi Zen Hei"):   # 日本語ラベル(plot_results.py と同じ。無ければ既定フォント)
        if any(x.name == f for x in fm.fontManager.ttflist):
            matplotlib.rcParams["font.family"] = f
            break
matplotlib.rcParams["axes.unicode_minus"] = False

H_LAND, V_CH = 0.05, 0.1                  # 陸の判定の水深 (m)、分流路とみなす流速 (m/s)
PFILE = {"base": "param.txt"}


def pfile(case):
    return PFILE.get(case, "param_%s.txt" % case)


class Case:
    """1 ケースの結果(出力の番号と時刻、地形の諸元)。"""

    def __init__(self, case):
        self.case = case
        self.d = "result_%s" % case
        txt = open(pfile(case), encoding="utf-8").read()

        def pget(key, default):
            m = re.search(r"^\s*%s\s*=\s*([0-9.eE+-]+)" % key, txt, re.M)
            return float(m.group(1)) if m else default
        self.txt = txt
        self.dx = pget("lx", 1000.0) / pget("nx", 200.0)
        self.morfac = pget("morfac", 100.0)
        dt_file = pget("dt_file", 3600.0)
        frames = []
        fn = os.path.join(self.d, "FILENUMBER.csv")
        if os.path.exists(fn):
            for row in csv.reader(open(fn)):
                if row[0].startswith("#"):
                    continue
                n, t = int(row[0]), float(row[2])
                if n < 9000:
                    frames.append((n, t))
        if not frames:                    # 計算の途中: Z ファイルの連番から
            frames = [(int(os.path.basename(f)[1:5]), int(os.path.basename(f)[1:5]) * dt_file)
                      for f in sorted(glob.glob(os.path.join(self.d, "Z[0-9][0-9][0-9][0-9].txt")))
                      if int(os.path.basename(f)[1:5]) < 9000]
        self.frames = frames
        self.z0 = self.load("Z", 0)
        self.ny, self.nx = self.z0.shape
        self.lch = self._lch()
        self.xc = (np.arange(self.nx) + 0.5) * self.dx
        self.yc = (np.arange(self.ny) + 0.5) * self.dx
        self.mouth = (self.lch, self.ny * self.dx / 2.0)

    def _lch(self):
        # 陸の地盤高(西側の非侵食の陸 +1.5 m)が続く列の数 = 河道の長さ
        land = np.isclose(self.z0[0], 1.5)
        return self.dx * int(np.argmin(land)) if not land.all() else self.nx * self.dx

    def load(self, pfx, n):
        return np.loadtxt(os.path.join(self.d, "%s%04d.txt" % (pfx, n)))

    def morph_h(self, t):
        return t * self.morfac / 3600.0

    def frame_at(self, th):
        """地形時間 th (h) に最も近い出力。"""
        return min(self.frames, key=lambda f: abs(self.morph_h(f[1]) - th))


def metrics(c, n):
    """出力 n の指標(陸化・R・汀線半径・分流路の本数と幅・堆積)。"""
    h = c.load("H", n)
    z = c.load("Z", n)
    vpath = os.path.join(c.d, "V%04d.txt" % n)
    v = np.loadtxt(vpath) if os.path.exists(vpath) else None
    X, Y = np.meshgrid(c.xc, c.yc)
    sea = X > c.lch
    land = (h < H_LAND) & sea
    out = {"area": land.sum() * c.dx * c.dx}
    dz = z - c.z0
    out["dep"] = dz[dz > 0].sum() * c.dx * c.dx
    mx, my = c.mouth
    dist = np.hypot(X - mx, Y - my)
    out["R"] = float(dist[land].max()) if land.any() else 0.0
    # 汀線半径: 方位ごとの最も遠い陸
    rmax = np.hypot(c.nx * c.dx, c.ny * c.dx)
    rs = np.arange(0.5 * c.dx, rmax, 0.5 * c.dx)
    radii = []
    for th in np.deg2rad(np.arange(-89.5, 90.0, 1.0)):
        px, py = mx + rs * np.cos(th), my + rs * np.sin(th)
        ok = (px > 0) & (px < c.nx * c.dx) & (py > 0) & (py < c.ny * c.dx)
        i = (px[ok] / c.dx).astype(int)
        j = (py[ok] / c.dx).astype(int)
        hit = land[j, i]
        if hit.any():
            radii.append(rs[ok][np.nonzero(hit)[0].max()])
    radii = np.array(radii)
    out["rmean"] = float(radii.mean()) if len(radii) else 0.0
    out["rsd"] = float(radii.std()) if len(radii) else 0.0
    # 分流路の本数(円弧 0.5 R・0.8 R)
    for key, fr in (("ch05", 0.5), ("ch08", 0.8)):
        rho = fr * out["R"]
        n_ch, widths = 0, []
        if rho > 2 * c.dx:
            ths = np.arange(-np.pi / 2, np.pi / 2, 0.25 * c.dx / rho)
            px, py = mx + rho * np.cos(ths), my + rho * np.sin(ths)
            ok = (px > 0) & (px < c.nx * c.dx) & (py > 0) & (py < c.ny * c.dx)
            ths, px, py = ths[ok], px[ok], py[ok]
            i, j = (px / c.dx).astype(int), (py / c.dx).astype(int)
            wet = ~land[j, i]
            # 連なり(同じ状態の続く区間)に分ける
            edges = np.nonzero(np.diff(wet.astype(int)))[0] + 1
            seg = np.split(np.arange(len(wet)), edges)
            for k, s in enumerate(seg):
                if not wet[s[0]] or k == 0 or k == len(seg) - 1:
                    continue              # 陸の区間と、円弧の端に接する水(開いた海・海岸沿い)は数えない
                if v is not None and v[j[s], i[s]].max() < V_CH:
                    continue              # 流れのない水たまり
                n_ch += 1
                widths.append((ths[s[-1]] - ths[s[0]]) * rho + c.dx)
        out[key] = n_ch
        out[key + "_w"] = widths
    return out


def fmt_w(ws):
    if not ws:
        return "—"
    return "%.0f〜%.0f m" % (min(ws), max(ws)) if len(ws) > 1 else "%.0f m" % ws[0]


def have(case):
    return os.path.exists("result_%s/Z0000.txt" % case) and os.path.exists(pfile(case))


def dz_panel(ax, c, n, title):
    dz = c.load("Z", n) - c.z0
    h = c.load("H", n)
    ext = [0, c.nx * c.dx, c.ny * c.dx, 0]
    im = ax.imshow(dz, extent=ext, cmap="RdBu_r", vmin=-2, vmax=2)
    ax.contour(c.xc, c.yc, h, levels=[H_LAND], colors="k", linewidths=0.6)
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    return im


def mtitle(lab, m):
    return lab + "\n" + T("陸化 %.0f×10³ m²、最大半径 %.0f m、分流路 %d / %d 本" % (m["area"] / 1e3, m["R"], m["ch05"], m["ch08"]),
                          "land %.0f×10³ m², max radius %.0f m, channels %d / %d" % (m["area"] / 1e3, m["R"], m["ch05"], m["ch08"]))


def row_print(lab, c, n, m):
    print("| %s | %.0f h | %.0f | %.0f | %.0f | %.0f ± %.0f (%.2f) | %d / %d | %s / %s |" % (
        lab, c.morph_h(dict(c.frames)[n]), m["dep"] / 1e3, m["area"] / 1e3, m["R"], m["rmean"], m["rsd"],
        m["rsd"] / m["rmean"] if m["rmean"] else 0.0, m["ch05"], m["ch08"], fmt_w(m["ch05_w"]), fmt_w(m["ch08_w"])))


def header():
    print("| ケース | 地形時間 | 堆積 (10³ m³ かさ) | 陸化 (10³ m²) | 最大半径 R (m) | 汀線半径 平均 ± 標準偏差 (m)(凹凸比) "
          "| 分流路 0.5 R / 0.8 R (本) | 幅 0.5 R / 0.8 R |")
    print("|---|---|---|---|---|---|---|---|")


def compare(cases, th, fname, figsize):
    """cases = [(case, ラベル)] を地形時間 th (h) の堆積厚で並べる。"""
    cs = [(Case(k), lab) for k, lab in cases if have(k)]
    if not cs:
        return
    fig, axs = plt.subplots(1, len(cs), figsize=figsize, constrained_layout=True)
    axs = np.atleast_1d(axs)
    header()
    for ax, (c, lab) in zip(axs, cs):
        n, t = c.frame_at(th)
        m = metrics(c, n)
        row_print(c.case, c, n, m)
        im = dz_panel(ax, c, n, mtitle(lab, m))
    fig.colorbar(im, ax=axs, shrink=0.7, label="Δz (m)")
    fig.savefig(os.path.join(FIGDIR, fname), dpi=100)
    plt.close(fig)
    print()


def sandmud():
    cs = [(k, lab) for k, lab in (("sand", T("砂の多い sand(泥の流入濃度 0.00015)", "sand-rich (mud inflow conc. 0.00015)")),
                                   ("mud", T("泥の多い mud(泥の流入濃度 0.001)", "mud-rich (mud inflow conc. 0.001)"))) if have(k)]
    compare(cs, 4000.0, "sandmud.png", (13, 5.5))
    if not cs:
        return
    fig, axs = plt.subplots(1, 4, figsize=(18, 4), constrained_layout=True)
    for k, lab in cs:
        c = Case(k)
        rows = []
        for n, t in c.frames[1:]:
            m = metrics(c, n)
            rows.append((c.morph_h(t), m["area"] / 1e3, m["R"], m["ch05"], m["rsd"]))
        r = np.array(rows)
        for a, col in zip(axs, (1, 2, 3, 4)):
            a.plot(r[:, 0], r[:, col], "o-", label=lab.split("(")[0])
    for a, yl in zip(axs, (T("陸化 (10³ m²)", "land (10³ m²)"), T("最大半径 R (m)", "max radius R (m)"),
                            T("分流路の本数(0.5 R の円弧)", "channels (arc at 0.5 R)"),
                            T("汀線半径の標準偏差 (m)", "SD of shoreline radius (m)"))):
        a.set_ylabel(yl)
        a.set_xlabel(T("地形時間 (h)", "landform time (h)"))
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    fig.savefig(os.path.join(FIGDIR, "sandmud_timeseries.png"), dpi=100)
    plt.close(fig)


def fixation():
    compare([("varq", T("流量の変動だけ(varq)", "discharge variation only (varq)")),
             ("fixstrong", T("参考: 冠水で弱まらない強い定着(c_τ 10、T_fix 20 h)", "reference: strong fixation not weakened when submerged")),
             ("fix", T("定着+冠水の減衰+河岸の係数+側岸侵食(fix)", "fixation + submerged decay + bank coeff. + bank erosion (fix)"))],
            4000.0, "fixation.png", (18, 5.8))


def wave():
    compare([("baseqb", T("波なし(baseqb)", "no waves (baseqb)")),
             ("wave_lsm0", T("参考: 波あり、汀線の向きをセル半径の核で(wave_lsm = 0)", "reference: waves, shoreline orientation with the cell-radius kernel")),
             ("wave", T("波あり(wave。wave_lsm = 10 m)", "waves (wave; wave_lsm = 10 m)"))],
            1500.0, "wave_cmp.png", (18, 4.6))


def ensemble():
    names = ["ens_w1", "ens_w2", "ens_w3", "ens_w4", "ens_w5", "ens_c1"]
    cs = [Case(k) for k in names if have(k)]
    if not cs:
        return
    fig, axs = plt.subplots(2, 4, figsize=(20, 6.5), constrained_layout=True)
    header()
    dzs, lands = [], []
    for ax, c in zip(axs.flat, cs):
        n, t = c.frame_at(1200.0)
        m = metrics(c, n)
        row_print(c.case, c, n, m)
        lab = c.case.replace("ens_", "") + (T("(相関長 50 m)", " (correlation 50 m)") if c.case == "ens_c1" else "")
        im = dz_panel(ax, c, n, lab + T(": 陸化 %.1f×10³ m²、分流路 %d / %d 本", ": land %.1f×10³ m², channels %d / %d")
                      % (m["area"] / 1e3, m["ch05"], m["ch08"]))
        if c.case != "ens_c1":
            dzs.append(c.load("Z", n) - c.z0)
            lands.append((c.load("H", n) < H_LAND).astype(float))
    print()
    c = cs[0]
    ext = [0, c.nx * c.dx, c.ny * c.dx, 0]
    if dzs:
        ax = axs.flat[6]
        ax.imshow(np.mean(dzs, axis=0), extent=ext, cmap="RdBu_r", vmin=-2, vmax=2)
        ax.contour(c.xc, c.yc, np.mean(lands, axis=0), levels=[0.5], colors="k", linewidths=0.8)
        ax.set_title(T("%d 実現(白色の擾乱)の平均の Δz。黒線 = 陸になる確率 0.5" % len(dzs),
                       "mean Δz of %d realizations (white noise); black = land probability 0.5" % len(dzs)), fontsize=9)
        ax = axs.flat[7]
        im2 = ax.imshow(np.std(dzs, axis=0), extent=ext, cmap="viridis", vmin=0, vmax=1.0)
        ax.set_title(T("実現の間の標準偏差 (m)", "standard deviation between realizations (m)"), fontsize=9)
        fig.colorbar(im2, ax=axs.flat[7], shrink=0.8)
    fig.colorbar(im, ax=axs, shrink=0.6, label="Δz (m)")
    fig.savefig(os.path.join(FIGDIR, "ensemble.png"), dpi=100)
    plt.close(fig)


def table():
    header()
    for p in sorted(glob.glob("param*.txt")):
        k = "base" if p == "param.txt" else p[6:-4]
        if not have(k):
            continue
        c = Case(k)
        if not c.frames:
            continue
        n = c.frames[-1][0]
        row_print(k, c, n, metrics(c, n))
    print()


if __name__ == "__main__":
    os.makedirs(FIGDIR, exist_ok=True)
    todo = ARGS or ["sandmud", "fixation", "wave", "ensemble"]
    for a in todo:
        {"sandmud": sandmud, "fixation": fixation, "wave": wave, "ensemble": ensemble, "table": table}[a]()
