#!/usr/bin/env python3
# examples/debris_bedrock の入力と設定ファイルの生成(plot_results.py と定数を対で保守)
#   python3 make_init.py      地形・土層厚と param_*.txt を書く
#
# 幅 10 m(5 セル、Δx = 2 m、両岸は壁)・長さ 400 m の渓流に、谷頭から土石流(混合体の
# 三角形のハイドログラフ)を 1 回流し、岩盤がどこでどれだけ削れるかを見る
# (docs/mountain_stream_plan.md §12。developer.md §89.18〜)。勾配は谷頭から
# 0.35 → 0.20 → 0.10 → 0.04 → 0.01 の 5 区間、南端は自由流出。
# 構成(CASES): 抵抗則・侵食堆積式 2 通り(高橋・中川 T、クーロン + Manning C)× 河床 2 通り
# (裸岩 _b、厚さ 0.3 m の堆積層 _c)、閾値を変えた T_b05・T_b20、同じ流量の清水の出水 W(流水の
# 剥離則に同じ係数・閾値を当てる)。
import math

DX, NX, NY = 2.0, 5, 200                       # 格子幅 (m)、横断・縦断のセル数
BREAKS = [(0.0, 0.35), (120.0, 0.20), (220.0, 0.10), (300.0, 0.04), (360.0, 0.01)]
ZBOT = 10.0                                    # 下流端の標高 (m)
QPEAK, TPEAK, TEND = 40.0, 10.0, 70.0          # 混合体の流量のピーク (m3/s)・時刻・終了 (s)
CMIX = 0.35                                    # 流入の混合体積濃度 C
SDCOV = 0.3                                    # 堆積層の厚さ (m)
# 岩盤侵食(土石流の項と、清水の出水に当てる流水の剥離則で同じ値)
KD, TAUCD, MD, HSTAR = 1.8e-4, 1000.0, 1.0, 0.05
TT, DT, DTF = 300.0, 0.02, 10.0                # 計算時間・時間刻み・出力間隔 (s)

# 名前 → (抵抗則・侵食堆積式, 河床, 閾値 τ_cd (Pa))
CASES = {
    "T_b": ("T", "bare", TAUCD), "T_c": ("T", "cov", TAUCD),
    "C_b": ("C", "bare", TAUCD), "C_c": ("C", "cov", TAUCD),
    "T_b05": ("T", "bare", 500.0), "T_b20": ("T", "bare", 2000.0),
    "W": ("W", "bare", TAUCD),
}


def slope_at(s):
    sl = BREAKS[0][1]
    for s0, v in BREAKS:
        if s >= s0:
            sl = v
    return sl


def zc(j):
    """セル中心の標高(下流端から勾配を積分)"""
    s = (j - 0.5) * DX
    z, x, ds = ZBOT, NY * DX, 0.01
    while x > s + 1e-9:
        step = min(ds, x - s)
        z += slope_at(x - step / 2) * step
        x -= step
    return z


def write(fn, f, fmt="%.6f"):
    with open(fn, "w") as o:
        for j in range(1, NY + 1):
            o.write(" ".join(fmt % f(i, j) for i in range(1, NX + 1)) + "\n")


def hydro(c):
    """(分, 水の流量 m3/s) と (分, 濃度 h_s/h) の折れ線"""
    pts = [(0.0, 0.0), (TPEAK, QPEAK), (TEND, 0.0), (1.0e6, 0.0)]
    return ([(t / 60.0, q * (1.0 - c)) for t, q in pts], [(t / 60.0, c / (1.0 - c)) for t, q in pts])


