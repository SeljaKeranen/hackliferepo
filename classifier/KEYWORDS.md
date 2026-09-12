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
  recomputes every stat from the corpus and fails (exit 1) if the JSON has
  drifted, a keyword misses its threshold, a `variant_of` reference is broken,
  or a term is malformed - in `--update` mode too, which rewrites the stats
  first and then still reports violations. Run:
  `python3 classifier/validate_keywords.py`; matching unit checks:
  `python3 classifier/validate_keywords.py --self-test`.

## The governing principle: search broad, classify precise

Live database searches should maximise recall with the category-agnostic
`meta.broad_net` terms (`aging`, `ageing`, `senescence`, `longevity`, and so
on, plus Swedish equivalents). The per-category keywords then do the precise
work locally: a downstream classifier assigns categories to whatever the broad
net catches. Searching each database directly with narrow category keywords
would silently drop everything the categories' vocabularies miss - the
per-category coverage numbers below (40-68%) show how much that would lose.

## Classification rubric: step 0 is relevance

Before assigning any category, the classifier or judge must first ask whether
the record has anything to do with longevity, human ageing, or ageing biology
at all. A record that matched the broad search net but concerns
material/component/infrastructure ageing, a non-ageing use of a matched term,
or an otherwise unrelated topic gets the output category `not_relevant` - it
is never forced into a substantive category. `not_relevant` is distinct from
`ambiguous`: `ambiguous` stays reserved for genuinely on-topic records the
text does not let you place (the annotation guide's "insufficient or
borderline information").

Worked examples from the corpus's real false hits:

- `swecris:P46678-1_Energi` "Accelerated ageing and voltage disturbances -
  need, possibilities and limitations" - matched `ageing`, is about electrical
  component testing: `not_relevant`.
- `swecris:P42789-1_Energi` "Separating the influence of temperature and
  current swing on the ageing of a Li-Ion battery" - matched `ageing`,
  battery chemistry: `not_relevant`.
- `cordis:101000236` "GEroNIMO: Genome and Epigenome eNabled breedIng in
  MOnogastrics" - matched `longevity` via "productive longevity" in livestock
  breeding: `not_relevant`.
- Contrast: "International journal of ageing and later life" is on-topic
  (human ageing) but the text gives no basis for a substantive category:
  `ambiguous`, not `not_relevant`.

The atlas's LLM labels predate this distinction and fold both cases into
`ambiguous`, which is why the `exclusion_markers` and trap-term stats in
`keywords.json` measure against `ambiguous`; a future re-labelling should
separate the two.

## Evidence base

The corpus is teammate Max's Aging Funding Atlas: 2,944 grant records
(1,531 NIH RePORTER, 855 SweCRIS, 558 CORDIS), each with a title, an LLM
category (`llm_category`), an LLM-chosen supporting quote (`llm_quote`), and a
rule-based category from keyword rules that were never committed. The atlas
was added in commit `2e59b27` and lives in the tree at
`data/Track3_C2/output/` (commit `4061bff` deleted a duplicate top-level
`Track3_C2/` copy, not this one; the live files are byte-identical to the
`2e59b27` blobs). The validator reads the live directory by default and falls
back to history if it disappears:

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

Matching semantics (implemented in `validate_keywords.py`, unit-checked by
`--self-test`): case-insensitive whole-word/phrase match on title + llm_quote;
`*` at the end of a word matches any word-character suffix (`senolytic*`
matches "senolytics"); spaces match any whitespace run; everything else,
including hyphens, matches literally (`long-term care` does not match "long
term care" - no such variant occurs in this corpus, but expect it in live
data). Substring matching without word boundaries was rejected because it
inflates "aging" with "imaging", "managing" and "packaging".

## Thresholds and validation results

Keep a keyword if precision >= 0.60 and hits >= 3 (English) or hits >= 1
(Swedish - only 38 Swedish-language records exist, so Swedish stats are thin).
Every kept keyword with fewer than 5 hits, in either language, carries
`low_evidence: true`. Spelling
variants of a kept keyword (`calorie restriction`, `hallmarks of ageing`,
`end-of-life`) are marked `variant_of` and skip only the hit-count floor:
they must reference a kept non-variant term, match at least one record, and
still meet the precision threshold.

`python3 classifier/validate_keywords.py` output on the recovered corpus:

| category | en keywords | sv keywords | coverage of category records |
| --- | --- | --- | --- |
| fundamental_aging | 37 | 1 | 0.555 |
| intervention | 11 | 1 | 0.414 |
| age_related_disease | 58 | 8 | 0.770 |
| care | 16 | 6 | 0.624 |

English counts include the 35 HALD-derived keywords described below (marked
`source: "HALD"` in the JSON); the rest are the seed lexicon.

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
guessed at (`stem cell exhaustion`, `spermidine`, `assisted living`,
`hemtjänst`, `benskörhet`). `nad+` has 5 hits but splits 3
age_related_disease / 2 fundamental_aging, so it fails as the intervention
keyword it is usually proposed as.

The bare trap terms stay valuable as broad-net search terms - they are in
`meta.broad_net` with their measured category spread. Three
`exclusion_markers` (`battery`, `li-ion`, `aging infrastructure`, 95-100%
ambiguous) can pre-filter obvious non-biology hits before classification.

One Swedish caveat: `ålderssjukdom*` (age-related disease) matches via the
funder prefix "[Stiftelsen för ålderssjukdomar vid KI]" in titles rather than
project text, but it is sound Swedish search vocabulary regardless.

## HALD enrichment

The lexicon was enriched from HALD, the Human Aging and Longevity Dataset
(CC BY 4.0), a text-mined knowledge graph built from 339,918 PubMed abstracts:
entity list plus aging/longevity biomarker files from the Figshare bulk data
(doi:10.6084/m9.figshare.22828196.v6; paper
[10.1038/s41597-023-02781-0](https://doi.org/10.1038/s41597-023-02781-0);
portal https://bis.zju.edu.cn/hald). Entity names (genes, diseases,
metabolites, biomarkers) were treated as candidate keywords and validated
exactly like the seed terms.

The funnel, recorded in `meta.hald_enrichment`: 6,922 entity names -> 6,891
usable candidates (after dropping duplicates of existing lexicon terms, terms
under 3 characters, and malformed terms) -> 255 with at least one corpus hit
-> 62 with >= 3 hits -> 40 clearing the precision threshold toward one of the
four categories -> **35 admitted** with `source: "HALD"`. Most HALD entities
have zero grant hits, as expected: molecular-level entities rarely appear in
grant titles and quote snippets.

Five threshold-clearing terms were excluded as live-search traps and moved to
`trap_terms` with their stats: `disease` (too generic), `app` (the gene APP
clears the proxy, but live text says application), `shock` (heat-shock
contexts only), `clock` (already covered by `epigenetic clock*`; bare form
matches scheduling), `fatigue` (the material-fatigue engineering trap, same
class as `accelerated ageing`). Some admissions overlap seed stems
(`alzheimer disease` under `alzheimer*`, `myocardial infarction` under
`myocardial`); they are kept because each carries its own stats and some
plural forms (`cardiovascular diseases`) are not covered by the singular seed
term. Gene symbols (`apoe`, `tert`, `myc`, `cgas`, `tfeb`) ride on word
boundaries and are `low_evidence` at 3-5 hits each.

## How to use this lexicon

- **Broad-net search recipes.** Query each API with `meta.broad_net` terms
  only, never category keywords: SweCRIS `searchText` once per term in both
  languages; CORDIS bulk download filtered locally against the broad net; NIH
  RePORTER `advanced_text_search` with the English net OR-ed in one query
  where length limits allow. Log query strings and dates.
- **Relevance gate, then rubric.** Classify every fetched record with step 0
  first (`not_relevant` for material/component/infrastructure ageing and other
  off-topic matches), then assign one of the four substantive categories or
  `ambiguous` per the annotation guide.
- **HALD entities as a relevance signal.** A record matching any HALD entity
  name is evidence the text is biomedical: useful as a feature at the
  relevance gate (a battery-ageing grant matches the broad net but no HALD
  entity).
- **Trap terms as negative filters.** `exclusion_markers` (battery, li-ion,
  aging infrastructure) can auto-route obvious engineering records to
  `not_relevant` before classification; per-category `trap_terms` tell the
  classifier which surface matches must NOT decide a category on their own.
- **Precision as priors.** Each keyword's precision proxy is a defensible
  prior: a record matched only by `cancer` (0.65) deserves lower classifier
  confidence than one matched by `epigenetic clock*` (1.0). Combining matched
  keywords' precisions gives a transparent confidence score.
- **Funding-ratio hookup.** The headline metric divides money as
  numerator = `fundamental_aging` + `intervention` grants, denominator = all
  four substantive categories; `not_relevant` records are excluded entirely
  and `ambiguous` reported separately as an honesty band, not silently folded
  into either side.

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
