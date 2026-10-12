"""advection supplement: native bilingual schematic and unchanged numerical curves.

Regenerate only this page with make_guide_figs.py advection.
"""
from _terms import *

M = {'ja': {'a': '(a) 線 k 上の面値の再構成(面 c、q_c > 0 の場合)',
        'b': '(b) 限定器 $\\psi$(r)',
        'flow': '流れ q_c > 0',
        'face': '面 c',
        'cell_c': 'セル c',
        'cell_n': 'セル n',
        's2': 'スキーム 2: ū_c = u_m(1 次風上)',
        's3': 'スキーム 3: ū_c = u_m + $\\psi$(r)/2 · (u_e − u_m)',
        'r': 'r = (u_m − u_mm)/(u_e − u_m)',
        'vl': 'van Leer  $\\psi$ = (r + |r|)/(1 + |r|)',
        'central': '$\\psi$ = 1: 中心差分',
        'lw': '$\\psi$ = r',
        'tvd': 'TVD 領域内の比較帯（本文 §4.3）',
        'upwind': '$\\psi$ = 0: 1 次風上(スキーム 2)',
        'ext': 'r ≤ 0（勾配の符号反転など）で ψ = 0 → 1次風上',
        'xlabel': 'r(風上側勾配 / 風下側勾配)'},
 'en': {'a': '(a) Face-value reconstruction on line k (face c, q_c > 0)',
        'b': '(b) Limiter $\\psi$(r)',
        'flow': 'flow q_c > 0',
        'face': 'face c',
        'cell_c': 'cell c',
        'cell_n': 'cell n',
        's2': 'scheme 2: ū_c = u_m (first-order upwind)',
        's3': 'scheme 3: ū_c = u_m + $\\psi$(r)/2 · (u_e − u_m)',
        'r': 'r = (u_m − u_mm)/(u_e − u_m)',
        'vl': 'van Leer  $\\psi$ = (r + |r|)/(1 + |r|)',
        'central': '$\\psi$ = 1: central',
        'lw': '$\\psi$ = r',
        'tvd': 'Comparison band within the TVD region (§4.3)',
        'upwind': '$\\psi$ = 0: first-order upwind (scheme 2)',
        'ext': 'r ≤ 0 (e.g. opposite slopes): ψ = 0 → first-order upwind',
        'xlabel': 'r (upwind slope / downwind slope)'}}

CV = {'ja': {
 'a':'(a) スキーム1：セル中心で勾配を求め、エッジへ投影',
 'b':'(b) スキーム2・3：軸エッジの検査体積',
 'c':'(c) スキーム2・3：対角エッジの検査体積',
 'steps':['各セルで3×3の重み付き差分（風上側を重く）',
          'セルの移流項 T = −(u·∇)u を計算',
          '両側セルの T を平均し、法線方向へ投影 → Aₑ'],
 'stencil':'青：セルcの3×3 ／ 黄：セルnの3×3 ／ 破線：実効4×3セル。1次元では5エッジ幅の平滑化。',
 'axis_dim':'L = Δx、W = Δy', 'diag_dim':'L = Δr、W = 2ΔxΔy/Δr',
 'local':'矢印は流束の正方向。c → n が線kの正方向、側方面は外向きが正。正方セルの例。',
 'flow':'流向面：q_c、q_n = セル流量(m, n)のk方向投影。',
 'side':'側方面：点線の2本のENCエッジ流量を平均。\n流入時の流速は平行な隣接エッジ u_t±（1次風上）。',
 'area':'橙：運動量検査体積（面積 L×W）。正方セルでは軸が1セル分、対角が2セル分。',
 'legend':'● セル中心：h, z, u, v, m, n    ■／◇ エッジ：uv, mn    橙の印：更新対象 u_e',
}, 'en': {
 'a':'(a) Scheme 1: cell-centre gradients, then projection to the edge',
 'b':'(b) Schemes 2, 3: control volume of an axis edge',
 'c':'(c) Schemes 2, 3: control volume of a diagonal edge',
 'steps':['Weighted 3×3 differences at each cell (upwind side weighted more)',
          'Compute cell advection T = −(u·∇)u',
          'Average T from the two cells, then project onto the normal → Aₑ'],
 'stencil':'Blue: 3×3 stencil at c. Yellow: 3×3 at n. Dashed: effective 4×3 cells; five-edge smoothing in 1D.',
 'axis_dim':'L = Δx, W = Δy', 'diag_dim':'L = Δr, W = 2ΔxΔy/Δr',
 'local':'Arrows show positive flux directions: c → n along k; outward on lateral faces. Square-cell examples.',
 'flow':'Streamwise faces: q_c, q_n project cell flux (m, n) onto k.',
 'side':'Lateral faces: mean of two dotted ENC-edge fluxes.\nInflow uses the parallel edge u_t± (first-order upwind).',
 'area':'Orange: momentum control volume, area L×W. One cell area for axis edges, two for diagonal edges.',
 'legend':'● Cell centres: h, z, u, v, m, n    ■ / ◇ Edges: uv, mn    Orange marker: target u_e',
}}


