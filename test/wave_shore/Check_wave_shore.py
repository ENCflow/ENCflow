#!/usr/bin/env python3
# wave_shore 検定(developer.md §84.15、docs/wave_plan.md §7)
#   一様勾配 0.02 の海浜(北が乾いた浜、汀線 y = 20 m)に正弦波状の汀線の擾乱 η = a sin(kx)
#   (a = 6 m、L = 200 m)を置き、沖波 H0 = 0.5 m・T = 5 s を北向きから α だけ振った向きで
#   与える。Ashton & Murray (2006) の線形理論では、汀線(等深線)の擾乱は
#     ∂η/∂t = D ∂²η/∂x²、 D = Q_s'(α)/h_b、
#     Q_s'(α) = K2 H0^{12/5} T^{1/5} cos^{1/5}α (cos²α − 1.2 sin²α)
#   で拡散(|α| < 42°)または成長(高角)する。h_b は砕波水深(Komar & Gaughan の H_b / γ)。
#   汀線方位の平滑化は物理長 wave_lsm = 5 m(= 2Δx)の多パス核+局所勾配項(段 3 (a))。
#     (1) low(α = 20°): 中央 2 波長(x = 200〜600 m)の h = 0.5 m 等深線の振幅 a(t) が
#         exp(−D k² t) で減衰し、測った減衰率が理論の D k² に ±TOL_D
#     (2) high(α = 60°): 同じ振幅が exp(+|D| k² t) で育ち、成長率が理論の |D| k² の
#         RATIO_LO〜RATIO_HI 倍。かつ砕波帯沖側の等深線(h = 0.8 m)の凹凸のスペクトルで
#         波長 10 m 未満のパワーが PSMALL_MAX % 未満(格子スケールの砂州が無い)
#     (2b) high0(高角、従来のセル半径の核 wave_lsm = 0): 同じパワーが PSMALL_MIN % 以上
#         (格子スケールの砂州が育つ = 物理長の平滑化が要ることの記録)
#     (3) 保存: Σ(z − z0) が 0(閉領域。印字精度 1e-4 × セル数の丸めを許容)
#     (4) 無効時のビット一致は Run.sh が cmp で見る(off と nowave)
#     (5) bar / bar0(直線汀線の沖の非侵食の水没砂州 = 離岸堤。段 3 (b) の部分遮蔽 f_wave_shadow):
#         遮蔽ありで陰の中央(x = 360〜440 m、汀線から 25 m)の地形変化(Σ|Δz|)が遮蔽なしの
#         LEE_QUIET 倍以下(陰が休む)、陰の風上側の縁(x = 440〜500 m)の堆積が UP_RATIO 倍以上、
#         風下側(x = 250〜350 m)の侵食が DOWN_RATIO 倍以上(回折が無いので砂は陰の中央でなく
#         風上側の縁に溜まる。一線モデルの離岸堤と同じ型)
import sys, os, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import NX, NY, DX, YL, S, A, L

H0, T, K2, GAMMA, G = 0.5, 5.0, 0.34, 0.78, 9.8
MORFAC, DT_FILE = 5.0, 1800.0
TOL_D = 0.35
RATIO_LO, RATIO_HI = 0.5, 1.5   # (2) 高角の成長率の理論比の範囲(実測 0.86)
PSMALL_MAX, PSMALL_MIN = 15.0, 20.0   # (2) 波長 10 m 未満のパワー (%)。実測: 物理長 6 %、従来核 30 %
HC2 = 0.8                    # 凹凸を測る等深線(砕波帯の沖側)
LEE_QUIET, UP_RATIO, DOWN_RATIO = 0.5, 1.5, 1.5   # (5) 実測: 陰の中央 0.21、風上の縁 4.3、風下 2.6
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

# (2) high: 振幅の成長率と、凹凸のスペクトル(格子スケールのパワー)
def small_power(z):
    h = -z
    yc = np.full(NX, np.nan)
    for i in range(NX):
        col = h[:, i]
        j = np.argmax(col >= HC2)
        if j == 0: continue
        f = (HC2 - col[j - 1]) / (col[j] - col[j - 1])
        yc[i] = y[j - 1] + f * (y[j] - y[j - 1])
    yy = yc[sel]; yy = np.where(np.isnan(yy), np.nanmean(yy), yy); yy = yy - yy.mean()
    F = np.abs(np.fft.rfft(yy)) ** 2; kk = np.fft.rfftfreq(len(yy), d=DX)
    lam = np.where(kk > 0, 1.0 / np.maximum(kk, 1e-12), np.inf); F[0] = 0.0
    return 100.0 * F[lam < 10.0].sum() / F.sum(), float(yy.std())
