"""
main.py — FastAPI application entry point.

Routes:
  GET  /health                   → liveness check
  GET  /api/styles               → the grouped style preset library
  POST /api/score                → fast path: draft scores only, no generation
  POST /api/analyze              → score draft + generate + score every direction
  POST /api/direction            → regenerate ONE direction against new controls
  POST /api/fingerprint/validate → validate voice samples (count/length check)
"""
from __future__ import annotations
import logging
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import (
    HealthResponse,
    AnalyzeRequest, AnalyzeResponse,
    AxisScores, AxisDeltas, DraftScores, DirectionCard,
    ScoreOnlyRequest, ScoreOnlyResponse,
    DirectionRequest, DirectionResponse,
    FingerprintRequest, FingerprintResponse,
    WriterControls,
)
from app.services.embeddings import mean_embedding, split_into_paragraphs
from app.services.generation import (
    generate_baseline, generate_divergent_directions, regenerate_direction,
    generate_single_direction, resolve_single_style,
)
from app.services import model_registry
from app.services.scoring import (
    compute_distinctiveness, compute_voice_match, score_axes, score_summary,
)
from app.services.guardrails import check_faithfulness
from app.services.styles import styles_payload

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

# ── Refine loop config ────────────────────────────────────────────────────────
# A direction is "weak" and worth regenerating if any of these thresholds fail.
REFINE_DISTINCTIVENESS_MIN = 30   # below this → too generic, regenerate
REFINE_FAITHFULNESS_MIN    = 60   # below this → too many hallucinations, regenerate


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "Stilliu backend starting. demo_mode=%s  configured: embed=%s  gen=%s  baseline=%s",
        settings.demo_mode,
        settings.embedding_model_id,
        settings.generation_model_id,
        settings.baseline_model_id,
    )
    if not settings.demo_mode:
        from app.services.embeddings import get_embedding_client
        from app.services.generation import get_generation_client, get_baseline_client
        loop = asyncio.get_event_loop()
        logger.info("Warming up SDK clients (one-time ~10s)...")
        await asyncio.gather(
            loop.run_in_executor(None, get_embedding_client),
            loop.run_in_executor(None, get_generation_client),
            loop.run_in_executor(None, get_baseline_client),
        )
        # The configured ids above are only a request. Report what the region
        # actually gave us, so the log and the UI badges agree with reality.
        resolved = model_registry.cached()
        if resolved is not None:
            logger.info(
                "Running with: embed=%s  gen=%s  baseline=%s",
                resolved.embedding.model_id,
                resolved.creative.model_id,
                resolved.baseline.model_id,
            )
        logger.info("SDK clients warmed up. Ready to serve requests.")
    yield
    logger.info("Stilliu backend shutting down.")


