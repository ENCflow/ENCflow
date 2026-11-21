#!/usr/bin/env python3
"""wetbank の検定: 雨で濡れた河岸が、斜めのラスタ河道の水深を雨の流入の分を超えて変えないか。

  python3 Check_wetbank.py          判定と表
  python3 Check_wetbank.py table    README 用の Markdown の表も出す

各ケースの最後の出力の水深を、斜めの区間の中央の半分(中心線に沿う距離 s = lin + L/4 〜 lin + 3L/4)の
河道セルで平均する(h)。河岸を濡らしても、物理的には雨の流入で流量が Q0 → Q(s) に増える分しか水深は
変わらないはずで、Manning の等流(水深 ∝ Q^0.6)なら h_wet / h_dry − 1 ≈ 0.6 (Q/Q0 − 1)。その差

    E = h_wet / h_dry − 1 − 0.6 (Q/Q0 − 1)      (同じ構成の雨あり・乾いた河岸のケースの比)

を「濡れた河岸による余分な水深」とする(理論値 0)。Q(s) は上流端の流量 Q0 に、s までの領域の面積 ×
降雨強度を足したもの(定常の質量保存。河岸の雨水は横断勾配ですぐ河道へ入る)。

構成(make_init.py の OPTS。どれも 4 つのスイッチ f_advection_donor・f_advection_bend・f_advection_lateral・
f_dry_head_cap を明示)は 2 組。組ごとに、0 の構成(f_advection_donor = 0)・側方面 0 の構成・組み合わせそのもの:
  古い組(古い値の組み合わせ 3・1・1・3): o0 = 0・1・0・3、o3l0 = 3・1・0・3、o3 = 3・1・1・3
  新しい組(4 つの値の組み合わせ 4・2・2・4): o0n = 0・2・0・4、o4l0 = 4・2・0・4、o4 = 4・2・2・4
下の (3)(5)(6)(7) は組ごとに判定する(o0・o3l0・o3 を、新しい組では o0n・o4l0・o4 に読み替える)。ただし (3) は
古い組だけで判定し、新しい組では記録する(f_advection_donor = 4 の流れごとの重みは、深い供給元の重みも変えるので、
乾いた河岸の流れが 0 と一致する性質そのものがない)。新しい組の (6) は、o4 と o4l0 を比べる(側方面の規則
f_advection_lateral = 2 が、乾いた河岸の流れを変えないこと)。

判定(PASS/FAIL):
  (1) 定常: 測る区間の河道セルの平均水深が、最後の 2 つの出力で 1 mm 未満しか変わらない(乾いた河岸の 30° の
      階段では、個々のセルが 1 cm 程度揺れ続けるが、平均は 0.1 mm 以内で一定)
  (2) 河道に収まる: 測る区間の河岸セルの水深が 0.1 m 未満(越流しない = 検定の前提)
  (3) 乾いた河岸では o0 と o3l0 の水深が全セルで一致(f_advection_donor = 3 そのものは、乾いた河岸の流れを
      変えない)
  (4) 格子に沿う水路(θ = 0°)では、どの構成でも |E| <= 1 %
  (5) f_advection_donor = 3 は 0 より悪くない: E(o3l0) <= E(o0) + 0.5 %、E(o3) <= E(o0) + 0.5 %(全ての形)
  (6) 乾いた河岸では、o3 の区間平均の水深が o0 に ±TOL_DRY で一致(f_advection_lateral = 1 は、河道の
      セルどうしの側方面にも掛かるので、45° の階段と幅が複数セルの河道では、個々のセルの水深は一致しない。
      セルごとの差の最大は記録)。新しい組では、o4 と o4l0 の区間平均の水深が ±TOL_DRY で一致
  (7) 組み合わせそのもの(o3・o4)は、濡れた河岸による余分な水深が小さい: 全ての形で |E| <= E_MAX
E(o0)・E(o3l0)・E(o0n)・E(o4l0) が 0 から離れる量(斜めの水路での残差)は限界として表に出し、合否には使わない(README)。
TOL_DRY と E_MAX は、今の値(0.006 % 以下、−0.4〜3.7 %・0.2〜2.0 %)に余裕を見た回帰の上限で、理論から出した値ではない。
"""
import glob, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_init as M    # noqa: E402

