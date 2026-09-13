"use strict";

/* Longevity Politics Index — two decoupled layers over one map:

   - funding (default): the funding-gap ratio as a 0–100 index, read from
     ratio/output/aggregates{,_adjudicated}.json and drilled into with
     ratio/output/labels{,_adjudicated}.jsonl. Sweden keeps its national
     SweCRIS corpus; the other 26 EU members and the US carry the European
     Commission and NIH numbers. Method and caveats live in ratio/README.md.
   - politics: the original findings layer, read from eval/findings/ and
     eval/verdicts/, scored by map/scoring.js (documented in map/README.md).

   Both layers render into the same map and panel but share no data path. */

const { scoreCountry, jurisdictionFor, ratioIndex, JURISDICTIONS } = window.Scoring;

const NOW = new Date();

/* ---------- layer + scenario state (URL-shareable) ---------- */

const QS = new URLSearchParams(location.search);
const LAYERS = ["funding", "politics"];
const SCENARIOS = ["rules", "adjudicated"];
let LAYER = LAYERS.includes(QS.get("layer")) ? QS.get("layer") : "funding";
let SCENARIO = SCENARIOS.includes(QS.get("scenario")) ? QS.get("scenario") : "rules";

let selection = { layer: null, key: null }; // key: jurisdiction code or ISO
let grantView = null; // { region, cats, label } drill-down in the funding layer
let grantShown = 0;

function syncURL() {
  const qs = new URLSearchParams();
  if (LAYER !== "funding") qs.set("layer", LAYER);
  if (SCENARIO !== "rules") qs.set("scenario", SCENARIO);
  if (LAYER === "funding" && selection.layer === "funding" && selection.key) {
    qs.set("region", selection.key);
  }
  const q = qs.toString();
  history.replaceState(null, "", q ? `${location.pathname}?${q}` : location.pathname);
}

function bumpGrantView(view) {
  grantView = view;
  grantShown = 0;
}

/* ---------- generic fetching ---------- */

async function fetchJSON(url) {
  // Distinguishes "absent" (404, an expected state) from "broken" (network
  // error, server error, malformed JSON) so failures can be surfaced.
  try {
    const res = await fetch(url);
    if (res.status === 404) return { state: "missing", data: null };
    if (!res.ok) return { state: "error", data: null };
    return { state: "ok", data: await res.json() };
  } catch {
    return { state: "error", data: null };
  }
}

async function fetchText(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return { state: "error", data: null };
    return { state: "ok", data: await res.text() };
  } catch {
    return { state: "error", data: null };
  }
}

const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"']/g, (ch) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch])
  );

const fmtEUR = (v) => {
  if (v == null || !isFinite(v)) return "\u2014";
  if (Math.abs(v) >= 1e9) return "\u20ac" + (v / 1e9).toFixed(1) + "B";
  if (Math.abs(v) >= 1e6) return "\u20ac" + (v / 1e6).toFixed(1) + "M";
  if (Math.abs(v) >= 1e3) return "\u20ac" + (v / 1e3).toFixed(0) + "k";
  return "\u20ac" + Math.round(v);
};
const pct = (v) => (typeof v === "number" && isFinite(v) ? (v * 100).toFixed(1) + "%" : "\u2014");

/* ---------- funding-gap layer data ---------- */

const RATIO_BASE = "../ratio/output/";
const FUND_FILES = {
  rules: { agg: "aggregates.json", labels: "labels.jsonl" },
  adjudicated: { agg: "aggregates_adjudicated.json", labels: "labels_adjudicated.jsonl" },
};
const FUND = { rules: null, adjudicated: null }; // { agg, labels, labelsPromise, labelsError }
let fundingError = "";

// Pitch switch: the method note and the caveat list stay in the built data and
// on the ratio page, but the map hides them for the demo. Flip to true to show
// them again.
const SHOW_METHOD_NOTES = false;

const CATS = [
  ["fundamental_aging", "Fundamental ageing biology"],
  ["intervention", "Interventions against ageing"],
  ["age_related_disease", "Age-related disease"],
  ["care", "Care of older people"],
  ["social_population_aging", "Ageing societies & populations"],
  ["ambiguous", "Ambiguous"],
  ["not_relevant", "Not relevant (excluded)"],
];
const CAT_NAME = Object.fromEntries(CATS.map(([key, name]) => [key, name]));
const REGION_ORDER = ["SE", "EU", "US"];

async function loadFunding(scenario) {
  if (FUND[scenario]) return FUND[scenario];
  const files = FUND_FILES[scenario];
  const res = await fetchJSON(RATIO_BASE + files.agg);
  if (res.state !== "ok" || !res.data || !res.data.regions) {
    throw new Error(
      `ratio/output/${files.agg} could not be loaded; run python3 ratio/build.py` +
        (scenario === "adjudicated" ? " and build_adjudicated.py" : "")
    );
  }
  FUND[scenario] = { agg: res.data, labels: null, labelsPromise: null, labelsError: "" };
  return FUND[scenario];
}

function funding() {
  return FUND[SCENARIO];
}

// Labels are ~9 MB and only needed once a jurisdiction panel asks for grants,
// so fetch them on first drill-down rather than on boot.
function ensureLabels() {
  const f = funding();
  if (!f || f.labels || f.labelsError || f.labelsPromise) return;
  const file = FUND_FILES[SCENARIO].labels;
  f.labelsPromise = fetchText(RATIO_BASE + file).then((res) => {
    f.labelsPromise = null;
    if (res.state !== "ok") {
      f.labelsError = `ratio/output/${file} could not be loaded.`;
    } else {
      try {
        f.labels = res.data.trim().split("\n").filter(Boolean).map((l) => JSON.parse(l));
      } catch (e) {
        f.labelsError = `ratio/output/${file} is malformed (${e}).`;
      }
    }
    renderPanel();
  });
  renderPanel();
}

/* ---------- politics layer data ---------- */

