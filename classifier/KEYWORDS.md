# Search-keyword lexicon for the "follow the money" grant classifier

A validated lexicon of search keywords for the Track 3 challenge 2 question:
how much public research funding targets the biology of ageing versus
age-related disease versus elderly care. The categories and their edge rules
come from the annotation guide at
`data/Track3_C2/benchmark/ANNOTATION_GUIDE.md` in commit `2e59b27`:
`fundamental_aging`, `intervention`, `age_related_disease`, `care`,
`ambiguous`. The lexicon covers the first four; `ambiguous` is an outcome, not
a search target.

Files:

- [`keywords.json`](keywords.json) - the lexicon: per-category English and
  Swedish keywords with per-keyword corpus stats, trap terms with false-hit
  examples, a category-agnostic broad search net, and exclusion markers.
- [`validate_keywords.py`](validate_keywords.py) - stdlib script that
  recomputes every stat from the recovered corpus and fails if the JSON has
  drifted. Run: `python3 classifier/validate_keywords.py`.

## The governing principle: search broad, classify precise

Live database searches should maximise recall with the category-agnostic
`meta.broad_net` terms (`aging`, `ageing`, `senescence`, `longevity`, and so
on, plus Swedish equivalents). The per-category keywords then do the precise
work locally: a downstream classifier assigns categories to whatever the broad
net catches. Searching each database directly with narrow category keywords
would silently drop everything the categories' vocabularies miss - the
per-category coverage numbers below (40-68%) show how much that would lose.

## Evidence base

The corpus is teammate Max's Aging Funding Atlas: 2,944 grant records
(1,531 NIH RePORTER, 855 SweCRIS, 558 CORDIS), each with a title, an LLM
category (`llm_category`), an LLM-chosen supporting quote (`llm_quote`), and a
rule-based category from keyword rules that were never committed. The atlas
was added in commit `2e59b27` and deleted from main in `4061bff`; recover it
with:

```
git show 2e59b27:data/Track3_C2/output/swecris.csv
git show 2e59b27:data/Track3_C2/output/cordis.csv
git show 2e59b27:data/Track3_C2/output/nih_reporter.csv
```

LLM label distribution: 967 ambiguous, 879 fundamental_aging, 830
age_related_disease, 157 care, 111 intervention.

**Caveat: the LLM labels are the yardstick here, and they are unverified.**
They agree with the lost keyword rules on only 61.8% of records, and the
30-record human benchmark is still unlabelled. Every "precision" figure in
this lexicon is therefore a proxy - the share of a keyword's hits whose
`llm_category` matches the keyword's category - not ground truth. When the
human benchmark is labelled, re-run the validation against it.

## Method

1. **Seed** each category with the annotation guide's include-lists (cellular
   senescence, epigenetic clocks, senolytics, rapamycin, Alzheimer's,
   nursing-home workflows, ...).
2. **Expand** from the corpus: log-odds ratio (with +0.5 smoothing) of
   unigram and bigram document frequencies in each category's records versus
   all other records, computed over lowercased title + llm_quote. Top-ranked
   distinctive terms were curated into candidate keywords. Swedish candidates
   were derived from the 38 Swedish-language records only - no guessed
   translations.
3. **Validate** every candidate against all 2,944 records: hits, precision
   proxy, per-category hit breakdown, and example false hits.
4. **Prune** at the stated thresholds and record why notable candidates fell.

Matching semantics (implemented in `validate_keywords.py`): case-insensitive
whole-word/phrase match on title + llm_quote; `*` in a keyword matches any
word-character suffix (`senolytic*` matches "senolytics"); spaces match any
whitespace run. Substring matching without word boundaries was rejected
because it inflates "aging" with "imaging", "managing" and "packaging".

## Thresholds and validation results

Keep a keyword if precision >= 0.60 and hits >= 3 (English) or hits >= 1
(Swedish - only 38 Swedish-language records exist, so Swedish stats are thin
and every entry with fewer than 5 hits carries `low_evidence: true`). Spelling
variants of a kept keyword (`calorie restriction`, `hallmarks of ageing`,
`end-of-life`) are kept regardless of hit count and marked `variant_of`.

`python3 classifier/validate_keywords.py` output on the recovered corpus:

| category | en keywords | sv keywords | coverage of category records |
| --- | --- | --- | --- |
| fundamental_aging | 33 | 1 | 0.549 |
| intervention | 10 | 1 | 0.396 |
| age_related_disease | 28 | 8 | 0.677 |
| care | 16 | 6 | 0.624 |

Coverage = share of the category's LLM-labelled records matched by at least
one of its kept keywords. It is deliberately partial: these keywords are
precision instruments for classification and query construction, not the
recall net. `intervention` is the weakest category (111 records in the
corpus) and its coverage reflects that; expect to lean on the classifier
rather than keywords there.

## Trap terms and notable exclusions

Full list with per-term stats and example false hits in `keywords.json` under
each category's `trap_terms`. The headline traps:

