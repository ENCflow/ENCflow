#!/usr/bin/env python3
"""catchment_metal の入力データを data/ に生成する(make が呼ぶ)。

理想化した農業流域(格子 250 m、東西 80 列 × 南北 48 行 = 20 km × 12 km、陸域約 214 km²)。
本川が西から東へ流れて東端の入り江(海域マスク)に注ぎ、北の丘陵から 2 本、南の低地から
3 本の支川が合流する。北西の支川 T1 の中流に鉱山の排水口、南の支川 T2 の流域の低地に農地と
3 基のため池(地形で表す。堤とあふれ口を持つ窪地)を置く。

地形は「最寄りの河道の河床高 + 河道からの距離に比例して上がる斜面」で作る(北の丘陵ほど
急)。河道セルは河床をさらに 1.5 m 掘り込み、サブグリッド河道幅(本川 15 m、支川 8 m)を
与える。値は現象を見やすくするための模式値で、特定の流域の再現ではない。

出力(data/):
  z_notank.txt / z_tank.txt      地盤高(ため池なし / あり)
  mask.txt, sw.txt                領域マスク(流域+入り江)、海域マスク(入り江)
  rw_notank.txt / rw_tank.txt     河道マスク(ため池の湛水域と堤では河道を切る)
  width_notank.txt / width_tank.txt  サブグリッド河道幅 (m)
  ksv_tank.txt                    Green-Ampt の鉛直透水係数 (mm/h。ため池の底だけ小さい)
  farm_cells.txt                  農地のセル(1 行 1 セル "i j"。1 始まり)
  tank_id.txt                     ため池の番号(図化用。0 = ため池でない)
  cells.txt                       鉱山・観測点・測線のセル(図化と param の確認用)
"""
import os
import sys
import numpy as np

NX, NY, DX = 80, 48, 250.0
KM = 1000.0
# 河道の折れ線(x 東向き km、y は北端から南向き km)と上流端・下流端の河床高 (m)
MAIN = dict(name="M", pts=[(0.4, 5.6), (4.0, 6.0), (8.0, 6.6), (12.0, 6.4), (16.0, 6.0), (19.2, 6.1)],
            z0=33.5, z1=2.0, width=15.0)
TRIBS = [dict(name="T1", pts=[(5.0, 0.6), (6.2, 2.6), (7.9, 6.5)], z0=90.0, width=8.0),     # 丘陵・鉱山
         dict(name="T2", pts=[(11.0, 11.4), (11.6, 9.5), (12.1, 6.45)], z0=35.0, width=8.0),  # 農地・ため池
         dict(name="T3", pts=[(15.0, 0.6), (16.0, 6.0)], z0=71.0, width=8.0),
         dict(name="T4", pts=[(3.0, 11.4), (4.2, 6.0)], z0=43.0, width=8.0),
         dict(name="T5", pts=[(17.4, 11.0), (17.8, 6.05)], z0=29.0, width=8.0)]
INCISE = 1.5                     # 河道セルの掘り込み (m)
X_COAST = 19.25                  # 海岸線 (km)。これより東で入り江の範囲が海
BAY_HALF = 1.25                  # 入り江の南北の半幅 (km。本川の河口 y = 6.1 km を中心)
TANK_S = [1.25, 2.55, 3.85]      # ため池の堤の位置(T2 の上流端からの距離 km)
TANK_LA, TANK_WC = 0.80, 0.42    # 湛水域の長さ(堤から上流へ)と半幅 (km)
TANK_D = 2.5                     # 満水位での最大水深 (m)
FREEBOARD = 1.0                  # 堤の余裕高 (m。あふれ口だけ満水位)
KSV, KSV_TANK = 10.0, 0.3        # 鉛直透水係数 (mm/h): 流域 / ため池の底(堆積で目詰まり)
MINE_XY = (6.0, 2.2)             # 鉱山の排水口(T1 の中流)
FARM = dict(x0=9.5, x1=14.0, y0=7.5)     # 農地の範囲 (km。T2 の流域の低地)
# 観測点(河道の最寄りセル)と測線の名前・位置 (km)
GAUGES = [("G1", "T1", (6.6, 3.6)),      # 鉱山の下流 1.5 km
          ("G2", "M", (9.0, 6.6)),        # T1 合流後の本川
          ("G3", "T2", (12.0, 7.0)),      # 農地・ため池の支川の出口
          ("G4", "M", (14.0, 6.3)),       # T2 合流後の本川
          ("G5", "M", (18.5, 6.1))]       # 河口の近く