const FINDINGS_BASE = "../eval/findings/";
const VERDICTS_BASE = "../eval/verdicts/";
// Tried when the server offers no directory listing for eval/findings/.
const FALLBACK_FILES = ["sweden.json", "us.json", "singapore.json"];

// Countries whose findings exist but that the 1:110m geometry omits; rendered
// as circle markers at [lon, lat].
const MICRO = {
  SG: { name: "Singapore", coords: [103.82, 1.352] },
  MT: { name: "Malta", coords: [14.42, 35.9] },
};

const loadWarnings = [];

async function listFindingsFiles() {
  // python3 -m http.server serves an HTML directory listing; parse its links so
  // any eval/findings/*.json added later shows up with no code change.
  try {
    const res = await fetch(FINDINGS_BASE);
    const type = res.headers.get("Content-Type") || "";
    if (res.ok && type.includes("html")) {
      const html = await res.text();
      const names = [...html.matchAll(/href="([^"?]+\.json)"/g)]
        .map((m) => decodeURIComponent(m[1]).split("/").pop());
      if (names.length) return { files: [...new Set(names)], mode: "listing" };
    }
  } catch {
    /* fall through to the fixed candidate list */
  }
  return { files: FALLBACK_FILES, mode: "fallback" };
}

async function loadPolitics() {
  loadWarnings.length = 0;
  const discovery = await listFindingsFiles();
  if (discovery.mode === "fallback") {
    loadWarnings.push(
      "No directory listing at eval/findings/; discovery fell back to a fixed " +
        "candidate list, so country files added later may be missing here."
    );
  }
  const byCountry = new Map();
  await Promise.all(
    discovery.files.map(async (file) => {
      const base = file.replace(/\.json$/, "");
      const [findingsRes, verdictsRes] = await Promise.all([
        fetchJSON(FINDINGS_BASE + file),
        fetchJSON(`${VERDICTS_BASE}${base}.verdicts.json`),
      ]);
      if (findingsRes.state === "error" || (findingsRes.state === "ok" && !Array.isArray(findingsRes.data))) {
        loadWarnings.push(`Findings file ${file} failed to load and is not shown.`);
        return;
      }
      if (findingsRes.state === "missing") return; // fallback candidate that doesn't exist
      if (verdictsRes.state === "error") {
        loadWarnings.push(
          `Verdicts for ${base} failed to load; its findings are shown as awaiting review.`
        );
      }
      const verdicts =
        verdictsRes.state === "ok" && verdictsRes.data && typeof verdictsRes.data === "object"
          ? verdictsRes.data
          : {};
      for (const rec of findingsRes.data) {
        if (!rec || typeof rec.country !== "string") continue;
        const iso = rec.country.toUpperCase();
        if (!byCountry.has(iso)) byCountry.set(iso, { iso, records: [], verdicts: {} });
        byCountry.get(iso).records.push(rec);
      }
      for (const [id, v] of Object.entries(verdicts)) {
        const iso = id.slice(0, 2).toUpperCase();
        if (byCountry.has(iso)) byCountry.get(iso).verdicts[id] = v;
        else loadWarnings.push(`Verdict ${id} in ${base} matches no loaded finding country.`);
      }
    })
  );
  return new Map([...byCountry].map(([iso, entry]) => [iso, scoreCountry(entry, NOW)]));
}

/* ---------- colors + map ---------- */

const ramp = (t) => d3.interpolateViridis(0.16 + 0.8 * t);
const EMPTY_FILL = "#1a2231";

const svg = d3.select("#map");
const stage = document.getElementById("stage");
const tooltip = document.getElementById("tooltip");
const panelBody = document.getElementById("panel-body");

let countries = new Map(); // politics layer: iso -> scored entry
let world = null;
let nameByIso = new Map();
let zoomBehavior = null;

const projection = d3.geoNaturalEarth1();
const geoPath = d3.geoPath(projection);
const gRoot = svg.append("g");

function fitProjection() {
  const w = stage.clientWidth;
  const h = stage.clientHeight;
  const panelW = w > 760 ? 430 : 0;
  projection.fitExtent(
    [
      [28, Math.min(150, h * 0.16)],
      [Math.max(300, w - panelW), h - 30],
    ],
    { type: "Sphere" }
  );
}

function fundingIndexFor(iso) {
  const f = funding();
  if (!f) return null;
  const j = jurisdictionFor(iso);
  if (!j) return null;
  const d = f.agg.regions[j];
  return d ? ratioIndex(d.ratio) : null;
}

function fillFor(iso) {
  if (LAYER === "funding") {
    const idx = fundingIndexFor(iso);
    return idx == null ? EMPTY_FILL : ramp(idx / 100);
  }
  const c = countries.get(iso);
  if (!c) return EMPTY_FILL;
  if (c.status === "scored") return ramp(c.index / 100);
  if (c.status === "nothing") return "url(#hatch)";
  return EMPTY_FILL;
}

function isInteractive(iso) {
  return LAYER === "funding" ? fundingIndexFor(iso) != null : countries.has(iso);
}

function markersForLayer() {
  if (LAYER === "funding") {
    return [
      { key: "EU", name: "Malta", coords: MICRO.MT.coords, iso: "MT", kind: "iso" },
      { key: "EU", name: "European Commission (CORDIS)", coords: [4.35, 50.85], iso: null, kind: "ec" },
    ];
  }
  return [...countries.keys()]
    .filter((iso) => !nameByIso.has(iso) && MICRO[iso])
    .map((iso) => ({ key: iso, name: MICRO[iso].name, coords: MICRO[iso].coords, iso, kind: "iso" }));
}

function markerFill(m) {
  if (LAYER === "funding") {
    const idx = fundingIndexFor(m.iso || "BE");
    return idx == null ? EMPTY_FILL : ramp(idx / 100);
  }
  return fillFor(m.iso);
}

function markerSelected(m) {
  if (LAYER === "funding") return selection.layer === "funding" && selection.key === m.key;
  return selection.layer === "politics" && selection.key === m.key;
}

