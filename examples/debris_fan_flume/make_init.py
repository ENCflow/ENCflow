#!/usr/bin/env python3
"""debris_fan_flume の入力と設定の生成(高橋・中川・山敷 1991 の水路実験: 土石流扇状地の形成と侵食)

    python3 make_init.py          全ケースの入力(data_dx5/・data_dx25/)と設定(param_<ケース>.txt)を書く
    python3 make_init.py list     計算する順のケース名を表示する(Makefile が使う)

実験(同論文 §3。水路と材料は前報の高橋・中川・原田 1990 の実験 2):
  幅 10 cm・勾配 18° の水路の、下流端から 5.5〜8.5 m の 3 m に厚さ 10 cm の材料を敷いて飽和させ、上流から
  600 cc/s を 20 秒給水して土石流を起こす。水路の下流端に勾配 5° の氾濫台をつなぎ、扇状地をつくる。
  そのあと水路から清水 300 cc/s を 10 分流して、扇状地を侵食させる。材料は 5 種類の珪砂の混合
  (平均粒径 3.04 mm、最大 11 mm、√(d84/d16) = 6.12)。
座標: x は水路を下る向き(水平距離)。水路の出口が x = XO、水路の軸が y = 0。斜面に沿う長さは水平距離に
  直す(18° の水路は cos 18° 倍)。材料の厚さは鉛直の厚さ(床に直角な 10 cm を cos 18° で割る)。
氾濫台の大きさ・水路の上流端の形・固定床の粗さは論文に書かれていないので、ここで決めた値(README)。
設定は param.txt(ケース form の注釈つきの雛形)の行を差し替え・削除・追加して書く。
"""
import math
import sys

# ---- 幾何(m)
TH_FLUME = math.radians(18.0)    # 水路の勾配
TH_BOARD = math.radians(5.0)     # 氾濫台の勾配(流下方向。横断方向は水平)
W_FLUME = 0.10                   # 水路の幅
XO = 8.30                        # 水路の出口の x(水平距離。上流端 x = 0 から)
LX, LY = 10.0, 1.4               # 計算領域(氾濫台は x = XO〜LX の 1.7 m × 幅 1.4 m。三方が自由流出)
ZO = 0.30                        # 出口の氾濫台の高さ(基準は任意)
S_UP, S_DN = 8.5, 5.5            # 材料を敷いた区間(出口からの、床に沿う距離)
T_BED = 0.10                     # 材料の厚さ(床に直角)
XB1 = XO - S_UP * math.cos(TH_FLUME)     # 材料の区間の上流端の x(0.216)
XB2 = XO - S_DN * math.cos(TH_FLUME)     # 同、下流端の x(3.069)
SD_BED = T_BED / math.cos(TH_FLUME)      # 材料の鉛直の厚さ(0.105)
LAMBDA = 0.35                    # 材料の空隙率(論文の c* = 0.65)
# ---- 給水
Q_FORM, T_FORM = 6.0e-4, 20.0    # 形成: 600 cc/s を 20 秒
Q_ERO, T_ERO = 3.0e-4, 600.0     # 侵食: 清水 300 cc/s を 10 分
# ---- 材料の粒度(前報の Fig. 10 の累積曲線の段から読み取った 5 つの粒径集団。読み取りは概略で、割合は
#      平均粒径 3.04 mm に合うように決めた。README)
D_CLASS = (0.17e-3, 0.55e-3, 1.4e-3, 4.5e-3, 8.0e-3)      # 粒径階の粒径 (m)
F_CLASS = (0.18, 0.17, 0.22, 0.25, 0.18)                  # 粒径階の割合
D_MEAN = 3.04e-3                 # 平均粒径(論文の d_L。単一粒径の計算と土石流の式に使う)
LA = 0.008                       # 交換層厚 (m)(最大の粒径階の粒径)
# ---- 格子
GRIDS = {"dx5": 0.05, "dx25": 0.025}    # 格子間隔(論文の扇状地の計算は 5 cm)
DT_PER_DX = 0.08                 # 時間刻み dt = 0.08 Δx (s)(5 cm で 0.004 s)


def grid(dx):
    nx, ny = int(round(LX / dx)), int(round(LY / dx))
    xc = [(i + 0.5) * dx for i in range(nx)]
    yc = [-LY / 2 + (j + 0.5) * dx for j in range(ny)]
    return nx, ny, xc, yc


def in_flume(y):
    return abs(y) < W_FLUME / 2


