# Longview

Longview is a research prototype for health ministry analysts comparing Sweden, the United States and Singapore. It combines a dated policy record, published population-health indicators and an interpretable five-year life-expectancy forecast. A ten-year view explores explicit assumptions; it has no ten-year validation.

Team: Selja, Max, Jan. Stockholm AI × Longevity Hackathon, 11–13 September 2026. Track 3, challenge 1. The [playbook](docs/playbook.md) gives the submission requirements and judging weights. The three-country scope supersedes the earlier EU-first notes in [the original challenge plan](docs/challenge.md).

The implementation advances technical execution, evidence and responsible use, track fit, and the Demo Day presentation. The map, country comparisons, scenario controls, source filters, print brief and remote review workflow are built. Source-grounding and model tests use actual retrieved public data; synthetic review tests stay in ignored `outputs/` and are never imported as human approvals. Human review remains incomplete, so the public release withholds policy claims. The initial sample contains 34 candidates; two supplemental funding leads are outside that frozen benchmark.

The model's wider historical test has 1,098 country-origin forecasts. Regression MAE is 1.10 years; no change is 1.23 and the previous trend is 1.28. The US regression performs worse than both baselines. Its wider empirical interval covers 74.9% of outcomes despite a 90% target. The [full evaluation](docs/model-evaluation.json) records the selection procedure, country results and limitations. These numbers do not establish causal policy effects or clinical performance.

## Open and run

The current temporary preview is [Longview on Vercel](https://temporary-fast-peridot-kempbnu.vercel.app). Temporary hosting expires unless claimed by the team. Deployment details and the private reviewer key stay in ignored `outputs/`; never commit them. The production build contains static assets, derived numerical summaries, fitted parameters and an encrypted reviewer packet. Research keys stay on the research machine.

Tested with Python 3.13 and Node 22:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
npm ci
npm run dev
```

The checked-in curated release is enough to run the app. Longview's raw source documents, API responses and SQLite database are excluded from Git. To reproduce the research and model from the documented sources:

```bash
.venv/bin/python -m scripts.research-discovery
.venv/bin/python -m scripts.collect-sources
.venv/bin/python -m scripts.extend-us
.venv/bin/python -m pipeline.data
.venv/bin/python -m pipeline.curate
.venv/bin/python -m scripts.research-fundamental
.venv/bin/python -m scripts.collect-fundamental-sources
.venv/bin/python -m pipeline.funding
.venv/bin/python -m pipeline.model
.venv/bin/python -m pipeline.release
node scripts/package-review.mjs
npm run build
```

Discovery requires `YOU_API_KEY` / `TAVILY_API_KEY` in the environment or the existing ignored `keys` file. There is a transactional cap of 500 combined provider requests, including retries and the seven planning requests. Responses are cached locally. No credit purchases are authorised. Re-running curation changes evidence versions only when the underlying records change; existing approvals cannot silently survive edits.

The supplemental [fundamental-ageing funding investigation](docs/fundamental-ageing-research.md) has a separate scope and no comparable national totals yet. Its two candidate records can be regenerated with the supplemental discovery, retrieval and `pipeline.funding` commands above. Do not substitute programme budgets for national basic-research spending.

## Evidence review and the ≥90% requirement

The public page displays the initial sample's review progress, pass rate and pending/passed/failed status. It passes only when the frozen sample is fully human-reviewed and at least 90% of its first completed verdicts pass all four checks. Every published finding separately needs a current all-pass human verdict. The forecast's error in years is a different metric.

Remote reviewers open the private `/review/` link, enter initials, check original sources and export their verdict file. Reviews save in that browser, not on a public server. Import an actual teammate export on the research machine:

```bash
.venv/bin/python -m pipeline.import_reviews /path/to/longview-review.json
.venv/bin/python -m pipeline.release
```

For the final evidence gate, use `python -m pipeline.release --strict`. It fails if any candidate is unapproved, the initial sample is incomplete, or its first-review accuracy is below 90%. The target cannot be achieved by removing failed records or correcting the sample after the fact. Version fingerprints bind reviews to the claim and provenance; history is append-only.

Local review remains available through `python3 eval/server.py --country sweden --port 8710`, with `united-states` and `singapore` as the other country slugs. See [the review guide](eval/README.md).

## Verify and produce the pitch

```bash
.venv/bin/python -m pytest tests -q
python3 eval/test_findings.py
npm test
npx playwright install chromium
npm run test:browser
npm run build
.venv/bin/python scripts/make-deck.py
node scripts/record-demo.mjs
.venv/bin/python scripts/package-delivery.py
npm run build
.venv/bin/python scripts/package-delivery.py --offline
.venv/bin/python -m scripts.security-check
```

The browser checks cover desktop/mobile rendering, country selection, scenario/reset behaviour, deep links, print output and encrypted review/export. They run against `http://localhost:5173` by default; set `DEMO_URL` for a deployed check. Chromium needs its standard Linux libraries and fonts. The browser helper also recognises the temporary runtime libraries used in this remote environment.

The hosted footer links to the deck, recording and offline app. [Delivery status](docs/delivery-status.md) records completed checks and the remaining submission requirements.

Generated deliverables are `outputs/longview-three-slides.pptx`, `outputs/longview-three-slides.pdf`, `outputs/longview-demo.webm` and `outputs/analyst-brief.pdf`. The deck has exactly three slides, editable text and data lines, speaker notes, and a screenshot of the actual app. Generate it after refreshing the release and browser screenshots. [Pitch notes](docs/pitch-notes.md) provide a three-minute spoken version.

## Data and deployment

The branch also preserves the team's [Aging Funding Atlas dataset](data/Track3_C2/METHODOLOGY.md) from remote main, with its [licence and provenance notes](data/Track3_C2/output/DATA_LICENCES.md). That contribution has a separate benchmark and awaits integration into Longview. The app currently loads the frozen releases in `public/release/`.

[Dataset licences and definitions](docs/dataset-register.md) are recorded before use. SQLite has foreign keys and unique observation keys. Each series retains its definition, units, query, retrieval time, revision and content fingerprint. Missing values are not zero-filled. Data from the current revised vintage cannot establish historical publication availability.

React, TypeScript and Vite build the static UI. Python collects and validates evidence, stores it in SQLite, fits the model and exports browser parameters. The public app has no research endpoint and no credential access. Vercel and Netlify configurations are included; [deployment instructions](docs/deployment.md) explain how to publish only the build output and keep the preview.

The Sunday submission still requires the team's human review, a persistent hosting claim, and organiser upload access. No ministry adoption test has been run. The project cannot determine which policy caused a lifespan change, predict an individual's life, or provide a comparable fundamental-ageing funding ranking yet.
