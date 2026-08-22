"""비서 본체 — 하이브리드 엔진.

`Assistant.ask()` 하나만 쓰면 된다. 안에서 두 갈래로 나뉜다.

  Claude 엔진 : ANTHROPIC_API_KEY(또는 `ant auth login` 프로필)가 있으면
                Claude API 에 도구 목록을 넘기고, 모델이 고른 도구를 실행해
                결과를 다시 넣어주는 루프를 돈다. 여러 도구를 엮거나
                되묻는 대화가 된다.
  규칙 엔진   : 자격증명이 없거나 API 호출이 실패하면 키워드 기반으로
                도구 하나를 골라 실행한다. 오프라인에서도 돈다.

어느 쪽이든 숫자는 도구가 만든다. 모델은 도구가 돌려준 값을 설명할 뿐,
가격이나 점수를 지어내지 않도록 시스템 프롬프트에서 막는다.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from ..config import Config, load_config
from .intent import parse_intent, suggestions
from .tools import (AssistantContext, SCORE_CAVEAT, TOOLS, anthropic_tool_defs,
                    render_tool, run_tool)

DEFAULT_MODEL = "claude-opus-5"

SYSTEM_PROMPT = f"""\
당신은 개인투자자용 '미국주식 분석·매매 시스템'에 내장된 한국어 AI 비서입니다.
사용자의 질문을 이 시스템의 분석 도구로 옮겨 실행하고, 결과를 쉽게 풀어주는 것이
당신의 역할입니다.

## 반드시 지킬 것

1. **숫자는 절대 지어내지 마세요.** 주가·점수·비율·날짜 등 모든 수치는 도구를
   호출해서 얻은 값만 씁니다. 도구가 값을 주지 않았다면 "데이터가 없습니다"라고
   말하세요. 기억이나 추정으로 채우면 안 됩니다.
2. **질문에 종목·시장이 걸려 있으면 먼저 도구를 부르세요.** 도구 없이 답할 수
   있는 것은 용어 설명과 사용법 안내뿐입니다.
3. **매매 지시를 하지 마세요.** 이 시스템의 종합점수는 검증 결과 미래 수익률
   예측력이 확인되지 않았습니다({SCORE_CAVEAT}) 등급(상위/중상/중립/중하/하위)은
   점수 구간에서의 위치일 뿐입니다. "사세요/파세요", "오를 겁니다" 같은 표현
   대신 지표가 지금 어떤 상태인지를 서술하세요.
4. **모의매매(paper_trade)는 계좌 상태를 바꿉니다.** 사용자가 종목과 수량을
   분명히 말했을 때만 호출하고, 애매하면 먼저 되물으세요. 실행 후에는 체결가와
   잔여 현금을 그대로 알려주세요.
5. 도구가 error 를 돌려주면 숨기지 말고 무엇이 실패했는지 알려주고, 가능한
   대안(다른 종목명, 오프라인 모드 등)을 제안하세요.

## 답변 스타일

