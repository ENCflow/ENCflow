#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coastal_compound_flood: 入力マップと各ケースの設定ファイルを作る。

  python3 gen_data.py            入力マップ(data/)と、全ケースの設定(param_<ケース>.txt)を書く
  python3 gen_data.py list       本体の 6 ケースの名前を表示する(Makefile が使う)
  python3 gen_data.py lag        雨と高潮のずれの 8 ケースの名前
  python3 gen_data.py supp       補足(下水道を通った水の割合)の 2 ケースの名前
  python3 gen_data.py check      数値設定の確認の 4 ケースの名前(格子 10 m の data_dx10/ もこのとき使う)

町: 海(西)に面した 800 m × 500 m(40 ha)。防潮堤の背後に幅 120 m の低地(地盤 +0.9 m、窪地の底
+0.64 m)、その東は勾配 1/250 の緩い斜面(東端 +3.6 m)。北・東・南は壁(分水界)。

下水道(管路連続体層 f_gwconduit の入力): 管の諸元から前処理で換算する(式は users_guide/gwflow_models.md §6)。
  枝管網  全セル。径 0.4 m の管が東西・南北に 20 m 間隔で通る格子状の網(枝管と支線をならしたもの)
          通水能密度 = C / 間隔、貯留容量 = 断面積 × 2 / 間隔(2 方向の管)、貯留係数 = 容量 / 径
  幹線    東西の 1 列(町の中央)。函渠 幅 2.5 m × 高さ 1.0 m。斜面の勾配 1/250 で 6.1 m³/s
          (計画降雨 50 mm/h の町全体の流出 5.6 m³/s)。1 セル幅の線として置くので、通水能密度は
          C ÷ (軸エッジの通過幅 0.414 Δx) で与える(下の「1 セル幅の線の通水能」)
  ポンプ井 幹線の海側の端のセル。自由水面をもつ室(面積 100 m²)。吐口と機場はこのセルに置く
  吐口    ポンプ井から防潮堤を抜けて海へ(樋門 2.5 m × 1.6 m、流量係数 0.75 → Cd·A = 3.0 m²。
          フラップつき = 管路の水頭が潮位より高いときだけ流れる)
  機場    ポンプ井の水を堤防の外へ出す(param.txt の &list_struct_pump)

1 セル幅の線の通水能: 管路層は、セルの辺を「軸エッジ 1 本 + 斜めエッジ 2 本」に分け、既定(gwc_diagratio)
  では 8 本の通過幅がどれも 0.414 Δx。1 セル幅の線に沿う流れは軸エッジだけを通るので、与えた密度 × 0.414 Δx が
  線の通水能になる(同じ勾配なら軸の向きでも斜めの向きでも同じ)。面に広がる枝管網は、軸と斜めのエッジを
  合わせて、密度 × セル幅ぶんを運ぶ。

ポンプ井を自由水面にする理由: 吐口は、1 つのセルに町全体の流量を集めて、時間刻みに 1 回だけ水を抜く。
  満管の管(疑似スロット)のセルは、1 回に抜ける水が「疑似スロットの貯留係数 × 潮位との水頭差 × セルの面積」
  までなので、吐口の流量が時間刻みで頭打ちになる。実際の機場と同じように自由水面をもつ室にすると、この
  頭打ちは起きない(users_guide/gwflow.md の吐口の項)。

雨・高潮・機場の値は、このファイルの定数と param.txt(基本ケース)の両方にある。食い違えば止まる(check_base)。
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 町と下水道の諸元
LX_SEA, LX_LAND, LY = 60.0, 800.0, 500.0   # 海の帯の幅、陸の東西・南北の長さ (m)
Z_COAST = 0.90                  # 防潮堤の背後の地盤高 (m)
X_LOW = 120.0                   # 低地の幅 (m)
S_LOW, S_UP = 0.0005, 0.004     # 低地・斜面の勾配
DEP_X, DEP_Y = 70.0, 130.0      # 窪地の中心(防潮堤からの距離、北端からの距離。m)
DEP_D, DEP_RX, DEP_RY = 0.30, 50.0, 80.0   # 窪地の深さと半径 (m)
Z_SEA = -2.0                    # 海底(記録用。海域マスクのセルの標高は潮位 − hsea0 に置かれる)

