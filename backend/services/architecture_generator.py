"""Architecture Generator — LLM-driven architecture generation with deterministic fallback."""

import json
import logging
from models.input_models import SystemInput, SensitivityLevel, TimeToMarket
from models.architecture_models import Architecture, ComponentDiagram
from services.model_registry import generate_llm_output

logger = logging.getLogger(__name__)

ARCH_SYSTEM_PROMPT = (
    "You are a world-class software architect.\n"
    "Given a system description and constraints, generate a detailed architecture proposal.\n\n"
    "You MUST return ONLY valid JSON with these exact keys:\n"
    "{\n"
    '  "description": "2-3 sentence description tailored to the system and constraints",\n'
    '  "nodes": ["Component1", "Component2", ...],\n'
    '  "edges": [{"from": "Component1", "to": "Component2", "label": "protocol/method"}, ...],\n'
    '  "database_strategy": "detailed database approach for this system",\n'
    '  "communication_model": "how components communicate",\n'
    '  "scaling_model": "how the system scales",\n'
    '  "failure_domain_analysis": "failure modes and mitigation strategies"\n'
    "}\n\n"
    "RULES:\n"
    "- Tailor everything to the SPECIFIC system described, not generic boilerplate\n"
    "- Include 5-8 components in nodes that are relevant to the system\n"
    "- Include 4-8 edges showing realistic connections\n"
    "- Return ONLY JSON, no markdown fences, no explanations\n"
)

ARCH_STYLES = {
    "monolith": "Monolith Architecture — single deployable unit, shared database, in-process calls",
    "microservices": "Microservices Architecture — independently deployable services, each with own database, API gateway",
    "event_driven": "Event-Driven Architecture — async messaging, event bus, CQRS/event sourcing patterns",
    "serverless": "Serverless/FaaS Architecture — cloud functions, managed services, pay-per-invocation",
}


def _build_user_prompt(inp: SystemInput, style: str) -> str:
    """Build a detailed prompt for a specific architecture style."""
    style_desc = ARCH_STYLES.get(style, style)
    return (
        f"System: {inp.system_description}\n"
        f"Expected Users: {inp.expected_users:,}\n"
        f"Budget Sensitivity: {inp.budget_sensitivity.value}\n"
        f"Fault Tolerance: {inp.fault_tolerance.value}\n"
        f"Time to Market: {inp.time_to_market.value}\n\n"
        f"Architecture Style to Generate: {style_desc}\n\n"
        f"Generate the architecture JSON for this SPECIFIC system using the {style} style. "
        f"Make components, database strategy, and communication model directly relevant "
        f"to \"{inp.system_description}\" with {inp.expected_users:,} users."
    )


def _parse_llm_architecture(raw: str, name: str, style: str) -> Architecture | None:
    """Try to parse LLM output into an Architecture object."""
    try:
        # Strip markdown fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        data = json.loads(text)

        # Validate required fields
        description = data.get("description", "")
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        if not description or len(nodes) < 3 or len(edges) < 2:
            logger.warning(f"[architecture] LLM output for {name} missing required fields")
            return None

        # Validate edges have from/to
        valid_edges = []
        for e in edges:
            if isinstance(e, dict) and "from" in e and "to" in e:
                valid_edges.append({
                    "from": str(e["from"]),
                    "to": str(e["to"]),
                    "label": str(e.get("label", "")),
                })

        return Architecture(
            name=name,
            style=style,
            description=str(description),
            component_diagram=ComponentDiagram(
                nodes=[str(n) for n in nodes],
                edges=valid_edges,
            ),
            database_strategy=str(data.get("database_strategy", "Standard database approach")),
            communication_model=str(data.get("communication_model", "Standard communication")),
            scaling_model=str(data.get("scaling_model", "Standard scaling")),
            failure_domain_analysis=str(data.get("failure_domain_analysis", "Standard failure handling")),
        )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"[architecture] Failed to parse LLM output for {name}: {e}")
        return None


# ═══════════════════════════════════════
#  Deterministic Fallbacks (original logic)
# ═══════════════════════════════════════

