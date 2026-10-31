#!/usr/bin/env python3
# fluxline(流量測線の角度掃引)の検定(developer.md §24.3)
#   使い方: Check_fluxline.py stair [resdir]   構成 1(param_stair.txt。既定 result_stair)
#           Check_fluxline.py xy [resdir]      構成 2(param_xy.txt。既定 result_xy)
#   読むもの: resdir/fluxes/flux*.csv(測線の幾何は見出し、流量は最後の行)と、最終の水深・流速
#             の分布 H9998.bil・V9998.bil(float32)
#
#   定常の東向きの流れ(全幅の流量 Q)に置いた測線を、測線の種類ごとに比べる。
#   単位幅流量 q は測線が通るセルの h·|V| の平均(流れは東向きなので x 成分に等しい)。
#   stair(セル番号指定。ENC は階段面のエッジ流量。§24.2):
#     壁から壁・y 長手(流れに直交する向きから 45° 未満): Q に一致(|差| ≤ 5e-4 m³/s)
#     壁から壁・x 長手(45° 以上): Q − q_end。q_end は北端の踏面セル(壁沿いの行)の h·|V|。
#       長手方向にだけ半セル延長する規約(§24 (2b))で、その踏面セルから下流へ抜ける流量を
#       含まない(比 1 ± 0.01)
#     内部・y 長手: q (n − δ)(n は踏面の数)。δ は端の角を通る斜めエッジ(各端 2 本)を
#       数えない分で、d = 2/(2+√2) = 0.586 に近い。0.55〜0.62 で、角度・長さによらない
#       (ばらつき 0.005 以下)
#     内部・x 長手: q |Δj|(中心間の行差。比 1 ± 0.005)
#     流れに平行: |Q| ≤ 2e-3 m³/s
#   xy(実座標指定。セル内線分成分の積算。§36.2):
#     壁から壁: 全角度で Q に一致(|差| ≤ 5e-4 m³/s)
#     内部: q × 線分の南北の長さ(F·n̂·L。比 1 ± 2e-4)
#     流れに平行: |Q| ≤ 1e-3 m³/s
#   さらに、壁から壁の測線の最後の 2 行(2100 s・2400 s)の差が 2e-4 m³/s 以下(定常)。
#   水路と流れは param_*.txt・make_init.py と対で保守する
import glob
import math
import os
import struct
import sys

NX, NY = 500, 21
Q_IN = 9.860442
DIAG = 2.0 / (2.0 + math.sqrt(2.0))


def read_bil(resdir, name):
    with open(os.path.join(resdir, name), "rb") as f:
        return struct.unpack("<%df" % (NX * NY), f.read())


def read_flux(fn):
    head, rows = {}, []
    with open(fn) as f:
        for line in f:
            if line.startswith("# xR"):
                head["xy"] = [float(v) for v in line.split("=,")[1].split(",")]
            elif line.startswith("# ixR"):
                head["ij"] = [int(v) for v in line.split("=,")[1].split(",")]
            elif not line.startswith("#"):
                rows.append([float(v) for v in line.split(",")])
    return head, rows


