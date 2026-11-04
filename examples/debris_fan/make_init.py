#!/usr/bin/env python3
"""examples/debris_fan の入力と設定ファイルの生成(make が呼ぶ)。

  python3 make_init.py            CASES のすべてのケースの入力(data_<case>/)と設定(param_<case>.txt)を書く
  python3 make_init.py 10 22.5    格子間隔 10 m・向き 22.5° の 8 近傍のケースだけ書く(4 を足すと 4 近傍)

地形・崩壊深・初期水深は、谷に沿う座標の解析式で与える。s は谷を下る向きの距離(上流端 0)、
n は谷を横切る向き(谷筋 0、正が北岸 = 崩壊斜面の側)。格子に対する谷の向き θ と格子間隔 Δx を
変えても、同じ式を各格子のセル中心で標本化するので、補間の誤差は入らない(違いは格子の離散化だけ)。
谷の外枠(s・n の長方形)の外は領域外、下流端の外側の帯は海域マスク(標高 0 m の吸い込み)。

  地形   山体(谷底からの比高 H_R)に谷底幅 WF・谷壁 35° の谷を刻む。谷底の縦断勾配は上流端 0.25 から
         谷の出口(s = L_V)の 0.12 へ直線的に緩む(凹形)。出口の先は扇頂を中心とする円錐状の扇状地で、
         半径方向の勾配が 0.12 から 0.03(半径 L_F)へ緩む。山体は出口の線から 35° の山麓の崖で終わる。
  崩壊   北岸の谷壁(35°)の、谷底から 10〜150 m ほど上までの楕円(谷沿い 80 m × 斜面方向に水平 160 m)。
         深さは放物面(中心で最大)で、体積が V0 になるように格子ごとに規格化する(粗い格子でも同じ土量)。
         崩壊深の分だけ土層厚 sd を与える(その下は不侵食の基盤)。
  水     崩壊土塊は飽和(間隙水 λD)で、さらに谷の水・地下水を取り込んで濃度 C0 の土石流として流れ
         出すとみなし、その差の水を崩壊域の初期水深に与える(h = D((1 − λ)/C0 − 1))。
  住宅地 扇状地の扇頂から 100〜400 m、軸から ±60° の扇形に 30 m 間隔で並ぶ家屋の位置(houses.txt。
         計算には使わず、図化で流動深・流体力・堆積厚を読む)。

出力(data_<case>/。入力ファイルは先頭行が北端):
  z.txt        地盤高 (m)
  sd.txt       土層厚 (m)(崩壊深。それ以外 0)
  dbinit.txt   崩壊深 (m)(fn_dbinit)
  hinit.txt    初期水深 (m)(崩壊域の水)
  mask.txt     領域マスク(1: 計算する)
  sw.txt       海域マスク(1: 下流端の吸い込み)
  size.txt     nx ny ox oy dx theta(図化で谷沿いの座標へ戻すための格子の原点と向き)
houses.txt     家屋の位置 s n (m)(ケースによらない)
"""
import math
import os
import sys
import numpy as np

# ---------------------------------------------------------------- 地形(谷沿いの座標、m)
L_V = 1000.0             # 上流端から谷の出口(扇頂)までの谷の長さ
L_F = 800.0              # 扇頂から下流端までの扇状地の長さ(軸上)
L_SEA = 40.0             # 下流端の外側の吸い込みの帯の幅
W = 800.0                # 領域の幅(n = −W/2 〜 W/2)
S_TOP, S_APX, S_END = 0.32, 0.18, 0.035  # 谷底の勾配(上流端・扇頂)、扇状地の端の勾配
Z_END = 5.0              # 扇状地の下流端(軸上)の標高
WF = 30.0                # 谷底の幅
TAN_W = 0.7              # 谷壁の勾配(35°)
H_R = 160.0              # 谷底から尾根までの比高
H_F, L_T = 40.0, 300.0   # 尾根の比高を谷の出口の L_T 手前から下げ、出口で H_F にする(山麓の線が谷に
                         #   ほぼ直交するように。崖の脚は出口の線から 50 m 以内)
TAN_FRONT = 0.7          # 山麓の崖の勾配(35°)
# ---------------------------------------------------------------- 崩壊(谷沿いの座標、m)
S_C, N_C = 250.0, 100.0  # 崩壊の楕円の中心(谷壁の脚は n = WF/2 = 15 m)
A_S, A_N = 40.0, 80.0    # 楕円の半径(谷沿い、斜面方向の水平距離)
V0 = 1.0e5               # 崩壊土量 (m³。かさ体積 = 崩壊深の体積)
LAMBDA = 0.4             # 崩壊土塊と堆積物の空隙率(param の fluv_porosity と対)
C0 = 0.45                # 流れ出す土石流の濃度(崩壊域の初期水深を決める)
SD_MARGIN = 0.05         # 崩壊域の土層厚の余裕 (m)。同じ更新の中で侵食が流動化より先に働き、
                         #   崩壊域の水が最初の数ステップで削るぶん(数 mm)で崩壊深が切られないように
