#!/usr/bin/env python3
# examples/timberyard の入力生成(引数なしで全ファイルを書く。make が呼ぶ)
#   z.txt / sw.txt / gv.txt / stock.txt と、比較ケースの stock_far.txt(貯木場を
#   港の沖側へ移した材木ストック)・z_wall4.txt(防潮壁の天端 +4.0 m。開口部は +0.5 m)
#   伊勢湾台風型の「海岸の貯木場から高潮で材木が市街地へ流入する」現象の
#   理想化実験。西から順に:
#     i=1        : 海域マスク列(潮位強制。高潮ハイドログラフの入口)
#     i=2..15    : 港湾水面(z=-3 m。通常セル+初期水位で湛水)
#     i=16..35   : 貯木場(z=-2 m。材木ストック 0.5 m3/m2 を配置)
#     i=36..37   : 岸壁・防潮壁(z=+1.5 m。中央 j=25..36 は開口部 z=+0.5 m
#                  = 流入が集中する低所)
#     i=38..120  : 市街地(z=+0.5 → +2.0 m へ緩勾配。建物空隙率 gv=0.6)
#   貯木場・市街地を海域マスクにしない理由: 海セルには材木ストックを
#   置けず流木の移流も働かない(解説は README.md)。
import numpy as np

Z_WALL = 1.5                   # 防潮壁天端 (m)
Z_WALL_HIGH = 4.0              # かさ上げした防潮壁の天端 (m。z_wall4.txt)

nx, ny = 120, 60
z = np.zeros((ny, nx))
sw = np.zeros((ny, nx), dtype=int)
gv = np.ones((ny, nx))
stock = np.zeros((ny, nx))

for j in range(ny):
    for i in range(nx):
        x = i + 1                      # セル番号(1 スタート)
        if x == 1:
            sw[j, i] = 1               # 海域マスク列(潮位強制)
            z[j, i] = -3.0
        elif x <= 15:
            z[j, i] = -3.0             # 港湾水面
        elif x <= 35:
            z[j, i] = -2.0             # 貯木場
            stock[j, i] = 0.5          # 材木ストック (m3/m2)
        elif x <= 37:
            # 岸壁・防潮壁。中央に開口部(低所)
            if 25 <= (j + 1) <= 36:
                z[j, i] = 0.5
            else:
                z[j, i] = Z_WALL
        else:
            # 市街地: +0.5 m から東端 +2.0 m へ緩勾配
            z[j, i] = 0.5 + 1.5 * (x - 38) / (nx - 38)
            gv[j, i] = 0.6             # 建物占有 40%(空隙率 0.6)

np.savetxt('z.txt', z, fmt='%.4f')
np.savetxt('sw.txt', sw, fmt='%d')
np.savetxt('gv.txt', gv, fmt='%.2f')
np.savetxt('stock.txt', stock, fmt='%.3f')
# 貯木場を港の沖側(i = 2..14。防潮壁から 210〜340 m)へ移す: 同じ 6 万 m3 を 13 列に
far = np.zeros((ny, nx))
far[:, 1:14] = stock.sum() / (ny * 13)
np.savetxt('stock_far.txt', far, fmt='%.6f')
# 防潮壁を +4.0 m にかさ上げ(開口部は +0.5 m のまま = 陸閘が開いている)
zw = z.copy()
zw[:, 35:37] = np.where(zw[:, 35:37] > 0.5, Z_WALL_HIGH, zw[:, 35:37])
np.savetxt('z_wall4.txt', zw, fmt='%.4f')
vol = stock.sum() * 10.0 * 10.0
print('written: z.txt sw.txt gv.txt stock.txt stock_far.txt z_wall4.txt (%d x %d)' % (nx, ny))
print('timber stock total = %.0f m3 (far: %.0f m3)' % (vol, far.sum() * 100.0))