def board_z(x):
    """氾濫台の面の高さ(x >= XO)。"""
    return ZO - (x - XO) * math.tan(TH_BOARD)


def fields(dx):
    """(z, sd, mask) の 2 次元リスト [j][i]。z は土層の表面、sd は土層厚(鉛直)。水路の外(x < XO で幅の外)は
    領域外。材料の区間より上流の水路の床は、材料の表面の高さの固定床(給水が段を落ちないように)。"""
    nx, ny, xc, yc = grid(dx)
    z, sd, mask = [], [], []
    for y in yc:
        zr, sr, mr = [], [], []
        for x in xc:
            if x < XO:
                zz = ZO + (XO - x) * math.tan(TH_FLUME)
                s = 0.0
                if x < XB2:
                    zz += SD_BED
                    if x >= XB1:
                        s = SD_BED
                m = 1 if in_flume(y) else 0
            else:
                zz, s, m = board_z(x), 0.0, 1
            zr.append(zz)
            sr.append(s)
            mr.append(m)
        z.append(zr)
        sd.append(sr)
        mask.append(mr)
    return z, sd, mask


def write_geom(gname):
    import os
    dx = GRIDS[gname]
    z, sd, mask = fields(dx)
    d = "data_" + gname
    os.makedirs(d, exist_ok=True)
    with open(d + "/z.txt", "w") as f:
        f.write("\n".join(" ".join("%.6f" % v for v in r) for r in z) + "\n")
    with open(d + "/sd.txt", "w") as f:
        f.write("\n".join(" ".join("%.6f" % v for v in r) for r in sd) + "\n")
    with open(d + "/mask.txt", "w") as f:
        f.write("\n".join(" ".join("%d" % v for v in r) for r in mask) + "\n")


def flume_rows(dx):
    """水路の幅に入る行番号(1 始まり)。"""
    nx, ny, xc, yc = grid(dx)
    return [j + 1 for j, y in enumerate(yc) if in_flume(y)]


def inflow_block(dx, series):
    """上流端(西辺)の水路のセルからの給水。series は [(時刻 min, 流量 m3/s), ...]。"""
    rows = flume_rows(dx)
    lines = [f"  inflow_cell(:,{k},1) = 1, {j}" for k, j in enumerate(rows, 1)]
    lines += [f"  inflow_val(:,{k},1) = {t:g}, {q:g}" for k, (t, q) in enumerate(series, 1)]
    return "\n".join(lines)


def record_block(dx):
    """計測点: 水路の出口の 1 セル上流の、水路の幅のセル。流量測線も同じ断面。"""
    rows = flume_rows(dx)
    io = int(round(XO / dx))                   # 水路の最後の列(1 始まり。出口のすぐ上流)
    lines = ["  pbxytype = 0"]
    lines += [f"  pbxy(:,{k}) = {io}, {j}" for k, j in enumerate(rows, 1)]
    lines += ["  flxytype = 0", f"  flxy(:,1) = {io}, {rows[-1]}, {io}, {rows[0]}"]
    return "\n".join(lines)


SERIES_FORM = [(0.0, Q_FORM), (T_FORM / 60.0, Q_FORM), (T_FORM / 60.0 + 1.0e-4, 0.0), (9999.0, 0.0)]
SERIES_ERO = [(0.0, Q_ERO), (9999.0, Q_ERO)]
# 土石流の行(侵食の段の掃流砂だけのケースで消す)
DEBRIS_KEYS = ("f_debris", "f_dbed", "f_dbres", "db_phi", "db_d50", "db_delte", "db_deltd", "f_dbimm", "db_immexp",
               "f_dbsel", "f_dbstop", "db_vstop", "db_wstop", "f_dbwet", "db_satbed", "f_out_hs")
# 混合粒径の行(単一粒径のケースで消す)
MIX_KEYS = ("f_bedmix", "bmix_d", "bmix_frac0", "bmix_la", "f_out_bmix")
SINGLE = {k: None for k in MIX_KEYS}
SINGLE_DB = dict(SINGLE, f_dbsel=None)   # 土石流を残す単一粒径のケース(選択子は混合粒径が前提なので行を消す)
NODEBRIS = {k: None for k in DEBRIS_KEYS}


def ero(src, **rep):
    """侵食の段: ケース src の保存を初期条件にして(f_state_restore = 2。保存は書かない)、清水を 10 分流す。"""
    r = {"tt": f"{T_ERO:g}", "dt_disp": "60", "dt_file": "60", "dt_recrd": "1.0", "f_state_save": "0",
         "f_state_restore": "2", "dir_save": f"'save_{src}'", "inflow": SERIES_ERO}
    r.update(rep)
    return r


