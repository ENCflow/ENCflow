#!/usr/bin/env python3
# examples/paddy_dam の入力生成(data/ に書く。make が呼ぶ)
#
# 合成地形の低平地の排水区(630 m × 960 m、Δx = 10 m、63 列 × 96 行)。周りは堤防・台地で閉じ、外の川の
# 水位が高く自然排水できない(内水)。水は南西の排水機場のポンプだけで域外へ出る。
#   区画(30 a = 30 m × 100 m = 3 × 10 セル。区画の幅 3 セルは表現 B の解像の下限)を 4 組 × 2 列 × 19 枚 =
#   152 枚並べる(水田 45.6 ha)。
#   北から: 外周 j = 1、組ごとに [農道 1 | 区画の列 A 10 | 小排水路 1 | 区画の列 B 10](22 行 × 4 組 = j 2..89)、
#   農道 j 90、集落・畑の帯 j 91..93、幹線排水路 j 94、堤防 j 95..96。
#   西から: 外周 i = 1(台地)、農道 i 2、区画 i 3..59(3 列 × 19 枚)、農道 i 60、支線排水路 i 61、外周 i 62..63
#   (台地)。支線・幹線排水路は 30 m 格子のセルの境にそろえてあり、30 m の河道のセルに区画を含まない。
#   流れ: 小排水路(東へ)→ 支線排水路(東端を南へ)→ 幹線排水路(南端を西へ)→ 排水機場(南西の端)。
#   集落は幹線排水路の北の帯の西側(i 2..22)で、地区で最も低い(幹線があふれると最初に浸かる)。
# 地盤: 北から南へ 1/1000 で下る面 z0 = 1.2 − 0.001 y(y は北端からの距離 m)。区画の田面は区画の中で平ら
#   (z0 の平均)、農道 z0 + 0.45(畦畔の天端 = 田面 + 0.30 m より高い)、畑 z0 + 0.05、集落 z0 − 0.10、外周の
#   台地 z0 + 1.0。排水路の底は
#   小排水路 z0 − 0.5 − 0.0005 x(東へ下る。x は西端からの距離 m)、支線排水路 z0 − 0.9、幹線排水路
#   z0 − 1.0 − 0.0005 (x_支線 − x)(西へ下る)。
# 書くもの(data/)。10 m の入力は表現 B(Δx = 10 m。param_B10_*.txt)、30 m の入力は表現 A(Δx = 30 m。
# param_A30_*.txt)が読む。同じ 10 m の地区から作るので、2 つの表現は同じ地区を解く:
#   z.txt                 地盤高 (m)
#   rn.txt                粗度(排水路 0.03、区画 0.05、農道・畑・集落・台地 0.04)
#   gv.txt・bb.txt        集落の建物の空隙率 0.7 と家屋の平均寸法 10 m(ほかは 1 と 10)
#   plot.txt              区画番号(1..152。0 = 区画でない)
#   outlet.txt            落水口の向き(列 A は南 = 7、列 B は北 = 2。区画の小排水路側の短い辺の中央)
#   class_N.txt           全て通常の落水口(種類 1)
#   class_D.txt           全て田んぼダム(種類 2)
#   class_Du.txt          北の 2 組(上流側の半分)だけ田んぼダム
#   class_Dd.txt          南の 2 組(下流側の半分)だけ田んぼダム
#   use.txt               土地利用の番号(図のため。1 農道・2 小排水路・3 支線・4 幹線・5 区画・6 集落・7 畑・8 台地)
#   catch.txt             水田へ流れ込むセル(1。農道・台地のうち、雨が区画へ流れ込むもの。catchment() でたどる)
#   *30.txt               表現 A の 30 m 格子(10 m の値の 3 × 3 の平均): frac30(水田面積率。0.99 で頭打ち)、
#                         frac30c(frac30 に水田へ流れ込む面積を足したもの。ケース A30_*2c)、z30(地盤高。
#                         排水路を含むセルは排水路の底の最低)、rw30・w30(支線・幹線排水路のセルの河道マスクと
#                         サブグリッド幅 m)、gv30(空隙率)、adopt30_N・D・Du・Dd(取組率)
import os
import numpy as np

