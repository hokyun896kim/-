# -*- coding: utf-8 -*-
"""
2권 《질문이 바뀌면 경제가 보인다》 — 콘텐츠 파서.
1권과 구조가 달라(영문 PART, 장 끝 '한 줄 정리', 부록 도구상자) 전용 파서를 둔다.
요소 스키마는 1권과 동일하므로 build_preview/docx/epub 렌더러를 그대로 재사용한다.
"""
import re, pathlib
from content import split_blocks
from content import clean as _clean0
def clean(s): return _clean0(s).replace("**","")   # 굵게 표식 제거 포함

ROOT=pathlib.Path(__file__).resolve().parent
SRC=ROOT/"source"/"book2.md"

TITLE="질문이 바뀌면 경제가 보인다"
SUBTITLE="막막한 경제 뉴스를, AI와 함께 읽는 법"
KEYLINE="경제는 외우는 것이 아니라, 질문으로 읽는 것이다."
PROJECT="호차차"
AUTHOR="호차차"
EMAIL="morningstar8590@kakao.com"
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

def _is_heading(b): return bool(re.match(r'^#{1,3}\s', b.strip()))
def _is_struct(b):  # 요약 수집을 멈춰야 하는 경계(헤딩/굵은 장/굵은 한줄정리)
    s=b.strip()
    return (_is_heading(s) or bool(re.match(r'^\*\*\d+장\.', s))
            or bool(re.match(r'^\*\*한 줄 정리\*\*', s)) or s.startswith("# PART"))

def _endnote_lines(blocks):
    text=" ".join(clean(b) for b in blocks)
    sents=[s.strip() for s in re.split(r'(?<=다\.)|(?<=요\.)', text) if s.strip()]
    out=[s for s in sents if len(s)>=6][:3]
    return out or ([clean(" ".join(blocks))[:120]] if blocks else [])

def parse():
    raw=SRC.read_text(encoding="utf-8")
    lines=raw.split("\n")
    def idx(pred):
        for i,l in enumerate(lines):
            if pred(l): return i
        return -1
    i_p1=idx(lambda l: l.startswith("# PART 1"))
    i_apx=idx(lambda l: l.startswith("# 부록"))
    prologue_md="\n".join(lines[:i_p1])
    body_md="\n".join(lines[i_p1:i_apx])
    apx_md="\n".join(lines[i_apx:])

    E=[('cover',), ('disclaimer', DISCLAIMER), ('toc',)]
    # 프롤로그
    E.append(('h1big','prologue','경제가 어려운 건 당신 탓이 아닙니다','chat_q'))
    E += _prose(prologue_md, skip_bold_head=True, lead_first=True)
    # 본문
    E += _body(body_md)
    # 부록
    E += _appendix(apx_md)
    # 닫는 문장 + 뒷부속
    E.append(('closing', "경제는 외우는 것이 아니라, 질문으로 읽는 것입니다."))
    E.append(('authorbio', AUTHOR, AUTHOR_BIO))
    E.append(('colophon', [("제목",TITLE),("부제",SUBTITLE),("지은이",AUTHOR),
                           ("발행",f"{PROJECT} (자가출판)"),("발행일",PUBDATE),("문의",EMAIL)]))
    return E

def _prose(md, skip_bold_head=False, lead_first=False):
    E=[]; buf=[]; first=[lead_first]
    def flush():
        if buf:
            t=" ".join(buf).strip()
            if t: E.append(('para', t, first[0])); first[0]=False
            buf.clear()
    for b in split_blocks(md):
        s=b.strip()
        if not s: continue
        if skip_bold_head and re.match(r'^\*\*[^*]+\*\*$', s):  # **프롤로그**, **부제** 류 제거
            continue
        if re.match(r'^[-*]\s+', s):
            flush(); E.append(('bullets',[clean(x) for x in re.findall(r'(?m)^[-*]\s+(.+)$',s)])); continue
        buf.append(clean(s))
        if len(" ".join(buf))>=300: flush()
    flush()
    return E

def _body(md):
    blocks=[b for b in split_blocks(md) if b.strip()]
    E=[]; buf=[]; need_lead=[False]
    def flush():
        if buf:
            t=" ".join(buf).strip()
            if t: E.append(('para', t, need_lead[0])); need_lead[0]=False
            buf.clear()
    k=0
    while k<len(blocks):
        s=blocks[k].strip()
        m=re.match(r'^# PART\s*(\d+)\.\s*(.+)$', s)
        if m: flush(); E.append(('part', m.group(1), clean(m.group(2)), '', '')); k+=1; continue
        m=re.match(r'^(?:#{1,2}\s*|\*\*)(\d+)장\.\s*(.+?)\*?\*?$', s)
        if m: flush(); E.append(('chapter', int(m.group(1)), clean(m.group(2)), '')); need_lead[0]=True; k+=1; continue
        if re.match(r'^(##\s*한 줄 정리|\*\*한 줄 정리\*\*)', s):
            flush(); k+=1; summ=[]
            while k<len(blocks) and not _is_struct(blocks[k]):
                summ.append(blocks[k]); k+=1
            E.append(('endnote', _endnote_lines(summ))); continue
        if re.match(r'^#{1,3}\s', s):                       # 기타 소제목
            flush(); E.append(('h3', clean(re.sub(r'^#{1,3}\s*','',s)))); k+=1; continue
        if re.match(r'^\*\*[^*]+\*\*$', s):
            flush(); E.append(('h3', s.strip('*'))); k+=1; continue
        if re.match(r'^[-*]\s+', s):
            flush(); E.append(('bullets',[clean(x) for x in re.findall(r'(?m)^[-*]\s+(.+)$',s)])); k+=1; continue
        buf.append(clean(s))
        if len(" ".join(buf))>=300: flush()
        k+=1
    flush()
    return E

def _appendix(md):
    E=[('h1big','appendix','부록 · AI 경제 읽기 도구상자','clipboard')]
    blocks=[b for b in split_blocks(md) if b.strip()]
    for b in blocks[1:]:      # 첫 블록(# 부록 …) 제외
        s=b.strip()
        m=re.match(r'^##\s*(\d+)\.\s*(.+)$', s)
        if m: E.append(('cat', m.group(1), clean(m.group(2)))); continue
        m=re.match(r'^###\s*(.+)$', s)
        if m: E.append(('h3', clean(m.group(1)))); continue
        if re.match(r'^##\s', s):                 # 《제목》 등
            E.append(('h3', clean(re.sub(r'^##\s*','',s)))); continue
        if re.match(r'^[-*]\s+', s):
            E.append(('bullets',[clean(x) for x in re.findall(r'(?m)^[-*]\s+(.+)$',s)])); continue
        E.append(('para', clean(s), False))
    return E