function markerAria(m) {
  if (LAYER === "funding") {
    const idx = fundingIndexFor(m.iso || "BE");
    return idx == null ? `${m.name}: no funding-gap data yet` : `${m.name}: funding-gap index ${idx}`;
  }
  return ariaFor(m.iso, m.name);
}

function applyFills(paths, animate) {
  const paint = () => paths.attr("fill", (d) => fillFor(d.properties.iso_a2));
  if (!animate || window.matchMedia("(prefers-reduced-motion: reduce)").matches) paint();
  else requestAnimationFrame(() => requestAnimationFrame(paint));
}

function drawMap() {
  if (!world) return;
  fitProjection();
  gRoot.selectAll("*").remove();

  const defs = svg.selectAll("defs").data([0]).join("defs");
  defs.html(
    '<pattern id="hatch" width="5" height="5" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">' +
      '<rect width="5" height="5" fill="#182234"></rect>' +
      '<rect width="2" height="5" fill="#31425f"></rect></pattern>'
  );

  gRoot.append("path").attr("class", "sphere").attr("d", geoPath({ type: "Sphere" }));
  gRoot.append("path").attr("class", "graticule").attr("d", geoPath(d3.geoGraticule10()));

  const paths = gRoot
    .append("g")
    .selectAll("path")
    .data(world.features)
    .join("path")
    .attr("class", "country")
    .attr("d", geoPath)
    .attr("fill", EMPTY_FILL)
    .style("vector-effect", "non-scaling-stroke")
    .attr("tabindex", (d) => (isInteractive(d.properties.iso_a2) ? 0 : null))
    .attr("role", (d) => (isInteractive(d.properties.iso_a2) ? "button" : null))
    .attr("aria-label", (d) => ariaFor(d.properties.iso_a2, d.properties.name))
    .classed("active", (d) => isInteractive(d.properties.iso_a2))
    .on("mousemove", (event, d) => showTooltip(event, d.properties.iso_a2, d.properties.name))
    .on("mouseleave", hideTooltip)
    .on("click", (event, d) => {
      event.stopPropagation();
      countryClick(d.properties.iso_a2, d.properties.name);
    })
    .on("keydown", (event, d) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        countryClick(d.properties.iso_a2, d.properties.name);
      }
    });
  applyFills(paths, true);

  const markers = gRoot
    .append("g")
    .selectAll("circle")
    .data(markersForLayer())
    .join("circle")
    .attr("class", (m) => "marker" + (m.kind === "ec" ? " ec" : ""))
    .attr("cx", (m) => projection(m.coords)[0])
    .attr("cy", (m) => projection(m.coords)[1])
    .attr("r", (m) => (m.kind === "ec" ? 5.5 : 6))
    .attr("fill", markerFill)
    .attr("tabindex", 0)
    .attr("role", "button")
    .attr("aria-label", markerAria)
    .style("vector-effect", "non-scaling-stroke")
    .on("mousemove", (event, m) => showTooltip(event, m.iso || "BE", m.name))
    .on("mouseleave", hideTooltip)
    .on("click", (event, m) => {
      event.stopPropagation();
      markerClick(m);
    })
    .on("keydown", (event, m) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        markerClick(m);
      }
    });
  markers.classed("selected", markerSelected);

  markSelection();

  zoomBehavior = d3
    .zoom()
    .scaleExtent([1, 14])
    .on("zoom", (event) => {
      gRoot.attr("transform", event.transform);
      gRoot.selectAll(".marker").attr("r", function (m) {
        const base = m.kind === "ec" ? 5.5 : 6;
        return base / Math.sqrt(event.transform.k);
      });
    });
  svg.call(zoomBehavior);
  // Sync the zoom state to the freshly fitted projection; without this a
  // resize while zoomed leaves a stale transform on gRoot.
  svg.call(zoomBehavior.transform, d3.zoomIdentity);
  svg.on("click", () => {
    selection = { layer: null, key: null };
    markSelection();
    renderPanel();
  });
}

function countryClick(iso, name) {
  if (!isInteractive(iso)) return;
  if (LAYER === "funding") {
    const j = jurisdictionFor(iso);
    selection = { layer: "funding", key: j, focusIso: iso };
    bumpGrantView(null);
    markSelection();
    renderPanel();
    zoomToCountry(iso);
    if (!funding() || funding().labels || funding().labelsError) return;
    ensureLabels();
  } else {
    selection = { layer: "politics", key: iso, focusIso: iso };
    markSelection();
    renderPoliticsCountry(iso);
    zoomToCountry(iso);
  }
}

function markerClick(m) {
  if (LAYER === "funding") {
    selection = { layer: "funding", key: m.key, focusIso: m.iso };
    bumpGrantView(null);
    markSelection();
    if (m.iso) zoomToCountry(m.iso);
    else zoomToJurisdiction(m.key);
    renderPanel();
    if (!funding() || funding().labels || funding().labelsError) return;
    ensureLabels();
  } else {
    countryClick(m.iso, m.name);
  }
}

function markSelection() {
  gRoot.selectAll(".country").classed("selected", (d) => {
    const iso = d.properties.iso_a2;
    if (LAYER === "funding") return selection.layer === "funding" && jurisdictionFor(iso) === selection.key;
    return selection.layer === "politics" && iso === selection.key;
  });
  gRoot.selectAll(".marker").classed("selected", markerSelected);
  syncURL();
}

function zoomToCountry(iso) {
  if (!zoomBehavior) return;
  const feature = world.features.find((f) => f.properties.iso_a2 === iso);
  let x, y, k;
  if (feature) {
    const [[x0, y0], [x1, y1]] = geoPath.bounds(feature);
    x = (x0 + x1) / 2;
    y = (y0 + y1) / 2;
    k = Math.min(8, 0.5 / Math.max((x1 - x0) / stage.clientWidth, (y1 - y0) / stage.clientHeight));
  } else if (MICRO[iso]) {
    [x, y] = projection(MICRO[iso].coords);
    k = 6;
  } else {
    return;
  }
  const panelW = stage.clientWidth > 760 ? 430 : 0;
  const transform = d3.zoomIdentity
    .translate((stage.clientWidth - panelW) / 2, stage.clientHeight / 2)
    .scale(Math.max(1, k))
    .translate(-x, -y);
  const motionOk = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  (motionOk ? svg.transition().duration(750) : svg).call(zoomBehavior.transform, transform);
}

