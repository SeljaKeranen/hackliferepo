#!/usr/bin/env python3
"""Smoke test for eval/server.py's HTTP contract.

Runs the real handler against a temporary findings/verdicts directory on an
ephemeral port, then exercises the read path, the write path, and the write
path's rejection branches. Stdlib only.

Run: python3 eval/test_server.py
"""
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server

FINDING = {
    "id": "xx-001", "type": "finding", "country": "XX", "classification": "policy",
    "claim": "A sufficiently long test claim for the server smoke test.",
    "source_url": "https://example.org/doc", "source_date": "2026-01-02",
    "confidence": "high", "retrieved_at": "2026-01-02T03:04:05Z",
}

failures = []


def expect(cond, msg):
    if not cond:
        failures.append(msg)


def request(port, path, body=None, headers=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def main():
    tmp = tempfile.TemporaryDirectory()
    server.FINDINGS_DIR = os.path.join(tmp.name, "findings")
    server.VERDICTS_DIR = os.path.join(tmp.name, "verdicts")
    server.JUDGMENTS_DIR = os.path.join(tmp.name, "judgments")
    os.makedirs(server.FINDINGS_DIR)
    os.makedirs(server.JUDGMENTS_DIR)
    with open(os.path.join(server.FINDINGS_DIR, "testland.json"), "w", encoding="utf-8") as f:
        json.dump([FINDING], f)
    with open(os.path.join(server.FINDINGS_DIR, "broken.json"), "w", encoding="utf-8") as f:
        f.write("{not json")
    judgment = {
        "finding_id": "xx-001",
        "finding_fingerprint": server.finding_fingerprint(FINDING),
        "judged_at": "2026-01-03T00:00:00Z",
        "judges": {dim: {"verdict": "pass", "reason": "smoke"}
                   for dim in server.JUDGE_DIMENSIONS},
    }
    with open(os.path.join(server.JUDGMENTS_DIR, "testland.judgments.json"),
              "w", encoding="utf-8") as f:
        json.dump({"xx-001": judgment}, f)

    httpd = HTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    status, data = request(port, "/api/data")
    expect(status == 200, "GET /api/data should be 200")
    expect(data["countries"]["testland"]["findings"] == [FINDING],
           "findings should round-trip through /api/data")
    expect(data["countries"]["testland"]["verdicts"] == {},
           "missing verdicts file should read as empty object")
    expect(data["countries"]["broken"].get("error"),
           "corrupt findings file must surface an error, not pose as clean")
    expect(data["countries"]["broken"]["findings"] == [],
           "corrupt findings file should serve an empty findings list")
    served_judgment = data["countries"]["testland"]["judgments"].get("xx-001", {})
    expect(set(served_judgment.get("judges", {})) == set(server.JUDGE_DIMENSIONS),
           "AI judgments should be served on /api/data")
    expect(served_judgment.get("judges", {}).get("credibility")
           == {"verdict": "pass", "reason": "smoke"},
           "judge record content should round-trip unmodified")
    expect(served_judgment.get("stale") is False,
           "current judgment should not be marked stale")
    expect(data["countries"]["broken"]["judgments"] == {},
           "missing judgments file should read as empty object")

    verdict = {"country": "testland", "finding_id": "xx-001",
               "checks": {k: True for k in server.CHECKS}, "reviewer": "smoke"}
    status, res = request(port, "/api/verdict", verdict)
    expect(status == 200 and res.get("ok"), "valid verdict should be accepted")
    expect(res.get("verdict", {}).get("correct") is True,
           "all-pass verdict should be correct")
    expect(res.get("verdict", {}).get("finding_fingerprint")
           == server.finding_fingerprint(FINDING),
           "verdict should carry the reviewed finding's fingerprint")
    with open(os.path.join(server.VERDICTS_DIR, "testland.verdicts.json"),
              encoding="utf-8") as f:
        expect("xx-001" in json.load(f), "verdict should persist to the country's file")

    status, _ = request(port, "/api/verdict", {**verdict, "finding_id": "xx-999"})
    expect(status == 400, "verdict for a nonexistent finding must be rejected")

    findings_path = os.path.join(server.FINDINGS_DIR, "testland.json")
    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump([{**FINDING, "claim": FINDING["claim"] + " Edited after review."}], f)
    status, data = request(port, "/api/data")
    expect(data["countries"]["testland"]["verdicts"]["xx-001"].get("stale") is True,
           "editing a reviewed finding must mark its served verdict stale")
    expect(data["countries"]["testland"]["judgments"]["xx-001"].get("stale") is True,
           "editing a judged finding must mark its served AI judgment stale")
    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump([], f)
    status, data = request(port, "/api/data")
    expect(data["countries"]["testland"]["verdicts"]["xx-001"].get("stale") is True,
           "a verdict whose finding vanished must be marked stale")
    expect(data["countries"]["testland"]["judgments"]["xx-001"].get("stale") is True,
           "a judgment whose finding vanished must be marked stale")
    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump([FINDING], f)
    status, data = request(port, "/api/data")
    expect(data["countries"]["testland"]["verdicts"]["xx-001"].get("stale") is False,
           "restoring the reviewed content must clear the stale flag")

    with open(os.path.join(server.VERDICTS_DIR, "testland.verdicts.json"),
              "a", encoding="utf-8") as f:
        f.write("<<<<<<< merge conflict")
    status, _ = request(port, "/api/verdict", verdict)
    expect(status == 500, "corrupt verdicts file must refuse writes, not be clobbered")
    status, data = request(port, "/api/data")
    expect("verdicts" in (data["countries"]["testland"].get("error") or ""),
           "corrupt verdicts file must surface an error on /api/data")
    with open(os.path.join(server.VERDICTS_DIR, "testland.verdicts.json"),
              encoding="utf-8") as f:
        expect("<<<<<<<" in f.read(), "corrupt verdicts file must be left untouched")
    os.unlink(os.path.join(server.VERDICTS_DIR, "testland.verdicts.json"))
    status, _ = request(port, "/api/verdict", verdict)
    expect(status == 200, "missing verdicts file should start a fresh one")

    with open(os.path.join(server.JUDGMENTS_DIR, "testland.judgments.json"),
              "a", encoding="utf-8") as f:
        f.write("<<<<<<< merge conflict")
    status, data = request(port, "/api/data")
    expect("judgments" in (data["countries"]["testland"].get("error") or ""),
           "corrupt judgments file must surface an error on /api/data")

    for bad_country in ("../evil", "evil/../..", "nosuch", "TESTLAND", "", 7, None):
        status, _ = request(port, "/api/verdict", {**verdict, "country": bad_country})
        expect(status == 400, f"country {bad_country!r} must be rejected with 400")
    status, _ = request(port, "/api/verdict", verdict,
                        headers={"Origin": "https://evil.example"})
    expect(status == 403, "cross-origin verdict write must be rejected with 403")
    status, _ = request(port, "/api/verdict",
                        {**verdict, "checks": {"source_resolves": "yes"}})
    expect(status == 400, "non-boolean check value must be rejected with 400")

    httpd.shutdown()
    tmp.cleanup()
    if failures:
        print(f"FAIL: {len(failures)} problem(s)")
        for msg in failures:
            print(f"  - {msg}")
        sys.exit(1)
    print("OK: server smoke test passed")


if __name__ == "__main__":
    main()
