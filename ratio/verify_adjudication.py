#!/usr/bin/env python3
"""Verify adjudication files: every quote must appear in its source record.

Usage:
    python3 ratio/verify_adjudication.py --sources ratio/data/se_pilot.jsonl \
        --adjudications ratio/output/adjudicated_se_pilot.jsonl

Checks each adjudication line against the source record text (title +
abstract): quote present as a case-insensitive substring, label in the
output vocabulary, no duplicate record ids. Prints a label distribution and
exits 1 on any failure. Stdlib only.
"""

import argparse
import json
import re
import sys
from collections import Counter

LABELS = {"fundamental_aging", "intervention", "age_related_disease", "care",
          "social_population_aging", "not_relevant", "ambiguous"}


def norm(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sources", required=True)
    ap.add_argument("--adjudications", required=True)
    args = ap.parse_args()

    sources = {}
    for line in open(args.sources, encoding="utf-8"):
        rec = json.loads(line)
        sources[rec["record_id"]] = rec
    rows = [json.loads(line) for line in
            open(args.adjudications, encoding="utf-8")]

    failures, seen, counts, changed = [], set(), Counter(), 0
    exact = 0
    for row in rows:
        rid = row["record_id"]
        if rid in seen:
            failures.append(f"{rid}: duplicate adjudication")
        seen.add(rid)
        if rid not in sources:
            failures.append(f"{rid}: no source record")
            continue
        if row.get("label") not in LABELS:
            failures.append(f"{rid}: unknown label {row.get('label')!r}")
        src = sources[rid]
        raw = (src.get("title") or "") + " " + (src.get("abstract") or "")
        if not norm(row.get("quote")) or norm(row["quote"]) not in norm(raw):
            failures.append(f"{rid}: quote not found in source text")
        if row.get("quote") in raw:
            exact += 1
        counts[row["label"]] += 1
        changed += row["label"] != "ambiguous"

    print(f"adjudications: {len(rows)} | sources: {len(sources)}")
    print(f"quotes verified (case-insensitive): "
          f"{len(rows) - sum('quote not found' in f for f in failures)}"
          f"/{len(rows)} | case-exact: {exact}/{len(rows)}")
    print(f"resolved out of ambiguous: {changed}/{len(rows)}")
    print("label distribution:", dict(counts.most_common()))
    if failures:
        print(f"\n{len(failures)} failure(s):")
        for failure in failures:
            print(" -", failure)
        return 1
    print("all adjudications verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
