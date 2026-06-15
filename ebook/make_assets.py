# -*- coding: utf-8 -*-
"""
라인 일러스트(아이콘) + 장식 요소를 SVG로 정의하고 PNG로 렌더한다.
산출: ebook/build/img/<name>_<color>.png  (투명 배경, 2x 해상도)
"""
import pathlib, cairosvg

ROOT=pathlib.Path(__file__).resolve().parent
IMG=ROOT/"build"/"img"; IMG.mkdir(parents=True, exist_ok=True)
NAVY="#163B4E"; ACCENT="#C0894B"; CREAM="#F6F1E7"; FONT="Noto Sans CJK KR"

# 각 아이콘: viewBox 0 0 64 64 내부 마크업. stroke는 {C}로 치환.
ICONS = {
 "chat_q": '<rect x="9" y="11" width="46" height="32" rx="8"/><path d="M19 43v9l10-9"/>'
           '<path d="M26 23a6 6 0 1 1 8 9c-2 1.4-2 2.8-2 4.2"/><circle cx="32" cy="40" r="1.8" fill="{C}" stroke="none"/>',
 "chat_x": '<rect x="9" y="11" width="46" height="32" rx="8"/><path d="M19 43v9l10-9"/>'
           '<path d="M26 21l12 12M38 21L26 33"/>',
 "chat_check": '<rect x="9" y="11" width="46" height="32" rx="8"/><path d="M19 43v9l10-9"/>'
           '<path d="M24 27l5 6 10-11"/>',
 "scale": '<path d="M32 10v40"/><path d="M16 50h32"/><path d="M12 20h40"/><circle cx="32" cy="14" r="3"/>'
          '<path d="M12 20l-7 14h14zM5 34a7 7 0 0 0 14 0"/><path d="M52 20l-7 14h14zM45 34a7 7 0 0 0 14 0"/>',
 "heart": '<path d="M32 50C12 36 14 18 26 18c4 0 6 3 6 3s2-3 6-3c12 0 14 18-6 32z"/>'
          '<path d="M20 34h7l3-6 4 12 3-6h7" stroke-width="2.4"/>',
 "seed": '<path d="M32 52V30"/><path d="M32 34c-10 0-14-6-14-14 9 0 14 5 14 14z"/>'
         '<path d="M32 30c8 0 12-5 12-12-8 0-12 4-12 12z"/><path d="M22 52h20"/>',
 "gear": '<circle cx="30" cy="30" r="9"/><path d="M30 14v-5M30 51v-5M14 30H9M51 30h-5M19 19l-3-3M44 44l-3-3M41 19l3-3M19 41l-3 3"/>'
         '<path d="M44 46l8 8M50 50l4-1-1 4" stroke-width="2.6"/>',
 "cycle": '<path d="M16 24a18 18 0 0 1 30-6"/><path d="M46 10v9h-9"/>'
          '<path d="M48 40a18 18 0 0 1-30 6"/><path d="M18 54v-9h9"/>',
 "table": '<rect x="12" y="30" width="40" height="6" rx="2"/><path d="M18 36v12M46 36v12"/>'
          '<circle cx="22" cy="22" r="5"/><circle cx="42" cy="22" r="5"/>',
 "sunrise": '<path d="M8 46h48"/><path d="M18 46a14 14 0 0 1 28 0"/><path d="M32 16v8M14 28l4 4M50 28l-4 4M6 40h6M52 40h6"/>',
 "notebook": '<rect x="14" y="10" width="30" height="44" rx="3"/><path d="M14 20h30M22 28h16M22 36h16M22 44h10"/>'
             '<path d="M44 14l8 4-14 28-9 3 3-9z" stroke-width="2.6"/>',
 "coins": '<ellipse cx="30" cy="18" rx="14" ry="6"/><path d="M16 18v10c0 3.3 6.3 6 14 6s14-2.7 14-6V18"/>'
          '<path d="M16 28v10c0 3.3 6.3 6 14 6s14-2.7 14-6V28"/>',
 "hourglass": '<path d="M18 10h28M18 54h28"/><path d="M20 10c0 12 24 14 24 22s-24 10-24 22"/>'
              '<path d="M44 10c0 12-24 14-24 22s24 10 24 22"/>',
 "compass": '<circle cx="32" cy="32" r="22"/><path d="M32 32l10-14-14 10z" fill="{C}" stroke="none"/>'
            '<path d="M32 32l-6 10 10-6" /><circle cx="32" cy="32" r="2.4" fill="{C}" stroke="none"/>',
 "surge": '<path d="M10 46h44"/><path d="M14 40l10-12 8 6 14-18"/><path d="M38 16h10v10"/>'
          '<path d="M16 46v-4M26 46v-8M36 46v-6M46 46v-12" stroke-width="2.4"/>',
 "umbrella": '<path d="M32 12v6M32 46v6a5 5 0 0 1-10 0"/><path d="M10 30a22 16 0 0 1 44 0z"/>'
             '<path d="M10 30c6-6 12 6 22 0 10 6 16-6 22 0" stroke-width="2.2"/>',
 "docmag": '<path d="M16 10h22l10 10v18H16z"/><path d="M38 10v10h10"/><path d="M22 26h14M22 32h10"/>'
           '<circle cx="40" cy="44" r="8"/><path d="M46 50l8 8" stroke-width="3"/>',
 "clipboard": '<rect x="16" y="12" width="32" height="42" rx="4"/><rect x="25" y="8" width="14" height="8" rx="2"/>'
              '<path d="M23 26l4 4 6-7M23 38l4 4 6-7" stroke-width="2.6"/><path d="M38 28h6M38 40h6" stroke-width="2.4"/>',
 "flag": '<path d="M18 54V12"/><path d="M18 14h26l-6 8 6 8H18" stroke-linejoin="round"/>',
 "moon": '<path d="M40 12a20 20 0 1 0 12 36A16 16 0 0 1 40 12z"/><path d="M30 24l1.5 4 4 1.5-4 1.5L30 35l-1.5-4-4-1.5 4-1.5z" fill="{C}" stroke="none"/>',
}