def cv_geometry(diagonal=False):
    c=np.array([2.5,3.5]) if diagonal else np.array([3.5,1.5])
    n=c+([1,-1] if diagonal else [1,0])
    d=(n-c)/np.linalg.norm(n-c);t=np.array([-d[1],d[0]])
    L=np.linalg.norm(n-c);W=np.sqrt(2) if diagonal else 1.
    poly=np.array([c-t*W/2,n-t*W/2,n+t*W/2,c+t*W/2])
    return c,n,d,t,L,W,poly


def build_cv(lang):
    t=CV[lang];fig,ax=canvas(1430)
    text(ax,48,32,t['a'],13,weight='bold')
    x,y,d=80,130,85
    rect(ax,x+d,y,3*d,3*d,'#dbe8fa',gid='stencil-c')
    rect(ax,x+2*d,y,3*d,3*d,'#fbefd8',alpha=.75,gid='stencil-n')
    grid(ax,x,y,6,3,d)
    rect(ax,x+d,y,4*d,3*d,'none',ORANGE,1.5,gid='stencil-union',ls='--')
    for i in range(6):
        for j in range(3):dot(ax,(x+(i+.5)*d,y+(j+.5)*d))
    for i,col,name in [(2,BLUE,'c'),(3,'#ac7a28','n')]:
        p=np.array([x+(i+.5)*d,y+1.5*d])
        for a in [-1,0,1]:
            for b in [-1,0,1]:
                if a or b:line(ax,[p+np.array([a,b])*20,p+np.array([a,b])*62],col,.9)
        text(ax,p[0]-15,p[1]-12,name,11,color=col,ha='right',va='bottom',weight='bold',bbox=dict(fc='white',ec='none',pad=.3))
    edge(ax,(x+3*d,y+1.5*d),ORANGE,gid='scheme1-edge')
    text(ax,x+3*d,y+1.5*d+24,'$u_e$',11,color=ORANGE,ha='center',bbox=dict(fc='white',ec='none',pad=.3))
    for i,s in enumerate(t['steps']):
        rect(ax,720,135+i*83,1032,66,'#f4f5f2')
        text(ax,740,152+i*83,str(i+1),11,color=BLUE,weight='bold')
        block(ax,786,152+i*83,s,940,10)
    block(ax,48,424,t['stencil'],1704,10,color=MUTED)
    line(ax,[(48,479),(1752,479)],RULE,.9)
    text(ax,48,514,t['b'],12.5,weight='bold');text(ax,970,514,t['c'],12.5,weight='bold')
    text(ax,48,564,t['local'],9.7,color=MUTED)
    for diag,x0,y0,dd,nx,ny in [(False,70,701,86,7,3),(True,1060,653,79,6,6)]:
        c,n,dv,tv,L,W,poly=cv_geometry(diag)
        pos=lambda p:np.array([x0,y0])+np.asarray(p)*dd
        mid=(c+n)/2
        grid(ax,x0,y0,nx,ny,dd)
        patch=Polygon(pos(poly),fc='#fdf1dc',ec='#d9922a',lw=1.8,zorder=3,gid='cv-diag' if diag else 'cv-axis');ax.add_patch(patch)
        for i in range(nx):
            for j in range(ny):dot(ax,pos([i+.5,j+.5]))
        for v,name in zip([-2,-1,0,1,2],['mm','m','e','p','pp']):
            p=pos(mid+v*(n-c));edge(ax,p,ORANGE if v==0 else BLUE,diag,gid=('diag-' if diag else 'axis-')+name)
            if diag and v==0:
                text(ax,p[0]-14,p[1]-14,'$u_e$',10,color=ORANGE,ha='right')
            else:
                text(ax,p[0]+(24 if diag else 0),p[1]+(4 if diag else 19),'$u_{'+name+'}$',10,color=ORANGE if v==0 else BLUE,ha='left' if diag else 'center')
        for sign,name in [(1,'+'),(-1,'−')]:
            p=pos(mid+sign*tv*W);edge(ax,p,GREEN,diag)
            text(ax,p[0]+21,p[1]-24,'u_t'+name,9.4,color=GREEN)
            face=mid+sign*tv*W/2
            arrow(ax,[pos(face-sign*tv*.23),pos(face+sign*tv*.42)],'#d9922a',1.25)
        # Streamwise face fluxes point c -> n; the lateral fluxes point outward.
        for p,shift,key in [(c,-.33,'c'),(n,.33,'n')]:
            pp=p+tv*.22
            arrow(ax,[pos(pp-dv*.25),pos(pp+dv*.25)],'#d9922a',1.3)
            q=pos(p-dv*.32-tv*.47) if key=='c' else pos(p+dv*.56-tv*.69)
            text(ax,*q,'q_'+key,10,color='#b2791a',ha='center')
        text(ax,*pos(c-tv*.14),'c',10,ha='center',va='bottom')
        text(ax,*pos(n-tv*.14),'n',10,ha='center',va='bottom')
        for p in [c,n]:line(ax,[pos(p),pos(p+tv*W)],GREEN,1.0,ls=':',z=5)
        if diag:
            text(ax,995,1159,t['diag_dim'],10.5,color='#b2791a')
        else:
            dimension(ax,(pos(c)[0],661),(pos(n)[0],661),'L',(pos(mid)[0],625))
            dimension(ax,pos(mid+dv*3.2-tv*W/2),pos(mid+dv*3.2+tv*W/2),'W',pos(mid+dv*3.7-tv*.16))
            block(ax,48,1060,t['axis_dim'],820,10.5,color='#b2791a')
            block(ax,48,1107,t['flow'],825,10)
    block(ax,970,1205,t['side'],782,9.6,color=GREEN)
    block(ax,48,1305,t['area'],1704,10)
    text(ax,48,1367,t['legend'],9.8,color=MUTED)
    return fig


