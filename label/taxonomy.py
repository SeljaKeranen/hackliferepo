"""The labelling taxonomy, as Andrew Steele settled it on 2026-09-13.

One question with three answers, plus two independent flags. This replaces
the earlier prevent/slow versus fighting-the-consequences split, which he
rejected as unbounded and hard to defend.

    "I think I'd split it into 'geroscience' (ie research into the causes of
    ageing, and attempts to intervene in it or develop treatments), then
    choose a specific disease (cancer is the most common referent) to
    compare to."

Two properties the rest of the package depends on:

  - CANCER IS INDEPENDENT. It is not a rival answer to the geroscience
    question, it is a separate tick, so a senolytic trialled on tumours is
    both. Andrew again: "You might find it's more successful to have one
    prompt ask 'is this ageing?' and another ask 'is this cancer?' rather
    than one prompt for both."
  - BORDERLINE IS NOT "COULDN'T TELL". Borderline means the text was clear
    and the *grant* reads both ways. Couldn't-tell means the *text* failed
    the reader. Collapsing them loses the distinction between a hard grant
    and a thin abstract, and those need opposite responses: adjudication
    versus better source text.
"""
from __future__ import annotations

from typing import Tuple

GEROSCIENCE_ANSWERS: Tuple[str, ...] = ("yes", "no", "borderline")

ANSWER_LABELS = {
    "yes": "Yes",
    "no": "No",
    "borderline": "Borderline",
}

ANSWER_HINTS = {
    "yes": "Ageing itself is what is studied or targeted",
    "no": "Age may be the context; ageing is not the subject",
    "borderline": "The text is clear; the grant reads both ways",
}

# Palette carried over from the design so the server, the two pages and any
# exported report agree on what each answer looks like.
ANSWER_COLOURS = {
    "yes": "#1B5E8C",
    "no": "#8A8A8F",
    "borderline": "#8B5A9E",
}
CANCER_COLOUR = "#2F7A4F"
FLAG_COLOUR = "#B4472F"

# How the classifier's own vocabulary (ratio/classify.py, five substantive
# categories plus ambiguous and not_relevant) maps onto this question, for
# the human-versus-classifier comparison in agreement.py. fundamental_aging
# and intervention are the numerator of the funding-gap ratio and are
# exactly "causes of ageing, and attempts to intervene in it" -- so they map
# to yes. Everything substantive but outside the numerator maps to no.
# ambiguous maps to borderline; nothing maps to the flag, which has no
# classifier equivalent.
CLASSIFIER_TO_ANSWER = {
    "fundamental_aging": "yes",
    "intervention": "yes",
    "age_related_disease": "no",
    "care": "no",
    "social_population_aging": "no",
    "ambiguous": "borderline",
    "not_relevant": "no",
}


def classifier_answer(label: str) -> str:
    """Projects a classifier label onto the geroscience question. Returns ""
    for an unknown label rather than guessing, so a vocabulary change shows
    up as missing data instead of a silently wrong comparison."""
    return CLASSIFIER_TO_ANSWER.get(label, "")
