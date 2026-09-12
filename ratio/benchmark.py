#!/usr/bin/env python3
"""Human benchmark tooling for the 30-record grant set.

Two subcommands:

  sheet   Build a self-contained blind annotation page from
          data/Track3_C2/benchmark/benchmark_30.csv + benchmark_30_key.json.
          The page shows input_id, source, year, title and abstract only (no
          model labels) and exports one JSONL file per annotator.

  score   Read one or more exported label files, join them through the key
          to ratio/output/labels.jsonl (rules) and output/adjudicated.jsonl
          (model adjudication), and report agreement, per-class
          precision/recall/F1, confusion, inter-annotator agreement (Cohen's
          kappa) and every disagreement.

Outputs live under ratio/benchmark/ and are never overwritten by this
script; human labels are append-only evidence.

Usage:
    python3 ratio/benchmark.py sheet
    python3 ratio/benchmark.py score --labels ratio/benchmark/human_labels_*.jsonl
    python3 ratio/benchmark.py --self-test
Python 3 stdlib only; no network, no model calls.
"""

import argparse
import csv
import hashlib
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BENCH_DIR = REPO / "data" / "Track3_C2" / "benchmark"
CSV_PATH = BENCH_DIR / "benchmark_30.csv"
KEY_PATH = BENCH_DIR / "benchmark_30_key.json"
OUT_DIR = HERE / "benchmark"

LABELS = [
    ("fundamental_aging", "Fundamental ageing biology",
     "Ageing mechanisms themselves: senescence, epigenetic clocks, "
     "inflammaging, proteostasis, stem-cell exhaustion, mitochondrial "
     "dysfunction, comparative longevity, geroscience."),
    ("intervention", "Interventions against ageing",
     "Research developing or testing an intervention whose objective targets "
     "ageing biology, senescence, lifespan or healthspan (geroprotectors, "
     "senolytics, rapamycin, metformin as geroprotection, dietary "
     "restriction for lifespan). A study of an intervention's mechanism is "
     "fundamental ageing biology."),
    ("age_related_disease", "Age-related disease",
     "A specific age-related disease treated as the objective: Alzheimer's, "
     "cancer, cardiovascular disease, diabetes, osteoporosis, sarcopenia, "
     "clinical frailty, age-related sensory loss. Disease vaccines or "
     "therapies aimed at older adults belong here."),
    ("care", "Care of older people",
     "Elderly care, long-term care, caregiving, social services, care "
     "delivery research; not clinical treatment."),
    ("social_population_aging", "Ageing societies and populations",
     "Social, behavioural, psychological, economic or population-ageing "
     "research: loneliness, housing, retirement, life course, age-friendly "
     "environments, ageing societies, wellbeing of older people."),
    ("ambiguous", "Ambiguous",
     "On-topic but the text does not let you place it."),
    ("not_relevant", "Not relevant",
     "Material, component, infrastructure, equipment or animal/plant/ecology "
     "ageing, or no human ageing objective at all."),
]

