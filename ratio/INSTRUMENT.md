# Longview research instrument

This implements the team's revised deliverable supplied on 12 September 2026 after its conversation with Andrew. It advances Demo Day architecture, technical execution, evidence and responsible use, and the path to adoption through independent researcher review.

The deliverable is a labeling and disagreement-review instrument. We are not publishing a funding estimate this weekend. The existing pipeline has been run and records have been spot-checked; it has not been properly validated by humans. Andrew's confirmation of the team's interpretation, including the taxonomy, is pending.

## Working taxonomy

The authoritative, versioned rubric is [instrument/taxonomy.json](instrument/taxonomy.json). Both the classifier and the UI read it. Label the stated research purpose as preventing/slowing ageing, fighting the consequences of ageing, neither, or ambiguous. Record low confidence independently.

Our provisional interpretation includes research on fundamental biological ageing in preventing/slowing ageing, even without an intervention. Andrew still needs to confirm that boundary. Research into disease, care, or social consequences needs an explicit ageing connection. A general cancer objective, a drug name, or background motivation is insufficient. Model organisms can study biological ageing; leaf senescence and battery ageing are outside scope. A grant with two clearly competing aims can be ambiguous without low confidence. Missing or truncated evidence can make any judgment low confidence.

We do not convert the earlier seven categories or model-generated “expert” judgments into human labels. Historical artifacts remain available for development and audit. They have no external validation status.

## Build and review

From the repository root, using Python 3.10+:

```sh
python3 -m ratio.instrument.build
python3 -m http.server 8010 --bind 127.0.0.1
```

Open `/ratio/` on the served host. The root page and `/ratio/benchmark/sheet.html` lead to the new instrument. Generated abstracts and predictions live in ignored `ratio/instrument/output/`; build them before hosting. Python's HTTP server is a local preview. For remote use, package the static site and serve that directory through the team's existing host:

```sh
python3 -m ratio.instrument.package outputs/research-instrument-site
```

The package uses an explicit file allowlist. It excludes the full corpus, historical ratios, model caches, credentials and human files. It contains the 60-item collected-text review sample; source attribution and the SweCRIS licence qualification below still apply. Packaging does not deploy or authorize new redistribution.

The labeling page shows the complete text available in the frozen corpus, a dated original source link, four categories, a low-confidence checkbox, and a reason field. It hides predictions and other reviewers' decisions during initial judgment. It does not fetch missing abstracts or add translations. Each researcher uses a reviewer code, attests to independent human review, and exports their completed JSON. Progress is stored in that browser. There is no central database, automatic upload, or live cross-device synchronization.

The admin view imports multiple human export files. It displays counts by category per item, low-confidence counts, agreement for every pair of overlapping reviewers, and pipeline agreement against each reviewer separately. Human category disagreements appear first. CSV export retains every individual decision, source/text version, pipeline origin, and date. JSON archives preserve the original decisions for later adjudication. No reviewer, majority vote, or AI pass becomes ground truth automatically.

Imports reject wrong taxonomy/packet versions, changed source text, unknown IDs, invalid labels, duplicate items, and conflicting first decisions by the same reviewer. Re-importing the same export is idempotent. Import validation happens before storage changes. Human attestation is not identity authentication: the team must establish who supplied each code and whether their labeling was independent. This browser admin is not an access-controlled shared service. Do not include identifying or private information in notes.

The same checks and descriptive comparisons run from the CLI (Node.js 18+):

```sh
python3 ratio/benchmark.py score --labels /path/to/reviewer-a.json /path/to/reviewer-b.json
```

Each CLI run writes a new ignored archive and CSV under `ratio/instrument/human/`. It never changes a classifier label or publishes a funding result. Corrections need an explicit later adjudication procedure that preserves the original decisions; an adjudication editor is not implemented in this release.

## Corpus and sources

We keep the existing `ratio/data/census_*.jsonl.gz` corpus unchanged: 13,224 records (870 SweCRIS, 239 CORDIS, 12,115 NIH RePORTER), covering the collection's 2015–2025 window. Source retrieval dates and collection queries are recorded in [data/funnel.json](data/funnel.json), dated 12 September 2026. The build checks duplicate IDs before selecting review items and refuses conflicting duplicates.

