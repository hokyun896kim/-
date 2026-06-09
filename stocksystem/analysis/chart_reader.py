"""차트 이미지 판독 엔진 (Claude 비전 모델).

업로드한 차트 캡처 이미지를 Claude 비전 모델에게 보내, 추세·지지/저항·
패턴·지표·매매신호를 구조화된 형태로 읽어온다.

설계 노트:
- `anthropic` 패키지는 함수 안에서 지연 import 한다. 패키지가 없거나
  네트워크가 없는 환경(오프라인 데모)에서도 stocksystem 의 나머지 기능과
  테스트가 영향을 받지 않도록 하기 위함이다.
- 비전 + 구조화 출력(json_schema)을 사용해 항상 파싱 가능한 결과를 받는다.
- 모델은 기본적으로 가장 똑똑한 claude-opus-4-8 을 적응형 사고와 함께 쓴다.

⚠️ 결과는 교육·연구용 참고 자료이며 투자자문이 아니다.
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Optional

# 기본 모델: 가장 capable 한 Opus 4.8
DEFAULT_MODEL = "claude-opus-4-8"

# 매매 신호 등급(스코어링 모듈과 톤을 맞춘다)
SIGNAL_LABELS = ["적극매수", "매수", "중립", "매도", "적극매도"]

# 차트 판독 전문가 시스템 프롬프트
_SYSTEM = """\
당신은 20년 경력의 기술적 분석(테크니컬 애널리스트) 전문가입니다.
사용자가 올린 '주가 차트 이미지'를 보고 차트를 판독합니다.

판독 원칙:
- 이미지에 실제로 보이는 것만 근거로 삼습니다. 보이지 않는 가격·날짜를
  지어내지 마세요. 축 눈금이 안 보이면 '대략', '상단/하단 부근'처럼
  상대적으로 표현합니다.
- 추세(상승/하락/횡보), 추세선·채널, 지지/저항 구간, 거래량, 차트 패턴
  (헤드앤숄더, 이중 천장/바닥, 삼각수렴, 깃발, 컵앤핸들 등), 캔들 신호,
  이미지에 함께 표시된 보조지표(이동평균선·MACD·RSI·볼린저밴드 등)를
  종합적으로 읽습니다.
- 한쪽으로 단정하지 말고 상방/하방 시나리오와 무효화(손절) 기준을 함께
  제시합니다.
- 모든 설명은 한국어로, 초보자도 이해할 수 있게 풀어서 씁니다.
- 이것은 교육용 분석이며 투자 권유가 아님을 잊지 마세요.

