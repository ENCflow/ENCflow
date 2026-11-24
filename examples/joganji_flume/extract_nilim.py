#!/usr/bin/env python3
"""国総研の常願寺川 1/100 移動床模型実験(ケース 2)の Excel から、例題が使う部分を data_nilim/ に抜き出す。

  python3 extract_nilim.py <kadounikyokukacase2.xlsx> [data_nilim]

元のデータ: 国土技術政策総合研究所 河川研究室「模型実験等データアーカイブ」の「セグメント１河川の二極化に関する
実験」(令和 7 年度)の「【河道の二極化】ケース2模型実験データ.xlsx」
(https://www.nilim.go.jp/lab/fbg/tech/kadounikyokukacase2.xlsx。技術情報のページ
https://www.nilim.go.jp/lab/fbg/tech/tech.html から)。利用規約は政府標準利用規約(第 2.0 版)。
data_nilim/ の各ファイルは、この Excel からケース 2-1(通水 1 回目、240 分)の比較に要る量だけを抜き出し、列を並べ替えて
gzip した加工物で、各ファイルの冒頭の # 行に出典と加工の内容を書く。値は丸めていない(Excel の値をそのまま書く)。

出力(すべて模型スケール。長さ m、時間 min、流量 L/s):
  grid.csv.gz      格子点(I 2363 × J 87。I は上流端 1 から下流端 2363): I, J, x, y, 初期河床高 z0, 固定床高 zfix,
                   固定床 fixed(1 = 固定床、0 = 移動床), ケース 2-1 終了時(240 分)の河床高 z240
  gsd.csv.gz       メッシュ(格子点の間 2362 × 86)の表層の粒径集団 1〜3 の割合 (%) とパターン分類: 初期と 240 分
  sections.csv     63 断面: 名前, I, 縦断距離, 低水路河岸平均河床高, 粗度係数(低水路・左右の高水敷),
                   初期の構成比率(粒径集団 1〜3 %), 敷き均し厚さ
  banks.csv.gz     I ごとの左岸低水路河岸・左岸堤防・右岸低水路河岸・右岸堤防の座標
  bc_2-1.csv.gz    上流端の流量と粒径集団 1〜3 の給砂量(1 秒ごと。L/s)
  wl_2-1.csv.gz    水位計 21 か所の水位の時系列(約 6 秒ごと)
  vel_2-1.csv.gz   93 分の流速 u, v(解析範囲外の点を除く)
依存: openpyxl(この抜き出しのときだけ。例題の計算・図化は data_nilim/ だけを読む)
"""
import gzip
import os
import sys

import openpyxl

SRC = ("出典: 国土技術政策総合研究所 河川研究室「模型実験等データアーカイブ」セグメント１河川の二極化に関する実験 "
       "【河道の二極化】ケース2模型実験データ.xlsx (https://www.nilim.go.jp/lab/fbg/tech/kadounikyokukacase2.xlsx、"
       "政府標準利用規約 第2.0版) を加工して作成")


def sheet_rows(wb, title):
    return wb[title].iter_rows(values_only=True)


def num(v):
    return v if isinstance(v, (int, float)) else float(v)


def open_out(path, header_lines, columns):
    f = gzip.open(path, "wt", encoding="utf-8", newline="") if path.endswith(".gz") else \
        open(path, "w", encoding="utf-8", newline="")
    f.write("# " + SRC + "\n")
    for h in header_lines:
        f.write("# " + h + "\n")
    f.write(",".join(columns) + "\n")
    return f


def minutes(v):
    """'HH:MM:SS.ffffff'(または datetime.time・timedelta)を分に"""
    if hasattr(v, "total_seconds"):
        return v.total_seconds() / 60.0
    if hasattr(v, "hour"):
        return v.hour * 60 + v.minute + (v.second + v.microsecond * 1e-6) / 60.0
    h, m, s = str(v).split(":")
    return int(h) * 60 + int(m) + float(s) / 60.0


