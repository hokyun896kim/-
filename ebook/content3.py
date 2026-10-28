# -*- coding: utf-8 -*-
"""
3권 《나는 유튜브 매매법을 믿지 않았다》 — v0.8 콘텐츠 파서.
구조: # N부 / ## N장 / ### 소제목, 인용 박스(> **라벨** …)로 핵심·그림·더 깊이 보기·주의·규칙을 구분.
장 끝 ‘질문을 바꿨습니다’는 예전 질문 → 바뀐 질문 카드 + AI 프롬프트 박스로 정리한다.
요소 스키마는 1·2권과 공유 → build_preview/docx/epub 재사용.
"""
import re, pathlib, shutil
from content import split_blocks
from content import clean as _clean0
from content2 import _is_table, _parse_table, _collect
def clean(s):
    return _clean0(s).replace("**","").replace("*","")

ROOT=pathlib.Path(__file__).resolve().parent
SRC=ROOT/"source"/"book3.md"
IMGSRC=ROOT/"assets"/"book3"; IMG=ROOT/"build"/"img"

TITLE="나는 유튜브 매매법을 믿지 않았다"
SUBTITLE="AI와 함께 21년 치 데이터로 돌려봤더니, 살아남은 건 몇 개뿐이었다"
KEYLINE="“그 방법, 정말 통했어? 숫자로 보여 줘.”"
PROJECT="호차차"; AUTHOR="호차차"; EMAIL="morningstar8590@kakao.com"
PUBDATE="2026년 11월 초판 1쇄"
COVER="book3_cover.png"
PDF_OUT="book3_preview.pdf"; DOCX_OUT="book3.docx"; EPUB_OUT="book3.epub"
AUTHOR_BIO=("개인투자자. 유튜브와 커뮤니티에서 유행하는 매매법을 그냥 믿지 않고, AI와 함께 21년 치 한국 시장 데이터로 "
 "하나씩 돌려 본 기록을 남긴다. 계산은 AI가, 의심은 사람이 맡는다는 원칙으로 일한다. "
 "『나는 AI에게 종목을 묻지 않았다』에 이은 두 번째 이야기다.")
FONT_PT=11.0; LINE=1.85; PARA_EM=1.0      # 미리보기(PDF) 본문
BODY_PT=11.0; PARA_AFTER=10               # Word 본문
DESCRIPTION="유튜브 매매법을 AI와 함께 21년 치 한국 시장 데이터로 검증한 기록 — 무엇이 무너지고 무엇이 살아남았나"
KEYWORDS=["주식 백테스트","매매법 검증","AI 투자","챗GPT 주식","개인투자자","손절","급락 반등","눌림목","코스피 RSI"]
READKEY="이 책의 핵심은 매매법이 아니라 ‘검증하는 질문’입니다."
READGUIDE="3부의 규칙은 숫자까지 공개하지만, 장마다 ‘따라 하기 전에 알아야 할 것’ 박스를 규칙보다 먼저 읽어 주세요."
# 책 고유 색(표지의 네이비 + 코랄)
THEME={"navy":"#13283F","navy2":"#24496B","accent":"#D9553C","accentd":"#B5402B",
       "tint2":"#FBEFEA","cream1":"#FCF1EC","cream2":"#F6DDD3","edge":"#E8B9A9"}

