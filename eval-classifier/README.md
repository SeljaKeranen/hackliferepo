# Grant-classifier evaluation gate

Quickstart for reviewers — three lines:

```sh
git pull
python3 eval-classifier/server.py       # review UI at http://localhost:8001
# review; then commit eval-classifier/verdicts/<you>.verdicts.json
```

This is the human verification loop for the labels the funding-gap ratio
pipeline (`ratio/classify.py`) assigns to grant records. Sibling of the
political findings loop in `eval/` (same judge-panel + agree/disagree
pattern, different pipeline); the two share no code or data.

**The deliverable is the measured agreement between the pipeline and human
judgment — not 100% accuracy.** The challenge bar is >= 85% agreement on the
reviewed sample with `ambiguous` flagged explicitly rather than forced, but
an honest low number beats a lenient high one: **disagreements are the
product**, they quantify the classifier's reliability. Judge each label
strictly on the rubric, never leniently.

## The taxonomy and the mapping

Humans label in the **four-label taxonomy** (the team's working taxonomy
after Andrew's input, same label ids as
`ratio/instrument/taxonomy.json` "andrew-working-v1" on the Longview
instrument branch, PR #16):

| label | means |
| --- | --- |
| `preventing_slowing` | the stated aim studies biological ageing itself or develops/tests ways to modify it (fundamental mechanisms count, even without a therapy) |
| `consequences` | the stated aim concerns age-related disease, functional decline, care, or social/population consequences of ageing — needs an explicit ageing connection |
| `neither` | the available aims support neither definition (battery life, leaf senescence, unrelated topics) |
| `ambiguous` | the two definitions compete without a clear primary aim, or the text does not support a choice |

Every verdict also carries an independent **low-confidence checkbox**: it
records uncertainty about your judgment (missing or truncated text), not a
probability — a clearly documented boundary case is `ambiguous` *without*
low confidence.

The pipeline still emits its raw five-category labels; for the agreement
metric they are mapped (`server.py:FOUR_LABEL_MAP`), and the raw label
stays visible on every record and in every export:

| pipeline raw label | four-label |
| --- | --- |
| `fundamental_aging`, `intervention` | `preventing_slowing` |
| `age_related_disease`, `care`, `social_population_aging` | `consequences` |
| `not_relevant` | `neither` |
| `ambiguous` | `ambiguous` |

## The metric

**Agreement = records where the human four-label matches the pipeline's
mapped label / records with a human consensus.** A click on **Agree**
confirms the mapped label; **Disagree** requires picking the correct
four-label. The header shows the point estimate with a 95% Wilson
confidence interval and n. Stale verdicts (the record changed after review)
count as unreviewed. The header also shows **ambiguous honesty**: of the
consensus-reviewed records the pipeline flagged `ambiguous`, how many the
human confirmed as genuinely unplaceable — whether the pipeline flags
uncertainty honestly instead of forcing categories.

`python3 eval-classifier/server.py --summary` prints the same numbers and
exits 0 on target (or nothing reviewed), 1 below target, 2 on unreadable
evidence files.

## Tuning half and sealed holdout (overfitting guard)

Every sampled record is deterministically assigned to a **tuning** half or a
**sealed holdout** half by a seeded hash of its record id
(`sample.py:split_for`; per-record, so records never migrate between halves
when the sample is regenerated — the halves are approximately equal). The
screen and `--summary` report agreement for each half separately plus
combined. The discipline:

- **Classifier fixes may be motivated only by tuning-half findings.** The
  holdout half is never mined for error patterns.
- **The acceptance test for any classifier change is non-degrading
  agreement on the holdout half**, checked once per change — not iterated
  against.
- **Low-confidence expert verdicts and inter-reviewer overlap records are
  measurement-only**: they inform the reliability numbers, never tuning
  inputs.
- **The holdout comparison uses a frozen sample.** When checking a
  classifier change, keep the committed `sample.json` fixed: which records
  the sampler picks depends on the pipeline's labels, so re-running
  `sample.py` against new labels changes the holdout *membership* (the
  per-record hash only keeps a given record's half stable). Regenerate the
  sample only as a deliberate, separate step that starts a new baseline.

The comments on PRs #11 and #12 carry the captain's baseline-and-holdout
direction that this scheme implements.

## Two reviewers at once

Verdicts are per-reviewer files: the server writes only
`verdicts/<reviewer>.verdicts.json`, with the reviewer slug taken from
`--reviewer`, else `git config user.name`, else `$USER`. On a shared
machine or account, ALWAYS pass `--reviewer <your-name>` — two people
falling back to the same identity would silently overwrite each other's
verdicts instead of surfacing their disagreements. The server prints the
identity it resolved at startup and the UI header shows it; check it before
reviewing. Two people on
different machines can review simultaneously and both commit — the files
never collide, and the metric merges every verdict file at read time:

- A record reviewed by several reviewers **counts once**.
- If their labels **conflict**, the record is surfaced as an
  **inter-reviewer disagreement** (a visible list in the UI and a count in
  `--summary`) and excluded from the agreement numbers until resolved.
  That overlap is valuable calibration data, not an error — discuss and
  re-review.
- To split the work without coordination, open the UI with
  `?assign=1of2` / `?assign=2of2` — a deterministic hash of the record id
  divides the sample.

The same collision problem exists in `eval/` (findings review); retrofitting
this per-reviewer scheme there is noted as follow-up work rather than done
in this change, because `eval/` has committed per-country verdict files and
its own test contract — the mechanical change is the same but touches its
server, UI and validation tests.

## The rubric

Label the **stated research purpose** from the taxonomy table above.
Decide relevance first (is this about human ageing at all? if not:
`neither`), then whether the aim targets ageing biology itself
(`preventing_slowing`) or its consequences (`consequences` — the ageing
connection must be explicit: treating a disease common in older adults does
not by itself qualify). `ambiguous` is a first-class answer, never a
dumping ground. Tick low confidence when the text limits your judgment.
Judge from title + quote — the same text the classifier saw (shown on each
card; the source link is there for doubt, but the classifier can only be
graded on its input).

The raw five-category definitions the *pipeline* uses (with worked corpus
examples) live in [`classifier/KEYWORDS.md`](../classifier/KEYWORDS.md);
they matter for understanding what the raw label meant, not for your
verdict.

## The admin panel (for the researcher review)

`http://localhost:8001/admin.html` (any running review server) shows:

- per-item label counts across all reviewers, with **disagreements ranked
  to the top** (human-vs-human first, then pipeline-vs-human, then
  low-confidence);
- **labeller-vs-labeller agreement** for every reviewer pair with overlap
  (share of identical four-labels, Wilson 95% CI);
- **pipeline-vs-human agreement** combined and per tuning/holdout split,
  and per reviewer;
- **one-click CSV export** of every decision (`/api/export.csv`: one row
  per record × reviewer, with raw + mapped pipeline labels, low-confidence
  flags, notes, provenance; formula-injection-escaped).

### Importing Longview instrument exports

The Longview research instrument (PR #16, `ratio/instrument/`) exports
per-reviewer JSON files in its `longview-human-labels-v1` format. Drop such
files into `eval-classifier/imports/` and they are ingested as extra
reviewers named `import:<reviewer>` in every metric. Only attested human
exports are accepted (model/simulation files are rejected loudly), and
only with `taxonomy_version` = `andrew-working-v1` — the same label
strings under a different taxonomy version are not comparable evidence.
Decisions on record ids outside this gate's sample are counted and
skipped. `--summary` prints how many included decisions came from imports,
so the headline number never moves invisibly.

Import files are evidence with the same trust model as `verdicts/`: the
gate cannot prove who authored a file, so an import landing in a PR must
be reviewed there like any other evidence — check in the PR that the file
came from the named researcher, not from the same author as the classifier
change it appears to confirm. Nothing cryptographic binds a reviewer code
to a person. **Limitation:** imported decisions attested to the instrument's
own text of the record, not to this gate's card, so they bypass this
gate's fingerprint check — the admin view and CSV mark their origin.

## How the sample was stratified

`sample.py` draws ~72 of the pipeline's 2,944 labelled records,
deterministically for a fixed labels file and seed (default 20260912):

1. **All 30 legacy benchmark records** from
   `data/Track3_C2/benchmark/benchmark_30_key.json` (recovered with
   `git show 2e59b27:data/Track3_C2/benchmark/benchmark_30_key.json` if the
   live file disappears). The benchmark predates this gate and was never
   labelled; reviewing here labels it (see benchmark export below).
2. **At least one record per non-empty label × source stratum** (7 labels ×
   swecris/cordis/reporter), so no category or source goes unmeasured.
3. **Decision-boundary oversample**: 10 records with a substantive label
   whose winning precision margin is below 0.45 (forced calls just above the
   classifier's 0.3 ambiguity floor), and 10 records where the atlas's old
   `llm_category` (one of the four original substantive labels) disagrees
   with the new label.
4. **Round-robin top-up across labels** to the target, so the large
   ambiguous/not_relevant pools cannot drown the small categories.

Every sampled record carries `sampling.why` naming which of these rules
picked it. `sample.json`'s `meta` records the seed, the labels file's
SHA-256, the per-rule pick counts and the resulting label counts. To
regenerate after the pipeline re-runs:

```sh
python3 ratio/classify.py                    # writes ratio/output/labels.jsonl
python3 eval-classifier/sample.py            # writes eval-classifier/sample.json
```

Regenerating changes record fingerprints wherever a record's attested
content changed, which marks the affected AI judgments and human verdicts
stale — the UI demands a re-review and `test_gate.py` fails until they are
re-done. That is the point: attestation never outlives the content it
attested to. The server also refuses (HTTP 409) any verdict whose card
rendered an older version of the record than the one on disk.

## The AI judge panel

Three independent AI judges pre-mark every sampled record before the human
pass (fan-out judging sessions, one batch per judge dimension, each given
the rubric above and the record's full text):

1. **relevance** — is this grant about human ageing/longevity at all? This
   validates the step-0 call: a `not_relevant` label on an on-topic record
   fails here, as does a substantive label on a battery-ageing grant.
2. **category** — is the assigned label right under the rubric, including
   the ageing-anchor and mechanism-vs-intervention rules? If not, the judge
   records a `proposed_label`.
3. **evidence** — do the matched keywords and the stated reason actually
   appear in and support the record's text? No phantom matches, no reason
   that overreaches what title + quote say.

Each verdict is `pass` / `fail` / `uncertain` with a one-or-two-line reason,
stored in `judgments.json` keyed by record id, with the record's fingerprint
(same invalidation pattern as `eval/`):

```json
{
  "swecris:2019-01234_VR": {
    "record_id": "swecris:2019-01234_VR",
    "record_fingerprint": "16-hex-digit fingerprint of the judged content",
    "judged_at": "2026-09-12T12:00:00Z",
    "judges": {
      "relevance": { "verdict": "pass", "reason": "..." },
      "category": { "verdict": "fail", "reason": "...",
                    "proposed_label": "care" },
      "evidence": { "verdict": "pass", "reason": "..." }
    }
  }
}
```

The review screen sorts judge-flagged records first and shows the three
verdicts per card. **The AI judgments are advisory pre-marks only: the
human verdicts in `verdicts/` are the agreement metric the gate is scored
on.** The judges compress the human workload; they do not replace it.
The judges pre-date the four-label retarget and speak the raw label space
(`proposed_label` is a raw category); they remain valid as attention
routers — a category flag still means "look closely" — but their proposals
are not four-labels.

## The legacy benchmark export

The atlas shipped a 30-record human benchmark that was never labelled
(`data/Track3_C2/benchmark/`, "0/30 labelled" in its evaluation report).
All 30 are in this gate's sample; once reviewed, export them in the format
the old evaluate path expects:

```sh
python3 eval-classifier/export_benchmark.py   # writes benchmark_30_filled.csv
```

Only consensus verdicts export (conflicting or stale ones stay blank).
`human_category` gets the human-confirmed **four-label** verbatim — honesty
over backwards compatibility — and labels the annotation guide does not
know carry `legacy_equiv=ambiguous` in `human_notes` for old tooling.
`human_confidence` is 1.0 throughout: the gate collects a categorical
decision plus a separate low-confidence flag, not graded confidence.

## Where things live

- `sample.py` — stratified sampler (labels.jsonl → `sample.json`).
- `sample.json` — the sampled records under review (committed; carries its
  provenance in `meta`).
- `judgments.json` — AI judge pre-marks (committed; read-only to the server).
- `verdicts/<reviewer>.verdicts.json` — human verdicts, one file per
  reviewer, written by that reviewer's server on every click. Committed:
  the verdicts are the evidence for the agreement claim, so commit yours
  after a review session. The server refuses to save over a verdicts file
  it cannot parse, so evidence is never silently clobbered.
- `server.py` / `static/` — the review UI (`/`) and the admin panel
  (`/admin.html`, with `/api/admin` and `/api/export.csv`). `--summary`
  prints the metrics.
- `imports/` — drop Longview instrument export files here (not committed
  unless they are real review evidence you want in the PR).
- `export_benchmark.py` — fills the legacy benchmark CSV from the verdicts.
- `test_sample.py`, `test_gate.py` — sampler determinism and boundary
  logic; verdict/agreement math (multi-reviewer merge, conflicts, Wilson
  interval), fingerprint invalidation, the server's HTTP contract, the
  benchmark export, and validity of the committed
  sample/judgments/verdicts files.

## Limitations (by design, for the pilot)

- The reviewer grades the classifier on its input (title + llm_quote from
  the atlas), not on full abstracts the classifier never saw. Agreement
  measured here does not transfer automatically to live full-text data —
  KEYWORDS.md's corpus caveats apply to the gate too.
- The sample is ~2.4% of the corpus and deliberately oversamples the
  benchmark, decision boundaries and small categories, so the agreement
  number describes the pipeline on this stratified review sample — it is
  not an unbiased corpus-wide estimate (the boundary oversample makes it,
  if anything, a pessimistic one).
- Verdicts trust the local operator: the gate records what was clicked on
  this machine and cannot prove a human did the clicking. The evidence
  model is the committed workflow — per-reviewer files under version
  control with fingerprints, reviewed in the PR like any other evidence.
- The labels under review came from a snapshot of `ratio/output/labels.jsonl`
  (`sample.json` meta has its SHA-256). If the ratio pipeline changes, re-run
  the sampler; fingerprints will mark anything that changed for re-review.
