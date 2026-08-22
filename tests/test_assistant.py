"""AI 비서 테스트 (전부 오프라인 — SampleProvider + 가짜 Claude 클라이언트).

비서의 핵심 약속 두 가지를 지키는지 본다.
  1. 숫자는 기존 분석 모듈이 만든다 (비서가 다른 값을 내면 안 된다)
  2. API 키가 없어도, 도구가 실패해도 대화가 죽지 않는다
"""
import json

import pytest

from stocksystem.assistant import Assistant, parse_intent, run_tool
from stocksystem.assistant.agent import _trim
from stocksystem.assistant.intent import extract_sector, extract_symbols
from stocksystem.assistant.tools import (AssistantContext, TOOLS,
                                         anthropic_tool_defs, render_tool,
                                         resolve_symbol)
from stocksystem.analysis import analyze_symbol
from stocksystem.config import load_config
from stocksystem.data import SampleProvider


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def ctx(cfg, tmp_path):
    c = AssistantContext(cfg=cfg, provider_name="sample")
    c._provider = SampleProvider()
    c.broker_state = str(tmp_path / "paper.json")   # 실제 계좌를 건드리지 않게
    return c


@pytest.fixture
def bot(cfg, tmp_path):
    b = Assistant(cfg, provider_name="sample", engine="rules",
                  broker_state=str(tmp_path / "paper.json"))
    b.ctx._provider = SampleProvider()
    return b


# ----------------------------- 심볼/섹터 해석 -----------------------------


@pytest.mark.parametrize("text,expected", [
    ("엔비디아 어때?", "NVDA"),
    ("마소 분석해줘", "MSFT"),
    ("AAPL", "AAPL"),
    ("apple 좋아?", "AAPL"),
    ("테슬라 뉴스", "TSLA"),
])
def test_resolve_symbol(text, expected):
    assert resolve_symbol(text) == expected


def test_resolve_symbol_unknown():
    assert resolve_symbol("듣도보도못한회사") is None
    assert resolve_symbol("") is None


def test_extract_symbols_keeps_order_without_duplicates():
    assert extract_symbols("애플이랑 마소 비교해줘") == ["AAPL", "MSFT"]
    assert extract_symbols("NVDA vs AMD") == ["NVDA", "AMD"]
    assert extract_symbols("AAPL AAPL AAPL") == ["AAPL"]


def test_extract_sector():
    assert extract_sector("반도체 종목 골라줘") == "Technology"
    assert extract_sector("제약주 어때") == "Healthcare"
    assert extract_sector("아무거나") is None


# ----------------------------- 의도 파악 -----------------------------


@pytest.mark.parametrize("question,tool", [
    ("엔비디아 어때?", "analyze_stock"),
    ("AAPL 분석해줘", "analyze_stock"),
    ("오늘 시장 어때?", "market_overview"),
    ("공포탐욕지수 알려줘", "market_overview"),
    ("기술주 상위 5개 골라줘", "screen_stocks"),
    ("선취매 종목 찾아줘", "early_bird"),
    ("아직 안 오른 종목 있어?", "early_bird"),
    ("애플이랑 마소 비교해줘", "compare_stocks"),
    ("NVDA 헤게모니 스프레드", "hegemony"),
    ("테슬라 뉴스 어때?", "news_sentiment"),
    ("AAPL 골든크로스 백테스트", "backtest"),
    ("엔비디아 6개월 전망 확률", "simulate_future"),
    ("내 모의계좌 수익률", "paper_status"),
    ("관심종목 순위 알려줘", "watchlist_ranking"),
])
def test_parse_intent_picks_expected_tool(question, tool, cfg):
    intent = parse_intent(question, cfg)
    assert intent is not None, question
    assert intent.tool == tool


def test_parse_intent_returns_none_when_offtopic():
    assert parse_intent("오늘 점심 뭐 먹지", None) is None
    assert parse_intent("", None) is None
    assert parse_intent("   ", None) is None


def test_parse_intent_extracts_arguments(cfg):
    i = parse_intent("반도체 상위 20% 중에 3개만 골라줘", cfg)
    assert i.tool == "screen_stocks"
    assert i.args["sector"] == "Technology"
    assert i.args["top_pct"] == 20.0
    assert i.args["limit"] == 3


def test_paper_trade_needs_quantity_and_verb(cfg):
    """계좌를 바꾸는 도구는 수량 + 매수/매도 동사가 모두 있을 때만 뜬다."""
    i = parse_intent("엔비디아 10주 매수", cfg)
    assert i.tool == "paper_trade"
    assert i.args == {"action": "buy", "symbol": "NVDA", "quantity": 10.0}

    # 수량이 없으면 매매가 아니라 분석 질문으로 본다
    assert parse_intent("엔비디아 사고 싶은데 어때?", cfg).tool != "paper_trade"
    # 동사가 없으면 마찬가지
    assert parse_intent("엔비디아 10주 들고 있는데", cfg).tool != "paper_trade"


