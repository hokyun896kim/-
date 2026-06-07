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

def cover_image():
    # 신국판 비율 152:225 → 1240x1835
    Wc,Hc=1240,1835
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hc}" viewBox="0 0 {Wc} {Hc}">
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="0.4" y2="1">
   <stop offset="0" stop-color="#102B39"/><stop offset="0.55" stop-color="#163B4E"/><stop offset="1" stop-color="#23596F"/>
 </linearGradient>
 <radialGradient id="glow" cx="0.85" cy="0.12" r="0.5">
   <stop offset="0" stop-color="#C0894B" stop-opacity="0.40"/><stop offset="1" stop-color="#C0894B" stop-opacity="0"/>
 </radialGradient>
</defs>
<rect width="{Wc}" height="{Hc}" fill="url(#bg)"/>
<rect width="{Wc}" height="{Hc}" fill="url(#glow)"/>
<text x="100" y="240" font-family="{FONT}" font-size="30" letter-spacing="10" fill="{ACCENT}" font-weight="700">AI · INVESTING · SYSTEM</text>
<text x="96" y="350" font-family="{FONT}" font-size="86" font-weight="800" fill="#FFFFFF">나는 AI에게</text>
<text x="96" y="452" font-family="{FONT}" font-size="86" font-weight="800" fill="#FFFFFF">종목을 묻지 않았다</text>
<rect x="100" y="510" width="150" height="6" fill="{ACCENT}"/>
<text x="100" y="586" font-family="{FONT}" font-size="40" font-weight="700" fill="#E4ECEF">7천만 원에서 2.5억까지,</text>
<text x="100" y="642" font-family="{FONT}" font-size="40" font-weight="700" fill="#E4ECEF">AI 투자 시스템의 시작</text>
<!-- 중앙 모티프: 말풍선 + 상승 차트 -->
<g transform="translate(360,760)">
 <rect x="0" y="0" width="520" height="360" rx="44" fill="#FFFFFF" fill-opacity="0.05" stroke="{ACCENT}" stroke-width="4"/>
 <path d="M70 360 l-8 60 70 -50" fill="none" stroke="{ACCENT}" stroke-width="4" stroke-linejoin="round"/>
 <line x1="70" y1="120" x2="70" y2="280" stroke="#9FB4BC" stroke-width="3"/>
 <line x1="70" y1="280" x2="450" y2="280" stroke="#9FB4BC" stroke-width="3"/>
 <polyline points="95,250 175,225 255,190 335,140 415,95" fill="none" stroke="#FFFFFF" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
 <path d="M415 95 l-30 4 14 22 z" fill="{ACCENT}"/>
 <circle cx="335" cy="140" r="9" fill="{ACCENT}"/>
 <text x="260" y="60" font-family="{FONT}" font-size="120" font-weight="800" fill="{ACCENT}" text-anchor="middle" opacity="0.9">?</text>
</g>
<text x="100" y="1695" font-family="{FONT}" font-size="38" font-weight="700" fill="#D7E1E5">도토리 AI 투자위원회</text>
<text x="100" y="1742" font-family="{FONT}" font-size="30" fill="#BBC9CF">개인투자자를 위한 AI 활용 실전 기록</text>
</svg>'''
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(IMG/"cover.png"), output_width=Wc, output_height=Hc)

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
