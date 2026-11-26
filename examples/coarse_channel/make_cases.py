#!/usr/bin/env python3
"""examples/coarse_channel: 粗い格子で川をどう表すか — 系統的な確かめの入力と設定を作る(make が呼ぶ)

  python3 make_cases.py gen [系列 ...]    runs/data_<ケース>/ の入力と runs/param_<ケース>.txt、runs/cases_<系列>.txt
  python3 make_cases.py list <系列>       その系列のケース名(1 行に 1 つ)

どのケースも、勾配 1/1000・粗度 0.03 の河道に単位幅流量 8.5 m²/s(等流水深 3.50 m)を流す定常の流れ。粗い格子は
Δx = 100 m、比べる細かい格子は Δx = 20 m。直線の河道では、中ほどの 2 km(中心線の距離 3〜5 km)の水深 h と水面勾配 I
から通水の幅 B_eff = n Q /(h^(5/3) √I) を逆算し、川幅 B と比べる(1 なら川幅どおりに流れる)。

系列:
  axis    格子に沿う直線の河道。川幅 B = 0.2〜3 セル × 表し方(サブグリッド 1 列・解像の切り捨て/切り上げ・等分・
          解像 + 残り)
  oblique 格子に斜めの直線の河道。向き 0°・11.3°・18.4°・26.6°・33.7°・45°(勾配 0・1:5・1:3・1:2・2:3・1:1)×
          川幅 1.2・2・3 セル × 表し方(上の 4 つと、段を太らせる k1・k2、太らせて幅を縮める k2w)+ 細かい格子
  wide    広い川(川幅 6・10 セル)の斜めの区間 × 表し方(解像・n+1 列・解像 + 残り・段を太らせる)
  mask    1 セル幅の川(川幅 0.3・0.6・0.8・1.0 セル)の河道マスク: 8 連結(1 列に 1 セル)と 4 連結(段で 2 セル)
  bend    屈曲(90° の円弧。半径 500・1,000・1,500 m、川幅 2 セル)× 段の太らせ方 + 細かい格子
  wet     河道の脇の水: 地形の河岸の乾いた・雨の水膜と、仮想壁面の向こうの乾いた・雨・湛水

セルの中心は、勾配 p/q の向きでは、中心線からの距離が間隔 δ = Δ/√(p² + q²) の「列」に並ぶ(0°: 100 m、11.3°: 19.6 m、
18.4°: 31.6 m、26.6°: 44.7 m、33.7°: 27.7 m、45°: 70.7 m)。直線の河道の表し方は、この列を選んで作る:
  lo     n = floor(B/δ) 列を解像した河道           hi     n + 1 列を解像した河道
  mix    n 列を解像 + 外側の 1 列を残りの幅 B − nδ のサブグリッド河道(n = 0 ならサブグリッド 1 列)
  split  n + 1 列をすべて幅 B/(n + 1) のサブグリッド河道(等分)
  k1・k2 lo を、隣り合う列の境目で中心線に最も近い k 行が両方の列の解像セルになるように太らせる(くびれをなくす)
  k2w    k2 で太らせた帯のセルを、表す面積が川幅と同じになる幅のサブグリッド河道にする
  sub1   1 列(格子に沿う 1 行)を幅 B のサブグリッド河道にする(B ≥ Δ なら幅で絞られない解像セル)
  d8     1 列に 1 セル(8 連結。D8 の落水線と同じ型)を幅 B のサブグリッド河道にする
  st4    幅 ω = Δ(cos θ + sin θ) の帯に入るセル(4 連結の階段)を幅 B のサブグリッド河道にする
  fine   細かい格子(Δx = 20 m)で round(B/δ) 列を解像(表した幅で割って比べる)
"""
import math
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
DX, DXF = 100.0, 20.0               # 粗い格子・細かい格子
S, RN, QB = 1.0 / 1000.0, 0.03, 8.5  # 河床勾配、粗度、単位幅流量 (m²/s)
L = 8000.0                           # 直線の河道の長さ(中心線)
S1, S2 = 3000.0, 5000.0              # 測る区間(中心線の距離)
RESOLVED = 9999.0                    # 解像した河道の幅(セルより広い = 幅で絞らない)
Z0 = 20.0 + S * L                    # 上流端の河床
ANGLES = {"a00": (0, 1), "a11": (1, 5), "a18": (1, 3), "a27": (1, 2), "a34": (2, 3), "a45": (1, 1)}
ANGLE_DEG = {k: math.degrees(math.atan2(p, q)) for k, (p, q) in ANGLES.items()}
AXIS_W = (20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0, 200.0, 250.0, 300.0)
OBL_W = (120.0, 200.0, 300.0)
WIDE_W = (600.0, 1000.0)
MASK_W = (30.0, 60.0, 80.0, 100.0)
BEND_R = (500.0, 1000.0, 1500.0)
BEND_W = 200.0


