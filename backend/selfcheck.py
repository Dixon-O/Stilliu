"""
selfcheck.py — offline validation of the measurement engine.

Runs entirely on numpy + stdlib. No watsonx SDK, no network, no credentials.
Execute on the user's machine:  python backend/selfcheck.py

Exits 0 on pass, 1 on any failure.
"""
import sys
import numpy as np

sys.path.insert(0, "backend")

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
failures = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  {PASS}  {name}")
    else:
        print(f"  {FAIL}  {name}" + (f"  ({detail})" if detail else ""))
        failures.append(name)


# ── textutil ─────────────────────────────────────────────────────────────────
print("\n[textutil]")
from app.services.textutil import cosine_distance, clamp, split_into_paragraphs

a = np.array([1.0, 0.0, 0.0])
b = np.array([0.0, 1.0, 0.0])
check("cosine_distance identical",  cosine_distance(a, a) == 0.0)
check("cosine_distance orthogonal", abs(cosine_distance(a, b) - 1.0) < 1e-6)
check("cosine_distance zero-vec",   cosine_distance(np.zeros(3), a) == 1.0)
check("clamp low",  clamp(-5.0, 0.0, 1.0) == 0.0)
check("clamp high", clamp(5.0,  0.0, 1.0) == 1.0)
check("clamp mid",  clamp(0.5,  0.0, 1.0) == 0.5)
paras = split_into_paragraphs("Hello world.\n\nSecond para.")
check("split_into_paragraphs count", len(paras) == 2)
check("split_into_paragraphs empty fallback", split_into_paragraphs("") == [""])

# ── stylometry ────────────────────────────────────────────────────────────────
print("\n[stylometry]")
from app.services.stylometry import (
    style_features, style_vector, style_distance, mean_style_distance,
    FEATURE_NAMES,
)

MINIMALIST = "She left. He stayed. Rain fell."
VERBOSE = (
    "The extraordinarily complex situation unfolded with remarkable, almost "
    "breathtaking, deliberateness; each participant, whether consciously or not, "
    "contributed to the inexorable momentum of events that would, ultimately, "
    "reshape everything they had previously understood about themselves."
)

feats_m = style_features(MINIMALIST)
feats_v = style_features(VERBOSE)
check("style_features returns all keys", set(feats_m.keys()) == set(FEATURE_NAMES))
check("minimalist shorter sentences",
      feats_m["mean_sentence_len"] < feats_v["mean_sentence_len"])
check("verbose longer words",
      feats_m["mean_word_len"] < feats_v["mean_word_len"])

vec = style_vector(MINIMALIST)
check("style_vector shape",  vec.shape == (len(FEATURE_NAMES),))
check("style_vector in [0,1]", bool(np.all(vec >= 0) and np.all(vec <= 1)))

dist_same = style_distance(MINIMALIST, MINIMALIST)
dist_diff = style_distance(MINIMALIST, VERBOSE)
check("style_distance self == 0",       dist_same == 0.0)
check("style_distance in [0,1]",        0.0 <= dist_diff <= 1.0)
check("style_distance different > 0",   dist_diff > 0.0)
check("style_distance minimalist vs verbose > 0.1", dist_diff > 0.1,
      f"got {dist_diff:.4f}")

check("mean_style_distance empty refs == 0",
      mean_style_distance(MINIMALIST, []) == 0.0)
check("mean_style_distance single ref == style_distance",
      abs(mean_style_distance(MINIMALIST, [VERBOSE]) - dist_diff) < 1e-6)

# ── guardrails ────────────────────────────────────────────────────────────────
print("\n[guardrails]")
from app.services.guardrails import extract_claims, check_faithfulness

