"""Coastal wave field chapter (users_guide/wavefield.md).

Two figures:
  wavefield_plan     plan view: the sides and the processes on a straight coast,
                     lateral Neumann against absorbing sides, the direction
                     convention, and the cells waves pass through.
  wavefield_profile  cross-shore profile: the phase-averaged wave height, the mean
                     water level and the longshore current with and without the
                     roller, and the vertical structure behind wf_flow = 2.

Explanatory figures, not ENCflow results.  What is computed here: the wave crests
and rays of (a) of the plan (linear dispersion and Snell's law on a 1/80 beach),
the lateral-side wave heights of (b) (exact rays over a cos^s directional spectrum
on a uniform depth, no numerical diffusion), and the 1-D beach profile (linear
theory, Baldock et al. 1998 breaking with the depth limit, the roller, the
radiation stress and the GLM wave-current friction of users_guide/
wavefield_models.md sec. 2, 5 and 6, with the defaults of the chapter).
Regenerate only this chapter with make_guide_figs.py wavefield.
"""
from _terms import *
from _wave import G, RHO, wavenumber, group, spreading_exponent, paragraph, fit_height
import matplotlib
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle, Arc

T = {'ja': {
 # plan
 'pa': '(a) 直線海岸の設定と、波浪場が計算すること',
 'pb': '(b) 海岸に交わる左右の辺: 側方 Neumann と吸収',
 'pc': '(c) 向きの規約',
 'pd': '(d) 波が通るセル・通らないセル',
 'side1': '1 入射: 沖の波(wf_hm0・wf_trep・wf_dir・wf_spread)',
 'side2': '2 側方 Neumann: 辺の外にも同じ海が続く',
 'side0': '0 吸収(陸側の辺。型は何でもよい)',
 'bcset': '入力例: wf_bc_side = 1, 0, 2, 2(辺 W・E・N・S の順)。海底地形・進行方向 20° の例',
 'land': '陸',
 'surf': '砕波帯',
 'shoal': '浅水変形: 浅いほど波高が増す',
 'refr': '屈折: 峰が等深線に沿うよう曲がる',
 'shadow': '陰',
 'bw': '防波堤',
 'crest': '白線: 波の峰(説明用。線の太さは波高。位相平均の計算が解くのは波高と向き)',
 'ray': '紺の矢印: 波向線(峰に直角)',
 'neu': '側方 Neumann(2)',
 'abs': '吸収(0)',
 'neu_note': '外から斜めに入る波も届き、岸沿いに一様',
 'abs_note': '外から入るはずの波がなく、辺の近くに偽の陰ができる',
 'hh0': '波高比 H/H₀',
 'b_note': '一様な水深・砕波なしの例。沖の辺(左)から進行方向 20°・方向分散 20° の波を入れ、向きごとの波線で求めた(数値拡散なし)。等値線は 0.95・0.8・0.5',
 'travel': '進む向き',
 'from': '来る向き',
 'east': '東 0°\n(x 軸)', 'north': '北 90°', 'west': '西 180°', 'south': '南 270°',
 'ex': 'wf_dir と出力 Wa は進む向き θ を x 軸(東)から反時計回りに測る(例は θ = 20°)。',
 'naut': 'nautical の規約(SWAN・XBeach など)は来る向き θ_n を北から時計回りに測る。換算は θ = 270° − θ_n(x 軸が東の格子)で、例の θ_n は 250°。180° の差ではない。',
 'ysign': '出力の y 成分(v・Wfy・Wsy・Qby・Qsy)は南が正。波向の規約(北が 90°)とは逆。',
 'ax_i': '列 i: 東へ増える',
 'ax_j': '行 j: 南へ増える',
 'up': 'θ = 90°(北へ進む)',
 'vpos': 'v > 0(南向き)',
 'cw': '波浪セル(水深 > wf_hmin)',
 'cdry': '乾いたセル・水深 ≤ wf_hmin',
 'cland': '陸',
 'csw': '海域マスクの海セル sw(潮位の境界。浅水流でも計算しない)',
 'cabs': '吸収セル: 家屋の空隙率 gv < 1',
 'cabs2': '吸収セル: サブグリッド河道の幅・断面形',
 'cdike': '陸(1 セル厚の斜めの堤)',
 'rule1': '波浪セル以外のセルへ向かう波は吸収される(反射なし。台帳の absorbed)。',
 'rule2': '角を共有する 2 セルがともに波の通らないセルなら、その対角(✕)は閉じる。斜めの堤を波はすり抜けない(1 セル幅の斜めの水路に水を通す浅水流とは意図的に違う)。',
 'rule3': '海セルの帯の外側から波は入らない。入射の辺に接するセルは波浪セルにする。',
 # profile
 'qa': '(a) 岸沖断面で見た波と流れ(縦を約 37 倍に誇張)',
 'qb': '(b) 波高',
 'qc': '(c) 砕波とローラーの散逸',
 'qd': '(d) 平均水位',
 'qe': '(e) 沿岸流(進行方向 20° の斜め入射)',
 'qf': '(f) 砕波帯の鉛直の構造(wf_flow = 2)',
 'qg': '(g) 砂を運ぶ速度(f_wfsed)',
 'off': '沖の波(入射の辺から)',
 'shoal2': '浅水変形: 波高が増す',
 'brk0': '砕波の始まり',
 'surf2': '砕波帯: 砕けた波はローラー(波頭の表面の渦)を経て散逸',
 'env': '破線: モデルが解く波高 H_m0(包絡。個々の波は解かない)',
 'inst': '実線: ある瞬間の水面(説明用)',
 'mwl': '平均水位(セットダウン・セットアップ)',
 'shore': '汀線(水深 wf_hmin)',
 'swash': '遡上域: 位相平均の波浪場は解かない(f_wfswash は経験式で砂を積み上げ・削る)',
 'runup': '遡上の上限 η + R',
 'Hm0': 'H_m0(砕波と上限あり)',
 'Hsh': '浅水変形だけ(砕波なし)',
 'Hlim': '水深による上限 √2 γmax h',
 'yH': 'H_m0 (m)',
 'Dw': '砕波の散逸 D_w(波 → ローラー)',
 'Dr': 'ローラーの散逸 D_r(ここで運動量を放す)',
 'yD': 'W/m²',
 'roll1': 'ローラーあり(既定)',
 'roll0': 'ローラーなし',
 'ye': 'η (m)',
 'sdown': 'セットダウン',
 'sup': 'セットアップ',
 'yv': 'v (m/s)',
 'vshift': 'ローラーで最大が岸側へ',
 'xlab': '岸沖方向の位置 x (m)。静水の汀線 = 0、沖が負',
 'note': '(b)〜(e) は勾配 1/80 の海浜に H_m0 = 1.5 m・T = 8 s・進行方向 20° の不規則波(単一方向)を入れた 1 次元の定常の釣り合いを、解説 §2・§5・§6 の式と章の既定値(マニングの粗度 0.025、水平混合なし)で解いた説明用の例で、ENCflow の計算結果ではない。',
 'fcrest': '波の山', 'ftrough': '波の谷', 'fbed': '海底', 'fshore': '岸 →',
 'fstokes': 'Stokes 輸送 u^S: 波とローラーが運ぶ質量(谷より上に集中)',
 'fund': '戻り流れ: 底層の離岸方向の流れ',
 'fuL': '浅水流の流速(出力 u・v)は水深平均の Lagrangian 流速 u^L = 水の質量輸送。閉じた海浜では正味の流量 0 で u^L ≈ 0',
 'fuE': '底面摩擦はオイラー流速 u^E = u^L − u^S(戻り流れ)と波の軌道流速 u_rms で決まる',
 'gstorm': '高波浪: 戻り流れが勝ち、砂は沖へ(砂州ができる)',
 'gcalm': '低波浪・うねり(砕波帯より沖): 岸向きの速度が勝ち、砂は岸へ(浜の回復)',
 'gua': 'u_a: 波の歪度・非対称による岸向きの速度',
 'guE': 'u^E: 戻り流れ',
 'gus': '砂を運ぶ速度 u_s = u^E + u_a',
 'gnote': '波の軌道流速が砂を攪拌し、u_s が運ぶ。釣り合いは wfsed_facsk・wfsed_facas に敏感(校正の量)。',
 'gshore': '汀線',
}, 'en': {
 'pa': '(a) A straight coast: the setting and what the wave field computes',
 'pb': '(b) Sides crossing the coast: Neumann vs absorbing',
 'pc': '(c) Direction convention',
 'pd': '(d) Cells waves pass through and cells they do not',
 'side1': '1 incident: offshore waves (wf_hm0, wf_trep, wf_dir, wf_spread)',
 'side2': '2 lateral Neumann: the same sea continues outside the side',
 'side0': '0 absorbing (landward side; any type will do)',
 'bcset': 'input: wf_bc_side = 1, 0, 2, 2 (sides W, E, N, S); sea-bed topography, direction 20°',
 'land': 'land',
 'surf': 'surf zone',
 'shoal': 'shoaling: height grows in shallower water',
 'refr': 'refraction: crests turn to follow the depth contours',
 'shadow': 'shadow',
 'bw': 'breakwater',
 'crest': 'white lines: wave crests (illustration; line width = wave height; the phase-averaged model solves height and direction)',
 'ray': 'navy arrows: wave rays (normal to the crests)',
 'neu': 'lateral Neumann (2)',
 'abs': 'absorbing (0)',
 'neu_note': 'oblique waves from outside arrive; uniform alongshore',
 'abs_note': 'the waves from outside are missing: a false shadow near the side',
 'hh0': 'height ratio H/H₀',
 'b_note': 'Uniform depth, no breaking. Waves of direction 20° and spreading 20° enter from the offshore side (left); computed with rays for each direction (no numerical diffusion). Contours 0.95, 0.8, 0.5',
 'travel': 'travelling to',
 'from': 'coming from',
 'east': 'east 0°\n(x axis)', 'north': 'north 90°', 'west': 'west 180°', 'south': 'south 270°',
 'ex': 'wf_dir and the output Wa give the direction of travel θ counterclockwise from the x axis (east); the example is θ = 20°.',
 'naut': 'The nautical convention (SWAN, XBeach, ...) measures the coming-from direction θ_n clockwise from north. Convert with θ = 270° − θ_n (grid with the x axis to the east); θ_n of the example is 250°, not a difference of 180°.',
 'ysign': 'y components of the output (v, Wfy, Wsy, Qby, Qsy) are positive to the south, unlike the direction convention (north = 90°).',
 'ax_i': 'column i: to the east',
 'ax_j': 'row j: to the south',
 'up': 'θ = 90° (north)',
 'vpos': 'v > 0 (southward)',
 'cw': 'wave cell (depth > wf_hmin)',
 'cdry': 'dry cell, depth ≤ wf_hmin',
 'cland': 'land',
 'csw': 'sea-mask sea cell sw (tide boundary; not computed by the flow either)',
 'cabs': 'absorbing cell: building porosity gv < 1',
 'cabs2': 'absorbing cell: subgrid channel width or cross-section',
 'cdike': 'land (one-cell-thick diagonal dike)',
 'rule1': 'Waves heading for any cell other than a wave cell are absorbed (no reflection; absorbed in the ledger).',
 'rule2': 'If both cells sharing a corner are non-wave cells, that diagonal (✕) is closed: waves do not slip through a diagonal dike (deliberately unlike the shallow water flow, which passes water through a one-cell-wide diagonal channel).',
 'rule3': 'Waves do not enter from outside a band of sea cells: make the cells next to the incident side wave cells.',
 # profile
 'qa': '(a) Waves and flow across the shore (vertical scale × 37)',
 'qb': '(b) Wave height',
 'qc': '(c) Dissipation by breaking and by the roller',
 'qd': '(d) Mean water level',
 'qe': '(e) Longshore current (oblique incidence, direction 20°)',
 'qf': '(f) Vertical structure (wf_flow = 2)',
 'qg': '(g) Velocity carrying sand (f_wfsed)',
 'off': 'offshore waves (incident side)',
 'shoal2': 'shoaling: height grows',
 'brk0': 'breaking begins',
 'surf2': 'surf zone: broken waves dissipate\nthrough the roller (surface eddy on the crest)',
 'env': 'dashed: wave height H_m0 solved by the model (envelope; individual waves are not solved)',
 'inst': 'solid: water surface at one instant (illustration)',
 'mwl': 'mean water level (set-down, set-up)',
 'shore': 'shoreline (depth wf_hmin)',
 'swash': 'swash zone: not solved by the phase-averaged wave field (f_wfswash moves sand there with empirical formulas)',
 'runup': 'runup limit η + R',
 'Hm0': 'H_m0 (with breaking and the limit)',
 'Hsh': 'shoaling only (no breaking)',
 'Hlim': 'depth limit √2 γmax h',
 'yH': 'H_m0 (m)',
 'Dw': 'breaking dissipation D_w (waves → roller)',
 'Dr': 'roller dissipation D_r (momentum released here)',
 'yD': 'W/m²',
 'roll1': 'with roller (default)',
 'roll0': 'without roller',
 'ye': 'η (m)',
 'sdown': 'set-down',
 'sup': 'set-up',
 'yv': 'v (m/s)',
 'vshift': 'the roller moves the peak shoreward',
 'xlab': 'cross-shore position x (m); still-water shoreline = 0, offshore negative',
 'note': '(b)–(e): steady 1-D balance for random waves (single direction) of H_m0 = 1.5 m, T = 8 s and direction 20° on a 1/80 beach, solved with the formulas of the explanation (sec. 2, 5, 6) and the defaults of the chapter (Manning n = 0.025, no horizontal mixing). An illustration, not an ENCflow result.',
 'fcrest': 'crest', 'ftrough': 'trough', 'fbed': 'sea bed', 'fshore': 'shore →',
 'fstokes': 'Stokes transport u^S: mass carried by the waves and the roller (concentrated above the trough)',
 'fund': 'undertow: offshore flow near the bed',
 'fuL': 'The shallow water velocity (output u, v) is the depth-mean Lagrangian velocity u^L = the mass transport of water. On a closed beach the net flux is 0, so u^L ≈ 0',
 'fuE': 'Bed friction acts with the Eulerian velocity u^E = u^L − u^S (the undertow) and the wave orbital velocity u_rms',
 'gstorm': 'high waves: the undertow wins and sand moves offshore (a bar forms)',
 'gcalm': 'low waves, swell (outside the surf zone): the onshore velocity wins and sand moves onshore (beach recovery)',
 'gua': 'u_a: onshore velocity by wave skewness and asymmetry',
 'guE': 'u^E: undertow',
 'gus': 'velocity carrying sand u_s = u^E + u_a',
 'gnote': 'The orbital velocity stirs the sand and u_s carries it. The balance is sensitive to wfsed_facsk and wfsed_facas (calibration).',
 'gshore': 'shoreline',
}}