DISCLAIMER=[
 "이 책은 특정 종목이나 상품의 매수·매도를 권유하기 위한 책이 아닙니다. AI와 함께 한국 주식시장의 매매법들을 과거 데이터로 검증한 기록입니다.",
 "책에 나오는 수익률과 승률은 모두 과거 데이터로 계산한 결과이며, 앞으로도 같은 결과가 나온다는 보장은 없습니다. 특히 3부의 숫자 대부분은 성적을 본 뒤에 고른 값입니다.",
 "각 장의 ‘따라 하기 전에 알아야 할 것’과 ‘더 깊이 보기’를 규칙보다 먼저 읽어 주십시오.",
 "책에 등장하는 종목은 실제 시세를 사용했으나 이름은 가렸습니다. 투자 판단과 그 결과는 각자의 몫입니다.",
]
PART_SUM={
 1:"경험은 강하지만 표본이 작다. 1편의 감을 21년 치 숫자 앞에 다시 세웠다.",
 2:"그럴듯한 이야기는 숫자를 확인하고 싶은 마음을 지운다. 유명한 매매법 대부분은 무작위보다 못했다.",
 3:"살아남은 것들은 남들이 신나서 살 때가 아니라, 다들 겁먹고 던질 때 나타났다.",
 4:"계산은 AI가 하고, 의심은 내가 한다. 좋은 숫자일수록 먼저 깨뜨려 본다.",
}
# 쪽 나눔 규칙(이 책 전용): 박스·카드·표·그림은 쪽을 넘기지 않고, 문단은 쪽 경계에 3줄 이상씩 남긴다
EXTRA_CSS=("p,li{orphans:3;widows:3}"
           ".infobox,.rulecard,.prompt,.qchange,.keybox,.callout,figure.cfig,table.gtbl,.endnote{page-break-inside:avoid}"
           "h3,.qhead,.iblabel{page-break-after:avoid}"
           ".rulecard{font-size:9.2pt}.rulecard .rc-sec{padding:2.2mm 4.6mm}"      # 긴 카드도 한 쪽에
           ".rulecard li{line-height:1.45;margin-bottom:.5mm}.rulecard .rc-lbl{margin-bottom:.8mm}"
           # 박스·표를 조금 촘촘하게 → 통째로 다음 쪽으로 밀려 생기는 빈 공간을 줄인다
           "table.gtbl{font-size:8.9pt}table.gtbl th,table.gtbl td{padding:1.6mm 2.3mm;line-height:1.4}"
           ".prompt{font-size:9pt;line-height:1.52;padding:3mm 3.8mm}.prompt ul.plist li{margin-bottom:1.1mm}"
           ".ib-caution{font-size:8.9pt;line-height:1.52}.ib-deep{font-size:8.4pt;line-height:1.5}"
           ".qchange{padding:4mm 5mm}h3.qhead{margin-top:8mm}"
           "table.gtbl.dense{font-size:8.4pt}table.gtbl.dense th,table.gtbl.dense td{padding:1.05mm 2mm;line-height:1.33}")
FIG_SCALE={"b3_rId35":0.78,"b3_rId164":0.8}   # 그림별 축소 비율(쪽 끝 남은 공간에 맞추기)
# 미리보기 샘플 PDF(sample_pdf.py): 표지~1장 + 구매 안내 쪽. 색은 새 표지(남색·파랑·금색)에 맞춤
SAMPLE={
 "out":"book3_sample.pdf", "rerender":True,
 "lead":"“그 방법, 정말 통했어? 숫자로 보여 줘.”<br>유튜브 매매법을 21년 치 데이터로 하나씩 확인한 기록,<br>나머지 이야기는 본문에서 이어집니다.",
 "toc":["프롤로그 · 1~14장 · 에필로그","1부 감으로 바꾼 질문, 숫자로 확인하다","2부 통할 것 같았는데 안 통한 것들",
        "3부 그래도 살아남은 것들","4부 AI와 함께 의심하는 법",
        "부록 A~C · 매매법을 만났을 때 던질 질문 / AI 결과를 의심하는 질문 / 3부 규칙 요약 카드"],
 "foot":"종목 추천·수익 보장 아님(투자 교육·검증 기록)",
 "keywords":"주식 백테스트, 매매법 검증, AI 투자, 미리보기",
 "colors":{"g1":"#1A2337","g2":"#22304D","g3":"#2F4166","gold":"#4FB287","goldl":"#9BD8BC",       # 표지(남색·초록)에 맞춤
           "glow":"rgba(46,125,91,.32)","edge":"rgba(79,178,135,.6)","lead":"#DCE2EC","toc":"#EEF1F6","foot":"#AEB8CB"},
}
RULE_LABELS=("사는 조건","파는 조건","계좌","대상","손절")

# ---------- 인용 박스 ----------
def _qlines(s):
    return [re.sub(r'^>\s?','',l) for l in s.splitlines()]

def _items(text):
    """‘ - a - b’ / ‘1. a 2. b’ 한 줄 목록을 항목으로. 반환: (항목들, 번호목록 여부)"""
    t=text.strip()
    if re.match(r'^\d+\.\s', t):
        parts=re.split(r'\s(?=\d{1,2}\.\s)', t); return [re.sub(r'^\d+\.\s*','',p).strip() for p in parts if p.strip()], True
    if t.startswith('- '):
        parts=re.split(r'(?:^|\s)-\s(?=\S)', t); return [p.strip() for p in parts if p.strip()], False
    return [], False

def _item(x):
    """‘**굵은 첫 문장** 나머지’ → (lead, rest) / 그 외 문자열."""
    m=re.match(r'^\*\*(.+?)\*\*\s*(.*)$', x.strip())
    return (clean(m.group(1)), clean(m.group(2))) if m else clean(x)

