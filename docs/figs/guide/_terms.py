"""Drawing helpers local to the advection, nonhydro and diffusion supplements.

No global style changes. Coordinates on explanatory canvases are in pixels,
with y increasing downwards. Plot data remain in the original data units.
"""
from io import StringIO
from pathlib import Path
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, Polygon, FancyArrowPatch
from _schematic import drawing_style, text, block, line, arrow, INK, MUTED, RULE

BLUE, ORANGE, GREEN = '#2a78d6', '#eb6834', '#527d37'
WATER, SOIL, BED = '#cfe0f6', '#e4d9c8', '#8c7b63'
DPI = 150


def canvas(height, width=1800):
    fig=plt.figure(figsize=(width/DPI,height/DPI),dpi=DPI)
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,width),ylim=(height,0));ax.axis('off')
    ax.set_gid('annotation-canvas')
    return fig,ax


def plot_axes(fig, x, y, w, h):
    fw,fh=fig.get_size_inches()*fig.dpi
    ax=fig.add_axes([x/fw,1-(y+h)/fh,w/fw,h/fh])
    ax.spines[['top','right']].set_visible(False)
    ax.tick_params(labelsize=9)
    return ax


def rect(ax,x,y,w,h,fill='white',edge='none',lw=1,gid=None,**kw):
    p=Rectangle((x,y),w,h,fc=fill,ec=edge,lw=lw,gid=gid,**kw);ax.add_patch(p);return p


def grid(ax,x,y,nx,ny,d):
    for i in range(nx+1):line(ax,[(x+i*d,y),(x+i*d,y+ny*d)],RULE,.8,z=2)
    for j in range(ny+1):line(ax,[(x,y+j*d),(x+nx*d,y+j*d)],RULE,.8,z=2)


def dot(ax,p,color=MUTED,gid=None):
    a,=ax.plot(*p,'o',ms=4.5,color=color,zorder=7,gid=gid);return a


def edge(ax,p,color=BLUE,diag=False,gid=None):
    a,=ax.plot(*p,'D' if diag else 's',ms=6,mec=color,mfc='white' if diag else color,
              mew=1.2,zorder=8,gid=gid);return a


def dimension(ax,a,b,label,label_pos):
    p=FancyArrowPatch(a,b,arrowstyle='<->',mutation_scale=9,color=ORANGE,lw=1,shrinkA=0,shrinkB=0)
    ax.add_patch(p);text(ax,*label_pos,label,10,color=ORANGE,ha='center')


def legend_rows(ax,x,y,items,width=760,step=58,size=9):
    """items: (color, linestyle, label). Labels stay outside numerical axes."""
    for i,(color,style,label) in enumerate(items):
        yy=y+i*step
        line(ax,[(x,yy+12),(x+42,yy+12)],color,1.8,ls=style)
        block(ax,x+60,yy,label,width-60,size)


def export(fig,stem,lang):
    dest=Path(__file__).resolve().parents[1]/(stem+('' if lang=='ja' else '_en'))
    fig.savefig(dest.with_suffix('.png'),dpi=DPI)
    svg=StringIO();fig.savefig(svg,format='svg',metadata={'Date':None})
    content='\n'.join(line.rstrip() for line in svg.getvalue().splitlines())+'\n'
    dest.with_suffix('.svg').write_text(content,encoding='utf-8',newline='\n')
    plt.close(fig)
    return str(dest.with_suffix('.png'))
