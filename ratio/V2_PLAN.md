# Ratio v2 plan: keyword expansion and near-tie rules

Status: Tracks A and B implemented and validated 2026-09-12; Phase 2
(model adjudication) complete for all three regions via
`ratio/adjudicate.py` (deepseek-flash, 1,314/1,314 quotes verified, 0
failures; API-vs-in-session overlap agreement 24/29). Adjudicated ratios:
SE 0.240, EU 0.684, US 0.500; ambiguous shares ~0%. See ratio/README.md for
the full tables and caveats. Results on the atlas expert labels
(`ratio/eval_rules.py`): agreement 53.3% -> 56.7%, rules-ambiguous
770 -> 644, no category down more than 2pp. `EVIDENCE_FLOOR` was tuned once
on the expert set (0.70 rejected: ambiguity rose to 916 with no accuracy
gain); `REL_MARGIN` tuned to 0.10 (0.08+ cost social >2pp).

Original scope: applies to the funding-gap ratio pipeline
(`ratio/classify.py`, `ratio/build.py`, `classifier/keywords.json`).
Phase 1 = keyword expansion (Track A) and near-tie rule changes (Track B).
Phase 2 (later, approved but not specified here) = DeepSeek v4.1 adjudication
of the remaining ambiguous records. The UI stays unchanged: one ambiguous
band, no split.

Baseline (v1 census build, `ratio/output/`): 2,866 ambiguous records,
EUR 1,503M, split by reason:

| reason class | records | EUR | what it is |
| --- | ---: | ---: | --- |
| `no_match` (anchor, no category keyword) | 1,443 | 840M | lexicon coverage gap |
| `near_tie` (margin < 0.3) | 1,423 | 663M | decision rule too coarse |
| SE total | 246 | 93.6M | 187 no_match + 59 near_tie |
| EU ambiguous share | 60.8% | - | the biggest presentation problem |
| US ambiguous share | 18.7% | - | near_tie-dominated (1,350) |

Evidence for the diagnosis: SE top-EUR ambiguous are social/care records
(FINGER-Pro healthy ageing, loneliness research programme, life-course
inequality), EU top-EUR include a KEYWORDS.md worked example
(`cordis:101118919` Bats → should be `fundamental_aging`), US top are
funding-heavy near-ties (`reporter:5U01AG078533` education and cognitive
functioning) and anchor-only centres (Longevity Consortium).

## Track A - keyword expansion

### A1. Candidate harvest (deterministic, no model calls)

New script `ratio/mine_candidates.py` (stdlib only):

1. Join the 2,866 ambiguous `record_id`s from `ratio/output/labels.jsonl` to
   the census texts in `ratio/data/census_*.jsonl.gz`.
2. Tokenise (case-folded, unicode-aware), extract 1-3-grams, drop stopwords
   and terms already in the lexicon (any block, including traps and
   retrieval factors), drop pure numbers.
3. Rank candidates by amount-weighted frequency and by log-odds with +0.5
   smoothing against all non-ambiguous records (same method as
   `classifier/KEYWORDS.md` section "Method"), computed separately for
   English and Swedish texts (`extra.abstract_language == "sv"` or
   `record_id` swecris with Swedish title).
4. Emit `ratio/candidates.csv`: `term, lang, n_ambiguous, eur_ambiguous,
   log_odds, example_record_ids, context_snippet`.

No candidate enters the lexicon from this file automatically; A2/A3 decide.

### A2. Validation gates (every admitted keyword)

A candidate is admitted only with a target category and pass on both gates:

- **Gate 1, lexicon validator**: run
  `python3 classifier/validate_keywords.py --update` after insertion;
  entry must clear the standard thresholds (en: >=3 hits, >=0.60 precision
  against atlas `llm_category`; sv: >=1 hit, >=0.60; `low_evidence: true`
  under 5 hits; `variant_of` only for spelling variants of kept terms).
- **Gate 2, expert labels**: precision >= 0.60 against
  `ratio/expert/expert-labels.jsonl` on records present in that corpus,
  minimum 3 records. This is the stronger label source; a Gate-1 pass with
  a Gate-2 fail is rejected.
