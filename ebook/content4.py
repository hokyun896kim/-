# -*- coding: utf-8 -*-
"""
4권 《공시는 뉴스보다 먼저 말한다》 — 콘텐츠 파서(content2.py 기반).
구조: #PART / #N장 / ### 핵심 질문·이 장의 역할·이 장의 질문은…·6단계 프레임·프롬프트·실습·한 줄 정리.
요소 스키마는 1권과 동일 → build_preview/docx/epub 재사용.
"""
import re, pathlib
from content import split_blocks
from content import clean as _clean0
def clean(s):  # 굵게/기울임 마크 제거 포함
    return _clean0(s).replace("**","").replace("*","")

ROOT=pathlib.Path(__file__).resolve().parent
SRC=ROOT/"source"/"book4.md"

TITLE="공시는 뉴스보다 먼저 말한다"
SUBTITLE="AI와 함께 읽는 DART 공시, 기업이 직접 쓴 한 줄의 무게"
KEYLINE="이 공시, 주주인 나에게 유리한가, 불리한가?"
PROJECT="호차차"; AUTHOR="호차차"; EMAIL="morningstar8590@kakao.com"
PUBDATE="2026-12-15"
PUBDATE_KO="2026년 12월 15일"   # 유페이퍼 검수 예시 표기(연·월·일 모두)
EPUB_VERSION="epub2"   # 유페이퍼는 EPUB 2.0만 받음
PUBLISHER="유페이퍼"; PRICE="9,900원"   # 유페이퍼 검수: 판권·표지·등록정보 일치
COVER="book4_cover.png"
PDF_OUT="book4_preview.pdf"; DOCX_OUT="book4.docx"; EPUB_OUT="book4.epub"
AUTHOR_BIO=("개인투자자. 뉴스보다 공시 원문을 먼저 읽고, 그 한 줄이 주주에게 유리한지 불리한지 따지는 습관을 기록해 왔다. "
 "AI를 정답 기계가 아니라 원문을 함께 따져 보는 질문 파트너로 쓰는 것이 원칙이다. "
 "『나는 AI에게 종목을 묻지 않았다』, 『그 매매법, 정말 통했을까』, 『질문이 바뀌면 경제가 보인다』에 이은 ‘호차차의 AI 읽기’ 네 번째 이야기다.")
FONT_PT=11.2; LINE=1.85; PARA_EM=1.0      # 미리보기(PDF) 본문 키우기/단락 띄우기
BODY_PT=11.2; PARA_AFTER=10               # Word 본문
# 책별 메타데이터(검색 키워드/주제) — 2권은 ‘종목추천’이 아니라 ‘경제뉴스 읽기’
DESCRIPTION="DART 공시 원문을 AI와 함께 읽고, 주주인 나에게 유리한지 불리한지 판단하는 법"
KEYWORDS=["공시","DART","전자공시","공시 읽는 법","유상증자","전환사채","자사주","개인투자자","AI 투자","챗GPT 주식"]
# 쪽 나눔(3권과 같은 규칙): 문단은 쪽 경계에 3줄 이상씩, 박스·표·그림은 쪽을 넘기지 않음
EXTRA_CSS=("p,li{orphans:3;widows:3}"
           ".prompt,.keybox,.callout,figure.cfig,table.gtbl,.endnote{page-break-inside:avoid}"
           "h3{page-break-after:avoid}"
           ".keybox{display:block}")
