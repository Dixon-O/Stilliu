"""
generation.py — Granite generation for:
  1. The "bland AI default" baseline (used for Generic Distance measurement).
  2. Three persona-constrained divergent directions (run in parallel).

SDK client is cached at module level — same pattern as embeddings.py.
Cold-start ~3s on first call; subsequent calls ~8s for 400-token output.
"""
from __future__ import annotations
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Module-level client cache ────────────────────────────────────────────────
_generation_client: ModelInference | None = None


def get_generation_client() -> ModelInference:
    global _generation_client
    if _generation_client is None:
        settings = get_settings()
        logger.info("Initialising generation client (one-time cold start)...")
        credentials = Credentials(
            url=settings.watsonx_url,
            api_key=settings.watsonx_api_key,
        )
        api_client = APIClient(credentials=credentials, project_id=settings.watsonx_project_id)
        _generation_client = ModelInference(
            model_id=settings.generation_model_id,
            api_client=api_client,
            params={
                GenParams.MAX_NEW_TOKENS: 400,
                GenParams.TEMPERATURE: 0.8,
                GenParams.TOP_P: 0.95,
                GenParams.REPETITION_PENALTY: 1.15,
            },
        )
        logger.info("Generation client ready.")
    return _generation_client


# ── Personas ─────────────────────────────────────────────────────────────────

PERSONAS = [
    {
        "name": "Sparse Minimalist",
        "description": "Short sentences. Nothing decorative. Meaning carried by what is left out.",
        "instruction": (
            "Rewrite the following draft as a Sparse Minimalist. "
            "Use short, declarative sentences. Strip every adjective that does not change meaning. "
            "Remove all filler phrases ('in order to', 'the fact that', 'it is important'). "
            "Do NOT use long flowing sentences, metaphors, or rhetorical questions. "
            "The power comes from compression and silence."
        ),
    },
    {
        "name": "The Arguer",
        "description": "Leads with a bold claim. Builds a case. Anticipates pushback and answers it.",
        "instruction": (
            "Rewrite the following draft as The Arguer. "
            "Open with a direct, controversial, or counterintuitive claim. "
            "Build your case step by step, anticipating the strongest objection, then answering it. "
            "Do NOT use hedging language ('perhaps', 'might', 'some people think'). "
            "Do NOT start with a question. Every sentence should advance the argument."
        ),
    },
    {
        "name": "Sensory-Led",
        "description": "Grounds ideas in physical sensation, texture, and concrete scene.",
        "instruction": (
            "Rewrite the following draft as Sensory-Led. "
            "Open with a concrete sensory detail — something seen, heard, felt, or smelled. "
            "Ground every abstract idea in a physical object, texture, or moment. "
            "Do NOT begin with an abstract claim or a statistic. "
            "Do NOT use the words 'important', 'significant', or 'interesting'. "
            "Make the reader feel present in the idea."
        ),
    },
]


def _build_voice_anchor(style_signals: dict | None) -> str:
    """Construct a voice-constraint clause from extracted style signals."""
    if not style_signals:
        return ""
    parts = []
    avg = style_signals.get("avg_sentence_length", 0)
    if avg < 12:
        parts.append("keep sentences short (under 15 words on average)")
    elif avg > 22:
        parts.append("use longer, more developed sentences")
    richness = style_signals.get("vocabulary_richness", 0)
    if richness > 0.7:
        parts.append("use varied, precise vocabulary")
    punct = style_signals.get("dominant_punctuation", [])
    if "\u2014" in punct or "\u2013" in punct:
        parts.append("em-dashes are welcome where natural")
    if not parts:
        return ""
    return " Voice constraint: " + "; ".join(parts) + "."