SENS = 0.6               # Manning の等流の水深の流量感度 dlnh/dlnQ
TOL_DRY = 1.0e-3         # (6) 乾いた河岸の区間平均の水深の相対差の上限(o3 と o0、o4 と o4l0)
E_MAX = 5.0              # (7) 組み合わせそのもの(o3・o4)の |E| の上限 (%)
OPTS = [o[0] for o in M.OPTS]
# 組: (名前, 0 の構成, 側方面 0 の構成, 組み合わせそのもの, (6) の比べる相手, (3) を判定するか)
GROUPS = (("old", "o0", "o3l0", "o3", "o0", True), ("new", "o0n", "o4l0", "o4", "o4l0", False))


def manning_h(q, w, s0, rn):
    """矩形断面(幅 w、径深 = 面積 / 潤辺)の等流水深(二分法)。"""
    lo, hi = 1e-4, 50.0
    for _ in range(80):
        h = 0.5 * (lo + hi)
        a = w * h
        qq = a * (a / (w + 2 * h)) ** (2 / 3) * s0 ** 0.5 / rn
        lo, hi = (h, hi) if qq < q else (lo, h)
    return 0.5 * (lo + hi)


def geom(geo):
    d = f"d_{geo}"
    info = {}
    for line in open(os.path.join(d, "info.txt")):
        w = line.split()
        if w[0] != "inflow":
            info[w[0]] = float(w[1])
    s = np.loadtxt(os.path.join(d, "s.txt"))
    rw = np.loadtxt(os.path.join(d, "rw.txt")) > 0
    mask = np.loadtxt(os.path.join(d, "mask.txt")) > 0
    s1, s2 = info["lin"] + 0.25 * info["L"], info["lin"] + 0.75 * info["L"]
    reach = (s >= s1) & (s <= s2)
    return info, s, rw, mask, reach, 0.5 * (s1 + s2)


def last_two(case):
    fs = sorted(f for f in glob.glob(f"result_{case}/H[0-9][0-9][0-9][0-9].txt") if int(f[-8:-4]) < 9000)
    if len(fs) < 2:
        sys.exit(f"result_{case}: outputs not found (run ./Run.sh first)")
    return np.loadtxt(fs[-1]), np.loadtxt(fs[-2])


