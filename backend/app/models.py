"""
models.py — Pydantic request/response schemas for all API endpoints.
Defined once here so frontend types can be generated from them later.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── Shared ──────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    demo_mode: bool


# ── /api/analyze ─────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    draft: str = Field(..., min_length=10, description="The writer's current draft text.")
    voice_samples: Optional[list[str]] = Field(
        default=None,
        description="2–5 past writing samples for voice fingerprinting. Optional.",
    )


class ScoreResult(BaseModel):
    generic_distance: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="0 = maximally distinctive, 100 = sounds like bland AI default.",
    )
    voice_distance: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="0 = matches your voice perfectly, 100 = sounds unlike you. "
                    "None if no voice samples provided.",
    )
    generic_raw: float = Field(..., description="Raw cosine distance before normalisation.")
    voice_raw: Optional[float] = Field(default=None, description="Raw cosine distance before normalisation.")


class DirectionCard(BaseModel):
    persona: str = Field(..., description="Persona label, e.g. 'Sparse Minimalist'")
    persona_description: str = Field(..., description="One-line description of this persona's style approach.")
    text: str = Field(..., description="The generated alternative direction.")
    generic_distance: float = Field(..., ge=0.0, le=100.0)


class AnalyzeResponse(BaseModel):
    scores: ScoreResult
    directions: list[DirectionCard]
    demo_mode: bool = False


# ── /api/fingerprint ─────────────────────────────────────────────────────────

class FingerprintRequest(BaseModel):
    samples: list[str] = Field(
        ...,
        min_length=2,
        description="2–5 past writing samples to build the voice fingerprint centroid.",
    )


class FingerprintResponse(BaseModel):
    sample_count: int
    paragraph_count: int
    active: bool = True
    message: str
