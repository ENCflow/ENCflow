#!/usr/bin/env python3
# test/bedslide の入力生成(動く底層 f_bedslide の検定。landslide_tsunami_plan.md §6)
#   make_init.py zbench / dbbench : 構成1 格子に沿った等勾配斜面(tanθ=ST)と厚さ D の帯
#   make_init.py zrot   / dbrot   : 構成2 45° 回転した等勾配斜面と同じ厚さの帯(格子依存の検出器)
#   make_init.py z      / db      : 構成3 斜面→湖(work/slide_tsunami と同じ幾何)+平面すべり面
# 幾何定数は Check_bedslide.py と対で保守する
import sys, math

ST = 0.4                      # 斜面勾配 tanθ(全構成共通)
# 構成1(格子沿い): 100 m × 20 m、dx=1。厚さ D=1 m の層を全域(壁から壁)に置く。
#   層の端(ソケットの壁)を作らない: 有限の帯は、動いた先の堆積が地表の上に
#   乗り、残った側は地表より下のスカーになるので、後続は段差を登れず詰まる
#   (表面勾配駆動の慣性なし流の性質 = 崩壊面が地表に抜けない箱型と同じ)。
#   全域一様層なら内部は速度 V で平行移動し、断面 x=XS を通過する体積が
#   D・V・Ly・t になる(上流端の希薄化 1.5V・t と下流壁の堆積の背水が
#   断面に届く前の時間で検定する)
NXB, NYB, DXB = 100, 20, 1.0
BD = 1.0
# 構成2(45°回転): 60 m × 60 m、dx=1。斜面は u=(x+y)/√2 方向に下る。層は全域一様
NXR, NYR, DXR = 60, 60, 1.0
# 構成3(津波): 600 m × 200 m、dx=5(work/slide_tsunami と同一)
NX, NY, DX = 120, 40, 5.0
XSHORE, ZBOT = 200.0, -40.0
REL_X, REL_Y, REL_D, STF, NTAPER = (40.0, 110.0), (70.0, 130.0), 12.0, 0.25, 2

kind = sys.argv[1]
rows = []
if kind in ("zbench", "dbbench"):
    for j in range(1, NYB + 1):
        y = (j - 0.5) * DXB
        vals = []
        for i in range(1, NXB + 1):
            x = (i - 0.5) * DXB
            if kind == "zbench":
                vals.append("%.4f" % (ST * (NXB * DXB - x)))
            else:
                vals.append("%.3f" % BD)
        rows.append(" ".join(vals))
elif kind in ("zrot", "dbrot"):
    # 行順は北→南(j=1 が北)。y は南向きに増える座標で書き、斜面は u=(x+y)/√2 で下る
    for j in range(1, NYR + 1):
        y = (j - 0.5) * DXR
        vals = []
        for i in range(1, NXR + 1):
            x = (i - 0.5) * DXR
            u = (x + y) / math.sqrt(2.0)
            if kind == "zrot":
                vals.append("%.4f" % (ST * (NXR * DXR * math.sqrt(2.0) - u)))
            else:
                vals.append("%.3f" % BD)
        rows.append(" ".join(vals))
else:
    for j in range(1, NY + 1):
        y = (j - 0.5) * DX
        vals = []
        for i in range(1, NX + 1):
            x = (i - 0.5) * DX
            if kind == "z":
                vals.append("%.4f" % max(ST * (XSHORE - x), ZBOT))
            else:
                d = 0.0
                if REL_X[0] <= x <= REL_X[1] and REL_Y[0] <= y <= REL_Y[1]:
                    d = min(REL_D, (ST - STF) * (REL_X[1] - x))
                    dy = min(y - REL_Y[0], REL_Y[1] - y) / DX
                    d *= min(1.0, (dy + 0.5) / (NTAPER + 0.5))
                vals.append("%.3f" % max(d, 0.0))
        rows.append(" ".join(vals))
print("\n".join(rows))
