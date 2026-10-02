#!/usr/bin/env python3
"""直線水路と折れ線水路の定常水深を路長に沿って比較し、屈曲 1 回あたりの
損失水頭を求める。

  python3 Check_bendloss.py [suffix ...]
    suffix は結果ディレクトリの接尾辞("" = result_straight / result_zigzag、
    "_s3" = スキーム 3、"_h2" = f_hcap_upwind=2 など)。
最終出力(t = tt)の H, m, n を path_*.csv の路上セルで読む。
  - 等流水深 h_n(Manning)との比較
  - 直線区間ごとの平均水深(区間中央 40 セル)
  - 屈曲損失 = 折れ線の水面標高 − 直線の水面標高 を路長で比べ、
    屈曲 1 回あたりの段差を速度水頭 u²/2g で無次元化(損失係数 K)
"""
import csv, glob, math, os, re, sys
G, DX, S, N, Q = 9.8, 10.0, 0.005, 0.03, 4.0
hn = (Q * N / math.sqrt(S)) ** 0.6
un = Q / hn

def last(d, pre):
    fs = sorted(f for f in glob.glob(os.path.join(d, pre + "[0-9][0-9][0-9][0-9].txt"))
                if int(re.findall(r"(\d{4})\.txt", f)[0]) < 9000)
    return [[float(v) for v in l.split()] for l in open(fs[-1]) if l.strip()]

def profile(kind, suf):
    d = f"result_{kind}{suf}"
    H = last(d, "H"); M = last(d, "m"); Nn = last(d, "n")
    path = list(csv.DictReader(open(f"path_{kind}.csv")))
    s, h, q, z = [], [], [], []
    for r in path:
        i, j, k = int(r["i"]) - 1, int(r["j"]) - 1, int(r["k"])
        s.append(k * DX); h.append(H[j][i]); q.append(math.hypot(M[j][i], Nn[j][i]))
        z.append(100.0 - S * DX * k)
    return s, h, q, z

sufs = sys.argv[1:] or [""]
print("Manning uniform flow: h_n = %.3f m, u = %.3f m/s, u^2/2g = %.3f m, Fr = %.2f"
      % (hn, un, un**2 / (2*G), un / math.sqrt(G*hn)))
for suf in sufs:
    print("=== variant '%s'" % (suf or "default"))
    try:
        ss, hs, qs, zs = profile("straight", suf); sz, hz, qz, zz = profile("zigzag", suf)
    except (IndexError, FileNotFoundError) as e:
        print("  missing results:", e); continue
    # 区間平均(各 80 セル区間の中央 40 セル = k 20..59 相対)
    print("  reach  straight h   zigzag h   dh(m)   |  q straight  q zigzag")
    reach_dh = []
    for r in range(5):
        k0 = r * 80 + 20; k1 = r * 80 + 60
        a = sum(hs[k0:k1]) / 40; b = sum(hz[k0:k1]) / 40
        qa = sum(qs[k0:k1]) / 40; qb = sum(qz[k0:k1]) / 40
        reach_dh.append(b - a)
        print("  %5d  %9.3f  %9.3f  %7.3f   |  %9.3f  %9.3f" % (r + 1, a, b, b - a, qa, qb))
    # 屈曲 1 回あたりの損失: 上流側区間 r と下流側区間 r+1 の水深差の差分
    # (折れ線の水面は各屈曲で段差を持ち、上流ほど高い。直線との差 dh を
    #  区間ごとに取り、隣接区間の差 dh(r) - dh(r+1) が屈曲 r の損失水頭)
    print("  bend   head loss (m)   K = loss/(u^2/2g)")
    for r in range(4):
        loss = reach_dh[r] - reach_dh[r + 1]
        print("  %4d   %12.3f   %8.2f" % (r + 1, loss, loss / (un**2 / (2*G))))
    print("  mean depth over reaches 1-4: straight %.3f (h_n %.3f), zigzag %.3f"
          % (sum(hs[20:300]) / 280, hn, sum(hz[20:300]) / 280))
