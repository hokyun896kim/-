# hochacha-backtest-check

1. 유튜브·커뮤니티 매매법이나 AI가 준 백테스트 결과를 그대로 믿기 전에 검증 질문(상장폐지 포함, 같은 날 무작위 비교, 미래 엿보기, 기간 분할, 신호 vs 체결 기준)을 던지게 하는 Claude 스킬입니다.
2. 설치: 이 폴더를 프로젝트의 `.claude/skills/hochacha-backtest-check/`(또는 개인 `~/.claude/skills/`)에 복사하면 Claude가 `SKILL.md`를 읽어 자동으로 씁니다.
3. 사용: "이 매매법 승률 80%래, 믿어도 돼?", "AI가 준 백테스트 결과 검토해 줘", "ch11 급락 반등 규칙 알려 줘"처럼 요청합니다.
4. 구성: `SKILL.md`(핵심 원칙·색인), `chapters/`(장별 요약 17개), `glossary.md`·`patterns.md`·`cheatsheet.md`.
5. 투자 권유가 아닙니다. 모든 숫자는 원고의 과거 데이터 결과이며 미래 수익을 보장하지 않습니다.

출처: 호차차 지음, 『그 매매법, 정말 통했을까 — AI와 함께 21년 치 데이터로 확인한 유튜브 매매법의 성적표』. 스킬 구조는 book-to-skill(MIT) 형식 참고.
