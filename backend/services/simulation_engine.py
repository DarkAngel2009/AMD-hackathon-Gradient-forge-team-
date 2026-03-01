"""Simulation Engine — fully LLM-driven multi-factor scoring with unbiased fallback."""

import json
import math
import logging
from models.input_models import SystemInput, SensitivityLevel, TimeToMarket
from models.architecture_models import Architecture, SimulationScores
from services.model_registry import generate_llm_output

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════
#  Comprehensive LLM Scoring Prompt
# ═══════════════════════════════════════

SCORING_SYSTEM_PROMPT = (
    "You are an expert system architect, performance analyst, and cloud cost engineer.\n"
    "You have NO preference for any architecture style. You evaluate purely on technical merit\n"
    "for the SPECIFIC system described.\n\n"
    "TASK: Score the given architecture on 5 metrics (0–100) using deep multi-factor analysis.\n\n"
    "EVALUATION FRAMEWORK — consider ALL of these factors for EACH metric:\n\n"
    "LATENCY (higher = faster/better response time):\n"
    "  - Cold-start latency risk for this architecture\n"
    "  - WebSocket connection setup overhead at the specified concurrency\n"
    "  - Inter-service communication hops and serialization cost\n"
    "  - Database query path length and caching effectiveness\n"
    "  - Network round trips for a single user request\n"
    "  - Sustained vs burst latency under the given user load\n\n"
    "SCALABILITY (higher = handles more growth):\n"
    "  - Horizontal scalability ceiling for the specified user count\n"
    "  - WebSocket concurrency handling — max connections per node/service\n"
    "  - Message fan-out cost at scale\n"
    "  - Connection sharding or presence tracking needs\n"
    "  - Sustained throughput efficiency under 100k+ concurrency\n"
    "  - Database scaling approach and bottleneck risk\n"
    "  - Auto-scaling speed and granularity\n\n"
    "OPERATIONAL_COMPLEXITY (higher = MORE complex to operate, which is worse):\n"
    "  - Number of independently deployable units\n"
    "  - Monitoring, logging, and debugging overhead\n"
    "  - Configuration management burden\n"
    "  - Team expertise requirements\n"
    "  - CI/CD pipeline complexity\n"
    "  - Time to set up from scratch\n\n"
    "INFRASTRUCTURE_COST (higher = MORE expensive, which is worse):\n"
    "  - Estimated cost per 1M messages at this architecture\n"
    "  - Estimated cost per 10k concurrent connections\n"
    "  - Serverless sustained-load cost vs containerized infrastructure cost\n"
    "  - Database cost at the stated user volume\n"
    "  - Idle cost when traffic drops (wasteful over-provisioning)\n"
    "  - Network egress and data transfer costs\n\n"
    "RESILIENCE (higher = more fault tolerant):\n"
    "  - Multi-region failover capability\n"
    "  - Blast radius of a single component failure\n"
    "  - Data durability and recovery mechanisms\n"
    "  - Graceful degradation under partial failure\n"
    "  - Zero-downtime deployment capability\n\n"
    "COMPLIANCE PENALTIES — subtract from relevant scores when:\n"
    "  - Architecture lacks explicit WebSocket scaling at the specified concurrency → penalize scalability\n"
    "  - GDPR/CCPA detected but no regional data isolation described → penalize resilience\n"
    "  - Missing encryption, audit logging, or deletion workflows → penalize resilience\n"
    "  - No circuit breaker or retry logic for distributed calls → penalize resilience\n\n"
    "CRITICAL RULES:\n"
    "- DO NOT favor any architecture by default. Monolith CAN score highest if constraints favor it.\n"
    "- Event-Driven SHOULD score highest for sustained throughput workloads.\n"
    "- Serverless should be PENALIZED for sustained high-concurrency WebSocket workloads (cold starts, connection limits).\n"
    "- Monolith should score WELL for low user counts with simple deployment needs.\n"
    "- Base ALL scores on the SPECIFIC system, user count, and constraints provided.\n"
    "- Scores must differ meaningfully between architectures — no identical scores.\n\n"
    "ALSO PROVIDE a scoring_breakdown object explaining the key reasoning for each metric.\n\n"
    "Return ONLY valid JSON in this exact format:\n"
    "{\n"
    '  "latency": 72.5,\n'
    '  "scalability": 85.0,\n'
    '  "operational_complexity": 45.0,\n'
    '  "infrastructure_cost": 55.0,\n'
    '  "resilience": 78.0,\n'
    '  "scoring_breakdown": {\n'
    '    "latency_reasoning": "one sentence explaining the latency score",\n'
    '    "scalability_reasoning": "one sentence explaining the scalability score",\n'
    '    "cost_reasoning": "one sentence explaining the cost score",\n'
    '    "resilience_reasoning": "one sentence explaining the resilience score",\n'
    '    "websocket_assessment": "how well this architecture handles WebSocket at stated concurrency",\n'
    '    "cost_estimate": "estimated monthly cost range at stated concurrency"\n'
    "  }\n"
    "}\n\n"
    "Return ONLY the JSON. No markdown fences, no explanations outside the JSON.\n"
)


