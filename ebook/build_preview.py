#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 미리보기 생성기 ― content.parse() 요소를 HTML로 렌더 후 WeasyPrint로 PDF.
Word(book.docx)와 동일한 콘텐츠/디자인을 시각 확인하기 위한 용도.
산출물: ebook/build/preview.pdf
"""
import html, pathlib, re
from weasyprint import HTML
import os, importlib
C = importlib.import_module(os.environ.get('BOOK','content'))

ROOT=pathlib.Path(__file__).resolve().parent
ASSETS=ROOT/"assets"; BUILD=ROOT/"build"; BUILD.mkdir(exist_ok=True)
TOC=[]

def esc(s): return html.escape(s)

def opener_html(icon, eyebrow, title, anchor, subtitle=None, major=False):
    img=f'<img class="heroimg" src="build/img/hero_{icon}.png">' if icon else ''
    eb=f'<div class="ceyebrow">{esc(eyebrow)}</div>' if eyebrow else ''
    sub=f'<div class="csub">{esc(subtitle)}</div>' if subtitle else ''
    cls="chaptit major" if major else "chaptit"
    return (f'<section class="chapopen" id="{anchor}">{img}{eb}'
            f'<h2 class="{cls}">{esc(title)}</h2>{sub}</section>')

def first_sentence_split(text):
    # 따옴표가 끼지 않은 짧고 깔끔한 첫 문장만 도입문으로(없으면 None)
    m=re.match(r'^([^"“”]{6,38}?[.?!])\s*(.*)$', text, re.S)
    if m and len(m.group(1))<=38: return m.group(1), m.group(2)
    return None, text

def theme_css(T):
    """책별 색 테마(표지 색에 맞춘 포인트 색) — 공통 CSS 변수와 크림 배경을 덮어쓴다."""
    if not T: return ''
    return ('<style>:root{'+f'--navy:{T["navy"]};--navy2:{T["navy2"]};--accent:{T["accent"]};'
            f'--accentd:{T["accentd"]};--tint2:{T["tint2"]};--cream1:{T["cream1"]};--cream2:{T["cream2"]};--edge:{T["edge"]}'+'}'
            '.endnote,.partpage .pintro{background:linear-gradient(135deg,var(--cream1),var(--cream2))}'
            '.endnote{box-shadow:inset 0 0 0 1.5px var(--edge)}</style>')


# ── WeasyPrint는 word-break:keep-all을 무시하고 한글을 글자 사이에서 끊는다(69.0 확인).
#    한글이 든 어절(인라인 태그 포함)을 nowrap 묶음으로 감싸 단어 단위로만 줄을 바꾼다.
_INL = r"(?:strong|b|em|i|span|a|sup|sub|mark|u|small|code)"
_WORD = re.compile(r"(?:[^\s<]|<" + _INL + r"\b[^>]*>|</" + _INL + r">)+")
_HAN = re.compile(r"[\uac00-\ud7a3]")
def _wrap_word(m):
    w = m.group(0); plain = re.sub(r"<[^>]+>", "", w)
    if len(plain) > 12 and "<" not in w:                    # 긴 덩어리: 괄호·가운뎃점 자리에서만 줄바꿈 허용
        w2 = re.sub(r"(?<=[^\s(])(?=\()|(?<=[)ㆍ·])(?=[^\s)」』”’.,])", "\u200b", w)
        if len(plain) > 16 or not _HAN.search(plain):   # 조각마다 묶어 ZWSP 자리에서만 끊기게
            return "\u200b".join(f'<span class="kw">{s}</span>' if len(s) > 1 else s for s in w2.split("\u200b"))
    if not (_HAN.search(plain) or re.search(r"\d", plain)) or len(plain) < 2 or len(plain) > 16: return w
    opens = re.findall(r"<(" + _INL + r")\b", w); closes = re.findall(r"</(" + _INL + r")>", w)
    if opens != closes[::-1] or w.startswith("</") : return w          # 태그가 어절 밖으로 걸치면 그대로
    _K[0] += 1; k = _K[0]
    if k in _SPLIT and not opens and len(plain) >= 4:      # 벌어진 줄 다음 어절: 가운데서만 나눌 수 있게(앞뒤 2음절은 묶음)
        cut = [i for i in range(2, len(w) - 1) if _HAN.match(w[i]) and (_HAN.match(w[i-1]) or w[i-1].isdigit())]   # 음절 사이만, 앞뒤 2자 이상
        han = lambda s: len(_HAN.findall(s))
        cut = [i for i in cut if (han(w[:i]) >= 2 or re.search(r"\d", w[:i])) and han(w[i:]) >= 2   # 앞은 2음절 이상(숫자 덩어리 허용)
               and not (han(w[i:]) <= 3 and re.search(r"[.?!]", w[i:]))]   # 문장 끝 어미('니다.')만 넘기지 않는다
        punct = [i for i in range(1, len(w)) if w[i-1] in "·ㆍ)/" and w[i] not in ")」』”’.,"]
        if punct: cut = punct                                 # 가운뎃점·괄호 뒤가 있으면 그 자리에서만
        if not cut: return f'<span class="kw" data-k="{k}">' + w + '</span>'
        segs = [w[a:b] for a, b in zip([0] + cut, cut + [len(w)])]
        return "\u200b".join(f'<span class="kw">{s}</span>' for s in segs)
    return f'<span class="kw" data-k="{k}">' + w + '</span>'
_K = [0]; _SPLIT = set()
def loose_next_words(doc, limit=0.7):
    """양끝맞춤으로 단어 사이가 limit em 넘게 벌어진 줄을 찾아, 다음 줄 첫 어절의 data-k를 돌려준다."""
    found = set()
    def tbs(b, out):
        if type(b).__name__ == "TextBox": out.append(b)
        for c in getattr(b, "children", []) or []: tbs(c, out)
    def first_k(b):
        el = getattr(b, "element", None)
        if el is not None and el.get("data-k"): return int(el.get("data-k"))
        for c in getattr(b, "children", []) or []:
            r = first_k(c)
            if r is not None: return r
        return None
    def walk(b):
        ls = [c for c in (getattr(b, "children", []) or []) if type(c).__name__ == "LineBox"]
        for a, nxt in zip(ls, ls[1:]):
            tb = []; tbs(a, tb)
            if not tb: continue
            js = max((getattr(x, "justification_spacing", 0) or 0) for x in tb)
            if js > limit * tb[0].style["font_size"]:
                k = first_k(nxt)
                if k is not None: found.add(k)
        for c in getattr(b, "children", []) or []:
            if type(c).__name__ != "LineBox": walk(c)
    for pg in doc.pages: walk(pg._page_box)
    return found
def keep_words(body):
    out = []; skip = 0
    for part in re.split(r"(<svg\b.*?</svg>|<style\b.*?</style>|<script\b.*?</script>)", body, flags=re.S):
        if part.startswith(("<svg", "<style", "<script")): out.append(part); continue
        # 태그 밖 텍스트 + 인라인 태그 묶음만 대상. 블록 태그는 _WORD에 안 걸린다.
        out.append(re.sub(r"(?<=>)([^<]*(?:<" + _INL + r"\b[^>]*>[^<]*|</" + _INL + r">[^<]*)*)", lambda m: _WORD.sub(_wrap_word, m.group(1)), part))
    return "".join(out)

def render(write=True):
    if not (BUILD/"img"/"heart.png").exists():
        import make_assets; make_assets.build()
    parts=[]
    for el in C.parse():
        t=el[0]
        if t=='cover':
            parts.append(f'<section class="coverpage" style="background-image:url(build/img/{C.COVER})"></section>')
        elif t=='disclaimer':
            items="".join(f"<p>{esc(d)}</p>" for d in el[1])
            parts.append(f'<section class="frontmatter"><h2 class="plain">일러두기</h2>'
                         f'<div class="disclaimer"><span class="tag">DISCLAIMER</span>{items}</div>'
                         f'<p class="readkey">{esc(getattr(C,"READKEY","이 책의 핵심은 종목명이 아니라 ‘질문의 구조’입니다."))}</p>'
                         f'<p class="readguide">{esc(getattr(C,"READGUIDE","이 책은 순서대로 읽어도 좋지만, 6부와 부록은 필요할 때 다시 꺼내보는 실전 노트처럼 활용하셔도 좋습니다."))}</p></section>')
        elif t=='toc':
            parts.append("<!--TOC-->")
        elif t=='part':
            anchor=f"part{el[1]}"; TOC.append(("part",anchor,f"{el[1]}부. {el[2]}"))
            icon=el[3] if len(el)>3 else ''; intro=el[4] if len(el)>4 else ''
            img=f'<img class="partimg" src="build/img/{icon}.png">' if icon else ''
            it=f'<p class="pintro">{esc(intro)}</p>' if intro else ''
            if len(el)>5 and el[5]:      # 부 표지 하단 안내(예: ‘3부를 읽기 전에’)
                it+=f'<div class="pnote"><span class="pnlabel">{esc(el[5][0])}</span>{esc(el[5][1])}</div>'
            ptitle=esc(el[2])
            if ", " in el[2] and len(el[2])>12: ptitle=ptitle.replace(", ",", <br>",1)   # 긴 부 제목은 쉼표에서 줄바꿈
            cls="partpage hasnote" if len(el)>5 and el[5] else "partpage"
            parts.append(f'<section class="{cls}" id="{anchor}">{img}'
                         f'<div class="pno">{esc(el[1])}부</div><h1 class="part">{ptitle}</h1>{it}</section>')
        elif t=='h1big':
            kind=el[1]; anchor=f"{kind}{len(TOC)}"; icon=el[3] if len(el)>3 else ''
            if kind=='prologue':
                TOC.append((kind,anchor,"프롤로그"))
                parts.append(opener_html(icon,"","프롤로그",anchor,subtitle=el[2],major=True))
            elif kind=='epilogue':
                TOC.append((kind,anchor,"에필로그"))
                parts.append(opener_html(icon,"","에필로그",anchor,subtitle=el[2],major=True))
            else:
                TOC.append((kind,anchor,el[2]))
                parts.append(opener_html(icon,"APPENDIX",el[2],anchor,major=True))
        elif t=='chapter':
            anchor=f"ch{el[1]}"; icon=el[3] if len(el)>3 else ''
            TOC.append(("chapter",anchor,f"{el[1]}장. {el[2]}"))
            parts.append(opener_html(icon, f"CHAPTER {el[1]}", f"{el[1]}장. {el[2]}", anchor))
        elif t=='keysentence':
            parts.append(f'<div class="keybox"><div class="ktext"><span class="klabel">이 장의 핵심</span>'
                         f'<p>{esc(el[1])}</p></div></div>')
        elif t=='ornament':
            parts.append('<div class="ornament"><img src="build/img/ornament.png"></div>')
        elif t=='figure':
            tag=el[3] if len(el)>3 and el[3] else "개념도"
            cap=(f'<figcaption><span class="figtag">{esc(tag)}</span>{esc(el[2])}</figcaption>'
                 if len(el)>2 and el[2] else '')
            sc=getattr(C,"FIG_SCALE",{}).get(el[1])
            st=f' style="max-width:{118*sc:.0f}mm"' if sc else ''
            parts.append(f'<figure class="cfig"><img src="build/img/{el[1]}.png"{st}>{cap}</figure>')
        elif t=='callout':
            parts.append(f'<div class="callout"><p class="ctitle">{esc(el[1])}</p><p>{esc(el[2])}</p></div>')
        elif t=='compare':
            headers,rows,good_right=el[1],el[2],el[3]
            caption=el[4] if len(el)>4 else ''
            clsA,clsB=("col-bad","col-good") if good_right else ("col-good","col-bad")
            body="".join(f'<tr><td class="{clsA}">{esc(b)}</td><td class="{clsB}">{esc(c)}</td></tr>'
                         for a,b,c in rows)
            capt=f'<p class="tcap">{esc(caption)}</p>' if caption else ''
            parts.append(f'<table class="compare"><thead><tr><th>{esc(headers[1])}</th>'
                         f'<th>{esc(headers[2])}</th></tr></thead><tbody>{body}</tbody></table>{capt}')
        elif t=='gtable':
            rows,hdr=el[1],el[2]; twocol=all(len(r)==2 for r in rows)
            trs=[]
            for ri,row in enumerate(rows):
                cs=""
                for ci,c in enumerate(row):
                    if hdr and ri==0: cs+=f'<th class="hd">{esc(c)}</th>'
                    elif (not hdr) and twocol and ci==0: cs+=f'<th class="rl">{esc(c)}</th>'
                    else: cs+=f'<td>{esc(c)}</td>'
                trs.append(f'<tr>{cs}</tr>')
            dense=" dense" if len(rows)>=8 else ""          # 긴 표는 촘촘하게(책별 CSS에서만 적용)
            parts.append(f'<table class="gtbl{dense}">{"".join(trs)}</table>')
        elif t=='cards':
            body="".join(f'<div class="card"><span class="cidx">{i}</span><h4>{esc(x[0])}</h4>'
                         f'<p>{esc(x[1])}</p></div>' for i,x in enumerate(el[1],1))
            parts.append(f'<div class="cardgrid">{body}</div>')
        elif t=='modebar':
            body="".join(f'<div class="mode"><b>{esc(n)}</b>{esc(d)}</div>' for n,d in el[1])
            parts.append(f'<div class="modebar">{body}</div>')
        elif t=='flow':
            body="".join(f'<div class="step"><div class="dot">{i}</div><div class="body">'
                         f'<h4>{esc(x[0])}</h4><p>{esc(x[1])}</p></div></div>' for i,x in enumerate(el[1],1))
            parts.append(f'<div class="flow">{body}</div>')
        elif t=='dodont':
            label,items,kind=el[1],el[2],el[3]; mark="✕" if kind=="dont" else "✓"
            lis="".join(f'<li><span class="qnum">{mark}</span>{esc(a)} — <span class="fillline">{esc(b)}</span></li>'
                        for a,b in items)
            parts.append(f'<div class="{kind}"><span class="lbl">{esc(label)}</span>'
                         f'<ul class="checklist" style="margin:0">{lis}</ul></div>')
        elif t=='pullquote':
            parts.append(f'<blockquote class="pull"><p>{esc(el[1])}</p></blockquote>')
        elif t=='endnote':
            lines=el[1] if isinstance(el[1],(list,tuple)) else [el[1]]
            lis="".join(f'<li>{esc(s)}</li>' for s in lines)
            parts.append(f'<div class="endnote"><span class="enlabel">이 장의 정리</span><ol>{lis}</ol></div>')
        elif t=='writeline':
            parts.append('<div class="writeline"></div>')
        elif t=='closing':
            parts.append(f'<div class="closing"><img src="build/img/ornament.png">'
                         f'<p>{esc(el[1])}</p></div>')
        elif t=='authorbio':
            parts.append(f'<section class="authorbio"><h2 class="plain">지은이</h2>'
                         f'<div class="abname">{esc(el[1])}</div><p>{esc(el[2])}</p></section>')
        elif t=='colophon':
            rows="".join(f'<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>' for k,v in el[1])
            parts.append(f'<section class="colophon"><div class="ctitle">{esc(C.TITLE)}</div>'
                         f'<table class="coltbl">{rows}</table>'
                         f'<p class="crights">© {esc(C.AUTHOR)}. 이 책의 저작권은 지은이에게 있으며, '
                         f'무단 복제·전재·배포를 금합니다.</p>'
                         f'<p class="cnote">본 전자책은 특정 종목의 매수·매도 권유나 수익 보장을 위한 것이 아니며, '
                         f'투자 교육·실전 기록을 목적으로 합니다. 투자의 최종 판단과 책임은 독자 본인에게 있습니다.</p></section>')
        elif t=='apxnote':
            parts.append(f'<div class="apxnote"><span class="anlabel">사용법</span>{esc(el[1])}</div>')
        elif t=='h3': parts.append(f'<h3>{esc(el[1])}</h3>')
        elif t=='para':
            if len(el)>2 and el[2] and el[1]:   # 장 첫 문단: 짧고 깔끔한 첫 문장만 굵게
                lead,rest=first_sentence_split(el[1])
                if lead:
                    parts.append(f'<p class="leadp"><strong class="lead">{esc(lead)}</strong> {esc(rest)}</p>')
                else:
                    parts.append(f'<p>{esc(el[1])}</p>')
            else:
                parts.append(f'<p>{esc(el[1])}</p>')
        elif t=='bullets':
            parts.append('<ul class="bullets">'+''.join(f'<li>{esc(x)}</li>' for x in el[1])+'</ul>')
        elif t=='numlist':
            lis="".join(f'<li><span class="ln">{esc(str(num))}.</span> {esc(x)}</li>' for num,x in el[1])
            parts.append(f'<ul class="numlist">{lis}</ul>')
        elif t=='cat':
            parts.append(f'<p class="apx-cat"><span>{esc(el[1])}</span>{esc(el[2])}</p>')
        elif t=='q':
            qmode,num,text=el[1],el[2],el[3]
            badge=f'<span class="qnum">Q{num}</span>' if qmode else f'<span class="qnum">{num}.</span>'
            parts.append(f'<p class="apx-q">{badge}{esc(text)}</p>')
        elif t=='prompt':
            label=el[2] if len(el)>2 and el[2] else "붙여넣을 프롬프트"
            if isinstance(el[1],(list,tuple)):
                body='<ul class="plist">'+"".join(f'<li>{esc(x)}</li>' for x in el[1])+'</ul>'
            else: body=esc(el[1])
            parts.append(f'<div class="prompt"><span class="ptag">{esc(label)}</span>{body}</div>')
        elif t=='infobox':
            kind,label,items,ordered=el[1],el[2],el[3],el[4]
            lis=[]
            for x in items:
                lis.append(f'<li><b>{esc(x[0])}</b> {esc(x[1])}</li>' if isinstance(x,tuple) else f'<li>{esc(x)}</li>')
            if len(items)==1 and not isinstance(items[0],tuple) and kind in ('learn','note'):
                body=f'<p>{esc(items[0])}</p>'
            else:
                tag='ol' if ordered else 'ul'; body=f'<{tag}>{"".join(lis)}</{tag}>'
            lb=f'<span class="iblabel">{esc(label)}</span>' if label else ''
            parts.append(f'<div class="infobox ib-{kind}">{lb}{body}</div>')
        elif t=='rulecard':
            secs=[]
            for label,items,ordered,text in el[1]:
                main,_,sub=label.partition(" (")
                sub=f'<small>({esc(sub)}</small>' if sub else ''
                if items:
                    tag='ol' if ordered else 'ul'; body=f'<{tag}>'+"".join(f'<li>{esc(x)}</li>' for x in items)+f'</{tag}>'
                else: body=f'<p>{esc(text)}</p>'
                secs.append(f'<div class="rc-sec"><div class="rc-lbl"><span>{esc(main)}</span>{sub}</div>{body}</div>')
            head=el[2] if len(el)>2 and el[2] else "규칙 카드"
            parts.append(f'<div class="rulecard"><div class="rc-head">{esc(head)}</div>{"".join(secs)}</div>')
        elif t=='qhead':
            parts.append(f'<h3 class="qhead"><span class="qh-eb">이 장을 마치며</span>{esc(el[1])}</h3>')
        elif t=='qchange':
            sit=f'<div class="qsit">{esc(el[1])}</div>' if el[1] else ''
            parts.append(f'<div class="qchange">{sit}'
                         f'<div class="qrow qold"><span class="qtag">예전 질문</span><p>{esc(el[2])}</p></div>'
                         f'<div class="qarrow">↓</div>'
                         f'<div class="qrow qnew"><span class="qtag">바뀐 질문</span><p>{esc(el[3])}</p></div></div>')
        elif t=='tnote':
            parts.append(f'<p class="tnote">자료 · {esc(el[1])}</p>')
        elif t=='fill':
            parts.append(f'<p class="fillline">{esc(el[1])}<span class="fillrule" style="display:block"></span></p>')
    body="\n".join(parts)

    # 목차 생성
    rows=[]
    for kind,anchor,label in TOC:
        if kind=="part":
            num,_,rest=label.partition(". ")
            rows.append(f'<div class="tpart"><span class="pno">{esc(num)}</span>{esc(rest)}</div>')
        else:
            rows.append(f'<li><a href="#{anchor}"><span class="t">{esc(label)}</span><span class="dots"></span></a></li>')
    toc=f'<section class="toc"><h2 class="plain">차례</h2><ol>{"".join(rows)}</ol></section>'
    body=body.replace("<!--TOC-->", toc)

    body=re.sub(r'<table class="gtbl([^"]*)"(.*?)</table>', lambda m: f'<table class="gtbl{m.group(1)}{" long" if m.group(0).count("<tr")>=7 else ""}"'+m.group(2)+'</table>', body, flags=re.S)
    raw_body=body; _SPLIT.clear(); _K[0]=0; body=keep_words(raw_body)
    css=(ASSETS/"preview.css").read_text(encoding="utf-8")+".kw{white-space:nowrap}"
    meta=(f'<title>{esc(C.TITLE)}</title>'
          f'<meta name="author" content="{esc(C.AUTHOR)}">'
          f'<meta name="description" content="{esc(getattr(C,"DESCRIPTION","AI 투자 루틴과 개인투자자의 판단 구조화 기록 — "+C.SUBTITLE))}">'
          f'<meta name="keywords" content="{esc(", ".join(getattr(C,"KEYWORDS",["AI 투자","주식투자","투자 루틴","섹터 분석","포트폴리오","개인투자자","챗GPT 주식","AI 종목분석"])))}">')
    over=(f'<style>body{{font-size:{C.FONT_PT}pt;line-height:{getattr(C,"LINE",1.78)}}} '
          f'p{{margin-bottom:{getattr(C,"PARA_EM",0.82)}em}}</style>') if hasattr(C,'FONT_PT') else ''
    over+=theme_css(getattr(C,"THEME",None))
    over+=f'<style>{C.EXTRA_CSS}</style>' if getattr(C,'EXTRA_CSS','') else ''
    doc=f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">{meta}<style>{css}</style>{over}</head><body>{body}</body></html>'
    (BUILD/(C.OUTBASE_PREVIEW if hasattr(C,"OUTBASE_PREVIEW") else "preview.html")).write_text(doc,encoding="utf-8")
    head_=doc[:doc.index("<body>")]
    for _ in range(4):                                       # 벌어진 줄 보정: 다음 어절을 나눠 다시 조판
        rd=HTML(string=doc,base_url=str(ROOT)).render()
        new=loose_next_words(rd)-_SPLIT
        if not new: break
        _SPLIT.update(new); _K[0]=0
        doc=head_+"<body>"+keep_words(raw_body)+"</body></html>"
    print(f"[ok] 줄 간격 보정 어절 {len(_SPLIT)}개")
    (BUILD/(C.OUTBASE_PREVIEW if hasattr(C,"OUTBASE_PREVIEW") else "preview.html")).write_text(doc,encoding="utf-8")
    if write:
        (rd if not new else HTML(string=doc,base_url=str(ROOT)).render()).write_pdf(str(BUILD/C.PDF_OUT))
        print("[ok] preview PDF →", BUILD/C.PDF_OUT)
    return doc

if __name__=="__main__": render()