def render(name, inner, color, px):
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{px}" height="{px}">'
         f'<g fill="none" stroke="{color}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">'
         f'{inner.replace("{C}",color)}</g></svg>')
    out=IMG/f"{name}.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out), output_width=px, output_height=px)
    return out

def ornament():
    # 장식 구분선: 가운데 다이아몬드 + 양옆 가는 선 (골드)
    w,h=360,24; c=ACCENT
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
         f'<g stroke="{c}" stroke-width="1.4" fill="{c}">'
         f'<line x1="40" y1="12" x2="150" y2="12" stroke-linecap="round"/>'
         f'<line x1="210" y1="12" x2="320" y2="12" stroke-linecap="round"/>'
         f'<path d="M180 4l6 8-6 8-6-8z"/>'
         f'<circle cx="160" cy="12" r="2.2" stroke="none"/><circle cx="200" cy="12" r="2.2" stroke="none"/>'
         f'</g></svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(IMG/"ornament.png"), output_width=w*3, output_height=h*3)

def hero(name, inner):
    # 장 도입부용 일러스트: 크림 원 + 가는 골드 링 + 네이비 라인 아이콘
    px=600
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{px}" height="{px}">'
         f'<circle cx="32" cy="32" r="30" fill="{CREAM}"/>'
         f'<circle cx="32" cy="32" r="29" fill="none" stroke="{ACCENT}" stroke-width="0.8" opacity="0.75"/>'
         f'<g fill="none" stroke="{NAVY}" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round" '
         f'transform="translate(9.6 9.6) scale(0.7)">{inner.replace("{C}",NAVY)}</g></svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(IMG/f"hero_{name}.png"), output_width=px, output_height=px)

def part_badge(name, inner):
    # 부 표제지용 큰 아이콘: 크림 원 배경 + 네이비 라인 아이콘
    px=520
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{px}" height="{px}">'
         f'<circle cx="32" cy="32" r="30" fill="{CREAM}"/>'
         f'<g fill="none" stroke="{NAVY}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" '
         f'transform="translate(9.6 9.6) scale(0.7)">{inner.replace("{C}",NAVY)}</g></svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(IMG/f"part_{name}.png"), output_width=px, output_height=px)