def hn(q):
    """マニングの等流水深(広い矩形断面。q は単位幅流量)"""
    return (RN * q / math.sqrt(S)) ** 0.6


# ------------------------------------------------------------------ ケースの一覧
def cases(series):
    """(名前, 種類, 引数の辞書) の並び"""
    out = []
    if series == "axis":
        for b in AXIS_W:
            n = int(math.floor(b / DX + 1e-9))
            reps = ["sub1"]
            if n >= 1:
                reps.append("lo")
            if abs(b / DX - n) > 1e-6:
                reps.append("hi")
                if n >= 1:
                    reps += ["mix", "split"]
            out += [(f"axis_b{int(b):04d}_{r}", "straight", dict(an="a00", b=b, rep=r, dx=DX)) for r in reps]
    elif series == "oblique":
        for an, (p, q) in ANGLES.items():
            d = DX / math.hypot(p, q)
            for b in OBL_W:
                n = int(math.floor(b / d + 1e-9))
                reps = ["lo"] if abs(b / d - n) < 1e-6 else ["lo", "hi", "mix", "split"]
                if an != "a00":
                    reps += ["k1", "k2", "k2w"]
                out += [(f"obl_{an}_b{int(b):04d}_{r}", "straight", dict(an=an, b=b, rep=r, dx=DX)) for r in reps]
                out.append((f"obl_{an}_b{int(b):04d}_fine", "straight", dict(an=an, b=b, rep="fine", dx=DXF)))
    elif series == "wide":
        for an, (p, q) in ANGLES.items():
            d = DX / math.hypot(p, q)
            for b in WIDE_W:
                n = int(math.floor(b / d + 1e-9))
                reps = ["lo"] if abs(b / d - n) < 1e-6 else ["lo", "hi", "mix"]
                if an != "a00":
                    reps += ["k1", "k2"]
                out += [(f"wide_{an}_b{int(b):04d}_{r}", "straight", dict(an=an, b=b, rep=r, dx=DX)) for r in reps]
    elif series == "mask":
        for an in ANGLES:
            for b in MASK_W:
                reps = ["d8"] if an == "a00" else ["d8", "st4"]
                out += [(f"mask_{an}_b{int(b):04d}_{r}", "straight", dict(an=an, b=b, rep=r, dx=DX)) for r in reps]
    elif series == "bend":
        for r in BEND_R:
            for rep in ("lo", "k1", "k2", "fine"):
                out.append((f"bend_r{int(r):04d}_{rep}", "bend", dict(r=r, b=BEND_W, rep=rep, dx=DXF if rep == "fine" else DX)))
    elif series == "wet":
        for var in ("dry", "rain", "wall_dry", "wall_rain", "wall_pond"):
            out.append((f"wet_{var}", "wet", dict(var=var)))
    else:
        raise ValueError(series)
    return out


SERIES = ("axis", "oblique", "wide", "mask", "bend", "wet")


