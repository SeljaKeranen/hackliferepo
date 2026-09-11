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
            return self.send_json({"country": self.country, "findings": findings})
        if path == "/api/verdicts":
            return self.send_json(load_json(self.verdicts_path, {}))
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
            "reviewer": str(payload.get("reviewer") or ""),
            "note": str(payload.get("note") or ""),
            "reviewed_at": str(payload.get("reviewed_at") or ""),
        }
        # Safe read-modify-write only because HTTPServer serializes requests;
        # switching to ThreadingHTTPServer would need a lock around this block.
        verdicts = load_json(self.verdicts_path, {})
        verdicts[finding_id] = verdict
        atomic_write_json(self.verdicts_path, verdicts)
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