NX, NY, DX = 63, 96, 10.0
Z_N, S_NS, S_EW = 1.2, 1.0e-3, 0.5e-3
NUNIT, NPLOT_X = 4, 19
PW, PL = 3, 10                    # 区画の幅(東西)・長さ(南北)のセル数
I_ROAD_W = 2                      # 西の農道の列
I_PLOT1 = 3                       # 区画の西端の列
I_ROAD_E = 60                     # 東の農道の列
I_BR = 61                         # 支線排水路の列
J_ROAD_S = 90                     # 区画の南の農道
J_SET1, J_SET2 = 91, 93           # 集落・畑の帯
J_MAIN = 94                       # 幹線排水路
I_SET2 = 22                       # 集落の東端の列
UNIT_ROWS = 2 * PL + 2            # 組の行数(農道 + 区画 + 小排水路 + 区画)
USE = {"road": 1, "drain": 2, "branch": 3, "main": 4, "plot": 5, "house": 6, "field": 7, "hill": 8}
HLEV = 0.30                       # 畦畔高(param の pd_hlev の既定と同じ)


def catchment(z, use, isp):
    """水田へ流れ込む面積: 区画でも排水路でもない 10 m のセルから、8 近傍の最急の下り(区画のセルは畦畔の天端 =
    田面 + 畦畔高を高さとする)をたどり、区画のセルに着くものを 1 とする。排水路に着くか、下りがなくなったら 0。
    着いた区画のセルを dest に返す(独自の簡略な前処理。浅水流の分流は表さず、1 つの向きだけをたどる)"""
    ny, nx = z.shape
    isd = np.isin(use, [USE["drain"], USE["branch"], USE["main"]])
    ze = np.where(isp, z + HLEV, z)
    catch = np.zeros((ny, nx), dtype=int)
    dest = np.full((ny, nx, 2), -1, dtype=int)
    for j0 in range(ny):
        for i0 in range(nx):
            if isp[j0, i0] or isd[j0, i0]:
                continue
            j, i = j0, i0
            for _ in range(ny * nx):
                best, nxt = 0.0, None
                for dj in (-1, 0, 1):
                    for di in (-1, 0, 1):
                        jj, ii = j + dj, i + di
                        if (dj == 0 and di == 0) or not (0 <= jj < ny and 0 <= ii < nx):
                            continue
                        s = (z[j, i] - ze[jj, ii]) / (DX * (np.sqrt(2.0) if dj and di else 1.0))
                        if s > best:
                            best, nxt = s, (jj, ii)
                if nxt is None or isd[nxt]:
                    break
                if isp[nxt]:
                    catch[j0, i0] = 1
                    dest[j0, i0] = nxt
                    break
                j, i = nxt
    return catch, dest


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(here, "data")
    os.makedirs(d, exist_ok=True)
    use = np.full((NY, NX), USE["hill"], dtype=int)
    plot = np.zeros((NY, NX), dtype=int)
    outl = np.zeros((NY, NX), dtype=int)
    unit = np.zeros((NY, NX), dtype=int)       # 区画の組(1..4。北から)
    # 区画・農道・小排水路(添字は 1 始まりで考え、配列には −1 して入れる)
    pid = 0
    for u in range(NUNIT):
        j0 = 2 + UNIT_ROWS * u                   # 組の北の農道の行
        use[j0 - 1, I_ROAD_W - 1:I_BR - 1] = USE["road"]
        use[j0 + PL, I_ROAD_W - 1:I_BR - 1] = USE["drain"]   # 小排水路(行 j0 + PL + 1)
        for ja, out_dir, jo in ((j0 + 1, 7, j0 + PL), (j0 + PL + 2, 2, j0 + PL + 2)):
            for n in range(NPLOT_X):
                pid += 1
                i1 = I_PLOT1 + PW * n
                sl = (slice(ja - 1, ja - 1 + PL), slice(i1 - 1, i1 - 1 + PW))
                plot[sl] = pid
                use[sl] = USE["plot"]
                unit[sl] = u + 1
                outl[jo - 1, i1 - 1 + PW // 2] = out_dir
    for j in range(2, J_ROAD_S):                 # 西と東の農道(小排水路の行は小排水路のまま)
        for i in (I_ROAD_W, I_ROAD_E):
            if use[j - 1, i - 1] != USE["drain"]:
                use[j - 1, i - 1] = USE["road"]
    use[J_ROAD_S - 1, I_ROAD_W - 1:I_BR - 1] = USE["road"]
    # 支線・幹線排水路、集落・畑
    use[1:J_MAIN, I_BR - 1] = USE["branch"]
    use[J_SET1 - 1:J_SET2, I_ROAD_W - 1:I_BR - 1] = USE["field"]
    use[J_SET1 - 1:J_SET2, I_ROAD_W - 1:I_SET2] = USE["house"]
    use[J_MAIN - 1, I_ROAD_W - 1:I_BR] = USE["main"]
    # 地盤高
    z = np.zeros((NY, NX))
    xbr = (I_BR - 0.5) * DX
    for j in range(1, NY + 1):
        for i in range(1, NX + 1):
            x, y = (i - 0.5) * DX, (j - 0.5) * DX
            z0 = Z_N - S_NS * y
            u = use[j - 1, i - 1]
            zc = {USE["road"]: z0 + 0.45, USE["drain"]: z0 - 0.5 - S_EW * x, USE["branch"]: z0 - 0.9,
                  USE["main"]: z0 - 1.0 - S_EW * (xbr - x), USE["house"]: z0 - 0.10, USE["field"]: z0 + 0.05,
                  USE["hill"]: z0 + 1.0}.get(u, z0)
            z[j - 1, i - 1] = zc
    for p in range(1, pid + 1):                 # 区画の田面は平ら(z0 の平均)
        m = plot == p
        z[m] = z[m].mean()
    rn = np.full((NY, NX), 0.04)
    rn[np.isin(use, [USE["drain"], USE["branch"], USE["main"]])] = 0.03
    rn[use == USE["plot"]] = 0.05
    gv = np.where(use == USE["house"], 0.7, 1.0)
    np.savetxt(os.path.join(d, "z.txt"), z, fmt="%.4f")
    np.savetxt(os.path.join(d, "rn.txt"), rn, fmt="%.3f")
    np.savetxt(os.path.join(d, "gv.txt"), gv, fmt="%.2f")
    np.savetxt(os.path.join(d, "bb.txt"), np.full((NY, NX), 10.0), fmt="%.1f")
    np.savetxt(os.path.join(d, "plot.txt"), plot, fmt="%d")
    np.savetxt(os.path.join(d, "outlet.txt"), outl, fmt="%d")
    np.savetxt(os.path.join(d, "use.txt"), use, fmt="%d")
    isp = plot > 0
    for tag, cl in (("N", np.where(isp, 1, 0)), ("D", np.where(isp, 2, 0)),
                    ("Du", np.where(isp, np.where(unit <= 2, 2, 1), 0)),
                    ("Dd", np.where(isp, np.where(unit >= 3, 2, 1), 0))):
        np.savetxt(os.path.join(d, "class_%s.txt" % tag), cl, fmt="%d")
    # 30 m 格子(表現 A の比べ。3 × 3 セルの平均)
    f = 3
    nxc, nyc = NX // f, NY // f
    def coarse(a, fill):
        return a.reshape(nyc, f, nxc, f)
    frc = coarse(isp.astype(float), 0.0).mean(axis=(1, 3))
    zc = coarse(z, z.max()).mean(axis=(1, 3))
    isb = np.isin(use, [USE["branch"], USE["main"]])
    nb = coarse(isb.astype(float), 0.0).sum(axis=(1, 3))
    rw = (nb > 0).astype(int)
    wid = np.where(rw > 0, nb / f * DX, 0.0)             # 粗いセルを横切る排水路の幅(10 m)
    zr = coarse(np.where(isb, z, np.inf), np.inf).min(axis=(1, 3))
    zc = np.where(rw > 0, zr, zc)
    frc = np.where(rw > 0, 0.0, frc)
    # 区画だけの 30 m のセルは面積率 1 になるが、双方向は水田でない面積の割合 1 − a/gv を 0.01 以上にする必要が
    # あるので 0.99 で頭打ちにする(表現 B の区画は畦畔を厚さのない壁にした面積なので、1 に近いほど B にそろう)
    frc = np.minimum(frc, 0.99)
    np.savetxt(os.path.join(d, "frac30.txt"), frc, fmt="%.4f")
    np.savetxt(os.path.join(d, "z30.txt"), zc, fmt="%.4f")
    np.savetxt(os.path.join(d, "rw30.txt"), rw, fmt="%d")
    np.savetxt(os.path.join(d, "w30.txt"), wid, fmt="%.2f")
    gvc = np.maximum(coarse(gv, 1.0).mean(axis=(1, 3)), frc)
    np.savetxt(os.path.join(d, "gv30.txt"), gvc, fmt="%.4f")
    # 水田へ流れ込む面積(集水面積)を足した面積率 frac30c(ケース A30_*2c)。流れ込む先を表現 B の地形でたどり、
    # 流れ込む先の区画のセルを含む 30 m のセルの面積率に足す(同じく 0.99 で頭打ち)
    catch, dest = catchment(z, use, isp)
    np.savetxt(os.path.join(d, "catch.txt"), catch, fmt="%d")
    add = np.zeros((nyc, nxc))
    for j, i in zip(*np.nonzero(catch)):
        add[dest[j, i, 0] // f, dest[j, i, 1] // f] += 1.0 / (f * f)
    frcc = np.where(frc > 0, np.minimum(frc + add, 0.99 * gvc), frc)
    np.savetxt(os.path.join(d, "frac30c.txt"), frcc, fmt="%.4f")
    print("catchment: %.2f ha of roads and upland drain into plots; %.2f ha added to the 30 m fractions, "
          "%.2f ha cut by the cap" % (catch.sum() * DX * DX / 1e4, ((frcc - frc) * f * f * DX * DX).sum() / 1e4,
                                      (add.sum() - (frcc - frc).sum()) * f * f * DX * DX / 1e4))
    uc = coarse(unit * isp, 0).sum(axis=(1, 3)) / np.maximum(coarse(isp.astype(float), 0.0).sum(axis=(1, 3)), 1e-9)
    for tag, a in (("N", np.zeros((nyc, nxc))), ("D", np.ones((nyc, nxc))),
                   ("Du", np.where((uc > 0) & (uc <= 2.0), 1.0, 0.0)), ("Dd", np.where(uc > 2.0, 1.0, 0.0))):
        np.savetxt(os.path.join(d, "adopt30_%s.txt" % tag), a, fmt="%.2f")
    ih = np.nonzero(use == USE["house"])
    print("written: data/ (10 m: %d x %d, %d plots = %.1f ha of paddies; 30 m: %d x %d)"
          % (NX, NY, pid, isp.sum() * DX * DX / 1e4, nxc, nyc))
    print("ground: plots %.3f..%.3f m, main drain bed at the pump %.3f m, houses %.3f..%.3f m"
          % (z[isp].min(), z[isp].max(), z[J_MAIN - 1, I_ROAD_W - 1], z[ih].min(), z[ih].max()))


if __name__ == "__main__":
    main()
