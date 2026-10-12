"""Building debris: stock transfers, thresholds, porosity and volume bases.

The two-threshold ramp (curve, axes and labels) is preserved at its original
pixel scale from commit 386a6f1. It is embedded losslessly in PNG and SVG;
the rest is vector artwork. The crop excludes the unrelated criterion-arrow
annotation below its left corner. No graph is redrawn or resampled.
Generate only this figure: python docs/figs/make_guide_figs.py bldgdebris
"""
from io import BytesIO, StringIO
from pathlib import Path
import base64, hashlib
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, Circle
from PIL import Image
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

CANVAS, DPI = (1575, 1580), 150
BLUE, ORANGE, GREEN, BROWN = '#287ca5', '#b56432', '#52744b', '#876342'
RAMP_SOURCE_BOX = (520,98,900,260)
RAMP_REGIONS = ((520,98,900,220),(565,220,900,260))
RAMP_AT = (1110,186)
RAMP_SIZE = (380,162)
RAMP_SHA = {
 'ja':'1876e88c2031138744154ddeaf9fc89bc104c8bf7659f2c0e924b92d06d83353',
 'en':'06a1aacc676dfe4f142c5c4db19f9942556b51dcd46a64d960e4ce0776ca9bab',
}
BOXES = {
 'flow':(35,184,350,156), 'criterion':(440,184,620,156),
 'stock':(35,520,340,170), 'mobile':(720,520,360,170),
 'deposit':(1180,895,360,145),
 'feedback':(35,1150,735,230), 'output':(800,1150,740,230),
}
ROUTES = {
 'criterion_input':[(385,262),(440,262)],
 'destroy':[(375,605),(535,605)],
 'float_share':[(535,605),(720,605)],
 'sink_share':[(535,605),(535,1010),(1180,1010)],
 'stop':[(1080,605),(1530,605),(1530,895)],
 'refloat':[(1180,930),(1050,930),(1050,690)],
 'damage':[(180,690),(180,1150)],
 'feedback':[(35,1260),(16,1260),(16,262),(35,262)],
}
T={
 'ja':{
  'title':'家屋破壊・瓦礫  |  3つの台帳と、空隙率への帰還',
  'sub':'fn_bldgdebris / &list_bldgdebris  •  家屋・瓦礫をセルごとの材積で扱う。個別の家屋応答や瓦礫の軌跡は解かない。',
  'a':'(a) 判定量 X と破壊レート',
  'flow':'流れから読む量',
  'flowbody':'H = h + max(hs, 0)\nV = セル流速\n流動流木 hd・流動瓦礫 hbd',
  'criterion':'f_bdcrit で判定量 X を選ぶ',
  'criterionbody':'1: 浸水深 X = H\n2: 荷重 X = [h + (1+s)max(hs,0)\n                  + sg木·hd + bd_sg·hbd] V²',
  'ramp':'2閾値の場合: レート倍率 a(X)',
  'rate':'① 破壊量 w = min(wbs, bd_wdes × a(X) × Δt)',
  'ratenote':'第1閾値以下は a = 0。第2閾値以上は a = 1。第1閾値のみを指定した場合は、超過時に a = 1。',
  'b':'(b) 材積の移送（実線）と、破壊率・空隙率の帰還（緑破線）',
  'stock':'家屋ストック wbs',
  'stockbody':'不動 / bd_stock0 または fn_bdstock\n幾何面積当たりの材積\n材積 = A × wbs',
  'mobile':'流動瓦礫 hbd',
  'mobilebody':'水・混合体の流れで移流\n実効面積当たりの材積\n材積 = A × f × hbd',
  'deposit':'堆積瓦礫 wbd',
  'depositbody':'不動 / 再流動は任意\n材積 = A × f × wbd',
  'destroy':'① 破壊', 'float':'浮遊分',
  'floatrate':'(1 − bd_fsink) w',
  'stop':'② 停止・堆積',
  'stopbody':'h ≤ dd: 流動分を全量堆積\nそれ以外は H < hf または V < bd_vstop\nレート bd_wstop（残る hbd まで）',
  'refloat':'③ 再流動（既定: 無効）',
  'refloatbody':'H > bd_rfloat × hf\nかつ V > bd_vfloat\nbd_wfloat > 0 で有効\nレート bd_wfloat（残る wbd まで）',
  'sink':'沈下分 bd_fsink × w をその場で堆積へ',
  'damage':'破壊率 d = 1 − wbs / wbs0\n初期ストック wbs0 > 0 のセル\nストックなしでは出力 d = 0',
  'feedback':'空隙率への帰還  |  f_bdgv = 1（既定）',
  'feedbackbody':'gv = gv0 + (1 − gv0) × fw × d\nfw は fn_bdfrac（省略時1）。ランプ倍率 a とは別。\n空隙面積基底の h・hbd・wbd 等を再スケールし、\n体積を保存。水深・水位が下がり、流れへ返る。\nf_bdgv = 0 はこの帰還を止める。',
  'output':'出力と材積収支',
  'outputbody':'Bf = hbd / Bd = wbd / Bs = d\nBd9999 = セルごとの期間最大 maxₜ(hbd + wbd)\n累積通過量ではなく、その時点の材積の最大値。\n材積 Q = Σ A [wbs + f (hbd + wbd)]\n閉領域・ダム捕捉なしなら Q を保存。',
  'basis':'A = dx × dy、f = gv × wfrac（河道幅を指定しない場合は wfrac = 1）。破壊量 w を hbd・wbd へ渡す際は f で割る。',
  'draft':'hf は bd_dlog・bd_sg による円柱の浮力平衡から求める喫水。乾燥判定の h と、停止・再流動の H を区別する。',
  'order':'局所処理: 荷重評価 → ①破壊・帰還 → ②停止 → ③再流動 → ダム捕捉 → 最大値更新。',
  'footer':'ランプ図は既存の軸・ラベル・曲線を保持。沈下・堆積材積を地盤 z に加えず、瓦礫による空隙の再閉塞も扱わない。',
 },
 'en':{
  'title':'Building destruction and debris  |  Three ledgers and porosity feedback',
  'sub':'fn_bldgdebris / &list_bldgdebris  •  Cell-based volumes; individual house responses and debris trajectories are not resolved.',
  'a':'(a) Criterion X and the destruction rate',
  'flow':'Read from the flow',
  'flowbody':'H = h + max(hs, 0)\nV = cell speed\nFloating wood hd and debris hbd',
  'criterion':'Select criterion X with f_bdcrit',
  'criterionbody':'1: depth X = H\n2: load X = [h + (1+s)max(hs,0)\n                 + sg_log·hd + bd_sg·hbd] V²',
  'ramp':'Two thresholds: rate multiplier a(X)',
  'rate':'① Destroyed amount w = min(wbs, bd_wdes × a(X) × Δt)',
  'ratenote':'a = 0 at / below threshold 1; a = 1 at / above threshold 2. With only threshold 1 specified, a = 1 when exceeded.',
  'b':'(b) Volume transfers (solid) and damage / porosity feedback (dashed green)',
  'stock':'Building stock wbs',
  'stockbody':'Immobile / bd_stock0 or fn_bdstock\nVolume per geometric cell area\nVolume = A × wbs',
  'mobile':'Floating debris hbd',
  'mobilebody':'Advected with water / mixture\nVolume per effective area\nVolume = A × f × hbd',
  'deposit':'Deposited debris wbd',
  'depositbody':'Immobile / optional refloat\nVolume = A × f × wbd',
  'destroy':'① Destroy', 'float':'Floating share',
  'floatrate':'(1 − bd_fsink) w',
  'stop':'② Stop / deposit',
  'stopbody':'h ≤ dd: deposit all floating debris\nOtherwise: H < hf or V < bd_vstop\nRate bd_wstop, up to available hbd',
  'refloat':'③ Refloat (default: off)',
  'refloatbody':'H > bd_rfloat × hf\nand V > bd_vfloat\nEnabled when bd_wfloat > 0\nRate bd_wfloat, up to available wbd',
  'sink':'Deposit the sinking share bd_fsink × w locally',
  'damage':'Damage d = 1 − wbs / wbs0\nFor cells with initial stock wbs0 > 0\nOutput d = 0 where there is no stock',
  'feedback':'Porosity feedback  |  f_bdgv = 1 (default)',
  'feedbackbody':'gv = gv0 + (1 − gv0) × fw × d\nfw is fn_bdfrac (default 1), distinct from ramp factor a.\nRescale effective-area columns h, hbd, wbd, etc. to\nconserve volume. Depth and water level drop, feeding\nback to the flow. f_bdgv = 0 disables this feedback.',
  'output':'Outputs and volume accounting',
  'outputbody':'Bf = hbd / Bd = wbd / Bs = d\nBd9999 = per-cell period maximum maxₜ(hbd + wbd)\nPeak instantaneous amount, not cumulative passage.\nVolume Q = Σ A [wbs + f (hbd + wbd)]\nQ is conserved in a closed domain without dam capture.',
  'basis':'A = dx × dy, f = gv × wfrac (wfrac = 1 without channel widths). Divide destroyed amount w by f when adding it to hbd / wbd.',
  'draft':'Draft hf uses cylindrical buoyancy balance with bd_dlog and bd_sg. Distinguish dry-cell depth h from H used for stopping / refloat.',
  'order':'Local order: evaluate load → ① destruction / feedback → ② stop → ③ refloat → dam capture → update maxima.',
  'footer':'The ramp retains its original axes, labels and curve. Deposited debris is not added to bed z and does not re-close the void space.',
 },
}


