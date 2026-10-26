#!/usr/bin/env python3
"""vzcol: VZ(鉛直不飽和浸透)共有参照柱の検定(developer.md §87)

Python 標準ライブラリのみ。使い方:
  python3 Check_vzcol.py base   result                  # param.txt の結果
  python3 Check_vzcol.py fixed  result_fixed            # 固定圧下端の定常解
  python3 Check_vzcol.py tight  result result_tight     # 時間許容を 1/4 にした再計算との差
  python3 Check_vzcol.py avg    result result_avg       # 面積平均モード(一様雨)と厳密モードの一致
  python3 Check_vzcol.py sd0    result_sd0              # 土層厚 0 のセルを含む区画の集約
  python3 Check_vzcol.py hydro  result_hydro            # 静水圧の初期条件(vz_wt0)が静止解のまま

base の検定項目:
  (a) 定常期(雨 = q0 = 1 mm/h、t <= 3600 s): 全深さの累積流束 = q0·t、貯留不変
  (b) 各出力深さの保存則 S(t) − S(t1) = [F0(t) − F0(t1)] − [D(t) − D(t1)]
      (非線形残差の予算 vz_mb_rate·t の範囲)
  (c) 鉛直分布の θ(ψ)・K(ψ) が小杉式(Kosugi 1996)の値と一致
  (d) 区画の貯留・排水をセル別の読み出し(土層厚の補間)で積み上げた値と、
      面積重み W・M による集約値が一致。区画の収支残差が予算内
  (e) 柱の上端入力 F0 が降雨表(1 分更新・線形補間)から独立に組み立てた雨量と
      一致し、Log の S_total の変化が F0 − 系外流出/全面積 と一致
"""
import csv
import math
import os
import sys

# param.txt と同じ値(検定用の例示値)
KS = 100.0 / 3.6e6
THS, THR, PSIM, SIGMA = 0.5, 0.1, -0.5, 1.5
Q0 = 1.0 / 3.6e6
DT = 5.0
DT_PRUPDATE = 60.0
MB_RATE = 1.0e-11
DX = DY = 10.0
RAIN_TABLE = [(0, 1), (60, 1), (61, 50), (180, 50), (181, 0), (9999, 0)]   # (min, mm/h)
SD = [[0.3000, 0.5000, 0.7375],
      [1.0000, 1.2340, 1.5000],
      [2.0000, 2.5000, 0.4125],
      [0.6000, 0.8000, 1.1111],
      [1.3000, 1.7000, 2.2222],
      [0.9000, 1.0125, 1.4000],
      [0.3333, 2.9000, 1.8000],
      [0.5500, 1.2000, 2.7500]]

failed = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failed.append(msg)


def read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    data = [[float(v) for v in r] for r in rows[1:] if r]
    return head, data


def kosugi(psi):
    if psi >= 0.0:
        return THS, KS
    x = (math.log(-psi) - math.log(-PSIM)) / SIGMA
    se = 0.5 * math.erfc(x / math.sqrt(2.0))
    q2 = 0.5 * math.erfc((x + SIGMA) / math.sqrt(2.0))
    return THR + (THS - THR) * se, KS * math.sqrt(se) * q2 * q2


def read_prof(path):
    head, data = read_csv(path)
    return data          # z, psi, theta, K, zbottom, Fbottom


def read_log(path):
    out = {}
    with open(path) as f:
        for line in f:
            s = line.split()
            if len(s) < 5 or ":" not in s[0] or s[0].startswith("time"):
                continue
            h, m, sec = s[0].split(":")
            t = int(h) * 3600 + int(m) * 60 + float(sec)
            out[round(t)] = float(s[4])          # S_total
    return out


def rain_rate(tmin):
    for (t1, r1), (t2, r2) in zip(RAIN_TABLE[:-1], RAIN_TABLE[1:]):
        if t1 <= tmin <= t2:
            return (r1 + (r2 - r1) * (tmin - t1) / (t2 - t1)) / 3.6e6
    return 0.0


def expected_f0(tend):
    """降雨表から地上雨量の積算 (m) を組み立てる(makepre の更新規則に合わせる:
    初期化時 t=0 と、t が DT_PRUPDATE の倍数になるステップで rate(t) に更新し、
    更新したステップから次の更新の前のステップまでその値を使う)"""
    nstep = int(round(tend / DT))
    idt = int(round(DT_PRUPDATE / DT))
    rate = rain_rate(0.0)
    total = 0.0
    for it in range(1, nstep + 1):
        if it % idt == 0:
            rate = rain_rate(it * DT / 60.0)
        total += rate * DT
    return total