# ------------------------------------------------------------------ 直線の河道
def straight(an, b, rep, dx):
    """直線で一様な幅 b の河道。戻り値の辞書: width(0 = 河道でない、RESOLVED = 解像、それ以外 = サブグリッドの幅)、
    z(河床)、s(中心線の距離)、dn(中心線からの距離)、nx・ny・lx、ct(cos θ)、brep(比べる幅)、area(表した面積の幅)"""
    p, q = ANGLES[an]
    r = math.hypot(p, q)
    st, ct = p / r, q / r
    nx = int(math.ceil(L * ct / DX)) * int(round(DX / dx))
    lx = nx * dx
    margin = max(400.0, 0.75 * b + 200.0)
    # 中心線(x = 0 で高さ y0)が粗い格子・細かい格子とも 2 列の真ん中を通る: y0 = (Δ/q)((p + q − 1)/2 + K)
    y0 = (DX / q) * ((p + q - 1) / 2.0 + math.ceil(margin / (DX / q)))
    ly = math.ceil((y0 + lx * st / ct + margin) / DX) * DX
    ny = int(round(ly / dx))
    d = dx / r
    X = (np.arange(1, nx + 1)[None, :] - 0.5) * dx
    Y = ly - (np.arange(1, ny + 1)[:, None] - 0.5) * dx
    dn = -st * X + ct * (Y - y0)
    s = ct * X + st * (Y - y0)
    k = np.floor(dn / d + 1e-6).astype(int)             # 列 k: dn = (k + 1/2) δ
    width = np.zeros((ny, nx))
    n = int(round(b / d)) if rep == "fine" else int(math.floor(b / d + 1e-9))
    kmin = -int(math.ceil(n / 2))
    core = (k >= kmin) & (k <= kmin + n - 1)
    extra = k == kmin + n
    brep = b
    if rep in ("fine", "lo", "k1", "k2", "k2w"):
        width[core] = RESOLVED
        brep = n * d if rep == "fine" else b
        if rep in ("k1", "k2", "k2w"):
            kk = 1 if rep == "k1" else 2
            yj = ly - (np.arange(ny) + 0.5) * dx
            for i in range(nx - 1):
                yc = y0 + (i + 1) * dx * st / ct
                # 中心線に近い順(1e-6 m で丸めた距離。同じ距離なら北の行)
                for j in np.argsort(np.round(np.abs(yj - yc), 6), kind="stable")[:kk]:
                    width[j, i] = width[j, i + 1] = RESOLVED
    elif rep == "hi":
        width[core | extra] = RESOLVED
    elif rep == "mix":
        if n >= 1:
            width[core] = RESOLVED
        width[extra] = b - n * d
    elif rep == "split":
        width[core | extra] = b / (n + 1)
    elif rep == "sub1":                                 # 格子に沿う 1 行(0° だけ)
        width[k == 0] = b if b < dx else RESOLVED
    elif rep == "d8":                                   # 1 列に 1 セル(中心線に最も近いセル)
        for i in range(nx):
            j = int(np.argmin(np.round(np.abs(dn[:, i]), 6)))
            width[j, i] = b if b < dx else RESOLVED
    elif rep == "st4":                                  # 4 連結の階段: −ω/2 < dn ≤ ω/2
        om = dx * (ct + st)
        width[(dn > -om / 2 + 1e-6) & (dn <= om / 2 + 1e-6)] = b if b < dx else RESOLVED
    else:
        raise ValueError(rep)
    if rep == "k2w":
        sel = (s >= S1) & (s <= S2) & (width > 0)
        a = float(sel.sum()) * dx * dx / (S2 - S1)      # 太らせた帯が表す幅
        w = dx * b / a
        width[width > 0] = w if w < dx else RESOLVED
    chan = width > 0
    z = np.where(chan, Z0 - S * s, -9999.0)
    sel = (s >= S1) & (s <= S2)
    area = float((width[sel] >= RESOLVED).sum() + np.where(chan & (width < RESOLVED), width / dx, 0.0)[sel].sum()) \
        * dx * dx / (S2 - S1)
    # 図に描く本当の河道の両岸(中心線からの距離): 帯の表し方は列 kmin の下の縁から川幅 b、
    # 1 列・1 行の表し方は中心線を挟んで川幅 b(sub1 は列 0 の中)
    if rep in ("d8", "st4"):
        out = (-b / 2, b / 2)
    elif rep == "sub1":
        out = (0.0, b)
    else:
        out = (kmin * d, kmin * d + (n * d if rep == "fine" else b))
    return dict(width=width, z=z, s=s, dn=dn, nx=nx, ny=ny, lx=lx, ly=ly, ct=ct, st=st, y0=y0, d=d, n=n, kmin=kmin,
                out=out, brep=brep, area=area, theta=math.atan2(p, q))


