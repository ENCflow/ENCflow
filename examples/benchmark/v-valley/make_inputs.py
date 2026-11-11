#!/usr/bin/env python3
"""examples/benchmark/v-valley の入力と設定ファイルの生成(make が呼ぶ)。

  python3 make_inputs.py              全ケースの入力(data_<格子>/)と設定(param_<ケース>.txt)を書く
  python3 make_inputs.py 0.03 20 45   斜面の勾配 0.03・格子 20 m・向き 45° の入力と、その格子のケースの設定だけ書く

水路のない V 字谷。谷に沿う座標 (s, n) の式を各格子のセル中心で評価して地形を与える(補間しない)。
s は谷を下る向きの距離(上流端 0、下流端 L)、n は谷底の軸からの横断距離(正の側を「左岸側」と呼ぶ)。

  地形   z = Z_OUT + S_V (L − s) + S_S |n|。谷の勾配 S_V = 0.02 は固定、斜面の勾配 S_S を 0.01〜0.04 で変える。
         谷底は線(幅 0)で、S_S > S_V のとき最急勾配の向きは谷底より斜面側を向く
  範囲   長さ L = 1000 m、幅 2 × 810 m。上流端と両側の尾根は壁
  出口   下流端(s = L)の全幅の先 N_SEA セル分を海域マスク(標高 0 m・水深 H_SEA = 1 m に固定された吸い込み。
         入った水は消える)にする。海の水位 1 m は下流端の谷底(Z_OUT = 3 m)より低いので背水は生じない
  粗度   マニングの n = 0.1(一様)
  向き   θ = 45° では、谷底の軸 n = 0 が格子のセル中心を通るように(谷底は斜めの 1 列のセル)、かつ
         下流端の計測面がセル中心の列に重なるように格子の原点を置く

出力(data_s<S_S>_dx<Δx>_r<θ>/。入力ファイルは先頭行が北端):
  z.txt     地盤高 (m)     mask.txt  領域マスク(1: 計算する)     sw.txt  海域マスク(1: 吸い込みの海セル)
  hinit.txt 初期水深 (m)(海セルだけ H_SEA)
  size.txt  nx ny ox oy dx theta(図化で (s, n) へ戻すための格子の原点と向き)
設定(param_<ケース>.txt)は、注釈付きの雛形 param.txt(S_S = 0.03・10 m・0°・8 近傍)の格子・時間刻み・
計測・入出力の行と、4 近傍のケースで変える 1 行(p_diagratio)を差し替えて書く。雛形そのもののケースは
書かない(雛形の計測の行が計算値と違えば止まる)。
"""
import math
import os
import sys
import numpy as np

# ---------------------------------------------------------------- 幾何(谷に沿う座標、m)
L = 1000.0               # 谷の長さ(上流端 s = 0、下流端 s = L)
WH = 810.0               # 谷底の軸から尾根まで(片側)
S_V = 0.02               # 谷の勾配(固定)
S_S_LIST = (0.01, 0.02, 0.03, 0.04)   # 斜面の勾配(谷底へ向かう)
S_S_BASE = 0.03          # 格子を変えて比べるときの斜面の勾配
Z_OUT = 3.0              # 下流端の谷底の標高(海の水位 H_SEA より高く)
H_SEA = 1.0              # 海セルの水深 = 水位 (m)(標高 0 m に固定)
RN = 0.1                 # マニングの粗度(一様)
N_SEA = 2                # 下流端の先の海セルの長さ(セル数)
# ---------------------------------------------------------------- 降雨・時間
P_MMH = 10.8             # 降雨強度 (mm/h)
T_RAIN = 60.0            # 降雨の継続時間 (min)
T_END = 360.0            # 計算時間 (min)(n = 0.1 の薄い流れは遅く、谷が排水し切るまで 6 時間)
DT_PER_DX = 0.1          # 時間刻み dt = 0.1 Δx (s)
# ---------------------------------------------------------------- ケース
DXS = (20.0, 10.0, 5.0)
DX_BASE = 10.0
THETAS = (0.0, 45.0)
VARIANTS = {"": {}, "_4nb": {"p_diagratio": "0.0"}}


def grid_name(ss, dx, theta):
    return f"s{round(ss * 100):02d}_dx{dx:g}_r{theta:g}"


def case_name(ss, dx, theta, suffix=""):
    return grid_name(ss, dx, theta) + suffix


def grids():
    """計算する格子 (S_S, Δx, θ): 10 m で斜面の勾配 4 通り × 2 つの向き、S_S = 0.03 で 20・5 m × 2 つの向き。"""
    out = [(ss, DX_BASE, th) for ss in S_S_LIST for th in THETAS]
    out += [(S_S_BASE, dx, th) for dx in DXS if dx != DX_BASE for th in THETAS]
    return out


