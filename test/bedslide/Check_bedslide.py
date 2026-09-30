#!/usr/bin/env python3
# bedslide(動く底層)検定
#   使い方: Check_bedslide.py <bench|tsunami>
#   bench  : 構成1(格子沿い)と構成2(45° 回転)の save_bench / save_rot
#     (1) 台帳: Σ(z−z0) = 0(内部移転)、Σ(sd−sd0) = 0、岩盤面 z−sd 不変
#     (2) 速度: 内部セル(壁の境界層の外・断面付近)の Vb 出力が
#         V = √(ξ D (tanθ−μ)) に相対 TOL_VB 以内(格子沿い・45° とも。鋭い検出器)
#     (3) 輸送: 断面(x=XS / u=US)を通過した体積 Σ_{下流}(z−z0) を
#         D・L_sec・tt で割った速度が V に相対 TOL_Q 以内(粗い検出器。
#         45° の総流出の正規化誤り(√2 倍)はこれで捕まる)
#   tsunami: 構成3 の result
#     (1) 台帳(同上)、(2) Σh 不変、(3) 平坦湖底への堆積、(4) 造波、
#     (5) 発火体積 = 停止 + 移動中(Screen_tsunami.log)
#   plunge : 構成4(混合体→引き渡し→底層)result_plunge と対照 result_mix
#     (1) 固体台帳: Σhs + (1−λ)Σ(z−z0) = 0(save の倍精度。hb は z の内数)
#     (2) 水の台帳: Σh − Σh0 = 疑似間隙水 λ·relsat·ΣD(f_dbwet=0 では引き渡しで h 不変)
#     (3) 引き渡し体積 > 0(Screen_plunge.log)、平坦湖底(x≥300)へ堆積 > MIN_DEP
#     (4) 対照(混合体のみ)は平坦湖底に達しない(堆積 < MIN_DEP)
#   出力は分布テキスト(Z0000 / Z9998・Sd・Hb・H・E の最終フレーム)を読む
import sys, math, re, struct

ST = 0.4
XI, MU, BD = 200.0, 0.1, 1.0            # param_bench / param_rot と対
TT_BENCH = 1.0
XS, US = 55.0, 45.0                     # 通過体積を測る断面(格子沿い x / 回転 u)
TOL_SUM = 1.0e-9                        # 台帳(m·cell)
TOL_VB = 0.005                          # 内部セルの速度 Vb の相対許容(鋭い検出器)
TOL_Q = 0.10                            # 断面通過速度の相対許容(壁沿いの行・列は
                                        #   斜め配分の相手を欠き通過量が減る = 8 方向
                                        #   配分の性質。格子沿いは 2・ld/ny = 2.9%、
                                        #   45° は両端の壁セル+階段断面の幾何 ≈ 5〜8%)
NX3, NY3, DX3 = 120, 40, 5.0            # param.txt と対
XFLAT = 300.0
MIN_DEP, MIN_ETA = 0.05, 0.2


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


def load_save(savedir, nx, ny, with_hs=False):
    """state.dat(h, z, hrs, hg, sd, hs)と geomorph_bedslide.dat(hb)を倍精度で読む"""
    ntot = nx * ny
    with open(savedir + "/state.dat", "rb") as f:
        h = read_rle_array(f, ntot)
        z = read_rle_array(f, ntot)
        read_rle_array(f, ntot)     # hrs
        read_rle_array(f, ntot)     # hg
        sd = read_rle_array(f, ntot)
        hs = read_rle_array(f, ntot)
    try:
        with open(savedir + "/geomorph_bedslide.dat", "rb") as f:
            hb = read_rle_array(f, ntot)
    except FileNotFoundError:
        hb = [0.0] * ntot
    if with_hs:
        return h, z, sd, hb, hs
    return h, z, sd, hb


def read_mat(path):
    with open(path) as f:
        return [[float(v) for v in line.split()] for line in f if line.strip()]


