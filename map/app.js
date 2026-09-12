"use strict";

/* Longevity Politics Index — reads eval/findings/*.json + eval/verdicts/*.verdicts.json
   and renders a scored world map. The scoring methodology lives in map/scoring.js
   (regression-tested by `node map/test_scoring.js`) and is documented in map/README.md. */

const { HALFWAY, scoreCountry } = window.Scoring;

const NOW = new Date();

/* ---------- data loading ---------- */

const FINDINGS_BASE = "../eval/findings/";
const VERDICTS_BASE = "../eval/verdicts/";
// Tried when the server offers no directory listing for eval/findings/.
const FALLBACK_FILES = ["sweden.json", "us.json", "singapore.json"];

// Countries whose findings exist or are planned but that the 1:110m geometry
// omits; rendered as circle markers at [lon, lat].
const MICRO = {
  SG: { name: "Singapore", coords: [103.82, 1.352] },
  MT: { name: "Malta", coords: [14.42, 35.9] },
};

// Human-visible data-loading problems, surfaced in the ranking panel. A missing
// verdicts file is normal (no reviews yet); a fetch/parse failure is not.
const loadWarnings = [];

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

async function loadCountries() {
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
  const scored = new Map([...byCountry].map(([iso, entry]) => [iso, scoreCountry(entry, NOW)]));
  for (const c of scored.values()) {
    for (const s of c.scored) {
      if (s.unknownClassification)
        console.warn(`Finding ${s.finding.id}: unknown classification "${s.finding.classification}" scored at 0.4`);
      if (s.unknownConfidence)
        console.warn(`Finding ${s.finding.id}: unknown confidence "${s.finding.confidence}" scored at 0.4`);
    }
  }
  return scored;
}

/* ---------- colors ---------- */

const ramp = (t) => d3.interpolateViridis(0.16 + 0.8 * t);
const EMPTY_FILL = "#1a2231";

function countryFill(c) {
  if (!c) return EMPTY_FILL;
  if (c.status === "scored") return ramp(c.index / 100);
  if (c.status === "nothing") return "url(#hatch)";
  return EMPTY_FILL;
}

/* ---------- map ---------- */

const svg = d3.select("#map");
const stage = document.getElementById("stage");
const tooltip = document.getElementById("tooltip");
const panelBody = document.getElementById("panel-body");

let countries = new Map(); // iso -> scored entry
let world = null;
let nameByIso = new Map();
let selectedIso = null;

const projection = d3.geoNaturalEarth1();
const geoPath = d3.geoPath(projection);
const gRoot = svg.append("g");
let zoomBehavior = null;

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

function bindCountryInteractions(selection, isoOf, nameOf) {
  selection
    .attr("tabindex", 0)
    .attr("role", "button")
    .attr("aria-label", (d) => ariaFor(isoOf(d), nameOf(d)))
    .on("mousemove", (event, d) => showTooltip(event, isoOf(d), nameOf(d)))
    .on("mouseleave", hideTooltip)
    .on("click", (event, d) => {
      event.stopPropagation();
      selectCountry(isoOf(d));
    })
    .on("keydown", (event, d) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectCountry(isoOf(d));
      }
    });
}

function drawMap() {
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
    .on("mousemove", (event, d) => showTooltip(event, d.properties.iso_a2, d.properties.name))
    .on("mouseleave", hideTooltip);

  // reveal: flat ground first, score colors on the next frame (CSS-transitioned)
  requestAnimationFrame(() =>
    requestAnimationFrame(() => paths.attr("fill", (d) => countryFill(countries.get(d.properties.iso_a2))))
  );

  const scoredPaths = paths.filter((d) => countries.has(d.properties.iso_a2)).classed("scored", true);
  bindCountryInteractions(scoredPaths, (d) => d.properties.iso_a2, (d) => d.properties.name);

  // circle markers for scored countries the 110m geometry omits
  const missing = [...countries.keys()].filter(
    (iso) => !nameByIso.has(iso) && MICRO[iso]
  );
  const markers = gRoot
    .append("g")
    .selectAll("circle")
    .data(missing)
    .join("circle")
    .attr("class", "marker")
    .attr("cx", (iso) => projection(MICRO[iso].coords)[0])
    .attr("cy", (iso) => projection(MICRO[iso].coords)[1])
    .attr("r", 6)
    .attr("fill", (iso) => countryFill(countries.get(iso)))
    .style("vector-effect", "non-scaling-stroke");
  bindCountryInteractions(markers, (iso) => iso, (iso) => MICRO[iso].name);

  markSelection();

  zoomBehavior = d3
    .zoom()
    .scaleExtent([1, 14])
    .on("zoom", (event) => {
      gRoot.attr("transform", event.transform);
      gRoot.selectAll(".marker").attr("r", 6 / Math.sqrt(event.transform.k));
    });
  svg.call(zoomBehavior);
  // Sync the zoom state to the freshly fitted projection; without this a
  // resize while zoomed leaves a stale transform on gRoot.
  svg.call(zoomBehavior.transform, d3.zoomIdentity);
  svg.on("click", () => {
    selectedIso = null;
    markSelection();
    renderRanking();
  });
}

