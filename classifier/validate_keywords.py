#!/usr/bin/env python3
"""Validate the grant-search keyword lexicon against the Aging Funding Atlas.

The atlas (2,944 records: swecris + cordis + nih_reporter) was added in commit
2e59b27 and later deleted from main in 4061bff. Recover the CSVs from history:

    git show 2e59b27:data/Track3_C2/output/swecris.csv      > <dir>/swecris.csv
    git show 2e59b27:data/Track3_C2/output/cordis.csv       > <dir>/cordis.csv
    git show 2e59b27:data/Track3_C2/output/nih_reporter.csv > <dir>/nih_reporter.csv

Usage:
    python3 classifier/validate_keywords.py                 # auto-recover via git show
    python3 classifier/validate_keywords.py --data-dir DIR  # use pre-recovered CSVs
    python3 classifier/validate_keywords.py --update        # rewrite stats in keywords.json

Exit status 0 means every stored stat matches a recomputation and every kept
keyword clears its threshold. Python 3 stdlib only.

Matching semantics (shared by this script and KEYWORDS.md): a keyword matches a
record if it appears in the lowercased title + llm_quote as a whole word or
phrase; a ``*`` in a keyword matches any word-character suffix (``senolytic*``
matches "senolytics"); spaces match any whitespace run.

Precision proxy: the share of a keyword's matching records whose llm_category
equals the keyword's category. The LLM labels are unverified, so this is a
proxy, not ground truth; the 30-record human benchmark remains the real test.
"""

import argparse
import collections
import csv
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ATLAS_COMMIT = "2e59b27"
ATLAS_FILES = ["swecris.csv", "cordis.csv", "nih_reporter.csv"]
ATLAS_PREFIX = "data/Track3_C2/output/"
EXPECTED_RECORDS = 2944
CATEGORIES = ["fundamental_aging", "intervention", "age_related_disease", "care"]


def recover_atlas(dest: Path) -> None:
    for name in ATLAS_FILES:
        blob = subprocess.run(
            ["git", "show", f"{ATLAS_COMMIT}:{ATLAS_PREFIX}{name}"],
            check=True, capture_output=True,
        ).stdout
        (dest / name).write_bytes(blob)


def load_rows(data_dir: Path):
    rows = []
    for name in ATLAS_FILES:
        with open(data_dir / name, encoding="utf-8-sig", newline="") as fh:
            rows.extend(csv.DictReader(fh))
    if len(rows) != EXPECTED_RECORDS:
        sys.exit(f"expected {EXPECTED_RECORDS} atlas records, got {len(rows)}")
    return [
        {
            "record_id": r["record_id"],
            "source": r["source"],
            "llm_category": r["llm_category"],
            "title": r["title"],
            "text": (r["title"] + " " + r["llm_quote"]).lower(),
        }
        for r in rows
    ]


def compile_term(term: str) -> re.Pattern:
    pat = re.escape(term.lower())
    pat = pat.replace(r"\*", r"\w*").replace(r"\ ", r"\s+")
    return re.compile(r"\b" + pat + r"\b")


def term_stats(term: str, category: str, rows, examples: int = 0) -> dict:
    pat = compile_term(term)
    hits = [r for r in rows if pat.search(r["text"])]
    by_cat = collections.Counter(r["llm_category"] for r in hits)
    stats = {
        "hits": len(hits),
        "by_category": dict(sorted(by_cat.items(), key=lambda kv: -kv[1])),
    }
    if category:
        stats["precision"] = round(by_cat[category] / len(hits), 3) if hits else 0.0
    if examples:
        false_hits = [r for r in hits if r["llm_category"] != category]
        stats["example_false_hits"] = [
            {
                "record_id": r["record_id"],
                "llm_category": r["llm_category"],
                "title": r["title"][:110],
            }
            for r in false_hits[:examples]
        ]
    return stats


def coverage(keywords: list, category: str, rows) -> float:
    pats = [compile_term(k["term"]) for k in keywords]
    cat_rows = [r for r in rows if r["llm_category"] == category]
    matched = sum(1 for r in cat_rows if any(p.search(r["text"]) for p in pats))
    return round(matched / len(cat_rows), 3) if cat_rows else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", type=Path,
                    help="directory with the three recovered atlas CSVs "
                         "(default: auto-recover via git show)")
    ap.add_argument("--keywords", type=Path,
                    default=Path(__file__).parent / "keywords.json")
    ap.add_argument("--update", action="store_true",
                    help="rewrite all stats in keywords.json instead of validating")
    args = ap.parse_args()

    if args.data_dir:
        rows = load_rows(args.data_dir)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            recover_atlas(Path(tmp))
            rows = load_rows(Path(tmp))

    lex = json.loads(args.keywords.read_text(encoding="utf-8"))
    thresholds = lex["meta"]["thresholds"]
    failures = []

    def check(entry, fresh, label):
        stale = {k: entry.get(k) for k in fresh if k in entry}
        if args.update:
            entry.update(fresh)
        elif stale != fresh:
            failures.append(f"stale stats for {label}: stored {stale} != computed {fresh}")

    for cat, block in lex["categories"].items():
        for lang in ("en", "sv"):
            for entry in block.get(lang, []):
                fresh = term_stats(entry["term"], cat, rows)
                check(entry, fresh, f"{cat}/{lang}/{entry['term']}")
                th = thresholds[lang]
                exempt = "variant_of" in entry
                if not exempt and (
                    entry["hits"] < th["min_hits"]
                    or entry["precision"] < th["min_precision"]
                ):
                    failures.append(
                        f"below threshold: {cat}/{lang}/{entry['term']} "
                        f"hits={entry['hits']} precision={entry['precision']}"
                    )
                if args.update:
                    if entry["hits"] < 5:
                        entry["low_evidence"] = True
                    else:
                        entry.pop("low_evidence", None)
        for entry in block.get("trap_terms", []):
            fresh = term_stats(entry["term"], cat, rows, examples=3)
            check(entry, fresh, f"{cat}/trap/{entry['term']}")

    for lang in ("en", "sv"):
        for entry in lex["meta"]["broad_net"][lang]:
            fresh = term_stats(entry["term"], None, rows)
            check(entry, fresh, f"broad_net/{lang}/{entry['term']}")
    for entry in lex["meta"]["exclusion_markers"]:
        fresh = term_stats(entry["term"], "ambiguous", rows)
        fresh["ambiguous_share"] = fresh.pop("precision")
        check(entry, fresh, f"exclusion/{entry['term']}")

    print(f"atlas records: {len(rows)}")
    print(f"{'category':22s} {'en':>3s} {'sv':>3s} {'coverage':>9s}")
    for cat in CATEGORIES:
        block = lex["categories"][cat]
        kws = block.get("en", []) + block.get("sv", [])
        cov = coverage(kws, cat, rows)
        fresh_cov = {"coverage": cov}
        check(block, fresh_cov, f"{cat}/coverage")
        print(f"{cat:22s} {len(block.get('en', [])):3d} {len(block.get('sv', [])):3d} {cov:9.3f}")

    if args.update:
        args.keywords.write_text(
            json.dumps(lex, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"updated {args.keywords}")
        return 0
    if failures:
        print(f"\n{len(failures)} validation failure(s):")
        for f in failures:
            print(" -", f)
        return 1
    print("all stored stats match; all keywords clear their thresholds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
