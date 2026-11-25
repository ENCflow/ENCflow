#!/usr/bin/env python3
# vchannel: 一様な V 字水路の流れの横断分布を、厳密解と比べる
#   使い方: Check_vchannel.py        (result_<構成>_<向き>/ を読む。地形・定数は make_init.py と対で保守する)
#
# 区間の中央(両端からの希薄波が届かない所)は流れの向きに一様で、流動深 h(n) が変わらず、横断方向の流れもない
# ので、各列の流速は自分の流動深だけで決まる(横断方向の応力のない抵抗則の厳密解。独自の整理):
#   Voellmy 則   du/dt = g (S − μ) − g u² / (ξ h)      →  u = u_t tanh(g (S − μ) t / u_t)、 u_t = sqrt(ξ h (S − μ))
#   マニング則   du/dt = g S − g n² u² / h^(4/3)        →  u = u_n tanh(g S t / u_n)、       u_n = h^(2/3) S^(1/2) / n
# 指標は、区間の中央の流量 Q = Σ h u_s(u_s は沢筋方向の流速の成分)の、厳密解との比。流れの向きを格子に対して
# 0°・22.5°・45° に回して、比が向きによらないことも見る。
#
# 判定(許容幅は、5 m 格子の計算の値に 2〜3 % の余裕を足したもの。README の表):
#   (1) 摩擦なし: 最初の 1 秒の沢筋方向の加速度が g S(流速 ÷ g S t が 0.96〜1.01。1 ステップ遅れの分 0.975 が下限の側)
#   (2) 4 近傍・格子に沿う向き: 流量が厳密解の ±2 % 以内(横断方向の結合がない計算。検定の組み方の確認)
#   (3) Voellmy 則・既定: 流量の比が 0.86〜1.02、向きによる幅が 10 % 以内
#   (4) Voellmy 則・f_opening_dynamic = 0: 流量の比が 0.86〜1.00、向きによる幅が 5 % 以内
#   (5) 水・既定: 流量の比が 0.80〜1.00、向きによる幅が 4 % 以内
import math
import os
import struct
import sys

import make_init as M

N, DX = M.N, M.DX
WIN = (-150.0, 100.0)                  # 流量を取る区間(20 秒後に一様な範囲) s (m)
WIN_FR = (-400.0, -200.0)              # 摩擦なしの構成(1 秒後)
NCORE = 7.5                            # 摩擦なしの構成で流速を平均する幅 |n| (m)
TOL = {"fr": (0.96, 1.01), "n4": 0.02,
       "vo": (0.86, 1.02, 0.10), "vo0": (0.86, 1.00, 0.05), "w": (0.80, 1.00, 0.04)}


def last_output(rdir):
    """最後の分布出力の (番号, 時刻)。"""
    k, t = None, None
    for line in open(os.path.join(rdir, "FILENUMBER.csv")):
        if line.startswith("#"):
            continue
        f = line.split(",")
        if int(f[0]) < 9000:
            k, t = int(f[0]), float(f[2])
    return k, t


def read_bil(rdir, name, k):
    """分布出力(float32。先頭の行が北端)を、セル (i, j)(j は北向き)の辞書引きできる関数で返す。"""
    with open(os.path.join(rdir, "%s%04d.bil" % (name, k)), "rb") as f:
        a = struct.unpack("<%df" % (N * N), f.read(4 * N * N))
    return lambda i, j: a[(N - 1 - j) * N + i]


def u_exact(h, t, cfg):
    if h <= 0.0:
        return 0.0
    if cfg.startswith("w"):
        ut = h ** (2.0 / 3.0) * math.sqrt(M.S) / M.RN
        return ut * math.tanh(M.GG * M.S * t / ut)
    mu, xi = (1.0e-4, 1.0e9) if cfg == "fr" else (M.MU, M.XI)
    acc = M.GG * (M.S - mu)
    ut = math.sqrt(xi * h * (M.S - mu))
    return ut * math.tanh(acc * t / ut)


