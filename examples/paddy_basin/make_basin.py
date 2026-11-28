#!/usr/bin/env python3
"""examples/paddy_basin の入力と設定を作る(make が呼ぶ。numpy だけを使う)。

  python3 make_basin.py            data/ の入力と runs/param_<ケース>.txt・runs/cases.txt を書く

合成の傾斜地の流域(Δx = 200 m、51 列 × 50 行の格子。流域は 2500 セル = 100 km²)。田んぼダムの手引き(農林水産省 2026)の概算式と、その元に
なった吉川(2022)の簡便法が対象にする「背水の起きにくい中小規模の傾斜地の流域」を模す。

地形(i は西から、j は北から。出口は南端の中央 (26, 50)):
  s = 出口からの北向きの距離、d = 主川の谷の中心線からの距離
  谷底   z = 50 + s/250 + 0.01 d                      (d ≤ 1,000 m。主川へ 1/100 で下る幅 2 km の谷底)
  山地   z = 50 + s/250 + 10 + 0.08 (d − 1,000)        (d > 1,000 m。勾配 8 % の山腹)
  支川の谷  山腹に s = 1.5・3.5・5.5・7.5・9.5 km の谷(深さ 25 m、幅 σ = 300 m)を刻む。谷の深さは谷底の縁から
           500 m で 0 → 25 m に増す(谷の底も主川へ下り続け、窪地を作らない)
  南端の行は出口のセルだけを残す(ほかは領域マスクの外)。出口は水位規定(常に空)で、水はここからだけ出る
河道: 主川(中央の列 i = 26 の全ての行)と、支川(各支川の谷の中心の行で、谷底を横切って山腹の上から 0.6 km までの
     セル)を河道のセル(fn_rw)にする。河道のセルは河道に沿って下流へ、ほかのセルは最急勾配の 8 近傍へ落ちる落水線
     (D8)で集水面積 A を数え、幅 W = max(3, 2.5 √A) m(A は km²。出口で 25 m)のサブグリッド幅(fn_width。堤防
     なし)を与え、地盤を 2 m 掘り下げる
水田: 河道でないセルを、最寄りの河道からの高さ(落水線で最初に着く河道のセルの掘り下げ前の地盤からの比高。HAND)の
     低い順に水田のセル(水田面積率 0.9。残り 0.1 は畦畔・農道)にする。流域の水田面積率 A_r = 10・20・40・60 %
     (水田のセルの数 = A_r × 流域のセル数 / 0.9)。谷底から山腹へ広がる
粗度: 山地(森林)0.3、水田のセル 0.1(田んぼダムの有無・タンクの有無によらず同じ)、河道のセル 0.035
雨: 物部式(n = 0.5)の中央山型 24 時間雨量(1 時間ごとの段)。総雨量 150・250・350 mm(ピークの 1 時間に
     31・51・71 mm)。手引きの水田流出簡易計算プログラムの計画降雨波形と同じ作り方。山地は浸透なし(全量が流れる)

ケース(runs/param_<ケース>.txt。R<総雨量>_A<水田面積率 %>_<水田>):
  _0  水田のタンクなし(同じ地表で、雨はそのまま流れる。概算式の「非水田」の基準)
  _N  全ての水田が通常の落水口(取組率 0)
  _D  全ての水田が田んぼダム(取組率 1。機能分離型 φ50)
  _H  半分が田んぼダム(取組率 0.5。A_r = 40 % だけ。取組率に比例するかの確かめ)

data/ に書くもの(テキスト行列、行は北から南):
  z.txt・mask.txt・rw.txt・w.txt   地盤高(河道は掘り下げ後)、領域マスク、河道マスク、河道の幅 (m)
  acc.txt・hand.txt・order.txt     集水面積(セル数)、最寄りの河道からの比高 (m)、水田にする順位(図のため)
  frac_<A>.txt・rn_<A>.txt         水田面積率 0.9 / 0、粗度
"""
import math
import os

import numpy as np