def rect(ax,key,fill,edge=RULE):
    p=Rectangle(BOXES[key][:2],*BOXES[key][2:],fc=fill,ec=edge,lw=.8,zorder=1)
    ax.add_patch(p);p.set_gid('box_'+key);return p


def build(lang):
    t=T[lang]
    fig=plt.figure(figsize=(CANVAS[0]/DPI,CANVAS[1]/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,CANVAS[0]),ylim=(CANVAS[1],0));ax.axis('off')
    text(ax,35,30,t['title'],size=13,weight='bold')
    text(ax,35,77,t['sub'],size=8.5,color=MUTED)
    text(ax,35,126,t['a'],size=10,weight='bold')
    for key,fill,color in [('flow','#e8f1f7',BLUE),('criterion','#faf0da',ORANGE),
                           ('stock','#f3f0e9',BROWN),('mobile','#e8f1f7',BLUE),
                           ('deposit','#f3f0e9',BROWN),('feedback','#eef3e9',GREEN),
                           ('output','#fafaf7',INK)]:
        rect(ax,key,fill)
        x,y,w,h=BOXES[key]
        text(ax,x+18,y+15,t[key],size=9.7,weight='bold',color=color)
        block(ax,x+18,y+55,t[key+'body'],w-36,size=8.4)
    text(ax,1110,156,t['ramp'],size=8.5,color=ORANGE)
    text(ax,35,376,t['rate'],size=10,color=ORANGE,weight='bold')
    text(ax,35,417,t['ratenote'],size=8.5,color=MUTED)
    text(ax,35,465,t['b'],size=10,weight='bold')
    for key,points in ROUTES.items():
        feedback=key in ('damage','feedback')
        color=GREEN if feedback or key=='refloat' else BLUE if key=='criterion_input' else ORANGE
        a=arrow(ax,points,color,lw=1.5,size=10,ls='--' if feedback else '-')
        a.set_gid(key)
    p=Circle((535,605),4,fc=ORANGE,ec='none',zorder=11);ax.add_patch(p);p.set_gid('split')
    text(ax,450,557,t['destroy'],size=8.4,color=ORANGE,ha='center')
    text(ax,625,530,t['float'],size=8.3,color=ORANGE,ha='center')
    text(ax,625,564,t['floatrate'],size=7.8,color=ORANGE,ha='center')
    text(ax,1115,659,t['stop'],size=9.4,color=ORANGE,weight='bold')
    block(ax,1115,704,t['stopbody'],380,size=8.4,color=ORANGE)
    text(ax,715,759,t['refloat'],size=9.1,color=GREEN,weight='bold')
    block(ax,715,802,t['refloatbody'],315,size=8.2,color=GREEN)
    text(ax,565,1062,t['sink'],size=8.6,color=ORANGE)
    text(ax,207,771,t['damage'],size=8.2,color=GREEN)
    for yy,key in [(1422,'basis'),(1460,'draft'),(1498,'order'),(1540,'footer')]:
        text(ax,35,yy,t[key],size=8.0,color=MUTED)
    return fig


