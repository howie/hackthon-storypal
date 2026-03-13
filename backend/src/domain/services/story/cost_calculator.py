"""Story cost estimation — pure functions, no external dependencies.

Pricing tables based on public rates as of 2026-03.
"""

from decimal import Decimal

# Gemini pricing per 1M tokens
_LLM_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "default": {"input": 0.15, "output": 0.60},
}

# TTS pricing per 1M characters
_TTS_PRICING_PER_M_CHARS: dict[str, float] = {
    "gemini": 0.0,  # still preview on Google AI Studio (GA only on Vertex AI)
    "google": 4.0,
    "elevenlabs": 30.0,
    "azure": 16.0,
    "default": 4.0,
}

# Image pricing per image
_IMAGE_PRICING_PER_IMAGE: dict[str, float] = {
    "gemini": 0.02,
    "default": 0.02,
}


def _match_llm_pricing(model: str) -> dict[str, float]:
    """Find the best matching pricing entry for a model name."""
    for key in _LLM_PRICING:
        if key != "default" and key in model:
            return _LLM_PRICING[key]
    return _LLM_PRICING["default"]


def estimate_llm_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Estimate LLM cost from token counts."""
    pricing = _match_llm_pricing(model)
    cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
    return Decimal(str(round(cost, 6)))


def estimate_tts_cost(provider: str, characters: int) -> Decimal:
    """Estimate TTS cost from character count."""
    rate = _TTS_PRICING_PER_M_CHARS.get(provider, _TTS_PRICING_PER_M_CHARS["default"])
    cost = characters * rate / 1_000_000
    return Decimal(str(round(cost, 6)))


def estimate_image_cost(provider: str, count: int = 1) -> Decimal:
    """Estimate image generation cost."""
    rate = _IMAGE_PRICING_PER_IMAGE.get(provider, _IMAGE_PRICING_PER_IMAGE["default"])
    return Decimal(str(round(rate * count, 6)))