def _monolith_fallback(inp: SystemInput) -> Architecture:
    desc = f"A single deployable unit handling all features for \"{inp.system_description}\". "
    if inp.expected_users > 50000:
        desc += "Vertical scaling will be stressed at this user count; consider read-replicas and caching layers."
    else:
        desc += "Ideal for fast iteration and simple deployment at this scale."

    nodes = ["API Gateway", "Monolith Server", "Database", "Cache Layer", "Load Balancer"]
    edges = [
        {"from": "Load Balancer", "to": "API Gateway", "label": "HTTP"},
        {"from": "API Gateway", "to": "Monolith Server", "label": "Internal"},
        {"from": "Monolith Server", "to": "Database", "label": "SQL/ORM"},
        {"from": "Monolith Server", "to": "Cache Layer", "label": "Redis"},
    ]

    db = "Single PostgreSQL instance"
    if inp.expected_users > 50000:
        db += " with read replicas and connection pooling (PgBouncer)"
    if inp.budget_sensitivity == SensitivityLevel.LOW:
        db = "Managed PostgreSQL (RDS/Cloud SQL) with automated backups"

    comm = "In-process function calls; REST API for external clients"
    scaling = "Vertical scaling (bigger instance). Horizontal via load balancer + sticky sessions."
    if inp.expected_users > 80000:
        scaling += " Consider splitting into 2-3 bounded contexts before microservices."

    failure = "Single failure domain — entire app goes down together. "
    if inp.fault_tolerance == SensitivityLevel.HIGH:
        failure += "CRITICAL: This architecture has a high blast radius. Deploy multi-AZ with health-check restarts."
    else:
        failure += "Mitigate with health-check probes and rolling deploys."

    return Architecture(
        name="Monolith", style="monolith", description=desc,
        component_diagram=ComponentDiagram(nodes=nodes, edges=edges),
        database_strategy=db, communication_model=comm,
        scaling_model=scaling, failure_domain_analysis=failure,
    )


def _microservices_fallback(inp: SystemInput) -> Architecture:
    desc = f"Decomposed independent services for \"{inp.system_description}\". "
    if inp.time_to_market == TimeToMarket.FAST:
        desc += "Warning: initial setup overhead is high — expect slower first release but faster long-term velocity."
    else:
        desc += "Enables independent scaling and deployment of each domain boundary."

    nodes = [
        "API Gateway", "Auth Service", "Core Service", "Notification Service",
        "User Service", "Database (per service)", "Message Broker", "Service Mesh"
    ]
    edges = [
        {"from": "API Gateway", "to": "Auth Service", "label": "gRPC"},
        {"from": "API Gateway", "to": "Core Service", "label": "gRPC"},
        {"from": "API Gateway", "to": "User Service", "label": "REST"},
        {"from": "Core Service", "to": "Message Broker", "label": "Async"},
        {"from": "Message Broker", "to": "Notification Service", "label": "Pub/Sub"},
        {"from": "Auth Service", "to": "Database (per service)", "label": "SQL"},
        {"from": "Core Service", "to": "Database (per service)", "label": "SQL"},
        {"from": "User Service", "to": "Database (per service)", "label": "SQL"},
    ]

    db = "Database-per-service pattern — each service owns its datastore. "
    if inp.budget_sensitivity == SensitivityLevel.HIGH:
        db += "Use shared PostgreSQL with schema isolation to reduce cost."
    else:
        db += "PostgreSQL for transactional services, Redis for sessions, optional MongoDB for flexible schemas."

    comm = "Synchronous: gRPC / REST between services. Asynchronous: RabbitMQ / Kafka for events."
    scaling = "Horizontal per-service auto-scaling via Kubernetes HPA. Each service scales independently."
    failure = "Isolated failure domains per service. Circuit breakers (Hystrix/Resilience4j) prevent cascading failures. "
    if inp.fault_tolerance == SensitivityLevel.HIGH:
        failure += "Deploy with service mesh (Istio) for automatic retries, timeouts, and mTLS."

    return Architecture(
        name="Microservices", style="microservices", description=desc,
        component_diagram=ComponentDiagram(nodes=nodes, edges=edges),
        database_strategy=db, communication_model=comm,
        scaling_model=scaling, failure_domain_analysis=failure,
    )


def _event_driven_fallback(inp: SystemInput) -> Architecture:
    desc = f"Event-driven architecture for \"{inp.system_description}\" using asynchronous message passing. "
    desc += "Components react to events rather than direct calls — ideal for workflows with complex state transitions."

    nodes = [
        "Event Producer (API)", "Event Bus (Kafka/NATS)", "Command Handler",
        "Event Store", "Read Model / Projections", "Notification Worker",
        "Analytics Consumer", "Database"
    ]
    edges = [
        {"from": "Event Producer (API)", "to": "Event Bus (Kafka/NATS)", "label": "Publish"},
        {"from": "Event Bus (Kafka/NATS)", "to": "Command Handler", "label": "Subscribe"},
        {"from": "Command Handler", "to": "Event Store", "label": "Persist"},
        {"from": "Event Store", "to": "Read Model / Projections", "label": "Project"},
        {"from": "Event Bus (Kafka/NATS)", "to": "Notification Worker", "label": "Subscribe"},
        {"from": "Event Bus (Kafka/NATS)", "to": "Analytics Consumer", "label": "Subscribe"},
        {"from": "Read Model / Projections", "to": "Database", "label": "Query Store"},
    ]

    db = "Event Store (append-only log) as source of truth + materialized read models. "
    if inp.budget_sensitivity == SensitivityLevel.HIGH:
        db += "Use PostgreSQL with JSONB for event store to minimize costs."
    else:
        db += "Apache Kafka for durable event log, PostgreSQL/DynamoDB for read projections."

    comm = "Fully asynchronous — publish/subscribe via event bus. CQRS separates read and write paths."
    scaling = "Consumers scale independently by adding partitions. Write path scales via sharding event topics."
    failure = "Loose coupling limits blast radius. Dead-letter queues capture failed events for replay. "
    if inp.fault_tolerance == SensitivityLevel.HIGH:
        failure += "Event sourcing enables full state reconstruction from event log — zero data loss."

    return Architecture(
        name="Event-Driven", style="event_driven", description=desc,
        component_diagram=ComponentDiagram(nodes=nodes, edges=edges),
        database_strategy=db, communication_model=comm,
        scaling_model=scaling, failure_domain_analysis=failure,
    )


