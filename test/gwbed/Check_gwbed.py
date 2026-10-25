#!/usr/bin/env python3
# =====================================================================
# gwbed: 河床交換能(f_gwbed)の reference 非依存検定(developer.md §16.5)
#   gain  : 構成 1(param.txt)。堤内地(飽和)→ 河道の側方流入が上限
#           q_k = k_bed·l_k·h_e で律速される。
#             - Log の S_grnd が t >= 300 s で一定、かつ堤内地セルの Hg が
#               0.2 − (1 ステップ分の損失) に全桁一致(相対 1e-12)
#             - S_total = 1.2 不変(相対 1e-12)
#             - プローブ h の 100 s あたり増分: 河道 +2λ'·100、堤内地 −λ'·100
#               (λ' = k_bed·sd·(l_ax + l_diag)/A。プローブは 5 桁出力なので
#               絶対 2e-5 の許容)、河道 Hg = 0.2、堤内地 Hg = 0.1999
#   lined : 構成 2(param_lined.txt)。k_bed = 0 の遮断。河道の Hg = 0、
#           h = 1.2 が全時間で不変、S_grnd = 12×0.2/18 (t >= 300 s)
#   vert  : 構成 3(param_vert.txt)。鉛直浸透能の置き換え。
#           S_grnd(t) = (12 K_sv + 6 k_bed) t / 18 = 7e-6 t に全桁一致
#   使い方: python3 Check_gwbed.py {gain|lined|vert} <result dir>
# =====================================================================
import glob
import math
import os
import sys

mode, rdir = sys.argv[1], sys.argv[2]
rc = 0

# ---- 格子と係数(param.txt と同じ値。l_k は m_gwflow_lateral の幾何と同式) ----
dx = dy = 2.0
A = dx * dy
sd, sy = 1.0, 0.2
cap = sd * sy
r = 2.0 / (2.0 + math.sqrt(2.0))          # gw_diagratio(既定)
lp, ld = 1.0 - r, r / 2.0
l_ax = math.sqrt((lp * dy) ** 2)           # 軸方向の通過幅
l_diag = math.sqrt((ld * dy) ** 2 + (ld * dx) ** 2)   # 対角方向の通過幅
n_bank, n_chan, n_act = 12, 6, 18          # 堤内地・河道・有効セル数


def read_log(path):
    names, rows = None, []
    for line in open(path):
        if line.startswith("time,"):
            names = [s.strip() for s in line.split(",")]
            continue
        f = line.split()
        if names is None or len(f) < 5 or ":" not in f[0]:
            continue
        hh, mm, ss = f[0].split(":")
        t = int(hh) * 3600 + int(mm) * 60 + float(ss)
        rows.append((t, float(f[2]), float(f[3]), float(f[4])))   # t, S_surf, S_grnd, S_total
    return rows


def read_probe(path):
    rows = []
    for line in open(path):
        if line.startswith("#"):
            continue
        f = [float(x) for x in line.split(",")]
        rows.append((f[1] * 60.0, f[3], f[8]))                      # t(s), h, hg
    return rows


def chk(label, a, b, tol, scale=None):
    global rc
    scale = abs(b) if scale is None else scale
    ok = abs(a - b) <= tol * max(scale, 1e-300)
    print(f"  {label}: {a:.14e} vs {b:.14e} -> {'OK' if ok else 'NG'}")
    if not ok:
        rc = 1


log = read_log(os.path.join(rdir, "Log.txt"))
print(f"Check_gwbed {mode}: {rdir} ({len(log)} log rows, t_end = {log[-1][0]:.0f} s)")

if mode in ("gain", "lined"):
    k = (3600.0 if mode == "gain" else 0.0) / 1000.0 / 3600.0     # k_bed (m/s)
    dt = 0.25
    loss_step = k * sd * (l_ax + l_diag) * dt / A                  # 堤内地 1 セルの 1 ステップ損失 (m)
    hg_bank = cap - loss_step
    s_grnd = (n_bank * hg_bank + n_chan * (cap if mode == "gain" else 0.0)) / n_act
    for t, ssurf, sg, stot in log:
        chk(f"S_total(t={t:6.0f})", stot, 1.2, 1e-12)
        if t >= 300.0:
            chk(f"S_grnd (t={t:6.0f})", sg, s_grnd, 1e-12)
    pc = read_probe(os.path.join(rdir, "probes", "probe0001.csv"))   # 河道 (1,2)
    pb = read_probe(os.path.join(rdir, "probes", "probe0002.csv"))   # 堤内地 (1,1)
    rate_bank = -k * sd * (l_ax + l_diag) / A                        # 堤内地の dh/dt
    rate_chan = 2.0 * k * sd * (l_ax + l_diag) / A                   # 河道の dh/dt
    pc = [p for p in pc if p[0] >= 300.0]
    pb = [p for p in pb if p[0] >= 300.0]
    for (t0, h0, g0), (t1, h1, g1) in zip(pc[:-1], pc[1:]):
        chk(f"channel dh ({t0:4.0f}->{t1:4.0f} s)", h1 - h0, rate_chan * (t1 - t0), 2e-5, 1.0)
    for (t0, h0, g0), (t1, h1, g1) in zip(pb[:-1], pb[1:]):
        chk(f"bank    dh ({t0:4.0f}->{t1:4.0f} s)", h1 - h0, rate_bank * (t1 - t0), 2e-5, 1.0)
    for t, h, g in pc:
        chk(f"channel Hg (t={t:4.0f})", g, cap if mode == "gain" else 0.0, 1e-5, 1.0)
        if mode == "lined":
            chk(f"channel h  (t={t:4.0f})", h, 1.2, 1e-5, 1.0)
    for t, h, g in pb:
        chk(f"bank    Hg (t={t:4.0f})", g, hg_bank, 1e-5, 1.0)
elif mode == "vert":
    ksv = 36.0 / 1000.0 / 3600.0
    k = 3.6 / 1000.0 / 3600.0
    for t, ssurf, sg, stot in log:
        chk(f"S_grnd (t={t:6.0f})", sg, (n_bank * ksv + n_chan * k) * t / n_act, 1e-10, 7e-6 * 3600.0)
        chk(f"S_total(t={t:6.0f})", stot, 0.1, 1e-12)
else:
    print(f"usage: Check_gwbed.py {{gain|lined|vert}} <result dir> (got '{mode}')")
    rc = 2

print(f"Check_gwbed {mode}: {'PASS' if rc == 0 else 'FAIL'}")
sys.exit(rc)