DEEP, SHALLOW = '#a8c8ea', '#e6f0fb'
NAVY = '#1d4f91'
SKY = '#8fb3dc'
CMAP = LinearSegmentedColormap.from_list('wf', ['#ffffff', '#d6e6f8', '#8db9ea', '#4a8fdc'])
CELL = {'W': '#cfe0f6', 'S': '#5aa0d8', 'K': '#8c7b63', 'D': '#f1ece3', 'L': SOIL, 'B': '#c9c6bf', 'C': '#c9c6bf'}


# ----------------------------------------------------------------------------- physics
def beach_profile(hm0=1.5, T=8.0, th0=20.0, slope=1 / 80, x0=-1000.0, dx=0.5, roller=True,
                  gamma=0.78, alpha=1.0, gammax=0.6, beta=0.1, nman=0.025, hmin=0.1, iters=4):
    """Steady 1-D waves, roller, set-up and longshore current on a plane beach (shoreline x = 0).

    Single direction refracting by Snell's law; Baldock et al. (1998) breaking with
    H_b = (0.88/k) tanh(gamma k h/0.88) and the limit H_rms <= gammax h feeding the
    roller (D_r = 2 beta g E_r/c); radiation stress with the roller; GLM: the closed
    beach has u^L = 0, so the bed sees the undertow u^E = -u^S, and the friction speed
    includes 1.16 u_rms (wf_flow = 2).  No horizontal mixing.  The defaults of the
    chapter (wf_gamma, wf_alpha, wf_gammax, wf_beta, wf_hmin) and Manning n = 0.025.
    The water depth includes the set-up (a few outer iterations).
    """
    sig, f = 2 * np.pi / T, 1 / T
    xall = np.arange(x0, 60.0, dx)
    eta = np.zeros_like(xall)
    for _ in range(iters):
        hall = -xall * slope + eta
        nw = int(np.argmax(hall <= hmin))
        x, h = xall[:nw], hall[:nw]
        k = wavenumber(sig, h)
        n, c, cg = group(sig, k, h)
        th = np.arcsin(np.sin(np.radians(th0)) * k[0] / k)
        cth = np.cos(th)
        Hb = 0.88 / k * np.tanh(gamma * k * h / 0.88)

        def dw(E, i):
            Hr = np.sqrt(8 * max(E, 0.0) / (RHO * G))
            if Hr <= 0:
                return 0.0
            return alpha / 4 * RHO * G * f * np.exp(-(Hb[i] / Hr)**2) * (Hb[i]**2 + Hr**2)
        E, Er = np.zeros_like(x), np.zeros_like(x)
        Dw, Dl, Dr = np.zeros_like(x), np.zeros_like(x), np.zeros_like(x)
        E[0] = RHO * G * hm0**2 / 16
        for i in range(len(x) - 1):                            # energy flux, midpoint rule
            F = E[i] * cg[i] * cth[i]
            Em = (F - 0.5 * dx * dw(E[i], i)) / (0.25 * (cg[i] + cg[i + 1]) * (cth[i] + cth[i + 1]))
            Dw[i] = dw(Em, i)
            En = max(F - dx * Dw[i], 0.0) / (cg[i + 1] * cth[i + 1])
            Emax = RHO * G * (gammax * h[i + 1])**2 / 8
            if En > Emax:
                Dl[i + 1] = (En - Emax) * cg[i + 1] * cth[i + 1] / dx
                En = Emax
            E[i + 1] = En
        Dw[-1] = dw(E[-1], len(x) - 1)
        Db = Dw + Dl
        if roller:                                             # roller energy flux R = E_r c cos(theta)
            R = 0.0
            for i in range(len(x) - 1):
                Er[i] = R / (c[i] * cth[i])
                k1 = Db[i] - 2 * beta * G * R / (c[i]**2 * cth[i])
                Rm = max(R + 0.5 * dx * k1, 0.0)
                k2 = 0.5 * (Db[i] + Db[i + 1]) - 2 * beta * G * Rm / (0.25 * (c[i] + c[i + 1])**2 * 0.5 * (cth[i] + cth[i + 1]))
                R = max(R + dx * k2, 0.0)
            Er[-1] = R / (c[-1] * cth[-1])
            Dr = 2 * beta * G * Er / c
        Hrms = np.sqrt(8 * E / (RHO * G))
        Sxx = E * (n * cth**2 + n - 0.5) + Er * cth**2
        Sxy = (E * n + Er) * cth * np.sin(th)
        Fx, Fy = -np.gradient(Sxx, x), -np.gradient(Sxy, x)
        us = (E + 2 * Er) / (RHO * h * c)
        usx, usy = us * cth, us * np.sin(th)
        urms = Hrms * sig / (2 * np.sqrt(2) * np.sinh(k * h))
        uE = -usx
        cf = G * nman**2 / h**(1 / 3)
        vE = np.zeros_like(x)
        for i in np.where(Fy > 0)[0]:                         # rho cf |u_E| v_E = F_y
            lo, hi = 0.0, 5.0
            for _ in range(60):
                v = 0.5 * (lo + hi)
                lo, hi = (v, hi) if RHO * cf[i] * np.sqrt(uE[i]**2 + v**2 + (1.16 * urms[i])**2) * v < Fy[i] else (lo, v)
            vE[i] = 0.5 * (lo + hi)
        dedx = (Fx / RHO - cf * np.sqrt(uE**2 + vE**2 + (1.16 * urms)**2) * uE) / (G * h)
        et = np.concatenate([[0], np.cumsum(0.5 * (dedx[1:] + dedx[:-1]) * np.diff(x))])
        eta = np.interp(xall, x, et, right=et[-1])
    Hsh = np.sqrt(8 * E[0] / (RHO * G)) * np.sqrt(cg[0] * cth[0] / (cg * cth))
    return dict(x=x, h=h, Hm0=np.sqrt(2) * Hrms, Hsh=np.sqrt(2) * Hsh, th=th, k=k, E=E, Er=Er, Dw=Dw, Dr=Dr,
                Db=Db, Fx=Fx, Fy=Fy, usx=usx, usy=usy, urms=urms, vE=vE, vL=vE + usy, eta=et)


