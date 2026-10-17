"""advection scheme design supplement (docs/advection_design.md): parity sub-lattices,
the lateral faces of diagonal edges before/after 2026-10-17, and verification curves.

Regenerate only this page with make_guide_figs.py advscheme.  The numerical
curves are copied from test/dambreak (stoker.csv, t = 30 s) and
test/sublattice (Check_sublattice.py, mixed configuration) so that the figure
needs no result files; refresh them when those tests change.
"""
from _terms import *

T = {'ja': {
 'p_a': '(a) 偶奇の副格子と 8 本のリンク',
 'p_b': '(b) 副格子で逆回転する斜め循環(移流項に見えないモード)',
 'p_note': '斜めリンク(細い実線)は i+j の偶奇が同じセル(同色)だけを結ぶ。法線リンク(太い灰線)が両者を結ぶ。',
 'p_note2': '偶数セル(青)の渦と奇数セル(橙)の逆向きの渦。法線エッジの流速は両セル平均で 0、発散もゼロ。',
 'l_a': '(a) 修正前: 同じ偶奇の平行リンク(距離 √2Δ)を風上値に',
 'l_b': '(b) 現行: 反対偶奇の平行リンク 2 本の平均(幅 W = Δ/√2)',
 'l_note': '橙: 検査体積。緑 ◇: 側方面の流入値 ū_t に使うリンク。点線: 側方面を横切る他方の対角リンク(流量 q_t。両案で共通)。',
 'l_dim_a': 'W = 2ΔxΔy/Δr = √2Δ', 'l_dim_b': 'W = ΔxΔy/Δr = Δ/√2',
 'r_a': '(a) ダム破壊(Stoker 解、t = 30 s)', 'r_b': '(b) 副格子モードの減衰(test/sublattice、mixed)',
 'r_num': '数値(スキーム 3)', 'r_ana': '解析解', 'r_x': 'x (m)', 'r_h': '水深 (m)',
 'r_t': 't (s)', 'r_amp': '副格子モードの振幅 / 初期値',
 'r_old': 'スキーム 3(修正前)', 'r_new': 'スキーム 3(現行)', 'r_s1': 'スキーム 1',
}, 'en': {
 'p_a': '(a) Parity sub-lattices and the eight links',
 'p_b': '(b) Diagonal circulation rotating oppositely on the sub-lattices (invisible to advection)',
 'p_note': 'Diagonal links (thin) connect only cells of the same parity of i+j (same colour); axis links (thick grey) connect the two.',
 'p_note2': 'Gyre on even cells (blue) and the opposite gyre on odd cells (orange): axis-edge velocities average to zero, divergence is zero.',
 'l_a': '(a) Before: the same-parity parallel link (distance √2Δ) as upwind value',
 'l_b': '(b) Now: mean of the two opposite-parity parallel links (width W = Δ/√2)',
 'l_note': 'Orange: control volume. Green ◇: links used for the inflow value ū_t. Dotted: the other-diagonal links crossing the faces (flux q_t, same in both).',
 'l_dim_a': 'W = 2ΔxΔy/Δr = √2Δ', 'l_dim_b': 'W = ΔxΔy/Δr = Δ/√2',
 'r_a': '(a) Dam break (Stoker solution, t = 30 s)', 'r_b': '(b) Decay of the sub-lattice mode (test/sublattice, mixed)',
 'r_num': 'numerical (scheme 3)', 'r_ana': 'analytic', 'r_x': 'x (m)', 'r_h': 'depth (m)',
 'r_t': 't (s)', 'r_amp': 'sub-lattice mode amplitude / initial',
 'r_old': 'scheme 3 (before)', 'r_new': 'scheme 3 (now)', 'r_s1': 'scheme 1',
}}

