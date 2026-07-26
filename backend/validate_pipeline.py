"""
validate_pipeline.py — Full end-to-end pipeline validation.
Run: python validate_pipeline.py  (from stilliu/backend with venv active)
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from app.config import get_settings
get_settings.cache_clear()

from app.services.embeddings import get_embedding_client, mean_embedding, split_into_paragraphs
from app.services.generation import get_generation_client, generate_baseline, generate_divergent_directions
from app.services.fingerprint import build_voice_centroid, extract_style_signals
from app.services.scoring import compute_generic_score, compute_voice_score

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
print(f"    Warm-up: {time.time()-t0:.1f}s")

print("\n[2] Scoring draft...")
t0 = time.time()
draft_paras = split_into_paragraphs(DRAFT)
draft_vec = mean_embedding(draft_paras)
baseline_text = generate_baseline(DRAFT)
baseline_vec = mean_embedding(split_into_paragraphs(baseline_text))
generic_display, generic_raw = compute_generic_score(draft_vec, baseline_vec)
print(f"    Time: {time.time()-t0:.1f}s")
print(f"    generic_distance : {generic_display}/100  (raw: {generic_raw:.4f})")
print(f"    Baseline preview : {baseline_text[:120]}")

print("\n[3] Voice fingerprint...")
centroid = build_voice_centroid(VOICE_SAMPLES)
voice_display, voice_raw = compute_voice_score(draft_vec, centroid)
signals = extract_style_signals(VOICE_SAMPLES)
print(f"    voice_distance   : {voice_display}/100  (raw: {voice_raw:.4f})")
print(f"    Style signals    : avg_sent={signals['avg_sentence_length']}  richness={signals['vocabulary_richness']}")

print("\n[4] Generating 3 divergent directions (parallel)...")
t0 = time.time()
directions = generate_divergent_directions(DRAFT, style_signals=signals)
print(f"    Generation time  : {time.time()-t0:.1f}s")

all_scores_lower = True
for d in directions:
    dir_vec = mean_embedding(split_into_paragraphs(d["text"]))
    dir_score, _ = compute_generic_score(dir_vec, baseline_vec)
    is_lower = dir_score < generic_display
    if not is_lower:
        all_scores_lower = False
    print(f"\n    [{d['name']}]  generic_score={dir_score}/100  {'LOWER' if is_lower else 'NOT lower'}")
    print(f"    {d['text'][:240]}")

print("\n" + "=" * 60)
print(f"Score check (directions < original): {'PASS' if all_scores_lower else 'NOTE: some directions scored >= original'}")
print(f"Original generic_distance: {generic_display}/100")
print("PIPELINE VALIDATION COMPLETE")
print("=" * 60)