# ----------------------------------------------------------------------------- plan
XS, LX, LY = 1100.0, 1200.0, 900.0      # shoreline, domain (m)
SLOPE, T0, TH0 = 1 / 80, 8.0, 20.0      # beach slope, period (s), offshore direction (deg)
XB, YB = 700.0, (400.0, 545.0)           # breakwater


def beach_rays():
    """Snell's law on the plane beach: direction, ray offset and crest phase against x."""
    sig = 2 * np.pi / T0
    x = np.linspace(0, XS - 8, 1500)
    h = (XS - x) * SLOPE
    k = wavenumber(sig, h)
    th = np.arcsin(np.sin(np.radians(TH0)) * k[0] / k)     # k sin(theta) = const
    dy = np.concatenate([[0], np.cumsum(0.5 * (np.tan(th[1:]) + np.tan(th[:-1])) * np.diff(x))])
    ph = np.concatenate([[0], np.cumsum(0.5 * (k[1:] * np.cos(th[1:]) + k[:-1] * np.cos(th[:-1])) * np.diff(x))])
    return x, dy, ph, k[0] * np.sin(np.radians(TH0))


def panel_plan(ax, t, X0, Y0, W):
    from matplotlib.collections import LineCollection
    s = W / LX
    P = lambda x, y: (X0 + x * s, Y0 + (LY - y) * s)          # north up
    Hp = LY * s
    gh = 44                                                     # ghost strip height (px)
    for yy in (Y0 - gh, Y0 + Hp):                               # ghost strips (lateral Neumann)
        rect(ax, X0, yy, XS * s, gh, '#eef4fb', SKY, 1.0, ls=(0, (4, 3)), zorder=1)
        rect(ax, X0 + XS * s, yy, (LX - XS) * s, gh, '#f3eee6', '#c9bba5', 1.0, ls=(0, (4, 3)), zorder=1)
    n = 80                                                      # sea with depth shading
    c0, c1 = np.array(matplotlib.colors.to_rgb(DEEP)), np.array(matplotlib.colors.to_rgb(SHALLOW))
    for i in range(n):
        f = (i + 0.5) / n
        rect(ax, P(XS * i / n, 0)[0], Y0, XS / n * s + 0.6, Hp, tuple((1 - f) * c0 + f * c1), zorder=2)
    rect(ax, P(XS, 0)[0], Y0, (LX - XS) * s, Hp, SOIL, zorder=2)
    pr = beach_profile(hm0=1.5, T=T0, th0=TH0, slope=SLOPE, x0=-XS)   # wave height for the crest widths
    xp, Hp_ = pr['x'] + XS, pr['Hm0']
    xbr = xp[np.argmax(pr['Dw'] > 0.1 * pr['Dw'].max())]       # surf zone: breaking above 10 % of its peak
    rect(ax, P(xbr, 0)[0], Y0, (XS - xbr) * s, Hp, '#f4f9fe', zorder=3, alpha=0.8)
    for d in (10, 5, 2):                                        # depth contours
        xc = XS - d / SLOPE
        line(ax, [P(xc, -gh / s), P(xc, LY + gh / s)], '#5d87b8', 0.9, ls=(0, (5, 3)), z=4)
        p = P(xc, 18)
        text(ax, p[0] + 4, p[1], f'{d} m', 8.5, color='#3e6a9e', va='bottom',
             bbox=dict(fc='white', ec='none', alpha=0.7, pad=1))
    x, dy, ph, ky = beach_rays()
    bw_lo, bw_hi = YB
    yb_lo = bw_lo + dy - np.interp(XB, x, dy)                   # rays through the breakwater ends
    yb_hi = bw_hi + dy - np.interp(XB, x, dy)
    ylo, yhi = -gh / s, LY + gh / s
    Hx = np.interp(x, xp, Hp_)
    segs, widths, cols = [], [], []
    for m in range(1, int(ph[-1] / (2 * np.pi)) + 1, 2):        # every second crest
        yc = (m * 2 * np.pi - ph) / ky
        for i in range(0, len(x) - 3, 3):
            i2 = i + 3
            if not (ylo < yc[i] < yhi and ylo < yc[i2] < yhi):
                continue
            xm, ym = 0.5 * (x[i] + x[i2]), 0.5 * (yc[i] + yc[i2])
            if xm > XB and np.interp(xm, x, yb_lo) < ym < np.interp(xm, x, yb_hi):
                continue                                        # no crests in the shadow
            segs.append([P(x[i], yc[i]), P(x[i2], yc[i2])])
            widths.append(0.4 + 2.6 * Hx[i] / Hp_.max())        # width ~ wave height
            cols.append('white' if xm < xbr else '#7ea7d4')
    ax.add_collection(LineCollection(segs, linewidths=widths, colors=cols, zorder=5, capstyle='round'))
    xs_ = x[x >= XB]                                            # shadow
    poly = [P(a, b) for a, b in zip(xs_, np.interp(xs_, x, yb_lo))] + \
           [P(a, b) for a, b in zip(xs_[::-1], np.interp(xs_[::-1], x, yb_hi))]
    ax.add_patch(Polygon(poly, fc='#6b6a66', ec='none', alpha=0.22, zorder=4))
    rect(ax, P(XB, bw_hi)[0] - 4, P(XB, bw_hi)[1], 9, (bw_hi - bw_lo) * s, '#4a4946', zorder=8)
    for y0 in (-30.0, 150.0, 300.0, 610.0):                     # rays
        yy = y0 + dy
        keep = yy < LY + 0.6 * gh / s
        yhit = y0 + np.interp(XB, x, dy)
        if bw_lo < yhit < bw_hi:
            keep &= x <= XB - 6
        xx, yy = x[keep], yy[keep]
        arrow(ax, [P(a, b) for a, b in zip(xx[::25], yy[::25])] + [P(xx[-1], yy[-1])], NAVY, 1.4, size=10, z=9)
    rect(ax, X0, Y0, W, Hp, 'none', INK, 1.6, zorder=10)        # domain
    for yy in np.linspace(90, 810, 6):                          # offshore waves at the incident side
        a = P(-115, yy - 115 * np.tan(np.radians(TH0)))
        arrow(ax, [a, P(-8, yy)], ORANGE, 1.8, size=11, z=10)
    text(ax, X0 - 98, Y0 + Hp / 2, t['side1'], 9.5, color=ORANGE, ha='center', va='center', rotation=90)
    text(ax, X0 + W + 14, Y0 + Hp / 2, t['side0'], 9.5, color=MUTED, ha='center', va='center', rotation=270)
    text(ax, X0 + 8, Y0 - gh + 12, t['side2'], 9.5, color='#3e6a9e')
    text(ax, X0 + 8, Y0 + Hp + 12, t['side2'], 9.5, color='#3e6a9e')
    p = P(XS + 50, LY * 0.5)
    text(ax, p[0], p[1], t['land'], 10, color=BED, ha='center', va='center')
    p = P(0.5 * (xbr + XS), 120)
    text(ax, p[0], p[1], t['surf'], 9, color=NAVY, ha='center', va='center',
         bbox=dict(fc='white', ec='none', alpha=0.8, pad=2))
    p = P(XB + 160, 482)
    text(ax, p[0], p[1], t['shadow'], 10.5, color=INK, ha='center', va='center', weight='bold')
    p = P(XB - 6, bw_lo)
    text(ax, p[0] - 6, p[1] + 2, t['bw'], 8.8, color=INK, ha='right')
    p = P(300, 150)
    text(ax, p[0], p[1], t['shoal'], 9, color=NAVY, ha='left', va='center',
         bbox=dict(fc='white', ec='none', alpha=0.8, pad=2))
    p = P(150, 860)
    text(ax, p[0], p[1], t['refr'], 9, color=NAVY, ha='left', va='center',
         bbox=dict(fc='white', ec='none', alpha=0.8, pad=2))
    return Hp, gh