function zoomToJurisdiction(key) {
  if (!zoomBehavior) return;
  const feats = world.features.filter((f) => jurisdictionFor(f.properties.iso_a2) === key);
  if (!feats.length) return;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const f of feats) {
    const [[a, b], [c, d]] = geoPath.bounds(f);
    x0 = Math.min(x0, a); y0 = Math.min(y0, b);
    x1 = Math.max(x1, c); y1 = Math.max(y1, d);
  }
  const panelW = stage.clientWidth > 760 ? 430 : 0;
  const k = Math.min(6, 0.85 / Math.max((x1 - x0) / Math.max(1, stage.clientWidth - panelW), (y1 - y0) / stage.clientHeight));
  const transform = d3.zoomIdentity
    .translate((stage.clientWidth - panelW) / 2, stage.clientHeight / 2)
    .scale(Math.max(1, k))
    .translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
  const motionOk = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  (motionOk ? svg.transition().duration(750) : svg).call(zoomBehavior.transform, transform);
}

/* ---------- tooltip ---------- */

function ariaFor(iso, fallbackName) {
  const name = nameByIso.get(iso) || fallbackName || iso;
  if (LAYER === "funding") {
    const j = jurisdictionFor(iso);
    const idx = fundingIndexFor(iso);
    const src = j ? JURISDICTIONS[j].source : "";
    if (idx == null) return `${name}: no funding-gap data yet`;
    return `${name}: funding-gap index ${idx} (${src})`;
  }
  const c = countries.get(iso);
  if (!c) return `${name}: not yet covered`;
  if (c.status === "scored") return `${name}: index ${c.index} from ${c.scored.length} findings`;
  return `${name}: searched, nothing reliable found`;
}

let tooltipKey = null;

