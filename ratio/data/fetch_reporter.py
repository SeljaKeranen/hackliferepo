#!/usr/bin/env python3
"""Census fetch: NIH RePORTER, the full atlas net with no cap or sampling.

Re-runs the Aging Funding Atlas's RePORTER protocol (METHODOLOGY.md 3.1,
commit 2e59b27) against API v2, keeping every match instead of the
stratified 2,000-record sample:

  - for each of the 8 net phrases and each fiscal year 2015-2025, POST
    /v2/projects/search with advanced_text_search {operator: "and",
    search_field: "projecttitle,abstracttext"};
  - pagination offset/limit at 500 per page, NO per-query ceiling (the
    atlas stopped at 2,000 per phrase-year, then sampled);
  - dedup by ProjectNum across phrase-years; a record's matched-phrase set
    is the set of phrases whose result sets contain it. When the same
    ProjectNum appears as parent and subproject rows, the parent row
    (subproject_id null, full award amount) is kept;
  - records with no abstract are dropped, as in the atlas, and counted.

NIH RePORTER is U.S. federal government data (generally public domain);
attribute NIH RePORTER. One request per second, per the API guidance.

Usage: python3 ratio/data/fetch_reporter.py
Writes census_reporter.jsonl.gz + a funnel section in funnel.json.
Python 3 stdlib only.
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from census_common import (ABSTRACT_LIMIT, YEARS, FX_DATE, to_eur, today,
                           write_census)

API = "https://api.reporter.nih.gov/v2/projects/search"
PAGE_SIZE = 500

# The atlas net, METHODOLOGY.md section 3.1 (8 phrases).
PHRASES = ["cellular senescence", "biological aging", "biological ageing",
           "geroscience", "healthspan", "inflammaging", "senolytic",
           "epigenetic clock"]

INCLUDE_FIELDS = [
    "ProjectNum", "SubprojectId", "ProjectTitle", "AbstractText",
    "FiscalYear", "AwardAmount", "Organization", "AgencyIcAdmin",
    "ProjectStartDate", "ProjectEndDate", "ActivityCode",
]


def post(payload: dict, retries: int = 5) -> dict:
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(retries):
        req = urllib.request.Request(
            API, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - retry transient API errors
            wait = 5 * (attempt + 1)
            print(f"    retry {attempt + 1}/{retries} after {exc} "
                  f"(sleep {wait}s)", file=sys.stderr)
            time.sleep(wait)
    raise SystemExit(f"RePORTER gave no answer after {retries} retries")


def fetch_phrase_year(phrase: str, year: int) -> list:
    rows, offset = [], 0
    while True:
        data = post({
            "criteria": {
                "advanced_text_search": {
                    "operator": "and",
                    "search_field": "projecttitle,abstracttext",
                    "search_text": phrase,
                },
                "fiscal_years": [year],
            },
            "include_fields": INCLUDE_FIELDS,
            "offset": offset,
            "limit": PAGE_SIZE,
        })
        got = data.get("results", [])
        rows.extend(got)
        total = data.get("meta", {}).get("total", 0)
        offset += PAGE_SIZE
        time.sleep(1)  # 1 req/s per API guidance
        if offset >= total or not got:
            return rows


def main():
    retrieved = today()
    by_num = {}
    fetched_rows = 0
    for phrase in PHRASES:
        phrase_rows = 0
        for year in YEARS:
            rows = fetch_phrase_year(phrase, year)
            phrase_rows += len(rows)
            for r in rows:
                num = r.get("project_num")
                if not num:
                    continue
                entry = by_num.get(num)
                if entry is None:
                    by_num[num] = {"row": r, "phrases": {phrase}}
                else:
                    entry["phrases"].add(phrase)
                    # prefer the parent row: full award, not one subproject
                    if (entry["row"].get("subproject_id")
                            and not r.get("subproject_id")):
                        entry["row"] = r
        fetched_rows += phrase_rows
        print(f"  {phrase!r}: {phrase_rows} rows "
              f"({len(by_num)} unique so far)")

    no_abstract, records = 0, []
    for num, entry in by_num.items():
        r = entry["row"]
        abstract = (r.get("abstract_text") or "").strip()
        if not abstract:
            no_abstract += 1
            continue
        org = r.get("organization") or {}
        agency = r.get("agency_ic_admin") or {}
        amount = r.get("award_amount")
        records.append({
            "record_id": f"reporter:{num}",
            "source": "reporter",
            "source_id": num,
            "title": (r.get("project_title") or "").strip(),
            "abstract": abstract[:ABSTRACT_LIMIT],
            "funder": (agency.get("name") or "NIH").strip(),
            "country": "US",
            "year": r.get("fiscal_year"),
            "amount": amount,
            "currency": "USD",
            "amount_eur": to_eur(amount, "USD"),
            "fx_date": FX_DATE,
            "url": f"https://reporter.nih.gov/project-details/{num}",
            "extra": {
                "matched_phrases": sorted(entry["phrases"]),
                "organization": (org.get("org_name") or "").strip(),
                "activity_code": r.get("activity_code"),
                "subproject_id": r.get("subproject_id"),
            },
            "retrieved_at": retrieved,
        })

    funnel = {
        "retrieved_at": retrieved,
        "endpoint": API,
        "auth": "none (public API)",
        "net_phrases": PHRASES,
        "window_fiscal_years": [YEARS[0], YEARS[-1]],
        "fetched_rows_all_queries": fetched_rows,
        "unique_project_nums": len(by_num),
        "dropped_no_abstract": no_abstract,
        "kept": len(records),
        "kept_without_amount": sum(1 for r in records
                                   if r["amount_eur"] is None),
    }
    write_census("reporter", records, funnel)
    print(f"funnel: {funnel}")


if __name__ == "__main__":
    main()