def _quotes(text):
    """“…” 여러 개가 붙은 단락 → 개별 프롬프트."""
    t=text.strip()
    if t.startswith('“'):
        qs=re.findall(r'“[^”]+”', t)
        if qs and len("".join(qs))>=len(t)-len(qs)*2-4: return [clean(q) for q in qs]
    return [clean(t)]

def _blockquote(s):
    """인용 블록 하나 → 요소 목록."""
    lines=_qlines(s); paras=[]; cur=[]
    for l in lines:
        if l.strip(): cur.append(l)
        elif cur: paras.append(" ".join(cur)); cur=[]
    if cur: paras.append(" ".join(cur))
    img=re.search(r'<img src="([^"]+)"', s)
    if img:
        name="b3_"+pathlib.Path(img.group(1)).stem
        IMG.mkdir(parents=True, exist_ok=True)
        src=IMGSRC/pathlib.Path(img.group(1)).name
        if src.exists(): shutil.copy(src, IMG/f"{name}.png")
        tag,cap="그림",""
        for p in paras:
            m=re.match(r'^\*\*(개념도|그림|사례)\*\*\s*(.*)$', p)
            if m: tag,cap=m.group(1),clean(m.group(2))
        return [('figure', name, cap, tag)]
    if len(paras)>1 and all(p.startswith('**') for p in paras):   # 한 인용 안의 라벨 박스 여러 개
        out=[]
        for p in paras: out+=_blockquote('> '+p)
        return out
    head=paras[0] if paras else ""
    m=re.match(r'^\*\*(.+?)\*\*:?\s*(.*)$', head)
    if m:
        label=clean(m.group(1)); rest=m.group(2)
        if label=="이 장의 핵심": return [('keysentence', clean(rest), '')]
        if label.startswith("더 깊이 보기"):
            items,ordered=_items(rest)
            return [('infobox','deep',label.replace(" | "," · "),[clean(i) for i in items] or [clean(rest)],ordered)]
        if label.startswith("따라 하기 전에"):
            items,_=_items(rest)
            return [('infobox','caution',label,[_item(i) for i in items] or [clean(rest)],False)]
        if label.startswith(RULE_LABELS):
            items,ordered=_items(rest)
            sec=(label, [clean(i) for i in items], ordered, "" if items else clean(rest))
            return [('rulecard',[sec])]
        if label=="배운 것": return [('infobox','learn',label,[clean(rest)],False)]
        return [('callout', label, clean(rest))]
    # 라벨 없는 인용: 프롬프트(“…”) / 표 출처 / 일반 메모
    if head.startswith('“'):
        items=[]
        for p in paras: items+=_quotes(p)
        return [('prompt', items, 'AI에게 이렇게 묻습니다')]
    if re.match(r'^\d{4}\s*~\s*\d{4}', head):
        return [('tnote', clean(head))]
    return [('infobox','note','',[clean(" ".join(paras))],False)]

def _is_quote(s): return s.lstrip().startswith('>')

# ---------- 본문 ----------
def _qchange(blocks):
    """‘질문을 바꿨습니다’ 소절: 예전 질문/바뀐 질문 + AI 프롬프트 + 나머지 문단."""
    out=[]; before=after=sit=""; plabel=None; rest=[]
    for b in blocks:
        s=b.strip()
        m=re.match(r'^예전에는\s*(.*?)\s*이렇게 물었습니다\.\s*(.+)$', s)
        if m and not before: sit=clean(m.group(1)); before=clean(m.group(2)); continue
        m=re.match(r'^이제는\s*(.*?)이렇게 묻습니다\.\s*(.+)$', s)
        if m and not after: after=clean(m.group(2)); continue
        if re.match(r'^AI에게(도|는)?\s.*(묻습니다|바꿨습니다)\.$', s) and plabel is None:
            plabel=clean(s).rstrip('.'); continue
        rest.append(b)
    if before and after: out.append(('qchange', sit, before, after))
    for b in rest:
        if _is_quote(b):
            for el in _blockquote(b):
                if el[0]=='prompt' and plabel: el=('prompt', el[1], plabel)
                out.append(el)
        else: out += _plain(b)
    return out

def _plain(b):
    s=b.strip()
    if not s: return []
    if _is_table(s):
        rows,hdr=_parse_table(s); return [('gtable', rows, hdr)]
    if re.fullmatch(r'\*\*[^*]+\*\*', s): return [('h3', clean(s))]
    if re.match(r'^[-*]\s+', s):
        return [('bullets',[clean(x) for x in re.findall(r'(?m)^[-*]\s+(.+)$',s)])]
    if re.match(r'^\d+\.\s', s):
        return [('numlist',[(n,clean(x)) for n,x in re.findall(r'(?m)^(\d+)\.\s+(.+)$',s)])]
    if _is_quote(s): return _blockquote(s)
    return [('para', clean(s), False)]

