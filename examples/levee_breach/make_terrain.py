#!/usr/bin/env python3
# examples/levee_breach の入力生成(data/ に書く。make が呼ぶ)
#   z.txt        河道 + 堤防 + 堤内地(氾濫原)の地盤高
#   z_dike.txt   z.txt の堤内地に二線堤(東西の盛土)を足した地盤高
#   rn.txt       粗度(河道 0.03、それ以外 0.05)
#   gv.txt       建物の空隙率(住宅地 0.7 = 建物が 3 割を占める。他は 1)
#   bdstock.txt  家屋ストック(住宅地 0.2 m3/m2 の木造家屋。他は 0)
#   h0.txt       初期水深(河道に平水 300 m3/s の等流水深 1.87 m。他は 0)
# 地形: dx = dy = 10 m、175 列 × 200 行(1,750 m × 2,000 m)。北から南へ 1/1000 で
#   下る。西から順に:
#     i=1..3     : 山付き(堤内地 + 6 m。河道の西岸。氾濫しない)
#     i=4..13    : 河道(幅 100 m。河床 = 堤内地 − 2 m)
#     i=14..15   : 堤防(幅 20 m。天端 = 堤内地 + 4 m。行 J_LOW1..J_LOW2 の 150 m は
#                  天端が 1 m 低い = 整備が済んでいない区間。越水が始まる所)
#     i=16..175  : 堤内地(東へ 1/2000 で下る。東辺は台地 = 閉じた辺)
#   二線堤: 行 J_DIKE..J_DIKE+1 の堤内地全幅に高さ 2 m の盛土(z_dike.txt だけ)
#   住宅地: A 破堤口のすぐ裏、B 下流側(南へ 600〜900 m)、C 二線堤の南
import os
import numpy as np

NX, NY, DX = 175, 200, 10.0
I_RIV1, I_RIV2 = 4, 13           # 河道の列(1 始まり)
I_LEV1, I_LEV2 = 14, 15          # 堤防の列
S_NS, S_EW = 1.0e-3, 0.5e-3      # 南向き・東向きの勾配
D_RIV, H_LEV, H_HILL = 2.0, 4.0, 6.0
J_LOW1, J_LOW2, D_LOW = 53, 67, 1.0   # 天端の低い区間(150 m)と低さ (m)
J_DIKE, H_DIKE = 155, 2.0        # 二線堤の行(2 行 = 幅 20 m)と高さ (m)
GV_HOUSE, STOCK = 0.7, 0.2       # 住宅地の空隙率、家屋ストック (m3/m2)
H_BASE = 1.87                    # 平水 300 m3/s の等流水深 (m。幅 100 m、n 0.03、勾配 1/1000)
BLOCKS = {"A": (17, 36, 50, 70),     # 住宅地 (i1, i2, j1, j2)
          "B": (40, 80, 115, 140),
          "C": (40, 80, 170, 195)}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(here, "data")
    os.makedirs(d, exist_ok=True)
    z = np.zeros((NY, NX))
    rn = np.full((NY, NX), 0.05)
    for j in range(1, NY + 1):
        ys = (j - 0.5) * DX                          # 北端からの距離 (m)
        for i in range(1, NX + 1):
            xe = max(0.0, i - I_LEV2 - 0.5) * DX     # 堤防の東端からの距離 (m)
            zfp = -S_NS * ys - S_EW * xe             # 堤内地の地盤高(堤防の位置では xe = 0)
            if i < I_RIV1:
                zc = zfp + H_HILL
            elif i <= I_RIV2:
                zc = zfp - D_RIV
                rn[j - 1, i - 1] = 0.03
            elif i <= I_LEV2:
                zc = zfp + H_LEV - (D_LOW if J_LOW1 <= j <= J_LOW2 else 0.0)
            else:
                zc = zfp
            z[j - 1, i - 1] = zc
    zd = z.copy()
    zd[J_DIKE - 1:J_DIKE + 1, I_LEV2:] += H_DIKE
    gv = np.ones((NY, NX))
    st = np.zeros((NY, NX))
    for i1, i2, j1, j2 in BLOCKS.values():
        gv[j1 - 1:j2, i1 - 1:i2] = GV_HOUSE
        st[j1 - 1:j2, i1 - 1:i2] = STOCK
    np.savetxt(os.path.join(d, "z.txt"), z, fmt="%.4f")
    np.savetxt(os.path.join(d, "z_dike.txt"), zd, fmt="%.4f")
    np.savetxt(os.path.join(d, "rn.txt"), rn, fmt="%.3f")
    np.savetxt(os.path.join(d, "gv.txt"), gv, fmt="%.2f")
    np.savetxt(os.path.join(d, "bdstock.txt"), st, fmt="%.3f")
    h0 = np.zeros((NY, NX))
    h0[:, I_RIV1 - 1:I_RIV2] = H_BASE
    np.savetxt(os.path.join(d, "h0.txt"), h0, fmt="%.2f")
    j = (J_LOW1 + J_LOW2) // 2
    print("written: data/z.txt z_dike.txt rn.txt gv.txt bdstock.txt h0.txt (%d x %d, dx = %g m)" % (NX, NY, DX))
    print("row %d: river bed %.3f, crest (low section) %.3f, normal crest %.3f, landside toe %.3f m"
          % (j, z[j - 1, I_RIV1 - 1], z[j - 1, I_LEV1 - 1], z[J_LOW1 - 3, I_LEV1 - 1] + S_NS * 2 * DX, z[j - 1, I_LEV2]))
    print("river bed at the south edge: %.3f m" % z[NY - 1, I_RIV1 - 1])
    print("houses: %.0f m3 of stock" % (st.sum() * DX * DX))


if __name__ == "__main__":
    main()
