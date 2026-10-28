#!/usr/bin/env python3
# examples/bedrock_cover の図化と数表(make_init.py と定数を対で保守)
#   python3 plot_results.py       figs/*.png(日本語)と数表(標準出力)
#   python3 plot_results.py en    en/figs/*.png(英語)
# 分布出力(bil = 単精度)の Ri(累積下刻)・Sd(土層厚)・Z・H・V を、区間 J1〜J2 の平均で読む。
# 理論線は、等流の水理(H・V)から求めた剥離の速度 E_p0 と掃流砂の容量 q_c を使う:
#   被覆率 F_s = q/q_c、露出率 1 − q/q_c、下刻速度 E = (1 − q/q_c)(E_p0 + β q)
#   (q は掃流砂の流砂量。剥離物は 1:1 で可動層に入り、(1 − λ) E_p だけ下流の q を増やすので、
#   q(x) = q_c − (q_c − q_in) exp(−(1 − λ) E_p0 x / q_c)。研磨の細粒分は系外へ出る)
import sys, os, math, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import (CASES, NY, DX, S, N, D50, LAM, HSTAR, KP, TAUC, PM, BETA, QC, MORFAC, J1, J2,
                       R_SWEEP, R_MEAN, R_ON, P_SHORT, P_LONG, SD_INIT, R_COVER, J_STEP, DZ_STEP, R_KNICK, z_of)
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt

