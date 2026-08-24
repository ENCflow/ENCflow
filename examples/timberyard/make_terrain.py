#!/usr/bin/env python3
# 貯木場高潮流木デモの入力生成(z.txt / sw.txt / gv.txt / stock.txt)
#   伊勢湾台風型の「海岸の貯木場から高潮で材木が市街地へ流入する」現象の
#   理想化実験。西から順に:
#     i=1        : 海域マスク列(潮位強制。高潮ハイドログラフの入口)
#     i=2..15    : 港湾水面(z=-3 m。通常セル+初期水位で湛水)
#     i=16..35   : 貯木場(z=-2 m。材木ストック 0.5 m3/m2 を配置)
#     i=36..37   : 岸壁・防潮壁(z=+1.5 m。中央 j=25..36 は開口部 z=+0.5 m
#                  = 流入が集中する低所)
#     i=38..120  : 市街地(z=+0.5 → +2.0 m へ緩勾配。建物空隙率 gv=0.6)
#   貯木場・市街地を海域マスクにしない理由: 海セルには材木ストックを
#   置けず流木の移流も働かない(users_guide/driftwood.md の例題解説)。
import numpy as np

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
                z[j, i] = 1.5
        else:
            # 市街地: +0.5 m から東端 +2.0 m へ緩勾配
            z[j, i] = 0.5 + 1.5 * (x - 38) / (nx - 38)
            gv[j, i] = 0.6             # 建物占有 40%(空隙率 0.6)

np.savetxt('z.txt', z, fmt='%.4f')
np.savetxt('sw.txt', sw, fmt='%d')
np.savetxt('gv.txt', gv, fmt='%.2f')
np.savetxt('stock.txt', stock, fmt='%.3f')
vol = stock.sum() * 10.0 * 10.0
print('written: z.txt sw.txt gv.txt stock.txt (%d x %d)' % (nx, ny))
print('timber stock total = %.0f m3' % vol)
