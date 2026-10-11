"""氷河(docs/users_guide/glacier.md)の説明図: 氷河の縦断面に質量収支・流動・滑動・侵食・雪崩再配分を配置。

  glacier_profile.png / glacier_profile.svg (日本語・英語)
データ不要の模式図(matplotlib のみ)。
"""
import numpy as np
from pathlib import Path as FilePath
from _style import *
from _schematic import (drawing_style, text, block, paragraph, line, curve,
                        arrow as profile_arrow, monotone_cubic, export,
                        INK, MUTED, RULE)

T = {
    "ja": dict(
        title="氷河の縦断面とプロセス(fn_glacier。fn_meteo の気温と fn_snow の降雪が必須。状態は氷厚 hi → 出力 Hi)",
        ava="雪崩再配分 f_glava\n氷面勾配 > gl_ava_tanc の雪を\n最急下方の隣接セルへ",
        acc="涵養: 越年した雪だけが氷になる\n(時定数 gl_tfirn_yr、氷密度 gl_dens)\n季節の雪は融けて流出",
        ela="平衡線は指定しない(気温と降水から自動)\n気温は氷面標高 z + hi で評価(f_temp_lapse と組)",
        abl="消耗: 氷面の度日融解 gl_ddfi(T > gl_tmelt)\n雪に覆われていないときだけ",
        melt="融解水 → 地表水\n(実時間。gl_morfac で加速しない)",
        flow="氷体流動 f_glflow(SIA。Glen 則 gl_afl)",
        slide="底面滑動 f_glslide(Weertman 型 gl_as。f_glflow 必須)",
        ero="氷河侵食 f_glero(f_glslide 必須): ė = Kg·usˡ(gl_kg, gl_lexp)\n滑動する氷の下だけ z を下げる(土層 sd があれば先に減る)\n岩屑は系外へ(堆積モレーンなし)",
        init="初期: 既定は氷なし(hi = 0)から降雪で育てる(スピンアップ)。実在氷河は fn_glacier_hi0 で氷厚を与える",
        time="時間: 氷化・流動・侵食は dt_glacier_c ごとに更新、1 回の更新 = gl_morfac 回分(fn_geomorph 併用時は morfac と同値に)",
        snow="積雪(SWE)", ice="氷 hi", rock="地盤 z",
        acc_z="涵養域", abl_z="消耗域",
    ),
    "en": dict(
        title="Glacier long profile and processes (fn_glacier; needs fn_meteo temperature and fn_snow snowfall; state = ice thickness hi → output Hi)",
        ava="avalanche redistribution f_glava\nsnow on surface slopes > gl_ava_tanc\nmoves to the steepest downhill neighbour",
        acc="accumulation: only perennial snow turns to ice\n(time constant gl_tfirn_yr, ice density gl_dens)\nseasonal snow melts and runs off",
        ela="equilibrium line not prescribed\n(emerges from temperature and precipitation;\ntemperature evaluated at z + hi with f_temp_lapse)",
        abl="ablation: degree-day melt of the ice surface\ngl_ddfi (T > gl_tmelt), only where no snow covers it",
        melt="meltwater → surface water\n(real time; not scaled by gl_morfac)",
        flow="ice flow f_glflow (SIA; Glen's law gl_afl)",
        slide="basal sliding f_glslide (Weertman type gl_as; needs f_glflow)",
        ero="glacial erosion f_glero (needs f_glslide): ė = Kg·usˡ (gl_kg, gl_lexp)\nlowers z only under sliding ice (soil sd is consumed first)\nthe debris leaves the system (no moraine deposition)",
        init="initial state: default is no ice (hi = 0), grown from snowfall (spin-up); real glaciers take fn_glacier_hi0",
        time="time: firnification, flow and erosion update every dt_glacier_c; one update = gl_morfac repetitions (equal to morfac when fn_geomorph is on)",
        snow="snow (SWE)", ice="ice hi", rock="bed z",
        acc_z="accumulation zone", abl_z="ablation zone",
    ),
}



# Conceptual coordinates only. These do not define model inputs or a solution.
HEAD, TOE, ELA = 1.2, 8.0, 4.3
BED_X = np.array([1.3, 2.2, 3.4, 5.0, 6.6, 8.0, 9.2, 10.5])
BED_Z = np.array([3.0, 2.1, 1.75, 1.45, 1.1, .75, .5, .4])
SURFACE_X = np.array([HEAD, 1.8, 3.1, ELA, 5.6, 6.7, 7.2])


def _hermite(x, a, b, ya, yb, ma, mb):
    """Cubic connector with explicit endpoint elevations and tangents."""
    u = (np.asarray(x) - a) / (b - a)
    return ((2*u**3 - 3*u**2 + 1)*ya + (u**3 - 2*u**2 + u)*(b-a)*ma
            + (-2*u**3 + 3*u**2)*yb + (u**3 - u**2)*(b-a)*mb)


