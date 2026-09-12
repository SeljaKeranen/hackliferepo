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
NUMERATOR = set(clf.NUMERATOR)


def blank_bucket():
    return {
        "counts": collections.Counter(),
        "eur": collections.Counter(),
        "eur_missing": 0,
    }


def add(bucket, label, eur):
    bucket["counts"][label] += 1
    if eur is None:
        bucket["eur_missing"] += 1
    else:
        bucket["eur"][label] += eur


def finish(bucket):
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


def main():
    ruleset = clf.load_ruleset()
    rows = clf.load_corpus()

    OUT_DIR.mkdir(exist_ok=True)
    regions = collections.defaultdict(blank_bucket)
    funders = collections.defaultdict(blank_bucket)
    total = blank_bucket()

    with open(OUT_DIR / "labels.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            out = clf.classify(r["title"], r["llm_quote"], ruleset)
            region = REGION_BY_SOURCE[r["source"]]
            funder = r["funder"].strip()
            eur = float(r["amount_eur"]) if r["amount_eur"] else None
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
            "corpus": f"2,944 grant records from commit {clf._vk.ATLAS_COMMIT} "
                      "(SweCRIS 855, CORDIS 558, NIH RePORTER 1,531)",
            "lexicon": "classifier/keywords.json",
            "numerator": sorted(NUMERATOR),
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
