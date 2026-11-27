#!/usr/bin/env python3
"""examples/debris_dam の入力と設定ファイルの生成(make が呼ぶ)。

  python3 make_init.py            すべてのケースの入力(data_<地形>/)と設定(param_<ケース>.txt)を書く
  python3 make_init.py list       make run で計算するケース名を、計算する順に 1 行ずつ出す
  python3 make_init.py quick      make quick で計算するケース名を出す
  python3 make_init.py dams       make dams で計算するケース名(堤体をはじめから置く系列)を出す
  python3 make_init.py perturb    make perturb で計算するケース名(流入量を少し変えて結果の幅を見る)を出す

地形は解析式で与え、各格子のセル中心で標本化する(格子間隔を変えても同じ式)。x は本川を下る向き
(西端 0、東が下流)、y は本川の谷筋を 0 として北が正。入力ファイルは先頭行が北端。

  本川     谷底幅 WG の峡谷(谷壁の勾配 TW)。河床勾配 S0。合流点の上流 XB0〜XB1 は谷底が北へ広がる
           盆地(谷底幅 wb。ここに水がたまる)。下流の XV0〜XV1 で谷が開け、その先は幅 WC の低水路と、
           北岸の幅 WFP の氾濫原(集落。岸から離れるほど高い)になる。
  支流     x = XT で北から合流する。谷底幅 WT、谷壁 TW。谷底の勾配は合流点の SA から谷頭の SB へ
           直線的に増す。
  崩壊斜面 谷頭の上の、勾配 SR の平らな斜面(幅 WS × 長さ LS。谷頭とは長さ LF の漏斗でつながる)。
           厚さ DS の崩積土(土層)が載る。ここだけが土層で、ほかは侵食されない基盤。
  雨域     支流の谷底と崩壊斜面(谷壁には降らせない。谷壁の流出が斜面の縁だけを先に飽和させるのを
           避けるための簡略化)。
  家屋     氾濫原の、低水路の岸から 25〜115 m に 30 m おきの 4 列(建物の空隙率 gv = 0.5 のセル)。

地形の変種(GEOMS。感度のケース):
  dx       格子間隔。
  wb       盆地の谷底幅(WG なら峡谷のまま = 湛水量が小さい)。
  sk       合流点の下流 XK0〜XK1 の河床を急な区間にしたときの勾配。
  dam      (高さ, 天端の長さ, 上流の法面勾配, 下流の法面勾配)。合流点に堤体をはじめから置き、上流を
           天端の高さまで湛水させる(決壊の条件を比べる系列。崩壊斜面の土層は置かない)。堤体は土層で、
           侵食される。
  tilt     堤体の天端の、谷を横切る向きの勾配。0 なら天端は水平で、越流は谷の全幅で起こる。正の値を与えると、
           天端は y = YLOW(支流の対岸の側)の幅 DAM_NOTCH を底に両側へ上がり、越流はそこに集まる(土石流が
           つくる堤体の形)。

出力(data_<地形>/):
  z.txt          地盤高 (m)
  sd.txt         土層厚 (m)(崩壊斜面の崩積土か、はじめから置く堤体。それ以外 0)
  hinit_q<Q>.txt 初期水深 (m)(本川の流量 Q の等流水深。堤体を置く地形は、上流の湛水と、その上流の等流)
  prmap.txt      雨域(1: 降る。&list_precip の倍率 × 1 mm/h)
  gv.txt         建物の空隙率(家屋のセル 0.5、ほか 1)
  size.txt       nx ny dx(図化用)
設定: param.txt(基本ケース。注釈つきの雛形)の行を差し替えて param_<ケース>.txt を書く。
"""
import os
import sys

import numpy as np