N_MAN = 0.013                   # 管の粗度係数
D_B, PITCH_B, BURY_B = 0.4, 20.0, 1.5      # 枝管網: 径、間隔、管底の深さ (m)
B_T, H_T, BURY_T = 2.5, 1.0, 2.5           # 幹線: 函渠の幅・高さ、管底の深さ (m)
Y_TRUNK = 250.0                 # 幹線の位置(北端からの距離。m)
A_WELL = 100.0                  # ポンプ井の水面の面積 (m²)
CDA_OUT = 3.0                   # 吐口のオリフィス係数 Cd·A (m²)
INLET = 0.01                    # 枡の密度 (個/m²)
SLOT_B, SLOT_T = 20.0, 10.0     # 疑似スロットの貯留係数 = 貯留係数 ÷ この値(枝管網、幹線とポンプ井)
DIAG = 2.0 / (2.0 + math.sqrt(2.0))        # 管路層の斜めの配分 gwc_diagratio の既定

# ---------------------------------------------------------------- 外力とケース
T_SURGE, DUR_SURGE, ETA_SURGE = 330.0, 150.0, 2.0   # 高潮: ピークの時刻・上げ(下げ)の時間 (分)、高さ (m)
RAIN_PEAK, RAIN_RAMP, RAIN_TOP = 50.0, 60.0, 60.0   # 雨: 強さ (mm/h)、上げ(下げ)の時間・ピークの続く時間 (分)
QP, HP_ON, HP_FULL = 1.5, -1.2, -0.8                # 機場: 能力 (m³/s)、動き始める水位・全力になる水位 (m)

# ケース = (地形の組, 雨のピークのずれ(時間。None = 雨なし), 高潮, 初期飽和度 gw_sat0, 機場, 追加の差し替え)
#   基本ケース compound は param.txt そのもの(雨 + 高潮 + 高い地下水位 + 機場)
CASES = {
    "rain":     ("dx20", 0, False, 0.0, True, {}),
    "surge":    ("dx20", None, True, 0.0, True, {}),
    "rain_gw":  ("dx20", 0, False, 0.9, True, {}),
    "both":     ("dx20", 0, True, 0.0, True, {}),
    "compound": ("dx20", 0, True, 0.9, True, {}),
    "nopump":   ("dx20", 0, True, 0.9, False, {}),
}
LAGS = [-4, -3, -2, -1, 1, 2, 3, 4]
for _l in LAGS:
    CASES["lag_%s%d" % ("m" if _l < 0 else "p", abs(_l))] = ("dx20", _l, True, 0.9, True, {})
CASES["tracer"] = ("dx20", 0, True, 0.9, True, {"wq": True})
CASES["tracer_m1"] = ("dx20", -1, True, 0.9, True, {"wq": True})
CASES["chk_dt"] = ("dx20", 0, True, 0.9, True, {"dt": "0.25"})
CASES["chk_slot"] = ("dx20s", 0, True, 0.9, True, {"gwc_nsubmax": "400"})
CASES["chk_epsh"] = ("dx20", 0, True, 0.9, True, {"gwc_eps_h": "0.005", "gwc_nsubmax": "400"})
CASES["chk_dx10"] = ("dx10", 0, True, 0.9, True, {"gwc_nsubmax": "400"})
GROUPS = {
    "list": ["rain", "surge", "rain_gw", "both", "compound", "nopump"],
    "lag": ["lag_%s%d" % ("m" if l < 0 else "p", abs(l)) for l in LAGS],
    "supp": ["tracer", "tracer_m1"],
    "check": ["chk_dt", "chk_slot", "chk_epsh", "chk_dx10"],
}
GEOMS = {"dx20": (20.0, "data", SLOT_B, SLOT_T),
         "dx20s": (20.0, "data_slot50", 50.0, 50.0),     # 疑似スロットを既定(貯留係数 ÷ 50)にした組
         "dx10": (10.0, "data_dx10", SLOT_B, SLOT_T)}    # 格子 10 m の組


def pipe_circ(d):
    """円管の断面積 A (m²) と満管の通水能 C = (1/n)·A·R^(2/3) (m³/s。流量 = C·√動水勾配)"""
    a = math.pi * d * d / 4.0
    return a, (1.0 / N_MAN) * a * (d / 4.0) ** (2.0 / 3.0)


def pipe_box(b, h):
    """函渠(幅 b × 高さ h)の断面積と満管の通水能"""
    a = b * h
    return a, (1.0 / N_MAN) * a * (a / (2.0 * (b + h))) ** (2.0 / 3.0)


def specs():
    """格子によらない換算値"""
    a_b, c_b = pipe_circ(D_B)
    a_t, c_t = pipe_box(B_T, H_T)
    cap_b = a_b * 2.0 / PITCH_B             # 2 方向の管の体積 ÷ 面積 (m)
    return dict(a_b=a_b, c_b=c_b, a_t=a_t, c_t=c_t, cap_b=cap_b, dens_b=c_b / PITCH_B, sy_b=cap_b / D_B)


