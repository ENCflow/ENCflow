#!/usr/bin/env python3
# pump(井戸揚水シンク f_gwpump)の解析検定(developer.md §16.3)
#   使い方: Check_pump.py [resdir [screen]]   (既定 result、Screen.log)
#   読むもの: resdir/Log.txt、resdir/Hg0002.txt(3600 s の地下貯留)、画面出力
#
#   平坦な閉領域(21 × 21、Δx = 2 m、A = 1764 m²)の初期水 h0 = 0.05 m が一定浸透能 Ks = 1e-4 m/s
#   (Green-Ampt の ψ = 0)で地下へ入り、井戸 1(全セル等分配 Q1 = 0.01 m³/s)と井戸 2(中央セル
#   Q2 = 2e-5 m³/s)が最初から地下から汲む。解析値は
#     S_total(t) = h0 − (Q1 + Q2) t / A、S_surf(t) = max(h0 − Ks t, 0)
#     Hg(3600 s) = h0 − Q1 t / A(中央以外)、中央はさらに Q2 t / Δx² だけ低い
#   S は Log の全有効桁(相対 1e-9)、Hg は分布出力の表示(f12.4)の丸めの範囲で比べる。
#   画面の「demand / pumped」が井戸ごとに一致し、需要 Q t に等しいことも確かめる。
#   構成は param.txt と対で保守する。
import os
import re
import sys

H0, KS = 0.05, 1.0e-4
Q1, Q2 = 0.01, 2.0e-5
NX = NY = 21
DX = 2.0
AREA = NX * NY * DX * DX
T_END = 3600.0
RTOL = 1e-9
HG_ATOL = 5e-5 + 1e-9     # f12.4 の表示の丸め(半量子 5e-5)+ 計算値の誤差の余裕
CENTER = (11, 11)         # (i, j)。1 始まり


def hms(s):
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def main(resdir="result", screen="Screen.log"):
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    print("== pump: storage, map and pumped volumes against the analytical values")
    rows = []
    with open(os.path.join(resdir, "Log.txt")) as f:
        head = f.readline().replace(",", " ").split()
        i_surf, i_tot = head.index("S_surf(m)"), head.index("S_total(m)")
        for line in f:
            c = line.split()      # 見出しと同じ並び(time, progress, S_surf, S_grnd, S_total, ...)
            rows.append((hms(c[0]), float(c[i_surf]), float(c[i_tot])))
    check(abs(rows[-1][0] - T_END) < 1e-6, f"Log reaches t = {T_END:g} s ({len(rows)} rows)")
    err_tot = max(abs(st - (H0 - (Q1 + Q2) * t / AREA)) / (H0 - (Q1 + Q2) * t / AREA) for t, _ss, st in rows)
    check(err_tot < RTOL, f"S_total = h0 - (Q1 + Q2) t / A at every row (max rel err {err_tot:.1e}; "
          f"S_total(end) = {rows[-1][2]:.12f} m, analytical {H0 - (Q1 + Q2) * T_END / AREA:.12f} m)")
    err_surf = max(abs(ss - max(H0 - KS * t, 0.0)) for t, ss, _st in rows)
    check(err_surf < 1e-12, f"S_surf = max(h0 - Ks t, 0) (max abs err {err_surf:.1e} m)")

    with open(os.path.join(resdir, "Hg0002.txt")) as f:
        hg = [[float(v) for v in line.split()] for line in f if line.strip()]
    want = H0 - Q1 * T_END / AREA
    ci, cj = CENTER
    others = [v for j, row in enumerate(hg, 1) for i, v in enumerate(row, 1) if (i, j) != (ci, cj)]
    center = hg[cj - 1][ci - 1]
    check(len(hg) == NY and all(len(r) == NX for r in hg) and max(abs(v - want) for v in others) <= HG_ATOL,
          f"Hg(3600 s) outside the centre = h0 - Q1 t / A = {want:.4f} m (shown to 4 decimals; "
          f"range {min(others):.4f}-{max(others):.4f})")
    drop = Q2 * T_END / (DX * DX)
    check(abs(center - (want - drop)) <= HG_ATOL,
          f"Hg(3600 s) at the centre is lower by Q2 t / dx^2 = {drop:.4f} m ({center:.4f} m)")

    pumped = {}
    if os.path.exists(screen):
        with open(screen) as f:
            for line in f:
                m = re.search(r"well (\d+): demand\s+(\S+) m3, pumped\s+(\S+) m3", line)
                if m:
                    pumped[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
    for k, q in ((1, Q1), (2, Q2)):
        if k not in pumped:
            check(False, f"screen shows the demand / pumped line of well {k}")
            continue
        d, p = pumped[k]
        check(abs(d - q * T_END) <= 1e-4 * q * T_END and abs(p - d) <= 1e-4 * d,
              f"well {k}: pumped = demand = Q t = {q * T_END:g} m3 ({p:.4E} / {d:.4E})")

    print(f"=== pump check {'PASS' if nfail == 0 else f'FAIL ({nfail})'} ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