app = FastAPI(
    title="Stilliu API",
    version="0.2.0",
    description="Measures creative distinctiveness and generates divergent directions.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fixture_analyze_response() -> AnalyzeResponse:
    """Hardcoded fixture so the demo never breaks regardless of schema changes."""
    draft_scores = DraftScores(
        distinctiveness=38.0,
        voice_match=None,
        summary="Distinctiveness 38/100 (leaning generic) · no voice samples",
    )
    directions = [
        DirectionCard(
            persona="Sparse Minimalist",
            persona_description="Short sentences. Nothing decorative. Meaning carried by what is left out.",
            text=(
                "AI erases voices. Not through malice — through averaging. "
                "Every writer who leans on it drifts toward the mean. "
                "The work gets cleaner. Blander. Safer. That's the cost nobody mentions."
            ),
            scores=AxisScores(distinctiveness=78.0, voice_match=None, on_message=72.0),
            deltas=AxisDeltas(distinctiveness=40.0, voice_match=None, on_message=22.0),
            faithfulness=100,
            unsupported_claims=[],
            summary="Distinctiveness 78/100 · On-message 72/100",
            refined=False,
        ),
        DirectionCard(
            persona="The Arguer",
            persona_description="Leads with a bold claim. Builds a case. Anticipates pushback and answers it.",
            text=(
                "AI homogenisation is the most underreported threat to writing culture right now. "
                "Yes, individual quality improves. But read a hundred AI-assisted essays and you'll "
                "find the same cadence, the same hedges, the same arc. The counterargument is that "
                "good ideas transcend style. That's wrong. Style is how an idea becomes yours."
            ),
            scores=AxisScores(distinctiveness=71.0, voice_match=None, on_message=81.0),
            deltas=AxisDeltas(distinctiveness=33.0, voice_match=None, on_message=31.0),
            faithfulness=100,
            unsupported_claims=[],
            summary="Distinctiveness 71/100 · On-message 81/100",
            refined=False,
        ),
        DirectionCard(
            persona="Sensory-Led",
            persona_description="Grounds ideas in physical sensation, texture, and concrete scene.",
            text=(
                "Paste your draft into any AI assistant. Watch it come back smoother, rounder, "
                "emptier — like river stones that lost their edges in the current. That's what "
                "homogenisation feels like from the inside: not loss, but a quiet erasure of the grain."
            ),
            scores=AxisScores(distinctiveness=83.0, voice_match=None, on_message=68.0),
            deltas=AxisDeltas(distinctiveness=45.0, voice_match=None, on_message=18.0),
            faithfulness=100,
            unsupported_claims=[],
            summary="Distinctiveness 83/100 · On-message 68/100",
            refined=False,
        ),
    ]
    return AnalyzeResponse(
        draft_scores=draft_scores,
        directions=directions,
        baseline_preview="This text explores an important topic that many people find relevant today...",
        demo_mode=True,
    )


def _fixture_direction(style_name: str) -> DirectionCard:
    """A single fixture card, for demo-mode single-style regeneration."""
    fixture = _fixture_analyze_response()
    for card in fixture.directions:
        if card.persona == style_name:
            return card
    return fixture.directions[0].model_copy(update={
        "persona": style_name,
        "persona_description": f"Fixture direction standing in for {style_name}.",
    })


# ── Shared scoring pipeline ───────────────────────────────────────────────────
# /api/score, /api/analyze and /api/direction all need the same groundwork:
# embed the draft, generate the bland baseline, embed that, optionally build the
# voice centroid, then score the draft against it. It lives here once so the
# three endpoints cannot drift apart — a direction regenerated on its own must
# be measured against exactly the same anchors as one from a full batch, or its
# deltas would not be comparable.

@dataclass
class _ScoringContext:
    draft: str
    draft_vec: Any
    baseline_text: str
    baseline_vec: Any
    voice_centroid: Any | None
    voice_samples: list[str] = field(default_factory=list)
    controls: WriterControls = field(default_factory=WriterControls)

    @property
    def source_pool(self) -> list[str]:
        """Everything a claim is allowed to be grounded in."""
        return [self.draft] + self.voice_samples


async def _prepare_context(
    loop: asyncio.AbstractEventLoop,
    draft: str,
    voice_samples: list[str],
    controls: WriterControls,
) -> tuple[_ScoringContext, DraftScores]:
    """Embed the draft, generate and embed the baseline, score the draft."""
    # Phase A — draft embed and baseline generation are independent.
    draft_paras = split_into_paragraphs(draft)
    draft_vec, baseline_text = await asyncio.gather(
        loop.run_in_executor(None, mean_embedding, draft_paras),
        loop.run_in_executor(None, generate_baseline, draft),
    )

    # Phase B — baseline embed and voice centroid are also independent.
    baseline_paras = split_into_paragraphs(baseline_text)
    if voice_samples:
        from app.services.fingerprint import build_voice_centroid
        baseline_vec, voice_centroid = await asyncio.gather(
            loop.run_in_executor(None, mean_embedding, baseline_paras),
            loop.run_in_executor(None, build_voice_centroid, voice_samples),
        )
    else:
        baseline_vec = await loop.run_in_executor(None, mean_embedding, baseline_paras)
        voice_centroid = None

    draft_dist, _, _ = compute_distinctiveness(draft_vec, baseline_vec, draft, baseline_text)
    draft_voice: float | None = None
    if voice_centroid is not None:
        draft_voice, _, _ = compute_voice_match(draft_vec, voice_centroid, draft, voice_samples)

    ctx = _ScoringContext(
        draft=draft,
        draft_vec=draft_vec,
        baseline_text=baseline_text,
        baseline_vec=baseline_vec,
        voice_centroid=voice_centroid,
        voice_samples=voice_samples,
        controls=controls,
    )
    return ctx, DraftScores(distinctiveness=draft_dist, voice_match=draft_voice)


def _score_against(ctx: _ScoringContext, text: str, vec: Any) -> dict:
    return score_axes(
        draft_vector=ctx.draft_vec,
        draft_str=ctx.draft,
        baseline_vector=ctx.baseline_vec,
        baseline_str=ctx.baseline_text,
        # With no voice samples there's no centroid to compare against, so the
        # draft stands in. The resulting value is a draft-vs-draft artifact and
        # is suppressed before it reaches the response.
        voice_centroid=ctx.voice_centroid if ctx.voice_centroid is not None else ctx.draft_vec,
        voice_samples=ctx.voice_samples,
        direction_vector=vec,
        direction_str=text,
    )


async def _build_direction_card(
    loop: asyncio.AbstractEventLoop,
    d: dict,
    ctx: _ScoringContext,
) -> DirectionCard:
    """Embed, score, faithfulness-check and (if weak) refine one direction."""
    dir_vec = await loop.run_in_executor(
        None, mean_embedding, split_into_paragraphs(d["text"]))
    axes = _score_against(ctx, d["text"], dir_vec)

    faith_score, unsupported = check_faithfulness(d["text"], ctx.source_pool)
    refined = False

    # ── Refine loop: regenerate if weak ──────────────────────────────────────
    needs_refine = (
        axes["distinctiveness"] < REFINE_DISTINCTIVENESS_MIN
        or (ctx.controls.preserve_facts and faith_score < REFINE_FAITHFULNESS_MIN)
    )
    if needs_refine:
        feedback_parts = []
        if axes["distinctiveness"] < REFINE_DISTINCTIVENESS_MIN:
            feedback_parts.append(
                f"distinctiveness too low ({axes['distinctiveness']:.0f}/100) — "
                "push the style further from generic AI prose"
            )
        if ctx.controls.preserve_facts and faith_score < REFINE_FAITHFULNESS_MIN:
            feedback_parts.append(
                f"faithfulness too low ({faith_score}/100) — "
                f"remove invented claims: {', '.join(unsupported[:3])}"
            )
        new_d = await loop.run_in_executor(
            None, regenerate_direction,
            ctx.draft, d["name"], d["description"],
            ctx.voice_samples, ctx.controls, "; ".join(feedback_parts),
        )
        new_vec = await loop.run_in_executor(
            None, mean_embedding, split_into_paragraphs(new_d["text"]))
        axes = _score_against(ctx, new_d["text"], new_vec)
        faith_score, unsupported = check_faithfulness(new_d["text"], ctx.source_pool)
        d = new_d
        refined = True

    has_voice = ctx.voice_centroid is not None
    # Don't let the summary claim a voice match when there are no voice samples.
    summary_axes = dict(axes)
    if not has_voice:
        summary_axes["voice_match"] = None

    return DirectionCard(
        persona=d["name"],
        persona_description=d["description"],
        text=d["text"],
        scores=AxisScores(
            distinctiveness=axes["distinctiveness"],
            voice_match=axes["voice_match"] if has_voice else None,
            on_message=axes["on_message"],
        ),
        deltas=AxisDeltas(
            distinctiveness=axes["delta_distinctiveness"],
            voice_match=axes["delta_voice_match"] if has_voice else None,
            on_message=axes["delta_on_message"],
        ),
        faithfulness=faith_score,
        unsupported_claims=unsupported,
        summary=score_summary(summary_axes),
        refined=refined,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    settings = get_settings()
    # Prefer the ids the region resolved to over the ones we asked for — the
    # badges in the UI read this, and they should never claim a model that
    # isn't loaded.
    resolved = model_registry.cached()
    return HealthResponse(
        status="ok",
        demo_mode=settings.demo_mode,
        embed_model=resolved.embedding.model_id if resolved else settings.embedding_model_id,
        gen_model=resolved.creative.model_id if resolved else settings.generation_model_id,
        baseline_model=resolved.baseline.model_id if resolved else settings.baseline_model_id,
    )


@app.get("/api/styles")
async def list_styles():
    """
    The style preset library, grouped. The frontend renders its picker straight
    from this so the list never has to be duplicated client-side — adding a
    preset in styles.py is enough to make it appear in the UI.
    """
    return styles_payload()


@app.post("/api/score", response_model=ScoreOnlyResponse)
async def score_only(req: ScoreOnlyRequest):
    """
    Fast path — returns draft scores only, no generation.
    Use this to show live score dials before the full analyze call completes.
    """
    settings = get_settings()

    if settings.demo_mode:
        fixture = _fixture_analyze_response()
        return ScoreOnlyResponse(
            draft_scores=fixture.draft_scores,
            baseline_preview=fixture.baseline_preview,
            demo_mode=True,
        )

    try:
        async def _run():
            loop = asyncio.get_event_loop()
            ctx, draft_scores = await _prepare_context(
                loop, req.draft, req.voice_samples or [], WriterControls())

            draft_scores.summary = score_summary({
                "distinctiveness": draft_scores.distinctiveness,
                "voice_match": draft_scores.voice_match,
                "on_message": 100.0,
                "draft_distinctiveness": draft_scores.distinctiveness,
                "draft_voice_match": draft_scores.voice_match,
                "delta_distinctiveness": 0.0,
                "delta_voice_match": 0.0,
                "delta_on_message": 0.0,
                "raw_dist_sem": 0.0, "raw_dist_sty": 0.0,
                "raw_voice_sem": 0.0, "raw_voice_sty": 0.0,
                "raw_msg_sem": 0.0,
            })
            return ScoreOnlyResponse(
                draft_scores=draft_scores,
                baseline_preview=ctx.baseline_text[:160].strip(),
                demo_mode=False,
            )

        return await asyncio.wait_for(_run(), timeout=settings.score_timeout)

    except asyncio.TimeoutError:
        logger.warning("Score-only timed out — returning fixture fallback.")
        fixture = _fixture_analyze_response()
        return ScoreOnlyResponse(
            draft_scores=fixture.draft_scores,
            baseline_preview="[timeout — fixture fallback]",
            demo_mode=True,
        )
    except Exception as exc:
        logger.error("Score-only error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    settings = get_settings()

    # Validated before the try block: an HTTPException raised inside would be
    # swallowed by the catch-all below and re-reported as a 500.
    if req.controls.personas is not None and not req.controls.personas \
            and not req.controls.custom_persona.strip():
        raise HTTPException(
            status_code=400,
            detail="No styles selected. Pick at least one style, or write a custom "
                   "style brief.",
        )

    if settings.demo_mode:
        return _fixture_analyze_response()

    try:
        async def _run():
            loop = asyncio.get_event_loop()
            ctx, draft_scores = await _prepare_context(
                loop, req.draft, req.voice_samples or [], req.controls)

            raw_directions = await loop.run_in_executor(
                None, generate_divergent_directions,
                req.draft, ctx.voice_samples, req.controls,
            )
            direction_cards = list(await asyncio.gather(
                *[_build_direction_card(loop, d, ctx) for d in raw_directions]
            ))

            return AnalyzeResponse(
                draft_scores=draft_scores,
                directions=direction_cards,
                baseline_preview=ctx.baseline_text[:160].strip(),
                demo_mode=False,
            )

        return await asyncio.wait_for(_run(), timeout=settings.analyze_timeout)

    except asyncio.TimeoutError:
        logger.warning("Analysis timed out — returning fixture fallback.")
        fixture = _fixture_analyze_response()
        fixture.demo_mode = True
        return fixture
    except Exception as exc:
        logger.error("Analysis error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/direction", response_model=DirectionResponse)
async def direction(req: DirectionRequest):
    """
    Regenerate exactly one direction.

    This is the endpoint that makes the controls feel direct rather than
    batched: change a control, re-run only the direction you're reading. It
    costs one generation instead of up to six, and because it goes through the
    same _prepare_context anchors, the deltas it returns stay comparable with
    the ones from a full /api/analyze run.
    """
    settings = get_settings()

    style = resolve_single_style(req.style, req.controls)
    if style is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown style {req.style!r}. Fetch GET /api/styles for the "
                   f"current list, or set controls.custom_persona to use a brief.",
        )

    if settings.demo_mode:
        fixture = _fixture_analyze_response()
        return DirectionResponse(
            direction=_fixture_direction(req.style),
            draft_scores=fixture.draft_scores,
            baseline_preview=fixture.baseline_preview,
            demo_mode=True,
        )

    try:
        async def _run():
            loop = asyncio.get_event_loop()
            ctx, draft_scores = await _prepare_context(
                loop, req.draft, req.voice_samples or [], req.controls)

            raw = await loop.run_in_executor(
                None, generate_single_direction,
                req.draft, style, ctx.voice_samples, req.controls,
            )
            card = await _build_direction_card(loop, raw, ctx)
            return DirectionResponse(
                direction=card,
                draft_scores=draft_scores,
                baseline_preview=ctx.baseline_text[:160].strip(),
                demo_mode=False,
            )

        return await asyncio.wait_for(_run(), timeout=settings.analyze_timeout)

    except asyncio.TimeoutError:
        logger.warning("Single-direction generation timed out for %s.", req.style)
        raise HTTPException(
            status_code=504,
            detail=f"Generating {req.style} timed out. Your other directions are "
                   f"unaffected — try again.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Direction error for %s: %s", req.style, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/fingerprint/validate", response_model=FingerprintResponse)
async def validate_fingerprint(req: FingerprintRequest):
    """Validate voice samples without computing embeddings — fast UX feedback."""
    para_count = sum(len(split_into_paragraphs(s)) for s in req.samples)
    return FingerprintResponse(
        sample_count=len(req.samples),
        paragraph_count=para_count,
        active=True,
        message=f"{len(req.samples)} samples · {para_count} paragraphs indexed for voice fingerprint.",
    )
