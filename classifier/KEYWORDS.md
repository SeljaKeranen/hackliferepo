# Search-keyword lexicon for the "follow the money" grant classifier

A validated lexicon of search keywords for the Track 3 challenge 2 question:
how much public research funding targets the biology of ageing versus
age-related disease versus elderly care. Four categories and their edge rules
come from the annotation guide at
`data/Track3_C2/benchmark/ANNOTATION_GUIDE.md` in commit `2e59b27`:
`fundamental_aging`, `intervention`, `age_related_disease`, `care`. A fifth,
`social_population_aging`, was added 12 September 2026 and is defined in this
file's rubric section (the annotation guide lives only in the deleted atlas
tree, so this file is the single owner of the definition on `main`). The
lexicon covers all five; `ambiguous` is an outcome, not a search target.

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
per-category coverage numbers below (41-77%) show how much that would lose.

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

## Rubric rule: mechanism versus intervention

After the relevance gate, the hardest recurring boundary is between
`fundamental_aging` and `intervention`. The rule: an `intervention` grant
funds **developing or testing an intervention** aimed at slowing or reversing
ageing; a grant **studying an intervention's mechanism** - how it works, what
pathways it engages, what it reveals about ageing biology - is
`fundamental_aging`, no matter how prominently the title names the
intervention.

The trap-term stats show why this must be a rubric rule rather than more
keywords: `senolytic*` (precision 0.474), `dietary restriction` (0.583),
`lifespan extension` (0.0), and `extend healthspan` (0.5) all fail as
intervention keywords precisely because mechanistic studies of interventions
land in `fundamental_aging`. They stay trap terms for keyword purposes; the
rubric now tells the classifier how to decide such records.

Worked examples from the corpus's real trap false hits:

- `reporter:5R01AG052606-06` "Effects of dietary restriction on age-related
  neurophysiological adaptations" - uses dietary restriction as a probe into
  ageing neurophysiology: `fundamental_aging`.
- `cordis:894917` "Exploiting superlongevous model mammals to explore new
  links between protein and organelle homeostasis and lifespan" - matched
  `lifespan extension`, studies mechanism: `fundamental_aging`.
- `cordis:101118919` "Learning from Bats: New Strategies to Extend Healthspan"
  - despite the intervention-flavoured title, the work is comparative biology
  of ageing mechanisms: `fundamental_aging`.
- Contrast: `swecris:2025-02364_VR` "Unlocking Cognitive Health: How Metformin
  Slows Brain Aging Through Precision Medicine" - tests a drug to slow ageing:
  `intervention`.

## The social_population_aging category

Added 12 September 2026. Social, behavioral and population-ageing research:
retirement and pensions, working-life and labour-market studies of older
workers, loneliness and social isolation research, population ageing and
demography, socioeconomic conditions in later life, ageism, and healthy-ageing
policy studies. The motivation is measured: 53% of CORDIS and 45% of Swecris
records carry the `ambiguous` label, and much of that share is social and
population-ageing research that had no home among the original four
categories.

Edges:

- **Versus `care`**: care is the delivery and organisation of services to
  older people (nursing homes, home care, caregiving, welfare technology);
  social_population_aging is research *about* ageing societies and older
  people's lives. A loneliness *intervention delivered through care services*
  is `care`; a study of *retirement's effect on social networks* is
  social_population_aging.
- **Versus `age_related_disease`**: epidemiology of a disease in older
  populations stays `age_related_disease`; studies of socioeconomic ageing
  outcomes without a disease target land here.
- **Versus `not_relevant`**: the record must still concern human ageing -
  step 0 applies first, unchanged.
- **Funding ratio**: this category counts **only in the denominator** of the
  funding-gap ratio, never the numerator. It represents money going to
  understanding ageing societies, not to slowing ageing.

### Co-occurrence rule: these keywords never stand alone

The category carries `requires_ageing_anchor: true` in `keywords.json`. Its
keywords (`retirement`, `pension*`, `labor market`, `working life`,
`living conditions`, ...) are ordinary social-science vocabulary; only the
combination with ageing makes them this category. Two consequences:

- **Live search**: query with the ageing broad net (optionally AND-ed with
  social terms), never with social terms alone - standalone they flood results
  with general labour-market and social research.
- **Classification**: a social keyword counts toward
  `social_population_aging` only when an ageing anchor - a `meta.broad_net`
  term or an explicit older-adults reference - is also present in the record.

This is the same co-occurrence Jan's classifier encodes: his SOCIAL regex
assigns `other_aging_research` only when an AGE-net term also matches the
record (SOCIAL && AGE in `funding/classify.py` on `codex/ageing-funding-gap`).