# ---------------------------------------------------------------- 領域と本川 (m)
LX, Y0, Y1 = 3000.0, -150.0, 650.0   # 領域(x: 0〜LX、y: Y0〜Y1)
S0 = 0.02                            # 本川の河床勾配
ZEND = 10.0                          # 下流端(x = LX)の河床高
WG = 40.0                            # 峡谷部の谷底幅
TW = 0.7                             # 谷壁の勾配(35°)
HCAP = 240.0                         # 北の谷壁の比高の上限(台地)
XB0, XB1, LB = 150.0, 700.0, 80.0    # 上流の盆地の区間と、幅の遷移の長さ
WB = 150.0                           # 盆地の谷底幅(基本)
XV0, XV1 = 1900.0, 2100.0            # 谷が開ける区間(この下流が集落)
WC = 20.0                            # 集落の区間の低水路の幅
WFP = 150.0                          # 氾濫原の幅(北岸)
HFP = 1.2                            # 氾濫原の比高(低水路の河床から岸の肩まで)
SFP = 0.01                           # 氾濫原の横断勾配(岸から離れると高い)
XK0, XK1 = 1000.0, 1400.0            # 合流点の下流の急な区間(地形の sk)
# ---------------------------------------------------------------- 支流と崩壊斜面 (m)
XT, WT = 900.0, 20.0                 # 合流点の x、支流の谷底幅
YH = 320.0                           # 谷頭の y(合流点は y = WG/2)
SA, SB = 0.20, 0.40                  # 支流の谷底の勾配(合流点 → 谷頭)
SR = 0.40                            # 崩壊斜面の勾配
LF, LS, WS = 60.0, 250.0, 200.0      # 漏斗の長さ、崩壊斜面の長さと幅
DS = 3.0                             # 崩積土の厚さ(崩壊斜面の土層)
# ---------------------------------------------------------------- 水理・土砂の定数(param.txt と対)
RN = 0.04                            # マニングの粗度
LAMBDA = 0.4                         # 空隙率
SY0 = 0.2                            # 比湧水量
HOUSE_ROWS = (25.0, 55.0, 85.0, 115.0)   # 家屋の列(低水路の北岸からの距離)
HOUSE_X = (2150.0, 2850.0)           # 家屋のある x の範囲
HOUSE_PITCH = 20.0                   # 家屋の長さ(列に沿う向き)と、隣の家屋との間隔(列ごとに半ピッチずらす)
HOUSE_W = 10.0                       # 家屋の幅(列を横切る向き)
GV_HOUSE = 0.5                       # 家屋のセルの空隙率
# ---------------------------------------------------------------- 計測と対策
PROBE_X = (600.0, 800.0, 880.0, 920.0, 1000.0, 1200.0, 2000.0, 2400.0)   # 計測点の x (m)
FLUX_X = (80.0, 1100.0, 1800.0, 2400.0)                                  # 流量測線の x (m)。上流の線は湖の外
CULV_XIN, CULV_XOUT = 600.0, 1200.0  # 仮排水路(暗渠)の呑口と吐口の x
CULV_B, CULV_D = 4.0, 3.0            # 断面の幅と高さ
CULV_RISE = 1.5                      # 呑口・吐口の敷高(河床からの高さ)

# ---------------------------------------------------------------- 地形とケース
DAM_H = 13.0                         # はじめから置く堤体の高さ(基本ケースの土石流がつくる堤体と同じ程度)
DAM_TILT = 0.11                      # 天端の傾いた堤体の、谷を横切る向きの天端の勾配(基本ケースの土石流がつくる堤体は、
                                     # 最も低い所から支流の側の谷壁の脚まで 35 m で 3.6 m 高い)
YLOW = -15.0                         # 傾いた天端の最も低い所の中心の y (m)(支流の対岸の側。基本ケースの堤体と同じ位置)
DAM_NOTCH = 10.0                     # 最も低い所の幅 (m)(10 m 格子で 1 セル、5 m 格子で 2 セル。高さは格子によらない)
GEOM_DEFAULT = dict(dx=10.0,         # 格子間隔 (m)
                    sk=S0,           # 合流点の下流 XK0〜XK1 の勾配(S0 なら一様)
                    wb=WB,           # 合流点の上流 XB0〜XB1 の谷底幅(WG なら峡谷のまま)
                    dam=None,        # はじめから置く堤体 (高さ m, 天端の長さ m, 上流の法面勾配, 下流の法面勾配)
                    tilt=0.0)        # 堤体の天端の、谷を横切る向きの勾配(0 なら水平。y = YLOW の幅 DAM_NOTCH を底に
                                     # 両側へ上がる)
GEOMS = {
    "g10": dict(),
    "g5": dict(dx=5.0),
    "d12": dict(dam=(DAM_H, 10.0, 0.12, 0.12)),                 # 土石流の堆積に近い、法面の緩い三角形
    "d25": dict(dam=(DAM_H, 10.0, 0.25, 0.25)),                 # 法面の急な三角形(1:4)
    "d25c": dict(dam=(DAM_H, 40.0, 0.25, 0.25)),                # 台形(天端 40 m、法面 1:4)
    "d12s": dict(dam=(DAM_H, 10.0, 0.12, 0.12), wb=WG),         # 峡谷だけ(湛水量が小さい)
    "d12l": dict(dam=(DAM_H, 10.0, 0.12, 0.12), wb=300.0),      # 広い盆地(湛水量が大きい)
    "d12k": dict(dam=(DAM_H, 10.0, 0.12, 0.12), sk=0.10),       # 下流が急
    "d12x5": dict(dam=(DAM_H, 10.0, 0.12, 0.12), dx=5.0),       # 5 m 格子
    "d12t": dict(dam=(DAM_H, 10.0, 0.12, 0.12), tilt=DAM_TILT),             # 天端が支流の側へ上がる(土石流の堆積の形)
    "d12tx5": dict(dam=(DAM_H, 10.0, 0.12, 0.12), tilt=DAM_TILT, dx=5.0),   # 同、5 m 格子
}
DT_PER_DX = 0.01                     # 時間刻み dt = 0.01 Δx (s)
Q_BASE = 40.0                        # 本川の流量 (m³/s)


