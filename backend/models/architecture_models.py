"""Pydantic schemas for architecture output, scores, and comparison."""

from typing import Optional
from pydantic import BaseModel, Field


class ComponentDiagram(BaseModel):
    """Logical component diagram representation."""
    nodes: list[str] = Field(default_factory=list, description="Component names")
    edges: list[dict] = Field(default_factory=list, description="Connections between components")


class Architecture(BaseModel):
    """A single generated architecture."""
    name: str
    style: str  # monolith | microservices | event_driven | serverless
    description: str
    component_diagram: ComponentDiagram
    database_strategy: str
    communication_model: str
    scaling_model: str
    failure_domain_analysis: str


class SimulationScores(BaseModel):
    """Simulated metric scores (0-100, higher = better, except cost/complexity where lower = better)."""
    latency: float = Field(..., ge=0, le=100)
    scalability: float = Field(..., ge=0, le=100)
    operational_complexity: float = Field(..., ge=0, le=100)
    infrastructure_cost: float = Field(..., ge=0, le=100)
    resilience: float = Field(..., ge=0, le=100)


class ArchitectureResult(BaseModel):
    """Architecture + its simulation scores."""
    architecture: Architecture
    scores: SimulationScores
    overall_score: float = 0.0
    scoring_breakdown: Optional[dict] = None


class ComparisonResult(BaseModel):
    """Ranked architectures with trade-off reasoning."""
    rankings: list[ArchitectureResult]
    trade_off_reasoning: list[str]
    recommendation: str
    constraint_tension_warning: Optional[str] = None
    llm_analysis: Optional[dict] = None


class ScaffoldOutput(BaseModel):
    """Generated scaffold files."""
    architecture_name: str
    files: dict[str, str]  # filename -> content
