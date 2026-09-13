#!/usr/bin/env python3
"""Tests for the gate sampler: determinism, benchmark inclusion, stratum
coverage, and boundary-flag logic, against a synthetic labels file so the
tests never depend on the ratio pipeline having run.

Run: python3 eval-classifier/test_sample.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sample

failures = []


def expect(cond, msg):
    if not cond:
        failures.append(msg)


def synthetic_labels(n=200):
    """A labels list covering every label x source stratum, with known
    boundary records."""
    labels = ("fundamental_aging", "intervention", "age_related_disease",
              "care", "social_population_aging", "ambiguous", "not_relevant")
    sources = ("swecris", "cordis", "reporter")
    records = []
    for i in range(n):
        label = labels[i % len(labels)]
        rec = {
            "record_id": f"{sources[i % 3]}:R{i:04d}",
            "source": sources[i % 3],
            "title": f"Synthetic grant {i}",
            "label": label,
            "reason": "synthetic",
            "matched_keywords": {},
            "anchor_terms": [],
            "confidence": None,
            "llm_category": "ambiguous",
        }
        if i % 11 == 0 and label in sample.SUBSTANTIVE:
            rec["confidence"] = 0.1          # low-margin forced call
        elif label in sample.SUBSTANTIVE:
            rec["confidence"] = 0.9
        if i % 13 == 0:
            rec["llm_category"] = "care"     # disagrees unless label is care
        records.append(rec)
    return records


def main():
    records = synthetic_labels()
    by_id = {r["record_id"]: r for r in records}
    bench = {r["record_id"]: f"B{i + 1:02d}"
             for i, r in enumerate(records[:30])}

    # boundary flags
    low = {"record_id": "x", "label": "care", "confidence": 0.2,
           "llm_category": "care"}
    expect(sample.boundary_flags(low) == ["low_margin"],
           "substantive label with margin < threshold must flag low_margin")
    expect("low_margin" not in sample.boundary_flags(
               {**low, "label": "ambiguous"}),
           "ambiguous is never low_margin - the label already flags itself")
    expect(sample.boundary_flags({**low, "confidence": None}) == [],
           "gate outcomes (confidence null) are never low_margin")
    # the tuning/holdout split is a pure function of (seed, record_id):
    # stable across runs and across changes to the rest of the sample
    expect(sample.split_for("swecris:X1", 7) == sample.split_for(
               "swecris:X1", 7),
           "split assignment must be deterministic")
    expect(any(sample.split_for(f"r{i}", 7)
               != sample.split_for(f"r{i}", 8) for i in range(64)),
           "the split must depend on the seed")

    dis = {"record_id": "x", "label": "care", "confidence": None,
           "llm_category": "intervention"}
    expect(sample.boundary_flags(dis) == ["llm_disagree"],
           "old substantive llm label != new label must flag llm_disagree")
    expect(sample.boundary_flags({**dis, "llm_category": "ambiguous"}) == [],
           "old ambiguous is not a disagreement signal - it was a catch-all")

    # determinism: same inputs + seed -> byte-identical pick
    p1 = sample.draw_sample(records, bench, seed=7, target=60)
    p2 = sample.draw_sample(records, bench, seed=7, target=60)
    expect(p1 == p2, "same seed must reproduce the exact sample")
    p3 = sample.draw_sample(records, bench, seed=8, target=60)
    expect(set(p1) != set(p3),
           "a different seed should draw a different sample")

    # benchmark inclusion and reasons
    expect(set(bench) <= set(p1), "every benchmark record must be sampled")
    expect(all("benchmark" in p1[rid] for rid in bench),
           "benchmark records must carry the benchmark reason")

    # stratum coverage: every non-empty label x source stratum is sampled
    want = {(r["label"], r["source"]) for r in records}
    got = {(by_id[rid]["label"], by_id[rid]["source"]) for rid in p1}
    expect(want == got, f"missing strata: {want - got}")

    # size and quota bounds
    expect(len(p1) == 60, f"target size must be hit exactly, got {len(p1)}")
    n_low = sum(1 for v in p1.values() if "low_margin" in v)
    n_dis = sum(1 for v in p1.values() if "llm_disagree" in v)
    expect(n_low == sample.QUOTA_LOW_MARGIN,
           f"low_margin quota should be filled, got {n_low}")
    expect(n_dis == sample.QUOTA_LLM_DISAGREE,
           f"llm_disagree quota should be filled, got {n_dis}")

    # a target below the mandatory picks still keeps benchmark + strata
    p_small = sample.draw_sample(records, bench, seed=7, target=10)
    expect(set(bench) <= set(p_small),
           "benchmark records survive even a too-small target")

    # a labels file smaller than the target yields every record, silently
    # capping at the pool size (documented, not an error)
    few = records[:40]
    p_all = sample.draw_sample(few, {r["record_id"]: f"B{i + 1:02d}"
                                     for i, r in enumerate(few[:30])},
                               seed=7, target=72)
    expect(len(p_all) == 40,
           "an undersized labels file caps the sample at the pool size")

    # load_labels rejects malformed input loudly
    def labels_file(lines):
        fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        fh.write("\n".join(lines) + "\n")
        fh.close()
        return fh.name

    ok_rec = dict(records[0])
    for bad, why in (
            ([], "an empty labels file must be rejected"),
            ([json.dumps({k: v for k, v in ok_rec.items()
                          if k != "label"})],
             "a record missing a required field must be rejected"),
            ([json.dumps(ok_rec), json.dumps(ok_rec)],
             "duplicate record_ids must be rejected")):
        path = labels_file(bad)
        try:
            sample.load_labels(path)
            expect(False, why)
        except SystemExit:
            pass
        finally:
            os.unlink(path)

    # end-to-end build() against a temp labels file, with the corpus and
    # benchmark lookups stubbed so nothing touches the repo data
    real_quotes, real_bench = sample.load_quotes, sample.load_benchmark_ids
    sample.load_quotes = lambda: {r["record_id"]: f"quote {r['record_id']}"
                                  for r in records}
    sample.load_benchmark_ids = lambda: dict(bench)
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl",
                                         delete=False) as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
            path = fh.name
        data = sample.build(path, seed=7, target=60)
        expect(data["meta"]["sampled"] == len(data["records"]) == 60,
               "meta.sampled must match the record count")
        expect(data["meta"]["benchmark_records"] == 30,
               "meta must count all 30 benchmark records")
        expect(all(r["quote"] == f"quote {r['record_id']}"
                   for r in data["records"]),
               "every sampled record must carry its corpus quote")
        expect(all(r["sampling"]["stratum"]
                   == f"{r['label']}|{r['source']}"
                   for r in data["records"]),
               "sampling.stratum must name the record's label x source")
        expect(all(r["sampling"]["split"] in ("tuning", "holdout")
                   for r in data["records"]),
               "every sampled record must be assigned a split")
        splits = data["meta"]["split_counts"]
        expect(set(splits) == {"tuning", "holdout"}
               and min(splits.values()) >= len(data["records"]) // 4,
               f"the halves should be roughly balanced: {splits}")
        data2 = sample.build(path, seed=7, target=60)
        expect(data["records"] == data2["records"],
               "build() must be deterministic for a fixed labels file + seed")

        # a labels file that lost a benchmark record must fail loudly - the
        # 30 legacy records are a hard guarantee of the gate
        sample.load_benchmark_ids = lambda: {**bench, "missing:B99": "B99"}
        try:
            sample.build(path, seed=7, target=60)
            expect(False, "build() must reject a labels file missing a "
                          "benchmark record")
        except SystemExit as exc:
            expect("missing:B99" in str(exc.code),
                   "the missing-benchmark error must name the record")
        os.unlink(path)
    finally:
        sample.load_quotes, sample.load_benchmark_ids = real_quotes, real_bench

    if failures:
        print(f"FAIL: {len(failures)} problem(s)")
        for msg in failures:
            print(f"  - {msg}")
        sys.exit(1)
    print("OK: sampler tests passed")


if __name__ == "__main__":
    main()
