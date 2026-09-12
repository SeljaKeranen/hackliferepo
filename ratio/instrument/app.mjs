import {
  FORMAT,
  reviewerValid,
  validateExport,
  mergeExports,
  summarize,
  exportCSV,
} from "./review.mjs";
const app = document.querySelector("#app");
let packet,
  predictions,
  index = 0;
const node = (tag, text, className) => {
  const n = document.createElement(tag);
  if (text != null) n.textContent = text;
  if (className) n.className = className;
  return n;
};
const button = (text, fn, secondary = false) => {
  const n = node("button", text, secondary ? "secondary" : "");
  n.type = "button";
  n.onclick = fn;
  return n;
};
const link = (text, url) => {
  const n = node("a", text);
  n.href = url;
  return n;
};
const nameFor = (id) =>
  packet.taxonomy.labels.find((x) => x.id === id)?.name || id;
const storageKey = (kind, reviewer = "") =>
  `longview-instrument:${packet.packet_id}:${kind}:${reviewer}`;
function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    throw new Error(
      "Saved browser data could not be read. Do not clear it; preserve your exports and ask the team to recover the data.",
    );
  }
}
function write(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}
function download(name, content, type = "application/json") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([content], { type }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function error(text, target = app) {
  target.append(node("p", text, "error"));
}
function heading(kicker, title, description) {
  app.replaceChildren(
    node("div", kicker, "eyebrow"),
    node("h1", title),
    node("p", description, "lead"),
  );
}
function rubric() {
  const box = node("div", null, "panel");
  box.append(node("h2", "Working labeling rules"));
  for (const label of packet.taxonomy.labels) {
    const d = node("details");
    d.append(node("summary", label.name), node("p", label.description));
    box.append(d);
  }
  box.append(
    node("p", packet.taxonomy.confidence_note, "small"),
    node("p", packet.taxonomy.status, "small"),
  );
  return box;
}
function stat(value, caption) {
  const box = node("div", null, "stat");
  box.append(node("strong", value), node("span", caption));
  return box;
}
function metadata() {
  return node(
    "p",
    `Taxonomy ${packet.taxonomy_version} · Packet ${packet.packet_id.slice(0, 12)} · Development review`,
    "meta",
  );
}
function overview() {
  heading(
    "Research funding / validation instrument",
    "A shared way to judge what ageing research is for.",
    "Read the source. Label the purpose. Compare independent decisions before estimating funding.",
  );
  const actions = node("div", null, "actions");
  const start = link("Start labeling →", "#label");
  start.className = "button";
  actions.append(start, link("Open research admin", "#admin"));
  app.append(actions);
  const grid = node("div", null, "grid panel");
  grid.append(
    stat(packet.audit.records.toLocaleString(), "existing corpus records"),
    stat(packet.audit.sample_size, "shared development review items"),
    stat("None", "external classifier validation"),
  );
  app.append(grid);
  const method = node("div", null, "panel");
  method.append(
    node("h2", "The instrument is the deliverable."),
    node(
      "p",
      "The source corpus and pipeline already exist. This version gives researchers a common rubric, a blind labeling workspace and an admin view of disagreements. Earlier AI-generated “expert” labels do not count as human evidence.",
    ),
    node(
      "p",
      "No funding number, cancer calibration, or country map is part of this release. The 90% human-agreement requirement remains a future acceptance target; this development sample cannot establish final accuracy.",
    ),
  );
  const scope = node("ul");
  for (const [source, count] of Object.entries(packet.audit.source_counts))
    scope.append(node("li", `${source}: ${count.toLocaleString()} records`));
  method.append(
    scope,
    node("p", packet.audit.corpus_scope),
    node("p", packet.audit.text_note),
    node(
      "p",
      `${packet.audit.missing_abstracts} missing abstracts; ${packet.audit.possibly_truncated_abstracts} at the collection text limit. No additional truncation or translation is applied here.`,
      "small",
    ),
  );
  app.append(method, rubric(), metadata());
}
function currentReviewer() {
  return read(storageKey("reviewer"), "");
}
function humanExport(reviewer, decisions) {
  return {
    format: FORMAT,
    packet_id: packet.packet_id,
    taxonomy_version: packet.taxonomy_version,
    label_origin: "human",
    human_attested: true,
    reviewer,
    decisions,
  };
}
function savedDecisions(reviewer) {
  const raw = read(storageKey("decisions", reviewer), []);
  if (!raw.length) return [];
  return validateExport(humanExport(reviewer, raw), packet).decisions;
}
function labelView() {
  heading(
    "Independent source review",
    "Label the research purpose.",
    "Use a reviewer code. Initial judgments hide pipeline labels and other reviewers’ decisions.",
  );
  const controls = node("div", null, "panel");
  const identity = node("label", "Reviewer code ", "field");
  const name = document.createElement("input");
  name.type = "text";
  name.id = "reviewer";
  name.placeholder = "e.g. AP01";
  name.autocomplete = "off";
  name.value = currentReviewer();
  identity.append(name);
  controls.append(identity);
  controls.append(
    node(
      "p",
      "Use a code rather than your full name. Progress stays in this browser; exports let the research admin combine reviewers. There is no automatic upload or shared database.",
      "small",
    ),
  );
  const attestation = node("label", null, "check");
  const human = document.createElement("input");
  human.type = "checkbox";
  human.id = "attest";
  human.checked = read(storageKey("attested", name.value), false);
  attestation.append(
    human,
    node(
      "span",
      "I am a human reviewer. I will read the source text and make my own judgment.",
    ),
  );
  controls.append(attestation);
  const status = node("p");
  controls.append(status);
  const meter = document.createElement("progress");
  meter.max = packet.records.length;
  controls.append(meter);
  const exportButton = button("Export completed reviews", () => {
    try {
      const reviewer = name.value.trim();
      const body = validateExport(
        humanExport(reviewer, savedDecisions(reviewer)),
        packet,
      );
      download(`human-labels-${reviewer}.json`, JSON.stringify(body, null, 2));
    } catch (e) {
      error(e.message, controls);
    }
  });
  exportButton.id = "export-reviews";
  const exportActions = node("div", null, "actions");
  exportActions.append(exportButton);
  controls.append(exportActions);
  app.append(controls);
  const card = node("div", null, "panel");
  app.append(card);
  function renderRecord() {
    card.replaceChildren();
    let decisions = [];
    try {
      decisions = savedDecisions(name.value.trim());
    } catch (e) {
      error(e.message, card);
      return;
    }
    meter.value = decisions.length;
    status.textContent = `${decisions.length} / ${packet.records.length} saved in this browser for ${name.value.trim() || "this reviewer"}`;
    const record = packet.records[index],
      saved = decisions.find((d) => d.record_id === record.record_id);
    const nav = node("div", null, "actions");
    const select = document.createElement("select");
    select.id = "record-select";
    select.setAttribute("aria-label", "Grant to review");
    packet.records.forEach((r, i) => {
      const option = node(
        "option",
        `${decisions.some((d) => d.record_id === r.record_id) ? "✓ " : ""}${i + 1}. ${r.title}`,
      );
      option.value = i;
      select.append(option);
    });
    select.value = index;
    select.onchange = () => {
      index = Number(select.value);
      renderRecord();
    };
    nav.append(
      select,
      button(
        "Next unreviewed",
        () => {
          const next = packet.records.findIndex(
            (r) => !decisions.some((d) => d.record_id === r.record_id),
          );
          if (next >= 0) index = next;
          renderRecord();
        },
        true,
      ),
    );
    card.append(nav);
    card.append(
      node("h2", record.title),
      node(
        "p",
        `${record.record_id} · ${record.source} · award year ${record.year} · retrieved ${record.retrieved_at}`,
        "meta",
      ),
    );
    if (record.url && /^https?:\/\//.test(record.url)) {
      const source = link("Open original source ↗", record.url);
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      card.append(source);
    }
    const textNote =
      record.text_status === "missing_abstract"
        ? "No abstract was collected. Inspect the original source; use low confidence if evidence remains insufficient."
        : record.text_status === "possibly_truncated"
          ? "The collected abstract reaches the 6,000-character limit and may be truncated. Check the source for the remaining text."
          : "Showing the entire collected abstract. Completeness against the source has not been verified.";
    card.append(node("p", textNote, "small"));
    const layout = node("div", null, "split");
    layout.append(
      node("div", record.abstract || "No abstract available.", "abstract"),
    );
    const form = document.createElement("form");
    form.id = "decision-form";
    const choices = document.createElement("fieldset");
    choices.append(node("legend", "Primary research purpose"));
    for (const label of packet.taxonomy.labels) {
      const option = node("label", null, "category");
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "category";
      input.value = label.id;
      input.required = true;
      input.checked = saved?.label === label.id;
      option.append(input, node("span", label.name));
      choices.append(option);
    }
    form.append(choices);
    const low = node("label", null, "check");
    const lowInput = document.createElement("input");
    lowInput.type = "checkbox";
    lowInput.id = "low-confidence";
    lowInput.checked = saved?.low_confidence || false;
    low.append(
      lowInput,
      node("span", "Low confidence in this judgment (independent of category)"),
    );
    form.append(low);
    const reasonLabel = node(
      "label",
      "Short reason, including any missing evidence",
      "field",
    );
    const reason = document.createElement("textarea");
    reason.id = "reason";
    reason.required = true;
    reason.minLength = 3;
    reason.maxLength = 4000;
    reason.value = saved?.reason || "";
    reasonLabel.append(reason);
    form.append(reasonLabel);
    const submit = node(
      "button",
      saved ? "First verdict saved" : "Save human verdict",
    );
    submit.type = "submit";
    form.append(submit);
    if (saved) {
      form
        .querySelectorAll("input, textarea, button")
        .forEach((el) => (el.disabled = true));
      form.append(
        node(
          "p",
          "The first completed verdict is retained. Export it; document corrections separately during human adjudication.",
          "small",
        ),
      );
    }
    form.onsubmit = (event) => {
      event.preventDefault();
      try {
        const reviewer = name.value.trim();
        if (!reviewerValid(reviewer) || !human.checked)
          throw new Error(
            "Enter a reviewer code and confirm independent human review first.",
          );
        const label = form.querySelector("input[name=category]:checked")?.value;
        const decision = {
          record_id: record.record_id,
          source_version: record.source_version,
          label,
          low_confidence: lowInput.checked,
          reason: reason.value,
          reviewed_at: new Date().toISOString(),
        };
        const validated = validateExport(
          humanExport(reviewer, [...decisions, decision]),
          packet,
        );
        write(storageKey("decisions", reviewer), validated.decisions);
        renderRecord();
      } catch (e) {
        error(e.message, form);
      }
    };
    layout.append(form);
    card.append(layout);
  }
  name.onchange = () => {
    try {
      const value = name.value.trim();
      if (!reviewerValid(value))
        throw new Error(
          "Use a reviewer code of 2–40 letters, digits, hyphens or underscores.",
        );
      write(storageKey("reviewer"), value);
      human.checked = read(storageKey("attested", value), false);
      renderRecord();
    } catch (e) {
      error(e.message, controls);
    }
  };
  human.onchange = () => {
    try {
      write(storageKey("attested", name.value.trim()), human.checked);
    } catch (e) {
      error(e.message, controls);
    }
  };
  renderRecord();
  app.append(rubric(), metadata());
}
function rate(value) {
  return value == null ? "Not available" : `${(value * 100).toFixed(1)}%`;
}
function table(headers, rows) {
  const wrap = node("div", null, "table-wrap");
  const t = document.createElement("table");
  const head = document.createElement("thead");
  const tr = document.createElement("tr");
  headers.forEach((h) => tr.append(node("th", h)));
  head.append(tr);
  const body = document.createElement("tbody");
  rows.forEach((values) => {
    const row = document.createElement("tr");
    values.forEach((value) => {
      const td = document.createElement("td");
      td.append(
        value instanceof Node ? value : document.createTextNode(String(value)),
      );
      row.append(td);
    });
    body.append(row);
  });
  t.append(head, body);
  wrap.append(t);
  return wrap;
}
async function adminView() {
  heading(
    "Research admin / development sample",
    "Inspect agreement. Keep the disagreements.",
    "This page imports completed human exports and compares each reviewer separately. It never treats an AI label or a majority vote as adjudicated truth.",
  );
  app.append(
    node(
      "p",
      "Researchers should finish their blind judgments before opening this view. Imports and comparisons stay in this browser. Use CSV and JSON exports to preserve the research record.",
      "small",
    ),
  );
  try {
    if (!predictions) {
      const response = await fetch("instrument/output/predictions.json");
      if (!response.ok) throw new Error("Build the predictions packet first.");
      const body = await response.json();
      if (body.packet_id !== packet.packet_id)
        throw new Error(
          "The prediction and source packets have different versions.",
        );
      predictions = body.predictions;
    }
  } catch (e) {
    error(e.message);
    return;
  }
  if (location.hash !== "#admin") return;
  let exports = read(storageKey("admin"), []);
  const controls = node("div", null, "panel");
  const fileLabel = node("label", "Import human review files ", "field");
  const input = document.createElement("input");
  input.type = "file";
  input.multiple = true;
  input.accept = ".json";
  input.id = "import-reviews";
  fileLabel.append(input);
  controls.append(fileLabel);
  const message = node("p");
  message.id = "admin-message";
  controls.append(message);
  const actions = node("div", null, "actions");
  controls.append(actions);
  app.append(controls);
  const results = node("div");
  app.append(results);
  function render() {
    const s = summarize(packet, exports, predictions);
    results.replaceChildren();
    actions.replaceChildren();
    actions.append(
      button("Export decisions CSV", () =>
        download(
          "human-decisions.csv",
          exportCSV(packet, s),
          "text/csv;charset=utf-8",
        ),
      ),
      button(
        "Export review archive JSON",
        () =>
          download(
            "human-review-archive.json",
            JSON.stringify(
              {
                format: "longview-human-archive-v1",
                packet_id: packet.packet_id,
                exports,
              },
              null,
              2,
            ),
          ),
        true,
      ),
    );
    const grid = node("div", null, "grid panel");
    grid.append(
      stat(
        `${s.reviewed_items}/${packet.records.length}`,
        "items with human labels",
      ),
      stat(s.overlapping_items, "items with independent overlapping labels"),
      stat(s.disputed_items, "items with human category disagreement"),
    );
    results.append(grid);
    results.append(
      node(
        "p",
        `${s.reviewers} reviewer codes · ${s.decisions} individual decisions. Identity and independence are attested, not authenticated. No external validation. These unweighted development-sample comparisons do not establish population accuracy or satisfy the 90% final-evaluation target.`,
        "small",
      ),
    );
    const pairs = node("div", null, "panel");
    pairs.append(node("h2", "Labeller vs labeller"));
    if (!s.reviewerPairs.length)
      pairs.append(
        node(
          "p",
          "Import at least two reviewers with overlapping items to measure agreement.",
        ),
      );
    else
      pairs.append(
        table(
          [
            "Reviewers",
            "Overlap",
            "Category agreement",
            "Cohen’s κ",
            "Confidence flag agreement",
          ],
          s.reviewerPairs.map((p) => [
            `${p.left} / ${p.right}`,
            p.n,
            rate(p.rate),
            p.kappa == null ? "Undefined" : p.kappa.toFixed(3),
            p.n ? `${p.confidence_agree}/${p.n}` : "No overlap",
          ]),
        ),
      );
    results.append(pairs);
    const model = node("div", null, "panel");
    model.append(node("h2", "Pipeline vs each human reviewer"));
    if (!s.pipelinePairs.length)
      model.append(
        node(
          "p",
          "No imported human decisions. Model output alone gives no human agreement result.",
        ),
      );
    else
      model.append(
        table(
          ["Reviewer", "Compared items", "Category agreement"],
          s.pipelinePairs.map((p) => [p.reviewer, p.n, rate(p.rate)]),
        ),
      );
    model.append(
      node(
        "p",
        "Agreement includes all four categories. Ambiguous remains visible; low confidence is counted separately. No reviewer is selected as ground truth.",
        "small",
      ),
    );
    results.append(model);
    const itemBox = node("div", null, "panel");
    itemBox.append(node("h2", "Items, disagreements first"));
    for (const item of s.items) {
      const d = document.createElement("details");
      const summary = node(
        "summary",
        `${item.human_disagreement ? "Disagreement · " : ""}${item.label_count} labels · ${item.record.title}`,
      );
      d.dataset.recordId = item.record.record_id;
      d.append(summary);
      const detail = node("div");
      detail.append(
        node(
          "p",
          `${item.record.record_id} · ${item.low_confidence_count} low-confidence decisions`,
          "meta",
        ),
      );
      detail.append(
        node(
          "p",
          packet.taxonomy.labels
            .map((l) => `${l.name}: ${item.counts[l.id]}`)
            .join(" · "),
          "small",
        ),
      );
      const p = item.prediction;
      if (p) {
        detail.append(
          node(
            "p",
            `Unvalidated ${p.label_origin} candidate: ${nameFor(p.label)}${p.low_confidence ? " · low confidence" : ""}`,
          ),
          node("p", p.reason, "small"),
        );
        for (const quote of p.evidence || [])
          detail.append(node("blockquote", quote, "small"));
      }
      if (item.decisions.length)
        detail.append(
          table(
            ["Reviewer", "Category", "Low confidence", "Reason", "Date"],
            item.decisions.map((r) => [
              r.reviewer,
              nameFor(r.label),
              r.low_confidence ? "Yes" : "No",
              r.reason,
              r.reviewed_at,
            ]),
          ),
        );
      const source = link(
        "Open original source ↗",
        /^https?:\/\//.test(item.record.url) ? item.record.url : "#admin",
      );
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      detail.append(
        source,
        node("p", `Source retrieved ${item.record.retrieved_at}`, "small"),
      );
      d.append(detail);
      itemBox.append(d);
    }
    results.append(itemBox);
  }
  input.onchange = async () => {
    try {
      const bodies = [];
      for (const file of input.files) {
        const body = JSON.parse(await file.text());
        if (body.format === "longview-human-archive-v1") {
          if (
            body.packet_id !== packet.packet_id ||
            !Array.isArray(body.exports)
          )
            throw new Error("Invalid or stale archive.");
          bodies.push(...body.exports);
        } else bodies.push(body);
      }
      const next = mergeExports(exports, bodies, packet);
      write(storageKey("admin"), next);
      exports = next;
      render();
      message.className = "success";
      message.textContent =
        "Human files imported. Existing first verdicts were preserved.";
    } catch (e) {
      message.className = "error";
      message.textContent = e.message;
    } finally {
      input.value = "";
    }
  };
  try {
    render();
  } catch (e) {
    error(e.message, results);
  }
  app.append(metadata());
}
function route() {
  if (!packet) return;
  try {
    if (location.hash === "#label") labelView();
    else if (location.hash === "#admin")
      adminView().catch((e) => error(e.message));
    else overview();
  } catch (e) {
    error(e.message);
  }
}
try {
  const response = await fetch("instrument/output/packet.json");
  if (!response.ok)
    throw new Error(
      "The review packet has not been built. Run “python3 -m ratio.instrument.build” from the repository root, then serve the repository over HTTP.",
    );
  packet = await response.json();
  if (packet.format !== "longview-instrument-v1")
    throw new Error("Wrong review packet format.");
  route();
  window.addEventListener("hashchange", route);
} catch (e) {
  app.replaceChildren(node("h1", "Build the local review packet."));
  error(e.message);
  app.append(
    node(
      "p",
      "Generated abstracts and human decisions stay out of Git. See the instrument guide for build and hosting instructions.",
    ),
  );
}
