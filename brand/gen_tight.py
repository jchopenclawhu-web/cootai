import cairosvg, os
OUT="/home/educator/ai-agency-site/brand"
LATIN="'Noto Sans CJK TC','DejaVu Sans',Arial,sans-serif"

def plus(cx,baseline,fs,color,scale=1.0):
    sw=int(fs*0.13*scale); bh=int(fs*0.13*scale)
    bl=int(fs*0.46*scale); by=int(baseline-fs*0.50)
    st=int(baseline-fs*0.74); sb=int(baseline+fs*0.02)
    v=f'<rect x="{cx-sw//2}" y="{st}" width="{sw}" height="{sb-st}" rx="{sw//3}" fill="{color}"/>'
    h=f'<rect x="{cx-bl//2}" y="{by}" width="{bl}" height="{bh}" rx="{bh//3}" fill="{color}"/>'
    return v+h

def make(name,coo_c,t_c,ai_c,bg="#fff",tag=None,tag_c=None, gap=48):
    W,H=1000,290; fs=150
    x_coo=60
    # COO ends ~ x=60+ 3*~96 = 348; place plus right after with small gap
    x_plus=430
    x_ai=x_plus+gap+40
    coo=f'<text x="{x_coo}" y="205" font-family="{LATIN}" font-weight="800" font-size="{fs}" fill="{coo_c}" letter-spacing="0">COO</text>'
    p=plus(x_plus,205,fs,t_c,1.05)
    ai=f'<text x="{x_ai}" y="205" font-family="{LATIN}" font-weight="800" font-size="{fs}" fill="{ai_c}" letter-spacing="0">ai</text>'
    tg=f'<text x="{x_coo+2}" y="268" font-family="{LATIN}" font-weight="500" font-size="36" fill="{tag_c or coo_c}" letter-spacing="1">{tag}</text>' if tag else ''
    bgr=f'<rect width="100%" height="100%" fill="{bg}"/>' if bg else ''
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{bgr}{coo}{p}{ai}{tg}</svg>'
    open(f"{OUT}/{name}.svg","w").write(svg)
    cairosvg.svg2png(bytestring=svg.encode(),write_to=f"{OUT}/{name}.png",output_width=W,background_color=bg or "white")
    print("made",name)

make("cootai_tight_orange","#12263F","#FF6B35","#12263F",bg="#FFFFFF",tag="智慧營運 · AI 自動化",tag_c="#5A6B7C")
make("cootai_tight_teal","#0F2B2B","#06B6A4","#0F2B2B",bg="#FFFFFF",tag="COO + AI，為您的生意效勞",tag_c="#4A6B68")
