#!/usr/bin/env python3
"""wfswash: 遡上域(swash)の輸送(fn_geomorph の f_wfswash。developer.md §90.21)の検定

Python 標準ライブラリのみ。使い方:
  python3 Check_wfswash.py rate  result_rate save_rate   # 1 回の地形更新の量(式・汀線の面)
  python3 Check_wfswash.py diag  result_diag save_diag   # 45° の汀線(汀線の向きによらないこと)
  python3 Check_wfswash.py eq    save_eq                 # 平衡勾配の前浜は変わらない
  python3 Check_wfswash.py mild  save_mild               # 平衡より緩い前浜の積み上げ
  python3 Check_wfswash.py steep save_steep              # 平衡より急な前浜の沖向きの輸送
  python3 Check_wfswash.py obl   result_obl save_obl     # 斜め入射の沿岸の輸送の総量
  python3 Check_wfswash.py cliff result_cliff save_cliff # 遡上の届かない崖の前(遡上域なし)は動かない
  python3 Check_wfswash.py flow  result_flow save_flow   # 連成(閉じた海盆の土砂の保存など)

地形は save の state.dat(倍精度)、初期の地形は z_*.txt(make_z.py。z は 2 進で厳密な値か、
モデルと同じ 10 進の文字列)、波高・平均波向は初期の出力(0000。単精度)で読む。

独立に組み立てる参照(モデルと同じ式。§90.21):
  - 遡上高 R = 1.1 S/2、S = √(H0 L0 (0.563 β² + 0.004))(Stockdon ら 2006 式 (19) の振れ幅)、
    H0 = E H_inc、L0 = gT²/2π、β = 汀線セルの中央差分の勾配の大きさ(0.9 tanφ_m で頭打ち)
  - 露出度 E = 汀線セルの ±2 セルの波浪セルの max(H/min(H_inc, √2 γmax h))(1 で頭打ち)
  - 岸沖 q_c = K_c 2√(2g) R^{3/2} (1 − z/R)² tanφ_m/(tan²φ_m − tan²β)(tanβ − tanβ_e)
    (Larson ら 2004 式 (8)。正 = 沖向き。かさ)。tanβ は面の両側のセルの勾配の平均の大きさ、
    z = 乾いたセルの地盤の静水面からの高さ。面の流束 = −q_c (n̂·ê) × セルの辺の長さ
  - 沿岸 Q_l = K_l f (u_s² v_s/g) ∫(1 − z/R)^{3/2} dx(Larson & Wamsley 2007 式 (4) を遡上域の幅
    R/tanβ(Δ で頭打ち)で積分)、u_s = √(2gR)、v_s = u_s tanθ(θ = 汀線の法線と平均波向の角)。
    遡上域がある(4 近傍の地盤の高い乾いたセルのどれかが z − η < R)汀線セルだけ
"""
import math
import struct
import sys

G = 9.8                 # 重力加速度(既定 p%gg)
KC = 1.6e-3             # wfswash_kc の既定(Larson ら 2004)
KL = KC                 # wfswash_kl の既定(= K_c。Larson & Wamsley 2007)
TBE = 0.1               # wfswash_tanbe(各 param)
TPHI = math.tan(math.radians(30.0))   # wfswash_phim の既定 30°
HINC = 1.0              # wf_hm0
TP = 8.0                # wf_trep
L0 = G * TP * TP / (2.0 * math.pi)
HSR = math.sqrt(2.0) * 0.6            # 不規則波の飽和 √2 γmax(wf_gammax の既定 0.6)
PORO = 0.4              # fluv_porosity
DX = DY = 5.0
DD = 0.001              # 限界水深 dd の既定
MORFAC = 5.0            # param_flow の morfac
NX = 60

failed = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failed.append(msg)


