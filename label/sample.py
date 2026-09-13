"""Build a labelling batch from the real corpus.

Joins three files that already exist in the repo:

  ratio/data/census_*.jsonl.gz   title, ABSTRACT, funder, year, amount, url
  ratio/output/labels.jsonl      the classifier's label (hidden from labellers)
  ratio/expert/expert-labels.jsonl  the expert pass (hidden from labellers)

The abstracts matter. Every earlier layer in this project judged grants from
a title plus a short extracted quote, and both the expert README and
classifier/KEYWORDS.md name that as a limitation. The census files carry the
full abstract, so researchers get the real text.

Sampling is stratified across the classifier's label so a batch is not all
easy negatives, and deliberately over-weights the records where the
classifier and the expert pass disagree, because those are where human
judgment is worth the most. Selection is seeded and the manifest records
which stratum each grant came from, so the draw is reproducible and its
biases are legible rather than hidden.
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
from collections import Counter
from pathlib import Path
from typing import Dict, List

from label import store

REPO_ROOT = Path(__file__).resolve().parents[1]
CENSUS_DIR = REPO_ROOT / "ratio/data"
CLASSIFIER_LABELS = REPO_ROOT / "ratio/output/labels.jsonl"
EXPERT_LABELS = REPO_ROOT / "ratio/expert/expert-labels.jsonl"

DEFAULT_SIZE = 40
DEFAULT_SEED = 20260913
MIN_ABSTRACT_CHARS = 180  # below this there is nothing for a human to judge

# Strata over the classifier's label, with the share of the batch each gets.
# "disagreement" (classifier vs expert pass) is first and largest: those are
# the records a human read is most likely to settle.
STRATA = (
    ("disagreement", 0.40),
    ("fundamental_aging", 0.15),
    ("intervention", 0.10),
    ("age_related_disease", 0.15),
    ("ambiguous", 0.10),
    ("not_relevant", 0.10),
)


def _read_jsonl(path: Path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_census() -> Dict[str, dict]:
    records = {}
    for path in sorted(CENSUS_DIR.glob("census_*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    records[rec["record_id"]] = rec
    return records


def build(size: int = DEFAULT_SIZE, seed: int = DEFAULT_SEED) -> dict:
    census = load_census()
    classifier = {r["record_id"]: r for r in _read_jsonl(CLASSIFIER_LABELS)}
    expert = {r["record_id"]: r for r in _read_jsonl(EXPERT_LABELS)}

    pools: Dict[str, List[str]] = {name: [] for name, _ in STRATA}
    for record_id, clf in classifier.items():
        source = census.get(record_id)
        if not source:
            continue
        abstract = (source.get("abstract") or "").strip()
        if len(abstract) < MIN_ABSTRACT_CHARS:
            continue
        clf_label = clf.get("label", "")
        exp_label = (expert.get(record_id) or {}).get("expert_label", "")
        if exp_label and exp_label != clf_label:
            pools["disagreement"].append(record_id)
        elif clf_label in pools:
            pools[clf_label].append(record_id)

    rng = random.Random(seed)
    chosen: List[tuple] = []
    taken = set()
    for name, share in STRATA:
        pool = sorted(set(pools[name]) - taken)
        want = min(round(size * share), len(pool))
        for record_id in rng.sample(pool, want) if want else []:
            chosen.append((record_id, name))
            taken.add(record_id)

    # Top up from the largest remaining pool if rounding left us short.
    if len(chosen) < size:
        leftovers = sorted({r for p in pools.values() for r in p} - taken)
        for record_id in rng.sample(leftovers, min(size - len(chosen), len(leftovers))):
            chosen.append((record_id, "topup"))
            taken.add(record_id)

    rng.shuffle(chosen)

    records = []
    for record_id, stratum in chosen:
        source = census[record_id]
        clf = classifier.get(record_id, {})
        records.append({
            # Shown to the labeller
            "record_id": record_id,
            "title": source.get("title", ""),
            "abstract": (source.get("abstract") or "").strip(),
            "funder": source.get("funder", ""),
            "year": source.get("year"),
            "amount_eur": source.get("amount_eur"),
            "url": source.get("url", ""),
            "source": source.get("source", ""),
            # Withheld from the labeller; served only to the admin view
            "_hidden": {
                "stratum": stratum,
                "classifier_label": clf.get("label", ""),
                "classifier_reason": clf.get("reason", ""),
                "expert_label": (expert.get(record_id) or {}).get("expert_label", ""),
                "expert_reason": (expert.get(record_id) or {}).get("reason", ""),
            },
        })

    for record in records:
        record["fingerprint"] = store.record_fingerprint(record)

    return {
        "size": len(records),
        "seed": seed,
        "strata": dict(Counter(r["_hidden"]["stratum"] for r in records)),
        "built_from": {
            "census": "ratio/data/census_*.jsonl.gz (full abstracts)",
            "classifier": "ratio/output/labels.jsonl",
            "expert": "ratio/expert/expert-labels.jsonl",
        },
        "note": ("Every labeller sees every record in this batch. Overlap is "
                  "deliberate: inter-rater agreement cannot be computed from a "
                  "partitioned queue."),
        "records": records,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--batch", default="batch_001", help="batch id (used as the filename)")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()
    if not store.is_slug(args.batch):
        raise SystemExit(f"batch id must be a lowercase slug, got {args.batch!r}")

    batch = build(args.size, args.seed)
    path = store.batch_path(args.batch)
    store.atomic_write_json(path, batch)
    print(f"wrote {path} — {batch['size']} records")
    for name, count in sorted(batch["strata"].items()):
        print(f"  {count:3d}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
