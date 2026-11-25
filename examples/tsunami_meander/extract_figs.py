#!/usr/bin/env python3
"""小林ら (2019)・小林ら (2021) の PDF の図(ベクタ図形)から、実験値と論文の計算曲線を数値として取り出す

  使い方: python3 extract_figs.py <2019 の PDF> <2021 の PDF> [出力ディレクトリ]
  要るもの: pdftocairo(poppler-utils)。Python は標準ライブラリだけ

  論文の図は Excel のグラフがベクタ図形のまま PDF に埋め込まれている。pdftocairo -svg でページを SVG にし、
  path の座標を読む。軸の校正は、図の枠と目盛線(灰色の格子線)の位置に、図の目盛の数値を対応させた 1 次式の
  最小二乗で行う(当てはめの残差を表示する)。点の座標は PDF の中で約 0.3 pt に丸められていて、これが読み取りの
  分解能を決める(各 CSV の冒頭に書く)。
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/2000/svg}"

# ---------------------------------------------------------------- SVG の path を変換行列つきで読む
def _matrix(t):
    if not t: return (1, 0, 0, 1, 0, 0)
    m = re.match(r"matrix\(([^)]*)\)", t.strip())
    if m: return tuple(float(v) for v in re.split(r"[ ,]+", m.group(1).strip()))
    m = re.match(r"translate\(([^)]*)\)", t.strip())
    v = [float(x) for x in re.split(r"[ ,]+", m.group(1).strip())]
    return (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
def _mul(a, b):
    return (a[0]*b[0] + a[2]*b[1], a[1]*b[0] + a[3]*b[1], a[0]*b[2] + a[2]*b[3], a[1]*b[2] + a[3]*b[3],
            a[0]*b[4] + a[2]*b[5] + a[4], a[1]*b[4] + a[3]*b[5] + a[5])
def _subpaths(d, m):
    toks = re.findall(r"[MLCZ]|-?\d*\.?\d+(?:[eE][-+]?\d+)?", d)
    subs, cur, i = [], [], 0
    def pt(k): return (m[0]*float(toks[k]) + m[2]*float(toks[k+1]) + m[4], m[1]*float(toks[k]) + m[3]*float(toks[k+1]) + m[5])
    while i < len(toks):
        t = toks[i]
        if t == "M":
            if cur: subs.append(cur)
            cur = [pt(i+1)]; i += 3
        elif t == "L": cur.append(pt(i+1)); i += 3
        elif t == "C": cur.append(pt(i+5)); i += 7
        elif t == "Z": i += 1
        else: cur.append(pt(i)); i += 2
    if cur: subs.append(cur)
    return subs
def read_page(pdf, page, tmp):
    svg = os.path.join(tmp, f"p{page}.svg")
    subprocess.run(["pdftocairo", "-svg", "-f", str(page), "-l", str(page), pdf, svg], check=True)
    out = []
    def walk(el, m):
        tag = el.tag.replace(NS, "")
        if tag in ("defs", "clipPath", "mask"): return
        mm = _mul(m, _matrix(el.get("transform"))) if el.get("transform") else m
        if tag == "path":
            subs = _subpaths(el.get("d"), mm)
            pts = [q for s in subs for q in s]
            if pts:
                xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
                out.append(dict(stroke=el.get("stroke"), fill=el.get("fill"), sw=float(el.get("stroke-width") or 0),
                                dash=el.get("stroke-dasharray"), subs=subs, pts=pts,
                                bb=(min(xs), max(xs), min(ys), max(ys))))
        for ch in el: walk(ch, mm)
    walk(ET.parse(svg).getroot(), (1, 0, 0, 1, 0, 0))
    return out

# ---------------------------------------------------------------- 色の判定
def rgb(c):
    if not c or c == "none": return None
    m = re.match(r"rgb\(([\d.]+)%, *([\d.]+)%, *([\d.]+)%\)", c)
    return tuple(float(v) for v in m.groups()) if m else None
def is_color(c, ref, tol=3.0):
    v = rgb(c)
    return v is not None and all(abs(a - b) <= tol for a, b in zip(v, ref))
BLACK, WHITE, GRID = (0, 0, 0), (100, 100, 100), (85.1, 85.1, 85.1)
BLUE, ORANGE, GRAY, YELLOW, LBLUE, RED = (26.7, 44.7, 76.9), (92.9, 49.0, 19.2), (64.7, 64.7, 64.7), (100, 75.3, 0), (35.7, 60.8, 83.5), (100, 0, 0)

# ---------------------------------------------------------------- 図(枠)と軸の校正
def lsq(p, v):
    n = len(p); mp = sum(p) / n; mv = sum(v) / n
    a = sum((x - mp) * (y - mv) for x, y in zip(p, v)) / sum((x - mp) ** 2 for x in p)
    b = mv - a * mp
    return a, b, max(abs(a * x + b - y) for x, y in zip(p, v))
class Chart:
    """frame = (x0, x1, y0, y1): 図の枠の位置(ページ座標 pt。±2 の範囲で探す)
       xvals / yvals: 「枠の左端(下端)+ 枠の内側の目盛線」に、左(下)から順に対応する目盛の数値。
       None を入れた位置は校正に使わない(枠の端が目盛でないとき)"""
    def __init__(self, paths, frame, xvals, yvals, name, xframe=None):
        self.name = name
        fr = [p for p in paths if is_color(p["stroke"], BLACK) and len(p["pts"]) in (4, 5) and
              all(abs(a - b) < 2.0 for a, b in zip(p["bb"], frame))]
        if not fr: raise RuntimeError(f"{name}: frame not found {frame}")
        self.bb = fr[0]["bb"]; x0, x1, y0, y1 = self.bb
        # この図の系列は、枠の path から次の図の枠(黒い線の矩形)か背景(白い大きな矩形)までの間に並ぶ
        # (隣の図の、枠の外へ伸びた線や、凡例の見本を拾わない)
        def is_rect(q):
            if len(q["subs"]) != 2 or len(q["subs"][0]) not in (4, 5): return False
            a0, a1, b0, b1 = q["bb"]
            return (a1 - a0) > 60 and (b1 - b0) > 40 and all(min(abs(x - a0), abs(x - a1)) < 0.05 and min(abs(y - b0), abs(y - b1)) < 0.05
                                                             for x, y in q["subs"][0])
        self.i0 = paths.index(fr[0]); self.i1 = len(paths)
        for j in range(self.i0 + 1, len(paths)):
            q = paths[j]
            w = q["bb"][1] - q["bb"][0]; h = q["bb"][3] - q["bb"][2]
            if is_rect(q) and is_color(q["stroke"], BLACK) and q["fill"] in (None, "none") and q["bb"] != self.bb:
                self.i1 = j; break
            if is_rect(q) and is_color(q["fill"], WHITE) and q["stroke"] is None and w > 150 and h > 90:   # 次の図・凡例の背景
                self.i1 = j; break
        gx, gy = set(), set()
        for p in paths:
            if not is_color(p["stroke"], GRID): continue
            if p["bb"][0] < x0 - 1 or p["bb"][1] > x1 + 1 or p["bb"][2] < y0 - 1 or p["bb"][3] > y1 + 1: continue
            for s in p["subs"]:
                if len(s) != 2: continue
                if abs(s[0][0] - s[1][0]) < 0.05 and abs(s[0][1] - s[1][1]) > 10: gx.add(round(s[0][0], 2))
                if abs(s[0][1] - s[1][1]) < 0.05 and abs(s[0][0] - s[1][0]) > 10: gy.add(round(s[0][1], 2))
        px = [x0] + sorted(g for g in gx if g > x0 + 0.5)
        py = [y1] + sorted((g for g in gy if g < y1 - 0.5), reverse=True)
        def fit(pos, vals, what):
            if len(pos) != len(vals): raise RuntimeError(f"{name}: {what} ticks {len(pos)} != values {len(vals)}: {pos}")
            pp = [p for p, v in zip(pos, vals) if v is not None]; vv = [v for v in vals if v is not None]
            return lsq(pp, vv)
        if xframe is None:
            self.ax, self.bx, rx = fit(px, xvals, "x")
        else:      # 縦の目盛線がない図: 枠の左右端の値(軸の目盛の両端)で校正する
            self.ax = (xframe[1] - xframe[0]) / (x1 - x0); self.bx = xframe[0] - self.ax * x0; rx = 0.0
        self.ay, self.by, ry = fit(py, yvals, "y")
        # PDF の座標の丸め(約 0.3 pt)が読み取りの分解能を決める
        self.resx = abs(self.ax) * 0.31; self.resy = abs(self.ay) * 0.31
        print(f"  {name}: frame x[{x0:.1f},{x1:.1f}] y[{y0:.1f},{y1:.1f}]  fit residual x {rx:.4f} y {ry:.4f}  resolution x {self.resx:.4f} y {self.resy:.4f}")
    def val(self, q): return (self.ax * q[0] + self.bx, self.ay * q[1] + self.by)
    def inside(self, p, mrg=3.0):
        x0, x1, y0, y1 = self.bb; cx = 0.5 * (p["bb"][0] + p["bb"][1]); cy = 0.5 * (p["bb"][2] + p["bb"][3])
        return x0 - mrg <= cx <= x1 + mrg and y0 - mrg <= cy <= y1 + mrg
    def markers(self, paths, stroke=None, fill="any", size=6.0):
        """小さな閉じた図形(マーカー)の中心。fill=None は白抜き(fill が none か白)"""
        out = []
        for p in paths[self.i0 + 1:self.i1]:
            w = p["bb"][1] - p["bb"][0]; h = p["bb"][3] - p["bb"][2]
            if w > size or h > size or w < 0.5 or h < 0.5 or not self.inside(p): continue
            if stroke is not None and not is_color(p["stroke"], stroke): continue
            if fill is None:
                if not (p["fill"] in (None, "none") or is_color(p["fill"], WHITE)): continue
            elif fill != "any" and not is_color(p["fill"], fill): continue
            out.append(self.val((0.5 * (p["bb"][0] + p["bb"][1]), 0.5 * (p["bb"][2] + p["bb"][3]))))
        return sorted(out)
    def lines(self, paths, stroke, dashed=None, minpts=3, sw=None):
        """枠に重なる折れ線(点数 minpts 以上)。枠の外へ出た点は捨てる"""
        out = []
        x0, x1, y0, y1 = self.bb
        for p in paths[self.i0 + 1:self.i1]:
            if len(p["subs"]) != 1 or len(p["pts"]) < minpts or not is_color(p["stroke"], stroke): continue
            if p["fill"] not in (None, "none"): continue
            if dashed is not None and bool(p["dash"]) != dashed: continue
            if sw is not None and abs(p["sw"] - sw) > 0.05: continue
            if p["bb"][1] < x0 or p["bb"][0] > x1 or p["bb"][3] < y0 or p["bb"][2] > y1: continue
            pts = [self.val(q) for q in p["pts"] if x0 - 0.5 <= q[0] <= x1 + 0.5 and y0 - 0.5 <= q[1] <= y1 + 0.5]
            if len(pts) >= minpts: out.append(pts)
        return out

def write_csv(fn, header, rows, fmt):
    with open(fn, "w") as f:
        for h in header[:-1]: f.write("# " + h + "\n")
        f.write(header[-1] + "\n")
        for r in rows: f.write(",".join(fm.format(v) if not isinstance(v, str) else v for fm, v in zip(fmt, r)) + "\n")
    print(f"  -> {fn} ({len(rows)} rows)")

SRC19 = "小林大祐・内田龍彦・河原能久 (2019): 蛇行水路における段波の伝播特性に関する実験的研究, 河川技術論文集, 25, 249-254. doi:10.11532/river.25.0_249"
SRC21 = "小林大祐・内田龍彦・太田一行 (2021): 蛇行水路における波状段波の増幅特性, 土木学会論文集B1(水工学), 77(2), I_1183-I_1188. doi:10.2208/jscejhe.77.2_I_1183"
HOW = "図のベクタ図形の座標を extract_figs.py で読んだ値(手作業の読み取りではない)。軸は図の枠と目盛線で校正"

def main():
    pdf19, pdf21 = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "data_kobayashi"
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp()

    # ================= 2019: 図-2・図-3 断面平均波高の時間変化(断面 1・4・8)
    print("2019 Fig.2, Fig.3")
    P = read_page(pdf19, 3, tmp)
    cfg = [("breaking", 1, (103.8, 266.4, 86.4, 165.8), [2.35, 4.85, 7.35, 9.85, 12.35]),
           ("breaking", 4, (127.6, 259.9, 240.4, 315.6), [12.31, 14.81, 17.31, 19.81]),
           ("breaking", 8, (154.9, 238.8, 386.0, 459.3), [26.39, 31.39]),
           ("undular", 1, (324.2, 490.4, 87.3, 166.3), [1.76, 4.26, 6.76, 9.26, 11.76]),
           ("undular", 4, (330.0, 473.9, 242.5, 316.8), [11.73, 14.23, 16.73, 19.23, 21.73]),
           ("undular", 8, (346.7, 468.8, 387.1, 460.9), [25.22, 27.72, 30.22, 32.72])]
    rows = []
    for bore, sec, frame, xv in cfg:
        c = Chart(P, frame, xv, [0.0, 0.5, 1.0, None], f"fig{2 if bore == 'breaking' else 3} sec{sec}")
        for x, y in c.markers(P, stroke=BLACK, fill=BLACK, size=4.0): rows.append((bore, sec, x, y))
    write_csv(os.path.join(out, "k2019_fig2_fig3_section_mean.csv"),
              [SRC19, "図-2(砕波段波)・図-3(波状段波)の実験値: 断面 1・4・8 の断面平均波高(1 断面 5 点の平均)の時間変化", HOW,
               "tstar = t sqrt(g/h0)(t はゲート開放からの時間、h0 = 0.285 m)、eta = 断面平均波高 / 解析波高 h_t0",
               "読み取りの分解能: tstar 約 0.02、eta 約 0.006", "bore,section,tstar,eta"],
              rows, ["{}", "{:d}", "{:.3f}", "{:.4f}"])

    # ================= 2019: 図-4・図-5 横断方向の時間平均波高分布(断面 1・4・8)
    print("2019 Fig.4, Fig.5")
    P = read_page(pdf19, 4, tmp)
    cfg = [("breaking", 1, (110.7, 277.3, 75.5, 159.7)), ("breaking", 4, (110.9, 279.0, 217.5, 301.1)), ("breaking", 8, (108.7, 279.9, 366.7, 451.3)),
           ("undular", 1, (337.2, 498.9, 77.3, 161.5)), ("undular", 4, (338.6, 502.1, 221.0, 304.8)), ("undular", 8, (338.4, 505.1, 370.6, 455.0))]
    rows = []
    for bore, sec, frame in cfg:
        # 縦の目盛線は 0.25・0.5・0.75・1(枠の右端 = 1 に重なる)、横の目盛線は -0.3〜0.4 の 0.1 刻み(0 の線は軸の色なので
        # 目盛線に数えない。0.4 の線は枠の上端に重なる)
        c = Chart(P, frame, [0.0, 0.25, 0.5, 0.75, 1.0], [-0.4, -0.3, -0.2, -0.1, 0.1, 0.2, 0.3, 0.4], f"fig{4 if bore == 'breaking' else 5} sec{sec}")
        ex = c.lines(P, BLACK, dashed=True, minpts=5, sw=2.25)
        an = c.lines(P, BLACK, dashed=False, minpts=20, sw=2.25)
        assert len(ex) == 1 and len(ex[0]) == 5 and len(an) == 1, (len(ex), len(an))
        for x, y in ex[0]: rows.append((bore, sec, "exp", x, y))
        for x, y in an[0][:-1:6] + [an[0][-2]]: rows.append((bore, sec, "analytical", x, y))   # 線の最後の 1 点は枠の角へ戻る点
    write_csv(os.path.join(out, "k2019_fig4_fig5_transverse.csv"),
              [SRC19, "図-4(砕波段波)・図-5(波状段波): 断面 1・4・8 の、断面平均からの偏差の時間平均の横断分布", HOW,
               "exp = 実験値(1 断面 5 点)、analytical = 論文の解析解(一様湾曲の定常流の横断水面形。論文の式 (6)。線の 6 点おき)",
               "n_over_B = 左岸からの距離 / 水路幅、dev = (波高 - 断面平均波高) の時間平均 / h_t0",
               "図の凡例は実線を「実験波高」、点付きの破線を「解析波高」としているが、5 点の折れ線(測定点は 1 断面 5 点)が点付きの破線で、",
               "本文の記述(断面 8 の外岸で実測が解析解よりかなり大きい)とも合うので、点付きの破線を実験値、実線を解析解として読んだ",
               "読み取りの分解能: dev 約 0.003", "bore,section,series,n_over_B,dev"],
              rows, ["{}", "{:d}", "{}", "{:.4f}", "{:.4f}"])

    # ================= 2019: 図-8 最大波高の縦断分布、図-10 断面 4 の 5 点の波高
    print("2019 Fig.8, Fig.10")
    P = read_page(pdf19, 6, tmp)
    rows = []
    for bore, frame in (("breaking", (108.1, 279.9, 67.2, 174.7)), ("undular", (340.6, 511.5, 66.9, 174.1))):
        c = Chart(P, frame, [0.0, 0.25, 0.5, 0.75, 1.0], [0.8, 1.2, 1.6, 2.0, None], f"fig8 {bore}")
        for bank, fill in (("left", BLACK), ("right", WHITE)):
            mk = c.markers(P, stroke=BLACK, fill=fill, size=5.0)
            assert len(mk) == 8, len(mk)
            for k, (x, y) in enumerate(mk, 1): rows.append((bore, k, bank, x, y))
    write_csv(os.path.join(out, "k2019_fig8_max_height.csv"),
              [SRC19, "図-8 の実験値: 両岸沿い(岸から 0.02 m)の最大波高の縦断分布。断面 1〜8", HOW,
               "s_over_L = 蛇行の始点(ゲート)からの中心線に沿う距離 / 蛇行長、hmax = 最大波高 / h_t0",
               "読み取りの分解能: hmax 約 0.005", "bore,section,bank,s_over_L,hmax"],
              rows, ["{}", "{:d}", "{}", "{:.4f}", "{:.4f}"])
    c = Chart(P, (339.2, 503.7, 269.2, 382.6), [2.1, 2.3, 2.5, 2.7], [0.0, 0.5, 1.0, 1.5, 2.0, 2.5], "fig10")
    rows = []
    for d, col in ((0.02, BLUE), (0.20, ORANGE), (0.40, GRAY), (0.60, YELLOW), (0.78, LBLUE)):
        mk = c.markers(P, stroke=col, fill=col, size=3.0)
        for x, y in mk: rows.append((d, x, y))
    write_csv(os.path.join(out, "k2019_fig10_section4.csv"),
              [SRC19, "図-10 の実験値: 波状段波の断面 4 の 5 点の波高の時間変化(到達の前後 0.6 s)", HOW,
               "dist_left = 左岸(断面 4 の外岸)からの距離 (m)、t = ゲート開放からの時間 (s)、eta = 波高 / h_t0",
               "読み取りの分解能: t 約 0.001 s、eta 約 0.007", "dist_left,t,eta"],
              rows, ["{:.2f}", "{:.4f}", "{:.4f}"])

    # ================= 2021: 図-2・図-3 直線水路、図-4 第 1 波波高の比較
    print("2021 Fig.2, Fig.3, Fig.4")
    P = read_page(pdf21, 3, tmp)
    c = Chart(P, (340.0, 536.9, 60.6, 126.5), [17.6, 22.6, 27.6, 32.6], [0.0, 0.4, 0.8, 1.2, None], "2021 fig2")
    rows = [("exp", x, y) for x, y in c.markers(P, stroke=BLACK, fill=None, size=5.0)]
    for nm, col, dashed in (("calc2d", BLACK, True), ("calc3d_coarse", BLUE, False), ("calc3d_fine", ORANGE, False)):
        ln = c.lines(P, col, dashed=dashed, minpts=50)
        assert len(ln) == 1, (nm, len(ln))
        rows += [(nm, x, y) for x, y in ln[0][::2]]
    write_csv(os.path.join(out, "k2021_fig2_straight_sec4.csv"),
              [SRC21, "図-2: 直線水路の Section 4(水路中央)の波高の時間変化。exp = 実験値、calc2d = 論文の平面 2 次元計算(浅水流方程式)、",
               "calc3d_coarse / calc3d_fine = 論文の 3 次元計算(OpenFOAM interFoam。粗い格子・細かい格子)。計算の線は 2 点おき", HOW,
               "tstar = 図の横軸の値(t sqrt(g/h0) と書かれているが、段波の到達がゲートからの距離 4.03 m と合わない。時刻の原点は不明)、eta = 波高 / h_t",
               "読み取りの分解能: tstar 約 0.008、eta 約 0.002", "series,tstar,eta"],
              rows, ["{}", "{:.3f}", "{:.4f}"])
    c = Chart(P, (350.0, 522.4, 328.0, 391.6), None, [0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, None], "2021 fig4", xframe=(0.0, 1.25))
    rows = []
    for nm, col, dashed in (("S110_outer", RED, False), ("S110_inner", BLUE, False), ("S125_outer", RED, True), ("S125_inner", BLUE, True),
                            ("straight_LmS110", BLACK, False), ("straight_LmS125", BLACK, True)):
        ln = [l for l in c.lines(P, col, dashed=dashed, minpts=6) if len(l) == 6]
        assert len(ln) == 1, (nm, len(ln))
        for k, (x, y) in zip((1, 3, 4, 5, 7, 8), ln[0]): rows.append((nm, k, x, y))
    write_csv(os.path.join(out, "k2021_fig4_first_wave.csv"),
              [SRC21, "図-4 の実験値: 波状段波の第 1 波の波高。蛇行水路(S = 1.10、S = 1.25)の外岸沿い・内岸沿い(岸から 0.02 m)と直線水路(中央)", HOW,
               "s_over_Lm = 蛇行の始点からの中心線に沿う距離 / 蛇行長(直線水路はゲートからの距離を 2 つの蛇行長で割った 2 通り)、h1st = 第 1 波の波高 / h_t",
               "外岸 = 各湾曲部の曲率半径方向の側壁(Section 1・7・8 は右岸、Section 3・4・5 は左岸)",
               "読み取りの分解能: h1st 約 0.006、s_over_Lm 約 0.002", "series,section,s_over_Lm,h1st"],
              rows, ["{}", "{:d}", "{:.4f}", "{:.4f}"])

    # ================= 2021: 図-5 外岸沿いの第 1 波波高の縦断分布、図-6 Section 4 外岸の時間変化
    print("2021 Fig.5, Fig.6")
    P = read_page(pdf21, 4, tmp)
    rows = []
    for ch, frame in (("S125", (99.1, 290.8, 75.4, 132.1)), ("S110", (325.8, 514.1, 76.9, 132.1))):
        c = Chart(P, frame, None, [1.0, 1.5, 2.0, 2.5], f"2021 fig5 {ch}", xframe=(0.0, 1.25))
        mk = c.markers(P, stroke=BLACK, fill=BLACK, size=6.0)
        assert len(mk) == 6, len(mk)
        rows += [(ch, "exp", x, y) for x, y in mk]
        for nm, dashed in (("calc2d", True), ("calc3d", False)):
            for col in (BLUE, RED):
                for ln in c.lines(P, col, dashed=dashed, minpts=20):
                    rows += [(ch, nm, x, y) for x, y in ln[::3] + [ln[-1]]]
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    write_csv(os.path.join(out, "k2021_fig5_outer_bank.csv"),
              [SRC21, "図-5: 蛇行水路の外岸沿いの第 1 波の波高の縦断分布。exp = 実験値、calc2d = 論文の平面 2 次元計算の初期ピーク、calc3d = 論文の 3 次元計算(線は 3 点おき)", HOW,
               "s_over_Lm = 蛇行の始点からの中心線に沿う距離 / 蛇行長(0〜0.25 と 0.75〜1.25 は右岸、0.25〜0.75 は左岸)、h1st = 第 1 波の波高 / h_t",
               "読み取りの分解能: h1st 約 0.003、s_over_Lm 約 0.002", "channel,series,s_over_Lm,h1st"],
              rows, ["{}", "{}", "{:.4f}", "{:.4f}"])
    rows = []
    for ch, frame, xv, yv in (("S125", (102.0, 296.3, 198.8, 273.0), [11.73, 16.73, 21.73, 26.73], [0.0, 0.4, 0.8, 1.2, 1.6]),
                              ("S110", (332.4, 519.8, 198.9, 271.2), [8.78, 13.78, 18.78, 23.78], [0.0, 0.5, 1.0, 1.5, 2.0, 2.5])):
        c = Chart(P, frame, xv, yv, f"2021 fig6 {ch}")
        rows += [(ch, "exp", x, y) for x, y in c.markers(P, stroke=BLACK, fill=None, size=5.0)]
        for nm, col, dashed in (("calc2d", BLACK, True), ("calc3d", BLUE, False)):
            ln = c.lines(P, col, dashed=dashed, minpts=50)
            assert len(ln) == 1, (ch, nm, len(ln))
            rows += [(ch, nm, x, y) for x, y in ln[0][::2]]
    write_csv(os.path.join(out, "k2021_fig6_sec4_outer.csv"),
              [SRC21, "図-6: 蛇行水路の Section 4 の外岸(左岸から 0.02 m)の波高の時間変化。exp = 実験値、calc2d = 論文の平面 2 次元計算、calc3d = 論文の 3 次元計算(線は 2 点おき)", HOW,
               "tstar = 図の横軸の値(t sqrt(g/h0))、eta = 波高 / h_t。S = 1.25 の図は、段波の到達がゲートからの距離と合わない(時刻の原点は不明)",
               "読み取りの分解能: tstar 約 0.008、eta 約 0.003", "channel,series,tstar,eta"],
              rows, ["{}", "{}", "{:.3f}", "{:.4f}"])

if __name__ == "__main__":
    main()
