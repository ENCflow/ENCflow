#!/usr/bin/env python3
# curvature(曲率項 f_dbcurv)検定
#   使い方: Check_curvature.py <save_off> <save_on>
#
#   定常 1 次元の常微分方程式(水平座標系。q_m = u・h_t 一定)
#     (ge − u²/h_t) dh_t/dx = ge(−z' − μF) − ge u²/(ξ h_t)
#     ge = g/(1+z'²)(= g cos²θ。f_gravity_correction の Ni 補正)
#     F  = 1 + a_c/√(g・ge)(曲率項。off では F=1)
#     a_c = u² z''/√(1+z'²)(コード curv_prepare と同じ定義)
#   を上流の等流深から下流へ積分した h_ode(x) を基準にする。
#   (1) 等流(A) : 窓 WA の <h_t> が Voellmy 等流深 h_nA に相対 TOL_N 以内(両構成)
#   (2) 等流(B) : 窓 WB(円弧の十分下流)の <h_t> が h_nB に相対 TOL_N 以内(両構成)。
#                 曲率項は直線部では消えるため on/off の差 < TOL_SAME
#   (3) 円弧上  : 窓 WC(円弧の接点 A+5m 〜 接点 B)の <h_t> が h_ode の窓平均に
#                 相対 TOL_C 以内(両構成)
#   (4) 効果    : 窓 WC の厚化 <h_t>(on) − <h_t>(off) が ODE の差の [RATIO_LO, RATIO_HI] 倍
#   <h_t> は全行平均。Voellmy 則の等流は横断方向に一様にならない(壁際の行が
#   薄く速い。Manning 則では出ない。§28.10 の観察)ため、行平均で 1 次元解と
#   比べる(test/volcano と同じ扱い)。円弧下端より下流では行間の流量再配分が
#   進むため、窓 WC は曲率項が働く円弧上に置く
import sys, struct, math, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_init as mi

G, MU, XI = 9.81, 0.2, 500.0          # param_*.txt と対
QIN, CSIN = 16.0, 0.8
QM = QIN * (1.0 + CSIN) / (mi.NY * mi.DX)   # 単位幅の混合体流量 (m²/s)
WA = (30.0, 55.0)
WB = (150.0, 210.0)
WC = (mi.XA + 5.0, mi.XB)
TOL_N, TOL_SAME, TOL_C = 0.05, 0.01, 0.10
RATIO_LO, RATIO_HI = 0.7, 1.4
J1, J2 = 1, mi.NY                      # 行平均に使う行(1 起点、両端含む。全行)


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
    hdr = read_rec(f)
    n, nrun = struct.unpack("<2q", hdr)
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    packed_raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(packed_raw) // 8), packed_raw)
    out = [0.0] * n
    i = 0
    k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def load_ht(savedir):
    """行 J1..J2 で平均した混合流動深 h_t(i) を返す(i = 0..nx-1)"""
    nx, ny = mi.NX, mi.NY
    ntot = nx * ny
    with open(savedir + "/state.dat", "rb") as f:
        h = read_rle_array(f, ntot)
        for _ in range(4):
            read_rle_array(f, ntot)     # z, hrs, hg, sd
        hs = read_rle_array(f, ntot)
    ht = []
    for i in range(nx):
        ht.append(sum(h[(j - 1) * nx + i] + hs[(j - 1) * nx + i]
                      for j in range(J1, J2 + 1)) / (J2 - J1 + 1))
    return ht


def zderiv(x):
    """z'(x), z''(x)(make_init.z_of の解析微分)"""
    if x <= mi.XA:
        return -mi.ST1, 0.0
    if x < mi.XB:
        d = x - mi.CX
        q = math.sqrt(mi.R ** 2 - d * d)
        return d / q, mi.R ** 2 / q ** 3
    return -mi.ST2, 0.0


def hnorm(st):
    return (QM * QM / (XI * (st - MU))) ** (1.0 / 3.0)


