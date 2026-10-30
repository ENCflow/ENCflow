#!/usr/bin/env python3
# examples/levee_breach の入力生成(z.txt / z_vwall.txt / rn.txt / rw.txt)
#   直線河道 + 解像堤防 + 堤内地(氾濫原)の理想化地形。dx = dy = 10 m、
#   120 列 × 80 行(1,200 m × 800 m)。北から南へ 1/1000 で下る。西から順に:
#     i=1..15    : 山付き(z = 堤内地 + 4 m。河道の西岸。氾濫はしない)
#     i=16..20   : 河道(幅 50 m。河床 = 堤内地 − 3 m)
#     i=21..22   : 堤防(幅 20 m。天端 = 堤内地 + 3 m)← 解像堤防(DEM の標高で表す)
#     i=23..120  : 堤内地(東へ 1/2000 で下る)
#   z_vwall.txt は比較ケース(仮想壁面)用で、堤防セル i=21..22 を堤内地の
#   地盤高に置き換えたもの(堤防は &list_channel の bank0 で立てる)。
#   rw.txt は河道マスク(仮想壁面ケースで堤防を立てるのに必要)、
#   rn.txt は粗度(河道 0.03、それ以外 0.05)。
import numpy as np

NX, NY, DX = 120, 80, 10.0
I_RIV1, I_RIV2 = 16, 20          # 河道の列(1 スタート)
I_LEV1, I_LEV2 = 21, 22          # 堤防の列
S_NS, S_EW = 1.0e-3, 0.5e-3      # 南向き・東向きの勾配
H_LEV, D_RIV, H_HILL = 3.0, 3.0, 4.0

z = np.zeros((NY, NX)); zv = np.zeros((NY, NX))
rn = np.full((NY, NX), 0.05); rw = np.zeros((NY, NX), dtype=int)
for j in range(1, NY + 1):
    ys = (j - 0.5) * DX                      # 北端からの距離 (m)
    for i in range(1, NX + 1):
        xe = max(0.0, (i - I_LEV2 - 0.5)) * DX  # 堤防の東端からの距離 (m)
        zfp = 0.0 - S_NS * ys - S_EW * xe       # 堤内地の地盤高(堤防位置では xe = 0)
        if i < I_RIV1:
            zc = zfp + H_HILL
        elif i <= I_RIV2:
            zc = zfp - D_RIV; rn[j-1, i-1] = 0.03; rw[j-1, i-1] = 1
        elif i <= I_LEV2:
            zc = zfp + H_LEV
        else:
            zc = zfp
        z[j-1, i-1] = zc
        zv[j-1, i-1] = zfp if I_LEV1 <= i <= I_LEV2 else zc

np.savetxt('z.txt', z, fmt='%.4f')
np.savetxt('z_vwall.txt', zv, fmt='%.4f')
np.savetxt('rn.txt', rn, fmt='%.3f')
np.savetxt('rw.txt', rw, fmt='%d')
print('written: z.txt z_vwall.txt rn.txt rw.txt (%d x %d, dx = %g m)' % (NX, NY, DX))
print('levee crest at the breach row j=50: z = %.3f m, floodplain toe (i=%d): %.3f m, river bed: %.3f m'
      % (z[49, I_LEV1-1], I_LEV2+1, z[49, I_LEV2], z[49, I_RIV1-1]))
