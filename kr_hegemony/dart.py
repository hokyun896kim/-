"""DART(전자공시) OpenAPI 백엔드 — 한국 연결재무제표로 헤게모니 스프레드 계산.

yfinance의 한국 재무 커버리지 한계를 보완한다. DART 연결손익계산서에서
매출액·영업이익을 직접 받아 YoY 스프레드를 산출하므로 훨씬 정확하다.

필요: 무료 DART API 키 (https://opendart.fss.or.kr → 인증키 신청).
      환경변수 DART_API_KEY 로 전달.

핵심 함수
- corp_map(key): 종목코드(6자리) → DART 고유번호(corp_code) 매핑
- annual_spread(key, corp_code, year): 연간 매출/영업이익 YoY + 스프레드
- quarter_spread(key, corp_code, year): 최근 분기 누적 YoY (있을 때)

네트워크가 필요하므로 이 모듈은 사용자 PC/Actions에서 실행한다.
순수 파싱 로직(_spread_from_rows, _pick)은 오프라인 단위테스트로 검증된다.
"""
from __future__ import annotations

import io
import json
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

BASE = "https://opendart.fss.or.kr/api"

# 손익계산서 계정 식별 (account_id 우선, 없으면 한글명 키워드)
REV_IDS = {"ifrs-full_Revenue", "ifrs_Revenue", "dart_OperatingRevenue"}
REV_NM = ("매출액", "수익(매출액)", "영업수익", "매출")
OP_IDS = {"dart_OperatingIncomeLoss", "ifrs-full_OperatingIncomeLoss",
          "ifrs-full_ProfitLossFromOperatingActivities"}
OP_NM = ("영업이익", "영업이익(손실)")

REPRT_ANNUAL = "11011"          # 사업보고서(연간)
# 분기 보고서 (최신 우선 시도)
REPRT_QUARTERS = ["11014", "11012", "11013"]  # 3분기 · 반기 · 1분기


def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "hegemony-kr"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _num(s) -> float | None:
    if s is None:
        return None
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _pick(rows: list[dict], ids: set[str], nms: tuple, fields: list[str]):
    """IS/CIS 행에서 계정을 찾아 fields(우선순위) 중 첫 유효 숫자를 반환."""
    def grab(r):
        for fld in fields:
            v = _num(r.get(fld))
            if v is not None:
                return v
        return None
    # 1) account_id 정확 매칭
    for r in rows:
        if r.get("sj_div") in ("IS", "CIS") and r.get("account_id") in ids:
            v = grab(r)
            if v is not None:
                return v
    # 2) 한글 계정명 키워드 매칭
    for r in rows:
        if r.get("sj_div") not in ("IS", "CIS"):
            continue
        nm = (r.get("account_nm") or "").replace(" ", "")
        if any(k.replace(" ", "") in nm for k in nms):
            v = grab(r)
            if v is not None:
                return v
    return None


def _yoy(cur, prev):
    if cur is None or prev is None or prev == 0:
        return None
    return (cur / abs(prev) - 1) * 100 if prev > 0 else (cur - prev) / abs(prev) * 100


def _spread_from_rows(rows: list[dict], cur_fields: list[str],
                      prev_fields: list[str]) -> dict | None:
    """손익 행 리스트에서 매출/영업이익 YoY + 스프레드를 계산 (순수 함수, 테스트용)."""
    rev_c = _pick(rows, REV_IDS, REV_NM, cur_fields)
    rev_p = _pick(rows, REV_IDS, REV_NM, prev_fields)
    op_c = _pick(rows, OP_IDS, OP_NM, cur_fields)
    op_p = _pick(rows, OP_IDS, OP_NM, prev_fields)
    rev_yoy, op_yoy = _yoy(rev_c, rev_p), _yoy(op_c, op_p)
    if rev_yoy is None or op_yoy is None:
        return None
    return {"rev": round(rev_yoy, 1), "op": round(op_yoy, 1),
            "spread": round(op_yoy - rev_yoy, 1)}


# ----------------------------- 네트워크 호출 -----------------------------
def corp_map(key: str) -> dict[str, str]:
    """종목코드(6자리) → corp_code(8자리) 매핑 다운로드."""
    raw = _get(f"{BASE}/corpCode.xml?crtfc_key={key}")
    zf = zipfile.ZipFile(io.BytesIO(raw))
    root = ET.fromstring(zf.read(zf.namelist()[0]))
    out = {}
    for el in root.iter("list"):
        sc = (el.findtext("stock_code") or "").strip()
        cc = (el.findtext("corp_code") or "").strip()
        if sc and len(sc) == 6 and cc:
            out[sc] = cc
    return out


def _statement(key: str, corp_code: str, year: int, reprt: str,
               fs: str) -> list[dict] | None:
    url = (f"{BASE}/fnlttSinglAcntAll.json?crtfc_key={key}"
           f"&corp_code={corp_code}&bsns_year={year}&reprt_code={reprt}"
           f"&fs_div={fs}")
    try:
        d = json.loads(_get(url))
    except Exception:
        return None
    if d.get("status") != "000":
        return None
    return d.get("list", [])


def annual_spread(key: str, corp_code: str, year: int) -> dict | None:
    """연간 사업보고서로 매출/영업이익 YoY + 스프레드.

    한 번의 호출에 당기(thstrm)·전기(frmtrm)가 함께 와서 YoY 가 바로 나온다.
    연결(CFS) 우선, 없으면 별도(OFS).
    """
    for fs in ("CFS", "OFS"):
        rows = _statement(key, corp_code, year, REPRT_ANNUAL, fs)
        if not rows:
            continue
        res = _spread_from_rows(rows, ["thstrm_amount"], ["frmtrm_amount"])
        if res:
            res["fs"] = fs
            return res
    return None


def quarter_spread(key: str, corp_code: str, year: int) -> dict | None:
    """최신 분기 보고서의 누적 YoY (있을 때). q_op 베이스로 사용.

    누적금액(thstrm_add_amount) 우선, 없으면 당기금액(thstrm_amount).
    완전한 TTM 은 아니며 '최근 분기누적' 흐름의 근사치다.
    """
    for reprt in REPRT_QUARTERS:
        for fs in ("CFS", "OFS"):
            rows = _statement(key, corp_code, year, reprt, fs)
            if not rows:
                continue
            res = _spread_from_rows(
                rows, ["thstrm_add_amount", "thstrm_amount"],
                ["frmtrm_add_amount", "frmtrm_amount"])
            if res:
                res["fs"] = fs
                res["reprt"] = reprt
                return res
    return None
