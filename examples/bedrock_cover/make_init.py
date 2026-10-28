#!/usr/bin/env python3
# examples/bedrock_cover の入力と設定ファイルの生成(plot_results.py と定数を対で保守)
#   幅 1 セルの掘り込み水路(両岸は +2 m の乾いた地盤)を東西に K 本並べ、水路ごとに
#   給砂(区間流入の掃流砂 inflow_qb)や初期の土層厚だけを変えて 1 回の計算で比べる
#   (水路は岸で隔てられ、互いに影響しない)。水路は南北向き(北 j = 1 が高く勾配 S で南へ
#   下る)、北端の区間流入 Q = q·Δx(q は Manning の等流水深 H0 の単位幅流量)、南辺は自由流出。
#   python3 make_init.py      全構成の地形・初期水深・土層厚と param_*.txt を書く
# 岩盤下刻の 3 つのモデル(f_rockinc。docs/users_guide/geomorph.md):
#   p  = 剥離だけ(rock_kp)、a = 研磨だけ(rock_beta)、pa = 両方
import math

NY, DX = 100, 1.0
S, N, Z0, BANK, H0 = 0.01, 0.04, 10.0, 2.0, 0.3
V0 = H0 ** (2.0 / 3.0) * math.sqrt(S) / N           # Manning の等流流速 (m/s)
Q = H0 * V0 * DX                                    # 水路 1 本の区間流入の流量 (m3/s)
D50, LAM, HSTAR = 0.01, 0.4, 0.01                   # 礫径・空隙率・被覆の長さ H*
KP, TAUC, PM, BETA = 1.0e-6, 10.0, 1.5, 0.005       # 剥離 k_p (m/s)・τ_c (Pa)・m、研磨 β (1/m)
QC = 1.81e-3                                        # 等流の掃流砂容量の概算 (m2/s 固体。給砂比の基準)
DT, MORFAC = 0.1, 10.0
J1, J2 = 30, 90                                     # 下刻速度を測る区間(北の流入から 30〜90 m)

# 構成(名前: (モデル, 水路ごとの設定, 流れの時間 tt (s), 出力間隔 dt_file (s)))
R_SWEEP = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)            # A: 一定給砂の給砂比 r = q_in/q_c
R_MEAN, R_ON = 0.35, 0.7                            # B: 平均の給砂比、パルスの間の給砂比(半分の時間)
P_SHORT, P_LONG = 600.0, 12000.0                    # B: パルスの周期(地形の時間 s)
SD_INIT = (0.0, 0.5 * HSTAR, 10.0 * HSTAR)          # C: 初期の土層厚(裸岩・薄い・厚い被覆)
R_COVER = 0.4                                       # C: 給砂比
J_STEP, DZ_STEP = 70, 0.3                           # D: 段差の位置(j > J_STEP を DZ_STEP 下げる)
R_KNICK = (0.0, 0.4)                                # D: 給砂比


def qb_const(r):
    return [(0.0, r * QC * DX), (9999.0, r * QC * DX)]


def qb_pulse(r_on, period_geo, tt):
    """半分の時間だけ r_on で給砂する矩形のパルス(時刻は流れの時間の分。立ち上がりは 0.01 分)"""
    pf = period_geo / MORFAC / 60.0                 # 周期(流れの時間の分)
    pts, t = [], 0.0
    while t < tt / 60.0 + pf:
        pts += [(t, r_on * QC * DX), (t + 0.5 * pf - 0.01, r_on * QC * DX),
                (t + 0.5 * pf, 0.0), (t + pf - 0.01, 0.0)]
        t += pf
    return pts


def z_of(i, j, step=False):
    z = Z0 + S * NY * DX - S * (j - 0.5) * DX + (0.0 if i % 2 == 0 else BANK)
    if step and j > J_STEP:
        z -= DZ_STEP
    return z


def write_grid(fn, nx, f):
    with open(fn, "w") as o:
        for j in range(1, NY + 1):
            o.write(" ".join("%.6f" % f(i, j) for i in range(1, nx + 1)) + "\n")


CASES = {
    "A_p":  ("p", [qb_const(r) for r in R_SWEEP], 3000, 300),
    "A_a":  ("a", [qb_const(r) for r in R_SWEEP], 3000, 300),
    "A_pa": ("pa", [qb_const(r) for r in R_SWEEP], 3000, 300),
    "B_p":  ("p", [qb_const(R_MEAN), qb_pulse(R_ON, P_SHORT, 6000), qb_pulse(R_ON, P_LONG, 6000)], 6000, 60),
    "B_a":  ("a", [qb_const(R_MEAN), qb_pulse(R_ON, P_SHORT, 6000), qb_pulse(R_ON, P_LONG, 6000)], 6000, 60),
    "C_pa": ("pa", [qb_const(R_COVER)] * len(SD_INIT), 3000, 60),
    "D_p":  ("p", [qb_const(r) for r in R_KNICK], 3000, 300),
}
HEADERS = {
    "A": "一定給砂の給砂比 r = %s(水路ごと)。定常の下刻速度と被覆の厚さを測る" % ", ".join("%g" % r for r in R_SWEEP),
    "B": "同じ平均の給砂比 %g の一定給砂と、半分の時間だけ %g のパルス(周期 %g s・%g s。地形の時間)"
         % (R_MEAN, R_ON, P_SHORT, P_LONG),
    "C": "給砂比 %g で、初期の土層厚 %s m(裸岩・薄い被覆・厚い被覆)" % (R_COVER, ", ".join("%g" % h for h in SD_INIT)),
    "D": "j > %d を %g m 下げた段差(遷急点)。給砂比 %s" % (J_STEP, DZ_STEP, ", ".join("%g" % r for r in R_KNICK)),
}
MODELS = {"p": "剥離だけ", "a": "研磨だけ", "pa": "剥離と研磨"}


