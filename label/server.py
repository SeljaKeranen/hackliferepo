#!/usr/bin/env python3
"""Grant labelling server: a blind tool for researchers, and a dashboard for
whoever is running the study.

Run:
    python3 -m label.sample --batch batch_001     # build a batch first
    python3 label/server.py                        # http://localhost:8002

Each researcher gets their own link:
    http://localhost:8002/?batch=batch_001&who=r-lindqvist
The dashboard lives at /admin?batch=batch_001

BLIND BY CONSTRUCTION. /api/records strips the `_hidden` block before
serving, so the classifier label, the expert label and the sampling stratum
cannot reach the labelling page even if its JavaScript asked for them. The
independence of the human judgments is the whole value of the study, and it
is enforced here rather than by the page choosing not to render something.

IDENTITY, NOT AUTHENTICATION. `who` attributes a judgment to a person; it
does not authenticate them. Anyone with a link can write as any name. That
is the right trade for a handful of trusted colleagues doing a favour, and
the wrong one for anything else -- put it behind real auth before it holds
anything sensitive.

A sibling of eval/ and eval-classifier/, sharing no code or data with
either, per the decoupling rule in AGENTS.md.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from label import agreement, store  # noqa: E402
from label.taxonomy import GEROSCIENCE_ANSWERS  # noqa: E402

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_BODY = 1_000_000
MAX_REASON = 2000


def public_record(record: dict) -> dict:
    """Everything the labeller may see, and nothing else."""
    return {
        "record_id": record.get("record_id", ""),
        "title": record.get("title", ""),
        "abstract": record.get("abstract", ""),
        "funder": record.get("funder", ""),
        "year": record.get("year"),
        "amount_eur": record.get("amount_eur"),
        "source": record.get("source", ""),
        "fingerprint": record.get("fingerprint", ""),
    }


def own_judgments(judgments: dict, labeller_id: str) -> dict:
    """A labeller sees their own answers (so they can revisit and revise),
    never anyone else's -- reading a colleague's answer mid-pass would make
    the judgments dependent and the agreement statistic meaningless."""
    mine = {}
    for record_id, entries in judgments.items():
        for entry in entries:
            if entry.get("labeller_id") == labeller_id:
                mine[record_id] = entry
    return mine


def judgments_csv(batch: dict, judgments: dict) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "record_id", "title", "funder", "year", "amount_eur", "labeller_id",
        "geroscience", "cancer", "cant_tell", "reason", "labelled_at",
        "classifier_label", "expert_label", "stratum", "record_fingerprint",
    ])
    by_id = {r["record_id"]: r for r in batch.get("records", [])}
    for record_id, entries in sorted(judgments.items()):
        record = by_id.get(record_id, {})
        hidden = record.get("_hidden", {})
        for entry in entries:
            writer.writerow([
                record_id, record.get("title", ""), record.get("funder", ""),
                record.get("year", ""), record.get("amount_eur", ""),
                entry.get("labeller_id", ""), entry.get("geroscience", ""),
                entry.get("cancer", ""), entry.get("cant_tell", ""),
                entry.get("reason", ""), entry.get("labelled_at", ""),
                hidden.get("classifier_label", ""), hidden.get("expert_label", ""),
                hidden.get("stratum", ""), entry.get("record_fingerprint", ""),
            ])
    return out.getvalue()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text, content_type, filename=None):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def _batch_or_error(self, qs):
        batch_id = (qs.get("batch") or [""])[0]
        if not store.is_slug(batch_id) or batch_id not in store.list_batches():
            self.send_json({"error": f"unknown batch {batch_id!r}",
                             "available": store.list_batches()}, 400)
            return None, None
        batch = store.load_batch(batch_id)
        if not batch.get("records"):
            self.send_json({"error": f"batch {batch_id} is empty or unreadable"}, 500)
            return None, None
        return batch_id, batch

    def do_GET(self):
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)

        if path == "/api/batches":
            return self.send_json({"batches": store.list_batches()})

        if path == "/api/records":
            batch_id, batch = self._batch_or_error(qs)
            if batch is None:
                return None
            who = (qs.get("who") or [""])[0]
            if not store.is_slug(who):
                return self.send_json(
                    {"error": "add ?who=<your-id> to the link, lowercase letters, "
                               "digits and dashes"}, 400)
            judgments = store.load_judgments(batch_id)
            return self.send_json({
                "batch": batch_id,
                "labeller_id": who,
                "records": [public_record(r) for r in batch["records"]],
                "mine": own_judgments(judgments, who),
            })

        if path == "/api/summary":
            batch_id, batch = self._batch_or_error(qs)
            if batch is None:
                return None
            return self.send_json(
                agreement.summarise(batch, store.load_judgments(batch_id)))

        if path == "/api/record":
            batch_id, batch = self._batch_or_error(qs)
            if batch is None:
                return None
            record_id = (qs.get("record_id") or [""])[0]
            record = next((r for r in batch["records"]
                           if r["record_id"] == record_id), None)
            if record is None:
                return self.send_json({"error": f"unknown record {record_id!r}"}, 404)
            judgments = store.load_judgments(batch_id)
            return self.send_json({
                "record": record,  # admin view: hidden block included on purpose
                "judgments": judgments.get(record_id, []),
            })

        if path == "/api/export.csv":
            batch_id, batch = self._batch_or_error(qs)
            if batch is None:
                return None
            return self.send_text(
                judgments_csv(batch, store.load_judgments(batch_id)),
                "text/csv; charset=utf-8", f"{batch_id}-judgments.csv")

        if path == "/admin":
            self.path = "/admin.html"
        elif path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/judgment":
            return self.send_json({"error": "not found"}, 404)

        origin = self.headers.get("Origin")
        if origin is not None and urlparse(origin).netloc != self.headers.get("Host", ""):
            return self.send_json({"error": "cross-origin writes not allowed"}, 403)

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= MAX_BODY:
                return self.send_json({"error": "bad Content-Length"}, 400)
            payload = json.loads(self.rfile.read(length))
        except ValueError:
            return self.send_json({"error": "invalid JSON body"}, 400)
        if not isinstance(payload, dict):
            return self.send_json({"error": "body must be a JSON object"}, 400)

        batch_id = payload.get("batch")
        if not store.is_slug(batch_id or "") or batch_id not in store.list_batches():
            return self.send_json({"error": f"unknown batch {batch_id!r}"}, 400)
        labeller_id = payload.get("labeller_id")
        if not store.is_slug(labeller_id or ""):
            return self.send_json({"error": "labeller_id must be a lowercase slug"}, 400)

        batch = store.load_batch(batch_id)
        record = next((r for r in batch.get("records", [])
                       if r["record_id"] == payload.get("record_id")), None)
        if record is None:
            return self.send_json(
                {"error": f"unknown record {payload.get('record_id')!r}"}, 400)

        answer = payload.get("geroscience")
        if answer not in GEROSCIENCE_ANSWERS and answer is not None:
            return self.send_json(
                {"error": f"geroscience must be one of {GEROSCIENCE_ANSWERS} or null"}, 400)

        judgment = {
            "labeller_id": labeller_id,
            "geroscience": answer,
            "cancer": bool(payload.get("cancer")),
            "cant_tell": bool(payload.get("cant_tell")),
            "reason": str(payload.get("reason") or "")[:MAX_REASON],
            "labelled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "record_fingerprint": record.get("fingerprint", ""),
        }
        try:
            store.save_judgment(batch_id, record["record_id"], judgment)
        except ValueError as exc:
            return self.send_json({"error": str(exc)}, 500)
        return self.send_json({"ok": True, "judgment": judgment})

    def log_message(self, fmt, *args):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8002)))
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"),
                    help="0.0.0.0 to accept connections from other machines. "
                          "There is no authentication -- only do this behind a "
                          "tunnel or on a trusted network.")
    args = ap.parse_args()

    batches = store.list_batches()
    if not batches:
        print("no batches yet — run: python3 -m label.sample --batch batch_001")
    server = HTTPServer((args.host, args.port), Handler)
    shown = "localhost" if args.host == "127.0.0.1" else args.host
    print(f"labelling  http://{shown}:{args.port}/?batch={batches[0] if batches else 'BATCH'}&who=your-name")
    print(f"dashboard  http://{shown}:{args.port}/admin?batch={batches[0] if batches else 'BATCH'}")
    if args.host != "127.0.0.1":
        print("warning: bound beyond localhost with no authentication")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
