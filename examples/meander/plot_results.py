#!/usr/bin/env python3
"""examples/meander の結果の図と数表。

  python3 plot_results.py      # figs/*.png(日本語ラベル)と数表
  python3 plot_results.py en   # en/figs/*.png(英語ラベル)と数表

  figs/planform.png  初期の河道と、主な 7 構成の 200 h 後の河床変化 z − z0
  figs/fixation.png  流量変動+定着(result_fix)の定着度 a と終了時の水深
  figs/sections.png  非粘着性(result)の湾曲頂部の 70 m 下流 x = 420・520 m の横断の時間発展
  figs/metrics.png   x = 150〜650 m の河幅・中心の最大移動・湿潤帯の最大振幅の時間発展
  figs/feed.png      給砂を入れた流量変動+定着の構成の 100 h・200 h の河床変化

数表(標準出力。README の表はこれを写したもの):
  表 1  100 / 150 / 200 h の河幅・中心の最大移動・湿潤帯の最大振幅、最深の洗掘、定着セル
  表 2  定着と給砂の構成の 200 h の定着セル・砂州の高さ・区間ごとの河床変化・氾濫原の堆積
  表 3  画面出力(Screen_<名>.log)の台帳: 安息角崩落・側岸侵食・崩落土塊・容量給砂・細粒分と fluv_dzmax の発動
  表 4  非粘着性(result)の 200 h の湾曲ごとの外岸の後退と、横断 x = 420・520 m の後退と内岸の砂州の高さ
指標の定義は README の「幾何と設定」を参照。終わった計算の結果ディレクトリだけを扱い、地形 200 h に届かずに
止まった計算は表と図から外して止まった時刻を示す。
依存: numpy, matplotlib
"""
import os
import re
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import make_init as mi

EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


FIGDIR = "en/figs" if EN else "figs"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
os.makedirs(FIGDIR, exist_ok=True)

DX, NX, NY = mi.DX, mi.NX, mi.NY
MORFAC = 50.0
XR = (150.0, 650.0)                                # 指標を測る x の範囲 (m)
# (結果ディレクトリ, 画面出力, 日本語名, 英語名, 色)
CASES = [
    ("result", "Screen.log", "非粘着性(一定 Q)", "non-cohesive (constant Q)", "#2a78d6"),
    ("result_cohesive", "Screen_cohesive.log", "粘着性(一定 Q)", "cohesive (constant Q)", "#d6572a"),
    ("result_cohesive_slump", "Screen_cohesive_slump.log", "粘着性+崩落土塊", "cohesive + slump blocks", "#e0a020"),
    ("result_varq", "Screen_varq.log", "流量変動のみ", "varying Q only", "#8a6fd1"),
    ("result_fix", "Screen_fix.log", "流量変動+定着", "varying Q + fixation", "#2a9d5a"),
    ("result_fixrec", "Screen_fixrec.log", "流量変動+定着(緩い減水期)", "varying Q + fixation (gentle recession)", "#7fbf7b"),
    ("result_fixsusp", "Screen_fixsusp.log", "流量変動+定着+浮遊砂", "varying Q + fixation + suspended fines", "#b5641e"),
    ("result_feed", "Screen_feed.log", "非粘着性+容量給砂", "non-cohesive + capacity feed", "#6b6b6b"),
    ("result_fixfeed", "Screen_fixfeed.log", "流量変動+定着+容量給砂", "varying Q + fixation + capacity feed", "#1b7837"),
    ("result_fixsuspfines", "Screen_fixsuspfines.log", "流量変動+定着+浮遊砂+給砂+細粒分の帳簿",
     "varying Q + fixation + fines + feed + fines ledger", "#542788"),
]


def _rows(rdir):
    """FILENUMBER.csv の行(計算中は空)"""
    fn = rdir + "/FILENUMBER.csv"
    return [l.split(",") for l in open(fn) if l.strip() and not l.startswith("#")] if os.path.exists(fn) else []


