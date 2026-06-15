# -*- coding: utf-8 -*-
"""
2권 《질문이 바뀌면 경제가 보인다》 — ver0.5 콘텐츠 파서.
구조: #PART / #N장 / ### 핵심 질문·이 장의 역할·이 장의 질문은…·6단계 프레임·프롬프트·실습·한 줄 정리.
요소 스키마는 1권과 동일 → build_preview/docx/epub 재사용.
"""
import re, pathlib
from content import split_blocks
from content import clean as _clean0
def clean(s):  # 굵게/기울임 마크 제거 포함
    return _clean0(s).replace("**","").replace("*","")

ROOT=pathlib.Path(__file__).resolve().parent
SRC=ROOT/"source"/"book2.md"

TITLE="질문이 바뀌면 경제가 보인다"
SUBTITLE="금리·환율·실적 뉴스를 내 돈의 언어로 번역하는 직장인 AI 경제 루틴"
KEYLINE="경제는 외우는 것이 아니라, 질문으로 읽는 것이다."
PROJECT="호차차"; AUTHOR="호차차"; EMAIL="morningstar8590@kakao.com"
PUBDATE="2026년 6월 초판 1쇄"
COVER="book2_cover.png"
PDF_OUT="book2_preview.pdf"; DOCX_OUT="book2.docx"; EPUB_OUT="book2.epub"
AUTHOR_BIO=("개인투자자이자 ‘경제 읽기’ 기록자. AI를 정답 기계가 아니라 ‘질문 파트너’로 쓰면서, "
 "막막하던 경제 뉴스와 지표를 스스로 읽고 판단하는 루틴을 만들어 왔다. 이 책은 그 과정을 정리한 실전 안내서다. "
 "전작 『나는 AI에게 종목을 묻지 않았다』에 이은 ‘호차차의 AI 읽기’ 두 번째 기록이다.")
