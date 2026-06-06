# 🇰🇷 한국 헤게모니 트리 (KR Hegemony Tree)

미국판 헤게모니 트리 v1.2의 **동결된 스코어러를 그대로** 한국 코스피·코스닥에
적용한 버전입니다. 헤게모니 스프레드 = **영업이익 증가율(YoY) − 매출 증가율(YoY)**
은 국적과 무관하므로 로직은 동일하고, **데이터 소스와 링크·통화만 현지화**했습니다.

| 항목 | 미국판 | 한국판 |
|---|---|---|
| 종목 | 미국 상장 | 코스피(.KS)·코스닥(.KQ) |
| 1차 자료 | SEC EDGAR · 8-K | **DART 전자공시** · 분기보고서 |
| 보조 링크 | Yahoo · Finviz · SeekingAlpha | **네이버 금융 · FnGuide · 한경 컨센서스** |
| 통화 | $ (USD/KRW 환산) | **₩ (환산 없음)** |
| AI 프롬프트 | SEC·영문 | **DART · K-IFRS 연결 영업이익 · 한국어 웹검색** |
| 벤치마크(RS) | S&P500(SPY) | **코스피(^KS11)** |

> 스코어러(`scoreCandidate` 등)는 미국판과 **한 줄도 다르지 않습니다.** 동결 원칙 유지.

---

## 🚀 사용법

### 1) 데모로 바로 보기 (네트워크 불필요)
```bash
cd kr_hegemony
python build_tree_kr.py --demo      # data/tree_kr.json (합성 데모) 생성
python -m http.server 8899          # 로컬 서버
# 브라우저에서 http://localhost:8899 접속
```
> `file://` 로 직접 열면 CORS로 데이터가 안 읽힙니다. 로컬 서버나 Netlify로 여세요.

### 2) 실시간 데이터로 생성 (인터넷 필요)
```bash
pip install yfinance
cd kr_hegemony
python build_tree_kr.py             # yfinance로 실제 재무·시세 → data/tree_kr.json
python -m http.server 8899
```
- yfinance가 `.KS/.KQ` 종목의 연간·분기 손익계산서, 시세를 가져옵니다.
- **주의**: 한국 종목은 미국만큼 재무 커버리지가 깨끗하지 않아 일부 종목의
  분기TTM·PER이 비는 경우가 있습니다(스크리너가 자동으로 — 처리).

### 3) 배포 (Netlify)
`kr_hegemony` 폴더(= `index.html` + `data/tree_kr.json`)를 통째로 드래그&드롭.

---

## 📁 구성
```
kr_hegemony/
├── index.html            # 한국판 도구 (스코어러는 미국판 v1.2와 동일)
├── data/tree_kr.json     # 데이터 (build_tree_kr.py 로 생성)
├── build_tree_kr.py      # 데이터 빌더 (--demo: 합성 / 기본: yfinance 실시간)
└── README_kr.md
```

## 🔧 유니버스 편집
`build_tree_kr.py` 의 `UNIVERSE` 리스트에 `(티커, 종목명, 대섹터, 세부산업, 코드)`를
추가/수정하면 됩니다. (예: `("042700.KS", "한미반도체", "IT·반도체", "반도체 장비·소재", "SEMIEQ")`)

## 🧱 한계 & 다음 단계
- yfinance의 한국 재무 데이터는 일부 종목에서 분기 영업이익이 비어 헤게모니
  스프레드 산출이 안 될 수 있습니다 → 더 정확히는 **DART OpenAPI** 연동이 근본 해법.
- DART OpenAPI(무료 키)로 연결재무제표를 직접 받으면 커버리지·정확도가 크게 오릅니다.
  필요 시 `build_tree_kr.py` 에 DART 백엔드를 추가하세요.
