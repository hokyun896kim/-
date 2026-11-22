---
name: hochacha-ebook
description: Use when planning, writing, designing, building, checking or publishing a 호차차 e-book or print book in this repository — 기획, 집필, 원고 윤문, 표지·인포그래픽, PDF·EPUB·DOCX 빌드, 유페이퍼 등록·승인거절·반려 대응, 교보문고 퍼플 종이책(POD), 상세페이지·카드뉴스 같은 홍보물.
---

# 호차차 전자책 제작

세 권을 내며 겪은 실패(EPUB 3.0 거절, 판권 누락 거절, "AI 같은 표지", "양산형", 지루한 프롤로그, 1권과 비슷한 제목)를 다시 겪지 않기 위한 작업 기준이다. 사실은 원고에서, 판정은 명령 출력에서 나온다.

## 언제 쓰나
- 새 책 기획, 장 집필·재구성, 윤문
- 표지·인포그래픽·홍보 이미지 제작
- PDF·EPUB·DOCX 빌드, 유페이퍼·퍼플 등록과 재신청
- 쓰지 않을 때: 1권(『나는 AI에게 종목을 묻지 않았다』) 산출물 수정 — 출간 완료, 잠금

## 파이프라인 한눈에
| 단계 | 파일 | 명령 |
|---|---|---|
| 원고 | `ebook/source/bookN.md` | — |
| 파서·책 정보 | `ebook/contentN.py` (TITLE, PUBLISHER, PUBDATE, PUBDATE_KO, PRICE, EPUB_VERSION). 4권 `content4.py`는 content2 기반에 `N부.` 헤딩·에필로그·`>` 질문 상자 지원 | — |
| 그림 | `ebook/infographic2.py`(2권). 데이터 계약형 생성기 본보기: `ebook/archive/sign-tomorrow/infographic4.py` | — |
| 표지 | `ebook/coverN.py` | `python3 ebook/coverN.py` |
| 본문 PDF | `ebook/build_preview.py` | `cd ebook && BOOK=contentN python build_preview.py` |
| DOCX / EPUB / 미리보기 | `build_docx.py` / `build_epub.py` / `sample_pdf.py` | 같은 방식 |
| 집필 중 초고 PDF | `ebook/build_draft.py` | `cd ebook && python3 build_draft.py 4` |
| 쪽 나눔 감사 | (세션 스크래치 audit.py) | 두 쪽에 걸친 박스 0, 홀로 남은 소제목 0 |
| **출간 게이트** | `scripts/check_publish.py` | `python3 .claude/skills/hochacha-ebook/scripts/check_publish.py N` |
| 등록 서류 | `ebook/publish/bookN/등록정보.md` | — |

WeasyPrint는 69.0 고정(70은 목차 쪽번호가 0이 됨).

## 철칙
1. **게이트 출력 없이 "올려도 됩니다"라고 말하지 않는다.** `check_publish.py`가 `통과`를 찍어야 한다. 근거 없는 "통과할 거예요"가 거절 두 번의 원인이었다.
2. **새 사실·숫자를 지어내지 않는다.** 장면은 각색해도 되지만 저자의 실제 경험인 척하지 않는다(독자 시점으로 쓰거나 "[사례]" 자리로 남긴다). 금융 수치는 예시라고 표시하고 계산해서 검산한다.
3. **판권·표지·등록정보는 한 값에서 나온다.** contentN.py의 상수를 바꾸고 다시 빌드한다. 등록정보.md도 같은 값으로 맞춘다.
4. **재신청은 신규 등록이 아니라 "수정"** → 파일 교체 → "전자책수정" + "기본정보저장" → "판매".
5. **문단·숫자·인용·프롬프트 문안은 윤문 대상이 아니다.** 바꾸면 되돌린다.

## 단계별 기준 (자세한 내용은 references/)
- 기획·집필 흐름, 병렬 에이전트 분배 → `references/workflow.md`
- 문체·AI 티 제거·장면 재구성 → `references/writing.md`
- 표지·인포그래픽·홍보물 디자인 → `references/design.md`
- 유페이퍼·퍼플 제출 규격과 거절 대응 → `references/publish.md`
- 자료 조사(금리·경쟁 도서·트렌드) → `references/research.md`

## 핑계와 현실
| 핑계 | 현실 |
|---|---|
| "대부분 플랫폼은 EPUB3도 받아요" | 유페이퍼는 EPUB 2.0만 받는다. 거절됐다 |
| "판권에 날짜는 있잖아요" | "2026-11-20"·"2026년 11월"로는 거절됐다. **"발행일 2026년 11월 20일"**, **"가격 8,900원"** 표기 그대로 |
| "표지에 출판사명은 굳이…" | 제목·저자·출판사 중 하나라도 없으면 거절(개인은 "유페이퍼") |
| "그림은 대충 맞으면 돼요" | 그림의 숫자는 원고에서 계산·대조한다(infographic4.py가 다르면 멈춘다) |
| "이번엔 급하니 게이트는 생략" | 거절되면 재검수로 더 늦어진다. 게이트는 1분이다 |

## 위험 신호 — 멈추고 다시 본다
- 1권 파일을 고치려 한다
- 숫자가 원고에 없는데 그림·소개문에 들어간다
- 표지 제목만 바꿔도 다른 책 표지로 통한다
- 같은 장면·비유("노선도", "모임")가 여러 장에서 되풀이된다
- 등록정보의 가격·발행일이 판권과 다르다
