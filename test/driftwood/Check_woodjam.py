#!/usr/bin/env python3
# driftwood の集積流木(fn_dwtrap・culv_jam。developer.md §50.7・§50.8)の検定。標準ライブラリだけで書く
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
#   Check_woodjam.py grow <result_dir> <E> <dw_jamgrow>
#     集積が進むほど捕捉率が上がる dw_jamgrow(developer.md §50.10)。捕捉率は
#       E_eff(w) = E + (1 − E)·w/w_full(w < w_full)、1(w >= w_full)   (w: セルの集積量、w_full = dw_jamgrow)
#     捕捉セルの面積あたりに届いた流木の累積を A とすると dw/dA = E_eff(w) で、
#       w = E w_full/(1 − E)·[exp((1 − E) A/w_full) − 1]      (A <= A* = w_full/(1 − E)·ln(1/E))
#       w = w_full + (A − A*)                                   (A > A*)
#     集積した割合 trap_m3 / rec_hyd_m3 が w(A_tot)/A_tot に ±TOL_E で一致し、終了時に流動流木が残っていない。
#     A_tot = 発生した流木の全量 / 捕捉セルの面積(流れへの作用なし = 一様な流れで、全量が捕捉セルを 1 回通る)
#   Check_woodjam.py culv <result_dir> <V_j> [both]
#     カルバートの流入口の集積(culv_jam = 1。上流槽を 1 本のカルバートで排水する test/culvert の配置)
#     (1) 台帳: 捕捉の累積 trap_m3 と現在の集積 vol_jam_m3 が V_j (m3) に一致し、流動流木と立木が
#         残っていない(上流槽の水は全部がカルバートを通るので、流木も全量が流入口に集積する)
#     (2) 流量則: Log.txt の S(平均水深。f_disp_debug = 1)から求めた流量 Q = −A_total ΔS/Δt が、
#         その時刻の集積 V_j(t) の損失 C_A(t) = 2 κ0 V_j(t)/(B D) を入れた流量則に、最初の出力間隔を
#         除く全区間で ±TOL_Q で一致する。流入口の集積は、引いた水の割合ずつ捕捉するので数分〜数十分
#         かけて出来上がる。V_j(t) は driftwood.csv の vol_jam_m3(dt_recrd を dt_disp の半分にして、
#         区間の両端と中点の値を読む)。上流水深は h1 = S·A_total/A_up、流量則は区間の両端と中点の
#         シンプソン平均
#           堰:   Q_w = 0.35 B h1 √(2g h1)·(1 + C_A/3)^(−3/2)
#           満管: Q_p = B D √(2g/(1 + c_e + C_A))·√(h1 − (d_c + D)/2)、d_c = min(D, (Q_w²/(g B²))^(1/3))
#           Q = Q_w(h1 < D)、min(Q_w, Q_p)(h1 >= D)
#     (3) 感度: 集積のない流量則(C_A = 0)に対する比 Q/Q_0 が全区間で SENS より小さい(集積の損失が
#         効いている)。both を付けると、満管が支配する区間と堰が支配する区間の両方があること
#   Check_woodjam.py share <result_dir>
#     本流の水の一部を引くカルバートの流入口の捕捉(culv_jam = 1・f_dwjam = 0。developer.md §50.11)。
#     取水セル群の流動流木のうち、カルバートが引いた水と同じ割合が集積する。流れが定常なら、
#     取水セル群の濃度は上流から来る濃度に等しく、集積する割合は流量の比になる:
#       trap_m3 / rec_hyd_m3 = Q_c / Q_in
#     (1) 集積した割合が Q_c/Q_in に ±TOL_SHARE で一致。Q_in = 取水セル群の上流の断面流量
#         (fluxes/flux0001.csv)、Q_c = Q_in − 取水セル群と吐口セル群の間の断面流量(flux0002.csv)。
#         どちらも最後の記録(定常)。Q_c/Q_in が SHARE_MIN〜SHARE_MAX にあること(全量でも 0 でもない
#         条件の検定になっている)と、吐口セル群の下流の断面流量(flux0003.csv)が Q_in に戻ることも見る
#     (2) 終了時に流動流木が残っていない
import sys, os, math, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_jam import NX, NY, DX, S, N, G, W, I_TRAP, Q_UNIT, rows, total_stock
from make_jam import C_BW, C_D, C_CE, C_ATOT, C_AUP

D_LOG = 0.3                       # dw_dlog(param_jam*.txt と対)
TOL_VOL, TOL_STEADY, TOL_RISE, TOL_E = 1.0e-9, 1.0e-3, 0.03, 0.03
TOL_Q, SENS = 0.005, 0.95         # カルバートの流量則との一致、集積なしの流量則に対する比の上限
TOL_SHARE, SHARE_MIN, SHARE_MAX = 0.01, 0.05, 0.5   # 引いた水の割合との一致、検定に使う割合の範囲


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