# ------------------------------------------------------------------ 屈曲(90° の円弧)
def bend_geom(r):
    """中心線: 西端から東へ直線 → 半径 r で右(南)へ 90° 曲がる円弧 → 南へ直線で南端へ。戻り値: 長さ・大きさ・関数"""
    l1, l2 = 3000.0, 3000.0                             # 円弧の前後の直線
    margin = 600.0
    xa, ya = l1, l2 + r + margin                        # 円弧の始まり(中心線)
    xc, yc = xa, ya - r                                 # 円弧の中心
    lx = math.ceil((xa + r + margin) / DX) * DX
    ly = math.ceil((ya + margin) / DX) * DX
    larc = r * math.pi / 2
    return dict(l1=l1, l2=l2, r=r, xa=xa, ya=ya, xc=xc, yc=yc, lx=lx, ly=ly, larc=larc, ltot=l1 + larc + (ya - r))


def bend_coords(g, X, Y):
    """中心線の距離 s と、中心線からの距離 dn(流れの向きの左が正)"""
    s = np.zeros_like(X)
    dn = np.zeros_like(X)
    a1 = X <= g["xa"]                                   # 東向きの直線
    s[a1] = X[a1]
    dn[a1] = Y[a1] - g["ya"]
    a3 = (Y <= g["yc"]) & ~a1                           # 南向きの直線
    xo = g["xc"] + g["r"]
    s[a3] = g["l1"] + g["larc"] + (g["yc"] - Y[a3])
    dn[a3] = X[a3] - xo
    a2 = ~a1 & ~a3                                      # 円弧(中心 (xc, yc)、時計回り)
    rr = np.hypot(X[a2] - g["xc"], Y[a2] - g["yc"])
    ph = np.arctan2(X[a2] - g["xc"], Y[a2] - g["yc"])   # 北から時計回りの角
    s[a2] = g["l1"] + g["r"] * ph
    dn[a2] = rr - g["r"]
    return s, dn


def bend(r, b, rep, dx):
    g = bend_geom(r)
    nx, ny = int(round(g["lx"] / dx)), int(round(g["ly"] / dx))
    X = (np.arange(1, nx + 1)[None, :] - 0.5) * dx + np.zeros((ny, 1))
    Y = g["ly"] - (np.arange(1, ny + 1)[:, None] - 0.5) * dx + np.zeros((1, nx))
    s, dn = bend_coords(g, X, Y)
    width = np.zeros((ny, nx))
    width[np.abs(dn) < b / 2] = RESOLVED                # 中心が帯に入るセル
    if rep in ("k1", "k2"):
        kk = 1 if rep == "k1" else 2
        # 中心線が格子の線を横切る所で、線の両側のセルのうち横切る点に最も近い kk 組を解像セルにする。向きが x 寄りの
        # 区間は縦の線(x = iΔ)、y 寄りの区間は横の線(y = jΔ)を見る
        ts = np.linspace(0.0, g["ltot"], int(g["ltot"] / 2.0) + 1)
        pts = [centerline_point(g, t) for t in ts]
        done = set()
        for (x1, y1, tx1, ty1), (x2, y2, _, _) in zip(pts[:-1], pts[1:]):
            if abs(tx1) >= abs(ty1):                    # x 寄り: 縦の線
                i1, i2 = math.floor(x1 / dx), math.floor(x2 / dx)
                if i1 != i2 and 1 <= max(i1, i2) <= nx - 1:
                    xb = max(i1, i2) * dx
                    yb = y1 + (y2 - y1) * (xb - x1) / (x2 - x1)
                    key = ("v", max(i1, i2))
                    if key in done:
                        continue
                    done.add(key)
                    yj = g["ly"] - (np.arange(ny) + 0.5) * dx
                    for j in np.argsort(np.round(np.abs(yj - yb), 6), kind="stable")[:kk]:
                        width[j, max(i1, i2) - 1] = width[j, max(i1, i2)] = RESOLVED
            else:                                       # y 寄り: 横の線
                j1, j2 = math.floor((g["ly"] - y1) / dx), math.floor((g["ly"] - y2) / dx)
                if j1 != j2 and 1 <= max(j1, j2) <= ny - 1:
                    jb = max(j1, j2)                    # 線 y = ly − jb Δ(行 jb−1 と jb の間)
                    ybl = g["ly"] - jb * dx
                    xb = x1 + (x2 - x1) * (ybl - y1) / (y2 - y1)
                    key = ("h", jb)
                    if key in done:
                        continue
                    done.add(key)
                    xi = (np.arange(nx) + 0.5) * dx
                    for i in np.argsort(np.round(np.abs(xi - xb), 6), kind="stable")[:kk]:
                        width[jb - 1, i] = width[jb, i] = RESOLVED
    chan = width > 0
    z = np.where(chan, Z0 - S * s, -9999.0)
    return dict(width=width, z=z, s=s, dn=dn, nx=nx, ny=ny, g=g)


