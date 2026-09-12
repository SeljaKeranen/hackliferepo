#!/usr/bin/env python3
"""Validate mined keyword candidates against both label sources.

Gate 1: the lexicon validator's semantics and thresholds over the 2,944-record
atlas (en: >=3 hits, >="threshold" precision; sv: >=1 hit), with the same
PROXY_LABEL rule the validator uses (social_population_aging is measured
against the atlas 'ambiguous' label because the category postdates the LLM
labels).

Gate 2: precision against ratio/expert/expert-labels.jsonl, minimum 3 expert
records and 0.60 precision. A Gate-1 pass with fewer than 3 expert records is
provisional; a Gate-1 pass that fails Gate 2 is rejected.

Census impact columns show how many currently ambiguous census records (and
EUR) each candidate touches.

Inputs: ratio/candidates.csv, the atlas, the expert labels, the census.
Output: ratio/candidates_validated.csv with a decision per candidate.
Python 3 stdlib only; no network, no model calls.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "data"))
sys.path.insert(0, str(HERE.parent / "classifier"))

import classify as clf  # noqa: E402
import census_common  # noqa: E402
import validate_keywords as vk  # noqa: E402

CANDIDATES = HERE / "candidates.csv"
OUT_CSV = HERE / "candidates_validated.csv"
EXPERT = HERE / "expert" / "expert-labels.jsonl"
LABELS = HERE / "output" / "labels.jsonl"


def load_experts() -> dict:
    return {json.loads(line)["record_id"]: json.loads(line)["expert_label"]
            for line in EXPERT.open(encoding="utf-8")}


def atlas_rows() -> list:
    rows = []
    for r in clf.load_corpus():
        rows.append({
            "record_id": r["record_id"],
            "llm_category": r["llm_category"],
            "text": ((r["title"] or "") + " " + (r["llm_quote"] or "")).lower(),
        })
    return rows


def ambiguous_census() -> list:
    amb = set()
    for line in LABELS.open(encoding="utf-8"):
        rec = json.loads(line)
        if rec["label"] == "ambiguous":
            amb.add(rec["record_id"])
    docs = []
    for source in ("swecris", "cordis", "reporter"):
        for r in census_common.load_census(source):
            if r["record_id"] in amb:
                docs.append({
                    "record_id": r["record_id"],
                    "amount": float(r.get("amount_eur") or 0.0),
                    "text": ((r.get("title") or "") + " "
                             + (r.get("abstract") or "")).lower(),
                })
    return docs


def main() -> int:
    lexicon = json.loads((clf.KEYWORDS_JSON).read_text(encoding="utf-8"))
    thresholds = lexicon["meta"]["thresholds"]
    proxy = getattr(vk, "PROXY_LABEL", {})
    rows = atlas_rows()
    experts = load_experts()
    census = ambiguous_census()
    print(f"atlas rows {len(rows)} | experts {len(experts)} | "
          f"ambiguous census {len(census)}")

    candidates = list(csv.DictReader(
        CANDIDATES.open(encoding="utf-8-sig")))
    out = []
    for cand in candidates:
        term = cand["term"]
        category = cand["category"]
        lang = cand.get("lang") or "en"
        pattern = vk.compile_term(term)
        th = thresholds[lang]
        by_cat = Counter(r["llm_category"] for r in rows
                         if pattern.search(r["text"]))
        hits = sum(by_cat.values())
        proxy_label = proxy.get(category, category)
        prec_llm = round(by_cat[proxy_label] / hits, 3) if hits else 0.0
        gate1 = hits >= th["min_hits"] and prec_llm >= th["min_precision"]

        exp_hits, exp_match = 0, 0
        for r in rows:
            if pattern.search(r["text"]) and r["record_id"] in experts:
                exp_hits += 1
                exp_match += experts[r["record_id"]] == category
        prec_exp = round(exp_match / exp_hits, 3) if exp_hits else 0.0
        if exp_hits < 3:
            gate2 = False
        else:
            gate2 = prec_exp >= 0.60

        amb_hits, amb_eur = 0, 0.0
        for d in census:
            if pattern.search(d["text"]):
                amb_hits += 1
                amb_eur += d["amount"]

        is_trap = cand.get("is_trap") == "True"
        if gate1 and gate2 and is_trap:
            decision = "conditional_candidate"
        elif gate1 and gate2:
            decision = "admit"
        elif gate1 and exp_hits < 3:
            decision = "provisional"
        elif gate1:
            decision = "reject_gate2"
        elif gate2:
            decision = "reject_gate1"
        else:
            decision = "reject_both"

        out.append({
            "category": category, "term": term, "lang": lang,
            "is_trap": is_trap, "atlas_hits": hits,
            "prec_llm_proxy": prec_llm, "expert_hits": exp_hits,
            "prec_expert": prec_exp, "gate1": gate1, "gate2": gate2,
            "census_ambiguous_hits": amb_hits,
            "census_ambiguous_eur_m": round(amb_eur / 1e6, 2),
            "decision": decision, "example_record_id": cand["example_record_id"],
            "context": cand["context"],
        })

    order = {"admit": 0, "conditional_candidate": 1, "provisional": 2,
             "reject_gate1": 3, "reject_gate2": 4, "reject_both": 5}
    out.sort(key=lambda r: (order[r["decision"]], r["category"], -r["prec_expert"]))

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)

    decisions = Counter(r["decision"] for r in out)
    print(f"\ndecisions: {dict(decisions)}")
    for decision in ("admit", "conditional_candidate", "provisional"):
        picks = [r for r in out if r["decision"] == decision]
        if not picks:
            continue
        print(f"\n=== {decision} ({len(picks)})")
        for r in picks:
            print(f"  {r['category']:22s} {r['term']!r:38s} "
                  f"atlas={r['atlas_hits']:3d}/{r['prec_llm_proxy']:.2f} "
                  f"expert={r['expert_hits']:3d}/{r['prec_expert']:.2f} "
                  f"census_amb={r['census_ambiguous_hits']:3d} "
                  f"EUR={r['census_ambiguous_eur_m']:6.1f}M")
    print(f"\nwrote {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
