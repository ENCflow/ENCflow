#!/usr/bin/env python3
"""wfdoppler の検定(沿岸の波浪場の流れによる変化 = 段 W3。developer.md §88)(Python 標準ライブラリのみ)

  python3 Check_wfdoppler.py opp   result_opp     # 逆流の上の規則波: 作用量の流束の保存
  python3 Check_wfdoppler.py fol   result_fol     # 順流の上の規則波: 同上
  python3 Check_wfdoppler.py fol72 result_fol result_fol72  # 順流のずれは Δθ² で小さくなる
  python3 Check_wfdoppler.py unst  result_opp_u result_opp  # 非定常: 準定常の解に達し、台帳が閉じる
  python3 Check_wfdoppler.py blk   result         # 逆流で阻止される不規則波(param.txt)
  python3 Check_wfdoppler.py nocur result_nocur result   # 流れの作用なしなら阻止されない
  python3 Check_wfdoppler.py zero  result_zero result_zero_off  # 流れが 0 なら W1 の経路と同じ解
  python3 Check_wfdoppler.py river result_river result_river_nocur  # 河口の噴流(V10)

水路(120 × 8 セル、Δx = 5 m。河床は西 −3 m → 東 −1.5 m)の定常な流れ(流量 q = 1.2 m²/s)の
上を、西の辺から入射した波が東へ進む。モデルの水位・流速(出力の .bil)を使い、ビンの向き
θ = 0 の分散関係 (ω − kU)² = g k tanh(kh) を U → 0 で連続な枝でここで独立に解いて
(Newton 法。倍精度)、作用量の流束 (c_g + U)E/σ が保存される定常解と比べる。離散の
定常解は送り手のセル中心の値で流束を評価するので、セル中心でこの保存則を満たす。

順流(fol)は流れの湧き出しの列が波の入射の列(西端)と重なり、流速が 1 セルで倍になる
(湧き出しのセルの u は面の平均で半分)。この強い流速の勾配による流れの屈折(発散)で、
単一方向の波の約 3% が隣のビン(±Δθ)へ広がる(1 次風上の方向空間では θ = 0 は極値なので
制限つき 2 次の補正が働かない。ビン幅に一様に広がった波としての表現)。広がった分は
x 向きの輸送が c_g cos Δθ + U と遅く、下流で水深による屈折が θ = 0 へ戻すので、全エネルギーは
1 次元の理論から Δθ² に比例してずれる(既定の 40 ビンで最大 1.05e-4、72 ビンで 3.2e-5)。
逆流(opp)は湧き出しが東端(検定の範囲の外)にあり、入射の列の流れが一様なので丸めの規模で
一致する。
"""
import csv
import math
import struct
import sys

NX, NY = 120, 8
G, RHO = 9.8, 1025.0        # 重力加速度は既定の p%gg
H0 = 0.05
failed = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failed.append(msg)


def read_bil(d, name, k="9998", nx=NX, ny=NY):
    with open("%s/%s%s.bil" % (d, name, k), "rb") as f:
        v = struct.unpack("<%df" % (nx * ny), f.read())
    return [list(v[j * nx:(j + 1) * nx]) for j in range(ny)]


def read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    return [dict(zip(head, [c.strip() for c in r])) for r in rows[1:] if r]


def param_value(path, name):
    for line in open(path):
        s = line.split("!")[0]
        if "=" in s and s.split("=")[0].strip() == name:
            return float(s.split("=")[1].strip().rstrip(",").strip("'"))
    raise KeyError(name)


def doppler(om, h, um):
    """(ω − k um)² = g k tanh(kh) の U → 0 で連続な枝。解なし・c_g + um <= 0 なら None"""
    y = om * om * h / G
    kh = y / math.tanh(y ** 0.75) ** (2.0 / 3.0)
    for _ in range(30):
        t = math.tanh(kh)
        kh -= (kh * t - y) / (t + kh * (1.0 - t * t))
    k = kh / h
    for _ in range(200):
        kh = k * h
        s0 = math.sqrt(G * k * math.tanh(kh))
        cg0 = 0.5 * s0 / k * (1.0 + 2.0 * kh / math.sinh(2.0 * kh))
        f = s0 + k * um - om
        df = cg0 + um
        if df <= 0.0:
            return None
        dk = f / df
        k -= dk
        if abs(dk) <= 1e-14 * k:
            break
    sig = om - k * um
    kh = k * h
    cg = 0.5 * sig / k * (1.0 + 2.0 * kh / math.sinh(2.0 * kh))
    if sig <= 0.0 or cg + um <= 0.0:
        return None
    return k, sig, cg