def test_portfolio_intent_parses_holdings(cfg):
    i = parse_intent("AAPL 5000달러 MSFT 3000달러 포트폴리오 진단해줘", cfg)
    assert i.tool == "portfolio_checkup"
    assert {h["symbol"]: h["value"] for h in i.args["holdings"]} == {
        "AAPL": 5000.0, "MSFT": 3000.0}


# ----------------------------- 도구 계층 -----------------------------


def test_every_tool_result_is_json_serializable(ctx):
    """도구 결과는 그대로 tool_result 로 모델에 들어간다 → 반드시 순수 JSON."""
    calls = {
        "analyze_stock": {"symbol": "AAPL"},
        "market_overview": {},
        "screen_stocks": {"sector": "Technology", "limit": 3},
        "early_bird": {"sector": "Technology", "limit": 3},
        "hegemony": {"symbols": ["AAPL"]},
        "compare_stocks": {"symbols": ["AAPL", "MSFT"]},
        "portfolio_checkup": {"holdings": [{"symbol": "AAPL", "value": 1000}]},
        "backtest": {"symbol": "AAPL", "strategy": "RSI 역추세"},
        "news_sentiment": {"symbol": "AAPL"},
        "simulate_future": {"symbol": "AAPL", "horizon_days": 21},
        "paper_status": {},
        "watchlist_ranking": {},
    }
    assert set(calls) | {"paper_trade"} == set(TOOLS), "새 도구에 테스트 추가 필요"
    for name, args in calls.items():
        result = run_tool(ctx, name, args)
        assert "error" not in result, f"{name}: {result.get('error')}"
        text = json.dumps(result, ensure_ascii=False, allow_nan=False)
        assert "NaN" not in text                     # 표준 JSON 이어야 한다
        assert render_tool(name, result).strip()     # 렌더도 비지 않아야


def test_analyze_stock_matches_scoring_module(ctx, cfg):
    """비서가 내는 점수는 대시보드/CLI 와 같은 값이어야 한다."""
    direct = analyze_symbol("AAPL", ctx.provider, cfg)
    viaBot = run_tool(ctx, "analyze_stock", {"symbol": "AAPL"})
    assert viaBot["total_score"] == direct.total_score
    assert viaBot["grade"] == direct.recommendation_label


def test_run_tool_never_raises(ctx):
    assert "error" in run_tool(ctx, "없는도구", {})
    assert "error" in run_tool(ctx, "analyze_stock", {"nope": 1})
    assert "error" in run_tool(ctx, "compare_stocks", {"symbols": ["AAPL"]})
    assert "error" in run_tool(ctx, "backtest",
                               {"symbol": "AAPL", "strategy": "없는전략"})


def test_paper_trade_roundtrip(ctx):
    buy = run_tool(ctx, "paper_trade",
                   {"action": "buy", "symbol": "AAPL", "quantity": 3})
    assert buy["executed"]["symbol"] == "AAPL"
    status = run_tool(ctx, "paper_status", {})
    assert status["holdings"][0]["종목"] == "AAPL"
    assert status["holdings"][0]["수량"] == 3

    over = run_tool(ctx, "paper_trade",
                    {"action": "sell", "symbol": "AAPL", "quantity": 99})
    assert "error" in over            # 보유 수량 부족은 예외가 아니라 error


def test_anthropic_tool_defs_shape():
    defs = anthropic_tool_defs()
    assert len(defs) == len(TOOLS)
    for d in defs:
        assert set(d) == {"name", "description", "input_schema"}
        assert d["input_schema"]["type"] == "object"
        assert d["description"].strip()
        for req in d["input_schema"].get("required", []):
            assert req in d["input_schema"]["properties"]


# ----------------------------- 엔진 선택/폴백 -----------------------------


def test_rules_engine_answers_offline(bot):
    reply = bot.ask("엔비디아 어때?")
    assert reply.engine == "rules"
    assert [c.name for c in reply.tool_calls] == ["analyze_stock"]
    assert "NVDA" in reply.text


def test_rules_engine_guides_when_confused(bot):
    reply = bot.ask("오늘 점심 뭐 먹지")
    assert reply.tool_calls == []
    assert "물어보세요" in reply.text


def test_auto_engine_without_credentials_uses_rules(cfg, monkeypatch):
    monkeypatch.setattr("stocksystem.assistant.agent.credentials_available",
                        lambda: False)
    assert Assistant(cfg, provider_name="sample", engine="auto").engine == "rules"


def test_auto_engine_with_credentials_uses_claude(cfg, monkeypatch):
    monkeypatch.setattr("stocksystem.assistant.agent.credentials_available",
                        lambda: True)
    assert Assistant(cfg, provider_name="sample",
                     engine="auto").engine == "claude"


# ---- 가짜 Claude 클라이언트로 도구 호출 루프 검증 (네트워크 없음) ----


class _Block:
    def __init__(self, type, **kw):
        self.type = type
        for k, v in kw.items():
            setattr(self, k, v)


class _Resp:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason
        self.usage = _Block("usage", input_tokens=10, output_tokens=5,
                            cache_read_input_tokens=0)


