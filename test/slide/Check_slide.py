#!/usr/bin/env python3
# slide(瞬時流動化 f_release / 斜面安定 f_slide)疎通・保存則検定
#   save/state.dat から h, z, sd, hs を読み、モードに応じて検定する。
#   release モード(param.txt。崩壊深 D=1m を i∈[5,15], j∈[5,16] に与える):
#     (1) 固体総量保存: |Σhs + (1-λ)Σ(z-z0)| < TOL_SUM
#     (2) 共動更新恒等: max|(sd - sd0) - (z - z0)| < TOL_SD
#     (3) 水収支: |Σh − λ・relsat・ΣD| < TOL_W(水は放出間隙水のみ)
#     (4) 活性確認: 崩壊域の掘削(min dz < -0.5)と域外への移動
#   fslide モード(param_fs.txt。sd0=0.5):
#     (1) 固体総量保存(許容 TOL_SUM_FS: 多数回転換の丸め累積)
#     (2) 共動更新恒等
#     (4) 活性確認: 斜面部に sd ≈ 0(崩壊発生)のセルが存在
#   wet モード(param_wet.txt。構成1 + 地下水計算 + f_dbwet=3 + 初期地下水 gw_sat0。
#   developer.md §28.17):
#     (1) 固体総量保存、(2) 共動更新恒等
#     (3) 水台帳: |Σh + Σhg + w_r・Σ(z−z0) − gw_sat0・sy0・Σsd0 − 保持水の不足| < TOL_W
#         (w_r = λ − sy0。保持水の不足は、堆積のとき地表水・地下貯留から取れなかった分で、
#         画面出力の終了時の表示から読む)
#     (4) 活性確認: 崩壊域の掘削と域外への移動
#     (5) 保持水の授受の活性: |w_r・Σ(z−z0)| > MIN_WRET(f_dbwet=2 の台帳では閉じない)。
#         gw_sat0 = 0(乾いた土層)の変種では、保持水の不足 > 0(不足の台帳が働く)
#   z0 は slope_break(tanθ=0.4, 遷緩点 x=30m)と対で保守する。
#   使い方: Check_slide.py <savedir> <release|fslide>
#           Check_slide.py <savedir> wet <画面出力のファイル> <gw_sat0>
import sys, struct

NX, NY = 60, 20
DX = 1.0
ST, XB = 0.4, 30.0
PORO = 0.4
TOL_SUM, TOL_SD, TOL_W = 1.0e-9, 1.0e-10, 1.0e-9
TOL_SUM_FS = 1.0e-8
SY0, MIN_WRET = 0.2, 1.0e-6     # wet モード: sy0(param_wet と対)、|w_r Σdz| の下限
SHORTFALL_KEY = "retained pore water shortfall in deposition (f_dbwet=3)"


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


def z0_of(idx):
    i = idx % NX + 1
    x = (i - 0.5) * DX
    return ST * (XB - x) if x < XB else 0.0


savedir, mode = sys.argv[1], sys.argv[2]
resultdir = sys.argv[3] if len(sys.argv) > 3 else ""
SD0 = 5.0 if mode in ("release", "wet") else 0.5


def load_matrix(fn):
    return [[float(x) for x in line.split()] for line in open(fn) if line.split()]
with open(savedir + "/state.dat", "rb") as f:
    ntot = NX * NY
    h = read_rle_array(f, ntot)
    z = read_rle_array(f, ntot)
    hrs = read_rle_array(f, ntot)
    hg = read_rle_array(f, ntot)
    sd = read_rle_array(f, ntot)
    hs = read_rle_array(f, ntot)

dz = [zi - z0_of(idx) for idx, zi in enumerate(z)]
solids = sum(hs) + (1.0 - PORO) * sum(dz)
max_ident = max(abs((sdi - SD0) - d) for sdi, d in zip(sd, dz))