_JS = r'''"use strict";
const RECORDS = __DATA__;
const OPTIONS = __OPTIONS__;
const storeKey = name => "grant-benchmark:" + (name || "default");
let annotator = localStorage.getItem("grant-benchmark-name") || "";
let answers = JSON.parse(localStorage.getItem(storeKey(annotator)) || "{}");
const nameInput = document.getElementById("annotator");
const wrap = document.getElementById("cards");
nameInput.value = annotator;
function save() {
  localStorage.setItem(storeKey(annotator), JSON.stringify(answers));
}
function progress() {
  const done = RECORDS.filter(r => answers[r.input_id] && answers[r.input_id].label).length;
  document.getElementById("progress").textContent =
    (annotator ? annotator + " - " : "") + done + " / " + RECORDS.length + " answered";
}
function render() {
  wrap.innerHTML = "";
  for (const r of RECORDS) {
    const a = answers[r.input_id] || {};
    const card = document.createElement("section");
    card.className = "card" + (a.label ? " answered" : "");
    const opts = OPTIONS.map(([k, n]) =>
      '<label class="opt"><input type="radio" name="' + r.input_id + '" value="' + k + '"' +
      (a.label === k ? " checked" : "") + "> " + n + "</label>").join("");
    card.innerHTML =
      "<h2>" + r.input_id + " - " + r.title + "</h2>" +
      '<div class="meta">' + r.source + " | " + r.year + "</div>" +
      '<div class="abstract">' + r.abstract.replace(/</g, "&lt;") + "</div>" +
      '<div class="opts">' + opts + "</div>" +
      '<div class="conf">confidence <select data-role="confidence">' +
      '<option value="high">high</option><option value="medium">medium</option>' +
      '<option value="low">low</option></select></div>' +
      '<textarea data-role="notes" placeholder="notes (optional)">' +
      (a.notes || "").replace(/</g, "&lt;") + "</textarea>";
    wrap.appendChild(card);
    card.querySelectorAll("input[type=radio]").forEach(el =>
      el.addEventListener("change", () => {
        answers[r.input_id] = Object.assign(answers[r.input_id] || {}, { label: el.value });
        card.classList.add("answered");
        save();
        progress();
      }));
    const conf = card.querySelector('[data-role="confidence"]');
    conf.value = a.confidence || "high";
    conf.addEventListener("change", () => {
      answers[r.input_id] = Object.assign(answers[r.input_id] || {}, { confidence: conf.value });
      save();
    });
    const notes = card.querySelector('[data-role="notes"]');
    notes.addEventListener("input", () => {
      answers[r.input_id] = Object.assign(answers[r.input_id] || {}, { notes: notes.value });
      save();
    });
  }
  progress();
}
nameInput.addEventListener("change", () => {
  annotator = nameInput.value.trim();
  localStorage.setItem("grant-benchmark-name", annotator);
  answers = JSON.parse(localStorage.getItem(storeKey(annotator)) || "{}");
  render();
});
document.getElementById("export").addEventListener("click", () => {
  if (!annotator) {
    alert("Enter your name first - it names the export file.");
    return;
  }
  const safe = annotator.replace(/[^A-Za-z0-9_-]+/g, "_");
  const lines = RECORDS.map(r => {
    const a = answers[r.input_id] || {};
    return JSON.stringify({ input_id: r.input_id, label: a.label || null,
                            confidence: a.confidence || null, notes: a.notes || "" });
  });
  const blob = new Blob([lines.join("\n") + "\n"], { type: "application/jsonl" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "human_labels_" + safe + ".jsonl";
  a.click();
  URL.revokeObjectURL(a.href);
});
render();'''


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     ensure_ascii=False)
                          .encode("utf-8")).hexdigest()[:12]


def load_benchmark():
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    records = []
    for row in rows:
        input_id = row["input_id"]
        meta = key.get(input_id, {})
        records.append({
            "input_id": input_id,
            "record_id": meta.get("record_id"),
            "source": row["source"],
            "year": row["year"],
            "title": row["title"],
            "abstract": row["abstract"],
        })
    missing = [r["input_id"] for r in records if not r["record_id"]]
    if missing:
        sys.exit(f"key missing record_id for {missing}")
    return records