def lateral_maps(ax, t, fig, X0, Y0, w=300, h=180, gap=46):
    """Exact-ray wave height near Neumann and absorbing lateral sides (uniform depth)."""
    s = spreading_exponent(20.0)
    th = np.radians(TH0) + np.radians(np.linspace(-89.9, 89.9, 1801))
    wt = np.cos(th - np.radians(TH0))**s
    wt /= wt.sum()
    fwd = np.cos(th) > 0
    L, Wd = 80.0, 48.0
    xs, ys = np.linspace(0.25, L - 0.25, 160), np.linspace(0.25, Wd - 0.25, 96)
    XX, YY = np.meshgrid(xs, ys)
    E_abs = np.zeros_like(XX)
    for tm, wm in zip(th[fwd], wt[fwd]):
        y0 = YY - XX * np.tan(tm)
        E_abs += wm * ((y0 >= 0) & (y0 <= Wd))
    E_neu = np.full_like(XX, wt[fwd].sum())
    im, ybot = None, 0
    for k, (E, key, note) in enumerate([(E_neu, 'neu', 'neu_note'), (E_abs, 'abs', 'abs_note')]):
        px = X0 + k * (w + gap)
        a = plot_axes(fig, px, Y0, w, h)
        im = a.imshow(np.sqrt(E), origin='lower', extent=(0, L, 0, Wd), cmap=CMAP, vmin=0, vmax=1.0,
                      interpolation='bilinear', aspect='auto')
        if key == 'abs':
            a.contour(XX, YY, np.sqrt(E), levels=[0.5, 0.8, 0.95], colors=[INK], linewidths=0.8,
                      linestyles=[':', '--', '-'])
        a.set_xticks([]); a.set_yticks([])
        for sp in a.spines.values():
            sp.set_visible(False)
        col, ls = (SKY, (0, (3, 2))) if key == 'neu' else (MUTED, '-')
        for yy in (0, Wd):
            a.plot([0, L], [yy, yy], color=col, lw=3.0, ls=ls, clip_on=False, solid_capstyle='butt')
        a.plot([0, 0], [0, Wd], color=ORANGE, lw=3.0, clip_on=False, solid_capstyle='butt')
        a.plot([L, L], [0, Wd], color=MUTED, lw=1.0, clip_on=False)
        for yy in (10, 22, 34):
            a.annotate('', xy=(11, yy + 11 * np.tan(np.radians(TH0))), xytext=(1.0, yy),
                       arrowprops=dict(arrowstyle='-|>', color=ORANGE, lw=1.4))
        text(ax, px, Y0 - 28, t[key], 10, color=INK, weight='bold')
        ybot = max(ybot, paragraph(ax, px, Y0 + h + 10, t[note], w, 8.8, MUTED))
    cax = plot_axes(fig, X0, ybot + 38, 2 * w + gap, 12)
    cb = fig.colorbar(im, cax=cax, orientation='horizontal', ticks=[0, 0.25, 0.5, 0.75, 1.0])
    cb.ax.tick_params(labelsize=8.5)
    cb.outline.set_linewidth(0.6)
    text(ax, X0, ybot + 12, t['hh0'], 9, color=INK)
    return ybot + 84