| term | hits | precision for its naive category | what actually matches |
| --- | --- | --- | --- |
| `aging` (bare) | 963 | 0.60 (fundamental_aging) | 187 ambiguous hits: battery, materials and infrastructure ageing; 124 disease studies that merely mention aging (annotation-guide edge rule 2) |
| `ageing` (bare) | 241 | 0.29 | the British spelling skews to SweCRIS/CORDIS technical records - "Accelerated ageing and voltage disturbances", Li-ion battery ageing |
| `longevity` (bare) | 113 | 0.37 | "productive longevity" in animal breeding, work longevity, component longevity |
| `accelerated ageing` | 4 | 0.25 | the electrical-components trap class named in the task brief |
| `senolytic*` | 19 | 0.47 (intervention) | senolytics research splits between mechanism, therapy and disease application |
| `geroscience` | 23 | 0.39 (fundamental_aging) | field name spanning fundamental_aging and intervention |
| `healthspan` | 59 | 0.49 | splits 29/26 between fundamental_aging and intervention |
| `chemotherapy` | 6 | 0.17 (age_related_disease) | corpus hits are chemotherapy-induced senescence studies, labelled fundamental_aging |
| `older adults` | 84 | 0.20 (care) | population descriptor; its largest share is age_related_disease |
| `elderly` (bare) | 47 | 0.34 (care) | spreads across every category |
| `åldrande` (bare, sv) | 17 | 0.24 | spreads across all five categories, including "åldrande i litium-jonbatterier" |
| `äldre` (bare, sv) | 11 | 0.27 (care) | journals, conferences, population studies |

Other pruned candidates, with their measured precision: `anti-aging` (0.42),
`dietary restriction` (0.58 - mechanistic studies land in fundamental_aging),
`slow aging` (0.33), `lifespan extension` (0.00, n=2), `extend healthspan`
(0.50), `autophagy` (0.52), `dna damage` (0.52), `dna repair` (0.25),
`brain aging` (0.56), `aging brain` (0.57), `cognitive decline` (0.51),
`neurodegenerat*` (0.58), `healthy aging` (0.42), `healthy ageing` (0.24),
`aging population` (0.17), `population aging` (0.00), `geriatric*` (0.14),
`gerontolog*` (0.13). Terms with zero corpus hits were dropped rather than
guessed at (`stem cell exhaustion`, `nad+`, `spermidine`, `assisted living`,
`hemtjänst`, `benskörhet`).

The bare trap terms stay valuable as broad-net search terms - they are in
`meta.broad_net` with their measured category spread. Three
`exclusion_markers` (`battery`, `li-ion`, `aging infrastructure`, 95-100%
ambiguous) can pre-filter obvious non-biology hits before classification.

One Swedish caveat: `ålderssjukdom*` (age-related disease) matches via the
funder prefix "[Stiftelsen för ålderssjukdomar vid KI]" in titles rather than
project text, but it is sound Swedish search vocabulary regardless.

## Per-source query guidance

**SweCRIS** (855 corpus records). Free-text search over projects; the public
API at `swecris-api.vr.se` takes a `searchText` parameter (the same parameter
the SweCRIS web UI uses; an API token is published on vr.se). Query once per
broad-net term, in both English and Swedish - SweCRIS abstracts appear in
either language. Minimum Swedish net: `åldrande`, `äldre`, `senescens`,
`livslängd`, `ålderssjukdom`, `äldreomsorg`, `demens`. Expect the heaviest
trap load here: Swedish Energy Agency battery/materials-ageing grants dominate
the false hits, so apply the exclusion markers before classification.

**CORDIS** (558 corpus records). Do not query per keyword: download the bulk
projects dataset (CSV/JSON from `cordis.europa.eu/data`, EN titles and
objectives) once, then filter locally with the broad net and classify. This
sidesteps API rate limits and makes runs reproducible; record the download
date. Watch for agriculture: "productive longevity" in animal-breeding
projects is the main CORDIS trap.

**NIH RePORTER** (1,531 corpus records). POST to
`api.reporter.nih.gov/v2/projects/search` with
`criteria.advanced_text_search`: set `search_field` to
`"projecttitle,abstracttext,terms"` and `search_text` to broad-net terms
(quoted phrases supported, `and`/`or` operators available); page with
`offset`/`limit`. English only. NIH text is the cleanest of the three sources
(US spelling "aging" throughout, few engineering traps), but disease-institute
grants that merely mention aging are the dominant false-positive class - this
is where the classifier's trap handling matters most.

For all three: log every query string and date, keep raw result counts before
and after filtering, and let the classifier - not the query - decide the
category.

## Limitations

- Precision is measured against unverified LLM labels (see caveat above).
- The matched text is title + the LLM's chosen quote, not the full abstract;
  precision on full abstracts will differ (likely lower - more incidental
  mentions).
- Swedish evidence is 38 records; treat every `low_evidence` Swedish keyword
  as provisional until live SweCRIS results are classified.
- The corpus itself was collected by some ageing-related search, so keyword
  stats reflect performance *within* an ageing-flavoured pool, not against a
  whole funding database.
