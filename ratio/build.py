#!/usr/bin/env python3
"""Build the funding-gap ratio artifacts from the atlas corpus.

Runs ratio/classify.py over all 2,944 atlas records (live tree at
data/Track3_C2/output/, or git-show recovery from commit 2e59b27), then
aggregates per region (SE, EU, US) and per funder:

  ratio = EUR(fundamental_aging + intervention)
          / EUR(all five substantive categories)

not_relevant records are excluded from the ratio and counted separately;
ambiguous records are excluded from both numerator and denominator and
reported beside the ratio as an explicit honesty band
(ambiguous_share = ambiguous EUR / (classified + ambiguous EUR)).
social_population_aging counts only in the denominator, per KEYWORDS.md.

Regions follow the corpus source, which is the funding jurisdiction:
swecris -> SE, cordis -> EU (funder is the European Commission; the country
column holds the coordinator's member state), nih_reporter -> US.

Outputs (committed, so the page needs no pipeline run):
  ratio/output/labels.jsonl     one line per record: label + provenance
  ratio/output/aggregates.json  regions, funders, totals, method metadata

Usage: python3 ratio/build.py
Python 3 stdlib only; no model calls, no network.
"""

import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classify as clf

OUT_DIR = Path(__file__).resolve().parent / "output"
REGION_BY_SOURCE = {"swecris": "SE", "cordis": "EU", "reporter": "US"}
REGION_NAMES = {"SE": "Sweden", "EU": "European Union", "US": "United States"}


def blank_bucket() -> dict:
    return {
        "counts": collections.Counter(),
        "eur": collections.Counter(),
        "eur_missing": 0,
    }


def add(bucket: dict, label: str, eur: "float | None") -> None:
    bucket["counts"][label] += 1
    if eur is None:
        bucket["eur_missing"] += 1
    else:
        bucket["eur"][label] += eur


def parse_eur(record: dict) -> "float | None":
    """amount_eur as float, None when absent; loud failure on malformed or
    negative values rather than silently skewing the sums."""
    raw = record["amount_eur"]
    if not raw:
        return None
    try:
        eur = float(raw)
    except ValueError:
        sys.exit(f"{record['record_id']}: unparsable amount_eur {raw!r}")
    if eur < 0:
        sys.exit(f"{record['record_id']}: negative amount_eur {raw!r}")
    return eur


def region_of(record: dict) -> str:
    try:
        return REGION_BY_SOURCE[record["source"]]
    except KeyError:
        sys.exit(f"{record['record_id']}: unknown source "
                 f"{record['source']!r} (expected one of "
                 f"{sorted(REGION_BY_SOURCE)})")


def finish(bucket: dict) -> dict:
    counts = bucket["counts"]
    eur = {k: round(v, 2) for k, v in bucket["eur"].items()}
    cat_eur = {c: eur.get(c, 0.0) for c in clf.CATEGORIES}
    denominator = sum(cat_eur.values())
    numerator = sum(cat_eur[c] for c in clf.NUMERATOR)
    ambiguous_eur = eur.get("ambiguous", 0.0)
    return {
        "records": sum(counts.values()),
        "counts": dict(counts),
        "eur": eur,
        "numerator_eur": round(numerator, 2),
        "denominator_eur": round(denominator, 2),
        "ratio": round(numerator / denominator, 4) if denominator else None,
        "ambiguous_share": round(
            ambiguous_eur / (denominator + ambiguous_eur), 4)
            if denominator + ambiguous_eur else None,
        "eur_missing_records": bucket["eur_missing"],
    }