def centerline_point(g, t):
    """中心線の距離 t の点と向き(単位ベクトル)"""
    if t <= g["l1"]:
        return t, g["ya"], 1.0, 0.0
    if t <= g["l1"] + g["larc"]:
        ph = (t - g["l1"]) / g["r"]
        return g["xc"] + g["r"] * math.sin(ph), g["yc"] + g["r"] * math.cos(ph), math.cos(ph), -math.sin(ph)
    return g["xc"] + g["r"], g["yc"] - (t - g["l1"] - g["larc"]), 0.0, -1.0


# ------------------------------------------------------------------ 河道の脇の薄い水膜・仮想壁面の向こうの湛水
WET_AN, WET_B = "a27", 200.0
BANK_H, BANK_W, RAIN = 4.0, 300.0, 20.0                 # 河岸の高さ (m)・帯の幅 (m)・雨 (mm/h)


def wet(var):
    """26.6° の直線の河道(川幅 2 セル、段を 2 行太らせた解像の帯)の両側に河岸を置く。dry・rain は河岸を地形で表す
    (河床 + 4 m、河道へ向かって 2 % の横断勾配。rain は全域に 20 mm/h の雨)。wall_* は河岸の代わりに仮想壁面
    (天端 = 河床 + 10 m)を立て、壁の向こうを水平な地盤(区間の中ほどの河床 + 1 m)にする(wall_rain は全域に
    20 mm/h の雨、wall_pond は水深 1.5 m の静かな池)"""
    g = straight(WET_AN, WET_B, "k2", DX)
    width, dn, s = g["width"], g["dn"], g["s"]
    chan = width > 0
    # 河岸の帯: 河道の帯の縁(中心線から最も遠い河道セルの |dn|)から 300 m
    edge = float(np.abs(dn[chan]).max())
    bank = ~chan & (np.abs(dn) <= edge + BANK_W)
    zb = Z0 - S * s
    z = np.where(chan, zb, -9999.0)
    h0 = np.where(chan, hn(QB), 0.0)
    if var in ("dry", "rain"):
        z = np.where(bank, zb + BANK_H + 0.02 * np.maximum(np.abs(dn) - edge, 0.0), z)
    else:
        z = np.where(bank, Z0 - S * L / 2 + 1.0, z)
        if var == "wall_pond":
            h0 = np.where(bank, 1.5, h0)
    g.update(z=z, h0=h0, bank=bank, chan=chan)
    return g


# ------------------------------------------------------------------ 設定ファイル
PARAM = """!======================================================================
! examples/coarse_channel: {title}
!   make_cases.py が生成する(入力は runs/data_{name}/)
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
{extra_sys}  dir_data = 'data_{name}'
  dir_result = 'result_{name}'
  f_out_h = 1
  f_out_e = 1
/

&list_initial
  f_htype = 1
  fn_hinit = 'h0.txt'
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
{channel}{rain}
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
{bank}  fn_width = 'width.txt'
/
"""
RAIN_BLOCK = """
&list_precip
  prtype = 1                ! 一様な雨の時系列(時刻 min, 強度 mm/h)
  prval(1:2,1) = 0, {rain}
  prval(1:2,2) = 1440, {rain}
/
"""


