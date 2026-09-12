#!/usr/bin/env python3
"""Adjudicate ambiguous grants with a chat-completions API.

Reads the pending ambiguous records from ratio/output/labels.jsonl (minus
anything already in the output file), joins them to the census texts, asks
the model for a JSON verdict {label, quote, confidence, reason}, verifies the
quote against the record text, and appends results to the output file so runs
are resumable. Raw API responses are cached per record.

Usage:
    set DEEPSEEK_API_KEY=...        (or pass --key-file)
    python3 ratio/adjudicate.py --model deepseek-v4.1
    python3 ratio/adjudicate.py --limit 20 --dry-run
    python3 ratio/adjudicate.py --region US --limit 100 --workers 4

The API key is read from the environment or a file outside the repository and
is never written anywhere by this script. Python 3 stdlib + requests only.
"""

import argparse
import concurrent.futures as futures
import hashlib
import json
import os
import re
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "data"))
import census_common  # noqa: E402

LABELS = {"fundamental_aging", "intervention", "age_related_disease", "care",
          "social_population_aging", "not_relevant", "ambiguous"}
SOURCES = ("swecris", "cordis", "reporter")
SYSTEM_PROMPT = """You classify public research grants for a longevity funding \
analysis. Read the grant title and abstract, then return JSON:
{"label": ..., "quote": ..., "confidence": "high|medium|low", "reason": ...}

Step 0 - relevance gate. If the record is about material, component, \
infrastructure, equipment or animal/plant/ecology ageing (batteries, polymers, \
bridges, pipes, clouds, livestock, forests), or has no human ageing objective \
at all, use not_relevant even if the word ageing/ageing/longevity appears.
If the record is on-topic (human ageing) but the text does not let you decide, \
use ambiguous.

Substantive categories (choose one):
- fundamental_aging: ageing mechanisms themselves (senescence, epigenetic \
clocks, inflammaging, proteostasis, stem-cell exhaustion, mitochondrial \
dysfunction, comparative longevity, geroscience).
- intervention: research developing or testing an intervention whose stated \
objective targets ageing biology, senescence, lifespan or healthspan \
(geroprotectors, senolytics, rapamycin, metformin as geroprotection, dietary \
restriction for lifespan). A study of an intervention's mechanism is \
fundamental_aging.
- age_related_disease: a specific age-related disease (Alzheimer, cancer, \
cardiovascular disease, diabetes, osteoporosis, sarcopenia, clinical frailty, \
age-related sensory loss). Disease vaccines/therapies aimed at older adults \
are age_related_disease, not the numerator.
- care: elderly care, long-term care, caregiving, social services, care \
delivery research; not clinical treatment.
- social_population_aging: social, behavioural, psychological, economic or \
population-ageing research (loneliness, housing, retirement, life course, \
age-friendly environments, ageing societies), including when the outcome is \
wellbeing of older people.

The quote must be a verbatim substring (<=200 characters) of the title or \
abstract that justifies the label. Return JSON only, no markdown."""
USER_TEMPLATE = "record_id: {record_id}\ntitle: {title}\n\nabstract:\n{abstract}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_key(args) -> str:
    if args.key_file:
        key = Path(args.key_file).read_text(encoding="utf-8").strip()
        if key:
            return key.splitlines()[0].strip()
    key = os.environ.get(args.key_env, "").strip()
    if not key:
        sys.exit(f"no API key: set {args.key_env} or pass --key-file")
    return key


def load_corpus() -> dict:
    texts = {}
    for source in SOURCES:
        for rec in census_common.load_census(source):
            texts[rec["record_id"]] = rec
    return texts


def pending(region, done):
    rows = []
    for line in (HERE / "output" / "labels.jsonl").open(encoding="utf-8"):
        rec = json.loads(line)
        if rec["label"] != "ambiguous" or rec["record_id"] in done:
            continue
        if region and rec["region"] != region:
            continue
        rows.append(rec)
    rows.sort(key=lambda r: -(r["amount_eur"] or 0))
    return rows


def make_prompt(record):
    abstract = (record.get("abstract") or "")
    if len(abstract) > 3000:
        abstract = abstract[:3000] + "..."
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(
                record_id=record["record_id"], title=record["title"],
                abstract=abstract)}]


def parse_content(content: str) -> dict:
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        text = match.group(0)
    return json.loads(text)


def valid_quote(quote: str, record: dict) -> bool:
    if not quote or len(quote) > 400:
        return False
    text = re.sub(r"\s+", " ", ((record.get("title") or "") + " "
                                + (record.get("abstract") or "")).lower())
    return re.sub(r"\s+", " ", quote.lower()) in text


