#!/usr/bin/env python3
"""Tests for the gate's verdict/agreement math (multi-reviewer merge,
Wilson interval, conflict handling), fingerprint invalidation, the server's
HTTP contract (against a temp data directory), the benchmark export, and
the committed sample/judgments/verdicts artifacts.

Run: python3 eval-classifier/test_gate.py
"""
import glob
import importlib.util
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

GATE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_module(name, filename):
    # unique module names: a bare `import server` would collide with
    # eval/server.py if both suites ever share one interpreter; sys.modules
    # registration makes every loader share one instance, so patching
    # server globals here also steers export_benchmark's server
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(GATE_DIR, filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


server = _load_module("eval_classifier_server", "server.py")
sample_mod = _load_module("eval_classifier_sample", "sample.py")
export_benchmark = _load_module("eval_classifier_export",
                                "export_benchmark.py")

failures = []


def expect(cond, msg):
    if not cond:
        failures.append(msg)


def make_record(rid, label="care", **over):
    rec = {
        "record_id": rid, "source": "swecris", "title": f"Grant {rid}",
        "quote": "a supporting quote", "label": label,
        "reason": "test reason", "matched_keywords": {label: ["kw"]},
        "anchor_terms": ["ageing"], "confidence": 0.7,
        "llm_category": "care", "url": "https://example.org",
        "funder": "F", "amount_eur": 1000.0, "year": "2024", "region": "SE",
        "sampling": {"stratum": f"{label}|swecris", "why": ["fill"],
                     "boundary_flags": []},
    }
    rec.update(over)
    return rec


def verdict_for(rec, verdict="agree", label=None, reviewer="t"):
    return {
        "record_id": rec["record_id"],
        "record_fingerprint": server.record_fingerprint(rec),
        "verdict": verdict,
        "label": label or rec["label"],
        "reviewer": reviewer, "note": "",
        "reviewed_at": "2026-09-12T00:00:00Z",
    }


def test_summarize():
    recs = [make_record(f"r{i}") for i in range(5)]
    recs[3]["label"] = "ambiguous"
    by_id = {r["record_id"]: r for r in recs}
    a = {
        "r0": verdict_for(recs[0], reviewer="a"),                     # agree
        "r1": verdict_for(recs[1], "disagree", "intervention", "a"),
        "r3": verdict_for(recs[3], reviewer="a"),   # ambiguous confirmed
        "r4": verdict_for(recs[4], reviewer="a"),                     # agree
    }
    b = {
        # same record, same conclusion: counts once
        "r0": verdict_for(recs[0], reviewer="b"),
        # same record, conflicting label: inter-reviewer disagreement
        "r4": verdict_for(recs[4], "disagree", "not_relevant", "b"),
    }
    for v in (a, b):
        server.mark_stale(v, by_id)
    s = server.summarize(recs, {"a": a, "b": b}, {})
    expect(s["total"] == 5 and s["reviewed"] == 4,
           f"multi-reviewer records must count once: {s}")
    expect(s["consensus_reviewed"] == 3 and s["agreed"] == 2,
           f"conflicting records must leave the agreement pool: {s}")
    expect(s["agreement"] == round(2 / 3, 4),
           "agreement must be agreed/consensus-reviewed")
    expect([d["record_id"] for d in s["inter_reviewer_disagreements"]]
           == ["r4"],
           "the conflicting record must be listed as a disagreement")
    expect(s["inter_reviewer_disagreements"][0]["labels"]
           == {"a": "care", "b": "not_relevant"},
           "the disagreement must show each reviewer's label")
    expect(s["ambiguous_reviewed"] == 1 and s["ambiguous_confirmed"] == 1,
           "ambiguous honesty counts wrong")
    expect(s["judge_flagged"] == 5,
           "records without judgments count as flagged")
    ci = s["agreement_ci95"]
    expect(ci and 0 <= ci[0] <= s["agreement"] <= ci[1] <= 1,
           f"Wilson interval must bracket the point estimate: {ci}")

    # per-split reporting: records carry sampling.split; the halves'
    # counts must partition the combined numbers AND each half's agreement
    # must be exactly its own records' value (a bucket-assignment bug that
    # preserves grand totals must still fail here).
    # State at this point: r0 agree (a+b concur), r1 disagree(a),
    # r2 unreviewed, r3 agree(a, ambiguous), r4 conflict(a/b).
    for i, r in enumerate(recs):
        r["sampling"]["split"] = "tuning" if i % 2 == 0 else "holdout"
    s = server.summarize(recs, {"a": a, "b": b}, {})
    sp = s["splits"]
    expect(sp["tuning"]["total"] == 3 and sp["holdout"]["total"] == 2,
           f"split totals must partition the sample: {sp}")
    # tuning (r0 agreed, r2 unreviewed, r4 conflict): 1 consensus, 1 agreed
    expect(sp["tuning"]["consensus_reviewed"] == 1
           and sp["tuning"]["agreed"] == 1
           and sp["tuning"]["agreement"] == 1.0,
           f"tuning half must be exactly its own records: {sp['tuning']}")
    # holdout (r1 disagree, r3 agree): 2 consensus, 1 agreed
    expect(sp["holdout"]["consensus_reviewed"] == 2
           and sp["holdout"]["agreed"] == 1
           and sp["holdout"]["agreement"] == 0.5,
           f"holdout half must be exactly its own records: {sp['holdout']}")
    expect(sp["tuning"]["consensus_reviewed"]
           + sp["holdout"]["consensus_reviewed"] == s["consensus_reviewed"],
           "split consensus counts must partition the combined count")
    expect(sp["tuning"]["agreed"] + sp["holdout"]["agreed"] == s["agreed"],
           "split agreed counts must partition the combined count")

    # a stale verdict (edited record) drops out of every count
    recs[0]["reason"] = "edited after review"
    for v in (a, b):
        server.mark_stale(v, by_id)
    s = server.summarize(recs, {"a": a, "b": b}, {})
    expect(s["reviewed"] == 3 and s["agreed"] == 1,
           "stale verdicts must not count as reviewed")
    expect(server.summarize([], {}, {})["agreement"] is None,
           "agreement is undefined with nothing reviewed")

    # a malformed entry (no verdict field) counts as unreviewed, never as a
    # disagreement
    broken = {"r2": {"record_fingerprint":
                     server.record_fingerprint(recs[2]), "stale": False}}
    s = server.summarize(recs, {"a": broken}, {})
    expect(s["reviewed"] == 0,
           "a verdict entry without a verdict must not count as reviewed")

    # a hand-edited "agree" carrying a different label is the disagreement
    # it actually expresses, never counted as agreement
    inconsistent = verdict_for(recs[2], "agree", reviewer="a")
    inconsistent["label"] = "not_relevant"
    marked = {"r2": inconsistent}
    server.mark_stale(marked, by_id)
    s = server.summarize(recs, {"a": marked}, {})
    expect(s["reviewed"] == 1 and s["agreed"] == 0,
           "agreement must come from label equality, not the verdict word")

    # effective_verdicts refuses verdicts that never went through
    # mark_stale (no explicit stale: False) - forgetting the staleness
    # pass must yield a loud zero, not silently-fresh verdicts
    expect(server.effective_verdicts(
               {"a": {"r2": verdict_for(recs[2], reviewer="a")}}) == {},
           "unmarked verdicts must be excluded, not assumed fresh")

    # a verdict whose record vanished from the sample is stale
    ghost = {"gone": verdict_for(make_record("gone"), reviewer="a")}
    server.mark_stale(ghost, by_id)
    expect(ghost["gone"]["stale"] is True,
           "a verdict for a vanished record must be marked stale")
    expect(server.effective_verdicts({"a": ghost}) == {},
           "stale ghost verdicts must not count")

    # Wilson interval sanity on known values and boundaries
    expect(server.wilson_interval(0, 0) is None,
           "Wilson interval is undefined for n=0")
    lo, hi = server.wilson_interval(85, 100)
    expect(0.76 < lo < 0.85 < hi < 0.91,
           f"Wilson 85/100 should be about [0.77, 0.90], got [{lo}, {hi}]")
    lo, hi = server.wilson_interval(0, 10)
    expect(lo == 0.0 and 0 < hi < 0.35,
           f"Wilson 0/10 must clamp at 0: [{lo}, {hi}]")
    lo, hi = server.wilson_interval(10, 10)
    expect(0.65 < lo < 1 and hi == 1.0,
           f"Wilson 10/10 must clamp at 1: [{lo}, {hi}]")

    # the label vocabularies of the sibling modules stay consistent with
    # the server's - equality, not just subset, so a new label cannot
    # silently miss a list
    expect(set(sample_mod.ALL_LABELS) == set(server.LABELS),
           "sample.ALL_LABELS must equal server.LABELS")
    expect(set(sample_mod.SUBSTANTIVE) < set(server.LABELS),
           "sample.SUBSTANTIVE must be a subset of server.LABELS")
    expect(set(export_benchmark.NEW_LABELS)
           == set(server.LABELS) - set(export_benchmark.GUIDE_LABELS),
           "NEW_LABELS must be exactly the post-guide server labels")


def test_judge_flagged():
    rec = make_record("r0")
    fp = server.record_fingerprint(rec)
    all_pass = {"r0": {"record_fingerprint": fp, "stale": False, "judges": {
        d: {"verdict": "pass", "reason": "ok"}
        for d in server.JUDGE_DIMENSIONS}}}
    expect(not server.judge_flagged(rec, all_pass),
           "three passing judges must not flag")
    one_fail = json.loads(json.dumps(all_pass))
    one_fail["r0"]["judges"]["category"]["verdict"] = "fail"
    expect(server.judge_flagged(rec, one_fail), "a failing judge must flag")
    stale = json.loads(json.dumps(all_pass))
    stale["r0"]["stale"] = True
    expect(server.judge_flagged(rec, stale), "a stale judgment must flag")
    expect(server.judge_flagged(rec, {}), "a missing judgment must flag")


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


def test_http(tmp):
    rec = make_record("swecris:T1", label="care")
    server.SAMPLE_PATH = os.path.join(tmp, "sample.json")
    server.VERDICTS_DIR = os.path.join(tmp, "verdicts")
    server.JUDGMENTS_PATH = os.path.join(tmp, "judgments.json")
    server.REVIEWER = "smoke"
    my_verdicts = os.path.join(server.VERDICTS_DIR, "smoke.verdicts.json")
    with open(server.SAMPLE_PATH, "w", encoding="utf-8") as f:
        json.dump({"meta": {"seed": 1}, "records": [rec]}, f)
    with open(server.JUDGMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"swecris:T1": {
            "record_id": "swecris:T1",
            "record_fingerprint": server.record_fingerprint(rec),
            "judged_at": "2026-09-12T00:00:00Z",
            "judges": {d: {"verdict": "pass", "reason": "smoke"}
                       for d in server.JUDGE_DIMENSIONS}}}, f)

    httpd = HTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    fp = server.record_fingerprint(rec)
    status, data = request(port, "/api/data")
    expect(status == 200 and data["records"] == [{**rec, "fingerprint": fp}],
           "records should round-trip through /api/data with fingerprints")
    expect(data["reviewer"] == "smoke",
           "the local reviewer identity is served")
    expect(data["judgments"]["swecris:T1"]["stale"] is False,
           "current judgment should not be marked stale")
    expect(data["summary"]["judge_flagged"] == 0,
           "an all-pass judged record is not flagged")

    # the review page itself is served
    req = urllib.request.Request(f"http://127.0.0.1:{port}/")
    with urllib.request.urlopen(req) as resp:
        expect(resp.status == 200
               and "text/html" in resp.headers.get("Content-Type", ""),
               "GET / must serve the review page")

    # agree
    status, res = request(port, "/api/verdict",
                          {"record_id": "swecris:T1", "verdict": "agree",
                           "record_fingerprint": fp})
    expect(status == 200 and res["ok"], "agree verdict should be accepted")
    expect(res["verdict"]["label"] == "care"
           and res["verdict"]["reviewer"] == "smoke",
           "agree must record the pipeline's label and the local reviewer")
    expect(res["summary"]["agreed"] == 1 and res["summary"]["agreement"] == 1,
           "summary must update with the verdict")
    with open(my_verdicts, encoding="utf-8") as f:
        expect("swecris:T1" in json.load(f),
               "the verdict must persist to the reviewer's own file")

    # a second reviewer's file merges into the summary; a conflicting label
    # becomes an inter-reviewer disagreement
    other = verdict_for(rec, "disagree", "not_relevant", reviewer="other")
    with open(os.path.join(server.VERDICTS_DIR, "other.verdicts.json"),
              "w", encoding="utf-8") as f:
        json.dump({"swecris:T1": other}, f)
    status, data = request(port, "/api/data")
    expect(sorted(data["verdicts"]) == ["other", "smoke"],
           "all reviewers' verdict files are served")
    s = data["summary"]
    expect(s["reviewed"] == 1 and s["consensus_reviewed"] == 0
           and len(s["inter_reviewer_disagreements"]) == 1,
           f"a reviewer conflict must be surfaced, not averaged: {s}")
    os.unlink(os.path.join(server.VERDICTS_DIR, "other.verdicts.json"))

    # disagree with a corrected label
    status, res = request(port, "/api/verdict",
                          {"record_id": "swecris:T1", "verdict": "disagree",
                           "record_fingerprint": fp,
                           "correct_label": "not_relevant"})
    expect(status == 200 and res["verdict"]["label"] == "not_relevant",
           "disagree must record the corrected label")
    expect(res["summary"]["agreed"] == 0,
           "a disagree overwrites the earlier agree")

    # rejection branches
    for bad in ({"record_id": "nope", "verdict": "agree",
                 "record_fingerprint": fp},
                {"record_id": "swecris:T1", "verdict": "maybe",
                 "record_fingerprint": fp},
                {"record_id": "swecris:T1", "verdict": "disagree",
                 "record_fingerprint": fp},
                {"record_id": "swecris:T1", "verdict": "disagree",
                 "record_fingerprint": fp, "correct_label": "care"},
                {"record_id": "swecris:T1", "verdict": "disagree",
                 "record_fingerprint": fp, "correct_label": "policy"},
                {"record_id": "swecris:T1", "record_fingerprint": fp}):
        status, _ = request(port, "/api/verdict", bad)
        expect(status == 400, f"payload {bad} must be rejected with 400")
    status, _ = request(port, "/api/verdict", ["not", "an", "object"])
    expect(status == 400, "non-object JSON body must be rejected with 400")
    status, _ = request(port, "/api/verdict",
                        {"record_id": "swecris:T1", "verdict": "agree",
                         "record_fingerprint": fp},
                        headers={"Origin": "https://evil.example"})
    expect(status == 403, "cross-origin verdict write must be rejected")
    # DNS rebinding: an attacker domain resolving to 127.0.0.1 sends its
    # own name as Host (and a matching Origin); only loopback names may
    # write
    status, _ = request(port, "/api/verdict",
                        {"record_id": "swecris:T1", "verdict": "agree",
                         "record_fingerprint": fp},
                        headers={"Host": "evil.example:80",
                                 "Origin": "http://evil.example:80"})
    expect(status == 403, "a non-loopback Host header must be rejected")

    # a verdict against a version the reviewer never saw is refused
    status, _ = request(port, "/api/verdict",
                        {"record_id": "swecris:T1", "verdict": "agree",
                         "record_fingerprint": "0" * 16})
    expect(status == 409,
           "a stale-view verdict must be rejected with 409")

    # undo (no fingerprint needed: clearing is safe on any version)
    status, res = request(port, "/api/verdict",
                          {"record_id": "swecris:T1", "verdict": None})
    expect(status == 200 and res["verdict"] is None,
           "null verdict must clear the stored verdict")
    with open(my_verdicts, encoding="utf-8") as f:
        expect(json.load(f) == {}, "cleared verdict must not persist")

    # staleness: edit the sampled record after review
    request(port, "/api/verdict",
            {"record_id": "swecris:T1", "verdict": "agree",
             "record_fingerprint": fp})
    with open(server.SAMPLE_PATH, "w", encoding="utf-8") as f:
        json.dump({"meta": {}, "records": [
            {**rec, "label": "intervention"}]}, f)
    status, data = request(port, "/api/data")
    expect(data["verdicts"]["smoke"]["swecris:T1"]["stale"] is True,
           "editing a reviewed record must mark its verdict stale")
    expect(data["judgments"]["swecris:T1"]["stale"] is True,
           "editing a judged record must mark its judgment stale")
    expect(data["summary"]["reviewed"] == 0,
           "stale verdicts drop from the reviewed count")
    # ...and a save from the still-open old card is refused, not recorded
    status, _ = request(port, "/api/verdict",
                        {"record_id": "swecris:T1", "verdict": "agree",
                         "record_fingerprint": fp})
    expect(status == 409,
           "an old card must not approve a regenerated record")

    # corrupt verdicts file refuses writes and is left untouched
    new_fp = server.record_fingerprint({**rec, "label": "intervention"})
    with open(my_verdicts, "a", encoding="utf-8") as f:
        f.write("<<<<<<< merge conflict")
    status, _ = request(port, "/api/verdict",
                        {"record_id": "swecris:T1", "verdict": "agree",
                         "record_fingerprint": new_fp})
    expect(status == 500,
           "corrupt verdicts file must refuse writes, not be clobbered")
    with open(my_verdicts, encoding="utf-8") as f:
        expect("<<<<<<<" in f.read(),
               "corrupt verdicts file must be left untouched")
    status, data = request(port, "/api/data")
    expect("smoke.verdicts.json" in (data.get("error") or ""),
           "corrupt verdicts file must surface an error on /api/data")

    # a malformed record in the sample surfaces an error instead of
    # crashing the metrics
    with open(server.SAMPLE_PATH, "w", encoding="utf-8") as f:
        json.dump({"meta": {}, "records": [rec, None, {"title": "no id"}]},
                  f)
    status, data = request(port, "/api/data")
    expect(status == 200 and "malformed record" in (data.get("error") or ""),
           "malformed sample records must surface an error")
    expect(len(data["records"]) == 1 and data["summary"]["total"] == 1,
           "malformed sample records must be excluded, not crash summarize")

    # a badly named verdicts file is ignored BUT loudly reported
    stray = os.path.join(server.VERDICTS_DIR, "Bad Name.verdicts.json")
    with open(stray, "w", encoding="utf-8") as f:
        json.dump({}, f)
    status, data = request(port, "/api/data")
    expect("Bad Name.verdicts.json" in (data.get("error") or ""),
           "an invalid verdicts filename must surface an error, its "
           "evidence must never vanish silently")
    expect("Bad Name" not in data["verdicts"],
           "an invalid verdicts filename must not be loaded")
    os.unlink(stray)

    # a corrupt sample file refuses verdict writes with 500, not a
    # client-error 400 that would mask a broken evidence store
    with open(server.SAMPLE_PATH, "w", encoding="utf-8") as f:
        f.write("{not json")
    status, _ = request(port, "/api/verdict",
                        {"record_id": "swecris:T1", "verdict": "agree",
                         "record_fingerprint": fp})
    expect(status == 500,
           "a corrupt sample must fail verdict writes with 500")

    httpd.shutdown()


