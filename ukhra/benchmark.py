"""Score a classifier against human coders, using UKHRA 2022 as the key.

The problem this solves: our funding classifiers have never been checked
against anything. The UK Health Research Analysis is the one human-coded
funding corpus we can get at. Its 2022 public dataset holds 18,023 UK health
research awards, and each row carries the award's own title and abstract
alongside codes assigned by trained coders on two HRCS axes -- Health
Category (disease area) and Research Activity (what kind of work).

Text and human labels sitting on the same row is what makes it usable: a
classifier can be run on exactly the text a coder read, with no record
linkage to Gateway to Research and so no coverage-mismatch problem.

What it can and cannot check:

  CAN   cancer. "Cancer and Neoplasms" is an HRCS Health Category, so a
        cancer screen has a human-coded target to be scored against.
  CAN   prevention versus consequences, roughly. The eight Research
        Activity groups (1 Underpinning, 2 Aetiology, 3 Prevention,
        4 Detection and Diagnosis, 5 Treatment Development, 6 Treatment
        Evaluation, 7 Disease Management, 8 Health Services) give an
        empirical reference point for the axis our labelling round asks
        about.
  CANNOT ageing. HRCS has no ageing category. Nothing here validates ageing
        classification. The supported claim is narrower: a method that
        reproduces human coding where ground truth exists is more credible
        where it doesn't. That is not a measurement of ageing accuracy.

Ground-truth quality: only rows with CodingType == "Manual" count. 5,126 of
the 18,023 awards were coded by an algorithm (Dimensions), and scoring
against those would compare two classifiers and call it human validation.

The dataset is NOT committed (AGENTS.md: do not commit raw datasets):

    curl -sL -o /tmp/UKHRA2022.xlsx \\
      https://hrcsonline.net/wp-content/uploads/2024/01/UKHRA2022_HRCS_public_dataset_v1-2_30Jan2024.xlsx

Source: https://hrcsonline.net/reports/analysis-data/
Licence: Creative Commons. HRCS Online ask to be contacted about re-analysis
of the public datasets and require formal citation. Cite as UK Health
Research Analysis 2022 (UK Clinical Research Collaboration, 2023).
"""
from __future__ import annotations

import argparse
import importlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from ukhra import xlsx

AWARD_SHEET = "2022_Data_1Line"
CANCER_HEALTH_CATEGORY = "Cancer and Neoplasms"

# Some funders (notably MRC studentships) publish codes but withhold the
# text, leaving a literal placeholder where the abstract should be. Those
# rows are unscoreable: a classifier reading "Award abstract not available
# in public dataset" is being measured on the redaction, not on its own
# judgment. Excluded from scoring and counted, never silently dropped.
REDACTION_MARKERS = ("not available in public dataset",)

RA_GROUPS = {
    "1": "Underpinning", "2": "Aetiology", "3": "Prevention",
    "4": "Detection and Diagnosis", "5": "Treatment Development",
    "6": "Treatment Evaluation", "7": "Disease Management",
    "8": "Health Services",
}
# Alignment to the prevention-versus-consequences labelling axis. Groups 1
# and 2 are left unmapped on purpose: underpinning biology and aetiology sit
# upstream of the split, and they are the grants the taxonomy argues hardest
# about. Forcing them to one side would manufacture agreement.
PREVENTION_GROUPS = {"3"}
CONSEQUENCE_GROUPS = {"4", "5", "6", "7"}


@dataclass(frozen=True)
class UkhraAward:
    award_id: str
    funder: str
    title: str
    abstract: str
    value_2022_gbp: float
    health_categories: Sequence[str]
    ra_groups: Sequence[str]
    coding_type: str

    @property
    def text(self) -> str:
        return f"{self.title} {self.abstract}".strip()

    @property
    def is_text_redacted(self) -> bool:
        blob = self.text.lower()
        return not blob or any(m in blob for m in REDACTION_MARKERS)

    @property
    def is_cancer(self) -> bool:
        return CANCER_HEALTH_CATEGORY in self.health_categories

    @property
    def is_primary_cancer(self) -> bool:
        return bool(self.health_categories) and self.health_categories[0] == CANCER_HEALTH_CATEGORY


