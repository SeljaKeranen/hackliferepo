# Expert label layer for the funding-gap ratio

A senior-longevity-expert re-labelling of the full 2,944-grant corpus
(1,531 NIH RePORTER, 855 SweCRIS, 558 CORDIS; recovery commands in
`classifier/validate_keywords.py`). Every record was judged against the
verification-gate rubric of `classifier/KEYWORDS.md`, in gate order: step 0
relevance, ageing-anchor co-occurrence for anchored vocabulary, the five
substantive categories, the mechanism-vs-intervention boundary rule, and
`ambiguous` only for on-topic-but-undecidable records.

**File:** [`expert-labels.jsonl`](expert-labels.jsonl) — one line per record:
`{record_id, source, expert_label, confidence, reason, rule_path, judged_at}`.
Every reason quotes or cites the record's own text (title + `llm_quote`), so a
second-pass reviewer can audit each verdict against the record without other
context. `rule_path` names the gate step that decided the record:
`step0_relevance_gate` (1,034), `category_assignment` (1,632),
`anchor_cooccurrence` (87), `mechanism_vs_intervention` (128),
`ambiguous_undecidable` (63).

## Method

- Judged from the record's own text only: title + `llm_quote` (the quote an
  earlier pipeline extracted from the abstract; sometimes empty). Full
  abstracts were not available in the corpus.
- Blind to the rules-classifier label: judges saw only record_id, source,
  title and quote, so the comparison below is between two independent passes,
  not an edit of the rules output.
- 16 batches (grouped by source), each judged record-by-record by expert
  reading against the rubric — no keyword matching, no external APIs. A
  final cross-batch consistency pass by the lead reviewer harmonized the
  senolytic/geroprotector disease boundary and changed 4 verdicts
  (`cordis:765111`, `cordis:963988`, `cordis:799017`,
  `reporter:5R01AG067312-04`).
- Confidence: high 1,482, medium 1,066, low 396. Low-confidence verdicts are
  judgement calls the reason explains; they are the priority set for the
  second-pass review.
- Coverage: 2,944/2,944. Nothing was triaged out or left unjudged.

## Expert vs rules-classifier agreement

