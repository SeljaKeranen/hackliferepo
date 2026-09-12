#!/usr/bin/env python3
"""Deterministic rule classifier for the funding-gap ratio.

Implements the classification rubric of classifier/KEYWORDS.md exactly, using
the validated lexicon in classifier/keywords.json:

  step 0  relevance gate: exclusion markers and NONBIO-style engineering /
          agriculture vocabulary route obvious off-topic records to
          not_relevant; a record with no ageing anchor and no category
          keyword never gets a substantive category either.
  step 1  keyword voting: every kept (non-trap) lexicon keyword that matches
          the record votes for its category with its measured precision as
          the weight ("precision as priors" in KEYWORDS.md). Keywords with
          requires_ageing_anchor - the whole social_population_aging
          category and the flagged care terms - count only when an ageing
          anchor (a meta.broad_net term) is also present.
  step 2  mechanism-versus-intervention rubric rule: an intervention label
          needs explicit developing/testing language; a grant studying an
          intervention's mechanism goes to fundamental_aging.
  step 3  ambiguity: no keyword evidence, or a winning margin below
          TIE_MARGIN, yields ambiguous - never a forced category.

Matching semantics are imported from classifier/validate_keywords.py (the
same compile_term the lexicon stats were computed with), over the same text:
lowercased title + llm_quote.

No model calls, no network: python3 stdlib only. This is the reproducible
rules leg of the pipeline; the reason strings and the NONBIO idea align with
Jan's funding/classify.py on the codex/ageing-funding-gap branch (see
ratio/README.md for the exact citations).

Usage:
    python3 ratio/classify.py            # classify the atlas, print summary
    python3 ratio/classify.py --self-test

Library use: load_ruleset() once, then classify(title, quote, ruleset).
"""

import argparse
import collections
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KEYWORDS_JSON = REPO_ROOT / "classifier" / "keywords.json"

# Reuse the exact matching semantics the lexicon was validated with.
_spec = importlib.util.spec_from_file_location(
    "validate_keywords", REPO_ROOT / "classifier" / "validate_keywords.py")
_vk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vk)
compile_term = _vk.compile_term

NUMERATOR = ("fundamental_aging", "intervention")
CATEGORIES = ("fundamental_aging", "intervention", "age_related_disease",
              "care", "social_population_aging")

# A voted label needs the winner to beat the runner-up by this much summed
# precision, otherwise the record is ambiguous (or, at the
# fundamental_aging/intervention boundary, decided by the rubric rule).
# 0.3 is half the lexicon's 0.6 precision floor: one clear extra keyword
# always clears it, two near-equal keyword sets never do.
TIE_MARGIN = 0.3

# NONBIO-style exclusions for the step-0 relevance gate. The first three are
# meta.exclusion_markers from the lexicon (95-100% of their corpus hits are
# the engineering pool); the rest extend them with Jan's NONBIO vocabulary
# (funding/classify.py, codex/ageing-funding-gap) plus the corpus trap
# classes KEYWORDS.md names: electrical-component ageing ("accelerated
# ageing and voltage disturbances") and CORDIS animal-breeding "productive
# longevity". They fire only when the record matches no lexicon keyword and
# shows no biomedical context (BIO_CONTEXT below), so an engineering word in
# a genuinely biomedical grant never excludes it.
NONBIO_TERMS = [
    # lexicon meta.exclusion_markers
    "battery", "li-ion", "aging infrastructure",
    # Jan's NONBIO list
    "batteries", "galax*", "stellar", "steel", "concrete", "asphalt",
    "photovoltaic", "polymer*", "semiconductor*", "superconduct*",
    # corpus trap classes from KEYWORDS.md
    "voltage", "electrolyte*", "corrosion", "accelerated aging test*",
    "accelerated ageing", "livestock", "breeding", "dairy",
]

# Jan's biomedical-context guard, extended with a few unambiguous tokens.
BIO_CONTEXT = re.compile(
    r"\b(cell|cells|cellular|human|patient|patients|mouse|mice|clinical|"
    r"cohort|gene|genes|protein|proteins)\b")

# KEYWORDS.md: a classification anchor is "a meta.broad_net term or an
# explicit older-adults reference". The broad net carries "older adults" and
# "elderly"; this regex supplies the other explicit older-adults surface
# forms (aligned with the AGE net in Jan's funding/classify.py).
OLDER_REF = re.compile(
    r"\b(older (?:adults?|people|persons?|patients?|workers?|men|women|"
    r"individuals?|population)|oldest[- ]old|old age|later life|"
    r"aged care|care of the aged|centenarian\w*|nonagenarian\w*|"
    r"octogenarian\w*|supercentenarian\w*)\b")