def last_frame(rdir):
    last = None
    with open(rdir + "/FILENUMBER.csv") as f:
        for line in f:
            if line.startswith("#"):
                continue
            k = int(line.split(",")[0])
            if k < 9000:
                last = k
    return "%04d" % last


def load(rdir):
    tag = last_frame(rdir)
    d = {}
    d["z0"] = read_mat(rdir + "/Z0000.txt")
    d["sd0"] = read_mat(rdir + "/Sd0000.txt")
    for name in ("Z", "Sd", "Hb", "H"):
        d[name] = read_mat(rdir + "/%s%s.txt" % (name, tag))
    try:
        d["E"] = read_mat(rdir + "/E%s.txt" % tag)
        d["E0"] = read_mat(rdir + "/E0000.txt")
        d["H0"] = read_mat(rdir + "/H0000.txt")
    except FileNotFoundError:
        pass
    return d


def ledger(savedir, nx, ny, z0_of, sd0):
    """台帳は save の倍精度で検定する(分布テキストは 4 桁丸めで和が閉じない)"""
    h, z, sd, hb = load_save(savedir, nx, ny)
    ntot = nx * ny
    dz = sum(z[idx] - z0_of(idx) for idx in range(ntot))
    dsd = sum(sd[idx] - sd0 for idx in range(ntot))
    rock = max(abs((z[idx] - sd[idx]) - (z0_of(idx) - sd0)) for idx in range(ntot))
    ok = abs(dz) < TOL_SUM and abs(dsd) < TOL_SUM and rock < TOL_SUM
    print("(1) 台帳    : sum(dz) = %.2e, sum(dsd) = %.2e, max|d(z-sd)| = %.2e (tol %.0e) : %s"
          % (dz, dsd, rock, TOL_SUM, "PASS" if ok else "FAIL"))
    return ok


def centroid(mat, dx):
    ny, nx = len(mat), len(mat[0])
    m = sx = sy = 0.0
    for j in range(ny):
        for i in range(nx):
            v = mat[j][i]
            if v <= 0.0:
                continue
            m += v
            sx += v * (i + 0.5) * dx
            sy += v * (j + 0.5) * dx
    return m, sx / m, sy / m


