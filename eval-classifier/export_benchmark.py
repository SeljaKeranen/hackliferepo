#!/usr/bin/env python3
"""Fill the legacy 30-record human benchmark from the gate's verdicts.

Reads data/Track3_C2/benchmark/benchmark_30.csv (recovered with
`git show 2e59b27:...` if the live file disappears), the benchmark key, and
every eval-classifier/verdicts/<reviewer>.verdicts.json, and writes
benchmark_30_filled.csv with human_category / human_confidence /
human_notes filled for every benchmark record with a human consensus.
Unreviewed rows, stale verdicts and inter-reviewer conflicts are written
blank - including any annotation already present in the input CSV, so the
output holds exactly this gate's evidence and nothing else.

Vocabulary note: the guide predates the not_relevant/ambiguous split and the
social_population_aging category (classifier/KEYWORDS.md). Those labels are
written verbatim - honesty over backwards compatibility - with a
`legacy_equiv=ambiguous` marker in human_notes for old tooling that only
knows the original five labels.

Usage:
    python3 eval-classifier/export_benchmark.py
        [--out eval-classifier/benchmark_30_filled.csv]
"""
import argparse
import csv
import importlib.util
import io
import json
import sys
from pathlib import Path

GATE_DIR = Path(__file__).resolve().parent
BENCHMARK_CSV = "data/Track3_C2/benchmark/benchmark_30.csv"
BENCHMARK_KEY = "data/Track3_C2/benchmark/benchmark_30_key.json"
HUMAN_COLUMNS = ("human_category", "human_confidence", "human_notes")


def _load_module(name, filename):
    # Unique module names: a bare `import server` would collide with
    # eval/server.py if both suites ever share one interpreter.
    spec = importlib.util.spec_from_file_location(name, GATE_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


server = _load_module("eval_classifier_server", "server.py")
sampler = _load_module("eval_classifier_sample", "sample.py")

# labels the annotation guide postdates; everything else in server.LABELS is
# guide vocabulary and passes through untouched
NEW_LABELS = ("not_relevant", "social_population_aging")


def load_consensus(sample_path):
    """record_id -> the consensus verdict across all reviewers' current
    verdict files (None where reviewers conflict - conflicts are
    calibration data, not exportable evidence)."""
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    records = {r["record_id"]: r for r in sample["records"]}
    verdicts_by_reviewer = {}
    for reviewer, path in server.list_verdict_files():
        verdicts = json.loads(Path(path).read_text(encoding="utf-8"))
        server.mark_stale(verdicts, records)
        verdicts_by_reviewer[reviewer] = verdicts
    consensus = {}
    for rid, per_rev in server.effective_verdicts(
            verdicts_by_reviewer).items():
        labels = {v["label"] for v in per_rev.values()}
        if len(labels) == 1:
            consensus[rid] = next(iter(per_rev.values()))
    return consensus


def fill_rows(bench_rows, key, consensus):
    """Returns (filled_rows, n_filled). Rows keep guide column order; the
    three human columns are cleared first so nothing but this gate's
    consensus verdicts ends up in the output."""
    filled = 0
    for row in bench_rows:
        for col in HUMAN_COLUMNS:
            row[col] = ""
        entry = key.get(row["input_id"])
        v = consensus.get(entry["record_id"]) if entry else None
        if not isinstance(v, dict):
            continue
        label = v.get("label")
        if label not in server.LABELS:
            continue
        row["human_category"] = label
        # the gate collects a categorical decision, not graded confidence
        row["human_confidence"] = "1.0"
        notes = ["eval-classifier gate"]
        if label in NEW_LABELS:
            notes.append("legacy_equiv=ambiguous")
        if v.get("note"):
            notes.append(v["note"])
        row["human_notes"] = "; ".join(notes)
        filled += 1
    return bench_rows, filled


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path,
                    default=GATE_DIR / "benchmark_30_filled.csv")
    ap.add_argument("--sample", type=Path, default=GATE_DIR / "sample.json")
    args = ap.parse_args()

    if not args.sample.is_file():
        sys.exit(f"sample file not found: {args.sample} "
                 "(run eval-classifier/sample.py)")
    consensus = load_consensus(args.sample)
    key = json.loads(sampler.read_tracked(BENCHMARK_KEY))
    reader = csv.DictReader(io.StringIO(sampler.read_tracked(BENCHMARK_CSV)))
    rows, filled = fill_rows(list(reader), key, consensus)

    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{filled}/{len(rows)} benchmark records filled -> {args.out}")
    if filled < len(rows):
        print("unreviewed or stale benchmark records stay blank; review them "
              "in the gate (python3 eval-classifier/server.py) and re-run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
