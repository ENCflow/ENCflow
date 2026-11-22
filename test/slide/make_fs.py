#!/usr/bin/env python3
"""test/slide 構成 5〜8 の入力と設定ファイルの生成(Run.sh・Run_MPI.sh が呼ぶ)。

斜面安定判定 f_slide の選択子(developer.md §28.19)の検定。地形は一様な勾配の平面
z = Z0 − A x − B y(40 m × 30 m、Δx = 1 m。|∇z| = 0.3905 で、向きは格子の 8 方向のどれとも合わない。
y の向きにも傾くので、MPI の帯の境界をまたいで近傍を読む)。地下水計算は Green-Ampt(浸透能はほぼ 0)で、
層1の初期飽和度 gw_sat0 が土層の飽和厚 hw = gw_sat0·sd を決める。降雨・流入はない。

構成 5: 浸透力を全水頭の勾配で入れる安全率(f_slide_seep = 1)。判定だけ(f_slide = 2)で、安全率の
  出力 Fs を式の値と比べる(平面の地形と平面の土層厚では、全水頭も平面で勾配が解析的に決まる)
    fs_u0 / fs_u1 : 土層厚が一様(1 m)、飽和度 0.6。全水頭の勾配 J = tanθ なので、f_slide_seep = 0 と 1 が
                    同じ値(斜面に平行な浸透の従来の式)になる
    fs_g0 / fs_g1 : 土層厚が下流へ厚くなる平面(1 + 0.08 x + 0.06 y m)、飽和度 0.5、粘着力 2 kPa。
                    J = 0.4405 > tanθ = 0.3905 で、1 は従来の式より小さい安全率になる
    fs_l0 / fs_l1 : 土層厚 1 m・飽和。下流側を静水の湖にする(水位 LAKE_E)。湖の下は J = 0 で、
                    1 は Fs = tanφs/tanθ、0 はその (γt − γw)/γt 倍(従来の式の過小評価)
    fs_lq1        : fs_l1 の飽和度を 1 − 2.5e-4 に(地下貯留が容量にわずかに届かない)。地表水の水頭は、
                    貯留が容量の (1 − WFULL) 倍から容量までの間で 0 から 1 へ連続につながる(つながり κ。
                    ここでは 0.75)。湖の下は J = (1 − κ) tanθ
    fs_le1        : 同 1 − 1e-6(側方の地下水流の 1 回ぶんで欠ける桁)。κ = 0.999 で、湖の下の安全率は
                    静水の値 tanφs/tanθ から 0.1 % しか下がらない(容量に届いたかどうかの 2 値でつなぐと、
                    従来の式の値 = _l0 まで下がる)
    fs_m1 / fs_m0 : 流動中の土砂が載ったセルの水頭。fs_m1 は fs_l1 の湖の下の一部(REL_I × REL_J)を、
                    深さ REL_D だけ瞬時に流動化する(fn_dbinit、t = 1 s。f_dbwet = 3 で、崩れた層の水の
                    全部が流れへ出る)。流動面 z + h + hs は平らなまま。fs_m0 は、同じ形にはじめから
                    掘って清水を張ったケース。全水頭を流動面で読めば、2 つの安全率は同じになる
                    (水深 h だけで読むと、流動化したセルの水頭が hs だけ下がって、隣のセルの J が増える)
    fs_gdyn       : fs_g1 を流動化あり(f_slide = 1)で 5 秒。保存則と MPI の一致を見る
構成 6: 判定・流動化する深さの上限(slide_dmax)。土層厚 2 m、飽和度 0.9、slide_dmax = 0.5 m
    fs_d2         : 判定だけ。Fs が、上から 0.5 m と飽和厚 0.3 m の式の値になる
    fs_d1         : 流動化あり、地形の更新 1 回。標高がちょうど 0.5 m 下がり、土層が 1.5 m 残る
構成 7: 間隙水圧で起きる崩壊に限る(f_slide_wet = 1)。φs = 20° で乾いていても Fs = 0.93 < 1 の斜面
    fs_w1 / fs_w0 : 1 は流動化しない(標高・土層厚が不変)、0 は全層を流動化する
    fs_w2         : φs = 25°(乾いた Fs = 1.19)・飽和で f_slide_wet = 1。間隙水圧で Fs < 1 に
                    なるので、1 でも流動化する
構成 8: 濃い混合体が載るセルを判定しない(f_slide_noflow = 1)。構成 6 の fs_d1 を地形の更新 2 回
    fs_n1 / fs_n0 : 1 は 2 回目の更新で流動化しない(土層 1.5 m)、0 はもう 0.5 m 流動化する(1.0 m)

  python3 make_fs.py        d_fs/ の地形・土層厚・初期水深と p_fs_*.txt を書く
  python3 make_fs.py list   ケース名を 1 行ずつ出す
定数は Check_slide_fs.py と対。
"""
import os
import sys

