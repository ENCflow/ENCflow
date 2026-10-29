#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# nhbottom 構成 1(区間隆起)の線形理論検定(developer.md §69.10、docs/nonhydrostatic_plan.md §16)
#   使い方: Check_nhbottom.py      (事前に ./Run_theory.sh か、uplift で param.txt・param_h.txt・
#                                   param_n.txt の 3 ケースを実行しておく。numpy を使う)
#   読むもの: result_h/(静水圧)、result_n/(NH、加速度項なし)、result/(NH、加速度項あり)の
#             プローブ 3(x = xc + 200 m)
#
#   先頭波の最大水位 η_max とその時刻を、各モデルの線形理論(Theory.py。ENC の 1 次元シンボル Λ を
#   使う半離散の解)と比べる。差は主に振幅 ζ0/H = 2% の非線形性(先頭波がわずかに速く高い)と
#   時間離散化で、実測は振幅 +0.9〜1.0%(NH)・+3.8%(静水圧。箱型のパルスが切り立つ)、時刻
#   0.3〜0.4 s 早い(README の数表)。許容はそれに余裕を足した
#     振幅: NH ±2%、静水圧 ±5%。時刻: ±0.6 s(モデル間の到達の差は 3 s)
#   加速度項の効果(NH の加速度項あり / なしの η_max の比)は、両者に共通の離散化と非線形性の差が
#   打ち消し合うので、理論の比に ±1% で一致することを確かめる(実測 0.1%。加速度項が働かなければ
#   比は 1 で、理論の 0.898 から 11% 外れる)。構成は param*.txt・Theory.py と対で保守する。
import os
import sys

import numpy as np

from Theory import Theory, XC

PROBE, XP = 3, XC + 200.0
TT = np.arange(0, 40.0001, 0.05)
CASES = [("result_h", "hydro", "hydrostatic", 0.05),
         ("result_n", "nh0", "NH without the acceleration term", 0.02),
         ("result", "nh1", "NH with the acceleration term (f_nh_bottom = 1)", 0.02)]
DT_TOL = 0.6                    # 先頭波の時刻の許容 (s)
EFFECT_TOL = 0.01               # 加速度項の効果(比の比)の許容


def probe(rdir):
    d = np.loadtxt(os.path.join(rdir, "probes", "probe%04d.csv" % PROBE), delimiter=",", comments="#")
    return d[:, 0] * 3600, d[:, 2] + d[:, 3] - 10.0      # 時刻 (s)、水位 η = z + h − H


def main():
    nfail = 0

    def check(ok, msg):
        nonlocal nfail
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            nfail += 1

    print("== nhbottom: leading wave of the prescribed uplift at x = xc + 200 m against the linear theory")
    peak = {}
    for rdir, model, label, atol in CASES:
        t, e = probe(rdir)
        et = Theory(model).probe(XP, TT)
        i, j = int(np.argmax(e)), int(np.argmax(et))
        peak[model] = (e[i], et[j])
        ratio, dt = e[i] / et[j], t[i] - TT[j]
        check(abs(ratio - 1) <= atol and abs(dt) <= DT_TOL,
              f"{label}: eta_max {e[i]:.4f} m at {t[i]:.2f} s, theory {et[j]:.4f} m at {TT[j]:.2f} s "
              f"(ratio {ratio:.3f}, limit 1 +- {atol:g}; time {dt:+.2f} s, limit +- {DT_TOL:g} s)")
    enc = peak["nh1"][0] / peak["nh0"][0]
    th = peak["nh1"][1] / peak["nh0"][1]
    check(abs(enc / th - 1) <= EFFECT_TOL,
          f"effect of the acceleration term: eta_max with / without = {enc:.4f}, theory {th:.4f} "
          f"(ratio {enc / th:.4f}, limit 1 +- {EFFECT_TOL:g})")

    print(f"=== nhbottom check {'PASS' if nfail == 0 else f'FAIL ({nfail})'} ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
