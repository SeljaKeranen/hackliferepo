# The Funding-Gap Ratio (v1)

Per funding jurisdiction, how much public research funding targets **slowing
ageing** (fundamental ageing biology + interventions against ageing) as a
share of the whole ageing-research budget:

```
ratio = EUR(fundamental_aging + intervention)
        / EUR(fundamental_aging + intervention + age_related_disease
              + care + social_population_aging)
```

`not_relevant` records are excluded and counted separately; `ambiguous`
records sit in neither numerator nor denominator and are reported beside the
ratio as an explicit honesty band. `social_population_aging` counts only in
the denominator. This is the ratio hookup specified in
[`classifier/KEYWORDS.md`](../classifier/KEYWORDS.md).

## Run it

From the repository root:

```sh
python3 ratio/build.py            # reclassify + rebuild ratio/output/ (stdlib only)
python3 -m http.server 8010       # then open http://localhost:8010/ratio/
```

The page also works served from `ratio/` itself (`cd ratio && python3 -m
http.server`). It fetches `output/aggregates.json` and `output/labels.jsonl`,
both committed, so viewing needs no pipeline run — only an HTTP server (the
`file://` protocol blocks `fetch`). No install, no build step, no network
beyond localhost, no model calls.

Checks:

```sh
python3 ratio/classify.py --self-test    # worked examples from KEYWORDS.md + rubric branches
python3 ratio/build.py --self-test       # aggregation math unit checks
python3 classifier/validate_keywords.py  # lexicon integrity (must pass)
```

The committed outputs record the repo commit they were built at
(`method.built_at_commit`, shown in the page footer). Any change to
`ratio/classify.py` or `classifier/keywords.json` requires re-running
`python3 ratio/build.py`, or the page serves numbers from the older rules.

## Method: the funnel

Every number on the page traces back through this funnel, and every grant
behind every bar is one click away (title, funder, amount, dated source URL,
matched keywords, rule reason).

1. **Net.** The corpus is teammate Max's Aging Funding Atlas: 2,944 grant
   records collected through an ageing-related search net (SweCRIS 855,
   CORDIS 558, NIH RePORTER 1,531), committed in `2e59b27` and live at
   `data/Track3_C2/output/`. 98.7% carry an EUR-normalised amount; the 39
   records without one count in grant counts but not in EUR sums.
2. **Relevance gate (step 0).** Exclusion markers from the lexicon
   (`battery`, `li-ion`, `aging infrastructure`) plus a NONBIO list —
   engineering and agriculture vocabulary aligned with Jan's
   `funding/classify.py` on `codex/ageing-funding-gap` and the trap classes
   named in KEYWORDS.md — route obvious off-topic records to `not_relevant`,
   guarded so they never fire on a record with biomedical context or any
   lexicon keyword match. A record with no ageing anchor and no keyword
   match is also `not_relevant` (relevance not established).
3. **Ageing anchor.** Keywords flagged `requires_ageing_anchor` (the whole
   `social_population_aging` category and several `care` terms) count only
   when a `meta.broad_net` term or an explicit older-adults reference is
   present in the record, per the lexicon's co-occurrence rule.
4. **Category.** Precision-weighted keyword voting: every kept (non-trap)
   lexicon keyword that matches votes for its category with its measured
   precision as the weight. The mechanism-versus-intervention rubric rule
   decides only the `fundamental_aging`/`intervention` boundary:
   mechanism-study language keeps a record in `fundamental_aging` however
   prominently it names an intervention, and the `intervention` label needs
   explicit developing/testing language. Every other contest with a winning
   margin under 0.3 is `ambiguous` — never forced, including near-ties
   between `intervention` and a non-numerator category.
5. **Ratio.** Aggregate EUR per region (SE = SweCRIS funders, EU = European
   Commission via CORDIS, US = NIH via RePORTER) and per funder, then the
   formula above.

Matching semantics are imported from `classifier/validate_keywords.py` — the
exact `compile_term` the lexicon stats were computed with — over the same
text (lowercased title + `llm_quote`).

### v1 result (atlas corpus, rules only)

| region | ratio | ambiguous share | grants |
| --- | --- | --- | --- |
| SE | 20.7% | 46.3% | 855 |
| EU | 17.7% | 36.3% | 558 |
| US | 39.2% | 26.5% | 1,531 |

Label distribution: 770 ambiguous, 754 not_relevant, 711 age_related_disease,
579 fundamental_aging, 81 care, 31 social_population_aging, 18 intervention.

## What v1 is and is not

- **Rules only.** No model calls; deterministic and reproducible from the
  committed lexicon. The one-line reason and matched keywords per record are
  in `output/labels.jsonl`.
- **An atlas sample, not a census.** The corpus is an ageing-filtered sample
  per funder with different collection nets per source. Compare shapes across
  regions, not absolute budgets, and do not read any number as a funder's
  total spending.
- **Labels not yet human-verified.** Agreement with the atlas's own
  unverified LLM labels is 58.3% on the four categories both schemes share
  (the atlas's lost keyword rules scored 61.8% against the same labels).
  That figure is context, not a target: the LLM labels predate the
  `social_population_aging` category and the `not_relevant`/`ambiguous`
  split, and are themselves unverified.
- **Benchmark pending.** The challenge bar is ≥85% agreement with human
  labels on a small labelled set, with ambiguous flagged rather than forced.
  The 30-record human benchmark (`data/Track3_C2/benchmark/benchmark_30.csv`
  in commit `2e59b27`) is still unlabelled; `labels.jsonl` keeps every
  record's label, reason, matched keywords and confidence margin so the
  comparison can run the moment labels exist.
- **The `intervention` label is rare and its keyword net is the weakest.**
  The lexicon's own validation gives `intervention` the lowest coverage
  (0.414), and only 18 records get the label here. What that does to the
  numerator cannot be established from this evidence alone: intervention
  grants missed by the keywords may land in `fundamental_aging` (still
  numerator), in `ambiguous`, or elsewhere. The human benchmark is the way
  to find out.

## Files

- [`classify.py`](classify.py) — the deterministic rule classifier (rubric
  steps 0–3). Reason strings and the NONBIO idea align with Jan's
  `funding/classify.py` (`codex/ageing-funding-gap`); the lexicon, anchors,
  precisions and trap handling come from `classifier/keywords.json`.
- [`build.py`](build.py) — corpus recovery, classification, aggregation.
- [`output/labels.jsonl`](output/labels.jsonl) — one line per record:
  label, matched keywords, anchor terms, reason, confidence margin,
  provenance (funder, EUR, year, source URL), and the atlas `llm_category`
  for comparison.
- [`output/aggregates.json`](output/aggregates.json) — regions, funders,
  totals, method metadata and caveats (what the page renders).
- [`index.html`](index.html) — the 3-second visual. Decoupled from the eval
  loop and the map; it only reads `ratio/output/`.
