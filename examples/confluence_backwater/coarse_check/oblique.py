#!/usr/bin/env python3
# examples/confluence_backwater の補足 1「粗い格子」の切り分け: 斜めの河道での河道の表し方(oblique/ に書く。
# make coarse_oblique が呼ぶ)
#   直線で一様な幅 B(120 m・200 m)の河道を、格子の軸から 0°・18.4°・26.6°・33.7°・45° の向きに置き、一様な流量
#   (単位幅 8.5 m2/s。等流水深 3.50 m)を流した定常の等流で、通水の幅(等流水深から逆算)を川幅と比べる。勾配 1/1000、
#   粗度 0.03、長さ 8 km。河道の外は計算しない(壁)。上流端は区間流入、下流端は等流水深の水位。測るのは中ほどの
#   2 km(中心線の距離 3〜5 km)で、通水の幅 = n Q /(水深^(5/3) √水面勾配)。
#   中心線からの距離 dn のセル中心は、勾配 p/q の向きで間隔 δ = Δ/√(p² + q²) の「列」に並ぶ(0°: 100 m、
#   18.4°: 31.6 m、26.6°: 44.7 m、33.7°: 27.7 m、45°: 70.7 m)。中心線を 2 列の真ん中に置き、列を選んで河道にする:
#     band_lo  n = floor(B/δ) 列を解像した河道            band_hi  n + 1 列を解像した河道
#     mix      n 列を解像 + 外側の 1 列を残りの幅 B − nδ のサブグリッド河道(例題の狭窄部の表し方)
#     split    n + 1 列をすべて幅 B/(n + 1) のサブグリッド河道
#     k1, k2   解像 n 列を、隣り合う列の境目で中心線に最も近い k 行が両方の列の解像セルになるように太らせる
#              (くびれをなくす。make_coarse.py の THICK と同じ規則)
#     fine     細かい格子(Δx = 20 m)で round(B/δ) 列を解像(表した幅で割って比べる)
#   流入は解像したセルから入れる(流入の面は幅で絞られないので、細いサブグリッドのセルへ等分すると流入口で振動する。
#   開発記録 §18 の制約 (5))。粗い格子は 8 h、細かい格子は 4 h(最後の 1 h の水位の変化で定常を確かめる)。
#   python3 oblique.py gen     入力(oblique/data_*)・設定ファイル(oblique/param_*.txt)・ケースの一覧(oblique/cases.txt)
#   python3 oblique.py table   計算の後に数表(引数 en を足すと英語)
import math
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "oblique")
S, RN, L, QB = 1.0 / 1000.0, 0.03, 8000.0, 8.5
ANGLES = [("a00", 0, 1), ("a18", 1, 3), ("a27", 1, 2), ("a34", 2, 3), ("a45", 1, 1)]   # 勾配 p/q
WIDTHS = (120.0, 200.0)
S1, S2 = 3000.0, 5000.0
RESOLVED = 9999.0
EN = "en" in sys.argv[1:]


def T(ja, en):
    return en if EN else ja


def hn(q):
    return (RN * q / math.sqrt(S)) ** 0.6


def cases():
    out = []
    for an, p, q in ANGLES:
        d = 100.0 / math.hypot(p, q)
        for b in WIDTHS:
            n = int(math.floor(b / d + 1e-9))
            reps = ["band_lo"] if abs(b / d - n) < 1e-6 else ["band_lo", "band_hi", "mix", "split"]
            reps += ["k1", "k2"]
            out += [(f"{an}_b{int(b)}_{r}", an, b, r, 100.0) for r in reps]
            out.append((f"{an}_b{int(b)}_fine", an, b, "fine", 20.0))
    return out