def build(dx, slot_b=SLOT_B, slot_t=SLOT_T):
    """格子間隔 dx の全マップを作る(行は北から南、列は西から東)"""
    sp = specs()
    nsea, nxl, ny = int(round(LX_SEA / dx)), int(round(LX_LAND / dx)), int(round(LY / dx))
    nx = nsea + nxl
    ii, jj = np.meshgrid(np.arange(1, nx + 1), np.arange(1, ny + 1))
    xl = (ii - nsea - 0.5) * dx             # 防潮堤からの距離 (m)
    yy = (jj - 0.5) * dx                    # 北端からの距離 (m)
    sea = ii <= nsea
    z = Z_COAST + S_LOW * np.minimum(xl, X_LOW) + S_UP * np.maximum(xl - X_LOW, 0.0)
    z = z - DEP_D * np.exp(-((xl - DEP_X) / DEP_RX) ** 2 - ((yy - DEP_Y) / DEP_RY) ** 2)
    jt = int(Y_TRUNK / dx - 1e-9) + 1       # 幹線の行(1 始まり。y = 250 m を含む行。境目なら北側)
    trunk = (jj == jt) & ~sea
    well = trunk & (ii == nsea + 1)
    wax = (1.0 - DIAG) * dx                 # 軸エッジの通過幅 (m)
    cap_tc = sp["a_t"] / dx + sp["cap_b"]   # 幹線のセル: 幹線の体積 ÷ セル面積 + 枝管網
    sy_t = cap_tc / H_T
    sy_w = min(A_WELL / (dx * dx), 1.0)     # ポンプ井: 水面の面積 ÷ セル面積
    cap = np.where(trunk, cap_tc, sp["cap_b"])
    cnd = np.where(trunk, sp["c_t"] / wax, sp["dens_b"])
    bot = np.where(trunk, z - BURY_T, z - BURY_B)
    sy = np.where(trunk, sy_t, sp["sy_b"])
    slot = np.where(trunk, sy / slot_t, sy / slot_b)
    cap[well] = sy_w * BURY_T               # 井の底(幹線の管底)から地表まで
    sy[well] = sy_w
    slot[well] = sy_w / slot_t
    for a in (cap, cnd):
        a[sea] = 0.0
    bot[sea] = 0.0
    out = np.where(well, CDA_OUT, 0.0)
    inlet = np.where(sea, 0.0, INLET)
    z_out = np.where(sea, Z_SEA, z)
    return dict(dx=dx, nx=nx, ny=ny, nsea=nsea, jt=jt, xl=xl, yy=yy, sea=sea, trunk=trunk, well=well,
                z=z_out, cap=cap, cnd=cnd, bot=bot, sy=sy, slot=slot, inlet=inlet, outfall=out,
                cap_tc=cap_tc, sy_t=sy_t, sy_w=sy_w, wax=wax)


def write_maps(gname):
    dx, dname, slot_b, slot_t = GEOMS[gname]
    g = build(dx, slot_b, slot_t)
    d = os.path.join(HERE, dname)
    os.makedirs(d, exist_ok=True)
    np.savetxt(os.path.join(d, "z.txt"), g["z"], fmt="%.4f")
    np.savetxt(os.path.join(d, "sw.txt"), g["sea"].astype(int), fmt="%d")
    for name, fmt in (("cap", "%.5f"), ("cnd", "%.5f"), ("bot", "%.4f"), ("sy", "%.5f"), ("slot", "%.7f"),
                      ("inlet", "%.4f"), ("outfall", "%.3f")):
        np.savetxt(os.path.join(d, name + ".txt"), g[name], fmt=fmt)
    return g


def cells(g):
    """設定ファイルに書くセル番号(1 始まり): ポンプ井、窪地の底、低地の幹線の上、斜面の中ほど"""
    dx, nsea = g["dx"], g["nsea"]
    col = lambda x: nsea + int(x / dx - 1e-9) + 1
    row = lambda y: int(y / dx - 1e-9) + 1
    return dict(well=(nsea + 1, g["jt"]), dep=(col(DEP_X), row(DEP_Y)),
                low=(col(90.0), g["jt"]), slope=(col(410.0), row(130.0)))


