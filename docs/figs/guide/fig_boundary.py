"""境界条件の章の図: 4 つの族(辺境界・内部ソース・水位規定・区間流入)を 1 枚の平面図に置く。"""
from _style import *

T = {"ja": {
    "title": "境界条件の 4 つの族(fn_boundary の 4 グループ。書かなければその族は無効)。セル座標 (i, j) は 1 スタート",
    "n": "北辺 j = 1: f_bc_n = 0(壁。既定)",
    "s": "南辺 j = ny: f_bc_s = 1(自由流出)",
    "e": "東辺 i = nx\nf_bc_e = 2\n(長波放射)",
    "w": "西辺 i = 1\nf_bc_w = 0(壁)",
    "edge": "辺境界 &list_bound_edge(4 辺の型)\n 0: 不透過(壁)\n 1: 自由流出(通過・段落ち。流入なし)\n 2: 長波放射(水位偏差だけ透過。基準 bc_eta_*)",
    "inflow": "区間流入 &list_bound_inflow\n外縁に接するセル区間の法線面に\n総流量 Q(t) を規定(運動量あり)\ninflow_cell(:,k,n) = i, j\ninflow_val(:,k,n) = t, Q\ninflow_dist: 0 均等 / 1 水深 /\n 2 通水能(h^5/3)",
    "source": "内部ソース &list_bound_source\n任意のセル集合に Q(t)\n(> 0 湧き出し、< 0 吸い込み)\nsrc_cell(:,k,n) = i, j\nsrc_val(:,k,n) = t, Q\n(集合の総量を均等分配。運動量なし)",
    "stage": "水位規定 &list_bound_stage\nセル集合の水位を η に強制\n h = max(η − z, 0)\nstage_cell(:,k,n) = i, j\nstage_eta(n) = η(固定)\nstage_val(:,k,n) = t, η(時系列)\n(η を河床より低く → 完全排水口)",
    "i": "i(列。西→東)", "j": "j(行。北→南)",
    "Q": "Q(t)", "eta": "η(t)",
}, "en": {
    "title": "The four families of boundary conditions (4 groups in fn_boundary; an absent group = family off). Cell indices (i, j) are 1-based",
    "n": "north edge j = 1: f_bc_n = 0 (wall, default)",
    "s": "south edge j = ny: f_bc_s = 1 (free outflow)",
    "e": "east edge i = nx\nf_bc_e = 2\n(long-wave radiation)",
    "w": "west edge i = 1\nf_bc_w = 0 (wall)",
    "edge": "Edge boundaries &list_bound_edge (type of each edge)\n 0: impermeable (wall)\n 1: free outflow (pass-through / overfall; no inflow)\n 2: long-wave radiation (passes the level deviation only; reference bc_eta_*)",
    "inflow": "Segment inflow &list_bound_inflow\ntotal discharge Q(t) on the outward\nnormal face of a cell segment on the\nouter edge (carries momentum)\ninflow_cell(:,k,n) = i, j\ninflow_val(:,k,n) = t, Q\ninflow_dist: 0 equal / 1 depth /\n 2 conveyance (h^5/3)",
    "source": "Internal sources &list_bound_source\nQ(t) at an arbitrary cell set\n(> 0 injection, < 0 extraction)\nsrc_cell(:,k,n) = i, j\nsrc_val(:,k,n) = t, Q\n(total shared equally; no momentum)",
    "stage": "Prescribed water level &list_bound_stage\nforces the level of a cell set to η\n h = max(η − z, 0)\nstage_cell(:,k,n) = i, j\nstage_eta(n) = η (fixed)\nstage_val(:,k,n) = t, η (time series)\n(η below the bed -> perfect drain)",
    "i": "i (columns, W -> E)", "j": "j (rows, N -> S)",
    "Q": "Q(t)", "eta": "η(t)",
}}

NX, NY = 16, 11


