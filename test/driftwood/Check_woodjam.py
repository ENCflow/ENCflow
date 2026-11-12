#!/usr/bin/env python3
# driftwood の集積流木(fn_dwtrap。developer.md §50.7)の検定。標準ライブラリだけで書く
#   Check_woodjam.py jam <result_dir> <save_dir> [cd phi]
#     (1) 材積保存: save の driftwood.dat の Σwst + Σhd + Σwd + Σwj = 初期ストック総量
#         (捕捉率 1 なので下流へ出ない。gv = wfrac = 1 の水路が前提)
#     (2) 台帳: driftwood.csv の最後の行の trap_m3 と vol_jam_m3 が初期ストック総量に一致
#     (3) 定常: 最後の 2 つの出力(30 分と 40 分)の水深の差が TOL_STEADY 以内
#     (4) 堰上げ: 集積のセルの 1 つ上流の水深 h_up が、集積の下流の一様な区間の水深 h_dn から
#         漸変流の式
#           dh/dx = [S − n²q²/h^(10/3) − κ0·min(w/h, φ)·q²/(g h²)] / (1 − q²/(g h³))
#         を集積の両側の辺(長さ 2Δx、集積量は辺の両側のセルの平均 = w_j/2)について上流へ
#         積分した値 h_ana に一致。上昇量の比 (h_up − h_dn)/(h_ana − h_dn) が 1 ± TOL_RISE
#         κ0 = 2 C_D / (π d (1 − φ)³)(cd・phi の省略時は既定の 1.0・0.3)
#   Check_woodjam.py ratio <result_dir> <E>
#     集積した割合 trap_m3 / rec_hyd_m3 が E に ±TOL_E で一致し、終了時に流動流木が残っていない
#   Check_woodjam.py grow <result_dir>
#     集積した割合が 0.99 より大きい(dw_jamgrow で捕捉率が 1 になる)
import sys, os, math, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_jam import NX, NY, DX, S, N, G, W, I_TRAP, Q_UNIT, rows, total_stock

D_LOG = 0.3                       # dw_dlog(param_jam*.txt と対)
TOL_VOL, TOL_STEADY, TOL_RISE, TOL_E = 1.0e-9, 1.0e-3, 0.03, 0.03


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    assert struct.unpack("<i", f.read(4))[0] == n, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
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


def load(rdir, name, k):
    return [[float(v) for v in line.split()] for line in open("%s/%s%04d.txt" % (rdir, name, k))]


def ledger_last(rdir):
    lines = open(rdir + "/driftwood.csv").read().split("\n")
    names = lines[0].split(",")
    vals = [float(v) for v in [ln for ln in lines if ln.strip()][-1].split(",")]
    return dict(zip(names, vals))


def nframes(rdir):
    return max(int(ln.split(",")[0]) for ln in open(rdir + "/FILENUMBER.csv")
               if not ln.startswith("#") and int(ln.split(",")[0]) < 9000)