이미지가 주가 차트가 아니거나 너무 흐려 판독이 어려우면, summary 에 그
사실을 적고 signal 은 '중립', confidence 는 낮게 설정합니다.
"""

# 구조화 출력 스키마 (numeric min/max 등 미지원 제약은 쓰지 않는다)
_SCHEMA = {
    "type": "object",
    "properties": {
        "is_chart": {
            "type": "boolean",
            "description": "이미지가 판독 가능한 주가 차트이면 true",
        },
        "trend": {
            "type": "string",
            "description": "큰 흐름의 추세 (예: 단기 상승추세, 중기 횡보)",
        },
        "trend_detail": {
            "type": "string",
            "description": "추세에 대한 2~4문장 설명",
        },
        "support_levels": {
            "type": "array",
            "items": {"type": "string"},
            "description": "지지 구간/가격대. 보이는 대로 묘사",
        },
        "resistance_levels": {
            "type": "array",
            "items": {"type": "string"},
            "description": "저항 구간/가격대. 보이는 대로 묘사",
        },
        "patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["name", "description"],
                "additionalProperties": False,
            },
            "description": "식별된 차트 패턴 목록 (없으면 빈 배열)",
        },
        "indicators": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "reading": {"type": "string"},
                },
                "required": ["name", "reading"],
                "additionalProperties": False,
            },
            "description": "이미지에 함께 보이는 보조지표 판독 (없으면 빈 배열)",
        },
        "key_observations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "핵심 관찰 포인트 3~6개",
        },
        "bullish_scenario": {
            "type": "string",
            "description": "상방 시나리오와 조건",
        },
        "bearish_scenario": {
            "type": "string",
            "description": "하방 시나리오와 조건",
        },
        "invalidation": {
            "type": "string",
            "description": "분석이 깨지는 손절/무효화 기준",
        },
        "signal": {
            "type": "string",
            "enum": SIGNAL_LABELS,
            "description": "종합 매매 신호",
        },
        "confidence": {
            "type": "integer",
            "description": "판독 확신도 0~100",
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "유의해야 할 리스크",
        },
        "summary": {
            "type": "string",
            "description": "전체 판독 요약 (3~5문장)",
        },
    },
    "required": [
        "is_chart", "trend", "trend_detail", "support_levels",
        "resistance_levels", "patterns", "indicators", "key_observations",
        "bullish_scenario", "bearish_scenario", "invalidation", "signal",
        "confidence", "risks", "summary",
    ],
    "additionalProperties": False,
}


@dataclass
class ChartReading:
    """차트 판독 결과."""
    is_chart: bool
    trend: str
    trend_detail: str
    support_levels: list[str]
    resistance_levels: list[str]
    patterns: list[dict]
    indicators: list[dict]
    key_observations: list[str]
    bullish_scenario: str
    bearish_scenario: str
    invalidation: str
    signal: str
    confidence: int
    risks: list[str]
    summary: str
    model: str = DEFAULT_MODEL

    @classmethod
    def from_dict(cls, d: dict, model: str = DEFAULT_MODEL) -> "ChartReading":
        return cls(
            is_chart=bool(d.get("is_chart", True)),
            trend=d.get("trend", ""),
            trend_detail=d.get("trend_detail", ""),
            support_levels=list(d.get("support_levels", [])),
            resistance_levels=list(d.get("resistance_levels", [])),
            patterns=list(d.get("patterns", [])),
            indicators=list(d.get("indicators", [])),
            key_observations=list(d.get("key_observations", [])),
            bullish_scenario=d.get("bullish_scenario", ""),
            bearish_scenario=d.get("bearish_scenario", ""),
            invalidation=d.get("invalidation", ""),
            signal=d.get("signal", "중립"),
            confidence=int(d.get("confidence", 0)),
            risks=list(d.get("risks", [])),
            summary=d.get("summary", ""),
            model=model,
        )


class ChartReaderError(RuntimeError):
    """차트 판독 중 발생한 오류 (API 키 누락, 패키지 미설치 등)."""


def api_key_available(api_key: Optional[str] = None) -> bool:
    """사용 가능한 Anthropic API 키가 있는지 확인."""
    return bool(api_key or os.environ.get("ANTHROPIC_API_KEY"))


def read_chart(
    image_bytes: bytes,
    media_type: str = "image/png",
    *,
    context_note: str = "",
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> ChartReading:
    """차트 이미지를 판독해 구조화된 결과를 반환한다.

    Parameters
    ----------
    image_bytes : 차트 이미지 원본 바이트
    media_type  : "image/png" | "image/jpeg" | "image/webp" | "image/gif"
    context_note: 종목/기간 등 사용자가 덧붙이는 맥락 (선택)
    api_key     : 명시적 키. 없으면 ANTHROPIC_API_KEY 환경변수 사용
    model       : 사용할 Claude 모델 ID
    """
    try:
        import anthropic
    except ImportError as e:  # 패키지 미설치
        raise ChartReaderError(
            "anthropic 패키지가 설치되어 있지 않습니다. "
            "`pip install anthropic` 후 다시 시도하세요."
        ) from e

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ChartReaderError(
            "Anthropic API 키가 없습니다. 환경변수 ANTHROPIC_API_KEY 를 "
            "설정하거나 화면에서 키를 입력하세요."
        )

    client = anthropic.Anthropic(api_key=key)
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    prompt = "이 주가 차트를 판독해 주세요."
    if context_note.strip():
        prompt += f"\n\n참고 맥락: {context_note.strip()}"

    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=_SYSTEM,
            thinking={"type": "adaptive"},
            output_config={
                "format": {"type": "json_schema", "schema": _SCHEMA}
            },
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
    except anthropic.AuthenticationError as e:
        raise ChartReaderError("API 키가 유효하지 않습니다.") from e
    except anthropic.APIStatusError as e:
        raise ChartReaderError(f"API 오류({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise ChartReaderError("네트워크 연결 오류입니다.") from e

    # 구조화 출력: 첫 text 블록이 스키마를 만족하는 JSON
    import json
    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise ChartReaderError("모델이 빈 응답을 반환했습니다.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ChartReaderError("응답을 JSON 으로 해석하지 못했습니다.") from e

    return ChartReading.from_dict(data, model=model)