# ---------------------------------------------------------------- 住宅地(扇頂からの距離・軸からの角度)
R_H1, R_H2, ANG_H, D_H = 100.0, 400.0, 60.0, 30.0

# ---------------------------------------------------------------- ケース
DXS = (40.0, 20.0, 10.0, 5.0)      # 3 つの向きで比べる格子間隔(8 近傍・4 近傍とも)
DX_REF = 2.5                        # 収束の確認用の格子(谷の向き 0° だけ。8 近傍が比較の基準)
THETAS = (0.0, 22.5, 45.0)
DT_PER_DX = 0.01         # 時間刻み dt = 0.01 Δx(s。Δx = 5 m で 0.05 s。クーラン数が格子によらずそろう)


def case_name(dx, theta, nb=8):
    s = f"dx{dx:g}_r{theta:g}".replace(".", "p")
    return s if nb == 8 else s + "_4nb"


CASES = ([(dx, th, nb) for nb in (8, 4) for dx in DXS for th in THETAS]
         + [(DX_REF, 0.0, 8), (DX_REF, 0.0, 4)])
BASE = case_name(5.0, 0.0)   # param.txt そのもののケース


# ---------------------------------------------------------------- 解析式
def z_axis(xi):
    """谷筋〜扇状地の軸の縦断の標高(ξ = 上流端からの軸に沿う距離)。勾配が区間ごとに 1 次式で緩む。"""
    xi = np.asarray(xi, dtype=float)
    kf = (S_END - S_APX) / L_F
    kv = (S_APX - S_TOP) / L_V
    z_apx = Z_END + S_APX * L_F + 0.5 * kf * L_F ** 2
    u = np.clip(xi - L_V, 0.0, None)
    uf = np.minimum(u, L_F)
    zf = Z_END + S_APX * (L_F - uf) + 0.5 * kf * (L_F ** 2 - uf ** 2) - S_END * np.clip(u - L_F, 0.0, None)
    xv = np.minimum(xi, L_V)
    zv = z_apx + S_TOP * (L_V - xv) + 0.5 * kv * (L_V ** 2 - xv ** 2)
    return np.where(xi > L_V, zf, zv)


def slope_axis(xi):
    xi = np.asarray(xi, dtype=float)
    sv = S_TOP + (S_APX - S_TOP) * np.clip(xi, 0.0, L_V) / L_V
    sf = S_APX + (S_END - S_APX) * np.clip(xi - L_V, 0.0, L_F) / L_F
    return np.where(xi > L_V, sf, sv)


def terrain(s, n):
    """地盤高。山体(谷を刻んだ尾根)と扇状地(扇頂を中心とする円錐)の高い方。"""
    a = np.abs(n)
    relief = H_R + (H_F - H_R) * np.clip((s - (L_V - L_T)) / L_T, 0.0, 1.0)
    wall = np.minimum(TAN_W * np.clip(a - WF / 2, 0.0, None), relief)
    zv = np.where(s <= L_V, z_axis(s), z_axis(L_V) - S_APX * (s - L_V))
    z_mtn = zv + wall - TAN_FRONT * np.clip(s - L_V, 0.0, None)
    r = np.hypot(s - L_V, n)
    z_fan = z_axis(L_V + r)
    return np.maximum(z_mtn, z_fan)


def collapse_shape(s, n):
    """崩壊深の形(放物面。中心 1、楕円の縁 0)。"""
    rho2 = ((s - S_C) / A_S) ** 2 + ((n - N_C) / A_N) ** 2
    return np.clip(1.0 - rho2, 0.0, None)


def houses():
    """家屋の位置 (s, n)。扇頂から R_H1〜R_H2 の距離・軸から ±ANG_H° の扇形に D_H 間隔。"""
    out = []
    for s in np.arange(L_V + D_H / 2, L_V + R_H2 + 1e-9, D_H):
        for n in np.arange(-R_H2, R_H2 + 1e-9, D_H):
            r = math.hypot(s - L_V, n)
            if R_H1 <= r <= R_H2 and abs(math.degrees(math.atan2(n, s - L_V))) <= ANG_H and abs(n) <= W / 2 - 40.0:
                out.append((s, n))
    return np.array(out)