def cases_of(ss, dx, theta):
    """その格子で計算するケースの接尾辞。4 近傍は 45° の全部と、0° の S_S = 0.03・10 m(向きに依らないことの確認)。"""
    out = [""]
    if theta == 45.0 or (ss == S_S_BASE and dx == DX_BASE):
        out.append("_4nb")
    return out


BASE = case_name(S_S_BASE, DX_BASE, 0.0)   # param.txt そのもののケース


# ---------------------------------------------------------------- 格子
def frame(dx, theta):
    """格子の大きさと原点(ox, oy)。s = (x − ox) cosθ − (y − oy) sinθ、n = (x − ox) sinθ + (y − oy) cosθ。
    θ = 0 では谷の長方形の角が格子線に乗る。θ = 45° では谷底の軸 n = 0 がセル中心を通り、下流端の
    計測面(s = L − Δx/(2√2))がセル中心の列に重なるように原点を選ぶ(v-shaped と同じ)。"""
    th = math.radians(theta)
    c, sn = math.cos(th), math.sin(th)
    s_end = L + N_SEA * dx
    corners = [(s, n) for s in (0.0, s_end) for n in (-WH, WH)]
    xs = [s * c + n * sn for s, n in corners]
    ys = [-s * sn + n * c for s, n in corners]
    ox, oy = dx - min(xs), dx - min(ys)
    if theta == 45.0:
        u = (2 * ox + math.sqrt(2) * L) / dx - 0.5
        v = (2 * oy - math.sqrt(2) * L) / dx + 0.5
        u = math.ceil(u) if math.ceil(u) % 2 == 1 else math.ceil(u) + 1
        v = math.ceil(v) if math.ceil(v) % 2 == 1 else math.ceil(v) + 1
        ox = ((u + 0.5) * dx - math.sqrt(2) * L) / 2
        oy = ((v - 0.5) * dx + math.sqrt(2) * L) / 2
    elif theta != 0.0:
        sys.exit("向きは 0 か 45 だけ")
    nx = int(math.ceil((max(xs) + ox) / dx - 1e-9)) + 1
    ny = int(math.ceil((max(ys) + oy) / dx - 1e-9)) + 1
    return nx, ny, ox, oy, c, sn, s_end


def to_sn(dx, theta):
    nx, ny, ox, oy, c, sn, _ = frame(dx, theta)
    x = (np.arange(nx) + 0.5) * dx - ox
    y = (np.arange(ny) + 0.5) * dx - oy
    X, Y = np.meshgrid(x, y)
    return X * c - Y * sn, X * sn + Y * c


def classify(dx, theta):
    """セルの種類: 0 領域外、1 谷(斜面と谷底)、4 海(吸い込み)。"""
    _, _, _, _, _, _, s_end = frame(dx, theta)
    s, n = to_sn(dx, theta)
    kind = np.zeros(s.shape, dtype=int)
    inside = np.abs(n) < WH
    kind[inside & (s >= 0.0) & (s < L)] = 1
    kind[inside & (s >= L) & (s < s_end)] = 4
    return kind, s, n


def terrain(ss, s, n):
    return Z_OUT + S_V * (L - s) + ss * np.abs(n)


def grid(ss, dx, theta):
    kind, s, n = classify(dx, theta)
    z = np.where(kind == 1, terrain(ss, s, n), 0.0)
    hinit = np.where(kind == 4, H_SEA, 0.0)
    return {"z": z, "mask": (kind > 0).astype(int), "sw": (kind == 4).astype(int), "hinit": hinit}, kind, s, n


# ---------------------------------------------------------------- 計測(セル番号。ENCflow は西端の列・北端の行が 1)
def ij_of(dx, theta, s0, n0):
    nx, ny, ox, oy, c, sn, _ = frame(dx, theta)
    x = s0 * c + n0 * sn + ox
    y = -s0 * sn + n0 * c + oy
    return int(math.floor(x / dx)), int(math.floor(y / dx))


def to_enc(i, j, ny):
    return i + 1, ny - j


