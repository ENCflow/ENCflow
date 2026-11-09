#!/usr/bin/env python3
"""wetbank: 雨で濡れた河岸が斜めのラスタ河道の水深を変えないことの検定の入力と設定を生成する。

  python3 make_init.py          → d_<geo>/(z.txt・mask.txt・rw.txt・s.txt・info.txt)と p_<case>.txt
  python3 make_init.py list     → ケース名を 1 行に 1 つ書く(Run.sh 用)

水路の中心線は 西端から東向きの入口区間(300 m 以上)→ 格子に対して角度 θ の斜めの区間(長さ L)
→ 東向きの出口区間(300 m 以上)で東端の自由流出へ抜ける。河道は中心線からの垂直距離 d が
-ω/2 < d <= ω/2 のセルで、ω = N·Δx·(cos θ + sin θ)。N = 1 は 4 連結の 1 セル幅の階段(数値幾何の
標準の離散直線)で、tutorials/chichibu の河道マスクと同じ型(河道が 1 セル横にずれる段を持つ)。
継ぎ目は各区間の帯を w/2 延長して埋める。河床は中心線に沿う距離 s で Z0 − S·s。河岸は河道から
B 以内のセルで、標高は 河床 + H + SC·(距離 − ω/2)(河道へ向かう横断勾配 SC。雨水はすぐ河道へ入る)。
それより外は領域外。上流端は区間流入 Q0 = q0·N·Δx(格子に沿う 1 セル幅で水深約 2 m)。

ケース = 形 × 雨(0 = 乾いた河岸、20 mm/h)× f_advection_donor(0・3)。形は Δx = 50 m・1 セル幅の
θ = 0・10・22.5・30・45°、θ = 22.5° の 1 セル幅の Δx = 100・25 m、幅 100 m を 2・4 セルで表したもの。
"""
import math, os, sys

S, Z0, H, SC = 0.0044, 100.0, 6.0, 0.02       # 河床勾配、基準標高、河岸の高さ (m)、河岸の横断勾配
L, B = 4000.0, 250.0                          # 斜めの区間の長さ (m)、片側の河岸の帯の幅 (m)
Q0_UNIT, RN = 6.0, 0.035                      # 単位幅流量 (m²/s)、粗度
RAIN = 20.0                                   # 雨のケースの降雨強度 (mm/h)
TT, DT_FILE = 10800.0, 1800.0                 # 計算時間 (s)、出力間隔 (s)
GEOMS = [(0.0, 50.0, 1), (10.0, 50.0, 1), (22.5, 50.0, 1), (30.0, 50.0, 1), (45.0, 50.0, 1),
         (22.5, 100.0, 1), (22.5, 25.0, 1), (22.5, 50.0, 2), (22.5, 25.0, 4)]


def tag(th, dx, nc):
    return f"a{th:g}".replace(".", "p") + f"_dx{dx:g}_n{nc}"


def cases():
    return [f"{tag(*g)}_r{r:g}_o{o}" for g in GEOMS for r in (0.0, RAIN) for o in (0, 3)]


