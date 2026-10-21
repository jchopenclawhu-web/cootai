#!/usr/bin/env python3
"""CooTai LINE assets: profile picture + rich menu."""
import cairosvg, os

OUT = "/home/educator/ai-agency-site/brand"
LATIN = "'Noto Sans CJK TC','DejaVu Sans',Arial,sans-serif"
NAVY = "#12263F"
ORANGE = "#FF6B35"
CREAM = "#F7F5F2"

def plus(cx, cy, size, color, sw_ratio=0.20):
    """Centered plus glyph of overall 'size' px."""
    sw = int(size * sw_ratio)      # stroke width
    L = int(size * 0.52)           # arm half-length from center
    return (
        f'<rect x="{cx-sw//2}" y="{cy-L}" width="{sw}" height="{2*L}" rx="{sw//4}" fill="{color}"/>'
        f'<rect x="{cx-L}" y="{cy-sw//2}" width="{2*L}" height="{sw}" rx="{sw//4}" fill="{color}"/>'
    )

def render(name, svg, w, bg):
    open(f"{OUT}/{name}.svg", "w").write(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/{name}.png",
                     output_width=w, background_color=bg)
    print("made", name)

# ---------- 1. PROFILE PICTURE (LINE wants square, >=640px) ----------
S = 640
# wordmark fit into a square: COO + AI stacked is too wide, so icon-led version
prof = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" viewBox="0 0 {S} {S}">
<rect width="{S}" height="{S}" fill="{NAVY}"/>
{plus(320, 268, 300, ORANGE, 0.18)}
<text x="320" y="500" text-anchor="middle" font-family="{LATIN}" font-weight="800"
      font-size="86" fill="#FFFFFF" letter-spacing="6">COOTAI</text>
<text x="320" y="552" text-anchor="middle" font-family="{LATIN}" font-weight="500"
      font-size="30" fill="#9FB3C8" letter-spacing="8">酷台</text>
</svg>'''
render("line_profile", prof, S, NAVY)

# ---------- 2. RICH MENU (2500x1686 max) ----------
W, H = 2500, 843   # compact single-row menu
btn_w = W // 3
items = [
    ("服務內容", "看我們能做什麼", "服務包含什麼?"),
    ("價格方案", "月費與方案說明", "你們的價格怎麼算"),
    ("預約諮詢", "免費聊聊您的需求", "我想預約諮詢"),
]
parts = [f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
icons = ["◆", "◇", "✚"]
for i, (title, sub, _) in enumerate(items):
    x = i * btn_w
    # divider
    if i:
        parts.append(f'<line x1="{x}" y1="90" x2="{x}" y2="{H-90}" stroke="#D8D2C8" stroke-width="3"/>')
    cx = x + btn_w // 2
    # plus mark as icon
    parts.append(plus(cx, 270, 130, ORANGE, 0.16))
    parts.append(f'<text x="{cx}" y="470" text-anchor="middle" font-family="{LATIN}" '
                 f'font-weight="800" font-size="86" fill="{NAVY}">{title}</text>')
    parts.append(f'<text x="{cx}" y="545" text-anchor="middle" font-family="{LATIN}" '
                 f'font-weight="500" font-size="42" fill="#6B7280">{sub}</text>')

menu = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">' + "".join(parts) + '</svg>')
render("line_richmenu", menu, W, CREAM)
print("\nrich menu size:", W, "x", H, "| button width:", btn_w)