def main(mode="stair", resdir=None):
    if mode not in ("stair", "xy"):
        print("usage: Check_fluxline.py stair|xy [resdir]", file=sys.stderr)
        return 2
    resdir = resdir or "result_" + mode
    h = read_bil(resdir, "H9998.bil")
    vv = read_bil(resdir, "V9998.bil")
    qc = lambda i, j: h[(j - 1) * NX + i - 1] * vv[(j - 1) * NX + i - 1]
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    print("== fluxline %s: flux transects across a steady eastward flow (Q = %.6f m3/s)" % (mode, Q_IN))
    deltas, steady = [], 0.0
    for fn in sorted(glob.glob(os.path.join(resdir, "fluxes", "flux*.csv"))):
        head, rows = read_flux(fn)
        name = os.path.basename(fn)[4:8]
        qline = rows[-1][2]
        iR, jR, iL, jL = head["ij"]
        xR, yR, xL, yL = head["xy"]
        if mode == "stair":
            di, dj = iL - iR, jL - jR
            phi = math.degrees(math.atan2(abs(di), abs(dj)))
            if dj == 0:
                check(abs(qline) <= 2.0e-3, f"{name} parallel to the flow ({abs(di) + 1} cells): Q = {qline:.4f}")
                continue
            ylong = abs(dj) > abs(di)
            cells = []
            if ylong:
                for j in range(min(jR, jL), max(jR, jL) + 1):
                    cells.append((int(math.floor(iR + (j - jR) * di / dj + 0.5)), j))
            else:
                for i in range(min(iR, iL), max(iR, iL) + 1):
                    cells.append((i, int(math.floor(jR + (i - iR) * dj / di + 0.5))))
            q = sum(qc(i, j) for i, j in cells) / len(cells)
            full = sorted((jR, jL)) == [1, NY]
            kind = ("wall to wall" if full else "interior") + (", y-long" if ylong else ", x-long")
            tag = f"{name} {kind}, phi = {phi:4.1f} deg"
            if full:
                steady = max(steady, abs(rows[-1][2] - rows[-2][2]))
            if full and ylong:
                check(abs(qline - Q_IN) <= 5.0e-4, f"{tag}: Q = {qline:.4f} (Q_in {Q_IN:.4f})")
            elif full:
                inorth = iL if jL == 1 else iR
                qend = qc(inorth, 1)
                r = (Q_IN - qline) / qend
                check(abs(r - 1.0) <= 0.01,
                      f"{tag}: Q = {qline:.4f}, Q_in - Q = {Q_IN - qline:.4f} = {r:.4f} x the flux of the "
                      f"north end tread cell ({qend:.4f} m2/s x 1 m)")
            elif ylong:
                n = abs(dj) + 1
                delta = n - qline / q
                deltas.append(delta)
                check(0.55 <= delta <= 0.62,
                      f"{tag}: Q = {qline:.4f} = q (n - {delta:.4f}) with n = {n} treads, q = {q:.6f} m2/s")
            else:
                r = qline / (q * abs(dj))
                check(abs(r - 1.0) <= 0.005,
                      f"{tag}: Q = {qline:.4f} = {r:.5f} x q |dj| (|dj| = {abs(dj)}, q = {q:.6f} m2/s)")
        else:
            dx, dy = xL - xR, yL - yR
            phi = math.degrees(math.atan2(abs(dx), abs(dy)))
            if abs(dy) < 1e-9:
                check(abs(qline) <= 1.0e-3, f"{name} parallel to the flow ({abs(dx):.1f} m): Q = {qline:.4f}")
                continue
            full = abs(dy) > NY - 1e-3
            tag = f"{name} {'wall to wall' if full else 'interior'}, phi = {phi:4.1f} deg"
            if full:
                steady = max(steady, abs(rows[-1][2] - rows[-2][2]))
                check(abs(qline - Q_IN) <= 5.0e-4, f"{tag}: Q = {qline:.4f} (Q_in {Q_IN:.4f})")
            else:
                ns = 400
                pts = [(xR + dx * (k + 0.5) / ns, yR + dy * (k + 0.5) / ns) for k in range(ns)]
                q = sum(qc(int(math.floor(x)) + 1, int(math.floor(NY - y)) + 1) for x, y in pts) / ns
                r = qline / (q * abs(dy))
                check(abs(r - 1.0) <= 2.0e-4,
                      f"{tag}: Q = {qline:.4f} = {r:.6f} x F.n L (q = {q:.6f} m2/s, south-north length {abs(dy):.2f} m)")
    if deltas:
        spread = max(deltas) - min(deltas)
        check(spread <= 0.005, f"the end deficit delta of the interior y-long transects is the same for every angle "
              f"and length: {min(deltas):.4f}-{max(deltas):.4f} (d = 2/(2+sqrt2) = {DIAG:.4f})")
    check(steady <= 2.0e-4, f"steady: wall-to-wall Q changes by at most {steady:.4f} m3/s between 2100 s and 2400 s")

    print(f"=== fluxline {mode} check {'PASS' if nfail == 0 else f'FAIL ({nfail})'} ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
