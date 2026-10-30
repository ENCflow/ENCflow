#!/usr/bin/env python3
# examples/ashfall_lahar の入力生成(引数なしで全ファイルを書く。make が呼ぶ)
#   z.txt        降灰後の地表(= 元地形 + 降灰厚)
#   ash.txt      降灰厚(土層厚 sd として与える = 侵食できる層)
#   z_noash.txt  元地形(噴火前のケース)
#   z_dam.txt    z.txt に砂防堰堤の堤体を足した地表
#   ash_dam.txt  ash.txt の堤体セルを 0(不侵食)にした土層厚
# 地形: 西の山体斜面(tanθ=0.35)に谷底 15 m・谷壁の横断勾配 0.25 の谷(斜面の水は
#       100 m ほど流れる間に谷底へ集まる)→ x=300 m の谷出口 → 緩勾配の扇状地
#       (tanθ=0.08。谷壁は 100 m で消える)。東辺は自由流出、南北は壁。
# 降灰: 西(火口側)で厚く東へ薄くなる一方向の分布。斜面上 0.30 → 0.05 m、
#       扇状地 0.03 m
# 砂防堰堤: 谷出口の 12.5 m 上流(x = 285〜290 m の 1 列)に、谷底から高さ
#       DAM_H の不透過型の堤体(天端は水平。谷壁が天端より高くなる所まで)
NX, NY, DX = 120, 30, 5.0                 # 600 m × 150 m
XAPEX, ST_UP, ST_FAN = 300.0, 0.35, 0.08  # 谷出口の x、斜面勾配、扇状地勾配
SV, WFLOOR, LTAPER = 0.25, 15.0, 100.0    # 谷壁の横断勾配、谷底の幅、谷出口下流でのテーパ長
ASH0, ASH1, ASHFAN = 0.30, 0.05, 0.03     # 降灰厚: 斜面上端、谷出口、扇状地
I_DAM, DAM_H = 58, 5.0                    # 堤体の列(1 始まり。x = 287.5 m)、谷底からの高さ (m)
YC = NY * DX / 2


def z_ground(x, y):
    wall = SV * max(0.0, abs(y - YC) - WFLOOR / 2)   # 平らな谷底 + 両側の谷壁
    if x <= XAPEX:
        z = ST_UP * (XAPEX - x)
        v = wall
    else:
        z = -ST_FAN * (x - XAPEX)
        v = wall * max(0.0, 1.0 - (x - XAPEX) / LTAPER)
    return z + v + ST_FAN * (NX * DX - XAPEX)   # 東端で z=0


def ash(x, y):
    if x <= XAPEX:
        return ASH0 + (ASH1 - ASH0) * x / XAPEX
    return ASHFAN


def grids():
    z, a, zn, zd, ad = ([[0.0] * NX for _ in range(NY)] for _ in range(5))
    xd = (I_DAM - 0.5) * DX
    crest = z_ground(xd, YC) + DAM_H                 # 天端標高(谷底の元地形から DAM_H)
    for j in range(NY):
        y = (j + 0.5) * DX
        for i in range(NX):
            x = (i + 0.5) * DX
            zn[j][i] = z_ground(x, y)
            a[j][i] = ash(x, y)
            z[j][i] = zn[j][i] + a[j][i]
            zd[j][i], ad[j][i] = z[j][i], a[j][i]
            if i == I_DAM - 1 and z[j][i] < crest:   # 堤体: 天端まで盛り、灰は載せない
                zd[j][i], ad[j][i] = crest, 0.0
    return {"z": z, "ash": a, "z_noash": zn, "z_dam": zd, "ash_dam": ad}


def main():
    for name, g in grids().items():
        with open(name + ".txt", "w") as f:
            for row in g:
                f.write(" ".join("%.4f" % v for v in row) + "\n")


if __name__ == "__main__":
    main()
