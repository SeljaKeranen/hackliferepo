"""Cancer-relevance screen scored by the UKHRA benchmark.

Small and deliberately dumb: a whole-word keyword screen, which is what
makes it a useful baseline. The benchmark's job is to measure how far a
keyword screen gets against trained human coders, so that any smarter
classifier has a number to beat. Reuses compile_term from
classifier/validate_keywords.py rather than reimplementing the matching
rules (whole word/phrase, trailing '*' wildcard, whitespace runs).

Not derived from classifier/keywords.json: that file carries "cancer" only
as one age_related_disease keyword, which is a statement about ageing
relevance, not a cancer lexicon.
"""
from __future__ import annotations

from typing import List, Tuple

from classifier.validate_keywords import compile_term

CANCER_TERMS_EN: Tuple[str, ...] = (
    "cancer", "tumour*", "tumor*", "oncolog*", "carcinom*", "malignan*",
    "chemotherapy", "neoplas*", "metasta*", "leukemia", "leukaemia",
    "lymphoma", "sarcoma",
)
CANCER_TERMS_SV: Tuple[str, ...] = (
    "cancer", "tumör*", "onkolog*", "cellgift*", "malign*", "metastas*",
    "leukemi", "lymfom",
)

_PATTERNS = [(t, compile_term(t)) for t in CANCER_TERMS_EN + CANCER_TERMS_SV]


def looks_like_cancer(text: str) -> Tuple[bool, List[str]]:
    """Returns (is_cancer_relevant, matched_terms). One whole-word match is
    enough: this is a recall-oriented screen, not a final determination."""
    lowered = (text or "").lower()
    matched = [term for term, pattern in _PATTERNS if pattern.search(lowered)]
    return bool(matched), matched