def densify(pts, step=0.01):
    out = []
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = max(int(np.hypot(x1 - x0, y1 - y0) / step), 1)
        for k in range(n):
            t = k / n
            out.append((x0 + t * (x1 - x0), y0 + t * (y1 - y0)))
    out.append(pts[-1])
    a = np.array(out)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(a[:, 0]), np.diff(a[:, 1])))])
    return a, s


def channels():
    am, sm = densify(MAIN["pts"])
    zm = MAIN["z0"] + (MAIN["z1"] - MAIN["z0"]) * sm / sm[-1]
    lines = {"M": (am, zm, sm, MAIN["width"])}
    for t in TRIBS:
        a, s = densify(t["pts"])
        d = np.hypot(am[:, 0] - a[-1, 0], am[:, 1] - a[-1, 1])
        zj = zm[np.argmin(d)]                       # 合流点の本川の河床高
        lines[t["name"]] = (a, t["z0"] + (zj - t["z0"]) * s / s[-1], s, t["width"])
    return lines


def build():
    xc = (np.arange(NX) + 0.5) * DX / KM
    yc = (np.arange(NY) + 0.5) * DX / KM
    X, Y = np.meshgrid(xc, yc)
    lines = channels()
    allp = np.concatenate([v[0] for v in lines.values()])
    allz = np.concatenate([v[1] for v in lines.values()])
    P = np.stack([X.ravel(), Y.ravel()], axis=1)
    dmin = np.full(P.shape[0], np.inf)
    zc = np.zeros(P.shape[0])
    for k in range(0, allp.shape[0], 500):
        q = allp[k:k + 500]
        dd = np.hypot(P[:, None, 0] - q[None, :, 0], P[:, None, 1] - q[None, :, 1])
        idx = np.argmin(dd, axis=1)
        dk = dd[np.arange(P.shape[0]), idx]
        upd = dk < dmin
        dmin[upd] = dk[upd]
        zc[upd] = allz[k:k + 500][idx[upd]]
    dmin = dmin.reshape(NY, NX) * KM
    zc = zc.reshape(NY, NX)
    # 斜面: 河道からの距離に比例して上がり(2.5 km で頭打ち)、北の丘陵ほど急
    S = 0.012 + 0.028 / (1.0 + np.exp((Y - 3.5) / 0.8))
    L0 = 2500.0
    z = zc + S * L0 * np.tanh(dmin / L0)
    rw = np.zeros((NY, NX), dtype=int)
    width = np.zeros((NY, NX))
    for a, _, _, wdt in lines.values():
        ii = np.clip((a[:, 0] * KM / DX).astype(int), 0, NX - 1)
        jj = np.clip((a[:, 1] * KM / DX).astype(int), 0, NY - 1)
        rw[jj, ii] = 1
        width[jj, ii] = np.maximum(width[jj, ii], wdt)
    z = np.where(rw == 1, zc - INCISE, z)
    # 流域(超楕円)を海岸線で切り、入り江(海域マスク)を足す
    land = (((X - 9.9) / 9.75) ** 4 + ((Y - 6.0) / 6.0) ** 4 <= 1.0) & (X < X_COAST)
    sea = (X > X_COAST) & (np.abs(Y - 6.1) <= BAY_HALF)
    mask = (land | sea).astype(int)
    sw = sea.astype(int)
    rw = rw * land
    width = np.where(rw == 1, width, 0.0)
    z = np.where(sea, 0.0, z)
    return X, Y, z, rw, width, mask, sw, lines


def add_tanks(X, Y, z, rw, width, lines):
    a, _, s, _ = lines["T2"]
    zt, rwt, wt = z.copy(), rw.copy(), width.copy()
    tid = np.zeros_like(rw)
    info = []
    for k, sb in enumerate(TANK_S, start=1):
        ib = np.argmin(np.abs(s - sb))
        bx, by = a[ib]
        iu = max(ib - 20, 0)
        ux, uy = a[iu] - a[ib]
        nrm = np.hypot(ux, uy)
        ux, uy = ux / nrm, uy / nrm
        al = (X - bx) * ux + (Y - by) * uy          # 上流向きの距離
        cr = -(X - bx) * uy + (Y - by) * ux         # 横断方向の距離
        jb, ibx = int(by * KM / DX), int(bx * KM / DX)
        fsl = z[jb, ibx] + INCISE + TANK_D - 0.5    # 満水位(あふれ口の高さ)
        r2 = ((al - TANK_LA / 2) / (TANK_LA / 2)) ** 2 + (cr / TANK_WC) ** 2
        basin = (r2 <= 1.0) & (al > 0.06)
        zb = fsl - 0.3 - (TANK_D - 0.3) * np.sqrt(np.clip(1 - r2, 0, 1))
        zt = np.where(basin, np.minimum(zt, zb), zt)
        rwt[basin] = 0
        wt[basin] = 0.0
        tid[basin] = k
        bund = (np.abs(al) < 0.13) & (np.abs(cr) < TANK_WC + 0.30)
        zt = np.where(bund, np.maximum(zt, fsl + FREEBOARD), zt)
        zt[jb, ibx] = fsl                           # あふれ口(幅 8 m の河道セル)
        rwt[jb, ibx] = 1
        wt[jb, ibx] = 8.0
        tid[jb, ibx] = 0
        vol = float(np.sum(np.where(basin, np.maximum(fsl - zt, 0), 0)) * DX * DX)
        info.append(dict(k=k, spill=(ibx + 1, jb + 1), fsl=float(fsl), ncell=int(basin.sum()), vol=vol))
    return zt, rwt, wt, tid, info