The reason the per-keyword precision figures don't contradict this: they were
measured inside the atlas corpus, which was itself collected through an
ageing-related search net, so every matched record already carried an implicit
ageing anchor. The figures say nothing about how these terms behave in open
search (see the methodology caveat under Evidence base). A handful of `care`
terms with the same property (`home care`, `caregiv*`, `social services`, ...)
carry a per-term `requires_ageing_anchor: true`; age-anchored care terms
(`elderly care`, `nursing home*`, `care of older`, `äldreomsorg*`, ...) do
not need one.

Correspondence to teammate Jan's taxonomy: Jan's branch
(`codex/ageing-funding-gap`, `funding/classify.py`) has the equivalent
category `other_aging_research`, assigned by a SOCIAL regex (retirement,
pension, social isolation, loneliness, healthy ag(e|i)ng, cognitive ag(e|i)ng,
population ag(e|i)ng, social determinants, ageism, later life, housing
environments). The name `social_population_aging` was chosen deliberately -
it says what the category contains rather than what it is not - but the two
are the same bucket; a merge of the taxonomies should map them 1:1. Note the
difference in mechanics: Jan's regex terms are *assignment* rules in his
classifier, while this lexicon admits only terms that survive corpus
validation - most of Jan's SOCIAL terms failed here (see the funnel below).

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

**Caveat: every precision figure was measured inside an ageing-filtered
corpus and does not transfer to standalone open search.** The atlas was
collected through an ageing-related search net, so every record a keyword can
hit is already ageing-adjacent. A keyword's measured precision is conditional
on that pool; used as a standalone query against a whole funding database, the
same keyword can flood with unrelated research. This applies to **all**
categories' figures, and it bites hardest where the keyword's surface meaning
is not about ageing at all - which is why `social_population_aging` (and a few
`care` terms) carry `requires_ageing_anchor: true` and must only be used in
co-occurrence with the broad net.

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
| fundamental_aging | 39 | 1 | 0.562 |
| intervention | 11 | 1 | 0.414 |
| age_related_disease | 56 | 8 | 0.770 |
| care | 16 | 6 | 0.624 |
| social_population_aging | 11 | 1 | 0.048 |

`social_population_aging` has no LLM label of its own - the atlas vocabulary
predates it - so its precision and coverage are measured against
`llm_category == "ambiguous"` (`meta.proxy_labels` in the JSON, hardcoded as
`PROXY_LABEL` in the validator). That proxy cuts both ways: the 0.048 coverage
understates badly because `ambiguous` also holds the entire not_relevant
engineering pool (batteries, materials, infrastructure), and a term can clear
the precision floor by matching engineering records. Every admitted keyword's
hits were therefore additionally spot-checked by title; terms that cleared the
proxy numerically but failed the spot-check are recorded in the category's
`trap_terms` (see the funnel section below).

English counts include the 33 HALD-derived keywords and the 2
longevity-factor terms described below (marked `source: "HALD"` and
`source: "longevity_keywords_ext.md"` in the JSON); the rest are the seed
lexicon.

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
`aging population` (0.17), `geriatric*` (0.14),
`gerontolog*` (0.13). Terms with zero corpus hits were dropped rather than
guessed at (`stem cell exhaustion`, `spermidine`, `assisted living`,
`hemtjänst`, `benskörhet`). `nad+` has 5 hits but splits 3
age_related_disease / 2 fundamental_aging, so it fails as the intervention
keyword it is usually proposed as.

Two updates from the 12 September 2026 category addition:

- The intervention traps `senolytic*`, `dietary restriction`,
  `lifespan extension` and `extend healthspan` stay traps for keyword
  matching, but the rubric's mechanism-vs-intervention rule (above) now tells
  the classifier how to decide the records they match; each JSON entry carries
  a note to that effect.
- `healthy aging`, `healthy ageing` and `cognitive decline` were re-evaluated
  against `social_population_aging` on the theory that their old failure was
  having no home. They still spill (ambiguous shares 0.195, 0.12 and 0.051
  respectively - most of their hits are biology, intervention and disease
  records, not social research), so they stay trapped. `population aging`
  did move: formerly a `care` trap at precision 0.0, its ambiguous hits are
  social/population-ageing research, and it now sits in
  `social_population_aging` at 0.667 (n=3, `low_evidence`). Its spelled-out
  sibling `aging population` stays a care trap and fails the new category too
  (0.304).

The bare trap terms stay valuable as broad-net search terms - they are in
`meta.broad_net` with their measured category spread. Three
`exclusion_markers` (`battery`, `li-ion`, `aging infrastructure`, 95-100%
ambiguous) can pre-filter obvious non-biology hits before classification.

One Swedish caveat: `ålderssjukdom*` (age-related disease) matches via the
funder prefix "[Stiftelsen för ålderssjukdomar vid KI]" in titles rather than
project text, but it is sound Swedish search vocabulary regardless.

## HALD enrichment