def read_bil(d, name, ny, k="0000", nx=NX):
    with open("%s/%s%s.bil" % (d, name, k), "rb") as f:
        data = f.read()
    v = struct.unpack("<%df" % (nx * ny), data)
    return [list(v[j * nx:(j + 1) * nx]) for j in range(ny)]


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(raw) // 8), raw)
    out = [0.0] * n
    i = k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def read_state(savedir, ny, nx=NX):
    """state.dat(h, z, hrs, hg, sd, hs の順。m_state の保存)を 2 次元の表で返す"""
    with open(savedir + "/state.dat", "rb") as f:
        a = [read_rle(f, nx * ny) for _ in range(6)]
    return {k: [v[j * nx:(j + 1) * nx] for j in range(ny)]
            for k, v in zip(["h", "z", "hrs", "hg", "sd", "hs"], a)}


def read_z(name):
    with open(name) as f:
        return [[float(v) for v in line.split()] for line in f if line.strip()]


def runup(e, tb, hinc=HINC):
    tf = min(tb, 0.9 * TPHI)
    return 0.55 * math.sqrt(e * hinc * L0 * (0.563 * tf * tf + 0.004))


def fac(tb):
    tf = min(tb, 0.9 * TPHI)
    return TPHI / (TPHI * TPHI - tf * tf)


def qcross(r, zr, tb):
    """岸沖の正味の輸送(かさ m2/s。正 = 沖向き)"""
    return KC * 2.0 * math.sqrt(2.0 * G) * r ** 1.5 * (1.0 - zr / r) ** 2 * fac(tb) * (tb - TBE)


def grad(z, i, j):
    """中央差分の勾配(モデルの swash_zgrad と同じ。端は片側差分。y は行の増える向き = 南が正)"""
    ny, nx = len(z), len(z[0])
    oke, okw, oks, okn = i < nx - 1, i > 0, j < ny - 1, j > 0
    if oke and okw:
        gx = (z[j][i + 1] - z[j][i - 1]) / (2.0 * DX)
    elif oke:
        gx = (z[j][i + 1] - z[j][i]) / DX
    elif okw:
        gx = (z[j][i] - z[j][i - 1]) / DX
    else:
        gx = 0.0
    if oks and okn:
        gy = (z[j + 1][i] - z[j - 1][i]) / (2.0 * DY)
    elif oks:
        gy = (z[j + 1][i] - z[j][i]) / DY
    elif okn:
        gy = (z[j][i] - z[j - 1][i]) / DY
    else:
        gy = 0.0
    return gx, gy


def exposure(wh, h, i, j):
    ny, nx = len(wh), len(wh[0])
    e = 0.0
    for b in range(-2, 3):
        for a in range(-2, 3):
            ii, jj = i + a, j + b
            if 0 <= ii < nx and 0 <= jj < ny and wh[jj][ii] > 0.0:
                hs = min(HINC, HSR * h[jj][ii])
                if hs > 0.0:
                    e = max(e, wh[jj][ii] / hs)
    return min(e, 1.0)


CARD = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def predict_cross(z0, h0, wh, wh_h, dts):
    """1 回の更新の岸沖の流束による各セルの Δz(かさ)。モデルの汀線の 4 近傍の面の規則"""
    ny, nx = len(z0), len(z0[0])
    dz = [[0.0] * nx for _ in range(ny)]
    for j in range(ny):
        for i in range(nx):
            if h0[j][i] <= DD:
                continue
            for di, dj in CARD:
                ii, jj = i + di, j + dj
                if not (0 <= ii < nx and 0 <= jj < ny):
                    continue
                if h0[jj][ii] > DD or z0[jj][ii] <= z0[j][i]:
                    continue
                gw = grad(z0, i, j)
                tbw = math.hypot(*gw)
                r = runup(exposure(wh, wh_h, i, j), tbw)
                zr = max(z0[jj][ii] - (z0[j][i] + h0[j][i]), 0.0)
                if r <= 0.0 or zr >= r:
                    continue
                gd = grad(z0, ii, jj)
                gx, gy = 0.5 * (gw[0] + gd[0]), 0.5 * (gw[1] + gd[1])
                tb = math.hypot(gx, gy)
                pr = (gx * di + gy * dj) / tb
                if pr <= 0.0:
                    continue
                ls = DY if di != 0 else DX
                v = -qcross(r, zr, tb) * pr * ls * dts / (DX * DY)    # 乾いたセルの増分(かさ)
                dz[jj][ii] += v
                dz[j][i] -= v
    return dz


