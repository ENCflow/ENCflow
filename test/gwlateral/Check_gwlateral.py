#!/usr/bin/env python3
# gwlateral(地下水の側方流 f_gwlateral = 1)の検定(developer.md §16.1・§16.6)
#   使い方: Check_gwlateral.py gauss [resdir]       (既定 result。構成 1 = param.txt)
#           Check_gwlateral.py strip [resdir]       (既定 result_strip。構成 2 = param_strip.txt)
#           Check_gwlateral.py strip_open [resdir]  (既定 result_strip_open。構成 3)
#           Check_gwlateral.py line_open [resdir]   (既定 result_line_open。構成 4)
#   読むもの: resdir/Log.txt と、分布出力 Hg0001.bil 以降(float32・BIL・リトルエンディアン)
#             と FILENUMBER.csv(番号と時刻の対応)
#
#   線形化した Boussinesq 方程式: 平坦な基盤で地下貯留 hg の小さな起伏 η は
#     ∂η/∂t = D ∇²η、D = K_sh h̄ / sy、h̄ = H0 / sy(飽和帯厚)
#   に従う(非線形の補正は振幅比の 2 乗の程度。H0 = 0.2 m、A = 4 mm で 0.1 % 未満)。
#   gauss: ガウス形の小山の 2 次モーメントは初期の形によらず d⟨r²⟩/dt = 4D で伸びる。
#     8 方向の通過幅配分(軸 0.414、斜め 0.293)の離散演算子でも、内部では Σ w_k |δ_k|² = 4
#     なので厳密に同じ(縁に届く前の 300〜1800 s で比べる)。許容 0.5 %。
#   strip: 3 × 40 セルの南北に長い帯の南北方向のコサイン形の起伏 cos(π s / L) の減衰率を、
#     東西の縁の列の通水能の欠け(外へ向かう斜めのリンクがなく、南北方向が内部の
#     1 − diagratio/2 倍)を含む離散の予測 λ = D k² · (2 (1 − diagratio/2) + (nx − 2)) / nx と
#     比べる。許容 0.5 %。
#   strip_open・line_open: 塞がれた斜めの配分を軸エッジへ振り替える(f_gw_opening = 1)と、
#     3 × 40 の帯(構成 3)でも幅 1 セルの帯(構成 4。斜めはすべて塞がれる)でも壁沿いの
#     通水能が内部と同じになり、減衰率が λ = D k² に戻る。許容 0.5 %。
#   どちらも Log の S_grnd が初期の水量(最初のステップで全量浸透)のまま不変で、地表水が
#   残らないことも確かめる。構成は param*.txt・make_init.py と対で保守する。
import math
import os
import struct
import sys

H0, A = 0.2, 0.004
H0F = struct.unpack("<f", struct.pack("<f", H0))[0]   # 背景の float32 表現(丸めの偏りを除く)
KSH, SY = 0.01, 0.2                                    # gw_ksh_mmh = 36000、sy0
D = KSH * (H0 / SY) / SY                               # 0.05 m²/s
DIAGRATIO = 2.0 / (2.0 + math.sqrt(2.0))               # gw_diagratio の既定(p_diagratio と同値)
ATOL_LOG = 1e-13
CASES = {"gauss": ("result", 121, 121), "strip": ("result_strip", 3, 40),
         "strip_open": ("result_strip_open", 3, 40), "line_open": ("result_line_open", 1, 40)}


def hms(s):
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def frames(resdir):
    out = []
    with open(os.path.join(resdir, "FILENUMBER.csv")) as f:
        for line in f:
            if line.startswith("#"):
                continue
            c = [v.strip() for v in line.split(",")]
            k, t = int(c[0]), float(c[2])
            if 0 < k < 9000:
                out.append((k, t))
    return out


def read_bil(resdir, k, nx, ny):
    with open(os.path.join(resdir, "Hg%04d.bil" % k), "rb") as f:
        v = struct.unpack("<%df" % (nx * ny), f.read())
    return [v[j * nx:(j + 1) * nx] for j in range(ny)]


def read_log(resdir):
    rows = []
    with open(os.path.join(resdir, "Log.txt")) as f:
        head = f.readline().replace(",", " ").split()
        i_s, i_g = head.index("S_surf(m)"), head.index("S_grnd(m)")
        for line in f:
            c = line.split()
            rows.append((hms(c[0]), float(c[i_s]), float(c[i_g])))
    return rows