def _end_slope(x, y, left=False):
    """Endpoint tangent of the shape-preserving cubic used below."""
    h, d = np.diff(x), np.diff(y)/np.diff(x)
    a, b, da, db = (h[0], h[1], d[0], d[1]) if left else (h[-1], h[-2], d[-1], d[-2])
    m = ((2*a+b)*da-a*db)/(a+b)
    if m*da <= 0:
        return 0.0
    return 3*da if da*db < 0 and abs(m) > 3*abs(da) else m


def bed_elevation(x):
    """Keep the cliff shoulder at x=.6 sharp; join its foot tangentially."""
    x = np.asarray(x, float)
    valley = monotone_cubic(BED_X, BED_Z, np.clip(x, BED_X[0], BED_X[-1]))
    cliff = _hermite(x, .6, 1.3, 4.4, 3.0, -2.0,
                     _end_slope(BED_X, BED_Z, left=True))
    return np.where(x <= .6, 4.6 - x/3, np.where(x < 1.3, cliff, valley))


def surface_elevation(x):
    """A descending ice surface, tangent to the same bed at the terminus."""
    x = np.asarray(x, float)
    z = bed_elevation(x)
    sy = np.array([float(bed_elevation(HEAD)), 3.14, 3.04, 2.86, 2.46, 1.77, 1.35])
    surface = monotone_cubic(SURFACE_X, sy, np.clip(x, HEAD, 7.2))
    # The toe tangent is the weighted harmonic mean at the bed's x=8 knot.
    h = np.diff(BED_X)
    d = np.diff(BED_Z)/h
    k = int(np.flatnonzero(BED_X == TOE)[0])
    w1, w2 = 2*h[k]+h[k-1], h[k]+2*h[k-1]
    toe_slope = (w1+w2)/(w1/d[k-1]+w2/d[k])
    toe = _hermite(x, 7.2, TOE, sy[-1], float(bed_elevation(TOE)),
                   _end_slope(SURFACE_X, sy), toe_slope)
    return np.where((x <= HEAD) | (x >= TOE), z, np.where(x > 7.2, toe, surface))


def snow_depth(x):
    """A schematic snow band; its displayed thickness is not a SWE scale."""
    x = np.asarray(x, float)
    ramp = np.clip((x-.30)/.20, 0, 1)
    taper = np.clip((ELA-x)/.55, 0, 1)
    smooth = lambda t: t*t*(3-2*t)
    return .16*smooth(ramp)*smooth(taper)


def profiles():
    # Every layer uses this mesh, including exact contacts and curve junctions.
    x = np.unique(np.r_[np.linspace(0, 10.5, 2101), .3, .5, .6, BED_X,
                        SURFACE_X, ELA-.55, TOE])
    bed = bed_elevation(x)
    surface = surface_elevation(x)
    snow = surface + snow_depth(x)
    return x, bed, surface, snow


SHORT = {
    'ja': ['雪崩再配分', '涵養', '平衡線', '消耗', '氷体流動', '底面滑動', '氷河侵食', '融解水 → 地表水'],
    'en': ['avalanche redistribution', 'accumulation', 'equilibrium line', 'ablation',
           'ice flow', 'basal sliding', 'glacial erosion', 'meltwater → surface water'],
}


