"""nonhydro supplement: native bilingual schematic and unchanged numerical curves.

Regenerate only this page with make_guide_figs.py nonhydro.
"""
from _terms import *

D = {'ja': {'a': '(a) 線形波の分散関係(平坦床)',
        'b': '(b) 底面変位 → 水面のフィルタ F(kH)(f_nh_bottom)',
        'exact': '厳密(Airy)  √(tanh kH / kH)',
        'nh1': '1 層 NH(ENCflow、β = h²/4)  1/√(1 + (kH)²/4)',
        'nh2': '2 次圧力分布(Green–Naghdi 相当)  1/√(1 + (kH)²/3)',
        'hyd': '静水圧 SWE  1',
        'xlabel': 'kH(H: 水深、k: 波数 2π/L)',
        'ylabel': '位相速度 c / √(gH)',
        'range': '実用範囲の目安 kH ≲ 2（誤差 約2.5%）',
        'fex': '厳密  1/cosh kH',
        'fimp': 'f_nh_bottom = 1(平滑化源項)  1/(1 + (kH)²/4)²',
        'fnaive': '素朴な源項 −(h/2)z̈  (1 − (kH)²/4)/(1 + (kH)²/4)',
        'fnone': '加速度項なし・静水圧  1',
        'fylabel': 'F(kH)',
        'fnote': '素朴な源項は kH > 2 で符号が反転し、\n慣性なしの底層と正帰還で発散した(§7)'},
 'en': {'a': '(a) Linear dispersion relation (flat bed)',
        'b': '(b) Bottom-motion to surface filter F(kH) (f_nh_bottom)',
        'exact': 'exact (Airy)  √(tanh kH / kH)',
        'nh1': 'one-layer NH (ENCflow, β = h²/4)  1/√(1 + (kH)²/4)',
        'nh2': 'quadratic pressure (Green–Naghdi type)  1/√(1 + (kH)²/3)',
        'hyd': 'hydrostatic SWE  1',
        'xlabel': 'kH (H: depth, k: wavenumber 2π/L)',
        'ylabel': 'phase speed c / √(gH)',
        'range': 'Practical range: kH ≲ 2 (error about 2.5%)',
        'fex': 'exact  1/cosh kH',
        'fimp': 'f_nh_bottom = 1 (smoothed source)  1/(1 + (kH)²/4)²',
        'fnaive': 'naive source −(h/2)z̈  (1 − (kH)²/4)/(1 + (kH)²/4)',
        'fnone': 'no acceleration term / hydrostatic  1',
        'fylabel': 'F(kH)',
        'fnote': 'the naive source changes sign for kH > 2 and\n'
                 'blew up in feedback with the inertialess bed layer (§7)'}}

