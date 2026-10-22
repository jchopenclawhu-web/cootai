#!/usr/bin/env python3
"""1200x630 Open Graph share card for cootai.tw (LINE/FB/Twitter preview)."""
import cairosvg

LATIN = "'Noto Sans CJK TC','DejaVu Sans',Arial,sans-serif"
NAVY, ORANGE, VIOLET = "#12263F", "#FF6B35", "#7C3AED"
CREAM = "#F7F5F2"
W, H = 1200, 630

def plus(cx, cy, size, color, ratio=0.18):
    sw = int(size * ratio); L = int(size * 0.50)
    return (f'<rect x="{cx-sw//2}" y="{cy-L}" width="{sw}" height="{2*L}" rx="{sw//4}" fill="{color}"/>'
            f'<rect x="{cx-L}" y="{cy-sw//2}" width="{2*L}" height="{sw}" rx="{sw//4}" fill="{color}"/>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#12263F"/>
      <stop offset="100%" stop-color="#1B3557"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bg)"/>

  <!-- soft accent glow -->
  <circle cx="1050" cy="80" r="260" fill="#FF6B35" opacity="0.10"/>
  <circle cx="120" cy="600" r="200" fill="#7C3AED" opacity="0.12"/>

  <!-- wordmark -->
  <text x="80" y="210" font-family="{LATIN}" font-weight="800" font-size="112" fill="#FFFFFF">COO</text>
  {plus(400, 175, 132, ORANGE, 0.17)}
  <text x="452" y="210" font-family="{LATIN}" font-weight="800" font-size="112" fill="#A78BFA">AI</text>
  <text x="620" y="210" font-family="{LATIN}" font-weight="800" font-size="112" fill="#FFFFFF" opacity="0.55">酷台</text>

  <!-- headline -->
  <text x="80" y="345" font-family="{LATIN}" font-weight="800" font-size="62" fill="#FFFFFF">你的 AI 營運長</text>
  <text x="80" y="425" font-family="{LATIN}" font-weight="400" font-size="38" fill="#C9D4E3">自動回覆 · 語音聽得懂中文 · 24 小時不休息</text>

  <!-- divider -->
  <rect x="80" y="475" width="140" height="5" rx="2.5" fill="{ORANGE}"/>

  <!-- proof points -->
  <text x="80" y="548" font-family="{LATIN}" font-weight="700" font-size="30" fill="#FFFFFF">診所 · 餐廳 · 補習班 · 貿易 · 會計</text>
  <text x="80" y="592" font-family="{LATIN}" font-weight="400" font-size="26" fill="#8FA3BC">新北市林口區　·　cootai.tw</text>

  <!-- plus badge bottom right -->
  <rect x="980" y="500" width="140" height="140" rx="34" fill="{CREAM}"/>
  {plus(1050, 570, 78, NAVY, 0.20)}
</svg>'''

out = "/home/educator/ai-agency-site/brand/og_card.png"
cairosvg.svg2png(bytestring=svg.encode(), write_to=out, output_width=W, output_height=H)
open("/home/educator/ai-agency-site/brand/og_card.svg", "w").write(svg)
print("wrote", out)