def self_test() -> int:
    """Unit checks for the aggregation math; no corpus needed."""
    b = blank_bucket()
    add(b, "fundamental_aging", 20.0)
    add(b, "intervention", 10.0)
    add(b, "social_population_aging", 70.0)   # denominator-only
    add(b, "ambiguous", 100.0)                # honesty band, neither side
    add(b, "not_relevant", 300.0)             # excluded entirely
    add(b, "care", None)                      # missing EUR: counted, not summed
    f = finish(b)
    empty = finish(blank_bucket())
    nr_only = blank_bucket()
    add(nr_only, "not_relevant", 5.0)
    checks = [
        (f["records"] == 6, "records counts every add"),
        (f["numerator_eur"] == 30.0, "numerator = fundamental + intervention"),
        (f["denominator_eur"] == 100.0, "denominator = five categories"),
        (f["ratio"] == 0.3, "ratio math"),
        (f["ambiguous_share"] == 0.5, "ambiguous share beside the ratio"),
        (f["eur_missing_records"] == 1, "missing EUR counted separately"),
        (f["eur"].get("care", 0.0) == 0.0, "missing EUR not summed"),
        (empty["ratio"] is None, "empty bucket has no ratio"),
        (empty["ambiguous_share"] is None, "empty bucket has no share"),
        (finish(nr_only)["ratio"] is None, "not_relevant-only has no ratio"),
        (region_of({"record_id": "x", "source": "swecris"}) == "SE",
         "region mapping"),
        (parse_eur({"record_id": "x", "amount_eur": ""}) is None,
         "blank EUR is None"),
        (parse_eur({"record_id": "x", "amount_eur": "12.5"}) == 12.5,
         "EUR parses"),
    ]
    failed = [name for ok, name in checks if not ok]
    for name in failed:
        print(f"self-test FAILED: {name}")
    print(f"self-test: {len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true",
                    help="run aggregation unit checks and exit")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    ruleset = clf.load_ruleset()
    rows = clf.load_corpus()

    OUT_DIR.mkdir(exist_ok=True)
    regions = collections.defaultdict(blank_bucket)
    funders = collections.defaultdict(blank_bucket)
    total = blank_bucket()

    with open(OUT_DIR / "labels.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            out = clf.classify(r["title"], r["llm_quote"], ruleset)
            region = region_of(r)
            funder = r["funder"].strip()
            eur = parse_eur(r)
            add(regions[region], out["label"], eur)
            add(funders[(region, funder)], out["label"], eur)
            add(total, out["label"], eur)
            fh.write(json.dumps({
                "record_id": r["record_id"],
                "source": r["source"],
                "region": region,
                "year": r["year"],
                "funder": funder,
                "amount_eur": eur,
                "title": r["title"],
                "url": r["url"],
                "label": out["label"],
                "matched_keywords": out["matched_keywords"],
                "anchor_terms": out["anchor_terms"],
                "reason": out["reason"],
                "confidence": out["confidence"],
                "llm_category": r["llm_category"],
            }, ensure_ascii=False) + "\n")

    git_head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True,
        text=True, cwd=clf.REPO_ROOT).stdout.strip() or "unknown"

    aggregates = {
        "method": {
            "description": "Deterministic rule classifier over the Aging "
                           "Funding Atlas; see ratio/README.md.",
            "corpus": f"2,944 grant records from commit {clf.ATLAS_COMMIT} "
                      "(SweCRIS 855, CORDIS 558, NIH RePORTER 1,531)",
            "lexicon": "classifier/keywords.json",
            "numerator": sorted(clf.NUMERATOR),
            "denominator": list(clf.CATEGORIES),
            "tie_margin": clf.TIE_MARGIN,
            "built_at_commit": git_head,
            "caveats": [
                "Labels are rule-based and not yet human-verified; the "
                "30-record human benchmark is pending.",
                "The corpus is an ageing-filtered sample per funder, not a "
                "census of any funding body's budget.",
                "Ambiguous grants are excluded from the ratio and shown as "
                "an explicit share beside it.",
            ],
        },
        "total": finish(total),
        "regions": {
            reg: {"name": REGION_NAMES[reg], **finish(bucket)}
            for reg, bucket in sorted(regions.items())
        },
        "funders": [
            {"region": reg, "funder": funder, **finish(bucket)}
            for (reg, funder), bucket in sorted(
                funders.items(),
                key=lambda kv: -sum(kv[1]["eur"].values()))
        ],
    }
    (OUT_DIR / "aggregates.json").write_text(
        json.dumps(aggregates, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print(f"wrote {OUT_DIR / 'labels.jsonl'} ({len(rows)} records)")
    print(f"wrote {OUT_DIR / 'aggregates.json'}")
    for reg, data in aggregates["regions"].items():
        print(f"  {reg}: ratio={data['ratio']}  "
              f"ambiguous_share={data['ambiguous_share']}  "
              f"records={data['records']}")
    print(f"  total: ratio={aggregates['total']['ratio']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