def measure(cfg, name, theta):
    """区間の中央の (流量の比, 中央の流速の比, 流れの幅 m, 時刻)。摩擦なしの構成は中央の流速の比だけ。"""
    rdir = "result_%s_%s" % (cfg, name)
    k, t = last_output(rdir)
    h = read_bil(rdir, "H", k)
    hs = read_bil(rdir, "Hs", k) if not cfg.startswith("w") else (lambda i, j: 0.0)
    u, v = read_bil(rdir, "u", k), read_bil(rdir, "v", k)
    c, si = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    s1, s2 = WIN_FR if cfg == "fr" else WIN
    q, qe, qc, qce, us_sum, ue_sum, nc, wet = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0
    for j in range(N):
        y = (j + 0.5) * DX - M.LDOM / 2
        for i in range(N):
            x = (i + 0.5) * DX - M.LDOM / 2
            s, n = x * c + y * si, -x * si + y * c      # make_init.py の sn と同じ
            if s < s1 or s > s2 or abs(n) > 60.0:
                continue
            d = h(i, j) + max(hs(i, j), 0.0)
            us = u(i, j) * c - v(i, j) * si      # 出力の v は南向きが正
            h0 = max(M.D - M.zc(n), 0.0)
            ue = u_exact(h0, t, cfg)
            q += d * us
            qe += h0 * ue
            if d > 0.05:
                wet += 1
            if abs(n) < NCORE:
                qc += d * us
                qce += h0 * ue
                us_sum += us
                ue_sum += ue
                nc += 1
    width = wet * DX * DX / (s2 - s1)
    return q / qe, us_sum / ue_sum, width, t


def collect():
    """全構成の指標 {(構成, 向き): (流量の比, 中央の流速の比, 流れの幅, 時刻)}。"""
    res = {}
    for cfg, (_tmpl, _mods, oris) in M.CONFIGS.items():
        for name in oris:
            res[(cfg, name)] = measure(cfg, name, dict(M.THETAS)[name])
    return res


def main():
    ok_all = True
    res = collect()

    # (1) 摩擦なし: 加速度
    lo, hi = TOL["fr"]
    for name, theta in M.THETAS:
        r = res[("fr", name)][1]
        ok = lo <= r <= hi
        print("(1) 摩擦なし %5.1f°: 1 秒後の沢筋方向の流速 ÷ g S t = %.4f(%.2f〜%.2f) : %s"
              % (theta, r, lo, hi, "PASS" if ok else "FAIL"))
        ok_all = ok_all and ok

    # (2) 4 近傍・格子に沿う向き
    for cfg, label in (("vo4", "Voellmy 則"), ("w4", "水       ")):
        r = res[(cfg, "r0")][0]
        ok = abs(r - 1.0) <= TOL["n4"]
        print("(2) 4 近傍・0° %s: 流量 ÷ 厳密解 = %.4f(±%.2f) : %s" % (label, r, TOL["n4"], "PASS" if ok else "FAIL"))
        ok_all = ok_all and ok

    # (3)〜(5) 8 近傍: 流量の比と、向きによる幅
    for no, cfg, label in ((3, "vo", "Voellmy 則・既定               "),
                           (4, "vo0", "Voellmy 則・f_opening_dynamic = 0"),
                           (5, "w", "水・既定                       ")):
        lo, hi, spread = TOL[cfg]
        rs = [res[(cfg, name)] for name, _ in M.THETAS]
        qs = [r[0] for r in rs]
        ok = all(lo <= q <= hi for q in qs)
        print("(%d) %s: 流量 ÷ 厳密解 = %s(0°・22.5°・45°。%.2f〜%.2f) : %s"
              % (no, label, "・".join("%.4f" % q for q in qs), lo, hi, "PASS" if ok else "FAIL"))
        ok_all = ok_all and ok
        sp = (max(qs) - min(qs)) / (sum(qs) / len(qs))
        ok = sp <= spread
        print("      向きによる幅 (最大 − 最小)/平均 = %.4f(%.2f 以内)、中央の流速の比 %s、流れの幅 %s m : %s"
              % (sp, spread, "・".join("%.3f" % r[1] for r in rs), "・".join("%.0f" % r[2] for r in rs),
                 "PASS" if ok else "FAIL"))
        ok_all = ok_all and ok

    print("== vchannel(一様な V 字水路の厳密解)検定: %s ==" % ("PASS" if ok_all else "FAIL"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
