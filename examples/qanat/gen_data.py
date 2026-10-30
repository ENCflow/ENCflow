# -*- coding: utf-8 -*-
# qanat の入力生成(扇状地の帯水層+段丘崖+カナートの坑道)。data_qanat/ に書く
#
# 格子: nx=50, ny=21, dx=dy=10 m(500 m x 210 m)。行1が北。
# 地形(東向き下り。x はセル中心座標):
#   x < 300        : 勾配 0.015 の扇状地面(z = 3.5 + 0.015*(300-x))
#   300 <= x < 350 : 勾配 0.05 の段丘崖(z = 3.5 - 0.05*(x-300))
#   350 <= x < 490 : 平野(z = 1.0 → 0.5)
#   東端の列       : 扇状地の末端の排水路(z = -0.5)。地下水はここで湧き出して東の辺から出る
#                    (地下水位の上限 = 水位一定の境界の代わり)
# 帯水層: 層2 d2=8 m, sy2=0.2(初期の地下水位 = 地表下 1.8 m)。南北・西は閉じる
# 坑道: 中央行 j=11、i=2..35 のセル列。床勾配 0.004、断面 1 m2、通水能 0.5 m2/s。
#       上流の i=2..16 が集水区間(帯水層と水をやり取りする)、i=17..35 は漏れない
#       導水区間。出口 i=35(x=345、崖の中腹)で床が地表に出る。出口は開放の吐口で
#       地表へ流れ出し、平野を流れて排水路へ出ていく(下流の村や畑で使われる)
# 涵養: 扇状地の上端の帯(x < 50 m)に一定の涵養(山地から来る地下水の代わり)。
#       雨として降らせ、その帯だけ浸透能を大きくして全量を地下へしみ込ませる
# 揚水井: 坑道の上流部の脇(i=8, j=7。x=75 m、坑道から 40 m 北)
import os

nx, ny = 50, 21
dx = 10.0
jline = 11          # 坑道の行(1 始まり)
i1, i2 = 2, 35      # 坑道のセル範囲(i2 が出口)
slope_q = 0.004     # 坑道の床の勾配
I_RECH = 5          # 涵養の帯の終わりの列(x < 50 m)
RECH_LS = 10.0      # 涵養量 (L/s。帯全体)
Z_DITCH = -0.5      # 東端の排水路の地盤高 (m)
WELL = (8, 7)       # 揚水井のセル (i, j)
CND = 0.5           # 坑道の通水能密度 (m2/s)
I_LINED = 17        # 漏れない導水区間の始まりの列(x = 165 m。地下水位が坑道を横切るあたり)


def x_of(i):        # セル中心座標 (m)
    return (i - 0.5) * dx


def z_of(i):        # 地表高(扇状地面+段丘崖+平野+東端の排水路)
    x = x_of(i)
    if i == nx:
        return Z_DITCH
    if x < 300.0:
        return 3.5 + 0.015 * (300.0 - x)
    if x < 350.0:
        return 3.5 - 0.05 * (x - 300.0)
    return 1.0 - 0.5 * (x - 350.0) / (nx * dx - 360.0)


zbot_mouth = z_of(i2)                    # 出口の床 = 地表(1.25 m)


def zbot_of(i):     # 坑道の床の標高(出口から上流へ勾配 slope_q で上がる)
    return zbot_mouth + slope_q * (x_of(i2) - x_of(i))


def write_mat(d, name, fval, fmt="%.4f"):
    with open(os.path.join(d, name), "w") as f:
        for j in range(1, ny + 1):       # 行1 = 北
            f.write(" ".join(fmt % fval(i, j) for i in range(1, nx + 1)) + "\n")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(here, "data_qanat")
    os.makedirs(d, exist_ok=True)
    on_line = lambda i, j: (j == jline and i1 <= i <= i2)
    write_mat(d, "z.txt", lambda i, j: z_of(i))
    # 坑道: 貯留容量(断面 1 m2 x セル長 10 m / セル面積 100 m2 = 0.1 m 柱状)、床、通水能、吐口
    write_mat(d, "gwc_cap.txt", lambda i, j: 0.1 if on_line(i, j) else 0.0)
    write_mat(d, "gwc_bot.txt", lambda i, j: zbot_of(i) if on_line(i, j) else z_of(i))
    write_mat(d, "gwc_cnd.txt", lambda i, j: CND if on_line(i, j) else 0.0)
    write_mat(d, "gwc_outfall.txt", lambda i, j: 0.15 if (i == i2 and j == jline) else 0.0)
    # 坑道と帯水層の交換能 (mm/h): 導水区間(i >= I_LINED)は 0 = 漏れない
    write_mat(d, "gwc_leak.txt", lambda i, j: 30.0 if (on_line(i, j) and i < I_LINED) else 0.0)
    # 涵養: 帯の値は mm/day(prtype=2 の分布の既定の単位)
    area = I_RECH * ny * dx * dx
    rech_mmd = RECH_LS / 1000.0 / area * 86400.0 * 1000.0
    write_mat(d, "recharge.txt", lambda i, j: rech_mmd if i <= I_RECH else 0.0)
    write_mat(d, "gw_ksv.txt", lambda i, j: 100.0 if i <= I_RECH else 0.0)
    print(f"recharge {RECH_LS} L/s = {rech_mmd:.2f} mm/day on x < {I_RECH * dx:.0f} m")
    print("  i     x     z   zbot  depth")
    for i in (2, 10, 20, 28, 30, 31, 32, 33, 34, 35):
        print("%3d %6.1f %5.2f %5.2f %5.2f" % (i, x_of(i), z_of(i), zbot_of(i), z_of(i) - zbot_of(i)))


if __name__ == "__main__":
    main()