def panel_compass(ax, t, cx, cy, r):
    ax.add_patch(Circle((cx, cy), r, fc='#f7f9fc', ec=RULE, lw=1.2, zorder=2))
    for d in range(0, 360, 45):
        a = np.radians(d)
        line(ax, [(cx + 0.9 * r * np.cos(a), cy - 0.9 * r * np.sin(a)), (cx + r * np.cos(a), cy - r * np.sin(a))],
             MUTED, 1.0, z=3)
    line(ax, [(cx - r, cy), (cx + r, cy)], RULE, 0.9, z=2)
    line(ax, [(cx, cy - r), (cx, cy + r)], RULE, 0.9, z=2)
    text(ax, cx + r + 8, cy, t['east'], 9, color=INK, va='center')
    text(ax, cx, cy - r - 6, t['north'], 9, color=INK, ha='center', va='bottom')
    text(ax, cx - r - 8, cy, t['west'], 9, color=INK, ha='right', va='center')
    text(ax, cx, cy + r + 6, t['south'], 9, color=INK, ha='center')
    a = np.radians(TH0)
    u = np.array([np.cos(a), -np.sin(a)])                      # screen direction of travel (y down)
    c = np.array([cx, cy])
    arrow(ax, [c, c + 0.95 * r * u], ORANGE, 2.4, size=13, z=8)
    ax.add_patch(Arc((cx, cy), 1.3 * r, 1.3 * r, theta1=-TH0, theta2=0, color=ORANGE, lw=1.3, zorder=7))
    q = c + (0.65 * r + 9) * np.array([np.cos(np.radians(10)), -np.sin(np.radians(10))])
    text(ax, q[0], q[1], 'θ', 10, color=ORANGE, va='center')
    text(ax, *(c + 0.95 * r * u + [0, -8]), t['travel'], 9, color=ORANGE, ha='center', va='bottom')
    arrow(ax, [c - 0.95 * r * u, c - 0.10 * r * u], BLUE, 1.5, ls=(0, (4, 2)), size=11, z=7)
    text(ax, *(c - 0.95 * r * u + [0, 8]), t['from'], 9, color=BLUE, ha='center', va='top')
    # nautical: clockwise from north (screen 90 deg) to the coming-from direction (screen 200 deg).
    # The canvas y axis points down, so in data space the arc runs counterclockwise from -90 to +160 deg.
    rn = 0.42 * r
    ax.add_patch(Arc((cx, cy), 2 * rn, 2 * rn, theta1=-90, theta2=160, color=BLUE, lw=1.2,
                     ls=(0, (3, 2)), zorder=7))
    pa = [(cx + rn * np.cos(np.radians(g)), cy + rn * np.sin(np.radians(g))) for g in (150, 160)]
    arrow(ax, pa, BLUE, 1.2, size=9, z=7)
    q = c + (rn + 12) * np.array([np.cos(np.radians(35)), np.sin(np.radians(35))])
    text(ax, q[0], q[1], 'θ_n', 10, color=BLUE, va='center')


def panel_rows(ax, t, x0, y0, d):
    """Grid orientation: i to the east, j to the south; the direction convention against the y components."""
    grid(ax, x0, y0, 3, 3, d)
    rect(ax, x0, y0, 3 * d, 3 * d, 'none', INK, 1.2, zorder=6)
    arrow(ax, [(x0, y0 - 16), (x0 + 3 * d + 22, y0 - 16)], MUTED, 1.2, size=9, z=7)
    text(ax, x0 + 3 * d + 28, y0 - 16, t['ax_i'], 8.8, color=MUTED, va='center')
    arrow(ax, [(x0 - 16, y0), (x0 - 16, y0 + 3 * d + 22)], MUTED, 1.2, size=9, z=7)
    text(ax, x0 - 4, y0 + 3 * d + 18, t['ax_j'], 8.8, color=MUTED, va='center')
    c = np.array([x0 + 1.5 * d, y0 + 1.5 * d])
    arrow(ax, [c + [-12, 0], c + [-12, -1.35 * d]], ORANGE, 2.0, size=11, z=8)
    text(ax, x0 + 3 * d + 12, y0 + 0.45 * d, t['up'], 8.8, color=ORANGE, va='center')
    arrow(ax, [c + [12, 0], c + [12, 1.35 * d]], NAVY, 2.0, size=11, z=8)
    text(ax, x0 + 3 * d + 12, y0 + 2.55 * d, t['vpos'], 8.8, color=NAVY, va='center')