The lexicon was enriched from HALD, the Human Aging and Longevity Dataset
(Wu, Feng, Hu, Zhou, Li, Zhang, Hu, Chen, Chao, Ni and Chen; CC BY 4.0;
entity names used as keyword candidates, otherwise unmodified), a text-mined
knowledge graph built from 339,918 PubMed abstracts:
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
four categories -> **33 admitted** with `source: "HALD"`. Most HALD entities
have zero grant hits, as expected: molecular-level entities rarely appear in
grant titles and quote snippets.

Seven threshold-clearing terms were excluded as live-search traps and moved
to `trap_terms` with their stats: `disease` (too generic), `app` (the gene
APP clears the proxy, but live text says application), `shock` (heat-shock
contexts only), `clock` (already covered by `epigenetic clock*`; bare form
matches scheduling), `fatigue` (the material-fatigue engineering trap, same
class as `accelerated ageing`), `tert` (collides with the tert- prefix of
organic chemistry - tert-butyl electrolytes are battery-domain text), and
`myc` (c-Myc/myc-tag saturates unrelated methods sections). The corpus proxy
cannot see these collisions because the atlas contains almost no general
chemistry or methods-heavy text; that asymmetry is exactly why admitted
gene symbols stay `low_evidence`. Some admissions overlap seed stems
(`alzheimer disease` under `alzheimer*`, `myocardial infarction` under
`myocardial`); they are kept because each carries its own stats and some
plural forms (`cardiovascular diseases`) are not covered by the singular seed
term. The remaining gene symbols (`apoe`, `cgas`, `tfeb`) are unlikely to
collide with non-biomedical vocabulary and are `low_evidence` at 3-5 hits
each; `glucose` and `obesity` sit exactly at the 0.60 precision floor and
carry warning notes.

## Longevity-factor enrichment (`longevity_keywords_ext.md`)

A curated external candidate list of longevity and mortality factors (social,
behavioral, psychological, environmental, functional and biological; each row
citing its papers) was run through the same validation pipeline. It proposes
about 118 unique terms, and the funnel shows why it is not a category keyword
list:

- 8 terms are already covered by the lexicon (`obesity`,
  `caloric/calorie restriction`, `biological age`, `genomic instability`,
  `proteostasis`, `mitochondrial dysfunction`, `cellular senescence`,
  `frailty`); `telomere attrition` sits inside `telomere*` and
  `epigenetic clock` inside `epigenetic clock*`.
- 2 terms were admitted to `fundamental_aging` with
  `source: "longevity_keywords_ext.md"`: `dna methylation` (27 hits,
  precision 0.778) and `nutrient sensing` (3 hits, 1.0, `low_evidence`).
  Fundamental-ageing coverage rises 0.555 -> 0.562.
- The rest fail the thresholds or have zero corpus hits: `chronic inflammation`
  (11, 0.545), `senescent cells` (42, 0.190), `senolytics` (6, 0.500 - the
  list proposes it as an intervention keyword, but the corpus keeps it a trap
  term: the research splits between mechanism, therapy and disease
  application), `epigenetic alterations` (3, 0.0), and `macroautophagy`,
  `dysbiosis`, `pace of aging`, `dna methylation age`,
  `homeostatic dysregulation`, `grip strength` at 1 hit each. Zero hits:
  `stem cell exhaustion`, `intercellular communication`, `DunedinPACE`,
  `PhenoAge`, `GrimAge`, `senescent cell clearance`, `dasatinib`,
  `quercetin`, `walking speed`, `chair rising`, `standing balance`,
  `physical capability`, `frailty syndrome`, `hand grip strength`,
  `gait speed`.
- About 80 terms are social, behavioral, environmental or lifestyle mortality
  factors (`loneliness`, `smoking`, `alcohol consumption`, `sleep duration`,
  `air pollution`, `green space`, `socioeconomic status`, `adverse childhood
  experiences`, ...). At the time they had no home among the four grant
  categories; admitting them would drag precision below threshold and change
  the lexicon's mission from ageing-biology funding to all-cause-mortality
  research. The social subset was re-run as seed candidates for
  `social_population_aging` (next section); the lifestyle/environmental
  mortality factors (`smoking`, `air pollution`, `sleep duration`, ...) still
  fail there - their corpus hits are disease epidemiology, not social ageing
  research. British spellings from the list (`behavioural`, `neighbourhood`)
  were not added; the corpus uses US spelling.

The admitted stats come from the same unverified LLM labels as the rest of
the lexicon; `nutrient sensing` is `low_evidence` and provisional.

## social_population_aging derivation (12 September 2026)

Candidates came from three sources, then went through the standard funnel
(seed, expand, validate, prune - thresholds unchanged: precision >= 0.60
against the `ambiguous` proxy, hits >= 3 English / >= 1 Swedish,
`low_evidence` under 5 hits):

