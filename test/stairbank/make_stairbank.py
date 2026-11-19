#!/usr/bin/env python3
# test/stairbank の入力生成と定数(Check_stairbank.py・param_*.txt と定数を対で保守。標準ライブラリだけ)
#   格子に斜めの 1 セル幅の河道(8 連結。D8 の落水線と同じ型)の脇に、河床より高い岸のセル(段・角のセル)を置く。
#   上流端から 2 つ目の河道のセルに流量を与えて、段階的に上げ下げする。東辺は自由流出。
#     python3 make_stairbank.py names            構成名を 1 行に 1 つ
#     python3 make_stairbank.py geoms            形の名前を 1 行に 1 つ
#     python3 make_stairbank.py z <形>           標高(sb_z_<形>.txt 用)
#     python3 make_stairbank.py rw <形>          河道マスク(sb_rw_<形>.txt 用)
#     python3 make_stairbank.py params           param_<構成名>.txt を書き出す
import math, os, re, sys

DX, SLOPE, Z0 = 50.0, 0.0065, 400.0          # 格子間隔 (m)、河床勾配、上流端の河床の標高 (m)
RN_RIVER, RN_LAND = 0.04, 0.05               # 粗度(河道のセル・ほか)
H_SHELF, H_WALL = 10.0, 60.0                 # 段・角のセルの高さ、壁の高さ(いちばん近い河道のセルの河床から。m)
DT, REC = 0.75, 30                           # 時間刻み (s)、プローブ・測線の記録間隔 (s)
# 与える流量: 0 → 2,000 を 5 分、そのあと各段の長さごとに 5 分かけて次の段へ(分, m3/s)
STAGES = [2000.0, 4000.0, 6000.0, 8000.0, 10000.0, 8000.0, 6000.0, 4000.0, 2000.0]
# 各段の長さ(分。移りの 5 分を含む)。最後の 2,000 m3/s の段は 90 分: 段の上に載った水が河道へ抜けるのに 1 時間ほどかかる
T_STAGES = [30.0] * (len(STAGES) - 1) + [90.0]
T_MOVE = 5.0
T_ENDS = [sum(T_STAGES[:n + 1]) for n in range(len(STAGES))]      # 各段の終わりの時刻(分)
T_END = T_ENDS[-1]                           # 計算の長さ(分)= 330
MOVES = {"E": (1, 0), "NE": (1, -1), "N": (0, -1), "SE": (1, 1), "S": (0, 1)}

# 形: 流路(向きと回数)、段(河道のセルの 8 近傍を河床 + H_SHELF にするか)、角のセル(流路の k 番目のセルからのずれ)
#   階段 zz = 入口 8 セル + (東, 北東) × 24 + 出口 8 セル、対角 dg = 入口 8 + 北東 × 34 + 出口 8、
#   1 つの階段 st = 東 × 24 + 北東 × 1 + 東 × 24(階段の手前のセルが k = 24、直後が k = 25)
#   角のセル A = k = 24 のセルの北(= k = 25 のセルの西)、B = k = 24 のセルの東(= k = 25 のセルの南)
GEOMS = {
    "zw": ("E8,(E.NE)x24,E8", False, []),
    "zs": ("E8,(E.NE)x24,E8", True, []),
    "dw": ("E8,NE34,E8", False, []),
    "ds": ("E8,NE34,E8", True, []),
    "sw": ("E24,NE,E24", False, []),
    "sa": ("E24,NE,E24", False, [(24, 0, -1)]),
    "sab": ("E24,NE,E24", False, [(24, 0, -1), (24, 1, 0)]),
}
# 移流項の規則の組(&list_enc に書く行)。"" = 既定、"4" = 下の 4 つの値の組み合わせ(developer.md §113)
RULES = {
    "": [],
    "4": ["f_advection_donor = 4      ! 線の上流側の連結の流速を、その連結が代表する流れの分だけに掛ける",
          "f_advection_bend = 2       ! 到着した水の速さからの加速を、エネルギー水頭を保存する形の移流項で数える",
          "f_advection_lateral = 2    ! 入ってくる水より速い平行リンクの流速を、流量の比で下げて使う",
          "f_dry_head_cap = 4         ! 登る辺の頭打ちの、入ってくる流れの速さを、セルの平均流速で上から止める"],
}
# 構成名 = 形の名前 + 規則の組の名前(zs = 段のある階段を既定の規則で、zs4 = 同じ形を 4 つの値の組み合わせで)
SHAPES = ["zw", "zs", "dw", "ds", "sw", "sa", "sab"]
CASES = [g + r for r in ("", "4") for g in SHAPES]
WALL_OF = {"zs": "zw", "ds": "dw", "sa": "sw", "sab": "sw"}     # 比べる相手(壁だけの形)
K_STEP = 24                                  # 1 つの階段の形の、階段の手前のセルの番号


