#!/usr/bin/env python3
# glacier 構成7: 谷の氷の流れの向きによる差(8 近傍の 9 点と塞がれた配分の振り替え。§99)
#   使い方: Check_chan.py(result_ch0w1・ch45w1・ch0w3・ch45w3・ch45w3q と Screen_ch*.log を読む)
#   Hi0000(初期)と Hi9998(最終)から、谷に沿う座標 s(0°: (i − 0.5)Δx、45°: (i + j − 1)Δx/√2)の
#   氷の体積の重心の移動距離 Δs̄ を求め、45° と 0° の比 R = Δs̄(45°)/Δs̄(0°) を判定する。
#   SIA の幅あたりの流量は氷厚と面の勾配だけで決まる(側壁の抵抗はモデルにない)ので、
#   谷の向きによらず R = 1 が正しい。
#     (1) 体積保存: 5 つの計算の画面の S_total の初値/終値の相対差 < TOL_VOL
#     (2) 1 本の谷 : |R − 1| < TOL_R1(4 近傍では斜めの 1 セル幅の谷はつながらず流れない)
#     (3) 3 本の谷 : |R − 1| < TOL_R3、4 近傍の対照(ch45w3q)は R < RQ3(検定がこの差を
#                    検出できること)
#   格子・定数は Make_input.py の (4) と param_ch*.txt と対で保守する
import math
import sys

DX = 50.0
CASES = {"ch0w1": "0", "ch45w1": "45", "ch0w3": "0", "ch45w3": "45", "ch45w3q": "45"}
TOL_VOL = 1.0e-12
TOL_R1, TOL_R3, RQ3 = 0.03, 0.05, 0.92


def read_field(fn):
    return [[float(w) for w in line.split()] for line in open(fn)]


def stotal(logname):
    vals = []
    for line in open(logname, encoding="utf-8", errors="replace"):
        w = line.split()
        # 行形式: time progress% S_surf S_grnd S_total progress% Runge ...(Check_halfar.py と同じ)
        if len(w) >= 5 and ":" in w[0] and w[1].endswith("%"):
            try:
                vals.append(float(w[4]))
            except ValueError:
                pass
    return vals


def shift(tag, ori):
    h0 = read_field(f"result_{tag}/Hi0000.txt")
    h1 = read_field(f"result_{tag}/Hi9998.txt")
    if ori == "0":
        sc = lambda i, j: (i - 0.5) * DX
    else:
        sc = lambda i, j: (i + j - 1) * DX / math.sqrt(2.0)

    def cent(h):
        v = sum(h[j][i] for j in range(len(h)) for i in range(len(h[0])))
        m = sum(h[j][i] * sc(i + 1, j + 1) for j in range(len(h)) for i in range(len(h[0])))
        return m / v
    return cent(h1) - cent(h0)


rc = 0
ds = {}
ok1 = True
for tag, ori in CASES.items():
    st = stotal(f"Screen_{tag}.log")
    if len(st) < 2:
        print(f"FAIL: could not parse S_total from Screen_{tag}.log")
        ok1 = False
        continue
    rel = abs(st[-1] - st[0]) / max(abs(st[0]), 1e-30)
    ok1 = ok1 and rel < TOL_VOL
    ds[tag] = shift(tag, ori)
    print(f"    {tag:7s}: 重心の移動 {ds[tag]:7.2f} m、S_total {st[0]:.15e} -> {st[-1]:.15e}(相対 {rel:.1e})")
print(f"(1) 体積保存: 5 つの計算で S_total の相対差 < {TOL_VOL:.0e} : {'PASS' if ok1 else 'FAIL'}")
if not ok1:
    rc = 1
if len(ds) == len(CASES):
    r1 = ds["ch45w1"] / ds["ch0w1"]
    r3 = ds["ch45w3"] / ds["ch0w3"]
    rq = ds["ch45w3q"] / ds["ch0w3"]
    ok2 = abs(r1 - 1.0) < TOL_R1
    print(f"(2) 1 本の谷 : R = {r1:.3f}(tol 1±{TOL_R1:.2f}。4 近傍では流れない) : {'PASS' if ok2 else 'FAIL'}")
    ok3 = abs(r3 - 1.0) < TOL_R3 and rq < RQ3
    print(f"(3) 3 本の谷 : R = {r3:.3f}(tol 1±{TOL_R3:.2f})、4 近傍の対照 R = {rq:.3f}(tol < {RQ3:.2f}) : "
          f"{'PASS' if ok3 else 'FAIL'}")
    if not (ok2 and ok3):
        rc = 1
else:
    rc = 1
sys.exit(rc)