def main():
    xlsx = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_nilim")
    os.makedirs(out, exist_ok=True)
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)

    # --- 格子点: 初期河床・固定床(シート 9)と 240 分の河床(シート 4 の実験結果。ケース 2-1 の列) ---
    z240 = {}
    for k, r in enumerate(sheet_rows(wb, "4_河床高(全格子データ)")):
        if k < 4 or r[0] is None:
            continue
        z240[(int(r[0]), int(r[1]))] = r[5]
    f = open_out(os.path.join(out, "grid.csv.gz"),
                 ["シート 9_初期河床高(全格子データ) と 4_河床高(全格子データ) のケース 2-1(240 分)の列を (I, J) で結合",
                  "fixed: 元の「固定床・移動床」列(1 = 固定床、0 = 移動床)"],
                 ["I", "J", "x", "y", "z0", "zfix", "fixed", "z240"])
    n = 0
    for k, r in enumerate(sheet_rows(wb, "9_初期河床高(全格子データ)")):
        if k < 1 or r[0] is None:
            continue
        i, j = int(r[0]), int(r[1])
        f.write("%d,%d,%s,%s,%s,%s,%d,%s\n" % (i, j, r[2], r[3], r[4], r[5], int(r[6]), z240[(i, j)]))
        n += 1
    f.close()
    print("grid.csv.gz: %d points" % n)

    # --- 表層の粒度(シート 6。初期と 240 分)。I = 999 の行は元のファイルで I の欄が「固定床」と書かれている ---
    f = open_out(os.path.join(out, "gsd.csv.gz"),
                 ["シート 6_粒度分布(全メッシュデータ) の初期河床とケース 2-1(240 分)の列。値は % とパターン分類",
                  "元のファイルで I メッシュ番号が「固定床」と書かれた 86 行(998 と 1000 の間)は I = 999 とした"],
                 ["I", "J", "x", "y", "f1_0", "f2_0", "f3_0", "pat_0", "f1_240", "f2_240", "f3_240", "pat_240"])
    n = 0
    for k, r in enumerate(sheet_rows(wb, "6_粒度分布(全メッシュデータ)")):
        if k < 4 or r[1] is None:
            continue
        i = 999 if r[0] == "固定床" else int(r[0])
        f.write("%d,%d,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % ((i,) + tuple(r[1:4]) + tuple(r[4:12])))
        n += 1
    f.close()
    print("gsd.csv.gz: %d meshes" % n)

    # --- 断面: 粗度(シート 2)と初期の構成比率・敷き均し厚さ(シート 4) ---
    sec = []
    for k, r in enumerate(sheet_rows(wb, "2_初期河床・HWL・粗度")):
        if k < 2 or r[1] is None:
            continue
        sec.append([str(r[0]), int(r[1]), r[3], r[4], r[6], r[7], r[8]])
    comp = {}
    for k, r in enumerate(sheet_rows(wb, "4_初期河床粒度分布")):
        if k < 3 or r[2] is None:
            continue
        comp[int(r[2])] = (r[5], r[6], r[7], r[8])
    f = open_out(os.path.join(out, "sections.csv"),
                 ["シート 2_初期河床・HWL・粗度 と 4_初期河床粒度分布 を I で結合。dist は下流端 8.4k からの縦断距離 (m)",
                  "n_*: 粗度係数(低水路・左岸高水敷・右岸高水敷)。f1〜f3: 初期の構成比率 (%)。laid: 敷き均し厚さ (m)"],
                 ["name", "I", "dist", "zbank", "n_low", "n_lfp", "n_rfp", "f1", "f2", "f3", "laid"])
    for s in sec:
        c = comp[s[1]]
        f.write(",".join(str(v) for v in s + list(c)) + "\n")
    f.close()
    print("sections.csv: %d sections" % len(sec))

    # --- 河岸・堤防の法線(シート 6) ---
    f = open_out(os.path.join(out, "banks.csv.gz"),
                 ["シート 6_堤防・河岸法線形。k は構成点の通し番号(格子の I と同じ並び)"],
                 ["k", "x_lbank", "y_lbank", "x_llevee", "y_llevee", "x_rbank", "y_rbank", "x_rlevee", "y_rlevee"])
    n = 0
    for k, r in enumerate(sheet_rows(wb, "6_堤防・河岸法線形")):
        if k < 3 or r[0] is None:
            continue
        f.write("%d,%s,%s,%s,%s,%s,%s,%s,%s\n" % (int(r[0]), r[1], r[2], r[4], r[5], r[7], r[8], r[10], r[11]))
        n += 1
    f.close()
    print("banks.csv.gz: %d points" % n)

    # --- 境界条件(シート 5): ケース 2-1 の流量と給砂。流量と給砂の時刻は同じ 1 秒の並び(差は 1e-6 分未満を確認) ---
    q, fd = [], []
    for k, r in enumerate(sheet_rows(wb, "5_境界条件")):
        if k < 2:
            continue
        if r[4] is not None:
            run = r[4]
        if r[5] is not None and run == "ケース2-1":
            q.append((num(r[5]), num(r[7])))
        if r[8] is not None:
            frun = r[8]
        if r[9] is not None and frun == "2-1":
            fd.append((num(r[9]), num(r[11] or 0.0), num(r[12] or 0.0), num(r[13] or 0.0)))
    if len(q) != len(fd) or max(abs(a[0] - b[0]) for a, b in zip(q, fd)) > 1.0e-6:
        sys.exit("discharge and feed series of case 2-1 are not on the same time base")
    f = open_out(os.path.join(out, "bc_2-1.csv.gz"),
                 ["シート 5_境界条件 のケース 2-1: 上流端流量 実測値と上流端給砂量 実測値(粒径集団 1〜3)。時刻はケース時間 (min)",
                  "給砂量は元のファイルの L/s のまま(空隙込みか固体体積かは元のファイルに書かれていない)"],
                 ["t_min", "q_lps", "f1_lps", "f2_lps", "f3_lps"])
    for (t, v), (_, a, b, c) in zip(q, fd):
        f.write("%s,%s,%s,%s,%s\n" % (t, v, a, b, c))
    f.close()
    print("bc_2-1.csv.gz: %d rows" % len(q))

    # --- 水位の時系列(シート 2_水位(時系列)のケース 2-1 の 21 か所) ---
    rows = list(sheet_rows(wb, "2_水位（時系列）"))
    blk = [c for c, v in enumerate(rows[0]) if v]
    end = blk[1]
    f = open_out(os.path.join(out, "wl_2-1.csv.gz"),
                 ["シート 2_水位(時系列)のケース 2-1。t_min は元の時刻(時:分:秒)を分にしたもの"],
                 ["gauge", "x", "y", "t_min", "level"])
    n = 0
    for c in range(0, end, 3):
        name = rows[3][c]
        if not name:
            continue
        x, y = rows[3][c + 1], rows[3][c + 2]
        for r in rows[5:]:
            if r[c] is None or r[c + 1] is None:
                continue
            f.write("%s,%s,%s,%.6f,%s\n" % (name, x, y, minutes(r[c]), r[c + 1]))
            n += 1
    f.close()
    print("wl_2-1.csv.gz: %d samples" % n)

    # --- 流速(シート 5_流速 のケース 2-1、93 分) ---
    f = open_out(os.path.join(out, "vel_2-1.csv.gz"),
                 ["シート 5_流速 のケース 2-1(計測時点 93 分)。「解析範囲外」の点は除いた"],
                 ["I", "J", "x", "y", "u", "v"])
    n = 0
    for k, r in enumerate(sheet_rows(wb, "5_流速")):
        if k < 5 or r[0] is None or isinstance(r[4], str) or r[4] is None:
            continue
        f.write("%d,%d,%s,%s,%s,%s\n" % (int(r[0]), int(r[1]), r[2], r[3], r[4], r[5]))
        n += 1
    f.close()
    print("vel_2-1.csv.gz: %d points" % n)


if __name__ == "__main__":
    main()