NX, NY, DX = 40, 30, 1.0
Z0, A, B = 30.0, 0.30, 0.25          # 地形 z = Z0 − A x − B y
SDG = (1.0, 0.08, 0.06)              # 土層厚の平面 sd = s0 + c x + d y(fs_g*)
LAKE_E = 19.0                        # 湖の水位 (m。fs_l*。領域の下流側のおよそ 1/3 が湖になる)
SY0, POROSITY = 0.3, 0.4
GAMMA = 19000.0                      # 飽和単位体積重量 γt (N/m3)
WFULL = 1.0e-3                       # 地表水の水頭を飽和帯へつなぐ幅(容量に対する比。本体の gw_wfull と同じ値)
REL_D, REL_I, REL_J = 0.5, (31, 35), (16, 21)   # fs_m1 で流動化する深さ (m) とセルの範囲(湖の下。水深 2 m 以上)
DT, DTG = 0.05, 1.0

CASES = {
    #  name      sd        sat  lake   slide seep wet noflow dmax  c'     φs    更新回数
    "fs_u0":   dict(sd=1.0,   sat=0.6, lake=False, slide=2, seep=0, wet=0, noflow=0, dmax=0.0, c=0.0,    phi=25.0, nup=1),
    "fs_u1":   dict(sd=1.0,   sat=0.6, lake=False, slide=2, seep=1, wet=0, noflow=0, dmax=0.0, c=0.0,    phi=25.0, nup=1),
    "fs_g0":   dict(sd="g",   sat=0.5, lake=False, slide=2, seep=0, wet=0, noflow=0, dmax=0.0, c=2000.0, phi=25.0, nup=1),
    "fs_g1":   dict(sd="g",   sat=0.5, lake=False, slide=2, seep=1, wet=0, noflow=0, dmax=0.0, c=2000.0, phi=25.0, nup=1),
    "fs_l0":   dict(sd=1.0,   sat=1.0, lake=True,  slide=2, seep=0, wet=0, noflow=0, dmax=0.0, c=0.0,    phi=25.0, nup=1),
    "fs_l1":   dict(sd=1.0,   sat=1.0, lake=True,  slide=2, seep=1, wet=0, noflow=0, dmax=0.0, c=0.0,    phi=25.0, nup=1),
    "fs_lq1":  dict(sd=1.0,   sat=0.99975,  lake=True, slide=2, seep=1, wet=0, noflow=0, dmax=0.0, c=0.0,  phi=25.0, nup=1),
    "fs_le1":  dict(sd=1.0,   sat=0.999999, lake=True, slide=2, seep=1, wet=0, noflow=0, dmax=0.0, c=0.0,  phi=25.0, nup=1),
    "fs_m1":   dict(sd=1.0,   sat=1.0, lake=True,  slide=2, seep=1, wet=0, noflow=0, dmax=0.0, c=0.0,    phi=25.0, nup=2, rel=True),
    "fs_m0":   dict(sd=1.0,   sat=1.0, lake=True,  slide=2, seep=1, wet=0, noflow=0, dmax=0.0, c=0.0,    phi=25.0, nup=1, dug=True),
    "fs_gdyn": dict(sd="g",   sat=0.5, lake=False, slide=1, seep=1, wet=0, noflow=0, dmax=0.0, c=2000.0, phi=25.0, nup=5),
    "fs_d2":   dict(sd=2.0,   sat=0.9, lake=False, slide=2, seep=0, wet=0, noflow=0, dmax=0.5, c=0.0,    phi=25.0, nup=1),
    "fs_d1":   dict(sd=2.0,   sat=0.9, lake=False, slide=1, seep=0, wet=0, noflow=0, dmax=0.5, c=0.0,    phi=25.0, nup=1),
    "fs_w1":   dict(sd=1.0,   sat=1.0, lake=False, slide=1, seep=0, wet=1, noflow=0, dmax=0.0, c=0.0,    phi=20.0, nup=1),
    "fs_w0":   dict(sd=1.0,   sat=1.0, lake=False, slide=1, seep=0, wet=0, noflow=0, dmax=0.0, c=0.0,    phi=20.0, nup=1),
    "fs_w2":   dict(sd=1.0,   sat=1.0, lake=False, slide=1, seep=0, wet=1, noflow=0, dmax=0.0, c=0.0,    phi=25.0, nup=1),
    "fs_n1":   dict(sd=2.0,   sat=0.9, lake=False, slide=1, seep=0, wet=0, noflow=1, dmax=0.5, c=0.0,    phi=25.0, nup=2),
    "fs_n0":   dict(sd=2.0,   sat=0.9, lake=False, slide=1, seep=0, wet=0, noflow=0, dmax=0.5, c=0.0,    phi=25.0, nup=2),
}