Rules labels are `ratio/output/labels.jsonl` from the funding-gap-ratio branch
(PR #10). Overall agreement 53.3% — low, but the disagreement is concentrated
where the rules classifier abstains rather than where it asserts:

| rules label | n | expert agrees | rate |
| --- | --- | --- | --- |
| social_population_aging | 31 | 28 | 0.90 |
| not_relevant | 754 | 628 | 0.83 |
| intervention | 18 | 13 | 0.72 |
| fundamental_aging | 579 | 387 | 0.67 |
| care | 81 | 53 | 0.65 |
| age_related_disease | 711 | 406 | 0.57 |
| ambiguous | 770 | 53 | 0.07 |

Label totals, rules → expert: not_relevant 754 → 1,084, fundamental_aging
579 → 825, intervention 18 → 95, age_related_disease 711 → 627, care 81 → 97,
social_population_aging 31 → 153, ambiguous 770 → 63. The expert pass mostly
*empties the ambiguous bucket*: of the 770 records the rules classifier could
not place, 353 are fundamental ageing biology, 154 are off-topic engineering or
agriculture, 84 are disease research, 72 are social/population ageing, 35 are
interventions, and only 53 stay genuinely undecidable.

## Biggest disagreement classes

**ambiguous → fundamental_aging (353 records).** Ageing-biology grants whose
vocabulary misses the lexicon — cognitive ageing, cell-type-specific ageing,
comparative biology. Example: `swecris:2025-02115_KI` "whether MKs preserve
their function during ageing" (megakaryocyte ageing) had no keyword hit.

**age_related_disease → not_relevant (216).** Disease grants whose text shows
no ageing angle at all; disease keywords alone had decided them. Example:
`swecris:2022-01221_VR`, aerobic exercise for cardiovascular risk in lymphoma
survivors — no ageing content anywhere in the text.

**ambiguous → not_relevant (154).** The engineering pool the rules gate did
not catch because a category keyword or anchor blocked the step-0 shortcut:
battery ageing, super-insulation materials, supercapacitor lifetime.

**The tree-grant family (the class behind this task).** Rules labelled five
plant/forestry senescence grants `fundamental_aging`; the expert gate sends
all of them to `not_relevant`: `swecris:2021-05062_VR` "How do trees survive
the winter?", `swecris:2021-01474_Formas` "How do trees know it is autumn?",
`cordis:714916` "What makes leaves fall in autumn?", `cordis:101117001` (leaf
phenology under climate warming), `cordis:746821` (chloroplast/leaf
senescence). The instructive near-miss is `cordis:746235` "Could senescence be
adaptive? Causes and consequences of aging across the Tree of Life" — literal
tree words, but it is evolutionary biology of ageing across taxa:
`fundamental_aging` on both passes, correctly.

**ambiguous → social_population_aging (72) and care → social_population_aging
(24).** Social gerontology the lexicon's anchored keywords under-cover:
age-friendly neighbourhoods, LGBTQ+ ageing, cultural studies of ageing.

**fundamental_aging/ambiguous → intervention (68).** Geroprotector and
senotherapeutic development whose vocabulary the lexicon deliberately traps
(senolytics, dietary restriction, healthspan): CITP/ITP testing programs,
senotherapeutics against vascular ageing, metformin-slows-brain-aging trials.
The expert boundary: agents targeting ageing itself (even with a disease as
endpoint or proving ground) are `intervention`; senolytics deployed against
one named disease (COPD, fibrosis, melanoma, glaucoma) are
`age_related_disease`; senescence vocabulary in non-ageing contexts (fetal
membranes, tumour suppression, nevi) fails step 0.

## EUR moved if expert labels replace rule labels

Numerator = fundamental_aging + intervention (the ratio's definition;
social_population_aging is denominator-only).

| region | numerator (rules) | numerator (expert) | delta |
| --- | --- | --- | --- |
| EU | €79.4M | €193.3M | +€114.0M |
| SE | €27.3M | €62.7M | +€35.4M |
| US | €175.3M | €266.9M | +€91.6M |

The numerator rises in every region because the rules pass parked large sums
in `ambiguous` (EU €255.8M, US €161.4M, SE €113.7M), and most of that money is
in fact ageing-biology research. The expert pass also moves money *out* of the
denominator: EU age_related_disease drops €113.8M, largely to `not_relevant`
(disease grants with no ageing angle) and to `fundamental_aging`. Full
per-category, per-region figures are reproducible from `expert-labels.jsonl`
joined with the corpus on `record_id`.

## Known tensions for the second-pass review

- **Anchor rule false negatives.** Swedish home-care grants ("hemtjänst",
  "models of homebased care") with no explicit ageing anchor in title or quote
  are `not_relevant` under the co-occurrence rule, though they are de facto
  elderly-care research. Flagged low/medium confidence in the file
  (e.g. `swecris:2023-01399_Forte`, `swecris:2017-00030_Forte`,
  `swecris:2016-07151_Forte`). If the rubric owners loosen the rule for care
  vocabulary that is age-implying in Swedish practice, these flip to `care`.
- **Quote-truncation artifacts.** At least one grant appears twice with
  different quote truncations and legitimately different verdicts from the
  visible text (`swecris:2022-01650_VR` vs `swecris:2022-00773_VR`, the same
  intrinsic-muscle-weakness project). The verdicts follow each record's own
  text, per the rubric; the upstream fix is better quote extraction.
- **Geroprotector-with-disease-endpoint boundary.** Records like
  `reporter:5R01AG067326-02` ("Targeting Aging to prevent Alzheimer's
  Disease") sit exactly on the intervention/disease line; they carry low
  confidence and an explicit reason either way.
- **Title-only records.** Where `llm_quote` is empty the verdict rests on the
  title alone and confidence is lowered; precision on full abstracts would
  differ (`classifier/KEYWORDS.md`, Limitations).

## Judging alignment (per AGENTS.md)

This advances the Track 3 funding-gap-ratio evidence chain: the ratio's
credibility rests on label quality, and this layer is the human-verifiable
audit trail between the rule classifier and the headline number. It is
decoupled from the eval loop and the map; nothing in `ratio/` pipeline code is
modified. Verified: 2,944/2,944 records judged, output validated for
completeness, uniqueness, label vocabulary and non-empty grounded reasons.
Unverified: the expert labels themselves are one expert pass — the second-pass
review (task hackliferepo-phd-outcomes-expert-second-37) audits them; the
30-record human benchmark remains unlabelled.
