#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EPUB(서점 유통용) 생성 — content.parse() → 리플로우 XHTML → pandoc EPUB.
표지 이미지·메타데이터·내비게이션 포함. 산출: build/book.epub"""
import html, pathlib, subprocess, datetime
import os, importlib
C = importlib.import_module(os.environ.get('BOOK','content'))

ROOT=pathlib.Path(__file__).resolve().parent
ASSETS=ROOT/"assets"; BUILD=ROOT/"build"; IMG=BUILD/"img"
def esc(s): return html.escape(str(s))
def imgp(name): return str(IMG/f"{name}.png")

def render_elements():
    out=[]
    for el in C.parse():
        t=el[0]
        if t in ('cover','toc'): continue
        if t=='disclaimer':
            items="".join(f"<p>{esc(d)}</p>" for d in el[1])
            out.append(f'<h1>일러두기</h1><div class="disclaimer"><span class="tag">DISCLAIMER</span>{items}</div>'
                       f'<p class="readkey">{getattr(C,"READKEY","이 책의 핵심은 종목명이 아니라 ‘질문의 구조’입니다.")}</p>'
                       f'<p class="readguide">{getattr(C,"READGUIDE","이 책은 순서대로 읽어도 좋지만, 6부와 부록은 필요할 때 다시 꺼내보는 실전 노트처럼 활용하셔도 좋습니다.")}</p>')
        elif t=='part':
            ic=f'<img class="partimg" src="{imgp(el[3])}"/>' if len(el)>3 and el[3] else ''
            intro=f'<p class="pintro">{esc(el[4])}</p>' if len(el)>4 and el[4] else ''
            note=(f'<div class="pnote"><p class="pnlabel">{esc(el[5][0])}</p><p>{esc(el[5][1])}</p></div>'
                  if len(el)>5 and el[5] else '')
            out.append(f'{ic}<h1><span class="pno">{esc(el[1])}부</span> {esc(el[2])}</h1>{intro}{note}')
        elif t=='h1big':
            kind=el[1]; ic=f'<img class="heroimg" src="{imgp(el[3])}"/>' if len(el)>3 and el[3] else ''
            if kind=='prologue': out.append(f'{ic}<h1>프롤로그</h1><p class="csub">{esc(el[2])}</p>')
            elif kind=='epilogue': out.append(f'{ic}<h1>에필로그</h1>')
            else: out.append(f'{ic}<h1>{esc(el[2])}</h1>')
        elif t=='chapter':
            ic=f'<img class="heroimg" src="{imgp(el[3])}"/>' if len(el)>3 and el[3] else ''
            out.append(f'{ic}<h2>{esc(el[1])}장. {esc(el[2])}</h2>')
        elif t=='keysentence':
            out.append(f'<div class="keybox"><span class="klabel">이 장의 핵심</span><p>{esc(el[1])}</p></div>')
        elif t=='callout':
            out.append(f'<div class="callout"><p class="ctitle">● {esc(el[1])}</p><p>{esc(el[2])}</p></div>')
        elif t=='figure':
            tag=el[3] if len(el)>3 and el[3] else "개념도"
            cap=(f'<figcaption><span class="figtag">{esc(tag)}</span>{esc(el[2])}</figcaption>' if len(el)>2 and el[2] else '')
            alt=esc(f"{tag}: {el[2]}" if len(el)>2 and el[2] else tag)   # 대체텍스트(접근성)
            out.append(f'<figure class="cfig"><img src="{imgp(el[1])}" alt="{alt}"/>{cap}</figure>')
        elif t=='compare':
            h,rows,gr=el[1],el[2],el[3]; cap=el[4] if len(el)>4 else ''
            ca,cb=("col-bad","col-good") if gr else ("col-good","col-bad")
            body="".join(f'<tr><td class="{ca}">{esc(a)}</td><td class="{cb}">{esc(b)}</td></tr>' for _,a,b in rows)
            cp=f'<p class="tcap">→ {esc(cap)}</p>' if cap else ''
            out.append(f'<table class="compare"><tr><th>{esc(h[1])}</th><th>{esc(h[2])}</th></tr>{body}</table>{cp}')
        elif t=='gtable':
            rows,hdr=el[1],el[2]; twocol=all(len(r)==2 for r in rows); trs=[]
            for ri,row in enumerate(rows):
                cs=""
                for ci,c in enumerate(row):
                    if hdr and ri==0: cs+=f'<th class="hd">{esc(c)}</th>'
                    elif (not hdr) and twocol and ci==0: cs+=f'<th class="rl">{esc(c)}</th>'
                    else: cs+=f'<td>{esc(c)}</td>'
                trs.append(f'<tr>{cs}</tr>')
            out.append(f'<table class="gtbl">{"".join(trs)}</table>')
        elif t=='cards':
            cards="".join(f'<div class="card"><span class="cidx">{i}</span><h4>{esc(x[0])}</h4><p>{esc(x[1])}</p></div>'
                          for i,x in enumerate(el[1],1))
            out.append(f'<div class="cardgrid">{cards}</div>')
        elif t=='modebar':
            lis="".join(f'<li><b>{esc(n)}</b> {esc(d)}</li>' for n,d in el[1])
            out.append(f'<ul class="modebar">{lis}</ul>')
        elif t=='flow':
            lis="".join(f'<li><b>{esc(a)}</b> — {esc(b)}</li>' for a,b in el[1])
            out.append(f'<ol class="flow">{lis}</ol>')
        elif t=='dodont':
            label,items,kind=el[1],el[2],el[3]
            lis="".join(f'<li><b>{esc(a)}</b> — {esc(b)}</li>' for a,b in items)
            out.append(f'<div class="{kind}"><span class="lbl">{esc(label)}</span><ul>{lis}</ul></div>')
        elif t=='pullquote':
            out.append(f'<blockquote class="pull"><p>{esc(el[1])}</p></blockquote>')
        elif t=='endnote':
            lines=el[1] if isinstance(el[1],(list,tuple)) else [el[1]]
            lis="".join(f'<li>{esc(s)}</li>' for s in lines)
            out.append(f'<div class="endnote"><span class="enlabel">이 장의 정리</span><ol>{lis}</ol></div>')
        elif t=='ornament': out.append('<p class="ornament">✦</p>')
        elif t=='h3': out.append(f'<h3>{esc(el[1])}</h3>')
        elif t=='para': out.append(f'<p>{esc(el[1])}</p>')
        elif t=='bullets':
            out.append('<ul>'+''.join(f'<li>{esc(x)}</li>' for x in el[1])+'</ul>')
        elif t=='numlist':
            lis="".join(f'<li><span class="ln">{esc(n)}.</span>{esc(x)}</li>' for n,x in el[1])
            out.append(f'<ul class="numlist">{lis}</ul>')
        elif t=='cat':
            out.append(f'<p class="apx-cat"><span>{esc(el[1])}</span>{esc(el[2])}</p>')
        elif t=='q':
            qmode,num,text=el[1],el[2],el[3]
            badge=f'<span class="qnum">Q{esc(num)}</span>' if qmode else f'<span class="qnum">{esc(num)}.</span>'
            out.append(f'<p class="apx-q">{badge}{esc(text)}</p>')
        elif t=='prompt':
            label=el[2] if len(el)>2 and el[2] else "붙여넣을 프롬프트"
            body=('<ul class="plist">'+"".join(f'<li>{esc(x)}</li>' for x in el[1])+'</ul>'
                  if isinstance(el[1],(list,tuple)) else esc(el[1]))
            out.append(f'<div class="prompt"><span class="ptag">{esc(label)}</span>{body}</div>')
        elif t=='infobox':
            kind,label,items,ordered=el[1],el[2],el[3],el[4]
            if len(items)==1 and not isinstance(items[0],tuple) and kind in ('learn','note'):
                body=f'<p>{esc(items[0])}</p>'
            else:
                lis="".join(f'<li><b>{esc(x[0])}</b> {esc(x[1])}</li>' if isinstance(x,tuple) else f'<li>{esc(x)}</li>' for x in items)
                tg='ol' if ordered else 'ul'; body=f'<{tg}>{lis}</{tg}>'
            lb=f'<p class="iblabel">{esc(label)}</p>' if label else ''
            out.append(f'<div class="infobox ib-{kind}">{lb}{body}</div>')
        elif t=='rulecard':
            head=el[2] if len(el)>2 and el[2] else "규칙 카드"; secs=[]
            for label,items,ordered,text in el[1]:
                main,_,sub=label.partition(" (")
                sub=f' <small>({esc(sub)}</small>' if sub else ''
                if items:
                    tg='ol' if ordered else 'ul'; body=f'<{tg}>'+"".join(f'<li>{esc(x)}</li>' for x in items)+f'</{tg}>'
                else: body=f'<p>{esc(text)}</p>'
                secs.append(f'<div class="rc-sec"><p class="rc-lbl"><b>{esc(main)}</b>{sub}</p>{body}</div>')
            out.append(f'<div class="rulecard"><p class="rc-head">{esc(head)}</p>{"".join(secs)}</div>')
        elif t=='qhead':
            out.append(f'<p class="qh-eb">이 장을 마치며</p><h3 class="qhead">{esc(el[1])}</h3>')
        elif t=='qchange':
            sit=f'<p class="qsit">{esc(el[1])}</p>' if el[1] else ''
            out.append(f'<div class="qchange">{sit}<p class="qold"><span class="qtag">예전 질문</span> {esc(el[2])}</p>'
                       f'<p class="qarrow">↓</p><p class="qnew"><span class="qtag">바뀐 질문</span> {esc(el[3])}</p></div>')
        elif t=='tnote': out.append(f'<p class="tnote">자료 · {esc(el[1])}</p>')
        elif t=='fill': out.append(f'<p class="fillline">{esc(el[1])}</p>')
        elif t=='writeline': out.append('<hr class="writeline"/>')
        elif t=='closing': out.append(f'<div class="closing"><p class="ornament">✦</p><p>{esc(el[1])}</p></div>')
        elif t=='authorbio':
            out.append(f'<h1>지은이</h1><div class="authorbio"><p class="abname">{esc(el[1])}</p><p>{esc(el[2])}</p></div>')
        elif t=='colophon':
            rows="".join(f'<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>' for k,v in el[1])
            out.append(f'<h1>판권</h1><section class="colophon"><table>{rows}</table>'
                       f'<p class="crights">© {esc(C.AUTHOR)}. 무단 복제·전재·배포를 금합니다.</p>'
                       f'<p class="cnote">본 전자책은 특정 종목의 매수·매도 권유나 수익 보장을 위한 것이 아니며, 투자 교육·실전 기록을 목적으로 합니다. 투자의 최종 판단과 책임은 독자 본인에게 있습니다.</p></section>')
    return "\n".join(out)

def theme_css():
    """책별 색 테마 — epub.css의 포인트 색(네이비·골드)을 표지 색으로 덮어쓴다."""
    T=C.THEME; f=BUILD/"_epub_theme.css"
    f.write_text(
        f"h1,h2,h3,.ctitle,.rc-lbl b,.qnew,.keybox p{{color:{T['navy']}}}\n"
        f".pno,.qh-eb,.qsit,.enlabel{{color:{T['accentd']}}}\n"
        f".keybox{{border-left-color:{T['accent']};background:{T['tint2']}}}\n"
        f".klabel,.figtag{{color:{T['accentd']}}}\n"
        f".pintro,.endnote,.qchange{{background:{T['cream1']};border-color:{T['edge']}}}\n"
        f".pintro{{border-top-color:{T['accent']}}}\n"
        f".endnote .enlabel,.qnew .qtag{{background:{T['accent']};color:#fff}}\n"
        f".rulecard{{border-color:{T['navy']}}} .rc-head{{background:{T['navy']}}}\n"
        f".ib-caution{{border-color:{T['accent']}}} .ib-caution .iblabel,.ib-learn .iblabel{{color:{T['accentd']}}}\n"
        f".ib-learn{{border-color:{T['accent']}}} .prompt .plist li:before{{color:{T['accent']}}}\n",
        encoding="utf-8")
    return f

def build():
    body=render_elements()
    doc=(f'<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" lang="ko"><head>'
         f'<meta charset="utf-8"/><title>{esc(C.TITLE)}</title></head><body>{body}</body></html>')
    src=BUILD/"_epub_body.html"; src.write_text(doc, encoding="utf-8")
    meta=BUILD/"_epub_meta.yaml"
    meta.write_text(
        "---\n"
        f'title: "{C.TITLE}"\n'
        f'subtitle: "{C.SUBTITLE}"\n'
        f'author: "{C.AUTHOR}"\n'
        "lang: ko\n"
        f'date: "{datetime.date.today().isoformat()}"\n'
        f'publisher: "{C.AUTHOR}"\n'
        f'rights: "© {C.AUTHOR}. 무단 복제·전재·배포 금지. 투자 교육·실전 기록 목적(투자 권유·수익 보장 아님)."\n'
        f'description: "{getattr(C,"DESCRIPTION","AI 투자 루틴과 개인투자자의 판단 구조화 기록 — "+C.SUBTITLE)}"\n'
        + "subject:\n"+"".join(f"  - {k}\n" for k in getattr(C,"KEYWORDS",["AI 투자","주식투자","투자 루틴","섹터 분석","포트폴리오","개인투자자"]))
        + "---\n", encoding="utf-8")
    out=BUILD/C.EPUB_OUT
    subprocess.run([
        "pandoc", str(src), "--metadata-file", str(meta), "-f","html","-t","epub3","-o",str(out),
        "--toc","--toc-depth=2","--split-level=1",
        "--css",str(ASSETS/"epub.css"),
        *(["--css",str(theme_css())] if getattr(C,"THEME",None) else []),
        "--epub-cover-image",str(IMG/C.COVER),
    ], check=True)
    print("[ok] EPUB →", out)

if __name__=="__main__": build()