def depth_cols(head):
    deps = []
    for h in head:
        if h.startswith("D@"):
            deps.append(float(h[2:].split("(")[0]))
    return deps


def check_zone_sum(res, sd, tag):
    """区画の貯留・排水(面積重み W・M による集約)が、鉛直分布の出力から
    セルごとに土層厚の深さで読み出した値の和と一致する(土層厚 0 のセルは
    界面 0 で読む = 排水は上端入力 F0、貯留は 0)"""
    hc, col = read_csv(os.path.join(res, "vz_column.csv"))
    hz, zone = read_csv(os.path.join(res, "vz_zone.csv"))
    it, iF0 = hc.index("time(s)"), hc.index("F0(m)")
    izt = hz.index("time(s)")
    ivs, ivd = hz.index("vstore(m3)"), hz.index("vdrain(m3)")
    zrow = {round(r[izt]): r for r in zone}
    crow = {round(r[it]): r for r in col}
    profs = sorted(f for f in os.listdir(res) if f.startswith("vzprof_1_"))
    for f, t in zip(profs, [21600, 43200]):
        prof = read_prof(os.path.join(res, f))
        dz = prof[0][4]
        faces = [0.0] + [p[4] for p in prof]
        fcum = [crow[t][iF0]] + [p[5] for p in prof]
        bsum = [0.0]
        for p in prof:
            bsum.append(bsum[-1] + p[2] * dz)
        vs, vd = 0.0, 0.0
        for row in sd:
            for d in row:
                j = min(int(d / dz), len(prof))
                while j < len(prof) and faces[j + 1] <= d:
                    j += 1
                while j > 0 and faces[j] > d:
                    j -= 1
                if j >= len(prof):
                    a, j = 0.0, len(prof)
                    vs += DX * DY * bsum[j]
                    vd += DX * DY * fcum[j]
                    continue
                a = (d - faces[j]) / (faces[j + 1] - faces[j])
                vs += DX * DY * ((1 - a) * bsum[j] + a * bsum[j + 1])
                vd += DX * DY * ((1 - a) * fcum[j] + a * fcum[j + 1])
        zr = zrow[t]
        # vzprof は 16 桁で書かれるため、この比較は表示桁の範囲で一致すればよい
        check(abs(vs - zr[ivs]) / zr[ivs] < 1e-12,
              "%s t=%d: zone storage = sum of cell storages (rel %.2e)" % (tag, t, abs(vs - zr[ivs]) / zr[ivs]))
        check(abs(vd - zr[ivd]) / zr[ivd] < 1e-11,
              "%s t=%d: zone drainage = sum of cell drainages (rel %.2e)" % (tag, t, abs(vd - zr[ivd]) / zr[ivd]))


def check_sd0(res):
    """土層厚 0 のセル(雨がそのまま排水される区分)を含む区画の集約と収支"""
    print("== vzcol zero soil depth: " + res)
    sd = []
    with open(os.path.join("data_vzcol", "sd_zero.txt")) as f:
        for line in f:
            if line.split():
                sd.append([float(x) for x in line.split()])
    nzero = sum(1 for row in sd for d in row if d == 0.0)
    check(nzero > 0, "zero soil depth cells present (%d)" % nzero)
    check_zone_sum(res, sd, "(sd0)")
    hz, zone = read_csv(os.path.join(res, "vz_zone.csv"))
    izt, ivin, ires, iarea = (hz.index("time(s)"), hz.index("vin(m3)"), hz.index("residual(m3)"),
                              hz.index("area(m2)"))
    worst = 0.0
    for r in zone:
        worst = max(worst, abs(r[ires]) / (MB_RATE * r[izt] * r[iarea] + 1e-9 * r[ivin]))
    check(worst <= 1.0, "(sd0) zone water balance residual within the budget (worst ratio %.2e)" % worst)


