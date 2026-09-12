"use strict";

/* Longevity Politics Index — reads eval/findings/*.json + eval/verdicts/*.verdicts.json
   and renders a scored world map. Methodology v0 is documented in map/README.md;
   the constants below ARE the methodology. */

/* ---------- index methodology v0 ---------- */

const CLASS_WEIGHT = {
  legislation: 1.0,
  funding: 0.9,
  policy: 0.8,
  strategy: 0.7,
  "political statement": 0.4,
};
const CONF_MULT = { high: 1.0, medium: 0.7, low: 0.4 };
const VERIF_MULT = { verified: 1.0, pending: 0.7, failed: 0.0 };
const HALFWAY = 4; // saturation constant: index = 100 * S / (S + HALFWAY)

const NOW = new Date();

function recencyMult(sourceDate) {
  // source_date is YYYY, YYYY-MM or YYYY-MM-DD; a bare year is read as mid-year.
  const d = new Date(sourceDate.length === 4 ? sourceDate + "-07-01" : sourceDate);
  const years = (NOW - d) / (365.25 * 24 * 3600 * 1000);
  if (!isFinite(years)) return 0.3;
  if (years <= 2) return 1.0;
  if (years <= 5) return 0.75;
  if (years <= 10) return 0.5;
  return 0.3;
}

function verifState(verdict) {
  if (!verdict || !verdict.reviewed) return "pending";
  return verdict.correct ? "verified" : "failed";
}

function scoreFinding(f, verdict) {
  const state = verifState(verdict);
  const parts = {
    weight: CLASS_WEIGHT[f.classification] ?? 0.4,
    conf: CONF_MULT[f.confidence] ?? 0.4,
    verif: VERIF_MULT[state],
    recency: recencyMult(f.source_date),
    state,
  };
  parts.points = parts.weight * parts.conf * parts.verif * parts.recency;
  return parts;
}

function scoreCountry(entry) {
  const findings = entry.records.filter((r) => r.type === "finding");
  const nothing = entry.records.filter((r) => r.type === "nothing_reliable_found");
  const scored = findings.map((f) => ({ finding: f, ...scoreFinding(f, entry.verdicts[f.id]) }));
  const S = scored.reduce((sum, s) => sum + s.points, 0);
  return {
    ...entry,
    scored,
    nothing,
    S,
    index: findings.length ? Math.round((100 * S) / (S + HALFWAY)) : null,
    status: findings.length ? "scored" : nothing.length ? "nothing" : "empty",
    verified: scored.filter((s) => s.state === "verified").length,
    failed: scored.filter((s) => s.state === "failed").length,
    pending: scored.filter((s) => s.state === "pending").length,
  };
}

/* ---------- data loading ---------- */

const FINDINGS_BASE = "../eval/findings/";
const VERDICTS_BASE = "../eval/verdicts/";
// Tried when the server offers no directory listing for eval/findings/.
const FALLBACK_FILES = ["sweden.json", "us.json", "singapore.json"];

// Countries whose findings may exist but that the 1:110m geometry omits;
// rendered as circle markers at [lon, lat].
const MICRO = {
  SG: { name: "Singapore", coords: [103.82, 1.352] },
  MT: { name: "Malta", coords: [14.42, 35.9] },
  HK: { name: "Hong Kong", coords: [114.17, 22.32] },
  MC: { name: "Monaco", coords: [7.42, 43.74] },
  AD: { name: "Andorra", coords: [1.52, 42.51] },
  SM: { name: "San Marino", coords: [12.46, 43.94] },
  LI: { name: "Liechtenstein", coords: [9.55, 47.16] },
  BH: { name: "Bahrain", coords: [50.56, 26.07] },
  MV: { name: "Maldives", coords: [73.51, 4.18] },
};

async function fetchJSON(url) {
  try {
    const res = await fetch(url);
    return res.ok ? await res.json() : null;
  } catch {
    return null;
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
      if (names.length) return [...new Set(names)];
    }
  } catch {
    /* fall through to the fixed candidate list */
  }
  return FALLBACK_FILES;
}