def load_ukhra(path: Path) -> List[UkhraAward]:
    z = zipfile.ZipFile(path)
    sheets = xlsx.sheet_map(z)
    if AWARD_SHEET not in sheets:
        raise SystemExit(f"{path} has no '{AWARD_SHEET}' sheet (found: {sorted(sheets)})")
    strings = xlsx.shared_strings(z)
    it = xlsx.rows(z, sheets[AWARD_SHEET], strings)
    ix = {h: i for i, h in enumerate(next(it))}

    def cell(row, key):
        i = ix.get(key)
        return row[i] if i is not None and i < len(row) else ""

    awards = []
    for row in it:
        award_id = cell(row, "HRCS2022_ID")
        if not award_id:
            continue
        try:
            value = float(cell(row, "2022AnnualisedValue") or 0)
        except ValueError:
            value = 0.0
        awards.append(UkhraAward(
            award_id=award_id,
            funder=cell(row, "FundingOrganisation"),
            title=cell(row, "AwardTitle"),
            abstract=cell(row, "AwardAbstract"),
            value_2022_gbp=value,
            health_categories=[cell(row, f"HC_{i}").strip() for i in range(1, 6)
                                if cell(row, f"HC_{i}").strip()],
            ra_groups=[cell(row, f"RA_{i}").strip().split(".")[0] for i in range(1, 5)
                        if cell(row, f"RA_{i}").strip()],
            coding_type=cell(row, "CodingType"),
        ))
    return awards


@dataclass
class BinaryScore:
    tp: int
    fp: int
    fn: int
    tn: int
    funding_wrongly_included_gbp: float
    funding_missed_gbp: float

    @property
    def precision(self) -> Optional[float]:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else None

    @property
    def recall(self) -> Optional[float]:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else None

    @property
    def f1(self) -> Optional[float]:
        p, r = self.precision, self.recall
        return (2 * p * r / (p + r)) if p and r else None

    def as_dict(self) -> dict:
        return {"tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn,
                "precision": self.precision, "recall": self.recall, "f1": self.f1,
                "funding_wrongly_included_gbp": self.funding_wrongly_included_gbp,
                "funding_missed_gbp": self.funding_missed_gbp}


def score_cancer(awards: Sequence[UkhraAward], predict: Callable[[str], bool],
                 primary_only: bool = False) -> BinaryScore:
    """`predict` takes an award's title+abstract and returns True for
    cancer-relevant. Any classifier implementing that signature can be
    scored -- see --classifier."""
    tp = fp = fn = tn = 0
    wrongly_included = missed = 0.0
    for a in awards:
        predicted = predict(a.text)
        actual = a.is_primary_cancer if primary_only else a.is_cancer
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
            wrongly_included += a.value_2022_gbp
        elif not predicted and actual:
            fn += 1
            missed += a.value_2022_gbp
        else:
            tn += 1
    return BinaryScore(tp, fp, fn, tn, wrongly_included, missed)


def ra_group_profile(awards: Sequence[UkhraAward]) -> dict:
    """How UKHRA's own coders spread funding across the Research Activity
    groups: the empirical reference point for the prevention-versus-
    consequences labelling axis."""
    by_group: Dict[str, dict] = {}
    for a in awards:
        share = 1.0 / len(a.ra_groups) if a.ra_groups else 0.0
        for g in a.ra_groups:
            entry = by_group.setdefault(g, {"group": RA_GROUPS.get(g, g), "awards": 0,
                                              "apportioned_gbp": 0.0})
            entry["awards"] += 1
            entry["apportioned_gbp"] += a.value_2022_gbp * share
    prevention = sum(v["apportioned_gbp"] for k, v in by_group.items() if k in PREVENTION_GROUPS)
    consequences = sum(v["apportioned_gbp"] for k, v in by_group.items() if k in CONSEQUENCE_GROUPS)
    unmapped = sum(v["apportioned_gbp"] for k, v in by_group.items()
                   if k not in PREVENTION_GROUPS and k not in CONSEQUENCE_GROUPS)
    return {
        "by_group": {k: by_group[k] for k in sorted(by_group)},
        "prevention_gbp": prevention,
        "consequences_gbp": consequences,
        "unmapped_gbp": unmapped,
        "prevention_share_of_mapped": (prevention / (prevention + consequences)
                                        if (prevention + consequences) else None),
        "note": ("Groups 1 (Underpinning) and 2 (Aetiology) are left unmapped on "
                  "purpose: upstream biology sits on neither side of the "
                  "prevention/consequences split, and it is the territory an "
                  "ageing-biology grant occupies."),
    }


