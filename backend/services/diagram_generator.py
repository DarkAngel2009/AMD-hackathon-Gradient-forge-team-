"""Diagram Generator — produces valid Mermaid.js diagrams for architectures."""

import re
import logging
from services.model_registry import generate_llm_output

logger = logging.getLogger(__name__)

DIAGRAM_SYSTEM_PROMPT = (
    "You are a system architecture diagramming expert.\n"
    "Generate a valid Mermaid.js flowchart for the given architecture.\n\n"
    "STRICT RULES — violating ANY rule makes the diagram invalid:\n"
    "1. First line MUST be: graph TD\n"
    "2. Node IDs MUST be alphanumeric + underscores ONLY.  Good: API_GW   Bad: API-GW\n"
    "3. Node IDs MUST be prefixed with 'n_' to avoid collisions. Example: n_api_gw\n"
    "4. Display labels go in square brackets with quotes: n_api_gw[\"API Gateway\"]\n"
    "5. Edges: n_api_gw -->|HTTP| n_auth  OR  n_api_gw --> n_auth\n"
    "6. Do NOT use subgraph blocks — they cause rendering issues.\n"
    "7. Do NOT use Unicode arrows (→, ←). Only use -->\n"
    "8. Do NOT use colons in IDs (no Lambda:Invoke).\n"
    "9. Do NOT use markdown fences or explanations. Return ONLY the Mermaid code.\n"
    "10. Every node must be declared EXACTLY ONCE with its label.\n\n"
    "EXAMPLE:\n"
    "graph TD\n"
    "    n_client[\"Client Browser\"]\n"
    "    n_api[\"API Gateway\"]\n"
    "    n_auth[\"Auth Service\"]\n"
    "    n_db[\"PostgreSQL\"]\n"
    "    n_cache[\"Redis Cache\"]\n"
    "    n_client -->|HTTPS| n_api\n"
    "    n_api -->|JWT| n_auth\n"
    "    n_auth -->|SQL| n_db\n"
    "    n_api -->|cache| n_cache\n"
)


def sanitize_node_name(name: str) -> str:
    """Sanitize a string into a valid Mermaid node ID (alphanumeric + underscores only)."""
    sanitized = (
        name.replace(":", "_")
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "_")
            .replace(",", "")
            .replace("'", "")
            .replace('"', "")
    )
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', sanitized)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    if sanitized and not sanitized[0].isalpha():
        sanitized = "N" + sanitized
    return sanitized[:30] if sanitized else "Node"


def _build_fallback_mermaid(architecture: dict) -> str:
    """Generate a valid Mermaid diagram deterministically — flat structure, no subgraphs."""
    a = architecture if isinstance(architecture, dict) else architecture
    name = a.get("name", "Architecture")
    style = a.get("style", "unknown")
    diagram = a.get("component_diagram", {})
    nodes = diagram.get("nodes", [])
    edges = diagram.get("edges", [])

    lines = ["graph TD"]

    # Declare all nodes with n_ prefix to avoid any collisions
    node_id_map = {}
    used_ids = set()
    for node in nodes:
        base_id = "n_" + sanitize_node_name(node)
        nid = base_id
        counter = 2
        while nid in used_ids:
            nid = f"{base_id}_{counter}"
            counter += 1
        used_ids.add(nid)
        node_id_map[node] = nid
        # Escape quotes in label
        safe_label = node.replace('"', "'")
        lines.append(f'    {nid}["{safe_label}"]')

    # Add edges
    for edge in edges:
        from_name = edge.get("from", "")
        to_name = edge.get("to", "")
        label = edge.get("label", "")

        from_id = node_id_map.get(from_name)
        to_id = node_id_map.get(to_name)

        # If edge references a node not in our map, create it
        if not from_id and from_name:
            from_id = "n_" + sanitize_node_name(from_name)
            if from_id not in used_ids:
                used_ids.add(from_id)
                node_id_map[from_name] = from_id
                safe_label = from_name.replace('"', "'")
                lines.insert(1, f'    {from_id}["{safe_label}"]')
        if not to_id and to_name:
            to_id = "n_" + sanitize_node_name(to_name)
            if to_id not in used_ids:
                used_ids.add(to_id)
                node_id_map[to_name] = to_id
                safe_label = to_name.replace('"', "'")
                lines.insert(1, f'    {to_id}["{safe_label}"]')

        if from_id and to_id:
            if label:
                safe_label = label.replace('"', "'").replace("|", "/")
                lines.append(f"    {from_id} -->|{safe_label}| {to_id}")
            else:
                lines.append(f"    {from_id} --> {to_id}")

    # Style nodes by architecture type
    style_colors = {
        "monolith": "#3b82f6",
        "microservices": "#8b5cf6",
        "event_driven": "#10b981",
        "serverless": "#06b6d4",
    }
    color = style_colors.get(style, "#3b82f6")
    lines.append("")
    for nid in used_ids:
        lines.append(f"    style {nid} fill:{color}22,stroke:{color},color:#f1f5f9")

    return "\n".join(lines)