ah = []
for n in range(0, 3):
    amp, a_s = contour_amplitude(np.loadtxt("result_high/Z%04d.txt" % n))
    ah.append(amp)
ah = np.array(ah)
rate_h = -np.polyfit(t, np.log(ah), 1)[0]
rate_h_th = qs_prime(math.radians(60.0)) / HB * k * k
ratio_h = rate_h / rate_h_th
ps_h, sd_h = small_power(np.loadtxt("result_high/Z0002.txt"))
g2 = RATIO_LO < ratio_h < RATIO_HI and all(np.diff(ah) > 0) and ps_h < PSMALL_MAX
print("(2) high α=60°: 振幅 a(t) = %s m, 成長率 %.3e /s, 理論 |D| k² = %.3e /s, 比 %.2f (%.1f〜%.1f); 凹凸(等深線 %.1f m)の波長 10 m 未満のパワー %.0f%% (< %.0f%%) : %s"
      % (np.round(ah, 2), -rate_h, -rate_h_th, ratio_h, RATIO_LO, RATIO_HI, HC2, ps_h, PSMALL_MAX, "PASS" if g2 else "FAIL"))
ok = ok and g2
ps_h0, sd_h0 = small_power(np.loadtxt("result_high0/Z0002.txt"))
g2b = ps_h0 >= PSMALL_MIN
print("(2b) high0(従来のセル半径の核): 波長 10 m 未満のパワー %.0f%% (>= %.0f%%。格子スケールの砂州が育つ) : %s"
      % (ps_h0, PSMALL_MIN, "PASS" if g2b else "FAIL"))
ok = ok and g2b

# (3) 保存
for tag in ("low", "high"):
    zz = np.loadtxt("result_%s/Z0002.txt" % tag)
    dz = (zz - np.loadtxt("result_%s/Z0000.txt" % tag)).sum() * DX * DX
    tol = 1.0e-4 * NX * NY * DX * DX * 0.5
    g3 = abs(dz) < tol
    print("(3) %s 体積保存: Σ(z − z0) dA = %.2f m³ (印字精度の許容 %.1f m³) : %s" % (tag, dz, tol, "PASS" if g3 else "FAIL"))
    ok = ok and g3

# (5) 水没離岸堤: 遮蔽ありで陰の中央が休み、風上側の縁に堆積、風下に侵食
from make_init import XB1, XB2, YL
X = np.broadcast_to(x[None, :], (NY, NX)); Y = np.broadcast_to(y[:, None], (NY, NX))
core = (X >= XB1 + 10.0) & (X < XB2 - 10.0) & (Y >= YL) & (Y < 45.0)
upedge = (X >= XB2 - 10.0) & (X < XB2 + 50.0) & (Y >= YL) & (Y < 55.0)
down = (X >= XB1 - 100.0) & (X < XB1) & (Y >= YL) & (Y < 55.0)
v = {}
for tag in ("bar", "bar0"):
    dz = np.loadtxt("result_%s/Z0002.txt" % tag) - np.loadtxt("result_%s/Z0000.txt" % tag)
    v[tag] = (np.abs(dz[core]).sum() * DX * DX, dz[upedge].sum() * DX * DX, dz[down].sum() * DX * DX)
r_core = v["bar"][0] / max(v["bar0"][0], 1e-6); r_up = v["bar"][1] / max(v["bar0"][1], 1e-6); r_down = v["bar"][2] / min(v["bar0"][2], -1e-6)
g5 = r_core < LEE_QUIET and v["bar"][1] > 0 and r_up > UP_RATIO and v["bar"][2] < 0 and r_down > DOWN_RATIO
print("(5) 水没離岸堤: 陰の中央 Σ|Δz| %.0f m³ (遮蔽なし %.0f、比 %.2f < %.1f)、風上側の縁の堆積 %.0f m³ (%.0f、比 %.1f > %.1f)、風下の侵食 %.0f m³ (%.0f、比 %.1f > %.1f) : %s"
      % (v["bar"][0], v["bar0"][0], r_core, LEE_QUIET, v["bar"][1], v["bar0"][1], r_up, UP_RATIO, v["bar"][2], v["bar0"][2], r_down, DOWN_RATIO, "PASS" if g5 else "FAIL"))
ok = ok and g5

print("== wave_shore 検定: %s ==" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