- **Census-only terms** (no atlas/expert overlap): admitted only as
  `provisional: true` with 5 hand-checked examples in the entry's
  `evidence` field, and counted separately in the before/after table.

Entries record `source: "ambiguous-mining-2026-09-12"` plus the measured
stats, so the provenance stays reproducible.

### A3. Conditional voters for trap terms (new lexicon block)

Several frequent ambiguous matches are current `trap_terms` that can never
vote (`loneliness`, `social isolation`, `participation`, `ageing
population`, `social network*`, `extend healthspan`, `lifespan extension`,
`healthy aging/ageing`). Two changes:

- New per-category block `conditional_voters`, entries
  `{term, requires, weight, evidence, source}`:
  - `requires: "anchor"` - counts only when an ageing anchor is present
    (the existing `requires_ageing_anchor` machinery).
  - `requires: "dev_cues"` - counts for `intervention` only when
    `DEV_CUES` matches (explicit developing/testing language).
  - `weight` is measured for its target category on the expert labels
    (Gate 2), never the ambiguous-proxy precision from `trap_terms`.
- `classifier/validate_keywords.py` gets syntax-only validation for this
  block (term well-formed, known `requires`, weight in [0,1]) plus optional
  stats recomputation; no thresholds, because the terms are conditioned.
- `ratio/classify.py` adds conditional voters to the voting sum after the
  anchor/cue condition is checked, and lists them in `matched_keywords`
  with a `(conditional)` marker for transparency.

Initial candidates (all measured before admission):
`loneliness`, `social isolation`, `participation`, `ageing population`,
`age-friendly`, `life course`, `ageism` → `social_population_aging`;
`extend healthspan`, `lifespan extension`, `healthspan` → `intervention`
with `dev_cues`; `biology of ageing`, `aging biology`, `ageing biology`,
`mechanisms of ageing` → `fundamental_aging` (normal Gate 1/2 candidates,
not conditional; these are outright gaps flagged by the Bats record).

### A4. Change mechanics and regression

1. Edit `classifier/keywords.json` (new entries + conditional voters).
2. `python3 classifier/validate_keywords.py --update` then re-run without
   `--update` (must exit 0) and `--self-test`.
3. Update `classifier/KEYWORDS.md`: counts table, a new entry under the
   enrichment sections with the funnel (candidates -> Gate 1 pass -> Gate 2
   pass -> admitted), and the conditional-voter rules.
4. `python3 ratio/build.py`; record the before/after ambiguous table (by
   region, reason class, EUR) in `ratio/README.md`.
5. `python3 ratio/classify.py --self-test` and
   `python3 ratio/build.py --self-test && python3 ratio/build.py --check`
   after the rebuild.

### A5. Acceptance criteria (Track A)

- SE ambiguous share falls (target: below 25%), EU below 55%, with every
  admitted keyword traceable to both gates.
- No region's ratio moves by more than 3 percentage points without an
  explicit explanation in the README.
- Expert-label agreement on the 2,944-record overlap does not fall
  (baseline 53.3%) and ideally rises by >=2pp.
- The Bats record (`cordis:101118919`) classifies `fundamental_aging`.

## Track B - near-tie rules

### B1. Current logic (v1, for the record)

`ratio/classify.py`: per-category score = sum of matched keyword
precisions (step 1); `margin = top - second`; the fundamental/intervention
boundary has its own mechanism-vs-intervention rule (step 2); everything
else with `margin < TIE_MARGIN` (0.3) becomes `ambiguous` with the reason
"too close to call" (step 3). `TIE_MARGIN = 0.3` is a flat absolute
threshold: two weak single keywords can trigger it
(`care 0.667 vs fundamental_aging 0.667`, margin 0.0), while a strong
winner with a small absolute gap is refused too.

### B2. New decision rule (replaces the flat margin check)

Parameters, all stamped into `aggregates.json method`:

- `EVIDENCE_FLOOR = 0.60`: the winner must include at least one keyword
  with precision >= 0.60, or at least two winning terms with one
  unconditional keyword; single terms below 0.60 never decide. (Drafted at
  0.70, tuned down to the lexicon's own 0.60 floor on the expert set, where
  0.70 moved 132 mostly-wrong disease calls into ambiguous with no accuracy
  gain.)