EN = "en" in sys.argv[1:]
matplotlib.rcParams["font.family"] = ["DejaVu Sans"] if EN else ["IPAGothic", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
FIGDIR = "en/figs" if EN else "figs"
os.makedirs(FIGDIR, exist_ok=True)


def T(ja, en):
    return en if EN else ja


RHO, G, SGRAV, TAUSC, DVIRT = 1000.0, 9.8, 1.65, 0.05, 0.001   # m_geomorph_rockinc・fluvial と同じ
COL = {"p": "#287ca5", "a": "#ad5b29", "pa": "#52744b"}
LAB = {"p": T("剥離だけ", "plucking only"), "a": T("研磨だけ", "abrasion only"),
       "pa": T("剥離 + 研磨", "plucking + abrasion")}


def nx_of(case):
    return 2 * len(CASES[case][1]) + 1


def bil(case, name, k):
    nx = nx_of(case)
    data = open("result_%s/%s%04d.bil" % (case, name, k), "rb").read()
    a = struct.unpack("<%df" % (nx * NY), data)
    return [a[j * nx:(j + 1) * nx] for j in range(NY)]


def nout(case):
    return CASES[case][2] // CASES[case][3] + 1


def reach_mean(case, name, k, ch):
    a = bil(case, name, k)
    return sum(a[j][2 * ch + 1] for j in range(J1, J2)) / (J2 - J1)


def tgeo(case, k):
    return k * CASES[case][3] * MORFAC


def taub(vv, h):
    return RHO * G * N ** 2 * vv ** 2 / max(h, DVIRT) ** (1.0 / 3.0)


def ep0(vv, h):
    tb = taub(vv, h)
    return KP * (tb / TAUC - 1.0) ** PM if tb > TAUC else 0.0


def qcap(vv, h):
    taus = N ** 2 * vv ** 2 / (SGRAV * D50 * max(h, DVIRT) ** (1.0 / 3.0))
    if taus <= TAUSC:
        return 0.0
    qbs = 17.0 * taus ** 1.5 * (1.0 - TAUSC / taus) * (1.0 - math.sqrt(TAUSC / taus))
    return qbs * math.sqrt(SGRAV * G * D50 ** 3)


def theory(model, r_in, ep, qc):
    """区間 J1〜J2 の平均の定常の下刻速度と被覆の厚さ(剥離物の自己供給を含む)"""
    e_p = ep if "p" in model else 0.0
    beta = BETA if "a" in model else 0.0
    qin = r_in * QC * DX / DX
    es, hs = [], []
    for j in range(J1, J2):
        x = (j + 0.5) * DX                       # 流入セル(j = 1)の中心から
        q = qc - (qc - qin) * math.exp(-(1.0 - LAM) * e_p * x / qc) if e_p > 0.0 else qin
        q = min(q, qc)
        es.append((1.0 - q / qc) * (e_p + beta * q))
        hs.append(-HSTAR * math.log(1.0 - q / qc) if q < qc else float("inf"))
    return sum(es) / len(es), sum(hs) / len(hs)


# --- 水理(A_a の最終時刻、水路ごと。研磨だけなので河床はほぼ一様に下がる) ---
kend = nout("A_a") - 1
hh, vv = bil("A_a", "H", kend), bil("A_a", "V", kend)
hyd = [(sum(hh[j][2 * c + 1] for j in range(J1, J2)) / (J2 - J1), sum(vv[j][2 * c + 1] for j in range(J1, J2)) / (J2 - J1))
       for c in range(len(R_SWEEP))]
h_m = sum(h for h, _ in hyd) / len(hyd)
v_m = sum(v for _, v in hyd) / len(hyd)
EP0, QC_H = ep0(v_m, h_m), qcap(v_m, h_m)
print(T("等流の水理(区間 %d〜%d m の平均): ", "uniform-flow hydraulics (mean over %d-%d m): ") % (J1, J2)
      + "h = %.4f m, V = %.4f m/s, τ_b = %.2f Pa, E_p0 = %.3e m/s, q_c = %.4e m2/s"
      % (h_m, v_m, taub(v_m, h_m), EP0, QC_H))

# --- 図 1: 給砂比と下刻速度・被覆の厚さ(A) ---
print(T("\n[A] 一定給砂の定常(最後の 3 出力 = 地形の時間 %.0f s の Ri の増分)",
        "\n[A] steady state under constant supply (increase of Ri over the last 3 outputs = %.0f s of morphological time)")
      % (3 * CASES["A_a"][3] * MORFAC))
print(T("  モデル  r     下刻速度 (m/s)  理論        比     被覆 H (m)  理論",
        "  model   r     rate (m/s)      theory      ratio  cover H (m) theory"))
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0))
rr = [i / 100.0 for i in range(0, 100)]
worst = 0.0
for model in ("p", "a", "pa"):
    case = "A_" + model
    k2 = nout(case) - 1
    k1 = k2 - 3
    rates, covers = [], []
    for c, r in enumerate(R_SWEEP):
        rate = (reach_mean(case, "Ri", k2, c) - reach_mean(case, "Ri", k1, c)) / (tgeo(case, k2) - tgeo(case, k1))
        hcov = reach_mean(case, "Sd", k2, c)
        et, ht = theory(model, r, EP0, QC_H)
        rates.append(rate)
        covers.append(hcov)
        ratio = rate / et if et > 0.0 else float("nan")
        if 0.0 < r < 1.0 or (r == 0.0 and model != "a"):
            worst = max(worst, abs(ratio - 1.0))
        print("  %-6s %.1f   %.3e       %.3e   %5.3f  %.4f      %s"
              % (model, r, rate, et, ratio, hcov, "%.4f" % ht if ht < 1.0 else "∞"))
    ax[0].plot(R_SWEEP, [e * 1.0e6 for e in rates], "o", color=COL[model], label=LAB[model])
    ax[0].plot(rr, [theory(model, r, EP0, QC_H)[0] * 1.0e6 for r in rr], "-", color=COL[model], lw=1.2)
    if model == "a":
        ax[1].plot(R_SWEEP, [h * 100.0 for h in covers], "o", color="k", label=T("計算(3 モデル)", "computed (3 models)"))
    else:
        ax[1].plot(R_SWEEP, [h * 100.0 for h in covers], "o", color="k")
print(T("  理論との最大の相対差(0 < r < 1。r = 0 は剥離のあるモデル): %.3f",
        "  largest relative difference from the theory (0 < r < 1; r = 0 for the models with plucking): %.3f") % worst)
ax[1].plot(rr, [-HSTAR * math.log(1.0 - r) * 100.0 for r in rr], "-", color="k", lw=1.2,
           label=T("H = −H* ln(1 − r)(自己供給なし)", "H = −H* ln(1 − r) (no self-supply)"))