def _serverless_fallback(inp: SystemInput) -> Architecture:
    desc = f"Serverless / FaaS architecture for \"{inp.system_description}\". "
    if inp.expected_users > 80000:
        desc += "Cold-start latency may be noticeable at peak — use provisioned concurrency for hot paths."
    else:
        desc += "Pay-per-invocation model keeps costs proportional to actual usage."

    nodes = [
        "API Gateway (managed)", "Lambda / Cloud Functions", "Auth (Cognito/Firebase)",
        "DynamoDB / Firestore", "S3 / Cloud Storage", "Event Bridge / Pub/Sub",
        "CloudWatch / Monitoring"
    ]
    edges = [
        {"from": "API Gateway (managed)", "to": "Lambda / Cloud Functions", "label": "Invoke"},
        {"from": "Lambda / Cloud Functions", "to": "Auth (Cognito/Firebase)", "label": "Validate"},
        {"from": "Lambda / Cloud Functions", "to": "DynamoDB / Firestore", "label": "Read/Write"},
        {"from": "Lambda / Cloud Functions", "to": "S3 / Cloud Storage", "label": "Assets"},
        {"from": "Lambda / Cloud Functions", "to": "Event Bridge / Pub/Sub", "label": "Trigger"},
        {"from": "Event Bridge / Pub/Sub", "to": "Lambda / Cloud Functions", "label": "Async"},
    ]

    db = "DynamoDB / Firestore (fully managed, auto-scaling). "
    if inp.budget_sensitivity == SensitivityLevel.HIGH:
        db += "Use on-demand capacity to avoid reserved pricing overhead."
    else:
        db += "Provision throughput for predictable workloads; on-demand for spiky traffic."

    comm = "HTTP via API Gateway trigger. Async via EventBridge/SNS/SQS fan-out."
    scaling = "Automatic — cloud provider scales to demand. Set concurrency limits to control cost."
    failure = "Functions are stateless — any instance can handle any request. "
    if inp.fault_tolerance == SensitivityLevel.HIGH:
        failure += "Multi-region active-active with DynamoDB global tables for zero-downtime failover."
    else:
        failure += "Provider-managed fault tolerance with automatic retries on transient failures."

    return Architecture(
        name="Serverless", style="serverless", description=desc,
        component_diagram=ComponentDiagram(nodes=nodes, edges=edges),
        database_strategy=db, communication_model=comm,
        scaling_model=scaling, failure_domain_analysis=failure,
    )


FALLBACK_BUILDERS = {
    "monolith": _monolith_fallback,
    "microservices": _microservices_fallback,
    "event_driven": _event_driven_fallback,
    "serverless": _serverless_fallback,
}

STYLE_NAMES = {
    "monolith": "Monolith",
    "microservices": "Microservices",
    "event_driven": "Event-Driven",
    "serverless": "Serverless",
}


def _generate_single_llm(inp: SystemInput, style: str) -> Architecture:
    """Generate one architecture using LLM, falling back to deterministic."""
    name = STYLE_NAMES.get(style, style.title())
    fallback_fn = FALLBACK_BUILDERS.get(style, _monolith_fallback)
    fallback_arch = fallback_fn(inp)

    # Build fallback JSON string for the LLM call
    fallback_json = json.dumps({
        "description": fallback_arch.description,
        "nodes": fallback_arch.component_diagram.nodes,
        "edges": [e for e in fallback_arch.component_diagram.edges],
        "database_strategy": fallback_arch.database_strategy,
        "communication_model": fallback_arch.communication_model,
        "scaling_model": fallback_arch.scaling_model,
        "failure_domain_analysis": fallback_arch.failure_domain_analysis,
    })

    user_prompt = _build_user_prompt(inp, style)

    raw = generate_llm_output(
        module_type="architecture",
        system_prompt=ARCH_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=800,
        temperature=0.5,
        fallback=fallback_json,
    )

    # Try to parse LLM output
    llm_arch = _parse_llm_architecture(raw, name, style)
    if llm_arch:
        logger.info(f"[architecture] LLM-generated {name} accepted ({len(llm_arch.component_diagram.nodes)} nodes)")
        return llm_arch

    logger.warning(f"[architecture] Using deterministic fallback for {name}")
    return fallback_arch


def generate_architectures(inp: SystemInput) -> list[Architecture]:
    """Generate all 4 architecture strategies — LLM-driven with deterministic fallback."""
    styles = ["monolith", "microservices", "event_driven", "serverless"]
    return [_generate_single_llm(inp, style) for style in styles]
