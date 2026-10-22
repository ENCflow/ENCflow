#!/usr/bin/env python3
# wave_shore 検定(developer.md §84.15、docs/wave_plan.md §7)
#   一様勾配の水没した海浜(北が浅い。水位 0)に正弦波状の等深線の擾乱 η = a sin(kx)
#   (a = 6 m、L = 200 m)を置き、沖波 H0 = 0.5 m・T = 5 s を北向きから α だけ振った向きで
#   与える。Ashton & Murray (2006) の線形理論では、汀線(等深線)の擾乱は
#     ∂η/∂t = D ∂²η/∂x²、 D = Q_s'(α)/h_b、
#     Q_s'(α) = K2 H0^{12/5} T^{1/5} cos^{1/5}α (cos²α − 1.2 sin²α)
#   で拡散(|α| < 42°)または成長(高角)する。h_b は砕波水深(Komar & Gaughan の H_b / γ)。
#     (1) low(α = 20°): 中央 2 波長(x = 200〜600 m)の h = 0.5 m 等深線の振幅 a(t) が
#         exp(−D k² t) で減衰し、測った減衰率が理論の D k² に ±TOL_D(端の遮蔽・壁の影響と
#         砕波帯の離散化を許容)
#     (2) high(α = 60°): 反拡散 = 全波長が不安定で最短の波長が最も速く育つため、L = 200 m の
#         正弦波の振幅ではなく汀線の凹凸(砕波帯の沖側の等深線 h = 0.8 m の位置の標準偏差。
#         測定区間、nan 除外)で見る: high で初期の RUG_GROW 倍以上に増え、low では増えない
#     (3) 保存: Σ(z − z0) が 0(閉領域。印字精度 1e-4 × セル数の丸めを許容)
#     (4) 乾いたセルなし・海域マスクなしなので陸の不変は対象外。無効時のビット一致は
#         Run.sh が cmp で見る(off と nowave)
import sys, os, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, DX, YL, S, A, L

H0, T, K2, GAMMA, G = 0.5, 5.0, 0.34, 0.78, 9.8
MORFAC, DT_FILE = 5.0, 1800.0
TOL_D = 0.35
RUG_GROW = 1.5
HC2 = 0.8                    # 凹凸を測る等深線(砕波帯の沖側)
HC = 0.5                     # 測る等深線の水深 (m)
X1, X2 = 200.0, 600.0        # 測定区間(中央 2 波長。両端 1 波長は壁と遮蔽の影響域)

def qs_prime(alpha):
    c, s = math.cos(alpha), math.sin(alpha)
    return K2 * H0 ** 2.4 * T ** 0.2 * c ** 0.2 * (c * c - 1.2 * s * s)

HB = 0.39 * G ** 0.2 * (T * H0 ** 2) ** 0.4 / GAMMA
k = 2 * math.pi / L
x = (np.arange(NX) + 0.5) * DX
y = (np.arange(NY) + 0.5) * DX
sel = (x >= X1) & (x < X2)

def contour_amplitude(z):
    """各列で水深 HC(= −z)を横切る y を線形補間で求め、中央区間で sin(kx) に射影した振幅"""
    h = -z
    yc = np.full(NX, np.nan)
    for i in range(NX):
        col = h[:, i]
        j = np.argmax(col >= HC)
        if j == 0: continue
        f = (HC - col[j - 1]) / (col[j] - col[j - 1])
        yc[i] = y[j - 1] + f * (y[j] - y[j - 1])
    yy = yc[sel]; xx = x[sel]
    yy = yy - np.nanmean(yy)
    a_s = 2.0 * np.nansum(yy * np.sin(k * xx)) / sel.sum()
    a_c = 2.0 * np.nansum(yy * np.cos(k * xx)) / sel.sum()
    return math.hypot(a_s, a_c), a_s

ok = True
# (1) low: 減衰率
z0 = np.loadtxt("result_low/Z0000.txt")
amps = []
for n in range(0, 3):
    z = np.loadtxt("result_low/Z%04d.txt" % n)
    amp, a_s = contour_amplitude(z)
    amps.append((n * DT_FILE * MORFAC, amp, a_s))
t = np.array([a[0] for a in amps]); a = np.array([a[1] for a in amps])
rate = -np.polyfit(t, np.log(a), 1)[0]
D_th = qs_prime(math.radians(20.0)) / HB
rate_th = D_th * k * k
g1 = abs(rate / rate_th - 1.0) < TOL_D and all(np.diff(a) < 0)
print("(1) low α=20°: 等深線 %.1f m の振幅 a(t) = %s m (t = %s h), 減衰率 %.3e /s, 理論 D k² = %.3e /s (D = %.4f m²/s, h_b = %.3f m), 比 %.2f (±%.0f%%) : %s"
      % (HC, np.round(a, 2), np.round(t / 3600, 1), rate, rate_th, D_th, HB, rate / rate_th, 100 * TOL_D, "PASS" if g1 else "FAIL"))
ok = ok and g1

# (2) high: 汀線の凹凸(等深線 HC2 の位置の標準偏差)が増える。low では増えない
def rugosity(z):
    h = -z
    yc = np.full(NX, np.nan)
    for i in range(NX):
        col = h[:, i]
        j = np.argmax(col >= HC2)
        if j == 0: continue
        f = (HC2 - col[j - 1]) / (col[j] - col[j - 1])
        yc[i] = y[j - 1] + f * (y[j] - y[j - 1])
    return float(np.nanstd(yc[sel]))
r0h = rugosity(np.loadtxt("result_high/Z0000.txt")); r2h = rugosity(np.loadtxt("result_high/Z0002.txt"))
r0l = rugosity(np.loadtxt("result_low/Z0000.txt")); r2l = rugosity(np.loadtxt("result_low/Z0002.txt"))
g2 = r2h > RUG_GROW * r0h and r2l <= r0l
print("(2) 凹凸(等深線 %.1f m の位置の標準偏差): high α=60° %.1f → %.1f m (> %.1f 倍), low α=20° %.1f → %.1f m (増えない) : %s"
      % (HC2, r0h, r2h, RUG_GROW, r0l, r2l, "PASS" if g2 else "FAIL"))
ok = ok and g2

# (3) 保存
for tag in ("low", "high"):
    zz = np.loadtxt("result_%s/Z0002.txt" % tag)
    dz = (zz - np.loadtxt("result_%s/Z0000.txt" % tag)).sum() * DX * DX
    tol = 1.0e-4 * NX * NY * DX * DX * 0.5
    g3 = abs(dz) < tol
    print("(3) %s 体積保存: Σ(z − z0) dA = %.2f m³ (印字精度の許容 %.1f m³) : %s" % (tag, dz, tol, "PASS" if g3 else "FAIL"))
    ok = ok and g3

print("== wave_shore 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
