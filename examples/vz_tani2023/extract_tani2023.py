#!/usr/bin/env python3
"""谷(2023)の図から各事例の降雨・観測流出強度・論文の計算流出強度を取り出す

谷 誠 (2023): 鉛直不飽和浸透に基づく新しい洪水流出モデルの適用による山地小流域の
流出機構の再検討. 水文・水資源学会誌 36(1), 20–51. doi:10.3178/jjshwr.36.1741

論文の数値は図にしかないため、J-STAGE で公開されている PDF の図(ベクトル描画)の
座標から系列を取り出す。リポジトリには数値を置かない(データの再配布をしない)。
利用者が PDF を手元に用意し、このスクリプトで data/ に生成する。

  python3 extract_tani2023.py <論文の PDF> [出力ディレクトリ(既定 data)]

必要なもの: Python 3、pdfminer.six(pip install pdfminer.six)

事例と図: KIEX = 図−12、MREX = 図−11、MR1 = 図−13、TY1 = 図−14、TY2 = 図−15、
KI1 = 図−16、KI2 = 図−17。事例ごとに次を書き出す:
  rain_<EV>.csv   降雨強度の棒(各棒の始まり・終わりの時刻と強度。図の描画どおり)
  obs_<EV>.csv    観測流出強度(記号、または KIEX は観測の曲線)。対数軸の下端に
                  張り付いた記号は censored = 1(値は下端以下)
  calc_<EV>.csv   論文の計算流出強度(HYDRUS-1D)。対数軸の下端で切られた点は
                  clipped = 1。単位は図の縦軸のまま(MR1 は L/s、ほかは mm/h)
  precip_<EV>.txt ENCflow の &list_precip(降雨の棒を段階関数で与える。RAIN_SHIFT_H の
                  ずらしと、MREX の蒸発散の差し引き(RAIN_FACTOR)を適用)
  meta_<EV>.json  時刻の基準と表−1 との照合結果

時刻は図の時間軸の左端からの時間 (h)。日付の軸は日界の目盛り(0 時)から較正し、
左端の時刻を 1 時間単位に丸めて時刻 0 とする(KIEX は図の 0 h)。rain_<EV>.csv は
描かれた棒の区間のまま。読み取りの精度は描画の精度で、表−1 と照合して表示する。
"""
import csv
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timedelta

try:
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTCurve, LTFigure, LTLine, LTRect
except ImportError:
    sys.exit("pdfminer.six が必要です: pip install pdfminer.six")

# J-STAGE で 2026-10-26 に入手した PDF(36_36.1741.pdf)。違う版でも動くことはあるが、
# 図の位置・描画が変わっていれば読み取りを誤るので、照合結果を必ず確かめること
PDF_SHA256 = "f914ff0c61793b64560365d7d8f60c1540105adf1459d62f1b110ab2d358675b"