def records(dx, theta, kind, s, n):
    """下流端の計測面(全幅)と、谷底の軸のプローブ 2 つ(下流端と中央)のセル番号。"""
    ny, nx = kind.shape
    i0, j0 = ij_of(dx, theta, L - dx / 2 / (math.sqrt(2) if theta == 45.0 else 1.0), 0.0)
    assert kind[j0, i0] == 1
    if theta == 0.0:
        sel = (np.arange(nx)[None, :] == i0) & (kind == 1)
    else:
        I, J = np.meshgrid(np.arange(nx), np.arange(ny))
        sel = ((I - J) == (i0 - j0)) & (kind == 1)
    jj, ii = np.nonzero(sel)
    k = np.argsort(n[jj, ii])
    outlet = (*to_enc(ii[k[0]], jj[k[0]], ny), *to_enc(ii[k[-1]], jj[k[-1]], ny))
    p1 = to_enc(i0, j0, ny)
    # 谷底の軸に最も近いセルの列(|n| が最小。θ = 0 の 10・5 m では軸が格子線に乗るので n > 0 の側)のうち
    # L/2 に最も近いセル
    valley = kind == 1
    nmin = np.abs(n[valley]).min()
    axis = valley & (np.abs(np.abs(n) - nmin) < 1e-6) & (n >= -1e-6)
    jj, ii = np.nonzero(axis)
    km = np.argmin(np.abs(s[jj, ii] - L / 2))
    p2 = to_enc(ii[km], jj[km], ny)
    return outlet, p1, p2


# ---------------------------------------------------------------- 書き出し
def write_grid(ss, dx, theta):
    out, kind, s, n = grid(ss, dx, theta)
    nx, ny, ox, oy, _, _, _ = frame(dx, theta)
    ddir = f"data_{grid_name(ss, dx, theta)}"
    os.makedirs(ddir, exist_ok=True)
    for key, g in out.items():
        fmt = "%d" if key in ("mask", "sw") else ("%.4f" if key == "z" else "%.3f")
        np.savetxt(os.path.join(ddir, key + ".txt"), g[::-1], fmt=fmt)   # 先頭行が北端
    with open(os.path.join(ddir, "size.txt"), "w") as f:
        f.write(f"{nx} {ny} {ox:.6f} {oy:.6f} {dx:g} {theta:g}\n")
    outlet, p1, p2 = records(dx, theta, kind, s, n)
    naxis = int(((kind == 1) & (np.abs(n) < 1e-6)).sum())
    print(f"{grid_name(ss, dx, theta)}: nx = {nx}, ny = {ny}, 谷 {int((kind == 1).sum())} 海 {int((kind == 4).sum())} セル"
          f"(面積 {(kind == 1).sum() * dx * dx / 1e6:.4f} km²、谷底の軸上のセル {naxis})")
    return ddir, nx, ny, outlet, p1, p2


def write_param(name, ddir, dx, nx, ny, outlet, p1, p2, variant):
    rep = {"dt": f"{DT_PER_DX * dx:g}", "dx": f"{dx:g}", "dy": f"{dx:g}", "nx": f"{nx}", "ny": f"{ny}",
           "dir_data": f"'{ddir}'", "dir_result": f"'result_{name}'",
           "flxy(:,1)": ", ".join(str(v) for v in outlet),
           "pbxy(:,1)": ", ".join(str(v) for v in p1), "pbxy(:,2)": ", ".join(str(v) for v in p2)}
    rep.update(variant)
    lines = open("param.txt").read().splitlines()
    out = [f"! このファイルは make_inputs.py が param.txt から生成する(ケース {name})。編集は param.txt と make_inputs.py で"]
    done = set()
    for line in lines:
        key = line.split("=")[0].strip() if "=" in line and not line.lstrip().startswith("!") else None
        if key in rep:
            head, _, tail = line.partition("=")
            val_comment = tail.split("!", 1)
            if name == BASE and val_comment[0].strip().replace(" ", "") != rep[key].replace(" ", ""):
                sys.exit(f"param.txt の {key} = {val_comment[0].strip()} は計算値 {rep[key]} と違う")
            comment = "!" + val_comment[1] if len(val_comment) > 1 else ""
            line = f"{head}= {rep[key]}"
            if comment:
                line = f"{line:<28}{comment}"
            done.add(key)
        out.append(line)
    missing = set(rep) - done
    if missing:
        sys.exit(f"param.txt に {sorted(missing)} の行がありません")
    if name != BASE:
        with open(f"param_{name}.txt", "w") as f:
            f.write("\n".join(out) + "\n")


def main():
    args = sys.argv[1:]
    todo = [(float(args[0]), float(args[1]), float(args[2]))] if args else grids()
    for ss, dx, th in todo:
        ddir, nx, ny, outlet, p1, p2 = write_grid(ss, dx, th)
        for suf in cases_of(ss, dx, th):
            write_param(case_name(ss, dx, th, suf), ddir, dx, nx, ny, outlet, p1, p2, VARIANTS[suf])


if __name__ == "__main__":
    main()
