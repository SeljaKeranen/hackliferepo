# Funding pivot delivery status

Checked 12 September 2026. Branch: `codex/ageing-funding-gap`. Funding release: `5377161e107b0f80`. This change advances Track 3 funding classification and the Demo Day problem/user story, technical execution, evidence and communication components.

## What works

The public app has the landing report, Sweden and US portfolio reports, searchable source details, a method page and immutable report links. The visible 90% requirement is connected to actual review status. The private `/review/funding/` workspace supports blinded source review, separate report checks and JSON export from a remote browser. Earlier `/review/` remains available.

The official snapshot contains 6,623 retained award records and matching classification candidates: 1,281 Swedish Research Council/Forte records and 5,342 NIA-administered US parent awards. The collector keeps response hashes and full pagination metadata. SQLite integrity checking returned `ok`, with zero foreign-key violations. The source ledger has original URLs, dates, native currency, funding period and normalised source hashes.

Source discovery used both You.com and Tavily. The combined project ledger records 73 attempted provider requests against the cap of 500. All 12 new method cross-check queries returned results. Those searches are discovery evidence, not human correctness verdicts. Thirty-eight earlier model labels met the strict source-match and rule-agreement conditions for reuse as candidates; no new paid model calls were made.

Fourteen funding tests pass, covering money weighting, missing/zero amounts, duplicate and currency rejection, country-specific thresholds, stale sources and labels, first-verdict retention, crash recovery, public masking and an isolated approved-release path. The preserved Python regression suite and four JavaScript model checks also pass. Nine browser checks pass against both the built static app and the live Vercel preview, including country/frozen links, search, mobile, both reviewer pages and private export. A separate browser-only approved fixture checks the share-card download and approved monetary view.

Exactly three editable PowerPoint slides and a matching three-page PDF are generated. The captioned WebM is 94.92 seconds, 1440×900, VP8, with no audio. A frame was decoded successfully at 40 seconds. It records actual public-app interactions and the pending review state. The offline archive is release-matched and excludes private review packets. Its extracted copy passed a country deep-link and source-search test with external requests blocked. [The manifest](../public/downloads/manifest.json) records file hashes and recording verification.

The static build and nested downloadable archives pass the secret scan. Provider keys, reviewer keys, raw API responses, full abstracts and the local database are outside the build. Pending classification outputs and numerical aggregates are masked in both the UI and public JSON. Approved derived findings are checked against the finding schema and cite a dated report permalink with the full underlying source ledger.

## What is unverified or simulated

**No human verdicts have been imported for the new benchmark: 0/60 reviewed.** Classifier accuracy is not yet measured. Large-award and report approvals are also pending. The public country ratios and numerical share cards remain unavailable.

Unit tests and the isolated approved UI use synthetic human-shaped fixtures. Browser exports are saved only under ignored `outputs/`, explicitly marked as simulations and never imported. They do not contribute to the benchmark. Source collection and assistant inspection are not substitutes for expert review.

The previous policy benchmark, teammate grant benchmark and life-expectancy model remain in their original locations. Their results do not validate this funding report. The two selected portfolios are not complete national budgets, actual annual expenditure measures or a basis for ranking countries.

## What remains

Complete the 60 blinded human reviews, ten large-award checks per country and both report approvals. Settle biological boundaries with Andrew, using the separate development cases. If those decisions change source scope or taxonomy, preserve the old evaluation and freeze a new version before measuring accuracy. Import actual reviews, then regenerate the release and delivery artifacts.

Run the proposed five-reader comprehension/adoption test. It has not happened. The report makes no clinical claims or causal predictions about lifespan.

The Vercel preview is temporary because this machine has no authenticated Vercel account. The concrete claim link and exact expiry are in ignored `outputs/deployment.json` and were provided to the user. A team member must claim the deployment for persistence and obtain organiser access for the Sunday submission. No organiser upload, external messaging or main-branch merge has been performed.
