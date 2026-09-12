// Synthetic fixtures only; never use these exports as human validation.
import test from "node:test";
import assert from "node:assert/strict";
import {
  validateExport,
  mergeExports,
  summarize,
  agreement,
  csvCell,
  exportCSV,
} from "../ratio/instrument/review.mjs";
const packet = {
  packet_id: "fixture-packet",
  taxonomy_version: "andrew-working-v1",
  records: [1, 2, 3].map((id) => ({
    record_id: String(id),
    source_version: `v${id}`,
    source: "fixture",
    url: "https://example.org/fixture",
    retrieved_at: "2026-09-12",
  })),
};
function body(reviewer = "R1", decisions = [["1", "neither", false]]) {
  return {
    format: "longview-human-labels-v1",
    label_origin: "human",
    human_attested: true,
    packet_id: packet.packet_id,
    taxonomy_version: packet.taxonomy_version,
    reviewer,
    decisions: decisions.map(([id, label, low]) => ({
      record_id: id,
      source_version: `v${id}`,
      label,
      low_confidence: low,
      reason: "Fixture judgment only",
      reviewed_at: "2026-09-12T12:00:00Z",
    })),
  };
}
const predictions = packet.records.map((r) => ({
  record_id: r.record_id,
  label: "neither",
  label_origin: "rule",
}));
test("ambiguity and low confidence are separate", () => {
  const result = validateExport(
    body("R1", [
      ["1", "ambiguous", false],
      ["2", "neither", true],
    ]),
    packet,
  );
  assert.equal(result.decisions[0].low_confidence, false);
  assert.equal(result.decisions[1].label, "neither");
});
test("reject wrong version, old labels, simulations and non-human provenance", () => {
  for (const change of [
    { packet_id: "stale" },
    { taxonomy_version: "old" },
    { label_origin: "model" },
    { simulation: true },
    { human_attested: false },
  ])
    assert.throws(() => validateExport({ ...body(), ...change }, packet));
  const old = body();
  old.decisions[0].label = "fundamental_aging";
  assert.throws(() => validateExport(old, packet));
});
test("reject stale text, duplicate records, invalid confidence and missing dates", () => {
  for (const change of [
    { source_version: "stale" },
    { record_id: "missing" },
    { low_confidence: "false" },
    { reviewed_at: "2026-09-12" },
    { reason: "" },
  ]) {
    const item = body();
    Object.assign(item.decisions[0], change);
    assert.throws(() => validateExport(item, packet));
  }
  const duplicate = body();
  duplicate.decisions.push(duplicate.decisions[0]);
  assert.throws(() => validateExport(duplicate, packet));
});
test("idempotent imports and conflicting first verdict protection", () => {
  const a = body();
  assert.equal(mergeExports([a], [a], packet)[0].decisions.length, 1);
  const conflict = body("R1", [["1", "ambiguous", true]]);
  assert.throws(
    () => mergeExports([a], [conflict], packet),
    /Conflicting first verdict/,
  );
  assert.equal(a.decisions[0].label, "neither");
});
test("batch import validates atomically", () => {
  const existing = [body()];
  const before = JSON.stringify(existing);
  assert.throws(() =>
    mergeExports(
      existing,
      [body("R2"), { ...body("R3"), packet_id: "wrong" }],
      packet,
    ),
  );
  assert.equal(JSON.stringify(existing), before);
});
test("empty human sample gives no accuracy or agreement", () => {
  const s = summarize(packet, [], predictions);
  assert.equal(s.reviewed_items, 0);
  assert.deepEqual(s.pipelinePairs, []);
  assert.equal(agreement([]).rate, null);
});
test("unequal overlap, individual decisions and per-reviewer model agreement", () => {
  const a = body("R1", [
    ["1", "neither", false],
    ["2", "ambiguous", true],
  ]);
  const b = body("R2", [
    ["1", "consequences", false],
    ["3", "neither", false],
  ]);
  const s = summarize(packet, [a, b], predictions);
  assert.equal(s.decisions, 4);
  assert.equal(s.overlapping_items, 1);
  assert.equal(s.reviewerPairs[0].n, 1);
  assert.equal(s.reviewerPairs[0].rate, 0);
  assert.deepEqual(
    s.pipelinePairs.map((p) => p.rate),
    [0.5, 0.5],
  );
  assert.equal(s.items[0].record.record_id, "1");
  assert.equal(s.items[0].decisions.length, 2);
});
test("kappa is null when chance agreement is one or no overlap", () => {
  assert.equal(agreement([["neither", "neither"]]).kappa, null);
  assert.equal(agreement([]).kappa, null);
  assert.equal(
    agreement([
      ["neither", "neither"],
      ["ambiguous", "ambiguous"],
    ]).kappa,
    1,
  );
});
test("CSV preserves individual provenance and escapes formulas, commas and newlines", () => {
  assert.equal(csvCell("=1+1"), '"\'=1+1"');
  assert.equal(csvCell(" \t@SUM(1)"), '"\' \t@SUM(1)"');
  assert.equal(csvCell('a,"b"\nc'), '"a,""b""\nc"');
  const a = body();
  a.decisions[0].reason = "=malicious formula";
  const s = summarize(packet, [a, body("R2")], predictions);
  const csv = exportCSV(packet, s);
  assert.equal(csv.split("\r\n").length, 4);
  assert.match(csv, /label_origin/);
  assert.match(csv, /"human"/);
  assert.match(csv, /'=malicious/);
});