# Developing/testing cues for the mechanism-versus-intervention rubric rule:
# an intervention grant "funds developing or testing an intervention aimed at
# slowing or reversing ageing" (KEYWORDS.md). Mechanistic studies lack these
# or pair them with mechanism language, and lose the label.
DEV_CUES = re.compile(
    r"\b(develop\w*|test\w*|trial\w*|treat\w*|therap\w*|clinical|drug\w*|"
    r"dose|dosing|supplement\w*|(?:slow|slows|slowing|revers\w*|delay\w*) "
    r"(?:\w+ )?ag(?:e|i)ng)\b")


def load_ruleset(keywords_path=KEYWORDS_JSON):
    """Compile the lexicon into matchable rules. Call once, reuse."""
    lex = json.loads(Path(keywords_path).read_text(encoding="utf-8"))
    anchors = [(e["term"], compile_term(e["term"]))
               for lang in ("en", "sv")
               for e in lex["meta"]["broad_net"][lang]]
    keywords = {}
    for cat, block in lex["categories"].items():
        cat_anchor = block.get("requires_ageing_anchor", False)
        entries = []
        for lang in ("en", "sv"):
            for e in block.get(lang, []):
                entries.append({
                    "term": e["term"],
                    "precision": e["precision"],
                    "requires_anchor": bool(
                        cat_anchor or e.get("requires_ageing_anchor")),
                    "pattern": compile_term(e["term"]),
                })
        keywords[cat] = entries
    nonbio = [(t, compile_term(t)) for t in NONBIO_TERMS]
    return {"anchors": anchors, "keywords": keywords, "nonbio": nonbio}


def classify(title, quote, ruleset):
    """Classify one grant record from its title + supporting quote.

    Returns a dict with label, matched keywords per category, a one-line
    reason, and a confidence proxy (the winning precision margin; null for
    gate outcomes, which are not produced by voting).
    """
    text = ((title or "") + " " + (quote or "")).lower()
    anchor_terms = [t for t, p in ruleset["anchors"] if p.search(text)]
    older_ref = OLDER_REF.search(text)
    if older_ref and older_ref.group(0) not in anchor_terms:
        anchor_terms.append(older_ref.group(0))
    has_anchor = bool(anchor_terms)

    matched = {}
    for cat, entries in ruleset["keywords"].items():
        hits = [e for e in entries if e["pattern"].search(text)
                and (has_anchor or not e["requires_anchor"])]
        if hits:
            matched[cat] = hits
    matched_terms = {cat: [e["term"] for e in hits]
                     for cat, hits in matched.items()}

    def result(label, reason, confidence=None):
        return {
            "label": label,
            "matched_keywords": matched_terms,
            "anchor_terms": anchor_terms,
            "reason": reason,
            "confidence": confidence,
        }

    # step 0: relevance gate
    if not matched:
        nonbio_hits = [t for t, p in ruleset["nonbio"] if p.search(text)]
        if nonbio_hits and not BIO_CONTEXT.search(text):
            return result(
                "not_relevant",
                "The text concerns materials, engineering or agriculture "
                f"rather than human ageing (matched: {', '.join(nonbio_hits)}).")
        if not has_anchor:
            return result(
                "not_relevant",
                "No ageing anchor and no lexicon keyword appears in the "
                "available text, so ageing relevance is not established.")
        return result(
            "ambiguous",
            "An ageing anchor is present but no category keyword matches, "
            "so the text does not support any substantive category.")

    # step 1: precision-weighted voting
    scores = {cat: round(sum(e["precision"] for e in hits), 3)
              for cat, hits in matched.items()}
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    top_cat, top = ranked[0]
    second_cat, second = ranked[1] if len(ranked) > 1 else (None, 0.0)
    margin = round(top - second, 3)

    # step 2: mechanism-versus-intervention rubric rule
    contested = {top_cat, second_cat} == {"fundamental_aging", "intervention"}
    if (top_cat == "intervention" or (contested and margin < TIE_MARGIN)):
        if top_cat == "intervention" or second_cat == "intervention":
            if DEV_CUES.search(text):
                return result(
                    "intervention",
                    "The text describes developing or testing an intervention "
                    "against ageing (matched: "
                    f"{', '.join(matched_terms.get('intervention', []))}).",
                    margin)
            if "fundamental_aging" in matched:
                return result(
                    "fundamental_aging",
                    "Intervention vocabulary appears without developing/"
                    "testing language, so the rubric's mechanism rule assigns "
                    "the study of ageing biology (matched: "
                    f"{', '.join(matched_terms['fundamental_aging'])}).",
                    margin)
            return result(
                "ambiguous",
                "Intervention vocabulary appears without developing/testing "
                "language or mechanism evidence, so no rule is confident.",
                margin)

    # step 3: ambiguity floor for every other contested boundary
    if second_cat is not None and margin < TIE_MARGIN:
        return result(
            "ambiguous",
            f"Keyword evidence for {top_cat} ({top}) and {second_cat} "
            f"({second}) is too close to call (margin {margin} < "
            f"{TIE_MARGIN}).",
            margin)

    return result(
        top_cat,
        f"Lexicon keywords for {top_cat} decide the record (matched: "
        f"{', '.join(matched_terms[top_cat])}).",
        margin)


