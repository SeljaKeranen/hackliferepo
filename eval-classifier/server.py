#!/usr/bin/env python3
"""Localhost human-eval server for the grant-classifier evaluation gate.

Run: python3 eval-classifier/server.py [--port 8001] [--reviewer NAME]
Then open http://localhost:8001

Stdlib only. Serves the review UI over eval-classifier/sample.json (the
stratified sample of ratio-pipeline labels), AI judge pre-marks from
eval-classifier/judgments.json (read-only), and reads/writes human verdicts
to eval-classifier/verdicts/<reviewer>.verdicts.json. Humans label in the
four-label taxonomy (preventing_slowing / consequences / neither /
ambiguous, plus an independent low-confidence flag); the pipeline's raw
five-category label is mapped via FOUR_LABEL_MAP for the agreement metric
and stays visible per record. /admin.html serves the admin panel
(per-item counts, pairwise reviewer agreement, pipeline-vs-human agreement,
disagreements ranked first, CSV export); Longview instrument exports in
eval-classifier/imports/ are ingested as extra reviewers.

The measured deliverable is the pipeline's agreement with human judgment,
with `ambiguous` flagged honestly rather than forced; the working bar is
>= 85% on the reviewed sample. Disagreements are the product, not a failure.

Two reviewers can review at once on different machines: each server writes
only its local reviewer's verdict file (reviewer from --reviewer, else git
config user.name, slugified), and the metric merges every verdict file at
read time. A record reviewed by both counts once; if their labels conflict
it is surfaced as an inter-reviewer disagreement (calibration data) and
excluded from the agreement numbers.

`--summary` prints the current numbers and exits (used for the PR report
and by the tests).
"""
import argparse
import glob
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

GATE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(GATE_DIR, "static")
SAMPLE_PATH = os.path.join(GATE_DIR, "sample.json")
VERDICTS_DIR = os.path.join(GATE_DIR, "verdicts")
JUDGMENTS_PATH = os.path.join(GATE_DIR, "judgments.json")

# The pipeline's raw five-category label space (plus ambiguous/not_relevant).
# Kept visible on every record; sample.json is validated against it.
RAW_LABELS = ("fundamental_aging", "intervention", "age_related_disease",
              "care", "social_population_aging", "ambiguous", "not_relevant")
# The four-label human taxonomy (Andrew's working taxonomy, same label ids
# as ratio/instrument/taxonomy.json "andrew-working-v1"): every human
# verdict carries one of these plus an independent low-confidence flag.
LABELS = ("preventing_slowing", "consequences", "neither", "ambiguous")
# Documented mapping from the pipeline's raw labels into the four-label
# taxonomy, used for the pipeline-vs-human agreement metric. The raw label
# stays visible per record; only the comparison happens in mapped space.
FOUR_LABEL_MAP = {
    "fundamental_aging": "preventing_slowing",
    "intervention": "preventing_slowing",
    "age_related_disease": "consequences",
    "care": "consequences",
    "social_population_aging": "consequences",
    "not_relevant": "neither",
    "ambiguous": "ambiguous",
}
# Jan's Longview research-instrument export format (see PR #16,
# ratio/instrument/review.mjs): admin ingests these as extra reviewers.
IMPORT_FORMAT = "longview-human-labels-v1"
# The taxonomy version this gate's four labels implement. An import whose
# taxonomy_version differs may reuse the same label STRINGS with different
# semantics, so it is rejected, not mixed into the agreement numbers.
IMPORT_TAXONOMY_VERSION = "andrew-working-v1"
IMPORTS_DIR = os.path.join(GATE_DIR, "imports")
# Deliberately different from REVIEWER_SLUG_RE: import reviewer codes are
# opaque tokens minted by the instrument (its own 2-40 char rule), not
# filenames this server generates; they are namespaced with "import:",
# which the local slug rule cannot produce.
IMPORT_REVIEWER_RE = re.compile(r"[A-Za-z0-9_-]{2,40}")


def pipeline_label(rec):
    """The record's pipeline label mapped into the four-label taxonomy;
    None when the raw label is unknown (corrupt sample)."""
    return FOUR_LABEL_MAP.get(rec.get("label"))