# 미리보기 샘플 PDF(sample_pdf.py): 표지~1장 + 구매 안내 쪽. 색은 표지(남색·파랑·금색)에 맞춤
SAMPLE={
 "out":"book4_sample.pdf", "rerender":True,
 "lead":"“이 공시, 주주인 나에게 유리한가, 불리한가?”<br>뉴스가 요약하기 전에 원문에서 먼저 읽는 법,<br>나머지 이야기는 본문에서 이어집니다.",
 "toc":["프롤로그 · 1~14장 · 에필로그 · 부록","1부 공시는 왜 먼저 말하는가","2부 돈이 들어오는 공시 — 공급계약·잠정실적·자사주",
        "3부 돈이 나가는 공시 — 유상증자·전환사채·지분 변동","4부 조용한 경고 — 감사의견·침묵·관리종목",
        "5부 루틴과 검증","부록 · AI 질문 카드 31 / 유리·불리 체크리스트 48 / 용어 57"],
 "foot":"종목 추천·수익 보장 아님(공시 읽기 교육)",
 "keywords":"공시, DART, AI 투자, 미리보기",
 "colors":{"g1":"#121212","g2":"#1D1D1F","g3":"#2E2E30","gold":"#F2D200","goldl":"#FFE866",
           "glow":"rgba(242,210,0,.28)","edge":"rgba(242,210,0,.6)","lead":"#E6E6E6","toc":"#F2F2F2","foot":"#A8A8A8"},
}
READKEY="이 책의 질문은 하나입니다. 주주인 나에게 유리한가, 불리한가."
READGUIDE="1부를 먼저 읽고 2~4부는 궁금한 공시 유형부터 펼쳐도 됩니다. 부록의 질문 카드와 체크리스트는 공시를 열 때마다 옆에 두세요."
# 부(部) 표지에 들어갈 ‘한 줄 요약’ — 그 부 전체를 한 문장으로
PART_SUM={
 1:"뉴스는 공시를 옮겨 적는다. 원문을 고르고, 읽고, AI에게 제대로 넘기는 법부터.",
 2:"들어오는 돈의 공시는 크기보다 기간·조건·이행으로 무게를 잰다.",
 3:"나가는 돈의 공시는 내 지분이 얼마나 옅어지는지부터 계산한다.",
 4:"가장 큰 경고는 큰 소리로 오지 않는다. 정정·미확정·빈칸이 먼저 말한다.",
 5:"매일 15분의 기록이 쌓이면 내 체크리스트를 숫자로 검증할 수 있다.",
}
CH2_FIGURE={}; CH2_FIGURE2={}; ROUTE=set(); FIG_AT={}   # 4권 그림은 추후 데이터 계약형 생성기로
THEME={"navy":"#1D1D1F","navy2":"#3A3A3C","accent":"#C9A400","accentd":"#8A6D00",
       "tint2":"#FFF8D6","cream1":"#FFFBEA","cream2":"#FFF1A8","edge":"#E8D36A"}
DISCLAIMER=[
 "이 책은 특정 종목의 매수나 매도를 권유하지 않습니다. 공시를 읽고 스스로 판단하는 방법을 다룹니다.",
 "책에 나오는 공시 가운데 ‘가상의’라고 밝힌 것은 설명을 위해 만든 예시입니다.",
 "공시 제도와 공시 의무 기준은 바뀔 수 있으니 실제 판단 전에는 DART와 한국거래소의 최신 안내를 확인하시기 바랍니다.",
 "투자와 의사결정의 최종 판단·책임은 독자 본인에게 있습니다.",
]

def _is_heading(b): return bool(re.match(r'^#{1,4}\s', b.strip()))

def _is_table(s):
    lines=[l for l in s.splitlines() if l.strip()]
    return len(lines)>=2 and sum(1 for l in lines if l.strip().startswith('|'))>=2

def _parse_table(s):
    rows=[]; header=False
    for l in s.splitlines():
        t=l.strip()
        if not t.startswith('|'): continue
        if re.fullmatch(r'[\|\-\:\s]+', t) and '-' in t:
            if rows: header=True
            continue
        rows.append([clean(c) for c in t.strip('|').split('|')])
    # 빈 열 제거(양끝)
    return rows, header

def _render_blocks(blocks):
    """일반 본문 블록 → 요소. 단락은 병합하지 않고 블록 하나=문단 하나(단락 띄우기)."""
    E=[]
    for b in blocks:
        s=b.strip()
        if not s: continue
        if _is_table(s):
            rows,hdr=_parse_table(s); E.append(('gtable', rows, hdr)); continue
        if re.search(r'(?m)^\d+\.\s', s):
            E.append(('numlist',[(n,clean(x)) for n,x in re.findall(r'(?m)^(\d+)\.\s+(.+)$',s)])); continue
        if re.match(r'^[-*]\s+', s):
            E.append(('bullets',[clean(x) for x in re.findall(r'(?m)^[-*]\s+(.+)$',s)])); continue
        if s.startswith('>'):
            E.append(('prompt', clean(re.sub(r'(?m)^>\s?','',s)), 'AI에게 이렇게 묻습니다')); continue
        E.append(('para', clean(s), False))
    return E

