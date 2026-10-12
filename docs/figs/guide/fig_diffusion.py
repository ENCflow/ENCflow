"""diffusion supplement: native bilingual schematic and unchanged numerical curves.

Regenerate only this page with make_guide_figs.py diffusion.
"""
from _terms import *

N = {'ja': {'a': '(a) ゼロ方程式モデル  ν = ν0 + α·u*·h,  u* = √g·n·|V|·h^(−1/6)',
        'b': '(b) 陽解法の安定上界  ν_max = Δx²/(2.83·dt)(既定の p_diagratio)',
        'xlabel_a': '水深 h (m)',
        'ylabel_a': 'ν (m²/s)',
        'l1': 'α = 0.41/6(既定。Elder 型)、n = 0.03、|V| = 1 m/s',
        'l2': 'α = 0.3(横断混合を強める校正例)、n = 0.03、|V| = 1 m/s',
        'l3': 'α = 0.41/6、n = 0.03、|V| = 3 m/s',
        'xlabel_b': '格子幅 Δx (m)',
        'ylabel_b': 'ν_max (m²/s)',
        'dt': 'dt = {v} s',
        'band': '実用的な ν の範囲(0.01〜10 m²/s)',
        'note': 'ν がこの上界を超えると\nモデル 2 はクランプ、モデル 1 は警告'},
 'en': {'a': '(a) Zero-equation model  ν = ν0 + α·u*·h,  u* = √g·n·|V|·h^(−1/6)',
        'b': '(b) Explicit stability bound  ν_max = Δx²/(2.83·dt) (default p_diagratio)',
        'xlabel_a': 'depth h (m)',
        'ylabel_a': 'ν (m²/s)',
        'l1': 'α = 0.41/6 (default, Elder type), n = 0.03, |V| = 1 m/s',
        'l2': 'α = 0.3 (calibration for stronger transverse mixing), n = 0.03, |V| = 1 m/s',
        'l3': 'α = 0.41/6, n = 0.03, |V| = 3 m/s',
        'xlabel_b': 'grid spacing Δx (m)',
        'ylabel_b': 'ν_max (m²/s)',
        'dt': 'dt = {v} s',
        'band': 'practical range of ν (0.01–10 m²/s)',
        'note': 'above this bound model 2 clamps ν\nand model 1 warns'}}

S={'ja':{
 'a':'(a) 8近傍のエッジから拡散項を組み立てる',
 'b':'(b) 乾燥・無効な近傍は no-flux 閉鎖',
 'wet':'有効・湿潤な近傍', 'dry':'乾燥\nh < dd', 'inv':'無効\n領域外',
 'arrows':'青矢印：差分を取る接続方向 ／ 橙の線分：通過幅 l_k ／ ●：セル中心',
 'axis':'軸方向：l = (1 − p_d)Δ、r = Δ',
 'diag':'対角方向：l = (p_d/√2)Δ、r = √2Δ',
 'square':'正方セルの例。p_d = p_diagratio、A = Δ²。',
 'zero':'灰の点線：そのエッジの寄与は0。\n残るエッジの重みは変えません。',
 'nu':'ν_e は両セルの粘性係数の算術平均。f は u または v。',
 'conservative':'同じエッジの寄与は両側セルで逆符号。湿潤なセル間で運動量を交換します。',
 'consistent':'軸・対角を合わせた整合な9点ラプラシアン。p_d = 0 なら通常の5点形。',
 'monotone':'非負の重みは空間的な極値を均す向きに働きます。時間更新の単調性には時間刻みの条件も必要です。',
 'edge':'セル中心で u・v の拡散項を計算 → 両側セルで平均 → エッジ法線へ投影して運動方程式へ加算。',
},'en':{
 'a':'(a) Build the diffusion term from 8 neighbouring edges',
 'b':'(b) Dry / invalid neighbours: no-flux closure',
 'wet':'Valid, wet neighbours', 'dry':'Dry\nh < dd', 'inv':'Invalid\noutside',
 'arrows':'Blue arrows: difference directions. Orange segments: passage widths l_k. Dots: cell centres.',
 'axis':'Axis: l = (1 − p_d)Δ, r = Δ',
 'diag':'Diagonal: l = (p_d/√2)Δ, r = √2Δ',
 'square':'Square-cell example; p_d = p_diagratio, A = Δ².',
 'zero':'Grey dotted segments: zero contribution.\nDo not renormalise the remaining weights.',
 'nu':'ν_e is the arithmetic mean of the two cell viscosities; f is u or v.',
 'conservative':'One edge contributes with opposite signs to its two cells, exchanging momentum between wet cells.',
 'consistent':'Axis + diagonal terms form a consistent 9-point Laplacian; p_d = 0 gives the standard 5-point form.',
 'monotone':'Non-negative weights smooth spatial extrema. Monotonicity of a time update also requires a suitable time step.',
 'edge':'Compute diffusion of u and v at cell centres → average the two cells → project onto the edge normal and add to momentum.',
}}
PD=2/(2+np.sqrt(2))
DEAD={(1,0):'dry',(1,1):'dry',(1,-1):'inv',(0,-1):'inv'}


