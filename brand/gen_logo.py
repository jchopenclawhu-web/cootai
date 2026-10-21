#!/usr/bin/env python3
"""Generate CooTai logo concepts — tighter layout, CJK-safe."""
import cairosvg
import os

OUT = "/home/educator/ai-agency-site/brand"
os.makedirs(OUT, exist_ok=True)
LATIN = "'Noto Sans CJK TC','DejaVu Sans',Arial,sans-serif"

def plus_glyph(cx, baseline, fs, color, scale=1.0):
    stem_w = int(fs*0.135*scale)
    bar_h  = int(fs*0.135*scale)
    bar_len = int(fs*0.52*scale)   # tighter crossbar
    bar_y = int(baseline - fs*0.50)
    stem_top = int(baseline - fs*0.78)
    stem_bot = int(baseline + fs*0.04)
    v = f'<rect x="{cx-stem_w//2}" y="{stem_top}" width="{stem_w}" height="{stem_bot-stem_top}" rx="{stem_w//3}" fill="{color}"/>'
    hb = f'<rect x="{cx-bar_len//2}" y="{bar_y}" width="{bar_len}" height="{bar_h}" rx="{bar_h//3}" fill="{color}"/>'
    return v+hb

def wordmark(name, coo_c, t_c, ai_c, t_scale=1.1, bg="#FFFFFF", tag=None, tag_c=None):
    W,H = 1100, 300
    fs = 160
    # tuned x positions (tight, reads as one word)
    x_coo = 70
    x_plus = 585
    x_ai = 685
    coo = f'<text x="{x_coo}" y="215" font-family="{LATIN}" font-weight="800" font-size="{fs}" fill="{coo_c}" letter-spacing="2">COO</text>'
    plus = plus_glyph(x_plus, 215, fs, t_c, t_scale)
    ai = f'<text x="{x_ai}" y="215" font-family="{LATIN}" font-weight="800" font-size="{fs}" fill="{ai_c}" letter-spacing="2">AI</text>'
    tg = ''
    if tag:
        tg = f'<text x="{x_coo+2}" y="278" font-family="{LATIN}" font-weight="500" font-size="38" fill="{tag_c or coo_c}" letter-spacing="1">{tag}</text>'
    bgrect = f'<rect width="100%" height="100%" fill="{bg}"/>' if bg else ''
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{bgrect}{coo}{plus}{ai}{tg}</svg>'
    open(os.path.join(OUT,name+".svg"),"w").write(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(OUT,name+".png"),
                     output_width=W, background_color=bg or "white")
    print("made",name)

def appicon(name, plus_c, bg, fg):
    """Square app icon: CooTai 'C' + plus mark, or just the plus-t."""
    S=400
    # big plus-t centered, with subtle C ring
    v='<rect x="170" y="90" width="60" height="220" rx="20" fill="%s"/>' % plus_c
    h='<rect x="105" y="170" width="190" height="60" rx="20" fill="%s"/>' % plus_c
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" viewBox="0 0 {S} {S}"><rect width="{S}" height="{S}" rx="84" fill="{bg}"/>{v}{h}</svg>'
    open(os.path.join(OUT,name+".svg"),"w").write(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(OUT,name+".png"), output_width=S, background_color=bg)
    print("made",name)

# Concept 1: navy + orange plus (bold, corporate, high contrast)
wordmark("cootai_concept1_orange", "#12263F", "#FF6B35", "#12263F", 1.1,
         bg="#FFFFFF", tag="智慧營運 · AI 自動化", tag_c="#5A6B7C")

# Concept 2: charcoal + teal plus
wordmark("cootai_concept2_teal", "#0F2B2B", "#06B6A4", "#0F2B2B", 1.1,
         bg="#FFFFFF", tag="COO + AI，為您的生意效勞", tag_c="#4A6B68")

# Concept 3: COO dark / AI purple, purple plus (two-tone)
wordmark("cootai_concept3_violet", "#1E1B4B", "#7C3AED", "#7C3AED", 1.15,
         bg="#FFFFFF", tag="您的 AI 營運長", tag_c="#6D6A8F")

# Concept 4: inverse (dark bg)
wordmark("cootai_concept4_dark", "#FFFFFF", "#FF6B35", "#FFFFFF", 1.1,
         bg="#12263F", tag="智慧營運 · AI 自動化", tag_c="#9FB3C8")

# App icons
appicon("cootai_icon_orange", "#FF6B35", "#12263F", "#FFFFFF")
appicon("cootai_icon_teal",   "#06B6A4", "#0F2B2B", "#FFFFFF")

print("DONE ->", OUT)
