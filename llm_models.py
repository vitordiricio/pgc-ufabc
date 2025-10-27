"""
Pydantic models for structured LLM responses in traffic control system.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
from enum import Enum


class TrafficAction(Enum):
    """Possible actions for traffic light control."""
    CHANGE_TO_GREEN = "change_to_green"
    CHANGE_TO_RED = "change_to_red"
    KEEP_CURRENT = "keep_current"
    EXTEND_GREEN = "extend_green"


class IntersectionDecision(BaseModel):
    """Decision for a specific intersection and direction."""
    intersection_id: List[int] = Field(..., min_length=2, max_length=2, description="Intersection coordinates [row, col]")
    direction: str = Field(..., description="Direction: 'NORTH' or 'EAST'")
    action: TrafficAction = Field(..., description="Action to take")
    reasoning: str = Field(..., description="Brief explanation of why this decision was made")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level from 0.0 to 1.0")


class TrafficControlResponse(BaseModel):
    """Complete response from LLM for traffic control decisions."""
    decisions: List[IntersectionDecision] = Field(..., description="List of traffic light decisions")
    global_strategy: str = Field(..., description="Overall traffic management strategy being applied")
    priority_intersections: List[List[int]] = Field(..., description="Most critical intersections to focus on, each as [row, col]")
    estimated_impact: str = Field(..., description="Expected outcome of these decisions")
    next_evaluation_time: int = Field(default=60, description="Seconds until next evaluation (60-300)")


class TrafficStateData(BaseModel):
    """Current state of traffic simulation for LLM analysis."""
    intersections: List[dict] = Field(..., description="Current state of each intersection")
    global_metrics: dict = Field(..., description="Overall simulation metrics")
    time_since_last_change: int = Field(..., description="Frames since last traffic light change")
    current_heuristica: str = Field(..., description="Currently active heuristic")