def fields(d):
    a = {n: read_bil(d, n) for n in ("E", "u", "v", "Wh")}
    a["Z"] = read_bil(d, "Z", "0000")
    return a


def energy(h, wavetype):
    return RHO * G * h * h / (8.0 if wavetype == 2 else 16.0)


def flux_profile(a, om, j, cur=True):
    """セルごとの (k, σ, c_g, U)。阻止なら None"""
    out = []
    for i in range(NX):
        h = a["E"][j][i] - a["Z"][j][i]
        um = a["u"][j][i] if cur else 0.0
        out.append(doppler(om, h, um))
    return out


def uniformity(a, label, i1=NX):
    """セル 1..i1 の行(岸沿い)の一様さ(阻止の点より先は残りの小さな波だけなので除く)"""
    du = max(abs(a["u"][j][i] - a["u"][1][i]) for j in range(NY) for i in range(i1))
    dh = max(abs(a["Wh"][j][i] - a["Wh"][1][i]) for j in range(NY) for i in range(i1))
    check(dh <= 2e-3 * H0, "%s: alongshore uniformity of the wave height in cells 1-%d (max row difference "
          "%.1e m <= %.0e m)" % (label, i1, dh, 2e-3 * H0))
    print("  %s: max row difference of the current %.1e m/s" % (label, du))


def flux_deviation(a, om, i0, i1):
    """作用量の流束の保存 (c_g + U)E/σ = const からの最大の相対差(セル i0 を基準に i0..i1)"""
    j = 1
    prof = flux_profile(a, om, j)
    k, sig, cg = prof[i0]
    flux = (cg + a["u"][j][i0]) * energy(a["Wh"][j][i0], 2) / sig
    worst, iw = 0.0, -1
    for i in range(i0, i1 + 1):
        k, sig, cg = prof[i]
        pred = flux * sig / (cg + a["u"][j][i])
        err = abs(energy(a["Wh"][j][i], 2) - pred) / pred
        if err > worst:
            worst, iw = err, i
    return worst, iw, prof


def check_flux(d, label, i0, i1, tol):
    """作用量の流束の保存 (c_g + U)E/σ = const(セル i0 を基準に i0..i1)"""
    print("== %s (%s): regular waves on a %s current" % (label, d, "following" if label == "fol" else "opposing"))
    om = 2.0 * math.pi / param_value("param_%s.txt" % label, "wf_trep")
    a = fields(d)
    uniformity(a, label)
    j = 1
    worst, iw, prof = flux_deviation(a, om, i0, i1)
    e_ref = energy(a["Wh"][j][i0], 2)
    k0, sig0, cg0 = prof[i0]
    k1, sig1, cg1 = prof[i1]
    print("  %s: U %.3f -> %.3f m/s, k %.4f -> %.4f (sigma/omega %.4f -> %.4f), E/E_ref model %.4f"
          % (label, a["u"][j][i0], a["u"][j][i1], k0, k1, sig0 / om, sig1 / om,
             energy(a["Wh"][j][i1], 2) / e_ref))
    check(worst <= tol, "%s: action flux (c_g + U)E/sigma conserved from cell %d to %d (max relative "
          "difference %.2e at cell %d <= %.0e)" % (label, i0 + 1, i1 + 1, worst, iw + 1, tol))
    if label == "opp":
        e1 = energy(a["Wh"][j][0], 2)
        check(abs(e1 - energy(H0, 2)) <= 1e-5 * energy(H0, 2),
              "opp: the incident cell holds the offshore energy (E_1/E_0 - 1 = %.1e)" % (e1 / energy(H0, 2) - 1))
    # 流れなしの浅水変形だけの値との違い(ドップラー効果の大きさの記録)
    pr0 = flux_profile(a, om, j, cur=False)
    e_nc = e_ref * pr0[i0][2] / pr0[i1][2]
    print("  %s: E at cell %d is %.3f times the value without the current effect" % (label, i1 + 1,
          energy(a["Wh"][j][i1], 2) / e_nc))