class _FakeMessages:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def create(self, **kwargs):
        # messages 는 호출자가 계속 append 하는 살아있는 리스트다.
        # 그대로 담아두면 나중에 본 모습이 기록돼 검증이 무의미해진다.
        self.calls.append({**kwargs,
                           "messages": list(kwargs.get("messages", []))})
        return self.script.pop(0)


class _FakeClient:
    def __init__(self, script):
        self.messages = _FakeMessages(script)


def _claude_bot(cfg, tmp_path, script):
    b = Assistant(cfg, provider_name="sample", engine="claude",
                  broker_state=str(tmp_path / "paper.json"))
    b.ctx._provider = SampleProvider()
    b._client = _FakeClient(script)
    return b


def test_claude_engine_runs_tool_then_answers(cfg, tmp_path):
    script = [
        _Resp([_Block("tool_use", id="t1", name="analyze_stock",
                      input={"symbol": "AAPL"})], stop_reason="tool_use"),
        _Resp([_Block("text", text="애플 종합점수는 도구 결과대로입니다.")]),
    ]
    bot = _claude_bot(cfg, tmp_path, script)
    reply = bot.ask("애플 어때?")

    assert reply.engine == "claude"
    assert [c.name for c in reply.tool_calls] == ["analyze_stock"]
    assert reply.text.startswith("애플 종합점수")
    assert reply.usage["input_tokens"] == 20        # 두 번 호출한 합

    # 두 번째 요청에 tool_result 가 제대로 들어갔는지
    second = bot._client.messages.calls[1]["messages"]
    result_block = second[-1]["content"][0]
    assert result_block["tool_use_id"] == "t1"
    assert result_block["is_error"] is False
    assert json.loads(result_block["content"])["symbol"] == "AAPL"


def test_claude_engine_marks_tool_errors(cfg, tmp_path):
    script = [
        _Resp([_Block("tool_use", id="t1", name="backtest",
                      input={"symbol": "AAPL", "strategy": "없는전략"})],
              stop_reason="tool_use"),
        _Resp([_Block("text", text="전략 이름을 확인해 주세요.")]),
    ]
    bot = _claude_bot(cfg, tmp_path, script)
    bot.ask("이상한 전략으로 백테스트")
    result_block = bot._client.messages.calls[1]["messages"][-1]["content"][0]
    assert result_block["is_error"] is True


def test_claude_request_carries_tools_and_cached_system(cfg, tmp_path):
    bot = _claude_bot(cfg, tmp_path, [_Resp([_Block("text", text="네")])])
    bot.ask("안녕")
    kw = bot._client.messages.calls[0]
    assert len(kw["tools"]) == len(TOOLS)
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kw["thinking"] == {"type": "adaptive"}
    assert kw["output_config"] == {"effort": "medium"}
    assert kw["model"] == cfg.assistant.model


def test_claude_failure_falls_back_to_rules(cfg, tmp_path):
    class _Boom:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("network down")

    bot = Assistant(cfg, provider_name="sample", engine="claude",
                    broker_state=str(tmp_path / "paper.json"))
    bot.ctx._provider = SampleProvider()
    bot._client = _Boom()

    reply = bot.ask("엔비디아 어때?")
    assert reply.engine == "rules"                 # 대화가 끊기지 않는다
    assert "NVDA" in reply.text
    assert "network down" in reply.note


def test_claude_drops_unsupported_params_and_retries(cfg, tmp_path):
    """구형 모델이 thinking 을 거절하면 빼고 다시 부른다."""
    calls = []

    class _Picky:
        class messages:
            @staticmethod
            def create(**kwargs):
                calls.append(kwargs)
                if "thinking" in kwargs:
                    raise ValueError(
                        "400 thinking: unexpected parameter for this model")
                return _Resp([_Block("text", text="ok")])

    bot = Assistant(cfg, provider_name="sample", engine="claude",
                    broker_state=str(tmp_path / "paper.json"))
    bot._client = _Picky()
    reply = bot.ask("안녕")

    assert reply.engine == "claude"
    assert reply.text == "ok"
    assert len(calls) == 2 and "thinking" not in calls[1]


def test_conversation_history_survives_turns(cfg, tmp_path):
    script = [_Resp([_Block("text", text="첫 답")]),
              _Resp([_Block("text", text="둘째 답")])]
    bot = _claude_bot(cfg, tmp_path, script)
    bot.ask("하나")
    bot.ask("둘")
    sent = bot._client.messages.calls[1]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    bot.reset()
    assert bot._messages == []


def test_trim_cuts_only_on_plain_user_turns():
    msgs = ([{"role": "user", "content": "q"},
             {"role": "assistant", "content": "a"}] * 20)
    trimmed = _trim(msgs, keep=6)
    assert trimmed[0]["role"] == "user"
    assert isinstance(trimmed[0]["content"], str)
    assert len(trimmed) <= 7

    short = [{"role": "user", "content": "q"}]
    assert _trim(short, keep=6) is short