def _add(E, els):
    for el in els:
        if el[0]=='rulecard' and E and E[-1][0]=='rulecard':   # 연속 규칙 박스는 한 장의 카드로
            E[-1]=('rulecard', E[-1][1]+el[1]); continue
        E.append(el)

def _section(blocks, E, opener=None):
    """헤딩 단위로 순회하며 요소 생성(장/프롤로그/에필로그 공통)."""
    k=0; n=len(blocks)
    while k<n:
        s=blocks[k].strip()
        m=re.match(r'^###\s+(.+)', s)
        if m:
            label=clean(m.group(1)); body,k=_collect(blocks,k+1)
            if label=="질문을 바꿨습니다":
                E.append(('qhead', label)); _add(E, _qchange(body)); continue
            if label.startswith("카드") and body and _is_table(body[0].strip()):   # 부록 C 요약 카드
                rows,hdr=_parse_table(body[0].strip())
                if hdr and rows and rows[0][:2]==["항목","내용"]:
                    secs=[]
                    for r in rows[1:]:
                        v=r[1]
                        if re.search(r'[①-⑩]', v):
                            secs.append((r[0],[x.strip() for x in re.split(r'\s*[①-⑩]\s*', v) if x.strip()],True,""))
                        elif " / " in v: secs.append((r[0],[x.strip() for x in v.split(" / ")],False,""))
                        else: secs.append((r[0],[],False,v))
                    E.append(('rulecard', secs, label))
                    for b in body[1:]: _add(E, _plain(b))
                    continue
            # 빈 소제목, 또는 같은 라벨의 박스가 바로 이어지는 소제목은 생략(중복 방지)
            if not body or (_is_quote(body[0]) and clean(body[0]).lstrip('> ').startswith(label)): pass
            else: E.append(('h3', label))
            for b in body: _add(E, _plain(b))
            continue
        _add(E, _plain(s)); k+=1

def parse():
    md=SRC.read_text(encoding="utf-8")
    blocks=[b for b in split_blocks(md) if b.strip()]
    E=[('cover',), ('disclaimer', DISCLAIMER), ('toc',)]
    # 상위 구간 나누기: (종류, 제목, 블록들)
    segs=[]; cur=None
    for b in blocks:
        s=b.strip()
        if re.match(r'^#\s+[^#]', s) or re.match(r'^##\s+[^#]', s):
            h=re.sub(r'^#+\s*','',s).strip()
            lvl=1 if s.startswith('# ') else 2
            cur=[lvl, h, []]; segs.append(cur); continue
        if cur: cur[2].append(b)
    for lvl,h,body in segs:
        if h==TITLE or h=="일러두기": continue
        m=re.match(r'^(\d+)부\.\s*(.+)$', h)
        if lvl==1 and m:
            num=int(m.group(1))
            pre=[]
            for b in body: pre+=_plain(b)
            note=pre[0][1:] if len(pre)==1 and pre[0][0]=='callout' else None   # ‘N부를 읽기 전에’는 부 표지에
            E.append(('part', str(num), clean(m.group(2)), '', PART_SUM.get(num,''), note))
            if not note: _add(E, pre)
            continue
        if lvl==1 and h=="부록": continue
        m=re.match(r'^(\d+)장\.\s*(.+)$', h)
        if m:
            E.append(('chapter', int(m.group(1)), clean(m.group(2)), ''))
            _section(body, E); continue
        if h in ("프롤로그","에필로그"):
            sub=""
            if body and re.match(r'^###\s', body[0]): sub=clean(re.sub(r'^###\s*','',body[0])); body=body[1:]
            E.append(('h1big', 'prologue' if h=="프롤로그" else 'epilogue', sub, ''))
            _section(body, E); continue
        m=re.match(r'^부록\s*([A-Z])\.\s*(.+)$', h)
        if m:
            E.append(('h1big','appendix',f"부록 {m.group(1)} · {clean(m.group(2))}",''))
            _section(body, E); continue
        E.append(('h3', clean(h))); _section(body, E)
    E.append(('closing', KEYLINE))
    E.append(('authorbio', AUTHOR, AUTHOR_BIO))
    E.append(('colophon', [("제목",TITLE),("부제",SUBTITLE),("지은이",AUTHOR),
                           ("발행",f"{PROJECT} (자가출판)"),("발행일",PUBDATE),("문의",EMAIL)]))
    return E

if __name__=="__main__":
    from collections import Counter
    E=parse(); print(len(E), Counter(e[0] for e in E))
