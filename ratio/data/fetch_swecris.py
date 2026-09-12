#!/usr/bin/env python3
"""Census fetch: Swecris, the full atlas net with no cap.

Re-runs the Aging Funding Atlas's Swecris protocol (METHODOLOGY.md 3.3,
commit 2e59b27) against the live API, keeping every match instead of a
sample:

  - one CSV export per net phrase (13 phrases, English + Swedish),
    `GET /v1/scp/export?searchText=<phrase>`, paged;
  - a record's matched-phrase set is the set of phrases whose result sets
    contain it (matching happens API-side, exactly as the atlas did it);
  - broad-term rule: records matched ONLY by `aging` or `livslängd` are
    dropped (the atlas measured 73.3% ambiguous on that slice);
  - window: FundingStartDate year 2015-2025;
  - dedup key (ProjectId, FundingOrganisationId, FundingStartDate);
  - records with no title in either language are dropped.

Auth: the public test token published in the Swecris API documentation
(swagger at https://swecris-api.vr.se/index.html, linked from
https://www.vr.se/english/swecris.html). Data is openly accessible per VR;
attribute Swecris. Licence notes: ratio/data/CROSSCHECK.md and the atlas's
DATA_LICENCES.md (commit 2e59b27).

Usage: python3 ratio/data/fetch_swecris.py
Writes census_swecris.jsonl.gz + a funnel section in funnel.json.
Python 3 stdlib only.
"""

import csv
import io
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from census_common import (ABSTRACT_LIMIT, YEARS, FX_DATE, to_eur, today,
                           write_census, swecris_project_url)

csv.field_size_limit(10_000_000)  # abstracts overflow the 128 KiB default

API = "https://swecris-api.vr.se/v1/scp/export"
TOKEN = "VRSwecrisAPI2026-1"  # public test token from the API docs
PAGE_SIZE = 500

# The atlas net, METHODOLOGY.md section 3.3 (13 phrases, en + sv).
PHRASES = ["ageing", "aging", "senescence", "longevity", "healthspan",
           "geroscience", "inflammaging", "senolytic", "åldrande",
           "senescens", "livslängd", "hälsosamt åldrande",
           "biologiskt åldrande"]
# Records matched ONLY by these are excluded (atlas broad-term rule).
BROAD_ONLY = {"aging", "livslängd"}


def fetch_phrase(phrase: str) -> list:
    rows = []
    page = 1
    while True:
        q = urllib.parse.urlencode({"searchText": phrase, "page": page,
                                    "size": PAGE_SIZE})
        req = urllib.request.Request(
            f"{API}?{q}", headers={"Authorization": f"Bearer {TOKEN}"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            text = resp.read().decode("utf-8-sig")
        # stray NUL bytes appear in some abstracts; csv refuses them
        got = list(csv.DictReader(io.StringIO(text.replace("\x00", "")),
                                  delimiter=";"))
        rows.extend(got)
        if len(got) < PAGE_SIZE:
            return rows
        page += 1
        time.sleep(1)  # be polite to the public endpoint


def main():
    retrieved = today()
    by_key = {}
    fetched_rows = 0
    for phrase in PHRASES:
        rows = fetch_phrase(phrase)
        fetched_rows += len(rows)
        print(f"  {phrase!r}: {len(rows)} rows")
        for r in rows:
            key = (r["ProjectId"], r["FundingOrganisationId"],
                   r["FundingStartDate"])
            entry = by_key.setdefault(key, {"row": r, "phrases": set()})
            entry["phrases"].add(phrase)
        time.sleep(1)

    unique = len(by_key)
    precise = {k: v for k, v in by_key.items()
               if v["phrases"] - BROAD_ONLY}
    records, no_title, out_of_window, seen_ids = [], 0, 0, set()
    for (pid, org_id, start), entry in precise.items():
        r = entry["row"]
        year = int(start[:4]) if start[:4].isdigit() else None
        if year not in YEARS:
            out_of_window += 1
            continue
        title = (r.get("ProjectTitleEn") or r.get("ProjectTitleSv") or "").strip()
        if not title:
            no_title += 1
            continue
        record_id = f"swecris:{pid}"
        if record_id in seen_ids:  # ProjectId embeds the funder suffix, so
            record_id = f"swecris:{pid}:{org_id}"  # collisions are unexpected
        seen_ids.add(record_id)
        abstract = (r.get("ProjectAbstractEn") or r.get("ProjectAbstractSv")
                    or "").strip()[:ABSTRACT_LIMIT]
        try:
            amount = float(r["FundingsSek"]) if r.get("FundingsSek") else None
        except ValueError:
            amount = None
        records.append({
            "record_id": record_id,
            "source": "swecris",
            "source_id": pid,
            "title": title,
            "abstract": abstract,
            "funder": (r.get("FundingOrganisationNameEn")
                       or r.get("FundingOrganisationNameSv") or "").strip(),
            "country": "SE",
            "year": year,
            "amount": amount,
            "currency": "SEK",
            "amount_eur": to_eur(amount, "SEK"),
            "fx_date": FX_DATE,
            "url": swecris_project_url(pid),
            "extra": {
                "matched_phrases": sorted(entry["phrases"]),
                "funder_type": (r.get("FundingOrganisationTypeOfOrganisationEn")
                                or "").strip(),
                "coordinating_organisation":
                    (r.get("CoordinatingOrganisationNameEn") or "").strip(),
            },
            "retrieved_at": retrieved,
        })

    funnel = {
        "retrieved_at": retrieved,
        "endpoint": API,
        "auth": "Bearer public test token from the API docs",
        "net_phrases": PHRASES,
        "broad_only_excluded": sorted(BROAD_ONLY),
        "window_years": [YEARS[0], YEARS[-1]],
        "fetched_rows_all_phrases": fetched_rows,
        "unique_funding_rows": unique,
        "after_broad_term_rule": len(precise),
        "out_of_window": out_of_window,
        "dropped_no_title": no_title,
        "kept": len(records),
        "kept_without_amount": sum(1 for r in records
                                   if r["amount_eur"] is None),
    }
    write_census("swecris", records, funnel)
    print(f"funnel: {funnel}")


if __name__ == "__main__":
    main()
