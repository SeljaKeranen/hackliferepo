#!/usr/bin/env python3
"""Localhost human-eval server for longevity politics findings.

Run: python3 eval/server.py [--port 8000] [--country sweden]
Then open http://localhost:8000

Stdlib only. Serves the review UI, the findings file, and reads/writes
verdicts to eval/verdicts/<country>.verdicts.json.
"""
import argparse
import json
import os
import re
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.store import finding_version, connect, digest
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(EVAL_DIR, "static")
FINDINGS_DIR = os.path.join(EVAL_DIR, "findings")
VERDICTS_DIR = os.path.join(EVAL_DIR, "verdicts")

CHECKS = ("source_resolves", "date_correct", "classification_correct", "claim_supported")


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
    country = "sweden"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    @property
    def verdicts_path(self):
        return os.path.join(VERDICTS_DIR, f"{self.country}.verdicts.json")

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/findings":
            findings_path = os.path.join(FINDINGS_DIR, f"{self.country}.json")
            findings = load_json(findings_path, None)
            if findings is None:
                return self.send_json({"error": f"no findings file: {findings_path}"}, 404)
            provenance = load_json(os.path.join(EVAL_DIR, "provenance", self.country + ".json"), {})
            return self.send_json({"country": self.country, "findings": findings, "versions": {f["id"]: finding_version(f, provenance.get(f["id"], {})) for f in findings}})
        if path == "/api/provenance":
            return self.send_json(load_json(os.path.join(EVAL_DIR, "provenance", self.country + ".json"), {}))
        if path == "/api/verdicts":
            verdicts = load_json(self.verdicts_path, {})
            findings = load_json(os.path.join(FINDINGS_DIR, self.country + ".json"), [])
            provenance = load_json(os.path.join(EVAL_DIR, "provenance", self.country + ".json"), {})
            for f in findings:
                v = verdicts.get(f["id"])
                if v and v.get("version_hash") != finding_version(f, provenance.get(f["id"], {})):
                    v["reviewed"] = False
                    v["correct"] = False
                    v["checks"] = {c: None for c in CHECKS}
                    v["stale"] = True
            return self.send_json(verdicts)
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

        finding_id = payload.get("finding_id")
        checks = payload.get("checks")
        if not isinstance(finding_id, str) or not isinstance(checks, dict):
            return self.send_json({"error": "need finding_id (str) and checks (object)"}, 400)
        findings = load_json(os.path.join(FINDINGS_DIR, self.country + ".json"), [])
        finding = next((f for f in findings if f["id"] == finding_id), None)
        if finding is None:
            return self.send_json({"error": "unknown finding id"}, 404)
        provenance = load_json(os.path.join(EVAL_DIR, "provenance", self.country + ".json"), {}).get(finding_id, {})
        version = finding_version(finding, provenance)
        if payload.get("version_hash") != version:
            return self.send_json({"error": "evidence changed; reload before reviewing"}, 409)
        reviewer = payload.get("reviewer")
        if not isinstance(reviewer, str) or not reviewer.strip():
            return self.send_json({"error": "enter the human reviewer's name or initials"}, 400)
        clean_checks = {}
        for key in CHECKS:
            val = checks.get(key)
            if not (val is True or val is False or val is None):
                return self.send_json({"error": f"check {key} must be true/false/null"}, 400)
            clean_checks[key] = val

        reviewed = all(clean_checks[k] is not None for k in CHECKS)
        verdict = {
            "finding_id": finding_id,
            "checks": clean_checks,
            "reviewed": reviewed,
            "correct": reviewed and all(clean_checks[k] is True for k in CHECKS),
            "reviewer": reviewer.strip(),
            "version_hash": version,
            "note": str(payload.get("note") or ""),
            "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        # Safe read-modify-write only because HTTPServer serializes requests;
        # switching to ThreadingHTTPServer would need a lock around this block.
        verdicts = load_json(self.verdicts_path, {})
        verdicts[finding_id] = verdict
        atomic_write_json(self.verdicts_path, verdicts)
        # Append each completed review to preserve the pre-correction benchmark.
        if reviewed:
            history_path = os.path.join(VERDICTS_DIR, self.country + ".history.jsonl")
            with open(history_path, "a", encoding="utf-8") as history:
                history.write(json.dumps(verdict, ensure_ascii=False) + "\n")
            with connect() as db:
                if db.execute("SELECT 1 FROM findings WHERE id=?", (finding_id,)).fetchone():
                    db.execute("INSERT INTO reviews(finding_id,version_hash,reviewer,reviewed_at,checks,correct,note) VALUES(?,?,?,?,?,?,?)", (finding_id,version,reviewer.strip(),verdict["reviewed_at"],json.dumps(clean_checks),int(verdict["correct"]),verdict["note"]))
        return self.send_json({"ok": True, "verdict": verdict})

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet during review sessions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--country", default="sweden")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", args.country):
        parser.error("--country must be a plain lowercase name (it becomes a filename)")
    Handler.country = args.country
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Reviewing {args.country} findings at http://localhost:{args.port}")
    print(f"Verdicts persist to {os.path.join(VERDICTS_DIR, args.country + '.verdicts.json')}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