def check_rate(d, sd):
    print("== rate (%s, %s): one bed update on a beach milder than equilibrium" % (d, sd))
    ny = 8
    z0 = read_z("z_mild.txt")
    h0 = [[max(-v, 0.0) for v in row] for row in z0]
    st = read_state(sd, ny)
    wh = read_bil(d, "Wh", ny)
    hh = read_bil(d, "H", ny)
    dzp = predict_cross(z0, h0, wh, hh, 5.0)
    w, dc = 44, 45
    gw = grad(z0, w, 3)
    r = runup(exposure(wh, hh, w, 3), math.hypot(*gw))
    zr = z0[3][dc]
    q = qcross(r, zr, 0.025)
    print("  R = %.6f m, z = %.4f m, q_c = %.6e m2/s (onshore), predicted dz = %.6e m" % (r, zr, q, dzp[3][dc]))
    check(abs(dzp[3][dc] - (-q * 5.0 / DX)) < 1e-15, "rate: the prediction equals -q_c dt/dx on a straight shoreline")
    emax = 0.0
    other = 0.0
    for j in range(ny):
        for i in range(NX):
            dzm = st["z"][j][i] - z0[j][i]
            if dzp[j][i] != 0.0:
                emax = max(emax, abs(dzm - dzp[j][i]) / abs(dzp[j][i]))
            else:
                other = max(other, abs(dzm))
    check(dzp[3][dc] > 0.0 and dzp[3][w] < 0.0, "rate: onshore (the dry cell gains, the wet cell loses)")
    check(emax < 1e-6, "rate: the bed change of the shoreline cells matches Larson et al. (2004) (rel. error %.1e < 1e-6)" % emax)
    check(other == 0.0, "rate: the other cells do not change (max |dz| = %.1e)" % other)


def check_diag(d, sd):
    print("== diag (%s, %s): one bed update on a 45-degree shoreline" % (d, sd))
    ny = 60
    z0 = read_z("z_diag.txt")
    h0 = [[max(-v, 0.0) for v in row] for row in z0]
    st = read_state(sd, ny)
    wh = read_bil(d, "Wh", ny)
    hh = read_bil(d, "H", ny)
    dzp = predict_cross(z0, h0, wh, hh, 5.0)
    emax = 0.0
    other = 0.0
    for j in range(ny):
        for i in range(NX):
            dzm = st["z"][j][i] - z0[j][i]
            if dzp[j][i] != 0.0:
                emax = max(emax, abs(dzm - dzp[j][i]) / abs(dzp[j][i]))
            else:
                other = max(other, abs(dzm))
    check(emax < 1e-6, "diag: the bed change of every shoreline cell matches the face rule (rel. error %.1e < 1e-6)" % emax)
    # 他のセルは変わらない(領域の角の吸収境界の近くでは平均波向が 315° から丸めの規模でずれ、
    # ごく小さな沿岸の流束が出るので 1e-9 m まで許す)
    check(other < 1e-9, "diag: the other cells do not change (max |dz| = %.1e < 1e-9)" % other)
    # 中央の窓(線 i + j = 65 の乾いたセル、10 <= i <= 49)の単位長さあたりの総量 = q_c Δt(向きによらない)
    vol = 0.0
    k = 0
    for i in range(10, 50):
        j = 65 - i
        vol += (st["z"][j][i] - z0[j][i]) * DX * DY
        k += 1
    per = vol / (k * math.sqrt(2.0) * DX)
    tb = 1.0 / 40.0
    zr = z0[65 - 30][30]
    q = qcross(runup(1.0, tb), zr, tb)
    print("  per unit length: %.6e m2 (model), %.6e m2 (-q_c dt, z = %.4f m)" % (per, -q * 5.0, zr))
    check(abs(per / (-q * 5.0) - 1.0) < 1e-6,
          "diag: the transport per unit length of the 45-degree shoreline is q_c dt, as on an axis-aligned one (%.2e)"
          % (per / (-q * 5.0) - 1.0))