JUDGE_DIMENSIONS = ("relevance", "category", "evidence")
JUDGE_VERDICTS = ("pass", "fail", "uncertain")
# Reviewer slugs are verdict FILENAMES; keep them boring so they can't
# traverse paths (same rule as eval/'s country slugs).
REVIEWER_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")

# The local reviewer this server instance writes verdicts for; set by
# main() (or by tests). POST refuses to save while it is unset.
REVIEWER = None


def slugify_reviewer(name):
    slug = re.sub(r"[^a-z0-9_-]+", "-", str(name).strip().lower()).strip("-")
    return slug if REVIEWER_SLUG_RE.fullmatch(slug) else None


def detect_reviewer(cli_value=None):
    """--reviewer wins; else git config user.name; else $USER."""
    for candidate in (cli_value,
                      _git_user_name(),
                      os.environ.get("USER")):
        slug = slugify_reviewer(candidate) if candidate else None
        if slug:
            return slug
    return None


def _git_user_name():
    try:
        out = subprocess.run(["git", "config", "user.name"],
                             capture_output=True, cwd=GATE_DIR)
        return out.stdout.decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def record_fingerprint(rec):
    """Hash of the content a judge or reviewer attests to. Stored with each
    judgment and verdict so a later change to the sampled record (a re-run
    of the pipeline or the sampler) invalidates the attestation loudly.
    Provenance fields the reviewer does not judge (source, funder, amount,
    year, region, llm_category, sampling) are deliberately excluded."""
    core = json.dumps(
        [rec.get(k) for k in
         ("record_id", "title", "quote", "label", "reason",
          "matched_keywords", "anchor_terms", "confidence", "url")],
        ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(core.encode("utf-8")).hexdigest()[:16]


def mark_stale(attestations, by_id):
    """Flag attestations (verdicts or judgments) whose record changed since
    they were made, or vanished from the sample. Served only, never written
    back."""
    for rid, att in attestations.items():
        if isinstance(att, dict):
            rec = by_id.get(rid)
            att["stale"] = (rec is None
                            or att.get("record_fingerprint")
                            != record_fingerprint(rec))


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, RecursionError):
        # RecursionError: a maliciously deep JSON document must read as
        # unreadable, not crash the server mid-request
        return default


def atomic_write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def judge_flagged(rec, judgments):
    """True when any AI judge said fail/uncertain, the judgment is stale, or
    a dimension is missing - the records a human should look at first."""
    j = judgments.get(rec["record_id"])
    if not isinstance(j, dict) or not isinstance(j.get("judges"), dict):
        return True
    if j.get("stale"):
        return True
    return any((j["judges"].get(dim) or {}).get("verdict") != "pass"
               for dim in JUDGE_DIMENSIONS)


