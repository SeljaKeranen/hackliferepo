# Human eval loop

Human verification loop for the
[map-the-politics-of-longevity challenge](../docs/challenge.md), covering
Sweden, the US and Singapore. The challenge bar: at least 90% of sampled
findings verified correct by a human reviewer, every finding carrying a dated
source.

## Run it

```sh
python3 eval/server.py
```

Then open <http://localhost:8000>. No dependencies beyond Python 3 stdlib.
A `--port` flag exists; default 8000. The server serves every country file
found under `findings/*.json`; pick the country from the selector in the
header, which also shows the selected country's stats and the overall
accuracy across all countries.

## The rubric

Each finding shows its claim, a clickable source link, source date,
classification and confidence. The reviewer opens the source and marks four
checks, each pass or fail:

1. **Source resolves** — the URL opens and shows a real document from the
   claimed publisher (not a 404, parking page, or unrelated page).
2. **Date correct** — the `source_date` matches the source's publication or
   decision date (to the stated precision).
3. **Classification correct** — the label (policy / legislation / funding /
   strategy / political statement) is the right one for what the source shows.
4. **Claim supported** — everything the claim asserts is supported by the
   source; no invented numbers, dates, names, or overreach.

A finding is **correct only if all four checks pass**. The header shows
running accuracy = correct / reviewed.

## The AI judge panel

To compress the human workload, three independent AI judges pre-mark every
finding before the human pass (each judge fetched and read the source, not
just the claim text):

1. **credibility** — is the publisher credible, and does the source genuinely
   support the whole claim (right numbers, names, dates, no overreach)?
2. **recency** — is the source still current for what the claim asserts? If
   it is superseded or a materially newer official artifact exists, the judge
   records a `newer_source` suggestion (URL + date). Suggestions never replace
   the original source; they live only in the judgment record.
3. **classification** — is the label (policy / legislation / funding /
   strategy / political statement) right for what the source shows? If not,
   the judge records a `proposed_classification`.

Each judge verdict is `pass`, `fail` or `uncertain` with a one-or-two-line
reason. The review screen shows the three verdicts per finding and sorts
findings any judge flagged (fail/uncertain, or stale judgments) first. The
human then clicks **Agree** (all four checks pass), **Disagree** (pick which
check fails), or overrides individual checks. When a judge flag makes you
disagree, map the dimension to the rubric check like this: a credibility
fail is usually *claim supported* (or *source resolves* if the URL itself is
the problem), a recency fail with a wrong date on the original source is
*date correct* (a merely-superseded source with a correct date is a judgment
call — often still all-pass plus a note), and a classification fail is
*classification correct*. Disagree records the picked check as fail and the
untouched checks as pass; use the per-check buttons instead when more than
one check fails. The AI judgments are advisory
pre-marks only: the human's four-check verdict in `verdicts/` remains the
accuracy metric the challenge is scored on.

### Judgment record schema

`judgments/<country>.judgments.json` is an object keyed by finding id:

```json
{
  "se-001": {
    "finding_id": "se-001",
    "finding_fingerprint": "16-hex-digit fingerprint of the judged content",
    "judged_at": "2026-09-12T09:00:00Z",
    "judges": {
      "credibility": { "verdict": "pass", "reason": "..." },
      "recency": {
        "verdict": "fail", "reason": "...",
        "newer_source": { "url": "https://...", "date": "2026-02-24" }
      },
      "classification": {
        "verdict": "fail", "reason": "...",
        "proposed_classification": "policy"
      }
    }
  }
}
```

`verdict` is one of `pass` / `fail` / `uncertain`. `newer_source` (recency
only) and `proposed_classification` (classification only) are optional. The
fingerprint works like the verdict fingerprint: editing a finding marks its
judgments stale — the UI says so and `test_findings.py` fails until the
finding is re-judged. The server serves judgments read-only; there is no
write API for them.

## Where things live

- `../schema/finding.schema.json` — the finding record contract, including the
  explicit `nothing_reliable_found` record shape for quiet countries.
- `findings/<country>.json` — the findings under review, one file per country
  (`sweden.json`, `us.json`, `singapore.json`; committed; `data/` stays
  gitignored for local scratch).
- `judgments/<country>.judgments.json` — AI judge panel pre-marks (committed;
  schema above), produced by fan-out judging sessions and read-only to the
  server.
- `verdicts/<country>.verdicts.json` — verdicts, written by the server on every
  click. Committed: the verdicts are the evidence for the accuracy claim, so
  commit them after a review session. Each verdict stores a fingerprint of the
  finding content it attests to; if a finding is edited after review, the
  review screen shows the verdict as "stale — re-review" and drops it from the
  accuracy counts, and `test_findings.py` fails until it is re-reviewed.
  The server refuses to save over a verdicts file it cannot parse (fix the
  file by hand first) so evidence is never silently clobbered.

## Limitations (by design, for the pilot)

- One review session at a time per country: verdicts are last-write-wins with
  no locking, so don't review the same country from two tabs or machines at
  once. Merge parallel review sessions by hand if it ever comes to that.
- The page loads existing verdicts once at startup; reload to see verdicts
  written by a previous session.
- Clicking an already-selected pass/fail button clears that check back to
  "not answered" (that's the intended way to undo a click).

## Validate the data

```sh
python3 eval/test_findings.py
python3 eval/test_server.py
```

`test_findings.py` structurally validates every `findings/*.json` against the
schema constraints and cross-checks verdicts and AI judgments (ids exist,
fingerprints match, records sit in the right country file, judge records are
well-formed). `test_server.py` smoke-tests the server's HTTP contract against
a temporary data directory.