def geom(name):
    """地形 name の諸元(GEOM_DEFAULT に GEOMS[name] を重ねたもの)。"""
    g = dict(GEOM_DEFAULT)
    g.update(GEOMS[name])
    return g


# ケース: 名前 → (地形, 差し替える行 {キー: 値}, 足す行 {namelist 名: [行, ...]})。先頭の base は param.txt そのもの。
# 差し替えのキー "Q" は本川の流量 (m³/s。初期水深もこの流量の等流水深にする)、"Qin" は流入量だけを変える
# (初期水深は Q のまま。結果の幅を見る摂動)。足す行は、その namelist の終わりの "/" の前に入れる(param.txt に
# ない namelist は末尾に新しく書く)。"culvert" は仮排水路の namelist(culvert_block)に置き換わる
SHORT = {"tt": "1800"}                                   # 堤体ができるまで(30 分)
DAMRUN = {"tt": "3600", "dt_file": "60", "dt_disp": "300", "gw_sat0": "1.0",
          "prval(1:2,1)": "0, 0", "prval(1:2,2)": "60, 0"}   # 堤体を置く系列: 60 分(立ち上がりの遅いケースは 90 分、
                                                             # 決壊口が塞がって放流が遅れる 5 m 格子は 120 分)、
                                                             # 雨なし、堤体は飽和


def dam_case(gname, **rep):
    """堤体をはじめから置く系列のケース(DAMRUN に rep を重ねる)。"""
    r = dict(DAMRUN)
    r.update(rep)
    return (gname, r, {})


# ---- 粒度の幅を持つ堤体(混合粒径と土石流の併用)と、決壊のあとの流水による侵食
# 材料は 2 組。どちらも平均粒径は、比べる単一粒径のケースと同じにする
#   mix_d3cm:  0.5・2・8 cm(平均 3 cm。dam_ref と比べる。最も粗い粒径階も、決壊のあとの流量 40 m³/s で動く)
#   mix_d10cm: 1・5・40 cm(平均 10 cm。dam_d10cm と比べる。40 cm の粒径階は、決壊のあとの流れではほぼ動かない)
MIX3 = ((0.005, 0.02, 0.08), (0.35, 0.40, 0.25), None)
MIX10 = ((0.01, 0.05, 0.40), (0.50, 0.30, 0.20), 0.4)    # 交換層の厚さは最も粗い粒径(既定の「D90 の 2 倍」= 0.28 m はそれより薄い)
BMIX_OUT = "f_out_bmix = 1            ! 交換層の粒径階ごとの割合と、表層の平均粒径 Dm"
T_AFTER = 3 * 3600               # 決壊のあとの計算の長さ (s)


def mix_mean(mix):
    """粒度の平均粒径 (m)。"""
    return sum(d * f for d, f in zip(mix[0], mix[1]))


def mix_lines(mix):
    """混合粒径の行(粒径階の粒径、割合、交換層の厚さ)。"""
    d, f, la = mix
    out = ["f_bedmix = 1                ! 混合粒径(粒径階 × 交換層・下層)。土石流は粒径階ごとの組成を運ぶ",
           "bmix_d = %s   ! 粒径階の粒径 (m)" % ", ".join("%g" % v for v in d),
           "bmix_frac0 = %s   ! 割合(平均 %.1f cm)" % (", ".join("%g" % v for v in f), 100 * mix_mean(mix))]
    if la is not None:
        out.append("bmix_la = %g                ! 交換層の厚さ (m)。最も粗い粒径階の粒径" % la)
    return out


def save_lines(name):
    return ["f_state_save = 1           ! 終わりの状態を保存する(決壊のあとの計算の初期条件)", f"dir_save = 'save_{name}'"]


D10RUN = dict(DAMRUN, db_d50="0.1", fluv_d50="0.1", tt="5400")     # 代表粒径 10 cm の決壊(立ち上がりが遅いので 90 分)


