#!/usr/bin/env python3
"""HTTP contract tests for label/server.py.

The load-bearing one is the blind guarantee: /api/records must never carry
the classifier label, the expert label or the sampling stratum, because the
independence of the human judgments is the entire value of the study.

Runs the real handler against a temporary batch directory on an ephemeral
port. Stdlib only.

Run: python3 label/test_server.py
"""
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from label import server, store  # noqa: E402

BATCH = {
    "size": 2,
    "records": [
        {"record_id": "swecris:TEST-1", "title": "Cellular senescence in ageing muscle",
         "abstract": "A study of senescent cell accumulation in aged tissue.",
         "funder": "Test Funder", "year": 2023, "amount_eur": 1000.0,
         "url": "https://example.org/1", "source": "swecris", "fingerprint": "aaaaaaaaaaaaaaaa",
         "_hidden": {"stratum": "disagreement", "classifier_label": "fundamental_aging",
                      "classifier_reason": "matched senescence", "expert_label": "intervention",
                      "expert_reason": "expert said so"}},
        {"record_id": "swecris:TEST-2", "title": "How do trees know it is autumn?",
         "abstract": "Leaf senescence and cold acclimation in Populus tremula.",
         "funder": "Test Funder", "year": 2021, "amount_eur": 2000.0,
         "url": "https://example.org/2", "source": "swecris", "fingerprint": "bbbbbbbbbbbbbbbb",
         "_hidden": {"stratum": "not_relevant", "classifier_label": "not_relevant",
                      "classifier_reason": "plant", "expert_label": "not_relevant",
                      "expert_reason": "plant"}},
    ],
}

failures = []


def expect(cond, msg):
    if not cond:
        failures.append(msg)


def request(port, path, body=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except ValueError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw


def main():
    tmp = tempfile.TemporaryDirectory()
    store.BATCH_DIR = Path(tmp.name) / "batches"
    store.JUDGMENT_DIR = Path(tmp.name) / "judgments"
    store.BATCH_DIR.mkdir(parents=True)
    store.atomic_write_json(store.batch_path("batch_test"), BATCH)

    httpd = HTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        # --- the blind guarantee ---------------------------------------
        status, data = request(port, "/api/records?batch=batch_test&who=alice")
        expect(status == 200, f"expected 200 for a known batch, got {status}")
        blob = json.dumps(data)
        expect("_hidden" not in blob, "BLIND BROKEN: _hidden reached the labeller")
        expect("fundamental_aging" not in blob, "BLIND BROKEN: classifier label reached the labeller")
        expect("intervention" not in blob, "BLIND BROKEN: expert label reached the labeller")
        expect("disagreement" not in blob, "BLIND BROKEN: sampling stratum reached the labeller")
        expect(data["records"][0]["abstract"].startswith("A study"), "abstract should be served")

        # --- identity is required, and must be filename-safe ------------
        status, _ = request(port, "/api/records?batch=batch_test")
        expect(status == 400, "a link with no ?who= should be refused")
        status, _ = request(port, "/api/records?batch=batch_test&who=../etc")
        expect(status == 400, "a non-slug labeller id should be refused")
        status, _ = request(port, "/api/records?batch=nope&who=alice")
        expect(status == 400, "an unknown batch should be refused")

        # --- writing a judgment -----------------------------------------
        status, data = request(port, "/api/judgment", {
            "batch": "batch_test", "labeller_id": "alice", "record_id": "swecris:TEST-1",
            "geroscience": "yes", "cancer": True, "cant_tell": False, "reason": "senescence is the subject",
        })
        expect(status == 200, f"expected 200 writing a judgment, got {status}")
        expect(data["judgment"]["record_fingerprint"] == "aaaaaaaaaaaaaaaa",
               "judgment should record the fingerprint of the text judged")

        status, _ = request(port, "/api/judgment", {
            "batch": "batch_test", "labeller_id": "alice", "record_id": "swecris:TEST-1",
            "geroscience": "sideways",
        })
        expect(status == 400, "an answer outside the taxonomy should be refused")

        status, _ = request(port, "/api/judgment", {
            "batch": "batch_test", "labeller_id": "alice", "record_id": "swecris:NOPE",
            "geroscience": "yes",
        })
        expect(status == 400, "a judgment on an unknown record should be refused")

        # --- a labeller sees their own answers, never anyone else's ------
        request(port, "/api/judgment", {
            "batch": "batch_test", "labeller_id": "bob", "record_id": "swecris:TEST-1",
            "geroscience": "no",
        })
        status, data = request(port, "/api/records?batch=batch_test&who=alice")
        expect(list(data["mine"].keys()) == ["swecris:TEST-1"], "alice should see her own judgment")
        expect(data["mine"]["swecris:TEST-1"]["geroscience"] == "yes", "alice's own answer should come back")
        expect("bob" not in json.dumps(data["mine"]),
               "BLIND BROKEN: one labeller can see another's answer")

        # --- both judgments survive, unaveraged --------------------------
        status, summary = request(port, "/api/summary?batch=batch_test")
        contested = summary["contested"][0]
        expect(contested["n_judgments"] == 2, "both judgments should be kept")
        expect(contested["consensus"] is None, "a 1-1 split has no consensus")
        expect(contested["contention"] == 2.0, "a yes/no split is maximal contention")

        # --- admin can see what the labellers could not ------------------
        status, data = request(port, "/api/record?batch=batch_test&record_id=swecris:TEST-1")
        expect(data["record"]["_hidden"]["classifier_label"] == "fundamental_aging",
               "the admin view should show the withheld labels")
        expect(len(data["judgments"]) == 2, "the admin view should show every judgment")

        # --- CSV export --------------------------------------------------
        status, text = request(port, "/api/export.csv?batch=batch_test")
        expect(status == 200, "CSV export should succeed")
        expect("alice" in text and "bob" in text, "CSV should carry every labeller")
        expect("senescence is the subject" in text, "CSV should carry reasons")
    finally:
        httpd.shutdown()
        thread.join()
        tmp.cleanup()

    if failures:
        print(f"{len(failures)} failure(s):")
        for f in failures:
            print(" -", f)
        return 1
    print("all label/server.py contract checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
