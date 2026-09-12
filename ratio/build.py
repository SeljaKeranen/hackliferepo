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
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "data"))
import classify as clf
import census_common

OUT_DIR = Path(__file__).resolve().parent / "output"
CENSUS_SOURCES = ("swecris", "cordis", "reporter")
CENSUS_FILES = [census_common.DATA_DIR / f"census_{s}.jsonl.gz"
                for s in CENSUS_SOURCES]
# the files whose content determines the committed outputs; their combined
# hash is stamped into aggregates.json and enforced by --check, so stale
# outputs fail loudly instead of silently serving numbers from older rules
INPUT_FILES = [Path(__file__).resolve(),
               Path(clf.__file__).resolve(),
               clf.KEYWORDS_JSON] + CENSUS_FILES
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


def inputs_hash() -> str:
    h = hashlib.sha256()
    for path in INPUT_FILES:
        h.update(path.read_bytes())
    return h.hexdigest()[:12]


def check_fresh() -> int:
    """Exit 1 if the committed outputs were built from different inputs."""
    agg_path = OUT_DIR / "aggregates.json"
    if not agg_path.is_file():
        print(f"missing {agg_path} - run python3 ratio/build.py")
        return 1
    stored = json.loads(agg_path.read_text(encoding="utf-8"))
    stored_hash = stored.get("method", {}).get("inputs_hash")
    fresh = inputs_hash()
    if stored_hash != fresh:
        print(f"STALE outputs: aggregates.json was built from inputs "
              f"{stored_hash}, current inputs hash to {fresh} - "
              "run python3 ratio/build.py")
        return 1
    print(f"outputs are fresh (inputs {fresh})")
    return 0


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
    ap.add_argument("--check", action="store_true",
                    help="verify the committed outputs match the current "
                         "classifier + lexicon (exit 1 on drift)")
    ap.add_argument("--corpus", choices=["census", "atlas"], default="census",
                    help="census (default): the complete ratio/data/ fetch; "
                         "atlas: the 2,944-record sample, for comparison "
                         "runs only - committed outputs are census-based")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.check:
        return check_fresh()

    ruleset = clf.load_ruleset()
    if args.corpus == "census":
        rows = []
        for s in CENSUS_SOURCES:
            rows.extend(census_common.load_census(s))
        # census records carry the full (truncated) abstract as evidence
        # text; atlas rows only had the model's llm_quote
        for r in rows:
            r["llm_quote"] = r["abstract"]
            r["llm_category"] = None
    else:
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
        ["git", "describe", "--always", "--dirty"], capture_output=True,
        text=True, cwd=clf.REPO_ROOT).stdout.strip() or "unknown"

    per_source = collections.Counter(r["source"] for r in rows)
    if args.corpus == "census":
        retrieved = rows[0]["retrieved_at"] if rows else "?"
        corpus_desc = (f"census of {len(rows)} grant records - the complete "
                       f"result set of the atlas search nets, fetched "
                       f"{retrieved} (SweCRIS {per_source['swecris']}, "
                       f"CORDIS {per_source['cordis']}, NIH RePORTER "
                       f"{per_source['reporter']}); funnel in "
                       "ratio/data/funnel.json")
        corpus_caveats = [
            "The corpus is the complete result set of the ageing search "
            "nets, not any funding body's total budget; net recall bounds "
            "coverage - see ratio/data/CROSSCHECK.md for the comparison "
            "against published funder totals.",
            "Census records are classified over title + abstract; the "
            "earlier atlas sample used title + a short model-chosen quote.",
        ]
    else:
        corpus_desc = (f"2,944 grant records from commit {clf.ATLAS_COMMIT} "
                       "(SweCRIS 855, CORDIS 558, NIH RePORTER 1,531)")
        corpus_caveats = [
            "The corpus is an ageing-filtered sample per funder, not a "
            "census of any funding body's budget.",
        ]
    aggregates = {
        "method": {
            "description": "Deterministic rule classifier over the ageing "
                           "grant corpus; see ratio/README.md.",
            "corpus": corpus_desc,
            "corpus_mode": args.corpus,
            "lexicon": "classifier/keywords.json",
            "numerator": sorted(clf.NUMERATOR),
            "denominator": list(clf.CATEGORIES),
            "tie_margin": clf.TIE_MARGIN,
            "inputs_hash": inputs_hash(),
            "built_at_commit": git_head,
            "caveats": [
                "Labels are rule-based and not yet human-verified; the "
                "30-record human benchmark is pending.",
                *corpus_caveats,
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
