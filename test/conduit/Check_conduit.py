#!/usr/bin/env python3
# conduit(管路連続体層 f_gwconduit)の検定(developer.md §46)
#   使い方: Check_conduit.py [A|B] [resdir]   (既定 A。resdir の既定は A: result、B: result_lat)
#   読むもの: resdir/Log.txt と、最終時刻の分布出力 H・Hgc(A: 番号 3 = 150 s、B: 番号 2 = 120 s)
#
#   模式実験 A(param.txt。解析検定): 平坦な閉領域の一様湛水 h0 = 0.1 m が一様な枡から管路層へ
#   落ち、満管後は疑似スロットの被圧水頭が地表水位と釣り合う。側方流がなく全セルが同じ常微分
#   方程式に従うので、平衡は
#     水頭底 zbot = z0 − gwc_depth = −2 m、管頂水位 hcrown = zbot + gwc_cap/gwc_sy = −1 m、
#     h = hcrown + (hgc − gwc_cap)/gwc_slot_sy かつ h + hgc = h0
#     → hgc_eq = 51.1/1001 m、h_eq = h0 − hgc_eq
#   Log の S_surf・S_grnd が平衡へ単調に近づいて行き過ぎず(満管時の流入を平衡で制限する
#   eq_inflow。§46.4)、最終時刻に平衡値と表示全桁(14 桁)で一致し、S_total が h0 のまま不変で
#   あることを確かめる。最終時刻の H・Hgc の分布が一様に h_eq・hgc_eq であることは分布出力の
#   表示(f12.4)の丸めの範囲で比べる。
#   模式実験 B(param_lat.txt。自己検証。解析解はない): 枡を中心 3 × 3 に限り、管路層の側方
#   拡散(sqrt 乱流則)・Green-Ampt 浸透・管路 ⇔ 土層の漏水と浸入水をすべて働かせても、S_total
#   が h0 のまま不変(全結合経路の質量保存)で、最終時刻の Hgc・H の分布が点対称・転置対称で
#   厳密に一致する(8 方向配分の等方性)こと、中心が満管を超えて被圧すること(被圧枝を通る)を
#   確かめる。構成は param.txt・param_lat.txt と対で保守する。
import os
import sys

H0 = 0.1
CAP = 0.05                      # gwc_cap (m)
HGC_EQ = 51.1 / 1001.0          # A の解析平衡(管路層の貯留)
H_EQ = H0 - HGC_EQ              # A の解析平衡(地表水深)
ATOL_LOG = 1e-13                # Log の表示 14 桁の丸め(半量子 5e-15)+ 余裕
ATOL_MAP = 5e-5 + 1e-9          # f12.4 の表示の丸め(半量子 5e-5)+ 計算値の誤差の余裕
# 既定の resdir、終了時刻、最終の出力番号、見出し
CASES = {"A": ("result", 150.0, 3, "uniform ponding drains into the conduit layer to the analytical equilibrium"),
         "B": ("result_lat", 120.0, 2, "mass conservation and 8-direction isotropy with all exchange paths active")}


def hms(s):
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def read_log(resdir):
    rows = []
    with open(os.path.join(resdir, "Log.txt")) as f:
        head = f.readline().replace(",", " ").split()
        i_surf, i_grnd, i_tot = head.index("S_surf(m)"), head.index("S_grnd(m)"), head.index("S_total(m)")
        for line in f:
            c = line.split()      # 見出しと同じ並び(time, progress, S_surf, S_grnd, S_total, ...)
            rows.append((hms(c[0]), float(c[i_surf]), float(c[i_grnd]), float(c[i_tot])))
    return rows


def read_map(path):
    with open(path) as f:
        return [[float(v) for v in line.split()] for line in f if line.strip()]


def main(case="A", resdir=None):
    case = case.upper()
    if case not in CASES:
        print(f"usage: {os.path.basename(sys.argv[0])} [A|B] [resdir]", file=sys.stderr)
        return 2
    resdir = resdir or CASES[case][0]
    t_end, k_end, title = CASES[case][1:]
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    print(f"== conduit {case}: {title}")
    rows = read_log(resdir)
    hmap = read_map(os.path.join(resdir, f"H{k_end:04d}.txt"))
    gmap = read_map(os.path.join(resdir, f"Hgc{k_end:04d}.txt"))
    shape_ok = len(hmap) == 21 and len(gmap) == 21 and all(len(r) == 21 for r in hmap + gmap)
    check(abs(rows[-1][0] - t_end) < 1e-6, f"Log reaches t = {t_end:g} s ({len(rows)} rows)")
    err_t = max(abs(st - H0) for _t, _ss, _sg, st in rows)
    check(err_t < ATOL_LOG, f"S_total = h0 = {H0:g} m at every row (max abs err {err_t:.1e} m)")

    if case == "A":
        ss = [r[1] for r in rows]
        sg = [r[2] for r in rows]
        # 単調性は Log の表示の丸め(ATOL_LOG)まで許す(平衡後の行が丸めで揺れても誤検出しない)
        mono = all(b <= a + ATOL_LOG for a, b in zip(ss, ss[1:])) and all(b >= a - ATOL_LOG for a, b in zip(sg, sg[1:]))
        check(mono and min(ss) >= H_EQ - ATOL_LOG and max(sg) <= HGC_EQ + ATOL_LOG,
              f"S_surf decreases and S_grnd increases monotonically without overshooting the equilibrium "
              f"(min S_surf {min(ss):.14f}, max S_grnd {max(sg):.14f} m)")
        reached = next((t for t, s, _sg, _st in rows if abs(s - H_EQ) < ATOL_LOG), None)
        check(abs(ss[-1] - H_EQ) < ATOL_LOG and abs(sg[-1] - HGC_EQ) < ATOL_LOG,
              f"end: S_surf = h_eq = {H_EQ:.14f} m and S_grnd = hgc_eq = 51.1/1001 = {HGC_EQ:.14f} m "
              f"to all 14 shown digits ({ss[-1]:.14f} / {sg[-1]:.14f}; first reached at t = {reached} s)")
        flat = [v for r in hmap for v in r], [v for r in gmap for v in r]
        check(shape_ok and max(abs(v - H_EQ) for v in flat[0]) <= ATOL_MAP
              and max(abs(v - HGC_EQ) for v in flat[1]) <= ATOL_MAP,
              f"H and Hgc at {t_end:g} s are uniformly h_eq and hgc_eq (shown to 4 decimals; "
              f"H {min(flat[0]):.4f}-{max(flat[0]):.4f}, Hgc {min(flat[1]):.4f}-{max(flat[1]):.4f} m)")
    else:
        for name, a in (("Hgc", gmap), ("H", hmap)):
            rot = max(abs(a[j][i] - a[20 - j][20 - i]) for j in range(21) for i in range(21)) if shape_ok else 1.0
            tra = max(abs(a[j][i] - a[i][j]) for j in range(21) for i in range(21)) if shape_ok else 1.0
            check(rot == 0.0 and tra == 0.0,
                  f"{name} at {t_end:g} s is point- and transpose-symmetric (max deviation {rot:.1e} / {tra:.1e})")
        check(shape_ok and gmap[10][10] > CAP,
              f"the centre of the conduit layer is pressurized: Hgc = {gmap[10][10]:.4f} m > capacity {CAP:g} m")

    print(f"=== conduit {case} check {'PASS' if nfail == 0 else f'FAIL ({nfail})'} ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