def load_corpus(data_dir=None):
    """Load the 2,944-record atlas via the validator's loader (live tree,
    or git-show recovery from commit 2e59b27 if the tree is gone), keeping
    the funding fields the ratio needs."""
    import csv
    import tempfile

    live = REPO_ROOT / _vk.ATLAS_PREFIX
    if data_dir is not None:
        src = Path(data_dir)
    elif all((live / n).is_file() for n in _vk.ATLAS_FILES):
        src = live
    else:
        with tempfile.TemporaryDirectory() as tmp:
            _vk.recover_atlas(Path(tmp))
            return load_corpus(tmp)
    rows = []
    for name in _vk.ATLAS_FILES:
        with open(src / name, encoding="utf-8-sig", newline="") as fh:
            rows.extend(csv.DictReader(fh))
    if len(rows) != _vk.EXPECTED_RECORDS:
        sys.exit(f"expected {_vk.EXPECTED_RECORDS} records, got {len(rows)}")
    return rows


def self_test():
    ruleset = load_ruleset()
    # Worked examples from classifier/KEYWORDS.md, verbatim corpus text.
    cases = [
        # relevance gate: battery ageing
        ("Separating the influence of temperature and current swing on the "
         "ageing of a Li-Ion battery", "", "not_relevant"),
        # relevance gate: electrical-component ageing
        ("Accelerated ageing and voltage disturbances - need, possibilities "
         "and limitations",
         "A study will be conducted on the need, possibilities and "
         "limitations of including voltage disturbances in accelerated "
         "aging tests.", "not_relevant"),
        # relevance gate: livestock "productive longevity"
        ("GEroNIMO: Genome and Epigenome eNabled breedIng in MOnogastrics",
         "improve breeding for productive longevity in livestock",
         "not_relevant"),
        # on-topic but unplaceable -> ambiguous, not not_relevant
        ("International journal of ageing and later life", "", "ambiguous"),
        # mechanism rule: intervention named, mechanism studied
        ("Exploiting superlongevous model mammals to explore new links "
         "between protein and organelle homeostasis and lifespan", "",
         "fundamental_aging"),
        # explicit intervention development
        ("Unlocking Cognitive Health: How Metformin Slows Brain Aging "
         "Through Precision Medicine",
         "we will test whether metformin treatment slows brain aging",
         "intervention"),
        # plain single-category calls
        ("Cellular senescence in tissue aging",
         "we study cellular senescence and the aging process",
         "fundamental_aging"),
        ("Tau pathology in Alzheimer's disease",
         "tau and amyloid in alzheimer disease progression",
         "age_related_disease"),
        ("Improving elderly care work", "nursing homes and elderly care",
         "care"),
        # anchored social keyword with anchor present
        ("Retirement timing and ageing societies",
         "how retirement shapes life in an ageing society",
         "social_population_aging"),
        # the same social keyword with no ageing anchor never fires
        ("Retirement savings behaviour", "pension fund portfolio choice",
         "not_relevant"),
    ]
    failed = 0
    for title, quote, want in cases:
        got = classify(title, quote, ruleset)
        ok = got["label"] == want
        failed += not ok
        if not ok:
            print(f"self-test FAILED: {title[:60]!r}: want {want}, "
                  f"got {got['label']} ({got['reason']})")
    print(f"self-test: {len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", type=Path, help="directory with the three "
                    "atlas CSVs (default: live tree, else git recovery)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    ruleset = load_ruleset()
    rows = load_corpus(args.data_dir)
    labels = collections.Counter()
    agree = total = 0
    for r in rows:
        out = classify(r["title"], r["llm_quote"], ruleset)
        labels[out["label"]] += 1
        # agreement is context only: llm labels predate social_population_
        # aging and the not_relevant/ambiguous split, and are unverified
        if r["llm_category"] in CATEGORIES:
            total += 1
            agree += out["label"] == r["llm_category"]
    print("label distribution:")
    for label, n in labels.most_common():
        print(f"  {label:24s} {n:5d}")
    print(f"agreement with llm_category on its four substantive labels: "
          f"{agree}/{total} = {agree / total:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
