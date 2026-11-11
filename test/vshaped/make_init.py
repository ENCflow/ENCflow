#!/usr/bin/env python3
"""test/vshaped の入力を作る(Run.sh が呼ぶ。Python の標準ライブラリだけ)。

  python3 make_init.py        data_r0/(向き 0°)と data_r45/(45°)に z.txt・rn.txt・mask.txt・sw.txt・
                              hinit.txt・catch.txt を書き、param_r0.txt・param_r45.txt の格子と計測の行が
                              この幾何と合っているか確かめる(違えば終了コード 1)

幾何は examples/benchmark/v-shaped/make_inputs.py と同じ式(そちらは NumPy、こちらは標準ライブラリの
独立した実装で、20 m の格子だけ)。流域に沿う座標 (s, n): s は水路に沿って下流へ(上流端 0、出口 L)、
n は水路の軸からの横断距離。斜面 2 × 800 m(勾配 0.05、水路方向 0)、水路 20 m × 1000 m(勾配 0.02、
上流端で斜面の脚より 1 m、出口で 21 m 低い。出口の床 8 m)。流域の下流に同じ断面の区間(斜面と水路)を
200 m 続け、その先に水路だけの延長 3 セルと海セル(吸い込み)3 セルを置く(斜面が終わる所の手前の数セルで
水路の水深が上がる影響を、出口の計測面から離すため)。地形・粗度・マスクはセル中心で評価する。45° では
水路の軸がセル中心を通り、出口の計測面がセル中心の斜めの列に重なるように格子の原点を置く。
プローブ P2 は左岸側の斜面で水路の軸から 72 m(縁から 62 m)に最も近い列の中央(水路に接する 1〜2 列は水路との辺の
粗度で水が溜まるので、その外で理論と比べる)。
catch.txt は流域(斜面と水路。下流の区間・延長・海を除く)のセルが 1 で、Check_vshaped.py が収支に使う。
"""
import math
import os
import re
import sys

L, W, B = 1000.0, 20.0, 800.0        # 水路の長さ・幅、斜面の幅
S_C, S_S, S_O = 0.02, 0.05, 0.0      # 水路の縦断勾配、斜面の横断勾配、斜面の水路方向の勾配
D_UP, Z_OUT, H_SEA = 1.0, 8.0, 1.0   # 上流端の水路の深さ、出口の水路床の標高、海セルの水深
N_S, N_C = 0.015, 0.15               # 粗度(斜面・水路)
L_EXT = 200.0                        # 流域の下流に同じ断面を続ける区間の長さ (m)
N_P2 = 72.0                          # P2 を置く列の水路の軸からの距離の目標 (m)
N_EXT, N_SEA = 3, 3                  # その先の水路だけの延長と海のセル数
DX = 20.0
WH = W / 2 + B


def frame(theta):
    th = math.radians(theta)
    c, sn = math.cos(th), math.sin(th)
    s_end = L + L_EXT + (N_EXT + N_SEA) * DX
    corners = [(s, n) for s in (0.0, s_end) for n in (-WH, WH)]
    xs = [s * c + n * sn for s, n in corners]
    ys = [-s * sn + n * c for s, n in corners]
    ox, oy = DX - min(xs), DX - min(ys)
    if theta == 45.0:
        u = (2 * ox + math.sqrt(2) * L) / DX - 0.5
        v = (2 * oy - math.sqrt(2) * L) / DX + 0.5
        u = math.ceil(u) if math.ceil(u) % 2 == 1 else math.ceil(u) + 1
        v = math.ceil(v) if math.ceil(v) % 2 == 1 else math.ceil(v) + 1
        ox = ((u + 0.5) * DX - math.sqrt(2) * L) / 2
        oy = ((v - 0.5) * DX + math.sqrt(2) * L) / 2
    nx = int(math.ceil((max(xs) + ox) / DX - 1e-9)) + 1
    ny = int(math.ceil((max(ys) + oy) / DX - 1e-9)) + 1
    return nx, ny, ox, oy, c, sn, s_end


def kind_of(s, n, s_end):
    """0 領域外、1 斜面、2 水路(ここまでが流域)、3 水路の延長(下流の区間とその先)、4 海、5 下流の区間の斜面。"""
    if abs(n) >= WH or s < 0.0 or s >= s_end:
        return 0
    if abs(n) < W / 2:
        if s < L:
            return 2
        return 3 if s < L + L_EXT + N_EXT * DX else 4
    return 1 if s < L else (5 if s < L + L_EXT else 0)


def build(theta):
    nx, ny, ox, oy, c, sn, s_end = frame(theta)
    cells = {}          # (i, j) → (kind, s, n)。j は南端が 0
    for j in range(ny):
        y = (j + 0.5) * DX - oy
        for i in range(nx):
            x = (i + 0.5) * DX - ox
            s = x * c - y * sn
            n = x * sn + y * c
            cells[(i, j)] = (kind_of(s, n, s_end), s, n)
    return nx, ny, cells


def to_enc(i, j, ny):
    return i + 1, ny - j


