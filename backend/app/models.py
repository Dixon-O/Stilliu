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
    embed_model: str = ""
    gen_model: str = ""
    baseline_model: str = ""


# ── Writer controls ───────────────────────────────────────────────────────────
# Real levers a content writer wants to tweak. All optional with sensible
# defaults so existing callers keep working.

class WriterControls(BaseModel):
    preserve_facts: bool = Field(
        default=True,
        description="If true, directions must not introduce facts absent from the draft. "
                    "Enables the faithfulness guard and a stricter prompt clause.",
    )
    fmt: str = Field(
        default="prose",
        description="Output shape: 'prose', 'bullets', 'punchy', or 'longform'.",
    )
    length: str = Field(
        default="match",
        description="Target length relative to draft: 'shorter', 'match', or 'longer'.",
    )
    tone: str = Field(
        default="",
        description="Free-text tone hint, e.g. 'warm and candid', 'authoritative'.",
    )
    audience: str = Field(
        default="",
        description="Free-text intended audience, e.g. 'busy executives', 'newcomers'.",
    )
    personas: Optional[list[str]] = Field(
        default=None,
        description="Which style preset names to generate, in order. None means "
                    "'writer hasn't chosen' → the defaults are used. An empty "
                    "list means 'writer cleared the selection' and is honoured "
                    "as empty — the two are deliberately NOT the same. Names must "
                    "match app.services.styles.STYLES; unknown names are ignored. "
                    "Capped at MAX_SELECTED_STYLES.",
    )
    custom_persona: str = Field(
        default="",
        description="Free-text custom style brief. Added as an extra direction.",
    )
    divergence: str = Field(
        default="recast",
        description="How far a rewrite may travel from the draft: 'nudge' (word "
                    "choice and rhythm only), 'recast' (re-form freely, keep every "
                    "point), or 'break' (discard the original structure entirely).",
    )
    avoid_ai_cadence: bool = Field(
        default=False,
        description="Apply a global ban on the measured markers of AI-generated "
                    "prose (tricolons, 'not just X but Y', em-dash asides, "
                    "summarising closers, and the known over-represented lexicon).",
    )
    voice_strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How strongly to anchor to the author's voice. 0 = ignore voice, "
                    "1 = hug the voice tightly. Trades off against distinctiveness.",
    )

    # ── Narration ─────────────────────────────────────────────────────────────
    # Every one of these defaults to a no-op value, so a request that omits them
    # produces byte-identical prompts to before they existed.
    pov: str = Field(
        default="keep",
        description="Narrative person: 'keep' (leave as drafted), 'first', "
                    "'second', or 'third'.",
    )
    tense: str = Field(
        default="keep",
        description="Narrative tense: 'keep', 'present', or 'past'.",
    )
    vocabulary: str = Field(
        default="standard",
        description="Diction register: 'plain' (short, concrete, Anglo-Saxon), "
                    "'standard' (no instruction), or 'elevated' (precise and "
                    "uncommon where it earns its place).",
    )
    rhythm: str = Field(
        default="keep",
        description="Sentence-length distribution: 'keep', 'uniform' (even), "
                    "'varied' (long then short), or 'jagged' (extremes and "
                    "fragments). Directly targets a measured stylometry feature.",
    )
    opening: str = Field(
        default="keep",
        description="How the first sentence works: 'keep', 'claim', 'image', "
                    "'question', or 'in_media_res'.",
    )

    # ── Writer's own word lists ───────────────────────────────────────────────
    banned_words: str = Field(
        default="",
        description="Comma- or newline-separated words and phrases this writer "
                    "never wants to see. Applied on top of each style's own ban "
                    "list and the AI-cadence ban.",
    )
    keep_phrases: str = Field(
        default="",
        description="Comma- or newline-separated phrases that must survive "
                    "verbatim in every direction — a line the writer already "
                    "likes and does not want rewritten.",
    )


# ── /api/analyze ─────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    draft: str = Field(..., min_length=10, description="The writer's current draft text.")
    voice_samples: Optional[list[str]] = Field(
        default=None,
        description="2–5 past writing samples for voice fingerprinting. Optional.",
    )
    controls: WriterControls = Field(default_factory=WriterControls)


# ── Multi-axis scoring ────────────────────────────────────────────────────────
# HIGH = GOOD on every axis. All scores 0–100.

class AxisScores(BaseModel):
    distinctiveness: float = Field(
        ..., ge=0.0, le=100.0,
        description="100 = departs boldly from bland AI defaults; 0 = sounds generic.",
    )
    voice_match: Optional[float] = Field(
        default=None, ge=0.0, le=100.0,
        description="100 = sounds exactly like the author. None if no voice samples.",
    )
    on_message: float = Field(
        default=100.0, ge=0.0, le=100.0,
        description="100 = faithful to the draft's meaning; low = drifted off-message.",
    )


class DraftScores(BaseModel):
    """The draft's own scores — the baseline every direction is compared against."""
    distinctiveness: float = Field(..., ge=0.0, le=100.0)
    voice_match: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    summary: str = ""


class AxisDeltas(BaseModel):
    """Direction − draft. Positive = the direction improved on the draft."""
    distinctiveness: float = 0.0
    voice_match: Optional[float] = None
    on_message: float = 0.0


class DirectionCard(BaseModel):
    persona: str = Field(..., description="Persona label, e.g. 'Sparse Minimalist'")
    persona_description: str = Field(..., description="One-line description of this persona's style approach.")
    text: str = Field(..., description="The generated alternative direction.")
    scores: AxisScores
    deltas: AxisDeltas
    faithfulness: int = Field(
        default=100, ge=0, le=100,
        description="100 = every checkable claim is grounded in the draft/voice samples.",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims in this direction not found in the source material.",
    )
    summary: str = ""
    refined: bool = Field(
        default=False,
        description="True if this direction was regenerated by the refine loop.",
    )


class AnalyzeResponse(BaseModel):
    draft_scores: DraftScores
    directions: list[DirectionCard]
    baseline_preview: str = Field("", description="First 160 chars of the generic baseline, for transparency.")
    demo_mode: bool = False


# ── /api/direction (one style at a time) ─────────────────────────────────────

class DirectionRequest(BaseModel):
    """
    Regenerate exactly one direction against the current controls.

    This is what lets the writer tweak a control and re-run only the direction
    they're looking at, instead of paying for the whole batch again.
    """
    draft: str = Field(..., min_length=10)
    voice_samples: Optional[list[str]] = None
    controls: WriterControls = Field(default_factory=WriterControls)
    style: str = Field(
        ..., min_length=1,
        description="One style preset name, or styles.CUSTOM_STYLE_NAME to use "
                    "the controls' custom_persona brief.",
    )


class DirectionResponse(BaseModel):
    direction: DirectionCard
    draft_scores: DraftScores = Field(
        ...,
        description="Recomputed alongside the direction so the draft dials stay "
                    "consistent with the deltas shown on the card.",
    )
    baseline_preview: str = ""
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


# ── /api/score (fast path — scores only, no generation) ──────────────────────

class ScoreOnlyRequest(BaseModel):
    draft: str = Field(..., min_length=10)
    voice_samples: Optional[list[str]] = None


class ScoreOnlyResponse(BaseModel):
    draft_scores: DraftScores
    baseline_preview: str = Field("", description="First 160 chars of the generated baseline, for transparency.")
    demo_mode: bool = False
