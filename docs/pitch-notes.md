# Three-slide Demo Day pitch

Track 3: communication, trust and policy; public funding classification. The intended user is the public, with advocates sharing the report. This pitch advances the problem/user, working demo, evidence and next-steps components. It contains no verified numerical funding-gap claim yet.

**Slide 1: What do we fund when we fund ageing?**

“We want a public reader to see how research funding is divided between the biology of ageing and research into its consequences. The report uses one ratio inside a named government portfolio. It keeps the amount, funding period and original source attached. We are measuring whether there is a gap; we have not assumed the answer.”

Explain the numerator and research-only denominator. Biology and interventions remain separate in the report. Care delivery and pensions are excluded.

**Slide 2: Two portfolios. Every award traceable.**

“We collected 6,623 award records: 1,281 from Swedish Research Council and Forte, and 5,342 NIA-administered US parent awards. These are 2024 source records. They are not national totals, and their award periods differ.”

Open Sweden. Show the named funders and multi-year commitment basis. Search the ledger for mitochondria or metabolism, inspect an award and follow its source. Open the US report and show the fiscal-year basis. Go to the method and explain the objective classifier and unresolved categories.

Architecture: official API snapshots → local Python/SQLite → versioned objective candidates → blinded human review → approved static release. React and TypeScript serve the report. You.com and Tavily support discovery and source-definition crosschecks; they do not supply human verdicts. Keys stay outside the browser build.

**Slide 3: The estimate waits for human review.**

“The software works, but accuracy is not yet measured. Our separate benchmark has 60 records, 30 per country. All need review, with at least 90% correct overall and in each country. We also check the ten largest awards per country and require approval of the whole report. Until then, estimates stay private.”

Name the main failure modes: biology under disease labels; background words mistaken for objectives; mixed centres; large excluded awards; unresolved amounts; differing funding periods. The sensitivity range is a classification scenario for known amounts, not a confidence interval. The first verdict stays recorded even after correction.

Next: settle boundaries with an ageing biologist, complete human review and test the visual with five public readers. Reader understanding and adoption have not yet been measured. Team: Selja, Max and Jan.

If the live app is unavailable, play the captioned WebM in `public/downloads`. It shows the actual report, source search, method and pending gate. The same release is bundled offline; original-source links still need internet. Use the committed three-slide PDF if video playback fails.

Sources: [funding methodology](funding/methodology.md), [dataset/reuse register](funding/dataset-register.md), [dated provider crosschecks](funding/source-crosschecks.json), [release manifest](../public/downloads/manifest.json). Review status must be regenerated after human imports; do not describe an older recording as a newly approved result.
