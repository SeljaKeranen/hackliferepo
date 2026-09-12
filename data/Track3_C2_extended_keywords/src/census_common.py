"""Shared constants and helpers for the extended-keyword census fetch."""

import hashlib
import json
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parents[1]
RAW = OUT / "raw"
PROC = OUT / "processed"
RESULT = OUT / "output"

WINDOW = list(range(2015, 2027))
USER_AGENT = "LongviewFunding/1.0 (extended-keyword census)"
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
FALLBACK_FX = {"date": "2026-09-11", "USD": 1.1592, "SEK": 11.2373,
               "note": "documented Track3_C2 rates, ECB fetch unavailable"}

T1_EN = ["senescence", "senolytic", "senolytics", "geroscience", "healthspan",
         "inflammaging", "epigenetic clock", "longevity", "lifespan"]
T2_EN = ["aging", "ageing", "elderly", "older adults", "geriatric",
         "gerontology", "age-related", "healthy aging"]
SOCIAL_EN = ["social isolation", "loneliness", "retirement", "pension",
             "older workers", "labor market", "living conditions",
             "population aging", "aging society", "social relations",
             "social network", "living alone"]
T1_SV = ["senescens", "livslängd"]
T2_SV = ["åldrande", "äldre", "ålderssjukdom", "äldreomsorg", "demens",
         "hälsosamt åldrande"]
SOCIAL_SV = ["socioekonomisk"]

BROAD_ONLY_SV = {"aging", "livslängd"}

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def quote(term: str) -> str:
    return f'"{term}"' if " " in term else term


def fetch_fx(s) -> dict:
    try:
        r = s.get(ECB_URL, timeout=45)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        date, rates = "", {}
        for cube in root.iter(
                "{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube"):
            if cube.get("time"):
                date = cube.get("time")
            if cube.get("currency") in ("USD", "SEK"):
                rates[cube.get("currency")] = float(cube.get("rate"))
        if {"USD", "SEK"} <= set(rates):
            return {"date": date, "USD": rates["USD"], "SEK": rates["SEK"],
                    "source": "ECB eurofxref-daily", "retrieved_at": now()}
    except (requests.RequestException, ET.ParseError, ValueError) as exc:
        print(f"FX fetch failed ({type(exc).__name__}); using fallback")
    return dict(FALLBACK_FX)


def cached_json(s, method, url, cache_dir, payload=None, params=None,
                headers=None):
    request = {"method": method, "url": url, "payload": payload,
               "params": params}
    path = cache_dir / (digest(request) + ".json")
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8")), "cache"
    for attempt in range(6):
        try:
            r = s.request(method, url, json=payload, params=params,
                          headers=headers, timeout=120)
            r.raise_for_status()
            envelope = {"retrieved_at": now(), "endpoint": url,
                        "request": request, "status": r.status_code,
                        "response_hash": hashlib.sha256(r.content).hexdigest(),
                        "data": r.json()}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(envelope, ensure_ascii=False),
                            encoding="utf-8")
            return envelope, "live"
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 429:
                wait = int(exc.response.headers.get("Retry-After") or 30)
                time.sleep(min(max(wait, 5), 120))
                continue
            if attempt >= 3:
                raise
            time.sleep(2 ** attempt)
        except (requests.RequestException, ValueError):
            if attempt >= 3:
                raise
            time.sleep(2 ** attempt)


def cached_bytes(s, url, cache_dir, params=None, headers=None, suffix=".csv"):
    request = {"url": url, "params": params}
    key = digest(request)
    path = cache_dir / (key + suffix)
    meta_path = cache_dir / (key + ".meta.json")
    if path.is_file():
        return path.read_bytes(), json.loads(
            meta_path.read_text(encoding="utf-8")), "cache"
    for attempt in range(6):
        try:
            r = s.get(url, params=params, headers=headers, timeout=180)
            r.raise_for_status()
            meta = {"retrieved_at": now(), "endpoint": url, "request": request,
                    "status": r.status_code,
                    "response_hash": hashlib.sha256(r.content).hexdigest()}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(r.content)
            meta_path.write_text(json.dumps(meta, ensure_ascii=False),
                                 encoding="utf-8")
            return r.content, meta, "live"
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 429:
                wait = int(exc.response.headers.get("Retry-After") or 30)
                time.sleep(min(max(wait, 5), 120))
                continue
            if attempt >= 3:
                raise
            time.sleep(2 ** attempt)
        except requests.RequestException:
            if attempt >= 3:
                raise
            time.sleep(2 ** attempt)


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