def build(an, b, rep, dx):
    p, q = {a: (pp, qq) for a, pp, qq in ANGLES}[an]
    r = math.hypot(p, q)
    st, ct = p / r, q / r
    nx = int(math.ceil(L * ct / 100.0)) * int(100 / dx)
    lx = nx * dx
    margin = 400.0
    # 中心線(x = 0 で高さ y0)が粗い格子・細かい格子とも 2 列の真ん中を通る条件: y0 = (Δ/q)((p + q − 1)/2 + K)
    y0 = (100.0 / q) * ((p + q - 1) / 2.0 + math.ceil(margin / (100.0 / q)))
    ly = math.ceil((y0 + lx * st / ct + margin) / 100.0) * 100.0
    ny = int(round(ly / dx))
    d = dx / r
    X = (np.arange(1, nx + 1)[None, :] - 0.5) * dx
    Y = ly - (np.arange(1, ny + 1)[:, None] - 0.5) * dx
    dn = -st * X + ct * (Y - y0)
    s = ct * X + st * (Y - y0)
    k = np.floor(dn / d + 1e-6).astype(int)           # 列 k: dn = (k + 1/2) δ
    width = np.zeros((ny, nx))
    n = int(round(b / d)) if rep == "fine" else int(math.floor(b / d + 1e-9))
    kmin = -int(math.ceil(n / 2))
    core = (k >= kmin) & (k <= kmin + n - 1)
    extra = k == kmin + n
    if rep in ("fine", "band_lo", "k1", "k2"):
        width[core] = RESOLVED
        brep = n * d
        if rep in ("k1", "k2"):
            yj = ly - (np.arange(ny) + 0.5) * dx
            for i in range(nx - 1):
                yc = y0 + (i + 1) * dx * st / ct
                # 中心線に近い順(1e-6 m で丸めた距離。同じ距離なら北の行)
                for j in np.argsort(np.round(np.abs(yj - yc), 6), kind="stable")[:int(rep[1])]:
                    width[j, i] = width[j, i + 1] = RESOLVED
    elif rep == "band_hi":
        width[core | extra] = RESOLVED
        brep = (n + 1) * d
    elif rep == "mix":
        width[core] = RESOLVED
        width[extra] = b - n * d
        brep = b
    else:                                             # split
        width[core | extra] = b / (n + 1)
        brep = b
    chan = width > 0
    z = np.where(chan, 20.0 + S * L - S * s, -9999.0)
    sel = (s >= S1) & (s <= S2)
    area = float((width[sel] >= RESOLVED).sum() + np.where((width > 0) & (width < RESOLVED), width / d, 0.0)[sel].sum()) \
        * dx * dx / (S2 - S1)
    return dict(chan=chan, width=width, z=z, s=s, nx=nx, ny=ny, lx=lx, ct=ct, brep=brep, area=area)


PARAM = """!======================================================================
! confluence_backwater 補足 1 の切り分け(斜めの河道): {title}
!   直線で一様な河道の定常の等流。入力は coarse_check/oblique.py が data_{name}/ に作る
!======================================================================
&list_sysparam
  f_gridsystem = 0
  dt = {dt}
  t0 = 0
  tt_c = '{tt}'
  dt_disp_c = '1h'
  dt_file_c = '1h'          ! 最後の 2 つの出力で定常を確かめる
  fn_geoinfo = '-'
  fn_enc = '-'
  fn_initial = '-'
  fn_boundary = '-'
{chan_fn}  dir_data = 'data_{name}'
  dir_result = 'result_{name}'
  f_out_h = 1
  f_out_e = 1
/

&list_initial
  f_htype = 1
  fn_hinit = 'h0.txt'       ! 等流水深
/

&list_enc
  f_exflux_reduction = 1
/

&list_geoinfo
  nx = {nx}
  ny = {ny}
  dx = {dx}
  dy = {dx}
  f_ztype = 1
  fn_z = 'z.txt'
  f_rntype = 1
  fn_rn = 'rn.txt'
  f_masktype = 1
  fn_mask = 'mask.txt'
{rw}/
{channel}
&list_bound_stage
  fn_stage_cell(1) = 'cells_out.txt'
  fn_stage_val(1) = 'stage.txt'
/
&list_bound_inflow
  fn_inflow_cell(1) = 'cells_in.txt'
  fn_inflow_val(1) = 'q.txt'
  inflow_dist(1) = 2
/
"""
CHANNEL = """
&list_channel
  fn_bank = 'bank.txt'
  f_bank_datum = 2
  fn_width = 'width.txt'
/
"""
REP_TITLE = {"band_lo": "解像 n 列", "band_hi": "解像 n+1 列", "mix": "解像 n 列 + 残りの幅のサブグリッド 1 列",
             "split": "n+1 列のサブグリッドに幅を等分", "fine": "細かい格子 Δx = 20 m",
             "k1": "解像 n 列を段で 1 行共有するように太らせる", "k2": "解像 n 列を段で 2 行共有するように太らせる"}