S={'ja':{
 'a':'(a) 1層モデルの鉛直構造', 'b':'(b) 1ステップの射影（平坦床の基本形）',
 'c':'(c) 候補セルから活性集合を選ぶ',
 'surface':'水面 η = z_b + h','bottom':'底面 z_b','pressure':'同じ鉛直断面の q(z)',
 'linear':'水面で0、底面でq_b。\n鉛直に線形と仮定。',
 'velocity':'u：水深平均の水平流速',
 'kinematic':'水面と底面の運動学条件',
 'wbar':'層平均の鉛直速度  w̄ = (w_s + w_b)/2',
 'phi':'圧力ポテンシャル φ = −q_b/2、β = h²/4',
 'extension':'底面勾配・底面加速度を使う場合は作用素・源項が変わります（本文§7）。',
 'start':'ステップ頭：uⁿ、hⁿを保持',
 'predict':'1  静水圧予測子', 'predict_body':'移流・摩擦・適応RK、堤防・構造物・境界条件を計算 → u*、mn*',
 'project':'2  非静水圧の射影', 'project_body':'f_nonhydrostatic = 1 のときだけ\nセルのφをCG（既定）またはJacobiで反復計算',
 'continuity':'3  連続式', 'continuity_body':'補正後の流量 mn → hⁿ⁺¹',
 'off':'NH無効時は\n射影を通らない',
 'mask':'灰：浅水・乾燥・強制境界の縁 ／ 黄：砕波セルとその縁 → 静水圧（φ = 0）',
 'seed':'種', 'margin':'縁', 'breaking':'砕波', 'shallow':'浅水',
 'active':'破線内：種＋縁。候補セルの中だけで拡張。',
 'seed_body':'種：χ > nh_chi_on に加え、nh_amin・nh_arel の下限を満たすセル。',
 'margin_body':'縁：nh_margin 回、8近傍へ膨張。0なら候補の最大水深と最小格子幅から自動設定。',
 'inactive':'白：候補だが不活性（φ = 0）。\nf_nh_adaptive = 0 では候補全体を解く。',
 'candidate':'候補：有効・非海域、h ≥ nh_hmin、gv = 1、幅河道・断面形σの適用外など（本文§4）。',
 'nest':'図は単独格子の例。ネスト子格子の帯では親から与えるφを既知値として扱います。',
},'en':{
 'a':'(a) Vertical structure of the one-layer model', 'b':'(b) One-step projection: flat-bed baseline',
 'c':'(c) Select the active set within candidate cells',
 'surface':'Surface η = z_b + h','bottom':'Bottom z_b','pressure':'q(z) at the same vertical section',
 'linear':'Zero at the surface, q_b at the bed.\nAssumed linear in the vertical.',
 'velocity':'u: depth-averaged horizontal velocity',
 'kinematic':'Kinematic conditions at surface and bed',
 'wbar':'Layer-average vertical velocity: w̄ = (w_s + w_b)/2',
 'phi':'Pressure potential φ = −q_b/2; β = h²/4',
 'extension':'Bottom slope and acceleration change the operator / source (text §7).',
 'start':'Start of step: retain uⁿ and hⁿ',
 'predict':'1  Hydrostatic predictor', 'predict_body':'Advection, friction, adaptive RK, levees, structures and boundary conditions → u*, mn*',
 'project':'2  Non-hydrostatic projection', 'project_body':'Only when f_nonhydrostatic = 1\nIterate cell φ with CG (default) or Jacobi',
 'continuity':'3  Continuity', 'continuity_body':'Corrected flux mn → hⁿ⁺¹',
 'off':'NH off:\nskip projection',
 'mask':'Grey: shallow / dry / boundary margin. Yellow: breaking + margin. Both stay hydrostatic (φ = 0).',
 'seed':'Seeds', 'margin':'Margin', 'breaking':'Breaking', 'shallow':'Shallow',
 'active':'Dashed: seeds + margin, expanded within candidates only.',
 'seed_body':'Seeds: χ > nh_chi_on and above the nh_amin / nh_arel floors.',
 'margin_body':'Margin: nh_margin dilations over 8 neighbours; 0 selects it from maximum candidate depth and minimum cell spacing.',
 'inactive':'White: candidate but inactive (φ = 0).\nf_nh_adaptive = 0 solves all candidates.',
 'candidate':'Candidates: valid, non-sea cells; h ≥ nh_hmin, gv = 1; no subgrid width / section σ, etc. (text §4).',
 'nest':'Single-grid example. A nested child uses φ supplied by its parent as known values in the boundary strip.',
}}


def mask_cells():
    cells={(i,j):'cand' for i in range(16) for j in range(9)}
    for i in [0,13,14,15]:
        for j in range(9):cells[i,j]='shal'
    for j in range(2,7):cells[12,j]='shal'
    for i in range(9,12):
        for j in range(3,6):cells[i,j]='brk'
    for i in range(4,7):
        for j in range(3,6):cells[i,j]='seed'
    for i in range(2,9):
        for j in range(1,8):
            if cells[i,j]=='cand' and max(abs(i-5),abs(j-4))<=3:cells[i,j]='marg'
    return cells


def column_profiles():
    x=np.linspace(0,10,200)
    return x,.6+.12*x,4+.35*np.sin(.9*x)