def panel_cells(ax, t, X0, Y0, d):
    """W wave, S sea cell sw, K dike (land), D dry, L land, B building, C subgrid channel."""
    rows = ['SSWWWWWWWDLLL',
            'SSWWWWKWWDLLL',
            'WWWWWKWWWDBBL',
            'WWWWKWWWDLBBL',
            'WWWWWWWWDCCCC',
            'WWWWWWWWDLLLL']
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            x, y = X0 + i * d, Y0 + j * d
            rect(ax, x, y, d, d, CELL[ch], zorder=2)
            if ch == 'B':
                rect(ax, x + d * .24, y + d * .24, d * .52, d * .52, '#8a8780', zorder=3)
            if ch == 'C':
                line(ax, [(x, y + .5 * d), (x + d, y + .5 * d)], BLUE, 2.4, z=3)
            if ch == 'S':
                for q in range(3):
                    line(ax, [(x + 5, y + (q + .5) * d / 3), (x + d - 5, y + (q + .5) * d / 3)], 'white', 0.9, z=3)
    grid(ax, X0, Y0, len(rows[0]), len(rows), d)
    rect(ax, X0, Y0, len(rows[0]) * d, len(rows) * d, 'none', INK, 1.4, zorder=6)
    c = lambda i, j: np.array([X0 + (i + .5) * d, Y0 + (j + .5) * d])
    for j in (2, 3, 4, 5):                                      # waves entering from the incident side
        arrow(ax, [c(0, j) - [d * .75, 0], c(0, j) + [d * .2, 0]], ORANGE, 1.6, size=10, z=7)
    for j in (0, 1):                                            # no entry through the band of sea cells
        p = c(0, j) - [d * .75, 0]
        arrow(ax, [p, p + [d * .3, 0]], ORANGE, 1.3, ls=(0, (2, 2)), size=8, z=7)
    a, b = c(5, 1), c(6, 2)                                     # closed diagonal across the dike corner
    line(ax, [a, b], ORANGE, 1.6, ls=(0, (3, 2)), z=8)
    m = (a + b) / 2
    for sg in (1, -1):
        line(ax, [m + [-7, -7 * sg], m + [7, 7 * sg]], '#c0392b', 2.6, z=9)
    for (i, j) in [(8, 1), (7, 3), (7, 4)]:                     # absorbed toward non-wave cells
        p = c(i, j)
        arrow(ax, [p - [d * .30, 0], p + [d * .48, 0]], NAVY, 1.2, size=8, z=7)
    return len(rows[0]) * d, len(rows) * d


def cell_legend(ax, t, x, y, d=26, width=560):
    items = [('W', 'cw'), ('D', 'cdry'), ('L', 'cland'), ('K', 'cdike'), ('S', 'csw'), ('B', 'cabs'), ('C', 'cabs2')]
    for k, (ch, key) in enumerate(items):
        yy = y + k * 38
        rect(ax, x, yy, d, d, CELL[ch], RULE, 0.8, zorder=2)
        if ch == 'B':
            rect(ax, x + d * .24, yy + d * .24, d * .52, d * .52, '#8a8780', zorder=3)
        if ch == 'C':
            line(ax, [(x, yy + .5 * d), (x + d, yy + .5 * d)], BLUE, 2.0, z=3)
        if ch == 'S':
            for q in range(3):
                line(ax, [(x + 3, yy + (q + .5) * d / 3), (x + d - 3, yy + (q + .5) * d / 3)], 'white', 0.8, z=3)
        paragraph(ax, x + d + 12, yy + 3, t[key], width - d - 12, 9)
    return y + len(items) * 38


def build_plan(lang):
    t = T[lang]
    fig, ax = canvas(1800)
    text(ax, 40, 22, t['pa'], 12.5, weight='bold')
    Hp, gh = panel_plan(ax, t, 150, 120, 860)
    yb = 120 + Hp + gh + 16
    text(ax, 150, yb, t['bcset'], 9.5, color=INK)
    text(ax, 150, yb + 28, t['crest'], 9, color=MUTED)
    text(ax, 150, yb + 52, t['ray'], 9, color=MUTED)
    text(ax, 1100, 22, t['pb'], 12.5, weight='bold')
    yb2 = lateral_maps(ax, t, fig, 1110, 110)
    yb2 = paragraph(ax, 1110, yb2, t['b_note'], 650, 8.8, MUTED)
    yc = max(yb2 + 20, 520)
    text(ax, 1100, yc, t['pc'], 12.5, weight='bold')
    panel_compass(ax, t, 1225, yc + 172, 95)
    panel_rows(ax, t, 1440, yc + 97, 44)
    y = paragraph(ax, 1420, yc + 287, t['ysign'], 360, 9, NAVY)
    y = max(y, yc + 340)
    for key, colr in [('ex', ORANGE), ('naut', BLUE)]:
        y = paragraph(ax, 1100, y, t[key], 680, 9, colr, gap=6)
    y0 = max(y, 905) + 24
    text(ax, 40, y0, t['pd'], 12.5, weight='bold')
    gw, gh2 = panel_cells(ax, t, 110, y0 + 58, 46)
    cell_legend(ax, t, 110 + gw + 50, y0 + 58, width=1800 - (110 + gw + 50) - 30)
    y = y0 + 58 + gh2 + 22
    for key in ('rule1', 'rule2', 'rule3'):
        y = paragraph(ax, 110, y, t[key], 1650, 9, MUTED, gap=6)
    fit_height(fig, ax, y + 20)
    return fig


# ----------------------------------------------------------------------------- profile
XMIN, XMAX = -600.0, 60.0


def runup_amplitude(H0, T, beta):
    """Swash amplitude R = 1.1 S/2 of Stockdon et al. (2006) eq. 19 without the set-up (explanation sec. 9.3)."""
    L0 = G * T**2 / (2 * np.pi)
    return 1.1 * np.sqrt(H0 * L0 * (0.563 * beta**2 + 0.004)) / 2


def bore_shape(psi, b):
    """Cosine (b = 0) blended into a forward-leaning bore (b = 1); crests at psi = pi mod 2 pi."""
    saw = np.zeros_like(psi)
    N = 9
    for n in range(1, N):
        saw += np.sinc(n / N) * (2 / np.pi) * (-1)**(n + 1) * np.sin(n * psi) / n
    return (1 - b) * (-np.cos(psi)) + b * saw