def cover_from_image(src):
    from PIL import Image, ImageDraw, ImageFont
    Wc,Hc=1240,1835
    base=Image.open(str(src)).convert("RGB")
    s=max(Wc/base.width, Hc/base.height)
    base=base.resize((round(base.width*s), round(base.height*s)), Image.LANCZOS)
    lft=(base.width-Wc)//2; top=(base.height-Hc)//2
    img=base.crop((lft,top,lft+Wc,top+Hc)).convert("RGBA")
    # 가독성용 어둠막(상단 제목 / 하단 저자)
    ov=Image.new("RGBA",(Wc,Hc),(0,0,0,0)); od=ImageDraw.Draw(ov)
    for y in range(Hc):
        a=0
        if y<640: a=max(a,int(165*(1-y/640)))
        if y>1380: a=max(a,int(170*((y-1380)/(Hc-1380))))
        if a: od.line([(0,y),(Wc,y)],fill=(8,9,12,a))
    img=Image.alpha_composite(img,ov)
    d=ImageDraw.Draw(img)
    fp="/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    def F(sz): return ImageFont.truetype(fp,sz)
    def tracked(x,y,text,font,fill,tr):
        for ch in text:
            d.text((x,y),ch,font=font,fill=fill); x+=d.textlength(ch,font=font)+tr
    GOLD=(196,154,86); WHITE=(255,255,255); LIGHT=(228,236,239); SUB=(196,210,216)
    tracked(102,150,"AI · INVESTING · SYSTEM",F(29),GOLD,8)
    d.text((98,205),"나는 AI에게",font=F(94),fill=WHITE)
    d.text((98,322),"종목을 묻지 않았다",font=F(94),fill=WHITE)
    d.rectangle([102,478,252,485],fill=GOLD)
    d.text((102,522),"7천만 원 계좌에서 시작된 질문,",font=F(40),fill=LIGHT)
    d.text((102,578),"AI 투자 시스템의 시작",font=F(41),fill=LIGHT)
    d.text((102,1688),"호차차 지음",font=F(42),fill=(223,231,235))
    d.text((102,1740),"개인투자자를 위한 AI 활용 실전 기록",font=F(29),fill=SUB)
    img.convert("RGB").save(str(IMG/"cover.png"))

def cover_image():
    # 사용자 업로드 이미지가 있으면 그 위에 타이포 합성, 없으면 SVG 표지
    src=ROOT/"assets"/"cover_source.png"
    if src.exists():
        cover_from_image(src); return
    # 신국판 비율 152:225 → 1240x1835
    Wc,Hc=1240,1835
    UP="#C0894B"; DOWN="#3C5663"; WUP="#D2A263"; WDN="#5C7682"
    # --- 차트 영역(캔들 + 추세 + AI 신경망) ---
    # 캔들: (cx, body_top, body_bot, wick_top, wick_bot, up)
    candles=[(205,1180,1238,1158,1252,0),(312,1116,1186,1096,1206,1),
             (419,1132,1182,1112,1202,0),(526,1052,1140,1032,1162,1),
             (633,1010,1066,990,1088,1),(740,1036,1092,1016,1112,0),
             (847,948,1030,928,1052,1),(954,884,962,864,982,1)]
    cw=48
    chart=[]
    # 은은한 격자
    for gx in range(170,1090,118):
        chart.append(f'<line x1="{gx}" y1="900" x2="{gx}" y2="1270" stroke="#FFFFFF" stroke-opacity="0.045" stroke-width="1"/>')
    for gy in range(910,1271,90):
        chart.append(f'<line x1="150" y1="{gy}" x2="1085" y2="{gy}" stroke="#FFFFFF" stroke-opacity="0.045" stroke-width="1"/>')
    # 바닥축
    chart.append('<line x1="150" y1="1272" x2="1085" y2="1272" stroke="#6E8794" stroke-width="2" stroke-opacity="0.6"/>')
    # 캔들
    for cx,bt,bb,wt,wb,up in candles:
        fill=UP if up else DOWN; wick=WUP if up else WDN
        chart.append(f'<line x1="{cx}" y1="{wt}" x2="{cx}" y2="{wb}" stroke="{wick}" stroke-width="4"/>')
        chart.append(f'<rect x="{cx-cw//2}" y="{bt}" width="{cw}" height="{bb-bt}" rx="4" fill="{fill}"/>')
    # 추세선 + 화살표
    chart.append('<polyline points="150,1215 450,1120 700,1015 905,915 1018,840" fill="none" stroke="#FFFFFF" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>')
    chart.append(f'<path d="M1018 840 l-40 6 18 28 z" fill="{ACCENT}"/>')
    # AI 신경망 (상단 오버레이) — 노드 + 엣지 + 'AI' 칩
    nodes=[(470,792),(610,820),(762,770),(905,802),(1006,752)]
    edges=[((340,775),(470,792)),((470,792),(610,820)),((610,820),(762,770)),
           ((762,770),(905,802)),((905,802),(1006,752)),((610,820),(905,802)),
           ((905,802),(950,890)),((762,770),(842,946))]  # 마지막 2개: 차트로 연결
    for (x1,y1),(x2,y2) in edges:
        chart.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{ACCENT}" stroke-opacity="0.45" stroke-width="2"/>')
    for nx,ny in nodes:
        chart.append(f'<circle cx="{nx}" cy="{ny}" r="11" fill="#0E2A38" stroke="{ACCENT}" stroke-width="3"/>'
                     f'<circle cx="{nx}" cy="{ny}" r="3.2" fill="{ACCENT}"/>')
    # AI 칩
    chart.append(f'<rect x="232" y="748" width="108" height="56" rx="28" fill="{ACCENT}" fill-opacity="0.14" stroke="{ACCENT}" stroke-width="3"/>'
                 f'<text x="286" y="787" font-family="{FONT}" font-size="34" font-weight="800" fill="{ACCENT}" text-anchor="middle">AI</text>')
    chart_svg="\n".join(chart)

    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hc}" viewBox="0 0 {Wc} {Hc}">
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="0.4" y2="1">
   <stop offset="0" stop-color="#102B39"/><stop offset="0.55" stop-color="#163B4E"/><stop offset="1" stop-color="#23596F"/>
 </linearGradient>
 <radialGradient id="glow" cx="0.85" cy="0.12" r="0.55">
   <stop offset="0" stop-color="#C0894B" stop-opacity="0.38"/><stop offset="1" stop-color="#C0894B" stop-opacity="0"/>
 </radialGradient>
