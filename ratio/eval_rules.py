#!/usr/bin/env python3
"""Evaluate the rules classifier against the senior-expert labels.

Reference: ratio/expert/expert-labels.jsonl (one expert pass over the 2,944
atlas records). Prints the per-rules-label agreement table in the same shape
as ratio/expert/README.md, so the v2 rules can be compared with the published
v1 baseline (53.3% overall; per-label rates hardcoded below as V1_RATES).

Usage: python3 ratio/eval_rules.py
Python 3 stdlib only; no network, no model calls.
"""

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "classifier"))

import classify as clf  # noqa: E402

EXPERT = HERE / "expert" / "expert-labels.jsonl"
V1_RATES = {"social_population_aging": 0.90, "not_relevant": 0.83,
            "intervention": 0.72, "fundamental_aging": 0.67, "care": 0.65,
            "age_related_disease": 0.57, "ambiguous": 0.07}
V1_OVERALL = 0.533


def main() -> int:
    experts = {}
    for line in EXPERT.open(encoding="utf-8"):
        rec = json.loads(line)
        experts[rec["record_id"]] = rec["expert_label"]
    ruleset = clf.load_ruleset()
    rows = clf.load_corpus()

    table = collections.defaultdict(lambda: [0, 0])
    agree_all = 0
    for r in rows:
        out = clf.classify(r["title"], r["llm_quote"], ruleset)
        expert = experts.get(r["record_id"])
        table[out["label"]][0] += 1
        if out["label"] == expert:
            table[out["label"]][1] += 1
            agree_all += 1
    total = len(rows)
    print(f"records: {total} | v2 overall agreement: {agree_all / total:.3f} "
          f"(v1 baseline {V1_OVERALL})")
    print(f"{'rules label':24s} {'n':>5s} {'agree':>6s} {'v2':>6s} "
          f"{'v1':>6s}")
    for label in sorted(table, key=lambda k: -table[k][0]):
        n, ok = table[label]
        v1 = V1_RATES.get(label)
        v1_text = f"{v1:.2f}" if v1 is not None else "  - "
        print(f"{label:24s} {n:5d} {ok:6d} {ok / n:6.2f} {v1_text:>6s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