def rain_rows(lag):
    """雨の時系列(分, mm/h)。ピークの中央 = 高潮のピーク + lag 時間"""
    tc = T_SURGE + 60.0 * lag
    t1, t2 = tc - RAIN_TOP / 2 - RAIN_RAMP, tc - RAIN_TOP / 2
    t3, t4 = tc + RAIN_TOP / 2, tc + RAIN_TOP / 2 + RAIN_RAMP
    return [(t1, 0.0), (t2, RAIN_PEAK), (t3, RAIN_PEAK), (t4, 0.0)]


def tide_rows(surge):
    if not surge:
        return [(0.0, 0.0), (720.0, 0.0)]
    return [(0.0, 0.0), (T_SURGE - DUR_SURGE, 0.0), (T_SURGE, ETA_SURGE), (T_SURGE + DUR_SURGE, 0.0)]


def base_lines():
    return open(os.path.join(HERE, "param.txt"), encoding="utf-8").read().splitlines()


def base_value(key):
    """param.txt(基本ケース)の key の値(注釈を除いた文字列)"""
    for line in base_lines():
        if "=" in line and not line.lstrip().startswith("!") and line.split("=")[0].strip() == key:
            return line.split("=", 1)[1].split("!")[0].strip()
    sys.exit("param.txt に %s の行がありません" % key)


def base_pairs(prefix):
    """param.txt の prefix で始まるキー(tival・prval・pump_rule)の値の組の並び"""
    out = []
    for line in base_lines():
        key = line.split("=")[0].strip() if "=" in line and not line.lstrip().startswith("!") else ""
        if key.startswith(prefix):
            out.append(tuple(float(v) for v in line.split("=", 1)[1].split("!")[0].split(",")))
    return out


def check_base():
    """このファイルの定数と param.txt(基本ケース)の雨・高潮・機場が同じことを確かめる"""
    want = {"tival": tide_rows(True), "prval": rain_rows(0), "pump_rule": [(HP_ON, 0.0), (HP_FULL, QP)]}
    for prefix, rows in want.items():
        got = base_pairs(prefix)
        if len(got) != len(rows) or any(abs(a - b) > 1e-9 for g, r in zip(got, rows) for a, b in zip(g, r)):
            sys.exit("param.txt の %s %s が gen_data.py の定数 %s と合いません" % (prefix, got, rows))


