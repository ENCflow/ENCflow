#!/usr/bin/env python3
# examples/mountain_valley の図化と数表(make_init.py と定数を対で保守)
#   python3 plot_results.py       figs/*.png(日本語)と数表(標準出力)
#   python3 plot_results.py en    en/figs/*.png(英語)
# 分布出力(bil = 単精度)の Z・Sd・H・V を読み、台帳(Screen_*.log の dispose の表示)と合わせる。
# 予測(docs/mountain_stream_plan.md §11.3):
#   C2 斜面: 定常では土層厚 H_ss = sd* ln(W0/U)、横断の曲率 −U/D_eff(D_eff = D (1 − e^{−H_ss/H_c}))、
#            渓流から k セル目の高さ (U/D_eff) Δx² (k L − k(k−1)/2)(L = 斜面のセル数。分水界の流束 0)
#   C1 渓流: 各セルで (E_p0(S) + β q)(1 − q/q_c(S)) = U、q Δx = q_上流 Δx + (1 − λ)(E_p Δx Δy + Q_lat Δy)
#            (E_p = E_p0 (1 − q/q_c)。Q_lat は斜面から届く土層 = 定常で 2 U L_斜面。等流の水理で谷頭から解く)
#   C4: 研磨だけの定常は β q (1 − q/q_c(S)) = U(準定常のパルスは給砂中の半分の時間だけ)
import sys, os, math, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_init import (Grid, CASES, T_RUN, T_OUT, T_DROP, F_FLOOD, YR, S0, QF, N, D50, LAM, HSTAR, KP, TAUC,
                       PM, BETA, UPLIFT0, WTHR_P0, CREEP_D, SDSTAR, HC, HILL_L,
                       P_CASES, P_NX, P_NY, P_DX, P_N, P_D50, P_HSTAR, P_U, P_KP, P_TAUC, P_PM, P_BETA,
                       P_QC0, P_RM, P_SHORT, P_LONG, P_TGEO, P_DTG, P_Q)
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


RHO, G, SGRAV, TAUSC = 1000.0, 9.8, 1.65, 0.05     # m_geomorph_rockinc・fluvial と同じ
# 系列の色(識別。固定の順): 青・橙・水色。時刻・位置の順序は青の濃淡。予測は灰色の破線
C1, C2C, C3C = "#2a78d6", "#eb6834", "#1baf7a"
RAMP = ("#86b6ef", "#2a78d6", "#104281")
GRAY = "#52514e"
U = UPLIFT0 * 1.0e-3 / YR                           # 隆起 (m/s。出水の時間)
W0 = WTHR_P0 * 1.0e-3 / (1000.0 * YR)               # 裸岩の土層生成 (m/s。出水の時間)


def kyr(t_flood):
    return t_flood / F_FLOOD / 1000.0


# ---------------------------------------------------------------- 読み込み
def bil(case, name, k, nx, ny):
    data = open("result_%s/%s%04d.bil" % (case, name, k), "rb").read()
    a = struct.unpack("<%df" % (nx * ny), data)
    return [a[j * nx:(j + 1) * nx] for j in range(ny)]


def vgrid(case):
    return Grid(CASES[case][1])


def vbil(case, name, k):
    g = vgrid(case)
    return bil(case, name, k, g.nx, g.ny)


def vk(case, t_yr):
    """暦の時間 t_yr の出力番号(構成 V_c は V_b からの通し番号)"""
    return int(round(t_yr / T_OUT))


def ledgers(case):
    log = open("Screen_%s.log" % case, encoding="utf-8", errors="replace").read()
    vp, va = [float(x) for x in re.findall(r"plucked\s+(\S+) m3.*abraded\s+(\S+) m3", log)[-1]]
    vout = re.findall(r"open boundaries \(out - in\)\s+(\S+) m3", log)
    return vp, va, (float(vout[-1]) if vout else 0.0)


def have(case):
    return os.path.isdir("result_%s" % case) and os.path.exists("Screen_%s.log" % case)


# ---------------------------------------------------------------- 水理と予測
def uniform(qw, s, n=N):
    h = (qw * n / math.sqrt(s)) ** 0.6
    return h, qw / h


def ep0(qw, s, kp=KP, tauc=TAUC, pm=PM, n=N):
    h, v = uniform(qw, s, n)
    tb = RHO * G * n ** 2 * v ** 2 / h ** (1.0 / 3.0)
    return kp * (tb / tauc - 1.0) ** pm if tb > tauc else 0.0