def test_reviewer_identity():
    expect(server.slugify_reviewer("Selja Keränen") == "selja-ker-nen",
           "reviewer names slugify to filename-safe slugs")
    expect(server.slugify_reviewer("../evil") == "evil",
           "path characters never survive slugification")
    expect(server.slugify_reviewer("!!!") is None,
           "an unusable name yields None, not a bad filename")
    expect(server.detect_reviewer("Smoke Tester") == "smoke-tester",
           "--reviewer wins over every fallback")

    # the fallback chain: git config user.name, then $USER, then None;
    # an unusable earlier candidate falls through instead of stopping
    real_git, real_user = server._git_user_name, os.environ.get("USER")
    try:
        server._git_user_name = lambda: "Git Name"
        os.environ["USER"] = "envuser"
        expect(server.detect_reviewer(None) == "git-name",
               "git user.name is the first fallback")
        expect(server.detect_reviewer("!!!") == "git-name",
               "an unusable --reviewer falls through to git user.name")
        server._git_user_name = lambda: ""
        expect(server.detect_reviewer(None) == "envuser",
               "$USER is the last fallback")
        os.environ["USER"] = "***"
        expect(server.detect_reviewer(None) is None,
               "no usable candidate yields None, never a junk slug")
    finally:
        server._git_user_name = real_git
        if real_user is None:
            os.environ.pop("USER", None)
        else:
            os.environ["USER"] = real_user


