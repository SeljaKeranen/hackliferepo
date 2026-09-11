#!/usr/bin/env python3
"""Validate eval/findings/*.json and eval/verdicts/*.verdicts.json.

Stdlib only: the schema's constraints are enforced with structural asserts
mirroring schema/finding.schema.json. To keep the two from drifting, the
enums and regexes used here are asserted equal to the ones parsed out of the
schema file, and a built-in fixture self-test proves the validator still
rejects malformed records.

Run: python3 eval/test_findings.py
"""
import json
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "eval"))
from server import CHECKS  # single source for the rubric's check keys

SCHEMA_PATH = os.path.join(ROOT, "schema", "finding.schema.json")
FINDINGS_GLOB = os.path.join(ROOT, "eval", "findings", "*.json")
VERDICTS_GLOB = os.path.join(ROOT, "eval", "verdicts", "*.verdicts.json")

CLASSIFICATIONS = {"policy", "legislation", "funding", "strategy", "political statement"}
CONFIDENCES = {"high", "medium", "low"}
ID_RE = re.compile(r"^[a-z]{2}-[0-9]{3}$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$")

FINDING_REQUIRED = {
    "id", "type", "country", "classification", "claim",
    "source_url", "source_date", "confidence", "retrieved_at",
}
FINDING_ALLOWED = FINDING_REQUIRED | {"region", "source_note"}
NOTHING_REQUIRED = {"id", "type", "country", "search_note", "retrieved_at"}
NOTHING_ALLOWED = NOTHING_REQUIRED | {"region"}

errors = []


def check(cond, msg):
    if not cond:
        errors.append(msg)


def matches(regex, value):
    # fullmatch (not match) so a trailing newline can't sneak past the $ anchor
    return isinstance(value, str) and bool(regex.fullmatch(value))


def validate_record(rec, where):
    check(isinstance(rec, dict), f"{where}: record is not an object")
    if not isinstance(rec, dict):
        return
    rtype = rec.get("type")
    check(rtype in ("finding", "nothing_reliable_found"), f"{where}: bad type {rtype!r}")
    required = FINDING_REQUIRED if rtype == "finding" else NOTHING_REQUIRED
    allowed = FINDING_ALLOWED if rtype == "finding" else NOTHING_ALLOWED
    for key in required:
        check(key in rec, f"{where}: missing required field {key!r}")
    for key in rec:
        check(key in allowed, f"{where}: unexpected field {key!r}")

    check(matches(ID_RE, rec.get("id")), f"{where}: bad id {rec.get('id')!r}")
    check(matches(COUNTRY_RE, rec.get("country")), f"{where}: bad country {rec.get('country')!r}")
    check(matches(TIMESTAMP_RE, rec.get("retrieved_at")),
          f"{where}: bad retrieved_at {rec.get('retrieved_at')!r}")

    if rtype == "finding":
        check(rec.get("classification") in CLASSIFICATIONS,
              f"{where}: bad classification {rec.get('classification')!r}")
        check(rec.get("confidence") in CONFIDENCES,
              f"{where}: bad confidence {rec.get('confidence')!r}")
        claim = rec.get("claim", "")
        check(isinstance(claim, str) and 20 <= len(claim) <= 700,
              f"{where}: claim length outside 20..700")
        url = rec.get("source_url", "")
        check(isinstance(url, str) and url.startswith("https://"),
              f"{where}: source_url must be https ({url!r})")
        check(matches(DATE_RE, rec.get("source_date")),
              f"{where}: bad source_date {rec.get('source_date')!r}")
    else:
        note = rec.get("search_note", "")
        check(isinstance(note, str) and len(note) >= 20,
              f"{where}: search_note too short")


def validate_verdict(fid, v, where):
    check(isinstance(v, dict) and v.get("finding_id") == fid, f"{where}: finding_id mismatch")
    checks = v.get("checks", {}) if isinstance(v, dict) else {}
    for key in CHECKS:
        val = checks.get(key)
        check(val is True or val is False or val is None, f"{where}: bad check {key}")
    if isinstance(v, dict):
        reviewed = all(checks.get(k) is not None for k in CHECKS)
        check(v.get("reviewed") == reviewed, f"{where}: reviewed flag inconsistent")
        check(v.get("correct") == (reviewed and all(checks.get(k) is True for k in CHECKS)),
              f"{where}: correct flag inconsistent with checks")


def assert_schema_in_sync(schema):
    """Fail loudly if this validator drifts from schema/finding.schema.json."""
    defs = schema.get("$defs", {})
    check("finding" in defs, "schema: missing $defs.finding")
    check("nothingReliableFound" in defs, "schema: missing $defs.nothingReliableFound")
    props = defs.get("finding", {}).get("properties", {})
    check(set(props.get("classification", {}).get("enum", [])) == CLASSIFICATIONS,
          "schema drift: classification enum differs from validator")
    check(set(props.get("confidence", {}).get("enum", [])) == CONFIDENCES,
          "schema drift: confidence enum differs from validator")
    check(props.get("id", {}).get("pattern") == ID_RE.pattern,
          "schema drift: id pattern differs from validator")
    check(props.get("country", {}).get("pattern") == COUNTRY_RE.pattern,
          "schema drift: country pattern differs from validator")
    check(props.get("source_date", {}).get("pattern") == DATE_RE.pattern,
          "schema drift: source_date pattern differs from validator")
    check(set(defs.get("finding", {}).get("required", [])) == FINDING_REQUIRED,
          "schema drift: finding required fields differ from validator")
    check(set(defs.get("nothingReliableFound", {}).get("required", [])) == NOTHING_REQUIRED,
          "schema drift: nothingReliableFound required fields differ from validator")


