"""SRS Generator — produces a Software Requirements Specification document via LLM."""

import logging
from services.model_registry import generate_llm_output

logger = logging.getLogger(__name__)

SRS_SYSTEM_PROMPT = (
    "You are a senior software architect writing an IEEE-style Software Requirements "
    "Specification (SRS) document. Write professional, detailed Markdown.\n\n"
    "STRUCTURE — use these EXACT section numbers and headings (do NOT duplicate or reorder):\n\n"
    "# Software Requirements Specification\n"
    "## 1. Introduction\n"
    "### 1.1 Purpose\n"
    "### 1.2 Scope\n"
    "### 1.3 Definitions, Acronyms, and Abbreviations\n"
    "## 2. Overall Description\n"
    "### 2.1 Product Perspective\n"
    "### 2.2 User Classes and Characteristics\n"
    "### 2.3 Operating Environment\n"
    "## 3. Functional Requirements\n"
    "  Number every requirement as FR-1, FR-2, … with a bold title and one-line description.\n"
    "  Include at least 8 requirements tailored to the SPECIFIC system described.\n"
    "## 4. Non-Functional Requirements\n"
    "### 4.1 Performance Requirements\n"
    "### 4.2 Security Requirements\n"
    "### 4.3 Scalability Requirements\n"
    "### 4.4 Availability & Fault Tolerance\n"
    "  Number every requirement as NFR-1, NFR-2, … with measurable targets.\n"
    "## 5. System Architecture Overview\n"
    "### 5.1 Architecture Style\n"
    "### 5.2 Component Breakdown\n"
    "  Describe each service/component in a bullet list with its database and communication approach.\n"
    "### 5.3 Data Storage Strategy\n"
    "## 6. Risk Analysis\n"
    "### 6.1 Technical Risks\n"
    "### 6.2 Business Risks\n"
    "  Number risks as R-1, R-2, … with mitigation strategies.\n"
    "## 7. Assumptions and Dependencies\n"
    "## 8. Constraints\n\n"
    "RULES:\n"
    "- Tailor EVERY section to the specific system described — no generic boilerplate.\n"
    "- Include specific technologies, protocols, databases, and frameworks relevant to the system.\n"
    "- Functional requirements must directly relate to the system's domain.\n"
    "- Non-functional requirements must have measurable, numeric targets.\n"
    "- Architecture section must reference the recommended architecture from the analysis.\n"
    "- Be thorough but concise. Each section should have real substance.\n"
    "- Do NOT repeat sections. Each heading appears exactly once.\n"
    "- Output only the Markdown document, no preamble or commentary.\n"
)


def _build_srs_prompt(system_input: dict, architecture_results: list, comparison_result: dict) -> str:
    """Build the prompt with full context for SRS generation."""
    lines = [
        f"System: {system_input.get('system_description', 'N/A')}",
        f"Expected Users: {system_input.get('expected_users', 'N/A')}",
        f"Budget Sensitivity: {system_input.get('budget_sensitivity', 'N/A')}",
        f"Fault Tolerance: {system_input.get('fault_tolerance', 'N/A')}",
        f"Time to Market: {system_input.get('time_to_market', 'N/A')}",
        "",
        "Architectures Evaluated:",
    ]

    for r in architecture_results:
        arch = r if isinstance(r, dict) else r
        a = arch.get("architecture", arch)
        s = arch.get("scores", {})
        lines.append(
            f"  - {a.get('name', '?')} (style={a.get('style', '?')}) | "
            f"Score={arch.get('overall_score', '?')} | "
            f"DB: {a.get('database_strategy', 'N/A')}"
        )

    if comparison_result:
        rankings = comparison_result if isinstance(comparison_result, dict) else comparison_result
        ranked_names = [
            r.get("architecture", {}).get("name", "?") for r in rankings.get("rankings", [])
        ]
        lines.append(f"\nRecommended Ranking: {' > '.join(ranked_names)}")
        lines.append(f"Recommendation: {rankings.get('recommendation', 'N/A')}")

    lines.append("\nGenerate a complete, detailed SRS document for this system following the exact structure specified.")
    return "\n".join(lines)