def test_export():
    rec = make_record("swecris:T1", label="not_relevant")
    consensus = {"swecris:T1": verdict_for(rec)}
    key = {"B01": {"record_id": "swecris:T1"},
           "B02": {"record_id": "swecris:T2"}}
    rows = [{"input_id": "B01", "title": "t", "human_category": "old-junk",
             "human_confidence": "0.5", "human_notes": "stale annotation"},
            {"input_id": "B02", "title": "t", "human_category": "old-junk",
             "human_confidence": "0.5", "human_notes": "stale annotation"}]
    rows, filled = export_benchmark.fill_rows(rows, key, consensus)
    expect(filled == 1, "one consensus benchmark record should be filled")
    expect(rows[0]["human_category"] == "not_relevant",
           "the confirmed label is written verbatim")
    expect("legacy_equiv=ambiguous" in rows[0]["human_notes"],
           "post-guide labels must carry the legacy mapping note")
    expect(rows[1]["human_category"] == ""
           and rows[1]["human_notes"] == "",
           "rows without consensus are BLANKED, pre-existing annotations "
           "must not survive the export")

    # load_consensus: two agreeing reviewers merge to one verdict, a
    # conflict yields none, stale verdicts drop. Patch the server module
    # instance export_benchmark actually holds (it loads its own copy).
    exp_server = export_benchmark.server
    with tempfile.TemporaryDirectory() as tmp:
        old_sample, old_dir = exp_server.SAMPLE_PATH, exp_server.VERDICTS_DIR
        exp_server.SAMPLE_PATH = os.path.join(tmp, "sample.json")
        exp_server.VERDICTS_DIR = os.path.join(tmp, "verdicts")
        os.makedirs(exp_server.VERDICTS_DIR)
        try:
            r1 = make_record("swecris:T1", label="care")
            r2 = make_record("swecris:T2", label="care")
            r3 = make_record("swecris:T3", label="care")
            with open(exp_server.SAMPLE_PATH, "w", encoding="utf-8") as f:
                json.dump({"meta": {}, "records": [r1, r2, r3]}, f)
            stale = verdict_for(r3, reviewer="a")
            stale["record_fingerprint"] = "0" * 16
            for reviewer, verdicts in (
                    ("a", {"swecris:T1": verdict_for(r1, reviewer="a"),
                           "swecris:T2": verdict_for(r2, reviewer="a"),
                           "swecris:T3": stale}),
                    ("b", {"swecris:T1": verdict_for(r1, reviewer="b"),
                           "swecris:T2": verdict_for(
                               r2, "disagree", "ambiguous", "b")})):
                with open(os.path.join(exp_server.VERDICTS_DIR,
                                       f"{reviewer}.verdicts.json"),
                          "w", encoding="utf-8") as f:
                    json.dump(verdicts, f)
            consensus = export_benchmark.load_consensus(
                __import__("pathlib").Path(exp_server.SAMPLE_PATH))
            expect(sorted(consensus) == ["swecris:T1"],
                   f"only agreeing, current verdicts export: {sorted(consensus)}")
        finally:
            exp_server.SAMPLE_PATH, exp_server.VERDICTS_DIR = \
                old_sample, old_dir