def ode_profile(curv, x0, h0, x1, dx=0.01):
    """定常 ODE を x0(h=h0)から x1 へ積分。(x, h) の列を返す"""
    def dhdx(x, h):
        zp, zpp = zderiv(x)
        ge = G / (1.0 + zp * zp)
        u = QM / h
        fcur = 1.0
        if curv:
            ac = u * u * zpp / math.sqrt(1.0 + zp * zp)
            fcur = max(0.0, 1.0 + ac / math.sqrt(G * ge))
        rhs = ge * (-zp - MU * fcur) - ge * u * u / (XI * h)
        return rhs / (ge - u * u / h)
    xs, hs = [x0], [h0]
    x, h = x0, h0
    n = int(round((x1 - x0) / dx))
    for _ in range(n):
        k1 = dhdx(x, h)
        k2 = dhdx(x + dx / 2, h + dx / 2 * k1)
        k3 = dhdx(x + dx / 2, h + dx / 2 * k2)
        k4 = dhdx(x + dx, h + dx * k3)
        h += dx * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        x += dx
        xs.append(x)
        hs.append(h)
    return xs, hs


def window_mean(xs, hs, w):
    v = [hh for xx, hh in zip(xs, hs) if w[0] <= xx <= w[1]]
    return sum(v) / len(v)


def cell_window_mean(ht, w):
    v = [ht[i] for i in range(mi.NX) if w[0] <= (i + 0.5) * mi.DX <= w[1]]
    return sum(v) / len(v)


hnA, hnB = hnorm(mi.ST1), hnorm(mi.ST2)
ok = True
mean = {}
for name, sdir in (("off", sys.argv[1]), ("on", sys.argv[2])):
    ht = load_ht(sdir)
    mean[name] = {w: cell_window_mean(ht, win) for w, win in (("A", WA), ("B", WB), ("C", WC))}

print("等流深: h_nA = %.4f m (u = %.2f m/s), h_nB = %.4f m (u = %.2f m/s), q_m = %.2f m²/s"
      % (hnA, QM / hnA, hnB, QM / hnB, QM))
for name in ("off", "on"):
    eA = abs(mean[name]["A"] - hnA) / hnA
    eB = abs(mean[name]["B"] - hnB) / hnB
    okA, okB = eA < TOL_N, eB < TOL_N
    print("[%s] (1) 等流 A : <h_t> = %.4f m (err %.2f%%, tol %.0f%%) : %s"
          % (name, mean[name]["A"], 100 * eA, 100 * TOL_N, "PASS" if okA else "FAIL"))
    print("[%s] (2) 等流 B : <h_t> = %.4f m (err %.2f%%, tol %.0f%%) : %s"
          % (name, mean[name]["B"], 100 * eB, 100 * TOL_N, "PASS" if okB else "FAIL"))
    ok = ok and okA and okB
dB = abs(mean["on"]["B"] - mean["off"]["B"]) / hnB
okS = dB < TOL_SAME
print("    (2') 直線部の on/off 差 = %.2f%% (tol %.0f%%) : %s" % (100 * dB, 100 * TOL_SAME, "PASS" if okS else "FAIL"))
ok = ok and okS

ode = {}
for name, curv in (("off", False), ("on", True)):
    xs, hs = ode_profile(curv, WA[0], hnA, WB[1])
    ode[name] = window_mean(xs, hs, WC)
    eC = abs(mean[name]["C"] - ode[name]) / ode[name]
    okC = eC < TOL_C
    print("[%s] (3) 円弧上  : <h_t> = %.4f m vs ODE %.4f m (err %.2f%%, tol %.0f%%) : %s"
          % (name, mean[name]["C"], ode[name], 100 * eC, 100 * TOL_C, "PASS" if okC else "FAIL"))
    ok = ok and okC

d_enc = mean["on"]["C"] - mean["off"]["C"]
d_ode = ode["on"] - ode["off"]
ratio = d_enc / d_ode
okR = RATIO_LO <= ratio <= RATIO_HI
print("(4) 効果  : 円弧上の厚化 on−off = %.4f m(ODE %.4f m, 比 %.2f, 許容 [%.1f, %.1f]) : %s"
      % (d_enc, d_ode, ratio, RATIO_LO, RATIO_HI, "PASS" if okR else "FAIL"))
ok = ok and okR

print("== curvature 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