EVEN, ODD = '#dbe8fa', '#fbefd8'
STOKER_X = [601, 609, 617, 625, 633, 641, 649, 657, 665, 673, 681, 689, 697, 705, 713, 721, 729, 737, 745, 753, 761, 769, 777, 785, 793, 801, 809, 817, 825, 833, 841, 849, 857, 865, 873, 881, 889, 897, 905, 913, 921, 929, 937, 945, 953, 961, 969, 977, 985, 993]
STOKER_HN = [3.920, 3.920, 3.921, 3.922, 3.922, 3.922, 3.918, 3.913, 3.911, 3.910, 3.909, 3.909, 3.908, 3.907, 3.906, 3.906, 3.907, 3.906, 3.905, 3.906, 3.907, 3.908, 3.908, 3.903, 3.911, 1.011, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000]
STOKER_HA = [3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 3.962, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000]
SUB_T = [0, 300, 600, 900, 1200, 1500, 1800, 2100, 2400, 2700, 3000, 3300, 3600]
SUB_OLD = [1.0, 0.559, 0.525, 0.474, 0.409, 0.336, 0.258, 0.182, 0.111, 0.052, 0.005, -0.027, -0.047]
SUB_NEW = [1.0, 0.032, 0.0076, 0.0016, 0.0004, 0, 0, 0, 0, 0, 0, 0, 0]
SUB_S1 = [1.0, 0.284, 0.148, 0.080, 0.045, 0.027, 0.017, 0.011, 0.008, 0.006, 0.005, 0.005, 0.004]


def build_parity(lang):
    t=T[lang];fig,ax=canvas(1000)
    text(ax,48,32,t['p_a'],13,weight='bold');text(ax,900,32,t['p_b'],13,weight='bold')
    for panel,x0 in [(0,110),(1,960)]:
        y0,d,n=120,96,6
        for i in range(n):
            for j in range(n):
                rect(ax,x0+i*d,y0+j*d,d,d,EVEN if (i+j)%2==0 else ODD)
        grid(ax,x0,y0,n,n,d)
        cen=lambda i,j:(x0+(i+.5)*d,y0+(j+.5)*d)
        if panel==0:
            for i in range(n):
                for j in range(n):
                    p=np.array(cen(i,j))
                    for a,b in [(1,0),(0,1)]:
                        if i+a<n and j+b<n:line(ax,[p,np.array(cen(i+a,j+b))],'#8a8983',2.2,z=3)
                    for a,b in [(1,1),(1,-1)]:
                        if i+a<n and 0<=j+b<n:line(ax,[p,np.array(cen(i+a,j+b))],BLUE if (i+j)%2==0 else ORANGE,1.0,z=4)
            for i in range(n):
                for j in range(n):dot(ax,cen(i,j),BLUE if (i+j)%2==0 else ORANGE)
            text(ax,x0+2.5*d,y0+n*d+30,'i+j even',10,color=BLUE,ha='center')
            text(ax,x0+3.5*d,y0+n*d+30,'i+j odd',10,color=ORANGE,ha='center')
        else:
            cx,cy=x0+n*d/2,y0+n*d/2
            for i in range(n):
                for j in range(n):
                    p=np.array(cen(i,j));r=p-np.array([cx,cy]);rr=np.hypot(*r)
                    if rr<1:continue
                    tang=np.array([-r[1],r[0]])/rr*min(rr,2.2*d)/(2.2*d)
                    s=1 if (i+j)%2==0 else -1
                    v=tang*s*34
                    arrow(ax,[p-v/2,p+v/2],BLUE if s==1 else ORANGE,1.4)
    block(ax,48,780,t['p_note'],1704,10,color=MUTED)
    block(ax,48,840,t['p_note2'],1704,10,color=MUTED)
    return fig