def _stop_hours(rdir):
    """最後の出力の地形時間 (h)。途中で止まった計算では番号 9998 の行(停止時の出力)の時刻"""
    return max(float(r[2]) for r in _rows(rdir)) * MORFAC / 3600.0


CASES = [c for c in CASES if _rows(c[0])]


# 地形時間 200 h に届かずに止まった計算は表と図から外し、止まった時刻だけを示す
STOPPED = [(c, _stop_hours(c[0])) for c in CASES if _stop_hours(c[0]) < 199.0]
CASES = [c for c in CASES if _stop_hours(c[0]) >= 199.0]
NAME = {c[0]: (c[3] if EN else c[2]) for c in CASES}
COL = {c[0]: c[4] for c in CASES}
PLAN = [d for d in ("result", "result_cohesive", "result_cohesive_slump", "result_varq", "result_fix",
                    "result_fixsusp", "result_feed") if d in NAME]
FEED = [d for d in ("result_fixfeed", "result_fixsuspfines") if d in NAME]

x = (np.arange(NX) + 0.5) * DX
y = (np.arange(NY) + 0.5) * DX
ext = [0, NX * DX, 0, NY * DX]
z0 = np.loadtxt("z.txt"); h0 = np.loadtxt("h.txt")
inside = h0 > 0.05                                  # 初期の河道
cols = (x >= XR[0]) & (x <= XR[1])


def rd(rdir, name, k):
    return np.loadtxt("%s/%s%04d.txt" % (rdir, name, k))


def times(rdir):
    """出力番号 → 地形時間 (h)"""
    return {int(l.split(",")[0]): float(l.split(",")[2]) * MORFAC / 3600.0
            for l in open(rdir + "/FILENUMBER.csv") if not l.startswith("#") and int(l.split(",")[0]) < 9000}


def at(rdir, hours):
    tm = times(rdir)
    return min(tm, key=lambda k: abs(tm[k] - hours))


def metrics(h, z):
    """x = 150〜650 m の列ごとに湿潤セル(h > 0.1 m)の幅と重心を求め、
    河幅(列平均)、重心の初期からのずれの最大、中心軸 y = 120 m からの湿潤セルの距離の最大、
    z − z0 の最小を返す"""
    wet = h > 0.1
    w0 = h0 > 0.1
    width, shift, amp = [], [], 0.0
    for i in np.where(cols)[0]:
        m = wet[:, i]
        width.append(m.sum() * DX)
        if m.any():
            shift.append(abs(y[m].mean() - y[w0[:, i]].mean()))
            amp = max(amp, np.abs(y[m] - mi.YC).max())
    return np.mean(width), max(shift), amp, (z - z0)[:, cols].min()


def bed_change(h, z, xa, xb):
    """x = xa〜xb の湿潤セル(h > 0.05 m)の河床変化の平均"""
    m = (h > 0.05) & (x[None, :] >= xa) & (x[None, :] <= xb)
    return (z - z0)[m].mean()


def ledger(log):
    """画面出力の台帳(無ければ空)"""
    out = {}
    if not os.path.exists(log):
        return out
    pats = {"repose": r"angle-of-repose avalanching moved\s+([0-9.Ee+-]+)",
            "berode": r"bank erosion moved\s+([0-9.Ee+-]+)",
            "rockfall": r"rockfall moved\s+([0-9.Ee+-]+)",
            "cfeed": r"capacity feed \(fluv_bcfeed\) supplied\s+([0-9.Ee+-]+)",
            "fines": r"bed load carried\s+([0-9.Ee+-]+)",
            "dzclip": r"fluvial dzmax clip fired on\s+([0-9]+)"}
    for line in open(log, errors="replace"):
        for k, p in pats.items():
            m = re.search(p, line)
            if m:
                out[k] = float(m.group(1))
    return out


def f0(v):
    return "–" if v is None else "{:,.0f}".format(v)


# ------------------------------------------------------------------ 表 1
for c, hh in STOPPED:
    print("途中で停止: %s(地形 %.1f h。画面出力 %s を参照)" % (c[3] if EN else c[2], hh, c[1]))
