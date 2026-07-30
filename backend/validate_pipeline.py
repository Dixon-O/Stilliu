"""
validate_pipeline.py — Full end-to-end pipeline validation (live watsonx calls).
Run: python validate_pipeline.py  (from stilliu/backend with venv active)

Requires real credentials in .env. For offline validation of the deterministic
math with no credentials, run selfcheck.py instead.

Every run is recorded to results/validation-<timestamp>.json (see runlog.py), so
the headline number — how many directions actually beat the draft — can be
compared across runs instead of scrolling out of the terminal.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from app.config import get_settings
get_settings.cache_clear()

import runlog
from app.models import WriterControls
from app.services import model_registry
from app.services.embeddings import get_embedding_client, mean_embedding, split_into_paragraphs
from app.services.generation import (
    get_generation_client, get_baseline_client,
    generate_baseline, generate_divergent_directions,
)
from app.services.fingerprint import build_voice_centroid
from app.services.scoring import compute_distinctiveness, compute_voice_match, score_axes
from app.services.guardrails import check_faithfulness

DRAFT = (
    "Nobody warned me the hardest part of starting a company is the silence. "
    "Not the rejections. The silence between them. Three weeks without a single "
    "email and you start wondering if you imagined the whole thing."
)

VOICE_SAMPLES = [
    "The thing about Lagos traffic is it teaches you patience or it breaks you. "
    "There is no middle. I have watched men sob quietly in gridlock at 9am on a Tuesday. "
    "I have been that man.",
    "Every city has its particular cruelty. London's is the weather pretending it might improve. "
    "You pack an umbrella and it mocks you with sun.",
]

print("=" * 60)
print("STILLIU — Full Pipeline Validation")
print("=" * 60)

print("\n[1] Warming SDK clients...")
t0 = time.time()
get_embedding_client()
get_generation_client()
get_baseline_client()
warmup_s = round(time.time() - t0, 1)
print(f"    Warm-up: {warmup_s}s")

# Which ids the region actually served. Recorded because a score is only
# comparable across runs if the models behind it were the same.
_res = model_registry.cached()
models = {
    "creative": _res.creative.model_id if _res else get_settings().generation_model_id,
    "baseline": _res.baseline.model_id if _res else get_settings().baseline_model_id,
    "embedding": _res.embedding.model_id if _res else get_settings().embedding_model_id,
}
print(f"    creative : {models['creative']}")
print(f"    baseline : {models['baseline']}")
print(f"    embedding: {models['embedding']}")

print("\n[2] Scoring draft...")
t0 = time.time()
draft_paras = split_into_paragraphs(DRAFT)
draft_vec = mean_embedding(draft_paras)
baseline_text = generate_baseline(DRAFT)
baseline_vec = mean_embedding(split_into_paragraphs(baseline_text))
draft_dist, dist_sem, dist_sty = compute_distinctiveness(draft_vec, baseline_vec, DRAFT, baseline_text)
print(f"    Time: {time.time()-t0:.1f}s")
print(f"    draft distinctiveness : {draft_dist}/100  (sem={dist_sem:.4f}  style={dist_sty:.4f})")
print(f"    Baseline preview      : {baseline_text[:120]}")

print("\n[3] Voice fingerprint...")
centroid = build_voice_centroid(VOICE_SAMPLES)
draft_voice, voice_sem, voice_sty = compute_voice_match(draft_vec, centroid, DRAFT, VOICE_SAMPLES)
print(f"    draft voice match     : {draft_voice}/100  (sem={voice_sem:.4f}  style={voice_sty:.4f})")

print("\n[4] Generating divergent directions (parallel)...")
t0 = time.time()
controls = WriterControls(voice_strength=0.6)
directions = generate_divergent_directions(DRAFT, VOICE_SAMPLES, controls)
print(f"    Generation time  : {time.time()-t0:.1f}s")

gen_s = round(time.time() - t0, 1)
more_distinct = 0
records: list[dict] = []
source_pool = [DRAFT] + VOICE_SAMPLES
for d in directions:
    dir_vec = mean_embedding(split_into_paragraphs(d["text"]))
    axes = score_axes(
        draft_vector=draft_vec, draft_str=DRAFT,
        baseline_vector=baseline_vec, baseline_str=baseline_text,
        voice_centroid=centroid, voice_samples=VOICE_SAMPLES,
        direction_vector=dir_vec, direction_str=d["text"],
    )
    faith, unsupported = check_faithfulness(d["text"], source_pool)
    if axes["distinctiveness"] > draft_dist:
        more_distinct += 1
    records.append({
        "style": d["name"],
        "distinctiveness": axes["distinctiveness"],
        "delta_distinctiveness": axes["delta_distinctiveness"],
        "voice_match": axes["voice_match"],
        "on_message": axes["on_message"],
        "faithfulness": faith,
        "unsupported_claims": unsupported,
        "beat_the_draft": axes["distinctiveness"] > draft_dist,
    })
    print(f"\n    [{d['name']}]")
    print(f"    distinctiveness={axes['distinctiveness']}/100 (Δ{axes['delta_distinctiveness']:+})  "
          f"voice={axes['voice_match']}/100  on_message={axes['on_message']}/100  faith={faith}/100")
    if unsupported:
        print(f"    unsupported claims: {unsupported}")
    print(f"    {d['text'][:240]}")

print("\n" + "=" * 60)
print(f"Directions more distinctive than draft: {more_distinct}/{len(directions)}")
print(f"Draft distinctiveness: {draft_dist}/100")
print("PIPELINE VALIDATION COMPLETE")
print("=" * 60)

# The claim this script exists to support: a rewrite that scores higher than the
# draft on the axis the tool is named for. Persist it so it is quotable.
path = runlog.save("validation", {
    "region": get_settings().watsonx_url,
    "models": models,
    "timings_s": {"warmup": warmup_s, "generation": gen_s},
    "draft": {
        "distinctiveness": draft_dist,
        "semantic_distance": round(dist_sem, 4),
        "style_distance": round(dist_sty, 4),
        "voice_match": draft_voice,
    },
    "directions": records,
    "headline": {
        "directions_generated": len(directions),
        "beat_the_draft": more_distinct,
        "best_delta": max((r["delta_distinctiveness"] for r in records), default=None),
    },
})
runlog.announce(path)
