#!/usr/bin/env python3
"""Localhost human-eval server for the grant-classifier evaluation gate.

Run: python3 eval-classifier/server.py [--port 8001] [--reviewer NAME]
Then open http://localhost:8001

Stdlib only. Serves the review UI over eval-classifier/sample.json (the
stratified sample of ratio-pipeline labels), AI judge pre-marks from
eval-classifier/judgments.json (read-only), and reads/writes human verdicts
to eval-classifier/verdicts/<reviewer>.verdicts.json.

The measured deliverable is the pipeline's agreement with human judgment,
with `ambiguous` flagged honestly rather than forced; the challenge bar is
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

# every label a human can assign; ambiguous and not_relevant are first-class
LABELS = ("fundamental_aging", "intervention", "age_related_disease", "care",
          "social_population_aging", "ambiguous", "not_relevant")
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
    except (OSError, ValueError):
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
    verdicts. Malformed or stale entries count as unreviewed."""
    per_record = {}
    for reviewer, verdicts in sorted(verdicts_by_reviewer.items()):
        for rid, v in verdicts.items():
            if (isinstance(v, dict) and not v.get("stale")
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
    agreed = [rid for rid in consensus
              if next(iter(per_record[rid].values()))["verdict"] == "agree"]
    ambiguous = [rid for rid in consensus
                 if by_id[rid].get("label") == "ambiguous"]
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
        "judge_flagged": sum(judge_flagged(r, judgments) for r in records),
    }


def list_verdict_files():
    return sorted(
        (name, p) for p in glob.glob(
            os.path.join(VERDICTS_DIR, "*.verdicts.json"))
        if REVIEWER_SLUG_RE.fullmatch(
            name := os.path.basename(p)[:-len(".verdicts.json")]))


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
    by_id = {r.get("record_id"): r for r in records if isinstance(r, dict)}

    verdicts_by_reviewer = {}
    for reviewer, path in list_verdict_files():
        verdicts = load_json(path, None)
        if not isinstance(verdicts, dict):
            errors.append(f"verdicts file {os.path.basename(path)} is "
                          "unreadable")
            continue
        mark_stale(verdicts, by_id)
        verdicts_by_reviewer[reviewer] = verdicts

    judgments = (load_json(JUDGMENTS_PATH, None)
                 if os.path.exists(JUDGMENTS_PATH) else {})
    if not isinstance(judgments, dict):
        errors.append("judgments.json is unreadable")
        judgments = {}
    mark_stale(judgments, by_id)
    meta = sample.get("meta", {}) if isinstance(sample, dict) else {}
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

    def do_GET(self):
        if urlparse(self.path).path == "/api/data":
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
        # preflight).
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
        if verdict is None:
            # explicit undo: drop the local reviewer's verdict
            saved = None
        elif verdict == "agree":
            if rec.get("label") not in LABELS:
                # a corrupt sample must not become confirmed evidence
                return self.send_json(
                    {"error": f"sample record carries unknown label "
                              f"{rec.get('label')!r}; fix sample.json"}, 500)
            saved = {"verdict": "agree", "label": rec["label"]}
        elif verdict == "disagree":
            label = payload.get("correct_label")
            if label not in LABELS:
                return self.send_json(
                    {"error": f"correct_label must be one of {LABELS}"}, 400)
            if label == rec["label"]:
                return self.send_json(
                    {"error": "disagree needs a label different from the "
                              "pipeline's; use agree instead"}, 400)
            saved = {"verdict": "disagree", "label": label}
        else:
            return self.send_json(
                {"error": "verdict must be agree, disagree or null"}, 400)

        if saved is not None:
            saved.update({
                "record_id": record_id,
                "record_fingerprint": current_fp,
                "reviewer": REVIEWER,
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
