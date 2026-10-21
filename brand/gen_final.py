import cairosvg
OUT="/home/educator/ai-agency-site/brand"
LATIN="'Noto Sans CJK TC','DejaVu Sans',Arial,sans-serif"

def plus(cx,baseline,fs,color,scale=1.0):
    sw=int(fs*0.13*scale); bh=int(fs*0.13*scale)
    bl=int(fs*0.44*scale); by=int(baseline-fs*0.50)
    st=int(baseline-fs*0.72); sb=int(baseline+fs*0.02)
    return (f'<rect x="{cx-sw//2}" y="{st}" width="{sw}" height="{sb-st}" rx="{sw//3}" fill="{color}"/>'
            f'<rect x="{cx-bl//2}" y="{by}" width="{bl}" height="{bh}" rx="{bh//3}" fill="{color}"/>')

def make(name,coo_c,t_c,ai_c,bg="#fff",tag=None,tag_c=None,x_plus=425,gap=18):
    W,H=980,285; fs=150
    x_coo=60
    x_ai=x_plus+gap+38
    coo=f'<text x="{x_coo}" y="205" font-family="{LATIN}" font-weight="800" font-size="{fs}" fill="{coo_c}">COO</text>'
    p=plus(x_plus,205,fs,t_c,1.05)
    ai=f'<text x="{x_ai}" y="205" font-family="{LATIN}" font-weight="800" font-size="{fs}" fill="{ai_c}">AI</text>'
    tg=f'<text x="{x_coo+2}" y="265" font-family="{LATIN}" font-weight="500" font-size="35" fill="{tag_c or coo_c}" letter-spacing="1">{tag}</text>' if tag else ''
    bgr=f'<rect width="100%" height="100%" fill="{bg}"/>' if bg else ''
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{bgr}{coo}{p}{ai}{tg}</svg>'
    open(f"{OUT}/{name}.svg","w").write(svg)
    cairosvg.svg2png(bytestring=svg.encode(),write_to=f"{OUT}/{name}.png",output_width=W,background_color=bg or "white")
    print("made",name)

make("FINAL_A_navy_orange","#12263F","#FF6B35","#12263F",bg="#FFFFFF",tag="智慧營運 · AI 自動化",tag_c="#5A6B7C")
make("FINAL_B_charcoal_teal","#0F2B2B","#06B6A4","#0F2B2B",bg="#FFFFFF",tag="COO + AI，為您的生意效勞",tag_c="#4A6B68")
make("FINAL_C_two_tone_violet","#1E1B4B","#7C3AED","#7C3AED",bg="#FFFFFF",tag="您的 AI 營運長",tag_c="#6D6A8F")
make("FINAL_D_dark","#FFFFFF","#FF6B35","#FFFFFF",bg="#12263F",tag="智慧營運 · AI 自動化",tag_c="#9FB3C8")
