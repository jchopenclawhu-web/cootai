#!/usr/bin/env python3
"""Website logo assets: favicon, app icon, header wordmark SVG."""
import cairosvg, os

OUT = "/home/educator/ai-agency-site"
BRAND = os.path.join(OUT, "brand")
LATIN = "'Noto Sans CJK TC','DejaVu Sans',Arial,sans-serif"
NAVY = "#12263F"
ORANGE = "#FF6B35"

def plus(cx, cy, size, color, sw_ratio=0.18):
    sw = int(size * sw_ratio); L = int(size * 0.50)
    return (f'<rect x="{cx-sw//2}" y="{cy-L}" width="{sw}" height="{2*L}" rx="{sw//4}" fill="{color}"/>'
            f'<rect x="{cx-L}" y="{cy-sw//2}" width="{2*L}" height="{sw}" rx="{sw//4}" fill="{color}"/>')

def render(path, svg, w, bg):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=path, output_width=w, background_color=bg)
    print("made", path)

# ---------- favicon: square, high contrast, legible at 16px ----------
def favicon(size, name):
    S = size
    # At tiny sizes only the plus survives - that's intentional
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" viewBox="0 0 {S} {S}">'
           f'<rect width="{S}" height="{S}" rx="{int(S*0.22)}" fill="{NAVY}"/>'
           f'{plus(S//2, S//2, int(S*0.62), ORANGE, 0.20)}</svg>')
    render(f"{OUT}/{name}", svg, S, NAVY)

favicon(32,  "favicon-32.png")
favicon(180, "apple-touch-icon.png")
favicon(192, "icon-192.png")
favicon(512, "icon-512.png")

# proper .ico with multiple sizes
try:
    from PIL import Image
    img = Image.open(f"{OUT}/icon-512.png")
    img.save(f"{OUT}/favicon.ico", sizes=[(16,16),(32,32),(48,48),(64,64)])
    print("made favicon.ico")
except Exception as e:
    print("ico skipped:", e)

# ---------- header wordmark (transparent, horizontal) ----------
# COO + plus + AI, tight; plus sits on baseline like a 't'
W, H = 330, 130
fs = 62
x_coo, x_plus, x_ai = 4, 186, 222
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
       f'<text x="{x_coo}" y="86" font-family="{LATIN}" font-weight="800" font-size="{fs}" fill="{NAVY}">COO</text>'
       f'{plus(x_plus, 86-31, 74, ORANGE, 0.17)}'
       f'<text x="{x_ai}" y="86" font-family="{LATIN}" font-weight="800" font-size="{fs}" fill="#7C3AED">AI</text>'
       f'</svg>')
open(f"{BRAND}/logo_header.svg","w").write(svg)
cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{BRAND}/logo_header.png",
                 output_width=W*2, background_color="white")
print("made logo_header.svg/.png")
