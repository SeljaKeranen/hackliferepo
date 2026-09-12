import { useEffect, useMemo, useRef, useState } from "react";
import type {
  Country,
  Category,
  Grant,
  Release,
  Report,
} from "./funding-types";
import { downloadFundingCard } from "./funding-share";
const countries: Country[] = ["SE", "US"];
const slugs: Record<Country, string> = { SE: "sweden", US: "united-states" };
const pct = (v: number | null | undefined) =>
  v == null ? "—" : `${(v * 100).toFixed(1)}%`;
const num = (v: number) => v.toLocaleString("en");
const money = (v: number | null, c: string, compact = false) =>
  v === null
    ? "Amount unavailable"
    : new Intl.NumberFormat("en", {
        style: "currency",
        currency: c,
        maximumFractionDigits: compact ? 1 : 2,
        notation: compact ? "compact" : "standard",
      }).format(v / 100);
const date = (s: string | null) => (s ? s.slice(0, 10) : "Not supplied");
const descriptions: Record<Category, string> = {
  fundamental_aging: "Research into the mechanisms and biology of ageing.",
  intervention:
    "Research that explicitly targets ageing biology, senescence, lifespan or healthspan.",
  age_related_disease:
    "Research focused on an age-related disease without an established ageing-biology objective.",
  care_research: "Research into care and support for older people and carers.",
  other_aging_research:
    "Social, behavioural, demographic and other nonbiological ageing research.",
  outside_scope:
    "Awards whose research objectives fall outside the defined ageing scope.",
  unresolved:
    "Awards whose ageing relevance or main objective needs further review.",
};
const colors: Record<Category, string> = {
  fundamental_aging: "#245c44",
  intervention: "#8bab61",
  age_related_disease: "#cab887",
  care_research: "#c8d4ba",
  other_aging_research: "#e2d7c0",
  outside_scope: "#e4e6df",
  unresolved: "#ece9df",
};
function Flag({ country }: { country: Country }) {
  return country === "SE" ? (
    <svg className="flag" viewBox="0 0 30 20" aria-label="Sweden">
      <rect width="30" height="20" fill="#386793" />
      <path d="M0 10h30M10 0v20" stroke="#efd274" strokeWidth="4" />
    </svg>
  ) : (
    <svg className="flag" viewBox="0 0 30 20" aria-label="United States">
      <rect width="30" height="20" fill="#f3eae1" />
      {[0, 4, 8, 12, 16].map((y) => (
        <rect key={y} y={y} width="30" height="2" fill="#bd6b64" />
      ))}
      <rect width="13" height="10" fill="#45647c" />
      <path d="M3 3h7M3 6h7" stroke="white" strokeDasharray="1 2" />
    </svg>
  );
}
function Arrow() {
  return <span aria-hidden="true">↗</span>;
}
function Grid({ report }: { report: Report }) {
  const s = report.summary;
  const biology = s?.denominator_minor
    ? Math.round(
        (s.category_amount_minor.fundamental_aging / s.denominator_minor) * 100,
      )
    : 0;
  const intervention = s?.ratio ? Math.round(s.ratio * 100) - biology : 0;
  return (
    <div
      className={`money-grid ${report.publication_ready ? "" : "pending-grid"}`}
      role="img"
      aria-label={
        report.publication_ready
          ? `${pct(s?.ratio)} of classified ageing research award funding targets biology or ageing interventions`
          : "The funding grid is awaiting human review; no share is displayed"
      }
    >
      {Array.from({ length: 100 }, (_, i) => (
        <i
          key={i}
          style={
            report.publication_ready
              ? {
                  background:
                    i < biology
                      ? colors.fundamental_aging
                      : i < biology + intervention
                        ? colors.intervention
                        : "#e7dfcd",
                }
              : undefined
          }
        />
      ))}
    </div>
  );
}
function Gate({
  release,
  compact = false,
}: {
  release: Release;
  compact?: boolean;
}) {
  const r = release.review.overall;
  return (
    <section
      className={`verification ${compact ? "compact" : ""}`}
      aria-label="Human verification"
    >
      <div>
        <span className="eyebrow">EVIDENCE BEFORE A HEADLINE</span>
        <h2>
          {r.passed ? "The benchmark passed." : "90% is the requirement."}
        </h2>
        <p>
          All 60 sampled awards need human review. At least 90% must pass
          overall and in each country.
        </p>
      </div>
      <div className="verification-score">
        <strong>
          {r.reviewed}
          <span> / 60</span>
        </strong>
        <div
          className="progress"
          role="progressbar"
          aria-label="Human benchmark review progress"
          aria-valuemin={0}
          aria-valuemax={60}
          aria-valuenow={r.reviewed}
        >
          <i style={{ width: `${(r.reviewed / 60) * 100}%` }} />
        </div>
        <p>
          {r.accuracy === null
            ? "Accuracy not yet measured"
            : `${pct(r.accuracy)} correct among reviewed records`}
        </p>
        <small>
          Publication also requires ten large-award checks per country and
          approval of each report.
        </small>
      </div>
    </section>
  );
}
function PortfolioCard({ report }: { report: Report }) {
  return (
    <a className="portfolio-card" href={`/country/${slugs[report.country]}`}>
      <div className="card-top">
        <Flag country={report.country} />
        <span>{report.period}</span>
        <Arrow />
      </div>
      <h3>{report.name}</h3>
      <p className="portfolio-name">{report.label}</p>
      <div className="card-visual">
        <Grid report={report} />
        <div>
          <span
            className={`status-pill ${report.publication_ready ? "ready" : ""}`}
          >
            {report.publication_ready ? "Reviewed estimate" : "Review pending"}
          </span>
          <strong className="ratio">
            {report.publication_ready ? pct(report.summary?.ratio) : "—"}
          </strong>
          <p>
            {report.publication_ready
              ? "of classified ageing research funding targets biology or ageing interventions"
              : "The estimate appears after human verification."}
          </p>
        </div>
      </div>
      <div className="card-bottom">
        <span>{num(report.record_count)} award records</span>
        <span>Explore portfolio →</span>
      </div>
    </a>
  );
}
function Home({ release }: { release: Release }) {
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">
            <i className="live-dot" /> THE AGEING RESEARCH FUNDING REPORT
          </span>
          <h1>
            Where does ageing
            <br />
            research money <em>go?</em>
          </h1>
          <p>
            Follow public research funding from the biology of ageing to the
            diseases and care needs that come with it.
          </p>
          <div className="hero-actions">
            <a className="button primary" href="#portfolios">
              Explore the portfolios <span>↓</span>
            </a>
            <a className="text-link" href="/method">
              How we count <Arrow />
            </a>
          </div>
          <div className="hero-note">
            2024 award records · Sweden & the United States
            <br />
            Named government portfolios. Every award links to its source.
          </div>
        </div>
        <div
          className="hero-diagram"
          aria-label="The question: ageing biology and interventions as a share of ageing research funding"
        >
          <div className="diagram-label">ONE QUESTION. A TRACEABLE RATIO.</div>
          <div className="diagram-biology">
            <span className="diagram-icon">✳</span>
            <div>
              <small>THE NUMERATOR</small>
              <h3>
                Ageing biology
                <br />+ ageing interventions
              </h3>
            </div>
          </div>
          <div className="fraction-rule" />
          <div className="diagram-denominator">
            <span className="diagram-icon circles">◉</span>
            <div>
              <small>THE DENOMINATOR</small>
              <h3>
                All classified
                <br />
                ageing research
              </h3>
            </div>
          </div>
          <p>
            Calculated from award amounts.
            <br />
            Biology and interventions remain visible separately.
          </p>
          <span className="diagram-foot">
            METHOD OPEN · HUMAN REVIEW PENDING
          </span>
        </div>
      </section>
      <section id="portfolios" className="portfolio-section">
        <div className="section-heading">
          <div>
            <span className="eyebrow">START WITH A PORTFOLIO</span>
            <h2>Two windows into public funding.</h2>
          </div>
          <p>
            Different funders and award periods.
            <br />
            Read each report on its own terms.
          </p>
        </div>
        <div className="portfolio-grid">
          {countries.map((c) => (
            <PortfolioCard key={c} report={release.reports[c]} />
          ))}
        </div>
        <p className="scope-note">
          {release.scope_note} Swedish amounts can cover several years; NIH
          amounts are recorded for a US fiscal year.
        </p>
      </section>
      <Gate release={release} />
      <section className="source-teaser">
        <div>
          <span className="eyebrow">FOLLOW THE MONEY TO THE SOURCE</span>
          <h2>Every row has a way back.</h2>
          <p>
            Find the award, the government funder, the amount and the date. Open
            the original record and judge the method yourself.
          </p>
          <a className="button outline" href="/sources">
            Browse {num(release.source_count)} source records <Arrow />
          </a>
        </div>
        <div className="source-stack">
          <div>
            <b>NIH RePORTER</b>
            <span>National Institute on Aging</span>
            <span className="source-count">
              {num(release.reports.US.record_count)} records
            </span>
          </div>
          <div>
            <b>Swecris</b>
            <span>Swedish Research Council + Forte</span>
            <span className="source-count">
              {num(release.reports.SE.record_count)} records
            </span>
          </div>
          <p>
            Snapshot retrieved {date(release.source_checked_at)}
            <br />
            Amounts and source dates are preserved in the ledger.
          </p>
        </div>
      </section>
      <section className="demo-strip">
        <div>
          <span className="eyebrow">DEMO DAY</span>
          <h3>The report, in three slides.</h3>
          <p>
            Editable slides, a PDF and a recorded walkthrough of this release.
          </p>
        </div>
        <a href="/downloads/longview-three-slides.pdf">
          Slides PDF <Arrow />
        </a>
        <a href="/downloads/longview-three-slides.pptx">
          Editable deck <Arrow />
        </a>
        <a href="/downloads/longview-demo.webm">
          Watch demo <Arrow />
        </a>
        <a href="/downloads/longview-offline.zip">
          Offline copy <Arrow />
        </a>
      </section>
    </>
  );
}
function CountryPage({
  release,
  country,
}: {
  release: Release;
  country: Country;
}) {
  const r = release.reports[country],
    s = r.summary;
  const [copied, setCopied] = useState(false);
  const frozen = `/reports/${release.release_id}/${country.toLowerCase()}/`;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(
        new URL(frozen, location.origin).href,
      );
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  const share = () =>
    downloadFundingCard(
      r,
      new URL(frozen, location.origin).href,
      release.release_id,
    );
  return (
    <>
      <div className="breadcrumb">
        <a href="/">Portfolios</a>
        <span>/</span>
        {r.name}
      </div>
      <section className="country-heading">
        <div>
          <Flag country={country} />
          <span className="eyebrow">{r.period.toUpperCase()}</span>
          <h1>{r.name}</h1>
          <p>{r.label}</p>
        </div>
        <span className={`status-pill ${r.publication_ready ? "ready" : ""}`}>
          {r.publication_ready ? "Reviewed estimate" : "Human review pending"}
        </span>
      </section>
      <section className="report-panel">
        <div className="report-main">
          <span className="eyebrow">BIOLOGY + AGEING INTERVENTIONS</span>
          <strong className="report-ratio">
            {r.publication_ready ? pct(s?.ratio) : "Not yet published"}
          </strong>
          <p>
            of classified ageing-related research funding
            <br />
            in this government portfolio.
          </p>
          <Grid report={r} />
          <div className="legend">
            <span>
              <i style={{ background: colors.fundamental_aging }} />
              Ageing biology
            </span>
            <span>
              <i style={{ background: colors.intervention }} />
              Ageing interventions
            </span>
            <span>
              <i style={{ background: "#e7dfcd" }} />
              Other ageing research
            </span>
          </div>
          {!r.publication_ready && (
            <p className="muted">
              The grid remains blank until the review gate passes.
            </p>
          )}
        </div>
        <div className="report-aside">
          <h2>Read this number with its method.</h2>
          <p>{r.basis}</p>
          <div className="key-value">
            <span>Coverage</span>
            <strong>{num(r.record_count)} award records</strong>
          </div>
          <div className="key-value">
            <span>Human benchmark</span>
            <strong>{r.review.reviewed} / 30 reviewed</strong>
          </div>
          <div className="key-value">
            <span>Large-award checks</span>
            <strong>{r.review.top_awards_checked} / 10 passed</strong>
          </div>
          <div className="key-value">
            <span>Report approval</span>
            <strong>{r.review.report_approved ? "Approved" : "Pending"}</strong>
          </div>
          <div className="key-value">
            <span>Missing amounts</span>
            <strong>{r.missing_amount_records}</strong>
          </div>
          <div className="key-value">
            <span>True zero amounts</span>
            <strong>{r.zero_amount_records}</strong>
          </div>
          <a
            className="button primary"
            href={`/sources?country=${country}&release=${release.release_id}`}
          >
            Inspect the source records <Arrow />
          </a>
        </div>
      </section>
      {s && (
        <section className="breakdown">
          <h2>What makes up the estimate</h2>
          <div className="amount-rows">
            {Object.entries(release.categories).map(([k, name]) => (
              <div key={k}>
                <span>
                  <i style={{ background: colors[k as Category] }} />
                  {name}
                </span>
                <strong>
                  {money(s.category_amount_minor[k as Category], r.currency)}
                </strong>
                <span>{s.category_counts[k as Category]} awards</span>
              </div>
            ))}
          </div>
          <p>
            Numerator: {money(s.numerator_minor, r.currency)}. Denominator:{" "}
            {money(s.denominator_minor, r.currency)}. Biology alone:{" "}
            {pct(s.biology_only_ratio)} of the classified denominator.
          </p>
          <aside className="method-callout">
            <strong>
              Known-amount sensitivity: {pct(s.sensitivity_lower)}–
              {pct(s.sensitivity_upper)}
            </strong>
            <p>
              {s.range_note} Unresolved awards account for{" "}
              {pct(s.unresolved_known_money_share)} of known portfolio funding.
              The range also does not account for errors in resolved
              classifications.
            </p>
          </aside>
        </section>
      )}
      <section className="report-scope">
        <h2>A portfolio view, with clear limits.</h2>
        <div className="two-columns">
          <div>
            <h3>What is covered</h3>
            <p>
              {country === "SE"
                ? "All records returned for the Swedish Research Council and Forte, filtered to Swecris funding year 2024. The two funders are government bodies."
                : "All NIA-administered FY2024 records returned by NIH RePORTER, keeping parent awards and excluding constituent subprojects to avoid counting the same money twice."}
            </p>
            <a
              href={
                country === "SE"
                  ? "https://www.vr.se/english/swecris/swecris-api.html"
                  : "https://api.reporter.nih.gov/"
              }
              target="_blank"
              rel="noreferrer"
            >
              Official source and API <Arrow />
            </a>
          </div>
          <div>
            <h3>What this cannot tell us</h3>
            <p>
              It cannot establish the full national ageing research budget,
              actual annual expenditure or a country ranking. Other funders are
              outside the collection. Mixed objectives and biology hidden under
              disease labels need expert review.
            </p>
            <a href="/method">
              Read definitions and failure modes <Arrow />
            </a>
          </div>
        </div>
      </section>
      <Gate release={release} compact />
      <section className="snapshot">
        <div>
          <span className="eyebrow">A REPORT YOU CAN TRACE</span>
          <h3>Keep the source, scope and date together.</h3>
          <p>
            Frozen release <code>{release.release_id}</code> · Retrieved{" "}
            {date(release.source_checked_at)}
          </p>
        </div>
        <div className="snapshot-actions">
          <a className="button outline" href={frozen}>
            Open frozen report <Arrow />
          </a>
          <button onClick={copy}>
            {copied ? "Link copied" : "Copy report link"}
          </button>
          <button
            onClick={share}
            disabled={!r.publication_ready || s?.ratio == null}
          >
            Download share card
          </button>
        </div>
        {!r.publication_ready && (
          <p className="muted">
            Numerical share cards become available after review. This frozen
            report records the current pending state.
          </p>
        )}
      </section>
    </>
  );
}
function Ledger({ release, grants }: { release: Release; grants: Grant[] }) {
  const isLoading = grants.length === 0 && release.source_count > 0;
  const initial = new URLSearchParams(location.search).get("country") || "all";
  const [country, setCountry] = useState(initial);
  const [q, setQ] = useState("");
  const [funder, setFunder] = useState("all");
  const [sort, setSort] = useState("title");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Grant | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const funds = [
    ...new Set(
      grants
        .filter((g) => country === "all" || g.country === country)
        .map((g) => g.funder),
    ),
  ];
  const filtered = useMemo(
    () =>
      grants
        .filter(
          (g) =>
            (country === "all" || g.country === country) &&
            (funder === "all" || g.funder === funder) &&
            `${g.title} ${g.id} ${g.project_number} ${g.funder}`
              .toLowerCase()
              .includes(q.toLowerCase()),
        )
        .sort((a, b) =>
          sort === "amount"
            ? (b.amount_minor ?? -1) - (a.amount_minor ?? -1)
            : a.title.localeCompare(b.title),
        ),
    [grants, country, funder, q, sort],
  );
  useEffect(() => setPage(1), [country, funder, q, sort]);
  const open = (g: Grant) => {
    setSelected(g);
    dialog.current?.showModal();
  };
  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">THE SOURCE LEDGER</span>
        <h1>Follow every award.</h1>
        <p>
          {num(release.source_count)} official-source records. Search a topic,
          inspect the funding basis and open the original award.
        </p>
        <p className="muted">
          Award facts are imported from the sources. Classification results
          appear only after the report passes review.
        </p>
      </section>
      <section className="ledger">
        <div className="ledger-filters">
          <label className="search-label">
            Search titles or grant IDs
            <input
              type="search"
              placeholder="Try metabolism, dementia or a grant ID…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </label>
          <label>
            Country
            <select
              aria-label="Country"
              value={country}
              onChange={(e) => {
                setCountry(e.target.value);
                setFunder("all");
                if (e.target.value === "all") setSort("title");
              }}
            >
              <option value="all">Both portfolios</option>
              <option value="SE">Sweden</option>
              <option value="US">United States</option>
            </select>
          </label>
          <label>
            Funder
            <select
              aria-label="Funder"
              value={funder}
              onChange={(e) => setFunder(e.target.value)}
            >
              <option value="all">All selected funders</option>
              {funds.map((f) => (
                <option key={f}>{f}</option>
              ))}
            </select>
          </label>
          <label>
            Sort
            <select
              aria-label="Sort"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="title">Title A–Z</option>
              <option value="amount" disabled={country === "all"}>
                Largest award first
              </option>
            </select>
          </label>
        </div>
        {sort === "amount" && country === "all" && (
          <p>Choose one country to compare amounts in the same currency.</p>
        )}
        <div className="ledger-meta">
          <strong>
            {isLoading
              ? "Loading source records…"
              : `${num(filtered.length)} matching records`}
          </strong>
          <span>Release {release.release_id}</span>
        </div>
        <div className="ledger-table">
          <table>
            <thead>
              <tr>
                <th>Award & source</th>
                <th>Government portfolio</th>
                <th>Recorded amount</th>
                <th>Classification</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice((page - 1) * 15, page * 15).map((g) => (
                <tr key={g.id}>
                  <td>
                    <button className="grant-title" onClick={() => open(g)}>
                      {g.title} <Arrow />
                    </button>
                    <small>
                      {g.project_number} · Source date {date(g.source_date)}
                    </small>
                  </td>
                  <td>
                    <span className="country-cell">
                      <Flag country={g.country} />
                      {release.reports[g.country].name}
                    </span>
                    <small>{g.funder}</small>
                  </td>
                  <td className="amount">
                    {money(g.amount_minor, g.currency)}
                    <small>
                      {g.year} ·{" "}
                      {g.country === "SE"
                        ? "Grant commitment"
                        : "Fiscal-year award"}
                    </small>
                  </td>
                  <td>
                    <span className="status-pill">
                      {g.classification
                        ? release.categories[g.classification.category]
                        : "Review pending"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {isLoading && (
            <div className="empty" role="status">
              <p>Loading the source ledger for this report…</p>
            </div>
          )}
          {!isLoading && !filtered.length && (
            <div className="empty">
              <h3>No matching awards.</h3>
              <p>Try another topic or grant identifier.</p>
            </div>
          )}
        </div>
        <div className="pagination">
          <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
            ← Previous
          </button>
          <span>
            Page {page} of {Math.max(1, Math.ceil(filtered.length / 15))}
          </span>
          <button
            disabled={page * 15 >= filtered.length}
            onClick={() => setPage((p) => p + 1)}
          >
            Next →
          </button>
        </div>
      </section>
      <dialog
        ref={dialog}
        className="grant-dialog"
        onClick={(e) => {
          if (e.target === dialog.current) dialog.current.close();
        }}
      >
        <button
          className="close-dialog"
          aria-label="Close source details"
          onClick={() => dialog.current?.close()}
        >
          ×
        </button>
        {selected && (
          <>
            <span className="eyebrow">ORIGINAL-SOURCE AWARD FACTS</span>
            <h2>{selected.title}</h2>
            <span className="status-pill">
              {selected.classification
                ? release.categories[selected.classification.category]
                : "Classification pending human review"}
            </span>
            <dl>
              {[
                ["Grant ID", selected.project_number],
                ["Government funder", selected.funder],
                [
                  "Recorded amount",
                  money(selected.amount_minor, selected.currency),
                ],
                ["Funding basis", selected.amount_basis],
                ["Funding year", String(selected.year)],
                [
                  "Funding period",
                  `${date(selected.funding_start)} to ${date(selected.funding_end)}`,
                ],
                [
                  "Source date",
                  `${date(selected.source_date)}. ${selected.source_date_note}`,
                ],
                ["Retrieved", selected.retrieved_at],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
            {selected.classification && (
              <div className="method-callout">
                <p>{selected.classification.rationale}</p>
                <blockquote>
                  {selected.classification.supporting_passage}
                </blockquote>
                <small>
                  Classification method: {selected.classification.method}. The
                  report is reviewed; individual records are not all
                  human-verified.
                </small>
              </div>
            )}
            <p>{release.reports[selected.country].basis}</p>
            <a
              className="button primary"
              target="_blank"
              rel="noreferrer"
              href={selected.source_url}
            >
              Open original award & abstract <Arrow />
            </a>
            <details>
              <summary>Provenance and reproducibility</summary>
              <p>Source fields: {selected.source_location}</p>
              <p>
                Normalised source hash <code>{selected.source_hash}</code>
              </p>
              <p>
                Record version <code>{selected.version_hash}</code>
              </p>
            </details>
          </>
        )}
      </dialog>
    </>
  );
}
function Method({ release }: { release: Release }) {
  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">DATA & METHOD</span>
        <h1>A ratio you can question.</h1>
        <p>
          The method is part of the report. Start with the award, classify its
          objective, then add the money.
        </p>
      </section>
      <section className="method-formula">
        <span>Ageing biology + interventions targeting ageing</span>
        <div />
        <strong>All classified ageing-related research funding</strong>
        <p>
          The headline is a share of funding amounts, not a share of grant
          counts.
        </p>
      </section>
      <section className="method-body">
        <article>
          <h2>Use the research budget as the denominator.</h2>
          <p>
            The denominator includes ageing biology, interventions targeting
            ageing, age-related disease research, care research and other ageing
            research within the selected portfolio. Care research means studying
            care. Spending on delivering care, pensions and social benefits is
            excluded.
          </p>
          <p>
            Unresolved awards stay outside the central estimate and enter a
            separate sensitivity calculation. Outside-scope awards remain
            visible in the source ledger.
          </p>
          <h2>Keep the two funding bases visible.</h2>
          <div className="two-columns">
            {countries.map((c) => (
              <div key={c}>
                <h3>{release.reports[c].name}</h3>
                <p>{release.reports[c].basis}</p>
                <p>
                  {num(release.reports[c].record_count)} retained records.{" "}
                  {c === "US"
                    ? `${num(release.reports.US.coverage.excluded_subprojects || 0)} constituent subprojects excluded to prevent duplicate totals.`
                    : "All years were paged from both selected funders, then filtered locally by fundingYear = 2024."}
                </p>
                <a
                  href={
                    c === "US"
                      ? "https://report.nih.gov/faqs"
                      : "https://www.vr.se/english/swecris/swecris-api.html"
                  }
                  target="_blank"
                  rel="noreferrer"
                >
                  Source definition <Arrow />
                </a>
              </div>
            ))}
          </div>
          <p>
            No annualisation or exchange-rate conversion is applied. Funding
            government determines the country, even if a recipient is abroad.
            These portfolios do not represent all government research funding in
            either country.
          </p>
          <h2>Classify the objective, not just the title.</h2>
          <p>
            The current classifier uses inspectable rules over the complete
            available abstract. Earlier model labels are reused only as
            candidates when the title, year, amount and a verbatim source
            passage match, and the current rule agrees. No new paid model calls
            were made.
          </p>
          <p>
            A mention of metabolism or neurodegeneration does not settle the
            category. An ageing-biology objective can sit under a disease label;
            conversely, a disease project can mention ageing only as background.
            Ambiguous cases remain unresolved. Missing or short abstracts and
            Swedish-language abstracts are held for review under the current
            English rule set.
          </p>
          <div className="taxonomy">
            {Object.entries(release.categories).map(([k, t]) => (
              <div key={k}>
                <span
                  className="taxonomy-dot"
                  style={{ background: colors[k as Category] }}
                />
                <div>
                  <h3>{t}</h3>
                  <p>{descriptions[k as Category]}</p>
                </div>
              </div>
            ))}
          </div>
          <h2>Make uncertainty visible.</h2>
          <p>
            Let <b>N</b> be known funding for ageing biology and ageing
            interventions, <b>D</b> be all classified ageing-related funding,
            and <b>U</b> be known funding whose objective is unresolved.
          </p>
          <div className="formula-row">
            <div>
              <small>Central estimate</small>
              <strong>N / D</strong>
            </div>
            <div>
              <small>Lower sensitivity bound</small>
              <strong>N / (D + U)</strong>
            </div>
            <div>
              <small>Upper sensitivity bound</small>
              <strong>(N + U) / (D + U)</strong>
            </div>
          </div>
          <p>
            These are classification scenarios for known amounts, not confidence
            intervals. They do not cover errors in already classified awards.
            Unknown monetary amounts are counted separately and excluded from
            the bounds. True zeros remain zero. When no classified denominator
            exists, the ratio and bounds are unavailable.
          </p>
          <h2>Test the claims before sharing them.</h2>
          <p>
            The frozen benchmark contains 30 records per country, sampled across
            predicted categories with seed 42. Twelve development cases are
            excluded. Forty sampled titles do not mention ageing. Reviewers
            choose a category without seeing the model prediction, then check
            the source, financial fields and government scope.
          </p>
          <p>
            A record passes only when its category matches the frozen prediction
            and all three source checks pass. The first completed human verdict
            is retained. All 60 reviews are required, with at least 54 correct
            overall and 27 in each country. This stratified benchmark score is
            not an estimate of accuracy across all awards.
          </p>
          <p>
            Each report also needs human approval of its scope, money basis,
            arithmetic and uncertainty, plus category and source checks on the
            ten largest recorded awards, including large exclusions. A source or
            classification change invalidates the matching approvals. The
            original policy and grant benchmarks remain separate.
          </p>
          <aside className="method-callout">
            <strong>What would make us reject the headline?</strong>
            <p>
              Failing the 90% benchmark, unresolved scope or double-counting,
              incorrect high-value awards, or a rejected report assessment
              blocks publication. A small apparent share is not a finding until
              those checks pass. We do not assume the result will show a large
              funding gap.
            </p>
          </aside>
          <h2>Sources, reuse and cross-checking</h2>
          <p>
            Original award facts come from{" "}
            <a
              href="https://api.reporter.nih.gov/"
              target="_blank"
              rel="noreferrer"
            >
              NIH RePORTER
            </a>{" "}
            and{" "}
            <a
              href="https://www.vr.se/english/swecris.html"
              target="_blank"
              rel="noreferrer"
            >
              Swecris
            </a>
            . Public API access does not imply unrestricted copyright permission
            for grant abstracts. We keep full abstracts and API snapshots in the
            local research store; the public ledger contains factual metadata
            and, after approval, brief supporting excerpts.
          </p>
          <p>
            You.com and Tavily help discover and cross-check source definitions.
            Their summaries are not evidence verdicts. The combined research
            ledger records{" "}
            {release.research_crosschecks.attempted_requests_total} attempted
            requests against the authorised cap of{" "}
            {release.research_crosschecks.combined_cap}, including earlier
            project work.
          </p>
          <details>
            <summary>See the dated provider cross-checks</summary>
            <div className="crosschecks">
              {release.research_crosschecks.checks.map((x, i) => (
                <div key={i}>
                  <strong>
                    {x.provider} · {date(x.checked_at)}
                  </strong>
                  <p>{x.query}</p>
                  <span className="muted">{x.status.replaceAll("_", " ")}</span>
                  <ul>
                    {x.links.map((l) => (
                      <li key={l.url}>
                        <a href={l.url} target="_blank" rel="noreferrer">
                          {l.title || l.url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </details>
          <h2>What remains to be tested</h2>
          <p>
            Human classification accuracy has not yet been established for this
            release. Boundary definitions need an ageing biologist’s review,
            particularly projects under metabolism and neurodegeneration.
            National coverage, year-to-year stability and whether a new reader
            understands the report in three seconds remain untested.
          </p>
          <p>
            This is a research-funding communication tool. It does not predict
            clinical outcomes, recommend therapies or estimate the effect of
            funding on lifespan.
          </p>
          <a
            className="button outline"
            href={`/funding/releases/${release.release_id}.json`}
          >
            Download this release's method & coverage JSON <Arrow />
          </a>
        </article>
      </section>
      <Gate release={release} />
    </>
  );
}
export default function FundingApp() {
  const [release, setRelease] = useState<Release | null>(null),
    [grants, setGrants] = useState<Grant[]>([]),
    [error, setError] = useState("");
  const path = location.pathname.replace(/\/$/, "") || "/";
  const sourcePage = path === "/sources";
  useEffect(() => {
    const id = new URLSearchParams(location.search).get("release");
    const url =
      id && /^[a-f0-9]{16}$/.test(id)
        ? `/funding/releases/${id}.json`
        : "/funding/current.json";
    fetch(url)
      .then((r) => {
        if (!r.ok) throw Error("This report snapshot is unavailable.");
        return r.json();
      })
      .then((r: Release) => {
        setRelease(r);
        if (sourcePage)
          return fetch(`/funding/ledgers/${r.ledger_hash.slice(0, 16)}.json`)
            .then((x) => {
              if (!x.ok) throw Error("The source ledger could not be loaded.");
              return x.json();
            })
            .then((j) => setGrants(j.records));
      })
      .catch((e) => setError(e.message));
  }, [sourcePage]);
  useEffect(() => {
    document.title = `${path === "/method" ? "Data & method" : path === "/sources" ? "Source ledger" : path.includes("sweden") ? "Sweden" : path.includes("united-states") ? "United States" : "Where does ageing research money go?"} · Longview`;
  }, [path]);
  if (error)
    return (
      <main className="load-state">
        <h1>We couldn't load this report.</h1>
        <p>{error}</p>
        <a href="/">Return to the current report</a>
      </main>
    );
  if (!release)
    return (
      <main className="load-state" aria-live="polite">
        Loading the funding report…
      </main>
    );
  const country =
    path === "/country/sweden"
      ? "SE"
      : path === "/country/united-states"
        ? "US"
        : null;
  const known = path === "/" || path === "/method" || sourcePage || country;
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <a className="brand" href="/" aria-label="Longview home">
          <span className="brand-mark">
            <i />
            <i />
            <i />
            <i />
          </span>
          longview<span className="brand-sub">/ funding</span>
        </a>
        <nav aria-label="Main navigation">
          <a className={path === "/" || country ? "active" : ""} href="/">
            Portfolios
          </a>
          <a className={sourcePage ? "active" : ""} href="/sources">
            Sources
          </a>
          <a className={path === "/method" ? "active" : ""} href="/method">
            Method
          </a>
        </nav>
        <span className="edition">
          2024 EDITION <i />
        </span>
      </header>
      <main id="main">
        {known ? (
          path === "/" ? (
            <Home release={release} />
          ) : path === "/method" ? (
            <Method release={release} />
          ) : sourcePage ? (
            <Ledger release={release} grants={grants} />
          ) : (
            <CountryPage release={release} country={country as Country} />
          )
        ) : (
          <section className="page-heading">
            <h1>This page has moved.</h1>
            <p>Longview now focuses on public ageing research funding.</p>
            <a className="button primary" href="/">
              Explore the funding report
            </a>
          </section>
        )}
      </main>
      <footer className="site-footer">
        <div>
          <a className="brand" href="/">
            longview
          </a>
          <p>Public research funding, made traceable.</p>
        </div>
        <div>
          <a href="/method">Method & limitations</a>
          <a href="/sources">Source ledger</a>
          <a href="/review/funding/">Funding reviewer workspace</a>
          <a href="/review/">Earlier policy review</a>
        </div>
        <div>
          <span>Research prototype · Stockholm, 2026</span>
          <small>
            Source snapshot {date(release.source_checked_at)}
            <br />
            Release {release.release_id}
            <br />
            Not a national ranking or a clinical tool.
          </small>
        </div>
      </footer>
    </>
  );
}