def _endnote_lines(blocks):
    text=" ".join(clean(b) for b in blocks)
    sents=[s.strip() for s in re.split(r'(?<=다\.)|(?<=요\.)', text) if s.strip()]
    out=[s for s in sents if len(s)>=6][:3]
    return out or ([text[:120]] if text else ["—"])

def _collect(blocks, k):
    """다음 헤딩 전까지의 본문 블록 모으기."""
    body=[]
    while k<len(blocks) and not _is_heading(blocks[k]):
        body.append(blocks[k]); k+=1
    return body, k

def parse():
    raw=SRC.read_text(encoding="utf-8")
    raw=re.sub(r'(?m)^#\s+(\d+)부\.\s*(.+)$', r'# PART \1\n\n## \2', raw)   # 'N부. 제목' → PART 형식
    lines=raw.split("\n")
    def first(pat, start=0):
        for i in range(start,len(lines)):
            if re.match(pat, lines[i]): return i
        return -1
    i_pro=first(r'^#\s+프롤로그')
    i_body=first(r'^#\s+PART\s', i_pro+1)
    i_epi=first(r'^#\s+에필로그', i_body+1)
    i_apx=first(r'^#\s+부록', i_epi+1)
    prologue_md="\n".join(lines[i_pro:i_body])
    body_md="\n".join(lines[i_body:i_epi])
    epi_md="\n".join(lines[i_epi:i_apx])
    apx_md="\n".join(lines[i_apx:])
    def sub_of(md):
        m=re.search(r'(?m)^##\s+(.+)$', md); return clean(m.group(1)) if m else ""
    E=[('cover',), ('disclaimer', DISCLAIMER), ('toc',)]
    E.append(('h1big','prologue',sub_of(prologue_md),'chat_q'))
    E += _prologue(prologue_md)
    E += _body(body_md)
    E.append(('h1big','epilogue',sub_of(epi_md),''))
    E += _prologue(epi_md)
    E += _appendix(apx_md)
    E.append(('closing', KEYLINE))
    E.append(('authorbio', AUTHOR, AUTHOR_BIO))
    E.append(('colophon', [("도서명",TITLE),("부제",SUBTITLE),("저자명",AUTHOR),("출판사명",PUBLISHER),
                           ("발행일",PUBDATE_KO),("가격",PRICE),("E-MAIL",EMAIL)]))
    return E

def _prologue(md):
    blocks=[b for b in split_blocks(md) if b.strip()]
    E=[]; i=0; lead=[True]
    buf=[]
    def flush():
        if buf:
            t=" ".join(buf).strip()
            if t: E.append(('para', t, lead[0])); lead[0]=False
            buf.clear()
    for b in blocks:
        s=b.strip()
        if re.match(r'^#\s+프롤로그', s) or re.match(r'^##\s', s): continue   # 제목/부제 헤딩 제거
        m=re.match(r'^###\s+(.+)', s)
        if m: flush(); E.append(('h3', clean(m.group(1)))); continue
        if re.match(r'^[-*]\s+', s):
            flush(); E.append(('bullets',[clean(x) for x in re.findall(r'(?m)^[-*]\s+(.+)$',s)])); continue
        buf.append(clean(s))
        if len(" ".join(buf))>=300: flush()
    flush()
    return E

