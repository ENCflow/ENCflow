#!/usr/bin/env python3
"""test/taupart の合否判定(急勾配礫床の抵抗分割 f_taupart。developer.md §89.30、mountain_stream_plan.md §14)
  1. 等流: 1500 s の結果の計測区間(x = X1〜X2)で、水深が Manning の等流水深に ±2 %、V·h が q に ±1 %、
     水深の変動係数 < 1 %(全構成)。
  2. 定常の流砂量: 各構成の 1500 s と 3000 s の東辺の開境界の台帳(固体 m³)の差を 1500 s で割った
     流砂量が、3000 s の結果の出口セル(開境界の面は自セルの水理で容量を出す)の h・V から同じ流砂量式で
     評価した容量 × 幅 1 m に ±0.5 %。τ* は既定(f_gravity_correction = 2)の斜面の倍率 (1 + S²)^{7/6} を含む。
     分割ありは τ* に φ(h/D84) = (1 + (a1/a2)² (h/D84)^(−5/3))^(−e/2)
     を掛ける(d0 は D84 = 2.2 d50 の既定、d19_mpm は MPM 式)。閾値未満の構成(d76)は台帳が 0。
     芦田・道上の有効掃流力(f_taupart = 2。te・te_cap。developer.md §121)は τ* を変えず、流砂量に
     (u*e/u*)^3 = min(1, h^(1/3) / (g n² D²))^(3/2)、D = 6.0 + 5.75 log10(h / (d50 (1 + 2τ*))) を掛ける
     (原典 式 (11)・(23)。閾値の 2 因子は全 τ*。g は実行ファイルの既定 9.8)。te_cap は u*e が u* を超えて
     頭打ち(係数 1)になる粗い礫(d50 = 0.08 m)。
     上流端の河床低下波が計測区間に届いていない(1500 s の区間の |Δz| < 5 mm)ことも確かめる。
使い方: python3 Check_taupart.py(Screen_<構成>[_t2].log と result[_<構成>][_t2]/ を読む)
"""
import glob, math, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, DX, S, N, Q_UNIT, H0, X1, X2, JC

D50, TSC, SG, G, T1, T2 = 0.01, 0.05, 1.65, 9.81, 1500.0, 3000.0
# f_gravity_correction = 2(既定)の流砂のせん断の倍率(developer.md §93): (1 + (V̂·∇z)²)(1 + |∇z|²)^{1/6}。
# 出口セルの勾配は片側差分で S、流れは下り向きなので (1 + S²)^{7/6}(2026-11-05 に既定が 2 になって追加)
FAC_G2 = (1.0 + S * S) ** (7.0 / 6.0)
A1, A2 = 6.5, 2.5
GG = 9.8            # 実行ファイルの重力加速度の既定(式 (11) の係数の評価に使う)
# 構成: (D84 [m]。None = 2.2 d50, e, 流砂量式, f_taupart, d50 [m])
CFG = [("off", None, 1.5, 1, 0, D50), ("d044", 0.044, 1.5, 1, 1, D50), ("d19", 0.19, 1.5, 1, 1, D50),
       ("d76", 0.76, 1.5, 1, 1, D50), ("d0", None, 1.5, 1, 1, D50), ("d19_mpm", 0.19, 1.5, 2, 1, D50),
       ("te", None, 1.5, 1, 2, D50), ("te_cap", None, 1.5, 1, 2, 0.08)]


def phi(x, e):
    return (1.0 + (A1 / A2) ** 2 * x ** (-5.0 / 3.0)) ** (-e / 2.0)


def te_factor(h, ts, d):
    """芦田・道上 (1972) 式 (11) の (u*e/u*)^3(マニング閉じ。u*e <= u* で頭打ち)"""
    den = 6.0 + 5.75 * math.log10(h / (d * (1.0 + 2.0 * ts)))
    if den <= 0.0:
        return 1.0
    r = h ** (1.0 / 3.0) / (GG * N ** 2 * den ** 2)
    return min(1.0, r) ** 1.5


def qbs(form, ts):
    if ts <= TSC:
        return 0.0
    if form == 1:
        return 17.0 * ts ** 1.5 * (1.0 - TSC / ts) * (1.0 - math.sqrt(TSC / ts))
    return 8.0 * (ts - TSC) ** 1.5