| Dataset | Source and provenance | Licence and limits |
| --- | --- | --- |
| SweCRIS | [Swedish Research Council SweCRIS](https://www.vr.se/english/swecris.html); collection endpoint, queries and retrieval date in `data/funnel.json` | Existing register describes the data as openly accessible, with attribution to SweCRIS. It does not record a specific redistribution licence. We add no raw records to Git and require confirmation before wider redistribution. Funders include government and private bodies. |
| CORDIS | [CORDIS datasets](https://cordis.europa.eu/data); exact dump URLs, hashes and retrieval dates in `data/funnel.json` | Existing register records CC BY 4.0, European Union attribution, subject to third-party exceptions. |
| NIH RePORTER | [NIH RePORTER](https://reporter.nih.gov/); query endpoint and retrieval date in `data/funnel.json` | Existing register identifies US federal public-domain data; attribute NIH RePORTER. This corpus covers the included NIH search results. |

The inherited licence statements are documented in [the original dataset register](../data/Track3_C2/output/DATA_LICENCES.md); this change does not assert that a fresh legal review was performed. Collection filters differ by source. This is a corpus of search results, not a census of government spending. Semantic search within it cannot recover grants excluded during collection. We do not add Gateway to Research or widen collection this weekend.

Seven records have no collected abstract; 231 reach the fetchers' 6,000-character limit and may be truncated. Fetchers sometimes preferred English over Swedish. The UI preserves the text actually collected, with no further truncation; bilingual completeness cannot be reconstructed from this snapshot. The model runner now receives the full collected text instead of a further 3,000-character cut.

Record IDs, related projects, renewals and the differing award-accounting bases have not been reconciled into a population funding measure. No annualised or currency-converted sum is produced by this instrument. Earlier EUR ratios remain historical local artifacts, outside the new demo and deploy package.

## Architecture and reproducibility

```text
Frozen SweCRIS + CORDIS + NIH records
  -> PR #15 keyword rules as development candidates
  -> conservative four-label aim/evidence checks
  -> source-bound shared development sample
  -> independent human decisions + low-confidence flags
  -> admin disagreement queue + pairwise comparisons + CSV/JSON
```

`instrument/classifier.py` retains the existing lexicon as a candidate generator. A separate check requires evidence in a title or explicit aim sentence before assigning the new categories. Generic keyword hits alone produce an abstention. Competing aims and negation are routed for review. This deliberately conservative baseline has unmeasured recall, and regex aim extraction will miss valid phrasing, especially Swedish variants. Fewer ambiguous labels is not a success metric by itself.

`adjudicate.py` is an optional LLM candidate generator using the same rubric. It validates category, boolean low-confidence, reasons, and an exact supporting quote. Insufficient text permits an explicitly marked abstention. Cache and resume keys bind the entire prompt, source text/version, taxonomy, model, endpoint, and generation parameters. Invalid output is not applied. Model output is marked `label_origin=model` and `human_verified=false`; a mechanically verified quote does not prove the classification. No new paid model calls were made for this change.

```sh
python3 ratio/adjudicate.py --model YOUR_MODEL --limit 20 --dry-run
```

A dry run reports input size and maximum request attempts, including retries. It does not estimate currency costs without provider prices. Runs and generated candidates are local. No embedding model or vector index is added in this fix: retrieval is not needed to review the existing sample, and switching retrieval cannot repair collection coverage. New four-label model candidates are separate from PR #15's old seven-category outputs. To include a new model run in the development instrument:

```sh
python3 -m ratio.instrument.build --model-candidates ratio/instrument/output/model-candidates.jsonl
```

Only source- and request-bound current candidates apply; failed calls retain the rule candidate, and stale or malformed successful outputs stop the build. Changed predictions create a new packet version and require a new human review. No prior verdict is transferred silently.

## Evaluation and limitations

The shared sample has 60 items, 20 per source, drawn with seed 42 from source/category strata. Selection probabilities are recorded in the admin prediction packet, outside the blind view. All researchers can label the same items to create overlap. This is a development sample from an already inspected and mined corpus. It is not an untouched test set, and its unweighted agreement is not population accuracy.

Admin agreement includes ambiguous as an explicit category; low-confidence flags are reported separately. The denominator is shown beside every rate. Cohen's kappa is undefined when there is no overlap or its chance-agreement denominator is zero. Multiple specialists' independent labels and disagreement must remain available before adjudication.

The 90% human-agreement requirement remains a future acceptance target. We cannot claim it from unit tests, model-generated labels, or this tuned development corpus. Before a final evaluation, confirm the rubric, group related projects and renewals, reserve an untouched test sample, freeze prompts/retrieval, and define how human disagreement and unequal sampling probabilities will be handled. No external classifier check currently exists. Cancer calibration and UKHRA/HRCS benchmarking were dropped from the weekend scope.

Software checks use synthetic fixtures, never imported as actual human evidence. The browser smoke test covers labeling, persistence, multi-reviewer import, disagreement ordering and export. Specialist validation, a final held-out evaluation, authenticated shared storage, and any defensible funding result remain incomplete. The map is omitted from the new demo because geographic colouring would invite an unsupported comparison. The earlier policy map remains a separate archived prototype.

## Source-link correction, checked 12 September 2026

The old SweCRIS URLs used `?searchText=`, which the website does not route to a project. The official portal's frontend defines `/project/:projectId` under its hash router. Both future fetches and reads of the existing corpus now produce [project-specific URLs](https://www.vr.se/english/swecris.html#/project/2023-01125_Forte). The compressed corpus files are unchanged. This fixes navigation; it does not verify every record's scientific content.

## Software checks

```sh
python3 -m pip install -r ratio/requirements.txt
python3 -m unittest discover -s tests -p test_instrument.py -v
node --test tests/test_instrument_review.mjs
```

Browser verification requires Playwright (`npm install --no-save playwright`, then `npx playwright install chromium`) and the locally served site:

```sh
node scripts/check-instrument-browser.mjs http://127.0.0.1:8010
```

The browser check uses synthetic decisions in an isolated browser context and writes no human files into the repository. It checks the actual built review sample without turning test decisions into validation evidence.
