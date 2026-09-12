# How the classifier works

The funding-gap ratio classifies every grant in the 13,224-record census into
one of five substantive categories (plus `ambiguous` and `not_relevant`) and
sums money per region. The label path has two stages: a deterministic rules
engine, and a model adjudication for whatever the rules leave ambiguous. The
page (`ratio/index.html`) can show either scenario.

## Components

| piece | file | job |
| --- | --- | --- |
| Lexicon | `classifier/keywords.json` | per-category keywords with measured precision, trap terms, broad search net, exclusion markers, conditional voters |
| Validator | `classifier/validate_keywords.py` | recomputes every lexicon stat from the atlas and enforces thresholds |
| Rules engine | `ratio/classify.py` | applies the lexicon to title + abstract and returns a label with evidence |
| Adjudicator | `ratio/adjudicate.py` | resolves remaining ambiguous records via a chat-completions API, one verbatim quote per record |
| Quote checker | `ratio/verify_adjudication.py` | verifies every adjudication quote against the record text |
| Aggregators | `ratio/build.py`, `ratio/build_adjudicated.py` | sum EUR per region/category and compute the ratio; write the page artifacts |
| Page | `ratio/index.html` | renders rules mode or `?scenario=adjudicated` |

## Rule engine, step by step

```
title + abstract (lowercased)
 |
 +- step 0  relevance gate
 |    plant/agriculture/ecology arm first: senescence, lifespan and longevity
 |    are everyday botany, forestry, livestock and ecology vocabulary, so a
 |    plant/ecology hit routes to not_relevant unless a human or biomedical
 |    marker (or an explicit older-adults reference) blocks it.
 |    Then, when no category keyword matched, NONBIO materials/engineering
 |    terms (battery, li-ion, polymer, bridges, pipes, nuclear power, clouds,
 |    soot, honeypots, ...) route to not_relevant.
 |    Two guards keep the gate honest: a battery-context override waives the
 |    biomedical "cell" guard, "mouse" counts only as mouse model(s), and
 |    "cohort" only as cohort study/studies.
 |    No keyword and no ageing anchor -> not_relevant.
 |    Anchor but no keyword -> ambiguous.
 |
 +- step 1  precision-weighted voting
 |    every kept keyword that matches votes for its category with its
 |    measured precision as weight. Terms flagged requires_ageing_anchor
 |    (the whole social category and several care terms) count only when a
 |    meta.broad_net term or an older-adults reference appears.
 |    Conditional voters (loneliness 0.500, participation 0.444,
 |    social isolation 0.400, older age 0.400, housing 0.842,
 |    social inequalities 1.000 - all anchor-gated; senolytic* 0.421 -
 |    requires explicit developing/testing language) vote only under their
 |    condition and are marked "(conditional)" in the output.
 |
 +- step 2  mechanism vs intervention (the fundamental/intervention boundary)
 |    entered when those two are the top contenders or intervention stands
 |    alone: mechanism cues -> fundamental_aging; explicit develop/test/drug
 |    cues -> intervention; neither -> fundamental_aging when contested,
 |    ambiguous when intervention stands alone.
 |
 +- step 3  near-tie decision
      decisive when margin >= TIE_MARGIN (0.30), or when the relative margin
      >= REL_MARGIN (0.10) and the evidence floor holds (EVIDENCE_FLOOR 0.60:
      one term at or above it, or two matching terms with at least one
      unconditional keyword; fundamental_aging also qualifies with explicit
      mechanism language).
      Three boundary rules fire before the floor:
        1. mechanism language decides fundamental_aging vs age_related_disease
        2. service-delivery cues vs age-and-society cues decide care vs
           social_population_aging
        3. a disease-targeted vaccine or therapy in an older population is
           age_related_disease
      Anything still undecided stays ambiguous - never forced.
```

Output per record (`ratio/output/labels.jsonl`): `label`,
`matched_keywords`, `anchor_terms`, a one-line `reason`, and a `confidence`
margin. Thresholds and both tuning constants are stamped into
`aggregates.json method`.

## Where the lexicon numbers come from

- Keywords are validated against the 2,944-record atlas with hard thresholds:
  English >= 3 hits and precision >= 0.60, Swedish >= 1 hit and >= 0.60,
  `low_evidence: true` under 5 hits; spelling variants skip only the hit
  floor. Precision is the share of a keyword's hits whose atlas label equals
  the keyword's category.
- `social_population_aging` postdates the atlas labels, so its precision and
  coverage are measured against the `ambiguous` proxy (`PROXY_LABEL` in the
  validator); every admitted term there was additionally spot-checked.
- Trap terms (bare `aging`, `longevity`, `senolytic*`, `chemotherapy`,
  `disease`, `app`, `tert`, ...) are kept as negative filters and never vote.
- An enrichment pass mines candidates from expert-labelled blind spots
  (`ratio/mine_candidates.py`) and admits only terms that clear both the
  validator thresholds and expert-label precision >= 0.60
  (`ratio/validate_candidates.py`).

## Model adjudication (Phase 2)

`ratio/adjudicate.py` sends each remaining ambiguous record to
`deepseek-flash` with the same rubric, temperature 0, and asks for JSON
`{label, quote, confidence, reason}`. The quote must be a verbatim substring
of the record (`verify_adjudication.py`); responses are cached per record
under `data/llm_cache/` and runs are resumable. 1,314 adjudications were
completed with 1,314/1,314 quotes verified and no failures; a 29-record
overlap with an independent in-session pass agreed on 24 (83%).

## Aggregation and the ratio

`build.py` maps sources to funding jurisdictions (SweCRIS -> SE, CORDIS ->
EU, NIH RePORTER -> US) and sums EUR per category, funder and region:

```
ratio = EUR(fundamental_aging + intervention)
        / EUR(fundamental_aging + intervention + age_related_disease
              + care + social_population_aging)
```

`not_relevant` is excluded entirely; `ambiguous` is excluded from both sides
and reported beside the ratio as an explicit honesty band.
`build_adjudicated.py` redoes the same with the model labels and writes the
second page scenario; the rules outputs are never overwritten.

## Current numbers (2026-09-12)

| check | result |
| --- | --- |
| Lexicon validator | exit 0, all stats reproduce |
| `classify.py --self-test` | 23/23 worked cases |
| `build.py --self-test` | 13/13 aggregation checks; `--check` fresh |
| Rules vs expert labels | 53.3% -> 56.7% agreement; ambiguous 770 -> 644 |
| Census ambiguous share | SE 19.8%, EU 53.0%, US 8.4% (rules); ~0% adjudicated |
| Ratio | rules SE 0.228 / EU 0.648 / US 0.495; adjudicated 0.240 / 0.684 / 0.500 |
| Human benchmark | 30-record set built (`ratio/benchmark/sheet.html`), labels pending |

## Reproduce

```sh
python3 classifier/validate_keywords.py        # lexicon integrity
python3 ratio/classify.py --self-test          # rubric cases
python3 ratio/build.py                         # rules artifacts + --check
python3 ratio/eval_rules.py                    # agreement vs expert labels
python3 ratio/build_adjudicated.py             # adjudicated scenario
python3 ratio/benchmark.py --self-test         # benchmark tooling
```

## Adding or changing keywords

1. Mine candidates (`ratio/mine_candidates.py`) or add them manually.
2. Validate (`python3 ratio/validate_candidates.py` semantics; or insert and
   run `validate_keywords.py --update`).
3. Update `classifier/KEYWORDS.md`, rebuild `ratio/build.py`, and re-run
   `eval_rules.py` to confirm no category loses agreement.
4. Update this file and `ratio/README.md` if behaviour changed.
