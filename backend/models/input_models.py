"""Pydantic schemas for user input."""

from enum import Enum
from pydantic import BaseModel, Field


class SensitivityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TimeToMarket(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    ROBUST = "robust"


class SystemInput(BaseModel):
    """User-provided system description and constraints."""
    system_description: str = Field(..., min_length=5, description="What the system does")
    expected_users: int = Field(..., gt=0, description="Expected concurrent users")
    budget_sensitivity: SensitivityLevel = Field(default=SensitivityLevel.MEDIUM)
    fault_tolerance: SensitivityLevel = Field(default=SensitivityLevel.HIGH)
    time_to_market: TimeToMarket = Field(default=TimeToMarket.BALANCED)

    # Architectural priority weights (0–5, default 3)
    cost_weight: int = Field(default=3, ge=0, le=5, description="Importance of cost efficiency")
    scalability_weight: int = Field(default=5, ge=0, le=5, description="Importance of scalability")
    speed_weight: int = Field(default=3, ge=0, le=5, description="Importance of speed / low latency")
    reliability_weight: int = Field(default=5, ge=0, le=5, description="Importance of reliability")


class ScaffoldRequest(BaseModel):
    """Request to generate starter code for a chosen architecture."""
    architecture_name: str
    system_description: str
