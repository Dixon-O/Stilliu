"""
stylometry.py — topic-independent style features.

Sentence embeddings capture *what* a text is about; they are weak at *how* it is
written. Two rewrites of the same subject sit close together in embedding space
even when their prose styles are wildly different — which is exactly why a bold
stylistic rewrite can still score as "generic" on pure embedding distance.

This module extracts a compact, deterministic vector of classic stylometric
markers — sentence rhythm, lexical variety, function-word mix, punctuation
profile, lexical sophistication — that are largely invariant to topic. Distances
between two texts' style vectors give a real, reproducible "style distance" that
complements semantic (embedding) distance. Together they let us separate
STYLE distinctiveness from TOPIC distance.
"""
from __future__ import annotations
import re
import numpy as np

# ── Lexicons ──────────────────────────────────────────────────────────────────
# Function words: the backbone of stylometric / authorship signal. Their relative
# frequency is topic-independent and characteristic of an author's cadence.
FUNCTION_WORDS: frozenset[str] = frozenset("""
a an the and but or nor for yet so as if than then that this these those
i you he she it we they me him her us them my your his its our their mine yours
is am are was were be been being do does did done have has had having
will would shall should can could may might must ought
of in on at by to from with about into onto over under above below between among
through during before after since until while because although though unless
not no yes very too also just only even still more most much many few little
here there where when why how what which who whom whose
up down out off away back again once
""".split())

# A small set of very common content words, unioned with function words, used as
# the "known/common" vocabulary for the rare-word (lexical sophistication) proxy.
COMMON_EXTRA: frozenset[str] = frozenset("""
time year day people way man woman child work life world hand part place case
week company system program question government number group problem fact
say get make go know take see come think look want give use find tell ask
work seem feel try leave call good new first last long great little own other
old right big high different small large next early young important public bad
same able one two three ten thing things something someone everyone nothing
""".split())
COMMON_WORDS: frozenset[str] = FUNCTION_WORDS | COMMON_EXTRA

_WORD_RE = re.compile(r"[A-Za-z']+")
_SENT_RE = re.compile(r"[.!?]+")

# ── Feature definitions ─────────────────────────────────────────────────────
# Each feature is paired with a (min, max) scale used to map it into [0, 1] so
# the feature vector is dimensionless and distances are bounded. Ranges reflect
# typical English prose; they are heuristic anchors, tunable via calibrate.py.
FEATURE_SCALES: dict[str, tuple[float, float]] = {
    "mean_sentence_len":   (5.0, 30.0),   # words per sentence
    "sentence_len_std":    (0.0, 14.0),   # burstiness — variation in sentence length
    "mean_word_len":       (3.2, 6.5),    # characters per word
    "type_token_ratio":    (0.30, 0.90),  # unique / total words — lexical variety
    "function_word_ratio": (0.30, 0.60),  # function words / total words
    "rare_word_ratio":     (0.05, 0.55),  # words outside the common set — sophistication
    "comma_density":       (0.00, 0.14),  # commas per word
    "semicolon_density":   (0.00, 0.03),  # semicolons per word
    "dash_density":        (0.00, 0.05),  # em/en dashes per word
    "question_density":    (0.00, 0.60),  # questions per sentence
    "exclaim_density":     (0.00, 0.60),  # exclamations per sentence
    "long_word_ratio":     (0.00, 0.42),  # share of words longer than 6 chars
}
FEATURE_NAMES: list[str] = list(FEATURE_SCALES.keys())


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_RE.split(text) if s.strip()]


def style_features(text: str) -> dict[str, float]:
    """Compute the raw (un-normalised) stylometric features of a text."""
    words = _WORD_RE.findall(text.lower())
    sentences = _sentences(text)
    n_words = max(len(words), 1)
    n_sents = max(len(sentences), 1)

    sent_lens = [len(_WORD_RE.findall(s)) for s in sentences] or [0]
    unique = set(words)

    function_hits = sum(1 for w in words if w in FUNCTION_WORDS)
    rare_hits = sum(1 for w in words if w not in COMMON_WORDS)
    long_hits = sum(1 for w in words if len(w) > 6)

    return {
        "mean_sentence_len":   float(np.mean(sent_lens)),
        "sentence_len_std":    float(np.std(sent_lens)),
        "mean_word_len":       sum(len(w) for w in words) / n_words,
        "type_token_ratio":    len(unique) / n_words,
        "function_word_ratio": function_hits / n_words,
        "rare_word_ratio":     rare_hits / n_words,
        "comma_density":       text.count(",") / n_words,
        "semicolon_density":   text.count(";") / n_words,
        "dash_density":        (text.count("—") + text.count("–") + text.count(" - ")) / n_words,
        "question_density":    text.count("?") / n_sents,
        "exclaim_density":     text.count("!") / n_sents,
        "long_word_ratio":     long_hits / n_words,
    }


def style_vector(text: str) -> np.ndarray:
    """Return the feature vector mapped into [0, 1] per FEATURE_SCALES."""
    feats = style_features(text)
    out = np.empty(len(FEATURE_NAMES), dtype=np.float32)
    for i, name in enumerate(FEATURE_NAMES):
        lo, hi = FEATURE_SCALES[name]
        span = hi - lo if hi > lo else 1.0
        out[i] = max(0.0, min(1.0, (feats[name] - lo) / span))
    return out


def style_distance(text_a: str, text_b: str) -> float:
    """
    Normalised Euclidean distance between two texts' style vectors, in [0, 1].
    0 = stylistically identical, 1 = maximally different across all markers.
    """
    va, vb = style_vector(text_a), style_vector(text_b)
    dist = float(np.linalg.norm(va - vb))
    # Max possible distance is sqrt(n_features) (all dims differ by 1.0).
    return dist / np.sqrt(len(FEATURE_NAMES))


def mean_style_distance(text: str, references: list[str]) -> float:
    """Average style distance from `text` to a set of reference texts."""
    if not references:
        return 0.0
    return float(np.mean([style_distance(text, r) for r in references]))