def build_scheme(lang):
    t=S[lang];fig,ax=canvas(1610)
    text(ax,48,32,t['a'],13,weight='bold');text(ax,948,32,t['b'],13,weight='bold')
    x,zb,eta=column_profiles();px=80+52*x;yy=lambda z:470-60*z
    ax.add_patch(Polygon(np.c_[np.r_[px,px[::-1]],np.r_[yy(zb),yy(eta[::-1])]],fc=WATER,ec='none',zorder=1,gid='water'))
    ax.add_patch(Polygon(np.c_[np.r_[px,px[-1],px[0]],np.r_[yy(zb),[500,500]]],fc=SOIL,ec='none',zorder=1,gid='ground'))
    line(ax,list(zip(px,yy(zb))),BED,1.5);line(ax,list(zip(px,yy(eta))),BLUE,1.5)
    text(ax,80,156,t['surface'],10.5,color=BLUE)
    text(ax,425,456,t['bottom'],10.5,color=BED)
    # Surface and bottom arrows start exactly on their respective profiles.
    for xx,profile,sign,key,col in [(7.,eta,-1,'ws',BLUE),(1.2,zb,-1,'wb',BED)]:
        p=np.array([80+52*xx,yy(np.interp(xx,x,profile))])
        arrow(ax,[p,p+[0,sign*70]],col,1.3).set_gid(key+'-arrow')
        text(ax,p[0]+16,p[1]-83,'$w_s$' if key=='ws' else '$w_b$',11,color=col)
    arrow(ax,[(395,320),(530,320)],BLUE,1.5)
    text(ax,460,338,'u',12,color=BLUE,ha='center')
    # Pressure is a separate q-axis, not a wedge embedded in the sloping bed.
    z0=float(np.interp(3,x,zb));z1=float(np.interp(3,x,eta));top,bot=yy(z1),yy(z0)
    line(ax,[(236,top),(236,bot)],MUTED,.8,ls='--')
    line(ax,[(236,top),(695,top)],MUTED,.7,ls=':',z=2)
    line(ax,[(236,bot),(695,bot)],MUTED,.7,ls=':',z=2)
    ax.add_patch(Polygon([(710,top),(710,bot),(820,bot)],fc='#fdf1dc',ec=ORANGE,lw=1.3,gid='pressure-profile'))
    text(ax,710,top-36,'q = 0',10.5,color=ORANGE)
    text(ax,818,bot+14,'q_b',10.5,color=ORANGE,ha='center')
    block(ax,670,94,t['pressure'],225,10,color=ORANGE)
    block(ax,620,491,t['linear'] if lang=='ja' else 'q = 0 at surface; q_b at bed.\nLinear vertical profile.',274,9.5,color=ORANGE)
    text(ax,48,542,t['velocity'],10,color=BLUE)
    text(ax,48,591,t['kinematic'],10.5,weight='bold')
    text(ax,48,634,r'$w_s=\partial\eta/\partial t+\mathbf{u}\cdot\nabla\eta$',12,color=BLUE)
    text(ax,48,679,r'$w_b=\partial z_b/\partial t+\mathbf{u}\cdot\nabla z_b$',12,color=BED)
    text(ax,48,734,t['wbar'],10)
    text(ax,48,776,t['phi'],10,color=ORANGE)
    block(ax,48,822,t['extension'],844,9.5,color=MUTED)
    # A bypass has its own lane and never crosses the projection box.
    rect(ax,948,102,659,65,'white',RULE,1)
    text(ax,969,123,t['start'],10.5)
    rect(ax,948,207,659,147,'#edf3fb',BLUE,1.1)
    text(ax,969,226,t['predict'],11,weight='bold',color=BLUE)
    block(ax,969,272,t['predict_body'],615,9.7)
    rect(ax,948,403,659,277,'#fdf1dc',ORANGE,1.1)
    text(ax,969,422,t['project'],11,weight='bold',color=ORANGE)
    block(ax,969,467,t['project_body'],615,9.5)
    for y,s in [(543,r'$a^*=(u^*-u^n)/\Delta t$'),(590,r'$(1-\beta\nabla^2)\phi=\beta\nabla\cdot a^*$'),(637,r'$u^{n+1}=u^*+\Delta t\nabla\phi,\quad mn=u^{n+1}h_e$')]:text(ax,969,y,s,11)
    rect(ax,948,730,659,114,'#edf3fb',BLUE,1.1)
    text(ax,969,748,t['continuity'],11,weight='bold',color=BLUE)
    block(ax,969,791,t['continuity_body'],615,10)
    for start,end in [(167,207),(354,403),(680,730)]:arrow(ax,[(1277,start+5),(1277,end-5)],MUTED,1.2)
    arrow(ax,[(1607,321),(1780,321),(1780,774),(1615,774)],GREEN,1.2,ls='--').set_gid('bypass')
    block(ax,1630,471,t['off'],132,9.2,color=GREEN)
    line(ax,[(48,904),(1752,904)],RULE,.9)
    text(ax,48,935,t['c'],13,weight='bold')
    block(ax,48,983,t['candidate'],1704,9.8)
    cells=mask_cells();colors={'cand':'white','shal':'#e6e4df','brk':'#f2b84b','seed':BLUE,'marg':WATER}
    x0,y0,dd=80,1060,55
    for (i,j),kind in cells.items():
        rect(ax,x0+i*dd,y0+(8-j)*dd,dd,dd,colors[kind],gid=f'mask-{i}-{j}',hatch='///' if kind=='shal' else None,zorder=1)
    grid(ax,x0,y0,16,9,dd)
    rect(ax,x0+2*dd,y0+dd,7*dd,7*dd,'none',ORANGE,1.5,gid='active-set',ls='--',zorder=5)
    for x,y,key,col in [(5.5,4.5,'seed','white'),(5.5,1.5,'margin',BLUE),(10.5,4.5,'breaking','#71501b'),(14.5,4.5,'shallow',INK)]:
        text(ax,x0+x*dd,y0+y*dd,t[key],10,color=col,ha='center',va='center',weight='bold')
    for yy,key,col in [(1060,'active',ORANGE),(1145,'seed_body',BLUE),(1240,'margin_body',BLUE),(1370,'inactive',MUTED)]:block(ax,1030,yy,t[key],722,10,color=col)
    block(ax,1030,1470,t['mask'],722,9.5,color=MUTED)
    block(ax,48,1570,t['nest'],1704,9.2,color=MUTED)
    return fig


