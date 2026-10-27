#!/usr/bin/env python3
# examples/mountain_valley の入力と設定ファイルの生成(plot_results.py と定数を対で保守)
#   python3 make_init.py      全構成の地形・初期水深・土層厚・倍率の分布と param_*.txt を書く
#
# ===== 構成 V(C3: V 字谷の完全連成。docs/mountain_stream_plan.md §11.3・§11.4)=====
#   谷の長さ 200 m・幅 44 m。中央の列が幅 1 セルの渓流、両側に長さ L = 20 m の斜面、東西の端は
#   分水界(壁)。谷頭(北端)の渓流のセルに一定の形成流量、南辺は自由流出。出口の行(j = NY)は
#   隆起・風化・岩盤下刻のない基準面。基本の格子は Δx = 4 m(11 × 50)、解像度の確認は
#   Δx = 2 m(21 × 100。渓流の幅も 2 m になる)。
#   代表出水(形成流量)だけを計算し、連続に働く隆起・風化・クリープの係数を間欠係数
#   i_f = F / 1 年(F = 出水の時間 300 s/年)の逆数倍して与える(§11.2。developer.md §88.11 の 2)。
#   暦の時間 T = 出水の時間 / F × 1 年。
import math

# --- 地形・出水・渓流 ---
VAL_LEN, HILL_L = 200.0, 20.0                      # 谷の長さ・片側の斜面の長さ (m)
S0, SH, Z0 = 0.04, 0.25, 10.0                      # 初期の谷底の勾配・斜面の勾配(裸岩の V 字)
QF, N = 0.5, 0.04                                  # 形成流量 (m3/s)・Manning の n
D50, LAM, HSTAR = 0.03, 0.4, 0.2                   # 礫径・空隙率・被覆の長さ H* (m)
KP, TAUC, PM, BETA = 8.9e-8, 10.0, 1.5, 6.6e-4     # 剥離 k_p (m/s。出水中)・τ_c (Pa)・m、研磨 β (1/m)
# --- 暦の時間の率(連続に働く過程)と換算 ---
YR = 365.25 * 86400.0                              # 1 年 (s)。m_geomorph の yr_s
F_FLOOD = 300.0                                    # 出水の時間 (s/年) = i_f × 1 年(i_f = 9.5e-6)
U_CAL, W0_CAL, D_CAL = 0.1, 0.3, 0.01              # 隆起 (mm/yr)・裸岩の土層生成 (mm/yr)・クリープ (m2/yr)
SDSTAR, HC = 0.5, 0.3                              # 生成の減衰深 sd*・クリープの減衰厚 H_c (m)
UPLIFT0 = U_CAL * YR / F_FLOOD                     # 入力 uplift0 (mm/yr。出水の時間あたり)
WTHR_P0 = W0_CAL * 1000.0 * YR / F_FLOOD           # 入力 wthr_p0 (mm/kyr)
CREEP_D = D_CAL / F_FLOOD                          # 入力 creep_d (m2/s)
# --- 時間 ---
T_RUN, T_OUT = 2.0e5, 1.0e4                        # 構成 V_a・V_b・V_b2 の暦の時間・出力間隔 (年)
T_DROP = 1.0e5                                     # 構成 V_c(V_b の続き)の暦の時間 (年)

# 格子: 名前 → (Δx, dt, morfac)。dts = dt × morfac は薄い被覆の排出率 × dts の最大が 0.5 を
# 十分下回るように選ぶ(Δx = 4 m で dts = 50 s のとき 0.20)
GRIDS = {"4m": (4.0, 0.5, 100.0), "2m": (2.0, 0.25, 80.0)}


