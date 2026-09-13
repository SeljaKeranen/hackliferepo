# UKHRA benchmark

Scores a classifier against trained human coders, using the UK Health
Research Analysis 2022 as the answer key. Full write-up, results and
caveats: [`docs/ukhra-validation.md`](../docs/ukhra-validation.md).

```sh
curl -sL -o /tmp/UKHRA2022.xlsx \
  https://hrcsonline.net/wp-content/uploads/2024/01/UKHRA2022_HRCS_public_dataset_v1-2_30Jan2024.xlsx
python3 -m ukhra.benchmark --xlsx /tmp/UKHRA2022.xlsx --out ukhra/results.json
python3 -m ukhra.negative_control --xlsx /tmp/UKHRA2022.xlsx \
  --out ukhra/negative_control_results.json
python3 -m unittest discover -s ukhra -t . -p "test_*.py"   # no download needed
```

The dataset is not committed (`AGENTS.md`). The two `*results.json` files are
the committed outputs of those runs.

## Two different jobs

`benchmark.py` **measures correctness**: it scores a cancer screen against
human cancer coding, where there is ground truth.

`negative_control.py` **finds leaks**: it runs `ratio/classify.py` over the
same corpus, which is general health research with no ageing focus, so any
confident ageing label is a candidate relevance-gate leak. It makes no
accuracy claim — HRCS has no ageing category to be right against. It found 51
ageing labels on Infection, Reproductive Health, Oral/GI, Renal and Congenital
awards, including `rapamycin` firing on a malaria study.

## Scoring a different classifier

The shipped baseline is a keyword cancer screen (`cancer_terms.py`), there
to establish a number worth beating: **F1 0.803** against 11,664 human-coded
awards. To score something else, pass any function that takes text and
returns a truthy value for cancer-relevant:

```sh
python3 -m ukhra.benchmark --xlsx /tmp/UKHRA2022.xlsx --classifier mymodule:my_function
```

## What it can and cannot check

UKHRA codes each award by Health Category and Research Activity, so it can
score **cancer** classification, and it gives an empirical reference point
for a **prevention versus consequences** split.

It has **no ageing category**. Nothing here validates ageing classification.
The supported claim is narrower: a method that reproduces human coding where
ground truth exists is more credible where it doesn't.

## Files

- `benchmark.py` — loader, cancer scoring, CLI
- `negative_control.py` — runs the ageing classifier over the corpus to surface gate leaks
- `cancer_terms.py` — the baseline screen being scored
- `xlsx.py` — minimal stdlib XLSX reader (openpyxl is unavailable; repo is stdlib-only)
- `test_benchmark.py`, `test_negative_control.py` — tests, no download needed
- `results.json`, `negative_control_results.json` — committed outputs
