#!/usr/bin/env python3
"""test/stageside の検定: 境界として与えたセルの列(水位規定セル・湧き出し)から流れ出す水と、側方 Neumann の辺
(Python 標準ライブラリのみ)。

  長さ 600 m・幅 40 m(120 × 8 セル)の水路の東端の 1 列から水を入れ、東は壁、西は長波放射、南北は側方 Neumann に
  して、静水から 60 分計算する。東端の列は、水位規定セル(+0.2 m。s3・s4)と、湧き出し(48 m3/s。q3・q4)の 2 通り。
  移流項の規則は、古い値の組み合わせ(s3・q3 = f_advection_donor 3・f_advection_bend 1・f_advection_lateral 1・
  f_dry_head_cap 3)と、4 つの値の組み合わせ(s4・q4 = 4・2・2・4)の 2 通りで、合わせて 4 構成。

  判定(4 構成とも):
    (1) 最後まで計算する(発散して止まらない)
    (2) 定常: 40 分と 60 分の流速 u の差の最大が TOL_STEADY 未満
    (3) 岸沿いに一様: 列 I_UNI 以降で、行の間の u・水深 h の差の最大と、|v| の最大が TOL_UNI 未満
        (西の辺のすぐ内側は、長波放射の辺と側方 Neumann の辺の角の影響で 1e-5 m/s の差があるので、外す)
  判定(規則の違う 2 構成の比較。s4 と s3、q4 と q3):
    (4) 4 つの値の構成の水深・流速が、古い値の構成と一致する(差の最大が TOL_SAME 未満)。4 つの値の規則は、
        境界として与えたセル(水位規定セル・湧き出しのセル)から出る水に、静止からの加速を数えない(古い値と同じ。
        developer.md §113.9)。この水路のように、流れがゆるやかに変わるだけの所では、ほかの規則も古い値と
        同じ値になる
  記録(判定しない):
    s3・s4: 東端のすぐ内側の列のエネルギー水頭(水位 + 速度水頭)と、規定水位の差
    q3・q4: 湧き出しの列の水位と、隣の列の水位の差

  与えたセルの印を、側方 Neumann の辺の外(鏡像)の位置で読まないと、与えたセルの列と側方 Neumann の辺の角で、
  枠の中の面と境界面の扱いが食い違い、s4 が 13 分で発散する(developer.md §113.9 (7))。湧き出しのセルに静止からの
  加速を数えると、q4 の湧き出しの列が、流出の速度水頭の分(0.015 m)だけ q3 より深くなる(同 (9))。
  出力はバイナリ(単精度の .bil。行 8 × 列 120)を読む。基準は、今の値に余裕を見た回帰の上限。
"""
import array
import os
import sys

NX, NY = 120, 8
G = 9.8
ETA = 0.2                # s3・s4 の規定水位 (m)
Q = 48.0                 # q3・q4 の湧き出しの流量 (m3/s)
I_UNI = 6                # (3) を見る最初の列(1 始まり)
TOL_STEADY = 1.0e-5      # (2) m/s
TOL_UNI = 1.0e-6         # (3) m/s・m
TOL_SAME = 1.0e-5        # (4) m・m/s
CONFIGS = (("s3", "水位規定セルの列。古い値 3・1・1・3"), ("s4", "水位規定セルの列。4 つの値 4・2・2・4"),
           ("q3", "湧き出しの列。古い値 3・1・1・3"), ("q4", "湧き出しの列。4 つの値 4・2・2・4"))
PAIRS = (("s4", "s3"), ("q4", "q3"))


def read(d, name, tag):
    """result_<d>/<name><tag>.bil を [行][列] で返す。なければ None"""
    path = "result_%s/%s%s.bil" % (d, name, tag)
    if not os.path.exists(path) or os.path.getsize(path) != 4 * NX * NY:
        return None
    a = array.array("f")
    with open(path, "rb") as f:
        a.fromfile(f, NX * NY)
    return [list(a[j * NX:(j + 1) * NX]) for j in range(NY)]