def geom_of(case):
    """構成名 → 形の名前"""
    return case[:-1] if case.endswith("4") else case


def rule_of(case):
    """構成名 → 規則の組の名前"""
    return "4" if case.endswith("4") else ""


def expand(spec):
    out = []
    for tok in spec.split(","):
        m = re.fullmatch(r"\(([A-Z.]+)\)x(\d+)", tok)
        if m:
            out += m.group(1).split(".") * int(m.group(2))
            continue
        m = re.fullmatch(r"([A-Z]+)(\d*)", tok)
        out += [m.group(1)] * int(m.group(2) or 1)
    return out


def build(geom):
    """形(構成名でもよい)→ (nx, ny, 標高, 河道マスク, 流路のセルの一覧(1 始まりの (i, j))、角のセルの一覧)"""
    spec, shelf, corners = GEOMS[geom_of(geom)]
    cells, dist = [(0, 0)], [0.0]
    for mv in expand(spec):
        di, dj = MOVES[mv]
        cells.append((cells[-1][0] + di, cells[-1][1] + dj))
        dist.append(dist[-1] + DX * math.hypot(di, dj))
    margin = 4 if shelf else 3
    imin = min(c[0] for c in cells)
    jmin = min(c[1] for c in cells) - margin
    nx = max(c[0] for c in cells) - imin + 2          # 西に 1 列の壁。東の端は流路の終点(自由流出)
    ny = max(c[1] for c in cells) + margin - jmin + 1
    path = [(c[0] - imin + 2, c[1] - jmin + 1) for c in cells]
    bed = {p: Z0 - SLOPE * s for p, s in zip(path, dist)}
    z = [[0.0] * nx for _ in range(ny)]
    rw = [[0] * nx for _ in range(ny)]
    for j in range(1, ny + 1):
        for i in range(1, nx + 1):
            if (i, j) in bed:
                z[j - 1][i - 1], rw[j - 1][i - 1] = bed[(i, j)], 1
                continue
            # いちばん近い河道のセル(同じ距離なら河床の低い方)の河床から測る
            near = min(path, key=lambda p: ((p[0] - i) ** 2 + (p[1] - j) ** 2, bed[p]))
            ring = min(max(abs(p[0] - i), abs(p[1] - j)) for p in path)
            z[j - 1][i - 1] = bed[near] + (H_SHELF if (shelf and ring == 1) else H_WALL)
    side = []
    for k, di, dj in corners:
        i, j = path[k][0] + di, path[k][1] + dj
        z[j - 1][i - 1] = bed[path[k]] + H_SHELF
        side.append((i, j))
    return nx, ny, z, rw, path, side