- `REL_MARGIN = 0.15`: decide when
  `margin >= TIE_MARGIN` **or**
  (`margin / top >= REL_MARGIN` **and** evidence floor holds).
  Otherwise `ambiguous`.
- The reason string names which condition failed (evidence floor vs
  relative margin) so the UI drill-down stays informative without a UI
  split.

Worked examples under the new rule (target behaviour):

- `care 0.667 vs fundamental_aging 0.667` (Suicidal behavior in older
  adults): evidence floor fails (single weak terms) → stays `ambiguous`.
- `care 0.857 vs age_related_disease 0.816` (Life with dementia):
  evidence floor holds, relative margin 4.8% < 15% → stays `ambiguous`
  unless B3 resolves the boundary.
- Longevity Consortium-type records: A-track keywords decide them outright.

### B3. Boundary priority rules (only when those categories are top-2)

Ordered, applied before the B2 tie check; each needs a worked example in
`KEYWORDS.md` and a `classify.py --self-test` case:

1. `fundamental_aging` vs `intervention`: existing mechanism-vs-
   intervention rule, unchanged.
2. `fundamental_aging` vs `age_related_disease`: if `MECH_CUES` matches and
   the disease side is supported only by named-disease keywords, decide
   `fundamental_aging` (expert-verified pattern: 216 disease grants had no
   ageing angle; mechanism language signals the ageing objective).
3. `care` vs `social_population_aging`: service-delivery evidence
   (`caregiv*`, `nursing home*`, `home care`, `long-term care`,
   `äldreomsorg*`) decides `care`; age-and-society evidence (`loneliness`,
   `participation`, `life course`, `age-friendly`, `ageism`, `inequality`)
   decides `social_population_aging`; both or neither → `ambiguous`.
4. Vaccines/therapies aimed at a named disease in older adults (vaccine,
   immunotherapy, treatment + disease term + older-adults reference)
   decide `age_related_disease`, never the numerator (expert-verified
   pattern behind the EU's inflated numerator in review phase 1).

### B4. Validation protocol (before any rule is enabled)

1. Run both rule versions over the 2,944-record atlas with the expert
   labels as reference: overall agreement, per-category agreement,
   ambiguous count, confusion matrix. Baseline: 53.3% overall.
2. Acceptance: overall agreement rises; no category's agreement drops by
   more than 2 percentage points; ambiguous records fall; Bats and the
   boundary worked examples classify as specified.
3. Tune `EVIDENCE_FLOOR` / `REL_MARGIN` on the expert set only once each;
   record the chosen values and the rejected alternatives in the README.
4. Rebuild, compare v1 vs v2 region ratios, and document the delta and its
   cause per region. Keep the v1 outputs recoverable (git history plus the
   `--corpus atlas` comparison path); no silent overwrite of published
   numbers.

### B5. Out of scope (phase 3)

- DeepSeek v4.1 adjudication of records still ambiguous after Tracks A+B,
  as a separate `adjudicated` scenario (cached, quote-verified, spot-
  checked); it never overwrites the rules output.
- Human benchmark (30 records) remains the ground-truth instrument.
- UI changes: none.

## Risks

- Overfitting the rules to the handful of screenshot examples; the expert
  set is the only guard, and it is one expert pass, not ground truth.
- Expert labels cover the 2,944 atlas records only; census-only keywords
  rest on provisional hand checks.
- Swedish candidate mining has thin text; every sv addition is
  `low_evidence` by construction.
- Changing the lexicon invalidates the v1 inputs hash; outputs must be
  rebuilt and the README delta table written in the same commit.

## Judging alignment (per AGENTS.md)

Advances the Track 3 funding-gap ratio's evidence and technical execution:
fewer decisions parked in `ambiguous`, each new keyword and rule traceable
to measured evidence. Verified: baseline counts/EUR above, reproducible
from `ratio/output/labels.jsonl`. Unverified: the effect of Tracks A+B until
the expert-label comparison runs; label quality remains the binding
constraint.