def xy(i, j):
    """セル (i, j)(1 始まり)の中心の座標。"""
    return (i - 0.5) * DX, (j - 0.5) * DX


def z_of(i, j):
    x, y = xy(i, j)
    return Z0 - A * x - B * y


def sd_of(c, i, j):
    if c["sd"] == "g":
        x, y = xy(i, j)
        return SDG[0] + SDG[1] * x + SDG[2] * y
    return c["sd"]


def h_of(c, i, j):
    return max(0.0, LAKE_E - z_of(i, j)) if c["lake"] else 0.0


def in_patch(i, j):
    """fs_m1 で流動化し、fs_m0 ではじめから掘っておくセルか。"""
    return REL_I[0] <= i <= REL_I[1] and REL_J[0] <= j <= REL_J[1]


def dug(i, j):
    """掘った深さ (m)。"""
    return REL_D if in_patch(i, j) else 0.0


def write_matrix(path, fn):
    with open(path, "w") as f:
        for j in range(1, NY + 1):
            f.write(" ".join(f"{fn(i, j):.6f}" for i in range(1, NX + 1)) + "\n")


def write_inputs():
    os.makedirs("d_fs", exist_ok=True)
    write_matrix("d_fs/z.txt", z_of)
    write_matrix("d_fs/sd_g.txt", lambda i, j: sd_of({"sd": "g"}, i, j))
    write_matrix("d_fs/h_lake.txt", lambda i, j: h_of({"lake": True}, i, j))
    # fs_m1 の崩壊深と、fs_m0 の掘った地形・土層厚・水深(水位は同じ LAKE_E)
    write_matrix("d_fs/rel_m.txt", dug)
    write_matrix("d_fs/z_dug.txt", lambda i, j: z_of(i, j) - dug(i, j))
    write_matrix("d_fs/sd_dug.txt", lambda i, j: 1.0 - dug(i, j))
    write_matrix("d_fs/h_dug.txt", lambda i, j: max(0.0, LAKE_E - (z_of(i, j) - dug(i, j))))


