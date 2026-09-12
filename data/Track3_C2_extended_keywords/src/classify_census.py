"""Label the three census pools with the classifier keyword lexicon."""

import csv
import gzip
import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from census_common import OUT, PROC, RESULT, ROOT

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SOURCES = ["reporter", "cordis", "swecris"]


def load_lexicon():
    spec = importlib.util.spec_from_file_location(
        "vk", ROOT / "classifier" / "validate_keywords.py")
    vk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vk)
    lex = json.loads((ROOT / "classifier" / "keywords.json").read_text(
        encoding="utf-8"))
    categories = {}
    for cat, block in lex["categories"].items():
        cat_anchor = bool(block.get("requires_ageing_anchor"))
        terms = []
        for lang in ("en", "sv"):
            for entry in block.get(lang, []):
                if vk.term_error(entry["term"]):
                    continue
                terms.append({"term": entry["term"],
                              "pattern": vk.compile_term(entry["term"]),
                              "precision": entry.get("precision", 0.0),
                              "anchor_required": bool(
                                  entry.get("requires_ageing_anchor",
                                            cat_anchor))})
        traps = [{"term": e["term"], "pattern": vk.compile_term(e["term"])}
                 for e in block.get("trap_terms", [])
                 if not vk.term_error(e["term"])]
        categories[cat] = {"terms": terms, "traps": traps}
    anchors = [vk.compile_term(e["term"])
               for e in lex["meta"]["broad_net"]["en"]
               if not vk.term_error(e["term"])]
    exclusions = [{"term": e["term"], "pattern": vk.compile_term(e["term"])}
                  for e in lex["meta"]["exclusion_markers"]
                  if not vk.term_error(e["term"])]
    return categories, anchors, exclusions


def label(record, categories, anchors, exclusions):
    text = (record.get("title", "") + " " + record.get("abstract", "")).lower()
    anchor_matched = any(p.search(text) for p in anchors)
    flags = [e["term"] for e in exclusions if e["pattern"].search(text)]
    matched, traps, scores = {}, {}, {}
    for cat, block in categories.items():
        precision = {t["term"]: t["precision"] for t in block["terms"]}
        matched[cat] = [t["term"] for t in block["terms"]
                        if t["pattern"].search(text)
                        and (not t["anchor_required"] or anchor_matched)]
        traps[cat] = [t["term"] for t in block["traps"]
                      if t["pattern"].search(text)]
        scores[cat] = round(
            sum(precision[t] for t in matched[cat]), 3)
    best = max(scores, key=scores.get)
    if flags and scores[best] == 0:
        category = "not_relevant"
    else:
        category = best if scores[best] > 0 else "ambiguous"
    return {"rule_category": category, "rule_score": scores[best],
            "anchor_matched": anchor_matched, "matched_terms": matched,
            "trap_terms": traps, "exclusion_flags": flags}


def main() -> int:
    categories, anchors, exclusions = load_lexicon()
    summary = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "sources": {}}
    for source in SOURCES:
        path = PROC / f"{source}_census.jsonl"
        if not path.is_file():
            path = PROC / f"{source}_census.jsonl.gz"
        if not path.is_file():
            print(f"skip missing census for {source}")
            continue
        opener = gzip.open if path.suffix == ".gz" else open
        counts = Counter()
        sums = Counter()
        anchor_count = flagged = 0
        term_freq = Counter()
        broad_only = Counter()
        rows = 0
        label_cols = ["record_id", "source", "source_id", "year", "country",
                      "funder", "amount", "currency", "amount_eur", "url",
                      "rule_category", "rule_score", "anchor_matched",
                      "matched_terms", "trap_terms", "exclusion_flags"]
        with opener(path, "rt", encoding="utf-8") as fin, \
                (PROC / f"{source}_census_labeled.jsonl").open(
                    "w", encoding="utf-8") as fout, \
                (RESULT / f"{source}_census_labels.csv").open(
                    "w", encoding="utf-8-sig", newline="") as fcsv:
            writer = csv.DictWriter(fcsv, fieldnames=label_cols)
            writer.writeheader()
            for line in fin:
                if not line.strip():
                    continue
                rec = json.loads(line)
                rec.update(label(rec, categories, anchors, exclusions))
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                rows += 1
                counts[rec["rule_category"]] += 1
                sums[rec["rule_category"]] += rec.get("amount_eur") or 0
                anchor_count += rec["anchor_matched"]
                flagged += bool(rec["exclusion_flags"])
                broad_only[bool(rec.get("extra", {}).get("broad_only"))] += 1
                for cat, hits in rec["matched_terms"].items():
                    for term in hits:
                        term_freq[f"{cat}/{term}"] += 1
                row = dict(rec)
                for key in ("matched_terms", "trap_terms", "exclusion_flags"):
                    row[key] = json.dumps(row[key], ensure_ascii=False)
                writer.writerow({c: row.get(c) for c in label_cols})
        summary["sources"][source] = {
            "records": rows,
            "category_counts": dict(counts.most_common()),
            "category_amount_eur": {k: round(v, 2) for k, v in
                                    sums.most_common()},
            "anchor_matched": anchor_count,
            "exclusion_flagged": flagged,
            "broad_only_records": broad_only.get(True, 0),
            "top_matched_terms": dict(term_freq.most_common(20)),
        }
        print(f"{source}: {rows} records | {dict(counts.most_common())}")
    (RESULT / "census_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote output/census_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
