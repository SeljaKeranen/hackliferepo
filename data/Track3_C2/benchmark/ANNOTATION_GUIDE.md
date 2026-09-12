# Annotation guide - aging funding benchmark (30 records)

Label each record using **title + abstract only**. Do not look at model outputs.
Fill `human_category` with exactly one of:

| Category | Definition | Include example | Exclude example |
| --- | --- | --- | --- |
| fundamental_aging | Studies ageing mechanisms themselves | cellular senescence, epigenetic clocks, inflammaging, proteostasis, stem-cell exhaustion, mitochondrial dysfunction, comparative longevity | a cancer study that merely mentions "ageing" |
| intervention | Intervention framed around slowing/reversing ageing | rapamycin, senolytics, metformin as geroprotection, dietary restriction for lifespan/healthspan | a drug trial for a specific disease |
| age_related_disease | Research on a specific age-related disease | Alzheimer's, cancer, cardiovascular disease, diabetes, osteoporosis, sarcopenia, clinical frailty | mechanistic ageing study using a disease model |
| care | Elderly care, long-term care, caregiving, social services | nursing-home workflows, caregiver burden, home care | clinical treatment of a disease |
| ambiguous | Insufficient or borderline information | abstract too vague to decide | (do not force a category) |

Edge rules:
1. A disease name alone does not make a record `fundamental_aging`.
2. "Aging" mentioned inside a disease study is not enough for `fundamental_aging`.
3. Use `care` only for service/social-care delivery.
4. If you cannot decide from the text, use `ambiguous` - it is a valid, scored outcome.

`human_confidence`: 0.0-1.0. `human_notes`: optional, one line (e.g., "borderline
disease/mechanism").

Files:
- benchmark_30.csv      fill human_category / human_confidence / human_notes
- benchmark_30_key.json hidden mapping to model + rule labels (used by evaluate.py)

Evaluation: python src/evaluate.py (run after labelling).
