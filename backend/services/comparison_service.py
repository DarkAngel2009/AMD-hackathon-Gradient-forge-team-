"""Comparison Service — ranks architectures and generates trade-off reasoning."""

from typing import Optional
from models.input_models import SystemInput, SensitivityLevel, TimeToMarket
from models.architecture_models import ArchitectureResult, ComparisonResult
from services.llm_reasoning_service import (
    generate_llm_analysis,
    generate_trade_off_llm,
    generate_recommendation_llm,
)


def _generate_trade_off(a: ArchitectureResult, rank: int, system_input: dict | None = None) -> str:
    """Generate trade-off reasoning for one architecture — LLM with deterministic fallback."""
    if system_input:
        arch_dict = a.model_dump() if hasattr(a, "model_dump") else a.dict()
        return generate_trade_off_llm(arch_dict, rank, system_input)

    # Pure deterministic fallback
    s = a.scores
    name = a.architecture.name
    style = a.architecture.style

    strengths = []
    weaknesses = []

    if s.latency >= 70:
        strengths.append("low latency")
    if s.scalability >= 75:
        strengths.append("high scalability")
    if s.resilience >= 75:
        strengths.append("strong resilience")
    if s.operational_complexity <= 35:
        strengths.append("low operational overhead")
    if s.infrastructure_cost <= 35:
        strengths.append("cost-efficient")

    if s.latency < 55:
        weaknesses.append("higher latency")
    if s.scalability < 45:
        weaknesses.append("limited scalability")
    if s.resilience < 50:
        weaknesses.append("weaker fault tolerance")
    if s.operational_complexity >= 65:
        weaknesses.append("high operational complexity")
    if s.infrastructure_cost >= 60:
        weaknesses.append("higher infrastructure cost")

    lines = [f"**#{rank} — {name}** (Overall Score: {a.overall_score})"]
    if strengths:
        lines.append(f"  Strengths: {', '.join(strengths)}.")
    if weaknesses:
        lines.append(f"  Trade-offs: {', '.join(weaknesses)}.")

    insights = {
        "monolith": "Best suited for small teams that need to ship fast with minimal DevOps overhead. "
                    "Becomes a liability as the system and team grow.",
        "microservices": "Enables independent deployment and team autonomy, but demands mature CI/CD, "
                         "observability, and distributed-systems expertise.",
        "event_driven": "Excels at decoupled, auditable workflows and real-time processing. "
                        "Requires investment in event schema management and eventual-consistency handling.",
        "serverless": "Minimizes operational burden and aligns cost to usage. "
                      "Watch for cold-start latency, vendor lock-in, and debugging complexity.",
    }
    lines.append(f"  Insight: {insights.get(style, '')}")

    return " ".join(lines)


def _generate_recommendation(rankings: list[ArchitectureResult], system_input: dict | None = None) -> str:
    """Generate a recommendation — LLM with deterministic fallback."""
    if system_input:
        ranked_dicts = [
            r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in rankings
        ]
        return generate_recommendation_llm(ranked_dicts, system_input)

    # Pure deterministic fallback
    top = rankings[0]
    runner = rankings[1] if len(rankings) > 1 else None

    text = (
        f"Based on the weighted analysis, **{top.architecture.name}** is the recommended architecture "
        f"with an overall score of {top.overall_score}. "
    )

    if runner:
        diff = round(top.overall_score - runner.overall_score, 2)
        if diff < 3:
            text += (
                f"However, **{runner.architecture.name}** (score: {runner.overall_score}) is a very close "
                f"alternative — the difference of just {diff} points means both are viable depending on "
                f"team expertise and organizational priorities. "
            )
        else:
            text += (
                f"It leads **{runner.architecture.name}** by {diff} points, showing a clear advantage "
                f"under the given constraints. "
            )

    text += (
        "Consider your team's experience, existing infrastructure, and growth trajectory "
        "when making the final decision."
    )
    return text


def detect_constraint_tension(inp: SystemInput) -> Optional[str]:
    """Detect conflicting constraint combinations that create architectural tension."""
    if (
        inp.expected_users > 150000
        and inp.budget_sensitivity == SensitivityLevel.LOW
        and inp.fault_tolerance == SensitivityLevel.HIGH
        and inp.time_to_market == TimeToMarket.FAST
    ):
        return (
            "⚠ High scalability + low budget sensitivity + high reliability + fast time-to-market "
            "create architectural tension. No single architecture fully satisfies all constraints. "
            "Consider phased delivery or accepting trade-offs in one dimension."
        )
    return None


def compare(
    results: list[ArchitectureResult],
    inp: Optional[SystemInput] = None,
) -> ComparisonResult:
    """Rank architectures by overall score and generate trade-off reasoning."""
    # Sort descending by overall_score
    ranked = sorted(results, key=lambda r: r.overall_score, reverse=True)

    # Get system_input dict for LLM-driven reasoning
    inp_dict = None
    if inp is not None:
        inp_dict = inp.model_dump() if hasattr(inp, "model_dump") else inp.dict()

    trade_offs = [
        _generate_trade_off(arch, rank + 1, inp_dict) for rank, arch in enumerate(ranked)
    ]

    recommendation = _generate_recommendation(ranked, inp_dict)

    # Constraint tension detection
    tension_warning = None
    if inp is not None:
        tension_warning = detect_constraint_tension(inp)

    comparison = ComparisonResult(
        rankings=ranked,
        trade_off_reasoning=trade_offs,
        recommendation=recommendation,
        constraint_tension_warning=tension_warning,
    )

    # LLM strategic analysis
    llm_analysis = None
    if inp is not None:
        results_dicts = [
            r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in ranked
        ]
        cmp_dict = comparison.model_dump() if hasattr(comparison, "model_dump") else comparison.dict()
        llm_analysis = generate_llm_analysis(inp_dict, results_dicts, cmp_dict)

    comparison.llm_analysis = llm_analysis
    return comparison