function showTooltip(event, iso, name) {
  const key = `${LAYER}:${iso}`;
  if (tooltip.hidden || tooltipKey !== key) {
    tooltipKey = key;
    tooltip.innerHTML = tooltipHTML(iso, name);
    tooltip.hidden = false;
  }
  // A marker may stand in for a country (Malta) or an institution (Brussels);
  // always position against the pointer so it works for both.
  const pad = 14;
  const rect = tooltip.getBoundingClientRect();
  let left = event.clientX + pad;
  let top = event.clientY + pad;
  if (left + rect.width > window.innerWidth - 8) left = event.clientX - rect.width - pad;
  if (top + rect.height > window.innerHeight - 8) top = event.clientY - rect.height - pad;
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function tooltipHTML(iso, name) {
  let html = `<div class="tt-name">${esc(name || iso)}</div>`;
  if (LAYER === "funding") {
    const f = funding();
    const j = jurisdictionFor(iso);
    if (!f || !j || !f.agg.regions[j]) {
      html += `<div class="tt-line">No funding-gap data for this jurisdiction yet.</div>`;
      return html;
    }
    const d = f.agg.regions[j];
    const idx = ratioIndex(d.ratio);
    html += `<div class="tt-line"><span class="tt-score">Funding-gap index ${idx}</span> \u2014 ${pct(d.ratio)} of classified money targets slowing ageing</div>`;
    html += `<div class="tt-line">${fmtEUR(d.numerator_eur)} of ${fmtEUR(d.denominator_eur)} \u00b7 ${d.records.toLocaleString("en-GB")} grants \u00b7 ${pct(d.ambiguous_share)} ambiguous</div>`;
    html += `<div class="tt-line">${esc(JURISDICTIONS[j].name)} \u2014 ${esc(JURISDICTIONS[j].blurb)}</div>`;
    html += `<div class="tt-line">Click for the grant-level detail.</div>`;
    return html;
  }
  const c = countries.get(iso);
  if (!c) {
    html += `<div class="tt-line">Not yet covered by the research agent.</div>`;
  } else if (c.status === "scored") {
    html += `<div class="tt-line"><span class="tt-score">Index ${c.index}</span> from ${c.scored.length} finding${c.scored.length === 1 ? "" : "s"}</div>`;
    html += `<div class="tt-line">${c.verified} human-verified, ${c.pending} awaiting review${c.failed ? `, ${c.failed} failed review` : ""}</div>`;
    html += `<div class="tt-line">Click for the score breakdown.</div>`;
  } else {
    html += `<div class="tt-line">Searched: nothing reliable found. Click for the search notes.</div>`;
  }
  return html;
}

function hideTooltip() {
  tooltip.hidden = true;
  tooltipKey = null;
}

/* ---------- chrome: header, switches, counters, legend ---------- */

const TAGLINES = {
  funding:
    "The funding-gap ratio on the map: of every classified euro in the " +
    "ageing-research census, how much targets slowing ageing itself? " +
    "Sweden, the European Commission and the US, grant by grant.",
  politics:
    "Where governments act on longevity and healthy ageing. Every score " +
    "is built from dated, publicly linked sources \u2014 marked and discounted " +
    "while awaiting human review, and zero if review fails.",
};

function renderChrome() {
  document.getElementById("tagline").textContent = TAGLINES[LAYER];

  document.querySelectorAll("#layer-switch button").forEach((b) => {
    const on = b.dataset.layer === LAYER;
    b.classList.toggle("active", on);
    b.setAttribute("aria-pressed", String(on));
  });
  const scenarioSwitch = document.getElementById("scenario-switch");
  scenarioSwitch.hidden = LAYER !== "funding";
  document.querySelectorAll("#scenario-switch button").forEach((b) => {
    const on = b.dataset.scenario === SCENARIO;
    b.classList.toggle("active", on);
    b.setAttribute("aria-pressed", String(on));
  });

  renderCounters();
  renderLegend();
}

function renderCounters() {
  const box = document.getElementById("counters");
  if (LAYER === "funding") {
    const f = funding();
    if (!f) {
      box.innerHTML = "";
      box.hidden = true;
      return;
    }
    const regions = REGION_ORDER.map((k) => f.agg.regions[k]).filter(Boolean);
    const grants = f.agg.total && typeof f.agg.total.records === "number"
      ? f.agg.total.records
      : regions.reduce((s, d) => s + d.records, 0);
    const slowing = regions.reduce((s, d) => s + d.numerator_eur, 0);
    box.innerHTML = `
      <div class="counter"><b>${regions.length}</b><span>funding jurisdictions</span></div>
      <div class="counter"><b>${grants.toLocaleString("en-GB")}</b><span>grants in the census</span></div>
      <div class="counter"><b>${fmtEUR(slowing)}</b><span>targeting slowing ageing</span></div>`;
    box.hidden = false;
    return;
  }
  const scored = [...countries.values()].filter((c) => c.status === "scored");
  box.innerHTML = `
    <div class="counter"><b>${scored.length}</b><span>countries scored</span></div>
    <div class="counter"><b>${d3.sum(scored, (c) => c.scored.length)}</b><span>cited findings</span></div>
    <div class="counter"><b>${d3.sum(scored, (c) => c.verified)}</b><span>human-verified</span></div>`;
  box.hidden = false;
}

function legendSwatchFill(iso) {
  const idx = fundingIndexFor(iso);
  return idx == null ? EMPTY_FILL : ramp(idx / 100);
}

function renderLegend() {
  const legend = document.getElementById("legend");
  if (LAYER === "funding") {
    const f = funding();
    legend.innerHTML = `
      <div class="legend-title">Funding-gap index, 0&ndash;100</div>
      <canvas id="ramp" width="180" height="10" aria-hidden="true"></canvas>
      <div class="ramp-ends"><span>0</span><span>100</span></div>
      <div class="legend-row"><span class="swatch" style="background:${legendSwatchFill("SE")}"></span>Sweden &mdash; national SweCRIS</div>
      <div class="legend-row"><span class="swatch" style="background:${legendSwatchFill("DE")}"></span>26 other EU members &mdash; European Commission (CORDIS)</div>
      <div class="legend-row"><span class="swatch" style="background:${legendSwatchFill("US")}"></span>United States &mdash; NIH RePORTER (federal)</div>
      <div class="legend-row"><span class="swatch empty"></span>no ratio data yet</div>
      ${f ? "" : `<div class="legend-row legend-note">Funding data not loaded.</div>`}`;
    const canvas = document.getElementById("ramp");
    const ctx = canvas.getContext("2d");
    for (let x = 0; x < canvas.width; x++) {
      ctx.fillStyle = ramp(x / (canvas.width - 1));
      ctx.fillRect(x, 0, 1, canvas.height);
    }
    legend.hidden = false;
    return;
  }
  legend.innerHTML = `
    <div class="legend-title">Index, 0&ndash;100</div>
    <canvas id="ramp" width="180" height="10" aria-hidden="true"></canvas>
    <div class="ramp-ends"><span>0</span><span>100</span></div>
    <div class="legend-row"><span class="swatch hatch"></span>searched, nothing reliable found</div>
    <div class="legend-row"><span class="swatch empty"></span>not yet covered</div>`;
  const canvas = document.getElementById("ramp");
  const ctx = canvas.getContext("2d");
  for (let x = 0; x < canvas.width; x++) {
    ctx.fillStyle = ramp(x / (canvas.width - 1));
    ctx.fillRect(x, 0, 1, canvas.height);
  }
  legend.hidden = false;
}

/* ---------- panel: routing ---------- */

function displayName(iso) {
  return nameByIso.get(iso) || (MICRO[iso] && MICRO[iso].name) || iso;
}

function focusPanelHeading() {
  const heading = panelBody.querySelector(".panel-heading");
  if (heading) {
    heading.setAttribute("tabindex", "-1");
    heading.focus({ preventScroll: true });
  }
  panelBody.parentElement.scrollTop = 0;
}

function warningsHTML() {
  if (!loadWarnings.length) return "";
  return `<div class="load-warnings">${loadWarnings.map((w) => `<p>${esc(w)}</p>`).join("")}</div>`;
}

function renderPanel() {
  if (LAYER === "funding") renderFundingPanel();
  else renderPoliticsPanel();
}

/* ---------- panel: funding layer ---------- */

function renderFundingPanel() {
  const f = funding();
  if (!f) {
    panelBody.innerHTML = `<h2 class="panel-heading">Funding-gap data unavailable</h2>
      <p class="panel-sub">${esc(fundingError || "ratio/output could not be loaded.")}</p>`;
    return;
  }
  if (selection.layer === "funding" && selection.key && f.agg.regions[selection.key]) {
    renderFundingJurisdiction(selection.key);
  } else {
    renderFundingRanking();
  }
}

function fundingCaveatsHTML() {
  const f = funding();
  if (!f) return "";
  const items = [];
  if (SCENARIO === "adjudicated") {
    items.push(
      "Adjudicated scenario: every ambiguous record was re-labelled by deepseek-flash " +
        "with one machine-verified quote per record; model labels, not human ground truth."
    );
  }
  items.push(...(f.agg.method.caveats || []));
  items.push(
    "Regions are funding jurisdictions: SweCRIS funders (SE), the European Commission " +
      "via CORDIS (EU, shown for all EU members), NIH via RePORTER (US). Collection " +
      "nets and record counts differ per source, so compare shapes, not absolutes."
  );
  const escaped = items.map((c) => `<li>${esc(c)}</li>`).join("");
  const linked =
    `<li>Built from classifier+lexicon inputs ${esc(f.agg.method.inputs_hash || "?")} ` +
    `(repo state ${esc(f.agg.method.built_at_commit || "unknown")}). Full method and ` +
    `<a href="../ratio/">the funding-gap page</a>.</li>`;
  return `<ul class="caveats">${escaped}${linked}</ul>`;
}

function renderFundingRanking(focus = false) {
  const f = funding();
  const rows = REGION_ORDER
    .map((key) => ({ key, d: f.agg.regions[key] }))
    .filter((r) => r.d)
    .sort((a, b) => b.d.ratio - a.d.ratio);
  let html = `<h2 class="panel-heading">Funding-gap index</h2>
    <p class="panel-sub">The share of classified ageing-research money that targets
    slowing ageing rather than its consequences. Ambiguous grants count for neither
    side. ${SCENARIO === "adjudicated" ? "Adjudicated (AI) labels." : "Rules (v2) labels."}</p>`;
  rows.forEach((r, i) => {
    const idx = ratioIndex(r.d.ratio);
    html += `<button class="rank-row" data-jurisdiction="${esc(r.key)}">
      <span class="rank-num">${i + 1}</span>
      <span><span class="rank-name">${esc(JURISDICTIONS[r.key].name)}</span>
      <span class="rank-meta">${esc(JURISDICTIONS[r.key].source)} \u00b7 ${fmtEUR(r.d.numerator_eur)} of ${fmtEUR(r.d.denominator_eur)} \u00b7 ${r.d.records.toLocaleString("en-GB")} grants</span></span>
      <span class="rank-score">${idx}</span>
      <span class="rank-bar"><i style="width:${idx}%;background:${ramp(idx / 100)}"></i></span>
    </button>`;
  });
  if (SHOW_METHOD_NOTES) {
    html += `<p class="method-note">Index = 100 &times; slowing-ageing funding &frasl;
      classified funding, with ambiguous grants excluded from both sides. This is the
      same ratio as the <a href="../ratio/">funding-gap page</a>; the formula, data
      builds and limits are documented in <a href="../ratio/README.md">ratio/README.md</a>.</p>`;
    html += fundingCaveatsHTML();
  }
  panelBody.innerHTML = html;
  panelBody.querySelectorAll(".rank-row").forEach((row) =>
    row.addEventListener("click", () => {
      const key = row.dataset.jurisdiction;
      selection = { layer: "funding", key, focusIso: null };
      bumpGrantView(null);
      markSelection();
      zoomToJurisdiction(key === "EU" ? "EU" : key);
      renderPanel();
      if (!funding().labels && !funding().labelsError) ensureLabels();
    })
  );
  if (focus) focusPanelHeading();
}

function grantCard(r) {
  const safeUrl = /^https?:\/\//i.test(r.url || "") ? r.url : null;
  const title = safeUrl
    ? `<a href="${esc(safeUrl)}" target="_blank" rel="noopener noreferrer">${esc(r.title)}</a>`
    : esc(r.title);
  const kws = Object.values(r.matched_keywords || {}).flat();
  return `<article class="grant">
    <div class="grant-title">${title}</div>
    <div class="grant-meta"><span class="amt">${fmtEUR(r.amount_eur)}</span>
      \u00b7 ${esc(r.funder)} \u00b7 ${esc(r.year)} \u00b7 ${esc(r.source)}
      \u00b7 <span class="grant-label">${esc(CAT_NAME[r.label] || r.label)}</span></div>
    <p class="grant-why">${esc(r.reason)} ${kws.length ? `<span class="kw">[${esc(kws.join(", "))}]</span>` : ""}</p>
  </article>`;
}

function grantListHTML(region, labelName) {
  const f = funding();
  if (!f.labels) {
    if (f.labelsError) return `<p class="panel-sub">${esc(f.labelsError)}</p>`;
    return `<p class="panel-sub">Loading grant-level records&hellip;</p>`;
  }
  // By default show what the ratio counts: classified + ambiguous grants.
  // The off-topic not_relevant slice stays one click away in the category list.
  const view = grantView && grantView.region === region ? grantView : null;
  const cats = view ? view.cats : CATS.map(([key]) => key).filter((key) => key !== "not_relevant");
  const all = f.labels
    .filter((r) => r.region === region && cats.includes(r.label))
    .sort((a, b) => (b.amount_eur || 0) - (a.amount_eur || 0));
  if (!all.length) return `<p class="panel-sub">No grants in this slice.</p>`;
  const page = all.slice(0, grantShown + 25);
  let html = `<h3 class="grants-heading">${esc(labelName || "Grants")} \u00b7 ${all.length} matches, largest first</h3>`;
  html += page.map(grantCard).join("");
  if (page.length < all.length) {
    html += `<button class="more-btn" id="grants-more">Show ${Math.min(25, all.length - page.length)} more (${all.length - page.length} left)</button>`;
  }
  return html;
}

function renderFundingJurisdiction(key) {
  const f = funding();
  const d = f.agg.regions[key];
  const j = JURISDICTIONS[key];
  const idx = ratioIndex(d.ratio);
  let html = `<button class="back-btn" id="back">Back to the ranking</button>`;
  html += `<h2 class="panel-heading">${esc(j.name)}</h2>`;
  html += `<p class="panel-sub">${esc(j.source)} \u00b7 ${esc(j.blurb)}</p>`;
  html += `<div class="score-hero"><b style="color:${ramp(idx / 100)}">${idx}</b>
    <span class="of">funding-gap index of 100</span></div>`;
  html += `<p class="formula">= 100 &times; ${fmtEUR(d.numerator_eur)} slowing ageing
    &frasl; ${fmtEUR(d.denominator_eur)} classified (${pct(d.ratio)}).</p>`;
  html += `<p class="formula">${d.records.toLocaleString("en-GB")} grants classified
    \u00b7 ${pct(d.ambiguous_share)} ambiguous (${fmtEUR(d.eur.ambiguous || 0)}), excluded
    from both sides \u00b7 ${fmtEUR(d.eur.not_relevant || 0)} off-topic excluded.</p>`;

  const max = Math.max(...CATS.map(([cat]) => d.eur[cat] || 0), 0.001);
  html += `<div class="signals">`;
  for (const [cat, name] of CATS) {
    const eur = d.eur[cat] || 0;
    const n = d.counts[cat] || 0;
    const isNum = cat === "fundamental_aging" || cat === "intervention";
    html += `<button class="signal cat" data-cat="${esc(cat)}" title="Show the grants behind ${esc(name)}">
      <div class="signal-label"><b>${esc(name)}${isNum ? ' <span class="num-tag">counts toward the index</span>' : ""}</b>
        <span>${fmtEUR(eur)} \u00b7 ${n} grants</span></div>
      <div class="signal-bar"><i style="width:${(100 * eur) / max}%;background:${isNum ? ramp(idx / 100) : "#5d6880"}"></i></div>
    </button>`;
  }
  html += `</div>`;

  const funders = (f.agg.funders || [])
    .filter((x) => x.region === key && x.denominator_eur)
    .sort((a, b) => b.denominator_eur - a.denominator_eur)
    .slice(0, 8);
  if (funders.length) {
    html += `<h3 class="grants-heading">Top funders</h3><table class="funders">
      <thead><tr><th>Funder</th><th class="r">Index</th><th class="r">Slowing</th><th class="r">Grants</th></tr></thead><tbody>`;
    for (const x of funders) {
      html += `<tr><td>${esc(x.funder)}</td>
        <td class="r">${ratioIndex(x.ratio)}</td>
        <td class="r">${fmtEUR(x.numerator_eur)}</td>
        <td class="r">${x.records}</td></tr>`;
    }
    html += `</tbody></table>`;
  }

  html += `<div id="grants-slice">`;
  html += grantListHTML(
    key,
    grantView && grantView.region === key ? grantView.label : "Classified and ambiguous grants"
  );
  html += `</div>`;
  if (SHOW_METHOD_NOTES) html += fundingCaveatsHTML();

  panelBody.innerHTML = html;
  document.getElementById("back").addEventListener("click", () => {
    selection = { layer: "funding", key: null };
    bumpGrantView(null);
    markSelection();
    renderFundingRanking(true);
  });
  panelBody.querySelectorAll(".signal.cat").forEach((btn) =>
    btn.addEventListener("click", () => {
      const cat = btn.dataset.cat;
      bumpGrantView({ region: key, cats: [cat], label: CAT_NAME[cat] || cat });
      renderFundingJurisdiction(key);
    })
  );
  const more = document.getElementById("grants-more");
  if (more) {
    more.addEventListener("click", () => {
      grantShown += 25;
      renderFundingJurisdiction(key);
    });
  }
  focusPanelHeading();
}

/* ---------- panel: politics layer ---------- */

function renderPoliticsPanel() {
  if (selection.layer === "politics" && selection.key) renderPoliticsCountry(selection.key);
  else renderPoliticsRanking();
}

function renderPoliticsRanking(focus = false) {
  const list = [...countries.values()].sort((a, b) => (b.index ?? -1) - (a.index ?? -1));
  const covered = list.filter((c) => c.status === "scored");
  const quiet = list.filter((c) => c.status === "nothing");
  let html = `<h2 class="panel-heading">The politics index so far</h2>
    <p class="panel-sub">${covered.length} scored ${covered.length === 1 ? "country" : "countries"},
    ${quiet.length} searched with nothing reliable found. Click a country on the map
    or in the list for its score composition and cited findings.</p>`;
  html += warningsHTML();
  list.forEach((c, i) => {
    const name = displayName(c.iso);
    const meta =
      c.status === "scored"
        ? `${c.scored.length} findings, ${c.verified} verified, ${c.pending} awaiting review`
        : "searched, nothing reliable found";
    const score =
      c.status === "scored"
        ? `<span class="rank-score" style="color:${ramp(c.index / 100)}">${c.index}</span>`
        : `<span class="rank-score none">0</span>`;
    html += `<button class="rank-row" data-iso="${esc(c.iso)}">
      <span class="rank-num">${i + 1}</span>
      <span><span class="rank-name">${esc(name)}</span><span class="rank-meta">${esc(meta)}</span></span>
      ${score}
      <span class="rank-bar"><i style="width:${c.index ?? 0}%;background:${
        c.status === "scored" ? ramp(c.index / 100) : "transparent"
      }"></i></span>
    </button>`;
  });
  html += `<p class="method-note">Index v0 = 100 &times; S &frasl; (S + 4), where S sums
    weight &times; confidence &times; verification &times; recency over a country's findings.
    Weights and the gold-set calibration are still being tuned; the formula is documented in
    <a href="README.md">map/README.md</a>. All other countries are not yet covered.</p>`;
  panelBody.innerHTML = html;
  panelBody.querySelectorAll(".rank-row").forEach((row) =>
    row.addEventListener("click", () => {
      selection = { layer: "politics", key: row.dataset.iso };
      markSelection();
      zoomToCountry(row.dataset.iso);
      renderPoliticsCountry(row.dataset.iso);
    })
  );
  if (focus) focusPanelHeading();
}

function renderPoliticsCountry(iso) {
  const c = countries.get(iso);
  if (!c) return;
  const name = displayName(iso);
  let html = `<button class="back-btn" id="back">Back to the ranking</button>`;
  html += `<h2 class="panel-heading">${esc(name)}</h2>`;
  html += warningsHTML();

  if (c.status === "scored") {
    html += `<div class="score-hero"><b style="color:${ramp(c.index / 100)}">${c.index}</b>
      <span class="of">of 100</span></div>`;
    html += `<p class="formula">Index = 100 &times; S &frasl; (S + ${window.Scoring.HALFWAY}) with
      S&nbsp;=&nbsp;${c.S.toFixed(2)} points from ${c.scored.length} findings.
      ${c.verified} human-verified, ${c.pending} awaiting review${
      c.failed ? `, ${c.failed} failed review and excluded` : ""
    }.</p>`;

    const byClass = d3.rollup(c.scored, (v) => d3.sum(v, (s) => s.points), (s) => s.finding.classification);
    const maxPts = Math.max(...byClass.values(), 0.001);
    html += `<div class="signals">`;
    for (const [cls, pts] of [...byClass].sort((a, b) => b[1] - a[1])) {
      html += `<div class="signal">
        <div class="signal-label"><b>${esc(cls)}</b><span>${pts.toFixed(2)} pts</span></div>
        <div class="signal-bar"><i style="width:${(100 * pts) / maxPts}%;background:${ramp(c.index / 100)}"></i></div>
      </div>`;
    }
    html += `</div>`;

    html += `<h3 class="grants-heading">Findings, largest contribution first</h3>`;
    for (const s of [...c.scored].sort((a, b) => b.points - a.points)) {
      html += findingCard(s);
    }
  }

  for (const n of c.nothing) {
    html += `<div class="nothing-card"><b>Nothing reliable found${n.region ? ` for ${esc(n.region)}` : ""}.</b>
      ${esc(n.search_note)} <span>(checked ${esc(String(n.retrieved_at).slice(0, 10))})</span></div>`;
  }

  panelBody.innerHTML = html;
  document.getElementById("back").addEventListener("click", () => {
    selection = { layer: "politics", key: null };
    markSelection();
    renderPoliticsRanking(true);
  });
  focusPanelHeading();
}

function findingCard(s) {
  const f = s.finding;
  const verif =
    s.state === "verified"
      ? `<span class="f-verif ok">human-verified</span>`
      : s.state === "failed"
      ? `<span class="f-verif bad">failed review, excluded</span>`
      : `<span class="f-verif pending">awaiting human review</span>`;
  // Only http(s) sources become links; anything else (schema violations,
  // javascript:/data: schemes) renders as inert text.
  const safeUrl = /^https?:\/\//i.test(f.source_url || "") ? f.source_url : null;
  let host = "source";
  if (safeUrl) {
    try {
      host = new URL(safeUrl).hostname.replace(/^www\./, "");
    } catch {
      host = "source";
    }
  }
  const srcLine = safeUrl
    ? `<a href="${esc(safeUrl)}" target="_blank" rel="noopener noreferrer">${esc(host)}</a>`
    : `<span>${esc(f.source_url || "no source URL")}</span>`;
  return `<article class="finding${s.state === "failed" ? " excluded" : ""}">
    <div class="f-top">
      <span class="f-class">${esc(f.classification)}</span>
      <span>${esc(f.confidence)} confidence</span>
      ${verif}
    </div>
    <p class="f-claim">${esc(f.claim)}</p>
    <p class="f-src">${srcLine}, dated ${esc(f.source_date)}</p>
    <p class="f-points">${s.points.toFixed(2)} pts =
      ${s.weight.toFixed(2)} ${esc(f.classification)}
      &times; ${s.conf.toFixed(1)} ${esc(f.confidence)} confidence
      &times; ${s.verif.toFixed(1)} ${s.state === "verified" ? "verified" : s.state === "failed" ? "failed" : "awaiting review"}
      &times; ${s.recency.toFixed(2)} recency</p>
    ${f.source_note ? `<details><summary>How this was found</summary>${esc(f.source_note)}</details>` : ""}
  </article>`;
}

/* ---------- boot ---------- */

function showLoadError() {
  document.getElementById("load-error").hidden = false;
  panelBody.innerHTML = "";
}

async function boot() {
  document.querySelectorAll("#layer-switch button").forEach((b) =>
    b.addEventListener("click", () => setLayer(b.dataset.layer))
  );
  document.querySelectorAll("#scenario-switch button").forEach((b) =>
    b.addEventListener("click", () => setScenario(b.dataset.scenario))
  );

  const [geoRes] = await Promise.all([
    fetchJSON("vendor/world-110m.geojson"),
    loadPolitics().then((data) => {
      countries = data;
    }),
    loadFunding(SCENARIO).catch((e) => {
      fundingError = String(e && e.message ? e.message : e);
      return null;
    }),
  ]);
  if (geoRes.state !== "ok" || !geoRes.data || !geoRes.data.features) {
    showLoadError();
    return;
  }
  world = geoRes.data;
  nameByIso = new Map(world.features.map((f) => [f.properties.iso_a2, f.properties.name]));
  renderChrome();
  drawMap();
  renderPanel();
  // Deep link: /map/?region=SE|EU|US opens that jurisdiction's panel and
  // pulls the grant-level records in.
  const qsRegion = QS.get("region");
  if (LAYER === "funding" && qsRegion && funding() && funding().agg.regions[qsRegion]) {
    selection = { layer: "funding", key: qsRegion };
    grantView = null;
    markSelection();
    renderPanel();
    ensureLabels();
    zoomToJurisdiction(qsRegion);
  }
}

async function setLayer(layer) {
  if (!LAYERS.includes(layer) || layer === LAYER) return;
  LAYER = layer;
  selection = { layer: null, key: null };
  bumpGrantView(null);
  syncURL();
  renderChrome();
  drawMap();
  renderPanel();
}

async function setScenario(scenario) {
  if (!SCENARIOS.includes(scenario) || scenario === SCENARIO) return;
  SCENARIO = scenario;
  bumpGrantView(null);
  syncURL();
  try {
    await loadFunding(scenario);
    fundingError = "";
  } catch (e) {
    fundingError = String(e && e.message ? e.message : e);
  }
  selection = { layer: null, key: null };
  renderChrome();
  drawMap();
  renderPanel();
}

let resizeTimer = null;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (world) {
      drawMap();
      if (selection.layer === "politics" && selection.key) zoomToCountry(selection.key);
    }
  }, 150);
});

boot().catch((err) => {
  console.error("boot failed", err);
  showLoadError();
});
