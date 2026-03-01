"""LLM Reasoning Service — contextual AI analysis via model registry."""

import logging
from services.model_registry import generate_llm_output

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior distributed systems architect.\n"
    "Analyze the provided architecture comparison objectively.\n"
    "Avoid generic statements.\n"
    "Base reasoning strictly on the given metrics and constraints.\n"
    "Explain trade-offs clearly and concisely.\n\n"
    "Reply in EXACTLY this format with these three plain-text section headers\n"
    "(NO # or ## markdown prefix, just the text followed by a colon):\n\n"
    "EXECUTIVE SUMMARY:\n"
    "<your 3-4 sentence summary of why the top architecture won>\n\n"
    "RISK ANALYSIS:\n"
    "<your 3-4 sentence analysis of hidden risks in the top pick>\n\n"
    "STRATEGIC ADVICE:\n"
    "<your 3-4 sentence advice on when the ranking might change>\n\n"
    "RULES:\n"
    "- Do NOT use markdown headers (# or ##). Use plain text headers as shown above.\n"
    "- Each section must have substantive content, not placeholders.\n"
    "- Keep each section to 3-5 sentences maximum.\n"
    "- Do NOT combine sections or repeat content across sections.\n"
)

TRADE_OFF_SYSTEM_PROMPT = (
    "You are a senior distributed systems architect.\n"
    "Generate a concise trade-off analysis for the given architecture.\n"
    "Include specific strengths, weaknesses, and a style-specific insight.\n"
    "Be direct and data-driven based on the provided scores.\n"
    "Reply in plain text (2-3 sentences). Start with the rank and name."
)

RECOMMENDATION_SYSTEM_PROMPT = (
    "You are a senior distributed systems architect.\n"
    "Write a concise recommendation paragraph (3-4 sentences) explaining:\n"
    "1) Why the top architecture won.\n"
    "2) How close the runner-up is.\n"
    "3) What factors might change the decision.\n"
    "Be specific to the given data. Reply in plain text only."
)


def _build_prompt(system_input, architecture_results, comparison_result) -> str:
    """Build a structured analysis prompt from the engine data."""
    lines = [
        f"System: {system_input.get('system_description', 'N/A')}",
        f"Expected Users: {system_input.get('expected_users', 'N/A')}",
        f"Budget Sensitivity: {system_input.get('budget_sensitivity', 'N/A')}",
        f"Fault Tolerance: {system_input.get('fault_tolerance', 'N/A')}",
        f"Time to Market: {system_input.get('time_to_market', 'N/A')}",
        "",
        "Priority Weights:",
        f"  Cost: {system_input.get('cost_weight', 3)}/5",
        f"  Scalability: {system_input.get('scalability_weight', 3)}/5",
        f"  Speed: {system_input.get('speed_weight', 3)}/5",
        f"  Reliability: {system_input.get('reliability_weight', 3)}/5",
        "",
        "Architecture Metrics:",
    ]

    for r in architecture_results:
        arch = r if isinstance(r, dict) else r.dict()
        a = arch.get("architecture", arch)
        s = arch.get("scores", {})
        lines.append(
            f"  {a.get('name', '?')} (style={a.get('style', '?')}) — "
            f"Overall={arch.get('overall_score', '?')} | "
            f"Latency={s.get('latency', '?')} | "
            f"Scalability={s.get('scalability', '?')} | "
            f"OpComplexity={s.get('operational_complexity', '?')} | "
            f"InfraCost={s.get('infrastructure_cost', '?')} | "
            f"Resilience={s.get('resilience', '?')}"
        )

    rankings = comparison_result if isinstance(comparison_result, dict) else comparison_result.dict()
    ranked_names = [
        r.get("architecture", {}).get("name", "?") for r in rankings.get("rankings", [])
    ]
    lines.append(f"\nFinal Ranking: {' > '.join(ranked_names)}")
    lines.append(f"Recommendation: {rankings.get('recommendation', 'N/A')}")

    tension = rankings.get("constraint_tension_warning")
    if tension:
        lines.append(f"\n⚠ Constraint Tension: {tension}")

    lines.append(
        "\nProvide: 1) Executive Summary of why the top architecture won, "
        "2) Risk Analysis highlighting hidden risks, "
        "3) Strategic Advice on when the ranking might change."
    )

    return "\n".join(lines)


