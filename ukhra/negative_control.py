"""Run the ageing classifier over UKHRA as a large negative control.

UKHRA 2022 is 18,023 UK *health* research awards. Almost none of them are
ageing research, and none were selected by an ageing keyword search, so the
corpus is close to a null sample for our purposes. That makes it useful in a
way the atlas cannot be: every confident ageing label the classifier produces
here is a candidate relevance-gate leak, and no new human labels are needed to
go looking.

It also reads the funding-gap ratio on a corpus with no ageing focus, which
gives the reported per-region ratios a floor to be read against.

This complements ukhra/benchmark.py rather than repeating it. benchmark.py
scores a cancer screen against human cancer coding, which is a correctness
measurement. This has no ground truth for ageing (HRCS has no ageing category)
and makes no accuracy claim: it surfaces suspicious labels for a human to look
at, and reports which keywords drove them.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

from ukhra.benchmark import UkhraAward, load_ukhra

NUMERATOR_LABELS = ("fundamental_aging", "intervention")
SUBSTANTIVE_LABELS = NUMERATOR_LABELS + ("age_related_disease", "care", "social_population_aging")

# HRCS Health Categories that carry no plausible ageing framing on their own.
# A confident ageing label on one of these is worth a human look. Deliberately
# conservative: Cancer, Neurological, Cardiovascular and Metabolic are all
# genuinely age-related, so they are NOT listed here -- this is a list of
# likely leaks, not a list of errors.
NON_AGEING_HEALTH_CATEGORIES = (
    "Infection",
    "Reproductive Health and Childbirth",
    "Oral and Gastrointestinal",
    "Renal and Urogenital",
    "Congenital Disorders",
)


def ratio_classifier() -> Callable[[str, str], dict]:
    """Default: the repo's own ageing classifier, ratio/classify.py."""
    from ratio.classify import classify, load_ruleset

    ruleset = load_ruleset()
    return lambda title, abstract: classify(title, abstract, ruleset)


def run(path: Path, classify_fn: Callable[[str, str], dict] = None,
        examples_per_category: int = 4) -> dict:
    classify_fn = classify_fn or ratio_classifier()
    awards = [a for a in load_ukhra(path)
              if a.coding_type == "Manual" and not a.is_text_redacted]

    labels: Counter = Counter()
    keyword_drivers: Dict[str, Counter] = {}
    numerator_funding = denominator_funding = 0.0
    suspicious: List[dict] = []

    for award in awards:
        result = classify_fn(award.title, award.abstract)
        label = result.get("label", "")
        labels[label] += 1
        if label in SUBSTANTIVE_LABELS:
            denominator_funding += award.value_2022_gbp
        if label in NUMERATOR_LABELS:
            numerator_funding += award.value_2022_gbp
        for term in result.get("matched_keywords", {}).get(label, []):
            keyword_drivers.setdefault(label, Counter())[term] += 1
        primary_hc = award.health_categories[0] if award.health_categories else ""
        if label in NUMERATOR_LABELS and primary_hc in NON_AGEING_HEALTH_CATEGORIES:
            suspicious.append({
                "award_id": award.award_id,
                "human_health_category": primary_hc,
                "our_label": label,
                "title": award.title[:140],
                "matched_keywords": result.get("matched_keywords", {}),
                "value_2022_gbp": award.value_2022_gbp,
            })

    n = len(awards)
    return {
        "corpus": {
            "dataset": "UKHRA 2022, manually coded and non-redacted rows",
            "awards_scored": n,
            "note": ("A general UK health research corpus, not selected by any ageing "
                      "keyword search. Treat confident ageing labels here as candidate "
                      "relevance-gate leaks, not as measured errors."),
        },
        "label_distribution": dict(labels.most_common()),
        "numerator_share_of_awards": (
            sum(labels[l] for l in NUMERATOR_LABELS) / n if n else None),
        "funding_gap_ratio_on_ukhra": (
            numerator_funding / denominator_funding if denominator_funding else None),
        "funding_gap_ratio_note": (
            "The ratio the instrument reads on a corpus with no ageing focus. Not a "
            "target and not an error rate: a reference point for the per-region ratios "
            "reported elsewhere in the repo."),
        "keyword_drivers": {
            label: dict(counter.most_common(15))
            for label, counter in sorted(keyword_drivers.items())
        },
        "suspicious_numerator_labels": {
            "count": len(suspicious),
            "criterion": (f"label in {NUMERATOR_LABELS} while the human primary Health "
                           f"Category is one of {NON_AGEING_HEALTH_CATEGORIES}"),
            "examples": suspicious[:examples_per_category * len(NON_AGEING_HEALTH_CATEGORIES)],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--xlsx", type=Path, required=True,
                    help="path to UKHRA2022_HRCS_public_dataset_v1-2_30Jan2024.xlsx (not committed)")
    ap.add_argument("--out", type=Path, default=None, help="write the report as JSON")
    args = ap.parse_args()
    report = run(args.xlsx)
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