# 図ごとの読み取り仕様(座標は PDF の pt。目盛りの位置はここで与えた範囲から探す)
#   time   : 時間軸の目盛り(下端の y = base、長さ len の縦線)。間隔 = hours 時間。
#            ref_x の目盛りが ref(日時。None なら 0 h)
#   rain   : 降雨の縦軸の主目盛りの範囲 ylim と値 values。棒は下端がゼロ線の矩形
#   runoff : 流出強度の縦軸(scale = lin / log)。box はデータを探す y の範囲、
#            bottom は対数軸の下端(切られた点の判定)
#   calc   : 論文の計算値の線(solid = 1 本の折れ線、dash = 短い線分の集まり)を
#            線幅 lw と濃さ gray(CMYK の K)で見分ける
#   markers: 観測の記号(点の数 npts、幅 w・高さ h、線幅 lw で見分ける)
#   obs_curve: 観測が曲線で描かれている場合(KIEX)
#   exclude: 凡例の記号・線の見本の範囲 (x0, y0, x1, y1)
#   checks : 表−1 との照合(max = 最大時間雨量、total = 棒の合計。tol は許容)
FIGS = {
    "KIEX": dict(
        page=15, figure="図−12", axis_x=121.491, x_end=210.231,
        time=dict(base=587.577, len=(1.5, 4.0), hours=1.0, ref_x=121.491, ref=None),
        rain=dict(ylim=(585.0, 660.0), values=[0, 20, 40, 60, 80]),
        runoff=dict(ylim=(585.0, 660.0), values=[0, 20, 40, 60, 80], scale="lin",
                    box=(587.0, 664.0), bottom=587.577, unit="mm/h"),
        calc=dict(calc=dict(kind="dash", lw=0.894, gray=1.0)),
        markers={},
        obs_curve=dict(obs=dict(lw=0.537, gray=1.0)),
        exclude=[],                                  # 矢印は線幅(0.715)で区別できる
        checks=[("max", 79.8, 0.1), ("total", 164.0, 0.02)],
    ),
    "MREX": dict(
        page=14, figure="図−11", axis_x=114.326, x_end=211.848,
        time=dict(base=579.487, len=(80.0, 90.0), hours=24.0, ref_x=114.326, ref=datetime(1992, 5, 27)),
        rain=dict(ylim=(575.0, 670.0), values=[0, 0.5, 1.0, 1.5, 2.0]),
        runoff=dict(ylim=(515.0, 570.0), values=[0, 0.2, 0.4, 0.6], scale="lin",
                    box=(518.2, 577.1), bottom=518.298, unit="mm/h"),
        calc=dict(QcC=dict(kind="solid", lw=1.719, gray=0.246),
                  QcD=dict(kind="solid", lw=0.516, gray=1.0)),
        markers=dict(QU=dict(npts=6, w=(2.2, 2.6), h=(2.2, 2.6), lw=0.344),
                     QL=dict(npts=3, w=(1.6, 2.0), h=(1.6, 2.0), lw=0.516)),
        exclude=[],
        # 図の雨は約 12 時間ごとの平均の棒(昼夜の変動)。表−1 の総雨量とは丸めの分ずれる
        checks=[("total", 276.6, 0.03)],
    ),
    "MR1": dict(
        page=16, figure="図−13", axis_x=88.5, x_end=241.57,
        time=dict(base=474.234, len=(4.0, 4.6), hours=24.0, ref_x=126.802, ref=datetime(1996, 11, 17)),
        rain=dict(ylim=(605.0, 655.0), values=[0, 10, 20, 30]),
        runoff=dict(ylim=(473.0, 595.0), values=[0, 1, 2, 3, 4, 5], scale="lin",
                    box=(474.1, 604.1), bottom=474.234, unit="L/s"),
        calc=dict(QcC=dict(kind="solid", lw=2.149, gray=0.5),
                  QcD=dict(kind="solid", lw=0.644, gray=1.0),
                  QcDx3=dict(kind="dash", lw=1.074, gray=1.0)),
        markers=dict(QU=dict(npts=6, w=(4.8, 5.4), h=(4.8, 5.4), lw=0.644),
                     QL=dict(npts=3, w=(2.8, 3.2), h=(2.8, 3.2), lw=0.859)),
        exclude=[(124.0, 548.0, 175.0, 600.0)],      # 凡例
        # 図は 11/16 からで、表−1(総雨量 292.2 mm・112 h)のイベントの始まりを含まない
        checks=[],
    ),
    "TY1": dict(
        page=18, figure="図−14", axis_x=137.786, x_end=418.6,
        time=dict(base=627.383, len=(3.5, 6.0), hours=24.0, ref_x=167.825, ref=datetime(1987, 7, 15)),
        rain=dict(ylim=(620.0, 665.0), values=[0, 5, 10, 15]),
        runoff=dict(ylim=(520.0, 600.0), values=[0.01, 0.1, 1.0], scale="log",
                    box=(523.0, 623.0), bottom=525.103, unit="mm/h"),
        calc=dict(KT=dict(kind="solid", lw=0.699, gray=1.0),
                  SL=dict(kind="solid", lw=1.399, gray=0.5),
                  MN=dict(kind="dash", lw=1.399, gray=1.0)),
        markers=dict(KT=dict(npts=6, w=(3.1, 3.5), h=(3.1, 3.5), lw=0.466),
                     MN=dict(npts=3, w=(2.3, 2.6), h=(2.3, 2.6), lw=0.466),
                     SL=dict(npts=4, w=(2.9, 3.1), h=(2.5, 2.7), lw=0.466)),
        exclude=[],
        checks=[("max", 14.5, 0.06), ("total", 131.5, 0.02)],
    ),
    "TY2": dict(
        page=19, figure="図−15", axis_x=78.72, x_end=248.2,
        time=dict(base=604.562, len=(3.5, 6.0), hours=24.0, ref_x=94.148, ref=datetime(1976, 9, 9)),
        rain=dict(ylim=(600.0, 665.0), values=[0, 5, 10, 15]),
        runoff=dict(ylim=(495.0, 600.0), values=[0.1, 1.0, 10.0], scale="log",
                    box=(486.0, 601.0), bottom=488.38, unit="mm/h"),
        calc=dict(KT=dict(kind="solid", lw=0.398, gray=1.0),
                  MN=dict(kind="dash", lw=0.996, gray=1.0)),
        markers=dict(KT=dict(npts=6, w=(2.6, 3.0), h=(2.6, 3.0), lw=0.398),
                     MN=dict(npts=3, w=(1.9, 2.3), h=(1.9, 2.3), lw=0.597)),
        exclude=[(98.0, 575.0, 122.0, 592.0),     # (b) の凡例の記号
                 (140.0, 519.0, 174.0, 537.0)],   # 計算値の凡例の線の見本
        checks=[("max", 14.3, 0.06), ("total", 374.9, 0.02)],
    ),
    "KI1": dict(
        page=20, figure="図−16", axis_x=104.81, x_end=225.287,
        # 主目盛り(長さ 4.3)が 0 時、日付のラベルは日の中央(TY と同じ描き方)
        time=dict(base=556.86, len=(1.8, 4.6), hours=6.0, ref_x=104.81, ref=datetime(1982, 8, 1)),
        rain=dict(ylim=(550.0, 660.0), values=[0, 10, 20, 30]),
        runoff=dict(ylim=(480.0, 550.0), values=[0.1, 1.0, 10.0], scale="log",
                    box=(478.3, 553.9), bottom=478.338, unit="mm/h"),
        calc=dict(QcD=dict(kind="solid", lw=0.425, gray=1.0),
                  QcC=dict(kind="dash", lw=1.062, gray=1.0)),
        markers=dict(Qb=dict(npts=6, w=(2.8, 3.2), h=(2.8, 3.2), lw=0.425)),
        exclude=[],
        # 図は表−1 のイベント(348.9 mm・58 h)の一部。最大時間雨量だけを照合
        checks=[("max", 30.0, 0.06)],
    ),
    "KI2": dict(
        page=21, figure="図−17", axis_x=121.21, x_end=423.294,
        time=dict(base=572.225, len=(1.8, 4.6), hours=6.0, ref_x=142.287, ref=datetime(2006, 7, 15)),
        rain=dict(ylim=(570.0, 665.0), values=[0, 5, 10, 15, 20, 25]),
        runoff=dict(ylim=(480.0, 540.0), values=[0.1, 1.0], scale="log",
                    box=(478.8, 569.3), bottom=478.853, unit="mm/h"),
        calc=dict(QcD=dict(kind="solid", lw=0.424, gray=1.0),
                  QcC=dict(kind="dash", lw=1.273, gray=1.0)),
        markers=dict(Qb=dict(npts=6, w=(2.7, 3.2), h=(2.7, 3.2), lw=0.424)),
        exclude=[],
        checks=[("total", 341.3, 0.02)],
    ),
}

