# External validation against UKHRA 2022

**Judging alignment (`AGENTS.md`):** this is an external check on the
classification method. Everything else in the repo measures our classifiers
against our own labels or against each other. This measures a classifier
against trained human coders who never saw our work.

**What now works, with evidence:** a keyword cancer screen scored against
11,664 human-coded UK research awards gets precision 0.770, recall 0.839,
F1 0.803. Reproduce with the commands below; the tests run without the
download.

**What remains incomplete:** this validates the method on cancer, not on
ageing. HRCS has no ageing category, so the funding-gap ratio still has no
external check and still depends on human review.

## Why this dataset

Andrew Steele suggested the UK Health Research Analysis (UKHRA) and its
Health Research Classification System (HRCS) as a comparator. The 2022
public dataset holds 18,023 UK health research awards worth £2.79bn, and
each row carries the award's own title and abstract alongside codes assigned
by trained human coders on two axes: Health Category (disease area) and
Research Activity (what kind of work it is).

Text and human labels on the same row is what makes this usable. A
classifier can be run on exactly the text a human coder read, and compared.
No record linkage against Gateway to Research is needed, which removes the
coverage-mismatch problem that would otherwise dominate the analysis.

## What we excluded, and why

Two filters, both of which make the test harder to pass rather than easier:

- **Algorithmically coded rows (5,126 of 18,023).** The `CodingType` column
  distinguishes awards coded by a person from awards coded by the Dimensions
  algorithm. Scoring against the latter would measure agreement between two
  classifiers and call it human validation. Only the 12,543 `Manual` rows
  are treated as ground truth.
- **Redacted rows (879 of 12,543).** Some funders, mostly MRC studentships,
  publish codes but withhold the text, leaving the literal string "Award
  abstract not available in public dataset" where the abstract should be. No
  classifier can read those. They are excluded and counted, and the report
  also carries `cancer_including_redacted_rows` so the effect of the
  exclusion is auditable: leaving them in drops recall from 0.839 to 0.780.

That leaves 11,664 scoreable awards.

## Cancer result

The baseline screen in `ukhra/cancer_terms.py` against the human "Cancer and
Neoplasms" Health Category:

| | precision | recall | F1 |
| --- | --- | --- | --- |
| Cancer in any Health Category slot | 0.770 | 0.839 | 0.803 |
| Cancer as the primary Health Category | 0.724 | 0.859 | 0.786 |
| Including redacted rows (pessimistic) | 0.770 | 0.780 | 0.775 |

Confusion matrix for the headline row: 1,818 true positives, 544 false
positives, 348 false negatives, 8,954 true negatives. In funding terms it
would wrongly include £133.7m and miss £72.4m.

### Where the errors come from

**False positives are passing mentions.** Of the 544, the largest group
(202) are awards humans coded as "Generic Health Relevance" — work that
names cancer somewhere in the abstract without being cancer research. One
example is a public-engagement award titled "Experiencing the micro-world -
a cell's perspective". That is the known failure mode of keyword matching:
classifying on the presence of a word rather than on the stated research
aim.

Which is the useful part. It is a quantified argument for a classifier that
reads for aims rather than vocabulary, and it sets the number such a
classifier has to beat: 0.803 F1. Point the benchmark at any other
classifier with `--classifier module:function` and compare.

**False negatives are mostly missing evidence, not missing vocabulary.**
Once redacted rows are removed, the remaining 348 are largely awards
describing tumour biology in terms the lexicon does not carry.

## A finding for the labelling taxonomy

HRCS splits Research Activity into eight groups. Mapped against a
prevention-versus-consequences axis:

| HRCS Research Activity group | awards | apportioned £ |
| --- | ---: | ---: |
| 1 Underpinning | 1,927 | 361,864,819 |
| 2 Aetiology | 4,610 | 646,006,567 |
| 3 Prevention | 849 | 165,869,933 |
| 4 Detection and Diagnosis | 2,026 | 223,265,364 |
| 5 Treatment Development | 1,763 | 236,994,285 |
| 6 Treatment Evaluation | 2,055 | 306,107,425 |
| 7 Disease Management | 1,279 | 121,485,812 |
| 8 Health Services | 1,605 | 204,699,405 |

Reading groups 4–7 as "fighting the consequences" and group 3 as
"prevention", prevention takes 15.7% of the mapped funding: £166m against
£888m.

Groups 1 and 2, underpinning biology and aetiology, hold £1.21bn between
them, more than prevention and consequences combined, and they sit on
neither side of the split. The benchmark leaves them unmapped rather than
assigning them, because that is exactly the territory a grant on the biology
of ageing occupies.

