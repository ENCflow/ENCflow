#!/usr/bin/env python3
# ENCflow/examples/levee_breach/sweep_width.py
# 補足の「破堤幅と流量の関係」の 12 ケースの入力を作り、結果の表を出す(make sweep から呼ぶ)。
#
#   python3 sweep_width.py inputs      破堤口の規定底面運動(data_supp/bm_w<n>/)と設定(param_sweep_<case>.txt)を作る
#   python3 sweep_width.py table [en]  100 分の流量の表を出す(引数 en で英語の見出し)
#
# ケース(<case> = <方式>_w<n>):
#   破堤幅 n = 1・2・3・5 セル。列 21〜22 の堤防の、北から行 50、49〜50、49〜51、48〜52。
#   res  解像堤防 + 規定底面運動(make_breach.py --t0 70 --t1 80。破堤口の全セルが同時に堤底まで下がる)
#   vw0  仮想壁面 + &list_channel_breach、f_br_diag = 0(サイト = 河道セル (20,j) と堤内地セル (21,j) の法線エッジ)
#   vw1  同じで f_br_diag = 1(サイトに触れる斜めエッジも同じ実効天端で下げる)
#   破堤はどれも 70 分に始まり、80 分に全セル(全サイト)が同時に全壊する。設定は param_supp.txt・
#   param_supp_vwall.txt から、破堤口・破堤の時刻・出力先だけを変える(地形・境界・計測は補足と同じ)。
#
# 表: 100 分の測線 1(列 23 の全行。堤内地へ渡る全流量)の流量、広頂堰の目安 1.7·B·H^1.5
#   (B = n × dx、H = 破堤口前の河道のプローブ 2 (18,50) の水位 − 堤底(列 23・行 50 の地盤高))、
#   仮想壁面の解像堤防に対する比。
import glob
import os
import re
import subprocess
import sys

import numpy as np

WIDTHS = {1: (50, 50), 2: (49, 50), 3: (49, 51), 5: (48, 52)}   # 破堤幅 → 破堤口の行(1 始まり、北から)
KINDS = ("res", "vw0", "vw1")
T0, T1, T_READ = 70.0, 80.0, 100.0      # 破堤の開始・全壊、流量を読む時刻(分)
DX = 10.0
COLS, FLOOR_COL, ROW_H = (21, 22), 23, 50   # 堤防の列、堤底を取る列(堤内地側の法尻)、H を測る行
SITE_COLS = (20, 21)                    # 仮想壁面のサイト: 河道セルの列と堤内地セルの列


def sub1(text, old, new, what):
    """old がちょうど 1 回現れることを確かめて置き換える(元の設定の書き方が変わったら止める)。"""
    if text.count(old) != 1:
        sys.exit(f"sweep_width.py: {what} に '{old}' が 1 回だけ現れない(元の設定を確かめる)")
    return text.replace(old, new)


def header(src, n, kind):
    return (f"! sweep_width.py が {src} から作った設定(make sweep。ケース {kind}_w{n})。\n"
            f"! 破堤幅 {n} セル(行 {WIDTHS[n][0]}〜{WIDTHS[n][1]})、{T0:g} 分に破堤を始めて {T1:g} 分に全壊。\n"
            f"! 破堤口・破堤の時刻・出力先のほかは {src} と同じ。手で編集せず、sweep_width.py か元の設定を直して作り直す。\n")


