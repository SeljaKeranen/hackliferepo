# Longevity Politics Index map

Interactive world map for the [map-the-politics-of-longevity
challenge](../docs/challenge.md). Since the 13 September redesign its visible
interface is the funding-gap index; the original politics-findings layer is
retained in the code and reachable with `?layer=politics` for development, but
hidden from the header. The two layers share the map and panel but no data
path. This map does not replace, modify, or compete with the Longview app on
branch `codex/longview-demo`, which remains untouched.

## Layer 1: Funding-gap index (default)

The headline layer. Each coloured jurisdiction shows the **funding-gap ratio**
as a 0–100 index: the share of classified ageing-research money that targets
slowing ageing itself (fundamental ageing biology and interventions against
ageing) rather than managing its consequences. Ambiguous grants count for
neither side.

| Colour applies to | Data source | Corpus |
| --- | --- | --- |
| Sweden | `ratio/output/aggregates.json` (SE) | national SweCRIS |
| 26 other EU members | `ratio/output/aggregates.json` (EU) | European Commission, CORDIS |
| United States | `ratio/output/aggregates.json` (US) | NIH RePORTER, federal |

The `Adjudicated (AI)` toggle reads `aggregates_adjudicated.json` instead, the
scenario where every ambiguous record was re-labelled by deepseek-flash. The
index formula and both scenarios are documented in
[`ratio/README.md`](../ratio/README.md); the map reads the same built outputs
as [`ratio/index.html`](../ratio/index.html) and adds a geography.

Clicking a jurisdiction opens its panel: index and ratio arithmetic, category
breakdown, top funders, and the largest grants one by one (from
`ratio/output/labels.jsonl` or `labels_adjudicated.jsonl`), followed by the
method caveats. The full method page stays the funding-gap page; the map links
to it rather than duplicating it.

**Attribution caveat, deliberately visible on the page.** The EU number is
European Commission funding, not member-state budgets; the map shows it for
all 26 other EU members because it is the only EU-wide number the census
carries. Sweden keeps its national number because it has one. Treat the map as
a comparison of funding jurisdictions, not a ranking of countries.

## Layer 2: Politics findings (retained, hidden from the header)

One 0–100 score per covered country in the style of the World Happiness Index,
composed client-side from the human-verified records in `eval/findings/` and
the review verdicts in `eval/verdicts/`. Countries without findings render as
"not yet covered"; countries searched without result render with an explicit
"nothing reliable found" hatch. The map never fabricates data for uncovered
countries. The layer is kept for reference and development (reachable via
`?layer=politics`); the header switcher shows only the funding-gap index.

## Run it

From the repository root:

```sh
python3 -m http.server 8010
```

Then open <http://localhost:8010/map/>. No install, no build step, no network
needed beyond localhost: the map library, geometry and font are vendored.

URL parameters are shareable and deep-linkable:

| URL | Shows |
| --- | --- |
| `/map/` | Funding-gap index, rules scenario |
| `/map/?scenario=adjudicated` | Funding-gap index, AI-adjudicated scenario |
| `/map/?region=SE` (or `EU`, `US`) | Funding-gap panel for one jurisdiction |
| `/map/?layer=politics` | The politics-findings layer (hidden from the header; kept for development) |

The findings layer discovers `eval/findings/*.json` at runtime by parsing the
server's directory listing, so new country files appear without code changes.
Behind a server without directory listings it falls back to a fixed candidate
list (`sweden.json`, `us.json`, `singapore.json`) and shows a warning in the
panel. The eval review loop (`python3 eval/server.py`) is untouched and keeps
working standalone; the map only reads its JSON files. Likewise, the map never
writes to `ratio/output/`; `ratio/build.py` remains the only producer.

## Test it

```sh
node map/test_scoring.js
```

Regression-tests the pure functions in `scoring.js`: the findings-layer
formula (every multiplier tier, verdict states, saturation, country statuses)
and the funding-gap layer (ratio → 0–100 index, EU-27 and jurisdiction
mapping, unknown-value fallbacks). Runs on plain Node, no install.
`python3 eval/test_findings.py` still validates the findings data files
themselves.

## Politics-layer index methodology, v0

Computed in `scoring.js` (the constants there are the source of truth; the
same file is loaded by the browser page and by the regression test). For each
finding record:

```
points = weight(classification) x confidence x verification x recency
```

| Signal | Values |
| --- | --- |
| classification weight | legislation 1.0, funding 0.9, policy 0.8, strategy 0.7, political statement 0.4 |
| confidence | high 1.0, medium 0.7, low 0.4 |
| verification | human-verified correct 1.0, awaiting review 0.7, failed review 0.0 (shown but excluded) |
| recency of source_date | up to 2 years 1.0, up to 5 years 0.75, up to 10 years 0.5, older 0.3 |

A country's raw score S is the sum of its findings' points, and the headline
index saturates so a single finding cannot max a country out:

```
index = round(100 x S / (S + 4))
```

S = 4 points marks the halfway index of 50. A finding that failed human review
contributes zero and is shown crossed out in the country panel, so the index
can only be inflated by claims that survive verification. Every multiplier for
every finding is printed in the panel; nothing about the score is hidden.

These weights are a transparent v0, not a calibrated model. Calibrating them
against a gold set (and the gold-set builder itself) is future work; see the
note in [docs/challenge.md](../docs/challenge.md).

## Vendored assets

| File | Source | Version | Licence |
| --- | --- | --- | --- |
| `vendor/d3.v7.9.0.min.js` | <https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js> | 7.9.0 | ISC, Mike Bostock |
| `vendor/world-110m.geojson` | Natural Earth 1:110m admin-0 countries, via <https://github.com/nvkelso/natural-earth-vector> (`geojson/ne_110m_admin_0_countries.geojson`, retrieved 2026-09-11) | 5.x master | Public domain |
| `vendor/fraunces-latin-wght-normal.woff2` | Fontsource build of Fraunces variable, <https://cdn.jsdelivr.net/fontsource/fonts/fraunces:vf@latest/latin-wght-normal.woff2> (retrieved 2026-09-11) | Fraunces variable, latin subset | SIL OFL 1.1 |

`vendor/world-110m.geojson` is generated: it keeps only the country name and
ISO 3166-1 alpha-2 code and rounds coordinates. Regenerate it with
`vendor/strip_geo.py` (instructions in its docstring) rather than editing it.
The 1:110m geometry omits microstates; Malta (an EU member with data) and
Singapore (a findings country) are drawn as circle markers from the gazetteer
in `app.js`, alongside a Brussels marker for the European Commission —
extend the gazetteer when another microstate gains data.

## Known limits

- The funding-gap layer compares funding jurisdictions, not countries: the EU
  colour is European Commission money shown for member states (Sweden
  excepted, which has a national census). The corpus is the complete result set
  of the atlas search nets, not any funder's total budget; net recall bounds
  coverage.
- Rules-scenario labels are rule-based and not yet human-verified; the
  30-record human benchmark is pending. The adjudicated scenario is model
  labels, not human ground truth. Both are spelled out on the ratio page.
- The choropleth ramp is a clamped viridis sub-range, chosen for colorblind
  safety and projector contrast; funding-gap indices are comparable within
  this corpus only, and the politics-layer scores within the v0 formula only.
- Recency in the politics layer is computed against the viewer's clock, so a
  country's index can drift slightly over months as sources age. That is
  intended.
- Findings for a country with neither 110m geometry nor a gazetteer entry
  still appear in the politics ranking panel, just without a map shape.
