"""
calibrate.py — Live calibration probe for scoring.py constants.

Run from stilliu/backend/ with the venv active:
  python calibrate.py

Prints raw cosine distances between known generic vs distinctive text pairs
so we can set _DIST_SEM_FLOOR and _DIST_SEM_CEIL in scoring.py correctly.

The run is also written to results/calibration-<timestamp>.json (see runlog.py):
these two constants define the entire distinctiveness scale, so the measurements
behind whatever is currently in scoring.py should stay recoverable.
"""
import sys
import os
import numpy as np

# Ensure app module is on path
sys.path.insert(0, os.path.dirname(__file__))

# Override model IDs to correct eu-gb values
os.environ.setdefault("EMBEDDING_MODEL_ID", "ibm/granite-embedding-278m-multilingual")
os.environ.setdefault("GENERATION_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")

from app.config import get_settings
get_settings.cache_clear()

import runlog
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import Embeddings
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

settings = get_settings()
print(f"Region:    {settings.watsonx_url}")
print(f"Embed:     {settings.embedding_model_id}")
print(f"Generate:  {settings.generation_model_id}")
print()

creds = Credentials(url=settings.watsonx_url, api_key=settings.watsonx_api_key)
client = APIClient(credentials=creds, project_id=settings.watsonx_project_id)
emb = Embeddings(
    model_id=settings.embedding_model_id,
    api_client=client,
    params={EmbedParams.TRUNCATE_INPUT_TOKENS: 512},
)

TEXTS = {
    "bland_ai_1": (
        "It is important to consider the various factors that contribute to this topic. "
        "There are many key points to explore and understand in this context. "
        "This subject deserves careful attention and further exploration."
    ),
    "bland_ai_2": (
        "This topic is important and relevant to many people today. "
        "It is essential to understand the key aspects. "
        "In conclusion, there are several things to consider when examining this area."
    ),
    "distinct_human_1": (
        "Nobody warned me the hardest part of starting a company is the silence. "
        "Not the rejections — the silence between them. "
        "Three weeks without a single email and you start wondering if you imagined the whole thing."
    ),
    "distinct_human_2": (
        "The silence between rejections is worse than the rejections. "
        "Nobody tells you that. "
        "You build a whole mythology around the quiet — maybe they forgot, maybe they liked it, maybe, maybe."
    ),
    "mixed_medium": (
        "AI tools have significantly changed how people write. "
        "While they offer many benefits, there are also important considerations about "
        "creativity and originality that writers should think about carefully."
    ),
    "clearly_generic_ai": (
        "In today's rapidly changing world, it is crucial to understand the importance of innovation. "
        "By leveraging cutting-edge technology, we can enhance our capabilities and drive meaningful change. "
        "It is important to consider all stakeholders and ensure that solutions are both sustainable and impactful."
    ),
}


def cos_dist(a: np.ndarray, b: np.ndarray) -> float:
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    return round(float(1 - np.dot(a, b)), 5)


print("Embedding texts (live API call)...")
raw_vecs = emb.embed_documents(texts=list(TEXTS.values()))
vecs = {k: np.array(v, dtype="float32") for k, v in zip(TEXTS.keys(), raw_vecs)}
print(f"Embedding dim: {len(list(vecs.values())[0])}")
print()