def check_fol72(d40, d72):
    """順流のずれ(湧き出しの列の流れの屈折で隣のビンへ広がった分)は Δθ² に比例して小さくなる"""
    print("== fol72 (%s vs %s): the deviation on the following current converges as dtheta^2" % (d40, d72))
    om = 2.0 * math.pi / param_value("param_fol.txt", "wf_trep")
    w40 = flux_deviation(fields(d40), om, 2, 116)[0]
    w72 = flux_deviation(fields(d72), om, 2, 116)[0]
    n40 = 40
    n72 = int(param_value("param_fol72.txt", "wf_ntheta"))
    expect = (n72 / n40) ** 2
    check(w40 / w72 >= 0.8 * expect, "fol72: max relative difference %.2e with %d bins, %.2e with %d bins "
          "(ratio %.2f; (dtheta ratio)^2 = %.2f)" % (w40, n40, w72, n72, w40 / w72, expect))


def check_unst(d, dq):
    """非定常(静穏から)が準定常の解に達し、作用量 × ω の累積の台帳が流れの立ち上がりの間も閉じる"""
    print("== unst (%s vs %s): unsteady mode from calm on the opposing current" % (d, dq))
    a = read_bil(d, "Wh")
    b = read_bil(dq, "Wh")
    worst = max(abs(a[j][i] - b[j][i]) / b[j][i] for j in range(NY) for i in range(NX) if b[j][i] > 0.0)
    check(worst <= 1e-6, "unst: the unsteady run reaches the quasi-steady solution (max relative difference of "
          "the wave height %.1e <= 1e-6)" % worst)
    rows = read_csv("%s/wavefield.csv" % d)
    worst = 0.0
    for r in rows:
        inj = float(r["in_J"])
        if inj > 0.0:
            worst = max(worst, abs(float(r["imbalance_J"])) / inj)
    check(len(rows) >= 10 and worst <= 1e-9, "unst: the cumulative ledger (action x omega) closes in all %d rows "
          "while the current spins up from rest (max |imbalance|/in = %.1e <= 1e-9)" % (len(rows), worst))


def check_blk(d):
    print("== blk (%s): random waves blocked by an opposing current (param.txt)" % d)
    om = 2.0 * math.pi / param_value("param.txt", "wf_trep")
    a = fields(d)
    j = 1
    prof = flux_profile(a, om, j)
    ib = next((i for i in range(NX) if prof[i] is None), None)
    uniformity(a, "blk", ib if ib is not None else NX)
    hmax = max(a["Wh"][j])
    im = next((i for i in range(NX) if a["Wh"][j][i] < 0.1 * H0 and i > 0), None)
    check(ib is not None and im is not None and abs(im - ib) <= 1,
          "blk: blocking (no root on the branch or c_g + U <= 0) starts at cell %s, the wave height drops at "
          "cell %s" % (ib if ib is None else ib + 1, im if im is None else im + 1))
    rest = max(a["Wh"][j][i] for i in range(ib + 1, NX)) if ib is not None else 1.0
    check(rest <= 0.06 * H0, "blk: beyond the blocking point the wave height is at most %.4f m (<= 6%% of H_m0)"
          % rest)
    # 砕波が無視できる区間(上流)では作用量の流束の保存
    wb = read_bil(d, "Wb")
    wbmax = max(wb[j])
    i1 = max(i for i in range(ib) if wb[j][i] <= 1e-6 * wbmax)
    k, sig, cg = prof[0]
    flux = (cg + a["u"][j][0]) * energy(H0, 1) / sig
    worst = 0.0
    for i in range(i1 + 1):
        k, sig, cg = prof[i]
        pred = flux * sig / (cg + a["u"][j][i])
        worst = max(worst, abs(energy(a["Wh"][j][i], 1) - pred) / pred)
    check(worst <= 3e-3, "blk: action flux conserved upstream of breaking (cells 1-%d; max relative difference "
          "%.2e <= 3e-3)" % (i1 + 1, worst))
    print("  blk: maximum wave height %.4f m (%.2f H_m0) before the blocking point; breaking starts at cell %d"
          % (hmax, hmax / H0, i1 + 2))
    led = read_csv("%s/wavefield.csv" % d)[-1]
    vin = float(led["in_W"])
    brk = float(led["breaking_W"])
    blk = float(led["blocked_W"])
    imb = float(led["imbalance_W"])
    print("  blk: ledger in %.4g W, out %.4g W, breaking %.4g W, blocked %.4g W" % (vin, float(led["out_W"]), brk, blk))
    check(blk > 0.0, "blk: the blocked action flux is recorded in the ledger (blocked_W = %.3g W)" % blk)
    check(abs(imb) <= 1e-6 * vin, "blk: the ledger (action x omega) closes (imbalance %.1e of the inflow)" % (abs(imb) / vin))
    check(brk > blk, "blk: steepness-limited breaking on the opposing current removes most of the energy before "
          "the blocking point (breaking %.3g W > blocked %.3g W)" % (brk, blk))
    e1 = energy(a["Wh"][j][0], 1)
    check(abs(e1 / energy(H0, 1) - 1.0) <= 5e-3,
          "blk: the energy returning to the incident cell is small (E_1/E_0 - 1 = %.1e <= 5e-3)" % (e1 / energy(H0, 1) - 1))


