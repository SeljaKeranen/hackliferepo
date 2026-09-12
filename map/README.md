# Longevity Politics Index map

> **Scope.** This map is a presentation-layer prototype with a placeholder v0
> activity index. After the team's pivot, the headline metric will become the
> funding-gap ratio: money going to slowing ageing versus money going to
> managing its consequences. This map does not replace, modify, or compete
> with the Longview app on branch `codex/longview-demo`, which remains
> untouched.

Interactive world map for the [map-the-politics-of-longevity
challenge](../docs/challenge.md): one headline index per country in the style
of the World Happiness Index, composed client-side from the verified findings
in `eval/findings/` and the human verdicts in `eval/verdicts/`. Countries
without findings render as "not yet covered"; countries searched without
result render with an explicit "nothing reliable found" hatch. The map never
fabricates data for uncovered countries.

## Run it

From the repository root:

```sh
python3 -m http.server 8010
```

Then open <http://localhost:8010/map/>. No install, no build step, no network
needed beyond localhost: the map library, geometry and font are vendored.

The map discovers `eval/findings/*.json` at runtime by parsing the server's
directory listing, so new country files appear without code changes. Behind a
server without directory listings it falls back to a fixed candidate list
(`sweden.json`, `us.json`, `singapore.json`) and shows a warning in the panel
that discovery may be incomplete; a findings or verdicts file that exists but
fails to load is also called out in the panel rather than dropped silently.
The eval review loop (`python3 eval/server.py`) is untouched and keeps working
standalone; the map only reads its JSON files.

## Index methodology, v0

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

## Test it

```sh
node map/test_scoring.js
```

Regression-tests the formula against fixed fixtures: every multiplier tier,
the verified/pending/failed verdict states, the unknown-value fallbacks, the
saturation constant, and the scored/nothing/empty country statuses. Runs on
plain Node, no install. `python3 eval/test_findings.py` still validates the
data files themselves.

## Vendored assets

| File | Source | Version | Licence |
| --- | --- | --- | --- |
| `vendor/d3.v7.9.0.min.js` | <https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js> | 7.9.0 | ISC, Mike Bostock |
| `vendor/world-110m.geojson` | Natural Earth 1:110m admin-0 countries, via <https://github.com/nvkelso/natural-earth-vector> (`geojson/ne_110m_admin_0_countries.geojson`, retrieved 2026-09-11) | 5.x master | Public domain |
| `vendor/fraunces-latin-wght-normal.woff2` | Fontsource build of Fraunces variable, <https://cdn.jsdelivr.net/fontsource/fonts/fraunces:vf@latest/latin-wght-normal.woff2> (retrieved 2026-09-11) | Fraunces variable, latin subset | SIL OFL 1.1 |

`vendor/world-110m.geojson` is generated: it keeps only the country name and
ISO 3166-1 alpha-2 code and rounds coordinates. Regenerate it with
`vendor/strip_geo.py` (instructions in its docstring) rather than editing it.
The 1:110m geometry omits microstates; the two with committed or planned
findings (Malta, Singapore) are drawn as circle markers from the gazetteer in
`app.js` — extend it when another microstate gains a findings file.

## Known limits

- The choropleth ramp is a clamped viridis sub-range, chosen for colorblind
  safety and projector contrast; scores are comparable within this v0 formula
  only.
- Recency is computed against the viewer's clock, so a country's index can
  drift slightly over months as sources age. That is intended.
- Findings for a country with neither 110m geometry nor a gazetteer entry
  still appear in the ranking panel, just without a map shape.
