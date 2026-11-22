# -*- coding: utf-8 -*-
"""OpenDART 공식 API 도우미 — 4권 사례 공시 수집용.
인증키는 저장소에 두지 않는다: 환경변수 OPENDART_KEY 또는 ~/.config/hochacha/opendart_key(권한 600).

사용:
  python3 tools/opendart.py find 삼성전자                 # 회사 고유번호(corp_code) 찾기
  python3 tools/opendart.py list <corp_code> 20250101 20251231 [B]   # 공시 목록(유형 A 정기 B 주요사항 C 발행 D 지분 E 기타 F 감사 I 거래소)
  python3 tools/opendart.py doc <rcept_no>                # 공시 원문(zip) 내려받아 텍스트로 저장
"""
import io, json, os, pathlib, re, sys, urllib.parse, urllib.request, zipfile

BASE = "https://opendart.fss.or.kr/api/"
CACHE = pathlib.Path(__file__).resolve().parent.parent / "build" / "opendart"; CACHE.mkdir(parents=True, exist_ok=True)

def key():
    k = os.environ.get("OPENDART_KEY") or (pathlib.Path.home() / ".config/hochacha/opendart_key").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", k): sys.exit("OpenDART 인증키 형식이 아님")
    return k

def get(path, **params):
    params["crtfc_key"] = key()
    with urllib.request.urlopen(BASE + path + "?" + urllib.parse.urlencode(params), timeout=60) as r:
        return r.read()

def api(path, **params):
    d = json.loads(get(path, **params))
    if d.get("status") not in ("000", "013"):        # 013 = 조회된 데이터 없음
        raise RuntimeError(f"OpenDART {d.get('status')}: {d.get('message')}")
    return d

def corp_codes():
    f = CACHE / "corpCode.xml"
    if not f.exists():
        z = zipfile.ZipFile(io.BytesIO(get("corpCode.xml"))); f.write_bytes(z.read(z.namelist()[0]))
    t = f.read_text(encoding="utf-8")
    return re.findall(r"<corp_code>(\d+)</corp_code>\s*<corp_name>([^<]+)</corp_name>.*?<stock_code>([^<]*)</stock_code>", t, re.S)

def find(name):
    return [(c, n, s.strip()) for c, n, s in corp_codes() if name in n and s.strip()]

def disclosures(corp_code, bgn, end, ty=None):
    out, page = [], 1
    while True:
        p = dict(corp_code=corp_code, bgn_de=bgn, end_de=end, page_no=page, page_count=100)
        if ty: p["pblntf_ty"] = ty
        d = api("list.json", **p); out += d.get("list", [])
        if page >= int(d.get("total_page", 1) or 1): return out
        page += 1

def document(rcept_no):
    """공시 원문 zip → 태그를 걷어낸 텍스트 파일(build/opendart/<rcept_no>.txt)."""
    z = zipfile.ZipFile(io.BytesIO(get("document.xml", rcept_no=rcept_no)))
    txt = []
    for n in z.namelist():
        raw = z.read(n).decode("utf-8", "replace")
        raw = re.sub(r"</(P|TR|TITLE|SECTION-\d)>", "\n", raw)
        raw = re.sub(r"</T[DHU]>", " | ", raw)
        txt.append(re.sub(r"<[^>]+>", "", raw))
    out = CACHE / f"{rcept_no}.txt"; out.write_text("\n".join(txt), encoding="utf-8")
    return out

if __name__ == "__main__":
    cmd, *a = sys.argv[1:] or ["help"]
    if cmd == "find":
        for c, n, s in find(a[0])[:20]: print(c, n, s)
    elif cmd == "list":
        for r in disclosures(*a[:3], *(a[3:4])):
            print(r["rcept_dt"], r["rcept_no"], r["report_nm"].strip())
    elif cmd == "doc":
        print(document(a[0]))
    else:
        print(__doc__)
