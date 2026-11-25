# -*- coding: utf-8 -*-
"""조판 감사 — build/preview.html(마지막 build_preview 결과)을 다시 조판해 검사한다.
사용: cd ebook && python3 tools/layout_audit.py
검사: ① 쪽 아래 25% 이상 빈 쪽(다음 쪽이 장/부 시작이 아닌데) ② 줄머리 금칙 부호 ③ 양끝맞춤으로 단어 사이가 0.8em 넘게 벌어진 줄
      ④ 1~4글자 꼬리줄(본문 문단) ⑤ 쪽 경계에 걸친 박스·그림."""
import pathlib, re, sys
from weasyprint import HTML
ROOT = pathlib.Path(__file__).resolve().parent.parent
doc = HTML(string=(ROOT / "build" / "preview.html").read_text(encoding="utf-8"), base_url=str(ROOT)).render()
P = doc.pages

def kids(b): return getattr(b, "children", []) or []
def bottom(b):
    best = 0
    for c in kids(b):
        n = type(c).__name__
        if n == "MarginBox": continue
        if n in ("LineBox", "TableRowBox", "ImageBox", "BlockReplacedBox"): best = max(best, c.position_y + c.margin_height())
        best = max(best, bottom(c))
    return best
def classes(b, acc, d=0):
    el = getattr(b, "element", None)
    if el is not None and el.get("class"): acc.add(el.get("class").split()[0])
    if d < 6:
        for c in kids(b): classes(c, acc, d + 1)
def texts(b, out):
    if type(b).__name__ == "TextBox": out.append(b)
    for c in kids(b): texts(c, out)

gaps, kinsoku, loose, tails, split = [], [], [], [], []
BAD = set(".,)]}」』”’!?:;·…%")
def walk(b, pg, seen):
    el = getattr(b, "element", None)
    if el is not None and el.tag in ("figure", "div") and (el.get("class") or "").split()[:1] and (el.get("class") or "").split()[0] in ("cfig", "prompt", "keybox", "callout", "endnote"):
        key = id(el); seen.setdefault(key, set()).add(pg)
    lines = [c for c in kids(b) if type(c).__name__ == "LineBox"]
    if lines and el is not None and el.tag in ("p", "li", "td", "th", "div"):
        lt = []
        for L in lines:
            tb = []; texts(L, tb); lt.append(("".join(x.text for x in tb), tb))
        for (prev, _), (cur, _) in zip(lt, lt[1:]):
            if cur.strip()[:1] in BAD: kinsoku.append((pg, prev.strip()[-10:] + " ⏎ " + cur.strip()[:10]))
        for s, tb in lt[:-1]:
            if not tb: continue
            js = max((getattr(x, "justification_spacing", 0) or 0) for x in tb)
            if js > 0.8 * tb[0].style["font_size"]: loose.append((pg, round(js / tb[0].style["font_size"], 2), s.strip()[:36]))
        if el.tag == "p" and len(lt) >= 2 and 0 < len(lt[-1][0].strip()) <= 4: tails.append((pg, lt[-2][0].strip()[-12:] + " ⏎ " + lt[-1][0].strip()))
    for c in kids(b):
        if type(c).__name__ != "LineBox": walk(c, pg, seen)

seen = {}
for i, p in enumerate(P, 1): walk(p._page_box, i, seen)
split = sorted(min(v) for v in seen.values() if len(v) > 1)
for i, p in enumerate(P[:-1]):
    pb = p._page_box; frac = 1 - (bottom(pb) - pb.content_box_y()) / pb.height
    acc = set(); classes(P[i + 1]._page_box, acc)
    if frac > 0.25 and not ({"chapopen", "partpage", "authorbio", "colophon", "toc", "coverpage"} & acc) and i > 1:
        gaps.append((i + 1, f"{frac:.0%}"))
print(f"PAGES {len(P)}")
for name, v in [("쪽 아래 25%+ 빈 쪽", gaps), ("쪽을 넘는 박스·그림(시작 쪽)", split), ("줄머리 금칙", kinsoku), ("벌어진 줄(>0.8em)", loose), ("꼬리줄(≤4자)", tails)]:
    print(f"== {name}: {len(v)}")
    for x in v[:40]: print("  ", x)