# 降雨の棒の区間を precip_<EV>.txt へ渡すときのずらし (h)。描かれた 1 時間の棒は正時を
# 中心とし、その雨が正時の前の 1 時間か後の 1 時間かは図から決まらない。ENCflow の計算を
# 論文の計算流出強度(図の計算値)と比べ、論文の計算値が大きい範囲(TY・KI は 0.5 mm/h
# 以上、MR1 は 0.3 L/s 以上)の |log10(ENCflow/論文)| の 90 % 値が最小になるずらしを
# 採った(2026-10-26。compare_tani2023.py と同じ比較。KI2 は基底流の直線を足した比較):
#           −1.0 h           −0.5 h           0               +0.5 h           +1.0 h
#   TY1 KT  —                0.207            0.171           0.065(採用)      0.096
#   TY2 KT  0.100            0.020(採用)      0.067           0.157            —
#   KI1     0.188            0.093(採用)      0.142           0.304            0.444
#   KI2     0.184            0.080(採用)      0.118           0.271            0.354
#   MR1     0.059            0.031(採用)      0.047           0.089            0.114
# 採用したずらしでのピーク時刻の差は −0.1〜+0.15 h。TY1 だけが正時から始まる 1 時間、
# ほかは正時までの 1 時間に当たる(TY1 だけ向きが違う理由は論文からは分からない)。
# KIEX(棒は降雨の開始 0 h から)と MREX(約 12 時間の平均の棒)はずらさない
RAIN_SHIFT_H = {"KIEX": 0.0, "MREX": 0.0, "MR1": -0.5, "TY1": +0.5, "TY2": -0.5, "KI1": -0.5, "KI2": -0.5}