def test_committed_artifacts():
    """Validate whatever sample/judgments/verdicts are committed: shapes,
    known labels, and fingerprints that match the current sample."""
    sample_path = os.path.join(GATE_DIR, "sample.json")
    if not os.path.exists(sample_path):
        return
    with open(sample_path, encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("records")
    expect(isinstance(records, list) and records, "sample.json has records")
    ids = [r.get("record_id") for r in records]
    expect(len(ids) == len(set(ids)), "sample record_ids must be unique")
    expect(60 <= len(records) <= 80,
           f"sample size should be 60-80, got {len(records)}")
    bench = [r for r in records if "benchmark_id" in r.get("sampling", {})]
    expect(len(bench) == 30,
           f"all 30 benchmark records must be sampled, got {len(bench)}")
    for r in records:
        expect(r.get("label") in server.LABELS,
               f"{r.get('record_id')}: unknown label {r.get('label')!r}")
        for field in ("title", "reason", "source", "sampling"):
            expect(field in r, f"{r.get('record_id')}: missing {field}")
        expect(r.get("sampling", {}).get("split") in ("tuning", "holdout"),
               f"{r.get('record_id')}: missing tuning/holdout split")
    by_id = {r["record_id"]: r for r in records}

    judgments_path = os.path.join(GATE_DIR, "judgments.json")
    if os.path.exists(judgments_path):
        with open(judgments_path, encoding="utf-8") as f:
            judgments = json.load(f)
        expect(isinstance(judgments, dict), "judgments.json must be an object")
        expect(set(judgments) == set(by_id),
               "judgments.json must cover exactly the sampled records")
        for rid, att in judgments.items():
            expect(isinstance(att, dict),
                   f"judgments.json: {rid} must be an object")
            if not isinstance(att, dict):
                continue
            expect(att.get("record_fingerprint")
                   == server.record_fingerprint(by_id.get(rid, {})),
                   f"judgments.json: {rid} is stale - re-judge it")
            judges = att.get("judges", {})
            expect(set(judges) == set(server.JUDGE_DIMENSIONS),
                   f"judgments.json: {rid} must have exactly three judges")
            for dim, g in judges.items():
                expect(g.get("verdict") in server.JUDGE_VERDICTS,
                       f"judgments.json: {rid}/{dim} has a bad verdict")
                expect(isinstance(g.get("reason"), str) and g["reason"],
                       f"judgments.json: {rid}/{dim} needs a reason")
                if g.get("proposed_label") is not None:
                    expect(g["proposed_label"] in server.LABELS,
                           f"judgments.json: {rid}/{dim} proposes unknown "
                           "label")

    for path in sorted(glob.glob(
            os.path.join(GATE_DIR, "verdicts", "*.verdicts.json"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            verdicts = json.load(f)
        expect(isinstance(verdicts, dict), f"{name} must be an object")
        for rid, v in verdicts.items():
            expect(rid in by_id, f"{name}: {rid} is not in the sample")
            expect(isinstance(v, dict) and v.get("record_fingerprint")
                   == server.record_fingerprint(by_id.get(rid, {})),
                   f"{name}: {rid} is stale - re-review it")
            if isinstance(v, dict):
                expect(v.get("verdict") in ("agree", "disagree"),
                       f"{name}: {rid} has a bad verdict")
                expect(v.get("label") in server.LABELS,
                       f"{name}: {rid} has an unknown label")


def main():
    test_summarize()
    test_judge_flagged()
    with tempfile.TemporaryDirectory() as tmp:
        test_http(tmp)
    test_reviewer_identity()
    test_export()
    test_committed_artifacts()
    if failures:
        print(f"FAIL: {len(failures)} problem(s)")
        for msg in failures:
            print(f"  - {msg}")
        sys.exit(1)
    print("OK: gate tests passed")


if __name__ == "__main__":
    main()
