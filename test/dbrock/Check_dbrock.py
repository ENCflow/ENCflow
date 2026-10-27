#!/usr/bin/env python3
# dbrock 検定(土石流による岩盤侵食。f_rockinc の rock_kdb。developer.md §88.18、
# docs/mountain_stream_plan.md §12.7)
#   Check_dbrock.py db1        DB1: 自己被覆の解析解 e^{H/H*} = e^{H0/H*} + E_d0 t/H*(構成 db1)と、
#                                   更新間隔を変えた構成 db1_dtg との一致。倍率 0 の行は不変
#   Check_dbrock.py db3        DB3: 濃度の門(db3_cmin)・速度の門(db3_vstop)の外で岩盤が削れない
#   Check_dbrock.py db2 LOG    DB2: 閉じた箱の保存(全固体は不変、可動層の固体は岩盤起源の分だけ
#                                   増える、(sd − sd0) − (z − z0) = Ri。台帳と比べる)
# 水深・土砂柱状量・z・sd は save の state.dat(倍精度)、Ri は geomorph_rockinc.dat から読む。
# 定数は param*.txt・make_init.py と対で保守する。
import sys, os, math, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, DX, IC, J1, J2, sd1, fr1, NX2, NY2, DX2, z2, sd2

RHO, G = 1000.0, 9.8                 # m_geomorph_debris の rk_rhow、既定の重力加速度
LAM, SGRAV = 0.4, 1.65               # fluv_porosity・fluv_sgrav
# 構成 db1(DB1)
KD, TAUCD, MD, HS, T1 = 1.0e-3, 300.0, 1.5, 0.05, 600.0
TOL_DB1, TOL_SAME = 1.0e-9, 1.0e-12
# 構成 db2(DB2)
TOL_SUM, TOL_RI, TOL_LEDGER, MIN_V = 1.0e-10, 1.0e-12, 1.0e-7, 1.0e-3


def read_rec(f):
    n = struct.unpack("<i", f.read(4))[0]
    payload = f.read(n)
    n2 = struct.unpack("<i", f.read(4))[0]
    assert n == n2, "record marker mismatch"
    return payload