class Grid:
    def __init__(self, key):
        self.key = key
        self.dx, self.dt, self.morfac = GRIDS[key]
        self.lh = int(round(HILL_L / self.dx))     # 片側の斜面のセル数
        self.nx = 2 * self.lh + 1
        self.ny = int(round(VAL_LEN / self.dx))
        self.ic = self.lh + 1                       # 渓流の列
        self.sfx = "" if key == "4m" else "_" + key

    def q_unit(self):
        return QF / self.dx

    def uniform(self, s):
        h = (self.q_unit() * N / math.sqrt(s)) ** 0.6
        return h, self.q_unit() / h

    def zch(self, j):
        return Z0 + S0 * (self.ny - j + 0.5) * self.dx

    def z_init(self, i, j):
        return self.zch(j) + SH * self.dx * abs(i - self.ic)

    def flow_time(self, t_yr):
        """暦の時間 (年) → 流れの時間 (s)"""
        return t_yr * F_FLOOD / self.morfac

    def write(self, fn, f, fmt="%.6f"):
        with open(fn, "w") as o:
            for j in range(1, self.ny + 1):
                o.write(" ".join(fmt % f(i, j) for i in range(1, self.nx + 1)) + "\n")

    def maps(self):
        g = self
        return {
            "z_init%s.txt" % g.sfx: (g.z_init, "%.6f"),
            "h_init%s.txt" % g.sfx: (lambda i, j: g.uniform(S0)[0] if i == g.ic else 0.0, "%.6f"),
            "sd_zero%s.txt" % g.sfx: (lambda i, j: 0.0, "%.1f"),
            # 隆起の倍率: 出口の行は 0(基準面)/ 構成 V_c は出口の行が −1(基準面の低下)
            "up_base%s.txt" % g.sfx: (lambda i, j: 0.0 if j == g.ny else 1.0, "%.1f"),
            "up_drop%s.txt" % g.sfx: (lambda i, j: -1.0 if j == g.ny else 1.0, "%.1f"),
            # 風化の倍率: 渓流と出口の行は 0(渓流の岩盤は風化でなく流水で下がる。§88.13)
            "wthr_hill%s.txt" % g.sfx: (lambda i, j: 0.0 if (i == g.ic or j == g.ny) else 1.0, "%.1f"),
            # 岩盤下刻の倍率: 出口の行は 0(基準面)
            "rock_base%s.txt" % g.sfx: (lambda i, j: 0.0 if j == g.ny else 1.0, "%.1f"),
        }


CASES = {
    # 名前: (説明, 格子, 斜面の風化・クリープ, 隆起の倍率, 開始 (年), 終了 (年), 再開)
    "V_a": ("斜面の風化・クリープなし(渓流は自分の剥離物だけを運ぶ)", "4m", False, "up_base", 0.0, T_RUN, False),
    "V_b": ("斜面の風化・深さ依存クリープあり(完全連成)", "4m", True, "up_base", 0.0, T_RUN, False),
    "V_c": ("V_b の続き。出口の行を隆起の速さで下げる(基準面の低下)", "4m", True, "up_drop", T_RUN, T_RUN + T_DROP, True),
    "V_b2": ("V_b を Δx = 2 m で(解像度の確認。渓流の幅も 2 m)", "2m", True, "up_base", 0.0, T_RUN, False),
}


