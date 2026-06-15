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
DISCLAIMER=[
 "이 책은 특정 종목·상품의 투자를 권유하기 위한 책이 아닙니다.",
 "경제 뉴스와 지표를 스스로 읽고 판단하는 힘을 기르기 위한 교육·실전 안내서입니다.",
 "책에 나오는 사례와 수치는 이해를 돕기 위한 예시이며, 시점에 따라 달라질 수 있습니다.",
 "투자와 의사결정의 최종 판단·책임은 독자 본인에게 있습니다.",
]

def _is_heading(b): return bool(re.match(r'^#{1,4}\s', b.strip()))

def _render_blocks(blocks):
    """일반 본문 블록 → para(병합)/bullets/numlist 요소."""
    E=[]; buf=[]
    def flush():
        if buf:
            t=" ".join(buf).strip()
            if t: E.append(('para', t, False))
            buf.clear()
    for b in blocks:
        s=b.strip()
        if not s: continue
        if re.search(r'(?m)^\d+\.\s', s):
            flush(); E.append(('numlist',[(n,clean(x)) for n,x in re.findall(r'(?m)^(\d+)\.\s+(.+)$',s)])); continue
        if re.match(r'^[-*]\s+', s):
            flush(); E.append(('bullets',[clean(x) for x in re.findall(r'(?m)^[-*]\s+(.+)$',s)])); continue
        buf.append(clean(s))
        if len(" ".join(buf))>=300: flush()
    flush()
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
    E=[]; k=0; n=len(blocks); buf=[]
    def flush():
        if buf:
            t=" ".join(buf).strip()
            if t: E.append(('para', t, False))
            buf.clear()
    while k<n:
        s=blocks[k].strip()
        m=re.match(r'^#\s+PART\s*(\d+)', s)
        if m:
            flush(); num=m.group(1); title=""
            if k+1<n and re.match(r'^##\s', blocks[k+1]):
                title=clean(re.sub(r'^##\s*','',blocks[k+1].strip())); k+=1
            E.append(('part', num, title, '', '')); k+=1; continue
        m=re.match(r'^#\s+(\d+)장\.\s*(.+)', s)
        if m:
            flush(); E.append(('chapter', int(m.group(1)), clean(m.group(2)), '')); k+=1; continue
        m=re.match(r'^#{2,3}\s+(.+)', s)     # 소제목(##/###)
        if m:
            flush(); label=clean(m.group(1)); body,k=_collect(blocks,k+1)
            E += _dispatch(label, body); continue
        buf.append(clean(s))
        if len(" ".join(buf))>=300: flush()
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
        if body: out.append(('prompt', " ".join(clean(b) for b in body)))
        return out
    # 그 외(실습·6단계 프레임·바로 쓰는 질문·좋은 AI 질문·하루 10분·①②③·마무리·저자의 노트 등)
    return [('h3', label)] + _render_blocks(body)

def _appendix(md):
    blocks=[b for b in split_blocks(md) if b.strip()]
    E=[('h1big','appendix','부록 · AI 경제 읽기 도구상자','clipboard')]
    for b in blocks[1:]:
        s=b.strip()
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
