#!/usr/bin/env python3
"""谷(2023)の図から TY1・TY2 の降雨・観測流出強度・論文の計算流出強度を取り出す

谷 誠 (2023): 鉛直不飽和浸透に基づく新しい洪水流出モデルの適用による山地小流域の
流出機構の再検討. 水文・水資源学会誌 36(1), 20–51. doi:10.3178/jjshwr.36.1741

論文の数値は図にしかないため、J-STAGE で公開されている PDF の図(ベクトル描画)の
座標から系列を取り出す。リポジトリには数値を置かない(データの再配布をしない)。
利用者が PDF を手元に用意し、このスクリプトで data/ に生成する。

  python3 extract_tani2023.py <論文の PDF> [出力ディレクトリ(既定 data)]

必要なもの: Python 3、pdfminer.six(pip install pdfminer.six)

取り出すもの(図−14 = TY1、図−15 = TY2):
  rain_<EV>.csv   降雨強度の棒(各棒の始まり・終わりの時刻と強度。図の描画どおり)
  obs_<EV>.csv    観測流出強度の記号(○ KT、× MN、△ SL)。対数軸の下端に
                  張り付いた記号は censored = 1(値は下端以下)
  calc_<EV>.csv   論文の計算流出強度(HYDRUS-1D。分離した基底流を加えた値)。
                  対数軸の下端で切られた点は clipped = 1
  precip_<EV>.txt ENCflow の &list_precip(降雨の棒を時間ごとの段階関数で与える)
  meta_<EV>.json  時刻の基準と表−1 との照合結果

時刻は図の時間軸の左端(TY1: 1987-07-14 06:00、TY2: 1976-09-08 12:00。日界の
目盛りから決めた)からの時間 (h)。rain_<EV>.csv は描かれた棒の区間のまま。
棒は正時を中心に描かれており、その 1 時間が正時の前か後かは図から決まらない。
precip_<EV>.txt では、論文の計算流出強度と最もよく合う割り当て(RAIN_SHIFT_H。
TY1 は正時から始まる 1 時間、TY2 は正時までの 1 時間)にずらす(推定。README)。
読み取りの精度は描画の精度(座標は 0.001 pt。降雨強度の 1 目盛り 2.2 pt)で、
表−1 の最大時間雨量・総雨量と照合して表示する。
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
FIGS = {
    "TY1": dict(
        page=18, figure="図−14",
        axis_x=137.786,                      # 縦軸の線の x
        x_end=418.6,                         # 時間軸の右端
        day_tick_base=627.383,               # 日界の目盛り(下端の y)
        first_day=datetime(1987, 7, 15),     # 最初の日界の目盛りの日付(0 時)
        rain=dict(ylim=(620.0, 665.0), values=[0, 5, 10, 15]),
        runoff=dict(ylim=(520.0, 600.0), values=[0.01, 0.1, 1.0], box=(523.0, 623.0), bottom=525.103),
        calc=dict(KT=dict(kind="solid", lw=0.699, gray=1.0),
                  SL=dict(kind="solid", lw=1.399, gray=0.5),
                  MN=dict(kind="dash", lw=1.399, gray=1.0)),
        markers=dict(KT=dict(npts=6, w=(3.1, 3.5), h=(3.1, 3.5), lw=0.466),
                     MN=dict(npts=3, w=(2.3, 2.6), h=(2.3, 2.6), lw=0.466),
                     SL=dict(npts=4, w=(2.9, 3.1), h=(2.5, 2.7), lw=0.466)),
        exclude=[],                           # 凡例の記号・線の見本の範囲 (x0, y0, x1, y1)
        table1=dict(total=131.5, max_hourly=14.5),
    ),
    "TY2": dict(
        page=19, figure="図−15",
        axis_x=78.72,
        x_end=248.2,
        day_tick_base=604.562,
        first_day=datetime(1976, 9, 9),
        rain=dict(ylim=(600.0, 665.0), values=[0, 5, 10, 15]),
        runoff=dict(ylim=(495.0, 600.0), values=[0.1, 1.0, 10.0], box=(486.0, 601.0), bottom=488.38),
        calc=dict(KT=dict(kind="solid", lw=0.398, gray=1.0),
                  MN=dict(kind="dash", lw=0.996, gray=1.0)),
        markers=dict(KT=dict(npts=6, w=(2.6, 3.0), h=(2.6, 3.0), lw=0.398),
                     MN=dict(npts=3, w=(1.9, 2.3), h=(1.9, 2.3), lw=0.597)),
        exclude=[(98.0, 575.0, 122.0, 592.0),     # (b) の凡例の記号
                 (140.0, 519.0, 174.0, 537.0)],   # 計算値の凡例の線の見本
        table1=dict(total=374.9, max_hourly=14.3),
    ),
}

# 降雨の棒の区間を precip_<EV>.txt へ渡すときのずらし (h)。描かれた棒は正時を中心と
# する 1 時間で、その雨が正時の前の 1 時間か後の 1 時間かは図から決まらない。
# ENCflow の計算を論文の計算流出強度(図の計算値)と比べ、論文の計算値 0.5 mm/h 以上
# (基底流の影響が小さい範囲)の log10(ENCflow/論文) の絶対値の 90 % 値が最小に
# なるずらしを採った(2026-10-26。compare_tani2023.py と同じ比較):
#   TY1  −0.5 h: KT 0.207 SL 0.306 MN 0.382 / 0: 0.171 0.238 0.276 /
#        +0.5 h: 0.065 0.060 0.097(採用。ピーク時刻の差の中央値 −0.1 h)/ +1.0 h: 0.096 0.106 0.183
#   TY2  −1.0 h: KT 0.100 MN 0.121 / −0.5 h: 0.020 0.028(採用。ピーク時刻の差 −0.1 h)/
#        0: 0.067 0.094 / +0.5 h: 0.157 0.200
# TY1 は正時から始まる 1 時間、TY2 は正時までの 1 時間に当たる。事例で向きが違う
# 理由は論文からは分からない(推定であることを README に明記)。
RAIN_SHIFT_H = {"TY1": +0.5, "TY2": -0.5}

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
    """縦軸の主目盛り(軸から右へ 3.5〜6 pt の水平線)の y を下から順に返す"""
    ys = set()
    for it in items:
        if it["k"] != "line":
            continue
        (x0, y0, x1, y1) = it["bbox"]
        if abs(y1 - y0) < 0.01 and abs(x0 - axis_x) < 0.05 and 3.5 < x1 - x0 < 6.0 and ylim[0] <= y0 <= ylim[1]:
            ys.add(round(y0, 3))
    return sorted(ys)


def day_ticks(items, base):
    """日界の目盛り(下端が base の 3.5〜6 pt の縦線)の x を左から順に返す"""
    xs = set()
    for it in items:
        if it["k"] != "line":
            continue
        (x0, y0, x1, y1) = it["bbox"]
        if abs(x1 - x0) < 0.01 and abs(y0 - base) < 0.05 and 3.5 < y1 - y0 < 6.0:
            xs.add(round(x0, 3))
    return sorted(xs)


def extract(pdf, ev, spec, outdir):
    print("== %s(%s、PDF %d ページ)" % (ev, spec["figure"], spec["page"]))
    items = collect(pdf, spec["page"])

    # --- 時間軸: 日界の目盛り(等間隔 = 1 日) ---
    dx = day_ticks(items, spec["day_tick_base"])
    gaps = [b - a for a, b in zip(dx[:-1], dx[1:])]
    ppd = sum(gaps) / len(gaps)
    note(len(dx) >= 4 and max(abs(g - ppd) for g in gaps) < 0.1,
         "day ticks: %d, %.3f pt/day (spacing spread %.3f pt)" % (len(dx), ppd, max(gaps) - min(gaps)))
    x_day0 = dx[0]
    t_axis0 = spec["first_day"] + timedelta(hours=(spec["axis_x"] - x_day0) / ppd * 24.0)
    t_axis0 = datetime(t_axis0.year, t_axis0.month, t_axis0.day, t_axis0.hour) + \
        timedelta(hours=round(t_axis0.minute / 60.0))
    off_h = (spec["first_day"] - t_axis0).total_seconds() / 3600.0

    def hours(x):          # 図の x → 軸の左端からの時間 (h)
        return (x - x_day0) / ppd * 24.0 + off_h

    t_end = hours(spec["x_end"])

    # --- 縦軸の較正 ---
    ry = hticks(items, spec["axis_x"], spec["rain"]["ylim"])
    note(len(ry) == len(spec["rain"]["values"]), "rain axis ticks %s" % ry)
    rv = spec["rain"]["values"]
    rain_ppu = (ry[-1] - ry[0]) / (rv[-1] - rv[0])
    qy = hticks(items, spec["axis_x"], spec["runoff"]["ylim"])
    note(len(qy) == len(spec["runoff"]["values"]), "runoff (log) axis ticks %s" % qy)
    qv = spec["runoff"]["values"]
    q_ppd = (qy[-1] - qy[0]) / (math.log10(qv[-1]) - math.log10(qv[0]))
    ybot, ytop = spec["runoff"]["box"]
    yfloor = spec["runoff"]["bottom"]          # 対数軸の下端(枠)の y

    def qval(y):
        return 10 ** (math.log10(qv[0]) + (y - qy[0]) / q_ppd)

    def excluded(x, y):
        return any(a <= x <= c and b <= y <= d for (a, b, c, d) in spec["exclude"])

    # --- 降雨の棒 ---
    bars = set()
    for it in items:
        if it["k"] == "rect" and it["fill"]:
            x0, y0, x1, y1 = it["bbox"]
            if abs(y0 - ry[0]) < 0.05 and spec["axis_x"] < x0 < spec["x_end"] and y1 > y0:
                bars.add((round(x0, 3), round(x1, 3), round(y1, 3)))
    rain = []
    for x0, x1, y1 in sorted(bars):
        rain.append((hours(x0), hours(x1), (y1 - ry[0]) / rain_ppu))
    total = sum((b - a) * r for a, b, r in rain)
    hourly = sum(r for a, b, r in rain)
    rmax = max(r for a, b, r in rain)
    widths = [b - a for a, b, r in rain]
    note(all(abs(w - 1.0) < 0.05 for w in widths),
         "rain bars: %d, width %.3f-%.3f h (hourly)" % (len(rain), min(widths), max(widths)))
    note(abs(rmax - spec["table1"]["max_hourly"]) < 0.06,
         "max hourly rain %.2f mm/h (Table 1: %.1f)" % (rmax, spec["table1"]["max_hourly"]))
    note(abs(hourly - spec["table1"]["total"]) / spec["table1"]["total"] < 0.02,
         "total rain %.2f mm as the sum of hourly bars (Table 1: %.1f; difference %+.2f mm)"
         % (hourly, spec["table1"]["total"], hourly - spec["table1"]["total"]))

    # --- 論文の計算流出強度 ---
    calc = []
    for name, st in spec["calc"].items():
        pts = []
        for it in items:
            if it["k"] not in ("curve", "line") or abs(it["lw"] - st["lw"]) > 0.01:
                continue
            if abs(gray_of(it["scol"]) - st["gray"]) > 0.01:
                continue
            x0, y0, x1, y1 = it["bbox"]
            if not (spec["axis_x"] - 0.1 <= x0 and x1 <= spec["x_end"] + 0.5 and ybot <= y0 and y1 <= ytop):
                continue
            if st["kind"] == "solid" and it["npts"] < 40:
                continue
            if st["kind"] == "dash" and (x1 - x0 > 8.0 or y1 - y0 > 12.0):
                continue
            for (x, y) in it["pts"]:
                if not excluded(x, y):
                    pts.append((x, y))
        pts = sorted(set((round(x, 3), round(y, 3)) for x, y in pts))
        for x, y in pts:
            calc.append((name, hours(x), qval(y), 1 if y <= yfloor + 0.05 else 0))
        note(len(pts) > 30, "calculated %s: %d points" % (name, len(pts)))

    # --- 観測流出強度の記号 ---
    obs = []
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
            obs.append((name, hours(cx), qval(cy), 1 if abs(cy - yfloor) < 0.3 else 0))
        note(len(cen) > 10, "observed %s: %d markers" % (name, len(cen)))

    # --- 書き出し ---
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "rain_%s.csv" % ev), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_start(h)", "t_end(h)", "rain(mm/h)", "start"])
        for a, b, r in rain:
            w.writerow(["%.4f" % a, "%.4f" % b, "%.4f" % r,
                        (t_axis0 + timedelta(hours=a)).strftime("%Y-%m-%d %H:%M")])
    with open(os.path.join(outdir, "calc_%s.csv" % ev), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["catchment", "t(h)", "runoff(mm/h)", "clipped"])
        for row in calc:
            w.writerow([row[0], "%.4f" % row[1], "%.6g" % row[2], row[3]])
    with open(os.path.join(outdir, "obs_%s.csv" % ev), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["catchment", "t(h)", "runoff(mm/h)", "censored"])
        for row in obs:
            w.writerow([row[0], "%.4f" % row[1], "%.6g" % row[2], row[3]])

    # 降雨の段階関数(時間は分。棒のない時間は 0)。&list_precip の prval は線形補間
    # なので、各区間の終わりの直前(0.01 分前)にも同じ値の点を置く
    shift = RAIN_SHIFT_H[ev]
    steps = []
    t = 0.0
    for a, b, r in rain:
        a, b = max(round((a + shift) * 60.0), 0), round((b + shift) * 60.0)
        if a > t:
            steps.append((t, a, 0.0))
        steps.append((a, b, r))
        t = b
    steps.append((t, round(t_end * 60.0) + 60, 0.0))
    with open(os.path.join(outdir, "precip_%s.txt" % ev), "w") as f:
        f.write("! %s の降雨(谷 2023 の%sから extract_tani2023.py が生成。時間は分、強度は mm/h)\n"
                % (ev, spec["figure"]))
        f.write("! 時刻 0 = %s(図の時間軸の左端)。棒の区間を %+.1f h ずらした"
                "(RAIN_SHIFT_H)\n" % (t_axis0.strftime("%Y-%m-%d %H:%M"), shift))
        f.write("&list_precip\n  prtype = 1\n")
        k = 0
        for a, b, r in steps:
            k += 1
            f.write("  prval(1:2,%d) = %.2f, %.4f\n" % (k, a, r))
            k += 1
            f.write("  prval(1:2,%d) = %.2f, %.4f\n" % (k, b - 0.01, r))
        f.write("/\n")
    meta = dict(event=ev, figure=spec["figure"], pdf_page=spec["page"],
                t0=t_axis0.strftime("%Y-%m-%d %H:%M"), t_end_h=t_end,
                rain_total_mm=total, rain_hourly_sum_mm=hourly, rain_max_mmh=rmax,
                table1=spec["table1"], n_rain_bars=len(rain), n_prval=k, rain_shift_h=shift)
    with open(os.path.join(outdir, "meta_%s.json" % ev), "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    print("  time 0 = %s, end = %.1f h, prval points = %d (max 999)" % (meta["t0"], t_end, k))


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
