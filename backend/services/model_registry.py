"""Model Registry — centralized LLM routing with per-module model switching (Groq)."""

import os
import logging

logger = logging.getLogger(__name__)

# Supported module types
MODULE_TYPES = [
    "strategic_analysis",
    "scaffold",
    "compliance",
    "trade_off",
    "srs",
    "diagram",
    "architecture",
    "scoring",
]

# Default Groq models per module — llama-3.3-70b-versatile is the best for structured output
# Groq API: https://api.groq.com/openai/v1
DEFAULT_MODELS: dict[str, str] = {
    "strategic_analysis": "llama-3.3-70b-versatile",
    "scaffold": "llama-3.3-70b-versatile",
    "compliance": "llama-3.3-70b-versatile",
    "trade_off": "llama-3.3-70b-versatile",
    "srs": "llama-3.3-70b-versatile",
    "diagram": "llama-3.3-70b-versatile",
    "architecture": "llama-3.3-70b-versatile",
    "scoring": "llama-3.3-70b-versatile",
}

# Runtime overrides (set via API or config)
_model_overrides: dict[str, str] = {}


def set_model(module_type: str, model_name: str) -> None:
    """Override the model for a specific module."""
    if module_type not in MODULE_TYPES:
        raise ValueError(f"Unknown module type: {module_type}. Valid: {MODULE_TYPES}")
    _model_overrides[module_type] = model_name
    logger.info(f"Model override: {module_type} → {model_name}")


def get_model(module_type: str) -> str:
    """Get the active model for a module type."""
    return _model_overrides.get(module_type, DEFAULT_MODELS.get(module_type, DEFAULT_MODELS["strategic_analysis"]))


def get_all_models() -> dict[str, str]:
    """Return the effective model for every module type."""
    return {mt: get_model(mt) for mt in MODULE_TYPES}


def generate_llm_output(
    module_type: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 800,
    temperature: float = 0.4,
    fallback: str = "",
) -> str:
    """
    Central LLM call via Groq — routes to the correct model for the given module.
    Returns raw text. Never raises — returns fallback on any failure.
    """
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        logger.info(f"[{module_type}] GROQ_API_KEY not configured — returning fallback.")
        return fallback

    model = get_model(module_type)
    try:
        from groq import Groq

        client = Groq(api_key=api_key)

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        result = completion.choices[0].message.content
        logger.info(f"[{module_type}] LLM response: {len(result)} chars (model={model})")
        return result

    except Exception as e:
        logger.warning(f"[{module_type}] LLM call failed ({type(e).__name__}: {e}), returning fallback.")
        return fallback