def qcap(qw, s, d50=D50, n=N):
    h, v = uniform(qw, s, n)
    taus = n ** 2 * v ** 2 / (SGRAV * d50 * h ** (1.0 / 3.0))
    if taus <= TAUSC:
        return 0.0
    qbs = 17.0 * taus ** 1.5 * (1.0 - TAUSC / taus) * (1.0 - math.sqrt(TAUSC / taus))
    return qbs * math.sqrt(SGRAV * G * d50 ** 3)


def c1_profile(g, lat, u=U):
    """C1 の準解析解: 谷頭から各セル j の勾配 S_j と被覆の比 q_j/q_c(S_j)(lat = 横からの供給、
    かさ体積 m2/s。剥離物は 1:1 で可動層に入り、研磨の細粒分は系外へ出る)"""
    qw = QF / g.dx
    out, q = [], 0.0
    for _ in range(g.ny - 1):
        qprev = q

        def resid(s):
            e, c = ep0(qw, s), qcap(qw, s)
            if c <= 0.0:
                return -u, qprev
            a = (1.0 - LAM) * g.dx * e
            qq = (qprev + a + (1.0 - LAM) * lat) / (1.0 + a / c)
            if qq >= c:
                return -u, qq
            return (e + BETA * qq) * (1.0 - qq / c) - u, qq

        lo, hi = 1.0e-4, 0.5
        for _ in range(200):
            mid = math.sqrt(lo * hi)
            if resid(mid)[0] > 0.0:
                hi = mid
            else:
                lo = mid
        s = math.sqrt(lo * hi)
        q = resid(s)[1]
        out.append((s, q / qcap(qw, s)))
    return out


def c2_heights(g, u=U):
    hss = SDSTAR * math.log(W0 / u)
    deff = CREEP_D * (1.0 - math.exp(-hss / HC))
    return hss, deff, [u / deff * g.dx ** 2 * (k * g.lh - k * (k - 1) / 2.0) for k in range(1, g.lh + 1)]


# ---------------------------------------------------------------- C3 斜面
def mid_rows(g):
    return range(g.ny // 4, 3 * g.ny // 4)


def hill_profile(case, k):
    g = vgrid(case)
    z, sd = vbil(case, "Z", k), vbil(case, "Sd", k)
    rows = mid_rows(g)
    rel = [sum(z[j][g.ic - 1 + kk] - z[j][g.ic - 1] for j in rows) / len(rows) for kk in range(1, g.lh + 1)]
    hh = [sum(sd[j][g.ic - 1 + kk] for j in rows) / len(rows) for kk in range(1, g.lh + 1)]
    return rel, hh


def fig_valley():
    case = "V_b"
    g = vgrid(case)
    hss, deff, pred = c2_heights(g)
    x = [(k + 0.0) * g.dx for k in range(1, g.lh + 1)]
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for t, col in zip((5.0e4, 1.0e5, 2.0e5), RAMP):
        rel, hh = hill_profile(case, vk(case, t))
        lab = T("%g 万年" % (t / 1e4), "%g kyr" % (t / 1e3))
        ax[0].plot([0.0] + x, [0.0] + rel, color=col, lw=2, marker="o", ms=4, label=lab)
        ax[1].plot(x, hh, color=col, lw=2, marker="o", ms=4, label=lab)
    ax[0].plot([0.0] + x, [0.0] + pred, color=GRAY, lw=1.5, ls="--", label=T("定常の予測(C2)", "steady prediction (C2)"))
    ax[1].axhline(hss, color=GRAY, lw=1.5, ls="--", label=T("H_ss = sd* ln(W0/U)", "H_ss = sd* ln(W0/U)"))
    ax[0].set_xlabel(T("渓流の中心からの距離 (m)", "distance from the stream centre (m)"))
    ax[0].set_ylabel(T("渓流の底からの高さ (m)", "height above the stream bed (m)"))
    ax[0].set_title(T("斜面の横断形(中央の半分の行の平均)", "cross-slope profile (mean of the middle rows)"))
    ax[1].set_xlabel(T("渓流の中心からの距離 (m)", "distance from the stream centre (m)"))
    ax[1].set_ylabel(T("土層厚 (m)", "soil depth (m)"))
    ax[1].set_title(T("斜面の土層厚", "soil depth on the hillslope"))
    ax[1].set_ylim(0.4, 0.6)
    for a in ax:
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "valley.png"), dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- C3 渓流
def channel(case, k):
    g = vgrid(case)
    z, sd = vbil(case, "Z", k), vbil(case, "Sd", k)
    xs, ss, hs = [], [], []
    for j in range(1, g.ny - 1):               # 0 始まりの行番号(谷頭と出口の行を除く)
        xs.append((j + 0.5) * g.dx)
        ss.append((z[j - 1][g.ic - 1] - z[j + 1][g.ic - 1]) / (2.0 * g.dx))
        hs.append(sd[j][g.ic - 1])
    return xs, ss, hs