So the largest single block of UK health research funding falls in the zone
such a taxonomy is least decided about. Any human labelling round using a
prevention/consequences split needs to tell labellers what to do with a
mechanism study that names no disease and proposes no intervention.
Otherwise the disagreement rate on the biggest category will be noise.

## Negative control: the ageing classifier over UKHRA

`ukhra/negative_control.py` runs `ratio/classify.py` across the same 11,664
awards. UKHRA is general UK health research, not selected by any ageing
keyword search, so it is close to a null sample: confident ageing labels here
are candidate relevance-gate leaks, findable without a single new human label.

This makes no accuracy claim. HRCS has no ageing category, so there is nothing
to be right or wrong against. It surfaces labels worth a human look, and says
which keywords drove them.

| label | awards |
| --- | ---: |
| not_relevant | 6,203 |
| age_related_disease | 4,531 |
| ambiguous | 411 |
| care | 257 |
| fundamental_aging | 207 |
| intervention | 41 |
| social_population_aging | 14 |

**The denominator is the thing to look at.** 38.8% of all UK health research
lands in `age_related_disease`, driven by bare disease names: `cancer` alone
accounts for 1,933 of those 4,531, then `stroke` (353), `dementia*` (333),
`cardiovascular disease` (324), `obesity` (304), `heart failure` (293). Since
the funding-gap ratio divides by all substantive categories, a boundary that
catches a large share of general biomedicine on a disease mention inflates the
denominator and shrinks the ratio.

That is the same "fighting the consequences has no ceiling" problem the
Research Activity table above shows from the human side, arriving from the
classifier side.

**Ratio read on a corpus with no ageing focus: 0.062.** Not a target and not
an error rate. It is the floor the instrument reads on general health research,
and the per-region ratios reported elsewhere should be read against it.

**51 numerator labels landed on human Health Categories with no plausible
ageing framing** (Infection, Reproductive Health and Childbirth, Oral and
Gastrointestinal, Renal and Urogenital, Congenital Disorders). Three worth
fixing first:

- `rapamycin` → `intervention` on a *Plasmodium falciparum* malaria study.
  Rapamycin is a reagent there, not a geroprotector.
- `malnutrition` → `intervention` on environmental enteric dysfunction, a
  childhood gut disease.
- `dna methylation` → `fundamental_aging` on a reproductive health biobank.
  Generic molecular biology, not an epigenetic clock.

These are the same shape as the gate leaks already fixed by hand elsewhere
(battery "cell", NMR "mouse", antifouling). The difference is that this finds
them at 11,664-record scale instead of by mining examples.

## Reproduce

The dataset is not committed (`AGENTS.md`: do not commit raw datasets).

```sh
curl -sL -o /tmp/UKHRA2022.xlsx \
  https://hrcsonline.net/wp-content/uploads/2024/01/UKHRA2022_HRCS_public_dataset_v1-2_30Jan2024.xlsx
python3 -m ukhra.benchmark --xlsx /tmp/UKHRA2022.xlsx --out ukhra/results.json
python3 -m ukhra.negative_control --xlsx /tmp/UKHRA2022.xlsx \
  --out ukhra/negative_control_results.json
python3 -m unittest discover -s ukhra -t . -p "test_*.py"
```

`ukhra/xlsx.py` is a minimal stdlib XLSX reader written for this, since
openpyxl is not available and the repo stays stdlib-only. `ukhra/results.json`
and `ukhra/negative_control_results.json` are the committed outputs of the
runs above.

## Source and licence

UK Health Research Analysis 2022, UK Clinical Research Collaboration (2023).
Data: <https://hrcsonline.net/reports/analysis-data/>, file
`UKHRA2022_HRCS_public_dataset_v1-2_30Jan2024.xlsx`, retrieved 2026-09-12.
Released under Creative Commons. HRCS Online ask to be contacted about
re-analysis of the public datasets and require formal citation. Do both
before any of this is published or presented as a result.

## What this does not show

- It does not validate ageing classification. HRCS has no ageing category.
  The claim it supports is narrower: the method reproduces human coding on a
  category where ground truth exists, which makes ageing output more
  credible without measuring it.
- It scores a cancer keyword screen, not the ageing classifier in
  `ratio/classify.py`.
- UKHRA is UK-only, 2022, health research only. It is not a comparator for
  the SweCRIS or CORDIS totals elsewhere in this repo.
- Funding figures are 2022 annualised values in GBP and are not apportioned
  by Health Category percentage, so the £ figures above are coarser than the
  counts.
