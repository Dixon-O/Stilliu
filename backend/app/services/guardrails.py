"""
guardrails.py — faithfulness / hallucination guard.

Checks whether a generated direction introduces claims that cannot be
grounded in the source material (the user's draft + voice samples).

Strategy: extract "checkable claims" — numbers, percentages, years, quoted
strings, and capitalised multi-word proper nouns — then verify each one
appears (or is paraphrasable) in the source pool. Claims that cannot be
grounded are flagged as unsupported.

This is intentionally heuristic and fast (pure regex + string matching, no
LLM call). It catches the most common hallucination patterns (invented
statistics, fabricated publication names, made-up cities/organisations) while
staying offline-testable.
"""
from __future__ import annotations
import re

# ── Patterns ─────────────────────────────────────────────────────────────────
# Numbers: integers, decimals, percentages, currency amounts, ordinals
_NUM_RE = re.compile(
    r"""
    (?:
        \$\s*[\d,]+(?:\.\d+)?[KkMmBb]?   # $1.2M / $500
      | [\d,]+(?:\.\d+)?\s*%              # 42% / 3.5%
      | \b\d{4}\b                         # years: 1999, 2024
      | \b\d+(?:,\d{3})*(?:\.\d+)?\b     # plain numbers
      | \b(?:first|second|third|\d+th)\b  # ordinals
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Quoted strings (double or single, at least 3 chars)
_QUOTE_RE = re.compile(r'["“”]([^"“”]{3,})["“”]')

# Capitalised multi-word proper nouns (2–5 consecutive Title-Case words,
# not at sentence start — we skip the very first word of a sentence to
# avoid false positives on sentence-initial capitalisation).
_PROPER_RE = re.compile(
    r"(?<![.!?]\s)(?<!\A)(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})"
)


def _normalise(s: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation for fuzzy matching."""
    return re.sub(r"[^\w\s]", "", s.lower()).strip()


def extract_claims(text: str) -> list[str]:
    """
    Extract checkable claims from `text`:
    numbers/percentages/years, quoted strings, and multi-word proper nouns.
    Returns a deduplicated list of raw claim strings.
    """
    claims: list[str] = []
    claims += _NUM_RE.findall(text)
    claims += [m.group(1) for m in _QUOTE_RE.finditer(text)]
    claims += _PROPER_RE.findall(text)
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in claims:
        key = _normalise(c)
        if key and key not in seen:
            seen.add(key)
            out.append(c.strip())
    return out


def _claim_supported(claim: str, source_pool: str) -> bool:
    """Return True if the normalised claim appears anywhere in the source pool."""
    return _normalise(claim) in _normalise(source_pool)


def check_faithfulness(
    generated: str,
    source_texts: list[str],
) -> tuple[int, list[str]]:
    """
    Check `generated` text against a pool of source texts.

    Returns:
        faithfulness_score  — int 0-100; 100 = all claims grounded.
        unsupported         — list of claim strings not found in sources.

    A score of 100 means every extracted claim was found in the source pool
    (or no checkable claims were found). Lower scores indicate hallucination
    risk proportional to the fraction of unsupported claims.
    """
    claims = extract_claims(generated)
    if not claims:
        return 100, []

    pool = " ".join(source_texts)
    unsupported = [c for c in claims if not _claim_supported(c, pool)]
    supported_count = len(claims) - len(unsupported)
    score = round(100 * supported_count / len(claims))
    return score, unsupported
