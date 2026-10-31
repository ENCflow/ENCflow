#!/usr/bin/env python3
# frost(凍土による浸透抑制 f_gwfrost)の解析検定(developer.md §16.4)
#   使い方: Check_frost.py [resdir]   (既定 result)
#   読むもの: resdir/Log.txt、resdir/Ff000k.txt(低減係数)、resdir/Hg0002.txt(3600 s の地下貯留)
#
#   平坦な閉領域に h0 = 0.05 m を置き、一定浸透能 K = 1e-5 m/s(Green-Ampt の ψ = 0)に低減係数
#   Ff = 1 − FI/fro_fifull を掛ける。気温 −8.64 ℃一定でステップごとに ΔFI = 8.64·dt/86400
#   = 5e-5 ℃·day 積まれ、fro_fifull = 0.36 = N·ΔFI(N = 7200 = 3600 s / dt)なので、ステップ n の
#   低減係数は Ff_n = 1 − n/N。浸透は地表水が尽きない(合計 0.018 m < h0)ので
#     S_grnd(t_n) = K·dt·Σ_{k=1..n} (1 − k/N) = K·dt·(n − n(n+1)/(2N))、S_surf = h0 − S_grnd、
#     S_total = h0(一定)
#   を Log の全有効桁で比べる(相対 1e-9)。Ff の分布(0・1800・3600 s で 1・0.5・0)と 3600 s の
#   地下貯留の分布(一様に S_grnd(3600))は分布出力の表示(f12.4)の丸めの範囲で比べる。
#   構成は param.txt と対で保守する。
import os
import sys

H0, K, DT = 0.05, 1.0e-5, 0.5
N = 7200                        # fro_fifull / ΔFI = 0.36 / 5e-5
T_END = 3600.0
RTOL = 1e-9
ATOL_LOG = 1e-13
ATOL_MAP = 5e-5 + 1e-9          # f12.4 の表示の丸め(半量子 5e-5)+ 計算値の誤差の余裕


def hms(s):
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def sgrnd(t):
    n = int(round(t / DT))
    return K * DT * (n - n * (n + 1) / (2.0 * N))


def read_map(path):
    with open(path) as f:
        return [float(v) for line in f for v in line.split()]


def main(resdir="result"):
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    print("== frost: infiltration reduced linearly to zero by the freezing index")
    rows = []
    with open(os.path.join(resdir, "Log.txt")) as f:
        head = f.readline().replace(",", " ").split()
        i_surf, i_grnd, i_tot = head.index("S_surf(m)"), head.index("S_grnd(m)"), head.index("S_total(m)")
        for line in f:
            c = line.split()      # 見出しと同じ並び(time, progress, S_surf, S_grnd, S_total, ...)
            rows.append((hms(c[0]), float(c[i_surf]), float(c[i_grnd]), float(c[i_tot])))
    check(abs(rows[-1][0] - T_END) < 1e-6, f"Log reaches t = {T_END:g} s ({len(rows)} rows)")
    err = max(abs(sg - sgrnd(t)) / max(sgrnd(t), 1e-30) for t, _ss, sg, _st in rows if t > 0)
    check(err < RTOL and rows[0][2] == 0.0,
          f"S_grnd = K dt (n - n(n+1)/2N) at every row (max rel err {err:.1e}; "
          f"S_grnd(end) = {rows[-1][2]:.14f} m, analytical {sgrnd(T_END):.14f} m)")
    err_s = max(abs(ss - (H0 - sgrnd(t))) for t, ss, _sg, _st in rows)
    err_t = max(abs(st - H0) for _t, _ss, _sg, st in rows)
    check(err_s < ATOL_LOG and err_t < ATOL_LOG,
          f"S_surf = h0 - S_grnd and S_total = h0 (max abs err {err_s:.1e} / {err_t:.1e} m)")

    for k, t in ((0, 0.0), (1, 1800.0), (2, 3600.0)):
        ff = read_map(os.path.join(resdir, f"Ff{k:04d}.txt"))
        want = 1.0 - (t / DT) / N
        check(len(ff) == 441 and max(abs(v - want) for v in ff) <= ATOL_MAP,
              f"Ff({t:g} s) = 1 - FI/fro_fifull = {want:.4f} in every cell ({min(ff):.4f}-{max(ff):.4f})")
    hg = read_map(os.path.join(resdir, "Hg0002.txt"))
    check(len(hg) == 441 and max(abs(v - sgrnd(T_END)) for v in hg) <= ATOL_MAP,
          f"Hg(3600 s) = S_grnd(3600 s) = {sgrnd(T_END):.4f} m in every cell ({min(hg):.4f}-{max(hg):.4f})")

    print(f"=== frost check {'PASS' if nfail == 0 else f'FAIL ({nfail})'} ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