def build_lateral(lang):
    t=T[lang];fig,ax=canvas(1150)
    text(ax,48,32,t['l_a'],12.5,weight='bold');text(ax,920,32,t['l_b'],12.5,weight='bold')
    for panel,x0 in [(0,120),(1,980)]:
        y0,d,n=110,88,7
        for i in range(n):
            for j in range(n):
                rect(ax,x0+i*d,y0+j*d,d,d,EVEN if (i+j)%2==0 else ODD,alpha=.6)
        grid(ax,x0,y0,n,n,d)
        pos=lambda p:np.array([x0,y0])+np.asarray(p)*d
        c=np.array([3.5,3.5]);nn=c+np.array([-1,-1])
        dv=(nn-c)/np.linalg.norm(nn-c);tv=np.array([-dv[1],dv[0]])
        L=np.sqrt(2);W=np.sqrt(2) if panel==0 else 1/np.sqrt(2)
        mid=(c+nn)/2
        poly=np.array([c-tv*W/2,nn-tv*W/2,nn+tv*W/2,c+tv*W/2])
        patch=Polygon(pos(poly),fc='#fdf1dc',ec='#d9922a',lw=1.8,zorder=3);ax.add_patch(patch)
        for i in range(n):
            for j in range(n):dot(ax,pos([i+.5,j+.5]),BLUE if (i+j)%2==0 else ORANGE)
        # the edge e and the links along its line
        edge(ax,pos(mid),ORANGE,True);text(ax,*(pos(mid)+[14,-10]),'$u_e$',10,color=ORANGE)
        text(ax,*(pos(c)+[8,18]),'c',10);text(ax,*(pos(nn)+[-18,-8]),'n',10)
        # other-diagonal links crossing the faces (flux q_t): from c and n in direction +-t
        for base in [c,nn]:
            for s in [1,-1]:
                line(ax,[pos(base),pos(base+s*tv*np.sqrt(2))],GREEN,1.0,ls=':',z=5)
        # links used for u_t
        if panel==0:
            for s in [1,-1]:
                a=c+s*np.array([1,-1]);b=a+np.array([-1,-1])
                line(ax,[pos(a),pos(b)],BLUE,1.2,z=5);edge(ax,pos((a+b)/2),GREEN,True)
                text(ax,*(pos((a+b)/2)+[16,-6]),'u_t'+('+' if s==1 else '−'),9.5,color=GREEN)
            dimension(ax,pos(mid+dv*1.4),pos(mid+dv*1.4+tv*np.sqrt(2)),'W',pos(mid+dv*1.75+tv*.7))
            text(ax,x0,y0+n*d+40,t['l_dim_a'],10.5,color='#b2791a')
        else:
            for s in [1,-1]:
                for off in [np.array([s,0]),np.array([0,-s])]:
                    a=c+off;b=a+np.array([-1,-1])
                    line(ax,[pos(a),pos(b)],BLUE,1.2,z=5);edge(ax,pos((a+b)/2),GREEN,True)
                text(ax,*(pos(mid+s*tv/np.sqrt(2))+[18,-14]),'u_t'+('+' if s==1 else '−'),9.5,color=GREEN)
            dimension(ax,pos(mid+dv*1.4),pos(mid+dv*1.4+tv/np.sqrt(2)),'W',pos(mid+dv*1.75+tv*.35))
            text(ax,x0,y0+n*d+40,t['l_dim_b'],10.5,color='#b2791a')
    block(ax,48,1010,t['l_note'],1704,10,color=MUTED)
    return fig


def build_results(lang):
    t=T[lang];fig,base=canvas(760)
    text(base,48,32,t['r_a'],13,weight='bold');text(base,940,32,t['r_b'],13,weight='bold')
    ax=plot_axes(fig,90,100,760,560)
    ax.plot(STOKER_X,STOKER_HA,color=MUTED,lw=1.6,ls='--',label=t['r_ana'])
    ax.plot(STOKER_X,STOKER_HN,color=ORANGE,lw=1.6,label=t['r_num'])
    ax.set(xlabel=t['r_x'],ylabel=t['r_h'],xlim=(600,1000),ylim=(0,5));ax.legend(fontsize=9,frameon=False)
    ax=plot_axes(fig,980,100,760,560)
    ax.plot(SUB_T,SUB_OLD,'o-',color=MUTED,lw=1.4,ms=4,label=t['r_old'])
    ax.plot(SUB_T,SUB_S1,'s-',color=BLUE,lw=1.4,ms=4,label=t['r_s1'])
    ax.plot(SUB_T,SUB_NEW,'D-',color=ORANGE,lw=1.6,ms=4,label=t['r_new'])
    ax.axhline(0,color=RULE,lw=.8)
    ax.set(xlabel=t['r_t'],ylabel=t['r_amp'],xlim=(0,3600),ylim=(-.1,1.05));ax.legend(fontsize=9,frameon=False)
    return fig


def draw(lang):
    with drawing_style():
        export(build_parity(lang),'advscheme_parity',lang)
        export(build_lateral(lang),'advscheme_lateral',lang)
        return export(build_results(lang),'advscheme_results',lang)