def ledger_series(rdir, name):
    lines = [ln for ln in open(rdir + "/driftwood.csv").read().split("\n") if ln.strip()]
    names = lines[0].split(",")
    it, iv = names.index("time_s"), names.index(name)
    rows_ = [ln.split(",") for ln in lines[1:]]
    return [float(r[it]) for r in rows_], [float(r[iv]) for r in rows_]


def flux_last(rdir, k):
    """断面流量の記録 fluxes/flux000k.csv の最後の行の流量 (m3/s)"""
    lines = [ln for ln in open("%s/fluxes/flux%04d.csv" % (rdir, k)) if ln.strip() and not ln.startswith("#")]
    return float(lines[-1].split(",")[2])


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


def grow_share(e, wfull, atot):
    """dw/dA = E_eff(w) の解から、届いた流木のうち集積する割合"""
    astar = wfull / (1.0 - e) * math.log(1.0 / e)
    if atot <= astar:
        w = e * wfull / (1.0 - e) * (math.exp((1.0 - e) * atot / wfull) - 1.0)
    else:
        w = wfull + (atot - astar)
    return w / atot, astar


def check_grow(rdir, e, wfull):
    led = ledger_last(rdir)
    frac = led["trap_m3"] / led["rec_hyd_m3"]
    atot = led["rec_hyd_m3"] / (W * DX * DX)             # 捕捉セル(幅 W セル × 1 列)の面積あたりに届く量
    ana, astar = grow_share(e, wfull, atot)
    g1 = abs(frac / ana - 1.0) < TOL_E
    g2 = led["vol_float_m3"] < 1.0e-6 * total_stock() and led["vol_stock_m3"] == 0.0
    print("(1) dw_jamgrow: 集積 %.4f m3 / 発生 %.4f m3 = %.4f、解 %.4f(E = %g、dw_jamgrow = %g、届く量 %.3f m3/m2、"
          "飽和に要る量 %.3f m3/m2 = %s。±%.0f%%) : %s"
          % (led["trap_m3"], led["rec_hyd_m3"], frac, ana, e, wfull, atot, astar,
             "途中で飽和" if atot > astar else "飽和しない", 100 * TOL_E, "PASS" if g1 else "FAIL"))
    print("(2) 終了時の流動流木 %.3e m3、立木 %.3e m3(全部が捕捉セルを通った) : %s"
          % (led["vol_float_m3"], led["vol_stock_m3"], "PASS" if g2 else "FAIL"))
    return g1 and g2


def culv_law(h1, ca):
    """上流水深 h1、下流は乾いた完全排水口のときのカルバートの流量と支配レジーム(m_boundary の culv_q1)"""
    if h1 <= 0.0:
        return 0.0, "weir"
    qw = 0.35 * C_BW * h1 * math.sqrt(2.0 * G * h1)
    if ca > 0.0:
        qw *= (1.0 + ca / 3.0) ** (-1.5)
    if h1 >= C_D:
        dc = min(C_D, (qw * qw / (G * C_BW * C_BW)) ** (1.0 / 3.0))
        de = h1 - 0.5 * (dc + C_D)
        if de > 0.0:
            qp = C_BW * C_D * math.sqrt(2.0 * G / (1.0 + C_CE + ca)) * math.sqrt(de)
            if qp < qw:
                return qp, "pipe"
    return qw, "weir"


def read_log(rdir):
    t, s = [], []
    for line in open(rdir + "/Log.txt"):
        f = line.split()
        if len(f) < 3 or ":" not in f[0]:
            continue
        hh, mm, ss = f[0].split(":")
        t.append(int(hh) * 3600 + int(mm) * 60 + float(ss))
        s.append(float(f[2]))
    return t, s


