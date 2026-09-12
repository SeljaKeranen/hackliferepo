# Our challenge: map the politics of longevity

Decided 11 September 2026. We take Track 3 (Communication, Trust & Policy), challenge 1. The full challenge text sits in [tracks-challenges.md](tracks-challenges.md#1--map-the-politics-of-longevity); this file records the substance and our plan.

## The challenge

The question: where are governments and politicians seriously engaging with longevity, healthy ageing or the biology of ageing?

We build an AI research agent that searches public sources and produces a cited, time-stamped global map of political activity. Required output:

1. An interactive map with country- or state-level findings.
2. Each finding classified as policy, legislation, funding, strategy or political statement.
3. A source and date for every finding.
4. A confidence and coverage score, including an explicit "nothing reliable found" state.

Evaluation: accuracy on a small human-verified benchmark matters more than map coverage. The bar is at least 90% of sampled findings verified correct by a human reviewer, with every finding carrying a dated source — including the honest "nothing reliable found" results.

## Geographic scope

Decided 11 September 2026: we cover Sweden, the United States and Singapore first. This supersedes the EU-27-first scope decided earlier the same day. The US is covered at both federal and state level — the challenge explicitly allows state-level findings, so US records use the schema's optional `region` field for states. The rest of the world comes later, only if time allows.

This scope buys three things:

- Three signal-rich countries on three continents, so the benchmark exercises different source ecosystems (regeringen.se and riksdagen.se; congress.gov, NIH and state government portals; gov.sg agencies) instead of one EU-shaped pipeline.
- The US federal/state mix exercises the `region` field and the state-level half of the challenge's required output.
- Small enough that the human-verified benchmark can cover every finding in every country, not a sample.

## Initial goal

1. Lock the data schema for a finding first: country/region, classification, claim, source URL, source date, confidence.
2. Build the research agent plus a roughly 30–50 finding human-verified benchmark on Saturday; report accuracy against it.
3. Keep the map UI simple.

## Evaluation loop

Built 11 September 2026 as a Sweden-first pilot, extended the same day to the
US and Singapore: the finding schema lives in
[`schema/finding.schema.json`](../schema/finding.schema.json), findings from
primary sources per country in [`eval/findings/`](../eval/findings/), and a
localhost review screen (`python3 eval/server.py`) with a country selector
where the team marks each finding against a four-check rubric; verdicts persist
per country to `eval/verdicts/` and the screen shows per-country and overall
accuracy. See [`eval/README.md`](../eval/README.md).

## What this means in practice

Coverage explicitly matters less than accuracy. A modest map where nearly every finding survives human verification beats a dense map with unverified claims, so the benchmark and the honest "nothing reliable found" handling are first-class deliverables, not polish.