def generate_baseline(draft: str) -> str:
    """
    Generate a bland AI-default rewrite of the draft.
    This is the anchor for the Generic Distance measurement.
    Uses lower temperature for consistent, reliably bland output.
    """
    settings = get_settings()
    if settings.demo_mode:
        return (
            "This text explores an important topic that many people find relevant today. "
            "There are several key points to consider. First, it is important to understand "
            "the context. Additionally, there are various factors that contribute to this. "
            "In conclusion, this subject deserves further attention and exploration."
        )

    model = get_generation_client()
    prompt = (
        "You are a generic AI writing assistant with no distinctive style. "
        "Rewrite the following text in the most average, safe, corporate-bland way possible. "
        "Use cliches, passive voice, filler phrases, and hedge every claim. "
        "Output only the rewritten text, no commentary.\n\n"
        f"Text to rewrite:\n{draft}"
    )
    # Override params for baseline: lower temp, fewer tokens for consistency
    response = model.generate_text(
        prompt=prompt,
        params={GenParams.MAX_NEW_TOKENS: 300, GenParams.TEMPERATURE: 0.2},
    )
    return response.strip()


def generate_single_direction(draft: str, persona: dict, voice_anchor: str) -> dict:
    """
    Generate one persona direction. Called in parallel via ThreadPoolExecutor.
    Uses the cached client — thread-safe for concurrent reads.
    """
    model = get_generation_client()
    prompt = (
        f"{persona['instruction']}{voice_anchor}\n\n"
        f"Draft to transform:\n{draft}\n\n"
        f"Output only the rewritten text, no labels, no preamble, no commentary."
    )
    try:
        text = model.generate_text(prompt=prompt).strip()
        # Strip any accidental label prefix the model might add
        for prefix in [f"{persona['name']}:", "Direction:", "Rewrite:", "Output:"]:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
    except Exception as exc:
        logger.error("Generation failed for persona %s: %s", persona["name"], exc)
        text = draft
    return {"name": persona["name"], "description": persona["description"], "text": text}


def generate_divergent_directions(
    draft: str,
    style_signals: dict | None = None,
) -> list[dict]:
    """
    Generate three divergent directions IN PARALLEL.
    Wall-clock time ≈ single generation time (~8–10s), not 3x.
    """
    settings = get_settings()
    if settings.demo_mode:
        return _fixture_directions()

    voice_anchor = _build_voice_anchor(style_signals)
    results_map: dict[str, dict] = {}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(generate_single_direction, draft, persona, voice_anchor): persona
            for persona in PERSONAS
        }
        for future in as_completed(futures):
            persona = futures[future]
            try:
                results_map[persona["name"]] = future.result()
            except Exception as exc:
                logger.error("Persona %s failed: %s", persona["name"], exc)
                results_map[persona["name"]] = {
                    "name": persona["name"],
                    "description": persona["description"],
                    "text": draft,
                }

    return [results_map[p["name"]] for p in PERSONAS]


def _fixture_directions() -> list[dict]:
    return [
        {
            "name": "Sparse Minimalist",
            "description": "Short sentences. Nothing decorative. Meaning carried by what is left out.",
            "text": "AI erases voices. Not through malice — through averaging. Every writer who leans on it drifts toward the mean. The work gets cleaner. Blander. Safer. That's the cost nobody mentions.",
        },
        {
            "name": "The Arguer",
            "description": "Leads with a bold claim. Builds a case. Anticipates pushback and answers it.",
            "text": "AI homogenisation is the most underreported threat to writing culture right now. Yes, individual quality improves — Doshi and Hauser proved it. But read a hundred AI-assisted essays and you'll find the same cadence, the same hedges, the same arc. The counterargument is that good ideas transcend style. That's wrong. Style is how an idea becomes yours.",
        },
        {
            "name": "Sensory-Led",
            "description": "Grounds ideas in physical sensation, texture, and concrete scene.",
            "text": "Paste your draft into any AI assistant. Watch it come back smoother, rounder, emptier — like river stones that lost their edges in the current. That's what homogenisation feels like from the inside: not loss, but a quiet erasure of the grain.",
        },
    ]
