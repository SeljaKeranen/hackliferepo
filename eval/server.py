#!/usr/bin/env python3
"""Localhost human-eval server for longevity politics findings.

Run: python3 eval/server.py [--port 8000]
Then open http://localhost:8000

Stdlib only. Serves the review UI and every findings file under
eval/findings/*.json (one country per file); reads/writes verdicts to
eval/verdicts/<country>.verdicts.json. AI judge panel pre-marks from
eval/judgments/<country>.judgments.json are served read-only alongside.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(EVAL_DIR, "static")
FINDINGS_DIR = os.path.join(EVAL_DIR, "findings")
VERDICTS_DIR = os.path.join(EVAL_DIR, "verdicts")
JUDGMENTS_DIR = os.path.join(EVAL_DIR, "judgments")

CHECKS = ("source_resolves", "date_correct", "classification_correct", "claim_supported")
# AI judge panel dimensions; committed pre-marks the server serves read-only.
# The human's four-check verdict stays the accuracy metric.
JUDGE_DIMENSIONS = ("credibility", "recency", "classification")
JUDGE_VERDICTS = ("pass", "fail", "uncertain")
# Country slugs are findings FILENAMES ("sweden", "us"), not the two-letter
# ISO codes inside the records ("SE", "US"); keep them boring so they can't
# traverse paths.
COUNTRY_SLUG_RE = re.compile(r"[a-z][a-z0-9_-]*")


def list_countries():
    # Filter by the slug pattern so the read path serves exactly the names
    # the write path in do_POST will accept.
    return sorted(
        name for p in glob.glob(os.path.join(FINDINGS_DIR, "*.json"))
        if COUNTRY_SLUG_RE.fullmatch(name := os.path.splitext(os.path.basename(p))[0])
    )


def finding_fingerprint(rec):
    """Hash of the content a reviewer attests to. Stored with each verdict so
    a later edit to the finding invalidates the verdict loudly —
    eval/test_findings.py cross-checks it against the current findings file."""
    core = json.dumps(
        [rec.get(k) for k in
         ("claim", "search_note", "source_url", "source_date", "classification",
          "source_note")],
        ensure_ascii=False)
    return hashlib.sha256(core.encode("utf-8")).hexdigest()[:16]


def mark_stale(attestations, by_id):
    """Flag attestations (verdicts or judgments) whose finding changed since
    they were made, or vanished, so the UI can demand a re-review instead of
    showing stale green checkmarks. Served only, never written back."""
    for fid, att in attestations.items():
        if isinstance(att, dict):
            rec = by_id.get(fid)
            att["stale"] = (rec is None
                            or att.get("finding_fingerprint")
                            != finding_fingerprint(rec))


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
        path = urlparse(self.path).path
        if path == "/api/data":
            countries = {}
            for name in list_countries():
                findings = load_json(os.path.join(FINDINGS_DIR, f"{name}.json"), None)
                verdicts_path = os.path.join(VERDICTS_DIR, f"{name}.verdicts.json")
                verdicts = (load_json(verdicts_path, None)
                            if os.path.exists(verdicts_path) else {})
                judgments_path = os.path.join(JUDGMENTS_DIR, f"{name}.judgments.json")
                judgments = (load_json(judgments_path, None)
                             if os.path.exists(judgments_path) else {})
                # Don't let a corrupted file masquerade as a clean "0 findings"
                # or "not reviewed" country — the UI shows this error instead.
                errors = []
                if not isinstance(findings, list):
                    errors.append(f"findings file {name}.json is unreadable")
                    findings = []
                if not isinstance(verdicts, dict):
                    errors.append(f"verdicts file {name}.verdicts.json is unreadable")
                    verdicts = {}
                if not isinstance(judgments, dict):
                    errors.append(f"judgments file {name}.judgments.json is unreadable")
                    judgments = {}
                by_id = {r.get("id"): r for r in findings if isinstance(r, dict)}
                mark_stale(verdicts, by_id)
                mark_stale(judgments, by_id)
                entry = {"findings": findings, "verdicts": verdicts,
                         "judgments": judgments}
                if errors:
                    entry["error"] = "; ".join(errors)
                countries[name] = entry
            if not countries:
                return self.send_json(
                    {"error": f"no findings files in {FINDINGS_DIR}"}, 404)
            return self.send_json({"countries": countries})
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/verdict":
            return self.send_json({"error": "not found"}, 404)
        # Verdicts are evidence: refuse writes from other origins (a hostile web
        # page in another tab can POST to localhost without a CORS preflight).
        origin = self.headers.get("Origin")
        if origin is not None and urlparse(origin).netloc != self.headers.get("Host", ""):
            return self.send_json({"error": "cross-origin writes not allowed"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 1_000_000:
                return self.send_json({"error": "bad Content-Length"}, 400)
            payload = json.loads(self.rfile.read(length))
        except ValueError:
            return self.send_json({"error": "invalid JSON body"}, 400)
        if not isinstance(payload, dict):
            return self.send_json({"error": "body must be a JSON object"}, 400)

        country = payload.get("country")
        if (not isinstance(country, str) or not COUNTRY_SLUG_RE.fullmatch(country)
                or country not in list_countries()):
            return self.send_json({"error": f"unknown country {country!r}"}, 400)
        finding_id = payload.get("finding_id")
        checks = payload.get("checks")
        if not isinstance(finding_id, str) or not isinstance(checks, dict):
            return self.send_json({"error": "need finding_id (str) and checks (object)"}, 400)
        findings = load_json(os.path.join(FINDINGS_DIR, f"{country}.json"), None)
        if not isinstance(findings, list):
            return self.send_json(
                {"error": f"findings file for {country} is unreadable"}, 500)
        rec = next((r for r in findings
                    if isinstance(r, dict) and r.get("id") == finding_id), None)
        if rec is None:
            return self.send_json(
                {"error": f"unknown finding {finding_id!r} in {country}"}, 400)
        clean_checks = {}
        for key in CHECKS:
            val = checks.get(key)
            if not (val is True or val is False or val is None):
                return self.send_json({"error": f"check {key} must be true/false/null"}, 400)
            clean_checks[key] = val

        reviewed = all(clean_checks[k] is not None for k in CHECKS)
        verdict = {
            "finding_id": finding_id,
            "finding_fingerprint": finding_fingerprint(rec),
            "checks": clean_checks,
            "reviewed": reviewed,
            "correct": reviewed and all(clean_checks[k] is True for k in CHECKS),
            "reviewer": str(payload.get("reviewer") or ""),
            "note": str(payload.get("note") or ""),
            "reviewed_at": str(payload.get("reviewed_at") or ""),
        }
        # Safe read-modify-write only because HTTPServer serializes requests;
        # switching to ThreadingHTTPServer would need a lock around this block.
        verdicts_path = os.path.join(VERDICTS_DIR, f"{country}.verdicts.json")
        if os.path.exists(verdicts_path):
            verdicts = load_json(verdicts_path, None)
            if not isinstance(verdicts, dict):
                # Verdicts are committed review evidence: never let an
                # unreadable file silently degrade to {} and get overwritten.
                return self.send_json(
                    {"error": f"verdicts file for {country} is unreadable; "
                              "fix it by hand before saving new verdicts"}, 500)
        else:
            verdicts = {}
        verdicts[finding_id] = verdict
        atomic_write_json(verdicts_path, verdicts)
        return self.send_json({"ok": True, "verdict": verdict})

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet during review sessions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    countries = list_countries()
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Reviewing findings ({', '.join(countries) or 'none found'}) "
          f"at http://localhost:{args.port}")
    print(f"Verdicts persist to {VERDICTS_DIR}/<country>.verdicts.json")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
