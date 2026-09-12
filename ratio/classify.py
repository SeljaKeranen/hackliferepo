#!/usr/bin/env python3
"""Deterministic rule classifier for the funding-gap ratio.

Implements the classification rubric of classifier/KEYWORDS.md exactly, using
the validated lexicon in classifier/keywords.json:

  step 0  relevance gate: exclusion markers and NONBIO-style engineering /
          agriculture vocabulary route obvious off-topic records to
          not_relevant; a record with no ageing anchor and no category
          keyword never gets a substantive category either. A plant /
          agriculture / ecology arm (PLANTECO below) fires even when a
          lexicon keyword matched, because senescence, lifespan and
          longevity are everyday botany, forestry, ecology and
          animal-breeding vocabulary - unless a human or biomedical-model
          marker co-occurs (HUMAN_BIOMED below).
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
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KEYWORDS_JSON = REPO_ROOT / "classifier" / "keywords.json"

# Reuse the exact matching semantics the lexicon was validated with (same
# import style as eval/test_server.py and the rest of the repo).
sys.path.insert(0, str(REPO_ROOT / "classifier"))
import validate_keywords as _vk  # noqa: E402

compile_term = _vk.compile_term
ATLAS_COMMIT = _vk.ATLAS_COMMIT  # re-exported for build.py

NUMERATOR = ("fundamental_aging", "intervention")
# Single source of truth for the category list is the validator (which in
# turn is checked against classifier/keywords.json by load_ruleset below).
CATEGORIES = tuple(_vk.CATEGORIES)

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

# Plant / agriculture / ecology contexts in which senescence, lifespan and
# longevity are everyday non-ageing vocabulary (leaf senescence, productive
# longevity in livestock, population ecology). Unlike NONBIO, this arm must
# fire even when a lexicon keyword matched - the tree-physiology grant
# "How do trees survive the winter?" (swecris:2021-05062_VR) matches
# senescen* on "leaf senescence" and got fundamental_aging. Terms are
# compile_term patterns like the lexicon's own.
PLANTECO_TERMS = [
    "leaf", "leaves", "foliage", "plant", "plants", "seedling*",
    "tree", "trees", "forest*", "forestry", "deciduous", "conifer*",
    "crop", "crops", "agricultur*", "agronom*", "horticultur*",
    "arabidopsis", "wheat", "maize", "barley",
    "botany", "botanic*", "photosynthe*", "pollinat*",
    "livestock", "cattle", "dairy", "poultry", "herd", "breeding",
    "aquaculture", "fisheries",
    "grassland*", "meadow*", "soil", "ecosystem*", "ecolog*", "wildlife",
]

# Guard for the PLANTECO arm: a record with any human or biomedical-model
# marker is never excluded by plant/ecology vocabulary (a plant-derived
# compound tested in patients, a socio-ecological study of older adults).
# BIO_CONTEXT is too weak here - plants have cells, genes and proteins - so
# this list is human subjects, clinical settings, and the established
# animal models of ageing biology. OLDER_REF is checked alongside it.
HUMAN_BIOMED = re.compile(
    r"\b(humans?|patients?|clinical|cohorts?|participants?|volunteers?|"
    r"mouse|mice|murine|rats?|primates?|monkeys?|elderly|hospital\w*|"
    r"nursing|dementia|alzheimer\w*|geriatric\w*|"
    r"healthy ag(?:e)?ing|active ag(?:e)?ing|diet\w*|nutrition\w*|"
    r"supplement\w*|"
    r"drosophila|c\. elegans|elegans|killifish|zebrafish|yeast)\b")

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
    r"(?:\w+ )?ag(?:e)?ing)\b")

# Mechanism-study cues: "a grant studying an intervention's mechanism - how
# it works, what pathways it engages, what it reveals about ageing biology -
# is fundamental_aging, no matter how prominently the title names the
# intervention" (KEYWORDS.md). Checked before DEV_CUES, so a mechanistic
# study that also uses testing language stays fundamental_aging.
MECH_CUES = re.compile(
    r"\b(mechanis\w*|pathway\w*|biolog\w*|homeostasis|mode of action|"
    r"drug action)\b")


def load_ruleset(keywords_path=KEYWORDS_JSON) -> dict:
    """Compile the lexicon into matchable rules. Call once, reuse."""
    lex = json.loads(Path(keywords_path).read_text(encoding="utf-8"))
    if set(lex["categories"]) != set(CATEGORIES):
        sys.exit(f"category drift: lexicon has {sorted(lex['categories'])}, "
                 f"this pipeline aggregates {sorted(CATEGORIES)} - update "
                 "validate_keywords.CATEGORIES and rerun ratio/build.py")
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
    planteco = [(t, compile_term(t)) for t in PLANTECO_TERMS]
    return {"anchors": anchors, "keywords": keywords, "nonbio": nonbio,
            "planteco": planteco}


def classify(title: str, quote: str, ruleset: dict) -> dict:
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

    # step 0: relevance gate. The plant/agriculture/ecology arm runs first
    # and fires even when a lexicon keyword matched: senescence, lifespan
    # and longevity are everyday vocabulary in those fields, so the match
    # itself is what needs discounting. A human or biomedical-model marker
    # (or an explicit older-adults reference) always blocks the exclusion.
    planteco_hits = [t for t, p in ruleset["planteco"] if p.search(text)]
    if planteco_hits and not HUMAN_BIOMED.search(text) and not older_ref:
        return result(
            "not_relevant",
            "The ageing vocabulary appears in a plant, agriculture or "
            "ecology context with no human or biomedical-model marker "
            f"(matched: {', '.join(planteco_hits)}).")

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

    # step 2: mechanism-versus-intervention rubric rule. It decides ONLY the
    # fundamental_aging/intervention boundary - entered when those two are
    # the top-two contenders, or when intervention stands alone. A contest
    # between intervention and any OTHER category is left to the step-3
    # ambiguity floor (near-tie) or to the vote (decisive margin).
    contested = {top_cat, second_cat} == {"fundamental_aging", "intervention"}
    fa_boundary = contested or (top_cat == "intervention"
                                and second_cat is None)
    if fa_boundary and (top_cat == "intervention" or margin < TIE_MARGIN):
        mech = MECH_CUES.search(text)
        if mech:
            return result(
                "fundamental_aging",
                "Intervention vocabulary appears in a mechanism study, which "
                "the rubric assigns to ageing biology (mechanism cue: "
                f"{mech.group(0)}).",
                margin)
        if DEV_CUES.search(text):
            return result(
                "intervention",
                "The text describes developing or testing an intervention "
                "against ageing (matched: "
                f"{', '.join(matched_terms.get('intervention', []))}).",
                margin)
        if contested:
            return result(
                "fundamental_aging",
                "Intervention vocabulary appears without developing/testing "
                "language, so the rubric's mechanism rule assigns the study "
                "of ageing biology.",
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


# the atlas columns this pipeline consumes beyond the validator's own
# REQUIRED_COLUMNS (which cover record_id/source/llm_category/title/llm_quote)
RATIO_COLUMNS = {"funder", "amount_eur", "year", "url"}


def load_corpus(data_dir=None) -> list:
    """Load the 2,944-record atlas via the validator's constants (live tree,
    or git-show recovery from commit 2e59b27 if the tree is gone), validating
    the extra funding columns the ratio needs."""
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
    needed = _vk.REQUIRED_COLUMNS | RATIO_COLUMNS
    for name in _vk.ATLAS_FILES:
        with open(src / name, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            missing = needed - set(reader.fieldnames or [])
            if missing:
                sys.exit(f"{src / name}: missing column(s) {sorted(missing)}")
            rows.extend(reader)
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
        # contested FA/INT boundary, no cues -> mechanism rule wins
        ("Rapamycin and the lifespan of model organisms", "",
         "fundamental_aging"),
        # mechanism cue beats testing language (rubric's DR-as-probe rule)
        ("Testing how metformin affects senescence mechanisms", "",
         "fundamental_aging"),
        # intervention keyword alone, no cues, no mechanism evidence
        ("Rapamycin in aging", "", "ambiguous"),
        # intervention vs a non-fundamental category near-tie stays ambiguous
        # (real corpus record cordis:945153)
        ("Get strong to fight childhood cancer: an exercise intervention for "
         "children and adolescents undergoing anti-cancer treatment", "",
         "ambiguous"),
        # British spelling reaches the developing/testing cues
        ("Slowing ageing with metformin", "", "intervention"),
        # plant-senescence trap (real corpus record swecris:2021-05062_VR):
        # senescen* matches "leaf senescence" but the grant is tree
        # physiology, so the plant/ecology gate excludes it
        ("How do trees survive the winter?",
         "A main challenge for deciduous trees is to correctly time the "
         "onset of leaf senescence", "not_relevant"),
        # a plant term with human/biomedical context never excludes:
        # senescence here is human ageing biology despite "plant"
        ("Plant-derived senolytics against cellular senescence",
         "testing plant-derived compounds in aged mice", "fundamental_aging"),
        # ecology vocabulary with an explicit older-adults reference stays
        # on-topic (socio-ecological gerontology)
        ("A socio-ecological model of loneliness in older adults",
         "elderly care and community ecology of support", "care"),
        # a NONBIO term with biomedical context never excludes the record
        ("A battery of cognitive tests in aging patients", "", "ambiguous"),
        # a decisive intervention win over an unrelated category stands on
        # the vote; the rubric rule governs only the fundamental boundary
        ("Geroprotectors and senotherapies for residents of nursing homes",
         "", "intervention"),
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