ok = True
if mode == "release":
    # 崩壊域(i∈[5,15], j∈[5,16]。Run.sh の dbinit 生成と対)D=1m
    ncell = 11 * 12
    wexp = PORO * 1.0 * 1.0 * ncell     # λ・relsat・ΣD
    wsum = sum(h) + sum(hg)
    src_min = min(dz[idx] for idx in range(ntot)
                  if 5 <= idx % NX + 1 <= 15 and 5 <= idx // NX + 1 <= 16)
    out_dep = max(dz[idx] for idx in range(ntot) if idx % NX + 1 >= 16)
    ok1 = abs(solids) < TOL_SUM
    ok2 = max_ident < TOL_SD
    ok3 = abs(wsum - wexp) < TOL_W
    ok4 = src_min < -0.5 and out_dep > 1.0e-3
    print("(1) 固体総量保存: %.3e (tol %.0e) : %s" % (solids, TOL_SUM, "PASS" if ok1 else "FAIL"))
    print("(2) 共動更新    : %.3e (tol %.0e) : %s" % (max_ident, TOL_SD, "PASS" if ok2 else "FAIL"))
    print("(3) 水収支      : Σh+Σhg = %.6f (期待 %.6f) : %s" % (wsum, wexp, "PASS" if ok3 else "FAIL"))
    print("(4) 活性確認    : 崩壊域 min dz = %.3f, 域外堆積 max dz = %.3e : %s"
          % (src_min, out_dep, "PASS" if ok4 else "FAIL"))
    ok = ok1 and ok2 and ok3 and ok4
elif mode == "wet":
    # 構成4: 飽和(または乾いた)土層の瞬時流動化と保持水の授受(崩壊域は release と同じ)
    sat0 = float(sys.argv[4])
    short = None
    with open(sys.argv[3], encoding="utf-8", errors="replace") as flog:
        for ln in flog:
            if SHORTFALL_KEY in ln:
                short = float(ln.split(SHORTFALL_KEY)[1].split()[0])
    if short is None:
        print("(3) 水台帳      : 画面出力に保持水の不足の表示がない : FAIL")
        sys.exit(1)
    wret = (PORO - SY0) * sum(dz)
    hg0 = sat0 * SY0 * SD0 * ntot
    wres = sum(h) + sum(hg) + wret - hg0 - short
    src_min = min(dz[idx] for idx in range(ntot)
                  if 5 <= idx % NX + 1 <= 15 and 5 <= idx // NX + 1 <= 16)
    out_dep = max(dz[idx] for idx in range(ntot) if idx % NX + 1 >= 16)
    ok1 = abs(solids) < TOL_SUM
    ok2 = max_ident < TOL_SD
    ok3 = abs(wres) < TOL_W
    ok4 = src_min < -0.5 and out_dep > 1.0e-3
    ok5 = abs(wret) > MIN_WRET and (short > 0.0 if sat0 == 0.0 else True)
    print("(1) 固体総量保存: %.3e (tol %.0e) : %s" % (solids, TOL_SUM, "PASS" if ok1 else "FAIL"))
    print("(2) 共動更新    : %.3e (tol %.0e) : %s" % (max_ident, TOL_SD, "PASS" if ok2 else "FAIL"))
    print("(3) 水台帳      : Σh+Σhg+w_r・Σdz−hg0−不足 = %.3e (tol %.0e。hg0 = %.3f、不足 = %.3e) : %s"
          % (wres, TOL_W, hg0, short, "PASS" if ok3 else "FAIL"))
    print("(4) 活性確認    : 崩壊域 min dz = %.3f, 域外堆積 max dz = %.3e : %s"
          % (src_min, out_dep, "PASS" if ok4 else "FAIL"))
    print("(5) 保持水の授受: |w_r・Σdz| = %.3e (> %.0e)%s : %s"
          % (abs(wret), MIN_WRET, "、不足 > 0" if sat0 == 0.0 else "", "PASS" if ok5 else "FAIL"))
    ok = ok1 and ok2 and ok3 and ok4 and ok5
elif mode == "fsdiag":
    # f_slide=2(判定のみ。§28.9): 流動化しない(z・sd・hs 不変)+
    # Fs9999(期間最小)が斜面部で危険(<1)を検出している
    maxdz = max(abs(d) for d in dz)
    maxds = max(abs(sdi - SD0) for sdi in sd)
    maxhs = max(hs)
    ok1 = maxdz == 0.0 and maxds == 0.0 and maxhs == 0.0
    print("(1) 無流動化    : max|dz| = %.3e, max|sd-sd0| = %.3e, max hs = %.3e : %s"
          % (maxdz, maxds, maxhs, "PASS" if ok1 else "FAIL"))
    fsm = [x for row in load_matrix(resultdir + "/Fs9999.txt") for x in row]
    fse = [x for x in fsm if x >= 0.0]
    nsent = sum(1 for x in fsm if x < 0.0)
    ok2 = len(fse) > 0 and min(fse) < 1.0 and nsent > 0
    print("(2) Fs 診断     : 評価 %d セル min Fs = %.3f(<1 = 危険域検出), "
          "番兵 %d セル : %s" % (len(fse), min(fse) if fse else -1.0, nsent,
                                 "PASS" if ok2 else "FAIL"))
    ok = ok1 and ok2
else:
    slid = min(sd[idx] for idx in range(ntot) if idx % NX + 1 < 30)
    ok1 = abs(solids) < TOL_SUM_FS
    ok2 = max_ident < TOL_SD
    ok4 = slid < 1.0e-12
    print("(1) 固体総量保存: %.3e (tol %.0e) : %s" % (solids, TOL_SUM_FS, "PASS" if ok1 else "FAIL"))
    print("(2) 共動更新    : %.3e (tol %.0e) : %s" % (max_ident, TOL_SD, "PASS" if ok2 else "FAIL"))
    print("(4) 活性確認    : 斜面部 min sd = %.3e(0 = 崩壊発生): %s"
          % (slid, "PASS" if ok4 else "FAIL"))
    ok = ok1 and ok2 and ok4
    if ok and resultdir:
        # 危険度出力(§28.9): Fs9999 の危険検出、D9999 >= H9999(混合 >= 水)
        fsm = [x for row in load_matrix(resultdir + "/Fs9999.txt") for x in row]
        fse = [x for x in fsm if x >= 0.0]
        dmax = [x for row in load_matrix(resultdir + "/D9999.txt") for x in row]
        hmax = [x for row in load_matrix(resultdir + "/H9999.txt") for x in row]
        dneg = min(a - b for a, b in zip(dmax, hmax))
        ok5 = len(fse) > 0 and min(fse) < 1.0 and dneg >= 0.0
        print("(5) 危険度出力  : min Fs9999 = %.3f(<1), min(D9999-H9999) = %.3e(>=0) : %s"
              % (min(fse) if fse else -1.0, dneg, "PASS" if ok5 else "FAIL"))
        ok = ok and ok5

print("== slide(%s)検定: %s ==" % (mode, "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