def _parse_llm_response(text: str) -> dict:
    """Parse the LLM text into structured sections."""
    result = {
        "executive_summary": "",
        "risk_analysis": "",
        "strategic_advice": "",
    }

    current_key = None
    current_lines = []

    for line in text.split("\n"):
        # Strip markdown header chars (# ## ###) before checking section names
        cleaned = line.strip().lstrip("#").strip()
        upper = cleaned.upper()

        if upper.startswith("EXECUTIVE SUMMARY"):
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = "executive_summary"
            current_lines = []
        elif upper.startswith("RISK ANALYSIS"):
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = "risk_analysis"
            current_lines = []
        elif upper.startswith("STRATEGIC ADVICE"):
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = "strategic_advice"
            current_lines = []
        else:
            current_lines.append(line)

    if current_key:
        result[current_key] = "\n".join(current_lines).strip()

    # If parsing found nothing, put the whole response in executive_summary
    if not any(result.values()):
        result["executive_summary"] = text.strip()

    return result


def _generate_fallback(system_input, architecture_results, comparison_result) -> dict:
    """Deterministic fallback when LLM is unavailable."""
    rankings = comparison_result if isinstance(comparison_result, dict) else comparison_result.dict()
    ranked = rankings.get("rankings", [])

    if not ranked:
        return {
            "executive_summary": "No architectures to analyze.",
            "risk_analysis": "N/A",
            "strategic_advice": "N/A",
        }

    top = ranked[0]
    top_name = top.get("architecture", {}).get("name", "Unknown")
    top_style = top.get("architecture", {}).get("style", "unknown")
    top_score = top.get("overall_score", 0)

    runner = ranked[1] if len(ranked) > 1 else None
    runner_name = runner.get("architecture", {}).get("name", "N/A") if runner else "N/A"

    return {
        "executive_summary": (
            f"{top_name} leads with a score of {top_score}, driven by its "
            f"inherent strengths as a {top_style} architecture under the given constraints."
        ),
        "risk_analysis": (
            f"The {top_style} approach may face challenges at extreme scale or under "
            f"shifting constraint priorities. Monitor operational complexity and cost "
            f"trends as the system evolves."
        ),
        "strategic_advice": (
            f"If priorities shift significantly, {runner_name} could become the preferred "
            f"option. Re-evaluate when user load doubles or budget constraints change."
        ),
    }


def generate_llm_analysis(system_input, architecture_results, comparison_result) -> dict:
    """
    Generate AI-powered strategic analysis.
    Falls back to deterministic explanation if LLM is unavailable.
    """
    prompt = _build_prompt(system_input, architecture_results, comparison_result)
    fallback = _generate_fallback(system_input, architecture_results, comparison_result)

    raw = generate_llm_output(
        module_type="strategic_analysis",
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
        max_tokens=800,
        temperature=0.5,
        fallback="",
    )

    if not raw:
        return fallback

    parsed = _parse_llm_response(raw)

    # If parsing returned mostly empty, use the raw text as executive summary
    if not parsed["executive_summary"] and not parsed["risk_analysis"]:
        parsed["executive_summary"] = raw.strip()

    return parsed


