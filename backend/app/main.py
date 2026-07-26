"""
main.py — FastAPI application entry point.

Routes:
  GET  /health                   → liveness check
  POST /api/analyze              → score a draft + generate directions
  POST /api/fingerprint/validate → validate voice samples (count/length check)
"""
from __future__ import annotations
import json
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import (
    HealthResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ScoreResult,
    ScoreOnlyRequest,
    ScoreOnlyResponse,
    DirectionCard,
    FingerprintRequest,
    FingerprintResponse,
)
from app.services.embeddings import mean_embedding, split_into_paragraphs
from app.services.fingerprint import build_voice_centroid, extract_style_signals
from app.services.generation import generate_baseline, generate_divergent_directions
from app.services.scoring import compute_generic_score, compute_voice_score

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "demo_responses.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "Stilliu backend starting. demo_mode=%s  embed=%s  gen=%s",
        settings.demo_mode,
        settings.embedding_model_id,
        settings.generation_model_id,
    )
    if not settings.demo_mode:
        # Warm up both SDK clients at startup so first request is not cold.
        # Cold-start takes ~8–10s; warming here means request 1 is as fast as request 2.
        import asyncio
        from app.services.embeddings import get_embedding_client
        from app.services.generation import get_generation_client
        loop = asyncio.get_event_loop()
        logger.info("Warming up SDK clients (one-time ~10s)...")
        await asyncio.gather(
            loop.run_in_executor(None, get_embedding_client),
            loop.run_in_executor(None, get_generation_client),
        )
        logger.info("SDK clients warmed up. Ready to serve requests.")
    yield
    logger.info("Stilliu backend shutting down.")