def changes(sd, zfile, ny):
    st = read_state(sd, ny)
    z0 = read_z(zfile)
    dz = [[st["z"][j][i] - z0[j][i] for i in range(NX)] for j in range(ny)]
    return st, z0, dz


def face_slope(z, j, w):
    a = grad(z, w, j)
    b = grad(z, w + 1, j)
    return math.hypot(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))


def check_eq(sd):
    print("== eq (%s): a foreshore at the equilibrium slope does not change" % sd)
    _, _, dz = changes(sd, "z_eq.txt", 8)
    m = max(abs(v) for row in dz for v in row)
    check(m < 1e-12, "eq: the bed does not change (max |dz| = %.1e < 1e-12)" % m)


def check_profile(sd, zfile, tag, onshore):
    ny = 8
    st, z0, dz = changes(sd, zfile, ny)
    w, d = 44, 45
    tot = sum(sum(row) for row in dz) * DX * DY
    moved = sum(abs(v) for row in dz for v in row) * DX * DY / 2.0
    print("  %s: moved %.4f m3 (bulk), dz(wet) = %.4f m, dz(dry) = %.4f m" % (tag, moved, dz[3][w], dz[3][d]))
    check(moved > 1.0, "%s: the swash moves sediment (%.3f m3)" % (tag, moved))
    check(abs(tot) < 1e-9 * max(moved, 1.0), "%s: sediment conserved (sum dz dA = %.1e m3)" % (tag, tot))
    # 地形の更新が汀線で作る小さな長波の流れが行の間にごく小さな差を生む(丸めの規模の非対称)。
    # 汀線の法線がわずかに傾くと沿岸の流束が出て、沖隣のセルもごく小さく動く。1e-9 m まで許す
    other = max(abs(dz[j][i]) for j in range(ny) for i in range(NX) if i not in (w, d))
    check(other < 1e-9, "%s: only the shoreline cells change (others max |dz| = %.1e < 1e-9)" % (tag, other))
    spread = max(abs(dz[j][i] - dz[3][i]) for j in range(ny) for i in (w, d))
    check(spread < 1e-9, "%s: uniform alongshore (row difference %.1e < 1e-9)" % (tag, spread))
    if onshore:
        check(dz[3][d] > 0.0 and dz[3][w] < 0.0, "%s: onshore (the dry cell gains, the wet cell loses)" % tag)
    else:
        check(dz[3][d] < 0.0 and dz[3][w] > 0.0, "%s: offshore (the dry cell loses, the wet cell gains)" % tag)
    s0 = face_slope(z0, 3, w)
    s1 = face_slope(st["z"], 3, w)
    print("  %s: shoreline face slope %.4f -> %.4f (equilibrium %.2f)" % (tag, s0, s1, TBE))
    if onshore:
        check(s0 < s1 <= TBE + 1e-9, "%s: the foreshore steepens toward the equilibrium slope without passing it" % tag)
    else:
        check(TBE - 1e-9 <= s1 < s0, "%s: the foreshore flattens toward the equilibrium slope without passing it" % tag)
    return st, z0, dz


def check_mild(sd):
    print("== mild (%s): a foreshore milder than equilibrium builds up" % sd)
    st, z0, dz = check_profile(sd, "z_mild.txt", "mild", True)
    w, d = 44, 45
    eta = st["z"][3][w] + st["h"][3][w]
    r = runup(1.0, math.hypot(*grad(st["z"], w, 3)))
    top = st["z"][3][d]
    print("  mild: berm top %.4f m, runup limit eta + R = %.4f + %.4f m" % (top, eta, r))
    check(top <= max(eta, 0.0) + r, "mild: the deposit stays below the runup limit eta + R")
    check(top > z0[3][d + 1], "mild: a berm forms above the next dry cell (%.4f > %.4f)" % (top, z0[3][d + 1]))


def check_steep(sd):
    print("== steep (%s): a foreshore steeper than equilibrium is cut back" % sd)
    check_profile(sd, "z_steep.txt", "steep", False)