FONT_PT=11.2; LINE=1.85; PARA_EM=1.0      # 미리보기(PDF) 본문 키우기/단락 띄우기
BODY_PT=11.2; PARA_AFTER=10               # Word 본문
CH2_FIGURE={
 1:("fig2_1","용어가 아니라 ‘연결고리’가 어렵다"),
 2:("fig2_2","AI에게 답이 아니라 ‘판단 구조’를 시킨다"),
 3:("fig2_3","금리는 돈의 가격 — 대출·집값·소비를 흔든다"),
 4:("fig2_4","환율은 양방향 — 장바구니와 수출이 반대로"),
 5:("fig2_5","월급이 그대로면 물가만큼 가난해진다"),
 6:("fig2_6","좋은 고용도 물가→금리로 부담이 된다"),
 7:("fig2_7","발표보다 ‘말투(매파·비둘기파)’를 읽는다"),
 8:("fig2_8","전쟁 → 유가 → 물가 → 금리 → 내 지갑"),
 9:("fig2_9","매출보다 ‘영업이익’을 본다"),
 10:("fig2_10","이익이 더 빨리 좋아지는 회사"),
 11:("fig2_11","이익이 나도 현금이 없으면 무너진다"),
 12:("fig2_12","산업에도 사계절이 있다"),
 13:("fig2_13","재무제표 3종을 함께 읽는다"),
 14:("fig2_14","시장은 ‘기대와의 차이’에 반응한다"),
 15:("fig2_15","해석보다 원문(1차 소스) 먼저"),
 16:("fig2_16","‘A 때문에 B’가 진짜 인과인지 본다"),
 17:("fig2_17","기사에 ‘없는 것(침묵)’도 정보다"),
 18:("fig2_18","보고 싶은 것만 보지 않으려면 반증을"),
 19:("fig2_19","AI 답도 절차로 팩트체크한다"),
 20:("fig2_20","하루 10분이면 흐름이 쌓인다"),
 21:("fig2_21","점을 선으로 — 일주일로 흐름 잡기"),
 22:("fig2_22","질문→분해→검증→기록이 돌면 내 것이 된다"),
}
CH2_FIGURE2={
 1:("fig2b_1","용어를 좇으면 빠지는 함정"),2:("fig2b_2","맥락·목표·형식 — 좋은 질문 공식"),
 3:("fig2b_3","금리 방향이 시장 배경을 바꾼다"),4:("fig2b_4","환율 = 금리차·수급·심리"),
 5:("fig2b_5","물가가 건드리는 것들"),6:("fig2b_6","고용 온도 — 너무 뜨거워도 부담"),
 7:("fig2b_7","발표보다 ‘무엇이 달라졌나’"),8:("fig2b_8","유가 방향이 승자·패자를 가른다"),
 9:("fig2b_9","좋은 비용 vs 나쁜 비용"),10:("fig2b_10","이익이 매출보다 먼저 좋아진다"),
 11:("fig2b_11","갚을 현금이 있는가"),12:("fig2b_12","성장기 vs 성숙기 포인트"),
 13:("fig2b_13","현금→이익→자산 순으로 읽기"),14:("fig2b_14","기대의 사이클 — 지금 어디인가"),
 15:("fig2b_15","원문으로 거슬러 올라가기"),16:("fig2b_16","상관 ≠ 인과"),
 17:("fig2b_17","기사가 빼놓은 것 채우기"),18:("fig2b_18","일부러 반대편을 세우기"),
 19:("fig2b_19","믿을 신호 vs 의심 신호"),20:("fig2b_20","10분이 흐름·관점이 되는 법"),
 21:("fig2b_21","주간 복기 루프"),22:("fig2b_22","AI 잘 쓰기 vs 못 쓰기"),
}
DISCLAIMER=[
 "이 책은 특정 종목·상품의 투자를 권유하기 위한 책이 아닙니다.",
 "경제 뉴스와 지표를 스스로 읽고 판단하는 힘을 기르기 위한 교육·실전 안내서입니다.",
 "책에 나오는 사례와 수치는 이해를 돕기 위한 예시이며, 시점에 따라 달라질 수 있습니다.",
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
    lines=SRC.read_text(encoding="utf-8").split("\n")
    def first(pat, start=0):
        for i in range(start,len(lines)):
            if re.match(pat, lines[i]): return i
        return -1
    i_pro=first(r'^#\s+프롤로그')
    i_body=first(r'^#\s+PART\s', i_pro+1)
    i_apx=first(r'^#\s+부록', i_body+1)
    prologue_md="\n".join(lines[i_pro:i_body])
    body_md="\n".join(lines[i_body:i_apx])
    apx_md="\n".join(lines[i_apx:])

    E=[('cover',), ('disclaimer', DISCLAIMER), ('toc',)]
    # 프롤로그
    E.append(('h1big','prologue','경제가 어려운 건 당신 탓이 아닙니다','chat_q'))
    E += _prologue(prologue_md)
    E += _body(body_md)
    E += _appendix(apx_md)
    E.append(('closing', "경제는 외우는 것이 아니라, 질문으로 읽는 것입니다."))
    E.append(('authorbio', AUTHOR, AUTHOR_BIO))
    E.append(('colophon', [("제목",TITLE),("부제",SUBTITLE),("지은이",AUTHOR),
                           ("발행",f"{PROJECT} (자가출판)"),("발행일",PUBDATE),("문의",EMAIL)]))
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
        pcount[0]=0; p=[]
        if cn in CH2_FIGURE: nm,cap=CH2_FIGURE[cn]; p.append((2,('figure',nm,cap)))
        if cn in CH2_FIGURE2: nm,cap=CH2_FIGURE2[cn]; p.append((5,('figure',nm,cap)))
        pending[:]=p
    def place(force=False):
        rem=[]
        for th,el in pending:
            if force or pcount[0]>=th: E.append(el)
            else: rem.append((th,el))
        pending[:]=rem
    while k<n:
        s=blocks[k].strip()
        m=re.match(r'^#\s+PART\s*(\d+)', s)
        if m:
            place(True); num=m.group(1); title=""
            if k+1<n and re.match(r'^##\s', blocks[k+1]):
                title=clean(re.sub(r'^##\s*','',blocks[k+1].strip())); k+=1
            E.append(('part', num, title, '', '')); k+=1; continue
        m=re.match(r'^#\s+(\d+)장\.\s*(.+)', s)
        if m:
            place(True)                      # 이전 장 미배치분 보강
            cn=int(m.group(1)); E.append(('chapter', cn, clean(m.group(2)), '')); setup(cn); k+=1; continue
        m=re.match(r'^#{2,3}\s+(.+)', s)     # 소제목(##/###)
        if m:
            label=clean(m.group(1)); body,k=_collect(blocks,k+1)
            E += _dispatch(label, body); continue
        if _is_table(s):
            rows,hdr=_parse_table(s); E.append(('gtable', rows, hdr)); k+=1; continue
        E.append(('para', clean(s), False)); pcount[0]+=1
        place()                              # 임계값 도달한 도식 배치
        k+=1
    place(True)
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
    E=[('h1big','appendix','부록 · AI 경제 읽기 도구상자','clipboard')]
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
        E.append(('para', clean(s), False))
    return E
