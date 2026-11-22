# -*- coding: utf-8 -*-
"""출간 전 게이트 — 유페이퍼 거절 2회의 원인을 기계적으로 막는다.
사용: python3 .claude/skills/hochacha-ebook/scripts/check_publish.py <book번호 2|3|4> [--ebook-dir ebook]
검사: EPUB 2.0 · EPUBCheck 오류 0 · 판권(도서명/저자명/출판사명/발행일 YYYY년 M월 D일/가격 N원)이 PDF 마지막 쪽과 EPUB에 모두 ·
      표지 생성기에 출판사명 · 등록정보.md 가격·발행일·제목 일치 · PDF 쪽 크기 동일·빈 쪽 없음·첫 쪽 표지·책갈피.
종료 코드 0 = 통과, 1 = 실패(항목 출력)."""
import sys, re, zipfile, subprocess, importlib, pathlib, argparse

ap = argparse.ArgumentParser(); ap.add_argument("book"); ap.add_argument("--ebook-dir", default="ebook")
a = ap.parse_args()
ROOT = pathlib.Path(a.ebook_dir).resolve(); sys.path.insert(0, str(ROOT))
C = importlib.import_module(f"content{a.book}")
fails, oks = [], []
def check(cond, ok, bad): (oks if cond else fails).append(ok if cond else bad)

price = getattr(C, "PRICE", ""); pub = getattr(C, "PUBLISHER", ""); date_ko = getattr(C, "PUBDATE_KO", "")
check(pub == "유페이퍼" or (pub and pub != C.AUTHOR), f"출판사명: {pub}", "PUBLISHER 미설정 또는 저자명과 같음(개인은 '유페이퍼')")
check(re.fullmatch(r"\d{4}년 \d{1,2}월 \d{1,2}일", date_ko or ""), f"발행일 표기: {date_ko}", "PUBDATE_KO가 'YYYY년 M월 D일' 형식이 아님")
check(re.fullmatch(r"[\d,]+원", price or ""), f"가격 표기: {price}", "PRICE가 'N원' 형식이 아님")
need = [C.TITLE, C.AUTHOR, pub, date_ko, price, "발행일", "가격"]

# EPUB
epub = ROOT / "build" / C.EPUB_OUT
if epub.exists():
    z = zipfile.ZipFile(epub); opf = next(n for n in z.namelist() if n.endswith(".opf"))
    o = z.read(opf).decode("utf-8")
    check('version="2.0"' in o, "EPUB 2.0", "EPUB 버전이 2.0이 아님(유페이퍼는 3.0 등록거부)")
    check(f"<dc:publisher>{pub}</dc:publisher>" in o, "EPUB 출판사 메타데이터", "dc:publisher가 판권 출판사명과 다름")
    allx = " ".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith((".xhtml", ".html")))
    miss = [t for t in need if t and t not in allx]
    check(not miss, "EPUB 판권 항목", f"EPUB 판권에 없음: {miss}")
    r = subprocess.run(["epubcheck", str(epub)], capture_output=True, text=True)
    check(r.returncode == 0, "EPUBCheck 오류 0", "EPUBCheck 오류: " + " / ".join(l for l in (r.stdout + r.stderr).splitlines() if "ERROR" in l or "FATAL" in l)[:400])
else:
    fails.append(f"EPUB 없음: {epub}")

# PDF
pdf = ROOT / "build" / C.PDF_OUT
if pdf.exists():
    import pypdf
    rd = pypdf.PdfReader(str(pdf)); n = len(rd.pages)
    sizes = {(round(float(p.mediabox.width)), round(float(p.mediabox.height))) for p in rd.pages}
    check(len(sizes) == 1, f"PDF {n}쪽, 쪽 크기 동일 {sizes}", f"쪽 크기가 섞임: {sizes}")
    last = " ".join((rd.pages[-1].extract_text() or "").split())
    miss = [t for t in need if t and t not in last]
    check(not miss, "PDF 마지막 쪽 판권", f"PDF 마지막 쪽 판권에 없음: {miss}")
    check(bool(rd.pages[0].images), "PDF 첫 쪽 표지 이미지", "PDF 첫 쪽에 표지 이미지가 없음")
    check(len(rd.outline) > 1, f"PDF 책갈피 {len(rd.outline)}개", "PDF 책갈피(목차) 없음")
    blank = [i + 1 for i, p in enumerate(rd.pages) if not (p.extract_text() or "").strip() and not p.images]
    check(len(blank) < 2, "빈 쪽 2개 미만", f"빈 쪽 {blank}")
else:
    fails.append(f"PDF 없음: {pdf}")

# 표지·등록정보
cov = ROOT / f"cover{a.book}.py"
if cov.exists():
    check(pub in cov.read_text(encoding="utf-8"), "표지에 출판사명", f"표지 생성기({cov.name})에 '{pub}' 문구 없음")
reg = ROOT / "publish" / f"book{a.book}" / "등록정보.md"
if reg.exists():
    t = reg.read_text(encoding="utf-8")
    for want in (C.TITLE, price, getattr(C, "PUBDATE", "")):
        check(want in t, f"등록정보에 '{want}'", f"등록정보.md에 '{want}' 없음(판권과 불일치 위험)")

for s in oks: print("  ✓", s)
for s in fails: print("  ✗", s)
print("통과" if not fails else f"실패 {len(fails)}건"); sys.exit(1 if fails else 0)