1. The social/behavioral terms the longevity-factor funnel above excluded
   (`loneliness`, `social isolation`, `retirement`, `pension`, `ageism`,
   `population aging/ageing`, `healthy aging`, `cognitive aging`,
   `later life`, `socioeconomic`, ...).
2. Jan's SOCIAL regex terms from `funding/classify.py` on
   `codex/ageing-funding-gap`.
3. Corpus expansion: the same log-odds method as the seed lexicon, ambiguous
   records versus all others. Its top terms are engineering vocabulary
   (`batteries`, `water`, `climate`, `infrastructure`) - direct evidence of
   the proxy contamination described under the validation table - but it also
   surfaced `working life`, `retirement`, `societies` and the labour-market
   cluster. Swedish candidates were derived from the
   Swedish-language records only, as before.

The funnel: 97 English and 30 Swedish candidate terms tested -> 21 cleared
the numeric thresholds (two of them bare/wildcard duplicates of an admitted
stem) -> hits of every clearing term spot-checked by title -> **9 English
keywords + 2 spelling variants + 1 Swedish keyword admitted**; the 7
spot-check rejections are recorded as trap terms or noted below.

Spot-check rejections of numerically clearing terms (English ones in
`trap_terms` with stats): `ageing population` (0.643 - biomedical grants use
"our ageing population" as motivation boilerplate), `aging research` (0.643 -
hits are research infrastructure, training programs and journals, and live
text floods with center names), `participation` (0.778 - bare word floods
live grant text), `older age` (0.60 exactly, n=5 - bare population
descriptor, same class as the `older adults` trap), `digital*` (0.613 -
clears only because `ambiguous` holds the engineering pool: digital twins for
wastewater plants, OCR of early printed books), `social network*` (0.667,
n=3 - the ambiguous hits are wild-bird social networks and protein "social
network" dynamics).

Notable threshold failures: `loneliness` (0.25 - the corpus's loneliness
records are mostly care interventions and disease studies; care wins the
term) and `social isolation` (0.40, same split), both recorded as traps;
`later life` (0.462), `socioeconomic` (0.364), `wellbeing` (0.538),
`welfare` (0.542), `demograph*` (0.474), `intergenerational` (0.286),
`life course` (0.263), `old age` (0.333). Below the hit floor: `ageism`,
`social exclusion`, `successful ageing`, `time use`, `work longevity`,
`civic` (1-2 hits each) - sound social-ageing vocabulary, too rare in this
corpus to validate; revisit against live data. Swedish candidates from the
Swedish records: only `socioekonomisk*` clears (1 hit, 1.0, `low_evidence`);
`ensamhet` and `pensionering` have zero corpus hits and were dropped rather
than guessed at, `äldreomsorg*` stays in `care`, and bare `samhälle*`
(1 hit, 1.0) was rejected as a live-flood word. `pension*` sits in the
English list on its 3 English-language hits, but the stem also matches
Swedish pension vocabulary in live SweCRIS text.

Everything here inherits the proxy caveat: precision is the share of hits the
LLM labelled `ambiguous`, which is necessary (the category had no label) but
weaker evidence than the other categories' stats. The spot-checks and trap
notes are the compensating control. When records are re-labelled with the new
vocabulary, re-run the validation with a real label.

## How to use this lexicon

- **Broad-net search recipes.** Query each API with `meta.broad_net` terms
  only, never category keywords: SweCRIS `searchText` once per term in both
  languages; CORDIS bulk download filtered locally against the broad net; NIH
  RePORTER `advanced_text_search` with the English net OR-ed in one query
  where length limits allow. Log query strings and dates.
- **Relevance gate, then rubric.** Classify every fetched record with step 0
  first (`not_relevant` for material/component/infrastructure ageing and other
  off-topic matches), then assign one of the five substantive categories or
  `ambiguous`, applying the mechanism-vs-intervention rule at that boundary.
- **HALD entities as a relevance signal.** A record matching one of the 33
  admitted `source: "HALD"` keywords - NOT the raw 6,922-entity list, which
  contains unvetted generic tokens like `disease`, `app` and `tert` - is
  evidence the text is biomedical: useful as a feature at the relevance gate
  (a battery-ageing grant matches the broad net but none of the vetted
  entities). Trap-flagged terms never count as positive relevance signals.
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
  five substantive categories (`social_population_aging` is denominator-only,
  never numerator); `not_relevant` records are excluded entirely and
  `ambiguous` reported separately as an honesty band, not silently folded
  into either side.

## Per-source query guidance

For every source, the query is built from `meta.broad_net` terms - optionally
AND-ed with category keywords to narrow, never category keywords alone. This
matters most for `requires_ageing_anchor` terms (`social_population_aging` and
the flagged `care` terms): live search = (ageing broad net) AND optionally
social terms; classification counts a social keyword only when an ageing
anchor is present in the record.

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