def stencil_geometry():
    items=[]
    for di in [-1,0,1]:
        for dj in [-1,0,1]:
            if di==dj==0:continue
            offset=np.array([di,-dj],dtype=float);r=np.linalg.norm(offset)
            normal=offset/r;tangent=np.array([-normal[1],normal[0]])
            length=1-PD if r==1 else PD/np.sqrt(2)
            mid=.5*offset
            items.append(((di,dj),normal,mid-tangent*length/2,mid+tangent*length/2,length,r))
    return items


def build_stencil(lang):
    t=S[lang];fig,ax=canvas(1220)
    text(ax,48,32,t['a'],13,weight='bold');text(ax,948,32,t['b'],13,weight='bold')
    block(ax,48,93,t['arrows'],1704,10,color=MUTED)
    for x0,dead,prefix in [(120,{},'full'),(1100,DEAD,'closed')]:
        y0,dd=185,148;c=np.array([x0+1.5*dd,y0+1.5*dd])
        for di in [-1,0,1]:
            for dj in [-1,0,1]:
                p=c+np.array([di,-dj])*dd
                if (di,dj) in dead:
                    kind=dead[di,dj]
                    rect(ax,p[0]-dd/2,p[1]-dd/2,dd,dd,'#e6e4df',hatch='///' if kind=='inv' else None,zorder=0,gid=f'{prefix}-dead-{di}-{dj}')
                    text(ax,p[0],p[1]-55,t[kind],9.2,ha='center')
                dot(ax,p,gid=f'{prefix}-cell-{di}-{dj}')
        grid(ax,x0,y0,3,3,dd)
        for offset,normal,a,b,length,r in stencil_geometry():
            dropped=offset in dead
            line(ax,[c+a*dd,c+b*dd],MUTED if dropped else ORANGE,1.2 if dropped else 3.2,
                 ls=':' if dropped else '-',gid=f'{prefix}-width-{offset}',z=5)
            if not dropped:arrow(ax,[c+normal*27,c+normal*91],BLUE,1.2).set_gid(f'{prefix}-arrow-{offset}')
        text(ax,c[0]+43,c[1]-29,'$f_0$',10)
        if not dead:text(ax,c[0]+dd,c[1]-dd-35,'$f_k$',12,ha='center')
    text(ax,120,661,t['wet'],10.5,color=BLUE)
    block(ax,1030,661,t['zero'],722,10,color=MUTED)
    for y,k in [(719,'axis'),(767,'diag'),(820,'square')]:text(ax,48,y,t[k],10,color=ORANGE if k!='square' else MUTED)
    rect(ax,948,757,804,107,'#f4f5f2')
    text(ax,968,777,r'$\nu_e=(\nu_0+\nu_k)/2$',12,color=BLUE)
    block(ax,968,823,t['nu'],764,9.4)
    line(ax,[(48,899),(1752,899)],RULE,.9)
    text(ax,48,929,r'$\left.\nabla\!\cdot(\nu\nabla f)\right|_0\approx\frac{1}{A}\sum_{k=1}^{8}l_k\nu_e\frac{f_k-f_0}{r_k}$',14)
    block(ax,900,930,t['conservative'],852,10)
    block(ax,48,1020,t['consistent'],1704,10)
    block(ax,48,1080,t['monotone'],1704,10,color=GREEN)
    block(ax,48,1150,t['edge'],1704,9.6,color=MUTED)
    return fig


