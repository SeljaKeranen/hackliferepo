# Second-expert outcomes review of the funding-gap ratio

Independent verification pass over the funding-gap ratio pipeline (PR #10,
`ratio/` on branch `pr-10`), run 12 September 2026. Lens: **study outcomes** —
each grant judged on what the funded work is stated to produce or measure,
from the earliest stage (rules labels) to the final aggregate ratio numbers.
This pass is independent of the senior-expert re-tagging task; see "Expert
stage" below for its status.

## Method

- **Label sample audit.** 214 of 2,944 records, stratified by rules label ×
  region, with the top-3 EUR grants per stratum force-included (the grants
  that move the ratio) and the rest drawn with a fixed seed (37). All 18
  `intervention` and all 31 `social_population_aging` records were reviewed
  exhaustively. Each record was judged by a reviewer panel (8 parallel
  reviewers, one batch each, shared written rubric derived from
  `classifier/KEYWORDS.md`) on title + the atlas `llm_quote` snippet; the
  highest-EUR dissents were re-adjudicated by hand. Verdicts are in
  [`outcomes-review.jsonl`](outcomes-review.jsonl) (one line per record:
  record_id, stage, verdict concur/dissent/uncertain, corrected_label,
  reason).
- **Expert-stage audit (phase 2).** After the senior-expert re-tag landed,
  154 of its labels were adjudicated the same way — sampled from the
  disagreement-heavy rules→expert strata plus every record where phase 1 and
  the expert conflict, plus an agreement control. Same rubric, same panel
  setup, stage `expert` in the verdicts file.
- **Aggregate audit.** Full recomputation of every published number from
  `ratio/output/labels.jsonl`: region ratios, category EUR totals, ambiguous
  shares, missing-EUR counts, and all 43 funder rows; plus concentration,
  leave-one-out sensitivity, NIH activity-code composition, and cross-source
  amount-semantics checks.

Because the sample deliberately over-weights rare labels and the largest
grants, the dissent rates below are a stress test of the money that matters,
not an unbiased estimate of per-record accuracy across the corpus (random
records would score better).

## Aggregate audit: the arithmetic is exact

Every published number reproduces from the labels: SE 0.2066, EU 0.1768,
US 0.3917, total 0.2742; all category EUR totals, ambiguous shares, and all
43 funder rows match to the cent; missing-EUR counts (2/0/37) match. No
duplicate titles exist in the corpus. Funder-level ratios are internally
coherent (Forte, Sweden's welfare-research funder, at 0.4%; NIA at 36.7%) —
the aggregates follow from the labels. Every distortion found below enters
through the labels or the corpus, not the aggregation.

## Label verdicts vs the rules stage

214 verdicts: **140 concur (65%), 64 dissent (30%), 10 uncertain (5%).**

| rules label | n | concur | dissent | uncertain |
|---|---|---|---|---|
| fundamental_aging | 45 | 35 | 9 | 1 |
| intervention | 18 | 12 | 6 | 0 |
| age_related_disease | 36 | 23 | 12 | 1 |
| care | 30 | 20 | 8 | 2 |
| social_population_aging | 31 | 26 | 3 | 2 |
| ambiguous | 30 | 8 | 22 | 0 |
| not_relevant | 24 | 16 | 4 | 4 |

The four material dissent patterns, with sampled EUR:

1. **The ambiguous band hides classifiable slowing-ageing money (largest
   distortion).** 14 of 30 sampled `ambiguous` records are confidently
   `fundamental_aging` (45.0M EUR sampled), 2 more `social_population_aging`.
   Examples: MIA-Portugal ageing-biology institute (15.0M, EU), the Baltimore
   Longitudinal Study of Aging (4.2M, US), centenarian protective-omics
   (4.3M, US). One is decisive: `cordis:101118919` "Learning from Bats: New
   Strategies to Extend Healthspan" (11.9M) is a **worked example in
   KEYWORDS.md itself, specified as `fundamental_aging`** — the shipped
   classifier outputs `ambiguous` for it, contradicting its own spec.
   Because ambiguous is excluded from both sides, this suppresses the
   numerator EUR in every region.
2. **The relevance gate leaks off-topic money into the denominator.** 9 of
   36 sampled `age_related_disease` records have no ageing connection at all
   (19.5M sampled; the largest, `EXpanding Platforms for Efficacious mRNA
   Therapeutics`, 14.9M EU, is a first-in-man cancer immunotherapy platform).
   A 7.1M floating-solar-plant grant ("end-of-life", component ageing) sits
   in `care`. The leak runs both ways at smaller scale: a 3.5M US HIV-ageing
   cohort was wrongly `not_relevant`.
3. **The top of the EU numerator is disease work.** The EU's three largest
   `fundamental_aging` grants (17.6M of a 79.4M numerator) are vaccine
   strategies for older adults (6.1M + 5.5M) and Parkinson's
   diagnostics/therapeutics (6.0M) — all `age_related_disease` under the
   rubric's own rule that disease vaccines/therapies for older adults are not
   slowing-ageing work.
4. **`intervention` boundary is noisy but ratio-neutral.** 6 of 18 dissents,
   5 of them → `fundamental_aging` (mechanism studies of interventions,
   per the mechanism-vs-intervention rule). Both labels sit in the numerator,
   so the ratio is unaffected; the intervention EUR figure itself (7.0M
   total) should not be quoted with confidence.

`social_population_aging` (10% dissent) is the healthiest category — the new
category and its anchor rule work. `care`'s dissents are mostly the soft
boundary to `social_population_aging` (5 of 8), denominator-internal and
ratio-neutral.

## Outcome-level distortions in the published numbers

- **SE's headline is single-grant sensitive.** One 4.3M grant (mitochondrial
  function) is 15.9% of the SE numerator; dropping it moves SE from 20.7% to
  18.0%. No other region has a single-grant swing above 2.3pp.
