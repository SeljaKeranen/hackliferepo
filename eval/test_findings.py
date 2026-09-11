#!/usr/bin/env python3
"""Validate eval/findings/*.json against schema/finding.schema.json.

Stdlib only: the schema's constraints are enforced with structural asserts
mirroring the JSON Schema (kept in sync by hand; the schema file is the
contract, this script is the executable check).

Run: python3 eval/test_findings.py
"""
import json
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "schema", "finding.schema.json")
FINDINGS_GLOB = os.path.join(ROOT, "eval", "findings", "*.json")
VERDICTS_GLOB = os.path.join(ROOT, "eval", "verdicts", "*.verdicts.json")

CLASSIFICATIONS = {"policy", "legislation", "funding", "strategy", "political statement"}
CONFIDENCES = {"high", "medium", "low"}
CHECKS = ("source_resolves", "date_correct", "classification_correct", "claim_supported")
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

    check(ID_RE.match(rec.get("id", "")), f"{where}: bad id {rec.get('id')!r}")
    check(COUNTRY_RE.match(rec.get("country", "")), f"{where}: bad country {rec.get('country')!r}")
    check(TIMESTAMP_RE.match(rec.get("retrieved_at", "")),
          f"{where}: bad retrieved_at {rec.get('retrieved_at')!r}")

    if rtype == "finding":
        check(rec.get("classification") in CLASSIFICATIONS,
              f"{where}: bad classification {rec.get('classification')!r}")
        check(rec.get("confidence") in CONFIDENCES,
              f"{where}: bad confidence {rec.get('confidence')!r}")
        claim = rec.get("claim", "")
        check(isinstance(claim, str) and 20 <= len(claim) <= 700,
              f"{where}: claim length {len(claim)} outside 20..700")
        check(str(rec.get("source_url", "")).startswith("https://"),
              f"{where}: source_url must be https ({rec.get('source_url')!r})")
        check(DATE_RE.match(rec.get("source_date", "")),
              f"{where}: bad source_date {rec.get('source_date')!r}")
    else:
        note = rec.get("search_note", "")
        check(isinstance(note, str) and len(note) >= 20,
              f"{where}: search_note too short")


def main():
    # The schema file itself must parse and declare both record shapes.
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    check("finding" in schema.get("$defs", {}), "schema: missing $defs.finding")
    check("nothingReliableFound" in schema.get("$defs", {}),
          "schema: missing $defs.nothingReliableFound")

    findings_files = sorted(glob.glob(FINDINGS_GLOB))
    check(bool(findings_files), f"no findings files match {FINDINGS_GLOB}")
    for path in findings_files:
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            records = json.load(f)
        check(isinstance(records, list), f"{name}: top level must be an array")
        if not isinstance(records, list):
            continue
        ids = [r.get("id") for r in records if isinstance(r, dict)]
        check(len(ids) == len(set(ids)), f"{name}: duplicate ids")
        for i, rec in enumerate(records):
            validate_record(rec, f"{name}[{i}]")

    # Verdicts files, when present, must parse and keep the expected shape.
    for path in sorted(glob.glob(VERDICTS_GLOB)):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            verdicts = json.load(f)
        check(isinstance(verdicts, dict), f"{name}: top level must be an object")
        if not isinstance(verdicts, dict):
            continue
        for fid, v in verdicts.items():
            where = f"{name}[{fid}]"
            check(isinstance(v, dict) and v.get("finding_id") == fid,
                  f"{where}: finding_id mismatch")
            checks = v.get("checks", {}) if isinstance(v, dict) else {}
            for key in CHECKS:
                check(checks.get(key) in (True, False, None), f"{where}: bad check {key}")
            if isinstance(v, dict):
                reviewed = all(checks.get(k) is not None for k in CHECKS)
                check(v.get("reviewed") == reviewed, f"{where}: reviewed flag inconsistent")
                check(v.get("correct") == (reviewed and all(checks.get(k) is True for k in CHECKS)),
                      f"{where}: correct flag inconsistent with checks")

    if errors:
        print(f"FAIL: {len(errors)} problem(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    n_files = len(findings_files)
    print(f"OK: {n_files} findings file(s) valid against the schema constraints")


if __name__ == "__main__":
    main()