def _body(md):
    blocks=[b for b in split_blocks(md) if b.strip()]
    E=[]; k=0; n=len(blocks)
    pcount=[0]; pending=[]   # 장별 [(문단 임계값, figure 요소)]
    def setup(cn):
        pcount[0]=0; p=[]; t1,t2=FIG_AT.get(cn,(2,5))
        if cn in ROUTE: p.append((0,('figure',f'route_{cn}','',' ')))   # 첫 문단 앞
        if cn in CH2_FIGURE: nm,cap=CH2_FIGURE[cn]; p.append((t1,('figure',nm,cap)))
        if cn in CH2_FIGURE2: nm,cap=CH2_FIGURE2[cn]; p.append((t2,('figure',nm,cap)))
        pending[:]=p
    def place(force=False):
        rem=[]
        for th,el in pending:
            if force or pcount[0]>=th: E.append(el)
            else: rem.append((th,el))
        pending[:]=rem
    held=[]                      # '이 장의 정리'를 장 끝으로 미뤄 일관되게 마무리
    def flush():
        place(True)
        if held: E.extend(held); held.clear()
    while k<n:
        s=blocks[k].strip()
        m=re.match(r'^#\s+PART\s*(\d+)', s)
        if m:
            flush(); num=m.group(1); title=""
            if k+1<n and re.match(r'^##\s', blocks[k+1]):
                title=clean(re.sub(r'^##\s*','',blocks[k+1].strip())); k+=1
            E.append(('part', num, title, '', PART_SUM.get(int(num),''))); k+=1; continue
        m=re.match(r'^#\s+(\d+)장\.\s*(.+)', s)
        if m:
            flush()                          # 이전 장: 도식 보강 + 정리 박스 배치
            cn=int(m.group(1)); E.append(('chapter', cn, clean(m.group(2)), '')); setup(cn); k+=1; continue
        m=re.match(r'^#{2,3}\s+(.+)', s)     # 소제목(##/###)
        if m:
            label=clean(m.group(1)); body,k=_collect(blocks,k+1)
            if '마무리' in label: flush()    # 부(部) 마무리 앞에 장 정리를 먼저 둔다
            for el in _dispatch(label, body):
                (held if el and el[0]=='endnote' else E).append(el)
            continue
        if _is_table(s):
            rows,hdr=_parse_table(s); E.append(('gtable', rows, hdr)); k+=1; continue
        place()                              # 임계값 0(노선도)은 첫 문단 앞에
        E.append(('para', clean(s), False)); pcount[0]+=1
        place()                              # 임계값 도달한 도식 배치
        k+=1
    flush()
    return E

def _dispatch(label, body):
    """소제목 종류별 렌더 요소."""
    if label.startswith("핵심 질문") or label.startswith("이 장의 질문은"):
        out=[]
        if body: out.append(('keysentence', clean(body[0]), 'chat_q'))
        out += _render_blocks(body[1:]); return out
    if label.startswith("이 장의 역할"):
        out=[]
        if body: out.append(('callout', "이 장의 역할", clean(body[0])))
        out += _render_blocks(body[1:]); return out
    if label.startswith("한 줄 정리"):
        return [('endnote', _endnote_lines(body))]
    if label.startswith("프롬프트"):
        out=[('h3', label)]
        if body: out.append(('prompt', clean(body[0])))   # 첫 블록만 프롬프트
        out += _render_blocks(body[1:])                    # 나머지는 본문
        return out
    # 그 외(실습·6단계 프레임·바로 쓰는 질문·좋은 AI 질문·하루 10분·①②③·마무리·저자의 노트 등)
    return [('h3', label)] + _render_blocks(body)

def _appendix(md):
    blocks=[b for b in split_blocks(md) if b.strip()]
    E=[('h1big','appendix','부록 · 공시 읽기 도구상자','clipboard')]
    for b in blocks[1:]:
        s=b.strip()
        if _is_table(s):
            rows,hdr=_parse_table(s); E.append(('gtable', rows, hdr)); continue
        m=re.match(r'^##\s+(\d+)\.\s*(.+)', s)
        if m: E.append(('cat', m.group(1), clean(m.group(2)))); continue
        m=re.match(r'^#{2,4}\s+(.+)', s)
        if m: E.append(('h3', clean(m.group(1)))); continue
        if re.match(r'^[-*]\s+', s):
            E.append(('bullets',[clean(x) for x in re.findall(r'(?m)^[-*]\s+(.+)$',s)])); continue
        if re.search(r'(?m)^\d+\.\s', s):
            E.append(('numlist',[(nn,clean(x)) for nn,x in re.findall(r'(?m)^(\d+)\.\s+(.+)$',s)])); continue
        if s.startswith('>'):
            E.append(('prompt', clean(re.sub(r'(?m)^>\s?','',s)), 'AI에게 이렇게 묻습니다')); continue
        E.append(('para', clean(s), False))
    return E
