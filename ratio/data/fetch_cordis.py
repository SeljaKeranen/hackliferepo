#!/usr/bin/env python3
"""Census fetch: CORDIS, from the official bulk project dumps.

The Aging Funding Atlas queried the CORDIS search API phrase by phrase
(METHODOLOGY.md 3.2, commit 2e59b27). The census instead downloads the
Publications Office's complete project dumps - every FP7, Horizon 2020 and
Horizon Europe project - and applies the same 13-phrase net locally over
title + objective, so coverage no longer depends on the search index:

  - dumps: cordis-{fp7,h2020,HORIZON}projects-csv.zip from
    https://cordis.europa.eu/data/ (CC BY 4.0, (c) European Union);
  - net: the atlas's 13 CORDIS phrases, matched with the lexicon's
    compile_term semantics (whole word/phrase, case-insensitive,
    '*' suffix wildcard) over lowercased title + objective;
  - window: startDate year 2015-2025 (the atlas rule);
  - amount: ecMaxContribution (EUR, the EU contribution - same field the
    atlas used); country: coordinator organisation's country from the
    dump's organization.csv (the atlas used a first-organisation proxy).

Only the filtered ageing-relevant subset is committed; the raw dumps stay
in a local cache directory (data/cordis_dumps/, gitignored). Their URLs,
retrieval date and SHA-256 checksums are recorded in funnel.json.

Usage: python3 ratio/data/fetch_cordis.py [--dump-dir DIR] [--no-download]
Writes census_cordis.jsonl.gz + a funnel section in funnel.json.
Python 3 stdlib only.
"""

import argparse
import csv
import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from census_common import (ABSTRACT_LIMIT, REPO_ROOT, YEARS, FX_DATE,
                           to_eur, today, write_census, compile_term)

csv.field_size_limit(10_000_000)

DUMPS = {
    "fp7": "https://cordis.europa.eu/data/cordis-fp7projects-csv.zip",
    "h2020": "https://cordis.europa.eu/data/cordis-h2020projects-csv.zip",
    "horizon": "https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip",
}
DEFAULT_DUMP_DIR = REPO_ROOT / "data" / "cordis_dumps"

# The atlas net, METHODOLOGY.md section 3.2 (13 phrases).
PHRASES = ["cellular senescence", "senescence", "geroscience", "healthspan",
           "health span", "senolytic", "inflammaging", "biological ageing",
           "biological aging", "cellular ageing", "anti-ageing",
           "ageing research", "longevity"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    print(f"  downloading {url}")
    with urllib.request.urlopen(url, timeout=600) as resp:
        dest.write_bytes(resp.read())


def read_zip_csv(zpath: Path, name_part: str) -> list:
    """Read the first CSV member whose name contains name_part."""
    with zipfile.ZipFile(zpath) as zf:
        names = [n for n in zf.namelist()
                 if name_part in Path(n).name.lower()
                 and n.lower().endswith(".csv")]
        if not names:
            raise SystemExit(f"{zpath}: no CSV member matching {name_part!r} "
                             f"in {zf.namelist()}")
        with zf.open(names[0]) as fh:
            text = io.TextIOWrapper(fh, encoding="utf-8-sig")
            return list(csv.DictReader(text, delimiter=";"))


def parse_amount(raw: str) -> "float | None":
    """CORDIS dumps write decimals with a comma (e.g. '6999962,25')."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dump-dir", type=Path, default=DEFAULT_DUMP_DIR)
    ap.add_argument("--no-download", action="store_true",
                    help="use existing dump files, fail if missing")
    args = ap.parse_args()
    args.dump_dir.mkdir(parents=True, exist_ok=True)

    retrieved = today()
    patterns = [(p, compile_term(p)) for p in PHRASES]
    dump_meta = {}
    scanned = 0
    matched = {}       # project id -> {"row", "phrases", "programme"}
    coordinator = {}   # project id -> country
    for prog, url in DUMPS.items():
        zpath = args.dump_dir / Path(url).name
        if not zpath.is_file():
            if args.no_download:
                raise SystemExit(f"missing dump {zpath} (--no-download)")
            download(url, zpath)
        dump_meta[prog] = {"url": url, "sha256": sha256(zpath),
                           "bytes": zpath.stat().st_size,
                           "retrieved_at": retrieved}
        projects = read_zip_csv(zpath, "project")
        scanned += len(projects)
        prog_matched = 0
        for r in projects:
            text = ((r.get("title") or "") + " "
                    + (r.get("objective") or "")).lower()
            hits = [p for p, pat in patterns if pat.search(text)]
            if not hits:
                continue
            pid = r["id"]
            matched[pid] = {"row": r, "phrases": hits, "programme": prog}
            prog_matched += 1
        for org in read_zip_csv(zpath, "organization"):
            if (org.get("role") or "").strip().lower() == "coordinator":
                pid = org.get("projectID") or org.get("projectId") or ""
                if pid and pid not in coordinator:
                    coordinator[pid] = (org.get("country") or "").strip()
        print(f"  {prog}: {len(projects)} projects, {prog_matched} net-matched")

    records, out_of_window = [], 0
    for pid, entry in matched.items():
        r = entry["row"]
        start = (r.get("startDate") or "").strip()
        year = int(start[:4]) if start[:4].isdigit() else None
        if year not in YEARS:
            out_of_window += 1
            continue
        amount = parse_amount(r.get("ecMaxContribution"))
        records.append({
            "record_id": f"cordis:{pid}",
            "source": "cordis",
            "source_id": pid,
            "title": (r.get("title") or "").strip(),
            "abstract": (r.get("objective") or "").strip()[:ABSTRACT_LIMIT],
            "funder": "European Commission",
            "country": coordinator.get(pid, ""),
            "year": year,
            "amount": amount,
            "currency": "EUR",
            "amount_eur": to_eur(amount, "EUR"),
            "fx_date": FX_DATE,
            "url": f"https://cordis.europa.eu/project/id/{pid}",
            "extra": {
                "matched_phrases": sorted(entry["phrases"]),
                "programme": entry["programme"],
                "acronym": (r.get("acronym") or "").strip(),
                "status": (r.get("status") or "").strip(),
                "total_cost": parse_amount(r.get("totalCost")),
            },
            "retrieved_at": retrieved,
        })

    funnel = {
        "retrieved_at": retrieved,
        "dumps": dump_meta,
        "net_phrases": PHRASES,
        "match_fields": "title + objective (compile_term semantics)",
        "window_years": [YEARS[0], YEARS[-1]],
        "projects_scanned": scanned,
        "net_matched": len(matched),
        "out_of_window": out_of_window,
        "kept": len(records),
        "kept_without_amount": sum(1 for r in records
                                   if r["amount_eur"] is None),
    }
    write_census("cordis", records, funnel)
    print(f"funnel: {funnel}")


if __name__ == "__main__":
    main()