def gen():
    os.makedirs(OUT, exist_ok=True)
    names = []
    for name, an, b, rep, dx in cases():
        g = build(an, b, rep, dx)
        dd = os.path.join(OUT, f"data_{name}")
        os.makedirs(dd, exist_ok=True)
        chan, nx, ny = g["chan"], g["nx"], g["ny"]
        coarse = rep != "fine"
        h = hn(QB)
        arrays = [("z", g["z"], "%.3f"), ("rn", np.full(chan.shape, RN), "%.3f"), ("mask", chan.astype(int), "%d"),
                  ("h0", np.where(chan, h, 0.0), "%.3f")]
        if coarse:
            arrays += [("rw", chan.astype(int), "%d"), ("width", g["width"], "%.2f"),
                       ("bank", np.where(chan, g["z"] + 10.0, -9999.0), "%.3f")]
        for fn, a, fmt in arrays:
            np.savetxt(os.path.join(dd, f"{fn}.txt"), a, fmt=fmt)
        res = g["width"] >= RESOLVED
        src = res if res[:, 0].any() else chan
        with open(os.path.join(dd, "cells_in.txt"), "w") as f:
            f.writelines(f"1 {j + 1}\n" for j in range(ny) if src[j, 0])
        with open(os.path.join(dd, "cells_out.txt"), "w") as f:
            f.writelines(f"{nx} {j + 1}\n" for j in range(ny) if chan[j, nx - 1])
        s_out = (g["lx"] - 0.5 * dx) / g["ct"]          # 出口の列の中心線上の距離
        eta = 20.0 + S * L - S * s_out + h
        with open(os.path.join(dd, "stage.txt"), "w") as f:
            f.write(f"0 {eta:.4f}\n1440 {eta:.4f}\n")
        with open(os.path.join(dd, "q.txt"), "w") as f:
            f.write(f"0 {QB * b:.1f}\n1440 {QB * b:.1f}\n")
        ang = {"a00": "0°", "a18": "18.4°", "a27": "26.6°", "a34": "33.7°", "a45": "45°"}[an]
        with open(os.path.join(OUT, f"param_{name}.txt"), "w", encoding="utf-8") as f:
            f.write(PARAM.format(title=f"{ang}・川幅 {b:.0f} m・{REP_TITLE[rep]}", name=name, dt="2.0" if coarse else "1.0",
                                 tt="8h" if coarse else "4h", chan_fn="  fn_channel = '-'\n" if coarse else "",
                                 nx=nx, ny=ny, dx=f"{dx:.1f}", rw="  fn_rw = 'rw.txt'\n" if coarse else "",
                                 channel=CHANNEL if coarse else ""))
        names.append(name)
    with open(os.path.join(OUT, "cases.txt"), "w") as f:
        f.write("\n".join(names) + "\n")
    print(f"{len(names)} ケースの入力を oblique/ に書いた")


def measure(name, an, b, rep, dx):
    g = build(an, b, rep, dx)
    last = 4 if rep == "fine" else 8
    rd = os.path.join(OUT, f"result_{name}")
    e1 = np.loadtxt(os.path.join(rd, f"E{last:04d}.txt"))
    e0 = np.loadtxt(os.path.join(rd, f"E{last - 1:04d}.txt"))
    chan, s = g["chan"], g["s"]
    sel = chan & (s >= S1) & (s <= S2)
    h = float((e1 - g["z"])[sel].mean())
    slope = -float(np.polyfit(s[sel], e1[sel], 1)[0])
    beff = RN * QB * b / (math.sqrt(slope) * h ** (5.0 / 3.0))
    # 流入口のセルを除いた、最後の 1 h の水位の変化
    drift = float(np.abs(e1 - e0)[chan & (np.arange(g["nx"])[None, :] > 0)].max())
    return dict(beff=beff, rel=beff / (g["brep"] if rep == "fine" else b), h=h, slope=slope / S, drift=drift, area=g["area"])


def table():
    missing = [c[0] for c in cases()
               if not os.path.exists(os.path.join(OUT, f"result_{c[0]}", "E0004.txt" if c[3] == "fine" else "E0008.txt"))]
    if missing:
        print(T("計算していない: ", "not computed: ") + " ".join(missing))
        return
    val = {c[0]: measure(*c) for c in cases()}
    ang = {"a00": "0°", "a18": T("18.4°(1:3)", "18.4° (1:3)"), "a27": T("26.6°(1:2)", "26.6° (1:2)"),
           "a34": T("33.7°(2:3)", "33.7° (2:3)"), "a45": "45°"}
    print(T("== 通水の幅 ÷ 川幅(川幅 120 m / 200 m。Δx = 20 m は表した幅で割った値)",
            "== Conveyance width ÷ channel width (120 m / 200 m wide; Δx = 20 m divided by the width it represents)"))
    print(T("| 向き | 解像 n 列 | 解像 n+1 列 | 解像 + 残り | 等分 | 段で 2 行を共有 | Δx = 20 m |",
            "| Direction | n resolved rows | n+1 resolved rows | resolved + remainder | equal split | 2 rows shared at steps | Δx = 20 m |"))
    print("|---|---:|---:|---:|---:|---:|---:|")
    for an, p, q in ANGLES:
        cells = []
        for rep in ("band_lo", "band_hi", "mix", "split", "k2", "fine"):
            v = [val.get(f"{an}_b{int(b)}_{rep}") for b in WIDTHS]
            cells.append(" / ".join(f"{x['rel']:.2f}" if x else "—" for x in v))
        print(f"| {ang[an]} | " + " | ".join(cells) + " |")
    print()
    print(T("ケースごとの値(水深 m・水面勾配 ÷ 河床勾配・通水の幅 m・表した面積の幅 m・通水 ÷ 面積・流入口を除く最後の"
            " 1 h の水位の変化 m):",
            "Per case (depth m, water-surface slope ÷ bed slope, conveyance width m, width of the represented area m, "
            "conveyance ÷ area, largest change in the last hour away from the inflow cells m):"))
    for name, v in val.items():
        print(f"  {name:20s} {v['h']:6.3f} {v['slope']:6.3f} {v['beff']:7.1f} {v['area']:7.1f} {v['beff'] / v['area']:5.2f}"
              f" {v['drift']:.4f}")


if __name__ == "__main__":
    {"gen": gen, "table": table}[sys.argv[1]]()
