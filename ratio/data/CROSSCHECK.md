# Cross-check: census totals against published funder numbers

Retrieved and computed 2026-09-12. This file is the completeness evidence for
the census under `ratio/data/`: for each jurisdiction, our census total, an
authoritative published number, the delta, and why they differ. The deltas
are expected and explained, not forced into agreement — the census is a
complete pull of the atlas's ageing **search nets**, which is a different
(and much narrower) thing than any funder's total budget.

## Internal consistency: census vs the atlas's own funnel

Before external numbers, the census reproduces the atlas's documented
funnel (METHODOLOGY.md, commit `2e59b27`) exactly where it should:

| check | atlas (2026-09-12) | census (2026-09-12) | verdict |
| --- | ---: | ---: | --- |
| Swecris unique funding rows, 13-phrase net | 6,410 | 6,410 | exact match |
| NIH RePORTER unique ProjectNums, 8-phrase net | 12,115 | 12,115 | exact match |
| Swecris kept (precise, in-window) | 855 | 870 | +15; the atlas dropped ~29 more rows in undocumented "title/abstract checks" |
| RePORTER kept | 1,531 (sample) | 12,115 (all) | the sample kept 12.6% of the population |
| CORDIS kept | 558 (search API) | 239 (bulk dumps) | see below — the two nets differ |

The CORDIS delta is a scope finding, not a fetch failure. The atlas queried
the CORDIS **search engine**, which indexes fields beyond a project's title
and objective (publications, deliverables, report summaries). The census
filters the complete official project dumps (FP7 + H2020 + Horizon Europe,
84,625 projects) on title + objective only. 235 of the atlas's 558 records
are confirmed by the census net; the other 323 do not contain any of the 13
net phrases in their title or objective, and spot-checks show mostly
off-topic matches — SARS-CoV-2 antivirals (`cordis:101005026`), Se-enriched
dairy (`cordis:101007630`), Tibetan diaspora patronage (`cordis:101025661`).
That noise is a large part of why the atlas's CORDIS arm carried a 53.2%
ambiguous share. The census net is the stricter, defensible one; the cost is
that a genuinely ageing-relevant project whose objective never uses an
ageing term is missed (see the Swecris recall test below for a measured
example of that failure mode).

## United States: NIH RePORTER census vs NIA's published budget

- **Our census**: 12,115 grants FY2015–2025, €6,215.5M total; the National
  Institute on Aging accounts for 6,499 grants / €3,743.6M. In FY2023 alone
  the census captures **$552.4M** of NIA money (779 grants).
- **Published number**: NIA's FY 2023 Enacted appropriation is
  **$4,412.1M** — NIA's FY 2024 budget justification states "The FY 2024
  President's Budget request for NIA is $4,412.1 million, the same as the
  FY 2023 Enacted level",
  https://www.nia.nih.gov/about/budget/fiscal-year-2024-budget (retrieved
  2026-09-12).
- **Delta**: our net captures ~12.5% of NIA's FY2023 budget.
- **Why**: the 8-phrase net (cellular senescence, geroscience, healthspan,
  …) is precision-first for *fundamental ageing biology and geroscience*.
  Most of NIA's budget is Alzheimer's/ADRD research (congressionally
  earmarked at roughly $3.5B/yr in recent years), demography, epidemiology
  and care research — grants that rarely use those eight phrases. The
  census is complete **for the net**; the net is deliberately not NIA's
  whole portfolio. Conversely, 46% of census grants come from the other 25
  NIH institutes (NCI, NIGMS, NHLBI, …), which NIA's budget does not cover
  at all.

## European Union: CORDIS census vs the Horizon health-cluster budget

- **Our census**: 239 projects with 2015–2025 starts, €474.3M of EU
  contribution in total, across FP7 (tail), H2020 and Horizon Europe.
- **Published number**: the Horizon Europe health cluster (Cluster 1,
  2021–2027) alone has a budget of **€8,246M** —
  https://hadea.ec.europa.eu/programmes/horizon-europe/health_en (and the
  same figure in national contact point factsheets, e.g. FFG; retrieved
  2026-09-12). Its H2020 predecessor (SC1) was €7,472M for 2014–2020.
- **Delta**: our census is ~3% of the two health-cluster budgets over
  roughly the same span.
- **Why**: the 13-phrase net catches projects that name ageing biology in
  their title/objective; the health cluster funds the whole of health
  research (infectious disease, cancer, health systems, digital health),
  and most ageing-net matches are actually ERC/MSCA projects outside the
  cluster. The two scopes overlap but neither contains the other; no
  agreement is expected. What the number establishes is an order of
  magnitude: explicit ageing-biology framing is a low-single-digit percent
  of EU health-programme funding.

## Sweden: Swecris census vs Forte's published figures

- **Our census**: 870 funding rows 2015–2025, €409.0M (SEK ~4.6B) across
  all Swecris funders; Forte's subtotal is 206 rows / €86.2M (SEK ~969M,
  ~88 MSEK/yr).
- **Published numbers**: Forte states it distributes **around SEK 900M per
  year** across health, working life and welfare research, with national
  coordination responsibility for ageing research —
  https://forte.se/en/ (retrieved 2026-09-12). Our census attributes ~10%
  of Forte's annual distribution to the ageing net, consistent with ageing
  being one of Forte's several coordination areas.
- **Record-level recall test**: Forte's news item "22 million SEK for
  collaboration research in the field of ageing and health" (2023-02-21,
  https://forte.se/en/news/news/2023-02-21-22-million-sek-for-collaboration-research-in-the-field-of-ageing-and-health)
  names five funded projects with amounts. **Four of the five are in the
  census with exactly the published amounts** (`swecris:2022-01117_Forte`
  4.95M, `swecris:2022-01122_Forte` 3.93M, `swecris:2022-01136_Forte`
  5.0M, `swecris:2022-01155_Forte` 4.15M). The fifth
  (`2022-01121_Forte`, m-health support for family caregivers of persons
  with dementia, 4.25M) exists in Swecris with the correct amount but is
  **missed by the net**: its title and abstract contain no ageing term —
  dementia-care vocabulary only. Measured net recall on this independent
  list: 4/5, with the miss identified and explained.

## Known gaps the census does NOT close

- **Net recall bounds everything.** The census is complete for the atlas's
  search nets; grants that discuss ageing without net vocabulary (the
  dementia-caregiving example above) stay invisible. The 30-record human
  benchmark, once labelled, measures label precision — net recall needs
  its own sample.
- **Sweden**: Swecris covers the ~13 funders that report to it (VR, Forte,
  Formas, Vinnova, Energimyndigheten, RJ, Hjärt-Lungfonden, …). Sweden's
  largest private research funder, the Knut and Alice Wallenberg
  Foundation, and most disease charities (Cancerfonden, Alzheimerfonden)
  do not report to Swecris and are absent.
- **US**: NIH only. NSF, VA, DoD and private funders (e.g. Hevolution,
  Impetus) are out of scope.
- **EU**: EC framework programmes only; member-state national funders
  (DFG, ANR, …) are not in CORDIS.
- **CORDIS text basis**: title + objective. A project whose ageing content
  appears only in deliverables/reports is missed (the converse of the
  atlas's search-index noise).
- Award amounts are as published per grant (RePORTER per-FY awards,
  CORDIS `ecMaxContribution`, Swecris `FundingsSek` per funding row) and
  not annualised; FX is the fixed ECB 2026-09-11 snapshot.