def channel_cases():
    out = [("V_a", C1, T("斜面の供給なし(V_a)", "no hillslope supply (V_a)"), 0.0),
           ("V_b", C2C, T("斜面の供給あり(V_b)", "with hillslope supply (V_b)"), 2.0 * U * HILL_L)]
    if have("V_b2"):
        out.append(("V_b2", C3C, T("V_b、Δx = 2 m(V_b2)", "V_b with Δx = 2 m (V_b2)"), 2.0 * U * HILL_L))
    return out


def fig_channel():
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for case, col, lab, lat in channel_cases():
        g = vgrid(case)
        xs, ss, hs = channel(case, vk(case, T_RUN))
        prof = c1_profile(g, lat)
        xp = [(j + 0.5) * g.dx for j in range(1, g.ny - 1)]
        ax[0].plot(xs, ss, color=col, lw=2, label=lab)
        ax[0].plot(xp, [prof[j][0] for j in range(1, g.ny - 1)], color=col, lw=1.2, ls="--")
        ax[1].plot(xs, [100.0 * h for h in hs], color=col, lw=2, label=lab)
        ax[1].plot(xp, [100.0 * HSTAR * math.log(1.0 / (1.0 - prof[j][1])) for j in range(1, g.ny - 1)],
                   color=col, lw=1.2, ls="--")
    ax[0].plot([], [], color=GRAY, lw=1.2, ls="--", label=T("予測(C1。破線)", "prediction (C1, dashed)"))
    ax[0].set_ylabel(T("渓流の勾配", "stream slope"))
    ax[0].set_title(T("暦の 20 万年の渓流の勾配", "stream slope at 200 kyr"))
    ax[1].set_ylabel(T("渓流の可動層(被覆)の厚さ (cm)", "mobile layer (cover) on the stream bed (cm)"))
    ax[1].set_title(T("被覆の厚さ(破線は H* ln(1/(1 − q/q_c)))", "cover (dashed: H* ln(1/(1 − q/q_c)))"))
    for a in ax:
        a.set_xlabel(T("谷頭からの距離 (m)", "distance from the valley head (m)"))
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "channel.png"), dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- C3 基準面の低下
def drop_rows(g):
    return (g.ny // 5, 3 * g.ny // 5, g.ny - 2)  # 0 始まり: 谷頭寄り・中央・出口の隣


def fig_drop():
    g = vgrid("V_b")
    k0 = vk("V_b", T_RUN)
    z0 = vbil("V_b", "Z", k0)
    ks = range(k0, vk("V_c", T_RUN + T_DROP) + 1)
    rows = drop_rows(g)
    hss2 = SDSTAR * math.log(W0 / (2.0 * U))
    _, _, pred1 = c2_heights(g)
    _, _, pred2 = c2_heights(g, 2.0 * U)
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for r, col in zip(rows, RAMP):
        ts, dz, rel = [], [], []
        for k in ks:
            z = vbil("V_b" if k == k0 else "V_c", "Z", k)
            ts.append((k - k0) * T_OUT / 1000.0)
            dz.append(z[r][g.ic - 1] - z0[r][g.ic - 1])
            rel.append(0.5 * (z[r][0] + z[r][g.nx - 1]) - z[r][g.ic - 1])
        lab = T("谷頭から %d m" % ((r + 0.5) * g.dx), "%d m from the head" % ((r + 0.5) * g.dx))
        ax[0].plot(ts, dz, color=col, lw=2, marker="o", ms=3, label=lab)
        ax[1].plot(ts, rel, color=col, lw=2, marker="o", ms=3, label=lab)
    ax[1].axhline(pred1[-1], color=GRAY, lw=1.2, ls=":", label=T("元の定常(浸食速度 U)", "former steady state (erosion U)"))
    ax[1].axhline(pred2[-1], color=GRAY, lw=1.5, ls="--", label=T("新しい定常の予測(2U)", "new steady prediction (2U)"))
    ax[0].set_ylabel(T("渓流の底の変化 (m)", "change of the stream bed (m)"))
    ax[0].set_title(T("渓流: 基準面の低下が谷を上る", "stream: the base-level fall travels up the valley"))
    ax[1].set_ylabel(T("分水界の高さ − 渓流の底 (m)", "divide height − stream bed (m)"))
    ax[1].set_title(T("斜面: 起伏はゆっくり増える", "hillslope: the relief grows slowly"))
    for a, loc in zip(ax, ("upper right", "lower right")):
        a.set_xlabel(T("基準面の低下を始めてからの時間 (千年)", "time since the base level began to fall (kyr)"))
        a.grid(alpha=0.3)
        a.legend(fontsize=8, loc=loc)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "drop.png"), dpi=110)
    plt.close(fig)
    return hss2, pred2[-1]


