# Human eval loop

Sweden-first pilot of the human verification loop for the
[map-the-politics-of-longevity challenge](../docs/challenge.md). The challenge
bar: at least 90% of sampled findings verified correct by a human reviewer,
every finding carrying a dated source.

## Run it

```sh
python3 eval/server.py
```

Then open <http://localhost:8000>. No dependencies beyond Python 3 stdlib.
`--port` and `--country` flags exist; defaults are 8000 and sweden.

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

## Where things live

- `../schema/finding.schema.json` — the finding record contract, including the
  explicit `nothing_reliable_found` record shape for quiet countries.
- `findings/sweden.json` — the findings under review (committed; `data/` stays
  gitignored for local scratch).
- `verdicts/sweden.verdicts.json` — verdicts, written by the server on every
  click. Committed: the verdicts are the evidence for the accuracy claim, so
  commit them after a review session.

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
```

Structurally validates every `findings/*.json` against the schema constraints
and sanity-checks any verdicts files.

## Longview version-bound review

The three active packets are `sweden`, `united-states` and `singapore`. The original Sweden seed is preserved in `legacy/sweden.seed.json`. Rich provenance lives beside the schema-compatible findings in `provenance/`.

Each verdict now needs reviewer initials and the exact finding/provenance version hash served by `/api/findings`. Unknown IDs and stale versions are rejected. Completed reviews append to `verdicts/<country>.history.jsonl`; the first completed verdict for each frozen `benchmark.json` version determines the initial pass rate. Correcting a claim does not erase its original error.

For remote machines, `node scripts/package-review.mjs` encrypts the candidates into `public/review/packet.json`. The private key stays in ignored `outputs/reviewer.key`. The hosted `/review/` page decrypts in the reviewer's browser, saves work locally and exports a verdict JSON file. Import an actual human export with `python -m pipeline.import_reviews FILE`, then rebuild with `python -m pipeline.release`. Do not import synthetic browser-test exports from `outputs/`.

The initial sample is 34 records. Two supplemental research-funding leads were added after that freeze and are labelled separately. `pipeline.release --strict` requires every candidate to be currently approved and the full original sample to meet the ≥90% target. A pending release reports “not measured” until at least one initial verdict exists; it never displays a fabricated accuracy.