</defs>
<rect width="{Wc}" height="{Hc}" fill="url(#bg)"/>
<rect width="{Wc}" height="{Hc}" fill="url(#glow)"/>
<text x="100" y="240" font-family="{FONT}" font-size="30" letter-spacing="10" fill="{ACCENT}" font-weight="700">AI · INVESTING · SYSTEM</text>
<text x="96" y="350" font-family="{FONT}" font-size="86" font-weight="800" fill="#FFFFFF">나는 AI에게</text>
<text x="96" y="452" font-family="{FONT}" font-size="86" font-weight="800" fill="#FFFFFF">종목을 묻지 않았다</text>
<rect x="100" y="510" width="150" height="6" fill="{ACCENT}"/>
<text x="100" y="586" font-family="{FONT}" font-size="38" font-weight="700" fill="#E4ECEF">7천만 원 계좌에서 시작된 질문,</text>
<text x="100" y="642" font-family="{FONT}" font-size="40" font-weight="700" fill="#E4ECEF">AI 투자 시스템의 시작</text>
{chart_svg}
<text x="100" y="1695" font-family="{FONT}" font-size="40" font-weight="700" fill="#D7E1E5">호차차 지음</text>
<text x="100" y="1742" font-family="{FONT}" font-size="30" fill="#BBC9CF">개인투자자를 위한 AI 활용 실전 기록</text>
</svg>'''
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(IMG/"cover.png"), output_width=Wc, output_height=Hc)

def cover_book2():
    # 사용자 표지 이미지가 있으면 비율 보정(잘림 없이 위/아래 가장자리색으로 패딩) 후 사용
    src=ROOT/"assets"/"book2_cover_source.png"
    if src.exists():
        from PIL import Image
        Wc,Hc=1240,1835
        im=Image.open(str(src)).convert("RGB")
        w=Wc; h=round(im.height*Wc/im.width)
        im=im.resize((w,h), Image.LANCZOS)
        canvas=Image.new("RGB",(Wc,Hc))
        if h>=Hc:                      # 더 길면 중앙 크롭
            top=(h-Hc)//2; canvas.paste(im.crop((0,top,Wc,top+Hc)),(0,0))
        else:                          # 더 짧으면 위/아래 가장자리색으로 패딩
            y=(Hc-h)//2
            topc=im.crop((0,0,Wc,1)).resize((1,1)).getpixel((0,0))
            botc=im.crop((0,h-1,Wc,h)).resize((1,1)).getpixel((0,0))
            canvas.paste(Image.new("RGB",(Wc,y),topc),(0,0))
            canvas.paste(Image.new("RGB",(Wc,Hc-y-h),botc),(0,y+h))
            canvas.paste(im,(0,y))
        canvas.save(str(IMG/"book2_cover.png"))
        return
    # (이하 폴백 SVG 표지)
    Wc,Hc=1240,1835; G=ACCENT
    el=[]
    # 중앙 모티프: 뉴스 카드 + 돋보기 + AI 신경망
    el.append('<g transform="translate(250,820)">')
    el.append(f'<rect x="0" y="0" width="520" height="430" rx="22" fill="#FFFFFF" fill-opacity="0.05" stroke="{G}" stroke-width="3"/>')
    # 뉴스 헤드라인/본문 줄
    el.append(f'<rect x="48" y="56" width="300" height="22" rx="6" fill="{G}" opacity="0.9"/>')
    for i,(w) in enumerate([420,420,300,420,360]):
        el.append(f'<rect x="48" y="{120+i*46}" width="{w}" height="12" rx="6" fill="#9FB4BC" opacity="0.55"/>')
    # 돋보기
    el.append(f'<circle cx="360" cy="300" r="92" fill="#102B39" fill-opacity="0.5" stroke="{G}" stroke-width="6"/>')
    el.append(f'<line x1="426" y1="366" x2="500" y2="440" stroke="{G}" stroke-width="14" stroke-linecap="round"/>')
    # 돋보기 안 상승선
    el.append('<polyline points="312,330 340,300 366,312 396,270" fill="none" stroke="#FFFFFF" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>')
    el.append('</g>')
    # AI 신경망 (상단 오버레이)
    nodes=[(470,792),(610,820),(762,770),(905,802),(1006,752)]
    edges=[((340,775),(470,792)),((470,792),(610,820)),((610,820),(762,770)),
           ((762,770),(905,802)),((905,802),(1006,752)),((610,820),(905,802))]
    for (x1,y1),(x2,y2) in edges:
        el.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{G}" stroke-opacity="0.45" stroke-width="2"/>')
    for nx,ny in nodes:
        el.append(f'<circle cx="{nx}" cy="{ny}" r="11" fill="#0E2A38" stroke="{G}" stroke-width="3"/><circle cx="{nx}" cy="{ny}" r="3.2" fill="{G}"/>')
    el.append(f'<rect x="232" y="748" width="108" height="56" rx="28" fill="{G}" fill-opacity="0.14" stroke="{G}" stroke-width="3"/>'
              f'<text x="286" y="787" font-family="{FONT}" font-size="34" font-weight="800" fill="{G}" text-anchor="middle">AI</text>')
    motif="\n".join(el)
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hc}" viewBox="0 0 {Wc} {Hc}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="0.4" y2="1">
 <stop offset="0" stop-color="#102B39"/><stop offset="0.55" stop-color="#163B4E"/><stop offset="1" stop-color="#23596F"/></linearGradient>
 <radialGradient id="glow" cx="0.85" cy="0.12" r="0.55"><stop offset="0" stop-color="#C0894B" stop-opacity="0.38"/><stop offset="1" stop-color="#C0894B" stop-opacity="0"/></radialGradient></defs>
<rect width="{Wc}" height="{Hc}" fill="url(#bg)"/><rect width="{Wc}" height="{Hc}" fill="url(#glow)"/>
<text x="100" y="240" font-family="{FONT}" font-size="30" letter-spacing="9" fill="{G}" font-weight="700">AI · ECONOMY · READING</text>
<text x="96" y="350" font-family="{FONT}" font-size="86" font-weight="800" fill="#FFFFFF">질문이 바뀌면</text>
<text x="96" y="452" font-family="{FONT}" font-size="86" font-weight="800" fill="#FFFFFF">경제가 보인다</text>
<rect x="100" y="510" width="150" height="6" fill="{G}"/>
<text x="100" y="586" font-family="{FONT}" font-size="38" font-weight="700" fill="#E4ECEF">막막한 경제 뉴스를,</text>
<text x="100" y="642" font-family="{FONT}" font-size="38" font-weight="700" fill="#E4ECEF">AI와 함께 읽는 법</text>
{motif}
<text x="100" y="1695" font-family="{FONT}" font-size="40" font-weight="700" fill="#D7E1E5">호차차 지음</text>
<text x="100" y="1742" font-family="{FONT}" font-size="29" fill="#BBC9CF">호차차의 AI 읽기 · 두 번째 이야기</text>
</svg>'''
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(IMG/"book2_cover.png"), output_width=Wc, output_height=Hc)

def build():
    cover_image()
    for name,inner in ICONS.items():
        render(name, inner, NAVY, 96)        # 본문 키박스용(네이비)
        hero(name, inner)                    # 장 도입부 일러스트
    ornament()
    for name in ("heart","gear","table","coins","surge","clipboard"):
        part_badge(name, ICONS[name])
    import concept_diagrams; concept_diagrams.build()
    print("[ok] assets →", IMG, "(", len(list(IMG.glob('*.png'))), "files )")

if __name__=="__main__":
    build()