async function loadCountries() {
  const files = await listFindingsFiles();
  const byCountry = new Map();
  await Promise.all(
    files.map(async (file) => {
      const records = await fetchJSON(FINDINGS_BASE + file);
      if (!Array.isArray(records)) return;
      const base = file.replace(/\.json$/, "");
      const verdicts = (await fetchJSON(`${VERDICTS_BASE}${base}.verdicts.json`)) || {};
      for (const rec of records) {
        if (!rec || typeof rec.country !== "string") continue;
        const iso = rec.country.toUpperCase();
        if (!byCountry.has(iso)) byCountry.set(iso, { iso, records: [], verdicts: {} });
        byCountry.get(iso).records.push(rec);
      }
      for (const [id, v] of Object.entries(verdicts)) {
        const iso = id.slice(0, 2).toUpperCase();
        if (byCountry.has(iso)) byCountry.get(iso).verdicts[id] = v;
      }
    })
  );
  return new Map([...byCountry].map(([iso, entry]) => [iso, scoreCountry(entry)]));
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

  paths
    .filter((d) => countries.has(d.properties.iso_a2))
    .classed("scored", true)
    .attr("tabindex", 0)
    .attr("role", "button")
    .attr("aria-label", (d) => ariaFor(d.properties.iso_a2, d.properties.name))
    .on("click", (event, d) => {
      event.stopPropagation();
      selectCountry(d.properties.iso_a2);
    })
    .on("keydown", (event, d) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectCountry(d.properties.iso_a2);
      }
    });

  // circle markers for scored countries the 110m geometry omits
  const missing = [...countries.keys()].filter(
    (iso) => !world.features.some((f) => f.properties.iso_a2 === iso) && MICRO[iso]
  );
  gRoot
    .append("g")
    .selectAll("circle")
    .data(missing)
    .join("circle")
    .attr("class", "marker")
    .attr("tabindex", 0)
    .attr("role", "button")
    .attr("aria-label", (iso) => ariaFor(iso, MICRO[iso].name))
    .attr("cx", (iso) => projection(MICRO[iso].coords)[0])
    .attr("cy", (iso) => projection(MICRO[iso].coords)[1])
    .attr("r", 6)
    .attr("fill", (iso) => countryFill(countries.get(iso)))
    .style("vector-effect", "non-scaling-stroke")
    .on("mousemove", (event, iso) => showTooltip(event, iso, MICRO[iso].name))
    .on("mouseleave", hideTooltip)
    .on("click", (event, iso) => {
      event.stopPropagation();
      selectCountry(iso);
    })
    .on("keydown", (event, iso) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectCountry(iso);
      }
    });

  markSelection();

  zoomBehavior = d3
    .zoom()
    .scaleExtent([1, 14])
    .on("zoom", (event) => {
      gRoot.attr("transform", event.transform);
      gRoot.selectAll(".marker").attr("r", 6 / Math.sqrt(event.transform.k));
    });
  svg.call(zoomBehavior);
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

function showTooltip(event, iso, name) {
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
}

/* ---------- panel ---------- */

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

function displayName(iso) {
  return nameByIso.get(iso) || (MICRO[iso] && MICRO[iso].name) || iso;
}

function selectCountry(iso) {
  selectedIso = iso;
  markSelection();
  renderCountry(iso);
  zoomToCountry(iso);
}

function renderRanking() {
  const list = [...countries.values()].sort((a, b) => (b.index ?? -1) - (a.index ?? -1));
  const covered = list.filter((c) => c.status === "scored");
  const quiet = list.filter((c) => c.status === "nothing");
  let html = `<h2 class="panel-heading">The index so far</h2>
    <p class="panel-sub">${covered.length} scored ${covered.length === 1 ? "country" : "countries"},
    ${quiet.length} searched with nothing reliable found. Click a country on the map
    or in the list for its score composition and cited findings.</p>`;
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
}

function renderCountry(iso) {
  const c = countries.get(iso);
  if (!c) return;
  const name = displayName(iso);
  let html = `<button class="back-btn" id="back">Back to the ranking</button>`;
  html += `<h2 class="panel-heading">${esc(name)}</h2>`;

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
      ${esc(n.search_note)} <span>(checked ${esc(n.retrieved_at.slice(0, 10))})</span></div>`;
  }

  panelBody.innerHTML = html;
  document.getElementById("back").addEventListener("click", () => {
    selectedIso = null;
    markSelection();
    renderRanking();
  });
  panelBody.parentElement.scrollTop = 0;
}

function findingCard(s) {
  const f = s.finding;
  const verif =
    s.state === "verified"
      ? `<span class="f-verif ok">human-verified</span>`
      : s.state === "failed"
      ? `<span class="f-verif bad">failed review, excluded</span>`
      : `<span class="f-verif pending">awaiting human review</span>`;
  let host = "";
  try {
    host = new URL(f.source_url).hostname.replace(/^www\./, "");
  } catch {
    host = "source";
  }
  return `<article class="finding${s.state === "failed" ? " excluded" : ""}">
    <div class="f-top">
      <span class="f-class">${esc(f.classification)}</span>
      <span>${esc(f.confidence)} confidence</span>
      ${verif}
    </div>
    <p class="f-claim">${esc(f.claim)}</p>
    <p class="f-src"><a href="${esc(f.source_url)}" target="_blank" rel="noopener noreferrer">${esc(host)}</a>,
      dated ${esc(f.source_date)}</p>
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

async function boot() {
  const [geo, data] = await Promise.all([fetchJSON("vendor/world-110m.geojson"), loadCountries()]);
  if (!geo || !geo.features) {
    document.getElementById("load-error").hidden = false;
    panelBody.innerHTML = "";
    return;
  }
  world = geo;
  nameByIso = new Map(geo.features.map((f) => [f.properties.iso_a2, f.properties.name]));
  countries = data;
  drawMap();
  renderChrome();
  renderRanking();
  if (!countries.size) {
    panelBody.innerHTML = `<h2 class="panel-heading">No findings yet</h2>
      <p class="panel-sub">No files in <code>eval/findings/</code> could be loaded.
      Serve the repository root (<code>python3 -m http.server 8010</code>) and open
      <code>/map/</code> so the map can reach <code>../eval/findings/</code>.</p>`;
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

boot();
