"""AI 비서 계층.

자연어 질문을 받아 기존 분석 모듈을 대신 실행해주는 대화형 인터페이스.

두 가지 엔진으로 동작한다 (`engine="auto"` 면 자동 선택).
  - "claude" : ANTHROPIC_API_KEY 가 있으면 Claude API 의 도구 호출로
               질문을 이해하고, 여러 도구를 엮어 답한다.
  - "rules"  : 키가 없으면 키워드/패턴으로 의도를 파악해 도구 하나를
               실행한다. 네트워크·비용 없이 오프라인에서도 돈다.

어느 쪽이든 숫자는 전부 `tools.py` 의 도구가 만든다 — 즉 대시보드·CLI 와
같은 코드, 같은 결과다.
"""
from .agent import Assistant, Reply, ToolCall
from .tools import TOOLS, AssistantContext, render_tool, run_tool
from .intent import Intent, parse_intent

__all__ = ["Assistant", "Reply", "ToolCall", "AssistantContext", "TOOLS",
           "run_tool", "render_tool", "Intent", "parse_intent"]
