#!/usr/bin/env python3
"""test/tjunction の検定: 1 セル幅の T 字の合流の、合流の 1 セル上流の本川の水深を 1 次元の理論と比べる。

  理論(合流の 2 セル下流 J+2 の計算の水深から、合流の 1 セル上流 J−1 の水深を解く。区間 3 セル = 150 m の
  河床勾配と摩擦は、その計算の水深で台形積分する。矩形断面・単位幅):
    運動量: M(J−1) + ∫(S0 − Sf) h dx = M(J+2)、M = h²/2 + q²/(g h)。直角に入る支川の水は、本川の向きの
            運動量を持たない(開水路の合流の標準的な扱い。Taylor 1944)
    損失なし: E(J−1) = E(J+2) + hf − S0 L、E = h + q²/(2 g h²)。合流でエネルギーを失わない(下限)
  計算の水深の、2 つの理論の間の位置を p = (h − h_E)/(h_M − h_E) で表す(0 = 損失なし、1 = 運動量の理論)。

  判定する項目(現行のコードが満たすこと):
    (1) 6 構成とも定常(終わりの 10 分の水深の振れ幅)
    (2) 質量の収支(合流の 30 セル下流の測線の流量 = 与えた流量の和)
    (3) 合流から離れた下流は等流(水深がマニングの等流水深)
    (4) 合流でエネルギーが増えない(J−1 の水深が、損失なしの理論を下回らない)
  記録する項目(判定しない。現行の限界):
    (5) p の値(乾いた岸・濡れた岸)と、濡れた岸と乾いた岸の水深の差。合流の損失は、岸が濡れているとき
        だけ数えられている(README の「限界」)
標準ライブラリだけ。python3 Check_tjunction.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_tjunction import DX, S0, RN, G, QTOT, CASES, FILM, FILM_Q

T_AVG = 110.0            # この時刻(分)から終わりまでを平均する
TOL_STEADY = 0.03        # (1) 終わりの 10 分の水深の振れ幅 (m)
TOL_MASS = 2.0e-3        # (2) 測線の流量の相対差
TOL_UNI = 0.01           # (3) 下流の水深の、等流水深からの相対差
TOL_GAIN = 0.03          # (4) 損失なしの理論を下回ってよい幅 (m)


def probe(d, n):
    """プローブ n の、T_AVG 以降の水深の平均と振れ幅"""
    h = []
    with open("%s/probes/probe%04d.csv" % (d, n)) as f:
        for ln in f:
            if ln.startswith("#"):
                continue
            c = ln.split(",")
            if float(c[1]) >= T_AVG:
                h.append(float(c[3]))
    return sum(h) / len(h), max(h) - min(h)


def flux_last(d):
    with open("%s/fluxes/flux0001.csv" % d) as f:
        rows = [ln for ln in f if not ln.startswith("#")]
    return float(rows[-1].split(",")[2])


def solve(fn, lo, hi):
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if fn(lo) * fn(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def theory(h, q1, q3):
    """h = [J−1, J, J+1, J+2] の計算の水深。J−1 の水深の理論(運動量、損失なし)を返す"""
    q = [q1, 0.5 * (q1 + q3), q3, q3]                 # 合流のセル J は途中として平均
    sf = [RN ** 2 * qq ** 2 / hh ** (10.0 / 3.0) for qq, hh in zip(q, h)]
    force = sum(0.5 * ((S0 - sf[i]) * h[i] + (S0 - sf[i + 1]) * h[i + 1]) * DX for i in range(3))
    hf = sum(0.5 * (sf[i] + sf[i + 1]) * DX for i in range(3))
    m3 = h[3] ** 2 / 2 + q3 ** 2 / (G * h[3])
    e3 = h[3] + q3 ** 2 / (2 * G * h[3] ** 2)
    hc = (q1 ** 2 / G) ** (1.0 / 3.0)                 # 限界水深(常流の根を取るための下限)
    hm = solve(lambda x: x * x / 2 + q1 ** 2 / (G * x) - (m3 - force), hc, 20.0)
    he = solve(lambda x: x + q1 ** 2 / (2 * G * x * x) - (e3 + hf - S0 * 3 * DX), hc, 20.0)
    return hm, he


def main():
    ok = True
    q3 = QTOT / DX
    hn = (q3 * RN / S0 ** 0.5) ** 0.6                 # 合流の下流の等流水深
    res = {}
    worst = {"steady": 0.0, "mass": 0.0, "uni": 0.0, "gain": 9.9}
    print("=== tjunction: 1 セル幅の T 字の合流(合流の下流 %.0f m3/s = 単位幅 %.0f m2/s、等流水深 %.3f m) ===" % (QTOT, q3, hn))
    print("  構成(本川・支川 m3/s、岸)   J−1 の水深   理論: 損失なし / 運動量    位置 p    振れ幅    測線の流量")
    for tag in ("m800", "m500", "m200"):
        q1, q2 = CASES[tag]
        for bank in ("dry", "wet"):
            d = "result_%s_%s" % (tag, bank)
            pr = [probe(d, n) for n in range(1, 18)]
            h = [pr[n][0] for n in (5, 6, 7, 8)]       # プローブ 6〜9 = J−1, J, J+1, J+2
            hm, he = theory(h, q1 / DX, q3)
            p = (h[0] - he) / (hm - he)
            amp = max(a for _, a in pr)
            qin = q1 + q2 + (len(FILM) * FILM_Q if bank == "wet" else 0.0)
            qf = flux_last(d)
            res[(tag, bank)] = (h[0], hm, he, p)
            worst["steady"] = max(worst["steady"], amp)
            worst["mass"] = max(worst["mass"], abs(qf / qin - 1.0))
            worst["uni"] = max(worst["uni"], abs(pr[12][0] / hn - 1.0))      # プローブ 13 = J+6
            worst["gain"] = min(worst["gain"], h[0] - he)
            print("  %4.0f・%4.0f %s      %7.3f m      %7.3f / %7.3f m      %5.2f   %6.3f m   %8.2f m3/s"
                  % (q1, q2, "乾いた岸" if bank == "dry" else "濡れた岸", h[0], he, hm, p, amp, qf))

    def judge(label, good):
        nonlocal ok
        ok = ok and good
        print("  %s : %s" % (label, "PASS" if good else "FAIL"))

    judge("(1) 定常: 終わりの 10 分の水深の振れ幅の最大 %.3f m (< %.2f)" % (worst["steady"], TOL_STEADY), worst["steady"] < TOL_STEADY)
    judge("(2) 質量: 測線の流量と与えた流量の和の相対差の最大 %.1e (< %.0e)" % (worst["mass"], TOL_MASS), worst["mass"] < TOL_MASS)
    judge("(3) 合流の 6 セル下流の水深の、等流水深からの相対差の最大 %.1e (< %.0e)" % (worst["uni"], TOL_UNI), worst["uni"] < TOL_UNI)
    judge("(4) 合流でエネルギーが増えない: J−1 の水深 − 損失なしの理論 の最小 %+.3f m (> −%.2f)" % (worst["gain"], TOL_GAIN),
          worst["gain"] > -TOL_GAIN)
    pd = [res[(t, "dry")][3] for t in ("m800", "m500", "m200")]
    pw = [res[(t, "wet")][3] for t in ("m800", "m500", "m200")]
    dm_d = [res[(t, "dry")][0] - res[(t, "dry")][1] for t in ("m800", "m500", "m200")]
    dm_w = [res[(t, "wet")][0] - res[(t, "wet")][1] for t in ("m800", "m500", "m200")]
    dwd = [res[(t, "wet")][0] - res[(t, "dry")][0] for t in ("m800", "m500", "m200")]
    print("  (5) 記録(判定しない。現行の限界): 位置 p(0 = 損失なし、1 = 運動量の理論。本川が主・同じ・支川が主)")
    print("        乾いた岸 p = %.2f・%.2f・%.2f(運動量の理論との差 %+.2f・%+.2f・%+.2f m)" % (pd[0], pd[1], pd[2], dm_d[0], dm_d[1], dm_d[2]))
    print("        濡れた岸 p = %.2f・%.2f・%.2f(運動量の理論との差 %+.2f・%+.2f・%+.2f m)" % (pw[0], pw[1], pw[2], dm_w[0], dm_w[1], dm_w[2]))
    print("        濡れた岸 − 乾いた岸 の水深の差 %+.2f・%+.2f・%+.2f m(岸の水膜の有無で合流の堰上げが変わる)" % (dwd[0], dwd[1], dwd[2]))
    print("=== tjunction checks %s ===" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