# ケース: 名前 → (格子, 差し替える行 {キー: 値。None はその行を消す。"inflow" は給水の時系列})
CASES = {
    # ---- 形成(土石流。給水 600 cc/s を 20 秒、そのあと 20 秒)
    "form": ("dx5", {}),                                   # 混合粒径 5 階(param.txt そのもの)
    "form_single": ("dx5", dict(SINGLE_DB)),               # 単一粒径 3.04 mm
    "form_dx25": ("dx25", {}),                             # 格子 2.5 cm
    # 土石流の式の侵食を動ける粒径階に限る(f_dbsel。1 = 粒径階ごとの式の印字どおり、2 = 本文のかさの侵食速度)
    "form_sel1": ("dx5", {"f_dbsel": "1"}),
    "form_sel2": ("dx5", {"f_dbsel": "2"}),
    # ---- 侵食(清水 300 cc/s を 10 分)。掃流砂だけ(土石流のない構成に復元)と、土石流の式を有効にしたまま
    "ero": ("dx5", ero("form", **NODEBRIS)),               # 混合粒径、掃流砂だけ
    "ero_single": ("dx5", ero("form_single", **NODEBRIS, **SINGLE)),   # 単一粒径、掃流砂だけ
    "ero_debris": ("dx5", ero("form")),                    # 混合粒径、土石流の式を有効にしたまま
    "ero_debris_single": ("dx5", ero("form_single", **SINGLE_DB)),     # 単一粒径、同
    # 同じ扇状地(form の保存)から、土石流の式を有効にしたまま、侵食を動ける粒径階に限る
    "ero_sel1": ("dx5", ero("form", f_dbsel="1")),
    "ero_sel2": ("dx5", ero("form", f_dbsel="2")),
}
ORDER = ("form", "form_single", "form_dx25", "form_sel1", "form_sel2",
         "ero", "ero_single", "ero_debris", "ero_debris_single", "ero_sel1", "ero_sel2")


def write_param(case):
    """param.txt(ケース form の注釈つきの雛形)の行を差し替え・削除して param_<case>.txt を書く。"""
    if case == "form":
        return
    gname, rep = CASES[case]
    rep = dict(rep)
    dx = GRIDS[gname]
    nx, ny, xc, yc = grid(dx)
    series = rep.pop("inflow", SERIES_FORM)
    rep.update({"dir_data": f"'data_{gname}'", "dir_result": f"'result_{case}'"})
    rep.setdefault("dir_save", f"'save_{case}'")
    if gname != "dx5":
        rep.update({"dt": f"{DT_PER_DX * dx:g}", "nx": f"{nx}", "ny": f"{ny}"})
    lines = open("param.txt", encoding="utf-8").read().splitlines()
    out = [f"! このファイルは make_init.py が param.txt から生成する(ケース {case})。編集は param.txt と make_init.py で"]
    done = set()
    skip = False
    cur = None
    for line in lines:
        head = line.strip()
        if skip:                                   # 差し替える namelist の本体を読み飛ばす
            if head == "/":
                out.append("/")
                skip = False
                cur = None
            continue
        if head.startswith("&"):
            cur = head.split()[0]
            if cur == "&list_bound_inflow":
                out += [line, inflow_block(dx, series)]
                skip = True
                continue
            if cur == "&list_record":
                out += [line, record_block(dx)]
                skip = True
                continue
        elif head == "/":
            cur = None
        key = line.split("=")[0].strip() if "=" in line and not line.lstrip().startswith("!") else None
        if key in rep:
            done.add(key)
            if rep[key] is None:
                continue                           # 行を消す
            lhs, _, tail = line.partition("=")
            old = tail.split("!", 1)[0].strip()
            if old != rep[key]:
                line = f"{lhs}= {rep[key]}"
                line = f"{line:<30}! ケース form は {old}"
        out.append(line)
    missing = set(rep) - done
    if missing:
        sys.exit(f"param.txt に {sorted(missing)} の行がありません(ケース {case})")
    with open(f"param_{case}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print("\n".join(ORDER))
        return
    for gname in sorted({g for g, _ in CASES.values()}):
        write_geom(gname)
    for case in CASES:
        write_param(case)


if __name__ == "__main__":
    main()