def after_case(src, base, mix, debris=False):
    """決壊のあとの計算: ケース src(差し替える行は base)の終わりの保存を初期条件にして(f_state_restore = 2)、
    本川の流量を流し続ける。debris = False は土石流と斜面安定判定のない構成(掃流砂だけ。流れに残っていた土砂は、
    復元のときその場の河床に積もる)、True は決壊の計算と同じ構成(土石流の式を有効にしたまま)。"""
    r = dict(base)
    r.update({"tt": f"{T_AFTER}", "dt_file": "600", "dt_disp": "1800"})
    if not debris:
        r.update({"f_debris": "0", "f_slide": "0", "f_out_hs": "0", "f_out_fs": "0", "f_out_dmax": "0", "f_out_fmax": "0"})
    add = {"&list_sysparam": ["f_state_restore = 2        ! 保存を初期条件にして、時刻 0 から始める", f"dir_save = 'save_{src}'"]}
    if mix is not None:
        add["&list_geomorph"] = mix_lines(mix)
        add["&list_sysparam"].append(BMIX_OUT)
    return ("d12", r, add)


CASES = {
    # ---- 連鎖(豪雨 → 崩壊 → 土石流 → 天然ダム → 越流 → 決壊 → 洪水)
    "base": ("g10", {}, {}),
    "drain": ("g10", {}, {"&list_sysparam": ["fn_structure = '-'"], "culvert": []}),   # 仮排水路
    "coarse": ("g10", {"db_d50": "0.1", "fluv_d50": "0.1"}, {}),                       # 粗い土砂
    "q80": ("g10", {"Q": "80", "tt": "10800"}, {}),                                    # 本川の流量 2 倍
    # ---- 連鎖の前半(堤体ができるまで)の比較
    "norain": ("g10", {"tt": "1800", "prval(1:2,1)": "0, 0", "prval(1:2,2)": "60, 0"}, {}),   # 雨なし(対照)
    "wet0": ("g10", dict(SHORT, f_dbwet="0", f_dbunsat="0"), {}),                      # 間隙水を連行しない
    "wet2": ("g10", dict(SHORT, f_dbwet="2"), {}),                                     # 保持水を授受しない
    "slide0": ("g10", dict(SHORT, f_slide_seep="0", f_slide_wet="0", f_slide_noflow="0", slide_dmax="0.0"), {}),
    "noflow0": ("g10", dict(SHORT, f_slide_noflow="0"), {}),                          # 濃い混合体が載るセルも判定する
    "g5": ("g5", dict(SHORT), {}),                                                     # 5 m 格子
    # 判定・流動化する深さの上限を土層の半分にする(10 m と 5 m 格子)。はじめの飽和度は、崩壊の時刻が基本ケースと
    # 同じになる値(崩れる飽和度が 0.853 → 0.927 に上がる分。崩れるまでに要る水 14 mm を同じにする)
    "dmax15": ("g10", dict(SHORT, slide_dmax="1.5", gw_sat0="0.9035"), {}),
    "dmax15_dx5": ("g5", dict(SHORT, slide_dmax="1.5", gw_sat0="0.9035"), {}),
    # ---- 堤体をはじめから置く系列(決壊の条件)
    "dam_ref": ("d12", dict(DAMRUN), {"&list_sysparam": save_lines("dam_ref")}),
    "dam_face25": dam_case("d25"),
    "dam_crest40": dam_case("d25c", tt="5400"),
    "dam_small": dam_case("d12s"),
    "dam_large": dam_case("d12l", tt="5400"),
    "dam_d1cm": dam_case("d12", db_d50="0.01", fluv_d50="0.01"),
    "dam_d10cm": ("d12", dict(D10RUN), {"&list_sysparam": save_lines("dam_d10cm")}),
    "dam_delte": dam_case("d12", db_delte="0.0001", tt="5400"),
    "dam_q20": dam_case("d12", Q="20", tt="5400"),
    "dam_q80": dam_case("d12", Q="80"),
    "dam_steep": dam_case("d12k"),
    "dam_nofluv": dam_case("d12", f_fluvial="0", tt="5400"),
    "dam_tau1": dam_case("d12", fluv_taufac="1.0"),
    "dam_imm0": dam_case("d12", f_dbimm="0"),
    "dam_unsat": dam_case("d12", gw_sat0="0.83"),
    "dam_unsat0": dam_case("d12", gw_sat0="0.83", f_dbunsat="0"),
    "dam_dx5": dam_case("d12x5", slide_dmax="1.5", tt="7200"),   # 5 m 格子(slide_dmax は格子間隔の 0.3 倍の 1.5 m)
    "dam_dx5d3": dam_case("d12x5", tt="7200"),               # 5 m 格子で slide_dmax を 3 m のままにする
    "dam_tilt": dam_case("d12t"),                            # 天端が谷を横切る向きに傾いた堤体(細い決壊口ができる)
    "dam_tilt_dx5": dam_case("d12tx5", slide_dmax="1.5", tt="7200"),   # 同、5 m 格子
    # ---- 粒度の幅を持つ堤体(同じ堤体・同じ平均粒径で、土砂を 3 つの粒径階にする)と、決壊のあとの 3 時間
    "mix_d3cm": ("d12", dict(DAMRUN), {"&list_geomorph": mix_lines(MIX3), "&list_sysparam": save_lines("mix_d3cm") + [BMIX_OUT]}),
    "mix_d10cm": ("d12", dict(D10RUN), {"&list_geomorph": mix_lines(MIX10), "&list_sysparam": save_lines("mix_d10cm") + [BMIX_OUT]}),
    "after_one_d3cm": after_case("dam_ref", DAMRUN, None),                    # 単一粒径 3 cm、掃流砂だけ
    "after_mix_d3cm": after_case("mix_d3cm", DAMRUN, MIX3),                   # 粒度の幅(0.5・2・8 cm)、掃流砂だけ
    "after_one": after_case("dam_d10cm", D10RUN, None),                       # 単一粒径 10 cm、掃流砂だけ
    "after_mix": after_case("mix_d10cm", D10RUN, MIX10),                      # 粒度の幅(1・5・40 cm)、掃流砂だけ
    "after_one_debris": after_case("dam_d10cm", D10RUN, None, debris=True),   # 単一粒径 10 cm、土石流の式を有効にしたまま
    "after_mix_debris": after_case("mix_d10cm", D10RUN, MIX10, debris=True),  # 粒度の幅(1・5・40 cm)、土石流の式を有効にしたまま
}
AFTER3 = ("after_one_d3cm", "after_mix_d3cm")         # 決壊のあとの 3 時間、平均 3 cm の組(掃流砂だけ)
AFTER = ("after_one", "after_mix", "after_one_debris", "after_mix_debris")   # 同、平均 10 cm の組
MIXNEW = ("mix_d3cm", "mix_d10cm") + AFTER3 + AFTER   # 粒度の幅を持つ堤体の系列で足すケース(make run には含めない)
MIXED = ("dam_ref", "mix_d3cm", "dam_d10cm", "mix_d10cm") + AFTER3 + AFTER   # make mixed で計算するケース(決壊 4 本と、そのあとの 6 本)
QUICK = ("base", "drain", "dam_ref", "dam_face25", "dam_small", "dam_large")
DAMS = tuple(c for c in CASES if c.startswith("dam_"))
MAIN = tuple(c for c in CASES if c not in MIXNEW)        # make run で計算するケース