GOOD_FINDING = {
    "id": "xx-001", "type": "finding", "country": "XX", "classification": "policy",
    "claim": "A sufficiently long test claim for the fixture self-test.",
    "source_url": "https://example.org/doc", "source_date": "2026-01-02",
    "confidence": "high", "retrieved_at": "2026-01-02T03:04:05Z",
}
GOOD_NOTHING = {
    "id": "xx-002", "type": "nothing_reliable_found", "country": "XX",
    "search_note": "Searched parliament portal and government site, nothing reliable.",
    "retrieved_at": "2026-01-02T03:04:05Z",
}
# (mutation, expected error fragment) — each must make validate_record complain.
BAD_MUTATIONS = [
    ({"id": "bad id"}, "bad id"),
    ({"id": "se-001\n"}, "bad id"),
    ({"country": "sve"}, "bad country"),
    ({"classification": "opinion"}, "bad classification"),
    ({"confidence": "certain"}, "bad confidence"),
    ({"claim": "too short"}, "claim length"),
    ({"claim": "x" * 701}, "claim length"),
    ({"source_url": "http://example.org"}, "source_url must be https"),
    ({"source_date": "02/01/2026"}, "bad source_date"),
    ({"source_date": 20260102}, "bad source_date"),
    ({"retrieved_at": None}, "bad retrieved_at"),
    ({"type": "rumour"}, "bad type"),
    ({"extra_field": 1}, "unexpected field"),
]
BAD_VERDICTS = [
    ({"finding_id": "other"}, "finding_id mismatch"),
    ({"checks": {k: (1 if k == CHECKS[0] else True) for k in CHECKS}}, "bad check"),
    ({"reviewed": False}, "reviewed flag inconsistent"),
    ({"correct": False}, "correct flag inconsistent"),
]


def collect(validate, *args):
    """Run a validation function against a scratch error list and return it."""
    saved = errors[:]
    errors[:] = []
    validate(*args, "probe")
    probe = errors[:]
    errors[:] = saved
    return probe


def self_test():
    """Prove the validator accepts good fixtures and rejects each bad mutation."""
    for rec, name in ((GOOD_FINDING, "good finding"), (GOOD_NOTHING, "good nothing-found")):
        check(not collect(validate_record, rec),
              f"self-test: {name} fixture unexpectedly rejected")

    for mutation, expected in BAD_MUTATIONS:
        probe = collect(validate_record, {**GOOD_FINDING, **mutation})
        check(any(expected in e for e in probe),
              f"self-test: mutation {mutation} not rejected (expected {expected!r})")

    good_verdict = {
        "finding_id": "xx-001",
        "checks": {k: True for k in CHECKS},
        "reviewed": True, "correct": True, "reviewer": "t", "note": "",
        "reviewed_at": "2026-01-02T03:04:05Z",
    }
    partial = {**good_verdict, "checks": {**good_verdict["checks"], CHECKS[0]: None},
               "reviewed": False, "correct": False}
    incorrect = {**good_verdict, "checks": {**good_verdict["checks"], CHECKS[0]: False},
                 "correct": False}
    for v, name in ((good_verdict, "correct"), (partial, "partial"), (incorrect, "incorrect")):
        check(not collect(validate_verdict, "xx-001", v),
              f"self-test: {name} verdict fixture unexpectedly rejected")
    for mutation, expected in BAD_VERDICTS:
        probe = collect(validate_verdict, "xx-001", {**good_verdict, **mutation})
        check(any(expected in e for e in probe),
              f"self-test: verdict mutation {mutation} not rejected (expected {expected!r})")


def load_json_file(path):
    name = os.path.basename(path)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except ValueError as e:
        check(False, f"{name}: not valid JSON ({e})")
        return None


def main():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    assert_schema_in_sync(schema)
    self_test()

    findings_files = sorted(glob.glob(FINDINGS_GLOB))
    check(bool(findings_files), f"no findings files match {FINDINGS_GLOB}")
    for path in findings_files:
        name = os.path.basename(path)
        records = load_json_file(path)
        if records is None:
            continue
        check(isinstance(records, list), f"{name}: top level must be an array")
        if not isinstance(records, list):
            continue
        ids = [r.get("id") for r in records if isinstance(r, dict)]
        check(len(ids) == len(set(ids)), f"{name}: duplicate ids")
        for i, rec in enumerate(records):
            validate_record(rec, f"{name}[{i}]")

    for path in sorted(glob.glob(VERDICTS_GLOB)):
        name = os.path.basename(path)
        verdicts = load_json_file(path)
        if verdicts is None:
            continue
        check(isinstance(verdicts, dict), f"{name}: top level must be an object")
        if not isinstance(verdicts, dict):
            continue
        for fid, v in verdicts.items():
            validate_verdict(fid, v, f"{name}[{fid}]")

    if errors:
        print(f"FAIL: {len(errors)} problem(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"OK: schema in sync, validator self-test passed, "
          f"{len(findings_files)} findings file(s) valid")


if __name__ == "__main__":
    main()