print("## 表 1  河幅 / 中心の最大移動 / 湿潤帯の最大振幅 (m)、最深の洗掘 (m)、定着セル(x = 150〜650 m)")
print("| ケース | 100 h | 150 h | 200 h | 最深の洗掘 (m、200 h) | 定着した砂州セル(初期河道内、200 h) |")
print("|---|---|---|---|---|---|")
SER = {}
for rdir in NAME:
    tm = times(rdir)
    ks = sorted(tm)
    SER[rdir] = [(tm[k],) + metrics(rd(rdir, "H", k), rd(rdir, "Z", k)) for k in ks]
    cells = []
    for hh in (100, 150, 200):
        k = at(rdir, hh)
        wd, sh, am, _ = metrics(rd(rdir, "H", k), rd(rdir, "Z", k))
        cells.append("%.1f / %.1f / %.0f" % (wd, sh, am))
    K = at(rdir, 200)
    dzmin = metrics(rd(rdir, "H", K), rd(rdir, "Z", K))[3]
    fixed = "–"
    if os.path.exists("%s/Fx%04d.txt" % (rdir, K)):
        nf = ((rd(rdir, "Fx", K) > 0.5) & inside).sum()
        fixed = "%d(%d m²)" % (nf, nf * DX * DX)
    print("| %s | %s | %.2f | %s |" % (NAME[rdir], " | ".join(cells), dzmin, fixed))
print("(初期: 河幅 20.0 m、中心の移動 0、湿潤帯の最大振幅 19 m)")

# ------------------------------------------------------------------ 表 2
print()
print("## 表 2  200 h の定着セル・砂州の高さ・河床変化(湿潤セルの平均)・氾濫原の堆積・湿潤セル")
print("| ケース | 定着セル(初期河道内) | うち z − z0 > 1.0 m | 定着砂州の最大 z − z0 (m) | 河床変化 x = 50〜150 / 150〜300 / 300〜500 m | 氾濫原の堆積 > 0.1 m(セル) | 湿潤セル(h > 0.05 m) |")
print("|---|---|---|---|---|---|---|")
for rdir in NAME:
    K = at(rdir, 200)
    h = rd(rdir, "H", K); z = rd(rdir, "Z", K); dz = z - z0
    bc = " / ".join("%+.2f" % bed_change(h, z, a, b) for a, b in ((50, 150), (150, 300), (300, 500)))
    if os.path.exists("%s/Fx%04d.txt" % (rdir, K)):
        fixed = (rd(rdir, "Fx", K) > 0.5) & inside
        fx = "%d | %d | %.2f" % (fixed.sum(), (fixed & (dz > 1.0)).sum(), dz[fixed].max() if fixed.any() else float("nan"))
    else:
        fx = "– | – | –"
    print("| %s | %s | %s | %d | %d |" % (NAME[rdir], fx, bc, ((dz > 0.1) & ~inside).sum(), (h > 0.05).sum()))

# 定着セルの水没(出水期 150 h と低水期 100・200 h)
print()
print("定着セル(初期河道内、a > 0.5)のうち水没(h > 0.05 m)しているセル: 100 h / 150 h(出水期) / 200 h")
for rdir in NAME:
    if not os.path.exists("%s/Fx%04d.txt" % (rdir, at(rdir, 200))):
        continue
    s = []
    for hh in (100, 150, 200):
        k = at(rdir, hh)
        fixed = (rd(rdir, "Fx", k) > 0.5) & inside
        s.append("%d / %d" % ((fixed & (rd(rdir, "H", k) > 0.05)).sum(), fixed.sum()))
    print("  %s: %s" % (NAME[rdir], "、".join(s)))

# ------------------------------------------------------------------ 表 3
print()
print("## 表 3  台帳(画面出力。m³。崩落・侵食はかさ、給砂・細粒分は固体)と 1 更新の変動上限 fluv_dzmax の発動")
print("| ケース | 安息角崩落 | 側岸侵食則 | 崩落土塊(rockfall) | 容量給砂 | 掃流砂に同伴した細粒分 | fluv_dzmax の発動(エッジ) |")
print("|---|---|---|---|---|---|---|")
for c in CASES:
    lg = ledger(c[1])
    print("| %s | %s |" % (NAME[c[0]], " | ".join(f0(lg.get(k)) for k in ("repose", "berode", "rockfall", "cfeed", "fines", "dzclip"))))

