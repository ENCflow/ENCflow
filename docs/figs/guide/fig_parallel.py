"""MPI ownership, cell halos, OpenMP work sharing and ordered row sums.

The 10-column, 12-row example has uniform row weights and three ranks.
Owner and copy views share global row coordinates. Hatching denotes copies,
never additional ownership. The four-thread assignment is illustrative.
Generate only this bilingual PNG/SVG pair: make_guide_figs.py parallel.
"""
from io import StringIO
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1450), 150
BAND = ['#e8eef8', '#fbefd8', '#e6f1dd']
THREAD = ['#3877aa', '#568344', '#bd6338', '#927322']
THREAD_FILL = ['#edf3fa', '#eef5e8', '#fcf0e8', '#f6f2df']
COPY = '#b96335'
NX, NY, NRANK, NHALO = 10, 12, 3, 2
GLOBAL = (180, 236, 30, 31)  # x, row-1 y, column width, row height
LOCAL_X = 850
BANDS = [(1, 4), (5, 8), (9, 12)]
RECEIVED = [(0, 3, 4), (2, 9, 10)]
SENT = [(0, 5, 6), (2, 7, 8)]

T = {
 'ja': {
  'title':'並列実行  |  担当帯・ハロ・スレッドの関係',
  'sub':'encflow: OpenMP  /  encflow_mpi: MPI × OpenMP  •  サイズ・ランク数・スレッド数は説明例。',
  'a':'(a) MPI: 所有する行と、隣の行の写しを分ける',
  'a_sub':'10列 × 12行を3ランクで分担する例。色は所有ランク、斜線はハロの写しを示す。',
  'global':'全域の所有範囲', 'local':'rank 1 のセル配列',
  'alloc':'確保範囲: jsh = 3 … jeh = 10',
  'copy0':'rank 0 → rank 1: 3–4行の写し',
  'copy2':'rank 2 → rank 1: 9–10行の写し',
  'same':'同じ担当行を右に表示', 'owned':'担当行: js = 5 … je = 8',
  'h0':'上側ハロ2行\nrank 0 の写し', 'h1':'担当帯4行\n更新する値の正本', 'h2':'下側ハロ2行\nrank 2 の写し',
  'return':'矢印は rank 1 の受信例。逆向きには5–6行を rank 0 へ、\n7–8行を rank 2 へ送る。ハロは必要な計算の前に更新する。',
  'j':'j: 北 → 南に増加', 'i':'i: 西 → 東に増加',
  'partition':'実際の帯境界は行ごとの有効セル数で決める。各帯は最低2行。図は各行の重みが同じ場合。',
  'clip':'確保範囲は全域端でクリップする。図はセル配列の交換例で、エッジ配列の交換は別に行う。',
  'b':'(b) OpenMP: ランク内でループを分担',
  'b_sub':'rank 1 の担当行5–8、4スレッドの説明例',
  'thread':'スレッド {k}', 'shared':'共有メモリ上の担当帯',
  'b_note':'各スレッドが行ループを分担する。割り当てはループに依存し、\n図の1行1スレッドに固定されない。\nOMP_NUM_THREADS で1ランクあたりの数を指定する。',
  'c':'(c) 総和: 行の並びを保って集約',
  'c_sub':'各行の部分和 S_j（real64）を作る例',
  'rows':'S{a} … S{b}', 'assemble':'rank 0: S1, S2, …, S12（j 昇順）',
  'sum':'sum(buf) で一括総和 → 全ランクへ共有',
  'output':'分布出力も担当行を rank 0 に集約して保存。\nハロの写しは重複して数えない。',
  'condition':'再現性の前提',
  'repro1':'同じ実行ファイル・精度・入力・計算環境: スレッド数・MPIランク数によらず数値結果はビット一致。',
  'repro2':'別ビルド間: -Ofast では逐次版 ↔ MPI版で最終桁の差が出る場合がある。',
  'repro3':'厳密比較は -O2 の厳密数学条件で、コンパイラ・精度などを揃える。詳細と再開条件は本文参照。',
 },
 'en': {
  'title':'Parallel execution  |  Owned bands, halos and threads',
  'sub':'encflow: OpenMP  /  encflow_mpi: MPI × OpenMP  •  Sizes, rank counts and thread counts are illustrative.',
  'a':'(a) MPI: distinguish owned rows from copies',
  'a_sub':'Example: 10 columns × 12 rows, three ranks. Color identifies the owner; hatching identifies halo copies.',
  'global':'Global ownership', 'local':'Cell array on rank 1',
  'alloc':'Allocated: jsh = 3 … jeh = 10',
  'copy0':'rank 0 → rank 1: copy rows 3–4',
  'copy2':'rank 2 → rank 1: copy rows 9–10',
  'same':'Same owned rows', 'owned':'Owned: js = 5 … je = 8',
  'h0':'Upper halo: 2 rows\nCopies from rank 0', 'h1':'Owned band: 4 rows\nAuthoritative values', 'h2':'Lower halo: 2 rows\nCopies from rank 2',
  'return':'Arrows show reception by rank 1. It also sends rows 5–6 to rank 0\nand rows 7–8 to rank 2. Refresh halos before the relevant operations.',
  'j':'j increases north → south', 'i':'i increases west → east',
  'partition':'Actual bands use active-cell counts per row, with at least two rows per rank. Here all row weights are equal.',
  'clip':'Allocation is clipped at domain edges. This example shows cell arrays; edge arrays have separate exchanges.',
  'b':'(b) OpenMP: share loops within a rank',
  'b_sub':'Illustration: rank 1 owns rows 5–8, with four threads',
  'thread':'thread {k}', 'shared':'Owned band in shared memory',
  'b_note':'Threads share row-loop work. Assignment depends on the loop;\nit is not fixed to the one-row-per-thread example.\nOMP_NUM_THREADS sets the count per rank.',
  'c':'(c) Sums: assemble rows in global order',
  'c_sub':'Example: partial sums S_j (real64), one per row',
  'rows':'S{a} … S{b}', 'assemble':'rank 0: S1, S2, …, S12 (increasing j)',
  'sum':'sum(buf) once → broadcast total to all ranks',
  'output':'Field output also gathers owned rows to rank 0 for writing.\nHalo copies are not counted again.',
  'condition':'Conditions for reproducibility',
  'repro1':'Same executable, precision, input and computing environment: numerical results are bitwise independent of thread / rank count.',
  'repro2':'Across builds: -Ofast can cause last-bit differences between serial and MPI executables.',
  'repro3':'For bitwise comparisons use strict -O2 mathematics and matching compiler / precision. See text for details and restart conditions.',
 },
}