def nearest_channel(rw, x, y):
    js, iis = np.where(rw > 0)
    d = np.hypot((iis + 0.5) * DX / KM - x, (js + 0.5) * DX / KM - y)
    k = int(np.argmin(d))
    return int(iis[k]) + 1, int(js[k]) + 1


def main(out="data"):
    os.makedirs(out, exist_ok=True)
    X, Y, z, rw, width, mask, sw, lines = build()
    zt, rwt, wt, tid, info = add_tanks(X, Y, z, rw, width, lines)
    farm = ((X > FARM["x0"]) & (X < FARM["x1"]) & (Y > FARM["y0"]) & (mask > 0) & (sw == 0)
            & (rw == 0) & (rwt == 0) & (tid == 0))
    ksv = np.where(tid > 0, KSV_TANK, KSV)
    np.savetxt(f"{out}/z_notank.txt", z, fmt="%.3f")
    np.savetxt(f"{out}/z_tank.txt", zt, fmt="%.3f")
    np.savetxt(f"{out}/mask.txt", mask, fmt="%d")
    np.savetxt(f"{out}/sw.txt", sw, fmt="%d")
    np.savetxt(f"{out}/rw_notank.txt", rw, fmt="%d")
    np.savetxt(f"{out}/rw_tank.txt", rwt, fmt="%d")
    np.savetxt(f"{out}/width_notank.txt", width, fmt="%.1f")
    np.savetxt(f"{out}/width_tank.txt", wt, fmt="%.1f")
    np.savetxt(f"{out}/ksv_tank.txt", ksv, fmt="%.2f")
    np.savetxt(f"{out}/tank_id.txt", tid, fmt="%d")
    with open(f"{out}/farm_cells.txt", "w") as f:
        for j, i in zip(*np.where(farm)):
            f.write(f"{i + 1} {j + 1}\n")
    mine = nearest_channel(rw, *MINE_XY)
    with open(f"{out}/cells.txt", "w") as f:
        f.write(f"mine {mine[0]} {mine[1]}\n")
        for name, line, (x, y) in GAUGES:
            sel = np.zeros_like(rw)
            a = lines[line][0]
            ii = np.clip((a[:, 0] * KM / DX).astype(int), 0, NX - 1)
            jj = np.clip((a[:, 1] * KM / DX).astype(int), 0, NY - 1)
            sel[jj, ii] = 1
            gi, gj = nearest_channel(sel * rw, x, y)
            f.write(f"{name} {gi} {gj}\n")
        for d in info:
            jj, ii = np.where(tid == d["k"])
            kd = int(np.argmin(zt[jj, ii]))
            d["deep"] = (int(ii[kd]) + 1, int(jj[kd]) + 1)
            f.write(f"tank{d['k']} spill {d['spill'][0]} {d['spill'][1]} fsl {d['fsl']:.3f} "
                    f"cells {d['ncell']} volume_m3 {d['vol']:.0f} deepest {d['deep'][0]} {d['deep'][1]}\n")
    nland = int((mask - sw).sum())
    print(f"wrote {out}/: land cells {nland} ({nland * DX * DX / 1e6:.1f} km2), sea cells {int(sw.sum())}, "
          f"farm cells {int(farm.sum())} ({farm.sum() * DX * DX / 1e4:.0f} ha), mine cell {mine}")
    for d in info:
        print(f"  tank{d['k']}: spill cell {d['spill']}, full supply level {d['fsl']:.2f} m, "
              f"{d['ncell']} cells, volume {d['vol'] / 1e6:.2f} million m3")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
