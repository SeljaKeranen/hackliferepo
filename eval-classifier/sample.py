#!/usr/bin/env python3
"""Stratified sampler for the grant-classifier evaluation gate.

Draws the human-review sample from the ratio pipeline's labels
(ratio/output/labels.jsonl) and writes eval-classifier/sample.json, the
committed file the AI judges and the review server both read.

Selection, in order (all seeded, fully deterministic for a given labels
file + seed):

  1. the 30 legacy human-benchmark records
     (data/Track3_C2/benchmark/benchmark_30_key.json; recovered with
     `git show 2e59b27:...` if the live file disappears) - always included,
  2. at least one record from every non-empty label x source stratum,
  3. an oversample of the decision boundaries: records whose confidence
     margin is below LOW_MARGIN, and records where the atlas's old
     llm_category disagrees with the new label,
  4. a uniform top-up to the target size.

Each sampled record carries the classifier's full output (label, reason,
matched keywords, anchor terms, confidence margin), the text the classifier
saw (title + llm_quote), and why it was sampled. python3 stdlib only.

Usage:
    python3 eval-classifier/sample.py [--labels ratio/output/labels.jsonl]
        [--seed 20260912] [--target 72] [--out eval-classifier/sample.json]
"""
import argparse
import csv
import hashlib
import io
import json
import random
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LABELS = REPO_ROOT / "ratio" / "output" / "labels.jsonl"
DEFAULT_OUT = Path(__file__).resolve().parent / "sample.json"

ATLAS_COMMIT = "2e59b27"
ATLAS_PREFIX = "data/Track3_C2/output/"
ATLAS_FILES = ("swecris.csv", "cordis.csv", "nih_reporter.csv")
BENCHMARK_KEY = "data/Track3_C2/benchmark/benchmark_30_key.json"

# llm_category values that can meaningfully disagree with the new label;
# the old "ambiguous" folded together ambiguous/not_relevant/social records
# (classifier/KEYWORDS.md), so it is not treated as a disagreement signal.
OLD_SUBSTANTIVE = ("fundamental_aging", "intervention", "age_related_disease",
                   "care")
SUBSTANTIVE = OLD_SUBSTANTIVE + ("social_population_aging",)
# A substantive label whose winning precision margin is below this is a
# decision boundary worth oversampling: ratio/classify.py sends margins
# below 0.3 to ambiguous, so the band just above that floor is where forced
# calls are weakest. Low-margin ambiguous records are not flagged - the
# ambiguous label already declares the uncertainty.
LOW_MARGIN = 0.45
QUOTA_LOW_MARGIN = 10
QUOTA_LLM_DISAGREE = 10
DEFAULT_SEED = 20260912
DEFAULT_TARGET = 72


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_tracked(rel_path):
    """Text of a repo file: the live tree, or `git show` recovery from the
    atlas commit if the live file disappears. BOM-stripped either way."""
    live = REPO_ROOT / rel_path
    if live.is_file():
        return live.read_text(encoding="utf-8-sig")
    try:
        out = subprocess.run(
            ["git", "show", f"{ATLAS_COMMIT}:{rel_path}"], check=True,
            capture_output=True, cwd=REPO_ROOT).stdout.decode("utf-8")
    except (subprocess.CalledProcessError, OSError) as exc:
        stderr = getattr(exc, "stderr", b"") or b""
        detail = stderr.decode(errors="replace").strip() or str(exc)
        sys.exit(f"{rel_path} is not in the working tree and cannot be "
                 f"recovered from commit {ATLAS_COMMIT} (shallow clone or "
                 f"rewritten history?): {detail}")
    return out.lstrip("﻿")


def load_quotes():
    """record_id -> llm_quote from the atlas corpus (live tree, or git-show
    recovery from commit 2e59b27 if the tree is gone)."""
    quotes = {}
    for name in ATLAS_FILES:
        # StringIO, not splitlines(): quoted CSV fields carry embedded
        # newlines, and the reviewer must see the exact classifier input.
        text = read_tracked(f"{ATLAS_PREFIX}{name}")
        for row in csv.DictReader(io.StringIO(text)):
            quotes[row["record_id"]] = row["llm_quote"]
    return quotes


def load_benchmark_ids():
    """record_id -> benchmark input_id (B01..B30)."""
    key = json.loads(read_tracked(BENCHMARK_KEY))
    return {v["record_id"]: bid for bid, v in key.items()}


def load_labels(path):
    records = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            # strict on the documented labels.jsonl shape: a silently
            # missing confidence/llm_category would zero out the
            # decision-boundary oversample without any symptom
            for field in ("record_id", "source", "title", "label", "reason",
                          "matched_keywords", "anchor_terms", "confidence",
                          "llm_category"):
                if field not in rec:
                    sys.exit(f"{path}:{n}: record missing {field!r}")
            records.append(rec)
    if not records:
        sys.exit(f"{path}: no records")
    ids = [r["record_id"] for r in records]
    if len(ids) != len(set(ids)):
        sys.exit(f"{path}: duplicate record_id")
    return records


def split_for(record_id, seed):
    """Deterministic tuning/holdout assignment by seeded record-id hash.
    Per-record (independent of the rest of the sample), so a record never
    migrates between halves when the sample is regenerated; the halves are
    therefore approximately, not exactly, equal."""
    digest = hashlib.sha256(f"{seed}:{record_id}".encode("utf-8")).hexdigest()
    return "tuning" if int(digest, 16) % 2 == 0 else "holdout"


