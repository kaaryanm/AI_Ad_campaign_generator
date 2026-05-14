"""Pydantic schemas for the /campaign endpoint.

These models double as the OpenAI structured-output schema for the planning
call (`plan_campaign`) and the creatives call (`write_creatives`). A few
constraints worth knowing if you tweak them:

* OpenAI's strict structured outputs require every field to be required; we
  avoid `Optional` and use empty-string / empty-list defaults where the LLM
  may not always have something to say.
* We use a tiny `UsdRange` model instead of `tuple[float, float]` so the
  generated JSON Schema is friendly to the structured-output validator.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BidModel = Literal["CPM", "CPC", "CPA"]


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class CampaignRequest(BaseModel):
    """The single field an advertiser fills in: a one-liner about their business."""

    advertiser_brief: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="One- or two-sentence description of the advertiser's business.",
    )


# ---------------------------------------------------------------------------
# Ranked publishers (and exclusions)
# ---------------------------------------------------------------------------


class RankedPublisher(BaseModel):
    publisher_id: str
    name: str
    rank: int = Field(..., ge=1, description="1 = best fit. Unique per result.")
    fit_score: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(
        ...,
        description="Why this publisher fits: audience overlap, AOV alignment, category match, etc.",
    )


class ExcludedPublisher(BaseModel):
    publisher_id: str
    name: str
    reason: str = Field(
        ...,
        description="Concise reason the publisher was considered and dropped.",
    )


# ---------------------------------------------------------------------------
# Personas + creatives
# ---------------------------------------------------------------------------


class Persona(BaseModel):
    """A persona the planner selected for this advertiser, plus the reasoning."""

    persona_id: str
    name: str
    selection_reasoning: str = Field(
        ...,
        description="Why this persona is plausible for this advertiser.",
    )


class Creative(BaseModel):
    """One ad creative variant, tied to exactly one selected persona."""

    persona_id: str
    persona_name: str
    persona_reasoning: str = Field(
        ...,
        description="Short reminder of why this persona was chosen (mirrors Persona.selection_reasoning).",
    )
    headline: str = Field(..., max_length=120)
    body: str = Field(..., max_length=400)
    call_to_action: str = Field(default="", max_length=60)


# ---------------------------------------------------------------------------
# Campaign config
# ---------------------------------------------------------------------------


class UsdRange(BaseModel):
    """Inclusive [low, high] dollar range."""

    low: float = Field(..., ge=0.0)
    high: float = Field(..., ge=0.0)


class TargetingConfig(BaseModel):
    age_range: str = Field(..., description="e.g. '25-44'")
    geos: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


class PublisherAllocation(BaseModel):
    publisher_id: str
    name: str
    percent: float = Field(..., ge=0.0, le=1.0, description="Share of daily spend; allocations should sum to ~1.0.")
    suggested_daily_usd: UsdRange


class BudgetConfig(BaseModel):
    suggested_daily_usd: UsdRange
    suggested_flight_days: int = Field(..., ge=1, le=365)


class BidStrategy(BaseModel):
    model: BidModel
    suggested_range_usd: UsdRange
    rationale: str


class CampaignConfig(BaseModel):
    targeting: TargetingConfig
    publisher_allocation: list[PublisherAllocation]
    budget: BudgetConfig
    bid_strategy: BidStrategy


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------


class CampaignPlan(BaseModel):
    """Output of LLM call 1 (`plan_campaign`).

    Kept as its own type because call 2 (creatives) only needs the personas
    from this object as input — separating these makes the prompt boundary
    explicit.
    """

    ranked_publishers: list[RankedPublisher]
    excluded_publishers: list[ExcludedPublisher]
    selected_personas: list[Persona] = Field(..., min_length=3, max_length=5)
    campaign_config: CampaignConfig


class CreativeBundle(BaseModel):
    """Output of LLM call 2 (`write_creatives`)."""

    creatives: list[Creative] = Field(..., min_length=3, max_length=5)


class CampaignResult(BaseModel):
    """Combined payload returned by POST /campaign."""

    advertiser_brief: str
    ranked_publishers: list[RankedPublisher]
    excluded_publishers: list[ExcludedPublisher]
    selected_personas: list[Persona]
    creatives: list[Creative]
    campaign_config: CampaignConfig