- 한국어로, 결론부터. 3~8줄이면 충분합니다. 표는 항목이 4개 이상일 때만.
- 숫자에는 단위를 붙이세요 (달러, %, 점, %p).
- 여러 도구가 필요하면 한 번에 호출해도 됩니다 (예: 종목 분석 + 뉴스 분위기).
- 답변 끝에는 그 숫자가 무엇을 뜻하고 무엇을 뜻하지 않는지 한 줄로 덧붙이세요.
"""


@dataclass
class ToolCall:
    """실행된 도구 하나의 기록 (UI 가 접어서 보여줄 수 있게)."""

    name: str
    args: dict
    result: dict

    @property
    def rendered(self) -> str:
        return render_tool(self.name, self.result)


@dataclass
class Reply:
    text: str
    engine: str                       # "claude" | "rules"
    tool_calls: list[ToolCall] = field(default_factory=list)
    note: str = ""                    # 폴백 사유 등 부가 안내
    usage: dict = field(default_factory=dict)


def credentials_available() -> bool:
    """Claude 엔진을 쓸 자격증명이 있는지 확인한다.

    환경변수가 비어 있어도 `ant auth login` 프로필이 있으면 SDK 가 알아서
    찾는다. 그래서 env 만 보지 않고 클라이언트를 만들어 확인한다.
    """
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
            "ANTHROPIC_AUTH_TOKEN"):
        return True
    try:
        import anthropic
        client = anthropic.Anthropic()
    except Exception:
        return False
    return bool(getattr(client, "api_key", None)
                or getattr(client, "auth_token", None))


class Assistant:
    """대화형 비서. 대시보드·CLI 가 공유한다."""

    def __init__(self, cfg: Config | None = None,
                 provider_name: str | None = None, *,
                 engine: str = "auto", api_key: str | None = None,
                 model: str | None = None,
                 broker_state: str | None = None) -> None:
        self.cfg = cfg or load_config()
        acfg = self.cfg.assistant
        self.ctx = AssistantContext(
            cfg=self.cfg,
            provider_name=provider_name or self.cfg.data_provider,
        )
        if broker_state:
            self.ctx.broker_state = broker_state
        self.model = model or acfg.model
        self.max_turns = max(1, int(acfg.max_turns))
        self.max_tokens = int(acfg.max_tokens)
        self.effort = acfg.effort
        self.thinking = acfg.thinking
        self._api_key = api_key
        self._client: Any = None
        self._degraded: set[str] = set()   # API 가 거부한 선택적 파라미터
        self._messages: list[dict] = []

        requested = (engine or "auto").lower()
        if requested == "rules":
            self.engine = "rules"
        elif requested == "claude":
            self.engine = "claude"
        else:
            self.engine = ("claude" if (api_key or credentials_available())
                           else "rules")

    # ----------------------------- 공개 API -----------------------------

    def reset(self) -> None:
        """대화 기록을 지운다."""
        self._messages = []

    def ask(self, question: str) -> Reply:
        if not question or not question.strip():
            return Reply("무엇을 도와드릴까요?", self.engine)
        if self.engine == "claude":
            try:
                return self._ask_claude(question)
            except Exception as e:
                # 하이브리드의 핵심: API 가 막혀도 대화가 끊기지 않는다.
                reply = self._ask_rules(question)
                reply.note = (f"Claude 호출에 실패해 규칙 엔진으로 답했습니다 "
                              f"({type(e).__name__}: {e})"
                              + (f" · {reply.note}" if reply.note else ""))
                return reply
        return self._ask_rules(question)

    @property
    def available_tools(self) -> list[str]:
        return list(TOOLS)

    @staticmethod
    def examples() -> list[str]:
        return suggestions()

    # ----------------------------- 규칙 엔진 -----------------------------

    def _ask_rules(self, question: str) -> Reply:
        intent = parse_intent(question, self.cfg)
        if intent is None:
            ex = "\n".join(f"  · {s}" for s in suggestions()[:8])
            return Reply(
                "무엇을 물어보시는지 파악하지 못했습니다. 이런 걸 물어보세요:\n"
                f"{ex}\n\n(ANTHROPIC_API_KEY 를 설정하면 자유로운 대화가 "
                "가능합니다.)", "rules")

        result = run_tool(self.ctx, intent.tool, intent.args)
        call = ToolCall(intent.tool, intent.args, result)
        text = render_tool(intent.tool, result)
        return Reply(text, "rules", [call], note=intent.note)

    # ----------------------------- Claude 엔진 -----------------------------

    def _get_client(self):
        if self._client is None:
            import anthropic          # 선택적 의존성 — 여기서만 임포트
            self._client = (anthropic.Anthropic(api_key=self._api_key)
                            if self._api_key else anthropic.Anthropic())
        return self._client

    def _request_kwargs(self, messages: list[dict]) -> dict:
        kw: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            # 시스템 프롬프트와 도구 정의는 매 턴 동일하다 → 캐시 대상.
            "system": [{"type": "text", "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"}}],
            "tools": anthropic_tool_defs(),
            "messages": messages,
        }
        if "thinking" not in self._degraded and self.thinking != "off":
            kw["thinking"] = {"type": self.thinking}
        if "output_config" not in self._degraded and self.effort:
            kw["output_config"] = {"effort": self.effort}
        return kw

    def _create(self, messages: list[dict]):
        """요청을 보낸다. 모델이 못 받는 선택적 파라미터는 떼고 한 번 재시도.

        config 의 model 을 바꾸면(예: 구형 모델) adaptive thinking 이나
        effort 가 400 으로 거절될 수 있다. 그때 대화 전체를 실패시키는 대신
        해당 파라미터를 빼고 다시 부른다 — 이후 턴에도 계속 뺀다.
        """
        client = self._get_client()
        try:
            return client.messages.create(**self._request_kwargs(messages))
        except Exception as e:
            msg = str(e).lower()
            dropped = False
            for param in ("thinking", "output_config"):
                if param in msg and param not in self._degraded:
                    self._degraded.add(param)
                    dropped = True
            if not dropped:
                raise
            return client.messages.create(**self._request_kwargs(messages))

    def _ask_claude(self, question: str) -> Reply:
        messages = self._messages + [{"role": "user", "content": question}]
        calls: list[ToolCall] = []
        usage = {"input_tokens": 0, "output_tokens": 0, "cache_read": 0}
        response = None

        for _ in range(self.max_turns):
            response = self._create(messages)
            u = getattr(response, "usage", None)
            if u is not None:
                usage["input_tokens"] += getattr(u, "input_tokens", 0) or 0
                usage["output_tokens"] += getattr(u, "output_tokens", 0) or 0
                usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0

            if response.stop_reason == "refusal":
                messages.append({"role": "assistant", "content": response.content})
                self._messages = messages
                return Reply("이 질문에는 답할 수 없습니다. 다르게 물어봐 주세요.",
                             "claude", calls, usage=usage)

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "pause_turn":
                continue          # 서버 도구가 멈춘 것 — 그대로 이어 보낸다

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                break

            results = []
            for tu in tool_uses:
                args = dict(tu.input or {})
                result = run_tool(self.ctx, tu.name, args)
                calls.append(ToolCall(tu.name, args, result))
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result, ensure_ascii=False),
                    "is_error": bool(result.get("error")),
                })
            messages.append({"role": "user", "content": results})
        else:
            # max_turns 를 다 썼는데도 도구를 계속 부르는 중
            messages.append({
                "role": "user",
                "content": "도구 호출 한도에 도달했습니다. 지금까지 얻은 "
                           "결과만으로 답변을 정리해 주세요.",
            })
            response = self._create(messages)
            messages.append({"role": "assistant", "content": response.content})

        text = "\n".join(b.text for b in (response.content if response else [])
                         if b.type == "text").strip()
        if not text and calls:
            # 모델이 말을 안 붙였으면 도구 결과라도 보여준다
            text = "\n\n".join(c.rendered for c in calls)
        self._messages = _trim(messages)
        return Reply(text or "답변을 만들지 못했습니다.", "claude", calls,
                     usage=usage)


def _trim(messages: list[dict], keep: int = 24) -> list[dict]:
    """대화 기록을 최근 N개로 자른다.

    tool_result 로 시작하는 지점에서 끊으면 짝이 안 맞아 400 이 난다.
    user 텍스트 턴에서만 자른다.
    """
    if len(messages) <= keep:
        return messages
    for i in range(len(messages) - keep, len(messages)):
        m = messages[i]
        if m["role"] == "user" and isinstance(m.get("content"), str):
            return messages[i:]
    return messages[-2:]