def inputs():
    if not os.path.exists("data_supp/z.txt"):
        sys.exit("sweep_width.py: data_supp/z.txt がない(先に補足の入力を作る: make data_supp/bm/bmlist.txt)")
    res = open("param_supp.txt", encoding="utf-8").read()
    vwall = open("param_supp_vwall.txt", encoding="utf-8").read()
    for p in glob.glob("param_sweep_*.txt"):      # 前回の設定を残さない
        os.remove(p)
    for n, (j1, j2) in WIDTHS.items():
        subprocess.run([sys.executable, "../make_breach.py", "--z", "z.txt", "--cols", str(COLS[0]), str(COLS[1]),
                        "--rows", str(j1), str(j2), "--floor-col", str(FLOOR_COL),
                        "--t0", f"{T0:g}", "--t1", f"{T1:g}", "--out", f"bm_w{n}"],
                       cwd="data_supp", check=True, stdout=subprocess.DEVNULL)
        s = sub1(res, "fn_bmlist = 'bm/bmlist.txt'", f"fn_bmlist = 'bm_w{n}/bmlist.txt'", "param_supp.txt")
        s = sub1(s, "dir_result = 'result_supp'", f"dir_result = 'result_sweep_res_w{n}'", "param_supp.txt")
        with open(f"param_sweep_res_w{n}.txt", "w", encoding="utf-8") as f:
            f.write(header("param_supp.txt", n, "res") + s)
        for d in (0, 1):
            blk = ["&list_channel_breach", f"  f_br_diag = {d}"]
            for k, j in enumerate(range(j1, j2 + 1), start=1):
                blk += [f"  br_cell(:,{k}) = {SITE_COLS[0]}, {j}, {SITE_COLS[1]}, {j}",
                        f"  br_series(:,1,{k}) = 0.0, 1.0",
                        f"  br_series(:,2,{k}) = {T0:.1f}, 1.0",
                        f"  br_series(:,3,{k}) = {T1:.1f}, 0.0"]
            blk.append("/")
            s, cnt = re.subn(r"^&list_channel_breach\n.*?^/\n", "\n".join(blk) + "\n", vwall,
                             count=1, flags=re.S | re.M)
            if cnt != 1:
                sys.exit("sweep_width.py: param_supp_vwall.txt に &list_channel_breach の群がない")
            s = sub1(s, "dir_result = 'result_supp_vwall'", f"dir_result = 'result_sweep_vw{d}_w{n}'",
                     "param_supp_vwall.txt")
            with open(f"param_sweep_vw{d}_w{n}.txt", "w", encoding="utf-8") as f:
                f.write(header("param_supp_vwall.txt", n, f"vw{d}") + s)
    print("written: data_supp/bm_w{1,2,3,5}/ and param_sweep_{res,vw0,vw1}_w{1,2,3,5}.txt (12 cases)")


def at_time(path, t):
    """測線・プローブの CSV(列 2 が分)から時刻 t の行を返す。"""
    a = np.loadtxt(path, delimiter=",", comments="#")
    k = int(np.argmin(np.abs(a[:, 1] - t)))
    if abs(a[k, 1] - t) > 1e-6:
        sys.exit(f"sweep_width.py: {path} に {t:g} 分の行がない")
    return a[k]


def table(en):
    floor = np.loadtxt("data_supp/z.txt")[ROW_H - 1, FLOOR_COL - 1]
    if en:
        print("| Width (cells / sites) | Resolved levee Q (m³/s) | Broad-crested weir 1.7·B·H^1.5 (m³/s) | "
              "Virtual wall f_br_diag = 0 Q / ratio to resolved | f_br_diag = 1 Q / ratio to resolved |")
    else:
        print("| 幅(セル数 / サイト数) | 解像堤防 Q (m³/s) | 広頂堰 1.7·B·H^1.5 (m³/s) | "
              "仮想壁面 f_br_diag = 0 Q / 解像比 | f_br_diag = 1 Q / 解像比 |")
    print("|---:|---:|---:|---:|---:|")
    heads = []
    for n in WIDTHS:
        q = {k: at_time(f"result_sweep_{k}_w{n}/fluxes/flux0001.csv", T_READ)[2] for k in KINDS}
        p = at_time(f"result_sweep_res_w{n}/probes/probe0002.csv", T_READ)
        h = p[2] + p[3] - floor                    # 河道の水位(地盤高 + 水深)− 堤底
        heads.append(h)
        weir = 1.7 * n * DX * h ** 1.5
        print(f"| {n} | {q['res']:.1f} | {weir:.0f} | {q['vw0']:.1f} / {q['vw0'] / q['res']:.2f} | "
              f"{q['vw1']:.1f} / {q['vw1'] / q['res']:.2f} |")
    hs = ", ".join(f"{h:.2f}" for h in heads)
    print(f"(H = {hs} m for widths 1, 2, 3, 5; floor {floor:.3f} m)" if en else
          f"(H = {hs} m(幅 1・2・3・5)、堤底 {floor:.3f} m)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["inputs"]:
        inputs()
    elif args[:1] == ["table"]:
        table("en" in args[1:])
    else:
        sys.exit("usage: python3 sweep_width.py inputs | table [en]")