# 降雨に掛ける係数(論文 Ⅳ.1: MREX は降雨強度の 20 % を蒸発散として差し引いた強度を
# 地表面の境界条件とした)
RAIN_FACTOR = {"MREX": 0.8}

failed = []


def note(ok, msg):
    print(("  ok   " if ok else "  WARN ") + msg)
    if not ok:
        failed.append(msg)


def collect(pdf, pageno):
    """ページ内の矩形・線・曲線を(図の入れ子も含めて)平らに集める"""
    items = []

    def walk(o):
        if isinstance(o, LTRect):
            items.append(dict(k="rect", bbox=o.bbox, fill=o.fill, stroke=o.stroke))
        elif isinstance(o, LTCurve):          # LTLine も含む
            xs = [p[0] for p in o.pts]
            ys = [p[1] for p in o.pts]
            items.append(dict(k="line" if isinstance(o, LTLine) else "curve", pts=o.pts,
                              bbox=(min(xs), min(ys), max(xs), max(ys)), lw=o.linewidth,
                              scol=tuple(o.stroking_color) if isinstance(o.stroking_color, (list, tuple))
                              else (o.stroking_color,),
                              fill=o.fill, stroke=o.stroke, npts=len(o.pts)))
        if isinstance(o, LTFigure):
            for ch in o:
                walk(ch)

    for i, page in enumerate(extract_pages(pdf), start=1):
        if i == pageno:
            for o in page:
                walk(o)
            break
    return items


def gray_of(scol):
    """CMYK の K(0..1)または灰色の値を返す(線の濃さの判別用)"""
    return scol[-1] if scol else 1.0


def hticks(items, axis_x, ylim):
    """縦軸の主目盛り(軸から右へ 3.3〜6 pt の水平線)の y を下から順に返す"""
    ys = set()
    for it in items:
        if it["k"] != "line":
            continue
        (x0, y0, x1, y1) = it["bbox"]
        if abs(y1 - y0) < 0.01 and abs(x0 - axis_x) < 0.1 and 3.3 < x1 - x0 < 6.0 and ylim[0] <= y0 <= ylim[1]:
            ys.add(round(y0, 3))
    return sorted(ys)


def vticks(items, base, length):
    """時間軸の目盛り(下端が base、長さ length の縦線)の x を左から順に返す"""
    xs = set()
    for it in items:
        if it["k"] != "line":
            continue
        (x0, y0, x1, y1) = it["bbox"]
        if abs(x1 - x0) < 0.01 and abs(y0 - base) < 0.05 and length[0] < y1 - y0 < length[1]:
            xs.add(round(x0, 3))
    out = []
    for x in sorted(xs):             # 枠線と格子線が重なる位置は 1 本にまとめる
        if not out or x - out[-1] > 0.05:
            out.append(x)
    return out


