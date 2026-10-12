"""Post-processing route: ENCflow output -> out2vtk -> ParaView (JA / EN).

Rebuild: python docs/figs/make_guide_figs.py visualization

Implementation: utils/out2vtk/out2vtk.f90, out2vtk_run / inherit_param /
read_filenumber / write_terrain / write_flood_series / write_flood_one.
The example names use the default directory and no outfn_suffix.
Frame labels t0, t1, t2 denote recorded times, not equal time intervals.
This is a file-flow schematic, not a ParaView screenshot or a simulation.
"""
from io import StringIO
from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle

from _schematic import drawing_style, text, block, arrow, INK, MUTED, RULE

DPI, WIDTH, HEIGHT = 150, 1800, 1000
BLUE, ORANGE, GREEN = '#2a78d6', '#cf5a27', '#527d37'
PALE_BLUE, PALE_ORANGE, PALE_GREEN = '#eef4fc', '#fcf0e9', '#f0f5e9'


def rect(ax, x, y, w, h, fill='white', edge=RULE, gid=None):
    patch = Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge,
                      linewidth=1, gid=gid)
    ax.add_patch(patch)
    return patch


def build(lang):
    t = lambda ja, en: ja if lang == 'ja' else en
    fig = plt.figure(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, WIDTH), ylim=(HEIGHT, 0))
    ax.axis('off')
    text(ax, 55, 36, t('計算結果を3Dで見る：変換して、2つのファイルを開く',
                      'View results in 3D: convert, then open two files'), 20, weight='bold')
    text(ax, 57, 98, t('まずは計算に使った param.txt を渡すだけ。変換用の設定ファイルは不要。',
                      'Start with the param.txt used for the run. No separate converter settings are needed.'),
         11.5, color=MUTED)

    titles = [t('①  計算結果を用意', '1   Keep the simulation output'),
              t('②  1コマンドで変換', '2   Convert with one command'),
              t('③  ParaView で開く', '3   Open in ParaView')]
    for x, title, color in zip([60,660,1260],titles,[INK,ORANGE,BLUE]):
        text(ax,x,165,title,14,color=color,weight='bold')
        rect(ax,x,230,480,382,gid='step-'+str(x))

    text(ax,85,257,'param.txt',14,weight='bold')
    text(ax,85,316,'result/',13,weight='bold')
    for y,s in [(365,'Z0000.*'),(408,'H0000.*, H0001.*, …'),(451,'FILENUMBER.csv')]:
        text(ax,112,y,s,12.5)
    text(ax,85,544,'txt / bil + hdr / GeoTIFF',11,color=MUTED)
    arrow(ax,[(554,414),(642,414)],ORANGE)

    text(ax,685,257,t('計算ケースのディレクトリで', 'In the simulation case directory'),11)
    rect(ax,679,310,442,70,PALE_ORANGE,'none',gid='command')
    text(ax,698,331,'../../bin/out2vtk param.txt',12.5,color=ORANGE,weight='bold')
    text(ax,685,425,'result/vtk/',13,weight='bold')
    text(ax,711,475,'terrain.vts',13,color=GREEN,weight='bold')
    text(ax,711,522,'flood.pvd',13,color=BLUE,weight='bold')
    text(ax,685,576,t('＋ 各時刻の flood_XXXX.vts', '+ flood_XXXX.vts for each time'),10.5,color=MUTED)
    arrow(ax,[(1154,414),(1242,414)],BLUE)

    text(ax,1285,257,'File → Open → Apply',13,weight='bold')
    rect(ax,1282,327,436,66,PALE_GREEN,'none',gid='open-terrain')
    text(ax,1300,346,'terrain.vts',13,color=GREEN,weight='bold')
    text(ax,1685,349,t('地形', 'terrain'),11,ha='right',color=GREEN)
    rect(ax,1282,408,436,66,PALE_BLUE,'none',gid='open-water')
    text(ax,1300,427,'flood.pvd',13,color=BLUE,weight='bold')
    text(ax,1685,430,t('水面', 'water'),11,ha='right',color=BLUE)
    text(ax,1285,517,t('H（水深）で色分けして ▶ 再生', 'Color by H (depth), then press Play'),11.5)
    text(ax,1285,571,t('地形と水面を重ねて見る', 'View the water surface over the terrain'),10.5,color=MUTED)

    text(ax,60,677,t('flood.pvd が、水面ファイルと計算時刻をまとめる',
                    'flood.pvd links the water surfaces to their simulation times'),13,weight='bold')
    rect(ax,60,740,430,162,PALE_BLUE,'none',gid='collection')
    text(ax,85,761,'flood.pvd',15,color=BLUE,weight='bold')
    block(ax,85,819,t('FILENUMBER.csv の時刻を使う\nParaView の時刻表示は秒',
                     'Times from FILENUMBER.csv\nParaView time is in seconds'),380,11)
    arrow(ax,[(504,820),(603,820)],BLUE)
    for x,label,time in [(625,'flood_0000.vts','t₀'),(1005,'flood_0001.vts','t₁'),(1385,'flood_0002.vts','t₂')]:
        rect(ax,x,740,355,162,'#f7f8fa',RULE,gid=label)
        text(ax,x+20,764,label,12.5,color=BLUE,weight='bold')
        text(ax,x+20,821,t('水面標高 = Z + H', 'Water elevation = Z + H'),10.5)
        text(ax,x+20,866,'t = '+time,11,color=MUTED)
    text(ax,60,938,t('flood.pvd と flood_XXXX.vts は、同じフォルダにまとめておく。',
                    'Keep flood.pvd and all flood_XXXX.vts files together in the same folder.'),11,color=MUTED)
    return fig


def export(fig,lang):
    stem='visualization_workflow'+('' if lang=='ja' else '_en')
    dest=Path(__file__).resolve().parents[1]/stem
    fig.savefig(dest.with_suffix('.png'),dpi=DPI)
    svg=StringIO()
    fig.savefig(svg,format='svg',metadata={'Date':None})
    dest.with_suffix('.svg').write_text('\n'.join(x.rstrip() for x in svg.getvalue().splitlines())+'\n',
                                       encoding='utf-8',newline='\n')
    plt.close(fig)
    return str(dest.with_suffix('.png'))


def draw(lang):
    with drawing_style():
        return export(build(lang),lang)