def draw(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(10.5, 6.9)); ax.set_aspect("equal"); ax.axis("off")
    grid(ax, 0, 0, NX, NY, 1, "#c9c8c3", 0.5)
    ax.add_patch(Rectangle((0, 0), NX, NY, fc="#f7f6f2", ec="none", zorder=0))
    # 北辺・西辺: 壁(太い黒線)
    ax.plot([0, NX], [NY, NY], color="k", lw=3.2, zorder=5)
    ax.plot([0, 0], [0, NY], color="k", lw=3.2, zorder=5)
    # 南辺: 自由流出(外向き矢印)
    ax.plot([0, NX], [0, 0], color=C_G, lw=2.5, zorder=5)
    for x in range(1, NX, 2):
        arrow(ax, (x + 0.5, 0.55), (x + 0.5, -0.5), C_G, lw=1.2)
    # 東辺: 長波放射(双方向の小矢印)
    ax.plot([NX, NX], [0, NY], color=C_C, lw=2.5, zorder=5)
    for y in range(1, NY, 2):
        arrow(ax, (NX - 0.6, y + 0.65), (NX + 0.5, y + 0.65), C_C, lw=1.0)
        arrow(ax, (NX + 0.5, y + 0.25), (NX - 0.6, y + 0.25), C_C, lw=1.0, ls="--")
    # 西辺の区間流入(j = 6..8 の 3 セル)
    for jj in (6, 7, 8):
        y = NY - jj + 0.5
        ax.add_patch(Rectangle((0, y - 0.5), 1, 1, fc=C_X, alpha=0.35, ec="none", zorder=2))
        arrow(ax, (-1.1, y), (0.9, y), C_X, lw=2.0)
    ax.text(-1.25, NY - 7 + 0.5, t["Q"], color=C_X, fontsize=9, ha="right", va="center")
    # 内部ソース(2 セル)
    sc = [(5, 4), (5, 5)]
    for (i, j) in sc:
        ax.add_patch(Rectangle((i - 1, NY - j), 1, 1, fc=C_X, alpha=0.35, ec=C_X, lw=1.2, zorder=3))
    ax.add_patch(Circle((4.5, NY - 4), 0.32, fc="white", ec=C_X, lw=1.6, zorder=4))
    ax.text(4.5, NY - 4, "Q", color=C_X, fontsize=8.5, ha="center", va="center", zorder=5)
    # 水位規定セル群(3 セル)
    for (i, j) in [(12, 9), (13, 9), (13, 10)]:
        ax.add_patch(Rectangle((i - 1, NY - j), 1, 1, fc=C_C, alpha=0.55, ec=C_C, lw=1.2, zorder=3))
    ax.text(12.5, NY - 8.5, t["eta"], color=C_C, fontsize=9, ha="center", va="center", zorder=5)
    # 辺のラベル
    ax.text(NX / 2, NY + 0.3, t["n"], ha="center", va="bottom", fontsize=9, color="k")
    ax.text(NX / 2, -1.25, t["s"], ha="center", va="top", fontsize=9, color="#3f7a2a")
    ax.text(NX + 0.9, NY / 2 + 2.0, t["e"], ha="left", va="center", fontsize=9, color=C_C)
    ax.text(-0.4, NY - 4.3, t["w"], ha="right", va="center", fontsize=9, color="k")
    # 説明(族ごと。格子の下と右に並べる)
    box = dict(fc="white", ec="#d9d8d3", lw=0.6, pad=3)
    ax.annotate(t["inflow"], (0.0, NY - 7.5), (-6.4, -2.0), ha="left", va="top", fontsize=8, color="#b0481f", bbox=box,
                arrowprops=dict(arrowstyle="-", color=C_X, lw=0.7, shrinkB=2))
    ax.annotate(t["source"], (4.5, NY - 5), (3.4, -2.0), ha="left", va="top", fontsize=8, color="#b0481f", bbox=box,
                arrowprops=dict(arrowstyle="-", color=C_X, lw=0.7))
    ax.annotate(t["stage"], (13, NY - 9), (NX + 0.9, NY - 7.2), ha="left", va="top", fontsize=8, color=C_C, bbox=box,
                arrowprops=dict(arrowstyle="-", color=C_C, lw=0.7))
    ax.text(NX + 0.9, NY + 0.3, t["edge"], ha="left", va="top", fontsize=8, color="k", bbox=box)
    # 添字の向き
    ax.annotate("", (3, NY + 1.35), (0, NY + 1.35), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1))
    ax.text(3.2, NY + 1.35, t["i"], fontsize=8.5, color=C_P, ha="left", va="center")
    ax.annotate("", (-0.8, NY - 3), (-0.8, NY), arrowprops=dict(arrowstyle="-|>", color=C_P, lw=1))
    ax.text(-1.0, NY, t["j"], fontsize=8.5, color=C_P, va="top", ha="right", rotation=90)
    ax.set_xlim(-6.6, NX + 9.8); ax.set_ylim(-5.0, NY + 1.9)
    ax.set_title(t["title"], loc="left", fontsize=10)
    fig.tight_layout()
    return save(fig, "boundary_families", lang)