def write_case(name, kind, kw):
    dd = os.path.join(RUNS, f"data_{name}")
    os.makedirs(dd, exist_ok=True)
    fine = kw.get("rep") == "fine"
    dx = kw.get("dx", DX)
    rain = 0.0
    walls = True
    if kind == "straight":
        g = straight(kw["an"], kw["b"], kw["rep"], dx)
        mask = g["width"] > 0
        h0 = np.where(mask, hn(QB), 0.0)
        q_in = QB * kw["b"]
        title = f"直線 {ANGLE_DEG[kw['an']]:.1f}°・川幅 {kw['b']:.0f} m・{kw['rep']}"
    elif kind == "bend":
        g = bend(kw["r"], kw["b"], kw["rep"], dx)
        mask = g["width"] > 0
        h0 = np.where(mask, hn(QB), 0.0)
        q_in = QB * kw["b"]
        title = f"屈曲 半径 {kw['r']:.0f} m・川幅 {kw['b']:.0f} m・{kw['rep']}"
    else:
        var = kw["var"]
        g = wet(var)
        mask = g["chan"] | g["bank"]
        h0 = g["h0"]
        q_in = QB * WET_B
        rain = RAIN if var in ("rain", "wall_rain") else 0.0
        walls = var.startswith("wall")
        title = f"河道の脇の水: {var}"
    width, z, nx, ny = g["width"], g["z"], g["nx"], g["ny"]
    chan = width > 0
    use_chan = (not fine) and (kind != "wet" or walls)
    arrays = [("z", z, "%.3f"), ("rn", np.full(z.shape, RN), "%.3f"), ("mask", mask.astype(int), "%d"),
              ("h0", h0, "%.3f")]
    if use_chan:
        bank = np.where(chan, z + 10.0, -9999.0)
        arrays += [("rw", chan.astype(int), "%d"), ("width", width, "%.2f"), ("bank", bank, "%.3f")]
    for fn, a, fmt in arrays:
        np.savetxt(os.path.join(dd, f"{fn}.txt"), a, fmt=fmt)
    # 流入は解像セルから(なければ河道の全セル)。流出は東端(屈曲は南端)の河道セル
    res = width >= RESOLVED
    if kind == "bend":
        src = res[:, 0] if res[:, 0].any() else chan[:, 0]
        cells_in = [(1, j + 1) for j in range(ny) if src[j]]
        cells_out = [(i + 1, ny) for i in range(nx) if chan[ny - 1, i]]
        s_out = float(np.mean([g["s"][ny - 1, i - 1] for i, _ in cells_out]))
    else:
        src = res[:, 0] if res[:, 0].any() else chan[:, 0]
        cells_in = [(1, j + 1) for j in range(ny) if src[j]]
        cells_out = [(nx, j + 1) for j in range(ny) if chan[j, nx - 1]]
        s_out = (g["lx"] - 0.5 * dx) / g["ct"]
    with open(os.path.join(dd, "cells_in.txt"), "w") as f:
        f.writelines(f"{i} {j}\n" for i, j in cells_in)
    with open(os.path.join(dd, "cells_out.txt"), "w") as f:
        f.writelines(f"{i} {j}\n" for i, j in cells_out)
    eta = Z0 - S * s_out + hn(QB)
    with open(os.path.join(dd, "stage.txt"), "w") as f:
        f.write(f"0 {eta:.4f}\n1440 {eta:.4f}\n")
    with open(os.path.join(dd, "q.txt"), "w") as f:
        f.write(f"0 {q_in:.1f}\n1440 {q_in:.1f}\n")
    bank_lines = "  fn_bank = 'bank.txt'\n  f_bank_datum = 2\n"
    with open(os.path.join(RUNS, f"param_{name}.txt"), "w", encoding="utf-8") as f:
        f.write(PARAM.format(title=title, name=name, dt="1.0" if fine else "2.0", tt="4h" if fine else "8h",
                             extra_sys=("  fn_channel = '-'\n" if use_chan else "") + ("  fn_precip = '-'\n" if rain > 0 else ""), nx=nx, ny=ny, dx=f"{dx:.1f}",
                             rw="  fn_rw = 'rw.txt'\n" if use_chan else "",
                             channel=CHANNEL.format(bank=bank_lines) if use_chan else "",
                             rain=RAIN_BLOCK.format(rain=rain) if rain > 0 else ""))


def gen(series_list):
    os.makedirs(RUNS, exist_ok=True)
    for se in series_list:
        cs = cases(se)
        for name, kind, kw in cs:
            write_case(name, kind, kw)
        with open(os.path.join(RUNS, f"cases_{se}.txt"), "w") as f:
            f.write("\n".join(c[0] for c in cs) + "\n")
        print(f"{se}: {len(cs)} ケース")


if __name__ == "__main__":
    if sys.argv[1] == "gen":
        gen(sys.argv[2:] or list(SERIES))
    elif sys.argv[1] == "list":
        print("\n".join(c[0] for c in cases(sys.argv[2])))
