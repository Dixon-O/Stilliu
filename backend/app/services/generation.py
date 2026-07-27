"""
generation.py — watsonx generation (HYBRID model strategy):
  1. The "bland AI default" baseline — Granite instruct model (falls back to the
     creative model if the Granite id is unavailable in-region). This is the
     anchor for the Distinctiveness measurement.
  2. Persona-constrained divergent directions — Llama-3-3-70b, run in parallel,
     shaped by the writer's controls (format, length, tone, audience, voice).

SDK clients are cached at module level — same pattern as embeddings.py.
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
_baseline_client: ModelInference | None = None
_shared_api_client: APIClient | None = None


def _api_client() -> APIClient:
    global _shared_api_client
    if _shared_api_client is None:
        settings = get_settings()
        credentials = Credentials(url=settings.watsonx_url, api_key=settings.watsonx_api_key)
        _shared_api_client = APIClient(credentials=credentials, project_id=settings.watsonx_project_id)
    return _shared_api_client


def get_generation_client() -> ModelInference:
    global _generation_client
    if _generation_client is None:
        settings = get_settings()
        logger.info("Initialising creative generation client (one-time cold start)...")
        _generation_client = ModelInference(
            model_id=settings.generation_model_id,
            api_client=_api_client(),
            params={
                GenParams.MAX_NEW_TOKENS: 400,
                GenParams.TEMPERATURE: 0.8,
                GenParams.TOP_P: 0.95,
                GenParams.REPETITION_PENALTY: 1.15,
            },
        )
        logger.info("Creative generation client ready.")
    return _generation_client


def get_baseline_client() -> ModelInference:
    """
    Granite instruct client for the bland baseline. Falls back to the creative
    model id if the Granite model can't be instantiated in-region.
    """
    global _baseline_client
    if _baseline_client is None:
        settings = get_settings()
        for model_id in (settings.baseline_model_id, settings.generation_model_id):
            try:
                logger.info("Initialising baseline client with %s ...", model_id)
                _baseline_client = ModelInference(
                    model_id=model_id,
                    api_client=_api_client(),
                    params={GenParams.MAX_NEW_TOKENS: 300, GenParams.TEMPERATURE: 0.2},
                )
                break
            except Exception as exc:  # pragma: no cover - depends on region availability
                logger.warning("Baseline model %s unavailable (%s); trying fallback.", model_id, exc)
        if _baseline_client is None:  # pragma: no cover
            _baseline_client = get_generation_client()
    return _baseline_client

# ── Personas ─────────────────────────────────────────────────────────────────

PERSONAS = [
    {
        "name": "Sparse Minimalist",
        "description": "Short sentences. Nothing decorative. Meaning carried by what is left out.",
        "instruction": (
            "Rewrite the text below. Style: Sparse Minimalist. "
            "Rules: short declarative sentences only, no adjectives unless they change meaning, "
            "no filler phrases, no metaphors, no rhetorical questions."
        ),
    },
    {
        "name": "The Arguer",
        "description": "Leads with a bold claim. Builds a case. Anticipates pushback and answers it.",
        "instruction": (
            "Rewrite the text below. Style: The Arguer. "
            "Rules: open with a bold, direct claim; build the argument step by step; "
            "address the strongest objection and refute it; no hedging words "
            "('perhaps', 'might', 'some people think'); do not start with a question."
        ),
    },
    {
        "name": "Sensory-Led",
        "description": "Grounds ideas in physical sensation, texture, and concrete scene.",
        "instruction": (
            "Rewrite the text below. Style: Sensory-Led. "
            "Rules: open with a concrete sensory detail (seen, heard, felt, smelled); "
            "ground every abstract idea in a physical object or moment; "
            "do not use the words 'important', 'significant', or 'interesting'; "
            "do not start with an abstract claim or statistic."
        ),
    },
]

PERSONAS_BY_NAME = {p["name"]: p for p in PERSONAS}


def _resolve_personas(controls) -> list[dict]:
    """Select which personas to run based on writer controls."""
    chosen: list[dict] = []
    names = getattr(controls, "personas", None)
    if names:
        for n in names:
            if n in PERSONAS_BY_NAME:
                chosen.append(PERSONAS_BY_NAME[n])
    if not chosen:
        chosen = list(PERSONAS)
    custom = getattr(controls, "custom_persona", "") or ""
    if custom.strip():
        chosen.append({
            "name": "Your Custom Direction",
            "description": custom.strip()[:80],
            "instruction": f"Rewrite the text below following this style brief: {custom.strip()}",
        })
    return chosen


# ── Prompt construction ───────────────────────────────────────────────────────

_FORMAT_CLAUSE = {
    "prose":    "Write flowing prose in complete paragraphs.",
    "bullets":  "Structure the output as tight bullet points.",
    "punchy":   "Keep it punchy — short paragraphs, high impact, nothing wasted.",
    "longform": "Develop the piece more fully with well-formed paragraphs.",
}
_LENGTH_CLAUSE = {
    "shorter": "Make it noticeably shorter than the draft — cut hard.",
    "match":   "Keep roughly the same length as the draft.",
    "longer":  "Expand it somewhat beyond the draft's length.",
}


def _controls_clause(controls) -> str:
    """Turn writer controls into an explicit instruction clause."""
    if controls is None:
        return ""
    bits: list[str] = []
    fmt = getattr(controls, "fmt", "prose")
    if fmt in _FORMAT_CLAUSE and fmt != "prose":
        bits.append(_FORMAT_CLAUSE[fmt])
    length = getattr(controls, "length", "match")
    if length in _LENGTH_CLAUSE and length != "match":
        bits.append(_LENGTH_CLAUSE[length])
    tone = (getattr(controls, "tone", "") or "").strip()
    if tone:
        bits.append(f"Tone: {tone}.")
    audience = (getattr(controls, "audience", "") or "").strip()
    if audience:
        bits.append(f"Write for this audience: {audience}.")
    if getattr(controls, "preserve_facts", True):
        bits.append(
            "Do NOT invent facts, names, statistics, quotes, publications, or places. "
            "Use only information present in the draft."
        )
    return (" " + " ".join(bits)) if bits else ""


def _voice_anchor(voice_samples: list[str] | None, controls) -> str:
    """
    Verbatim voice few-shot anchoring: show the model real author sentences so it
    can imitate cadence and diction, scaled by voice_strength.
    """
    if not voice_samples:
        return ""
    strength = getattr(controls, "voice_strength", 0.5) if controls else 0.5
    if strength <= 0.05:
        return ""
    # Take up to ~3 short excerpts as concrete anchors.
    excerpts = []
    for s in voice_samples[:3]:
        s = s.strip().replace("\n", " ")
        if s:
            excerpts.append(s[:220])
    if not excerpts:
        return ""
    joined = "\n".join(f"  • {e}" for e in excerpts)
    hug = (
        "Match this author's voice closely — mirror their sentence rhythm, diction, and habits."
        if strength >= 0.66 else
        "Let this author's voice inform the rewrite while still applying the persona."
        if strength >= 0.33 else
        "Keep a light echo of this author's voice."
    )
    return (
        f"\n\nThe author writes like this:\n{joined}\n{hug}"
    )


# ── Baseline (Granite) ────────────────────────────────────────────────────────

def generate_baseline(draft: str) -> str:
    """
    Generate a bland AI-default rewrite of the draft using Granite.
    This is the anchor for the Distinctiveness measurement.
    """
    settings = get_settings()
    if settings.demo_mode:
        return (
            "This text explores an important topic that many people find relevant today. "
            "There are several key points to consider. First, it is important to understand "
            "the context. Additionally, there are various factors that contribute to this. "
            "In conclusion, this subject deserves further attention and exploration."
        )

    model = get_baseline_client()
    prompt = (
        "You are a generic AI writing assistant with no distinctive style. "
        "Rewrite the following text in the most average, safe, corporate-bland way possible. "
        "Use cliches, passive voice, filler phrases, and hedge every claim. "
        "Output only the rewritten text, no commentary.\n\n"
        f"Text to rewrite:\n{draft}"
    )
    response = model.generate_text(prompt=prompt)
    return response.strip()


# ── Directions (Llama) ────────────────────────────────────────────────────────

def _clean_output(text: str, persona_name: str) -> str:
    text = text.strip()
    for prefix in [f"{persona_name}:", "Direction:", "Rewrite:", "Output:", "Rewritten text:"]:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()
    return text


def generate_single_direction(
    draft: str,
    persona: dict,
    voice_samples: list[str] | None,
    controls,
) -> dict:
    """Generate one persona direction. Called in parallel via ThreadPoolExecutor."""
    model = get_generation_client()
    prompt = (
        f"{persona['instruction']}{_controls_clause(controls)}"
        f"{_voice_anchor(voice_samples, controls)}\n\n"
        f"Draft to transform:\n{draft}\n\n"
        f"Write the rewritten text immediately. Do not add notes, labels, preamble, "
        f"or commentary of any kind. Stop after the rewrite."
    )
    try:
        text = _clean_output(model.generate_text(prompt=prompt), persona["name"])
    except Exception as exc:
        logger.error("Generation failed for persona %s: %s", persona["name"], exc)
        text = draft
    return {"name": persona["name"], "description": persona["description"], "text": text}


def generate_divergent_directions(
    draft: str,
    voice_samples: list[str] | None = None,
    controls=None,
) -> list[dict]:
    """Generate divergent directions IN PARALLEL. Wall-clock ≈ single generation."""
    settings = get_settings()
    if settings.demo_mode:
        return _fixture_directions()

    personas = _resolve_personas(controls)
    results_map: dict[str, dict] = {}

    with ThreadPoolExecutor(max_workers=min(4, len(personas))) as pool:
        futures = {
            pool.submit(generate_single_direction, draft, persona, voice_samples, controls): persona
            for persona in personas
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

    return [results_map[p["name"]] for p in personas]


def regenerate_direction(
    draft: str,
    persona_name: str,
    persona_description: str,
    voice_samples: list[str] | None,
    controls,
    feedback: str,
) -> dict:
    """
    Regenerate one direction with corrective feedback appended — used by the
    refine loop when a direction scores poorly or fails the faithfulness guard.
    """
    settings = get_settings()
    if settings.demo_mode:
        return {"name": persona_name, "description": persona_description, "text": draft}

    persona = PERSONAS_BY_NAME.get(persona_name, {
        "name": persona_name,
        "description": persona_description,
        "instruction": f"Rewrite the text below in the style: {persona_description}",
    })
    model = get_generation_client()
    prompt = (
        f"{persona['instruction']}{_controls_clause(controls)}"
        f"{_voice_anchor(voice_samples, controls)}\n\n"
        f"Previous attempt fell short: {feedback}\n"
        f"Fix exactly that while keeping the persona.\n\n"
        f"Draft to transform:\n{draft}\n\n"
        f"Write only the rewritten text. No notes, labels, or commentary."
    )
    try:
        text = _clean_output(model.generate_text(prompt=prompt), persona_name)
    except Exception as exc:
        logger.error("Regeneration failed for %s: %s", persona_name, exc)
        text = draft
    return {"name": persona_name, "description": persona_description, "text": text}


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
            "text": "AI homogenisation is the most underreported threat to writing culture right now. Yes, individual quality improves. But read a hundred AI-assisted essays and you'll find the same cadence, the same hedges, the same arc. The counterargument is that good ideas transcend style. That's wrong. Style is how an idea becomes yours.",
        },
        {
            "name": "Sensory-Led",
            "description": "Grounds ideas in physical sensation, texture, and concrete scene.",
            "text": "Paste your draft into any AI assistant. Watch it come back smoother, rounder, emptier — like river stones that lost their edges in the current. That's what homogenisation feels like from the inside: not loss, but a quiet erasure of the grain.",
        },
    ]

