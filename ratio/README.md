# The Funding-Gap Ratio (v1, census corpus)

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

`build.py` reads the committed census under `ratio/data/` by default
(`--corpus atlas` reruns the old 2,944-record sample instead). To re-fetch
the census from the live sources — not needed to build or view anything:

```sh
python3 ratio/data/fetch_swecris.py    # Swecris API, public test token (~1 min)
python3 ratio/data/fetch_reporter.py   # NIH RePORTER API v2, paged (~15 min)
python3 ratio/data/fetch_cordis.py     # CORDIS bulk dumps (~120 MB download)
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
python3 ratio/build.py --check           # committed outputs match the current code (exit 1 on drift)
python3 classifier/validate_keywords.py  # lexicon integrity (must pass)
```

The committed outputs are stamped with a content hash of their inputs
(`method.inputs_hash` over `classify.py` + `build.py` + `keywords.json`,
shown in the page footer). `--check` recomputes it and fails when any of
those files changed after the last build, so a change to the classifier or
lexicon without re-running `python3 ratio/build.py` is caught mechanically,
not by a reader noticing a stale footer.

## Method: the funnel

Every number on the page traces back through this funnel, and every grant
behind every bar is one click away (title, funder, amount, dated source URL,
matched keywords, rule reason).

1. **Net.** The corpus is a census of the Aging Funding Atlas's per-source
   search nets (METHODOLOGY.md in commit `2e59b27`), re-fetched 2026-09-12
   with **no cap and no sampling**: 13,224 grant records (SweCRIS 870,
   CORDIS 239, NIH RePORTER 12,115), committed as
   `ratio/data/census_*.jsonl.gz` with per-source funnel numbers in
   [`data/funnel.json`](data/funnel.json). The fetch scripts
   (`ratio/data/fetch_*.py`, stdlib only) are re-runnable and record
   retrieval dates; [`data/CROSSCHECK.md`](data/CROSSCHECK.md) compares the
   census against published funder totals and documents the remaining
   coverage gaps. 97.6% of records carry an EUR-normalised amount (fixed
   ECB 2026-09-11 rates); the 321 without one count in grant counts but
   not in EUR sums. The earlier atlas corpus (2,944 sampled records)
   remains available via `python3 ratio/build.py --corpus atlas`.
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
exact `compile_term` the lexicon stats were computed with — over lowercased
title + abstract (census records; the atlas sample only carried a short
model-chosen `llm_quote` as evidence text).

### v1 result (census corpus, rules only)

| region | ratio | ambiguous share | grants |
| --- | --- | --- | --- |
| SE | 18.6% | 30.7% | 870 |
| EU | 64.0% | 60.8% | 239 |
| US | 42.8% | 18.7% | 12,115 |

Label distribution: 4,997 fundamental_aging, 4,802 age_related_disease,
2,866 ambiguous, 226 not_relevant, 169 care, 113 social_population_aging,
51 intervention.

Against the atlas sample (`--corpus atlas`: SE 20.1%, EU 16.4%, US 39.2%),
re-classifying the census records that are in the sample isolates what
changed: the US move to 42.8% is a pure sampling correction (the sample
subset scores 39.2% on identical census text), the SE numbers barely move,
and the EU jump comes from the net itself — the bulk-dump filter drops 323
search-index noise records the atlas had pulled in (see
[`data/CROSSCHECK.md`](data/CROSSCHECK.md)), and full objectives replace
one-line quotes. The EU ratio stands on a 60.8% ambiguous share and
€163.6M of classified money — read it as weak evidence.

## What v1 is and is not

- **Rules only.** No model calls; deterministic and reproducible from the
  committed lexicon. The one-line reason and matched keywords per record are
  in `output/labels.jsonl`.
- **A census of the nets, not of any budget.** The corpus is the complete
  result set of the atlas's ageing search nets, so sampling error is gone —
  but net recall still bounds coverage (a measured example: a
  dementia-caregiving grant with no ageing vocabulary is invisible,
  [`data/CROSSCHECK.md`](data/CROSSCHECK.md)). Collection nets differ per
  source, so compare shapes across regions, not absolute budgets, and do
  not read any number as a funder's total spending. Known out-of-scope:
  private foundations (Wallenberg, disease charities), non-NIH US federal
  funders, EU member-state national funders.
- **Labels not yet human-verified.** On the atlas sample, agreement with
  the atlas's own unverified LLM labels was 58.3% on the four categories
  both schemes share (the atlas's lost keyword rules scored 61.8% against
  the same labels). That figure is context, not a target: the LLM labels
  predate the `social_population_aging` category and the
  `not_relevant`/`ambiguous` split, cover none of the census-only records,
  and are themselves unverified.
- **Benchmark pending.** The challenge bar is ≥85% agreement with human
  labels on a small labelled set, with ambiguous flagged rather than forced.
  The 30-record human benchmark (`data/Track3_C2/benchmark/benchmark_30.csv`
  in commit `2e59b27`) is still unlabelled; `labels.jsonl` keeps every
  record's label, reason, matched keywords and confidence margin so the
  comparison can run the moment labels exist.
- **The `intervention` label is rare and its keyword net is the weakest.**
  The lexicon's own validation gives `intervention` the lowest coverage
  (0.414), and only 51 of 13,224 records get the label here. What that
  does to the numerator cannot be established from this evidence alone:
  intervention grants missed by the keywords may land in
  `fundamental_aging` (still numerator), in `ambiguous`, or elsewhere. The
  human benchmark is the way to find out.

## Files

- [`classify.py`](classify.py) — the deterministic rule classifier (rubric
  steps 0–3). Reason strings and the NONBIO idea align with Jan's
  `funding/classify.py` (`codex/ageing-funding-gap`); the lexicon, anchors,
  precisions and trap handling come from `classifier/keywords.json`.
- [`build.py`](build.py) — corpus loading (census or atlas), classification,
  aggregation.
- [`data/census_*.jsonl.gz`](data/) — the committed census, one gzipped
  JSONL per source with title, abstract, funder, year, native + EUR
  amounts, matched net phrases and retrieval date per record.
  [`data/funnel.json`](data/funnel.json) holds the per-source
  fetched → net-matched → kept numbers plus dump URLs and checksums;
  [`data/fetch_*.py`](data/) re-fetch it;
  [`data/CROSSCHECK.md`](data/CROSSCHECK.md) is the external completeness
  evidence. Licences: NIH RePORTER US-government public domain, CORDIS
  CC BY 4.0 (© European Union), Swecris openly accessible per VR
  (attribute Swecris); details per source in the fetch script headers.
- [`output/labels.jsonl`](output/labels.jsonl) — one line per record:
  label, matched keywords, anchor terms, reason, confidence margin,
  provenance (funder, EUR, year, source URL), and the atlas `llm_category`
  for comparison.
- [`output/aggregates.json`](output/aggregates.json) — regions, funders,
  totals, method metadata and caveats (what the page renders).
- [`index.html`](index.html) — the 3-second visual. Decoupled from the eval
  loop and the map; it only reads `ratio/output/`.
