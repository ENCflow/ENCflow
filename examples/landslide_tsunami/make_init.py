#!/usr/bin/env python3
# examples/landslide_tsunami の入力生成
#   make_init.py z          : 地形 z.txt(斜面 tanθ=0.4 → 汀線 x=200 m → 水中も同勾配 → 湖底 z=−40 m)
#   make_init.py slide      : 陸上の崩壊深 slide.txt(x∈[40,110] m の平面すべり。A・B で共用)
#   make_init.py submarine  : 水中の崩壊深 submarine.txt(x∈[220,290] m の平面すべり。C)
# 崩壊面は「斜面下端で地表に抜ける平面」(すべり面勾配 STF < 斜面勾配 ST)。
# 箱型(深さ一定)は下流側に壁のある穴になり、土塊が出られない(README 参照)
import sys

NX, NY, DX = 120, 40, 5.0          # 600 m × 200 m
ST, XSHORE, ZBOT = 0.4, 200.0, -40.0
STF, NTAPER = 0.25, 2              # すべり面勾配、側方テーパのセル数
BLOCKS = {                         # 名前: (x0, x1, y0, y1, Dmax)
    "slide":     (40.0, 110.0, 70.0, 130.0, 12.0),
    "submarine": (220.0, 290.0, 70.0, 130.0, 12.0),
}

kind = sys.argv[1]
rows = []
for j in range(1, NY + 1):
    y = (j - 0.5) * DX
    vals = []
    for i in range(1, NX + 1):
        x = (i - 0.5) * DX
        if kind == "z":
            vals.append("%.4f" % max(ST * (XSHORE - x), ZBOT))
        else:
            x0, x1, y0, y1, dmax = BLOCKS[kind]
            d = 0.0
            if x0 <= x <= x1 and y0 <= y <= y1:
                d = min(dmax, (ST - STF) * (x1 - x))
                dy = min(y - y0, y1 - y) / DX
                d *= min(1.0, (dy + 0.5) / (NTAPER + 0.5))
            vals.append("%.3f" % max(d, 0.0))
    rows.append(" ".join(vals))
print("\n".join(rows))