ax[0].set_xlabel(T("給砂比 r = q_in / q_c", "supply ratio r = q_in / q_c"))
ax[0].set_ylabel(T("定常の下刻速度 (10⁻⁶ m/s)", "steady incision rate (10⁻⁶ m/s)"))
ax[0].set_title(T("(a) 道具と被覆: 点 = 計算、線 = 理論", "(a) tools and cover: dots = model, lines = theory"), fontsize=10, loc="left")
ax[0].legend(fontsize=8)
ax[0].set_xlim(-0.03, 1.03)
ax[0].set_ylim(0, None)
ax[1].set_xlabel(T("給砂比 r = q_in / q_c", "supply ratio r = q_in / q_c"))
ax[1].set_ylabel(T("可動層の厚さ H (cm)", "mobile layer thickness H (cm)"))
ax[1].set_title(T("(b) 被覆の厚さ(H* = 1 cm)", "(b) cover thickness (H* = 1 cm)"), fontsize=10, loc="left")
ax[1].set_ylim(0, 4.5)
ax[1].set_xlim(-0.03, 1.03)
ax[1].legend(fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(FIGDIR + "/supply.png", dpi=130)
plt.close(fig)

# --- 図 2: 一定給砂とパルス給砂(B) ---
print(T("\n[B] 同じ平均の給砂比 %.2f: 一定給砂と、半分の時間だけ %.2f のパルス(地形の時間 %.0f s の累積下刻、区間平均)",
        "\n[B] same mean supply ratio %.2f: constant supply and pulses of %.2f for half of the time "
        "(cumulative incision over %.0f s of morphological time, reach mean)")
      % (R_MEAN, R_ON, tgeo("B_a", nout("B_a") - 1)))
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0), sharey=True)
labs = (T("一定給砂", "constant"), T("パルス 周期 %g s" % P_SHORT, "pulses, period %g s" % P_SHORT),
        T("パルス 周期 %g s" % P_LONG, "pulses, period %g s" % P_LONG))
sty = ("-", "--", ":")
for a_i, model in enumerate(("p", "a")):
    case = "B_" + model
    n = nout(case)
    tt = [tgeo(case, k) for k in range(n)]
    tot = []
    for c in range(3):
        ri = [reach_mean(case, "Ri", k, c) for k in range(n)]
        tot.append(ri[-1])
        ax[a_i].plot([t / 1000.0 for t in tt], [v * 100.0 for v in ri], sty[c], color=COL[model], lw=1.5, label=labs[c])
    if model == "a":
        qs = 0.5 * R_ON * (1.0 - R_ON) / (R_MEAN * (1.0 - R_MEAN))
        note = T("準定常の予想: パルス/一定 = %.2f" % qs, "quasi-steady estimate: pulses/constant = %.2f" % qs)
    else:
        qs = 1.0
        note = T("準定常の予想: パルス/一定 = 1(露出率が r に線形)", "quasi-steady estimate: pulses/constant = 1 (exposure linear in r)")
    print(T("  %-2s  一定 %.4f m、周期 %g s %.4f m(比 %.3f)、周期 %g s %.4f m(比 %.3f)。準定常の予想 %.3f",
            "  %-2s  constant %.4f m, period %g s %.4f m (ratio %.3f), period %g s %.4f m (ratio %.3f); "
            "quasi-steady estimate %.3f")
          % (model, tot[0], P_SHORT, tot[1], tot[1] / tot[0], P_LONG, tot[2], tot[2] / tot[0], qs))
    ax[a_i].set_title("(%s) %s" % ("ab"[a_i], LAB[model]), fontsize=10, loc="left")
    ax[a_i].text(0.97, 0.04, note, transform=ax[a_i].transAxes, fontsize=8, ha="right")
    ax[a_i].set_xlabel(T("地形の時間 (10³ s)", "morphological time (10³ s)"))
    ax[a_i].legend(fontsize=8, loc="upper left")
ax[0].set_ylabel(T("累積の下刻量(区間平均、cm)", "cumulative incision (reach mean, cm)"))
fig.tight_layout()
fig.savefig(FIGDIR + "/pulse.png", dpi=130)
plt.close(fig)

# --- 図 3: 初期の被覆(C) ---
print(T("\n[C] 給砂比 %.2f、剥離 + 研磨。初期の土層厚ごとの累積下刻(区間平均)",
        "\n[C] supply ratio %.2f, plucking + abrasion. Cumulative incision for each initial soil depth (reach mean)")
      % R_COVER)
case = "C_pa"
n = nout(case)
tt = [tgeo(case, k) / 1000.0 for k in range(n)]
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0))
cols = ("#287ca5", "#da9760", "#ad5b29")
for c, h0 in enumerate(SD_INIT):
    ri = [reach_mean(case, "Ri", k, c) for k in range(n)]
    sd = [reach_mean(case, "Sd", k, c) for k in range(n)]
    lab = T("初期の土層厚 %g cm" % (h0 * 100), "initial soil %g cm" % (h0 * 100))
    ax[0].plot(tt, [v * 100 for v in ri], color=cols[c], lw=1.5, label=lab)
    ax[1].plot(tt, [v * 100 for v in sd], color=cols[c], lw=1.5, label=lab)
    print(T("  初期 %.3f m: 累積下刻 %.4f m(地形の時間 %.0f s)、最終の H = %.4f m",
            "  initial %.3f m: cumulative incision %.4f m (morphological time %.0f s), final H = %.4f m")
          % (h0, ri[-1], tgeo(case, n - 1), sd[-1]))