def main():
    want_table = "table" in sys.argv[1:]
    fails = []
    rows = []
    for th, dx, nc in M.GEOMS:
        geo = M.tag(th, dx, nc)
        info, s, rw, mask, reach, smid = geom(geo)
        chan, bank = rw & reach, mask & ~rw & reach
        area_up = (mask & (s >= 0) & (s <= smid)).sum() * dx * dx
        q0 = info["q0"]
        res = {}
        for rain in (0.0, M.RAIN):
            for opt in OPTS:
                case = f"{geo}_r{rain:g}_{opt}"
                h, hp = last_two(case)
                dh = abs(h[chan].mean() - hp[chan].mean())
                if dh >= 1e-3:
                    fails.append(f"(1) {case}: not steady (reach-mean depth changed by {dh:.2e} m between the last "
                                 f"two outputs; max cell change {np.abs(h - hp)[chan].max():.2e} m)")
                hb = h[bank].max()
                if hb >= 0.1:
                    fails.append(f"(2) {case}: water on the banks ({hb:.3f} m >= 0.1 m)")
                res[(rain, opt)] = (h, h[chan].mean())
        qr = 1.0 + M.RAIN / 3.6e6 * area_up / q0
        e = {}
        for opt in OPTS:
            e[opt] = 100.0 * (res[(M.RAIN, opt)][1] / res[(0.0, opt)][1] - 1.0 - SENS * (qr - 1.0))
        if th == 0.0:
            for opt in OPTS:
                if abs(e[opt]) > 1.0:
                    fails.append(f"(4) {geo}: grid-aligned channel, |E| = {abs(e[opt]):.2f} % > 1 % ({opt})")
        row = [th, dx, nc, qr, SENS * (qr - 1.0) * 100]
        hn = manning_h(q0, info["omega"], info["S"], info["rn"])
        for gname, o0, ol0, oc, oref, judge3 in GROUPS:
            d3 = np.abs(res[(0.0, o0)][0] - res[(0.0, ol0)][0]).max()
            if judge3 and d3 > 0.0:
                fails.append(f"(3) {geo}: dry banks, {o0} and {ol0} differ")
            ddry = res[(0.0, oc)][1] / res[(0.0, oref)][1] - 1.0
            dcell = np.abs(res[(0.0, oc)][0] - res[(0.0, oref)][0]).max()
            if abs(ddry) > TOL_DRY:
                fails.append(f"(6) {geo}: dry banks, reach-mean depth of {oc} differs from {oref} by "
                             f"{100 * ddry:+.3f} % (> {100 * TOL_DRY:g} %)")
            for opt in (ol0, oc):
                if e[opt] > e[o0] + 0.5:
                    fails.append(f"(5) {geo}: {opt} is worse than {o0} (E {e[opt]:.1f} % > {e[o0]:.1f} %)")
            if abs(e[oc]) > E_MAX:
                fails.append(f"(7) {geo}: {oc} leaves an extra depth |E| = {abs(e[oc]):.1f} % > {E_MAX:g} %")
            hd = res[(0.0, o0)][1]
            row += [hd, hd / hn, e[o0], e[ol0], e[oc], 100 * ddry, dcell, d3]
        rows.append(row)
    print("geometry (theta, dx, cells)  rain effect | old group: h_dry(o0) h/h_n  E(o0)  E(o3l0)  E(o3)  dry o3-o0 "
          "(mean, max cell) | new group: h_dry(o0n) h/h_n  E(o0n)  E(o4l0)  E(o4)  dry o4-o4l0 (mean, max cell)  "
          "dry o0n-o4l0 max cell (record)")
    for r in rows:
        th, dx, nc, qr, ex = r[:5]
        a, b = r[5:13], r[13:21]
        print(f"  {th:5.1f} deg {dx:5.0f} m {nc:2d}   {ex:5.2f} %  |  {a[0]:6.3f} {a[1]:6.3f}  {a[2]:6.1f} %  {a[3]:6.1f} %  "
              f"{a[4]:6.1f} %  {a[5]:+7.3f} % {a[6]:6.3f} m  |  {b[0]:6.3f} {b[1]:6.3f}  {b[2]:6.1f} %  {b[3]:6.1f} %  "
              f"{b[4]:6.1f} %  {b[5]:+7.4f} % {b[6]:6.4f} m  {b[7]:6.3f} m")
    if want_table:
        print("\n| 向き θ | Δx | 河道の太さ | 雨の流入による増分 | h / h_n(古い組) | E(0) | E(3・側方面 0) | E(3) "
              "| h / h_n(新しい組) | E(0) | E(4・側方面 0) | E(4) |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            th, dx, nc, qr, ex = r[:5]
            a, b = r[5:13], r[13:21]
            print(f"| {th:g}° | {dx:g} m | {nc} セル | {ex:.1f} % | {a[1]:.3f} | {a[2]:.1f} % | {a[3]:.1f} % | {a[4]:.1f} % "
                  f"| {b[1]:.3f} | {b[2]:.1f} % | {b[3]:.1f} % | {b[4]:.1f} % |")
    if fails:
        print("\n".join(["FAIL " + f for f in fails]))
        return 1
    print("PASS: wetbank (steady, confined, dry o0 = o3l0, grid-aligned |E| <= 1 %, o3/o4 and lateral 0 not worse "
          f"than donor 0, dry reach mean unchanged by the lateral rule, |E(o3)|, |E(o4)| <= {E_MAX:g} %)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
