#!/usr/bin/env python3
"""Shared pieces for the census fetch scripts (stdlib only).

The census re-runs the Aging Funding Atlas's per-source search nets
(data/Track3_C2/METHODOLOGY.md section 3) WITHOUT the atlas's 2,000-record
cap or stratified sampling, over the same 2015-2025 window. Same nets, same
window, complete coverage: the sample-versus-census comparison then isolates
sampling error instead of confounding it with a scope change.

FX uses the SAME fixed ECB reference-rate snapshot as the atlas
(2026-09-11), so EUR deltas between sample and census are never
exchange-rate artifacts. Rates from data/Track3_C2/output/metadata.json.

Matching semantics for local filters reuse classifier/validate_keywords.py's
compile_term - whole word/phrase, case-insensitive, '*' suffix wildcard -
the same semantics the lexicon and ratio/classify.py use.
"""

import gzip
import io
import json
import sys
from datetime import date, timezone
from pathlib import Path
from urllib.parse import quote

DATA_DIR = Path(__file__).resolve().parent
REPO_ROOT = DATA_DIR.parent.parent

sys.path.insert(0, str(REPO_ROOT / "classifier"))
from validate_keywords import compile_term  # noqa: E402

YEARS = list(range(2015, 2026))  # atlas window: 2015-2025 inclusive

# ECB reference rates, snapshot 2026-09-11 (the atlas's fixed snapshot;
# source https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml).
FX_DATE = "2026-09-11"
RATES_PER_EUR = {"USD": 1.1592, "DKK": 7.4748, "GBP": 0.85815,
                 "SEK": 11.2373, "NOK": 10.7805, "EUR": 1.0}

ABSTRACT_LIMIT = 6000  # chars, same truncation as the atlas


def to_eur(amount: "float | None", currency: str) -> "float | None":
    if amount is None:
        return None
    return round(amount / RATES_PER_EUR[currency], 2)


def today() -> str:
    return date.today().isoformat()


def write_census(source: str, records: list, funnel: dict) -> Path:
    """Write census_<source>.jsonl.gz (sorted by record_id for stable
    diffs) and merge this source's funnel section into funnel.json."""
    out = DATA_DIR / f"census_{source}.jsonl.gz"
    records = sorted(records, key=lambda r: r["record_id"])
    # GzipFile with mtime=0 keeps the archive byte-identical across re-runs
    # of unchanged data (gzip.open cannot set mtime on Python 3.9)
    with gzip.GzipFile(out, "wb", mtime=0) as raw:
        with io.TextIOWrapper(raw, encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    funnel_path = DATA_DIR / "funnel.json"
    all_funnels = (json.loads(funnel_path.read_text(encoding="utf-8"))
                   if funnel_path.is_file() else {})
    all_funnels[source] = funnel
    funnel_path.write_text(
        json.dumps(all_funnels, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"wrote {out} ({len(records)} records); funnel.json updated")
    return out


def swecris_project_url(project_id: str) -> str:
    """SweCRIS uses a hash router; searchText is an API parameter, not a UI route.

    Verified against the official portal's /project/:projectId route on
    2026-09-12. Encode the project ID as one path segment.
    """
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("SweCRIS project ID is required")
    return "https://www.vr.se/english/swecris.html#/project/" + quote(project_id.strip(), safe="")


def source_url(record: dict) -> str:
    if record.get("source") == "swecris":
        project_id = record.get("source_id")
        if not project_id:
            record_id = record.get("record_id", "")
            if record_id.startswith("swecris:"):
                project_id = record_id.split(":", 2)[1]
        return swecris_project_url(project_id)
    return record.get("url", "")


def load_census(source: str) -> list:
    path = DATA_DIR / f"census_{source}.jsonl.gz"
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    for row in rows:
        row["url"] = source_url(row)
    return rows
