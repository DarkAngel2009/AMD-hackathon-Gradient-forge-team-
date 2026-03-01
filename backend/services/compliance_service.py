"""Compliance Service — detects regulatory requirements from system description."""

import json
import logging
from services.model_registry import generate_llm_output

logger = logging.getLogger(__name__)

COMPLIANCE_SYSTEM_PROMPT = (
    "You are a compliance and regulatory expert for software systems.\n"
    "Analyze the system description and constraints to identify regulatory requirements.\n"
    "Reply in EXACTLY this JSON format (no markdown, no code fences):\n"
    "{\n"
    '  "compliance_requirements": ["GDPR", "HIPAA", ...],\n'
    '  "architectural_implications": "one paragraph explaining how these affect architecture",\n'
    '  "risk_flags": ["flag1", "flag2", ...]\n'
    "}"
)

# Keyword-based fallback detection
DOMAIN_RULES: dict[str, dict] = {
    "healthcare": {
        "keywords": ["health", "medical", "patient", "clinical", "hospital", "ehr", "hipaa", "pharma", "telemedicine"],
        "requirements": ["HIPAA", "SOC2"],
        "risks": ["PHI data exposure", "Audit trail gaps", "Cross-border data transfer"],
    },
    "fintech": {
        "keywords": ["finance", "banking", "payment", "trading", "fintech", "pci", "transaction", "wallet", "lending"],
        "requirements": ["PCI-DSS", "SOC2"],
        "risks": ["PCI scope creep", "Transaction audit gaps", "Key management complexity"],
    },
    "government": {
        "keywords": ["government", "federal", "public sector", "citizen", "defense", "military"],
        "requirements": ["SOC2", "GDPR"],
        "risks": ["Data sovereignty violations", "Access control gaps", "Clearance-level data handling"],
    },
    "ecommerce": {
        "keywords": ["ecommerce", "e-commerce", "shopping", "cart", "checkout", "retail", "store"],
        "requirements": ["PCI-DSS", "GDPR"],
        "risks": ["Payment data exposure", "Cookie consent violations", "Cross-border shipping data"],
    },
    "social": {
        "keywords": ["social", "chat", "messaging", "community", "user profile", "content", "media"],
        "requirements": ["GDPR"],
        "risks": ["User data retention", "Right to deletion compliance", "Content moderation liability"],
    },
}


def _detect_domain(description: str) -> list[str]:
    """Detect matching domains from keywords in the description."""
    desc_lower = description.lower()
    matched = []
    for domain, rules in DOMAIN_RULES.items():
        if any(kw in desc_lower for kw in rules["keywords"]):
            matched.append(domain)
    return matched


def _generate_fallback(system_input: dict) -> dict:
    """Deterministic fallback compliance check."""
    desc = system_input.get("system_description", "")
    domains = _detect_domain(desc)

    requirements = set()
    risk_flags = []

    for domain in domains:
        rules = DOMAIN_RULES[domain]
        requirements.update(rules["requirements"])
        risk_flags.extend(rules["risks"])

    # Default: always flag GDPR for any user-facing system
    if not requirements:
        requirements.add("GDPR")
        risk_flags.append("General data protection review recommended")

    users = system_input.get("expected_users", 0)
    if users > 100000:
        requirements.add("SOC2")
        risk_flags.append("High user volume requires robust audit logging")

    implications = (
        f"Detected domains: {', '.join(domains) if domains else 'general'}. "
        f"The system must comply with {', '.join(sorted(requirements))}. "
        f"Architecture should incorporate encryption at rest and in transit, "
        f"audit logging, access control, and data retention policies."
    )

    return {
        "compliance_requirements": sorted(requirements),
        "architectural_implications": implications,
        "risk_flags": risk_flags[:6],
    }


def run_compliance_check(system_input: dict) -> dict:
    """
    Analyze system description for compliance requirements.
    Uses LLM with deterministic fallback.
    """
    desc = system_input.get("system_description", "")
    users = system_input.get("expected_users", 0)

    user_prompt = (
        f"System Description: {desc}\n"
        f"Expected Users: {users}\n"
        f"Budget Sensitivity: {system_input.get('budget_sensitivity', 'medium')}\n"
        f"Fault Tolerance: {system_input.get('fault_tolerance', 'medium')}\n\n"
        "Identify all applicable compliance frameworks (GDPR, HIPAA, SOC2, PCI-DSS, etc.), "
        "explain architectural implications, and flag specific risks."
    )

    fallback = _generate_fallback(system_input)
    fallback_str = json.dumps(fallback)

    raw = generate_llm_output(
        module_type="compliance",
        system_prompt=COMPLIANCE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=600,
        fallback=fallback_str,
    )

    # Try to parse LLM response as JSON
    try:
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        result = json.loads(cleaned)
        # Validate expected keys
        if "compliance_requirements" in result and "architectural_implications" in result:
            return result
    except (json.JSONDecodeError, KeyError, IndexError):
        pass

    return fallback
