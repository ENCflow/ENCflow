#!/usr/bin/env python3
# avalanche 構成 2〜5(一様な斜面の一斉発生)の検定
#   使い方: Check_sheet.py            (result_sh0・shm・shh・sht と save_sh0・shm・shh・sht を読む)
#   地形・定数は param_sh*.txt / make_init.py sheet と対で保守する
#
#   勾配 S の一様な斜面の全面で、厚さ D の雪が一斉に動き出し、下の雪を取り込む。流れに沿う変化がないので、
#   領域の中央の流速 u(水平)と流動深 h_t = h + hs(鉛直)は、時間だけの常微分方程式に従う(独自の整理。
#   f_gravity_correction = 2 の斜面に沿う抵抗。cos²θ = 1/(1 + S²)):
#       du/dt   = g cos²θ (S − μ) − g u² / (ξ h_t cos²θ) − [f_dbmom = 1 のとき] u E / h_t
#       dh_t/dt = E                    (f_dbwet = 1・db_satbed = 1: 取り込んだ雪がかさ体積のまま加わる)
#       E = δe u(f_dbed = 4)、E_r h_t u(f_dbed = 5)、0(流動深が db_hent 未満)
#   最後の項が、取り込んだ雪を静止から流速まで加速する分(運動量の保存)。Hungr の則では dh_t/dx = E_r h_t なので、
#   流動深は進んだ距離 x に対して D exp(E_r x) で増える
import struct
import sys

NX, NY, DX = 300, 20, 2.0
S, D, LAYER = 0.5, 0.5, 3.0
G, MU, XI, PORO = 9.8, 0.2, 1500.0, 0.1
DELTE, ER, HENT = 0.02, 0.02, 0.6
TEND = 8.0
IC, JC = 150, 10                       # 中央のセル(1 始まり)
TOL_ODE = 0.01                         # 常微分方程式との相対差
TOL_SUM = 1.0e-9                       # 固体の台帳(初期の雪の量との比)
TOL_SD = 1.0e-12


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


def read_state(savedir):
    ntot = NX * NY
    with open(savedir + "/state.dat", "rb") as f:
        h = read_rle_array(f, ntot)
        z = read_rle_array(f, ntot)
        read_rle_array(f, ntot)     # hrs
        read_rle_array(f, ntot)     # hg
        sd = read_rle_array(f, ntot)
        hs = read_rle_array(f, ntot)
    return h, z, sd, hs


def read_bil(resdir, name):
    """最後の出力(.bil。float32、先頭行が北端)の中央のセルの値。"""
    with open("%s/%s0001.bil" % (resdir, name), "rb") as f:
        a = struct.unpack("<%df" % (NX * NY), f.read(4 * NX * NY))
    return a[(NY - JC) * NX + (IC - 1)]


def ode(law, mom, dt=1.0e-4):
    """常微分方程式の解 (u, h_t, x) の TEND での値。law: 4 = 速度比例、5 = Hungr、0 = 連行なし。"""
    c2 = 1.0 / (1.0 + S * S)
    u, h, x, ent = 0.0, D, 0.0, 0.0
    for _ in range(int(round(TEND / dt))):
        e = 0.0
        if ent < LAYER:
            e = DELTE * u if law == 4 else (ER * h * u if law == 5 else 0.0)
        a = G * c2 * (S - MU) - G * u * u / (XI * h * c2) - (u * e / h if mom else 0.0)
        x += u * dt
        u += a * dt
        h += e * dt
        ent += e * dt
    return u, h, x


def idx(i, j):
    return (j - 1) * NX + (i - 1)


ok_all = True
cases = (("sh0", "(2) 速度比例・運動量を数えない", 4, False),
         ("shm", "(3) 速度比例・運動量を数える  ", 4, True),
         ("shh", "(4) Hungr の則・運動量を数える ", 5, True),
         ("sht", "(5) 流動深の下限(連行しない) ", 0, True))
for tag, title, law, mom in cases:
    u = read_bil("result_" + tag, "u")
    h, z, sd, hs = read_state("save_" + tag)
    k = idx(IC, JC)
    ht = h[k] + hs[k]
    ue, he, xe = ode(law, mom)
    du, dh = abs(u / ue - 1.0), abs(ht / he - 1.0)
    ok = du < TOL_ODE and dh < TOL_ODE
    print("%s: u = %.3f m/s(解 %.3f、差 %.2f %%)、h_t = %.3f m(解 %.3f、差 %.2f %%) : %s"
          % (title, u, ue, 100 * du, ht, he, 100 * dh, "PASS" if ok else "FAIL"))
    ok_all = ok_all and ok
    # 固体の台帳: Σhs + (1 − λ) Σ(z − z0) = 0(z0 は初期の雪面)
    z0 = [S * (NX * DX - (i + 0.5) * DX) + D + LAYER for i in range(NX)] * NY
    solids = sum(hs) + (1.0 - PORO) * sum(zi - z0i for zi, z0i in zip(z, z0))
    total = (1.0 - PORO) * (D + LAYER) * NX * NY
    ok = abs(solids) < TOL_SUM * total
    print("      固体の台帳 sum(hs)+(1-λ)sum(dz) = %.3e m*cell(初期の雪の %.1e 倍) : %s"
          % (solids, abs(solids) / total, "PASS" if ok else "FAIL"))
    ok_all = ok_all and ok
    if tag == "shh":
        # Hungr の則: 流動深は進んだ距離 x に対して D exp(E_r x)。x は常微分方程式の解の値
        import math
        xnum = math.log(ht / D) / ER
        ok = abs(xnum / xe - 1.0) < TOL_ODE
        print("      体積の成長 ln(h_t/D)/E_r = %.2f m(進んだ距離の解 %.2f m) : %s"
              % (xnum, xe, "PASS" if ok else "FAIL"))
        ok_all = ok_all and ok
    if tag == "sht":
        # 流動深 0.5 m < 下限 0.6 m なので、領域の中央部(下流端の壁にたまる所を除く)は連行しない
        # (動き出した 0.5 m を除いた残りの雪の厚さが、連行できる層の厚さのまま)
        dmax = max(abs(sd[idx(i, j)] - LAYER) for j in range(1, NY + 1) for i in range(100, 201))
        ok = dmax < TOL_SD
        print("      連行なし max|sd − %.1f|(i = 100〜200)= %.1e m : %s" % (LAYER, dmax, "PASS" if ok else "FAIL"))
        ok_all = ok_all and ok

print("== avalanche 構成 2〜5(一様な斜面)検定: %s ==" % ("PASS" if ok_all else "FAIL"))
sys.exit(0 if ok_all else 1)