# ------------------------------------------------------------------ 表 4: 外岸の後退(非粘着性)
# 河道の縁 = 氾濫原(列の初期の最高点 = 河床 + 1 m)より 0.5 m 以上低い所の端。初期の河岸からの移動を後退とする。
# 頂点 x = 350・550 m の湾曲は北へ、450・650 m の湾曲は南へ張り出す(外岸 = 張り出す側)。
if "result" in NAME:
    rdir = "result"; K = at(rdir, 200)
    z = rd(rdir, "Z", K); h = rd(rdir, "H", K)
    ret = {}                                        # 列 → (北岸の後退, 南岸の後退) m
    for i in range(NX):
        jc = np.where(h0[:, i] > 0)[0]; jl = np.where(z[:, i] < z0[:, i].max() - 0.5)[0]
        if jc.size and jl.size:
            ret[i] = ((jl.max() - jc.max()) * DX, (jc.min() - jl.min()) * DX)
    print()
    print("## 表 4  非粘着性(result)の %.0f h の外岸の後退(m。氾濫原より 0.5 m 以上低い所の縁の、初期の河岸からの移動)"
          % times(rdir)[K])
    print("| 湾曲の頂点 x (m) | 外岸 | 頂点から 100 m 下流までの最大の後退 (m) | その位置 x (m) |")
    print("|---|---|---|---|")
    for xa, side in ((350, 0), (450, 1), (550, 0), (650, 1)):
        cols = [i for i in ret if xa <= x[i] < xa + 100]
        v = max(ret[i][side] for i in cols)
        xs = [x[i] for i in cols if ret[i][side] == v]
        print("| %d | %s | %.0f | %.0f〜%.0f |" % (xa, ("北", "南")[side], v, min(xs), max(xs)))
    for xs, side in ((420, 0), (520, 1)):
        i = int(xs / DX); jc = np.where(h0[:, i] > 0)[0]
        inner = jc[: jc.size // 2] if side == 0 else jc[jc.size // 2:]   # 内岸側の半分
        jb = inner[np.argmax(z[inner, i] - z0[inner, i])]
        print("横断 x = %d m: 外岸(%s)の後退 %.0f m、内岸の砂州の最大 z − z0 %+.2f m(砂州の上の水深 %.2f m)" % (
            xs, ("北", "南")[side], ret[i][side], z[jb, i] - z0[jb, i], h[jb, i]))

# ------------------------------------------------------------------ 図 1: 平面
if PLAN:
    fig, axes = plt.subplots(len(PLAN) + 1, 1, figsize=(13, 2.75 * (len(PLAN) + 1)), sharex=True)
    im = axes[0].imshow(np.where(h0 > 0.05, h0, np.nan), origin="lower", extent=ext, cmap="Blues", vmin=0, vmax=2)
    axes[0].set_title(T("初期の河道(水深 m)", "initial channel (depth, m)"), fontsize=10, loc="left")
    fig.colorbar(im, ax=axes[0], shrink=0.85, pad=0.01)
    for ax, rdir in zip(axes[1:], PLAN):
        K = at(rdir, 200)
        h = rd(rdir, "H", K); dz = rd(rdir, "Z", K) - z0
        im = ax.imshow(dz, origin="lower", extent=ext, cmap="RdBu_r", vmin=-1.0, vmax=1.0)
        ax.contour(x, y, h0 > 0.05, levels=[0.5], colors="k", linewidths=0.4)
        ax.contour(x, y, h > 0.05, levels=[0.5], colors=COL[rdir], linewidths=0.9)
        ax.set_title(T("%s: %.0f h 後の河床変化 z − z0 (m)", "%s: bed change z − z0 (m) after %.0f h")
                     % (NAME[rdir], times(rdir)[K]), fontsize=9.5, loc="left")
        fig.colorbar(im, ax=ax, shrink=0.85, pad=0.01)
    for ax in axes:
        ax.set_ylabel("y (m)", fontsize=8.5); ax.tick_params(labelsize=7.5)
    axes[-1].set_xlabel("x (m)", fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.3 / fig.get_figheight()))
    fig.suptitle(T("黒 = 初期の河岸、色の線 = 終了時の水際(水深 0.05 m)", "black = initial banks, coloured line = final water edge (depth 0.05 m)"),
                 fontsize=9.5, x=axes[0].get_position().x0, y=1 - 0.08 / fig.get_figheight(), ha="left", va="top")
    fig.savefig(os.path.join(FIGDIR, "planform.png"), dpi=95); plt.close(fig)