text_with_claims = (
    'According to the Wall Street Journal, revenue grew 42% to $1.2M in 2023. '
    '"Innovation drives everything," said the CEO.'
)
claims = extract_claims(text_with_claims)
check("extract_claims finds percentage",    any("42" in c for c in claims))
check("extract_claims finds year",          any("2023" in c for c in claims))
check("extract_claims finds quoted string", any("Innovation" in c for c in claims))
check("extract_claims finds proper noun",   any("Wall Street" in c for c in claims))

# All claims grounded in source
score_full, unsupported_full = check_faithfulness(text_with_claims, [text_with_claims])
check("faithfulness 100 when source == generated", score_full == 100,
      f"got {score_full}")
check("no unsupported when source == generated", unsupported_full == [],
      str(unsupported_full))

# Hallucinated claim not in source
source = "The company had a good year."
score_low, unsupported_low = check_faithfulness(text_with_claims, [source])
check("faithfulness < 100 for hallucinated claims", score_low < 100,
      f"got {score_low}")
check("unsupported list non-empty for hallucinated claims", len(unsupported_low) > 0)

# No claims → 100
score_none, _ = check_faithfulness("The sky is blue.", ["The sky is blue."])
check("faithfulness 100 when no checkable claims", score_none == 100)

# ── scoring ───────────────────────────────────────────────────────────────────
print("\n[scoring]")
from app.services.scoring import (
    compute_distinctiveness, compute_voice_match, compute_on_message,
    score_axes, score_summary,
)

rng = np.random.default_rng(seed=7)
dim = 128

draft_vec    = rng.standard_normal(dim).astype(np.float32)
baseline_vec = rng.standard_normal(dim).astype(np.float32)
voice_vec    = rng.standard_normal(dim).astype(np.float32)
dir_vec      = rng.standard_normal(dim).astype(np.float32)

dist_score, raw_sem, raw_sty = compute_distinctiveness(
    draft_vec, baseline_vec, MINIMALIST, VERBOSE)
check("compute_distinctiveness in [0,100]", 0 <= dist_score <= 100,
      f"got {dist_score}")
check("compute_distinctiveness raw_sem >= 0", raw_sem >= 0)
check("compute_distinctiveness raw_sty in [0,1]", 0 <= raw_sty <= 1)

voice_score, _, _ = compute_voice_match(
    draft_vec, voice_vec, MINIMALIST, [VERBOSE])
check("compute_voice_match in [0,100]", 0 <= voice_score <= 100,
      f"got {voice_score}")

msg_score, _ = compute_on_message(draft_vec, draft_vec)
check("compute_on_message self == 100", msg_score == 100.0,
      f"got {msg_score}")

msg_score_diff, _ = compute_on_message(dir_vec, draft_vec)
check("compute_on_message different < 100", msg_score_diff < 100,
      f"got {msg_score_diff}")

axes = score_axes(
    draft_vector=draft_vec,
    draft_str=MINIMALIST,
    baseline_vector=baseline_vec,
    baseline_str=VERBOSE,
    voice_centroid=voice_vec,
    voice_samples=[VERBOSE],
    direction_vector=dir_vec,
    direction_str=VERBOSE,
)
required_keys = {
    "distinctiveness", "voice_match", "on_message",
    "draft_distinctiveness", "draft_voice_match",
    "delta_distinctiveness", "delta_voice_match", "delta_on_message",
    "raw_dist_sem", "raw_dist_sty", "raw_voice_sem", "raw_voice_sty", "raw_msg_sem",
}
check("score_axes returns all keys", required_keys.issubset(axes.keys()))
for k in ("distinctiveness", "voice_match", "on_message"):
    check(f"score_axes {k} in [0,100]", 0 <= axes[k] <= 100, f"got {axes[k]}")

summary = score_summary(axes)
check("score_summary is non-empty string", isinstance(summary, str) and len(summary) > 0)
check("score_summary contains all three axes",
      "Distinctiveness" in summary and "Voice" in summary and "On-message" in summary)

# ── final report ──────────────────────────────────────────────────────────────
print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
else:
    print("All checks passed.")
    sys.exit(0)
