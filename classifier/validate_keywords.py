#!/usr/bin/env python3
"""Validate the grant-search keyword lexicon against the Aging Funding Atlas.

The atlas (2,944 records: swecris + cordis + nih_reporter) was added in commit
2e59b27 and lives in the tree at data/Track3_C2/output/ (commit 4061bff deleted
a duplicate top-level Track3_C2/ copy, not this one). The default data source
is that live directory; if it is ever removed, the identical snapshot can be
recovered from history:

    git show 2e59b27:data/Track3_C2/output/swecris.csv      > <dir>/swecris.csv
    git show 2e59b27:data/Track3_C2/output/cordis.csv       > <dir>/cordis.csv
    git show 2e59b27:data/Track3_C2/output/nih_reporter.csv > <dir>/nih_reporter.csv

Usage:
    python3 classifier/validate_keywords.py                 # live tree, else git show
    python3 classifier/validate_keywords.py --data-dir DIR  # explicit CSV directory
    python3 classifier/validate_keywords.py --update        # rewrite stats in keywords.json
    python3 classifier/validate_keywords.py --self-test     # unit checks, no corpus needed

Exit status 0 means every stored stat matches a recomputation and every kept
keyword clears its threshold (this holds for --update too: the file is written
first, then threshold violations are still reported and fail the run).
Python 3 stdlib only; the git binary is needed only for the history fallback.

Matching semantics (shared by this script and KEYWORDS.md): a keyword matches a
record if it appears in the lowercased title + llm_quote as a whole word or
phrase; a ``*`` at the end of a word matches any word-character suffix
(``senolytic*`` matches "senolytics"); spaces match any whitespace run; other
characters, including hyphens, match literally.

Precision proxy: the share of a keyword's matching records whose llm_category
equals the keyword's category. The LLM labels are unverified, so this is a
proxy, not ground truth; the 30-record human benchmark remains the real test.

The social_population_aging category postdates the atlas's LLM label
vocabulary: its records were folded into 'ambiguous' (see KEYWORDS.md), so
that label is the precision/coverage proxy for the category (PROXY_LABEL).
"""

import argparse
import collections
import csv
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ATLAS_COMMIT = "2e59b27"
ATLAS_FILES = ["swecris.csv", "cordis.csv", "nih_reporter.csv"]
ATLAS_PREFIX = "data/Track3_C2/output/"
EXPECTED_RECORDS = 2944
REQUIRED_COLUMNS = {"record_id", "source", "llm_category", "title", "llm_quote"}
CATEGORIES = ["fundamental_aging", "intervention", "age_related_disease", "care",
              "social_population_aging"]
# categories whose precision/coverage proxy is a different llm_category label
PROXY_LABEL = {"social_population_aging": "ambiguous"}
LOW_EVIDENCE_HITS = 5   # below this, a kept keyword is flagged low_evidence
MAX_TERM_LENGTH = 60
MAX_WILDCARDS = 3


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def recover_atlas(dest: Path) -> None:
    for name in ATLAS_FILES:
        try:
            blob = subprocess.run(
                ["git", "show", f"{ATLAS_COMMIT}:{ATLAS_PREFIX}{name}"],
                check=True, capture_output=True, cwd=repo_root(),
            ).stdout
        except (subprocess.CalledProcessError, OSError) as exc:
            stderr = getattr(exc, "stderr", b"") or b""
            sys.exit(f"cannot recover {name} from commit {ATLAS_COMMIT}: "
                     f"{exc} {stderr.decode(errors='replace').strip()}")
        (dest / name).write_bytes(blob)