def check_culv(rdir, vj, both, cd=1.0, phi=0.3):
    led = ledger_last(rdir)
    g1 = (abs(led["trap_m3"] - vj) < 1.0e-6 * vj and abs(led["vol_jam_m3"] - vj) < 1.0e-6 * vj
          and led["vol_float_m3"] < 1.0e-6 * vj and led["vol_stock_m3"] == 0.0)
    print("(1) 台帳: trap_m3 = %.6f、vol_jam_m3 = %.6f(期待 %.6f m3)、流動 %.1e・立木 %.1e m3 : %s"
          % (led["trap_m3"], led["vol_jam_m3"], vj, led["vol_float_m3"], led["vol_stock_m3"],
             "PASS" if g1 else "FAIL"))

    kap = 2.0 * cd / (math.pi * D_LOG * (1.0 - phi) ** 3)
    ca = 2.0 * kap * vj / (C_BW * C_D)
    t, s = read_log(rdir)
    tl, vl = ledger_series(rdir, "vol_jam_m3")

    def ca_at(tt):                                       # その時刻の集積の損失係数 C_A(t)
        for a, v in zip(tl, vl):
            if abs(a - tt) < 1.0e-6:
                return 2.0 * kap * v / (C_BW * C_D)
        sys.exit("driftwood.csv に時刻 %g s の記録がない(dt_recrd を dt_disp の半分にする)" % tt)

    emax, rmin, rmax, nreg = 0.0, 1.0e30, 0.0, {"weir": 0, "pipe": 0}
    hmax, hmin = 0.0, 1.0e30
    for k in range(1, len(t) - 1):                       # 最初の出力間隔(流れと集積の立ち上がり)を除く
        qn = -C_ATOT * (s[k + 1] - s[k]) / (t[k + 1] - t[k])
        ha, hb = s[k] * C_ATOT / C_AUP, s[k + 1] * C_ATOT / C_AUP
        hm = 0.5 * (ha + hb)
        qm, reg = culv_law(hm, ca_at(0.5 * (t[k] + t[k + 1])))
        ql = (culv_law(ha, ca_at(t[k]))[0] + 4.0 * qm + culv_law(hb, ca_at(t[k + 1]))[0]) / 6.0
        q0 = (culv_law(ha, 0.0)[0] + 4.0 * culv_law(hm, 0.0)[0] + culv_law(hb, 0.0)[0]) / 6.0
        nreg[reg] += 1
        emax = max(emax, abs(qn / ql - 1.0))
        rmin, rmax = min(rmin, qn / q0), max(rmax, qn / q0)
        hmax, hmin = max(hmax, hm), min(hmin, hm)
    g2 = emax < TOL_Q
    print("(2) 流量則: κ0 = %.4f 1/m、出来上がった集積の C_A = 2 κ0 V_j/(B D) = %.4f(堰の倍率 %.4f、満管の倍率 %.4f)"
          % (kap, ca, (1.0 + ca / 3.0) ** (-1.5), math.sqrt((1.0 + C_CE) / (1.0 + C_CE + ca))))
    print("    集積 V_j(t) は最初の区間の終わり(%.0f s)で %.2f %%、次の区間の終わりで %.3f %% まで出来上がる"
          % (t[1], 100.0 * ca_at(t[1]) / ca, 100.0 * ca_at(t[2]) / ca))
    print("    h1 = %.3f → %.3f m の %d 区間で |Q/Q_law(V_j(t)) − 1| の最大 %.4f %% (< %.1f %%) : %s"
          % (hmax, hmin, len(t) - 2, 100.0 * emax, 100.0 * TOL_Q, "PASS" if g2 else "FAIL"))
    g3 = rmax < SENS and (not both or (nreg["pipe"] > 0 and nreg["weir"] > 0))
    print("(3) 感度: 集積のない流量則に対する比 Q/Q_0 = %.3f〜%.3f (< %.2f)、満管が支配 %d 区間・堰が支配 %d 区間%s : %s"
          % (rmin, rmax, SENS, nreg["pipe"], nreg["weir"], "(両方が必要)" if both else "",
             "PASS" if g3 else "FAIL"))
    return g1 and g2 and g3


def check_share(rdir):
    led = ledger_last(rdir)
    frac = led["trap_m3"] / led["rec_hyd_m3"]
    qin, qmid, qdn = flux_last(rdir, 1), flux_last(rdir, 2), flux_last(rdir, 3)
    share = (qin - qmid) / qin
    g1 = (abs(frac / share - 1.0) < TOL_SHARE and SHARE_MIN < share < SHARE_MAX
          and abs(qdn / qin - 1.0) < 1.0e-4)
    print("(1) 引いた水の割合: Q_in = %.4f、取水と吐口の間 %.4f、吐口の下流 %.4f m3/s → Q_c/Q_in = %.5f(%g〜%g の範囲)"
          % (qin, qmid, qdn, share, SHARE_MIN, SHARE_MAX))
    print("    集積 %.4f m3 / 発生 %.4f m3 = %.5f、比 %.4f (1 ± %.2f) : %s"
          % (led["trap_m3"], led["rec_hyd_m3"], frac, frac / share, TOL_SHARE, "PASS" if g1 else "FAIL"))
    g2 = led["vol_float_m3"] < 1.0e-6 * total_stock() and led["vol_stock_m3"] == 0.0
    print("(2) 終了時の流動流木 %.3e m3、立木 %.3e m3(全部が取水セル群を通った) : %s"
          % (led["vol_float_m3"], led["vol_stock_m3"], "PASS" if g2 else "FAIL"))
    return g1 and g2


if __name__ == "__main__":
    mode, rdir = sys.argv[1], sys.argv[2]
    if mode == "jam":
        cd = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
        phi = float(sys.argv[5]) if len(sys.argv) > 5 else 0.3
        ok = check_jam(rdir, sys.argv[3], cd, phi)
    elif mode == "ratio":
        ok = check_ratio(rdir, float(sys.argv[3]))
    elif mode == "culv":
        ok = check_culv(rdir, float(sys.argv[3]), "both" in sys.argv[4:])
    elif mode == "share":
        ok = check_share(rdir)
    else:
        ok = check_grow(rdir, float(sys.argv[3]), float(sys.argv[4]))
    print("== woodjam 検定(%s %s): %s ==" % (mode, rdir, "PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)