def check_nocur(d, dref):
    print("== nocur (%s vs %s): without the effect of the current the waves are not blocked" % (d, dref))
    a = read_bil(d, "Wh")
    b = read_bil(dref, "Wh")
    j = 1
    check(a[j][110] >= 0.5 * H0 and b[j][110] < 0.1 * H0,
          "nocur: wave height at x = 553 m %.4f m without the current effect, %.4f m with it" % (a[j][110], b[j][110]))


def check_zero(d, doff):
    print("== zero (%s vs %s): with no flow, f_wf_current = 1 gives the W1 solution" % (d, doff))
    a = read_bil(d, "Wh")
    b = read_bil(doff, "Wh")
    diff = max(abs(a[j][i] - b[j][i]) for j in range(NY) for i in range(NX))
    check(diff == 0.0, "zero: wave heights identical to the output precision (max difference %.1e m)" % diff)


def check_river(d, dnc):
    print("== river (%s vs %s): the jet of a river mouth stops the waves from entering the river (V10)" % (d, dnc))
    nx, ny, dx = 120, 80, 2.5
    hm0 = param_value("param_river.txt", "wf_hm0")
    a = read_bil(d, "Wh", nx=nx, ny=ny)
    b = read_bil(dnc, "Wh", nx=nx, ny=ny)
    u = read_bil(d, "u", nx=nx, ny=ny)
    cells = [(i, j) for j in range(38, 42) for i in range(nx) if 20.0 <= (i + 0.5) * dx <= 80.0]
    hc = sum(a[j][i] for i, j in cells) / len(cells)
    hn = sum(b[j][i] for i, j in cells) / len(cells)
    uc = sum(u[j][i] for i, j in cells) / len(cells)
    print("  river: channel x = 20-80 m (mean current %.2f m/s): H %.4f m with the current effect, %.4f m without"
          % (uc, hc, hn))
    check(hn >= 0.2 * hm0, "river: without the current effect the waves propagate up the channel (H >= 0.2 H_m0)")
    check(hc <= 0.02 * hm0, "river: with the current effect the waves do not enter the channel (H <= 0.02 H_m0)")
    jet = max(a[j][i] for j in range(38, 42) for i in range(nx) if 100.0 <= (i + 0.5) * dx <= 200.0)
    off = max(b[j][i] for j in range(38, 42) for i in range(nx) if 100.0 <= (i + 0.5) * dx <= 200.0)
    print("  river: wave height on the jet (x = 100-200 m) %.3f m with the current effect, %.3f m without "
          "(steepening and focusing on an opposing current)" % (jet, off))
    check(jet > off, "river: the opposing jet increases the wave height")
    led = read_csv("%s/wavefield.csv" % d)[-1]
    check(float(led["blocked_W"]) > 0.0, "river: blocking is recorded in the ledger (%.3g W)" % float(led["blocked_W"]))


def main():
    mode = sys.argv[1]
    if mode == "opp":
        check_flux(sys.argv[2], "opp", 0, 114, 1e-5)
    elif mode == "fol":
        check_flux(sys.argv[2], "fol", 2, 116, 2e-4)
    elif mode == "fol72":
        check_fol72(sys.argv[2], sys.argv[3])
    elif mode == "unst":
        check_unst(sys.argv[2], sys.argv[3])
    elif mode == "blk":
        check_blk(sys.argv[2])
    elif mode == "nocur":
        check_nocur(sys.argv[2], sys.argv[3])
    elif mode == "zero":
        check_zero(sys.argv[2], sys.argv[3])
    elif mode == "river":
        check_river(sys.argv[2], sys.argv[3])
    else:
        sys.exit("unknown mode " + mode)
    if failed:
        print("=== Check_wfdoppler.py %s: FAIL (%d) ===" % (mode, len(failed)))
        sys.exit(1)
    print("=== Check_wfdoppler.py %s: PASS ===" % mode)


if __name__ == "__main__":
    main()