- **US numerator contains infrastructure and training money.** 23.3% of US
  numerator EUR rides on NIH center (P30/P01/U54…) and training/fellowship
  (T32/K/F…) activity codes — capacity, not direct research output. Excluding
  both classes moves US from 39.2% to 37.5%; direction unchanged.
- **Cross-source EUR totals are not comparable, confirming the README's own
  caveat.** CORDIS records are whole multi-year project budgets (median 1.5M),
  NIH records are single-fiscal-year awards (median 0.33M; 46 core projects
  appear 2–3 times as separate support years), SweCRIS sits between. Within-
  region ratios largely cancel this; any cross-region EUR-magnitude claim
  does not survive it.

## Corrected-ratio scenarios

| scenario | SE | EU | US |
|---|---|---|---|
| published (rules) | 20.7% | 17.7% | 39.2% |
| direct-corrected (the 64 sampled fixes only — lower bound) | 21.3% | 19.8% | 40.8% |
| extrapolated (stratum dissent rates applied corpus-wide) | 22.6% | 36.1% | 55.3% |
| senior-expert full re-tag (verified below, best available estimate) | 32.6% | 40.6% | 49.9% |

The extrapolation row (computed before the expert layer landed) assumes the
sampled ambiguous records represent each region's whole ambiguous EUR pool;
since sampling force-included the largest (most classifiable) grants it is a
rough scenario, not an estimate — yet it independently predicted both
directions the expert layer confirmed: every ratio rises, and the EU
overtakes Sweden.

## Fitness-for-demo verdict on the SE/EU/US ratio numbers

- **Robust and defensible:** the US devotes the largest share of its
  ageing-research money to slowing ageing. It is highest in every scenario
  tested — leave-one-out, infra-excluded, both correction scenarios, and the
  verified expert re-tag (49.9% vs EU 40.6% vs SE 32.6%).
- **The published rules numbers (SE 21% / EU 19% / US 39%) are not fit to
  present as point estimates.** Two independent expert passes agree they are
  biased low in every region — mostly because the rules classifier parks
  classifiable fundamental-ageing money in the excluded ambiguous band — and
  that the published SE-vs-EU ordering is an artifact of exactly that bias:
  the verified expert layer puts the EU clearly above Sweden (40.6% vs
  32.6%), reversing the published 21%-vs-19%. Do not present the SE > EU
  ordering.