def check_jam(rdir, sdir, cd, phi):
    ntot = NX * NY
    with open(sdir + "/driftwood.dat", "rb") as f:
        hd = read_rle_array(f, ntot)
        wd = read_rle_array(f, ntot)
        wst = read_rle_array(f, ntot)
        read_rle_array(f, ntot)                                  # zref
        flag = struct.unpack("<i", read_rec(f))[0]               # 集積の印
        assert flag == 1, "no jam flag in driftwood.dat"
        wj = read_rle_array(f, ntot)
    area = DX * DX
    v0 = total_stock()
    vsum = (sum(hd) + sum(wd) + sum(wst) + sum(wj)) * area
    g1 = abs(vsum - v0) < TOL_VOL * v0
    print("(1) 材積保存: Σ(wst + hd + wd + wj)·A − 初期 = %.3e m3(初期 %.1f m3。集積 %.6f m3) : %s"
          % (vsum - v0, v0, sum(wj) * area, "PASS" if g1 else "FAIL"))

    led = ledger_last(rdir)
    g2 = abs(led["trap_m3"] - v0) < 1.0e-6 * v0 and abs(led["vol_jam_m3"] - v0) < 1.0e-6 * v0
    print("(2) 台帳: trap_m3 = %.6f、vol_jam_m3 = %.6f(初期 %.1f m3) : %s"
          % (led["trap_m3"], led["vol_jam_m3"], v0, "PASS" if g2 else "FAIL"))

    k = nframes(rdir)
    h = load(rdir, "H", k); h1 = load(rdir, "H", k - 1); wjm = load(rdir, "Wj", k)
    j1, j2 = rows()
    dsteady = max(abs(h[j - 1][i] - h1[j - 1][i]) for j in range(j1, j2 + 1) for i in range(NX))
    g3 = dsteady < TOL_STEADY
    print("(3) 定常: 最後の 2 つの出力の水深の差の最大 %.2e m (< %.0e) : %s" % (dsteady, TOL_STEADY, "PASS" if g3 else "FAIL"))

    def hmean(i):
        return sum(h[j - 1][i - 1] for j in range(j1, j2 + 1)) / W
    w = sum(wjm[j - 1][I_TRAP - 1] for j in range(j1, j2 + 1)) / W      # 集積のセルの w_j(横断の平均)
    hup = hmean(I_TRAP - 1)
    hdn = sum(hmean(i) for i in range(I_TRAP + 2, I_TRAP + 6)) / 4.0    # 下流の一様な区間
    kap = 2.0 * cd / (math.pi * D_LOG * (1.0 - phi) ** 3)
    q = Q_UNIT

    def rhs(hh):
        sf = N * N * q * q / hh ** (10.0 / 3.0)
        sj = kap * min(0.5 * w / hh, phi) * q * q / (G * hh * hh)
        return (S - sf - sj) / (1.0 - q * q / (G * hh ** 3))
    hh, n = hdn, 20000
    dx = -2.0 * DX / n
    for _ in range(n):                                                   # RK4 で上流へ
        k1 = rhs(hh); k2 = rhs(hh + 0.5 * dx * k1); k3 = rhs(hh + 0.5 * dx * k2); k4 = rhs(hh + dx * k3)
        hh += dx * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
    ratio = (hup - hdn) / (hh - hdn)
    g4 = abs(ratio - 1.0) < TOL_RISE
    print("(4) 堰上げ: w_j = %.4f m、κ0 = %.4f 1/m、φ = %g、辺の w_e/h = %.3f(上限 %s)"
          % (w, kap, phi, 0.5 * w / hup, "効く" if 0.5 * w / hup > phi else "効かない"))
    print("    下流 h_dn = %.4f m、上流 h_up = %.4f m、解析 h_ana = %.4f m、上昇量の比 %.4f (1 ± %.2f) : %s"
          % (hdn, hup, hh, ratio, TOL_RISE, "PASS" if g4 else "FAIL"))
    return g1 and g2 and g3 and g4


def check_ratio(rdir, e):
    led = ledger_last(rdir)
    frac = led["trap_m3"] / led["rec_hyd_m3"]
    g1 = abs(frac / e - 1.0) < TOL_E
    g2 = led["vol_float_m3"] < 1.0e-6 * total_stock() and led["vol_stock_m3"] == 0.0
    print("(1) 捕捉率: 集積 %.4f m3 / 発生 %.4f m3 = %.4f(E = %g、±%.0f%%) : %s"
          % (led["trap_m3"], led["rec_hyd_m3"], frac, e, 100 * TOL_E, "PASS" if g1 else "FAIL"))
    print("(2) 終了時の流動流木 %.3e m3、立木 %.3e m3(全部が捕捉セルを通った) : %s"
          % (led["vol_float_m3"], led["vol_stock_m3"], "PASS" if g2 else "FAIL"))
    return g1 and g2


def check_grow(rdir):
    led = ledger_last(rdir)
    frac = led["trap_m3"] / led["rec_hyd_m3"]
    g1 = frac > 0.99
    print("(1) dw_jamgrow: 集積 %.4f m3 / 発生 %.4f m3 = %.4f (> 0.99) : %s"
          % (led["trap_m3"], led["rec_hyd_m3"], frac, "PASS" if g1 else "FAIL"))
    return g1


if __name__ == "__main__":
    mode, rdir = sys.argv[1], sys.argv[2]
    if mode == "jam":
        cd = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
        phi = float(sys.argv[5]) if len(sys.argv) > 5 else 0.3
        ok = check_jam(rdir, sys.argv[3], cd, phi)
    elif mode == "ratio":
        ok = check_ratio(rdir, float(sys.argv[3]))
    else:
        ok = check_grow(rdir)
    print("== woodjam 検定(%s %s): %s ==" % (mode, rdir, "PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)