# ---- 結果の幅を見る摂動(make perturb): 流入量だけを少し変える。名前の m・p は −・+、数字は %。eps は
#      40.0001 m³/s(+0.00025 %)
PERT_BASE = {"base_m2": "39.2", "base_m1": "39.6", "base_eps": "40.0001", "base_p05": "40.2", "base_p1": "40.4",
             "base_p2": "40.8"}
PERT = {name: ("g10", {"Qin": q}, {}) for name, q in PERT_BASE.items()}
PERT.update({"dam_ref_p1": dam_case("d12", Qin="40.4"), "dam_face25_p1": dam_case("d25", Qin="40.4")})
PERT_TILT = {"m1": "39.6", "eps": "40.0001", "p1": "40.4"}        # 傾いた堤体の流入量の摂動(10 m と 5 m)
PERT.update({f"dam_tilt_{k}": dam_case("d12t", Qin=q) for k, q in PERT_TILT.items()})
PERT.update({f"dam_tilt_dx5_{k}": dam_case("d12tx5", slide_dmax="1.5", tt="7200", Qin=q)
             for k, q in PERT_TILT.items()})
PERT_OF = dict({name: "base" for name in PERT_BASE}, dam_ref_p1="dam_ref", dam_face25_p1="dam_face25")   # もとのケース
PERT_OF.update({f"dam_tilt_{k}": "dam_tilt" for k in PERT_TILT})
PERT_OF.update({f"dam_tilt_dx5_{k}": "dam_tilt_dx5" for k in PERT_TILT})
CASES.update(PERT)


def zf_axis(x, sk=S0):
    """本川の河床高。sk は XK0〜XK1 の区間の勾配(S0 なら一様)。"""
    x = np.asarray(x, dtype=float)
    zf0 = ZEND + S0 * LX + (sk - S0) * (XK1 - XK0)
    return zf0 - S0 * x - (sk - S0) * np.clip(x - XK0, 0.0, XK1 - XK0)