def build_dispersion(lang):
    t=D[lang];fig,base=canvas(1070)
    titles=['(a) 線形波の位相速度（平坦床）','(b) 底面変位から水面へのフィルタ'] if lang=='ja' else ['(a) Linear-wave phase speed: flat bed','(b) Bottom-motion to surface filter']
    kh=np.linspace(.01,4,400)
    for x,title in [(48,titles[0]),(970,titles[1])]:text(base,x,32,title,13,weight='bold')
    ax=plot_axes(fig,113,116,700,467)
    ax.axvspan(0,2,color='#eef3fa',zorder=0)
    ax.plot(kh,np.sqrt(np.tanh(kh)/kh),color='k',lw=2,gid='airy')
    ax.plot(kh,1/np.sqrt(1+kh**2/4),color=ORANGE,lw=2,gid='nh-linear')
    ax.plot(kh,1/np.sqrt(1+kh**2/3),color=BLUE,lw=1.3,ls='--',gid='nh-quadratic')
    ax.axhline(1,color=MUTED,lw=1.1,ls=':')
    ax.set(xlim=(0,4),ylim=(.3,1.05),xlabel=t['xlabel'],ylabel=t['ylabel'])
    legend_rows(base,48,668,[('k','-',t['exact']),(ORANGE,'-',t['nh1']),(BLUE,'--',t['nh2']),(MUTED,':',t['hyd'])],815,77,9.3)
    block(base,48,1007,t['range'],815,9.4,color=BLUE)
    ax=plot_axes(fig,1020,116,704,467);b=kh**2/4
    ax.plot(kh,1/np.cosh(kh),color='k',lw=2,gid='exact-filter')
    ax.plot(kh,1/(1+b)**2,color=ORANGE,lw=2,gid='smoothed-filter')
    ax.plot(kh,(1-b)/(1+b),color='#8fbf6a',lw=1.3,ls='--',gid='naive-filter')
    ax.axhline(1,color=MUTED,lw=1.1,ls=':');ax.axhline(0,color=RULE,lw=.8)
    ax.set(xlim=(0,4),ylim=(-.7,1.1),xlabel=t['xlabel'],ylabel=t['fylabel'])
    legend_rows(base,970,668,[('k','-',t['fex']),(ORANGE,'-',t['fimp']),('#8fbf6a','--',t['fnaive']),(MUTED,':',t['fnone'])],782,77,9.2)
    block(base,970,1007,t['fnote'],782,9.2,color=GREEN)
    return fig


def draw_scheme(lang):
    with drawing_style():return export(build_scheme(lang),'nonhydro_scheme',lang)


def draw_dispersion(lang):
    with drawing_style():return export(build_dispersion(lang),'nonhydro_dispersion',lang)


def draw(lang):
    draw_dispersion(lang)
    return draw_scheme(lang)