def load_rows(data_dir: Path) -> list:
    rows = []
    for name in ATLAS_FILES:
        path = data_dir / name
        if not path.is_file():
            sys.exit(f"missing atlas file: {path}")
        with open(path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing:
                sys.exit(f"{path}: missing column(s) {sorted(missing)}")
            rows.extend(reader)
    if len(rows) != EXPECTED_RECORDS:
        sys.exit(f"expected {EXPECTED_RECORDS} atlas records, got {len(rows)}")
    return [
        {
            "record_id": r["record_id"],
            "source": r["source"],
            "llm_category": r["llm_category"],
            "title": r["title"],
            "text": (r["title"] + " " + r["llm_quote"]).lower(),
        }
        for r in rows
    ]


def term_error(term: str) -> "str | None":
    """Reject malformed terms before they become regexes (author mistakes,
    and unbounded wildcard stacking that could backtrack pathologically)."""
    if not term or not re.search(r"\w", term):
        return "term must contain a word character"
    if len(term) > MAX_TERM_LENGTH:
        return f"term longer than {MAX_TERM_LENGTH} characters"
    if term.count("*") > MAX_WILDCARDS:
        return f"more than {MAX_WILDCARDS} wildcards"
    for word in term.split():
        if "*" not in word:
            continue
        if (word.count("*") > 1 or not word.endswith("*")
                or not re.search(r"\w", word[:-1])):
            return ("'*' only allowed once, at the end of a word with "
                    f"content (got {word!r})")
    return None


def compile_term(term: str) -> "re.Pattern":
    pat = re.escape(term.lower())
    pat = pat.replace(r"\*", r"\w*").replace(r"\ ", r"\s+")
    # \b only anchors against word characters; a term edge that is itself a
    # non-word character (e.g. "nad+") would never match before whitespace.
    lead = r"\b" if re.match(r"\w", term) else r"(?<!\w)"
    trail = r"\b" if re.search(r"[\w*]$", term) else r"(?!\w)"
    return re.compile(lead + pat + trail)


def term_stats(term: str, category: "str | None", rows: list,
               examples: int = 0) -> dict:
    pat = compile_term(term)
    hits = [r for r in rows if pat.search(r["text"])]
    by_cat = collections.Counter(r["llm_category"] for r in hits)
    stats = {
        "hits": len(hits),
        "by_category": dict(sorted(by_cat.items(), key=lambda kv: -kv[1])),
    }
    if category:
        stats["precision"] = round(by_cat[category] / len(hits), 3) if hits else 0.0
    if examples:
        false_hits = [r for r in hits if r["llm_category"] != category]
        stats["example_false_hits"] = [
            {
                "record_id": r["record_id"],
                "llm_category": r["llm_category"],
                "title": r["title"][:110],
            }
            for r in false_hits[:examples]
        ]
    return stats


def coverage(keywords: list, category: str, rows: list) -> float:
    pats = [compile_term(k["term"]) for k in keywords]
    cat_rows = [r for r in rows if r["llm_category"] == category]
    matched = sum(1 for r in cat_rows if any(p.search(r["text"]) for p in pats))
    return round(matched / len(cat_rows), 3) if cat_rows else 0.0


def self_test() -> int:
    checks = [
        (compile_term("aging").search("anti-aging cream") is not None, "hyphen boundary"),
        (compile_term("aging").search("imaging managing packaging") is None, "no substring"),
        (compile_term("senolytic*").search("senolytics work") is not None, "suffix wildcard"),
        (compile_term("cellulär* åldrande").search("cellulärt  åldrande") is not None,
         "unicode + mid-phrase wildcard + whitespace run"),
        (compile_term("nad+").search("boosting nad+ levels") is not None, "non-word edge"),
        (compile_term("nad+").search("nadir of the curve") is None, "non-word edge no overreach"),
        (compile_term("long-term care").search("long-term care homes") is not None, "literal hyphen"),
        (term_error("") is not None, "empty term rejected"),
        (term_error("*") is not None, "bare wildcard rejected"),
        (term_error("a*b") is not None, "mid-word wildcard rejected"),
        (term_error("a* a* a* a*") is not None, "wildcard stacking rejected"),
        (term_error("aging *") is not None, "bare wildcard word rejected"),
        (term_error("cellulär* åldrande") is None, "valid term accepted"),
    ]
    failed = [name for ok, name in checks if not ok]
    for name in failed:
        print(f"self-test FAILED: {name}")
    print(f"self-test: {len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", type=Path,
                    help="directory with the three atlas CSVs (default: the "
                         "live data/Track3_C2/output/, else git show recovery)")
    ap.add_argument("--keywords", type=Path,
                    default=Path(__file__).parent / "keywords.json")
    ap.add_argument("--update", action="store_true",
                    help="rewrite all stats in keywords.json (threshold "
                         "violations are still reported and fail the run)")
    ap.add_argument("--self-test", action="store_true",
                    help="run built-in matching unit checks and exit")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    live_dir = repo_root() / ATLAS_PREFIX
    if args.data_dir:
        rows = load_rows(args.data_dir)
    elif all((live_dir / n).is_file() for n in ATLAS_FILES):
        rows = load_rows(live_dir)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            recover_atlas(Path(tmp))
            rows = load_rows(Path(tmp))

    try:
        lex = json.loads(args.keywords.read_text(encoding="utf-8"))
        thresholds = lex["meta"]["thresholds"]
        categories = lex["categories"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        sys.exit(f"cannot load lexicon {args.keywords}: {exc!r}")
    failures = []

    def check(entry: dict, fresh: dict, label: str) -> None:
        stored = {k: entry.get(k) for k in fresh if k in entry}
        if args.update:
            entry.update(fresh)
        elif stored != fresh:
            failures.append(f"stale stats for {label}: stored {stored} != "
                            f"computed {fresh} (run --update)")

    for cat, block in categories.items():
        proxy = PROXY_LABEL.get(cat, cat)
        for lang in ("en", "sv"):
            kept_terms = {e["term"] for e in block.get(lang, [])
                          if "variant_of" not in e}
            for entry in block.get(lang, []):
                label = f"{cat}/{lang}/{entry['term']}"
                err = term_error(entry["term"])
                if err:
                    failures.append(f"malformed term {label}: {err}")
                    continue
                fresh = term_stats(entry["term"], proxy, rows)
                check(entry, fresh, label)
                # thresholds compare the exact ratio, not the rounded stat
                exact_precision = (fresh["by_category"].get(proxy, 0) / fresh["hits"]
                                   if fresh["hits"] else 0.0)
                th = thresholds[lang]
                if "variant_of" in entry:
                    # variants of a kept keyword skip only the hit-count floor;
                    # they must reference a real non-variant term, match
                    # something, and still meet the precision threshold
                    if entry["variant_of"] not in kept_terms:
                        failures.append(f"{label}: variant_of "
                                        f"{entry['variant_of']!r} is not a kept "
                                        f"non-variant term in {cat}/{lang}")
                    if fresh["hits"] < 1:
                        failures.append(f"{label}: variant has zero hits")
                    elif exact_precision < th["min_precision"]:
                        failures.append(
                            f"below threshold: {label} hits={fresh['hits']} "
                            f"precision={fresh['precision']} (variant)"
                        )
                elif (fresh["hits"] < th["min_hits"]
                        or exact_precision < th["min_precision"]):
                    failures.append(
                        f"below threshold: {label} hits={fresh['hits']} "
                        f"precision={fresh['precision']}"
                    )
                low = fresh["hits"] < LOW_EVIDENCE_HITS
                if args.update:
                    if low:
                        entry["low_evidence"] = True
                    else:
                        entry.pop("low_evidence", None)
                elif low and entry.get("low_evidence") is not True:
                    failures.append(f"{label}: low_evidence must be true "
                                    f"for hits={fresh['hits']}")
                elif not low and entry.get("low_evidence") is not None:
                    failures.append(f"{label}: low_evidence must be absent "
                                    f"for hits={fresh['hits']}")
        for entry in block.get("trap_terms", []):
            label = f"{cat}/trap/{entry['term']}"
            err = term_error(entry["term"])
            if err:
                failures.append(f"malformed term {label}: {err}")
                continue
            fresh = term_stats(entry["term"], proxy, rows, examples=3)
            check(entry, fresh, label)

    for lang in ("en", "sv"):
        for entry in lex["meta"]["broad_net"][lang]:
            label = f"broad_net/{lang}/{entry['term']}"
            err = term_error(entry["term"])
            if err:
                failures.append(f"malformed term {label}: {err}")
                continue
            fresh = term_stats(entry["term"], None, rows)
            check(entry, fresh, label)
    for entry in lex["meta"]["exclusion_markers"]:
        label = f"exclusion/{entry['term']}"
        err = term_error(entry["term"])
        if err:
            failures.append(f"malformed term {label}: {err}")
            continue
        fresh = term_stats(entry["term"], "ambiguous", rows)
        fresh["ambiguous_share"] = fresh.pop("precision")
        check(entry, fresh, label)

    print(f"atlas records: {len(rows)}")
    print(f"{'category':22s} {'en':>3s} {'sv':>3s} {'coverage':>9s}")
    for cat in CATEGORIES:
        block = categories[cat]
        kws = [k for k in block.get("en", []) + block.get("sv", [])
               if term_error(k["term"]) is None]
        cov = coverage(kws, PROXY_LABEL.get(cat, cat), rows)
        check(block, {"coverage": cov}, f"{cat}/coverage")
        print(f"{cat:22s} {len(block.get('en', [])):3d} "
              f"{len(block.get('sv', [])):3d} {cov:9.3f}")

    if args.update:
        args.keywords.write_text(
            json.dumps(lex, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"updated {args.keywords}")
    if failures:
        print(f"\n{len(failures)} validation failure(s):")
        for f in failures:
            print(" -", f)
        return 1
    print("all stored stats match; all keywords clear their thresholds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
