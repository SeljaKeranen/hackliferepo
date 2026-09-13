"use strict";

/* Regression test for the index methodology in map/scoring.js.
   Zero-install: run with `node map/test_scoring.js`. */

const assert = require("assert");
const S = require("./scoring.js");

const NOW = new Date("2026-09-12T00:00:00Z");

function finding(overrides) {
  return {
    id: "xx-001",
    type: "finding",
    country: "XX",
    classification: "legislation",
    claim: "A test claim long enough for the schema minimum length.",
    source_url: "https://example.org/doc",
    source_date: "2026-01-15",
    confidence: "high",
    retrieved_at: "2026-09-12T00:00:00Z",
    ...overrides,
  };
}

const verdictCorrect = { finding_id: "xx-001", reviewed: true, correct: true };
const verdictFailed = { finding_id: "xx-001", reviewed: true, correct: false };
const verdictPartial = { finding_id: "xx-001", reviewed: false, correct: false };

// verification states and multipliers
assert.strictEqual(S.verifState(undefined), "pending");
assert.strictEqual(S.verifState(verdictPartial), "pending");
assert.strictEqual(S.verifState(verdictCorrect), "verified");
assert.strictEqual(S.verifState(verdictFailed), "failed");
// a malformed verdict (reviewed but no correct flag) fails closed, never credits
assert.strictEqual(S.verifState({ finding_id: "xx-001", reviewed: true }), "failed");
assert.strictEqual(S.scoreFinding(finding({}), verdictCorrect, NOW).points, 1.0);
assert.strictEqual(S.scoreFinding(finding({}), undefined, NOW).points, 0.7);
assert.strictEqual(S.scoreFinding(finding({}), verdictFailed, NOW).points, 0.0);

// classification weights, including the unknown-value fallback
assert.strictEqual(S.scoreFinding(finding({ classification: "funding" }), verdictCorrect, NOW).points, 0.9);
assert.strictEqual(S.scoreFinding(finding({ classification: "policy" }), verdictCorrect, NOW).points, 0.8);
assert.strictEqual(S.scoreFinding(finding({ classification: "strategy" }), verdictCorrect, NOW).points, 0.7);
assert.strictEqual(S.scoreFinding(finding({ classification: "political statement" }), verdictCorrect, NOW).points, 0.4);
const unknownClass = S.scoreFinding(finding({ classification: "Policy" }), verdictCorrect, NOW);
assert.strictEqual(unknownClass.points, 0.4);
assert.strictEqual(unknownClass.unknownClassification, true);
assert.strictEqual(S.scoreFinding(finding({}), verdictCorrect, NOW).unknownClassification, false);

// confidence multipliers, including the unknown-value fallback
assert.strictEqual(S.scoreFinding(finding({ confidence: "medium" }), verdictCorrect, NOW).points, 0.7);
assert.strictEqual(S.scoreFinding(finding({ confidence: "low" }), verdictCorrect, NOW).points, 0.4);
assert.strictEqual(S.scoreFinding(finding({ confidence: "certain" }), verdictCorrect, NOW).unknownConfidence, true);

// recency tiers, precision variants, and malformed input
assert.strictEqual(S.recencyMult("2026-01-15", NOW), 1.0);
assert.strictEqual(S.recencyMult("2023-06-07", NOW), 0.75);
assert.strictEqual(S.recencyMult("2018-01-01", NOW), 0.5);
assert.strictEqual(S.recencyMult("2015-10-21", NOW), 0.3);
assert.strictEqual(S.recencyMult("2025", NOW), 1.0); // bare year read as mid-year
assert.strictEqual(S.recencyMult("2025-06", NOW), 1.0);
assert.strictEqual(S.recencyMult(undefined, NOW), 0.3);
assert.strictEqual(S.recencyMult("not a date", NOW), 0.3);