def row_y(j):
    return GLOBAL[1]+(j-1)*GLOBAL[3]


def rect(ax,key,x,y,w,h,fill='white',edge=RULE,lw=.8,hatch=None):
    a=Rectangle((x,y),w,h,facecolor=fill,edgecolor=edge,linewidth=lw,hatch=hatch,zorder=2)
    a.set_gid(key);ax.add_patch(a)
    return a


def connector(ax,key,points,color=COPY):
    a=arrow(ax,points,color,lw=1.15,size=9);a.set_gid(key)
    return a


def grid(ax,key,x,j1,j2,*,local=False):
    """Identical row coordinates in the owner and copy views."""
    _,_,cw,ch=GLOBAL
    for j in range(j1,j2+1):
        owner=next(r for r,(lo,hi) in enumerate(BANDS) if lo<=j<=hi)
        halo=local and owner!=1
        rect(ax,f'{key}_row_{j}',x,row_y(j),NX*cw,ch,BAND[owner],COPY if halo else RULE,
             lw=.45,hatch='///' if halo else None)
        text(ax,x-13,row_y(j)+ch/2,str(j),size=8.3,ha='right',va='center',color=MUTED)
    for k in range(1,NX):
        line(ax,[(x+k*cw,row_y(j1)),(x+k*cw,row_y(j2+1))],RULE,.45,z=3)
    rect(ax,f'{key}_outline',x,row_y(j1),NX*cw,(j2-j1+1)*ch,'none',INK,1)


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0));ax.axis('off')
    text(ax,35,22,t['title'],size=12,weight='bold')
    text(ax,35,65,t['sub'],size=8.8,color=MUTED)
    text(ax,35,113,t['a'],size=10.5,weight='bold')
    text(ax,35,153,t['a_sub'],size=9,color=MUTED)
    text(ax,180,198,t['global'],size=9.3,weight='bold')
    grid(ax,'global',GLOBAL[0],1,NY)
    for r,(a,b) in enumerate(BANDS):
        text(ax,72,(row_y(a)+row_y(b+1))/2,f'rank {r}',size=9,weight='bold',va='center')
        if r:line(ax,[(180,row_y(a)),(480,row_y(a))],INK,1.3,z=4)
    connector(ax,'j_direction',[(45,245),(45,600)],MUTED)
    text(ax,35,622,t['j'],size=8.4,color=MUTED)
    text(ax,340,622,t['i'],size=8.4,color=MUTED)
    text(ax,850,228,t['local'],size=9.3,weight='bold')
    text(ax,850,263,t['alloc'],size=8.6,color=MUTED)
    grid(ax,'local',LOCAL_X,3,10,local=True)
    rect(ax,'local_owned',850,row_y(5),300,4*GLOBAL[3],'none',INK,1.3)
    for owner,a,b in RECEIVED:
        y=(row_y(a)+row_y(b+1))/2
        rect(ax,f'source_{owner}',180,row_y(a),300,2*GLOBAL[3],'none',COPY,1.1)
        connector(ax,f'copy_{owner}',[(480,y),(850,y)])
    text(ax,521,289,t['copy0'],size=8.3,color=COPY)
    text(ax,521,544,t['copy2'],size=8.3,color=COPY)
    for j in [5,9]:line(ax,[(480,row_y(j)),(850,row_y(j))],MUTED,.75,ls='--').set_gid(f'owned_guide_{j}')
    text(ax,535,386,t['same'],size=8.4,color=MUTED)
    text(ax,535,425,t['owned'],size=8.4,color=INK)
    for key,j in [('h0',3),('h1',6),('h2',9)]:
        block(ax,1190,row_y(j)+7,t[key],345,size=8.7)
    block(ax,850,576,t['return'],690,size=8.2,color=MUTED)
    text(ax,35,663,t['partition'],size=8.8)
    text(ax,35,698,t['clip'],size=8.7,color=MUTED)
    line(ax,[(35,738),(1540,738)],RULE,.8)
    # OpenMP work sharing: illustrative assignment to the four owned rows.
    text(ax,35,766,t['b'],size=10,weight='bold')
    text(ax,35,808,t['b_sub'],size=8.7,color=MUTED)
    text(ax,195,864,t['shared'],size=9,weight='bold')
    for k in range(4):
        y=915+36*k
        rect(ax,f'thread_{k}',35,y+4,132,28,THREAD_FILL[k],THREAD[k],.9)
        text(ax,101,y+18,t['thread'].format(k=k),size=8.2,ha='center',va='center',color=THREAD[k])
        connector(ax,f'thread_to_row_{k}',[(167,y+18),(195,y+18)],THREAD[k])
        rect(ax,f'work_row_{k}',195,y,450,36,THREAD_FILL[k],THREAD[k],.55)
        text(ax,660,y+18,f'j = {k+5}',size=8.7,va='center',color=MUTED)
    for k in range(1,NX):line(ax,[(195+45*k,915),(195+45*k,1059)],RULE,.5,z=4)
    block(ax,35,1093,t['b_note'],700,size=8.7)
    # Row identity is kept by MPI_Gatherv before one SUM on rank 0.
    text(ax,795,766,t['c'],size=10,weight='bold')
    text(ax,795,808,t['c_sub'],size=8.7,color=MUTED)
    centers=[]
    for r,(a,b) in enumerate(BANDS):
        x=795+250*r;centers.append(x+112.5)
        rect(ax,f'sums_rank_{r}',x,859,225,63,BAND[r],RULE)
        text(ax,x+112.5,869,f'rank {r}',size=8.8,weight='bold',ha='center')
        text(ax,x+112.5,895,t['rows'].format(a=a,b=b),size=8.5,ha='center')
        line(ax,[(x+112.5,922),(x+112.5,943)],MUTED,.85).set_gid(f'sums_to_bus_{r}')
    line(ax,[(centers[0],943),(centers[-1],943)],MUTED,.85).set_gid('sum_bus')
    connector(ax,'sum_bus_to_array',[(1157.5,943),(1157.5,965)],MUTED)
    rect(ax,'row_array',795,965,725,50,'#f4f3ee',RULE)
    text(ax,1157.5,990,t['assemble'],size=9,ha='center',va='center')
    connector(ax,'array_to_sum',[(1157.5,1015),(1157.5,1035)],MUTED)
    text(ax,1157.5,1044,t['sum'],size=8.9,ha='center')
    rect(ax,'output_note',795,1090,725,93,'#f7f8f5',RULE)
    block(ax,815,1107,t['output'],685,size=8.7)
    # Build comparisons are separate from decomposition reproducibility.
    rect(ax,'repro_box',35,1230,1505,187,'#eef5e8',RULE)
    text(ax,55,1247,t['condition'],size=10,weight='bold',color='#426b34')
    for k in range(3):text(ax,55,1286+35*k,t[f'repro{k+1}'],size=8.5)
    return fig


def draw(lang):
    if lang not in T:raise ValueError('lang must be ja or en')
    out=Path(__file__).resolve().parents[1]/('parallel_bands'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            fig.savefig(out,dpi=DPI)
            svg=StringIO()
            fig.savefig(svg,format='svg',metadata={'Date':None,
                'Description':'Illustrative MPI bands, cell halo copies, OpenMP loop work sharing, ordered row sums, and build conditions for numerical reproducibility.'})
            out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in svg.getvalue().splitlines())+'\n',encoding='utf-8',newline='\n')
        finally:plt.close(fig)
    return str(out)
