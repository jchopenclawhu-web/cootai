import cairosvg
OUT="/home/educator/ai-agency-site/brand"
LATIN="'Noto Sans CJK TC','DejaVu Sans',Arial,sans-serif"

def plus(cx,baseline,fs,color,scale=1.0):
    sw=int(fs*0.13*scale); bh=int(fs*0.13*scale)
    bl=int(fs*0.50*scale); by=int(baseline-fs*0.52*scale)
    st=int(baseline-fs*(0.50+0.26*scale))   # taller stem as it scales
    sb=int(baseline+fs*0.03)
    return (f'<rect x="{cx-sw//2}" y="{st}" width="{sw}" height="{sb-st}" rx="{sw//3}" fill="{color}"/>'
            f'<rect x="{cx-bl//2}" y="{by}" width="{bl}" height="{bh}" rx="{bh//3}" fill="{color}"/>')

def make(name,coo_c,t_c,ai_c,tag,tag_c,bg="#FFFFFF",x_plus=445,gap=34,scale=1.32):
    W,H=990,285; fs=150
    x_coo=60
    x_ai=x_plus+gap+36
    coo=f'<text x="{x_coo}" y="205" font-family="{LATIN}" font-weight="800" font-size="{fs}" fill="{coo_c}">COO</text>'
    p=plus(x_plus,205,fs,t_c,scale)
    ai=f'<text x="{x_ai}" y="205" font-family="{LATIN}" font-weight="800" font-size="{fs}" fill="{ai_c}">AI</text>'
    tg=f'<text x="{x_coo+2}" y="265" font-family="{LATIN}" font-weight="500" font-size="35" fill="{tag_c}" letter-spacing="1">{tag}</text>'
    bgr=f'<rect width="100%" height="100%" fill="{bg}"/>' if bg else ''
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{bgr}{coo}{p}{ai}{tg}</svg>'
    open(f"{OUT}/{name}.svg","w").write(svg)
    cairosvg.svg2png(bytestring=svg.encode(),write_to=f"{OUT}/{name}.png",output_width=W,background_color=bg or "white")
    print("made",name)

# C variant with VIOLET plus (as originally), enlarged + more space
make("C2_violet_plus_big","#1E1B4B","#7C3AED","#7C3AED","您的 AI 營運長","#6D6A8F")
# C variant with ORANGE plus (what you described), enlarged + more space
make("C2_orange_plus_big","#1E1B4B","#FF6B35","#7C3AED","您的 AI 營運長","#6D6A8F")
# dark-bg version of orange-plus for completeness later
make("C2_orange_plus_big_dark","#FFFFFF","#FF6B35","#C4B5FD","您的 AI 營運長","#9FB3C8",bg="#1E1B4B")
