#!/usr/bin/env python3
# examples/ashfall_lahar の補足実験(谷の向きと格子): 入力生成(make rotated が呼ぶ)
#   谷(make_init.py と同じ地形・降灰。堰堤なし)を格子に沿わせた場合(0°)と 45° 傾けた
#   場合の 2 通りを data_rot0/・data_rot45/ に書く。谷に沿う座標 x'(0〜600 m)・横断 y'
#   (0〜150 m)の長方形の外は領域外、谷の下流端の外側 x' = 600〜615 m は海域マスク
#   (水位 0 m の吸い込み。東辺の自由流出の代わり。0° と 45° で同じ扱いにするため)
#     z.txt, ash.txt  地表と降灰厚(領域外は 0)
#     mask.txt        領域マスク(1: 計算する、0: 領域外)
#     sw.txt          海域マスク(1: 海)
#     xr.txt, yr.txt  各セル中心の谷沿いの座標 x'、y'(図化用)
#     size.txt        nx ny と、格子の原点のずれ ox oy(図化で谷沿いの座標へ戻す)
import math
import os
from make_init import DX, z_ground, ash

LX, LY, LSEA = 600.0, 150.0, 15.0          # 谷の長さ・幅、下流端の海の帯の幅 (m)


def frame(theta_deg):
    """格子の大きさと、谷沿いの座標 → 格子座標の変換の原点。"""
    th = math.radians(theta_deg)
    c, s = math.cos(th), math.sin(th)
    xs = [xr * c + yr * s for xr in (0, LX + LSEA) for yr in (0, LY)]
    ys = [-xr * s + yr * c for xr in (0, LX + LSEA) for yr in (0, LY)]
    ox, oy = DX - min(xs), DX - min(ys)
    nx = int(math.ceil((max(xs) - min(xs)) / DX - 1e-9)) + 2
    ny = int(math.ceil((max(ys) - min(ys)) / DX - 1e-9)) + 2
    return nx, ny, ox, oy, c, s


def grid(theta_deg):
    nx, ny, ox, oy, c, s = frame(theta_deg)
    out = {k: [[0.0] * nx for _ in range(ny)] for k in ("z", "ash", "mask", "sw", "xr", "yr")}
    for j in range(ny):                      # j = 0 が南端(書き出しで北端を先頭にする)
        y = (j + 0.5) * DX - oy
        for i in range(nx):
            x = (i + 0.5) * DX - ox
            xr, yr = x * c - y * s, x * s + y * c       # 谷沿いの座標
            out["xr"][j][i], out["yr"][j][i] = xr, yr
            if 0.0 <= xr < LX + LSEA and 0.0 <= yr < LY:
                out["mask"][j][i] = 1
                if xr < LX:
                    out["z"][j][i] = z_ground(xr, yr) + ash(xr, yr)
                    out["ash"][j][i] = ash(xr, yr)
                else:
                    out["sw"][j][i] = 1
    return nx, ny, ox, oy, out


def main():
    for th in (0, 45):
        nx, ny, ox, oy, out = grid(th)
        d = f"data_rot{th}"
        os.makedirs(d, exist_ok=True)
        for k, g in out.items():
            fmt = "%d" if k in ("mask", "sw") else "%.4f"
            with open(os.path.join(d, k + ".txt"), "w") as f:
                for row in reversed(g):      # 入力ファイルは先頭行が北端
                    f.write(" ".join(fmt % v for v in row) + "\n")
        with open(os.path.join(d, "size.txt"), "w") as f:
            f.write(f"{nx} {ny} {ox:.6f} {oy:.6f}\n")
        print(f"theta = {th}: nx = {nx}, ny = {ny}")


if __name__ == "__main__":
    main()