def write_param(name):
    desc, gkey, hill, upmap, t0, t1, restart = CASES[name]
    g = Grid(gkey)
    h0, v0 = g.uniform(S0)
    hill_lines = """  f_creep = 1
  creep_d = {cd:.6e}       ! クリープ D (m2/s) = {dc} m2/yr / {ff:g} s(出水の時間/年)
  creep_hstar = {hc}         ! 深さ依存クリープの減衰厚 H_c (m)
  f_wthr = 1
  wthr_p0 = {wp:.6e}       ! 裸岩の土層生成 (mm/kyr) = {wc} mm/yr / i_f
  wthr_sdstar = {sds}         ! 生成の減衰深 sd* (m)
  fn_wthr = 'wthr_hill{sfx}.txt' ! 渓流と出口の行は風化しない""".format(
        cd=CREEP_D, dc=D_CAL, ff=F_FLOOD, hc=HC, wp=WTHR_P0, wc=W0_CAL, sds=SDSTAR, sfx=g.sfx) if hill else \
        "  ! 斜面の風化・クリープなし(構成 V_a)"
    rst = ("  f_state_restore = 1       ! V_b の save(save_V_c に複製しておく)から再開(時刻継続。\n"
           "                            !   t0 は保存した計算と同じ 0、tt は通しの終了時刻)\n") if restart else ""
    txt = """!======================================================================
! examples/mountain_valley 構成 {name}: {desc}
!   make_init.py が生成(定数は make_init.py・plot_results.py と対で保守)。暦の時間 {t0:g}〜{t1:g} 年
!   (出水の時間 = 暦の時間 × {ff:g} s/年、流れの時間 = 出水の時間 / morfac)
!======================================================================
&list_sysparam
  dt = {dt}
  t0 = 0.0
  tt = {ft1:.1f}
  dt_disp = {fout:.1f}
  dt_file = {fout:.1f}
  dt_recrd = {fout:.1f}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_geomorph = '-'
  fn_boundary = '-'
  dir_result = 'result_{name}'
  dir_save = 'save_{name}'
  f_state_save = 1
{rst}  f_check_cfl = 1
  f_output_mode = 2         ! bil(単精度)
  f_out_z = 1
  f_out_vv = 1
/

&list_enc
/

&list_initial
  f_htype = 1
  fn_hinit = 'h_init{sfx}.txt'   ! 渓流は初期勾配の等流水深
  v0 = {v0:.6f}             ! 等流流速(南向き = j の増える向き)
/

&list_geoinfo
  lx = {lx:.1f}
  ly = {ly:.1f}
  nx = {nx}
  ny = {ny}
  f_ztype = 1
  fn_z = 'z_init{sfx}.txt'       ! 裸岩の V 字(谷底の勾配 {s0}、斜面の勾配 {sh})
  f_rntype = 0
  rn0 = {n}
  f_sdtype = 1
  fn_sd = 'sd_zero{sfx}.txt'     ! 裸岩から
  sy0 = 0.2
/

&list_geomorph
  dt_geomorph = 0.0         ! 毎ステップ更新
  morfac = {mf}            ! dts = {dts:g} s(出水の時間)
  f_fluvial = 1
  f_qbform = 1
  fluv_d50 = {d50}
  fluv_tausc = 0.05
  fluv_porosity = {lam}
  fluv_sgrav = 1.65
  fluv_dzmax = 0.05
  f_rockinc = 1
  rock_kp = {kp:.2e}          ! 剥離の速度係数 (m/s。出水中の値)
  rock_tauc = {tauc}
  rock_m = {pm}
  rock_beta = {beta:.2e}       ! 研磨係数 (1/m)
  rock_hstar = {hs}          ! 被覆の長さ H* (m)
  fn_rock = 'rock_base{sfx}.txt' ! 出口の行は侵食しない(基準面)
{hill}
  f_uplift = 1
  uplift0 = {up:.4f}       ! 隆起 (mm/yr) = {uc} mm/yr / i_f
  fn_uplift = '{upmap}{sfx}.txt'
/

&list_bound_edge
  f_bc_s = 1                ! 南辺は自由流出(出口)
/
&list_bound_inflow
  inflow_cell(1:2,1,1) = {ic}, 1
  inflow_val(1:2,1,1) = 0, {qf}
  inflow_val(1:2,2,1) = 1e9, {qf}
  inflow_dist(1) = 0
/
""".format(name=name, desc=desc, t0=t0, t1=t1, ff=F_FLOOD, dt=g.dt, ft1=g.flow_time(t1),
           fout=g.flow_time(T_OUT), rst=rst, v0=v0, lx=g.nx * g.dx, ly=g.ny * g.dx, nx=g.nx, ny=g.ny,
           s0=S0, sh=SH, n=N, mf=g.morfac, dts=g.dt * g.morfac, d50=D50, lam=LAM, kp=KP, tauc=TAUC, pm=PM,
           beta=BETA, hs=HSTAR, hill=hill_lines, up=UPLIFT0, uc=U_CAL, upmap=upmap, sfx=g.sfx, ic=g.ic, qf=QF)
    open("param_%s.txt" % name, "w").write(txt)


