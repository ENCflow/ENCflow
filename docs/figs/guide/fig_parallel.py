"""parallel_bands: 並列実行 — j 方向の帯分割(MPI ランク)とハロ行、ランク内の OpenMP スレッド、決定的な集約。"""
from _style import *

T = {"ja": {
    "ta": "(a) MPI: 領域を j 方向(行)の帯に自動分割。encflow_mpi(MODE = mpi)",
    "tb": "(b) 1 ランクの中: OpenMP スレッド(encflow / encflow_mpi とも)",
    "north": "北", "j": "j(行。北→南)", "rank": "rank {k}", "rows": "行 j = {a} … {b}",
    "halo": "ハロ行(隣接ランクの行の写し。\n各ステップで交換 = 通信)",
    "gather": "出力の集約(自動)", "file": "分布ファイル・ログ",
    "threads": "OMP_NUM_THREADS(既定: マシンのコア数)", "thread": "スレッド {k}",
    "band": "担当帯のセルをスレッドで分担",
    "det": "総和の集約は行ごとの部分和を決まった順序で足す(決定的)",
    "guar": "保証: スレッド数・MPI ランク数をどう変えても結果はビット単位で同一\n(逐次の検証結果 = 100 ランクの本計算。\nパラメータファイルも同一)",
}, "en": {
    "ta": "(a) MPI: automatic band decomposition in rows (j); encflow_mpi",
    "tb": "(b) Inside a rank: OpenMP threads (encflow and encflow_mpi)",
    "north": "N", "j": "j (rows, north→south)", "rank": "rank {k}", "rows": "rows j = {a} … {b}",
    "halo": "halo rows (copies of the\nneighbour's rows; exchanged\nevery step = communication)",
    "gather": "output aggregation\n(automatic)", "file": "distributed files, log",
    "threads": "OMP_NUM_THREADS (default: the machine's cores)", "thread": "thread {k}",
    "band": "the rank's band of cells is shared among threads",
    "det": "sums are aggregated from row partial sums in a fixed order (deterministic)",
    "guar": "Guarantee: results are bitwise identical for any number of threads or MPI ranks\n(a serial verification = a 100-rank production run;\nthe parameter file is the same)",
}}


def draw(lang):
    t = T[lang]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 5.4), gridspec_kw={"width_ratios": [1.1, 1]})
    NX, NY, NR = 10, 12, 3
    nb = NY // NR
    # ------------------------------------------------ (a) bands
    ax = axs[0]; ax.set_aspect("equal"); ax.set_anchor("N"); ax.axis("off")
    cols = ["#e8eef8", "#fbefd8", "#e6f1dd"]
    for r in range(NR):
        ytop = NY - r * nb
        ax.add_patch(Rectangle((0, ytop - nb), NX, nb, fc=cols[r], ec="none", zorder=0))
        ja, jb = r * nb + 1, (r + 1) * nb
        label(ax, -0.4, ytop - nb / 2 + 0.3, t["rank"].format(k=r), color=C_C, fs=10, ha="right", fontweight="bold")
        label(ax, -0.4, ytop - nb / 2 - 0.35, t["rows"].format(a=ja, b=jb), color=C_P, fs=8.5, ha="right")
    grid(ax, 0, 0, NX, NY, 1, C_P, 0.6)
    for r in range(1, NR):
        ax.plot([0, NX], [NY - r * nb, NY - r * nb], color="k", lw=2.0, zorder=3)
    # halo rows of rank 1 (2 rows on each side), hatched
    r = 1; ytop = NY - r * nb
    for (y0, h) in ((ytop, 2), (ytop - nb - 2, 2)):
        ax.add_patch(Rectangle((0, y0), NX, h, fill=False, hatch="///", ec=C_X, lw=0, zorder=2))
    ax.add_patch(Rectangle((0, ytop - nb - 2), NX, nb + 4, fill=False, ec=C_X, lw=1.6, ls="--", zorder=4))
    label(ax, NX + 1.2, ytop - nb / 2, t["halo"], color=C_X, fs=8.5, ha="left")
    for y in (ytop - 1, ytop - nb - 1):
        arrow(ax, (NX + 0.25, y + 1.2), (NX + 0.25, y - 1.2), C_X, lw=1.1)
        arrow(ax, (NX + 0.7, y - 1.2), (NX + 0.7, y + 1.2), C_X, lw=1.1)
    # orientation
    label(ax, NX / 2, NY + 0.95, t["north"], color=C_P, fs=10, fontweight="bold")
    ax.annotate("", (NX / 2, NY + 0.85), (NX / 2, NY + 0.4), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1.2))
    ax.annotate("", (-5.1, NY - 3), (-5.1, NY), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1))
    label(ax, -5.25, NY - 1.5, t["j"], color=C_P, fs=8.5, ha="right", rotation=90)
    # output aggregation -> distributed files / log
    arrow(ax, (NX / 2 - 1.5, -0.2), (NX / 2 - 1.5, -1.3), C_G, lw=1.8)
    label(ax, NX / 2 - 1.2, -0.75, t["gather"], color="#3f7a2a", fs=8.5, ha="left")
    ax.add_patch(FancyBboxPatch((NX / 2 - 3.2, -2.35), 6.4, 0.8, boxstyle="round,pad=0.05", fc="white", ec=C_G, lw=1.4, zorder=3))
    label(ax, NX / 2, -1.95, t["file"], color="#3f7a2a", fs=9)
    ax.set_xlim(-6.4, NX + 6.4); ax.set_ylim(-2.7, NY + 1.6)
    ax.set_title(t["ta"], loc="left", fontsize=9.5)
    # ------------------------------------------------ (b) threads inside a rank
    ax = axs[1]; ax.set_aspect("equal"); ax.set_anchor("N"); ax.axis("off")
    NT = 4
    ax.add_patch(Rectangle((0, 0), NX, nb, fc="#fbefd8", ec="k", lw=1.4, zorder=0))
    grid(ax, 0, 0, NX, nb, 1, C_P, 0.6)
    label(ax, -0.3, nb / 2, t["rank"].format(k=1), color=C_C, fs=10, ha="right", fontweight="bold")
    tc = [C_C, C_G, C_X, "#8a6b17"]
    for k in range(NT):
        x = 0.3 + k * 2.4
        ax.add_patch(FancyBboxPatch((x, nb + 1.3), 2.2, 0.7, boxstyle="round,pad=0.05", fc="white", ec=tc[k], lw=1.4, zorder=3))
        label(ax, x + 1.1, nb + 1.65, t["thread"].format(k=k), color=tc[k], fs=8.5)
        arrow(ax, (x + 1.1, nb + 1.2), (x + 1.1, nb + 0.15), tc[k], lw=1.3)
    label(ax, NX / 2, nb + 2.35, t["threads"], color=C_P, fs=9)
    label(ax, NX / 2, -0.4, t["band"], color=C_P, fs=8.8, va="top")
    label(ax, NX / 2, -1.2, t["det"], color=C_P, fs=8.5, va="top")
    ax.add_patch(FancyBboxPatch((-2.1, -4.15), NX + 4.2, 1.75, boxstyle="round,pad=0.1", fc="#eef6e8", ec=C_G, lw=1.4, zorder=1))
    label(ax, NX / 2, -3.27, t["guar"], color="#3f7a2a", fs=8.4)
    ax.set_xlim(-2.6, NX + 2.6); ax.set_ylim(-4.6, nb + 3.2)
    ax.set_title(t["tb"], loc="left", fontsize=9.5)
    fig.tight_layout()
    return save(fig, "parallel_bands", lang)