app = FastAPI(
    title="Stilliu API",
    version="0.1.0",
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


def _load_fixture(key: str) -> dict:
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        return json.load(f)[key]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    settings = get_settings()
    return HealthResponse(
        status="ok",
        demo_mode=settings.demo_mode,
        embed_model=settings.embedding_model_id,
        gen_model=settings.generation_model_id,
    )


@app.post("/api/score", response_model=ScoreOnlyResponse)
async def score_only(req: ScoreOnlyRequest):
    """
    Fast path — returns Generic Distance + Voice Distance scores only.
    No divergent generation. Typically resolves in ~2–4s vs ~20s for full analyze.
    Use this to show live score dials before the full analyze call completes.
    """
    settings = get_settings()

    if settings.demo_mode:
        fixture = _load_fixture("analyze")
        return ScoreOnlyResponse(
            scores=ScoreResult(**fixture["scores"]),
            baseline_preview="This topic is important and relevant today. There are many key points to consider...",
            demo_mode=True,
        )

    try:
        async def _run_scoring():
            loop = asyncio.get_event_loop()

            draft_paras = split_into_paragraphs(req.draft)
            # Run draft embedding + baseline generation concurrently
            draft_vec_fut = loop.run_in_executor(None, mean_embedding, draft_paras)
            baseline_text_fut = loop.run_in_executor(None, generate_baseline, req.draft)

            draft_vec, baseline_text = await asyncio.gather(draft_vec_fut, baseline_text_fut)

            baseline_paras = split_into_paragraphs(baseline_text)
            baseline_vec = await loop.run_in_executor(None, mean_embedding, baseline_paras)

            generic_display, generic_raw = compute_generic_score(draft_vec, baseline_vec)

            voice_display: float | None = None
            voice_raw: float | None = None

            if req.voice_samples:
                voice_centroid = await loop.run_in_executor(
                    None, build_voice_centroid, req.voice_samples
                )
                voice_display, voice_raw = compute_voice_score(draft_vec, voice_centroid)

            return ScoreOnlyResponse(
                scores=ScoreResult(
                    generic_distance=generic_display,
                    voice_distance=voice_display,
                    generic_raw=generic_raw,
                    voice_raw=voice_raw,
                ),
                baseline_preview=baseline_text[:120].strip(),
                demo_mode=False,
            )

        return await asyncio.wait_for(_run_scoring(), timeout=settings.score_timeout)

    except asyncio.TimeoutError:
        logger.warning("Score-only timed out — returning fixture fallback.")
        fixture = _load_fixture("analyze")
        return ScoreOnlyResponse(
            scores=ScoreResult(**fixture["scores"]),
            baseline_preview="[timeout — fixture fallback]",
            demo_mode=True,
        )
    except Exception as exc:
        logger.error("Score-only error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    settings = get_settings()

    # ── Demo / fixture mode ───────────────────────────────────────────────
    if settings.demo_mode:
        fixture = _load_fixture("analyze")
        return AnalyzeResponse(**fixture)

    # ── Live mode ─────────────────────────────────────────────────────────
    try:
        async def _run_analysis():
            loop = asyncio.get_event_loop()

            # Phase A: draft embedding + baseline generation — run CONCURRENTLY
            draft_paras = split_into_paragraphs(req.draft)
            draft_vec, baseline_text = await asyncio.gather(
                loop.run_in_executor(None, mean_embedding, draft_paras),
                loop.run_in_executor(None, generate_baseline, req.draft),
            )

            # Phase B: baseline embedding + voice fingerprint — run CONCURRENTLY
            baseline_paras = split_into_paragraphs(baseline_text)

            if req.voice_samples:
                baseline_vec, voice_centroid = await asyncio.gather(
                    loop.run_in_executor(None, mean_embedding, baseline_paras),
                    loop.run_in_executor(None, build_voice_centroid, req.voice_samples),
                )
                voice_display, voice_raw = compute_voice_score(draft_vec, voice_centroid)
                style_signals = extract_style_signals(req.voice_samples)
            else:
                baseline_vec = await loop.run_in_executor(None, mean_embedding, baseline_paras)
                voice_display, voice_raw, style_signals = None, None, None

            generic_display, generic_raw = compute_generic_score(draft_vec, baseline_vec)

            # Phase C: 3 persona directions — generated in PARALLEL via ThreadPoolExecutor
            # (generate_divergent_directions handles parallelism internally)
            raw_directions = await loop.run_in_executor(
                None, generate_divergent_directions, req.draft, style_signals
            )

            # Phase D: embed all 3 directions CONCURRENTLY to score them
            async def _embed_and_score(d: dict) -> DirectionCard:
                dir_paras = split_into_paragraphs(d["text"])
                dir_vec = await loop.run_in_executor(None, mean_embedding, dir_paras)
                dir_generic, _ = compute_generic_score(dir_vec, baseline_vec)
                return DirectionCard(
                    persona=d["name"],
                    persona_description=d["description"],
                    text=d["text"],
                    generic_distance=dir_generic,
                )

            direction_cards = list(await asyncio.gather(
                *[_embed_and_score(d) for d in raw_directions]
            ))

            return AnalyzeResponse(
                scores=ScoreResult(
                    generic_distance=generic_display,
                    voice_distance=voice_display,
                    generic_raw=generic_raw,
                    voice_raw=voice_raw,
                ),
                directions=direction_cards,
                demo_mode=False,
            )

        return await asyncio.wait_for(_run_analysis(), timeout=settings.analyze_timeout)

    except asyncio.TimeoutError:
        logger.warning("Analysis timed out — returning fixture fallback.")
        fixture = _load_fixture("analyze")
        fixture["demo_mode"] = True
        return AnalyzeResponse(**fixture)
    except Exception as exc:
        logger.error("Analysis error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/fingerprint/validate", response_model=FingerprintResponse)
async def validate_fingerprint(req: FingerprintRequest):
    """Validate voice samples without computing embeddings — fast UX feedback."""
    para_count = sum(
        len(split_into_paragraphs(s)) for s in req.samples
    )
    return FingerprintResponse(
        sample_count=len(req.samples),
        paragraph_count=para_count,
        active=True,
        message=f"{len(req.samples)} samples · {para_count} paragraphs indexed for voice fingerprint.",
    )