def boundary_flags(rec):
    flags = []
    conf = rec.get("confidence")
    if (conf is not None and conf < LOW_MARGIN
            and rec["label"] in SUBSTANTIVE):
        flags.append("low_margin")
    if (rec.get("llm_category") in OLD_SUBSTANTIVE
            and rec["label"] != rec["llm_category"]):
        flags.append("llm_disagree")
    return flags


def draw_sample(records, benchmark_ids, seed, target):
    """Pick record_ids and the reason each was picked. Deterministic:
    records are keyed and iterated in sorted record_id order and every
    random draw comes from one seeded generator."""
    rng = random.Random(seed)
    by_id = {r["record_id"]: r for r in records}
    ordered_ids = sorted(by_id)
    picked = {}  # record_id -> list of why-sampled reasons

    def pick(rid, why):
        picked.setdefault(rid, []).append(why)

    # 1. every legacy benchmark record present in the labels file
    for rid in sorted(rid for rid in benchmark_ids if rid in by_id):
        pick(rid, "benchmark")

    # 2. at least one record per non-empty label x source stratum
    strata = {}
    for rid in ordered_ids:
        r = by_id[rid]
        strata.setdefault((r["label"], r["source"]), []).append(rid)
    for key in sorted(strata):
        if not any(rid in picked for rid in strata[key]):
            pick(rng.choice(strata[key]), "stratum_min")

    # 3. decision-boundary oversample
    for flag, quota in (("low_margin", QUOTA_LOW_MARGIN),
                        ("llm_disagree", QUOTA_LLM_DISAGREE)):
        pool = [rid for rid in ordered_ids
                if flag in boundary_flags(by_id[rid]) and rid not in picked]
        for rid in rng.sample(pool, min(quota, len(pool))):
            pick(rid, flag)

    # 4. top-up to the target, round-robin across labels so the big
    # ambiguous/not_relevant pools don't drown the small categories
    pools = {}
    for rid in ordered_ids:
        if rid not in picked:
            pools.setdefault(by_id[rid]["label"], []).append(rid)
    while len(picked) < target and pools:
        for label in sorted(pools):
            if len(picked) >= target:
                break
            rid = pools[label].pop(rng.randrange(len(pools[label])))
            pick(rid, "fill")
            if not pools[label]:
                del pools[label]
    return picked


def build(labels_path, seed, target):
    records = load_labels(labels_path)
    quotes = load_quotes()
    benchmark_ids = load_benchmark_ids()
    missing_bench = sorted(set(benchmark_ids) - {r["record_id"]
                                                 for r in records})
    if missing_bench:
        sys.exit("labels file is missing benchmark record(s): "
                 f"{', '.join(missing_bench)}")
    picked = draw_sample(records, benchmark_ids, seed, target)

    by_id = {r["record_id"]: r for r in records}
    out_records = []
    for rid in sorted(picked):
        rec = dict(by_id[rid])
        rec["quote"] = quotes.get(rid, "")
        rec["sampling"] = {
            "stratum": f"{rec['label']}|{rec['source']}",
            "why": picked[rid],
            "boundary_flags": boundary_flags(by_id[rid]),
            "split": split_for(rid, seed),
        }
        if rid in benchmark_ids:
            rec["sampling"]["benchmark_id"] = benchmark_ids[rid]
        out_records.append(rec)

    label_counts = {}
    why_counts = {}
    split_counts = {}
    for r in out_records:
        label_counts[r["label"]] = label_counts.get(r["label"], 0) + 1
        split = r["sampling"]["split"]
        split_counts[split] = split_counts.get(split, 0) + 1
        for why in r["sampling"]["why"]:
            why_counts[why] = why_counts.get(why, 0) + 1
    return {
        "meta": {
            "seed": seed,
            "target": target,
            "sampled": len(out_records),
            "labels_file": Path(labels_path).name,
            "labels_sha256": sha256_file(labels_path),
            "labels_records": len(records),
            "benchmark_records": sum(
                1 for r in out_records if "benchmark_id" in r["sampling"]),
            "label_counts": dict(sorted(label_counts.items())),
            "why_counts": dict(sorted(why_counts.items())),
            "split_counts": dict(sorted(split_counts.items())),
        },
        "records": out_records,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", type=Path, default=DEFAULT_LABELS,
                    help="ratio pipeline labels.jsonl (default: "
                         "ratio/output/labels.jsonl)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--target", type=int, default=DEFAULT_TARGET)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.labels.is_file():
        sys.exit(f"labels file not found: {args.labels}\n"
                 "Run the ratio pipeline first (python3 ratio/classify.py "
                 "writes ratio/output/labels.jsonl) or point --labels at a "
                 "labels snapshot.")
    data = build(args.labels, args.seed, args.target)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    m = data["meta"]
    print(f"sampled {m['sampled']} of {m['labels_records']} records "
          f"({m['benchmark_records']} benchmark) -> {args.out}")
    for label, n in m["label_counts"].items():
        print(f"  {label:24s} {n:3d}")
    print("picked because: " + ", ".join(
        f"{why} {n}" for why, n in m["why_counts"].items()))
    print("split: " + ", ".join(
        f"{split} {n}" for split, n in m["split_counts"].items()))
    for flag, quota in (("low_margin", QUOTA_LOW_MARGIN),
                        ("llm_disagree", QUOTA_LLM_DISAGREE)):
        if m["why_counts"].get(flag, 0) < quota:
            print(f"note: {flag} oversample underfilled "
                  f"({m['why_counts'].get(flag, 0)}/{quota}) - the labels "
                  "file has few such records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