def write_case(name, c):
    tt = c["nup"] * DTG
    isdug, isrel = c.get("dug", False), c.get("rel", False)
    if c["sd"] == "g":
        sdl = "  f_sdtype = 1\n  fn_sd = 'sd_g.txt'        ! 下流へ厚くなる平面\n"
    elif isdug:
        sdl = f"  f_sdtype = 1\n  fn_sd = 'sd_dug.txt'      ! 1 m。掘った所は {1.0 - REL_D:g} m\n"
    else:
        sdl = f"  f_sdtype = 0\n  sd0 = {c['sd']:g}\n"
    if isdug:
        ini = f"  f_htype = 1\n  fn_hinit = 'h_dug.txt'    ! 水位 {LAKE_E:g} m の静水(掘った所は {REL_D:g} m 深い)\n"
    elif c["lake"]:
        ini = f"  f_htype = 1\n  fn_hinit = 'h_lake.txt'   ! 水位 {LAKE_E:g} m の静水(下流側)\n"
    else:
        ini = "  f_htype = 0\n  h0 = 0.0\n"
    zfile = "z_dug.txt" if isdug else "z.txt"
    znote = f"平面 z = {Z0:g} − {A:g} x − {B:g} y" + (f"。一部を {REL_D:g} m 掘る" if isdug else "")
    rel = ""
    if isrel:
        rel = (f"  fn_dbinit = 'rel_m.txt'    ! 湖の下の一部を深さ {REL_D:g} m だけ流動化する\n"
               "  db_reltime = 1.0\n")
    if isrel or isdug:
        rel += "  f_dbwet = 3               ! 崩れた層の水の全部(排水できる水と保持水)が流れへ出る\n"
    with open(f"p_{name}.txt", "w") as f:
        f.write(f"""!======================================================================
! slide: ケース {name}(make_fs.py が生成。構成 5〜8 の説明は make_fs.py の先頭)
!======================================================================
&list_sysparam
  f_gridsystem = 0
  f_govequation = 0
  dt = {DT:g}
  t0 = 0
  tt = {tt:g}
  dt_disp = {tt:g}
  dt_file = {tt:g}
  dt_recrd = {tt:g}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_geomorph = '-'
  fn_gwflow = '-'
  dir_data = 'd_fs'
  dir_result = 'result_{name}'
  dir_save = 'save_{name}'
  f_state_save = 1
  f_out_fs = 1              ! 安全率 Fs の分布(検定が読む)
  f_output_mode = 3         ! テキストと bil(単精度の 2 進。検定は bil を読む)
  f_check_cfl = 0
/
&list_enc
  f_gravity_correction = 2
/
&list_initial
{ini}/
&list_geoinfo
  lx = {NX * DX:g}
  ly = {NY * DX:g}
  nx = {NX}
  ny = {NY}
  f_ztype = 1
  fn_z = '{zfile}'            ! {znote}
  f_rntype = 0
  rn0 = 0.03
{sdl}  sy0 = {SY0:g}
/
&list_gwflow
  f_gwvertical = 2          ! Green-Ampt
  gw_sat0 = {c['sat']:g}             ! 層1の初期飽和度(飽和厚 hw = gw_sat0·sd)
/
&list_gwflow_greenampt
  gw_ksv_mmh = 1.0e-6       ! 浸透能 (mm/h)。正の値が要るので極小値(地下貯留は初期値のまま)
  gw_psif = 0.0
/
&list_geomorph
  dt_geomorph = {DTG:g}
  morfac = 1.0
  f_debris = 1
  db_phi = 35.0
  f_dbres = 1
  f_dbstop = 0
  f_slide = {c['slide']}               ! 1: 判定と流動化 / 2: 判定だけ
  slide_c = {c['c']:g}
  slide_phi = {c['phi']:g}
  slide_gamma = {GAMMA:g}
  f_slide_seep = {c['seep']}          ! 1: 浸透力を全水頭の勾配で入れる
  f_slide_wet = {c['wet']}           ! 1: 間隙水圧で起きる崩壊に限る
  f_slide_noflow = {c['noflow']}        ! 1: 濃い混合体が載るセルを判定しない
  slide_dmax = {c['dmax']:g}          ! 判定・流動化する深さの上限 (m。0 = 全層)
{rel}  fluv_porosity = {POROSITY:g}
/
""")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print("\n".join(CASES))
        return
    write_inputs()
    for name, c in CASES.items():
        write_case(name, c)


if __name__ == "__main__":
    main()