def rock_lines(model):
    lines = []
    if "p" in model:
        lines += ["%-28s! 剥離の速度係数 (m/s)" % ("  rock_kp = %.1e" % KP),
                  "%-28s! 剥離の閾値 τ_c (Pa)" % ("  rock_tauc = %.1f" % TAUC),
                  "%-28s! 剥離のべき指数" % ("  rock_m = %.1f" % PM)]
    if "a" in model:
        lines += ["%-28s! 研磨係数 β (1/m)" % ("  rock_beta = %.3f" % BETA)]
    return lines


def inflow_lines(series):
    out = []
    for k, qb in enumerate(series):
        s = k + 1
        out += ["  inflow_cell(1:2,1,%d) = %d, 1" % (s, 2 * s),
                "  inflow_val(1:2,1,%d) = 0, %.6f" % (s, Q),
                "  inflow_val(1:2,2,%d) = 9999, %.6f" % (s, Q),
                "  inflow_dist(%d) = 0" % s]
        out += ["  inflow_qb(1:2,%d,%d) = %.4f, %.6e" % (n + 1, s, t, v) for n, (t, v) in enumerate(qb)]
    return out


def write_param(name, model, series, tt, dtfile, nx, fn_z, fn_h, fn_sd):
    txt = """!======================================================================
! examples/bedrock_cover 構成 {name}({mtxt}): {head}
!   make_init.py が生成(定数は make_init.py・plot_results.py と対で保守)。水路は {k} 本で、
!   水路 k(k = 1, 2, …)は列 i = 2k(両側の奇数列は乾いた岸)、区間流入 k に対応する
!======================================================================
&list_sysparam
  dt = {dt}
  t0 = 0
  tt = {tt}
  dt_disp = 300
  dt_file = {dtfile}
  dt_recrd = {tt}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_geomorph = '-'
  fn_boundary = '-'
  dir_result = 'result_{name}'
  dir_save = 'save_{name}'
  f_state_save = 1
  f_check_cfl = 1
  f_output_mode = 2         ! bil(単精度)
  f_out_z = 1
  f_out_vv = 1
/

&list_enc
/

&list_initial
  f_htype = 1
  fn_hinit = '{fn_h}'
  v0 = {v0:.6f}             ! 等流流速(南向き = j の増える向き)
/

&list_geoinfo
  lx = {lx:.1f}
  ly = {ly:.1f}
  nx = {nx}
  ny = {ny}
  f_ztype = 1
  fn_z = '{fn_z}'
  f_rntype = 0
  rn0 = {n}
  f_sdtype = 1
  fn_sd = '{fn_sd}'
  sy0 = 0.2
/

&list_geomorph
  dt_geomorph = 0.0         ! 毎ステップ更新
  morfac = {morfac}             ! dts = 1 s
  f_fluvial = 1
  f_qbform = 1
  fluv_d50 = {d50}           ! 礫径 (m)。等流で τ* ≈ 0.18(動く)
  fluv_tausc = 0.05
  fluv_porosity = {lam}
  fluv_sgrav = 1.65
  fluv_dzmax = 0.05
  f_rockinc = 1
{rock}
  rock_hstar = {hs}         ! 被覆の長さ H* (m)
/

&list_bound_edge
  f_bc_s = 1                ! 南辺は自由流出
/
&list_bound_inflow
{inflow}
/
""".format(name=name, mtxt=MODELS[model], head=HEADERS[name[0]], k=len(series), dt=DT, tt=tt, dtfile=dtfile,
           fn_h=fn_h, v0=V0, lx=nx * DX, ly=NY * DX, nx=nx, ny=NY, fn_z=fn_z, n=N, fn_sd=fn_sd, morfac=MORFAC,
           d50=D50, lam=LAM, rock="\n".join(rock_lines(model)), hs=HSTAR, inflow="\n".join(inflow_lines(series)))
    open("param_%s.txt" % name, "w").write(txt)


if __name__ == "__main__":
    done = set()
    for name, (model, series, tt, dtfile) in CASES.items():
        k = len(series)
        nx = 2 * k + 1
        step = name.startswith("D")
        fn_z = "zinit_%d%s.txt" % (k, "_step" if step else "")
        fn_h = "hinit_%d.txt" % k
        fn_sd = "sd_%s.txt" % name if name.startswith("C") else "sdzero_%d.txt" % k
        if fn_z not in done:
            write_grid(fn_z, nx, lambda i, j: z_of(i, j, step))
            done.add(fn_z)
        if fn_h not in done:
            write_grid(fn_h, nx, lambda i, j: H0 if i % 2 == 0 else 0.0)
            done.add(fn_h)
        if fn_sd not in done:
            if name.startswith("C"):
                write_grid(fn_sd, nx, lambda i, j: SD_INIT[i // 2 - 1] if i % 2 == 0 else 0.0)
            else:
                write_grid(fn_sd, nx, lambda i, j: 0.0)
            done.add(fn_sd)
        write_param(name, model, series, tt, dtfile, nx, fn_z, fn_h, fn_sd)
    print("V0 = %.6f m/s, Q = %.6f m3/s; wrote %s" % (V0, Q, ", ".join("param_%s.txt" % c for c in CASES)))