def ramp_asset(lang):
    suffix='' if lang=='ja' else '_en'
    p=Path(__file__).resolve().parents[1]/f'bldgdebris_ramp_preserved{suffix}.png'
    data=p.read_bytes()
    if hashlib.sha256(data).hexdigest()!=RAMP_SHA[lang]:raise ValueError('Protected ramp asset changed')
    return data


def draw(lang):
    if lang not in T:raise ValueError('lang must be ja or en')
    data=ramp_asset(lang)
    out=Path(__file__).resolve().parents[1]/('bldgdebris_chain'+('' if lang=='ja' else '_en')+'.png')
    with drawing_style():
        fig=build(lang)
        try:
            png,svg=BytesIO(),StringIO()
            fig.savefig(png,format='png',dpi=DPI)
            fig.savefig(svg,format='svg',metadata={'Date':None,'Description':
                'Building-debris ledgers, criterion multipliers, transfer conditions and geometric/effective volume bases. The original ramp is a losslessly embedded raster; the schematic is vector artwork.'})
        finally:plt.close(fig)
    with Image.open(BytesIO(png.getvalue())) as im:combined=im.convert('RGBA')
    with Image.open(BytesIO(data)) as ramp:
        if ramp.size!=RAMP_SIZE:raise ValueError('Unexpected ramp size')
        combined.paste(ramp,RAMP_AT) # exact pixels; no resampling or blending
    combined.save(out,dpi=(DPI,DPI))
    scale=72/DPI
    embed=(f'<image id="preserved-ramp" x="{RAMP_AT[0]*scale:g}" y="{RAMP_AT[1]*scale:g}" '
           f'width="{RAMP_SIZE[0]*scale:g}" height="{RAMP_SIZE[1]*scale:g}" '
           'preserveAspectRatio="none" xlink:href="data:image/png;base64,'+base64.b64encode(data).decode('ascii')+'"/>\n')
    xml=svg.getvalue().replace('</svg>',embed+'</svg>')
    out.with_suffix('.svg').write_text('\n'.join(s.rstrip() for s in xml.splitlines())+'\n',encoding='utf-8',newline='\n')
    return str(out)