// scoreCountry: statuses, counts, failed exclusion, index formula
const entry = {
  iso: "XX",
  records: [
    finding({ id: "xx-001" }),
    finding({ id: "xx-002", classification: "funding" }),
    finding({ id: "xx-003" }),
    { id: "xx-004", type: "nothing_reliable_found", country: "XX",
      search_note: "Searched portals, nothing reliable found here.",
      retrieved_at: "2026-09-12T00:00:00Z" },
  ],
  verdicts: {
    "xx-001": { finding_id: "xx-001", reviewed: true, correct: true },
    "xx-002": { finding_id: "xx-002", reviewed: true, correct: false },
  },
};
const c = S.scoreCountry(entry, NOW);
assert.strictEqual(c.status, "scored");
assert.strictEqual(c.verified, 1);
assert.strictEqual(c.failed, 1);
assert.strictEqual(c.pending, 1);
// S = 1.0 (verified) + 0 (failed, excluded) + 0.7 (pending) = 1.7
assert.ok(Math.abs(c.S - 1.7) < 1e-9);
assert.strictEqual(c.index, Math.round((100 * 1.7) / (1.7 + S.HALFWAY)));

// saturation: S == HALFWAY marks the halfway index of 50
const four = S.scoreCountry(
  { iso: "YY", records: [1, 2, 3, 4].map((i) => finding({ id: `yy-00${i}` })),
    verdicts: Object.fromEntries([1, 2, 3, 4].map((i) => [`yy-00${i}`, verdictCorrect])) },
  NOW
);
assert.ok(Math.abs(four.S - 4.0) < 1e-9);
assert.strictEqual(four.index, 50);

// nothing-only and empty countries never get an index
const quiet = S.scoreCountry({ iso: "ZZ", records: [entry.records[3]], verdicts: {} }, NOW);
assert.strictEqual(quiet.status, "nothing");
assert.strictEqual(quiet.index, null);
const empty = S.scoreCountry({ iso: "ZY", records: [], verdicts: {} }, NOW);
assert.strictEqual(empty.status, "empty");
assert.strictEqual(empty.index, null);

// an all-failed country scores an honest zero, distinct from "nothing found"
const allFailed = S.scoreCountry(
  { iso: "ZX", records: [finding({ id: "zx-001" })],
    verdicts: { "zx-001": { finding_id: "zx-001", reviewed: true, correct: false } } },
  NOW
);
assert.strictEqual(allFailed.status, "scored");
assert.strictEqual(allFailed.index, 0);

/* ---------- funding-gap layer ---------- */

// the 0–100 headline index is the ratio itself, rounded; missing stays null
assert.strictEqual(S.ratioIndex(0.2278), 23);
assert.strictEqual(S.ratioIndex(0.6543), 65);
assert.strictEqual(S.ratioIndex(0), 0);
assert.strictEqual(S.ratioIndex(1), 100);
assert.strictEqual(S.ratioIndex(null), null);
assert.strictEqual(S.ratioIndex(undefined), null);
assert.strictEqual(S.ratioIndex(NaN), null);

// jurisdiction mapping: Sweden and the US keep their national corpora, all
// other EU members carry the European Commission's number, everyone else has
// no ratio data yet.
assert.strictEqual(S.jurisdictionFor("SE"), "SE");
assert.strictEqual(S.jurisdictionFor("US"), "US");
assert.strictEqual(S.jurisdictionFor("DE"), "EU");
assert.strictEqual(S.jurisdictionFor("MT"), "EU");
assert.strictEqual(S.jurisdictionFor("GB"), null);
assert.strictEqual(S.jurisdictionFor("CH"), null);

// the EU list is exactly the 27 current members
assert.strictEqual(S.EU27.length, 27);
assert.strictEqual(new Set(S.EU27).size, 27);
assert.ok(S.EU27.includes("SE") && S.EU27.includes("MT"));
assert.ok(!S.EU27.includes("GB"));

// every jurisdiction a feature can map to has display metadata
for (const code of ["SE", "EU", "US"]) {
  assert.ok(S.JURISDICTIONS[code].name && S.JURISDICTIONS[code].source);
}

console.log("OK: scoring regression tests passed");