print("=" * 55)
print("CALIBRATION: RAW COSINE DISTANCES")
print("=" * 55)
print()
print("-- Similar-style pairs (expect LOW distance) --------")
d_bb = cos_dist(vecs["bland_ai_1"], vecs["bland_ai_2"])
d_dd = cos_dist(vecs["distinct_human_1"], vecs["distinct_human_2"])
print(f"  bland_ai_1   vs bland_ai_2:         {d_bb}  <- expect low")
print(f"  distinct_h_1 vs distinct_h_2:       {d_dd}  <- expect low")
print()
print("-- Cross-style pairs (expect HIGHER distance) -------")
d_bd1 = cos_dist(vecs["bland_ai_1"], vecs["distinct_human_1"])
d_bd2 = cos_dist(vecs["bland_ai_2"], vecs["distinct_human_2"])
d_bd3 = cos_dist(vecs["clearly_generic_ai"], vecs["distinct_human_1"])
print(f"  bland_ai_1   vs distinct_h_1:       {d_bd1}")
print(f"  bland_ai_2   vs distinct_h_2:       {d_bd2}")
print(f"  clearly_gen  vs distinct_h_1:       {d_bd3}  <- clearest separation")
print()
print("-- Mixed medium ----------------------------------")
d_bm = cos_dist(vecs["bland_ai_1"], vecs["mixed_medium"])
d_dm = cos_dist(vecs["distinct_human_1"], vecs["mixed_medium"])
print(f"  bland_ai_1   vs mixed:              {d_bm}  <- should be lower than cross-style")
print(f"  distinct_h_1 vs mixed:              {d_dm}  <- should be lower than cross-style")
print()

# Also probe generation
print("=" * 55)
print("GENERATION PROBE (baseline + one persona)")
print("=" * 55)
sample_draft = (
    "Nobody warned me the hardest part of starting a company is the silence. "
    "Not the rejections — the silence between them."
)

gen_model = ModelInference(
    model_id=settings.generation_model_id,
    api_client=client,
    params={
        GenParams.MAX_NEW_TOKENS: 200,
        GenParams.TEMPERATURE: 0.3,
    },
)

baseline_prompt = (
    "You are a generic AI writing assistant with no distinctive style. "
    "Rewrite the following text in the most average, safe, corporate-bland way possible. "
    "Use cliches, passive voice, filler phrases, and hedge every claim. "
    "Output only the rewritten text, no commentary.\n\n"
    f"Text to rewrite:\n{sample_draft}"
)
print("\nGenerating bland baseline...")
baseline_text = gen_model.generate_text(prompt=baseline_prompt).strip()
print(f"Baseline: {baseline_text}")

# Embed both and compute distance
pair_vecs = emb.embed_documents(texts=[sample_draft, baseline_text])
v_draft = np.array(pair_vecs[0], dtype="float32")
v_baseline = np.array(pair_vecs[1], dtype="float32")
live_dist = cos_dist(v_draft, v_baseline)
print(f"\nDraft vs its OWN baseline distance: {live_dist}")
print("(This is the real-world range we need to normalise around)")
print()
print("=" * 55)
print("RECOMMENDED scoring.py constants:")
floor = min(d_bb, d_dd) + 0.01
ceil = max(d_bd1, d_bd2, d_bd3) - 0.01
# Names match the real constants in app/services/scoring.py so this output is
# directly copy-pasteable. They were once GENERIC_DIST_* here and _DIST_SEM_*
# there, which quietly made the recommendation useless.
print(f"  _DIST_SEM_FLOOR = {floor:.3f}   # below this = very generic")
print(f"  _DIST_SEM_CEIL  = {ceil:.3f}   # above this = very distinctive")
print("=" * 55)

# Persist it. These constants are the calibration the whole distinctiveness axis
# rests on, so "which run produced the numbers currently in scoring.py" needs to
# be answerable months later.
path = runlog.save("calibration", {
    "region": settings.watsonx_url,
    "models": {
        "embedding": settings.embedding_model_id,
        "generation": settings.generation_model_id,
    },
    "embedding_dim": len(list(vecs.values())[0]),
    "same_style_pairs": {
        "bland_vs_bland": d_bb,
        "distinct_vs_distinct": d_dd,
    },
    "cross_style_pairs": {
        "bland_1_vs_distinct_1": d_bd1,
        "bland_2_vs_distinct_2": d_bd2,
        "clearly_generic_vs_distinct_1": d_bd3,
    },
    "mixed_medium": {
        "bland_vs_mixed": d_bm,
        "distinct_vs_mixed": d_dm,
    },
    "live_baseline_probe": {
        "draft": sample_draft,
        "baseline_text": baseline_text,
        "distance": live_dist,
    },
    "recommended_constants": {
        "_DIST_SEM_FLOOR": round(floor, 3),
        "_DIST_SEM_CEIL": round(ceil, 3),
    },
})
runlog.announce(path)