def build_nu(lang):
    t=N[lang];fig,base=canvas(1040)
    titles=['(a) ゼロ方程式モデルの渦動粘性','(b) 陽解法の安定上界'] if lang=='ja' else ['(a) Eddy viscosity: zero-equation model','(b) Explicit stability bound']
    text(base,48,32,titles[0],13,weight='bold');text(base,970,32,titles[1],13,weight='bold')
    text(base,48,81,r'$\nu=\nu_0+\alpha u_*h,\quad u_*=\sqrt{g}\,n\,|V|\,h^{-1/6}$',11)
    text(base,970,81,r'$\nu_{\max}=\Delta x^2/(2.83\,dt)$',11)
    ax=plot_axes(fig,113,157,700,450)
    g=9.81;h=np.linspace(.05,10,300)
    def nu(alpha,n,V):return alpha*np.sqrt(g)*n*V*h**(5/6)
    ax.plot(h,nu(.41/6,.03,1.),color=ORANGE,lw=2,gid='nu-default')
    ax.plot(h,nu(.3,.03,1.),color=BLUE,lw=1.5,ls='--',gid='nu-alpha03')
    ax.plot(h,nu(.41/6,.03,3.),color='#8fbf6a',lw=1.5,ls='-.',gid='nu-speed3')
    ax.set(xlim=(0,10),ylim=(0,1),xlabel=t['xlabel_a'],ylabel=t['ylabel_a'])
    legend_rows(base,48,703,[(ORANGE,'-',t['l1']),(BLUE,'--',t['l2']),('#8fbf6a','-.',t['l3'])],815,80,9.2)
    text(base,48,984,'図(a)は ν₀ = 0、g = 9.81 m/s² の例。' if lang=='ja' else 'Panel (a): ν₀ = 0 and g = 9.81 m/s².',9.5,color=MUTED)
    ax=plot_axes(fig,1040,157,684,450)
    dx=np.logspace(-1,3,200)
    ax.axhspan(.01,10,color='#eef3fa',zorder=0,gid='practical-band')
    items=[]
    for dt,col,ls in [(.01,ORANGE,'-'),(.1,BLUE,'--'),(1.,'#8fbf6a','-.'),(10.,MUTED,':')]:
        ax.plot(dx,dx**2/(2.83*dt),color=col,lw=1.6,ls=ls,gid='bound-'+str(dt))
        items.append((col,ls,t['dt'].format(v=dt)))
    ax.set(xscale='log',yscale='log',xlim=(.1,1000),ylim=(1e-4,1e6),xlabel=t['xlabel_b'],ylabel=t['ylabel_b'])
    legend_rows(base,970,703,items,782,48,9.5)
    rect(base,970,915,32,22,'#eef3fa');text(base,1027,915,t['band'],9.3,color=BLUE)
    block(base,970,966,t['note'],782,9.5,color=MUTED)
    return fig


def draw_stencil(lang):
    with drawing_style():return export(build_stencil(lang),'diffusion_stencil',lang)


def draw_nu(lang):
    with drawing_style():return export(build_nu(lang),'diffusion_nu',lang)


def draw(lang):
    draw_nu(lang)
    return draw_stencil(lang)