# ===== 構成 P(C4: 同じ平均の谷頭のパルス給砂。docs/mountain_stream_plan.md §11.3)=====
#   test/rockinc の T11(C1)と同じ幅 1 セルの水路(Δx = 1 m、長さ 60 m、勾配 0.01 から、
#   n = 0.04、Q = 0.336 m3/s、d50 = 1 cm、H* = 5 cm、隆起 U = 1e-5 m/s、出口の行は隆起も
#   侵食もしない)を東西に 3 本並べ(両岸は +2 m の乾いた地盤)、平均の給砂比 P_RM の一定給砂と、
#   半分の時間だけ 2 P_RM で給砂するパルス(周期 P_SHORT・P_LONG。地形の時間)を比べる。
#   P_p = 剥離だけ、P_a = 研磨だけ(研磨は供給が道具なので、自己供給がない)
P_NY, P_DX, P_S0, P_N, P_Z0, P_BANK, P_H0 = 60, 1.0, 0.01, 0.04, 10.0, 2.0, 0.3
P_V0 = P_H0 ** (2.0 / 3.0) * math.sqrt(P_S0) / P_N
P_Q = P_H0 * P_V0 * P_DX
P_D50, P_HSTAR, P_U = 0.01, 0.05, 1.0e-5           # 礫径・被覆の長さ・隆起 (m/s。出水中)
P_KP, P_TAUC, P_PM, P_BETA = 6.0e-6, 10.0, 1.5, 0.05
P_QC0, P_RM = 1.81e-3, 0.4                          # 勾配 0.01 の等流の容量の概算 (m2/s)・平均の給砂比
P_SHORT, P_LONG = 600.0, 12000.0                   # パルスの周期(地形の時間 s)
P_TGEO, P_DTG = 3.0e5, 3000.0                     # 地形の時間 (s) と出力間隔(地形の時間 s)
P_DT, P_MORFAC = 0.1, 10.0                         # dts = 1 s(薄い被覆の排出率 × dts の最大 < 0.5)
P_TT, P_DTF = P_TGEO / P_MORFAC, P_DTG / P_MORFAC  # 流れの時間と出力間隔 (s)
P_CASES = {"P_p": "p", "P_a": "a"}
P_MODELS = {"p": "剥離だけ", "a": "研磨だけ"}


def p_qb_const(r):
    return [(0.0, r * P_QC0 * P_DX), (1.0e9, r * P_QC0 * P_DX)]


def p_qb_pulse(r_on, period_geo):
    """半分の時間だけ r_on で給砂する矩形のパルス(時刻は流れの時間の分。立ち上がりは 0.01 分)"""
    pf = period_geo / P_MORFAC / 60.0
    pts, t = [], 0.0
    while t < P_TT / 60.0 + pf:
        pts += [(t, r_on * P_QC0 * P_DX), (t + 0.5 * pf - 0.01, r_on * P_QC0 * P_DX),
                (t + 0.5 * pf, 0.0), (t + pf - 0.01, 0.0)]
        t += pf
    return pts


# 水路ごとの給砂(一定は namelist、パルスは時系列ファイル。点数の多い時系列は fn_inflow_qb で与える)
P_SERIES = [("const", p_qb_const(P_RM)), ("p_qb_short.txt", p_qb_pulse(2.0 * P_RM, P_SHORT)),
            ("p_qb_long.txt", p_qb_pulse(2.0 * P_RM, P_LONG))]
P_NX = 2 * len(P_SERIES) + 1


def p_z(i, j):
    return P_Z0 + P_S0 * (P_NY - j + 0.5) * P_DX + (0.0 if i % 2 == 0 else P_BANK)


def write_grid_p(fn, f, fmt="%.6f"):
    with open(fn, "w") as o:
        for j in range(1, P_NY + 1):
            o.write(" ".join(fmt % f(i, j) for i in range(1, P_NX + 1)) + "\n")


P_MAPS = {
    "p_z.txt": (p_z, "%.6f"),
    "p_h.txt": (lambda i, j: P_H0 if i % 2 == 0 else 0.0, "%.6f"),
    "p_sd.txt": (lambda i, j: 0.0, "%.1f"),
    "p_base.txt": (lambda i, j: 0.0 if j == P_NY else 1.0, "%.1f"),   # 隆起・岩盤下刻の倍率(出口の行は 0)
}