- **What to show on Demo Day:** the expert-layer ratios (this review
  concurs with 88% of adjudicated expert labels, EUR-weighted 87.5%, with
  residual dissent worth at most a point or two on the EU), with the rules
  layer kept as the transparent, reproducible first stage and the remaining
  ambiguous shares (12.5% / 4.4% / 2.9%) shown beside the bars. If only the
  rules layer can ship, quote ranges ("SE roughly 21–33%, EU 18–41%,
  US 39–50%") rather than points, and drop any SE-vs-EU comparison.
- **Cheap fixes to the rules layer**, in impact order: (1) fix the
  KEYWORDS.md-worked-example regression (Bats → fundamental_aging) and
  re-check the 0.3 tie-margin that overfills the ambiguous band, (2) add the
  sampled `not_relevant` corrections (mRNA platform, floating PV) as lexicon
  exclusions or overrides, (3) re-run `ratio/build.py`.

## Expert stage: verdicts vs the senior-expert re-tag

The parallel senior-expert re-tagging
(`ratio/expert/expert-labels.jsonl`, branch
`fm/hackliferepo-senior-longevity-expert-re-ae`) landed mid-review and covers
all 2,944 records. Cross-checks first: its published agreement stats
reproduce exactly from the data (rules-vs-expert 53.3%; the ambiguous bucket
empties 770 → 63), and its full-corpus ratios recompute to **SE 32.6%,
EU 40.6%, US 49.9%** (ambiguous shares 12.5% / 4.4% / 2.9%).

154 expert labels were adjudicated with the same rubric and panel setup,
drawn from the disagreement-heavy rules→expert strata (top-3 EUR per cell
force-included), all 20 records where phase 1 and the expert disagree, and a
10-record agreement control. Verdicts (stage `expert` in
`outcomes-review.jsonl`): **135 concur (88%), 11 dissent (7%), 8 uncertain
(5%)**; EUR-weighted concurrence 87.5% of 279M sampled. One panel dissent was
overridden by the lead reviewer because it contradicted a KEYWORDS.md worked
example (the Metformin record; documented in its verdict line).

The three flows that move the ratio are essentially unanimous:
ambiguous→fundamental_aging 22/23 concur, age_related_disease→not_relevant
22/22, ambiguous→not_relevant 14/15. Phase 1's independent corrected labels
agree with the expert on 90.2% of the 204 decided sampled records — two
independent passes converging on the same corrections.

Residual dissent against the expert layer concentrates in two spots:

1. **The expert over-assigns `intervention` to mechanism studies** (2 concur
   / 3 dissent / 1 uncertain in the fundamental_aging→intervention cell —
   e.g. genomic analysis of the CALERIE trial is mechanism knowledge, not a
   tested intervention). Both labels sit in the numerator, so the ratio is
   unaffected; the expert's intervention count (95 records) is soft.
2. **A slightly lenient step-0 for disease grants** (14.7M sampled kept in
   the denominator that this review reads as `not_relevant` — a 10.0M HIV
   microbiome-stratification grant and a 4.0M cardiovascular-biomarker grant
   with no ageing framing; plus one 6.1M vaccines-for-older-adults grant the
   expert put in the numerator as `intervention` that the rubric places in
   `age_related_disease`). Net direction: the expert EU ratio is a
   percentage point or two generous, all within the uncertainty band.

## Limitations

- Verdicts rest on grant titles plus the atlas's `llm_quote` snippet, not
  full abstracts; 10 records stayed `uncertain` for exactly that reason.
- Reviewer panel = one model family; a systematic bias shared by panel and
  rubric would not be caught. Verdicts are reproducible from
  `outcomes-review.jsonl` (fixed seed, stated rubric) and each carries a
  one-sentence outcomes-grounded reason for human spot-checking.
- The 30-record human benchmark (`data/Track3_C2/benchmark/`) remains the
  ground-truth instrument; this review does not replace it.