# ------------------------------------------------------------------ 図 2: 定着度
if "result_fix" in NAME:
    rdir = "result_fix"; K = at(rdir, 200)
    fx = rd(rdir, "Fx", K); h = rd(rdir, "H", K)
    fig, axes = plt.subplots(2, 1, figsize=(13, 5.8), sharex=True)
    im = axes[0].imshow(np.where(fx > 0.01, fx, np.nan), origin="lower", extent=ext, cmap="YlGn", vmin=0, vmax=1)
    axes[0].contour(x, y, h0 > 0.05, levels=[0.5], colors="k", linewidths=0.4)
    axes[0].contour(x, y, h > 0.05, levels=[0.5], colors="#1f5fbf", linewidths=0.9)
    axes[0].set_title(T("%.0f h 後の定着度 a(黒 = 初期の河岸、青 = 終了時(低水期)の水際)",
                        "fixation degree a after %.0f h (black = initial banks, blue = final water edge at low flow)") % times(rdir)[K],
                      fontsize=9.5, loc="left")
    fig.colorbar(im, ax=axes[0], shrink=0.85, pad=0.01)
    im = axes[1].imshow(np.where(h > 0.05, h, np.nan), origin="lower", extent=ext, cmap="Blues", vmin=0, vmax=2)
    axes[1].contour(x, y, h0 > 0.05, levels=[0.5], colors="k", linewidths=0.4)
    axes[1].set_title(T("終了時(低水期)の水深 (m)", "final depth (m) at low flow"), fontsize=9.5, loc="left")
    fig.colorbar(im, ax=axes[1], shrink=0.85, pad=0.01)
    for ax in axes:
        ax.set_ylabel("y (m)", fontsize=8.5); ax.tick_params(labelsize=7.5)
    axes[-1].set_xlabel("x (m)", fontsize=8.5)
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "fixation.png"), dpi=95); plt.close(fig)

# ------------------------------------------------------------------ 図 3: 横断
if "result" in NAME:
    rdir = "result"; tm = times(rdir); ks = sorted(tm)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    for ax, xa in zip(axes, (420, 520)):
        i = int(xa / DX)
        for k in ks:
            z = rd(rdir, "Z", k)
            ax.plot(y, z[:, i], color=plt.cm.viridis(k / max(ks)), lw=1.2, label="%.0f h" % tm[k])
        z = rd(rdir, "Z", ks[-1]); h = rd(rdir, "H", ks[-1])
        ax.plot(y, (z + np.where(h > 0.05, h, np.nan))[:, i], "k--", lw=0.8, label=T("水面(終了時)", "water surface (final)"))
        jc = np.where(h0[:, i] > 0)[0]
        jf = np.where(z[:, i] < z0[:, i].max() - 0.5)[0]           # 終了時に河岸より 0.5 m 以上低い所(河道)
        ax.set_xlim(y[min(jc.min(), jf.min())] - 12, y[max(jc.max(), jf.max())] + 12)
        ax.set_ylim(z0[jc, i].min() - 2.0, z0[jc, i].min() + 1.6)
        ax.set_title(T("x = %d m の横断(頂点 x = %d m の 70 m 下流。外岸 = %s)",
                       "x = %d m (70 m below the apex at %d m; outer bank: %s)")
                     % (xa, xa - 70, T("北側", "north") if xa == 420 else T("南側", "south")), fontsize=9.5, loc="left")
        ax.set_xlabel("y (m)", fontsize=8.5); ax.set_ylabel("z (m)", fontsize=8.5); ax.grid(alpha=0.3); ax.tick_params(labelsize=7.5)
    axes[0].legend(fontsize=7.5, ncol=2)
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "sections.png"), dpi=95); plt.close(fig)