def geomorph(model, taucd):
    rock = ("  f_rockinc = 1\n  rock_hstar = %.2f        ! 被覆の長さ H* (m)\n" % HSTAR)
    if model == "W":
        return ("  dt_geomorph = 0.0\n  morfac = 1.0\n"
                "  f_fluvial = 1             ! 清水の出水(裸岩なので掃流砂は動かない)\n"
                "  fluv_d50 = 0.1\n  fluv_porosity = 0.4\n" + rock +
                "  rock_kp = %.3e          ! 土石流の項と同じ係数・閾値を流水の剥離則に当てる\n"
                "  rock_tauc = %.1f\n  rock_m = %.1f\n" % (KD, taucd, MD))
    s = "  dt_geomorph = 0.0\n  morfac = 1.0\n  f_debris = 1\n  db_phi = 35.0\n"
    if model == "T":
        s += ("  f_dbed = 3                ! 高橋・中川(1991)\n  f_dbres = 3\n"
              "  db_d50 = 0.1\n  db_delte = 0.0001\n  db_deltd = 0.5\n")
    else:
        s += ("  f_dbed = 1                ! 高橋型平衡濃度への緩和\n  f_dbres = 1               ! クーロン + Manning\n"
              "  db_delte = 0.0007\n  db_deltd = 0.05\n")
    s += ("  f_dbstop = 1\n  db_vstop = 0.05\n  db_wstop = 0.05\n  fluv_porosity = 0.4\n" + rock +
          "  rock_kdb = %.3e         ! 土石流による岩盤侵食の速度係数 (m/s)\n"
          "  rock_taucdb = %.1f      ! 閾値 τ_cd (Pa)\n  rock_mdb = %.1f\n" % (KD, taucd, MD))
    return s


def param(name):
    model, bed, taucd = CASES[name]
    c = 0.0 if model == "W" else CMIX
    qw, cs = hydro(c)
    out = []
    out.append("!" + "=" * 70 + "\n! examples/debris_bedrock: 構成 %s(make_init.py が生成)\n!" % name + "=" * 70 + "\n")
    out.append("&list_sysparam\n  dt = %.2f\n  t0 = 0\n  tt = %.0f\n  dt_disp = 60\n  dt_file = %.0f\n"
               "  dt_recrd = %.0f\n  fn_geoinfo = '-'\n  fn_initial = '-'\n  fn_enc = '-'\n"
               "  fn_geomorph = '-'\n  fn_boundary = '-'\n  dir_result = 'result_%s'\n"
               "  dir_save = 'save_%s'\n  f_state_save = 1\n  f_check_cfl = 1\n"
               "  f_output_mode = 2         ! bil(単精度)\n  f_out_z = 1\n  f_out_vv = 1\n%s/\n"
               % (DT, TT, DTF, TT, name, name, "" if model == "W" else "  f_out_hs = 1\n"))
    out.append("&list_enc\n  f_gravity_correction = 1\n"
               "  f_opening_dynamic = 3     ! 塞がりを局所の平面から測る(急勾配の渓流。developer.md §68.41)\n/\n")
    out.append("&list_initial\n  f_htype = 0\n  h0 = 0.0\n/\n")
    out.append("&list_geoinfo\n  lx = %.1f\n  ly = %.1f\n  nx = %d\n  ny = %d\n  f_ztype = 1\n"
               "  fn_z = 'z.txt'\n  f_rntype = 0\n  rn0 = 0.05\n  f_sdtype = 1\n  fn_sd = '%s'\n"
               "  sy0 = 0.2\n/\n" % (NX * DX, NY * DX, NX, NY, "sd_bare.txt" if bed == "bare" else "sd_cov.txt"))
    out.append("&list_geomorph\n" + geomorph(model, taucd) + "/\n")
    out.append("&list_bound_edge\n  f_bc_s = 1                ! 南辺は自由流出\n/\n")
    s = "&list_bound_inflow\n"
    for i in range(1, NX + 1):
        s += "  inflow_cell(1:2,%d,1) = %d, 1\n" % (i, i)
    for k, (t, q) in enumerate(qw, 1):
        s += "  inflow_val(1:2,%d,1) = %.6f, %.6f\n" % (k, t, q)
    s += "  inflow_dist(1) = 0\n"
    if c > 0.0:
        for k, (t, v) in enumerate(cs, 1):
            s += "  inflow_cs(1:2,%d,1) = %.6f, %.6f\n" % (k, t, v)
    out.append(s + "/\n")
    with open("param_%s.txt" % name, "w") as o:
        o.write("".join(out))


if __name__ == "__main__":
    write("z.txt", lambda i, j: zc(j))
    write("sd_bare.txt", lambda i, j: 0.0, "%.1f")
    write("sd_cov.txt", lambda i, j: SDCOV, "%.1f")
    for n in CASES:
        param(n)
