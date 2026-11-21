#!/usr/bin/env python3
"""test/cascade の検定: 急な段々の河道で、流れの水頭が上流端の水位を超えないこと。

  test/chichibu の 50 m 格子のデータから切り出した、本川が段々に下る区間(河床 354 → 268 m)に、上流端のセルから
  流量をゆっくり上げながら与える。水は流速 0 で入るので、定常に近い流れの水頭 z + h + V²/2g は、流量を与える
  セルの水位を超えないはず(エネルギーは流れに沿って増えない)。各セルの「河床 + 期間最大流速の速度水頭」
  (水深を数えない、水頭の下限)が、流量を与えるセルの期間最大の水位を超える分(超過)を見る。

  移流項の規則の 4 つのスイッチ(f_advection_donor・f_advection_bend・f_advection_lateral・f_dry_head_cap)を全部
  明示した 4 構成(c2 = 3・1・0・2、c3 = 3・1・0・3、c3j = 3・1・1・3、c4 = 4・2・2・4 = 4 つの値の組み合わせ)。
  射流が低い岸へ乗り上げて河道へ戻る所で、乗り上げの数え方によって超過が出る(README)。頭打ち 3・4 は、岸を
  壁にした地形と同じ程度に収まる。2 は、岸が乾いていると大きく超える(2 の限界として記録)。

  判定する項目:
    (1) 質量の収支(4 構成とも): 終わりの 10 分の下流の測線の流量の平均が、与えた流量に ±TOL_MASS
    (2) 超過の最大(c3・c3j・c4): TOL_EXCESS 未満(河道マスクの外のセルを含む。期間最大水深が H_WET 以上のセル)
  記録する項目:
    (2) c2 の超過の最大と、その場所・流速
    (3) 期間最大流速の最大と、その場所
標準ライブラリだけ。python3 Check_cascade.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_cascade import CASES, IX0, IY0, SOURCE, Q_HI, T_END

GG = 9.8                 # 速度水頭に使う重力加速度 (m/s2。計算の既定と同じ)
TOL_MASS = 0.01          # (1) 終わりの 10 分の流量の平均の、与えた流量からの相対差
H_WET = 0.5              # (2) 超過を見るセルの、期間最大水深の下限 (m)
JUDGE = ("c3", "c3j", "c4")    # (2) を判定する構成(c2 は記録)
TOL_EXCESS = 10.0        # (2) 超過の上限 (m。岸を壁にした地形の値 5.7 m の 2 倍弱)


def read(path):
    rows = []
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        rows.append([float(v) for v in line.replace(",", " ").split()])
    return rows


def main():
    print("=== cascade: 急な段々の河道(流れの水頭が上流端の水位を超えないこと) ===")
    ok = True

    def note(msg, good):
        nonlocal ok
        print("  %s : %s" % (msg, "PASS" if good else "FAIL"))
        ok = ok and good

    z = read("cs_z.txt")
    si, sj = SOURCE
    for name, (don, bend, lat, cap) in CASES.items():
        d = "result_%s" % name
        print("-- f_advection_donor・f_advection_bend・f_advection_lateral・f_dry_head_cap = %d・%d・%d・%d(%s)"
              % (don, bend, lat, cap, name))
        fl = read(os.path.join(d, "fluxes", "flux0001.csv"))
        last = [abs(r[2]) for r in fl if r[1] >= T_END - 10.0]
        qm = sum(last) / len(last)
        note("(1) 終わりの 10 分の下流の測線の流量の平均 %.0f m3/s(与えた流量 %.0f に %+.2f %%。±%.0f %%)"
             % (qm, Q_HI, 100.0 * (qm / Q_HI - 1.0), 100.0 * TOL_MASS), abs(qm / Q_HI - 1.0) < TOL_MASS)
        hm = read(os.path.join(d, "H9999.txt"))
        vm = read(os.path.join(d, "V9999.txt"))
        eta_s = z[sj - 1][si - 1] + hm[sj - 1][si - 1]
        ex, vbest = None, None
        for j in range(len(vm)):
            for i in range(len(vm[0])):
                if vbest is None or vm[j][i] > vbest[0]:
                    vbest = (vm[j][i], i + IX0, j + IY0)
                if hm[j][i] < H_WET:
                    continue
                e = z[j][i] + vm[j][i] ** 2 / (2.0 * GG) - eta_s
                if ex is None or e > ex[0]:
                    ex = (e, i + IX0, j + IY0, vm[j][i], z[j][i])
        msg = ("(2) 河床 + 速度水頭が、流量を与えるセルの最大水位 %.1f m を超える分の最大 %+.1f m"
               "(セル (%d,%d)。河床 %.1f m、期間最大流速 %.1f m/s)" % (eta_s, ex[0], ex[1], ex[2], ex[4], ex[3]))
        if name in JUDGE:
            note(msg + " (< %.0f m)" % TOL_EXCESS, ex[0] < TOL_EXCESS)
        else:
            print("  %s(2 の限界として記録)" % msg)
        print("  (3) 期間最大流速の最大 %.1f m/s(セル (%d,%d)。記録)" % vbest)
    print("=== cascade checks %s ===" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
