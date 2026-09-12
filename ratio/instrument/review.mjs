// Browser and Node share the same import validation and descriptive statistics.
export const FORMAT = "longview-human-labels-v1";
export const LABELS = [
  "preventing_slowing",
  "consequences",
  "neither",
  "ambiguous",
];
export const reviewerValid = (value) =>
  typeof value === "string" && /^[A-Za-z0-9_-]{2,40}$/.test(value);

export function validateExport(body, packet) {
  if (
    !body ||
    body.format !== FORMAT ||
    body.label_origin !== "human" ||
    body.human_attested !== true ||
    body.simulation === true
  )
    throw new Error(
      "Import an attested human export from this instrument. Model and simulation files are not human labels.",
    );
  if (
    body.packet_id !== packet.packet_id ||
    body.taxonomy_version !== packet.taxonomy_version
  )
    throw new Error(
      "This export belongs to a different corpus, pipeline or taxonomy version.",
    );
  if (!reviewerValid(body.reviewer))
    throw new Error(
      "Use a reviewer code of 2–40 letters, digits, hyphens or underscores.",
    );
  if (!Array.isArray(body.decisions) || !body.decisions.length)
    throw new Error("The export contains no completed decisions.");
  const records = new Map(packet.records.map((r) => [r.record_id, r]));
  const seen = new Set();
  const decisions = body.decisions.map((d) => {
    if (!d || typeof d !== "object" || seen.has(d.record_id))
      throw new Error("Duplicate or invalid decision.");
    seen.add(d.record_id);
    const record = records.get(d.record_id);
    if (!record || record.source_version !== d.source_version)
      throw new Error("Unknown record or stale source text: " + d.record_id);
    if (!LABELS.includes(d.label) || typeof d.low_confidence !== "boolean")
      throw new Error(
        "Each decision needs one current category and a separate confidence flag.",
      );
    if (
      typeof d.reason !== "string" ||
      d.reason.trim().length < 3 ||
      d.reason.length > 4000
    )
      throw new Error(
        "Each decision needs a short reason (3–4,000 characters).",
      );
    if (
      typeof d.reviewed_at !== "string" ||
      !/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(d.reviewed_at) ||
      !Number.isFinite(Date.parse(d.reviewed_at))
    )
      throw new Error("A decision is missing a dated timestamp with timezone.");
    if (d.label_origin && d.label_origin !== "human")
      throw new Error("Non-human decision rejected.");
    return {
      record_id: d.record_id,
      source_version: d.source_version,
      label: d.label,
      low_confidence: d.low_confidence,
      reason: d.reason.trim(),
      reviewed_at: d.reviewed_at,
    };
  });
  return {
    format: FORMAT,
    packet_id: packet.packet_id,
    taxonomy_version: packet.taxonomy_version,
    reviewer: body.reviewer,
    label_origin: "human",
    human_attested: true,
    decisions,
  };
}

export function mergeExports(existing, incoming, packet) {
  const byReviewer = new Map();
  // Validate the entire batch before returning any change to the caller.
  for (const body of [...existing, ...incoming]) {
    const clean = validateExport(body, packet);
    const current = byReviewer.get(clean.reviewer) || {
      ...clean,
      decisions: [],
    };
    const decisions = new Map(current.decisions.map((d) => [d.record_id, d]));
    for (const decision of clean.decisions) {
      const first = decisions.get(decision.record_id);
      if (first && JSON.stringify(first) !== JSON.stringify(decision))
        throw new Error(
          `Conflicting first verdict for ${clean.reviewer} on ${decision.record_id}. Preserve both files for a separate adjudication; no labels were overwritten.`,
        );
      decisions.set(decision.record_id, decision);
    }
    current.decisions = [...decisions.values()].sort((a, b) =>
      a.record_id.localeCompare(b.record_id),
    );
    byReviewer.set(clean.reviewer, current);
  }
  return [...byReviewer.values()].sort((a, b) =>
    a.reviewer.localeCompare(b.reviewer),
  );
}