def wilson_interval(k, n, z=1.96):
    """95% Wilson score interval for k successes in n trials."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(max(0.0, centre - half), 4),
            round(min(1.0, centre + half), 4)]


def effective_verdicts(verdicts_by_reviewer):
    """record_id -> {reviewer: verdict} keeping only well-formed, current
    verdicts. Malformed or stale entries count as unreviewed. Requires the
    caller to have run mark_stale first: an entry without an explicit
    `stale: False` is excluded, so forgetting the staleness pass yields a
    loud zero instead of silently-fresh verdicts."""
    per_record = {}
    for reviewer, verdicts in sorted(verdicts_by_reviewer.items()):
        for rid, v in verdicts.items():
            if (isinstance(v, dict) and v.get("stale") is False
                    and v.get("verdict") in ("agree", "disagree")
                    and v.get("label") in LABELS):
                per_record.setdefault(rid, {})[reviewer] = v
    return per_record


def summarize(records, verdicts_by_reviewer, judgments):
    """The gate metrics. A record reviewed by several reviewers counts
    once; conflicting reviewer labels become an inter-reviewer disagreement
    and are excluded from the agreement numbers. Agreement is reported
    combined and per tuning/holdout split (the overfitting guard: fixes may
    only be motivated by tuning-half findings)."""
    per_record = effective_verdicts(verdicts_by_reviewer)
    by_id = {r["record_id"]: r for r in records}
    reviewed = [rid for rid in per_record if rid in by_id]
    conflicts = sorted(
        rid for rid in reviewed
        if len({v["label"] for v in per_record[rid].values()}) > 1)
    consensus = [rid for rid in reviewed if rid not in conflicts]
    # agreement is label equality in the four-label space, not the stored
    # verdict word: a hand-edited "agree" carrying a different label counts
    # as the disagreement it actually expresses
    agreed = [rid for rid in consensus
              if next(iter(per_record[rid].values()))["label"]
              == pipeline_label(by_id[rid])]
    ambiguous = [rid for rid in consensus
                 if pipeline_label(by_id[rid]) == "ambiguous"]
    ambiguous_confirmed = [rid for rid in ambiguous if rid in agreed]
    n = len(consensus)

    def split_of(rid):
        return (by_id[rid].get("sampling") or {}).get("split")

    splits = {}
    for split in ("tuning", "holdout"):
        s_total = [r for r in records
                   if (r.get("sampling") or {}).get("split") == split]
        s_consensus = [rid for rid in consensus if split_of(rid) == split]
        s_agreed = [rid for rid in agreed if split_of(rid) == split]
        sn = len(s_consensus)
        splits[split] = {
            "total": len(s_total),
            "reviewed": sum(1 for rid in reviewed if split_of(rid) == split),
            "consensus_reviewed": sn,
            "agreed": len(s_agreed),
            "agreement": round(len(s_agreed) / sn, 4) if sn else None,
            "agreement_ci95": wilson_interval(len(s_agreed), sn),
        }
    return {
        "total": len(records),
        "reviewed": len(reviewed),
        "consensus_reviewed": n,
        "agreed": len(agreed),
        "agreement": round(len(agreed) / n, 4) if n else None,
        "agreement_ci95": wilson_interval(len(agreed), n),
        "target": 0.85,
        "splits": splits,
        "inter_reviewer_disagreements": [
            {"record_id": rid,
             "labels": {rev: v["label"]
                        for rev, v in sorted(per_record[rid].items())}}
            for rid in conflicts],
        "ambiguous_reviewed": len(ambiguous),
        "ambiguous_confirmed": len(ambiguous_confirmed),
        "low_confidence": sum(
            1 for rid in reviewed
            for v in per_record[rid].values() if v.get("low_confidence")),
        "judge_flagged": sum(judge_flagged(r, judgments) for r in records),
    }


def load_imports(by_id):
    """Ingest Longview instrument export files (Jan's four-label labelling
    tool, PR #16) from eval-classifier/imports/*.json as extra reviewers.

    Decisions are matched to our sample by record_id; ids outside the sample
    are counted and skipped (the instrument packet is a different sample of
    the same corpus). Imported decisions attested to the instrument's own
    text of the record, not to this gate's card, so they carry
    imported: True and skip our fingerprint check - documented limitation,
    surfaced in the admin view. Returns (verdicts_by_reviewer, notes,
    errors)."""
    imported, notes, errors = {}, [], []
    try:
        entries = sorted(os.listdir(IMPORTS_DIR))
    except OSError:
        return {}, [], []
    for entry in entries:
        if not entry.endswith(".json"):
            errors.append(f"imports/{entry} is not a .json export; ignored")
            continue
        path = os.path.join(IMPORTS_DIR, entry)
        # regular files under a sane size only: a FIFO would block this
        # single-threaded server forever, a huge file would exhaust memory
        try:
            if not os.path.isfile(path):
                errors.append(f"imports/{entry} is not a regular file; "
                              "ignored")
                continue
            if os.path.getsize(path) > 10_000_000:
                errors.append(f"imports/{entry} exceeds 10 MB; ignored")
                continue
        except OSError:
            errors.append(f"imports/{entry} is unreadable")
            continue
        body = load_json(path, None)
        if not isinstance(body, dict):
            errors.append(f"imports/{entry} is unreadable")
            continue
        if body.get("format") != IMPORT_FORMAT:
            errors.append(f"imports/{entry}: not a {IMPORT_FORMAT} export")
            continue
        if body.get("taxonomy_version") != IMPORT_TAXONOMY_VERSION:
            errors.append(
                f"imports/{entry}: taxonomy_version "
                f"{body.get('taxonomy_version')!r} is not "
                f"{IMPORT_TAXONOMY_VERSION!r}; same label strings under a "
                "different taxonomy are not comparable evidence")
            continue
        if (body.get("label_origin") != "human"
                or body.get("human_attested") is not True
                or body.get("simulation") is True):
            errors.append(f"imports/{entry}: not an attested human export "
                          "(model/simulation files are not human labels)")
            continue
        reviewer = body.get("reviewer")
        if (not isinstance(reviewer, str)
                or not IMPORT_REVIEWER_RE.fullmatch(reviewer)):
            errors.append(f"imports/{entry}: invalid reviewer code")
            continue
        key = f"import:{reviewer}"  # ':' cannot appear in local slugs
        if key in imported:
            errors.append(f"imports/{entry}: duplicate reviewer "
                          f"{reviewer!r}; keep one export file per reviewer")
            continue
        decisions = body.get("decisions")
        if not isinstance(decisions, list) or not decisions:
            errors.append(f"imports/{entry}: no decisions")
            continue
        verdicts, skipped, bad = {}, 0, 0
        for d in decisions:
            if (not isinstance(d, dict)
                    or not isinstance(d.get("record_id"), str)
                    or d.get("label") not in LABELS
                    or not isinstance(d.get("low_confidence"), bool)):
                bad += 1
                continue
            rec = by_id.get(d["record_id"])
            if rec is None:
                skipped += 1  # not in our sample: expected, not an error
                continue
            if d["record_id"] in verdicts:
                bad += 1
                continue
            verdicts[d["record_id"]] = {
                "record_id": d["record_id"],
                "verdict": ("agree" if d["label"] == pipeline_label(rec)
                            else "disagree"),
                "label": d["label"],
                "low_confidence": d["low_confidence"],
                "note": str(d.get("reason") or ""),
                "reviewed_at": str(d.get("reviewed_at") or ""),
                "reviewer": key,
                "imported": True,
                # attests to the instrument's text version, not our card
                "stale": False,
            }
        if bad:
            errors.append(f"imports/{entry}: {bad} malformed decision(s) "
                          "ignored")
        if verdicts:
            imported[key] = verdicts
            notes.append(f"imports/{entry}: reviewer {reviewer!r}, "
                         f"{len(verdicts)} decision(s) on this sample, "
                         f"{skipped} outside it")
        else:
            notes.append(f"imports/{entry}: reviewer {reviewer!r} has no "
                         f"decisions on this sample ({skipped} outside it)")
    return imported, notes, errors


def admin_summary(records, verdicts_by_reviewer, judgments, meta):
    """Everything the admin panel shows: per-item label counts,
    labeller-vs-labeller pairwise agreement, per-reviewer pipeline
    agreement, disagreements ranked first, plus the gate summary."""
    per_record = effective_verdicts(verdicts_by_reviewer)
    by_id = {r["record_id"]: r for r in records}
    reviewers = sorted(
        {rev for vs in per_record.values() for rev in vs})
    pairs = []
    for i, a in enumerate(reviewers):
        for b in reviewers[i + 1:]:
            overlap = [rid for rid, vs in per_record.items()
                       if a in vs and b in vs and rid in by_id]
            agree = sum(1 for rid in overlap
                        if per_record[rid][a]["label"]
                        == per_record[rid][b]["label"])
            n = len(overlap)
            pairs.append({
                "a": a, "b": b, "n": n, "agree": agree,
                "rate": round(agree / n, 4) if n else None,
                "ci95": wilson_interval(agree, n),
            })
    per_reviewer = []
    for rev in reviewers:
        mine = [(rid, vs[rev]) for rid, vs in per_record.items()
                if rev in vs and rid in by_id]
        agree = sum(1 for rid, v in mine
                    if v["label"] == pipeline_label(by_id[rid]))
        n = len(mine)
        per_reviewer.append({
            "reviewer": rev,
            "imported": any(v.get("imported") for _, v in mine),
            "n": n, "agree": agree,
            "rate": round(agree / n, 4) if n else None,
            "ci95": wilson_interval(agree, n),
            "low_confidence": sum(1 for _, v in mine
                                  if v.get("low_confidence")),
        })
    items = []
    for rec in records:
        rid = rec["record_id"]
        decisions = [
            {"reviewer": rev, "label": v["label"],
             "low_confidence": bool(v.get("low_confidence")),
             "verdict": v.get("verdict"), "note": v.get("note", ""),
             "imported": bool(v.get("imported"))}
            for rev, v in sorted(per_record.get(rid, {}).items())]
        counts = {label: sum(1 for d in decisions if d["label"] == label)
                  for label in LABELS}
        mapped = pipeline_label(rec)
        items.append({
            "record_id": rid,
            "title": rec.get("title"),
            "source": rec.get("source"),
            "url": rec.get("url"),
            "split": (rec.get("sampling") or {}).get("split"),
            "raw_label": rec.get("label"),
            "pipeline_label": mapped,
            "counts": counts,
            "low_confidence": sum(1 for d in decisions
                                  if d["low_confidence"]),
            "decisions": decisions,
            "human_disagreement":
                len({d["label"] for d in decisions}) > 1,
            # mapped is None for a corrupt raw label, so every decision
            # counts as a pipeline disagreement - deliberately pushing the
            # corrupt record to the top of the queue
            "pipeline_disagreements":
                sum(1 for d in decisions if d["label"] != mapped),
        })
    # disagreements ranked to the top: human-vs-human first, then
    # pipeline-vs-human, then low-confidence, then reviewed before
    # unreviewed, stable by id
    items.sort(key=lambda i: (
        -int(i["human_disagreement"]), -i["pipeline_disagreements"],
        -i["low_confidence"], -sum(i["counts"].values()), i["record_id"]))
    return {
        "summary": summarize(records, verdicts_by_reviewer, judgments),
        "labels": LABELS,
        "mapping": FOUR_LABEL_MAP,
        "reviewers": per_reviewer,
        "pairwise": pairs,
        "items": items,
        "meta": meta,
        "import_notes": meta.get("import_notes", []),
    }


def formula_like(text):
    """True when a spreadsheet would evaluate the cell as a formula. The
    single source of truth for the injection guard - export_benchmark.py
    reuses it, so the two CSV writers cannot drift apart. A leading BOM is
    stripped before BOTH checks so it cannot smuggle a control character
    past the second one."""
    bare = text.lstrip('\ufeff')
    return bool(re.match(r"^\s*[=+@-]", bare)
                or re.match(r"^[\t\r\n]", bare))


def csv_cell(value):
    """CSV field with formula-injection guard (same rule as the Longview
    instrument's csvCell)."""
    text = "" if value is None else str(value)
    if formula_like(text):
        text = "'" + text
    return '"' + text.replace('"', '""') + '"'


def export_csv(records, verdicts_by_reviewer):
    """One row per (record, human decision); unreviewed records get one row
    with empty decision fields so the export covers the whole sample."""
    per_record = effective_verdicts(verdicts_by_reviewer)
    header = ["record_id", "source", "title", "url", "split",
              "pipeline_raw_label", "pipeline_label", "reviewer",
              "reviewer_origin", "human_label", "low_confidence", "note",
              "reviewed_at", "agrees_with_pipeline", "human_label_count",
              "human_disagreement"]
    rows = [header]
    for rec in records:
        rid = rec["record_id"]
        mapped = pipeline_label(rec)
        decisions = sorted(per_record.get(rid, {}).items())
        base = [rid, rec.get("source"), rec.get("title"), rec.get("url"),
                (rec.get("sampling") or {}).get("split"),
                rec.get("label"), mapped]
        n = len(decisions)
        disagreement = len({v["label"] for _, v in decisions}) > 1
        if not decisions:
            rows.append(base + [""] * 7 + [0, ""])
            continue
        for rev, v in decisions:
            rows.append(base + [
                rev, "instrument-import" if v.get("imported") else "gate",
                v["label"], bool(v.get("low_confidence")),
                v.get("note", ""), v.get("reviewed_at", ""),
                v["label"] == mapped, n, disagreement])
    return ("\r\n".join(",".join(csv_cell(c) for c in row) for row in rows)
            + "\r\n")


def list_verdict_files():
    """(files, rejected): valid (slug, path) pairs plus the basenames of
    files in the verdicts directory that look like verdicts but carry an
    unusable name. Rejected names must be surfaced, never silently
    dropped - a whole reviewer's evidence can hide behind a stray capital
    letter or backup suffix."""
    files, rejected = [], []
    try:
        entries = sorted(os.listdir(VERDICTS_DIR))
    except OSError:
        return [], []
    for entry in entries:
        if not entry.endswith(".verdicts.json"):
            rejected.append(entry)
            continue
        name = entry[:-len(".verdicts.json")]
        if REVIEWER_SLUG_RE.fullmatch(name):
            files.append((name, os.path.join(VERDICTS_DIR, entry)))
        else:
            rejected.append(entry)
    return files, rejected


def load_state():
    """Sample records, per-reviewer verdicts and judgments with staleness
    marked. Returns (records, verdicts_by_reviewer, judgments, meta,
    errors)."""
    errors = []
    sample = load_json(SAMPLE_PATH, None)
    records = sample.get("records") if isinstance(sample, dict) else None
    if not isinstance(records, list):
        errors.append(f"sample file {SAMPLE_PATH} is unreadable "
                      "(run eval-classifier/sample.py)")
        sample, records = {}, []
    well_formed = [r for r in records
                   if isinstance(r, dict)
                   and isinstance(r.get("record_id"), str)]
    if len(well_formed) != len(records):
        # a malformed record must surface loudly, not crash the metrics or
        # silently shrink the sample
        errors.append(f"sample file has {len(records) - len(well_formed)} "
                      "malformed record(s); fix sample.json")
    records = well_formed
    by_id = {r["record_id"]: r for r in records}

    verdicts_by_reviewer = {}
    files, rejected = list_verdict_files()
    for entry in rejected:
        errors.append(f"file {entry!r} in verdicts/ is not a valid "
                      "<reviewer-slug>.verdicts.json name and is IGNORED - "
                      "rename it or its verdicts will not count")
    for reviewer, path in files:
        verdicts = load_json(path, None)
        if not isinstance(verdicts, dict):
            errors.append(f"verdicts file {os.path.basename(path)} is "
                          "unreadable")
            continue
        mark_stale(verdicts, by_id)
        # a verdict in a label space this gate no longer speaks (the
        # pre-retarget five categories) must surface loudly: it silently
        # counts as unreviewed otherwise, which looks like lost evidence
        legacy = sum(
            1 for v in verdicts.values()
            if isinstance(v, dict) and v.get("verdict") in
            ("agree", "disagree") and v.get("label") not in LABELS)
        if legacy:
            errors.append(
                f"{os.path.basename(path)}: {legacy} verdict(s) carry "
                "labels outside the four-label taxonomy and are IGNORED - "
                "re-review those records")
        verdicts_by_reviewer[reviewer] = verdicts

    imported, import_notes, import_errors = load_imports(by_id)
    errors.extend(import_errors)
    verdicts_by_reviewer.update(imported)

    judgments = (load_json(JUDGMENTS_PATH, None)
                 if os.path.exists(JUDGMENTS_PATH) else {})
    if not isinstance(judgments, dict):
        errors.append("judgments.json is unreadable")
        judgments = {}
    mark_stale(judgments, by_id)
    meta = dict(sample.get("meta", {})) if isinstance(sample, dict) else {}
    meta["import_notes"] = import_notes
    return records, verdicts_by_reviewer, judgments, meta, errors


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def loopback_host(self):
        """True when the request's Host header names loopback. The review
        evidence must not be readable through DNS rebinding (an attacker
        domain resolving to 127.0.0.1), so every /api/ endpoint - reads
        included - checks this, not only the write path."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in ("127.0.0.1", "localhost", "[::1]")

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/") and not self.loopback_host():
            return self.send_json(
                {"error": "API served to localhost only"}, 403)
        if path == "/api/admin":
            records, verdicts_by_reviewer, judgments, meta, errors = \
                load_state()
            payload = admin_summary(records, verdicts_by_reviewer,
                                    judgments, meta)
            if errors:
                payload["error"] = "; ".join(errors)
            return self.send_json(payload)
        if path == "/api/export.csv":
            records, verdicts_by_reviewer, _j, _m, errors = load_state()
            if errors:
                # a partial evidence export would look unanimous where a
                # rejected reviewer file actually holds a disagreement
                return self.send_json(
                    {"error": "export refused, evidence incomplete: "
                              + "; ".join(errors)}, 500)
            body = export_csv(records, verdicts_by_reviewer) \
                .encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition",
                             'attachment; filename="eval-gate-export.csv"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return None
        if path == "/api/data":
            records, verdicts_by_reviewer, judgments, meta, errors = \
                load_state()
            # Serve each record's fingerprint; the client echoes it back on
            # /api/verdict so a verdict always attests to the version the
            # reviewer actually saw, never to a silently regenerated record.
            for rec in records:
                rec["fingerprint"] = record_fingerprint(rec)
            payload = {
                "records": records,
                "verdicts": verdicts_by_reviewer,
                "judgments": judgments,
                "meta": meta,
                "reviewer": REVIEWER,
                "summary": summarize(records, verdicts_by_reviewer,
                                     judgments),
                "labels": LABELS,
                "mapping": FOUR_LABEL_MAP,
            }
            if errors:
                payload["error"] = "; ".join(errors)
            return self.send_json(payload)
        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/verdict":
            return self.send_json({"error": "not found"}, 404)
        # Verdicts are evidence: refuse writes from other origins (a hostile
        # web page in another tab can POST to localhost without a CORS
        # preflight). Pinning Host to loopback names also closes the DNS
        # rebinding variant, where an attacker domain resolves to 127.0.0.1
        # and Origin "matches" its own Host header.
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        if host not in ("127.0.0.1", "localhost", "[::1]"):
            return self.send_json(
                {"error": "writes accepted from localhost only"}, 403)
        origin = self.headers.get("Origin")
        if (origin is not None
                and urlparse(origin).netloc != self.headers.get("Host", "")):
            return self.send_json(
                {"error": "cross-origin writes not allowed"}, 403)
        if REVIEWER is None:
            return self.send_json(
                {"error": "no reviewer identity; restart the server with "
                          "--reviewer <name>"}, 500)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 1_000_000:
                return self.send_json({"error": "bad Content-Length"}, 400)
            payload = json.loads(self.rfile.read(length))
        except ValueError:
            return self.send_json({"error": "invalid JSON body"}, 400)
        if not isinstance(payload, dict):
            return self.send_json({"error": "body must be a JSON object"}, 400)

        records, verdicts_by_reviewer, judgments, _meta, errors = load_state()
        if any("sample file" in e for e in errors):
            return self.send_json({"error": errors[0]}, 500)
        record_id = payload.get("record_id")
        rec = next((r for r in records
                    if isinstance(r, dict) and r.get("record_id") == record_id),
                   None)
        if rec is None:
            return self.send_json(
                {"error": f"unknown record {record_id!r}"}, 400)

        if "verdict" not in payload:
            # a missing field is a client bug, not an undo request
            return self.send_json(
                {"error": "verdict must be present: agree, disagree or "
                          "null (null = undo)"}, 400)
        verdict = payload["verdict"]
        current_fp = record_fingerprint(rec)
        if verdict is not None and payload.get("record_fingerprint") != current_fp:
            # the reviewer's card shows an older version of the record;
            # recording a verdict against content they never saw would
            # fabricate evidence
            return self.send_json(
                {"error": "record changed since the page loaded - reload "
                          "and re-review"}, 409)
        mapped = pipeline_label(rec)
        if verdict is None:
            # explicit undo: drop the local reviewer's verdict
            saved = None
        elif verdict == "agree":
            if mapped is None:
                # a corrupt sample must not become confirmed evidence
                return self.send_json(
                    {"error": f"sample record carries unknown label "
                              f"{rec.get('label')!r}; fix sample.json"}, 500)
            saved = {"verdict": "agree", "label": mapped}
        elif verdict == "disagree":
            if mapped is None:
                # same guard as agree: a corrupt sample must not accept
                # evidence in either direction
                return self.send_json(
                    {"error": f"sample record carries unknown label "
                              f"{rec.get('label')!r}; fix sample.json"}, 500)
            label = payload.get("correct_label")
            if label not in LABELS:
                return self.send_json(
                    {"error": f"correct_label must be one of {LABELS}"}, 400)
            if label == mapped:
                return self.send_json(
                    {"error": "disagree needs a label different from the "
                              "pipeline's; use agree instead"}, 400)
            saved = {"verdict": "disagree", "label": label}
        else:
            return self.send_json(
                {"error": "verdict must be agree, disagree or null"}, 400)

        low_confidence = payload.get("low_confidence", False)
        if saved is not None and not isinstance(low_confidence, bool):
            # a truthy string like "false" must not silently become True
            return self.send_json(
                {"error": "low_confidence must be a boolean"}, 400)
        if saved is not None:
            saved.update({
                "record_id": record_id,
                "record_fingerprint": current_fp,
                "reviewer": REVIEWER,
                # low confidence is independent of the chosen label:
                # "borderline case" stays distinct from "couldn't tell"
                "low_confidence": low_confidence,
                "note": str(payload.get("note") or ""),
                "reviewed_at": str(payload.get("reviewed_at") or ""),
            })

        # This server writes only the LOCAL reviewer's file, so parallel
        # review sessions on different machines never collide; merge happens
        # at read time. Safe read-modify-write only because HTTPServer
        # serializes requests.
        verdicts_path = os.path.join(VERDICTS_DIR,
                                     f"{REVIEWER}.verdicts.json")
        if os.path.exists(verdicts_path):
            stored = load_json(verdicts_path, None)
            if not isinstance(stored, dict):
                # Verdicts are committed review evidence: never let an
                # unreadable file silently degrade to {} and get overwritten.
                return self.send_json(
                    {"error": f"{os.path.basename(verdicts_path)} is "
                              "unreadable; fix it by hand before saving "
                              "new verdicts"}, 500)
        else:
            stored = {}
        if saved is None:
            stored.pop(record_id, None)
        else:
            stored[record_id] = saved
        atomic_write_json(verdicts_path, stored)
        mark_stale(stored, {r["record_id"]: r for r in records})
        verdicts_by_reviewer[REVIEWER] = stored
        return self.send_json({
            "ok": True,
            "verdict": stored.get(record_id),
            "summary": summarize(records, verdicts_by_reviewer, judgments),
        })

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet during review sessions


def main():
    global REVIEWER
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--reviewer",
                        help="reviewer name for the local verdict file "
                             "(default: git config user.name)")
    parser.add_argument("--summary", action="store_true",
                        help="print gate metrics and exit: 0 = on target "
                             "or nothing reviewed yet, 1 = agreement below "
                             "target, 2 = evidence files unreadable")
    args = parser.parse_args()
    if args.summary:
        records, verdicts_by_reviewer, judgments, _meta, errors = load_state()
        s = summarize(records, verdicts_by_reviewer, judgments)
        for e in errors:
            print(f"error: {e}")
        # provenance: imported instrument decisions are NOT fingerprinted
        # against this gate's cards; they must never move the headline
        # number invisibly
        imported = {k: v for k, v in verdicts_by_reviewer.items()
                    if k.startswith("import:")}
        if imported:
            print(f"instrument imports: {sum(len(v) for v in imported.values())} "
                  f"decision(s) from {len(imported)} imported reviewer(s) "
                  "INCLUDED in these numbers (not gate-fingerprinted)")
        print(f"records:            {s['total']} "
              f"({s['judge_flagged']} judge-flagged)")
        print(f"reviewed:           {s['reviewed']} by "
              f"{len(verdicts_by_reviewer)} reviewer(s)")
        print(f"agreed:             {s['agreed']}")
        def fmt(block):
            if block["agreement"] is None:
                return f"- (0/{block['total']} reviewed)"
            lo, hi = block["agreement_ci95"]
            return (f"{100 * block['agreement']:.1f}% "
                    f"(95% CI {100 * lo:.1f}-{100 * hi:.1f}%, "
                    f"n={block['consensus_reviewed']})")
        if s["agreement"] is None:
            print("agreement:          - (target >= 85%)")
        else:
            print(f"agreement:          {fmt(s)} target >= 85%")
        for split in ("tuning", "holdout"):
            print(f"  {split:17s} {fmt(s['splits'][split])}")
        print(f"reviewer conflicts: "
              f"{len(s['inter_reviewer_disagreements'])}")
        print(f"ambiguous flags:    {s['ambiguous_confirmed']}/"
              f"{s['ambiguous_reviewed']} confirmed")
        print(f"low confidence:     {s['low_confidence']} verdict(s)")
        if errors:
            return 2
        if s["agreement"] is not None and s["agreement"] < s["target"]:
            return 1
        return 0

    REVIEWER = detect_reviewer(args.reviewer)
    if REVIEWER is None:
        parser.error("could not derive a reviewer name from git config "
                     "user.name or $USER; pass --reviewer <name>")
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Reviewing classifier labels at http://localhost:{args.port} "
          f"as reviewer {REVIEWER!r}")
    print(f"Verdicts persist to {VERDICTS_DIR}/{REVIEWER}.verdicts.json")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
