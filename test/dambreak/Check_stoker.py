#!/usr/bin/env python3
"""ダム破壊(湿潤床)の数値解を Stoker (1957) の解析解と比較する。

result/ の最終出力(H????.txt, u????.txt。FILENUMBER.csv で時刻を特定)の
中央行(j = ny/2)を 1 次元プロファイルとして読み、次を表示する:
  - 段波位置と段波速度の相対誤差(数値解は h が (hm+hr)/2 を横切る位置)
  - 中間状態 hm, um の相対誤差(解析的な平坦区間の中央 50% の平均)
  - 水深・流速の L1 相対誤差(全域)
  - y 方向一様性(行間の最大偏差。ENC の対称性の診断)
また result/stoker.csv に x, h_num, u_num, h_ana, u_ana を書く
(Plot_dambreak.plt が読む)。合否判定はしない(診断用)。

初期条件の hl, hr, 段差位置は src/user_initial.f90 の dambreak_step と
同期して変更すること。
"""
import csv, math, os, sys

G = 9.8            # m_sysparam の既定 gg と合わせる
HL, HR = 10.0, 1.0 # dambreak_step と同期
RESDIR = os.environ.get("RESDIR", "result")


def read_namelist_value(fname, key, default):
    with open(fname, encoding="utf-8") as f:
        for line in f:
            s = line.split("!")[0].strip()
            if s.startswith(key) and "=" in s:
                return float(s.split("=")[1].strip().rstrip(","))
    return default


def read_matrix(fname):
    rows = []
    with open(fname) as f:
        for line in f:
            if line.strip():
                rows.append([float(v) for v in line.split()])
    return rows


def stoker_state(hl, hr):
    """中間状態 hm を二分法で解く(u_r = 0)。返り値 (hm, um, s)。"""
    cl = math.sqrt(G * hl)

    def resid(hm):
        cm = math.sqrt(G * hm)
        um = 2.0 * (cl - cm)
        s_mass = hm * um / (hm - hr)
        s_mom = math.sqrt(G * hm * (hm + hr) / (2.0 * hr))
        return s_mass - s_mom

    a, b = hr * (1 + 1e-9), hl * (1 - 1e-9)
    fa = resid(a)
    for _ in range(200):
        m = 0.5 * (a + b)
        fm = resid(m)
        if fa * fm <= 0:
            b = m
        else:
            a, fa = m, fm
    hm = 0.5 * (a + b)
    cm = math.sqrt(G * hm)
    um = 2.0 * (cl - cm)
    s = hm * um / (hm - hr)
    return hm, um, s


def stoker_profile(x, t, x0, hl, hr, hm, um, s):
    cl = math.sqrt(G * hl)
    cm = math.sqrt(G * hm)
    xi = (x - x0) / t
    if xi < -cl:
        return hl, 0.0
    if xi < um - cm:
        h = (2.0 * cl - xi) ** 2 / (9.0 * G)
        u = 2.0 / 3.0 * (xi + cl)
        return h, u
    if xi < s:
        return hm, um
    return hr, 0.0