def build_muscl(lang):
    t=M[lang];fig,base=canvas(1050)
    text(base,48,32,'(a) '+('面cの再構成：q_c > 0' if lang=='ja' else 'Reconstruction at face c: q_c > 0'),13,weight='bold')
    text(base,1000,32,t['b'],13,weight='bold')
    ax=plot_axes(fig,65,117,835,470);ax.axis('off')
    xs=np.array([0,1,2,3,4]);us=np.array([.35,.45,.95,1.05,1.08])
    for x in xs:ax.axvline(x,color=RULE,lw=.8)
    ax.axvspan(1,2,color='#dbe8fa',alpha=.5);ax.axvspan(2,3,color='#fbefd8',alpha=.5)
    ax.axvline(1.5,color='#d9922a',lw=1.6,ls='--')
    ax.plot(xs,us,'o',color=BLUE,ms=6,gid='edge-values')
    for x,u,name in zip(xs,us,['mm','m','e','p','pp']):
        ax.text(x,u-.105,'$u_{'+name+'}$',fontsize=10,color=ORANGE if name=='e' else BLUE,ha='center',va='top')
    d=us[2]-us[1];r=(us[1]-us[0])/d;psi=(r+abs(r))/(1+abs(r));f3=us[1]+.5*psi*d
    ax.plot([1,1.5],[us[1],us[1]],color='#8fbf6a',lw=1.4)
    ax.plot([1.5],[us[1]],'s',color='#8fbf6a',ms=8,mfc='white',mew=1.6,gid='face-upwind')
    ax.plot([1,1.5],[us[1],f3],color=ORANGE,lw=1.6)
    ax.plot([1.5],[f3],'D',color=ORANGE,ms=7,gid='face-muscl')
    ax.text(1.70,us[1]-.01,'2',color=GREEN,fontsize=10,va='top')
    ax.text(1.70,f3+.025,'3',color=ORANGE,fontsize=10,va='bottom')
    ax.annotate('',xy=(.9,1.3),xytext=(.1,1.3),arrowprops={'arrowstyle':'-|>','color':BLUE,'lw':1.4})
    ax.text(.5,1.4,t['flow'],fontsize=9.5,ha='center',color=BLUE)
    ax.text(1.5,1.49,t['face'],fontsize=10,ha='center',color='#b2791a',bbox=dict(fc='#eef3fa',ec='none',pad=1))
    for x,key in [(1.20,'cell_c'),(2.5,'cell_n')]:ax.text(x,.08,t[key],fontsize=9,ha='center',color=MUTED)
    ax.set(xlim=(-.3,4.6),ylim=(0,1.6))
    for yy,key,col in [(631,'s2',GREEN),(691,'s3',ORANGE),(751,'r',ORANGE)]:block(base,48,yy,t[key],870,10,color=col)
    text(base,48,831,'r = 0.2,  ψ = 1/3,  ū_c = 0.5333…',10.5,color=ORANGE)
    block(base,48,900,'左図の5つの値：0.35, 0.45, 0.95, 1.05, 1.08。側方面の再構成は1次風上です。' if lang=='ja' else 'Five edge values: 0.35, 0.45, 0.95, 1.05, 1.08. Lateral faces remain first-order upwind.',870,9.7,color=MUTED)
    ax=plot_axes(fig,1050,117,692,470)
    rr=np.linspace(-1,4,400)
    lo=np.clip(np.minimum(rr,1),0,None);hi=np.clip(np.minimum(2*rr,2),0,None)
    ax.fill_between(rr,lo,hi,color='#eef3fa',zorder=0,gid='tvd-region')
    ax.plot(rr,(rr+np.abs(rr))/(1+np.abs(rr)),color=ORANGE,lw=2,gid='van-leer')
    ax.axhline(1,color=BLUE,lw=1,ls='--');ax.plot(rr,rr,color=MUTED,lw=.9,ls=':');ax.axhline(0,color=GREEN,lw=1,ls='-.')
    ax.set(xlim=(-1,4),ylim=(-.2,2.5),xlabel=t['xlabel'],ylabel=r'$\psi(r)$')
    legend_rows(base,1000,673,[(ORANGE,'-',t['vl']),(BLUE,'--',t['central']),(MUTED,':',t['lw']),(GREEN,'-.',t['upwind'])],752,58,9)
    rect(base,1000,922,32,22,'#eef3fa');text(base,1059,920,t['tvd'],9.5)
    block(base,1000,976,t['ext'],752,9.2,color=MUTED)
    return fig


def draw_cv(lang):
    with drawing_style():return export(build_cv(lang),'advection_cv',lang)


def draw_muscl(lang):
    with drawing_style():return export(build_muscl(lang),'advection_muscl',lang)


def draw(lang):
    draw_muscl(lang)
    return draw_cv(lang)