def make_geom(th_deg, dx, nc, out):
    th = math.radians(th_deg)
    lin = max(300.0, 4 * dx)
    omega = nc * dx * (math.cos(th) + math.sin(th))
    ow = nc * dx
    margin = B + omega + 2 * dx
    p0, p1 = (0.0, margin), (lin, margin)
    p2 = (lin + L * math.cos(th), margin + L * math.sin(th))
    p3 = (p2[0] + lin, p2[1])
    nx = int(math.ceil(p3[0] / dx))
    ny = int(math.ceil((p2[1] + margin) / dx))
    segs = [(p0, p1, ow), (p1, p2, omega), (p2, p3, ow)]
    cum = [0.0]
    for a, b, _ in segs:
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    z = [[Z0 + 50.0] * nx for _ in range(ny)]
    mask = [[0] * nx for _ in range(ny)]
    rw = [[0] * nx for _ in range(ny)]
    sg = [[-1.0] * nx for _ in range(ny)]
    for j in range(ny):                       # j = 0 が北端の行
        y = (ny - j - 0.5) * dx
        for i in range(nx):
            x = (i + 0.5) * dx
            best, chan = None, False
            for k, (a, b, w) in enumerate(segs):
                ex, ey = b[0] - a[0], b[1] - a[1]
                ln = math.hypot(ex, ey)
                ux, uy = ex / ln, ey / ln
                t = (x - a[0]) * ux + (y - a[1]) * uy
                tc = min(max(t, 0.0), ln)
                d = -(x - a[0]) * uy + (y - a[1]) * ux
                dist = math.hypot(x - (a[0] + tc * ux), y - (a[1] + tc * uy))
                if -w / 2 < d <= w / 2 and -w / 2 <= t <= ln + w / 2:
                    chan = True
                if best is None or dist < best[0]:
                    best = (dist, cum[k] + tc, w)
            dist, s, w = best
            if chan:
                z[j][i], mask[j][i], rw[j][i], sg[j][i] = Z0 - S * s, 1, 1, s
            elif dist <= w / 2 + B:
                z[j][i] = Z0 - S * s + H + SC * max(dist - w / 2, 0.0)
                mask[j][i], sg[j][i] = 1, s
    # 河道が西端から東端まで 4 連結でつながることを確かめる
    chan = {(i, j) for j in range(ny) for i in range(nx) if rw[j][i]}
    seen = {(i, j) for i, j in chan if i == 0}
    stack = list(seen)
    while stack:
        i, j = stack.pop()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (i + di, j + dj)
            if q in chan and q not in seen:
                seen.add(q)
                stack.append(q)
    if not any(i == nx - 1 for i, _ in seen):
        sys.exit(f"{out}: channel is not 4-connected from west to east")
    os.makedirs(out, exist_ok=True)
    for name, a, fmt in (("z", z, "%.4f"), ("mask", mask, "%d"), ("rw", rw, "%d"), ("s", sg, "%.2f")):
        with open(os.path.join(out, name + ".txt"), "w") as f:
            for row in a:
                f.write(" ".join(fmt % v for v in row) + "\n")
    inflow = [(i + 1, j + 1) for j in range(ny) for i in range(nx) if rw[j][i] and i == 0]
    with open(os.path.join(out, "info.txt"), "w") as f:
        f.write(f"nx {nx}\nny {ny}\ndx {dx:g}\ntheta {th_deg:g}\nncell {nc}\nomega {omega:.4f}\n")
        f.write(f"L {L:g}\nB {B:g}\nlin {lin:g}\nS {S:g}\nq0 {Q0_UNIT * nc * dx:g}\nrn {RN:g}\n")
        f.write("inflow " + " ".join(f"{i},{j}" for i, j in inflow) + "\n")
    return nx, ny, inflow


def write_param(case, geo, dx, nc, nx, ny, inflow, rain, opt):
    q0 = Q0_UNIT * nc * dx
    cells = "\n".join(f"  inflow_cell(:,{k + 1},1) = {i}, {j}" for k, (i, j) in enumerate(inflow))
    precip = (f"&list_precip\n  prtype = 1\n  prval(:,1) =    0, {rain:g}\n  prval(:,2) = 6000, {rain:g}\n/\n"
              if rain > 0 else "")
    text = f"""! wetbank: {case}(make_init.py が生成。斜めの区間の向き・格子・河道の太さは d_{geo}/info.txt)
&list_sysparam
  dt = {dx / 25.0:g}
  t0 = 0
  tt = {TT:g}
  dt_disp = 1800
  dt_file = {DT_FILE:g}
  fn_geoinfo = '-'
  fn_initial = '-'
  fn_enc = '-'
  fn_boundary = '-'
  fn_precip = '{"-" if rain > 0 else ""}'
  dir_data = 'd_{geo}'
  dir_result = 'result_{case}'
  f_out_h = 1
/
&list_enc
  f_advection_donor = {opt}
/
&list_initial
  f_htype = 0
  h0 = 0.0
/
&list_geoinfo
  nx = {nx}
  ny = {ny}
  dx = {dx:g}
  dy = {dx:g}
  f_ztype = 1
  fn_z = 'z.txt'
  f_masktype = 1
  fn_mask = 'mask.txt'
  fn_rw = 'rw.txt'
  f_rntype = 0
  rn0 = {RN:g}
  rn0_rw = {RN:g}
/
{precip}&list_bound_edge
  f_bc_e = 1
/
&list_bound_inflow
{cells}
  inflow_val(:,1,1) =    0, {q0:g}
  inflow_val(:,2,1) = 6000, {q0:g}
  inflow_dist(1) = 0
/
"""
    with open(f"p_{case}.txt", "w") as f:
        f.write(text)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print("\n".join(cases()))
        sys.exit(0)
    for th, dx, nc in GEOMS:
        geo = tag(th, dx, nc)
        nx, ny, inflow = make_geom(th, dx, nc, f"d_{geo}")
        for rain in (0.0, RAIN):
            for opt in (0, 3):
                write_param(f"{geo}_r{rain:g}_o{opt}", geo, dx, nc, nx, ny, inflow, rain, opt)
        print(f"d_{geo}: nx {nx}, ny {ny}")