def main(case="gauss", resdir=None):
    if case not in CASES:
        print("usage: %s gauss|strip|strip_open|line_open [resdir]" % os.path.basename(sys.argv[0]), file=sys.stderr)
        return 2
    resdir = resdir or CASES[case][0]
    nx, ny = CASES[case][1:]
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    log = read_log(resdir)
    s0 = log[0][1] + log[0][2]
    err = max(abs(sg - s0) for t, ss, sg in log[1:])
    check(err < ATOL_LOG and max(ss for t, ss, sg in log[1:]) == 0.0,
          f"the initial water infiltrates in the first step and S_grnd stays {s0:.14f} m "
          f"(max abs change {err:.1e} m; no surface water left)")

    fr = frames(resdir)
    if case == "gauss":
        print("== gwlateral gauss: spreading of a Gaussian mound, d<r^2>/dt = 4D (D = %.3f m^2/s)" % D)
        xc, yc = nx * 0.5, ny * 0.5
        ts, r2s = [], []
        for k, t in fr:
            if t < 300 - 1e-6 or t > 1800 + 1e-6:
                continue
            a = read_bil(resdir, k, nx, ny)
            m0 = m2 = 0.0
            for j in range(ny):
                y = j + 0.5 - yc
                for i in range(nx):
                    x = i + 0.5 - xc
                    e = a[j][i] - H0F
                    m0 += e
                    m2 += (x * x + y * y) * e
            ts.append(t)
            r2s.append(m2 / m0)
        n = len(ts)
        tm, rm = sum(ts) / n, sum(r2s) / n
        slope = sum((t - tm) * (r - rm) for t, r in zip(ts, r2s)) / sum((t - tm) ** 2 for t in ts)
        resid = max(abs(r - (rm + slope * (t - tm))) for t, r in zip(ts, r2s))
        check(abs(slope / (4 * D) - 1) <= 0.005,
              f"d<r^2>/dt = {slope:.6f} m^2/s over {ts[0]:g}-{ts[-1]:g} s ({n} frames), "
              f"theory 4D = {4 * D:.6f} (ratio {slope / (4 * D):.5f}, limit 1 +- 0.005)")
        check(resid <= 1e-3 * (r2s[-1] - r2s[0]),
              f"<r^2> grows linearly in time (max deviation from the fitted line {resid:.2e} m^2)")
    else:
        opening = case.endswith("_open")
        print("== gwlateral %s: decay of a cosine mode along a %d x %d strip %s" % (
            case, nx, ny, "with the blocked diagonal shares transferred (f_gw_opening = 1)" if opening
            else "with the wall columns"))
        kk = math.pi / (ny * 1.0)
        fwall = 1.0 if opening else (2 * (1 - DIAGRATIO / 2) + (nx - 2)) / nx
        amps = []
        for k, t in fr:
            a = read_bil(resdir, k, nx, ny)
            s = sum((a[j][i] - H0F) * math.cos(math.pi * (j + 0.5) / ny) for j in range(ny) for i in range(nx))
            amps.append((t, 2.0 * s / (nx * ny)))
        (t1, a1), (t2, a2) = amps[0], amps[-1]
        lam = math.log(a1 / a2) / (t2 - t1)
        lam_int, lam_d = D * kk * kk, D * kk * kk * fwall
        check(abs(lam / lam_d - 1) <= 0.005,
              f"decay rate {lam:.5e} 1/s over {t1:g}-{t2:g} s, discrete prediction "
              f"{'with the transfer (no wall deficit)' if opening else 'with the wall columns'} "
              f"D k^2 x {fwall:.4f} = {lam_d:.5e} (ratio {lam / lam_d:.5f}, limit 1 +- 0.005; "
              f"interior theory D k^2 = {lam_int:.5e}, ratio {lam / lam_int:.4f})")
        rates = [math.log(amps[n][1] / amps[n + 1][1]) / (amps[n + 1][0] - amps[n][0]) for n in range(len(amps) - 1)]
        spread = (max(rates) - min(rates)) / lam
        check(spread <= 0.005, f"the decay is exponential (rate in each interval within {spread:.1e} of the mean)")

    print(f"=== gwlateral {case} check {'PASS' if nfail == 0 else f'FAIL ({nfail})'} ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