# ---------------------------------------------------------------- C4 パルス給砂
P_J1, P_J2 = 15, 58
P_LAB = (T("一定", "constant"), T("パルス 周期 %g s" % P_SHORT, "pulses, period %g s" % P_SHORT),
         T("パルス 周期 %g s" % P_LONG, "pulses, period %g s" % P_LONG))
P_COL = (C1, C2C, C3C)


def pbil(case, name, k):
    return bil(case, name, k, P_NX, P_NY)


def p_nout():
    return int(round(P_TGEO / P_DTG))


def p_series(case, ch):
    i = 2 * ch + 1
    ts, ss = [], []
    for k in range(1, p_nout() + 1):
        z = pbil(case, "Z", k)
        ts.append(k * P_DTG)
        ss.append((z[P_J1 - 1][i] - z[P_J2 - 1][i]) / ((P_J2 - P_J1) * P_DX))
    return ts, ss


def p_qs_slope(model, duty):
    """予測の区間 j = P_J1〜P_J2 の平均の勾配。研磨だけ: 給砂を duty の割合の時間だけ q_m/duty で
    与えた準定常 duty β q_on (1 − q_on/q_c(S)) = U(一様な勾配)。剥離だけ: 一定給砂の各セルで
    E_p0(S)(1 − q_j/q_c(S)) = U、q_j = q_m + (1 − λ) U Δy j(T11 の式。露出率は q に線形なので、
    準定常のパルスも同じ平均になる)"""
    qw = P_Q / P_DX

    def solve(f):
        lo, hi = 1.0e-4, 0.1
        for _ in range(200):
            mid = math.sqrt(lo * hi)
            if f(mid) > P_U:
                hi = mid
            else:
                lo = mid
        return math.sqrt(lo * hi)

    def capacity(s):
        return qcap(qw, s, P_D50, P_N)

    if model == "a":
        qon = P_RM * P_QC0 / duty
        return solve(lambda s: duty * P_BETA * qon * max(0.0, 1.0 - qon / capacity(s)) if capacity(s) > 0.0 else 0.0)
    ss = []
    for j in range(P_J1, P_J2 + 1):
        qj = P_RM * P_QC0 + (1.0 - LAM) * P_U * P_DX * j
        ss.append(solve(lambda s, qj=qj: ep0(qw, s, P_KP, P_TAUC, P_PM, P_N) * max(0.0, 1.0 - qj / capacity(s))
                        if capacity(s) > 0.0 else 0.0))
    return sum(ss) / len(ss)


def p_supply(ch, k):
    """水路 ch に出力の区間 k − 1 → k(地形の時間)で与えた給砂の固体体積"""
    if ch == 0:
        return P_RM * P_QC0 * P_DX * P_DTG
    per = P_SHORT if ch == 1 else P_LONG
    n, tot, t0 = 3000, 0.0, (k - 1) * P_DTG
    for m in range(n):
        t = t0 + (m + 0.5) * P_DTG / n
        tot += (2.0 * P_RM * P_QC0 * P_DX if (t % per) < 0.5 * per else 0.0) * P_DTG / n
    return tot