function markSelection() {
  gRoot.selectAll(".country").classed("selected", (d) => d.properties.iso_a2 === selectedIso);
  gRoot.selectAll(".marker").classed("selected", (iso) => iso === selectedIso);
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

/* ---------- tooltip ---------- */

function ariaFor(iso, fallbackName) {
  const c = countries.get(iso);
  const name = nameByIso.get(iso) || fallbackName || iso;
  if (!c) return `${name}: not yet covered`;
  if (c.status === "scored") return `${name}: index ${c.index} from ${c.scored.length} findings`;
  return `${name}: searched, nothing reliable found`;
}

let tooltipIso = null;

function showTooltip(event, iso, name) {
  if (tooltip.hidden || tooltipIso !== iso) {
    tooltipIso = iso;
    const c = countries.get(iso);
    let html = `<div class="tt-name">${esc(name || iso)}</div>`;
    if (!c) {
      html += `<div class="tt-line">Not yet covered by the research agent.</div>`;
    } else if (c.status === "scored") {
      html += `<div class="tt-line"><span class="tt-score">Index ${c.index}</span> from ${c.scored.length} finding${c.scored.length === 1 ? "" : "s"}</div>`;
      html += `<div class="tt-line">${c.verified} human-verified, ${c.pending} awaiting review${c.failed ? `, ${c.failed} failed review` : ""}</div>`;
      html += `<div class="tt-line">Click for the score breakdown.</div>`;
    } else {
      html += `<div class="tt-line">Searched: nothing reliable found. Click for the search notes.</div>`;
    }
    tooltip.innerHTML = html;
    tooltip.hidden = false;
  }
  const pad = 14;
  const rect = tooltip.getBoundingClientRect();
  let left = event.clientX + pad;
  let top = event.clientY + pad;
  if (left + rect.width > window.innerWidth - 8) left = event.clientX - rect.width - pad;
  if (top + rect.height > window.innerHeight - 8) top = event.clientY - rect.height - pad;
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function hideTooltip() {
  tooltip.hidden = true;
  tooltipIso = null;
}

/* ---------- panel ---------- */

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

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

function selectCountry(iso) {
  selectedIso = iso;
  markSelection();
  renderCountry(iso);
  zoomToCountry(iso);
}

function renderRanking(focus = false) {
  const list = [...countries.values()].sort((a, b) => (b.index ?? -1) - (a.index ?? -1));
  const covered = list.filter((c) => c.status === "scored");
  const quiet = list.filter((c) => c.status === "nothing");
  let html = `<h2 class="panel-heading">The index so far</h2>
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
  html += `<p class="method-note">Index v0 = 100 &times; S &frasl; (S + ${HALFWAY}), where S sums
    weight &times; confidence &times; verification &times; recency over a country's findings.
    Weights and the gold-set calibration are still being tuned; the formula is documented in
    <a href="README.md">map/README.md</a>. All other countries are not yet covered.</p>`;
  panelBody.innerHTML = html;
  panelBody.querySelectorAll(".rank-row").forEach((row) =>
    row.addEventListener("click", () => selectCountry(row.dataset.iso))
  );
  if (focus) focusPanelHeading();
}

function renderCountry(iso) {
  const c = countries.get(iso);
  if (!c) return;
  const name = displayName(iso);
  let html = `<button class="back-btn" id="back">Back to the ranking</button>`;
  html += `<h2 class="panel-heading">${esc(name)}</h2>`;
  html += warningsHTML();

  if (c.status === "scored") {
    html += `<div class="score-hero"><b style="color:${ramp(c.index / 100)}">${c.index}</b>
      <span class="of">of 100</span></div>`;
    html += `<p class="formula">Index = 100 &times; S &frasl; (S + ${HALFWAY}) with
      S&nbsp;=&nbsp;${c.S.toFixed(2)} points from ${c.scored.length} findings.
      ${c.verified} human-verified, ${c.pending} awaiting review${
      c.failed ? `, ${c.failed} failed review and excluded` : ""
    }.</p>`;

    // points contributed per classification, largest first
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

    html += `<h3 class="findings-heading">Findings, largest contribution first</h3>`;
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
    selectedIso = null;
    markSelection();
    renderRanking(true);
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

/* ---------- header + legend ---------- */

function renderChrome() {
  const scored = [...countries.values()].filter((c) => c.status === "scored");
  document.getElementById("c-countries").textContent = scored.length;
  document.getElementById("c-findings").textContent = d3.sum(scored, (c) => c.scored.length);
  document.getElementById("c-verified").textContent = d3.sum(scored, (c) => c.verified);
  document.getElementById("counters").hidden = false;

  const canvas = document.getElementById("ramp");
  const ctx = canvas.getContext("2d");
  for (let x = 0; x < canvas.width; x++) {
    ctx.fillStyle = ramp(x / (canvas.width - 1));
    ctx.fillRect(x, 0, 1, canvas.height);
  }
  document.getElementById("legend").hidden = false;
}

/* ---------- boot ---------- */

function showLoadError() {
  document.getElementById("load-error").hidden = false;
  panelBody.innerHTML = "";
}

async function boot() {
  const [geoRes, data] = await Promise.all([fetchJSON("vendor/world-110m.geojson"), loadCountries()]);
  if (geoRes.state !== "ok" || !geoRes.data || !geoRes.data.features) {
    showLoadError();
    return;
  }
  world = geoRes.data;
  nameByIso = new Map(world.features.map((f) => [f.properties.iso_a2, f.properties.name]));
  countries = data;
  drawMap();
  renderChrome();
  renderRanking();
  if (!countries.size) {
    panelBody.innerHTML = `<h2 class="panel-heading">No findings yet</h2>
      <p class="panel-sub">No files in <code>eval/findings/</code> could be loaded.
      Serve the repository root (<code>python3 -m http.server 8010</code>) and open
      <code>/map/</code> so the map can reach <code>../eval/findings/</code>.</p>` + warningsHTML();
  }
}

let resizeTimer = null;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (world) {
      drawMap();
      if (selectedIso) zoomToCountry(selectedIso);
    }
  }, 150);
});

boot().catch((err) => {
  console.error("boot failed", err);
  showLoadError();
});
