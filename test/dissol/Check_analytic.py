#!/usr/bin/env python3
# dissol の解析解比較(developer.md §86、docs/karst_plan.md §3)
#   bil(float32)の終了時出力 Z9998(・Sd9998・Hgc0003)を読み、各構成の
#   解析値と内部セルで比較する。
#   使い方: Check_analytic.py {a|b|c|d} <resultdir> [rtol]
#     a: result      Δz = -3e-4 m、Δsd = +1e-4 m(全セル)
#     b: result_sink Δz(中心 5x5) = -0.2 x Hgc0003、Δz(外側) = 0
#     c: result_rain Δz = -1.2e-3 m(全セル)
#     d: result_lat  中央 3x3 の窪みの溶解能 W = 4e-4 m を、床 (1-p)W と
#                    周囲 16 セルの壁 pW L_k/ΣL に配分(karst_plan §2.5。p = 0.4)
#     e: result_lata 同上を降雨源(全セル W)+ 自動配分 p = hΣL/(hΣL + Δx²)で(相対 1e-4)
#   終了コード: 0 = PASS、1 = FAIL
import sys, numpy as np

NX = NY = 21
KD = 100.0e-3 / 2500.0           # c_eq/ρ_r (m/m)。param.txt と対で保守する

def read_bil(fn):
    a = np.fromfile(fn, dtype="<f4")
    if a.size != NX * NY:
        raise SystemExit("FAIL: unexpected size in " + fn)
    return a.reshape(NY, NX).astype(np.float64)

def check(label, num, ana, rtol, atol=0.0):
    err = np.abs(num - ana)
    tol = atol + rtol * np.abs(ana)
    ok = bool(np.all(err <= tol))
    print("%-28s max|num - ana| = %.3e  (ana = %.6e)  %s"
          % (label, float(err.max()), float(np.abs(ana).max()), "PASS" if ok else "FAIL"))
    return ok

case = sys.argv[1]
rdir = sys.argv[2]
rtol = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0e-6
ok = True
z = read_bil(rdir + "/Z9998.bil")
if case == "a":
    # 浸透 1e-3 m × k_d × morfac 1e4 = 4e-4 m、残渣率 0.25
    w = KD * 1.0e-3 * 1.0e4
    sd = read_bil(rdir + "/Sd9998.bil")
    ok &= check("A: z  (z0 - 0.75 w)", z, np.full_like(z, -0.75 * w), rtol)
    ok &= check("A: sd (sd0 + 0.25 w)", sd, np.full_like(sd, 1.0 + 0.25 * w), rtol)
elif case == "b":
    hgc = read_bil(rdir + "/Hgc0003.bil")
    c = NX // 2
    inner = np.zeros((NY, NX), dtype=bool)
    inner[c-2:c+3, c-2:c+3] = True
    ana = np.where(inner, -KD * 0.5 * hgc * 1.0e4, 0.0)
    ok &= check("B: z (center 5x5)", z[inner], ana[inner], rtol)
    ok &= check("B: z (outside = z0)", z[~inner], ana[~inner], rtol, atol=1.0e-12)
elif case in ("d", "e"):
    # 配分式の独立実装: 窪み 9 セル(z = -1、水位 -0.5)、壁 = 8 近傍で z > -0.5
    auto = (case == "e")
    p_lat = 0.4
    DX = 2.0
    if auto:
        rtol = max(rtol, 1.0e-4)                # 降雨で h が 1e-5 m 増える分の p の変化
    W = KD * 1.0e-3 * 1.0e4                     # 窪みセル 1 個の総溶解能 (m)(e: 全セル)
    WD = 2.0 / (2.0 + np.sqrt(2.0))             # 斜め接触幅の比
    zpit = np.loadtxt("data_dissol/zpit.txt")
    c = NX // 2
    wet = np.zeros((NY, NX), dtype=bool)
    wet[c-1:c+2, c-1:c+2] = True
    ew = -0.5
    dz = np.zeros((NY, NX))
    for jw in range(NY):
        for iw in range(NX):
            if not wet[jw, iw]:
                continue
            walls = []
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    jn, i_n = jw + dj, iw + di
                    if 0 <= jn < NY and 0 <= i_n < NX and zpit[jn, i_n] > ew:
                        walls.append((jn, i_n, 1.0 if di == 0 or dj == 0 else WD))
            if walls:
                tot = sum(w for _, _, w in walls)
                if auto:
                    p_lat = 0.5 * tot * DX / (0.5 * tot * DX + DX * DX)
                dz[jw, iw] += (1.0 - p_lat) * W
                for jn, i_n, w in walls:
                    dz[jn, i_n] += p_lat * W * w / tot
            else:
                dz[jw, iw] += W
    if auto:
        dz[~wet] += W                           # 乾いたセルも降雨源で床が W 下がる
    ana = zpit - dz
    ok &= check(case.upper() + ": z (floor + walls)", z[dz > 0], ana[dz > 0], rtol)
    if (dz == 0).any():
        ok &= check(case.upper() + ": z (untouched = z0)", z[dz == 0], ana[dz == 0], rtol, atol=1.0e-12)
    tot_num = float((zpit - z).sum())
    tot_ana = (NX * NY if auto else 9.0) * W
    # 総和は float32 の z(≈ −1)の丸め 6e-8 × 25 セルが乗るため許容 1e-3(相対)
    tol_sum = 1.0e-3
    print("%s: total dissolved thickness = %.6e m (sum W = %.6e m, rtol %.0e)  %s"
          % (case.upper(), tot_num, tot_ana, tol_sum, "PASS" if abs(tot_num - tot_ana) <= tol_sum * tot_ana else "FAIL"))
    ok &= abs(tot_num - tot_ana) <= tol_sum * tot_ana
elif case == "c":
    w = KD * (30.0 / 3.6e6 * 3600.0) * 1000.0
    ok &= check("C: z (z0 - w)", z, np.full_like(z, -w), rtol)
else:
    raise SystemExit("usage: Check_analytic.py {a|b|c|d|e} <resultdir> [rtol]")
print("== dissol %s: %s ==" % (case.upper(), "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
