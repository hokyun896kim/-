"""LLM 폴백 체인 — Claude → Gemini → GPT → Grok (에신 V3.5 표준 자산 패턴).

.env 또는 환경변수에서 키를 읽어, 키가 있는 공급자만 순서대로 시도한다.
401/402/429/타임아웃 등 어떤 실패든 다음 공급자로 폴백한다 (재시도 총 3회 한도).
모든 공급자 실패 시 (None, None, 0.0) 반환 — 호출 측이 모듈 해설로 대체한다.
"""
from __future__ import annotations

import json
import os
import urllib.request

USD_KRW = 1400.0

# (provider, model, in_usd_per_mtok, out_usd_per_mtok)
_PRICES = {
    "claude": ("claude-opus-4-8", 5.0, 25.0),
    "gemini": ("gemini-2.5-pro", 1.25, 10.0),
    "openai": ("gpt-4.1", 2.0, 8.0),
    "grok": ("grok-3", 3.0, 15.0),
}

MAX_ATTEMPTS = 3  # 🛑 종료 조건: LLM 재시도 총 3회


def _load_env() -> None:
    """같은 폴더의 .env를 읽어 환경변수에 주입 (이미 있으면 유지)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def _cost_krw(provider: str, in_tok: int, out_tok: int) -> float:
    _, pin, pout = _PRICES[provider]
    usd = in_tok / 1e6 * pin + out_tok / 1e6 * pout
    return round(usd * USD_KRW, 2)


def _post_json(url: str, headers: dict, body: dict, timeout: int = 90) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _call_claude(system: str, user: str, max_tokens: int) -> tuple[str, float]:
    key = os.environ["ANTHROPIC_API_KEY"]
    model = _PRICES["claude"][0]
    try:
        import anthropic  # 공식 SDK 우선 (claude-api 표준)
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in msg.content if b.type == "text")
        cost = _cost_krw("claude", msg.usage.input_tokens, msg.usage.output_tokens)
        return text, cost
    except ImportError:  # SDK 미설치 PC 폴백 — raw HTTP
        data = _post_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
            {"model": model, "max_tokens": max_tokens, "system": system,
             "messages": [{"role": "user", "content": user}]})
        text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        u = data.get("usage", {})
        return text, _cost_krw("claude", u.get("input_tokens", 0), u.get("output_tokens", 0))


def _call_gemini(system: str, user: str, max_tokens: int) -> tuple[str, float]:
    key = os.environ["GEMINI_API_KEY"]
    model = _PRICES["gemini"][0]
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {"x-goog-api-key": key},
        {"system_instruction": {"parts": [{"text": system}]},
         "contents": [{"role": "user", "parts": [{"text": user}]}],
         "generationConfig": {"maxOutputTokens": max_tokens}})
    text = "".join(p.get("text", "")
                   for p in data["candidates"][0]["content"].get("parts", []))
    u = data.get("usageMetadata", {})
    return text, _cost_krw("gemini", u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0))


def _call_openai_style(provider: str, url: str, key: str, system: str, user: str,
                       max_tokens: int) -> tuple[str, float]:
    model = _PRICES[provider][0]
    data = _post_json(
        url, {"Authorization": f"Bearer {key}"},
        {"model": model, "max_tokens": max_tokens,
         "messages": [{"role": "system", "content": system},
                      {"role": "user", "content": user}]})
    text = data["choices"][0]["message"]["content"]
    u = data.get("usage", {})
    return text, _cost_krw(provider, u.get("prompt_tokens", 0), u.get("completion_tokens", 0))


def generate(system: str, user: str, max_tokens: int = 2000):
    """폴백 체인 실행. 반환: (text, provider, cost_krw) — 전부 실패 시 (None, None, 0.0)."""
    _load_env()
    chain = [
        ("claude", "ANTHROPIC_API_KEY", lambda: _call_claude(system, user, max_tokens)),
        ("gemini", "GEMINI_API_KEY", lambda: _call_gemini(system, user, max_tokens)),
        ("openai", "OPENAI_API_KEY", lambda: _call_openai_style(
            "openai", "https://api.openai.com/v1/chat/completions",
            os.environ.get("OPENAI_API_KEY", ""), system, user, max_tokens)),
        ("grok", "XAI_API_KEY", lambda: _call_openai_style(
            "grok", "https://api.x.ai/v1/chat/completions",
            os.environ.get("XAI_API_KEY", ""), system, user, max_tokens)),
    ]
    attempts = 0
    errors = []
    for name, env_key, call in chain:
        if not os.environ.get(env_key):
            continue
        if attempts >= MAX_ATTEMPTS:
            break
        attempts += 1
        try:
            text, cost = call()
            if text and text.strip():
                return text.strip(), name, cost
            errors.append(f"{name}: empty response")
        except Exception as e:  # noqa: BLE001 — 어떤 실패든 다음 공급자로
            errors.append(f"{name}: {e}")
    return None, None, 0.0
