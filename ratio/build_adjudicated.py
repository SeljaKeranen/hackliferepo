#!/usr/bin/env python3
"""Build the adjudicated-scenario artifacts for the ratio page.

Takes the rules-built output/labels.jsonl, replaces the label of every record
that has an API adjudication in output/adjudicated.jsonl, and aggregates the
same regions/funders/totals as build.py. Writes:

  output/labels_adjudicated.jsonl
  output/aggregates_adjudicated.json

The rules scenario (output/aggregates.json, output/labels.jsonl) is untouched;
the page switches between the two with ?scenario=adjudicated.

Usage: python3 ratio/build_adjudicated.py
Python 3 stdlib only; no network, no model calls.
"""

import collections
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build as B  # noqa: E402

OUT = HERE / "output"
ADJ_PATH = OUT / "adjudicated.jsonl"
LABELS_PATH = OUT / "labels.jsonl"
INPUT_HASH_FILES = [Path(B.__file__), Path(B.clf.__file__),
                    B.clf.KEYWORDS_JSON, ADJ_PATH]


def inputs_hash() -> str:
    h = hashlib.sha256()
    for path in INPUT_HASH_FILES:
        h.update(path.read_bytes())
    return h.hexdigest()[:12]


def main() -> int:
    adjudicated = {}
    for line in ADJ_PATH.open(encoding="utf-8"):
        rec = json.loads(line)
        if "error" not in rec:
            adjudicated[rec["record_id"]] = rec

    regions = collections.defaultdict(B.blank_bucket)
    funders = collections.defaultdict(B.blank_bucket)
    total = B.blank_bucket()
    applied = 0
    with (OUT / "labels_adjudicated.jsonl").open("w",
                                                 encoding="utf-8") as fh:
        for line in LABELS_PATH.open(encoding="utf-8"):
            row = json.loads(line)
            adj = adjudicated.get(row["record_id"])
            if adj:
                applied += 1
                row["label"] = adj["label"]
                row["reason"] = adj.get("reason", row.get("reason"))
                row["confidence"] = adj.get("confidence")
                row["quote"] = adj.get("quote")
                row["adjudicated_by"] = adj.get("adjudicated_by",
                                                "deepseek-flash (API)")
            eur = B.parse_eur(row)
            region = row["region"]
            funder = (row.get("funder") or "").strip()
            B.add(regions[region], row["label"], eur)
            B.add(funders[(region, funder)], row["label"], eur)
            B.add(total, row["label"], eur)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    aggregates = {
        "method": {
            "description": "Rule classifier with deepseek-flash adjudication "
                           "of every ambiguous record; see ratio/README.md.",
            "corpus": "same 13,224-grant census as the rules build",
            "corpus_mode": "census",
            "lexicon": "classifier/keywords.json",
            "scenario": "adjudicated",
            "model": "deepseek-flash (API, temperature 0)",
            "adjudicated_records": applied,
            "numerator": sorted(B.clf.NUMERATOR),
            "denominator": list(B.clf.CATEGORIES),
            "tie_margin": B.clf.TIE_MARGIN,
            "evidence_floor": B.clf.EVIDENCE_FLOOR,
            "rel_margin": B.clf.REL_MARGIN,
            "inputs_hash": inputs_hash(),
            "caveats": [
                "Adjudicated labels come from one deepseek-flash pass, not "
                "from human reviewers; the 30-record human benchmark is "
                "still unlabelled.",
                "Every adjudication carries one verbatim quote from the "
                "record, machine-verified (ratio/verify_adjudication.py); "
                "records whose quote failed validation keep their rules "
                "label.",
                "On a 29-record overlap the API pass agrees with the "
                "in-session pass on 24 (83%); disagreements are boundary "
                "calls and are documented in ratio/README.md.",
                "The corpus is the complete result set of the ageing search "
                "nets, not any funding body's total budget; compare shapes "
                "across regions, not absolute budgets.",
                "Ambiguous adjudications stay excluded from both sides and "
                "reported as the honesty band beside the ratio.",
            ],
        },
        "total": B.finish(total),
        "regions": {
            reg: {"name": B.REGION_NAMES[reg], **B.finish(bucket)}
            for reg, bucket in sorted(regions.items())
        },
        "funders": [
            {"region": reg, "funder": funder, **B.finish(bucket)}
            for (reg, funder), bucket in sorted(
                funders.items(), key=lambda kv: -sum(kv[1]["eur"].values()))
        ],
    }
    (OUT / "aggregates_adjudicated.json").write_text(
        json.dumps(aggregates, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"applied {applied} adjudications over {sum(total['counts'].values())} records")
    for reg, data in aggregates["regions"].items():
        print(f"  {reg}: ratio={data['ratio']} "
              f"ambiguous_share={data['ambiguous_share']} "
              f"records={data['records']}")
    print(f"wrote {OUT / 'labels_adjudicated.jsonl'} and "
          f"{OUT / 'aggregates_adjudicated.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