def last_file(resdir, prefix):
    fs = sorted(glob.glob(os.path.join(resdir, prefix + "[0-9][0-9][0-9][0-9].txt")))
    fs = [f for f in fs if int(f[-8:-4]) < 9000] + [f for f in fs if int(f[-8:-4]) == 9998]
    return fs[-1]


def ledger(logfile):
    pat = re.compile(r"open boundaries \(out - in\)\s+(\S+) m3")
    v = None
    for line in open(logfile, encoding="utf-8", errors="replace"):
        m = pat.search(line)
        if m:
            v = float(m.group(1))
    if v is None:
        sys.exit("FAIL: open-boundary ledger line not found in %s" % logfile)
    return v


def main():
    ok = True
    i1, i2 = int(X1 / DX), int(X2 / DX)
    print("%-8s %7s %7s %7s %8s %8s %10s %10s %8s" % ("config", "h/hn", "Vh/q", "h_out", "tau*", "factor", "rate", "expected", "ratio"))
    for name, d84, e, form, mode, d50 in CFG:
        r1 = "result" if name == "off" else "result_" + name
        r2 = r1 + "_t2"
        h = np.loadtxt(last_file(r1, "H"))[JC - 1, i1:i2]
        v = np.loadtxt(last_file(r1, "V"))[JC - 1, i1:i2]
        hm, vm = h.mean(), v.mean()
        if abs(hm / H0 - 1.0) > 0.02 or abs(vm * hm / Q_UNIT - 1.0) > 0.01 or h.std() / hm > 0.01:
            print("FAIL: %s is not uniform flow (h/hn %.4f, Vh/q %.4f, std/mean %.4f)" % (name, hm / H0, vm * hm / Q_UNIT, h.std() / hm)); ok = False
        ho = np.loadtxt(last_file(r2, "H"))[JC - 1, NX - 1]
        vo = np.loadtxt(last_file(r2, "V"))[JC - 1, NX - 1]
        # 上流端(無給砂)の河床低下波が計測区間に届いていないこと(1500 s の区間の |Δz| < 5 mm)。
        # 出口セル自身は自由流出境界の性質(§89.22)で 3000 s に 3 cm ほど下がるが、容量は出口セルの
        # その時点の h・V で評価するので判定には影響しない
        dz = (np.loadtxt(last_file(r1, "Z")) - np.loadtxt(os.path.join(r1, "Z0000.txt")))[JC - 1, i1:i2]
        if np.abs(dz).max() > 0.005:
            print("FAIL: %s: the bed of the measuring section moved (max |dz| %.4f m): the degradation wave reached it" % (name, np.abs(dz).max())); ok = False
        rate = (ledger("Screen_%s_t2.log" % name) - ledger("Screen_%s.log" % name)) / (T2 - T1)
        ts = N ** 2 * vo ** 2 / (SG * d50 * ho ** (1.0 / 3.0)) * FAC_G2
        f = phi(ho / (d84 if d84 else 2.2 * d50), e) if mode == 1 else 1.0
        fe = te_factor(ho, ts, d50) if mode == 2 else 1.0
        qb = qbs(form, f * ts) * math.sqrt(SG * G * d50 ** 3) * 1.0 * fe   # 幅 1 m の固体流砂量 (m3/s)
        print("%-8s %7.4f %7.4f %7.4f %8.4f %8.4f %10.6f %10.6f %8.4f" % (name, hm / H0, vm * hm / Q_UNIT, ho, f * ts, f * fe, rate, qb, rate / qb if qb > 0 else float("nan")))
        if mode == 2 and name == "te" and not (0.2 < fe < 0.6):
            print("FAIL: te: the eq. (11) factor %.4f is outside the expected range (0.2, 0.6)" % fe); ok = False
        if mode == 2 and name == "te_cap" and fe != 1.0:
            print("FAIL: te_cap: the eq. (11) factor %.4f should be capped at 1" % fe); ok = False
        if qb == 0.0:
            if rate != 0.0:
                print("FAIL: %s: phi tau* = %.4f < tau*c but the ledger rate is %g" % (name, f * ts, rate)); ok = False
            else:
                print("PASS: %s: phi tau* = %.4f < tau*c, no bed load" % (name, f * ts))
        elif abs(rate / qb - 1.0) > 0.005:
            print("FAIL: %s: steady rate / formula = %.4f (expected 1 +- 0.005)" % (name, rate / qb)); ok = False
        else:
            print("PASS: %s: steady rate / formula = %.4f" % (name, rate / qb))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