def _build_scoring_prompt(architecture: Architecture, inp: SystemInput) -> str:
    """Build comprehensive prompt with full system context for LLM scoring."""
    # Detect compliance requirements from system description
    desc_lower = inp.system_description.lower()
    compliance_flags = []
    if any(w in desc_lower for w in ["gdpr", "europe", "eu", "privacy"]):
        compliance_flags.append("GDPR")
    if any(w in desc_lower for w in ["ccpa", "california", "cpra"]):
        compliance_flags.append("CCPA")
    if any(w in desc_lower for w in ["soc2", "soc 2", "audit"]):
        compliance_flags.append("SOC2")
    if any(w in desc_lower for w in ["hipaa", "health", "medical"]):
        compliance_flags.append("HIPAA")
    if any(w in desc_lower for w in ["pci", "payment", "credit card"]):
        compliance_flags.append("PCI-DSS")

    # Detect traffic pattern from description
    traffic_pattern = "unknown"
    if any(w in desc_lower for w in ["real-time", "realtime", "chat", "websocket", "streaming", "live"]):
        traffic_pattern = "sustained high-concurrency (WebSocket/real-time)"
    elif any(w in desc_lower for w in ["batch", "scheduled", "cron", "periodic"]):
        traffic_pattern = "batch/periodic processing"
    elif any(w in desc_lower for w in ["api", "rest", "request-response"]):
        traffic_pattern = "request-response (HTTP API)"
    elif any(w in desc_lower for w in ["spike", "burst", "flash"]):
        traffic_pattern = "spiky/burst traffic"

    compliance_str = ", ".join(compliance_flags) if compliance_flags else "None explicitly detected"

    return (
        f"=== SYSTEM CONTEXT ===\n"
        f"System: {inp.system_description}\n"
        f"Expected Concurrent Users: {inp.expected_users:,}\n"
        f"Traffic Pattern: {traffic_pattern}\n"
        f"Budget Sensitivity: {inp.budget_sensitivity.value} (low=generous, high=tight)\n"
        f"Fault Tolerance: {inp.fault_tolerance.value}\n"
        f"Time to Market: {inp.time_to_market.value}\n"
        f"Compliance Requirements: {compliance_str}\n\n"
        f"=== ARCHITECTURE TO EVALUATE ===\n"
        f"Name: {architecture.name}\n"
        f"Style: {architecture.style}\n"
        f"Description: {architecture.description}\n"
        f"Components: {', '.join(architecture.component_diagram.nodes)}\n"
        f"Database Strategy: {architecture.database_strategy}\n"
        f"Communication Model: {architecture.communication_model}\n"
        f"Scaling Model: {architecture.scaling_model}\n"
        f"Failure Domain Analysis: {architecture.failure_domain_analysis}\n\n"
        f"=== SCORING INSTRUCTIONS ===\n"
        f"Score this {architecture.style} architecture for a system serving "
        f"{inp.expected_users:,} concurrent users with {traffic_pattern} traffic.\n"
        f"Budget: {inp.budget_sensitivity.value}. Fault tolerance: {inp.fault_tolerance.value}.\n"
        f"Compliance: {compliance_str}.\n\n"
        f"Think carefully about:\n"
        f"- Can this architecture handle {inp.expected_users:,} WebSocket connections efficiently?\n"
        f"- What is the realistic monthly cost at this concurrency?\n"
        f"- How does cold-start latency affect real-time user experience?\n"
        f"- Does this architecture support multi-region failover?\n"
        f"- Is the operational complexity justified for the team size?\n\n"
        f"Return the JSON scores."
    )


