"""
tests/test_guardrails.py — Unit tests for the faithfulness / hallucination guard.
"""
import pytest
from app.services.guardrails import extract_claims, check_faithfulness


class TestExtractClaims:
    def test_finds_percentage(self):
        claims = extract_claims("Revenue grew 42% last year.")
        assert any("42" in c for c in claims)

    def test_finds_year(self):
        claims = extract_claims("This happened in 2023.")
        assert any("2023" in c for c in claims)

    def test_finds_currency(self):
        claims = extract_claims("The deal was worth $1.2M.")
        assert any("1.2" in c for c in claims)

    def test_finds_quoted_string(self):
        claims = extract_claims('"Innovation drives everything," said the CEO.')
        assert any("Innovation" in c for c in claims)

    def test_finds_proper_noun(self):
        claims = extract_claims("According to the Wall Street Journal, sales rose.")
        assert any("Wall Street" in c for c in claims)

    def test_empty_text_returns_empty(self):
        assert extract_claims("") == []

    def test_no_claims_in_plain_prose(self):
        claims = extract_claims("The sky is blue and the grass is green.")
        assert len(claims) == 0


class TestCheckFaithfulness:
    def test_perfect_score_when_source_equals_generated(self):
        text = "Revenue grew 42% to $1.2M in 2023."
        score, unsupported = check_faithfulness(text, [text])
        assert score == 100
        assert unsupported == []

    def test_low_score_for_hallucinated_claims(self):
        generated = "According to the Wall Street Journal, revenue grew 42% in 2023."
        source = "The company had a good year."
        score, unsupported = check_faithfulness(generated, [source])
        assert score < 100
        assert len(unsupported) > 0

    def test_100_when_no_checkable_claims(self):
        score, unsupported = check_faithfulness("The sky is blue.", ["The sky is blue."])
        assert score == 100
        assert unsupported == []

    def test_multiple_sources_pooled(self):
        generated = "Revenue grew 42% and the CEO said 'great results'."
        sources = ["Revenue grew 42%.", "The CEO said 'great results'."]
        score, unsupported = check_faithfulness(generated, sources)
        assert score == 100

    def test_score_is_proportional(self):
        # Two claims, one grounded, one not
        generated = "Revenue grew 42% and the Wall Street Journal reported losses."
        source = "Revenue grew 42%."
        score, unsupported = check_faithfulness(generated, [source])
        assert 0 < score < 100