# ------------------------------------------------------------------ 図 4: 指標の時間発展
if SER:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for rdir, ser in SER.items():
        a = np.array(ser)
        ls = "--" if rdir in ("result_fixrec", "result_fixsuspfines", "result_fixfeed") else "-"
        for n, ax in enumerate(axes):
            ax.plot(a[:, 0], a[:, n + 1], ls, marker="o", ms=2.5, color=COL[rdir], lw=1.2, label=NAME[rdir])
    for ax, t in zip(axes, (T("河幅(湿潤セルの列平均、m)", "channel width (column mean of wet cells, m)"),
                            T("中心の最大移動 (m)", "maximum shift of the centre (m)"),
                            T("湿潤帯の最大振幅 (m)", "maximum amplitude of the wet belt (m)"))):
        ax.set_title(t, fontsize=10, loc="left"); ax.set_xlabel(T("地形時間 (h)", "landform time (h)"), fontsize=8.5)
        ax.grid(alpha=0.3); ax.tick_params(labelsize=7.5)
    axes[0].legend(fontsize=6.8, loc="upper left")
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "metrics.png"), dpi=95); plt.close(fig)

# ------------------------------------------------------------------ 図 5: 給砂を入れた構成
if FEED:
    fig, axes = plt.subplots(2 * len(FEED), 1, figsize=(13, 2.75 * 2 * len(FEED)), sharex=True)
    axes = np.atleast_1d(axes)
    for n, rdir in enumerate(FEED):
        for m, hh in enumerate((100, 200)):
            ax = axes[2 * n + m]; K = at(rdir, hh)
            h = rd(rdir, "H", K); dz = rd(rdir, "Z", K) - z0; fx = rd(rdir, "Fx", K)
            im = ax.imshow(dz, origin="lower", extent=ext, cmap="RdBu_r", vmin=-1.5, vmax=1.5)
            ax.contour(x, y, h0 > 0.05, levels=[0.5], colors="k", linewidths=0.4)
            ax.contour(x, y, h > 0.05, levels=[0.5], colors="#2a9d5a", linewidths=0.8)
            ax.contour(x, y, (fx > 0.5) & inside, levels=[0.5], colors="#b5641e", linewidths=0.8)
            ax.set_title(T("%s: %.0f h の z − z0 (m)", "%s: z − z0 (m) at %.0f h") % (NAME[rdir], times(rdir)[K]),
                         fontsize=9, loc="left")
            fig.colorbar(im, ax=ax, shrink=0.85, pad=0.01)
            ax.set_ylabel("y (m)", fontsize=8.5); ax.tick_params(labelsize=7.5)
    axes[-1].set_xlabel("x (m)", fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.3 / fig.get_figheight()))
    fig.suptitle(T("黒 = 初期の河岸、緑 = 水際、茶 = 初期の河道の中の定着砂州(a > 0.5)",
                   "black = initial banks, green = water edge, brown = fixed bars (a > 0.5) in the initial channel"),
                 fontsize=9.5, x=axes[0].get_position().x0, y=1 - 0.08 / fig.get_figheight(), ha="left", va="top")
    fig.savefig(os.path.join(FIGDIR, "feed.png"), dpi=95); plt.close(fig)

print()
print("figures: " + " ".join("%s/%s.png" % (FIGDIR, f) for f, ok in
                              (("planform", PLAN), ("fixation", "result_fix" in NAME), ("sections", "result" in NAME),
                               ("metrics", SER), ("feed", FEED)) if ok))