def check_hydro(res, dwt=0.5):
    """静水圧の初期条件 vz_wt0: 下端固定圧 ψ = 0 の柱で地下水面を下端に置くと
    流束 0 の静止解なので、雨なしで進めても ψ(ζ) = ζ − d_wt のまま、流束は 0"""
    print("== vzcol hydrostatic initial condition: " + res)
    profs = sorted(f for f in os.listdir(res) if f.startswith("vzprof_1_"))
    check(len(profs) >= 1, "profile files written (%d)" % len(profs))
    worst_psi, worst_f = 0.0, 0.0
    for f in profs:
        for z, psi, th, kk, zb, fb in read_prof(os.path.join(res, f)):
            worst_psi = max(worst_psi, abs(psi - (z - dwt)))
            worst_f = max(worst_f, abs(fb))
    check(worst_psi < 1e-12, "psi stays hydrostatic psi = z - d_wt (max abs dev %.2e m)" % worst_psi)
    check(worst_f < 1e-12, "cumulative fluxes stay 0 at all faces (max abs %.2e m)" % worst_f)
    hc, col = read_csv(os.path.join(res, "vz_column.csv"))
    iF0, iFb = hc.index("F0(m)"), hc.index("Fbottom(m)")
    check(all(abs(r[iF0]) == 0.0 and abs(r[iFb]) < 1e-12 for r in col),
          "no top input and no bottom outflow in vz_column.csv")


def check_base(res):
    print("== vzcol base: " + res)
    hc, col = read_csv(os.path.join(res, "vz_column.csv"))
    hz, zone = read_csv(os.path.join(res, "vz_zone.csv"))
    deps = depth_cols(hc)
    it, iF0, iFb = hc.index("time(s)"), hc.index("F0(m)"), hc.index("Fbottom(m)")
    iD = [hc.index("D@%.4f(m)" % d) for d in deps]
    iS = [hc.index("S@%.4f(m)" % d) for d in deps]

    # (a) 定常期
    r0 = col[0]
    worst_f, worst_s = 0.0, 0.0
    for r in col:
        t = r[it]
        if t > 3600.0 + 1e-6:
            break
        for k in [iF0, iFb] + iD:
            worst_f = max(worst_f, abs(r[k] - Q0 * t) / (Q0 * t))
        for k in iS:
            worst_s = max(worst_s, abs(r[k] - r0[k]))
    check(worst_f < 1e-9, "(a) steady phase: cumulative flux = q0*t at all depths (max rel err %.2e)" % worst_f)
    check(worst_s < 1e-12, "(a) steady phase: storage unchanged (max abs change %.2e m)" % worst_s)

    # (b) 深さ別の保存則(最初の記録を基準)
    worst = 0.0
    for r in col[1:]:
        dt_ = r[it] - r0[it]
        for kd, ks in zip(iD, iS):
            lhs = r[ks] - r0[ks]
            rhs = (r[iF0] - r0[iF0]) - (r[kd] - r0[kd])
            worst = max(worst, abs(lhs - rhs) / (MB_RATE * dt_ + 1e-12))
    check(worst <= 1.0, "(b) depth-wise conservation dS = F0 - D within the residual budget (worst ratio %.2e)" % worst)

    # (c) 小杉式
    profs = sorted(f for f in os.listdir(res) if f.startswith("vzprof_1_"))
    check(len(profs) >= 2, "(c) profile files written (%d)" % len(profs))
    worst_th, worst_k = 0.0, 0.0
    for f in profs:
        for z, psi, th, kk, zb, fb in read_prof(os.path.join(res, f)):
            th_ref, k_ref = kosugi(psi)
            worst_th = max(worst_th, abs(th - th_ref) / th_ref)
            worst_k = max(worst_k, abs(kk - k_ref) / k_ref)
    check(worst_th < 1e-12 and worst_k < 1e-10,
          "(c) Kosugi theta(psi), K(psi) match (max rel err %.2e, %.2e)" % (worst_th, worst_k))

    # (d) 区画の集約 = セル別の読み出しの総和(出力時刻 6 h・12 h)
    check_zone_sum(res, SD, "(d)")
    izt = hz.index("time(s)")
    ivin, ires = hz.index("vin(m3)"), hz.index("residual(m3)")
    iarea = hz.index("area(m2)")
    zrow = {round(r[izt]): r for r in zone}
    crow = {round(r[it]): r for r in col}
    worst = 0.0
    for r in zone:
        worst = max(worst, abs(r[ires]) / (MB_RATE * r[izt] * r[iarea] + 1e-9 * r[ivin]))
    check(worst <= 1.0, "(d) zone water balance residual within the budget (worst ratio %.2e)" % worst)

    # (e) 雨量と Log の S_total
    worst = 0.0
    for r in col:
        e = expected_f0(r[it])
        worst = max(worst, abs(r[iF0] - e) / e)
    check(worst < 1e-12, "(e) column input F0 equals the rainfall table (max rel err %.2e)" % worst)
    log = read_log(os.path.join(res, "Log.txt"))
    s0 = log[0]
    ivext = hz.index("vexternal(m3)")
    atot = DX * DY * sum(len(r) for r in SD)
    worst = 0.0
    for t, st in log.items():
        if t == 0 or t not in zrow:
            continue
        exp_ = s0 + crow[t][iF0] - zrow[t][ivext] / atot
        worst = max(worst, abs(st - exp_))
    check(worst < 5e-14 + MB_RATE * 43200, "(e) Log S_total = S0 + F0 - outflow/area (max abs err %.2e m)" % worst)