def main():
    nx = int(read_namelist_value("param.txt", "nx", 0))
    ny = int(read_namelist_value("param.txt", "ny", 0))
    lx = read_namelist_value("param.txt", "lx", 0.0)
    dx = lx / nx
    x0 = lx / 2

    # 最終出力番号と時刻
    last = None
    with open(os.path.join(RESDIR, "FILENUMBER.csv")) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#"):
                continue
            if int(row[0]) >= 9000:      # 9998/9999 は最終・最大値の要約スロット
                continue
            last = (int(row[0]), float(row[2]))
    if last is None:
        print("Check_stoker: FILENUMBER.csv is empty")
        return 1
    k, t = last
    hfile = os.path.join(RESDIR, "H%04d.txt" % k)
    ufile = os.path.join(RESDIR, "u%04d.txt" % k)
    H = read_matrix(hfile)
    U = read_matrix(ufile)
    if len(H) != ny or len(H[0]) != nx:
        print("Check_stoker: matrix size mismatch", len(H), len(H[0]), nx, ny)
        return 1
    jmid = ny // 2
    h_num = H[jmid]
    u_num = U[jmid]

    hm, um, s = stoker_state(HL, HR)
    xs = [(i + 0.5) * dx for i in range(nx)]
    ana = [stoker_profile(x, t, x0, HL, HR, hm, um, s) for x in xs]
    h_ana = [a[0] for a in ana]
    u_ana = [a[1] for a in ana]

    # 段波位置: h が (hm+hr)/2 を最後に横切る位置(下流側から探す)
    hc = 0.5 * (hm + HR)
    xb_num = None
    for i in range(nx - 1, 0, -1):
        if h_num[i] < hc <= h_num[i - 1]:
            xb_num = xs[i - 1] + (h_num[i - 1] - hc) / (h_num[i - 1] - h_num[i]) * dx
            break
    xb_ana = x0 + s * t

    # 中間状態の平均(解析的平坦区間の中央 50%)
    cm = math.sqrt(G * hm)
    xa = x0 + (um - cm) * t
    xb = xb_ana
    lo, hi = xa + 0.25 * (xb - xa), xa + 0.75 * (xb - xa)
    sel = [i for i, x in enumerate(xs) if lo <= x <= hi]
    hm_num = sum(h_num[i] for i in sel) / len(sel)
    um_num = sum(u_num[i] for i in sel) / len(sel)

    l1h = sum(abs(a - b) for a, b in zip(h_num, h_ana)) / sum(abs(b) for b in h_ana)
    l1u = sum(abs(a - b) for a, b in zip(u_num, u_ana)) / sum(abs(b) for b in u_ana)
    # 段波の前後 20 セルを除いた滑らかな区間での L1(鈍りと振動の指標)
    smooth = [i for i, x in enumerate(xs) if abs(x - xb_ana) > 20 * dx]
    l1h_s = (sum(abs(h_num[i] - h_ana[i]) for i in smooth)
             / sum(abs(h_ana[i]) for i in smooth))
    # 行間の最大偏差(y 方向一様性)
    dev = 0.0
    for i in range(nx):
        col = [H[j][i] for j in range(ny)]
        dev = max(dev, max(col) - min(col))
    # 段波背後の過剰(オーバーシュート)
    over_h = max(h_num[i] - hm for i in range(nx) if xa + 5 * dx < xs[i] < xb_ana)

    print("=== Stoker dam-break check (t = %.2f s, hl = %.1f, hr = %.1f) ===" % (t, HL, HR))
    print("  analytic: hm = %.4f m, um = %.4f m/s, bore speed s = %.4f m/s, x_bore = %.2f m"
          % (hm, um, s, xb_ana))
    if xb_num is None:
        print("  bore not found in numerical solution")
    else:
        print("  bore position  : num %.2f m  (err %+.2f m = %+.2f%% of travel, %.1f cells)"
              % (xb_num, xb_num - xb_ana, 100 * (xb_num - xb_ana) / (s * t),
                 (xb_num - xb_ana) / dx))
    print("  plateau hm     : num %.4f m   (err %+.2f%%)" % (hm_num, 100 * (hm_num / hm - 1)))
    print("  plateau um     : num %.4f m/s (err %+.2f%%)" % (um_num, 100 * (um_num / um - 1)))
    print("  overshoot h-hm : %+.4f m behind the bore" % over_h)
    print("  L1 rel. error  : h %.4f  u %.4f  (h excl. bore +-20 cells: %.4f)" % (l1h, l1u, l1h_s))
    print("  y-uniformity   : max row spread %.3e m" % dev)

    with open(os.path.join(RESDIR, "stoker.csv"), "w") as f:
        f.write("x,h_num,u_num,h_ana,u_ana\n")
        for i in range(nx):
            f.write("%.3f,%.6f,%.6f,%.6f,%.6f\n" % (xs[i], h_num[i], u_num[i], h_ana[i], u_ana[i]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