# ---------------------------------------------------------------- 格子
def frame(dx, theta):
    """格子の大きさと、谷沿いの座標 ↔ 格子座標の変換の原点(外枠の長方形の外側に 1 セルの余白)。"""
    th = math.radians(theta)
    c, sn = math.cos(th), math.sin(th)
    corners = [(s, n) for s in (0.0, L_V + L_F + L_SEA) for n in (-W / 2, W / 2)]
    xs = [s * c + n * sn for s, n in corners]
    ys = [-s * sn + n * c for s, n in corners]
    ox, oy = dx - min(xs), dx - min(ys)
    nx = int(math.ceil((max(xs) - min(xs)) / dx - 1e-9)) + 2
    ny = int(math.ceil((max(ys) - min(ys)) / dx - 1e-9)) + 2
    return nx, ny, ox, oy, c, sn


def to_sn(dx, theta):
    """各セル中心の谷沿いの座標 (s, n)。配列の行 0 が南端。"""
    nx, ny, ox, oy, c, sn = frame(dx, theta)
    x = (np.arange(nx) + 0.5) * dx - ox
    y = (np.arange(ny) + 0.5) * dx - oy
    X, Y = np.meshgrid(x, y)
    return X * c - Y * sn, X * sn + Y * c


def grid(dx, theta):
    nx, ny, ox, oy, _, _ = frame(dx, theta)
    s, n = to_sn(dx, theta)
    inside = (s >= 0.0) & (s < L_V + L_F + L_SEA) & (n >= -W / 2) & (n < W / 2)
    sea = inside & (s >= L_V + L_F)
    land = inside & ~sea
    z = np.where(land, terrain(s, n), 0.0)
    shape = np.where(land, collapse_shape(s, n), 0.0)
    d = shape * V0 / (shape.sum() * dx * dx)          # 体積を V0 に規格化
    h = d * ((1.0 - LAMBDA) / C0 - 1.0)
    sd = np.where(d > 0.0, d + SD_MARGIN, 0.0)
    out = {"z": z, "sd": sd, "dbinit": d, "hinit": h,
           "mask": inside.astype(int), "sw": sea.astype(int)}
    return nx, ny, ox, oy, out


def write_case(dx, theta, nb):
    name = case_name(dx, theta, nb)
    nx, ny, ox, oy, out = grid(dx, theta)
    ddir = f"data_{case_name(dx, theta)}"               # 4 近傍は同じ格子の入力を共有
    os.makedirs(ddir, exist_ok=True)
    for k, g in out.items():
        fmt = "%d" if k in ("mask", "sw") else "%.4f"
        np.savetxt(os.path.join(ddir, k + ".txt"), g[::-1], fmt=fmt)   # 先頭行が北端
    with open(os.path.join(ddir, "size.txt"), "w") as f:
        f.write(f"{nx} {ny} {ox:.6f} {oy:.6f} {dx:g} {theta:g}\n")
    write_param(name, ddir, dx, nx, ny, nb)
    vol = out["dbinit"].sum() * dx * dx
    print(f"{name}: nx = {nx}, ny = {ny}, cells = {int(out['mask'].sum())}, "
          f"D max = {out['dbinit'].max():.2f} m, V = {vol:.0f} m3")


def write_param(name, ddir, dx, nx, ny, nb):
    """param.txt(Δx = 5 m・0° の注釈付きの雛形)の格子・時間刻み・入出力の行を差し替えて書く。
    雛形そのもののケース(BASE)は param.txt を使うので書かない。"""
    if name == BASE:
        return
    rep = {"dt": f"{DT_PER_DX * dx:g}", "lx": f"{nx * dx:.1f}", "ly": f"{ny * dx:.1f}",
           "nx": f"{nx}", "ny": f"{ny}", "dir_data": f"'{ddir}'", "dir_result": f"'result_{name}'"}
    if nb == 4:
        rep["p_diagratio"] = "0.0"
    lines = open("param.txt").read().splitlines()
    out = [f"! このファイルは make_init.py が param.txt から生成する(ケース {name})。編集は param.txt と make_init.py で"]
    done = set()
    for line in lines:
        key = line.split("=")[0].strip() if "=" in line and not line.lstrip().startswith("!") else None
        if key in rep:
            head, _, tail = line.partition("=")
            val_comment = tail.split("!", 1)
            comment = "!" + val_comment[1] if len(val_comment) > 1 else ""
            line = f"{head}= {rep[key]}"
            if comment:
                line = f"{line:<28}{comment}"
            done.add(key)
        out.append(line)
    missing = set(rep) - done
    if missing:
        sys.exit(f"param.txt に {sorted(missing)} の行がありません")
    with open(f"param_{name}.txt", "w") as f:
        f.write("\n".join(out) + "\n")


def main():
    args = sys.argv[1:]
    if args:
        dx, th = float(args[0]), float(args[1])
        nb = int(args[2]) if len(args) > 2 else 8
        cases = [(dx, th, nb)]
    else:
        cases = CASES
    for dx, th, nb in cases:
        write_case(dx, th, nb)
    np.savetxt("houses.txt", houses(), fmt="%.1f", header="s n (m)  家屋の位置(谷沿いの座標)")


if __name__ == "__main__":
    main()