def p_outflow(case, ch, k0):
    """出口の掃流砂の流出(出力の区間ごとの平均 m3/s)を水路の土砂収支から求める。剥離だけ:
    (1 − λ) ΔΣz = (1 − λ) U Δt N_up + 給砂 − 流出(剥離は z を動かさない)。研磨だけ:
    (1 − λ) ΔΣsd = 給砂 − 流出(研磨は sd を動かさない)"""
    i = 2 * ch + 1
    zp, sp = pbil(case, "Z", k0 - 1), pbil(case, "Sd", k0 - 1)
    outs = []
    for k in range(k0, p_nout() + 1):
        z, sd = pbil(case, "Z", k), pbil(case, "Sd", k)
        if P_CASES[case] == "p":
            store = sum(z[j][i] - zp[j][i] for j in range(P_NY)) - P_U * P_DTG * (P_NY - 1)
        else:
            store = sum(sd[j][i] - sp[j][i] for j in range(P_NY))
        outs.append((p_supply(ch, k) - (1.0 - LAM) * store * P_DX * P_DX) / P_DTG)
        zp, sp = z, sd
    return outs


def fig_pulse():
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for a, case, ttl in ((ax[0], "P_p", T("剥離だけ(P_p)", "plucking only (P_p)")),
                         (ax[1], "P_a", T("研磨だけ(P_a)", "abrasion only (P_a)"))):
        for ch in range(3):
            ts, ss = p_series(case, ch)
            a.plot([t / 1000.0 for t in ts], ss, color=P_COL[ch], lw=1.8, label=P_LAB[ch])
        model = P_CASES[case]
        a.axhline(p_qs_slope(model, 1.0), color=GRAY, lw=1.2, ls="--",
                  label=T("一定給砂の予測", "prediction, constant supply") if model == "a" else
                  T("一定給砂・準定常のパルスの予測", "prediction, constant and quasi-steady pulses"))
        if model == "a":
            a.axhline(p_qs_slope(model, 0.5), color=GRAY, lw=1.2, ls=":",
                      label=T("準定常のパルスの予測", "prediction, quasi-steady pulses"))
        a.set_title(ttl)
        a.set_xlabel(T("地形の時間 (千秒)", "morphological time (ks)"))
        a.set_ylabel(T("区間の平均の勾配(j = %d〜%d)" % (P_J1, P_J2), "mean slope over j = %d-%d" % (P_J1, P_J2)))
        a.grid(alpha=0.3)
        if model == "p":                               # 振れる系列の上に凡例の余白を空ける
            lo, hi = a.get_ylim()
            a.set_ylim(lo, hi + 0.45 * (hi - lo))
            a.legend(fontsize=8, loc="upper center", ncol=2)
        else:
            a.legend(fontsize=8, loc="center right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGDIR, "pulse.png"), dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- 数表
def tables():
    print("=== C3 斜面(V_b、暦の %g 年。中央の半分の行の平均)===" % T_RUN)
    for case in ("V_b", "V_b2"):
        if not have(case):
            continue
        g = vgrid(case)
        hss, deff, pred = c2_heights(g)
        rel, hh = hill_profile(case, vk(case, T_RUN))
        print("  %s(Δx = %g m): H_ss = %.4f m、D_eff = %.4e m2/s" % (case, g.dx, hss, deff))
        print("    渓流からの高さ (m)   " + " ".join("%.3f" % v for v in rel))
        print("    予測(C2)            " + " ".join("%.3f" % v for v in pred))
        print("    土層厚 (m)          " + " ".join("%.3f" % v for v in hh))
        print("    max 相対差: 高さ %.2e、土層厚 %.2e" % (max(abs(a / b - 1) for a, b in zip(rel, pred)),
                                                       max(abs(h / hss - 1) for h in hh)))
    print("=== C3 渓流(暦の %g 年)と台帳 ===" % T_RUN)
    for case, _, lab, lat in channel_cases():
        g = vgrid(case)
        xs, ss, hs = channel(case, vk(case, T_RUN))
        prof = c1_profile(g, lat)
        j1 = g.ny // 5                          # 谷頭の加速域(流入セル直下)を避ける
        diffs = [abs(ss[j - 1] / prof[j][0] - 1.0) for j in range(j1, g.ny - 1)]
        vp, va, vout = ledgers(case)
        print("  %s: 勾配 %.4f〜%.4f(予測 %.4f〜%.4f)、max 相対差 %.2e(谷頭から %g m より下流)、"
              "被覆 %.3f〜%.3f m" % (case, ss[j1 - 1], ss[-1], prof[j1][0], prof[g.ny - 2][0], max(diffs),
                                   (j1 + 0.5) * g.dx, hs[j1 - 1], hs[-1]))
        print("    台帳: 剥離 %.1f m3、研磨 %.1f m3(かさ体積)、出口の掃流砂 %.1f m3(固体)= %.1f m3(かさ)。"
              "研磨の割合 %.0f %%、出口の掃流砂のうち岩盤起源(剥離)%.0f %%"
              % (vp, va, vout, vout / (1.0 - LAM), 100.0 * va / (vp + va), 100.0 * vp / (vout / (1.0 - LAM))))
    if have("V_c"):
        g = vgrid("V_b")
        k0 = vk("V_b", T_RUN)
        z0 = vbil("V_b", "Z", k0)
        rows = drop_rows(g)
        hss2, pred2 = SDSTAR * math.log(W0 / (2.0 * U)), c2_heights(g, 2.0 * U)[2]
        print("=== C3 基準面の低下(V_c。出口の行を U で下げる)===")
        print("  新しい定常の予測(浸食速度 2U): H_ss = %.3f m、分水界の高さ %.2f m" % (hss2, pred2[-1]))
        print("  千年  " + "  ".join("底 %3dm" % ((r + 0.5) * g.dx) for r in rows) + "  " +
              "  ".join("起伏 %3dm" % ((r + 0.5) * g.dx) for r in rows) + "  斜面の土層厚(中央)")
        for k in range(k0, vk("V_c", T_RUN + T_DROP) + 1, 2):
            z = vbil("V_b" if k == k0 else "V_c", "Z", k)
            sd = vbil("V_b" if k == k0 else "V_c", "Sd", k)
            hm = sum(sd[j][g.ic - 1 + kk] for j in mid_rows(g) for kk in range(1, g.lh + 1)) / (len(mid_rows(g)) * g.lh)
            print("  %4.0f  " % ((k - k0) * T_OUT / 1000.0) +
                  "  ".join("%7.2f" % (z[r][g.ic - 1] - z0[r][g.ic - 1]) for r in rows) + "  " +
                  "  ".join("%8.2f" % (0.5 * (z[r][0] + z[r][g.nx - 1]) - z[r][g.ic - 1]) for r in rows) +
                  "  %.3f" % hm)
    n = p_nout()
    per = int(round(P_LONG / P_DTG))                # 長周期のパルスの 1 周期の出力の数
    nwin = (n // 3) // per * per                    # 最後のおよそ 1/3 を長周期の整数倍にそろえた窓
    k0 = n - nwin + 1
    print("=== C4 同じ平均の給砂(給砂比 %g)の一定とパルス(最後の %d 区間 = 長周期 %d 周期)==="
          % (P_RM, nwin, nwin // per))
    for case in ("P_p", "P_a"):
        if not have(case):
            continue
        model = P_CASES[case]
        print("  %s: 予測 一定 %.5f%s" % (case, p_qs_slope(model, 1.0),
              ("、準定常のパルス %.5f" % p_qs_slope(model, 0.5)) if model == "a" else ""))
        for ch in range(3):
            ts, ss = p_series(case, ch)
            last = ss[k0 - 1:]
            sds = [pbil(case, "Sd", k)[(P_J1 + P_J2) // 2][2 * ch + 1] for k in range(k0, n + 1)]
            cov = "%.2f" % (sum(1 for v in sds if v > P_HSTAR) / len(sds))
            if ch == 1:
                cov = "—(出力の間隔が周期の倍数で位相がそろうため測れない)"
            outs = p_outflow(case, ch, k0)
            mo = sum(outs) / len(outs)
            cv = math.sqrt(sum((o - mo) ** 2 for o in outs) / len(outs)) / mo
            print("    %-18s 勾配 %.5f(%.5f〜%.5f)、区間の中央の被覆 > H* の時間の割合 %s、"
                  "出口の流出 %.3e m3/s(変動係数 %.2f)" % (P_LAB[ch], sum(last) / len(last), min(last), max(last),
                                                       cov, mo, cv))


if __name__ == "__main__":
    fig_valley()
    fig_channel()
    if have("V_c"):
        fig_drop()
    if have("P_p") and have("P_a"):
        fig_pulse()
    tables()