export function agreement(pairs) {
  if (!pairs.length) return { n: 0, agree: 0, rate: null, kappa: null };
  const agree = pairs.filter(([a, b]) => a === b).length;
  const rate = agree / pairs.length;
  const expected = LABELS.reduce(
    (sum, label) =>
      sum +
      ((pairs.filter(([a]) => a === label).length / pairs.length) *
        pairs.filter(([, b]) => b === label).length) /
        pairs.length,
    0,
  );
  return {
    n: pairs.length,
    agree,
    rate,
    kappa: expected === 1 ? null : (rate - expected) / (1 - expected),
  };
}

export function summarize(packet, exports, predictions) {
  const clean = mergeExports([], exports, packet);
  const model = new Map(predictions.map((p) => [p.record_id, p]));
  const humans = new Map(
    clean.map((e) => [
      e.reviewer,
      new Map(e.decisions.map((d) => [d.record_id, d])),
    ]),
  );
  const reviewerPairs = [];
  const names = [...humans.keys()];
  for (let i = 0; i < names.length; i++)
    for (let j = i + 1; j < names.length; j++) {
      const left = humans.get(names[i]),
        right = humans.get(names[j]);
      const overlap = [...left.keys()].filter((id) => right.has(id));
      reviewerPairs.push({
        left: names[i],
        right: names[j],
        ...agreement(
          overlap.map((id) => [left.get(id).label, right.get(id).label]),
        ),
        confidence_agree: overlap.filter(
          (id) => left.get(id).low_confidence === right.get(id).low_confidence,
        ).length,
      });
    }
  const pipelinePairs = names.map((reviewer) => ({
    reviewer,
    ...agreement(
      [...humans.get(reviewer)]
        .filter(([id]) => model.has(id))
        .map(([id, d]) => [d.label, model.get(id).label]),
    ),
  }));
  const items = packet.records
    .map((record) => {
      const decisions = clean.flatMap((e) =>
        e.decisions
          .filter((d) => d.record_id === record.record_id)
          .map((d) => ({ reviewer: e.reviewer, ...d })),
      );
      const prediction = model.get(record.record_id);
      const counts = Object.fromEntries(
        LABELS.map((label) => [
          label,
          decisions.filter((d) => d.label === label).length,
        ]),
      );
      return {
        record,
        decisions,
        prediction,
        counts,
        label_count: decisions.length,
        human_disagreement: new Set(decisions.map((d) => d.label)).size > 1,
        pipeline_disagreements: prediction
          ? decisions.filter((d) => d.label !== prediction.label).length
          : 0,
        low_confidence_count: decisions.filter((d) => d.low_confidence).length,
      };
    })
    .sort(
      (a, b) =>
        Number(b.human_disagreement) - Number(a.human_disagreement) ||
        b.pipeline_disagreements - a.pipeline_disagreements ||
        b.low_confidence_count - a.low_confidence_count ||
        a.record.record_id.localeCompare(b.record.record_id),
    );
  return {
    reviewers: names.length,
    decisions: clean.reduce((n, e) => n + e.decisions.length, 0),
    reviewed_items: items.filter((i) => i.label_count).length,
    overlapping_items: items.filter((i) => i.label_count >= 2).length,
    disputed_items: items.filter((i) => i.human_disagreement).length,
    reviewerPairs,
    pipelinePairs,
    items,
  };
}

export function csvCell(value) {
  let text = value == null ? "" : String(value);
  if (/^[\s\uFEFF]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text))
    text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}

export function exportCSV(packet, summary) {
  const headings = [
    "record_id",
    "source",
    "source_url",
    "source_date",
    "text_version",
    "taxonomy_version",
    "packet_id",
    "reviewer",
    "label_origin",
    "human_label",
    "low_confidence",
    "reason",
    "reviewed_at",
    "pipeline_label",
    "pipeline_origin",
    "pipeline_agrees",
    "human_label_count",
    "human_disagreement",
  ];
  const rows = summary.items.flatMap((item) =>
    item.decisions.map((d) => [
      item.record.record_id,
      item.record.source,
      item.record.url,
      item.record.retrieved_at,
      item.record.source_version,
      packet.taxonomy_version,
      packet.packet_id,
      d.reviewer,
      "human",
      d.label,
      d.low_confidence,
      d.reason,
      d.reviewed_at,
      item.prediction?.label,
      item.prediction?.label_origin,
      item.prediction ? item.prediction.label === d.label : "",
      item.label_count,
      item.human_disagreement,
    ]),
  );
  return (
    [headings, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n") +
    "\r\n"
  );
}
