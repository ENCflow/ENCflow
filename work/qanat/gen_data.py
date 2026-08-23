# -*- coding: utf-8 -*-
# qanat ケースのデータ生成(理想化した扇状地斜面+段丘崖+カナート坑道線)
#
# 格子: nx=40, ny=21, dx=dy=10 m(400 m x 210 m)。行1が北。
# 地形(東向き下り。x はセル中心座標):
#   x < 300        : 勾配 0.015 の扇状地面(z = 3.5 + 0.015*(300-x))
#   300 <= x <= 360: 勾配 0.05 の段丘崖(z = 3.5 - 0.05*(x-300))
#   x > 360        : 勾配 0.005 の低地(z = 0.5 - 0.005*(x-360))
# 帯水層: 層2(風化基岩層)d2=8 m, sy2=0.2, 初期飽和度 0.9
#         → 初期地下水位 = z - 1.8 m(地表下 1.8 m)
# 坑道: 中央行 j=11、i=2..35 のセル列。管底勾配 0.004。
#       出口セル i=35(x=345)は崖の中腹で管底=地表(z=1.25 m)。
#       地下水位下(集水部)は i=2..31、水面上(導水部)は i=32..34 の
#       3 セルだけ — 出口を崖に開けることで導水部の漏水損失を短くする
#       (実カナートが崖・段丘に口を開ける構図の理想化)。
import os

nx, ny = 40, 21
dx = 10.0
jline = 11          # 坑道の行(1 始まり)
i1, i2 = 2, 35      # 坑道のセル範囲(i2 が出口)
slope_q = 0.004     # 坑道床勾配

def x_of(i):        # セル中心座標 (m)
    return (i - 0.5) * dx

def z_of(i):        # 地表高(扇状地面+段丘崖+低地)
    x = x_of(i)
    if x < 300.0:
        return 3.5 + 0.015 * (300.0 - x)
    elif x <= 360.0:
        return 3.5 - 0.05 * (x - 300.0)
    else:
        return 0.5 - 0.005 * (x - 360.0)

zbot_mouth = z_of(i2)                    # 出口の管底 = 地表(1.25 m)

def zbot_of(i):     # 坑道床高(出口から上流へ勾配 slope_q で上がる)
    return zbot_mouth + slope_q * (x_of(i2) - x_of(i))

def write_mat(fn, fval):
    with open(fn, "w") as f:
        for j in range(1, ny + 1):       # 行1 = 北
            f.write(" ".join("%.4f" % fval(i, j) for i in range(1, nx + 1)))
            f.write("\n")

here = os.path.dirname(os.path.abspath(__file__))
d = os.path.join(here, "data_qanat")
os.makedirs(d, exist_ok=True)

on_line = lambda i, j: (j == jline and i1 <= i <= i2)

# 地形(j に依存しない一様断面)
write_mat(os.path.join(d, "z.txt"), lambda i, j: z_of(i))
# 坑道の貯留容量(断面 1 m2 x セル長 10 m / セル面積 100 m2 = 0.1 m 柱状)
write_mat(os.path.join(d, "gwc_cap.txt"), lambda i, j: 0.1 if on_line(i, j) else 0.0)
# 管底標高(線外は cap=0 で恒久無効のため値は使われない。z を入れておく)
write_mat(os.path.join(d, "gwc_bot.txt"),
          lambda i, j: zbot_of(i) if on_line(i, j) else z_of(i))
# 通水能密度(min 規約により線上のエッジだけが結合する)
write_mat(os.path.join(d, "gwc_cnd.txt"), lambda i, j: 0.05 if on_line(i, j) else 0.0)
# 枡(開口)密度: 出口セルのみ
write_mat(os.path.join(d, "gwc_inlet.txt"),
          lambda i, j: 0.01 if (i == i2 and j == jline) else 0.0)
# 層間交換能マップ (mm/h): 導水部(i>=32)をライニング(=0)した変種用
write_mat(os.path.join(d, "gwc_leak.txt"),
          lambda i, j: 30.0 if (on_line(i, j) and i < 32) else 0.0)
# 開放吐口の変種用: 出口セルに吐口(Cd*A = 0.15 m2。海隣接なし =
# 自セル地表への自由流出)
write_mat(os.path.join(d, "gwc_outfall.txt"),
          lambda i, j: 0.15 if (i == i2 and j == jline) else 0.0)

# 集水部・導水部の目安を表示(wt = 初期地下水位 = z - 1.8)
print("mouth: i=%d z=%.2f zbot=%.2f" % (i2, z_of(i2), zbot_mouth))
print("  i     x     z   zbot depth 集水?(depth>1.8)")
for i in range(i1, i2 + 1):
    dep = z_of(i) - zbot_of(i)
    if i in (2, 10, 20, 28, 30, 31, 32, 33, 34, 35):
        print("%3d %6.1f %5.2f %5.2f %5.2f  %s" %
              (i, x_of(i), z_of(i), zbot_of(i), dep, "集水" if dep > 1.8 else "導水"))
