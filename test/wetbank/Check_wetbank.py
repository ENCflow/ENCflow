#!/usr/bin/env python3
"""wetbank の検定: 雨で濡れた河岸が、斜めのラスタ河道の水深を雨の流入の分を超えて変えないか。

  python3 Check_wetbank.py          判定と表
  python3 Check_wetbank.py table    README 用の Markdown の表も出す

各ケースの最後の出力の水深を、斜めの区間の中央の半分(中心線に沿う距離 s = lin + L/4 〜 lin + 3L/4)の
河道セルで平均する(h)。河岸を濡らしても、物理的には雨の流入で流量が Q0 → Q(s) に増える分しか水深は
変わらないはずで、Manning の等流(水深 ∝ Q^0.6)なら h_wet / h_dry − 1 ≈ 0.6 (Q/Q0 − 1)。その差

    E = h_wet / h_dry − 1 − 0.6 (Q/Q0 − 1)      (同じ f_advection_donor の雨あり・乾いた河岸のケースの比)

を「濡れた河岸による余分な水深」とする(理論値 0)。Q(s) は上流端の流量 Q0 に、s までの領域の面積 ×
降雨強度を足したもの(定常の質量保存。河岸の雨水は横断勾配ですぐ河道へ入る)。

判定(PASS/FAIL):
  (1) 定常: 測る区間の河道セルの平均水深が、最後の 2 つの出力で 1 mm 未満しか変わらない(乾いた河岸の 30° の
      階段では、個々のセルが 1 cm 程度揺れ続けるが、平均は 0.1 mm 以内で一定)
  (2) 河道に収まる: 測る区間の河岸セルの水深が 0.1 m 未満(越流しない = 検定の前提)
  (3) 乾いた河岸では f_advection_donor = 0 と 3 の水深が全セルで一致
  (4) 格子に沿う水路(θ = 0°)では、どちらの f_advection_donor でも |E| <= 1 %
  (5) f_advection_donor = 3 は 0 より悪くない: E(3) <= E(0) + 0.5 %(全ての形)
E が 0 から離れる量(斜めの水路での残差)は限界として表に出し、合否には使わない(README)。
"""
import glob, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_init as M    # noqa: E402

SENS = 0.6               # Manning の等流の水深の流量感度 dlnh/dlnQ


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
            for opt in (0, 3):
                case = f"{geo}_r{rain:g}_o{opt}"
                h, hp = last_two(case)
                dh = abs(h[chan].mean() - hp[chan].mean())
                if dh >= 1e-3:
                    fails.append(f"(1) {case}: not steady (reach-mean depth changed by {dh:.2e} m between the last "
                                 f"two outputs; max cell change {np.abs(h - hp)[chan].max():.2e} m)")
                hb = h[bank].max()
                if hb >= 0.1:
                    fails.append(f"(2) {case}: water on the banks ({hb:.3f} m >= 0.1 m)")
                res[(rain, opt)] = (h, h[chan].mean())
        if np.abs(res[(0.0, 0)][0] - res[(0.0, 3)][0]).max() > 0.0:
            fails.append(f"(3) {geo}: dry banks, f_advection_donor 0 and 3 differ")
        qr = 1.0 + M.RAIN / 3.6e6 * area_up / q0
        e = {}
        for opt in (0, 3):
            e[opt] = 100.0 * (res[(M.RAIN, opt)][1] / res[(0.0, opt)][1] - 1.0 - SENS * (qr - 1.0))
        if th == 0.0:
            for opt in (0, 3):
                if abs(e[opt]) > 1.0:
                    fails.append(f"(4) {geo}: grid-aligned channel, |E| = {abs(e[opt]):.2f} % > 1 % (option {opt})")
        if e[3] > e[0] + 0.5:
            fails.append(f"(5) {geo}: option 3 is worse than 0 (E {e[3]:.1f} % > {e[0]:.1f} %)")
        hd = res[(0.0, 0)][1]
        hn = manning_h(q0, info["omega"], info["S"], info["rn"])
        rows.append((th, dx, nc, hd, hd / hn, qr, SENS * (qr - 1.0) * 100, e[0], e[3]))
    print("geometry (theta, dx, cells)   h_dry   h_dry/h_n   Q/Q0   rain effect   E(0)     E(3)")
    for th, dx, nc, hd, rh, qr, ex, e0, e3 in rows:
        print(f"  {th:5.1f} deg  {dx:5.0f} m  {nc:2d}      {hd:6.3f}   {rh:6.3f}    {qr:6.3f}   {ex:5.2f} %    "
              f"{e0:6.1f} %  {e3:6.1f} %")
    if want_table:
        print("\n| 向き θ | Δx | 河道の太さ | 乾いた河岸の水深 h (m) | h / h_n | 雨の流入による増分 | E(0) | E(3) |")
        print("|---|---|---|---|---|---|---|---|")
        for th, dx, nc, hd, rh, qr, ex, e0, e3 in rows:
            print(f"| {th:g}° | {dx:g} m | {nc} セル | {hd:.3f} | {rh:.3f} | {ex:.1f} % | {e0:.1f} % | {e3:.1f} % |")
    if fails:
        print("\n".join(["FAIL " + f for f in fails]))
        return 1
    print("PASS: wetbank (steady, confined, dry 0 = 3, grid-aligned |E| <= 1 %, option 3 not worse than 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
