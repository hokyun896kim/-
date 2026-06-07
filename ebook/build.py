#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전자책 빌드 파이프라인
  원본 docx → (pandoc) raw.md → 정제/디자인 마크업 → HTML → PDF(WeasyPrint) + EPUB(pandoc)

산출물:
  ebook/build/book.html   미리보기용 디자인 HTML
  ebook/build/book.pdf    PDF 전자책
  ebook/build/book.epub   EPUB 전자책
"""
import os, re, subprocess, html, datetime, pathlib

ROOT   = pathlib.Path(__file__).resolve().parent
SRC    = ROOT / "source" / "raw.md"
ASSETS = ROOT / "assets"
BUILD  = ROOT / "build"
BUILD.mkdir(exist_ok=True)

TITLE    = "나는 AI에게 종목을 묻지 않았다"
SUBTITLE = "7천만 원에서 2.5억까지, AI 투자 시스템의 시작"
KEYLINE  = "나는 AI에게 정답을 묻지 않았다.\nAI를 내 투자위원회로 만들기 시작했다."
PROJECT  = "도토리 AI 투자위원회"

PARTS = {
    1: ("1부", "나는 왜 계속 흔들렸는가"),
    2: ("2부", "질문이 바뀌자 투자가 바뀌었다"),
    3: ("3부", "AI를 투자위원회로 만들기 시작하다"),
    4: ("4부", "계좌를 키운 것은 매수 버튼이 아니었다"),
    5: ("5부", "실전에서 가장 먼저 달라진 것들"),
    6: ("6부", "독자가 오늘 바로 써볼 수 있는 질문들"),
}
PART_BEFORE_CH = {1: 1, 4: 2}  # 누락된 1·2부만 삽입 (3~6부는 원본에 존재)

# 수집되는 목차 구조 (PDF 목차 생성용)
TOC = []  # list of ("part"/"chapter"/"prologue"/"appendix", id, label)

# ----------------------------------------------------------------------
# 1. 원본 로드 및 본문 슬라이스
# ----------------------------------------------------------------------
raw = SRC.read_text(encoding="utf-8")
lines = raw.split("\n")

def find_line(prefix):
    for i, l in enumerate(lines):
        if l.startswith(prefix):
            return i
    raise ValueError("not found: " + prefix)

i_prologue = find_line("# 프롤로그")
i_appendix = find_line("# 부록")
i_tail     = find_line("# 2부 및 후속작 보류 목록")

body_md     = "\n".join(lines[i_prologue:i_appendix])
appendix_md = "\n".join(lines[i_appendix:i_tail])

# ----------------------------------------------------------------------
# 2. 본문 정제
# ----------------------------------------------------------------------
# 2-1) 집필 메모 블록인용 제거
body_md = re.sub(r"(?m)^> \*\*집필 메모\*\*[^\n]*\n(?:>[^\n]*\n?)*", "", body_md)
# 2-2) 표준 메모/박스 표(HTML table) 제거 (본문엔 없지만 안전망)
body_md = re.sub(r"(?s)<table>.*?</table>\s*", "", body_md)
# 2-3) 표준 단독 H1 '프롤로그' 제거 (실제 제목은 '## 프롤로그 —')
body_md = re.sub(r"(?m)^# 프롤로그\s*$", "", body_md)

out = []
chapter_components = {}   # 장번호 → 삽입할 raw HTML (장 제목 직후)

# 컴포넌트는 아래에서 정의 후 매핑
def register_components():
    chapter_components[5]  = comp_compare_company_stock()
    chapter_components[8]  = comp_premarket_modes()
    chapter_components[9]  = comp_postmarket_flow()
    chapter_components[13] = comp_surge_types()
    chapter_components[16] = comp_dont_ask()
    chapter_components[17] = comp_do_ask()

body_lines = body_md.split("\n")
processed = []
for idx, line in enumerate(body_lines):
    m_ch = re.match(r"^## (\d+)장\. (.+)$", line)
    m_pr = re.match(r"^## (프롤로그.*)$", line)
    if m_ch:
        n = int(m_ch.group(1)); title = m_ch.group(2).strip()
        # 부(部) 삽입
        if n in PART_BEFORE_CH:
            pno = PART_BEFORE_CH[n]
            ptag, ptitle = PARTS[pno]
            processed.append(f'# {ptag}. {ptitle} {{.part #part{pno}}}')
            processed.append("")
            TOC.append(("part", f"part{pno}", f"{ptag}. {ptitle}"))
        processed.append(f'## {n}장. {title} {{.chapter #ch{n}}}')
        TOC.append(("chapter", f"ch{n}", f"{n}장. {title}"))
        # 장 직후 컴포넌트 자리표시
        processed.append(f"<!--COMP{n}-->")
    elif m_pr:
        processed.append(f'## {m_pr.group(1).strip()} {{.prologue #prologue}}')
        TOC.append(("prologue", "prologue", "프롤로그"))
    elif re.match(r"^## ", line):
        # 장/부록/프롤로그가 아닌 H2 = 닫는 문장형 가짜 제목 → 마무리 인용구
        txt = line[3:].strip()
        processed.append(f'<blockquote class="closer"><p>{html.escape(txt)}</p></blockquote>')
    elif re.match(r"^# (\d)부\.", line):
        # 본문에 이미 있는 3~6부 H1
        m = re.match(r"^# (\d)부\. (.+)$", line)
        pno = int(m.group(1)); ptitle = m.group(2).strip()
        processed.append(f'# {pno}부. {ptitle} {{.part #part{pno}}}')
        TOC.append(("part", f"part{pno}", f"{pno}부. {ptitle}"))
    else:
        processed.append(line)

body_md = "\n".join(processed)

# ----------------------------------------------------------------------
# 3. 본문 삽입 컴포넌트(표/카드/흐름도) 정의
# ----------------------------------------------------------------------
def comp_compare_company_stock():
    rows = [
        ("판단 대상", "사업 그 자체 — 매출·이익·산업·경쟁력", "그 사업에 매겨진 <b>가격</b> — 기대가 반영된 주가"),
        ("좋다는 의미", "실적이 늘고 산업이 성장하는가", "지금 가격이 미래 기대 대비 매력적인가"),
        ("흔한 함정", "좋은 기업이면 언제 사도 된다", "이미 모두가 좋다고 아는 값에 산다"),
        ("핵심 질문", "이 기업은 사업적으로 좋은가?", "이 기대는 이미 주가에 반영됐는가?"),
    ]
    body = "".join(
        f'<tr><th>{r[0]}</th><td class="col-good">{r[1]}</td><td class="col-bad">{r[2]}</td></tr>'
        for r in rows)
    return f'''
<div class="callout"><p class="ctitle">이 장을 한눈에 — 좋은 기업 ≠ 좋은 주식</p>
<p>좋은 기업도 너무 비싸게 사면 나쁜 투자가 됩니다. ‘기업의 가치’와 ‘현재 가격의 매력’을 분리해 보는 것이 이 장의 핵심입니다.</p></div>
<table class="compare">
<thead><tr><th></th><th>좋은 기업</th><th>좋은 주식</th></tr></thead>
<tbody>{body}</tbody></table>
'''

def comp_premarket_modes():
    modes = [("공격","적극 신규·증액"),("정찰","소량 관찰 매수"),("유지","현 비중 유지"),
             ("감량","리스크 축소"),("현금대기","기회 대기")]
    bar = "".join(f'<div class="mode"><b>{m[0]}</b>{m[1]}</div>' for m in modes)
    return f'''
<div class="callout"><p class="ctitle">장전 루틴 — 종목보다 ‘오늘의 태도’를 먼저 정한다</p>
<p>장이 열리기 전, 오늘이 어떤 날인지 다섯 모드 중 하나로 먼저 규정합니다. 태도가 정해지면 장중 충동이 줄어듭니다.</p></div>
<div class="modebar">{bar}</div>
'''

def comp_postmarket_flow():
    steps = [
        ("오늘 시장 한 줄 판단", "오늘은 어떤 성격의 장이었는가"),
        ("강·약 섹터 정리", "어디로 돈이 들어오고 빠졌는가"),
        ("내 계좌 vs 시장", "시장보다 강했나, 약했나"),
        ("판단 vs 감정", "오늘 매매는 기준에 따른 것이었나"),
        ("내일 체크포인트", "내일 가장 먼저 확인할 질문 3개"),
    ]
    body = "".join(
        f'<div class="step"><div class="dot">{i+1}</div>'
        f'<div class="body"><h4>{s[0]}</h4><p>{s[1]}</p></div></div>'
        for i, s in enumerate(steps))
    return f'''
<div class="callout"><p class="ctitle">장마감 루틴 — 수익률이 아니라 ‘판단의 질’을 기록한다</p>
<p>하루의 감정을 기록으로 바꾸는 5단계 흐름입니다. 결과가 아니라 이유를 남기는 것이 다음 계좌를 바꿉니다.</p></div>
<div class="flow">{body}</div>
'''

def comp_surge_types():
    cards = [
        ("뉴스형", "재료·뉴스에 반응한 급등. 재료 소멸 시 되돌림 위험."),
        ("수급형", "특정 주체의 매수세가 만든 급등. 수급 지속성이 관건."),
        ("섹터형", "섹터 전체가 함께 오르는 급등. 흐름의 시작일 수도, 낙폭 반등일 수도."),
        ("실적형", "실적 개선이 뒷받침된 급등. 상대적으로 근거가 단단함."),
        ("과열형", "마지막 불꽃. 기대가 가격에 과도하게 반영된 구간."),
    ]
    body = "".join(
        f'<div class="card"><span class="cidx">{i+1}</span>'
        f'<h4>{c[0]} 급등</h4><p>{c[1]}</p></div>'
        for i, c in enumerate(cards))
    return f'''
<div class="callout"><p class="ctitle">급등주 분류 — “이 급등은 매수 신호인가, 조사 신호인가?”</p>
<p>모든 급등을 똑같이 보지 않습니다. 다섯 유형으로 성격을 먼저 나누면, 추격할지 기다릴지 보낼지가 보입니다.</p></div>
<div class="cardgrid">{body}</div>
'''

def comp_dont_ask():
    items = [
        ("정답 요구", "“이거 살까요?”처럼 결정을 떠넘기는 질문"),
        ("허락 요구", "“들고 가도 되죠?”처럼 안심을 구하는 질문"),
        ("예측 요구", "“내일 오를까요?”처럼 점괘를 바라는 질문"),
        ("단답 유도", "근거 없이 매수/매도 결론만 내게 하는 질문"),
    ]
    body = "".join(f'<li><span class="qnum">✕</span>{t} — <span class="fillline">{d}</span></li>' for t,d in items)
    return f'''
<div class="dont"><span class="lbl">이렇게 묻지 마라</span>
<ul class="checklist" style="margin:0">{body}</ul></div>
'''

def comp_do_ask():
    items = [
        ("조건을 묻기", "“매수하려면 무엇을 확인해야 하나요?”"),
        ("분리해 묻기", "“좋은 기업인지와 지금 좋은 주식인지 나눠줘”"),
        ("반증을 묻기", "“이 판단이 틀렸다고 볼 조건은?”"),
        ("선택지로 묻기", "“추격·눌림대기·관찰·보내기 중 어디인가?”"),
    ]
    body = "".join(f'<li><span class="qnum">✓</span>{t} — <span class="fillline">{d}</span></li>' for t,d in items)
    return f'''
<div class="do"><span class="lbl">이렇게 물어라</span>
<ul class="checklist" style="margin:0">{body}</ul></div>
'''

register_components()
for n, comp in chapter_components.items():
    body_md = body_md.replace(f"<!--COMP{n}-->", comp)
# 남은 자리표시 제거
body_md = re.sub(r"<!--COMP\d+-->", "", body_md)

# ----------------------------------------------------------------------
# 4. 부록 정제/디자인 (A~E)
# ----------------------------------------------------------------------
def render_appendix(md):
    # 메모 표 제거
    md = re.sub(r"(?s)<table>.*?</table>\s*", "", md)
    subs = re.split(r"(?m)^## (부록 [A-E]\. .+)$", md)
    # subs[0] = '' / 그다음 (title, content) 반복
    out_parts = []
    it = iter(subs[1:])
    for title in it:
        content = next(it)
        letter = title.split()[1].rstrip(".")  # 'A.' → 'A'
        anchor = f"apx{letter}"
        TOC.append(("appendix", anchor, title.strip()))
        out_parts.append(f'## {title.strip()} {{.chapter #{anchor}}}')
        out_parts.append(render_appendix_body(content, letter))
    return "\n\n".join(out_parts)

def render_appendix_body(content, letter):
    paras = re.split(r"\n\s*\n", content.strip())
    html_out = []
    qmode = letter in ("A", "D", "E")
    pending_prompt = False  # 부록 A: 질문 다음 문단 = 프롬프트
    fill_labels = ("작성", "기록란", "한 줄 메모", "최종 문장", "오늘의 금지 행동",
                   "오늘의 금지 행동:", "기록란")
    for p in paras:
        p = p.strip()
        if not p:
            continue
        # 카테고리 (n) cat
        mcat = re.match(r"^\*\*\((\d)\)\s*(.+?)\*\*$", p)
        if mcat:
            html_out.append(f'<p class="apx-cat"><span>{mcat.group(1)}</span>{mcat.group(2)}</p>')
            pending_prompt = False
            continue
        # 번호 질문/단계  **n. text**
        mq = re.match(r"^\*\*(\d+)\.\s*(.+?)\*\*$", p)
        if mq:
            badge = f'<span class="qnum">Q{mq.group(1)}</span>' if qmode else f'<span class="qnum">{mq.group(1)}.</span>'
            html_out.append(f'<p class="apx-q">{badge}{mq.group(2)}</p>')
            pending_prompt = (letter == "A")
            continue
        # 굵은 소제목 **text**
        msub = re.match(r"^\*\*(.+?)\*\*$", p)
        if msub:
            html_out.append(f'<h3>{msub.group(1)}</h3>')
            pending_prompt = False
            continue
        # 채움 라벨  'xxx:' (짧은 한 줄)
        if p.endswith(":") and len(p) <= 16 and "\n" not in p:
            lbl = p[:-1]
            html_out.append(f'<p class="fillline">{lbl}<span class="fillrule" style="display:block"></span></p>')
            continue
        # 불릿 리스트
        if re.match(r"^-\s+", p) or "\n- " in p or "\n-\t" in p:
            items = re.findall(r"(?m)^-\s+(.+)$", p)
            if items:
                lis = "".join(f"<li>{html.escape(i.strip())}</li>" for i in items)
                html_out.append(f'<ul class="bullets">{lis}</ul>')
                continue
        # 순서 리스트 (부록 C 프롬프트)
        if re.match(r"^\d+\.\s", p) or re.search(r"(?m)^\d+\.\s", p):
            items = re.findall(r"(?m)^\d+\.\s+(.+)$", p)
            if items:
                lis = "".join(f"<li>{html.escape(i.strip())}</li>" for i in items)
                html_out.append(f'<ol class="numlist">{lis}</ol>')
                continue
        # 일반 문단 (원본의 소프트 줄바꿈은 공백으로 결합)
        text = html.escape(re.sub(r"\s*\n\s*", " ", p))
        if pending_prompt:
            html_out.append(f'<div class="prompt"><span class="ptag">붙여넣을 프롬프트</span>{text}</div>')
            pending_prompt = False
        else:
            html_out.append(f"<p>{text}</p>")
    return "\n".join(html_out)

appendix_html = render_appendix(appendix_md)

# ----------------------------------------------------------------------
# 5. 마크다운 → HTML 본문 (pandoc)
# ----------------------------------------------------------------------
full_md = body_md + "\n\n" + appendix_html

tmp_md = BUILD / "_body.md"
tmp_md.write_text(full_md, encoding="utf-8")
body_html = subprocess.run(
    ["pandoc", str(tmp_md), "-f", "markdown+raw_html",
     "-t", "html"],
    capture_output=True, text=True, check=True).stdout

# ----------------------------------------------------------------------
# 6. 표지 / 판권 / 목차 (PDF·미리보기용)
# ----------------------------------------------------------------------
def cover_html():
    key = html.escape(KEYLINE).replace("\n", "<br>")
    return f'''
<section class="cover"><div class="inner">
  <div class="eyebrow">AI · INVESTING · SYSTEM</div>
  <h1>나는 AI에게<br>종목을 묻지 않았다</h1>
  <div class="rule"></div>
  <div class="sub">{html.escape(SUBTITLE)}</div>
  <div class="key">“{key}”</div>
  <div class="foot">{html.escape(PROJECT)}</div>
</div></section>'''

def frontmatter_html():
    disc = [
        "이 책은 특정 종목의 매수·매도를 권유하기 위한 책이 아닙니다.",
        "저자가 실제 투자 과정에서 AI를 활용해 시장을 해석하고, 투자 판단을 구조화하고, 포트폴리오를 관리하기 시작한 기록입니다.",
        "책에 등장하는 종목과 사례는 판단 프레임을 설명하기 위한 예시이며, 독자의 투자 성향·자산 규모·위험 감내도에 따라 판단은 달라질 수 있습니다.",
        "핵심은 종목명이 아니라 질문법·루틴·기록·복기·비중 조절에 대한 사고방식입니다.",
    ]
    items = "".join(f"<p>{html.escape(d)}</p>" for d in disc)
    return f'''
<section class="frontmatter">
  <h2>일러두기</h2>
  <div class="disclaimer"><span class="tag">DISCLAIMER</span>{items}</div>
  <ul class="meta-list">
    <li><b>제목</b> {html.escape(TITLE)}</li>
    <li><b>부제</b> {html.escape(SUBTITLE)}</li>
    <li><b>핵심</b> AI에게 정답이 아니라 ‘좋은 질문’을 묻는 법</li>
    <li><b>대상</b> AI를 투자에 활용하고 싶은 개인투자자</li>
  </ul>
</section>'''

def toc_html():
    rows = []
    for kind, anchor, label in TOC:
        if kind == "part":
            num, _, rest = label.partition(". ")
            rows.append(f'<div class="part"><span class="pno">{html.escape(num)}</span>{html.escape(rest)}</div>')
            rows.append("<ol>")
        elif kind in ("chapter", "prologue", "appendix"):
            rows.append(
                f'<li><a href="#{anchor}"><span class="t">{html.escape(label)}</span>'
                f'<span class="dots"></span></a></li>')
    body = "".join(rows)
    return f'<section class="toc"><h2>차례</h2>{body}</section>'

# ----------------------------------------------------------------------
# 7. 전체 HTML 조립 → PDF
# ----------------------------------------------------------------------
css = (ASSETS / "print.css").read_text(encoding="utf-8")
doc = f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>{html.escape(TITLE)}</title><style>{css}</style></head>
<body>
{cover_html()}
{frontmatter_html()}
{toc_html()}
<main>
{body_html}
</main>
</body></html>'''

html_path = BUILD / "book.html"
html_path.write_text(doc, encoding="utf-8")
print("[ok] HTML →", html_path)

from weasyprint import HTML
HTML(string=doc, base_url=str(ROOT)).write_pdf(str(BUILD / "book.pdf"))
print("[ok] PDF  →", BUILD / "book.pdf")

# ----------------------------------------------------------------------
# 8. EPUB (pandoc) — 표지 이미지 + 메타데이터
# ----------------------------------------------------------------------
def make_cover_png():
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 1800
    img = Image.new("RGB", (W, H), "#163B4E")
    d = ImageDraw.Draw(img)
    for y in range(H):  # 세로 그라데이션
        t = y / H
        r = int(0x12 + (0x21-0x12)*t); g = int(0x2F + (0x56-0x2F)*t); b = int(0x3E + (0x6E-0x3E)*t)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    fp = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    def font(sz): return ImageFont.truetype(fp, sz)
    d.text((90, 150), "AI · INVESTING · SYSTEM", font=font(34), fill="#C0894B")
    # 제목 줄바꿈
    title_lines = ["나는 AI에게", "종목을 묻지", "않았다"]
    y = 320
    for ln in title_lines:
        d.text((90, y), ln, font=font(120), fill="#FFFFFF"); y += 150
    d.rectangle([90, y+30, 290, y+40], fill="#C0894B")
    d.text((90, y+90), "7천만 원에서 2.5억까지,", font=font(44), fill="#D9E4E8")
    d.text((90, y+150), "AI 투자 시스템의 시작", font=font(44), fill="#D9E4E8")
    d.text((90, H-160), PROJECT, font=font(38), fill="#9FB4BC")
    cover = BUILD / "cover.png"
    img.save(cover)
    return cover

# EPUB용 마크다운: 표지 텍스트 페이지 + 일러두기 + 본문/부록 (마크다운 헤딩 유지)
epub_md = f"""# 일러두기 {{.unnumbered #front}}

