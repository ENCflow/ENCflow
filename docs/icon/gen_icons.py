#!/usr/bin/env python3
"""Generate ENCflow icon candidate SVGs."""
import os

OUT = os.path.dirname(os.path.abspath(__file__))
DEEP = "#0E5A8A"   # deep water blue  (grayscale ~30%)
LIGHT = "#66C2E0"  # light water blue (grayscale ~72%)
WHITE = "#FFFFFF"

HDR = '<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">\n'


def write(name, body):
    with open(os.path.join(OUT, name), "w") as f:
        f.write(HDR + body + "</svg>\n")
    print("wrote", name)


# ---------------------------------------------------------------- A: radial
def cand_a():
    b = f'''<defs><clipPath id="c"><circle cx="512" cy="512" r="512"/></clipPath></defs>
<circle cx="512" cy="512" r="512" fill="{DEEP}"/>
<g clip-path="url(#c)">
'''
    # diagonal rays (light blue, narrower) under cardinal rays (white, wider)
    for a in (45, 135, 225, 315):
        b += f'<rect x="692" y="479" width="360" height="66" fill="{LIGHT}" transform="rotate({a} 512 512)"/>\n'
    for a in (0, 90, 180, 270):
        b += f'<rect x="692" y="460" width="360" height="104" fill="{WHITE}" transform="rotate({a} 512 512)"/>\n'
    b += f'</g>\n<rect x="412" y="412" width="200" height="200" fill="{WHITE}"/>\n'
    write("candidate_a_radial8.svg", b)


# ------------------------------------------------- B: cell + 8 neighbours
def cand_b():
    b = f'<rect width="1024" height="1024" rx="180" fill="{DEEP}"/>\n'
    off = 310
    pts = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
    for dx, dy in pts:
        b += (f'<line x1="512" y1="512" x2="{512+dx*off}" y2="{512+dy*off}" '
              f'stroke="{WHITE}" stroke-width="30"/>\n')
    for dx, dy in pts:
        x, y = 512 + dx * off, 512 + dy * off
        b += f'<rect x="{x-65}" y="{y-65}" width="130" height="130" fill="{LIGHT}"/>\n'
    b += '<rect x="407" y="407" width="210" height="210" fill="#FFFFFF"/>\n'
    write("candidate_b_grid8.svg", b)


# ---------------------------------------------------------- ENC letter paths
def enc_group(scale, stroke_scale=1.6, color=WHITE):
    """ENC glyphs in local units: cap height 100, total width ~279.
    stroke_scale: boldness in local units (transform scales it uniformly)."""
    sw = 18 * stroke_scale
    s = scale
    g = f'<g fill="none" stroke="{color}" stroke-width="{sw:.1f}">\n'
    # E (x 0..62)
    for d in ("M9,0 V100", "M0,9 H62", "M0,50 H56", "M0,91 H62"):
        g += f'<path d="{d}"/>\n'
    # N (x 92..158)
    g += '<path d="M101,0 V100"/>\n<path d="M149,100 V0"/>\n'
    g += '<path d="M101,7 L149,93"/>\n'
    # C (x 188..279, circle center 238,50 r41, gap facing right)
    g += '<path d="M264.4,81.4 A41,41 0 1,1 264.4,18.6"/>\n'
    g += "</g>\n"
    # wrap with scale
    return f'<g transform="scale({s})">{g}</g>'


# ------------------------------------------------------ C: ENC monogram+wave
def cand_c():
    b = f'<rect width="1024" height="1024" rx="180" fill="{DEEP}"/>\n'
    s = 2.6
    w = 279 * s
    x0 = (1024 - w) / 2
    y0 = 300
    b += f'<g transform="translate({x0:.0f},{y0})">{enc_group(s)}</g>\n'
    # waves
    b += (f'<path d="M232,750 Q302,672 372,750 T512,750 T652,750 T792,750" '
          f'fill="none" stroke="{LIGHT}" stroke-width="42" stroke-linecap="round"/>\n')
    b += (f'<path d="M332,858 Q402,796 472,858 T612,858 T752,858" '
          f'fill="none" stroke="{LIGHT}" stroke-width="30" stroke-linecap="round" opacity="0.55"/>\n')
    write("candidate_c_encwave.svg", b)


# ----------------------------------------------------- D: layered crosses
def cand_d():
    b = f'''<defs><clipPath id="c"><circle cx="512" cy="512" r="512"/></clipPath></defs>
<circle cx="512" cy="512" r="512" fill="{DEEP}"/>
<g clip-path="url(#c)">
'''
    for a in (45, 135):
        b += f'<rect x="-40" y="437" width="1104" height="150" fill="{LIGHT}" transform="rotate({a} 512 512)"/>\n'
    for a in (0, 90):
        b += f'<rect x="-40" y="437" width="1104" height="150" fill="{WHITE}" transform="rotate({a} 512 512)"/>\n'
    b += "</g>\n"
    write("candidate_d_layers.svg", b)


# ------------------------------------------------- E: compass ticks + ENC
def cand_e():
    b = f'''<defs><clipPath id="c"><circle cx="512" cy="512" r="512"/></clipPath></defs>
<circle cx="512" cy="512" r="512" fill="{DEEP}"/>
<circle cx="512" cy="512" r="402" fill="none" stroke="{LIGHT}" stroke-width="16"/>
<g clip-path="url(#c)">
'''
    for a in (45, 135, 225, 315):
        b += f'<rect x="874" y="493" width="180" height="38" fill="{WHITE}" transform="rotate({a} 512 512)"/>\n'
    for a in (0, 90, 180, 270):
        b += f'<rect x="874" y="483" width="180" height="58" fill="{WHITE}" transform="rotate({a} 512 512)"/>\n'
    b += "</g>\n"
    s = 1.6
    w = 279 * s
    x0 = (1024 - w) / 2
    y0 = 512 - 50 * s
    b += f'<g transform="translate({x0:.0f},{y0:.0f})">{enc_group(s)}</g>\n'
    write("candidate_e_compass.svg", b)


cand_a(); cand_b(); cand_c(); cand_d(); cand_e()
