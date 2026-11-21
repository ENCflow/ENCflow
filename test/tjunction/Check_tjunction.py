#!/usr/bin/env python3
"""test/tjunction の検定: 1 セル幅の T 字の合流の、合流の 1 セル上流の本川の水深を 1 次元の理論と比べる。

  2 つの形(格子の軸に沿う合流 ax、格子に対して 45° 回した合流 rot)を、側方面の合流の規則
  f_advection_lateral = 0 と 1(ほかの 3 つは古い値の組み合わせ f_advection_donor = 3・f_advection_bend = 1・
  f_dry_head_cap = 3 を明示)と、4 つの値の組み合わせ(f_advection_donor = 4・f_advection_bend = 2・
  f_advection_lateral = 2・f_dry_head_cap = 4。深くて遅い隣のセルの扱い)で見る(6 つの組 × 3 つの流量比 ×
  乾いた岸・濡れた岸)。

  理論(合流の 2 セル下流 J+2 の計算の水深から、合流の 1 セル上流 J−1 の水深を解く。区間 3 セルの河床勾配と
  摩擦は、その計算の水深で台形積分する。矩形断面・単位幅。セルの間隔と通過幅は、ax が Δx と Δx、rot が
  √2 Δx と Δx/√2):
    運動量: M(J−1) + ∫(S0 − Sf) h dx = M(J+2)、M = h²/2 + q²/(g h)。直角に入る支川の水は、本川の向きの
            運動量を持たない(開水路の合流の標準的な扱い。Taylor 1944)
    損失なし: E(J−1) = E(J+2) + hf − S0 L、E = h + q²/(2 g h²)。合流でエネルギーを失わない(下限)
  計算の水深の、2 つの理論の間の位置を p = (h − h_E)/(h_M − h_E) で表す(0 = 損失なし、1 = 運動量の理論)。

  どの組でも判定する項目(f_advection_lateral = 0 の組は、濡れた岸の 45° の合流の堰上げが 1 m 高く、
  2 時間では上流に水をため終わらないので、(1)(2) の許容を緩めている):
    (1) 定常(終わりの 10 分の水深の振れ幅)
    (2) 質量の収支(合流の 30 セル下流の測線の流量 = 与えた流量の和)
    (3) 合流から離れた下流は等流(水深がマニングの等流水深)
    (4) 合流でエネルギーが増えない(J−1 の水深が、損失なしの理論を下回らない)
  f_advection_lateral = 1 と、4 つの値の組み合わせで判定し、0 では記録する項目(0 の限界):
    (5) 濡れた岸と乾いた岸の J−1 の水深の差が小さい(合流の堰上げが、岸の水膜の有無によらない)
    (6) p が決まった幅に入る(1 は ax が 0.5〜0.7、rot が 0.7〜0.95。4 つの値の組み合わせは P_BAND4)
  f_advection_lateral = 1 と、4 つの値の組み合わせの、向きを変えた構成(東西・南北を反転)で判定する項目:
    (7) 基本の向きと、同じ時刻の水深が同じ(規則が格子の向きによらない)
標準ライブラリだけ。python3 Check_tjunction.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_tjunction import S0, RN, G, QTOT, CASES, FILM_Q, GROUPS, SYM_BASE, ORIS, T_SYM, spacing, nfilm

T_AVG = 110.0            # この時刻(分)から終わりまでを平均する
TOL_STEADY = {0: 0.05, 1: 0.03, 4: 0.03}        # (1) 終わりの 10 分の水深の振れ幅 (m)。移流項の規則ごと
TOL_MASS = {0: 1.0e-2, 1: 2.0e-3, 4: 2.0e-3}    # (2) 測線の流量の相対差。同上
TOL_UNI = 0.01           # (3) 下流の水深の、等流水深からの相対差
TOL_GAIN = 0.03          # (4) 損失なしの理論を下回ってよい幅 (m)
TOL_WD = 0.02            # (5) 濡れた岸 − 乾いた岸 の水深の差 (m)
P_BAND = {"ax": (0.5, 0.7), "rot": (0.7, 0.95)}      # (6) p の幅(f_advection_lateral = 1)
P_BAND4 = {"ax": (0.4, 0.7), "rot": (0.7, 0.95)}     # (6) p の幅(4 つの値の組み合わせ)
TOL_SYM = 5.0e-6         # (7) 向きを変えた構成との水深の差 (m)。記録は 10⁻⁶ m の桁まで
TAGS = ("m800", "m500", "m200")


def series(d, n):
    """プローブ n の (時刻 [分], 水深) の並び"""
    out = []
    with open("%s/probes/probe%04d.csv" % (d, n)) as f:
        for ln in f:
            if ln.startswith("#"):
                continue
            c = ln.split(",")
            out.append((float(c[1]), float(c[3])))
    return out


def probe(d, n):
    """プローブ n の、T_AVG 以降の水深の平均と振れ幅"""
    h = [v for t, v in series(d, n) if t >= T_AVG]
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


def theory(h, q1, q3, dl):
    """h = [J−1, J, J+1, J+2] の計算の水深、dl = セルの間隔。J−1 の水深の理論(運動量、損失なし)を返す"""
    q = [q1, 0.5 * (q1 + q3), q3, q3]                 # 合流のセル J は途中として平均
    sf = [RN ** 2 * qq ** 2 / hh ** (10.0 / 3.0) for qq, hh in zip(q, h)]
    force = sum(0.5 * ((S0 - sf[i]) * h[i] + (S0 - sf[i + 1]) * h[i + 1]) * dl for i in range(3))
    hf = sum(0.5 * (sf[i] + sf[i + 1]) * dl for i in range(3))
    m3 = h[3] ** 2 / 2 + q3 ** 2 / (G * h[3])
    e3 = h[3] + q3 ** 2 / (2 * G * h[3] ** 2)
    hc = (q1 ** 2 / G) ** (1.0 / 3.0)                 # 限界水深(常流の根を取るための下限)
    hm = solve(lambda x: x * x / 2 + q1 ** 2 / (G * x) - (m3 - force), hc, 30.0)
    he = solve(lambda x: x + q1 ** 2 / (2 * G * x * x) - (e3 + hf - S0 * 3 * dl), hc, 30.0)
    return hm, he


def group(pre, geom, lat):
    """1 つの組(6 構成)を検定する。合格なら True"""
    ok = True
    strict = lat >= 1                 # 項目 (5)(6) を判定するか
    rule = "4 つの値の組み合わせ" if lat == 4 else "f_advection_lateral = %d" % lat
    dl, width = spacing(geom)
    q3 = QTOT / width
    hn = (q3 * RN / S0 ** 0.5) ** 0.6                 # 合流の下流の等流水深
    res = {}
    worst = {"steady": 0.0, "mass": 0.0, "uni": 0.0, "gain": 9.9}
    print("--- %s、%s(構成名 %s<流量比>_<岸>。合流の下流は単位幅 %.1f m2/s、等流水深 %.3f m) ---"
          % ("格子の軸に沿う合流" if geom == "ax" else "45° 回した合流", rule, pre, q3, hn))
    print("  構成(本川・支川 m3/s、岸)   J−1 の水深   理論: 損失なし / 運動量    位置 p    振れ幅    測線の流量")
    for tag in TAGS:
        q1, q2 = CASES[tag]
        for bank in ("dry", "wet"):
            d = "result_%s%s_%s" % (pre, tag, bank)
            pr = [probe(d, n) for n in range(1, 18)]
            h = [pr[n][0] for n in (5, 6, 7, 8)]       # プローブ 6〜9 = J−1, J, J+1, J+2
            hm, he = theory(h, q1 / width, q3, dl)
            p = (h[0] - he) / (hm - he)
            amp = max(a for _, a in pr)
            qin = q1 + q2 + (nfilm(geom) * FILM_Q if bank == "wet" else 0.0)
            qf = abs(flux_last(d))
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

    def note(label, good):
        """1 と、4 つの値の組み合わせでは判定、0 では記録(判定しない)"""
        if strict:
            judge(label, good)
        else:
            print("  %s : 記録(判定しない。0 の限界)" % label)

    judge("(1) 定常: 終わりの 10 分の水深の振れ幅の最大 %.3f m (< %.2f)" % (worst["steady"], TOL_STEADY[lat]), worst["steady"] < TOL_STEADY[lat])
    judge("(2) 質量: 測線の流量と与えた流量の和の相対差の最大 %.1e (< %.0e)" % (worst["mass"], TOL_MASS[lat]), worst["mass"] < TOL_MASS[lat])
    judge("(3) 合流の 6 セル下流の水深の、等流水深からの相対差の最大 %.1e (< %.0e)" % (worst["uni"], TOL_UNI), worst["uni"] < TOL_UNI)
    judge("(4) 合流でエネルギーが増えない: J−1 の水深 − 損失なしの理論 の最小 %+.3f m (> −%.2f)" % (worst["gain"], TOL_GAIN),
          worst["gain"] > -TOL_GAIN)
    pd = [res[(t, "dry")][3] for t in TAGS]
    pw = [res[(t, "wet")][3] for t in TAGS]
    dm_d = [res[(t, "dry")][0] - res[(t, "dry")][1] for t in TAGS]
    dm_w = [res[(t, "wet")][0] - res[(t, "wet")][1] for t in TAGS]
    dwd = [res[(t, "wet")][0] - res[(t, "dry")][0] for t in TAGS]
    note("(5) 濡れた岸 − 乾いた岸 の J−1 の水深の差 %+.3f・%+.3f・%+.3f m (絶対値 < %.2f)" % (dwd[0], dwd[1], dwd[2], TOL_WD),
         max(abs(v) for v in dwd) < TOL_WD)
    lo, hi = (P_BAND4 if lat == 4 else P_BAND)[geom]
    note("(6) 位置 p(0 = 損失なし、1 = 運動量の理論。本川が主・同じ・支川が主)が %.2f〜%.2f" % (lo, hi),
         all(lo <= v <= hi for v in pd + pw))
    print("        乾いた岸 p = %.2f・%.2f・%.2f(運動量の理論との差 %+.2f・%+.2f・%+.2f m)" % (pd[0], pd[1], pd[2], dm_d[0], dm_d[1], dm_d[2]))
    print("        濡れた岸 p = %.2f・%.2f・%.2f(運動量の理論との差 %+.2f・%+.2f・%+.2f m)" % (pw[0], pw[1], pw[2], dm_w[0], dm_w[1], dm_w[2]))
    return ok


def symmetry():
    """向きを変えた構成の、T_SYM の水深を、基本の向きの同じ時刻の水深と比べる"""
    ok = True
    t_sym = T_SYM / 60.0
    print("--- 向きを変えた構成(f_advection_lateral = 1 と、4 つの値の組み合わせ。%.0f 分の、17 プローブの水深を基本の向きと比べる) ---" % t_sym)
    for base in SYM_BASE:
        ref = []
        for n in range(1, 18):
            ref.append([v for t, v in series("result_%s" % base, n) if abs(t - t_sym) < 1.0e-6][0])
        worst = []
        for ori in ORIS:
            cur = [series("result_%s_%s" % (base, ori), n)[-1] for n in range(1, 18)]
            if any(abs(t - t_sym) > 1.0e-6 for t, _ in cur):
                print("  %s_%s: 最後の記録が %.0f 分でない" % (base, ori, t_sym))
                ok = False
                continue
            worst.append(max(abs(v - r) for (_, v), r in zip(cur, ref)))
        good = len(worst) == len(ORIS) and max(worst) < TOL_SYM
        ok = ok and good
        print("  (7) %s: 東西・南北・両方を反転した構成との水深の差の最大 %s m (< %.0e) : %s"
              % (base, "・".join("%.1e" % w for w in worst), TOL_SYM, "PASS" if good else "FAIL"))
    return ok


def main():
    print("=== tjunction: 1 セル幅の T 字の合流(合流の下流 %.0f m3/s) ===" % QTOT)
    ok = True
    for pre, geom, lat in GROUPS:
        ok = group(pre, geom, lat) and ok
    ok = symmetry() and ok
    print("=== tjunction checks %s ===" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
