#!/usr/bin/env python3
"""sliver の判定(Run.sh・Run_MPI.sh が呼ぶ。developer.md §136)

  python3 Check_sliver.py        全ケースの結果(result_<case>/)を判定して数表を書く

判定(どれも 3 時間の終わり = E0003・H0003。2 時間の結果 E0002 と比べて定常も確かめる):
  1. dg(45° の 1 列に 1 セル): 幅 0.01 m の角のセルを添えた構成と添えない構成の、河道セルの水位の差が 2 mm 以下
  2. ax(格子に沿う 2 行): 同じく、区間の 20〜80 % の河道セルの水位の差が等流水深の 1 % 以下。残る差(1.5 cm 前後)は、
     移流項が細片の行を濡れた隣として数える分で、細片の幅によらない(0.01 m と 0.001 m で同じ。§136.5)
  3. 河道の水位の 2 → 3 時間の変化が 2 mm 以下(定常)
  4. 添えない構成の区間の中ほど(40〜60 %)の水深が、マニングの等流水深と 1 % 以内(dg は斜めの自然幅 70.7 m、
     ax は幅 200 m で数える)
§136 の規則の前の版は、判定 1 で 1.2 m、判定 2 で 0.33 m の差になって不合格になる。
"""
import math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_sliver as ms

TOL_DG, TOL_AX_REL, TOL_STEADY, TOL_HN = 2.0e-3, 0.01, 2.0e-3, 0.01


def info(name):
    d = {}
    for line in open(f"d_{name}/info.txt"):
        k, v = line.split()
        d[k] = v
    return d


def load(name):
    kind = np.loadtxt(f"d_{name}/kind.txt", dtype=int)
    e3 = np.loadtxt(f"result_{name}/E0003.txt")
    e2 = np.loadtxt(f"result_{name}/E0002.txt")
    h3 = np.loadtxt(f"result_{name}/H0003.txt")
    return kind, e2, e3, h3


def reach(kind, lo, hi):
    """河道セル(kind 1)のうち、列が区間の lo〜hi(割合)に入るもの"""
    nx = kind.shape[1]
    sel = kind == 1
    sel[:, :int(lo * nx)] = False
    sel[:, int(hi * nx):] = False
    return sel


def main():
    fails = []

    def check(ok, msg):
        print(("  ok   " if ok else "FAIL: ") + msg)
        if not ok:
            fails.append(msg)

    names = [c[0] for c in ms.CASES]
    missing = [n for n in names if not os.path.exists(f"result_{n}/E0003.txt")]
    if missing:
        print("FAIL: 結果がない: " + " ".join(missing))
        sys.exit(1)

    print("== 1・2. 幅 0.01 m のセルを添えた構成と添えない構成の河道の水位の差(添えた − 添えない)")
    for geo in ("dg", "ax"):
        kind, _, en, _ = load(f"{geo}_none")
        kt, _, et, _ = load(f"{geo}_tiny")
        ch = kind == 1
        d = (et - en)[ch]
        q = float(info(f"{geo}_none")["q"])
        w = float(info(f"{geo}_none")["chan_w"])
        hn = ms.hn(q / w)
        if geo == "dg":
            check(np.abs(d).max() <= TOL_DG,
                  f"dg: 河道セルの最大の差 {1000 * np.abs(d).max():.1f} mm(平均 {1000 * d.mean():+.1f} mm。許容 {1000 * TOL_DG:.0f} mm)")
        else:
            m = reach(kind, 0.2, 0.8)
            dm = (et - en)[m]
            check(np.abs(dm).max() <= TOL_AX_REL * hn,
                  f"ax: 区間の 20〜80 % の最大の差 {1000 * np.abs(dm).max():.1f} mm(平均 {1000 * dm.mean():+.1f} mm。"
                  f"許容 = 等流水深 {hn:.2f} m の 1 % = {1000 * TOL_AX_REL * hn:.0f} mm。区間全体の最大 {1000 * np.abs(d).max():.1f} mm)")

    print("== 3. 河道の水位の 2 → 3 時間の変化(定常)")
    for name in names:
        kind, e2, e3, _ = load(name)
        ch = kind == 1
        dd = np.abs(e3 - e2)[ch].max()
        check(dd <= TOL_STEADY, f"{name}: {1000 * dd:.2f} mm(許容 {1000 * TOL_STEADY:.0f} mm)")

    print("== 4. 添えない構成の区間の中ほど(40〜60 %)の水深とマニングの等流水深")
    for geo in ("dg", "ax"):
        name = f"{geo}_none"
        kind, _, _, h3 = load(name)
        q = float(info(name)["q"])
        w = float(info(name)["chan_w"])
        hn = ms.hn(q / w)
        hm = h3[reach(kind, 0.4, 0.6)].mean()
        check(abs(hm / hn - 1.0) <= TOL_HN, f"{name}: 水深 {hm:.3f} m、等流水深 {hn:.3f} m(比 {hm / hn:.4f}。許容 ±1 %)")

    if fails:
        print(f"Check_sliver: {len(fails)} 件の不合格")
        sys.exit(1)
    print("Check_sliver: すべて合格")


if __name__ == "__main__":
    main()
