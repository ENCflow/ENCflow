#!/usr/bin/env python3
# ENCflow/examples/source_area/sweep.py
# 基本の 3 ケース(param.txt・param_surface.txt・param_vertical.txt)から、斜面の粗度・土層・雨の強さ
# などを変えた設定 param_sweep_<case>.txt を作る(make sweep から呼ぶ)。
#
#   python3 sweep.py inputs    設定を作る(前回の param_sweep_*.txt は消す)
#   python3 sweep.py targets   make の実行ターゲット名(run-sweep_<case>)を並べて出す
#   python3 sweep.py list      ケースの一覧(名前・元の設定・変える項目)を出す
#
# ケース(<case>):
#   surface_n06・n1・n2・n3・n5・n10・n30  浸透なし。斜面の粗度 rn0 = 0.6・1・2・3・5・10・30
#                                 (基本の 0.3 は param_surface.txt)
#   surface_dif_n03・n3・n10      浸透なし + 地表の流れを拡散波(f_govequation = 1)。rn0 = 0.3・3・10
#   vertical_n3                   鉛直浸透のみ。rn0 = 3
#   process_n1                    過程計算。rn0 = 1(地表の粗度への感度)
#   process_dif                   過程計算 + 地表の流れを拡散波
#   process_k3600・k10000・k100000  過程計算。側方飽和透水係数 gw_ksh_mmh = 3600・10000・100000 mm/h
#                                 (基本は 36000 mm/h。等価粗度が土層の通しやすさでどう変わるかを見る)
#   process_sd1                   過程計算。土層厚 sd0 = 1 m(基本は 0.5 m)
#   process_l2                    過程計算。土層の側方を 3600 mm/h に下げ、その下に比湧水量の小さい第 2 層
#                                 (f_gwlayer2 = 1。param.txt の &list_gwflow_layer2)を置く
#   process_r30                   過程計算。雨を 30 mm/h に(降雨を param_rain30.txt に差し替え、dt = 2 s)
#   surface_r30_n03・n1・n3       浸透なし。雨 30 mm/h で rn0 = 0.3・1・3
# 変えるのは下の CASES の項目と出力先だけで、地形・河道・計測は元の設定と同じ(降雨と時間刻みは、
# 雨の強さのケースだけが変える)。
import glob
import os
import re
import sys

# 名前: (元の設定, {項目: 値})
CASES = {
    "surface_n06": ("param_surface.txt", {"rn0": "0.6"}),
    "surface_n1": ("param_surface.txt", {"rn0": "1.0"}),
    "surface_n2": ("param_surface.txt", {"rn0": "2.0"}),
    "surface_n3": ("param_surface.txt", {"rn0": "3.0"}),
    "surface_n5": ("param_surface.txt", {"rn0": "5.0"}),
    "surface_n10": ("param_surface.txt", {"rn0": "10.0"}),
    "surface_n30": ("param_surface.txt", {"rn0": "30.0"}),
    "surface_dif_n03": ("param_surface.txt", {"f_govequation": "1"}),
    "surface_dif_n3": ("param_surface.txt", {"rn0": "3.0", "f_govequation": "1"}),
    "surface_dif_n10": ("param_surface.txt", {"rn0": "10.0", "f_govequation": "1"}),
    "vertical_n3": ("param_vertical.txt", {"rn0": "3.0"}),
    "process_n1": ("param.txt", {"rn0": "1.0"}),
    "process_dif": ("param.txt", {"f_govequation": "1"}),
    "process_k3600": ("param.txt", {"gw_ksh_mmh": "3600.0"}),
    "process_k10000": ("param.txt", {"gw_ksh_mmh": "10000.0"}),
    "process_k100000": ("param.txt", {"gw_ksh_mmh": "100000.0"}),
    "process_sd1": ("param.txt", {"sd0": "1.0"}),
    "process_l2": ("param.txt", {"gw_ksh_mmh": "3600.0", "f_gwlayer2": "1"}),
    "process_r30": ("param.txt", {"fn_precip": "'param_rain30.txt'", "dt": "2.0"}),
    "surface_r30_n03": ("param_surface.txt", {"fn_precip": "'param_rain30.txt'", "dt": "2.0"}),
    "surface_r30_n1": ("param_surface.txt", {"rn0": "1.0", "fn_precip": "'param_rain30.txt'", "dt": "2.0"}),
    "surface_r30_n3": ("param_surface.txt", {"rn0": "3.0", "fn_precip": "'param_rain30.txt'", "dt": "2.0"}),
}
NOTE = {"rn0": "斜面の粗度", "f_govequation": "地表の流れ(1: 拡散波)", "gw_ksh_mmh": "側方飽和透水係数 (mm/h)",
        "sd0": "土層厚 (m)", "f_gwlayer2": "第 2 層(1: 使う。設定は &list_gwflow_layer2)",
        "fn_precip": "降雨(30 mm/h × 12 時間 × 2 回)", "dt": "時間刻み (s)"}


def set_item(text, key, value, src):
    """「key = 値 ! コメント」の行を 1 行だけ置き換える(元の設定の書き方が変わったら止める)。"""
    pat = re.compile(rf"^(\s*){re.escape(key)}\s*=.*$", re.M)
    if len(pat.findall(text)) != 1:
        sys.exit(f"sweep.py: {src} に '{key} = ...' の行がちょうど 1 行ない(元の設定を確かめる)")
    def line(m):
        head = f"{m.group(1)}{key} = {value}"
        return (head.ljust(28) if len(head) < 28 else head + " ") + f"! {NOTE[key]}  <- sweep.py が変えた値"
    return pat.sub(line, text)


def inputs():
    for p in glob.glob("param_sweep_*.txt"):      # 前回の設定を残さない
        os.remove(p)
    for case, (src, items) in CASES.items():
        s = open(src, encoding="utf-8").read()
        for key, value in items.items():
            s = set_item(s, key, value, src)
        pat = re.compile(r"^(\s*)dir_result\s*=.*$", re.M)
        if len(pat.findall(s)) != 1:
            sys.exit(f"sweep.py: {src} に 'dir_result = ...' の行がちょうど 1 行ない")
        s = pat.sub(lambda m: f"{m.group(1)}dir_result = 'result_sweep_{case}'", s)
        changed = ", ".join(f"{k} = {v}" for k, v in items.items())
        head = (f"! sweep.py が {src} から作った設定(make sweep。ケース {case})。\n"
                f"! 変えた項目: {changed}(と出力先)。ほかは {src} と同じ。\n"
                f"! 手で編集せず、sweep.py か元の設定を直して作り直す。\n")
        with open(f"param_sweep_{case}.txt", "w", encoding="utf-8") as f:
            f.write(head + s)
    print(f"written: param_sweep_<case>.txt ({len(CASES)} cases)")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "inputs":
        inputs()
    elif cmd == "targets":
        print(" ".join(f"run-sweep_{c}" for c in CASES))
    elif cmd == "list":
        for case, (src, items) in CASES.items():
            print(f"{case:18s} {src:20s} " + ", ".join(f"{k} = {v}" for k, v in items.items()))
    else:
        sys.exit("usage: python3 sweep.py inputs | targets | list")


if __name__ == "__main__":
    main()