def write_param_p(name):
    model = P_CASES[name]
    rock = ("  rock_kp = %.1e           ! 剥離の速度係数 (m/s)\n  rock_tauc = %.1f\n  rock_m = %.1f\n  rock_beta = 0.0"
            % (P_KP, P_TAUC, P_PM)) if model == "p" else \
           ("  rock_kp = 0.0             ! 剥離なし\n  rock_beta = %.3f          ! 研磨係数 (1/m)" % P_BETA)
    inflow = []
    for k, (fn, qb) in enumerate(P_SERIES):
        s = k + 1
        inflow += ["  inflow_cell(1:2,1,%d) = %d, 1" % (s, 2 * s),
                   "  inflow_val(1:2,1,%d) = 0, %.6f" % (s, P_Q),
                   "  inflow_val(1:2,2,%d) = 1e9, %.6f" % (s, P_Q),
                   "  inflow_dist(%d) = 0" % s]
        if fn == "const":
            inflow += ["  inflow_qb(1:2,%d,%d) = %.4f, %.6e" % (n + 1, s, t, v) for n, (t, v) in enumerate(qb)]
        else:
            inflow += ["  fn_inflow_qb(%d) = '%s'   ! パルスの時系列(分, m3/s 固体)" % (s, fn)]
    txt = """!======================================================================
! examples/mountain_valley 構成 {name}({mdl}): 同じ平均の谷頭の給砂(給砂比 {rm})を、一定・
!   パルス(半分の時間だけ給砂比 {ron}。周期 {ps:g} s・{pl:g} s。地形の時間)で与えた 3 本の水路
!   (列 i = 2・4・6)。隆起 U = {u:g} m/s の下の定常で比べる(C4)。make_init.py が生成
!======================================================================
&list_sysparam
  dt = {dt}
  t0 = 0
  tt = {tt:g}
  dt_disp = {dtd:g}
  dt_file = {dtf:g}
  dt_recrd = {tt:g}
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
  fn_hinit = 'p_h.txt'
  v0 = {v0:.6f}             ! 等流流速(南向き)
/

&list_geoinfo
  lx = {lx:.1f}
  ly = {ly:.1f}
  nx = {nx}
  ny = {ny}
  f_ztype = 1
  fn_z = 'p_z.txt'
  f_rntype = 0
  rn0 = {n}
  f_sdtype = 1
  fn_sd = 'p_sd.txt'        ! 裸岩から
  sy0 = 0.2
/

&list_geomorph
  dt_geomorph = 0.0         ! 毎ステップ更新
  morfac = {mf}             ! dts = {dts:g} s
  f_fluvial = 1
  f_qbform = 1
  fluv_d50 = {d50}
  fluv_tausc = 0.05
  fluv_porosity = {lam}
  fluv_sgrav = 1.65
  fluv_dzmax = 0.05
  f_rockinc = 1
{rock}
  rock_hstar = {hs}         ! 被覆の長さ H* (m)
  fn_rock = 'p_base.txt'    ! 出口の行は侵食しない(基準面)
  f_uplift = 1
  uplift0 = {up:.1f}        ! 隆起 U = {u:g} m/s (mm/yr)
  fn_uplift = 'p_base.txt'  ! 出口の行は隆起しない(基準面)
/

&list_bound_edge
  f_bc_s = 1                ! 南辺は自由流出
/
&list_bound_inflow
{inflow}
/
""".format(name=name, mdl=P_MODELS[model], rm=P_RM, ron=2 * P_RM, ps=P_SHORT, pl=P_LONG, u=P_U, dt=P_DT,
           tt=P_TT, dtf=P_DTF, dtd=10 * P_DTF, v0=P_V0, lx=P_NX * P_DX, ly=P_NY * P_DX, nx=P_NX, ny=P_NY, n=P_N, mf=P_MORFAC,
           dts=P_DT * P_MORFAC, d50=P_D50, lam=LAM, rock=rock, hs=P_HSTAR, up=P_U * 1.0e3 * YR,
           inflow="\n".join(inflow))
    open("param_%s.txt" % name, "w").write(txt)


if __name__ == "__main__":
    for gkey in GRIDS:
        g = Grid(gkey)
        for fn, (f, fmt) in g.maps().items():
            g.write(fn, f, fmt)
    for name in CASES:
        write_param(name)
    for fn, (f, fmt) in P_MAPS.items():
        write_grid_p(fn, f, fmt)
    for fn, qb in P_SERIES:
        if fn != "const":
            with open(fn, "w") as o:
                for t, v in qb:
                    o.write("%.4f %.6e\n" % (t, v))
    for name in P_CASES:
        write_param_p(name)
    g = Grid("4m")
    h0, v0 = g.uniform(S0)
    print("H0 = %.4f m, V0 = %.4f m/s; uplift0 = %.4f mm/yr, wthr_p0 = %.6e mm/kyr, creep_d = %.6e m2/s; wrote %s"
          % (h0, v0, UPLIFT0, WTHR_P0, CREEP_D, ", ".join("param_%s.txt" % c for c in list(CASES) + list(P_CASES))))