def longshore(z0, wh, hh, wa, w, j):
    """汀線セル (w, j) の遡上域の沿岸輸送の総量 Q_l(かさ m3/s。t̂ = (0, 1) = 南向きが正)と E・R・入射角"""
    e = exposure(wh, hh, w, j)
    gx, gy = grad(z0, w, j)
    tb = math.hypot(gx, gy)
    nx, ny_ = gx / tb, gy / tb
    tx, ty = -ny_, nx
    sx = sy = 0.0
    for b in range(-2, 3):
        for a in range(-2, 3):
            ii, jj = w + a, j + b
            if wh[jj][ii] > 0.0:
                th = math.radians(wa[jj][ii])
                sx += wh[jj][ii] ** 2 * math.cos(th)
                sy -= wh[jj][ii] ** 2 * math.sin(th)       # 格子の y は南が正
    sn = math.hypot(sx, sy)
    cosa = (sx * nx + sy * ny_) / sn
    sina = (sx * tx + sy * ty) / sn
    r = runup(e, tb)
    us = math.sqrt(2.0 * G * r)
    vs = us * sina / cosa
    ws = r / tb
    aint = 0.4 * ws if ws <= DX else 0.4 * ws * (1.0 - (1.0 - DX / ws) ** 2.5)
    ql = KL * fac(tb) * us * us * vs / G * aint            # かさ (m3/s)。t̂ = (0, 1) = 南向きが正
    theta = math.degrees(math.atan2(sina, cosa))
    return e, r, theta, ql


def check_obl(d, sd):
    print("== obl (%s, %s): longshore swash transport under oblique waves" % (d, sd))
    ny = 16
    st, z0, dz = changes(sd, "z_eq16.txt", ny)
    wh = read_bil(d, "Wh", ny)
    hh = read_bil(d, "H", ny)
    wa = read_bil(d, "Wa", ny)
    e, r, theta, ql = longshore(z0, wh, hh, wa, 44, 7)
    vnorth = sum(dz[jj][i] for jj in range(8) for i in range(NX)) * DX * DY
    vsouth = sum(dz[jj][i] for jj in range(8, ny) for i in range(NX)) * DX * DY
    t = 600.0
    print("  E = %.6f, R = %.5f m, angle at the shoreline %.3f deg, Q_l = %.6e m3/s (north = %s)"
          % (e, r, theta, ql, ql < 0.0))
    print("  north half gained %.6f m3, -Q_l T = %.6f m3" % (vnorth, -ql * t))
    check(ql < 0.0 and vnorth > 0.0, "obl: the swash transport goes north with the waves (north half gains)")
    check(abs(vnorth / (-ql * t) - 1.0) < 1e-4,
          "obl: the volume moved alongshore is Q_l T (Larson & Wamsley 2007; rel. error %.1e < 1e-4)"
          % abs(vnorth / (-ql * t) - 1.0))
    check(abs(vnorth + vsouth) < 1e-9, "obl: sediment conserved (north + south = %.1e m3)" % (vnorth + vsouth))
    # 端の行の変化(北端に積もり南端が削れる)で勾配と遡上高が変わり、沿岸の流束の発散がゆっくり
    # 内側へ広がる。中央の行(6..9)は実質的に変わらない(端の変化 ~0.05 m に対して 1e-5 m 未満)
    mid = max(abs(dz[jj][i]) for jj in range(6, 10) for i in range(NX))
    check(mid < 1e-5, "obl: the middle rows stay practically unchanged (max |dz| = %.1e < 1e-5 m)" % mid)