def call_api(session, args, record, cache_dir):
    cache = cache_dir / (hashlib.sha256(record["record_id"].encode())
                         .hexdigest()[:20] + ".json")
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    url = args.base_url.rstrip("/") + "/chat/completions"
    payload = {"model": args.model, "messages": make_prompt(record),
               "temperature": 0.0, "max_tokens": args.max_tokens}
    last_error = None
    for attempt in range(4):
        try:
            response = session.post(url, json=payload, timeout=180)
            if response.status_code == 429 or response.status_code >= 500:
                time.sleep(min(60, 5 * (2 ** attempt)))
                last_error = f"HTTP {response.status_code}"
                continue
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            parsed = parse_content(content)
            result = {"record_id": record["record_id"], **parsed,
                      "raw_model": body.get("model"),
                      "usage": body.get("usage"), "retrieved_at": now()}
            result["quote_valid"] = valid_quote(str(parsed.get("quote", "")),
                                                record)
            if result["quote_valid"]:
                cache.write_text(json.dumps(result, ensure_ascii=False),
                                 encoding="utf-8")
                return result
            last_error = "quote not found in record text"
            payload["max_tokens"] = min(4000, payload["max_tokens"] * 2)
        except json.JSONDecodeError as exc:
            last_error = f"JSONDecodeError: {exc}"
            payload["max_tokens"] = min(4000, payload["max_tokens"] * 2)
            time.sleep(1)
        except (requests.RequestException, ValueError, KeyError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(min(30, 2 ** attempt))
    return {"record_id": record["record_id"], "error": str(last_error),
            "label": "ambiguous", "quote": "", "quote_valid": False,
            "confidence": "low",
            "reason": "API adjudication failed; left ambiguous."}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", ""))
    ap.add_argument("--base-url",
                    default=os.environ.get("DEEPSEEK_BASE_URL",
                                           "https://api.deepseek.com"))
    ap.add_argument("--key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--key-file", default=None)
    ap.add_argument("--region", choices=["SE", "EU", "US"], default=None)
    ap.add_argument("--input", default=None,
                    help="JSONL with record_id fields to adjudicate; "
                         "overrides the pending/region selection")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--out", default=str(HERE / "output"
                                         / "adjudicated_api.jsonl"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.model:
        sys.exit("--model is required (or set DEEPSEEK_MODEL)")

    out_path = Path(args.out)
    done = set()
    if out_path.is_file():
        for line in out_path.open(encoding="utf-8"):
            rec = json.loads(line)
            if "error" not in rec:
                done.add(rec["record_id"])
    texts = load_corpus()
    if args.input:
        ids = [json.loads(line)["record_id"]
               for line in open(args.input, encoding="utf-8") if line.strip()]
        tasks = [texts[i] for i in ids if i in texts and i not in done]
    else:
        tasks = [texts[r["record_id"]] for r in pending(args.region, done)
                 if r["record_id"] in texts]
    tasks.sort(key=lambda r: -(r.get("amount_eur") or 0))
    if args.limit:
        tasks = tasks[:args.limit]
    print(f"pending: {len(tasks)} records | already done: {len(done)} | "
          f"model: {args.model}")
    if not tasks:
        return 0
    if args.dry_run:
        for rec in tasks[:3]:
            print("\n---", rec["record_id"])
            print(make_prompt(rec)[1]["content"][:800])
        print(f"\ndry run: {len(tasks)} tasks would be sent")
        return 0

    key = load_key(args)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {key}",
                            "Content-Type": "application/json"})
    cache_dir = HERE / "data" / "llm_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    write_lock = threading.Lock()
    counts, errors, valid = Counter(), 0, 0
    with out_path.open("a", encoding="utf-8") as out, \
            futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {pool.submit(call_api, session, args, rec,
                                  cache_dir): rec for rec in tasks}
        for i, future in enumerate(futures.as_completed(future_map), 1):
            result = future.result()
            with write_lock:
                out.write(json.dumps(result, ensure_ascii=False) + "\n")
                out.flush()
            counts[result.get("label", "error")] += 1
            errors += "error" in result
            valid += bool(result.get("quote_valid"))
            if i % 25 == 0 or i == len(tasks):
                print(f"{i}/{len(tasks)} done | labels "
                      f"{dict(counts.most_common())} | "
                      f"quote_valid {valid} | failed {errors}", flush=True)
    print(f"\nwrote {out_path}")
    print(f"labels: {dict(counts.most_common())} | quote_valid "
          f"{valid}/{len(tasks)} | errors {errors}")
    rows = [json.loads(line) for line in out_path.open(encoding="utf-8")]
    latest = {}
    for rec in rows:
        if "error" not in rec:
            latest[rec["record_id"]] = rec
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in latest.values():
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"compacted {out_path.name}: {len(latest)} successful records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