def extract(pdf, ev, spec, outdir):
    print("== %s(%s、PDF %d ページ)" % (ev, spec["figure"], spec["page"]))
    items = collect(pdf, spec["page"])
    ts = spec["time"]

    # --- 時間軸 ---
    tx = vticks(items, ts["base"], ts["len"])
    gaps = [b - a for a, b in zip(tx[:-1], tx[1:])]
    pph = sum(gaps) / len(gaps) / ts["hours"]               # pt / h
    note(len(tx) >= 2 and max(abs(g - pph * ts["hours"]) for g in gaps) < 0.15,
         "time ticks: %d every %g h, %.4f pt/h (spacing spread %.3f pt)"
         % (len(tx), ts["hours"], pph, max(gaps) - min(gaps)))
    xref = min(tx, key=lambda x: abs(x - ts["ref_x"]))
    note(abs(xref - ts["ref_x"]) < 0.5, "reference tick at x = %.3f" % xref)
    if ts["ref"] is None:
        t_axis0 = None
        off_h = (xref - spec["axis_x"]) / pph
        t0_label = "0 h(図の時間軸の 0)"
    else:
        ta = ts["ref"] + timedelta(hours=(spec["axis_x"] - xref) / pph)
        t_axis0 = datetime(ta.year, ta.month, ta.day, ta.hour) + timedelta(hours=round(ta.minute / 60.0))
        off_h = (ts["ref"] - t_axis0).total_seconds() / 3600.0
        t0_label = t_axis0.strftime("%Y-%m-%d %H:%M")

    def hours(x):          # 図の x → 時刻 0 からの時間 (h)
        return (x - xref) / pph + off_h

    t_end = hours(spec["x_end"])

    # --- 縦軸の較正 ---
    rs = spec["rain"]
    ry = hticks(items, spec["axis_x"], rs["ylim"])
    note(len(ry) == len(rs["values"]), "rain axis ticks %s" % ry)
    rain_ppu = (ry[-1] - ry[0]) / (rs["values"][-1] - rs["values"][0])
    qs = spec["runoff"]
    qy = hticks(items, spec["axis_x"], qs["ylim"])
    note(len(qy) == len(qs["values"]), "runoff (%s) axis ticks %s" % (qs["scale"], qy))
    qv = qs["values"]
    if qs["scale"] == "log":
        q_ppd = (qy[-1] - qy[0]) / (math.log10(qv[-1]) - math.log10(qv[0]))

        def qval(y):
            return 10 ** (math.log10(qv[0]) + (y - qy[0]) / q_ppd)
    else:
        q_ppu = (qy[-1] - qy[0]) / (qv[-1] - qv[0])

        def qval(y):
            return qv[0] + (y - qy[0]) / q_ppu
    ybot, ytop = qs["box"]
    yfloor = qs["bottom"]

    def excluded(x, y):
        return any(a <= x <= c and b <= y <= d for (a, b, c, d) in spec["exclude"])

    # --- 降雨の棒 ---
    bars = set()
    for it in items:
        if it["k"] == "rect" and it["fill"]:
            x0, y0, x1, y1 = it["bbox"]
            if abs(y0 - ry[0]) < 0.05 and spec["axis_x"] - 0.5 < x0 < spec["x_end"] and y1 > y0 + 0.01:
                bars.add((round(x0, 3), round(x1, 3), round(y1, 3)))
    rain = []
    for x0, x1, y1 in sorted(bars):
        rain.append((hours(x0), hours(x1), (y1 - ry[0]) / rain_ppu))
    total = sum((b - a) * r for a, b, r in rain)
    rmax = max(r for a, b, r in rain)
    widths = [b - a for a, b, r in rain]
    print("  rain bars: %d, width %.3f-%.3f h, %.2f-%.2f h, total %.2f mm, max %.2f mm/h"
          % (len(rain), min(widths), max(widths), rain[0][0], rain[-1][1], total, rmax))
    for kind, val, tol in spec["checks"]:
        if kind == "max":
            note(abs(rmax - val) <= tol, "max rain %.2f mm/h (Table 1: %.1f)" % (rmax, val))
        else:
            note(abs(total - val) / val <= tol, "total rain %.2f mm (Table 1: %.1f; %+.1f %%)"
                 % (total, val, 100.0 * (total - val) / val))

    # --- 曲線(論文の計算値と、観測が曲線で描かれている場合) ---
    def curve_points(st, solid):
        pts = []
        for it in items:
            if it["k"] not in ("curve", "line") or abs(it["lw"] - st["lw"]) > 0.01:
                continue
            if abs(gray_of(it["scol"]) - st["gray"]) > 0.01:
                continue
            x0, y0, x1, y1 = it["bbox"]
            if not (spec["axis_x"] - 0.1 <= x0 and x1 <= spec["x_end"] + 0.5 and ybot <= y0 and y1 <= ytop):
                continue
            if solid and it["npts"] < 20:
                continue
            if not solid and (x1 - x0 > 8.0 or y1 - y0 > 12.0):
                continue
            for (x, y) in it["pts"]:
                if not excluded(x, y):
                    pts.append((x, y))
        return sorted(set((round(x, 3), round(y, 3)) for x, y in pts))

    calc = []
    for name, st in spec["calc"].items():
        pts = curve_points(st, st["kind"] == "solid")
        for x, y in pts:
            calc.append((name, hours(x), qval(y), 1 if qs["scale"] == "log" and y <= yfloor + 0.05 else 0))
        note(len(pts) > 15, "calculated %s: %d points" % (name, len(pts)))

    obs = []
    for name, st in spec.get("obs_curve", {}).items():
        pts = curve_points(st, True)
        for x, y in pts:
            obs.append((name, hours(x), qval(y), 0))
        note(len(pts) > 10, "observed %s (curve): %d points" % (name, len(pts)))

    # --- 観測の記号 ---
    for name, st in spec["markers"].items():
        cen = []
        for it in items:
            if it["k"] != "curve" or not it["stroke"] or it["npts"] != st["npts"]:
                continue
            if abs(it["lw"] - st["lw"]) > 0.01:
                continue
            x0, y0, x1, y1 = it["bbox"]
            w, h = x1 - x0, y1 - y0
            if not (st["w"][0] <= w <= st["w"][1] and st["h"][0] <= h <= st["h"][1]):
                continue
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            if not (spec["axis_x"] < cx < spec["x_end"] + 1.0 and ybot <= cy <= ytop) or excluded(cx, cy):
                continue
            if all(abs(cx - a) > 0.8 or abs(cy - b) > 0.8 for a, b in cen):   # × は 2 本の斜線
                cen.append((cx, cy))
        for cx, cy in sorted(cen):
            obs.append((name, hours(cx), qval(cy), 1 if qs["scale"] == "log" and abs(cy - yfloor) < 0.3 else 0))
        note(len(cen) > 10, "observed %s: %d markers" % (name, len(cen)))

    # --- 書き出し ---
    os.makedirs(outdir, exist_ok=True)

    def stamp(h):
        return (t_axis0 + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M") if t_axis0 else "%.3f h" % h

    with open(os.path.join(outdir, "rain_%s.csv" % ev), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_start(h)", "t_end(h)", "rain(mm/h)", "start"])
        for a, b, r in rain:
            w.writerow(["%.4f" % a, "%.4f" % b, "%.4f" % r, stamp(a)])
    with open(os.path.join(outdir, "calc_%s.csv" % ev), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["catchment", "t(h)", "runoff(%s)" % qs["unit"], "clipped"])
        for row in calc:
            w.writerow([row[0], "%.4f" % row[1], "%.6g" % row[2], row[3]])
    with open(os.path.join(outdir, "obs_%s.csv" % ev), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["catchment", "t(h)", "runoff(%s)" % qs["unit"], "censored"])
        for row in obs:
            w.writerow([row[0], "%.4f" % row[1], "%.6g" % row[2], row[3]])

    # 降雨の段階関数(時間は分。棒のない時間は 0)。&list_precip の prval は線形補間
    # なので、各区間の終わりの直前(0.01 分前)にも同じ値の点を置く
    shift = RAIN_SHIFT_H[ev]
    factor = RAIN_FACTOR.get(ev, 1.0)
    steps = []
    t = 0.0
    for a, b, r in rain:
        a, b = max(round((a + shift) * 60.0), 0), round((b + shift) * 60.0)
        if a > t:
            steps.append((t, a, 0.0))
        steps.append((a, b, r * factor))
        t = b
    steps.append((t, round(t_end * 60.0) + 60, 0.0))
    with open(os.path.join(outdir, "precip_%s.txt" % ev), "w") as f:
        f.write("! %s の降雨(谷 2023 の%sから extract_tani2023.py が生成。時間は分、強度は mm/h)\n"
                % (ev, spec["figure"]))
        f.write("! 時刻 0 = %s%s。棒の区間を %+.1f h ずらした(RAIN_SHIFT_H)"
                % (t0_label, "" if t_axis0 is None else "(図の時間軸の左端)", shift))
        f.write("。強度に %.2f を掛けた(RAIN_FACTOR)\n" % factor if factor != 1.0 else "\n")
        f.write("&list_precip\n  prtype = 1\n")
        k = 0
        for a, b, r in steps:
            k += 1
            f.write("  prval(1:2,%d) = %.2f, %.4f\n" % (k, a, r))
            k += 1
            f.write("  prval(1:2,%d) = %.2f, %.4f\n" % (k, b - 0.01, r))
        f.write("/\n")
    meta = dict(event=ev, figure=spec["figure"], pdf_page=spec["page"], t0=t0_label, t_end_h=t_end,
                rain_total_mm=total, rain_max_mmh=rmax, checks=spec["checks"], n_rain_bars=len(rain),
                n_prval=k, rain_shift_h=shift, rain_factor=factor, runoff_unit=qs["unit"])
    with open(os.path.join(outdir, "meta_%s.json" % ev), "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    print("  time 0 = %s, end = %.1f h, prval points = %d (max 999)" % (t0_label, t_end, k))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    pdf = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else "data"
    with open(pdf, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    note(sha == PDF_SHA256, "PDF SHA-256 %s%s" % (sha[:16], "" if sha == PDF_SHA256 else
                                                   " (differs from the version this script was written for)"))
    for ev, spec in FIGS.items():
        extract(pdf, ev, spec, outdir)
    if failed:
        print("=== extraction finished with %d warning(s): check the figures before use ===" % len(failed))
        sys.exit(1)
    print("=== extraction OK: %s/ ===" % outdir)


if __name__ == "__main__":
    main()
