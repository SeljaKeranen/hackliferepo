# Methodology - Aging Funding Atlas

## Question and user

How much public research funding targets fundamental ageing biology, in different
countries? User: research policy analyst / funder. Output is descriptive; no causal
claims about funding and health outcomes.

## 1. Data sources

All sources were retrieved on 2026-09-12 unless noted. Licences and provenance are
also published in `output/DATA_LICENCES.md`.

| Source | Operator | Endpoint(s) | Auth | Raw cache |
| --- | --- | --- | --- | --- |
| NIH RePORTER | U.S. National Institutes of Health | `POST https://api.reporter.nih.gov/v2/projects/search` | none | `data/raw/reporter/` |
| CORDIS search | EU Publications Office | `GET https://cordis.europa.eu/search?q=<query>&format=json&p=<page>` | none | `data/raw/cordis/search/` |
| CORDIS project details | EU Publications Office | `GET https://cordis.europa.eu/project/id/<id>?format=json` | none | `data/raw/cordis/details/` |
| Swecris | Swedish Research Council (VR) | `GET https://swecris-api.vr.se/v1/scp/export?searchText=<phrase>` | `Authorization: Bearer <token>` | `data/raw/swecris/` |
| ECB reference rates | European Central Bank | `https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml` (snapshot 2026-09-11) | none | `src/fx_rates.json` |

Access notes:
- NIH RePORTER is U.S. federal data (generally public domain); attribute NIH RePORTER.
- CORDIS content is (c) European Union, reuse permitted under CC BY 4.0 unless stated
  otherwise; check the CORDIS legal notice for third-party material.
- Swecris data is openly accessible per VR; attribute Swecris. The token lives only in
  `Track3_C2/.env` (gitignored). The 401s observed on 2026-09-11 were fixed on
  2026-09-12: the working combination is `Authorization: Bearer <public token>` on the
  `/v1/scp/*` endpoints (not the `api-key` header used earlier).

## 2. Scope (fixed decisions)

- Window: 2015-2025 (fiscal years for NIH RePORTER; start year for CORDIS and Swecris).
- Cap: <= 2,000 records per source.
- Language: English for RePORTER/CORDIS; Swecris titles/abstracts may be Swedish
  (English preferred when present).

## 3. Scraping protocol and keywords

### 3.1 NIH RePORTER

- Query: for each phrase and each fiscal year 2015-2025, POST criteria:
  `advanced_text_search {operator: "and", search_field: "projecttitle,abstracttext",
  search_text: "<phrase>"}` with `fiscal_years: [year]`.
- Pagination: `offset`/`limit` with 500 per page; 2,000-record ceiling per phrase-year.
- Fields collected: ProjectNum, ProjectTitle, AbstractText, FiscalYear, AwardAmount,
  Organization, AgencyIcAdmin, ProjectStartDate, ProjectEndDate, ActivityCode,
  PrincipalInvestigators.
- Keywords (8): `cellular senescence`, `biological aging`, `biological ageing`,
  `geroscience`, `healthspan`, `inflammaging`, `senolytic`, `epigenetic clock`.
- Result: 12,115 unique records; stratified sample by fiscal year to 2,000 (seed 42);
  1,531 with abstracts entered the dataset. Raw pages cached per phrase-year.

### 3.2 CORDIS

- Query: `q="<phrase>" AND contenttype='project'`, `format=json`, 10 records per page.
- Enrichment: for every project ID, fetch the project JSON for dates, `ecMaxContribution`,
  `totalCost`, `status` and associations (organisation countries).
- Keywords (13): `cellular senescence`, `senescence`, `geroscience`, `healthspan`,
  `health span`, `senolytic`, `inflammaging`, `biological ageing`, `biological aging`,
  `cellular ageing`, `anti-ageing`, `ageing research`, `longevity`.
- Result: 616 unique projects; 558 start in 2015-2025 and entered the dataset.
- Country attribution: first organisation with an `address.country` in the project's
  associations (documented proxy, not the official coordinator field).

### 3.3 Swecris

- Query: one CSV export per phrase, `searchText` over the full record.
- Keywords (13, English + Swedish): `ageing`, `aging`, `senescence`, `longevity`,
  `healthspan`, `geroscience`, `inflammaging`, `senolytic`, `åldrande`, `senescens`,
  `livslängd`, `hälsosamt åldrande`, `biologiskt åldrande`.
- Broad-term rule: records matched ONLY by `aging` or `livslängd` are excluded. On the
  unfiltered sample these produced a 73.3% ambiguous share (mostly non-ageing
  projects). Every record keeps its full matched-phrase set.
- Deduplication key: (`ProjectId`, `FundingOrganisationId`, `FundingStartDate`);
  multiple funders of one project remain separate funding rows.
- Result: 6,410 unique funding rows; 884 precise in-window rows; 855 entered the
  dataset after the title/abstract and dedupe checks.
- Funder mix: Swecris includes governmental and private funders; the field
  `extra.funder_type` is kept and a government-only split is published in
  `aggregates.json`.

## 4. Dataset description

### 4.1 Files

```text
data/processed/<source>/records.jsonl   unified records (working, gitignored)
data/processed/<source>/rules.jsonl     keyword-baseline labels
data/processed/<source>/llm.jsonl       deepseek-flash labels
data/processed/<source>/export.csv      per-source CSV export
output/<source>.csv                     committed derived data (same columns)
output/aggregates.json                  shares, coverage, government-only split
output/metadata.json                    counts, FX, limitations
```

### 4.2 Record schema (per row)