def records(theta, nx, ny, cells):
    """出口の計測面(全幅)・斜面の脚の計測線・プローブ 2 点のセル番号(examples の make_inputs.records と同じ規則。
    P2 は左岸側の斜面で軸から N_P2 に最も近い列の、s = L/2 に最も近いセル)。"""
    # 出口の列: 45° では s = L − Δx/(2√2) の斜めの列(i − j 一定)、0° では s = L − Δx/2 の列
    s_face = L - DX / 2 / (math.sqrt(2) if theta == 45.0 else 1.0)
    nx_, ny_, ox, oy, c, sn, _ = frame(theta)
    x = s_face * c + ox
    y = -s_face * sn + oy
    i0, j0 = int(math.floor(x / DX)), int(math.floor(y / DX))
    assert cells[(i0, j0)][0] == 2
    if theta == 45.0:
        col = [(i, j) for (i, j), (k, s, n) in cells.items() if k > 0 and i - j == i0 - j0]
    else:
        col = [(i, j) for (i, j), (k, s, n) in cells.items() if k > 0 and i == i0]
    col.sort(key=lambda ij: cells[ij][2])
    outlet = to_enc(*col[0], ny) + to_enc(*col[-1], ny)
    hill = [(ij, v) for ij, v in cells.items() if v[0] == 1 and v[2] > 0]
    nmin = min(v[2] for _, v in hill)
    foot = [ij for ij, v in hill if abs(v[2] - nmin) < 1e-6]
    foot.sort(key=lambda ij: cells[ij][1])
    footline = to_enc(*foot[0], ny) + to_enc(*foot[-1], ny)
    p1 = to_enc(i0, j0, ny)
    n2 = min(set(round(v[2], 6) for _, v in hill), key=lambda v: (abs(v - N_P2), -v))
    second = [ij for ij, v in hill if abs(v[2] - n2) < 1e-6]
    km = min(second, key=lambda ij: abs(cells[ij][1] - L / 2))
    p2 = to_enc(*km, ny)
    return outlet, footline, p1, p2


def write(theta, name):
    nx, ny, cells = build(theta)
    os.makedirs(name, exist_ok=True)
    files = {k: open(os.path.join(name, k + ".txt"), "w") for k in ("z", "rn", "mask", "sw", "hinit", "catch")}
    for j in range(ny - 1, -1, -1):          # 先頭行が北端
        row = {k: [] for k in files}
        for i in range(nx):
            kind, s, n = cells[(i, j)]
            if kind in (1, 5):
                z = Z_OUT + S_C * L + D_UP + S_S * (abs(n) - W / 2) + S_O * (L - s)
            elif kind in (2, 3):
                z = Z_OUT + S_C * (L - s)
            else:
                z = 0.0
            row["z"].append("%.4f" % z)
            row["rn"].append("%.3f" % (N_S if kind in (1, 5) else N_C))
            row["mask"].append("1" if kind > 0 else "0")
            row["sw"].append("1" if kind == 4 else "0")
            row["hinit"].append("%.3f" % (H_SEA if kind == 4 else 0.0))
            row["catch"].append("1" if kind in (1, 2) else "0")
        for k, f in files.items():
            f.write(" ".join(row[k]) + "\n")
    for f in files.values():
        f.close()
    ncatch = sum(1 for v in cells.values() if v[0] in (1, 2))
    return nx, ny, records(theta, nx, ny, cells), ncatch


def check_param(path, nx, ny, rec):
    """param の格子と計測の行が幾何と合っているか。"""
    want = {"nx": str(nx), "ny": str(ny),
            "flxy(:,1)": ", ".join(str(v) for v in rec[0]), "flxy(:,2)": ", ".join(str(v) for v in rec[1]),
            "pbxy(:,1)": ", ".join(str(v) for v in rec[2]), "pbxy(:,2)": ", ".join(str(v) for v in rec[3])}
    bad = []
    for line in open(path):
        if "=" not in line or line.lstrip().startswith("!"):
            continue
        key, _, tail = line.partition("=")
        key = key.strip()
        if key in want:
            val = tail.split("!")[0].strip().replace(" ", "")
            if val != want[key].replace(" ", ""):
                bad.append(f"{path}: {key} = {val} (期待 {want[key]})")
            want.pop(key)
    bad += [f"{path}: {k} の行がない" for k in want]
    return bad


def main():
    bad = []
    for theta, name, param in ((0.0, "data_r0", "param_r0.txt"), (45.0, "data_r45", "param_r45.txt")):
        nx, ny, rec, ncatch = write(theta, name)
        print(f"{name}: nx = {nx}, ny = {ny}, 流域 {ncatch} セル({ncatch * DX * DX / 1e6:.4f} km²), "
              f"出口 {rec[0]}, 脚 {rec[1]}, P1 {rec[2]}, P2 {rec[3]}")
        bad += check_param(param, nx, ny, rec)
    if bad:
        print("\n".join(bad))
        sys.exit(1)


if __name__ == "__main__":
    main()