def read_rle_array(f, ntot):
    n, nrun = struct.unpack("<2q", read_rec(f))
    assert n == ntot, "unexpected array size %d != %d" % (n, ntot)
    runs = struct.unpack("<%dq" % (2 * nrun), read_rec(f))
    packed_raw = read_rec(f)
    packed = struct.unpack("<%dd" % (len(packed_raw) // 8), packed_raw)
    out = [0.0] * n
    i = k = 0
    for r in range(nrun):
        i += runs[2 * r]
        lit = runs[2 * r + 1]
        out[i:i + lit] = packed[k:k + lit]
        i += lit
        k += lit
    return out


def grid(a, nx):
    return [a[j * nx:(j + 1) * nx] for j in range(len(a) // nx)]


def load_state(savedir, nx, ny):
    """state.dat の h, z, sd, hs(倍精度。並びは h, z, hrs, hg, sd, hs)"""
    with open(savedir + "/state.dat", "rb") as f:
        h = read_rle_array(f, nx * ny)
        z = read_rle_array(f, nx * ny)
        read_rle_array(f, nx * ny)
        read_rle_array(f, nx * ny)
        sd = read_rle_array(f, nx * ny)
        hs = read_rle_array(f, nx * ny)
    return grid(h, nx), grid(z, nx), grid(sd, nx), grid(hs, nx)


def load_ri(savedir, nx, ny):
    with open(savedir + "/geomorph_rockinc.dat", "rb") as f:
        return grid(read_rle_array(f, nx * ny), nx)


def report(label, ok, detail):
    print("%s: %s : %s" % (label, detail, "PASS" if ok else "FAIL"))
    return ok


def ed0(h, hs, zu, zd, fr):
    """裸岩の低下速度 E_d0(m_geomorph_debris のパス 1 と同じ式。流向 = 南向きの河床勾配)"""
    ht = h + max(hs, 0.0)
    c = max(hs, 0.0) / ht
    tan = (zu - zd) / (2.0 * DX)
    ge = G / (1.0 + tan ** 2)
    taud = RHO * (1.0 + SGRAV * c) * ge * ht * tan
    return fr * KD * (taud / TAUCD - 1.0) ** MD if taud > TAUCD else 0.0, taud, c


def check_db1():
    """DB1: 全更新が同じ定常の水理を見るので、各セルで e^{H/H*} − e^{H0/H*} = E_d0 T/H*"""
    h, z, sd, hs = load_state("save_db1", NX, NY)
    _, _, sdb, _ = load_state("save_db1_dtg", NX, NY)
    ri = load_ri("save_db1", NX, NY)
    i = IC - 1
    emax = dmax = 0.0
    taus, cs, nzero, rizero = [], [], 0, 0.0
    for j in range(J1 - 1, J2):
        fr = fr1(IC, j + 1)
        e, taud, c = ed0(h[j][i], hs[j][i], z[j - 1][i], z[j + 1][i], fr)
        taus.append(taud)
        cs.append(c)
        h0 = sd1(IC, j + 1)
        lhs = math.exp(sd[j][i] / HS) - math.exp(h0 / HS)
        rhs = e * T1 / HS
        if fr == 0.0:
            nzero += 1
            rizero = max(rizero, abs(ri[j][i]), abs(sd[j][i] - h0))
            continue
        emax = max(emax, abs(lhs / rhs - 1.0))
        dmax = max(dmax, abs(sdb[j][i] - sd[j][i]) / max(sd[j][i], 1e-30))
    ok = report("(DB1-1) 解析解", emax < TOL_DB1,
                "行 %d〜%d の max|(e^{H/H*} − e^{H0/H*}) / (E_d0 T/H*) − 1| = %.2e (tol %.0e)。"
                "τ_d = %.1f〜%.1f Pa、C = %.6f〜%.6f"
                % (J1, J2, emax, TOL_DB1, min(taus), max(taus), min(cs), max(cs)))
    ok = report("(DB1-2) 更新間隔", dmax < TOL_SAME,
                "dt_geomorph 100 s と 200 s の sd の max 相対差 = %.2e (tol %.0e)" % (dmax, TOL_SAME)) and ok
    ok = report("(DB1-3) 倍率 0", rizero == 0.0 and nzero > 0,
                "倍率 0 の %d 行の max(|Ri|, |sd − sd0|) = %.2e m" % (nzero, rizero)) and ok
    zch = max(abs(z[j][i] - (10.0 + 0.2 * (NY - j - 0.5) * DX)) for j in range(NY))
    ok = report("(DB1-4) z 不変", zch < 1e-12,
                "水路の max|z − z0| = %.2e m(生成物は可動層に入り z を動かさない)" % zch) and ok
    return ok


def check_db3():
    """DB3: 濃度 C < db_cmin、流速 |V| < db_vstop の構成では、どのセルも削れない"""
    ok = True
    for cfg, what in (("db3_cmin", "C = 1/3 < db_cmin = 0.5"), ("db3_vstop", "|V| < db_vstop = 10 m/s")):
        ri = load_ri("save_" + cfg, NX, NY)
        _, _, sd, _ = load_state("save_" + cfg, NX, NY)
        rmax = max(abs(ri[j][i]) for j in range(NY) for i in range(NX))
        smax = max(abs(sd[j][i] - sd1(i + 1, j + 1)) for j in range(NY) for i in range(NX))
        ok = report("(DB3) " + cfg, rmax == 0.0 and smax == 0.0,
                    "%s: max|Ri| = %.2e m、max|sd − sd0| = %.2e m" % (what, rmax, smax)) and ok
    return ok


def ledger(logfile):
    """dispose の台帳行(土石流が削った岩盤のかさ体積)を読む(ファイル中の最後の行)"""
    vd = None
    pat = re.compile(r"rock erosion by debris flows: eroded\s+(\S+) m3")
    for line in open(logfile, encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if m:
            vd = float(m.group(1))
    if vd is None:
        sys.exit("FAIL: ledger line not found in %s" % logfile)
    return vd


def check_db2(logfile):
    """DB2: 剥離は z を変えないので全固体は不変、可動層の固体が (1 − λ) × 岩盤起源のかさ体積だけ増える"""
    h, z, sd, hs = load_state("save_db2", NX2, NY2)
    ri = load_ri("save_db2", NX2, NY2)
    vd = ledger(logfile)
    area = DX2 * DX2
    cells = [(j, i) for j in range(NY2) for i in range(NX2)]
    shs = sum(max(hs[j][i], 0.0) for j, i in cells) * area
    sdz = sum(z[j][i] - z2(i + 1, j + 1) for j, i in cells) * area
    sdsd = sum(sd[j][i] - sd2(i + 1, j + 1) for j, i in cells) * area
    sri = sum(ri[j][i] for j, i in cells) * area
    tot = shs + (1.0 - LAM) * sdz
    mob = shs + (1.0 - LAM) * sdsd
    ok = report("(DB2-1) 全固体", abs(tot) < TOL_SUM * max(1.0, shs),
                "Σh_s A + (1 − λ)Σ(z − z0)A = %.3e m3 (tol %.0e)" % (tot, TOL_SUM))
    ok = report("(DB2-2) 可動層の固体", abs(mob / ((1.0 - LAM) * vd) - 1.0) < TOL_LEDGER,
                "Σh_s A + (1 − λ)Σ(sd − sd0)A = %.9e m3、(1 − λ) × 台帳 %.9e m3 (相対 tol %.0e)"
                % (mob, (1.0 - LAM) * vd, TOL_LEDGER)) and ok
    rmax = max(abs((sd[j][i] - sd2(i + 1, j + 1)) - (z[j][i] - z2(i + 1, j + 1)) - ri[j][i]) for j, i in cells)
    ok = report("(DB2-3) 累積下刻", rmax < TOL_RI and abs(sri / vd - 1.0) < TOL_LEDGER,
                "max|(sd − sd0) − (z − z0) − Ri| = %.2e m (tol %.0e)、Σ Ri A / 台帳 − 1 = %.2e"
                % (rmax, TOL_RI, sri / vd - 1.0)) and ok
    dzmax = max(abs(z[j][i] - z2(i + 1, j + 1)) for j, i in cells)
    ok = report("(DB2-4) 活性", vd > MIN_V and dzmax > 1e-3,
                "岩盤起源 %.3e m3 (min %.0e)、E-D の max|z − z0| = %.3e m、max Ri = %.3e m"
                % (vd, MIN_V, dzmax, max(ri[j][i] for j, i in cells))) and ok
    return ok


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "db1":
        ok = check_db1()
    elif mode == "db3":
        ok = check_db3()
    elif mode == "db2":
        ok = check_db2(sys.argv[2])
    else:
        sys.exit("usage: Check_dbrock.py db1 | db3 | db2 LOG")
    print("== dbrock %s: %s ==" % (mode, "PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)