def village_frac(x):
    """集落の区間への遷移(峡谷 0 → 集落 1)。"""
    return np.clip((np.asarray(x, dtype=float) - XV0) / (XV1 - XV0), 0.0, 1.0)


def channel_half(x):
    """本川の低水路の半幅(峡谷 WG/2 → 集落 WC/2)。"""
    return WG / 2 + (WC / 2 - WG / 2) * village_frac(x)


def basin_north(x, wb=WB):
    """上流の盆地で、谷底が北へ広がる幅(XB0〜XB1 で wb − WG。両端は長さ LB で 0 へ)。"""
    x = np.asarray(x, dtype=float)
    return (wb - WG) * np.clip((x - XB0) / LB, 0.0, 1.0) * np.clip((XB1 + LB - x) / LB, 0.0, 1.0)


def trib_axis(y, sk=S0):
    """支流の谷筋〜崩壊斜面の軸の標高(y: 合流点 WG/2 から北へ)。"""
    y = np.asarray(y, dtype=float)
    yj = WG / 2
    t = np.clip(y - yj, 0.0, YH - yj)
    rise = SA * t + 0.5 * (SB - SA) * t * t / (YH - yj)
    s = y - YH
    return (zf_axis(XT, sk) + rise + SR * np.clip(s, 0.0, LF + LS)
            + TW * np.clip(s - (LF + LS), 0.0, None))


def trib_half(y):
    """支流の谷底〜漏斗〜崩壊斜面の半幅。"""
    s = np.asarray(y, dtype=float) - YH
    return np.where(s <= 0, WT / 2, WT / 2 + (WS / 2 - WT / 2) * np.clip(s / LF, 0.0, 1.0))


def terrain(x, y, sk=S0, wb=WB):
    """地盤高(堤体を除く)。本川の谷と、支流の谷・崩壊斜面の低い方。"""
    fv = village_frac(x)
    half = channel_half(x)
    yn = y - half - basin_north(x, wb)                      # 谷底(低水路)の北の縁からの距離
    wfp, hfp = WFP * fv, HFP * fv
    bank = np.minimum(hfp, TW * np.clip(yn, 0.0, None))     # 岸の法面(勾配 TW で氾濫原の高さまで)
    zn = np.where(yn <= wfp, bank + SFP * np.clip(yn, 0.0, None),
                  bank + SFP * wfp + TW * (yn - wfp))
    zn = np.minimum(np.where(yn <= 0, 0.0, zn), HCAP)
    zs = TW * np.clip(-y - half, 0.0, None)
    zmain = zf_axis(x, sk) + np.where(y >= 0, zn, zs)
    ztrib = trib_axis(y, sk) + TW * np.clip(np.abs(x - XT) - trib_half(y), 0.0, None)
    return np.where(y > WG / 2, np.minimum(zmain, ztrib), zmain)


def block_dam(x, y, g):
    """合流点に置く堤体の厚さ(地形の dam)。堤体の表面と地盤高の差(正の所だけ)。"""
    hd, lc, sup, sdn = g["dam"]
    top = (zf_axis(XT, g["sk"]) + hd - sup * np.clip(XT - lc / 2 - x, 0.0, None)
           - sdn * np.clip(x - XT - lc / 2, 0.0, None)
           + g["tilt"] * np.clip(np.abs(y - YLOW) - DAM_NOTCH / 2, 0.0, None))
    return np.clip(top - terrain(x, y, g["sk"], g["wb"]), 0.0, None)


def slab_mask(x, y):
    """崩積土の載る範囲(崩壊斜面)。"""
    s = y - YH
    return (s >= LF) & (s <= LF + LS) & (np.abs(x - XT) <= WS / 2)


def rain_mask(x, y):
    """雨域(支流の谷底・漏斗・崩壊斜面)。"""
    return (np.abs(x - XT) <= trib_half(y)) & (y > WG / 2) & (y - YH <= LF + LS)


def normal_depth(q, width):
    """幅の広い長方形断面の等流水深(マニング)。"""
    return (q * RN / (width * np.sqrt(S0))) ** 0.6


def grid(dx):
    nx = int(round(LX / dx))
    ny = int(round((Y1 - Y0) / dx))
    xc = (np.arange(nx) + 0.5) * dx
    yc = Y1 - (np.arange(ny) + 0.5) * dx
    return nx, ny, xc, yc