mode = sys.argv[1]
ok = True
if mode == "bench":
    vana = math.sqrt(XI * BD * (ST - MU))
    disp = {}
    for cfg in ("bench", "rot"):
        if cfg == "bench":
            nx, ny, zf = 100, 20, "zbench.txt"
        else:
            nx, ny, zf = 60, 60, "zrot.txt"
        zin = read_mat(zf)
        z0_of = lambda idx: zin[idx // nx][idx % nx]
        ok = ledger("save_" + cfg, nx, ny, z0_of, 3.0) and ok
        h, z, sd, hb = load_save("save_" + cfg, nx, ny)
        gain = 0.0
        for idx in range(nx * ny):
            x = (idx % nx + 0.5) * 1.0
            y = (idx // nx + 0.5) * 1.0
            beyond = (x >= XS) if cfg == "bench" else ((x + y) / math.sqrt(2.0) >= US)
            if beyond:
                gain += z[idx] - z0_of(idx)
        if cfg == "bench":
            lsec = ny * 1.0
        else:
            lsec = (2.0 * nx - math.sqrt(2.0) * US) * math.sqrt(2.0)   # x+y=√2·US の正方形内の長さ
        vnum = gain / (BD * lsec * TT_BENCH)
        disp[cfg] = vnum
        # (2) 内部セルの速度 Vb
        vb = read_mat(("result_bench" if cfg == "bench" else "result_rot") + "/Vb0001.txt")
        vals = []
        for idx in range(nx * ny):
            i, j = idx % nx, idx // nx
            x, y = (i + 0.5), (j + 0.5)
            # 壁沿いには 8 方向配分の境界層(壁セルは斜め方向の相手を欠き
            # 通過量が減る → 厚さが変わり表面勾配が変わる)が内側へ広がる。
            # 45° の壁では 1 s で ~20 セル、流れに平行な壁では行内で閉じる
            margin = 5 if cfg == "bench" else 25
            if min(i, nx - 1 - i, j, ny - 1 - j) < margin:
                continue
            u = (x + y) / math.sqrt(2.0)
            if (cfg == "bench" and 45.0 <= x <= 55.0) or (cfg == "rot" and 40.0 <= u <= 50.0):
                vals.append(vb[j][i])
        vmin, vmax_ = min(vals), max(vals)
        errv = max(abs(vmin - vana), abs(vmax_ - vana)) / vana
        okvb = errv < TOL_VB
        ok = okvb and ok
        print("(2) 速度[%s]: 内部 %d セルの Vb = %.4f..%.4f m/s vs V = %.4f m/s (err %.2f%%, tol %.1f%%) : %s"
              % (cfg, len(vals), vmin, vmax_, vana, 100 * errv, 100 * TOL_VB, "PASS" if okvb else "FAIL"))
        err = abs(vnum - vana) / vana
        okv = err < TOL_Q
        ok = okv and ok
        print("(3) 輸送[%s]: 断面通過体積 %.2f m3 / (D・L=%.1f m・%.1f s) = %.3f m/s vs V = %.3f m/s"
              " (err %.2f%%, tol %.0f%%) : %s"
              % (cfg, gain, lsec, TT_BENCH, vnum, vana, 100 * err, 100 * TOL_Q, "PASS" if okv else "FAIL"))
    diff = abs(disp["rot"] - disp["bench"]) / disp["bench"]
    print("    (参考)45° 回転 / 格子沿い の通過速度 = %.3f / %.3f m/s (差 %.2f%%)"
          % (disp["rot"], disp["bench"], 100 * diff))
elif mode == "plunge":
    PORO, RELSAT = 0.4, 0.2                  # param_plunge / param_mix と対
    zin = read_mat("z.txt"); D = read_mat("db.txt")
    z0_of = lambda idx: zin[idx // NX3][idx % NX3]
    ntot = NX3 * NY3
    flat = [idx for idx in range(ntot) if (idx % NX3 + 0.5) * DX3 >= XFLAT]
    dep = {}
    for cfg in ("plunge", "mix"):
        h, z, sd, hb, hs = load_save("save_" + cfg, NX3, NY3, with_hs=True)
        sres = sum(hs) + (1.0 - PORO) * sum(z[idx] - z0_of(idx) for idx in range(ntot))
        rock = max(abs((z[idx] - sd[idx]) - (z0_of(idx) - 12.0)) for idx in range(ntot))
        ok1 = abs(sres) < TOL_SUM and rock < TOL_SUM
        ok = ok1 and ok
        print("(1) 固体台帳[%s]: sum(hs)+(1-λ)sum(dz) = %.2e, max|d(z-sd)| = %.2e (tol %.0e) : %s"
              % (cfg, sres, rock, TOL_SUM, "PASS" if ok1 else "FAIL"))
        h0 = [max(0.0 - z0_of(idx), 0.0) for idx in range(ntot)]
        wres = sum(h) - sum(h0) - PORO * RELSAT * sum(map(sum, D))
        ok2 = abs(wres) < TOL_SUM * 1.0e3
        ok = ok2 and ok
        print("(2) 水の台帳[%s]: sum(h) - sum(h0) - λ·relsat·ΣD = %.2e m*cell : %s"
              % (cfg, wres, "PASS" if ok2 else "FAIL"))
        dep[cfg] = max(z[idx] - z0_of(idx) for idx in flat)
    txt = open("Screen_plunge.log").read()
    mm = re.search(r"plunged\s+([0-9.E+-]+) m3", txt)
    vpl = float(mm.group(1)) if mm else -1.0
    vbulk = sum(map(sum, D)) * DX3 * DX3
    ok3 = 0.0 < vpl <= vbulk * (1.0 + 1.0e-3) and dep["plunge"] > MIN_DEP
    ok = ok3 and ok
    print("(3) 引き渡し: plunged %.0f m3 (放出かさ体積 %.0f)、平坦湖底 max dz = %.3f m (tol %.2f) : %s"
          % (vpl, vbulk, dep["plunge"], MIN_DEP, "PASS" if ok3 else "FAIL"))
    ok4 = dep["mix"] < MIN_DEP
    ok = ok4 and ok
    print("(4) 対照(混合体のみ): 平坦湖底 max dz = %.3f m (< %.2f で湖底に達しない) : %s"
          % (dep["mix"], MIN_DEP, "PASS" if ok4 else "FAIL"))
else:
    d = load("result")
    z0_of = lambda idx: max(ST * (200.0 - (idx % NX3 + 0.5) * DX3), -40.0)
    ok = ledger("save", NX3, NY3, z0_of, 12.0) and ok
    h0, h = d["H0"], d["H"]
    dh = sum(h[j][i] - h0[j][i] for j in range(NY3) for i in range(NX3))
    ok2 = abs(dh) < 1.0e-6 * sum(map(sum, h0))
    print("(2) 水の台帳: sum(h) - sum(h0) = %.2e m*cell : %s" % (dh, "PASS" if ok2 else "FAIL"))
    flat = [(j, i) for j in range(NY3) for i in range(NX3) if (i + 0.5) * DX3 >= XFLAT]
    dep = max(d["Z"][j][i] - d["z0"][j][i] for j, i in flat)
    ok3 = dep > MIN_DEP
    print("(3) 水中走行: 平坦湖底(x>=%.0f) の max dz = %.3f m (tol %.2f) : %s"
          % (XFLAT, dep, MIN_DEP, "PASS" if ok3 else "FAIL"))
    # 造波: 平坦湖底部の水面の最大(全出力フレーム)
    etamax = -1.0e9
    with open("result/FILENUMBER.csv") as f:
        for line in f:
            if line.startswith("#"):
                continue
            k = int(line.split(",")[0])
            if k >= 9000:
                continue
            e = read_mat("result/E%04d.txt" % k)
            hh = read_mat("result/H%04d.txt" % k)
            etamax = max(etamax, max(e[j][i] for j, i in flat if hh[j][i] > 0.01))
    ok4 = etamax > MIN_ETA
    print("(4) 造波    : 平坦湖底部の水面最大 = %.3f m (tol %.2f) : %s"
          % (etamax, MIN_ETA, "PASS" if ok4 else "FAIL"))
    txt = open("Screen_tsunami.log").read()
    mm = re.search(r"bedslide released\s+([0-9.E+-]+) m3, plunged\s+[0-9.E+-]+ m3, stopped\s+([0-9.E+-]+) m3, still moving\s+([0-9.E+-]+)", txt)
    ok5 = False
    if mm:
        rel, stp, mov = (float(v) for v in mm.groups())
        vdb = sum(map(sum, read_mat("db.txt"))) * DX3 * DX3
        # Screen の台帳は 5 桁表示(es12.4)なので相対 1e-4 で照合する
        ok5 = abs(rel - vdb) < 2.0e-4 * vdb and abs(rel - stp - mov) < 2.0e-4 * vdb
        print("(5) 発火台帳: released %.1f (与件 %.1f) = stopped %.1f + moving %.1f m3 : %s"
              % (rel, vdb, stp, mov, "PASS" if ok5 else "FAIL"))
    else:
        print("(5) 発火台帳: Screen_tsunami.log に台帳行がない : FAIL")
    ok = ok and ok2 and ok3 and ok4 and ok5

print("== bedslide 検定(%s): %s ==" % (mode, "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