def schematic(fig, pr, X0, Y0, W, H):
    a = plot_axes(fig, X0, Y0, W, H)
    zmin, zmax = -4.0, 1.6
    a.set(xlim=(XMIN, XMAX), ylim=(zmin, zmax))
    a.axis('off')
    M = lambda x, z: (X0 + (x - XMIN) / (XMAX - XMIN) * W, Y0 + (zmax - z) / (zmax - zmin) * H)
    x, eta, Hm = pr['x'], pr['eta'], pr['Hm0']
    xs = np.linspace(XMIN, XMAX, 1600)
    zb = xs * SLOPE
    a.fill_between(xs, zmin, zb, color=SOIL, lw=0, zorder=1)
    a.plot(xs, zb, color=BED, lw=1.3, zorder=3)
    # snapshot of the surface: phase from the cross-shore wavenumber, amplitude H_m0/2
    k = np.interp(xs, x, pr['k'] * np.cos(pr['th']))
    psi = np.concatenate([[0], np.cumsum(0.5 * (k[1:] + k[:-1]) * np.diff(xs))]) + 2.2
    i_pk = np.argmax(pr['Dw'])
    xb0 = x[np.argmax(pr['Dw'] > 0.1 * pr['Dw'].max())]
    bmix = np.clip((xs - xb0) / (x[i_pk] - xb0), 0, 1)
    wet = xs <= x[-1]
    zeta = np.interp(xs, x, eta)
    zs = np.where(wet, zeta + 0.5 * np.interp(xs, x, Hm) * bore_shape(psi, bmix), np.nan)
    a.fill_between(xs[wet], zb[wet], zs[wet], where=zs[wet] > zb[wet], color=WATER, lw=0, zorder=2)
    a.plot(xs[wet], zs[wet], color=BLUE, lw=1.4, zorder=5)
    a.plot(x, eta + Hm / 2, color=NAVY, lw=1.0, ls=(0, (4, 3)), zorder=6)
    a.plot(x, eta - Hm / 2, color=NAVY, lw=1.0, ls=(0, (4, 3)), zorder=6)
    a.plot([XMIN, XMAX], [0, 0], color=MUTED, lw=0.7, ls=':', zorder=4)
    a.plot(x, eta, color='#c0392b', lw=1.2, zorder=6)
    # rollers: white water on the front of the crests where the roller holds energy
    er = np.interp(xs, x, pr['Er'])
    crest = np.where((np.diff(np.sign(np.diff(np.nan_to_num(zs, nan=-9)))) < 0) & wet[1:-1])[0] + 1
    for ic in crest:
        if er[ic] > 0.12 * pr['Er'].max():
            L = 2 * np.pi / k[ic]
            sel = (xs > xs[ic] - 0.02 * L) & (xs < xs[ic] + 0.05 * L) & wet
            a.plot(xs[sel], zs[sel], color='#b7c4d3', lw=6.0, solid_capstyle='round', zorder=7)
            a.plot(xs[sel], zs[sel], color='white', lw=4.2, solid_capstyle='round', zorder=8)
    # swash zone up to the runup limit eta_s + R
    xsh = x[-1]
    es = eta[-1]
    R = runup_amplitude(1.5, T0, SLOPE)
    xr = (es + R) / SLOPE
    xm = es / SLOPE
    sw = (xs >= xsh) & (xs <= xr)
    thick = 0.06 * np.clip((xr - xs[sw]) / (xr - xm), 0, 1)
    a.fill_between(xs[sw], zb[sw], zb[sw] + thick + 0.02, color='#9cc3ea', lw=0, zorder=4)
    for xx in (xsh, xr):
        a.plot([xx, xx], [xx * SLOPE, xx * SLOPE + 0.9], color=MUTED, lw=0.8, zorder=6)
    return a, M, dict(xb0=xb0, xpk=x[i_pk], xsh=xsh, xr=xr, R=R)


def curve_axes(fig, X0, Y0, W, H, ylab, guides, xlab=None):
    a = plot_axes(fig, X0, Y0, W, H)
    a.set_xlim(XMIN, XMAX)
    for xx in guides:
        a.axvline(xx, color='#b9b6ae', lw=0.9, ls=':', zorder=1)
    a.axvline(0, color=RULE, lw=0.8, zorder=1)
    a.grid(color=RULE, lw=0.5, axis='y')
    a.set_ylabel(ylab, fontsize=9)
    a.tick_params(labelsize=8.5)
    if xlab:
        a.set_xlabel(xlab, fontsize=9)
    else:
        a.set_xticklabels([])
    return a


def column_panel(ax, t, X0, Y0, W, H):
    """Water column in the surf zone: onshore mass flux above the trough, undertow below."""
    xa, xb = X0, X0 + W
    ytop, ybed = Y0 + 70, Y0 + H
    amp = 34
    xx = np.linspace(xa, xb, 200)
    ys = ytop - amp * np.cos(2 * np.pi * (xx - xa) / W * 1.0 - 0.6)
    poly = [(xa, ybed)] + list(zip(xx, ys)) + [(xb, ybed)]
    ax.add_patch(Polygon(poly, fc=WATER, ec='none', zorder=2))
    line(ax, list(zip(xx, ys)), BLUE, 1.5, z=4)
    rect(ax, xa, ybed, W, 26, SOIL, zorder=2)
    line(ax, [(xa, ybed), (xb, ybed)], BED, 1.3, z=4)
    line(ax, [(xa, ytop - amp), (xb, ytop - amp)], MUTED, 0.7, ls=':', z=3)
    line(ax, [(xa, ytop + amp), (xb, ytop + amp)], MUTED, 0.7, ls=':', z=3)
    text(ax, xb + 6, ytop - amp, t['fcrest'], 8.5, color=MUTED, va='center')
    text(ax, xb + 6, ytop + amp, t['ftrough'], 8.5, color=MUTED, va='center')
    text(ax, xb + 6, ybed + 13, t['fbed'], 8.5, color=BED, va='center')
    text(ax, xb - 4, Y0 + 4, t['fshore'], 9, color=INK, ha='right')
    # onshore mass flux between crest and trough level
    xc = xa + 0.30 * W
    for yy in (ytop - 14, ytop + 10):
        arrow(ax, [(xc - 60, yy), (xc + 70, yy)], ORANGE, 2.2, size=12, z=8)
    # undertow profile below the trough
    yy = np.linspace(ytop + amp + 18, ybed - 14, 7)
    xq = xa + 0.62 * W
    prof = 0.75 + 0.25 * np.sin(np.pi * (yy - yy[0]) / (yy[-1] - yy[0]))
    for y_, f_ in zip(yy, prof):
        arrow(ax, [(xq + 10, y_), (xq + 10 - 120 * f_, y_)], NAVY, 1.6, size=10, z=8)
    line(ax, [(xq + 10, yy[0]), (xq + 10, yy[-1])], NAVY, 0.9, z=7)
    line(ax, list(zip(xq + 10 - 120 * prof, yy)), NAVY, 1.0, ls=(0, (3, 2)), z=7)
    return ytop, ybed


def sand_panel(ax, t, X0, Y0, W):
    """Two cases of the cross-shore sand velocity u_s = u^E + u_a (schematic lengths)."""
    y = Y0
    for key, uE, ua in (('gstorm', -1.0, 0.45), ('gcalm', -0.25, 0.6)):
        y = paragraph(ax, X0, y, t[key], W, 9, INK, gap=10)
        c = X0 + W * 0.45
        s_ = 120
        line(ax, [(c, y - 6), (c, y + 70)], RULE, 1.0, z=2)
        arrow(ax, [(c, y + 8), (c + s_ * uE, y + 8)], NAVY, 2.0, size=11, z=8)
        arrow(ax, [(c, y + 30), (c + s_ * ua, y + 30)], ORANGE, 2.0, size=11, z=8)
        arrow(ax, [(c, y + 54), (c + s_ * (uE + ua), y + 54)], GREEN, 2.6, size=12, z=8)
        text(ax, c + s_ * max(ua, 0) + 12, y + 30, 'u_a', 9, color=ORANGE, va='center')
        text(ax, c - s_ * 1.0 - 10, y + 8, 'u^E', 9, color=NAVY, ha='right', va='center')
        text(ax, c - s_ * 1.0 - 10, y + 54, 'u_s', 9.5, color=GREEN, ha='right', va='center', weight='bold')
        y += 86
    return y