def house_mask(x, y, dx):
    """家屋のセル(氾濫原の 4 列。長さ HOUSE_PITCH × 幅 HOUSE_W の家屋を、列ごとに半ピッチずらして並べる。
    セル中心が家屋の中にあるセル。10 m 格子で 1 棟 2 セル、5 m 格子で 8 セル)。"""
    d = y - channel_half(x)
    m = np.zeros(x.shape, dtype=bool)
    inx = (x >= HOUSE_X[0]) & (x <= HOUSE_X[1])
    for k, yy in enumerate(HOUSE_ROWS):
        col = (np.floor(x / HOUSE_PITCH).astype(int) % 2) == (k % 2)
        m |= inx & col & (np.abs(d - yy) < HOUSE_W / 2)
    return m


def fields(name):
    """地形 name の格子と、地盤高・土層厚。返り値は (諸元, x, y, 堤体のない地盤高, 地盤高, 土層厚)。
    堤体を置く地形は、崩壊斜面の土層を置かない(土石流を起こさない)。"""
    g = geom(name)
    nx, ny, xc, yc = grid(g["dx"])
    x, y = np.meshgrid(xc, yc)
    z0 = terrain(x, y, g["sk"], g["wb"])
    if g["dam"]:
        sd = block_dam(x, y, g)
        z = z0 + sd
    else:
        sd = np.where(slab_mask(x, y), DS, 0.0)
        z = z0
    return g, x, y, z0, z, sd


def lake_level(g):
    """堤体を置く地形の、はじめの湛水位(天端の高さ)。"""
    return float(zf_axis(XT, g["sk"])) + g["dam"][0]


def initial_depth(g, x, y, z, q):
    """初期水深。本川の谷底(盆地は広がった谷底の全幅)の等流水深。堤体を置く地形は、堤体の上流を
    湛水位まで満たし、下流は水なし。"""
    half = channel_half(x)
    north = basin_north(x, g["wb"])
    h = np.where((y > -half) & (y < half + north), normal_depth(q, 2 * half + north), 0.0)
    if g["dam"]:
        h = np.where(x < XT, np.maximum(np.clip(lake_level(g) - z, 0.0, None), h), 0.0)
    return h


def write_geom(name, flows):
    g, x, y, z0, z, sd = fields(name)
    dx = g["dx"]
    nx, ny, xc, yc = grid(dx)
    d = f"data_{name}"
    os.makedirs(d, exist_ok=True)
    np.savetxt(f"{d}/z.txt", z, fmt="%.3f")
    np.savetxt(f"{d}/sd.txt", sd, fmt="%.3f")
    np.savetxt(f"{d}/prmap.txt", np.where(rain_mask(x, y), 1.0, 0.0), fmt="%.1f")
    np.savetxt(f"{d}/gv.txt", np.where(house_mask(x, y, dx), GV_HOUSE, 1.0), fmt="%.2f")
    for q in sorted(flows):
        np.savetxt(f"{d}/hinit_q{q:g}.txt", initial_depth(g, x, y, z, q), fmt="%.4f")
    with open(f"{d}/size.txt", "w") as f:
        f.write(f"{nx} {ny} {dx:g}\n")


def floor_rows(dx):
    """本川の谷底(峡谷部)の行番号(1 始まり。北端が 1)。"""
    nx, ny, xc, yc = grid(dx)
    return [j + 1 for j in range(ny) if abs(yc[j]) < WG / 2]


def inflow_block(dx, q):
    """上流端(西辺)の流入セル(本川の谷底)と流量の行。"""
    lines = [f"  inflow_cell(:,{k},1) = 1, {j}" for k, j in enumerate(floor_rows(dx), 1)]
    lines += [f"  inflow_val(:,1,1) = 0, {q:g}", f"  inflow_val(:,2,1) = 99999, {q:g}"]
    return "\n".join(lines)


def record_block(dx):
    """計測点(本川の谷筋)と流量測線の行。"""
    nx, ny, xc, yc = grid(dx)
    jm = int(np.argmin(np.abs(yc + dx / 2))) + 1      # 谷筋のすぐ南の行(y = −Δx/2)
    ix = lambda xx: int(xx / dx) + 1
    lines = ["  pbxytype = 0"]
    lines += [f"  pbxy(:,{n}) = {ix(xx)}, {jm}" for n, xx in enumerate(PROBE_X, 1)]
    lines += ["  flxytype = 0"]
    lines += [f"  flxy(:,{n}) = {ix(xx)}, {ny}, {ix(xx)}, 1" for n, xx in enumerate(FLUX_X, 1)]
    return "\n".join(lines)


