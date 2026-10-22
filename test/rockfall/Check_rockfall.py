#!/usr/bin/env python3
# rockfall の検定(developer.md §87)
#   漸化式の独立実装で Z9998 / Sd9998(bil, float32)を再現し、岩の体積の保存を見る。
#   使い方: Check_rockfall.py <resultdir> [rtol]
import sys, numpy as np

NX = NY = 21
DX = 2.0
SD0 = 0.001
PHI, RELAX, BULK, NSTEP = 45.0, 1.0, 1.5, 10        # param.txt と対で保守する
NB = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]   # (di, dj) k=1..8(m_geomorph の din/djn)

def read_bil(fn):
    a = np.fromfile(fn, dtype="<f4")
    return a.reshape(NY, NX).astype(np.float64)

rdir = sys.argv[1]
rtol = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0e-6
z = np.loadtxt("data_rockfall/zpillar.txt")
sd = np.full_like(z, SD0)
z0 = z.copy()
tanphi = np.tan(np.radians(PHI))
fac = RELAX / (1.0 + BULK) / 8.0
for _ in range(NSTEP):
    qr = np.zeros((NY, NX, 8))
    zb = z - sd
    for j in range(NY):
        for i in range(NX):
            for k, (di, dj) in enumerate(NB):
                jn, i_n = j + dj, i + di
                if not (0 <= jn < NY and 0 <= i_n < NX):
                    continue
                dist = DX * (np.sqrt(2.0) if di != 0 and dj != 0 else 1.0)
                dzc = zb[j, i] - z[jn, i_n] - tanphi * dist
                if dzc > 0.0:
                    qr[j, i, k] = fac * dzc
    out = qr.sum(axis=2)
    vin = np.zeros((NY, NX))
    for k, (di, dj) in enumerate(NB):
        kk = 7 - k                                   # 近傍の「自分向き」成分(9−k の 0 始まり)
        for j in range(NY):
            for i in range(NX):
                jn, i_n = j + dj, i + di
                if 0 <= jn < NY and 0 <= i_n < NX:
                    vin[j, i] += qr[jn, i_n, kk]
    z = z - out + BULK * vin
    sd = sd + BULK * vin

znum = read_bil(rdir + "/Z9998.bil")
sdnum = read_bil(rdir + "/Sd9998.bil")
ok = True
for lab, num, ana in (("z", znum, z), ("sd", sdnum, sd)):
    err = np.abs(num - ana).max()
    tol = rtol * max(np.abs(ana).max(), 1.0)
    good = err <= tol
    ok &= good
    print("rockfall: max|%s_num - %s_ana| = %.3e (tol %.1e)  %s" % (lab, lab, err, tol, "PASS" if good else "FAIL"))
vrock = (z0 - z).sum() * DX * DX / (BULK - 1.0) * -1.0   # Σ Δz = (bulk − 1) V_rock(Δz = z − z0)
vrock = (z - z0).sum() * DX * DX / (BULK - 1.0)
vsd = (sd - SD0).sum() * DX * DX / BULK
print("rockfall: rock volume from dz = %.6f m3, from sd = %.6f m3, peak %.4f -> %.4f m  %s"
      % (vrock, vsd, z0.max(), z.max(), "PASS" if abs(vrock - vsd) <= 1e-9 * max(vrock, 1.0) else "FAIL"))
ok &= abs(vrock - vsd) <= 1e-9 * max(vrock, 1.0)
# 数値側の保存(float32 の丸め内)
vz = (znum - z0).sum() * DX * DX / (BULK - 1.0)
vs = (sdnum - SD0).sum() * DX * DX / BULK
good = abs(vz - vs) <= 1e-4 * max(vs, 1.0)
ok &= good
print("rockfall: numerical rock volume from dz = %.6f m3, from sd = %.6f m3  %s" % (vz, vs, "PASS" if good else "FAIL"))
print("== rockfall: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