def generate_trade_off_llm(arch_data: dict, rank: int, system_input: dict) -> str:
    """Generate LLM-powered trade-off analysis for a single architecture."""
    a = arch_data.get("architecture", {})
    s = arch_data.get("scores", {})

    user_prompt = (
        f"Architecture: #{rank} — {a.get('name', '?')} (style={a.get('style', '?')})\n"
        f"Overall Score: {arch_data.get('overall_score', '?')}\n"
        f"Scores — Latency: {s.get('latency', '?')}, Scalability: {s.get('scalability', '?')}, "
        f"OpComplexity: {s.get('operational_complexity', '?')}, InfraCost: {s.get('infrastructure_cost', '?')}, "
        f"Resilience: {s.get('resilience', '?')}\n"
        f"System: {system_input.get('system_description', 'N/A')}\n"
        f"Users: {system_input.get('expected_users', 'N/A')}"
    )

    # Deterministic fallback
    fallback_parts = [f"**#{rank} — {a.get('name', '?')}** (Overall Score: {arch_data.get('overall_score', '?')})"]
    strengths, weaknesses = [], []
    lat = s.get("latency", 50)
    scl = s.get("scalability", 50)
    res = s.get("resilience", 50)
    opc = s.get("operational_complexity", 50)
    cost = s.get("infrastructure_cost", 50)

    if lat >= 70: strengths.append("low latency")
    if scl >= 75: strengths.append("high scalability")
    if res >= 75: strengths.append("strong resilience")
    if opc <= 35: strengths.append("low operational overhead")
    if cost <= 35: strengths.append("cost-efficient")
    if lat < 55: weaknesses.append("higher latency")
    if scl < 45: weaknesses.append("limited scalability")
    if res < 50: weaknesses.append("weaker fault tolerance")
    if opc >= 65: weaknesses.append("high operational complexity")
    if cost >= 60: weaknesses.append("higher infrastructure cost")

    if strengths: fallback_parts.append(f"Strengths: {', '.join(strengths)}.")
    if weaknesses: fallback_parts.append(f"Trade-offs: {', '.join(weaknesses)}.")
    fallback_str = " ".join(fallback_parts)

    result = generate_llm_output(
        module_type="trade_off",
        system_prompt=TRADE_OFF_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=250,
        temperature=0.5,
        fallback=fallback_str,
    )

    return result.strip() if result.strip() else fallback_str


def generate_recommendation_llm(ranked_data: list, system_input: dict) -> str:
    """Generate LLM-powered recommendation."""
    if not ranked_data:
        return "No architectures to recommend."

    top = ranked_data[0]
    top_name = top.get("architecture", {}).get("name", "?")
    top_score = top.get("overall_score", 0)

    lines = ["Ranked architectures:"]
    for i, r in enumerate(ranked_data):
        a = r.get("architecture", {})
        lines.append(f"  #{i+1}: {a.get('name', '?')} (score={r.get('overall_score', '?')}, style={a.get('style', '?')})")
    lines.append(f"\nSystem: {system_input.get('system_description', 'N/A')}")
    lines.append(f"Users: {system_input.get('expected_users', 'N/A')}")

    runner = ranked_data[1] if len(ranked_data) > 1 else None
    runner_name = runner.get("architecture", {}).get("name", "N/A") if runner else "N/A"
    diff = round(top_score - (runner.get("overall_score", 0) if runner else 0), 2)

    fallback = (
        f"Based on the weighted analysis, **{top_name}** is the recommended architecture "
        f"with an overall score of {top_score}. "
    )
    if runner and diff < 3:
        fallback += (
            f"However, **{runner_name}** (score: {runner.get('overall_score', '?')}) is a very close "
            f"alternative — the difference of just {diff} points means both are viable. "
        )
    elif runner:
        fallback += f"It leads **{runner_name}** by {diff} points under the given constraints. "
    fallback += "Consider your team's experience and growth trajectory when making the final decision."

    result = generate_llm_output(
        module_type="trade_off",
        system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
        user_prompt="\n".join(lines),
        max_tokens=300,
        temperature=0.5,
        fallback=fallback,
    )

    return result.strip() if result.strip() else fallback