def build(lang):
    if lang not in T:
        raise ValueError('lang must be ja or en')
    t, short = T[lang], SHORT[lang]
    ja = lang == 'ja'
    fig = plt.figure(figsize=(13.2, 8.8))
    ax = fig.add_axes([.05, .465, .90, .48])
    ax.set(xlim=(-.1, 10.6), ylim=(-.3, 5.15), aspect='auto')
    ax.axis('off')
    header = fig.add_axes([.05, .948, .90, .05])
    header.set(xlim=(0, 1), ylim=(0, 1)); header.axis('off')
    block(header, 0, 1, t['title'], 1, size=10.7, weight='bold')
    x, bed, surface, snow = profiles()
    ice = (x >= HEAD) & (x <= TOE)
    cover = (x >= .30) & (x <= ELA)
    ax.fill_between(x, -.25, bed, color=C_ROCK, lw=0, zorder=1)
    ax.fill_between(x[ice], bed[ice], surface[ice], color=C_ICE, lw=0, zorder=2)
    # One snow polygon crosses the cliff/ice contact; no overlap or gap there.
    ax.fill_between(x[cover], surface[cover], snow[cover], color='white', lw=0, zorder=3)
    line(ax, list(zip(x, bed)), INK, 1.1, z=5)
    line(ax, list(zip(x[ice], surface[ice])), '#6aa5d0', 1.25, z=6)
    line(ax, list(zip(x[cover], snow[cover])), '#9bbbd6', 1.0, z=7)

    # All process arrows follow the same curves used by their host region.
    avalanche = curve((.75, 4.42), [
        ('C', (.99, 3.90), (1.20, 3.42), (1.46, 3.42)),
        ('C', (1.58, 3.42), (1.71, 3.39), (1.83, 3.39))])
    profile_arrow(ax, avalanche, C_X, 1.8)
    text(ax, 1.35, 4.72, '1  '+short[0], size=9.5, color=C_X)
    line(ax, [(1.36, 4.44), (1.04, float(surface_elevation(1.04)+.37))], MUTED, .7)

    for xv in (2.4, 3.0, 3.6):
        z0 = float(surface_elevation(xv))
        profile_arrow(ax, [(xv, z0+float(snow_depth(xv))+.17), (xv, z0-.15)], C_C, 1.35, size=10)
    for xv in (6.1, 6.7):
        z0 = float(surface_elevation(xv))
        profile_arrow(ax, [(xv, z0+.50), (xv, z0+.09)], C_X, 1.35, size=10)

    zela = float(surface_elevation(ELA))
    line(ax, [(ELA, zela), (ELA, 4.0)], MUTED, .9, ls='--')
    text(ax, ELA+.13, 4.23, '3  '+short[2], size=9, color=MUTED)
    for lo, hi, cx, label_ in [(1.95, ELA-.12, 3.1, '2  '+t['acc_z']),
                              (ELA+.12, 7.75, 6.3, '4  '+t['abl_z'])]:
        ax.annotate('', (lo, 3.75), (hi, 3.75), arrowprops=dict(
            arrowstyle='<->', color=MUTED, lw=.8, shrinkA=0, shrinkB=0))
        text(ax, cx, 3.93, label_, size=9.3, color=MUTED, ha='center', va='bottom')

    fx = np.linspace(3.3, 6.5, 160)
    fz = bed_elevation(fx) + .52*(surface_elevation(fx)-bed_elevation(fx))
    profile_arrow(ax, np.c_[fx, fz], '#2f6fb0', 2.0)
    text(ax, 4.65, 2.43, '5  '+short[4], size=10, color='#2f6fb0', ha='center')
    sx = np.linspace(3.6, 6.25, 140)
    profile_arrow(ax, np.c_[sx, bed_elevation(sx)+.095], C_X, 1.9)
    text(ax, 4.8, .94, '6  '+short[5], size=9.7, ha='center', color='white')
    ex = np.linspace(3.2, 6.8, 160)
    line(ax, np.c_[ex, bed_elevation(ex)-.14], C_G, 1.3, ls='--')
    for xv in (3.6, 6.5):
        z0 = float(bed_elevation(xv))
        profile_arrow(ax, [(xv, z0-.02), (xv, z0-.32)], C_G, 1.4, size=10)
    text(ax, 2.3, .48, '7  '+short[6], size=9.7, color='white')
    mx = np.linspace(6.85, 9.65, 230)
    profile_arrow(ax, np.c_[mx, surface_elevation(mx)+.06], C_C, 1.8)
    text(ax, 8.13, 1.78, '8  '+short[7], size=9.4, color=C_C, ha='center')
    line(ax, [(8.25, 1.5), (8.55, float(bed_elevation(8.55))+.10)], MUTED, .7)

    from matplotlib.patches import Patch
    handles = [Patch(fc='white', ec='#9bbbd6', label=t['snow']),
               Patch(fc=C_ICE, ec='#6aa5d0', label=t['ice']), Patch(fc=C_ROCK, label=t['rock'])]
    ax.legend(handles=handles, loc='upper right', fontsize=8.7, frameon=False, ncol=3,
              borderaxespad=0, handlelength=1.7)

    # Keep the original explanations verbatim, reflowed away from the geometry.
    for left, entries in [(.05, [(1, 'ava', C_X), (2, 'acc', C_C),
                                 (5, 'flow', '#2f6fb0'), (6, 'slide', C_X)]),
                          (.52, [(3, 'ela', MUTED), (4, 'abl', C_X),
                                 (7, 'ero', '#3f6f28'), (8, 'melt', C_C)])]:
        note = fig.add_axes([left, .165, .43, .265])
        note.set(xlim=(0, 1), ylim=(0, 1)); note.axis('off')
        line(note, [(0, 1.02), (1, 1.02)], RULE, .8, clip_on=False)
        y = .99
        for number, key, color in entries:
            y = paragraph(note, 0, y, f'{number}  '+t[key], 1,
                          size=8.7, color=color, gap=.045)

    foot = fig.add_axes([.05, .025, .9, .11])
    foot.set(xlim=(0, 1), ylim=(0, 1)); foot.axis('off')
    line(foot, [(0, 1.06), (1, 1.06)], RULE, .8, clip_on=False)
    y = paragraph(foot, 0, .94, t['init'], 1, size=8.5, gap=.10)
    y = paragraph(foot, 0, y, t['time'], 1, size=8.5, gap=.11)
    paragraph(foot, 0, y,
              '模式図：形状・縮尺は概念的。青い融解水の矢印は地表水への移行を示す（計算流路ではない）。'
              if ja else 'Schematic; not to scale. The blue meltwater arrow denotes transfer to surface water, not a computed flow path.',
              1, size=7.8, color=MUTED)
    return fig


def draw(lang):
    with drawing_style():
        png = export(build(lang), out_path('glacier_profile', lang))
        # Match the repository's LF policy on Windows as well.
        svg = FilePath(png).with_suffix('.svg')
        svg.write_bytes(svg.read_bytes().replace(b'\r\n', b'\n'))
        return png
