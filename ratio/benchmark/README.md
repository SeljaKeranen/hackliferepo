# Human benchmark (30-record grant set)

Tooling for the challenge's "small human-reviewed sample": 30 grants from the
Aging Funding Atlas (`data/Track3_C2/benchmark/benchmark_30.csv`, 20 RePORTER
/ 5 CORDIS / 5 SweCRIS), annotated blind against the current taxonomy.

## Workflow

The ratio page links here: `http://localhost:8010/ratio/` has a
"Human benchmark" entry in the header and a status line in the caveats
section that reads `report.json` when it exists.

1. Build the blind sheet (no model labels in the page):

   ```sh
   python3 ratio/benchmark.py sheet     # writes ratio/benchmark/sheet.html
   ```

2. Open `sheet.html` in a browser (file:// works; answers are kept in
   localStorage). One annotator per browser, or one browser profile per
   annotator. Pick one category per grant, set confidence, add notes, then
   **Export JSONL**. The download is `human_labels_<name>.jsonl`.
3. Put the exported files in this directory (do not edit them; they are the
   evidence) and score:

   ```sh
   python3 ratio/benchmark.py score --labels ratio/benchmark/human_labels_*.jsonl
   ```

   Writes `report.md` + `report.json`: adjudicated-vs-human and
   rules-vs-human agreement, per-class precision/recall/F1, confusion,
   Cohen's kappa when there are two annotators, and every disagreement with
   the record id for follow-up. Exit 1 when agreement is below the 0.85 bar.

## Rules

- The key (`benchmark_30_key.json`, record ids and old model labels) is
  hidden from annotators; the sheet contains only input_id, source, year,
  title and abstract.
- The frozen population digest is printed in the sheet header; score rejects
  unknown input_ids.
- Human labels are append-only evidence: never overwrite an exported file,
  add a new annotator file instead.
- Vocabulary: the current taxonomy (fundamental ageing biology,
  interventions, age-related disease, care, ageing societies and
  populations, plus ambiguous and not_relevant). The older
  `ANNOTATION_GUIDE.md` in the benchmark data directory predates the
  `social_population_aging` and `not_relevant` categories; the sheet carries
  the up-to-date rubric.
- Self-check: `python3 ratio/benchmark.py --self-test`.

## Ledger of results

Record each scored run here (date, annotators, agreement, headline):

| date | annotators | adjudicated vs human | rules vs human | pass 0.85 |
| --- | --- | --- | --- | --- |
| (none yet) | | | | |