| Field | Description |
| --- | --- |
| `record_id` | `<source>:<source_id>` (e.g. `reporter:5R00HL146905-05`) |
| `source` | `reporter` / `cordis` / `swecris` |
| `source_id` | source-native ID (ProjectNum / CORDIS id / Swecris ProjectId) |
| `title`, `abstract` | abstract truncated to 6,000 chars |
| `funder` | funding agency / organisation name |
| `country` | `US` / first listed CORDIS organisation country / `SE` |
| `year` | fiscal year (RePORTER) or start year (CORDIS, Swecris) |
| `amount`, `currency` | native amount: USD / EUR / SEK |
| `amount_eur`, `fx_date` | converted amount and the fixed rate date |
| `url` | dated source link (project page / reporter page / Swecris search link) |
| `extra` | source-specific: organisation, activity code, matched phrases, funder type, status |
| `retrieved_at` | retrieval date (2026-09-12) |
| `rule_category` (in rules.jsonl) | keyword baseline label |
| `llm_category`, `llm_confidence`, `llm_quote`, `llm_rationale` (in llm.jsonl) | model label with evidence quote |

### 4.3 Counts and coverage

| Source | Records | Ambiguous share | Notes |
| --- | ---: | ---: | --- |
| NIH RePORTER (US) | 1,531 | 18.8% | sample of 12,115; federal grants only |
| CORDIS (EU) | 558 | 53.2% | EU-funded projects, short summaries |
| Swecris (Sweden) | 855 | 44.8% | precise phrases only; government + private funders |
| **Total** | **2,944** | - | 2015-2025, all flash-labelled |

EUR conversion: ECB reference rates 2026-09-11 - USD 1.1592, SEK 11.2373 per EUR;
`amount_eur = amount / rate`; indicative only, not annualised.

### 4.4 Label provenance

- `rule_category`: keyword baseline (rules v1, `src/config.py`).
- `llm_category`: DeepSeek `deepseek-flash`, temperature 0, abstract truncated to
  1,500 chars, resumable cache. Pro-model outputs were archived and are not used.
- Human benchmark: 30 records (20 RePORTER / 5 CORDIS / 5 Swecris) with a blank
  annotation template and guide; labels pending. No category number is
  human-verified until that file is filled (`src/evaluate.py`).

## 5. Taxonomy

| Category | Definition | Excludes |
| --- | --- | --- |
| fundamental_aging | ageing mechanisms themselves (senescence, epigenetic clocks, inflammaging, proteostasis, stem-cell exhaustion, mitochondrial dysfunction, comparative longevity, geroscience) | disease-only studies |
| intervention | intervention framed around slowing/reversing ageing (geroprotectors, senolytics, rapamycin, metformin as geroprotection, dietary restriction for lifespan) | disease-specific drug studies |
| age_related_disease | a specific age-related disease (Alzheimer's, cancer, CVD, diabetes, osteoporosis, sarcopenia, clinical frailty) | mechanistic ageing studies |
| care | elderly care, long-term care, caregiving, social services | clinical treatment |
| ambiguous | insufficient/borderline information | never force a label |

Rules: a disease name does not imply fundamental ageing; "aging" mentioned in a
disease study is not enough; care is service delivery only.

## 6. Pipeline

1. Fetch per source -> raw pages cached under `data/raw/`.
2. Normalize -> per-source `records.jsonl` with the unified schema, plus `amount_eur`
   converted with fixed ECB rates.
3. Deduplicate: within source by ID and normalized title (Swecris: funding-row key).
4. Classify: keyword baseline (`rules.jsonl`) and DeepSeek flash (`llm.jsonl`).
5. Human benchmark: 30 stratified records; `evaluate.py` reports per-class
   precision/recall/F1 and disagreements once labels exist.
6. Aggregate: category shares and amounts by source/year; coverage map data;
   government-only split for Swecris.
7. Export: per-source CSVs (`output/`), static demo snapshot, Streamlit app.

## 7. Evaluation protocol

- Corpus-level: rules-vs-LLM agreement (measured: 61.8% on 2,944 records).
- Human benchmark: per-class precision/recall/F1 for both classifiers against the 30
  human labels, plus a disagreement list for error analysis.
- Success bar (team-set, Playbook-compatible): >= 85% agreement with human labels on
  the benchmark, with ambiguous cases explicitly flagged rather than forced.

## 8. Headline ratios (fundamental ageing share, 2026-09-12)

Definition: `fundamental_aging / (fundamental_aging + intervention +
age_related_disease + care)` on labelled records; bounds add all ambiguous records
to the numerator (upper) or denominator (lower).

| Region | Source | Point | Bounds | +intervention | ambiguous |
| --- | --- | ---: | --- | ---: | ---: |
| US | NIH RePORTER | 52.7% | 42.8-61.5% | 59.7% | 18.8% |
| EU | CORDIS | 41.8% | 19.5-72.8% | 46.4% | 53.2% |
| Sweden | Swecris (all) | 24.4% | 13.5-58.3% | 26.9% | 44.8% |
| Sweden | Swecris (government only) | 23.2% | 12.3-59.2% | 25.4% | 46.9% |

## 9. Known failure modes

- Short CORDIS summaries produce a high ambiguous share (53.2% vs 18.8% for RePORTER).
- Swecris still carries 44.8% ambiguous even after the precise-phrase filter.
- Sample-based shares carry sampling error; no confidence intervals are computed yet.
- Amounts are award-level and not annualised; cross-currency sums are indicative.
- CORDIS country is a first-organisation proxy, not the official coordinator.
- Model labels are not human-verified until the benchmark is labelled.