NX, NY, DX = 51, 50, 200.0
IC = 26                                  # 主川の列(出口の列)
WF, S_M, S_FL, S_H = 1000.0, 1.0 / 250, 0.01, 0.08
TRIB_S = (1500.0, 3500.0, 5500.0, 7500.0, 9500.0)
TRIB_D, TRIB_SIG, TRIB_RAMP = 25.0, 300.0, 500.0
TRIB_TOP = 600.0                         # 支川の上端から流域の端までの距離 (m)
INCISE = 2.0                             # 河道の掘り下げ (m)
FRAC = 0.9                               # 水田のセルの水田面積率
AR_LEVELS = (10, 20, 40, 60)             # 流域の水田面積率 (%)
STORMS = (150, 250, 350)                 # 24 時間の総雨量 (mm)
RN_FOREST, RN_PADDY, RN_RIVER = 0.3, 0.1, 0.035
D8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]   # (di, dj)


def terrain():
    z = np.zeros((NY, NX))
    for j in range(1, NY + 1):
        s = (NY - j + 0.5) * DX
        for i in range(1, NX + 1):
            d = abs(i - IC) * DX
            zz = 50.0 + s * S_M
            if d <= WF:
                zz += S_FL * d
            else:
                zz += S_FL * WF + S_H * (d - WF)
                ramp = min(1.0, (d - WF) / TRIB_RAMP)
                for sk in TRIB_S:
                    zz -= TRIB_D * ramp * math.exp(-((s - sk) ** 2) / (2 * TRIB_SIG ** 2))
            z[j - 1, i - 1] = zz
    mask = np.ones((NY, NX), dtype=int)
    mask[NY - 1, :] = 0
    mask[NY - 1, IC - 1] = 1                # 出口のセル
    return z, mask


def channels(mask):
    """河道のセル(主川の列と支川の行)と、河道のセルの流下先(主川は南へ、支川は主川の列へ向かって隣へ)"""
    rw = np.zeros((NY, NX), dtype=int)
    to = -np.ones((NY, NX, 2), dtype=int)
    for j in range(NY):
        if mask[j, IC - 1]:
            rw[j, IC - 1] = 1
            if j < NY - 1:
                to[j, IC - 1] = (j + 1, IC - 1)
    dmax = (IC - 1) * DX - TRIB_TOP
    for sk in TRIB_S:
        j = NY - int(round(sk / DX + 0.5))          # s = (NY − j + 0.5) Δx の行(0 始まりの添字)
        for i in range(NX):
            d = abs(i + 1 - IC) * DX
            if 0 < d <= dmax:
                rw[j, i] = 1
                to[j, i] = (j, i + (1 if i + 1 < IC else -1))
    return rw, to


def d8(z, mask, rw, to):
    """河道でないセルの流下先(最急勾配の 8 近傍)と集水面積(セル数。自セルを含む)。河道のセルの流下先は
    channels() のまま"""
    order = sorted(((z[j, i], j, i) for j in range(NY) for i in range(NX) if mask[j, i]), reverse=True)
    for _, j, i in order:
        if rw[j, i]:
            continue
        best, bj, bi = 0.0, -1, -1
        for di, dj in D8:
            jj, ii = j + dj, i + di
            if 0 <= jj < NY and 0 <= ii < NX and mask[jj, ii]:
                g = (z[j, i] - z[jj, ii]) / (DX * math.hypot(di, dj))
                if g > best:
                    best, bj, bi = g, jj, ii
        if bj < 0:
            raise SystemExit("make_basin: a cell without a lower neighbour at (%d, %d)" % (i + 1, j + 1))
        to[j, i] = (bj, bi)
    acc = np.where(mask > 0, 1, 0)
    for _, j, i in order:                    # 高い順に下流へ足す(河道は地盤の低い下流ほど後に来る)
        if to[j, i, 0] >= 0:
            acc[to[j, i, 0], to[j, i, 1]] += acc[j, i]
    return to, acc


def hand(z, mask, to, rw):
    """最寄りの河道からの比高(落水線で最初に着く河道のセルの地盤からの高さ。河道のセルは 0)"""
    h = np.zeros((NY, NX))
    for j in range(NY):
        for i in range(NX):
            if not mask[j, i] or rw[j, i]:
                continue
            jj, ii = j, i
            while not rw[jj, ii]:
                jj, ii = to[jj, ii]
                if jj < 0:
                    raise SystemExit("make_basin: a flow path does not reach a channel cell")
            h[j, i] = z[j, i] - z[jj, ii]
    return h