> 이 책은 특정 종목의 매수·매도를 권유하기 위한 책이 아닙니다. 저자가 실제 투자 과정에서 AI를 활용해 시장을 해석하고, 투자 판단을 구조화하고, 포트폴리오를 관리하기 시작한 기록입니다. 핵심은 종목명이 아니라 질문법·루틴·기록·복기·비중 조절에 대한 사고방식입니다.

{full_md}
"""
epub_src = BUILD / "_epub.md"
epub_src.write_text(epub_md, encoding="utf-8")

meta = BUILD / "_meta.yaml"
meta.write_text(
    f'---\ntitle: "{TITLE}"\nsubtitle: "{SUBTITLE}"\nlanguage: ko\n'
    f'date: "{datetime.date.today().isoformat()}"\n---\n', encoding="utf-8")

try:
    cover = make_cover_png()
    subprocess.run(
        ["pandoc", str(epub_src), str(meta),
         "-f", "markdown+raw_html",
         "-o", str(BUILD / "book.epub"),
         "--toc", "--toc-depth=2", "--split-level=1",
         "--css", str(ASSETS / "epub.css"),
         "--epub-cover-image", str(cover)],
        check=True)
    print("[ok] EPUB →", BUILD / "book.epub")
except Exception as e:
    print("[warn] EPUB 생성 실패:", e)

print("\n완료. TOC 항목:", len(TOC))