def write_param(case):
    """param.txt(基本ケース compound の注釈つきの雛形)の行を差し替えて param_<case>.txt を書く。
    値を差し替えた行は、注釈を「基本ケースは …」に替える。基本ケースは param.txt を使うので書かない。"""
    if case == "compound":
        return
    gname, lag, surge, sat0, pump, extra = CASES[case]
    dx, dname, _, _ = GEOMS[gname]
    g = build(dx)
    c = cells(g)
    rep = {"dir_result": "'result_%s'" % case, "gw_sat0": "%g" % sat0}
    if dname != "data":
        rep["dir_data"] = "'%s'" % dname
    if dx != 20.0:
        rep.update({"nx": "%d" % g["nx"], "ny": "%d" % g["ny"], "dx": "%g" % dx, "dy": "%g" % dx,
                    "pump_in_cell(1:2,1,1)": "%d, %d" % c["well"],
                    "pbxy(:,1)": "%d, %d" % c["well"], "pbxy(:,2)": "%d, %d" % c["dep"],
                    "pbxy(:,3)": "%d, %d" % c["low"], "pbxy(:,4)": "%d, %d" % c["slope"]})
    for k, v in extra.items():
        if k != "wq":
            rep[k] = v
    drop = set()                       # 行ごと注釈に変えるキー(機能を外す)
    if lag is None:
        drop.add("fn_precip")
    if not pump:
        drop.add("fn_structure")
    blocks = {"&list_tide": ["  tival(1:2,%d) = %4.0f, %.1f" % (k + 1, t, v)
                             for k, (t, v) in enumerate(tide_rows(surge))]}
    if lag is not None:
        blocks["&list_precip"] = ["  prval(:,%d) = %4.0f, %4.1f" % (k + 1, t, v)
                                  for k, (t, v) in enumerate(rain_rows(lag))]
    lines = base_lines()
    out = ["! このファイルは gen_data.py が param.txt から作る(ケース %s)。編集は param.txt と gen_data.py で" % case]
    done, cur = set(), None
    for line in lines:
        head = line.strip()
        if head.startswith("&"):
            cur = head.split()[0]
        key = line.split("=")[0].strip() if "=" in line and not head.startswith("!") else None
        if cur in blocks and key and (key.startswith("tival") or key.startswith("prval")):
            if blocks[cur] is not None:                   # 時系列の行をまとめて差し替える
                same = [l for l in lines if l.split("=")[0].strip().startswith(key[:5])]
                new = blocks[cur]
                if [l.split("!")[0].rstrip() for l in same] != new:
                    new = [new[0] + "   ! 基本ケースと違う時系列"] + new[1:]
                    out += new
                else:
                    out += same
                blocks[cur] = None
            continue
        if key in drop:
            out.append("  !" + line.lstrip().split("!")[0].rstrip() + "   ! このケースでは使わない")
            done.add(key)
            continue
        if key == "fn_record" and extra.get("wq"):
            out += [line, "  fn_wq = '-'               ! 水質(下水道から噴出した水に濃度 1 を付けて追う)"]
            continue
        if key in rep:
            lhs, _, tail = line.partition("=")
            old = tail.split("!", 1)[0].strip()
            if old != rep[key]:
                line = "%s= %s" % (lhs, rep[key])
                line = "%-27s ! 基本ケースは %s" % (line, old)
            done.add(key)
        out.append(line)
    missing = (set(rep) | drop) - done
    if missing:
        sys.exit("param.txt に %s の行がありません(ケース %s)" % (sorted(missing), case))
    if extra.get("wq"):
        out += ["",
                "!======================================================================",
                "! 水質: 下水道から地表へ出た水(噴出)に濃度 1 を付ける保存性のトレーサ。",
                "!   地表の濃度 C は「その場の水のうち下水道を通ってきた水の割合」、",
                "!   台帳 wq.csv の in_gwc_g は噴出した水の累積の体積 (m3) と読める",
                "!======================================================================",
                "&list_wq",
                "  wq_gwc_conc = 1.0         ! 噴出した水の濃度(1 = 全部が下水道を通った水)",
                "  f_wq_gwc_in = 1           ! 枡に入った水の分は地表から除く(既定)",
                "/"]
    with open(os.path.join(HERE, "param_%s.txt" % case), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def report(g):
    sp = specs()
    land = ~g["sea"]
    area = land.sum() * g["dx"] ** 2
    c = cells(g)
    print("格子 %g m: %d × %d セル(うち海 %d 列)、陸 %.1f ha" % (g["dx"], g["nx"], g["ny"], g["nsea"], area / 1e4))
    print("  地盤高: 防潮堤の背後 %.2f m、窪地の底 %.2f m、東端 %.2f m" % (g["z"][0, g["nsea"]], g["z"][land].min(), g["z"][0, -1]))
    print("  枝管網: C = %.2f m³/s、通水能密度 %.4f m²/s、容量 %.5f m、貯留係数 %.4f" % (sp["c_b"], sp["dens_b"], sp["cap_b"], sp["sy_b"]))
    print("  幹線: C = %.1f m³/s(勾配 %.4f で %.2f m³/s)、通水能密度 %.3f m²/s(= C ÷ %.3f m)、セルの容量 %.4f m、貯留係数 %.4f"
          % (sp["c_t"], S_UP, sp["c_t"] * math.sqrt(S_UP), sp["c_t"] / g["wax"], g["wax"], g["cap_tc"], g["sy_t"]))
    print("  ポンプ井 (%d, %d): 貯留係数 %.2f、容量 %.3f m、底 %.2f m" % (c["well"] + (g["sy_w"], g["cap"][g["well"]][0], g["bot"][g["well"]][0])))
    print("  計画降雨 %g mm/h の流出 %.2f m³/s、総雨量 %.0f mm = %.0f m³、機場 %.1f m³/s(%.1f mm/h 相当)"
          % (RAIN_PEAK, RAIN_PEAK / 3.6e6 * area, RAIN_PEAK * (RAIN_TOP + RAIN_RAMP) / 60.0,
             RAIN_PEAK * (RAIN_TOP + RAIN_RAMP) / 60.0 / 1e3 * area, QP, QP / area * 3.6e6))
    print("  プローブ: ポンプ井 %s、窪地の底 %s、低地の幹線の上 %s、斜面 %s" % (c["well"], c["dep"], c["low"], c["slope"]))


def main():
    args = sys.argv[1:]
    if args and args[0] in GROUPS:
        print(" ".join(GROUPS[args[0]]))
        return
    check_base()
    for gname in GEOMS:
        g = write_maps(gname)
        if gname != "dx20s":
            report(g)
    for case in CASES:
        write_param(case)
    print("data/・data_slot50/・data_dx10/ のマップと、param_<ケース>.txt %d 本を書いた" % (len(CASES) - 1))


if __name__ == "__main__":
    main()
