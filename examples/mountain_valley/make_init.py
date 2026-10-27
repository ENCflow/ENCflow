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


if __name__ == "__main__":
    for gkey in GRIDS:
        g = Grid(gkey)
        for fn, (f, fmt) in g.maps().items():
            g.write(fn, f, fmt)
    for name in CASES:
        write_param(name)
    g = Grid("4m")
    h0, v0 = g.uniform(S0)
    print("H0 = %.4f m, V0 = %.4f m/s; uplift0 = %.4f mm/yr, wthr_p0 = %.6e mm/kyr, creep_d = %.6e m2/s; wrote %s"
          % (h0, v0, UPLIFT0, WTHR_P0, CREEP_D, ", ".join("param_%s.txt" % c for c in CASES)))
