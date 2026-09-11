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

Decided 11 September 2026: we cover the 27 EU member states first, with country-level findings. Anything beyond the EU is a stretch goal only if time allows.

This scope buys two things:

- With only 27 countries, the human-verified benchmark can cover every country instead of a sample: a gold set of expected findings plus honest "nothing reliable found" entries for the quiet member states.
- Primary sources concentrate on EU institutions: CORDIS for funding, EUR-Lex and national parliament portals for legislation, European Commission and WHO-Europe strategy documents for policy.

## Initial goal

1. Lock the data schema for a finding first: country/region, classification, claim, source URL, source date, confidence.
2. Build the research agent plus a roughly 30–50 finding human-verified benchmark on Saturday; report accuracy against it.
3. Keep the map UI simple.

## What this means in practice

Coverage explicitly matters less than accuracy. A modest map where nearly every finding survives human verification beats a dense map with unverified claims, so the benchmark and the honest "nothing reliable found" handling are first-class deliverables, not polish.