def probes(geom):
    """プローブ: 階段・対角は流路の 1/3・1/2・2/3 のセル。1 つの階段は、階段の 4 つ上流・手前・直後・1 つ下流・3 つ下流と角のセル"""
    nx, ny, z, rw, path, side = build(geom)
    n = len(path)
    ks = [K_STEP - 4, K_STEP, K_STEP + 1, K_STEP + 2, K_STEP + 4] if geom.startswith("s") else [n // 3, n // 2, 2 * n // 3]
    return [path[k] for k in ks] + side, ks


def transect(geom):
    """測線: 流路の中ほど(1 つの階段の形は、階段の直後)の列を、南北に全部横切る"""
    nx, ny, z, rw, path, side = build(geom)
    k = K_STEP + 1 if geom.startswith("s") else len(path) // 2
    return path[k][0], ny, path[k][0], 1


def hydrograph():
    pts = [(0.0, 0.0)]
    for n, q in enumerate(STAGES):
        pts.append((T_ENDS[n] - T_STAGES[n] + T_MOVE, q))
        pts.append((T_ENDS[n], q))
    return pts


def param(name):
    geom, rule = geom_of(name), rule_of(name)
    nx, ny, z, rw, path, side = build(geom)
    desc = {"zw": "階段状の河道(東・北東が交互)。岸は壁だけ", "zs": "階段状の河道。両脇に、河床より 10 m 高い段",
            "dw": "対角の河道(北東向き)。岸は壁だけ", "ds": "対角の河道。両脇に、河床より 10 m 高い段",
            "sw": "階段が 1 つの河道。岸は壁だけ", "sa": "階段が 1 つの河道。階段の内側の角のセル A(河床 + 10 m)を開ける",
            "sab": "階段が 1 つの河道。角のセル A と B(河床 + 10 m)を開ける"}[geom]
    rdesc = {"": "移流項の規則は既定", "4": "移流項の規則は、&list_enc の 4 つの値の組み合わせ"}[rule]
    L = []
    L.append("!======================================================================")
    L.append("! stairbank %s: %s。%s" % (name, desc, rdesc))
    L.append("!   %d × %d セル(Δx = %.0f m)。河床勾配 %.4f の 1 セル幅の河道(8 連結)。河道でないセルは、河床より" % (nx, ny, DX, SLOPE))
    L.append("!   %.0f m 高い壁(段・角のセルは %.0f m)。上流端から 2 つ目の河道のセルに、2,000 → 4,000 → 6,000 → 8,000 →" % (H_WALL, H_SHELF))
    L.append("!   10,000 → 8,000 → 6,000 → 4,000 → 2,000 m3/s を 30 分ずつ(最後の 2,000 m3/s は 90 分)与える(移りは 5 分)。")
    L.append("!   東辺は自由流出。検定は Check_stairbank.py。入力 sb_*.txt は make_stairbank.py が作る")
    L.append("!======================================================================")
    L.append("&list_sysparam\n  f_gridsystem = 0\n  dt = %g\n  t0 = 0\n  tt = %d\n  dt_disp = 3600\n  dt_file = %d\n  dt_recrd = %d\n"
             "  fn_geoinfo = '-'\n  fn_boundary = '-'\n  fn_record = '-'\n  fn_enc = '-'\n  dir_result = 'result_%s'\n  f_out_h = 1\n/\n"
             % (DT, T_END * 60, T_END * 60, REC, name))
    L.append("&list_enc\n" + "".join("  %s\n" % r for r in RULES[rule]) + "/\n")
    L.append("&list_geoinfo\n  nx = %d\n  ny = %d\n  dx = %.1f\n  dy = %.1f\n  f_ztype = 1\n  fn_z = 'sb_z_%s.txt'\n"
             "  fn_rw = 'sb_rw_%s.txt'   ! 河道マスク\n  f_rntype = 0\n  rn0 = %.2f               ! 河道でないセルの粗度\n"
             "  rn0_rw = %.2f            ! 河道マスクのセルの粗度\n/\n" % (nx, ny, DX, DX, geom, geom, RN_LAND, RN_RIVER))
    L.append("&list_bound_edge\n  f_bc_e = 1                ! 東辺は自由流出(河道の出口)\n/\n")
    s = "&list_bound_source\n  src_cell(:,1,1) = %d, %d   ! 流量を与えるセル(上流端から 2 つ目の河道のセル)\n" % path[1]
    for n, (t, q) in enumerate(hydrograph()):
        s += "  src_val(:,%d,1) = %g, %.1f\n" % (n + 1, t, q)
    L.append(s + "/\n")
    pb, ks = probes(name)
    s = "&list_record\n  pbxytype = 0\n" + "".join("  pbxy(:,%d) = %d, %d\n" % ((n + 1,) + p) for n, p in enumerate(pb))
    s += "  flxytype = 0\n  flxy(:,1) = %d, %d, %d, %d\n/\n" % transect(name)
    L.append(s)
    return "\n".join(L)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "names":
        print("\n".join(CASES))
    elif cmd == "geoms":
        print("\n".join(SHAPES))
    elif cmd in ("z", "rw"):
        nx, ny, z, rw, path, side = build(sys.argv[2])
        a, fmt = (z, "%.4f") if cmd == "z" else (rw, "%d")
        print("\n".join(" ".join(fmt % v for v in row) for row in a))
    elif cmd == "params":
        here = os.path.dirname(os.path.abspath(__file__))
        for name in CASES:
            with open(os.path.join(here, "param_%s.txt" % name), "w") as f:
                f.write(param(name))
    else:
        sys.exit("usage: make_stairbank.py names | geoms | z <geom> | rw <geom> | params")