def check_fixed(res):
    """固定圧下端(ψ = 0 at L)+一定上端流束 q の定常解: dψ/dζ = 1 − q/K(ψ) の求積と比較"""
    print("== vzcol fixed: " + res)
    q = 10.0 / 3.6e6
    profs = sorted(f for f in os.listdir(res) if f.startswith("vzprof_1_"))
    prof = read_prof(os.path.join(res, profs[-1]))
    L = prof[-1][4]

    def dpdz(p):
        return 1.0 - q / kosugi(min(p, 0.0))[1]

    worst = 0.0
    for z, psi, th, kk, zb, fb in prof:
        # ζ = L(ψ = 0)から z まで RK4 で上向きに積分
        n = 400
        h = (z - L) / n
        p = 0.0
        for _ in range(n):
            k1 = dpdz(p)
            k2 = dpdz(p + 0.5 * h * k1)
            k3 = dpdz(p + 0.5 * h * k2)
            k4 = dpdz(p + h * k3)
            p += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        worst = max(worst, abs(psi - p))
    check(worst < 5e-4, "steady profile with fixed bottom pressure matches quadrature (max |dpsi| %.2e m)" % worst)
    # 定常なので最後の 2 回の記録の間の流束は全界面で q
    hc, col = read_csv(os.path.join(res, "vz_column.csv"))
    it, iF0, iFb = hc.index("time(s)"), hc.index("F0(m)"), hc.index("Fbottom(m)")
    a, b = col[-2], col[-1]
    fb = (b[iFb] - a[iFb]) / (b[it] - a[it])
    check(abs(fb - q) / q < 1e-6, "steady bottom flux equals the top flux (rel %.2e)" % (abs(fb - q) / q))


def check_pair(res1, res2, tol, label):
    print("== vzcol %s: %s vs %s" % (label, res1, res2))
    h1, c1 = read_csv(os.path.join(res1, "vz_column.csv"))
    h2, c2 = read_csv(os.path.join(res2, "vz_column.csv"))
    keys = [h for h in h1 if h.startswith("D@") or h in ("F0(m)", "Fbottom(m)")]
    worst = 0.0
    for k in keys:
        i1, i2 = h1.index(k), h2.index(k)
        scale = max(abs(r[i1]) for r in c1)
        for r1, r2 in zip(c1, c2):
            worst = max(worst, abs(r1[i1] - r2[i2]) / scale)
    check(len(c1) == len(c2), "same number of records")
    check(worst <= tol, "cumulative fluxes agree (max rel diff %.2e <= %.0e)" % (worst, tol))


def main():
    mode = sys.argv[1]
    if mode == "base":
        check_base(sys.argv[2])
    elif mode == "fixed":
        check_fixed(sys.argv[2])
    elif mode == "tight":
        check_pair(sys.argv[2], sys.argv[3], 2e-3, "time convergence")
    elif mode == "avg":
        check_pair(sys.argv[2], sys.argv[3], 1e-12, "area-average mode")
    elif mode == "sd0":
        check_sd0(sys.argv[2])
    elif mode == "hydro":
        check_hydro(sys.argv[2])
    else:
        sys.exit("unknown mode " + mode)
    if failed:
        print("=== vzcol check FAIL (%d) ===" % len(failed))
        sys.exit(1)
    print("=== vzcol check PASS ===")


if __name__ == "__main__":
    main()