def maxdiff(a, b, i0=0):
    return max(abs(a[j][i] - b[j][i]) for j in range(NY) for i in range(i0, NX))


def spread(a, i0):
    return max(max(a[j][i] for j in range(NY)) - min(a[j][i] for j in range(NY)) for i in range(i0, NX))


def bed(i):
    return -3.0 + 1.5 * (i + 0.5) / NX


def main():
    ok = True

    def judge(text, good, cond):
        nonlocal ok
        print("  %s (%s) : %s" % (text, cond, "PASS" if good else "FAIL"))
        ok = ok and good

    print("=== stageside: 東端の列(水位規定セル +%.1f m・湧き出し %.0f m3/s)から流れ出す水と、側方 Neumann の辺 ===" % (ETA, Q))
    res = {}
    for c, label in CONFIGS:
        print("--- %s(%s) ---" % (c, label))
        h = read(c, "H", "9998")
        u = read(c, "u", "9998")
        v = read(c, "v", "9998")
        u2 = read(c, "u", "0002")
        done = None not in (h, u, v, u2)
        judge("(1) 最後まで計算する", done, "60 分の出力がある")
        if not done:
            continue
        res[c] = (h, u)
        st = maxdiff(u, u2)
        judge("(2) 定常: 40 分と 60 分の流速の差の最大 %.1e m/s" % st, st < TOL_STEADY, "< %.0e" % TOL_STEADY)
        i0 = I_UNI - 1
        su, sh = spread(u, i0), spread(h, i0)
        vm = max(abs(v[j][i]) for j in range(NY) for i in range(i0, NX))
        judge("(3) 岸沿いに一様(列 %d〜%d): 行の間の差の最大 u %.1e m/s・h %.1e m、|v| の最大 %.1e m/s"
              % (I_UNI, NX, su, sh, vm), max(su, sh, vm) < TOL_UNI, "< %.0e" % TOL_UNI)
        j = NY // 2 - 1
        i = NX - 2                          # 東端のすぐ内側の列(1 始まりで 119)
        print("  流速 (m/s。列 1・60・119・120): %.4f・%.4f・%.4f・%.4f、水深 (m。同): %.4f・%.4f・%.4f・%.4f"
              % (u[j][0], u[j][59], u[j][NX - 2], u[j][NX - 1], h[j][0], h[j][59], h[j][NX - 2], h[j][NX - 1]))
        if c.startswith("s"):
            head = bed(i) + h[j][i] + u[j][i] ** 2 / (2 * G)
            print("  記録: 列 119 のエネルギー水頭 %.4f m(規定水位 %+.4f m との差 %+.4f m。速度水頭 %.4f m)"
                  % (head, ETA, head - ETA, u[j][i] ** 2 / (2 * G)))
        else:
            e119, e120 = bed(i) + h[j][i], bed(i + 1) + h[j][i + 1]
            print("  記録: 湧き出しの列(列 120)の水位 %+.4f m、隣の列(列 119)の水位 %+.4f m(差 %+.4f m。列 119 の"
                  "速度水頭 %.4f m)" % (e120, e119, e120 - e119, u[j][i] ** 2 / (2 * G)))
    print("--- 規則の違う 2 構成の比較 ---")
    for a, b in PAIRS:
        if a in res and b in res:
            dh = maxdiff(res[a][0], res[b][0])
            du = maxdiff(res[a][1], res[b][1])
            judge("(4) %s と %s の差の最大: 水深 %.1e m・流速 %.1e m/s" % (a, b, dh, du), max(dh, du) < TOL_SAME,
                  "< %.0e" % TOL_SAME)
        else:
            judge("(4) %s と %s の差" % (a, b), False, "2 構成とも 60 分の出力がある")
    print("=== stageside checks %s ===" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
