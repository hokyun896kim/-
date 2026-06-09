"""차트 판독 엔진 테스트 (네트워크/ API 키 불필요).

실제 Claude API 호출은 단위 테스트하지 않고, API 키가 없을 때의 방어
로직과 결과 파싱(from_dict)만 검증한다.
"""
import pytest

from stocksystem.analysis import chart_reader as cr


def test_signal_labels():
    assert cr.SIGNAL_LABELS == ["적극매수", "매수", "중립", "매도", "적극매도"]


def test_api_key_available(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert cr.api_key_available() is False
    assert cr.api_key_available("sk-xyz") is True
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    assert cr.api_key_available() is True


def test_read_chart_without_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(cr.ChartReaderError):
        cr.read_chart(b"not-an-image", api_key=None)


def test_from_dict_full():
    data = {
        "is_chart": True,
        "trend": "단기 상승추세",
        "trend_detail": "20일선 위 안착",
        "support_levels": ["150 부근"],
        "resistance_levels": ["170 부근", "180 부근"],
        "patterns": [{"name": "컵앤핸들", "description": "손잡이 형성 중"}],
        "indicators": [{"name": "RSI", "reading": "62, 중립 상단"}],
        "key_observations": ["거래량 증가"],
        "bullish_scenario": "170 돌파 시 상승",
        "bearish_scenario": "150 이탈 시 하락",
        "invalidation": "150 종가 이탈",
        "signal": "매수",
        "confidence": 68,
        "risks": ["실적 발표 변동성"],
        "summary": "전반적으로 우상향.",
    }
    r = cr.ChartReading.from_dict(data)
    assert r.is_chart is True
    assert r.signal == "매수"
    assert r.confidence == 68
    assert r.patterns[0]["name"] == "컵앤핸들"
    assert len(r.resistance_levels) == 2
    assert r.model == cr.DEFAULT_MODEL


def test_from_dict_defaults_on_missing():
    r = cr.ChartReading.from_dict({})
    assert r.signal == "중립"
    assert r.confidence == 0
    assert r.support_levels == []
    assert r.patterns == []
    assert r.is_chart is True


def test_schema_objects_are_strict():
    # 구조화 출력 스키마는 모든 object 에 additionalProperties:false 가 있어야 한다
    def check(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
            for v in node.values():
                check(v)
        elif isinstance(node, list):
            for v in node:
                check(v)
    check(cr._SCHEMA)
