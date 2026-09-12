# Longview — where does ageing research money go?

Longview turns public research award records into a source-linked funding report for the public and advocates. It estimates the share of a selected government portfolio's ageing research funding that targets ageing biology and interventions. Every award keeps its source, amount, date and funding basis.

This branch implements the funding-report pivot for **Track 3, public research funding classification**. It advances the Demo Day problem/user story, technical demo, evidence and responsible use, and communication criteria in the [playbook notes](docs/playbook.md).

The app has a landing report, Sweden and US portfolio pages, a searchable source ledger, a method page, immutable report snapshots and a separate private funding reviewer workspace. **Human verification is pending: 0/60 reviewed. Numerical estimates and share cards remain withheld.** Software test fixtures are not human evidence.

## What the snapshot covers

| Funding government | Selected portfolio | 2024 records |
| --- | --- | --- |
| Sweden | Swedish Research Council + Forte, Swecris funding year 2024 | 1,281 |
| United States | NIA-administered FY2024 parent awards, NIH RePORTER | 5,342 |

The source collection contains 6,623 retained records. NIH constituent subprojects are removed to avoid duplicate totals. The Swedish collection pages both funders completely before applying the funding-year filter. These are narrower portfolios, not national totals or a country ranking. Swedish commitments can cover several years; US fiscal-year award costs also have multi-year exceptions. No annualisation or currency conversion is applied.

The headline is `(ageing biology + ageing interventions) / classified ageing-related research funding`, using money amounts rather than grant counts. Biology and interventions remain visible separately. Unresolved known money enters sensitivity scenarios; missing amounts remain explicit. Read the [methodology](docs/funding/methodology.md) and [dataset/reuse register](docs/funding/dataset-register.md).

You.com and Tavily were both used for source-definition cross-checks. The project has used 73 combined attempted research requests out of the authorised 500; [dated query records](docs/funding/source-crosschecks.json) are committed. Award facts come from the official APIs, not search summaries. No additional paid model calls were made for this pivot.

The teammate's original [dataset and methodology](data/Track3_C2/METHODOLOGY.md) are preserved. Matching earlier labels are reused only as unverified candidates. The earlier life-expectancy model, policy materials and benchmarks remain in their original files; they do not establish results for this funding report.

## Run and verify

```bash
npm ci
npm run dev
# Public app: / ; /country/sweden ; /country/united-states ; /sources ; /method
# Private funding review: /review/funding/ ; earlier policy review: /review/
```

A remote user can use the hosted Vercel or Netlify deployment; no local browser connection is needed. See [deployment and ownership](docs/deployment.md). The public app needs no provider keys.

```bash
.venv/bin/python -m pytest -q tests
npm test
node scripts/check-funding-browser.mjs
# Optional positive-path UI fixture; never a human verdict:
# node scripts/check-funding-approved.mjs
npm run build
.venv/bin/python -m scripts.security-check
```

The funding suite checks amount weighting, zero/missing values, duplicate and mixed-currency rejection, per-country thresholds, stale-version rejection, first-verdict retention and public masking. Browser checks exercise both country reports, frozen links, source search, mobile layouts and a synthetic local review export. The synthetic export stays ignored and must never be imported.

## Rebuild the evidence

Use Python dependencies from `requirements.lock.txt`. Raw responses, abstracts and the SQLite store live in ignored `data/`; provider credentials live outside the public build.

```bash
.venv/bin/python -m funding.collect
.venv/bin/python -m funding.classify
.venv/bin/python -m funding.benchmark
.venv/bin/python -m funding.review
.venv/bin/python -m funding.release
node scripts/package-funding-review.mjs
```

Official API responses are cached and hashed. The collector fails on incomplete pagination. The classifier uses local rules over the full available abstract; it is not yet human-validated. `funding.benchmark` refuses to overwrite a changed frozen population. Preserve prior benchmarks when creating a new evaluation version.

The [human review guide](eval/funding/README.md) explains the remote workflow. Open the private link containing the key from ignored `outputs/funding-reviewer.key`, review the original sources, export the JSON and import a real human file:

```bash
.venv/bin/python -m funding.review --import-file /path/to/human-export.json
.venv/bin/python -m funding.release
node scripts/package-funding-review.mjs
```

Publication requires all 60 reviews, at least 90% overall and in each country, source/category checks for the ten largest awards per country and human approval of each report. Source and classification changes invalidate affected approvals. The frozen sample's first verdicts are retained. Human identity must be established by the team; a JSON attestation alone is not authentication.

## Three slides and a working fallback

The current delivery artifacts are in [public/downloads](public/downloads): [editable PowerPoint](public/downloads/longview-three-slides.pptx), [three-page PDF](public/downloads/longview-three-slides.pdf), [captioned walkthrough](public/downloads/longview-demo.webm) and [offline app](public/downloads/longview-offline.zip). They describe the pending review state, not a verified funding gap.

Regenerate them from the current funding release:

```bash
node scripts/check-funding-browser.mjs
.venv/bin/python -m funding.deck
node scripts/record-funding-demo.mjs
.venv/bin/python -m funding.delivery
npm run build
.venv/bin/python -m funding.delivery --offline
.venv/bin/python -m scripts.security-check
```

The deck contains exactly three slides. Text, diagrams and shapes are editable; the demo screenshot is a raster capture of the app. The recording shows real browser interaction with captions and no audio. The offline archive contains no private reviewer packet. Source links require internet; the bundled public report and source ledger work offline through the included Python server.

Still incomplete: real human benchmark and report reviews, Andrew's boundary-method decisions, a reader comprehension/adoption test, account-owned persistent hosting and the organiser submission. [Andrew's briefing](docs/funding/andrew-brief.md), [pitch notes](docs/pitch-notes.md), [delivery status](docs/delivery-status.md) and the [goal prompt](docs/goal-prompt.md) record the remaining work. No clinical claims, causal funding effects or lifespan forecasts are made by this report.