def mononobe(total):
    """物部式(n = 0.5)の中央山型 24 時間雨量の 1 時間ごとの雨量 (mm)。累加雨量 R(t) = total √(t/24) の差を
    大きい順に、12〜13 h を中心として前後交互に並べる"""
    inc = sorted((total * (math.sqrt(k / 24.0) - math.sqrt((k - 1) / 24.0)) for k in range(1, 25)), reverse=True)
    slots = [12]
    for k in range(1, 13):
        slots += [12 - k, 12 + k]
    out = [0.0] * 24
    for v, sl in zip(inc, [s for s in slots if 0 <= s < 24]):
        out[sl] = v
    return out


def write(path, a, fmt):
    np.savetxt(path, a, fmt=fmt)


PARAM = """!======================================================================
! examples/paddy_basin: {title}
!   make_basin.py が作る設定(手で直さない)。流域・ケースの説明は ../README.md
!======================================================================
&list_sysparam
  f_gridsystem = 0
  dt = 4.0                  ! 時間刻み (s)(河道の √(gh) + u ≈ 8 m/s、Δx = 200 m で Cn ≈ 0.16)
  t0 = 0
  tt_c = '48h'              ! 雨 24 h + 雨の後 24 h
  dt_disp_c = '6h'
  dt_file_c = '6h'
  dt_recrd_c = '5m'         ! 測線・プローブ・paddy.csv の記録間隔(ピークを 5 分で拾う)
  fn_geoinfo = '-'
  fn_channel = '-'          ! 河道の幅(&list_channel)
  fn_precip = '-'
  fn_record = '-'
  fn_boundary = '-'
{paddy_line}  dir_data = '../data'
  dir_result = 'result_{case}'
  f_output_mode = 2         ! 分布は bil
  f_check_cfl = 0
  dd = 0.0001               ! 斜面の薄い流れを止めない
  dv = 0.0001
/

&list_initial
  f_htype = 0
  h0 = 0.0
/

&list_geoinfo
  nx = {nx}
  ny = {ny}
  dx = {dx}
  dy = {dx}
  f_ztype = 1
  fn_z = 'z.txt'            ! 河道は 2 m 掘り下げ済み
  f_masktype = 1
  fn_mask = 'mask.txt'      ! 流域(南端の行は出口のセルだけ)
  fn_rw = 'rw.txt'          ! 河道のセル(主川の列と支川の行)
  rn0_rw = {rn_river}
  f_rntype = 1
  fn_rn = 'rn_{ar}.txt'     ! 山地 0.3、水田のセル 0.1
/

&list_channel
  fn_width = 'w.txt'        ! 河道の幅 max(3, 2.5 √A) m(堤防なし)
/

&list_bound_stage
  stage_cell(:,1,1) = {ic}, {ny}   ! 出口(常に空にする水位規定。水はここからだけ出る)
  stage_eta(1) = -999.0
/

&list_precip
  prtype = 1                ! 一様な雨(時刻 min, mm/h)。物部式の中央山型 24 時間 {total} mm
{rain}
/

&list_record
  pbxytype = 0
  pbxy(:,1) = {ic}, {nym1}     ! 出口の上流の主川
  flxytype = 0
  flxy(:,1) = 1, {nym1}, {nx}, {nym1}   ! 出口の 1 行上を横切る測線(出口へ入る水はすべてここを通る)
/
{paddy_block}"""