def culvert_block(dx):
    """仮排水路(暗渠 1 本。呑口は堤体の上流、吐口は下流の、谷底の幅のセル)の行。"""
    ix = lambda xx: int(xx / dx) + 1
    rows = floor_rows(dx)
    lines = [f"culv_in_cell(:,{k},1) = {ix(CULV_XIN)}, {j}" for k, j in enumerate(rows, 1)]
    lines += [f"culv_out_cell(:,{k},1) = {ix(CULV_XOUT)}, {j}" for k, j in enumerate(rows, 1)]
    zin = float(zf_axis(CULV_XIN)) + CULV_RISE
    zout = float(zf_axis(CULV_XOUT)) + CULV_RISE
    lines += [f"culv_width(1) = {CULV_B:g}             ! 断面の幅 (m)",
              f"culv_height(1) = {CULV_D:g}            ! 断面の高さ (m)",
              f"culv_zin(1) = {zin:.2f}             ! 呑口の敷高(河床 + {CULV_RISE:g} m。平常の水位より高い)",
              f"culv_zout(1) = {zout:.2f}            ! 吐口の敷高",
              f"culv_length(1) = {CULV_XOUT - CULV_XIN:g}          ! 管路の長さ (m)"]
    return lines


def write_param(case):
    """param.txt(基本ケースの注釈つきの雛形)の行を差し替えて param_<case>.txt を書く。
    基本ケース(base)は param.txt を使うので書かない。値を差し替えた行は、注釈を「基本ケースは …」に替える。"""
    if case == "base":
        return
    gname, rep, add = CASES[case]
    add = {k: list(v) for k, v in add.items()}
    dx = geom(gname)["dx"]
    dx0 = geom("g10")["dx"]
    nx, ny, xc, yc = grid(dx)
    rep = dict(rep)
    q = float(rep.pop("Q", Q_BASE))
    qin = float(rep.pop("Qin", q))                 # 流入量だけを変える(初期水深は q のまま)
    rep.update({"dir_data": f"'data_{gname}'", "dir_result": f"'result_{case}'",
                "fn_hinit": f"'hinit_q{q:g}.txt'"})
    if dx != dx0:
        rep.update({"dt": f"{DT_PER_DX * dx:g}", "nx": f"{nx}", "ny": f"{ny}",
                    "dx": f"{dx:g}", "dy": f"{dx:g}"})
    if "culvert" in add:
        add.pop("culvert")
        add["&list_struct_culvert"] = culvert_block(dx)
    lines = open("param.txt", encoding="utf-8").read().splitlines()
    out = [f"! このファイルは make_init.py が param.txt から生成する(ケース {case})。編集は param.txt と make_init.py で"]
    done = set()
    skip = None
    cur = None                                      # いま読んでいる namelist の名前
    for line in lines:
        if skip:                                    # 差し替える namelist の本体を読み飛ばす
            if line.strip() == "/":
                out.append("/")
                skip = None
                cur = None
            continue
        head = line.strip()
        if head.startswith("&"):
            cur = head.split()[0]
        elif head == "/":
            out += ["  " + a for a in add.pop(cur, [])]
            cur = None
        if cur == "&list_bound_inflow" and head.startswith("&") and (qin != Q_BASE or dx != dx0):
            out += [line, inflow_block(dx, qin)]
            skip = True
            continue
        if cur == "&list_record" and head.startswith("&") and dx != dx0:
            out += [line, record_block(dx)]
            skip = True
            continue
        key = line.split("=")[0].strip() if "=" in line and not line.lstrip().startswith("!") else None
        if key in rep:
            lhs, _, tail = line.partition("=")
            old = tail.split("!", 1)[0].strip()
            if old != rep[key]:                     # 値が同じなら行(注釈も)をそのまま残す
                line = f"{lhs}= {rep[key]}"
                line = f"{line:<27} ! 基本ケースは {old}"
            done.add(key)
        out.append(line)
    missing = set(rep) - done
    if missing:
        sys.exit(f"param.txt に {sorted(missing)} の行がありません(ケース {case})")
    for name, rows in add.items():                  # param.txt にない namelist
        out += ["", name] + ["  " + a for a in rows] + ["/"]
    with open(f"param_{case}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def case_flow(case):
    """初期水深を決める本川の流量 (m³/s)。"""
    return float(CASES[case][1].get("Q", Q_BASE))


def case_inflow(case):
    """上流端から入れる流量 (m³/s)。"""
    return float(CASES[case][1].get("Qin", case_flow(case)))


def main():
    args = sys.argv[1:]
    for key, names in (("list", MAIN), ("quick", QUICK), ("dams", DAMS), ("perturb", PERT), ("mixed", MIXED)):
        if args and args[0] == key:
            print("\n".join(names))
            return
    flows = {}
    for case, (gname, rep, add) in CASES.items():
        flows.setdefault(gname, set()).add(case_flow(case))
    for gname, qs in flows.items():
        write_geom(gname, qs)
    for case in CASES:
        write_param(case)


if __name__ == "__main__":
    main()
