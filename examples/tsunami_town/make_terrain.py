#!/usr/bin/env python3
# 津波の市街地遡上・家屋破壊・瓦礫デモの入力生成
#   (z.txt / sw.txt / gv.txt / bdstock.txt / bdfrac.txt / dwstock.txt)
#   海岸の低平な市街地に津波(先行波のみの理想化波形。fn_tide の時系列)が
#   遡上し、木造家屋を破壊して瓦礫を内陸へ運ぶ理想化実験。西から順に:
#     i=1        : 海域マスク列(潮位強制 = 津波波形の入口)
#     i=2..15    : 海(z=-5 m。通常セル+初期水位で湛水 = 解く海)
#     i=16..25   : 浜・貯木場(z=-2 → 0 m。i=16..25 に流木ストック = 流木ケース用)
#     i=26..27   : 海岸堤防(z=+2.0 m。中央 j=25..36 は開口部 z=+0.5 m)
#     i=28..120  : 市街地(z=+0.5 → +3.0 m の緩勾配。建物空隙率 gv=0.6。
#                  家屋ストック 0.3 m3/m2。木造率は内陸ほど低い(海側 100 % →
#                  内陸 40 %: 耐津波構造・RC 造の割合が増える想定)で、
#                  fn_bdstock に織り込み、fn_bdfrac で空隙率帰還の上限を与える)
#   海・浜を海域マスクにしない理由: 海セルには瓦礫・流木を置けず移流も
#   働かない(examples/timberyard/README.md と同じ流儀)。
import numpy as np

nx, ny = 120, 60
z = np.zeros((ny, nx))
sw = np.zeros((ny, nx), dtype=int)
gv = np.ones((ny, nx))
bdstock = np.zeros((ny, nx))
bdfrac = np.ones((ny, nx))
dwstock = np.zeros((ny, nx))
STOCK_WOOD = 0.3             # 木造 100 % の家屋ストック (m3/m2)

for j in range(ny):
    for i in range(nx):
        x = i + 1                      # セル番号(1 スタート)
        if x == 1:
            sw[j, i] = 1               # 海域マスク列(潮位強制)
            z[j, i] = -5.0
        elif x <= 15:
            z[j, i] = -5.0             # 海
        elif x <= 25:
            z[j, i] = -2.0 + 2.0 * (x - 16) / 9   # 浜(-2 → 0 m)
            dwstock[j, i] = 1.0        # 貯木場の材木ストック(流木ケース用。timberyard の 2 倍)
        elif x <= 27:
            # 海岸堤防。中央に開口部(低所)
            if 25 <= (j + 1) <= 36:
                z[j, i] = 0.5
            else:
                z[j, i] = 2.0
        else:
            # 市街地: +0.5 m から東端 +3.0 m へ緩勾配
            z[j, i] = 0.5 + 2.5 * (x - 28) / (nx - 28)
            gv[j, i] = 0.6             # 建物占有 40 %(空隙率 0.6)
            fw = 1.0 - 0.6 * (x - 28) / (nx - 28)   # 木造率 100 % → 40 %
            bdstock[j, i] = STOCK_WOOD * fw
            bdfrac[j, i] = fw

np.savetxt('z.txt', z, fmt='%.4f')
np.savetxt('sw.txt', sw, fmt='%d')
np.savetxt('gv.txt', gv, fmt='%.2f')
np.savetxt('bdstock.txt', bdstock, fmt='%.4f')
np.savetxt('bdfrac.txt', bdfrac, fmt='%.3f')
np.savetxt('dwstock.txt', dwstock, fmt='%.3f')
print('written: z.txt sw.txt gv.txt bdstock.txt bdfrac.txt dwstock.txt (%d x %d)' % (nx, ny))
print('building stock total = %.0f m3, timber stock total = %.0f m3'
      % (bdstock.sum() * 100.0, dwstock.sum() * 100.0))
