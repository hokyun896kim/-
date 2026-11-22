# hochacha-econ-news

경제뉴스 한 줄이 내 생활과 계좌까지 오는 경로를 해석하고, AI에게 답 대신 판단 구조를 묻는 질문을 설계하는 Claude 스킬입니다. 학습용이며 특정 종목이나 금융상품을 권유하지 않습니다.

## 설치·사용
1. 이 폴더를 프로젝트의 `.claude/skills/hochacha-econ-news/`에 복사하거나 심볼릭 링크로 연결합니다.
2. Claude Code를 다시 열면 `SKILL.md`의 description을 보고 경제뉴스 해석 요청에서 스킬이 자동으로 불립니다.
3. 뉴스 한 줄을 붙여 넣고 "6단계로 풀어 줘", "이 뉴스 사실인지 검증 순서대로 봐 줘"처럼 요청합니다.
4. 장 번호(예: "7장 말투 읽기")나 주제(예: "실적 온도차")를 말하면 해당 장 파일을 읽고 답합니다.
5. AI 질문 원문이 필요하면 `prompts.md`를, 빠른 판단 규칙이 필요하면 `cheatsheet.md`를 봅니다.

## 출처
- 원서: 『질문이 바뀌면 경제가 보인다: 금리·환율·실적 뉴스를 내 돈의 언어로 번역하는 직장인 AI 경제 루틴』, 호차차 지음, 출간편집본 ver0.5 (`ebook/source/book2.md`)
- 구조: book-to-skill(MIT) 형식 참고 (장 파일, glossary, patterns, cheatsheet, 마스터 SKILL.md 규격)