ax[0].set_xlabel(T("地形の時間 (10³ s)", "morphological time (10³ s)"))
ax[0].set_ylabel(T("累積の下刻量(区間平均、cm)", "cumulative incision (reach mean, cm)"))
ax[0].set_title(T("(a) 下刻", "(a) incision"), fontsize=10, loc="left")
ax[0].legend(fontsize=8)
ax[1].set_xlabel(T("地形の時間 (10³ s)", "morphological time (10³ s)"))
ax[1].set_ylabel(T("可動層の厚さ H(区間平均、cm)", "mobile layer H (reach mean, cm)"))
ax[1].set_ylim(0, 10.5)
ax[1].legend(fontsize=8)
ax[1].set_title(T("(b) 被覆の厚さ", "(b) cover thickness"), fontsize=10, loc="left")
fig.tight_layout()
fig.savefig(FIGDIR + "/cover.png", dpi=130)
plt.close(fig)

# --- 図 4: 遷急点(D) ---
print(T("\n[D] 段差(j > %d を %.2f m 下げる)の後退。剥離だけ。段差の位置 = 上流の区間(40 m)から落差の"
        "半分だけ下がった点(流入端から)",
        "\n[D] retreat of the step (j > %d lowered by %.2f m), plucking only. Step position = the point half "
        "the drop below the upstream reach (40 m), from the inflow end") % (J_STEP, DZ_STEP))
case = "D_p"
n = nout(case)
ks = (0, 2, 5, n - 1)
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0), sharey=True)
y = [(j + 0.5) * DX for j in range(NY)]
for c, r in enumerate(R_KNICK):
    i = 2 * c + 1
    for kk, k in enumerate(ks):
        z = bil(case, "Z", k)
        sd = bil(case, "Sd", k)
        ref = [z_of(2, j + 1) for j in range(NY)]     # 初期の一様勾配の面(段差なし)
        col = plt.cm.viridis(kk / (len(ks) - 0.5))
        ax[c].plot(y, [z[j][i] - ref[j] for j in range(NY)], color=col, lw=1.4,
                   label=T("地形の時間 %.0f s" % tgeo(case, k), "t = %.0f s" % tgeo(case, k)))
        ax[c].plot(y, [z[j][i] - sd[j][i] - ref[j] for j in range(NY)], color=col, lw=0.8, ls=":")
        sl = [(z[j][i] - z[j + 1][i]) / DX for j in range(NY - 1)]
        jm = max(range(NY - 1), key=lambda j: sl[j])
        dz = [z[j][i] - ref[j] for j in range(NY)]
        up = dz[39]                                   # 流入端から 40 m(セル 40)
        xk = float("nan")
        for j in range(40, NY):
            if dz[j] < up - 0.5 * DZ_STEP:
                xk = (j - 0.5) + (up - 0.5 * DZ_STEP - dz[j - 1]) / (dz[j] - dz[j - 1])
                break
        print(T("  r = %.1f  地形の時間 %6.0f s: 段差の位置 %.1f m、下刻 %.3f m(40 m)・%.3f m(90 m)、"
                "最大勾配 %.3f(セル %d → %d の間)",
                "  r = %.1f  morphological time %6.0f s: step at %.1f m, incision %.3f m (40 m), %.3f m (90 m), "
                "largest slope %.3f (between cells %d and %d)")
              % (r, tgeo(case, k), xk, round(-up, 6) + 0.0, round(-(dz[89] + DZ_STEP), 6) + 0.0, sl[jm], jm + 1, jm + 2))
    ax[c].set_title("(%s) %s" % ("ab"[c], T("給砂比 %g" % r, "supply ratio %g" % r)), fontsize=10, loc="left")
    ax[c].set_xlabel(T("流入端からの距離 (m)", "distance from the inflow end (m)"))
    ax[c].set_xlim(40, 100)
    ax[c].legend(fontsize=7, loc="lower left")
ax[0].set_ylabel(T("初期の一様勾配の面からの高さ (m)\n実線 = 河床 z、点線 = 岩盤面 z − sd",
                   "height above the initial uniform slope (m)\nsolid = bed z, dotted = bedrock z − sd"))
fig.tight_layout()
fig.savefig(FIGDIR + "/knick.png", dpi=130)
plt.close(fig)
print("\nfigures: %s/supply.png, pulse.png, cover.png, knick.png" % FIGDIR)
