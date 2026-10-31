"""
AI settings, read from environment variables (see src/ai/docs/plan/README.md). Never reads .env files.
"""
import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash"
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}

@dataclass(frozen=True)
class AISettings:
    """
    Every AI env var, parsed and with defaults applied.
    """
    openrouter_api_key: str | None = None
    label_model: str = DEFAULT_MODEL
    writer_model: str = DEFAULT_MODEL
    fallback_models: tuple[str, ...] = ()
    llm_timeout_s: float = 30.0
    max_concurrency: int = 8
    enable_llm: bool = True

def load_settings(env: Mapping[str, str] | None = None) -> AISettings:
    """
    Build AISettings from env (defaults to os.environ). Raises ValueError on invalid values.
    """
    env = os.environ if env is None else env
    return AISettings(
        openrouter_api_key=env.get("OPENROUTER_API_KEY", "").strip() or None,
        label_model=env.get("AI_LABEL_MODEL", "").strip() or DEFAULT_MODEL,
        writer_model=env.get("AI_WRITER_MODEL", "").strip() or DEFAULT_MODEL,
        fallback_models=_parse_list(env.get("AI_FALLBACK_MODELS", "")),
        llm_timeout_s=_parse_positive(env, "AI_LLM_TIMEOUT_S", 30.0, float),
        max_concurrency=_parse_positive(env, "AI_MAX_CONCURRENCY", 8, int),
        enable_llm=_parse_bool(env, "AI_ENABLE_LLM", True),
    )

def _parse_list(raw: str) -> tuple[str, ...]:
    """
    Split a comma-separated value, dropping blanks.
    """
    return tuple(item.strip() for item in raw.split(",") if item.strip())

def _parse_positive[N: (int, float)](env: Mapping[str, str], name: str, default: N, kind: type[N]) -> N:
    """
    Parse a positive number of the given kind, or return the default when the var is unset or blank.
    """
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = kind(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a {kind.__name__}, got {raw!r}") from error
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0, got {raw!r}")
    return value

def _parse_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    """
    Parse a boolean flag (1/0, true/false, yes/no, on/off), or return the default when unset or blank.
    """
    raw = env.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise ValueError(f"{name} must be 0 or 1, got {raw!r}")