def _validate_mermaid(code: str) -> bool:
    """Strict validation of Mermaid syntax."""
    stripped = code.strip()
    lower = stripped.lower()

    # Must start with graph or flowchart
    if not (lower.startswith("graph") or lower.startswith("flowchart")):
        return False

    # Must have at least one edge
    if "-->" not in code:
        return False

    # Reject Unicode arrows
    if "→" in code or "←" in code:
        return False

    # Reject markdown fences
    if "```" in code:
        return False

    # Detect subgraph/node ID collisions (the exact bug we saw)
    subgraph_ids = set()
    node_ids = set()
    for line in stripped.split("\n"):
        s = line.strip()
        if s.lower().startswith("subgraph "):
            # Extract subgraph ID (word after "subgraph")
            parts = s.split(None, 2)  # subgraph ID [optional label]
            if len(parts) >= 2:
                sg_id = parts[1].split("[")[0].split("(")[0]
                subgraph_ids.add(sg_id)
        elif "[" in s and not s.lower().startswith("subgraph") and not s.startswith("style "):
            # Node declaration: ID["label"] or ID[label]
            node_id = s.split("[")[0].strip()
            if node_id and not node_id.startswith("%%") and "-->" not in node_id:
                node_ids.add(node_id)

    # Check for collision
    collision = subgraph_ids & node_ids
    if collision:
        logger.warning(f"Mermaid validation: subgraph/node ID collision detected: {collision}")
        return False

    # Check for duplicate node declarations
    seen_defs = set()
    for line in stripped.split("\n"):
        s = line.strip()
        if "[" in s and not s.lower().startswith("subgraph") and not s.startswith("style "):
            node_id = s.split("[")[0].strip()
            if node_id and "-->" not in node_id:
                if node_id in seen_defs:
                    logger.warning(f"Mermaid validation: duplicate node declaration: {node_id}")
                    return False
                seen_defs.add(node_id)

    return True


def _sanitize_llm_mermaid(code: str) -> str:
    """Attempt to fix common LLM mistakes in Mermaid output."""
    code = code.replace("→", "-->")
    code = code.replace("←", "<--")
    # Remove markdown fences
    lines = code.strip().split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def generate_mermaid_diagram(architecture: dict) -> str:
    """Generate Mermaid.js code for an architecture using LLM.
    
    The prompt embeds each architecture's exact nodes and edges so the
    LLM produces a unique, architecture-specific diagram every time.
    Falls back to deterministic builder if LLM output fails validation.
    """
    a = architecture if isinstance(architecture, dict) else architecture
    name = a.get("name", "Unknown")
    style = a.get("style", "unknown")
    diagram = a.get("component_diagram", {})
    nodes = diagram.get("nodes", [])
    edges = diagram.get("edges", [])
    db = a.get("database_strategy", "N/A")
    comm = a.get("communication_model", "N/A")
    scaling = a.get("scaling_model", "N/A")

    # Build a highly specific prompt with this architecture's exact data
    node_list = "\n".join(f"  - {n}" for n in nodes)
    edge_list = "\n".join(
        f"  - {e.get('from', '?')} -> {e.get('to', '?')} ({e.get('label', 'link')})"
        for e in edges
    )

    user_prompt = (
        f"Create a Mermaid diagram for this SPECIFIC architecture:\n\n"
        f"Architecture Name: {name}\n"
        f"Architecture Style: {style}\n\n"
        f"MANDATORY NODES (you MUST include ALL of these):\n{node_list}\n\n"
        f"MANDATORY CONNECTIONS (you MUST include ALL of these):\n{edge_list}\n\n"
        f"Additional context:\n"
        f"  Database: {db}\n"
        f"  Communication: {comm}\n"
        f"  Scaling: {scaling}\n\n"
        f"IMPORTANT: Use ONLY the components listed above. "
        f"Prefix all node IDs with 'n_'. No subgraphs. "
        f"Return ONLY valid Mermaid code starting with 'graph TD'."
    )

    fallback = _build_fallback_mermaid(a)

    result = generate_llm_output(
        module_type="diagram",
        system_prompt=DIAGRAM_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=600,
        temperature=0.3,
        fallback=fallback,
    )

    # Clean up LLM response
    cleaned = _sanitize_llm_mermaid(result)

    # Validate strictly — if it passes, use the LLM version
    if _validate_mermaid(cleaned):
        logger.info(f"[diagram] LLM diagram accepted for {name}")
        return cleaned

    # Otherwise use the deterministic builder (guaranteed valid + unique)
    logger.warning(f"[diagram] LLM output failed validation for {name}, using deterministic fallback.")
    return fallback