def _parse_llm_scores(raw: str) -> tuple[SimulationScores | None, dict | None]:
    """Try to parse LLM output into SimulationScores + optional breakdown."""
    try:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        data = json.loads(text)

        required = ["latency", "scalability", "operational_complexity", "infrastructure_cost", "resilience"]
        scores = {}
        for key in required:
            val = float(data.get(key, -1))
            if val < 0 or val > 100:
                logger.warning(f"[scoring] Invalid score for {key}: {val}")
                return None, None
            scores[key] = round(val, 1)

        breakdown = data.get("scoring_breakdown", None)
        return SimulationScores(**scores), breakdown

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        logger.warning(f"[scoring] Failed to parse LLM scores: {e}")
        return None, None


# ═══════════════════════════════════════
#  Unbiased Deterministic Fallback
# ═══════════════════════════════════════
# No architecture is inherently favored. Scores are computed
# from neutral baselines + dynamic adjustments based on constraints.

def _fallback_simulate(architecture: Architecture, inp: SystemInput) -> SimulationScores:
    """Unbiased formula-based scoring — no architecture is default-favored."""
    style = architecture.style
    users = inp.expected_users

    # Neutral starting point — all architectures start equal
    scores = {
        "latency": 65.0,
        "scalability": 65.0,
        "operational_complexity": 50.0,
        "infrastructure_cost": 50.0,
        "resilience": 65.0,
    }

    # ── Dynamic adjustments based on architecture characteristics ──

    if style == "monolith":
        # Monolith: great latency (no network hops), low complexity, poor at extreme scale
        scores["latency"] += 15          # In-process calls are fast
        scores["operational_complexity"] -= 20  # Simple to deploy
        scores["infrastructure_cost"] -= 10     # Single deployment = cheaper

        # Scale penalty grows with user count
        if users > 10000:
            scale_penalty = min(30, math.log10(users / 10000) * 15)
            scores["scalability"] -= scale_penalty
        if users > 100000:
            scores["resilience"] -= 15  # Single point of failure at massive scale
        else:
            scores["resilience"] += 5   # Simple = fewer things to go wrong

    elif style == "microservices":
        # Microservices: good scale, high ops complexity, moderate cost
        scores["scalability"] += 15
        scores["resilience"] += 10
        scores["operational_complexity"] += 20  # Many moving parts
        scores["infrastructure_cost"] += 10     # Multiple services = more infra
        scores["latency"] -= 10                 # Network hops between services

        if users < 5000:
            scores["operational_complexity"] += 10  # Overkill for small scale

    elif style == "event_driven":
        # Event-Driven: excellent throughput, good resilience, moderate complexity
        scores["scalability"] += 12
        scores["resilience"] += 15             # Loose coupling = isolated failures
        scores["operational_complexity"] += 15  # Event choreography is complex
        scores["latency"] -= 5                 # Async adds some latency
        scores["infrastructure_cost"] += 5     # Event bus infra

        if users > 50000:
            scores["scalability"] += 5  # Shines at sustained throughput

    elif style == "serverless":
        # Serverless: auto-scale, low idle cost, but cold-start + connection limits
        scores["scalability"] += 10
        scores["operational_complexity"] -= 10  # Managed infra

        # Cold-start penalty for real-time workloads
        desc_lower = inp.system_description.lower()
        is_realtime = any(w in desc_lower for w in ["chat", "real-time", "realtime", "websocket", "streaming"])
        if is_realtime:
            scores["latency"] -= 15          # Cold starts hurt real-time
            scores["scalability"] -= 10      # WebSocket connection limits

        # Cost: cheap at low volume, expensive at sustained high volume
        if users > 50000:
            scores["infrastructure_cost"] += 15  # Sustained load = expensive serverless
        else:
            scores["infrastructure_cost"] -= 15  # Low volume = cheap

        if users > 100000:
            scores["infrastructure_cost"] += 10  # Gets very expensive at scale

    # ── Budget sensitivity adjustments ──
    if inp.budget_sensitivity == SensitivityLevel.HIGH:
        # Tight budget: penalize expensive architectures more
        if style in ("microservices", "event_driven"):
            scores["infrastructure_cost"] += 8
        if style == "monolith":
            scores["infrastructure_cost"] -= 8  # Monolith is cheapest

    # ── Fault tolerance adjustments ──
    if inp.fault_tolerance == SensitivityLevel.HIGH:
        if style == "monolith":
            scores["resilience"] -= 12  # Single point of failure
        elif style == "event_driven":
            scores["resilience"] += 5   # Event sourcing = great recovery

    # ── Time to market adjustments ──
    if inp.time_to_market == TimeToMarket.FAST:
        if style == "monolith":
            scores["operational_complexity"] -= 10  # Fastest to ship
        elif style == "microservices":
            scores["operational_complexity"] += 10  # Slowest to set up

    # Clamp all values
    for key in scores:
        scores[key] = max(0, min(100, round(scores[key], 1)))

    return SimulationScores(**scores)


