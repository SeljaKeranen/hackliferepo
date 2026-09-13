"use strict";

/* Index methodology v0 — the single source of truth for the score.
   DOM-free on purpose: loaded by the browser page (as window.Scoring) and by
   the Node regression test (node map/test_scoring.js). The formula is
   documented in map/README.md; these constants ARE the methodology.

   Wrapped in an IIFE because classic scripts share one global lexical scope:
   top-level consts here would collide with declarations in app.js. */

(function () {

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

function recencyMult(sourceDate, now) {
  // source_date is YYYY, YYYY-MM or YYYY-MM-DD; a bare year is read as mid-year.
  if (typeof sourceDate !== "string" || !sourceDate) return 0.3;
  const d = new Date(sourceDate.length === 4 ? sourceDate + "-07-01" : sourceDate);
  const years = (now - d) / (365.25 * 24 * 3600 * 1000);
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

function scoreFinding(f, verdict, now) {
  const state = verifState(verdict);
  const parts = {
    weight: CLASS_WEIGHT[f.classification] ?? 0.4,
    conf: CONF_MULT[f.confidence] ?? 0.4,
    verif: VERIF_MULT[state],
    recency: recencyMult(f.source_date, now),
    state,
    unknownClassification: !(f.classification in CLASS_WEIGHT),
    unknownConfidence: !(f.confidence in CONF_MULT),
  };
  parts.points = parts.weight * parts.conf * parts.verif * parts.recency;
  return parts;
}

function scoreCountry(entry, now) {
  const findings = entry.records.filter((r) => r.type === "finding");
  const nothing = entry.records.filter((r) => r.type === "nothing_reliable_found");
  const scored = findings.map((f) => ({ finding: f, ...scoreFinding(f, entry.verdicts[f.id], now) }));
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

/* ---------- Funding-gap layer ---------- */

// The 27 EU member states. Sweden is a member but has its own national
// SweCRIS corpus, so the funding-gap layer shows SE's own ratio rather than
// the European Commission's; the other 26 carry the EU colour.
const EU27 = [
  "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
  "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
  "SI", "ES", "SE",
];

const JURISDICTIONS = {
  SE: { name: "Sweden", source: "SweCRIS", blurb: "Swedish national funders, SweCRIS" },
  EU: { name: "European Commission", source: "CORDIS",
        blurb: "European Commission grants, CORDIS \u2014 shown for all 26 other EU members" },
  US: { name: "United States", source: "NIH RePORTER", blurb: "US federal NIH grants, RePORTER" },
};

// Which funding jurisdiction a map feature draws its number from. Sweden and
// the US have their own national corpus; every other EU member state is
// coloured with the European Commission's ratio, which is the only EU-wide
// number the census carries. Everything else has no ratio data yet.
function jurisdictionFor(iso) {
  if (iso === "SE") return "SE";
  if (iso === "US") return "US";
  if (EU27.includes(iso)) return "EU";
  return null;
}

// The headline 0–100 index is the funding-gap ratio itself: the share of
// classified ageing-research money that targets slowing ageing, ambiguous
// grants excluded from both sides. Same number as ratio/index.html.
function ratioIndex(ratio) {
  if (typeof ratio !== "number" || !isFinite(ratio)) return null;
  return Math.round(100 * ratio);
}

const Scoring = {
  CLASS_WEIGHT,
  CONF_MULT,
  VERIF_MULT,
  HALFWAY,
  EU27,
  JURISDICTIONS,
  recencyMult,
  verifState,
  scoreFinding,
  scoreCountry,
  jurisdictionFor,
  ratioIndex,
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = Scoring;
} else {
  window.Scoring = Scoring;
}

})();
