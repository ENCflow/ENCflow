#!/usr/bin/env python3
"""test/chutepool の検定: 落差を落ちた射流が池へ落ち込む所で、池の中の測線の流量が揺れないこと。

  test/chichibu のデータから切り出した地形に、流量をゆっくり上げながら与える。本川は、落差を落ちた直後に折れて
  池へ入り、落差の下のセルの流れの正面には、水位より高い斜面のセルがある。池の中の測線の流量(10 秒ごと)を見る。

  エッジ水深の頭打ち f_dry_head_cap = 2(構成 c2)・3(c3)と、4 つの値の組み合わせ(c4 = f_advection_donor・
  f_advection_bend・f_advection_lateral・f_dry_head_cap = 4・2・2・4)を見る(c2・c3 の残りの 3 つは 3・1・1 を明示)。
  3・4 は、送り手のセルへ射流で入ってくる
  流れを、同じ流量の限界流の比エネルギーまでしか数えない。速度水頭をそのまま数えると、正面の斜面へ水が登り、
  池の流量が揺れ続ける(README)。

  判定する項目(3 構成とも):
    (1) 質量の収支: 終わりの 5 分の測線の流量の平均が、与えた流量に ±TOL_MASS
    (2) 助走のあとの測線の流量が揺れない: 1 分の移動平均からのずれの最大が TOL_DEV 未満で、
        続けて逆向きの変化(どちらも REV_MIN を超える)がない
  記録する項目:
    (3) 落差の下のセルの流れの正面にある斜面のセルの、期間最大の水深
標準ライブラリだけ。python3 Check_chutepool.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_chutepool import CASES, Q_HI, T_SPIN, T_END

TOL_MASS = 0.01          # (1) 終わりの 5 分の流量の平均の、与えた流量からの相対差
T_FROM = T_SPIN + 5.0    # (2) この時刻(分)以降を見る
TOL_DEV = 80.0           # (2) 1 分の移動平均(10 秒値 7 点)からのずれの最大 (m3/s)
REV_MIN = 20.0           # (2) 向きの入れ替わりに数える 10 秒の変化の大きさ (m3/s)


def read(path):
    rows = []
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        rows.append([float(v) for v in line.replace(",", " ").split()])
    return rows


def osc(t, q):
    """T_FROM 以降の、1 分の移動平均からのずれの最大・その時刻、続けて逆向きの変化の数・その最初と最後の時刻"""
    k = [i for i in range(len(t)) if t[i] >= T_FROM]
    dev, tdev = 0.0, t[k[0]]
    for i in k[3:-3]:
        m = sum(q[i - 3:i + 4]) / 7.0
        if abs(q[i] - m) > dev:
            dev, tdev = abs(q[i] - m), t[i]
    rev = []
    for i in k[2:]:
        a, b = q[i - 1] - q[i - 2], q[i] - q[i - 1]
        if a * b < 0.0 and abs(a) > REV_MIN and abs(b) > REV_MIN:
            rev.append(t[i])
    return dev, tdev, rev


def main():
    print("=== chutepool: 落差のあとの池へ落ち込む流れ(池の中の測線の流量) ===")
    ok = True

    def note(msg, good):
        nonlocal ok
        print("  %s : %s" % (msg, "PASS" if good else "FAIL"))
        ok = ok and good

    for name, (don, bend, lat, cap) in CASES.items():
        d = "result_%s" % name
        fl = read(os.path.join(d, "fluxes", "flux0001.csv"))
        t = [r[1] for r in fl]
        q = [r[2] for r in fl]
        print("-- f_dry_head_cap = %d(%s。f_advection_donor・bend・lateral = %d・%d・%d)" % (cap, name, don, bend, lat))
        last = [q[i] for i in range(len(t)) if t[i] >= T_END - 5.0]
        qm = sum(last) / len(last)
        note("(1) 終わりの 5 分の測線の流量の平均 %.1f m3/s(与えた流量 %.0f に %+.2f %%。±%.0f %%)"
             % (qm, Q_HI, 100.0 * (qm / Q_HI - 1.0), 100.0 * TOL_MASS), abs(qm / Q_HI - 1.0) < TOL_MASS)
        dev, tdev, rev = osc(t, q)
        span = "(%.0f〜%.0f 分)" % (rev[0], rev[-1]) if rev else ""
        note("(2) %.0f 分以降の測線の流量: 1 分の移動平均からのずれの最大 %.0f m3/s @ %.1f 分 (< %.0f)、"
             "続けて逆向きの変化 %d 回%s (0 回)" % (T_FROM, dev, tdev, TOL_DEV, len(rev), span),
             dev < TOL_DEV and not rev)
        pb = read(os.path.join(d, "probes", "probe0002.csv"))
        print("  (3) 流れの正面の斜面のセルの期間最大の水深 %.2f m(記録)" % max(r[3] for r in pb))
    print("=== chutepool checks %s ===" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