# ═══════════════════════════════════════
#  Main API
# ═══════════════════════════════════════

# Store scoring breakdowns for frontend display
_scoring_breakdowns: dict[str, dict] = {}


def get_scoring_breakdown(arch_name: str) -> dict | None:
    """Retrieve the scoring breakdown for an architecture."""
    return _scoring_breakdowns.get(arch_name)


def get_all_breakdowns() -> dict[str, dict]:
    """Retrieve all scoring breakdowns."""
    return dict(_scoring_breakdowns)


def simulate(architecture: Architecture, inp: SystemInput) -> SimulationScores:
    """Score an architecture using LLM, with unbiased formula-based fallback."""
    fallback_scores = _fallback_simulate(architecture, inp)

    # Build fallback JSON
    fallback_json = json.dumps({
        "latency": fallback_scores.latency,
        "scalability": fallback_scores.scalability,
        "operational_complexity": fallback_scores.operational_complexity,
        "infrastructure_cost": fallback_scores.infrastructure_cost,
        "resilience": fallback_scores.resilience,
    })

    user_prompt = _build_scoring_prompt(architecture, inp)

    raw = generate_llm_output(
        module_type="scoring",
        system_prompt=SCORING_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=600,
        temperature=0.3,
        fallback=fallback_json,
    )

    # Try LLM scores
    llm_scores, breakdown = _parse_llm_scores(raw)
    if llm_scores:
        logger.info(f"[scoring] LLM scores accepted for {architecture.name}")
        if breakdown:
            _scoring_breakdowns[architecture.name] = breakdown
        return llm_scores

    logger.warning(f"[scoring] Using formula fallback for {architecture.name}")
    # Generate basic breakdown for fallback
    _scoring_breakdowns[architecture.name] = {
        "latency_reasoning": f"Formula-based: {architecture.style} baseline with user-count adjustments",
        "scalability_reasoning": f"Formula-based: {architecture.style} scaling characteristics for {inp.expected_users:,} users",
        "cost_reasoning": f"Formula-based: {architecture.style} infrastructure cost with {inp.budget_sensitivity.value} budget",
        "resilience_reasoning": f"Formula-based: {architecture.style} fault tolerance with {inp.fault_tolerance.value} requirements",
        "websocket_assessment": "Deterministic fallback — no WebSocket-specific analysis",
        "cost_estimate": "Deterministic fallback — no cost estimate available",
    }
    return fallback_scores


def compute_overall_score(scores: SimulationScores, inp: SystemInput) -> float:
    """
    Weighted average using user priority weights.
    For cost and complexity, invert so lower = better.
    Best Pick is determined PURELY by this computed score.
    """
    inverted_complexity = 100 - scores.operational_complexity
    inverted_cost = 100 - scores.infrastructure_cost

    w_speed = inp.speed_weight
    w_scale = inp.scalability_weight
    w_cost = inp.cost_weight
    w_rel = inp.reliability_weight
    w_complexity = w_speed * 0.5

    total_weight = w_speed + w_scale + w_cost + w_rel + w_complexity

    if total_weight == 0:
        weighted = (
            scores.latency * 0.20
            + scores.scalability * 0.25
            + inverted_complexity * 0.15
            + inverted_cost * 0.15
            + scores.resilience * 0.25
        )
        return round(weighted, 2)

    weighted = (
        scores.latency * w_speed
        + scores.scalability * w_scale
        + inverted_cost * w_cost
        + scores.resilience * w_rel
        + inverted_complexity * w_complexity
    ) / total_weight

    return round(max(0, min(100, weighted)), 2)