PADDY = """
&list_paddy
  fn_pd_frac = 'frac_{ar}.txt'     ! 水田のセルの水田面積率 0.9(流域の水田面積率 {ar} %)
  pd_adopt = {adopt}               ! 取組率(0 = 全て通常の落水口、1 = 全て田んぼダム)
/
"""


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(here, "data")
    r = os.path.join(here, "runs")
    os.makedirs(d, exist_ok=True)
    os.makedirs(r, exist_ok=True)
    z0, mask = terrain()
    rw, to = channels(mask)
    to, acc = d8(z0, mask, rw, to)
    area = acc * DX * DX / 1e6
    w = np.where(rw > 0, np.maximum(3.0, 2.5 * np.sqrt(area)), 0.0)
    hh = hand(z0, mask, to, rw)
    z = np.where(rw > 0, z0 - INCISE, z0)
    ncell = int(mask.sum())
    cand = sorted((hh[j, i], j, i) for j in range(NY) for i in range(NX) if mask[j, i] and not rw[j, i])
    order = np.zeros((NY, NX), dtype=int)
    for k, (_, j, i) in enumerate(cand):
        order[j, i] = k + 1
    write(os.path.join(d, "z.txt"), z, "%.3f")
    write(os.path.join(d, "mask.txt"), mask, "%d")
    write(os.path.join(d, "rw.txt"), rw, "%d")
    write(os.path.join(d, "w.txt"), w, "%.2f")
    write(os.path.join(d, "acc.txt"), acc, "%d")
    write(os.path.join(d, "hand.txt"), hh, "%.3f")
    write(os.path.join(d, "order.txt"), order, "%d")
    npaddy = {}
    for ar in AR_LEVELS:
        n = int(round(ar / 100.0 * ncell / FRAC))
        if n > len(cand):
            raise SystemExit("make_basin: not enough cells for A_r = %d %%" % ar)
        npaddy[ar] = n
        isp = (order > 0) & (order <= n)
        write(os.path.join(d, "frac_%d.txt" % ar), np.where(isp, FRAC, 0.0), "%.2f")
        write(os.path.join(d, "rn_%d.txt" % ar), np.where(isp, RN_PADDY, RN_FOREST), "%.3f")
    cases = []
    for total in STORMS:
        inc = mononobe(total)
        # 時刻の点を 1 時間ごとに 2 つ(段の始めと終わり)。点の間は直線で補間されるので、次の段の始めを 0.001 分
        # 後ろにずらして段にする
        rain_l = []
        for k, v in enumerate(inc):
            rain_l.append("  prval(1:2,%d) = %.3f, %.3f" % (2 * k + 1, 60.0 * k + (0.001 if k > 0 else 0.0), v))
            rain_l.append("  prval(1:2,%d) = %.3f, %.3f" % (2 * k + 2, 60.0 * (k + 1), v))
        rain_l.append("  prval(1:2,49) = 1440.001, 0.0")
        rain_l.append("  prval(1:2,50) = 99999, 0.0")
        rain = "\n".join(rain_l)
        for ar in AR_LEVELS:
            for tag, adopt in (("0", None), ("N", 0.0), ("D", 1.0), ("H", 0.5)):
                if tag == "H" and ar != 40:
                    continue
                case = "R%d_A%d_%s" % (total, ar, tag)
                if adopt is None:
                    title = "総雨量 %d mm、水田のセル(流域の %d %%)にタンクなし(非水田の基準)" % (total, ar)
                    pl, pb = "", ""
                else:
                    kind = {0.0: "全て通常の落水口", 1.0: "全て田んぼダム", 0.5: "半分が田んぼダム"}[adopt]
                    title = "総雨量 %d mm、流域の水田面積率 %d %%、%s" % (total, ar, kind)
                    pl = "  fn_paddy = '-'            ! 田んぼダム(サブグリッドの水田タンク = 表現 A、片方向)\n"
                    pb = PADDY.format(ar=ar, adopt="%.1f" % adopt)
                txt = PARAM.format(title=title, paddy_line=pl, case=case, nx=NX, ny=NY, dx=DX, rn_river=RN_RIVER,
                                   ar=ar, ic=IC, nym1=NY - 1, total=total, rain=rain, paddy_block=pb)
                with open(os.path.join(r, "param_%s.txt" % case), "w", encoding="utf-8") as f:
                    f.write(txt)
                cases.append(case)
    with open(os.path.join(r, "cases.txt"), "w") as f:
        f.write("\n".join(cases) + "\n")
    nch = int(rw.sum())
    print("basin: %d cells = %.1f km2, channel cells %d (outlet catchment %.1f km2, width %.1f m at the outlet)"
          % (ncell, ncell * DX * DX / 1e6, nch, area[NY - 1, IC - 1], w[NY - 1, IC - 1]))
    print("relief: %.1f .. %.1f m; paddy cells: %s; HAND at the last paddy cell: %s"
          % (z.min(), z.max(), ", ".join("A%d=%d" % (a, npaddy[a]) for a in AR_LEVELS),
             ", ".join("A%d=%.1f m" % (a, cand[npaddy[a] - 1][0]) for a in AR_LEVELS)))
    print("rain: " + ", ".join("%d mm (peak %.1f mm/h)" % (t, max(mononobe(t))) for t in STORMS))
    print("cases: %d (runs/cases.txt)" % len(cases))


if __name__ == "__main__":
    main()