def check_cliff(d, sd):
    print("== cliff (%s, %s): no swash zone in front of a cliff above the runup limit" % (d, sd))
    ny = 16
    st, z0, dz = changes(sd, "z_cliff16.txt", ny)
    wh = read_bil(d, "Wh", ny)
    hh = read_bil(d, "H", ny)
    wa = read_bil(d, "Wa", ny)
    w, j = 44, 7
    e, r, theta, ql = longshore(z0, wh, hh, wa, w, j)
    zr = z0[j][w + 1] - (z0[j][w] + hh[j][w])          # 崖の上端の汀線セルの水位からの高さ
    print("  E = %.6f, R = %.5f m, cliff top above the water level %.4f m; without the swash-zone condition"
          " Q_l = %.3e m3/s would act (%.2f m3 in 600 s)" % (e, r, zr, ql, abs(ql) * 600.0))
    check(zr > r, "cliff: the cliff top is above the runup limit (z - eta = %.3f m > R = %.3f m)" % (zr, r))
    check(abs(ql) * 600.0 > 1.0, "cliff: the waves are oblique enough that the formula alone would move sand")
    dmax = max(abs(dz[jj][i]) for jj in range(ny) for i in range(NX))
    check(dmax < 1e-12, "cliff: nothing moves (no swash zone; max |dz| = %.1e < 1e-12)" % dmax)


def check_flow(d, sd):
    print("== flow (%s, %s): coupled closed basin (waves on the flow, bed load, suspension, swash)" % (d, sd))
    ny = 8
    st, z0, dz = changes(sd, "z_mild.txt", ny)
    vals = [v for k in ("h", "z", "hs") for row in st[k] for v in row]
    check(all(math.isfinite(v) for v in vals), "flow: all values are finite")
    # 浮遊砂の交換は水柱側が水理時間、河床側が × morfac の台帳分離(MORFAC 方式。§90 の f_wfsed と
    # geomorph_plan.md §4)なので、保存されるのは morfac Σ hs + (1 − λ) Σ dz
    hs = sum(sum(row) for row in st["hs"])
    tot = MORFAC * hs + (1.0 - PORO) * sum(sum(row) for row in dz)
    moved = sum(abs(v) for row in dz for v in row)
    print("  flow: sum hs = %.6e, sum |dz| = %.4f, residual %.2e" % (hs, moved, tot))
    check(moved > 1e-2, "flow: the bed changes")
    check(abs(tot) < 1e-10 * moved, "flow: sediment conserved (morfac sum hs + (1 - lambda) sum dz = %.1e)" % tot)
    # 乾いた前浜の堆積(遡上域の輸送だけが乾いたセルへ積もらせる)が遡上の上限を越えない
    nd = 0
    worst = -1e9
    for j in range(ny):
        for i in range(NX):
            if st["h"][j][i] > DD or dz[j][i] <= 1e-9:
                continue
            lim = -1e9
            for di, dj in CARD:
                ii, jj = i + di, j + dj
                if 0 <= ii < NX and 0 <= jj < ny and st["h"][jj][ii] > DD and st["z"][jj][ii] < st["z"][j][i]:
                    eta = st["z"][jj][ii] + st["h"][jj][ii]
                    lim = max(lim, eta + runup(1.0, math.hypot(*grad(st["z"], ii, jj)), 1.2))
            nd += 1
            worst = max(worst, st["z"][j][i] - lim)
    print("  flow: %d dry cells gained sediment, max (z - (eta + R)) = %.4f m" % (nd, worst))
    check(nd > 0, "flow: the swash builds the dry foreshore")
    check(worst <= 0.0, "flow: the dry deposits stay below the runup limit (H_inc <= 1.2 m)")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    mode = sys.argv[1]
    if mode == "rate":
        check_rate(sys.argv[2], sys.argv[3])
    elif mode == "diag":
        check_diag(sys.argv[2], sys.argv[3])
    elif mode == "eq":
        check_eq(sys.argv[2])
    elif mode == "mild":
        check_mild(sys.argv[2])
    elif mode == "steep":
        check_steep(sys.argv[2])
    elif mode == "obl":
        check_obl(sys.argv[2], sys.argv[3])
    elif mode == "cliff":
        check_cliff(sys.argv[2], sys.argv[3])
    elif mode == "flow":
        check_flow(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(2)
    if failed:
        print("=== Check_wfswash.py %s: FAIL (%d) ===" % (mode, len(failed)))
        sys.exit(1)
    print("=== Check_wfswash.py %s: PASS ===" % mode)


if __name__ == "__main__":
    main()