def _generate_fallback(system_input: dict, architecture_results: list, comparison_result: dict) -> str:
    """Deterministic SRS fallback template."""
    desc = system_input.get("system_description", "System")
    users = system_input.get("expected_users", "N/A")
    budget = system_input.get("budget_sensitivity", "medium")
    ft = system_input.get("fault_tolerance", "medium")
    ttm = system_input.get("time_to_market", "balanced")

    top_arch = "N/A"
    if comparison_result and comparison_result.get("rankings"):
        top = comparison_result["rankings"][0]
        top_arch = top.get("architecture", {}).get("name", "N/A")

    return f"""# Software Requirements Specification

## 1. Introduction
### 1.1 Purpose
This document specifies the software requirements for: **{desc}**.
It serves as the primary reference for development, testing, and deployment activities.

### 1.2 Scope
The system is designed to serve approximately **{users}** concurrent users.
Budget sensitivity is **{budget}**, fault tolerance is **{ft}**, and time-to-market priority is **{ttm}**.

### 1.3 Definitions, Acronyms, and Abbreviations
- **SRS**: Software Requirements Specification
- **API**: Application Programming Interface
- **JWT**: JSON Web Token
- **SLA**: Service Level Agreement

## 2. Overall Description
### 2.1 Product Perspective
This system addresses the need for: {desc}. It is designed to operate at scale with {users} concurrent users.

### 2.2 User Classes and Characteristics
- End users interacting with the core system functionality
- Administrators managing system configuration and monitoring
- API consumers integrating programmatically

### 2.3 Operating Environment
Cloud-hosted infrastructure (AWS/GCP/Azure) with containerized deployments.

## 3. Functional Requirements
- **FR-1: User Authentication** — OAuth 2.0 / JWT-based authentication and authorization
- **FR-2: Core Business Logic** — {desc}
- **FR-3: Real-time Processing** — Low-latency data processing for active users
- **FR-4: Admin Dashboard** — System monitoring, user management, and analytics
- **FR-5: RESTful API** — Versioned API endpoints for all core operations
- **FR-6: Data Export** — Reporting and data export capabilities (CSV, JSON)
- **FR-7: Notifications** — Real-time event notifications to connected clients
- **FR-8: Audit Logging** — Immutable audit trail for all critical operations

## 4. Non-Functional Requirements
### 4.1 Performance Requirements
- **NFR-1**: Response time < 200ms for 95th percentile requests
- **NFR-2**: Throughput ≥ 1,000 requests/second under normal load

### 4.2 Security Requirements
- **NFR-3**: Data encryption at rest (AES-256) and in transit (TLS 1.3)
- **NFR-4**: Compliance with applicable data protection regulations (GDPR, SOC 2)

### 4.3 Scalability Requirements
- **NFR-5**: Horizontal scalability to {users} concurrent users
- **NFR-6**: Auto-scaling based on CPU/memory utilization thresholds

### 4.4 Availability & Fault Tolerance
- **NFR-7**: System availability ≥ 99.9% ({ft} fault tolerance)
- **NFR-8**: Automated failover with < 30s recovery time

## 5. System Architecture Overview
### 5.1 Architecture Style
Recommended architecture: **{top_arch}**
Selected based on weighted scoring across latency, scalability, operational complexity, infrastructure cost, and resilience.

### 5.2 Component Breakdown
- Core application service handling business logic
- Authentication service managing identity and access
- Data persistence layer with appropriate database technology
- Message queue for asynchronous processing

### 5.3 Data Storage Strategy
Primary data store selected based on the recommended architecture style, with caching layer for high-frequency reads.

## 6. Risk Analysis
### 6.1 Technical Risks
- **R-1: Scaling Bottlenecks** — Sudden user growth exceeding provisioned capacity. Mitigation: auto-scaling policies.
- **R-2: Dependency Failures** — Third-party service outages. Mitigation: circuit breakers and fallback mechanisms.
- **R-3: Data Migration** — Schema evolution complexity. Mitigation: versioned migrations with rollback capability.

### 6.2 Business Risks
- **R-4: Security Vulnerabilities** — Exposed API surfaces. Mitigation: regular penetration testing and WAF.
- **R-5: Compliance Risk** — Regulatory changes. Mitigation: modular compliance layer.

## 7. Assumptions and Dependencies
- Cloud infrastructure will be available (AWS/GCP/Azure)
- Development team has experience with the chosen architecture style
- CI/CD pipeline will be established for continuous deployment
- Monitoring and observability tools (Prometheus, Grafana) will be integrated

## 8. Constraints
- Budget sensitivity: {budget}
- Fault tolerance requirement: {ft}
- Time to market: {ttm}
- Expected user load: {users}
"""


def generate_srs(system_input: dict, architecture_results: list, comparison_result: dict) -> str:
    """Generate a full SRS document. Returns markdown string."""
    prompt = _build_srs_prompt(system_input, architecture_results, comparison_result)
    fallback = _generate_fallback(system_input, architecture_results, comparison_result)

    result = generate_llm_output(
        module_type="srs",
        system_prompt=SRS_SYSTEM_PROMPT,
        user_prompt=prompt,
        max_tokens=2500,
        temperature=0.3,
        fallback=fallback,
    )

    # If LLM returned something substantial, use it; otherwise fallback
    if result and len(result.strip()) > 200:
        return result.strip()
    return fallback