def load_predictor(spec: Optional[str]) -> Callable[[str], bool]:
    """Default is ukhra.cancer_terms. Pass module:function to score a
    different classifier, e.g. --classifier mypkg.mymod:is_cancer. The
    function takes text and returns something truthy for cancer-relevant."""
    if not spec:
        from ukhra.cancer_terms import looks_like_cancer
        return lambda text: looks_like_cancer(text)[0]
    module_name, _, func_name = spec.partition(":")
    if not func_name:
        raise SystemExit(f"--classifier needs module:function, got {spec!r}")
    func = getattr(importlib.import_module(module_name), func_name)
    return lambda text: bool(func(text))


def run(path: Path, classifier_spec: Optional[str] = None) -> dict:
    predict = load_predictor(classifier_spec)
    awards = load_ukhra(path)
    manual = [a for a in awards if a.coding_type == "Manual"]
    redacted = [a for a in manual if a.is_text_redacted]
    scoreable = [a for a in manual if not a.is_text_redacted]
    return {
        "source": {
            "dataset": "UK Health Research Analysis 2022 (UKCRC), HRCS public dataset v1-2",
            "url": "https://hrcsonline.net/reports/analysis-data/",
            "licence": ("Creative Commons; formal citation required, re-analysis should be "
                         "notified to HRCS Online"),
            "file": path.name,
        },
        "classifier": classifier_spec or "ukhra.cancer_terms:looks_like_cancer (keyword baseline)",
        "coverage": {
            "awards_total": len(awards),
            "awards_manually_coded": len(manual),
            "awards_algorithmically_coded": sum(1 for a in awards if a.coding_type == "Automated"),
            "awards_mixed_coding": sum(1 for a in awards if a.coding_type == "Mixed"),
            "manually_coded_text_redacted": len(redacted),
            "manually_coded_scoreable": len(scoreable),
            "total_value_2022_gbp": sum(a.value_2022_gbp for a in awards),
            "manual_value_2022_gbp": sum(a.value_2022_gbp for a in manual),
            "note": ("Only manually coded awards count as ground truth. Rows whose title "
                      "and abstract were withheld from the public release are excluded as "
                      "unscoreable."),
        },
        "cancer_any_health_category": score_cancer(scoreable, predict).as_dict(),
        "cancer_primary_health_category": score_cancer(scoreable, predict, primary_only=True).as_dict(),
        "cancer_including_redacted_rows": score_cancer(manual, predict).as_dict(),
        "research_activity_profile": ra_group_profile(scoreable),
        "limitations": [
            "HRCS has no ageing category: nothing here validates ageing classification.",
            "Scores a cancer screen, not the ageing classifier in ratio/classify.py.",
            "UKHRA is UK-only, 2022 spend, health research only: not a comparator for SweCRIS totals.",
            "Funding figures are GBP 2022 annualised values, not apportioned by Health Category share.",
            ("cancer_including_redacted_rows keeps the exclusion auditable: it scores the same "
             "classifier over rows whose text was withheld, where no classifier could succeed, "
             "and is the more pessimistic number."),
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--xlsx", type=Path, required=True,
                    help="path to UKHRA2022_HRCS_public_dataset_v1-2_30Jan2024.xlsx (not committed)")
    ap.add_argument("--classifier", default=None,
                    help="module:function to score instead of the keyword baseline")
    ap.add_argument("--out", type=Path, default=None, help="write the report as JSON")
    args = ap.parse_args()
    report = run(args.xlsx, args.classifier)
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