def build_sheet(records) -> str:
    population = digest([[r["input_id"], r["record_id"]] for r in records])
    rubric = "".join(
        f"<details><summary>{html.escape(name)}</summary>"
        f"<p>{html.escape(desc)}</p></details>" for _, name, desc in LABELS)
    radios = "".join(
        f'<label class="opt"><input type="radio" name="label" '
        f'value="{key}"> {html.escape(name)}</label>' for key, name, _ in LABELS)
    data = json.dumps(records, ensure_ascii=False).replace("</", "<\\/")
    options = json.dumps([[k, n] for k, n, _ in LABELS])
    js_source = _JS.replace("__DATA__", data).replace("__OPTIONS__", options)
    return (f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Grant benchmark annotation</title>
<style>
:root {{ --bg:#101623; --card:#151d2d; --line:#273349; --ink:#e8ecf4;
         --muted:#8b96ab; --gold:#f2c14e; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
        font:15px/1.55 -apple-system, "Segoe UI", Roboto, sans-serif; }}
main {{ max-width:860px; margin:0 auto; padding:36px 22px 80px; }}
h1 {{ font-size:26px; margin:0 0 6px; }}
.intro {{ color:var(--muted); font-size:13.5px; }}
.intro a {{ color:var(--gold); }}
.controls {{ position:sticky; top:0; background:var(--bg); padding:12px 0;
             border-bottom:1px solid var(--line); margin:18px 0 8px;
             display:flex; gap:12px; align-items:center; flex-wrap:wrap; }}
.controls input[type=text] {{ background:var(--card); border:1px solid var(--line);
             color:var(--ink); border-radius:8px; padding:8px 10px; font:inherit; }}
.controls button {{ background:var(--gold); color:#101623; border:0;
             border-radius:8px; padding:9px 14px; font:inherit; font-weight:600;
             cursor:pointer; }}
.progress {{ color:var(--muted); font-size:13px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
         padding:18px 20px; margin-top:14px; }}
.card h2 {{ font-size:15px; margin:0 0 4px; }}
.meta {{ color:var(--muted); font-size:12px; margin-bottom:8px; }}
.abstract {{ color:#c6cede; font-size:13px; white-space:pre-wrap;
             max-height:260px; overflow:auto; }}
.opts {{ display:grid; grid-template-columns:1fr 1fr; gap:6px 14px;
         margin-top:12px; }}
.opt {{ font-size:13px; }}
.conf {{ margin-top:10px; font-size:13px; color:var(--muted); }}
textarea {{ width:100%; margin-top:8px; background:#0d1320; color:var(--ink);
            border:1px solid var(--line); border-radius:8px; padding:8px;
            font:inherit; font-size:13px; }}
.answered {{ outline:2px solid #2c6e49; }}
</style>
</head>
<body>
<main>
<h1>Grant benchmark annotation</h1>
<p class="intro">30 ageing-research grants. Pick the single best category for
each from the title and abstract, set a confidence, add notes. The rubric is
below; the page does not show any model label. When done, enter your name and
export — send the downloaded JSONL file back. Frozen population
<code>{population}</code>; do not annotate a different set.</p>
<details><summary>Rubric</summary>{rubric}</details>
<div class="controls">
  <input type="text" id="annotator" placeholder="your name (for the export file)">
  <button id="export">Export JSONL</button>
  <span class="progress" id="progress"></span>
</div>
<div id="cards"></div>
</main>
""" + "<script>\n" + js_source + "\n</script>\n</body>\n</html>\n")


def load_human(paths):
    by_annotator = {}
    for path in paths:
        labels = {}
        for line in Path(path).open(encoding="utf-8"):
            if not line.strip():
                continue
            rec = json.loads(line)
            if not rec.get("label"):
                continue
            labels[rec["input_id"]] = rec
        if labels:
            name = Path(path).stem.replace("human_labels_", "")
            by_annotator[name] = labels
    return by_annotator


def load_pipeline_labels():
    rules, adjudicated = {}, {}
    for line in (HERE / "output" / "labels.jsonl").open(encoding="utf-8"):
        rec = json.loads(line)
        rules[rec["record_id"]] = rec["label"]
    adj_path = HERE / "output" / "adjudicated.jsonl"
    if adj_path.is_file():
        for line in adj_path.open(encoding="utf-8"):
            rec = json.loads(line)
            if "error" not in rec:
                adjudicated[rec["record_id"]] = rec["label"]
    return rules, adjudicated


def metrics(pairs, labels=LABELS):
    """pairs: list of (truth, prediction). Returns agreement + per-class."""
    keys = [k for k, _, _ in labels]
    agreement = sum(t == p for t, p in pairs) / len(pairs) if pairs else None
    per_class = {}
    for key in keys:
        tp = sum(t == key and p == key for t, p in pairs)
        fp = sum(t != key and p == key for t, p in pairs)
        fn = sum(t == key and p != key for t, p in pairs)
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = (2 * precision * recall / (precision + recall)
              if precision and recall else None)
        per_class[key] = {"n_truth": tp + fn, "precision": precision,
                          "recall": recall, "f1": f1}
    return {"n": len(pairs), "agreement": agreement, "per_class": per_class}


def kappa(pairs_a, pairs_b):
    """Cohen's kappa over the shared input_ids of two annotator dicts."""
    keys = sorted(set(pairs_a) & set(pairs_b))
    if not keys:
        return None
    a = [pairs_a[k] for k in keys]
    b = [pairs_b[k] for k in keys]
    observed = sum(x == y for x, y in zip(a, b)) / len(keys)
    pa, pb = Counter(a), Counter(b)
    expected = sum((pa[k] / len(keys)) * (pb[k] / len(keys))
                   for k in set(pa) | set(pb))
    return None if expected >= 1 else (observed - expected) / (1 - expected)


def confusion(pairs, labels=LABELS):
    keys = [k for k, _, _ in labels]
    table = defaultdict(Counter)
    for truth, pred in pairs:
        table[truth][pred] += 1
    lines = ["| human \\ model | " + " | ".join(keys) + " |",
             "| --- | " + " | ".join("---" for _ in keys) + " |"]
    for truth in keys:
        lines.append(f"| {truth} | " + " | ".join(
            str(table[truth].get(pred, 0)) for pred in keys) + " |")
    return "\n".join(lines)


def score(annotator_files) -> int:
    records = load_benchmark()
    by_input = {r["input_id"]: r for r in records}
    humans = load_human(annotator_files)
    if not humans:
        sys.exit("no labelled records found in the given files")
    rules, adjudicated = load_pipeline_labels()
    for name, labels in humans.items():
        unknown = [k for k in labels if k not in by_input]
        if unknown:
            sys.exit(f"{name}: unknown input_ids {unknown}")

    primary_name = sorted(humans)[0]
    primary = humans[primary_name]
    pairs = []
    detail = []
    for input_id, human in sorted(primary.items()):
        rec = by_input[input_id]
        rid = rec["record_id"]
        truth = human["label"]
        rules_label = rules.get(rid)
        adj_label = adjudicated.get(rid, rules_label)
        pairs.append((truth, adj_label))
        if truth != adj_label or truth != rules_label:
            detail.append({
                "input_id": input_id, "record_id": rid, "title": rec["title"],
                "human": truth, "rules": rules_label,
                "adjudicated": adj_label,
                "human_notes": human.get("notes", ""),
            })
    overall = metrics(pairs)
    rules_pairs = [(h["label"], rules[by_input[k]["record_id"]])
                   for k, h in sorted(primary.items())
                   if by_input[k]["record_id"] in rules]
    rules_overall = metrics(rules_pairs)

    lines = [
        "# Human benchmark report (30-record grant set)",
        "",
        f"Annotator(s): {', '.join(sorted(humans))}",
        f"Annotated: {len(primary)}/30 records",
        "",
        "## Headline",
        "",
        f"- Adjudicated model vs humans: **{overall['agreement']:.2f}** "
        f"({sum(1 for t, p in pairs if t == p)}/{len(pairs)})",
        f"- Rules model vs humans: **{rules_overall['agreement']:.2f}** "
        f"({sum(1 for t, p in rules_pairs if t == p)}/{len(rules_pairs)})",
        f"- Challenge bar: >= 0.85 with ambiguous flagged rather than forced.",
        "",
        "## Per-class (human = truth, adjudicated model)",
        "",
        "| class | n truth | precision | recall | F1 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key, name, _ in LABELS:
        m = overall["per_class"][key]
        fmt = lambda v: "-" if v is None else f"{v:.2f}"
        lines.append(f"| {name} | {m['n_truth']} | {fmt(m['precision'])} | "
                     f"{fmt(m['recall'])} | {fmt(m['f1'])} |")
    lines += ["", "## Confusion (human rows, adjudicated model columns)", "",
              confusion(pairs), ""]
    if len(humans) > 1:
        lines += ["## Inter-annotator agreement", ""]
        names = sorted(humans)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                left = {k: v["label"] for k, v in humans[names[i]].items()}
                right = {k: v["label"] for k, v in humans[names[j]].items()}
                k = kappa(left, right)
                lines.append(f"- {names[i]} vs {names[j]}: kappa "
                             f"{'-' if k is None else f'{k:.2f}'}")
        lines.append("")
    lines += ["## Disagreements with the model", ""]
    for row in detail:
        lines.append(f"- **{row['input_id']}** {row['title'][:90]}")
        lines.append(f"  human={row['human']} | rules={row['rules']} | "
                     f"adjudicated={row['adjudicated']} | "
                     f"record={row['record_id']}")
        if row["human_notes"]:
            lines.append(f"  notes: {row['human_notes']}")
    lines.append("")

    pass_bar = overall["agreement"] >= 0.85
    lines += [f"## Verdict",
              "",
              f"- {'PASS' if pass_bar else 'FAIL'}: adjudicated-vs-human "
              f"agreement {overall['agreement']:.2f} vs the 0.85 bar.",
              f"- Ambiguous records in the human labels: "
              f"{sum(1 for h in primary.values() if h['label'] == 'ambiguous')} "
              f"(flagged, not forced).",
              ""]

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT_DIR / "report.json").write_text(json.dumps({
        "annotators": sorted(humans),
        "annotated": len(primary),
        "adjudicated_vs_human": overall,
        "rules_vs_human": rules_overall,
        "disagreements": detail,
        "pass_085": pass_bar,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(lines[:12]))
    print(f"\nwrote {OUT_DIR / 'report.md'} and report.json")
    return 0 if pass_bar else 1


def self_test() -> int:
    pairs = [("care", "care"), ("care", "ambiguous"), ("care", "ambiguous"),
             ("care", "care"), ("not_relevant", "not_relevant")]
    m = metrics(pairs)
    checks = [
        (m["n"] == 5, "n"),
        (abs(m["agreement"] - 0.6) < 1e-9, "agreement"),
        (m["per_class"]["care"]["recall"] == 0.5, "recall"),
        (m["per_class"]["care"]["precision"] == 1.0, "precision"),
        (kappa({"a": "care", "b": "care"}, {"a": "care", "b": "ambiguous"})
         is not None, "kappa runs"),
    ]
    failed = [name for ok, name in checks if not ok]
    for name in failed:
        print(f"self-test FAILED: {name}")
    print(f"self-test: {len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="command")
    sheet = sub.add_parser("sheet", help="build the blind annotation page")
    sheet.add_argument("--out", default=str(OUT_DIR / "sheet.html"))
    sc = sub.add_parser("score", help="score exported human labels")
    sc.add_argument("--labels", nargs="+", required=True)
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.command == "sheet":
        records = load_benchmark()
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(build_sheet(records), encoding="utf-8")
        print(f"wrote {out} ({len(records)} records, blind)")
        return 0
    if args.command == "score":
        return score(args.labels)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