def build_profile(lang):
    t = T[lang]
    fig, ax = canvas(2000)
    pr = beach_profile(roller=True)
    pn = beach_profile(roller=False)
    LX0, LW = 110, 1060
    text(ax, 40, 22, t['qa'], 12.5, weight='bold')
    SY, SH = 95, 330
    a, M, g = schematic(fig, pr, LX0, SY, LW, SH)
    guides = (g['xb0'], g['xsh'])
    crest = lambda xx: np.interp(xx, pr['x'], pr['eta'] + pr['Hm0'] / 2)

    def lab(x, z, s, dx, dy, color=INK, ha='left'):
        p = M(x, z)
        q = (p[0] + dx, p[1] + dy)
        line(ax, [p, q], '#9a9890', 0.8, z=9)
        text(ax, q[0] + (4 if ha == 'left' else -4), q[1], s, 9, color=color, ha=ha, va='center',
             bbox=dict(fc='white', ec='none', alpha=0.85, pad=1.5))
    lab(-575, crest(-575), t['off'], 0, -36, NAVY)
    lab(-400, crest(-400), t['shoal2'], 0, -64, NAVY)
    lab(g['xb0'], crest(g['xb0']), t['brk0'], 0, -36, ORANGE)
    lab(-150, -0.55, t['surf2'], -20, 90, ORANGE, ha='right')
    lab(-40, np.interp(-40, pr['x'], pr['eta']), t['mwl'], -30, 50, '#c0392b', ha='right')
    lab(g['xsh'], g['xsh'] * SLOPE + 0.05, t['shore'], -12, -52, INK, ha='right')
    lab(g['xr'], g['xr'] * SLOPE + 0.05, t['runup'], 0, -78, INK, ha='right')
    p = M(-200, -2.6)
    paragraph(ax, p[0], p[1], t['swash'], LX0 + LW - p[0] - 12, 8.8, BED)
    q = M(0.5 * (g['xsh'] + g['xr']), 0.5 * (g['xsh'] + g['xr']) * SLOPE)
    line(ax, [(LX0 + LW - 60, p[1] - 4), q], '#9a9890', 0.8, z=9)
    y = SY + SH + 12
    text(ax, LX0, y, t['env'], 8.8, color=NAVY)
    text(ax, LX0, y + 24, t['inst'], 8.8, color=BLUE)
    y += 24
    # computed curves
    pr = {k_: (v_[::4] if isinstance(v_, np.ndarray) else v_) for k_, v_ in pr.items()}
    pn = {k_: (v_[::4] if isinstance(v_, np.ndarray) else v_) for k_, v_ in pn.items()}
    x, xn = pr['x'], pn['x']
    hgt, gap = 175, 70
    y0 = y + 70
    text(ax, 40, y0 - 38, t['qb'], 12, weight='bold')
    b = curve_axes(fig, LX0, y0, LW, hgt, t['yH'], guides)
    b.plot(x, pr['Hsh'], color=MUTED, lw=1.2, ls='--', label=t['Hsh'])
    htot = -x * SLOPE + pr['eta']
    b.plot(x, np.sqrt(2) * 0.6 * htot, color=MUTED, lw=1.0, ls=':', label=t['Hlim'])
    b.plot(x, pr['Hm0'], color=BLUE, lw=1.8, label=t['Hm0'])
    b.set_ylim(0, 2.5)
    b.set_yticks([0, 1, 2])
    for xx, key, ha in ((g['xb0'], 'brk0', 'right'), (g['xsh'], 'gshore', 'right')):
        b.text(xx - 4, 1.03, t[key], transform=b.get_xaxis_transform(), fontsize=8.5, color=MUTED,
               ha=ha, va='bottom')
    b.legend(fontsize=8.5, frameon=False, loc='lower left')
    y0 += hgt + gap
    text(ax, 40, y0 - 38, t['qc'], 12, weight='bold')
    c = curve_axes(fig, LX0, y0, LW, hgt, t['yD'], guides)
    c.plot(x, pr['Db'], color=ORANGE, lw=1.8, label=t['Dw'])
    c.plot(x, pr['Dr'], color=GREEN, lw=1.8, ls='--', label=t['Dr'])
    c.set_ylim(0, 1.35 * max(pr['Db'].max(), pr['Dr'].max()))
    c.legend(fontsize=8.5, frameon=False, loc='upper left')
    y0 += hgt + gap
    text(ax, 40, y0 - 38, t['qd'], 12, weight='bold')
    d = curve_axes(fig, LX0, y0, LW, hgt, t['ye'], guides)
    d.plot(x, pr['eta'], color=BLUE, lw=1.8, label=t['roll1'])
    d.plot(xn, pn['eta'], color=MUTED, lw=1.3, ls='--', label=t['roll0'])
    d.axhline(0, color=INK, lw=0.6)
    d.set_ylim(-0.05, 0.27)
    d.set_yticks([0, 0.1, 0.2])
    d.legend(fontsize=8.5, frameon=False, loc='upper left')
    i = np.argmin(pr['eta'])
    d.annotate(t['sdown'], xy=(x[i], pr['eta'][i]), xytext=(x[i] - 110, -0.035), fontsize=8.5, color=INK,
               arrowprops=dict(arrowstyle='-', color='#9a9890', lw=0.8), va='center')
    d.annotate(t['sup'], xy=(x[-1], pr['eta'][-1]), xytext=(x[-1] - 150, 0.2), fontsize=8.5, color=INK,
               arrowprops=dict(arrowstyle='-', color='#9a9890', lw=0.8), va='center', ha='right')
    y0 += hgt + gap
    text(ax, 40, y0 - 38, t['qe'], 12, weight='bold')
    e = curve_axes(fig, LX0, y0, LW, hgt, t['yv'], guides, xlab=t['xlab'])
    e.plot(x, pr['vL'], color=BLUE, lw=1.8, label=t['roll1'])
    e.plot(xn, pn['vL'], color=MUTED, lw=1.3, ls='--', label=t['roll0'])
    e.set_ylim(0, 0.68)
    e.set_yticks([0, 0.2, 0.4, 0.6])
    i1, i0 = np.argmax(pr['vL']), np.argmax(pn['vL'])
    e.annotate('', xy=(x[i1], pr['vL'][i1] + 0.04), xytext=(xn[i0], pr['vL'][i1] + 0.04),
               arrowprops=dict(arrowstyle='-|>', color=INK, lw=1.0))
    e.text(xn[i0] - 8, pr['vL'][i1] + 0.04, t['vshift'], fontsize=8.5, ha='right', va='center')
    y_end = y0 + hgt + 74
    y_end = paragraph(ax, LX0, y_end, t['note'], LW, 8.8, MUTED)
    # right column
    RX, RW = 1250, 400
    text(ax, 1215, 22, t['qf'], 12.5, weight='bold')
    ytop, ybed = column_panel(ax, t, RX, 80, RW, 520)
    yy = paragraph(ax, 1230, ybed + 46, t['fstokes'], 540, 9, ORANGE)
    yy = paragraph(ax, 1230, yy, t['fund'], 540, 9, NAVY)
    yy = paragraph(ax, 1230, yy + 4, t['fuL'], 540, 9, INK)
    yy = paragraph(ax, 1230, yy, t['fuE'], 540, 9, INK)
    text(ax, 1230, yy + 30, t['qg'], 12.5, weight='bold')
    yy = yy + 72
    for key, colr in (('guE', NAVY), ('gua', ORANGE), ('gus', GREEN)):
        yy = paragraph(ax, 1230, yy, t[key], 540, 9, colr, gap=4)
    yy = sand_panel(ax, t, 1230, yy + 14, 540)
    yy = paragraph(ax, 1230, yy, t['gnote'], 540, 9, MUTED)
    ax.set_zorder(10)                                           # canvas labels above the plot axes
    fit_height(fig, ax, max(y_end, yy) + 20)
    return fig

def draw(lang):
    with drawing_style():
        export(build_plan(lang), 'wavefield_plan', lang)
        return export(build_profile(lang), 'wavefield_profile', lang)
