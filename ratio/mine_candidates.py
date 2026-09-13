#!/usr/bin/env python3
"""Mine keyword candidates from the rules classifier's blind spots.

For every category, find 1-3-grams over-represented in records the senior
expert labelled with that category while the rules classifier called them
ambiguous (the 770-record blind-spot set), against records the expert
labelled with any other category. The category label comes from the expert
file, so candidates arrive pre-categorised and target exactly the vocabulary
the lexicon misses.

Inputs: the 2,944-record atlas (title + llm_quote), ratio/expert/
expert-labels.jsonl, ratio/classify.py.
Output: ratio/candidates.csv (columns: category, term, n_pos, n_bg, lift,
eur_pos_m, example_record_id, context). Nothing enters the lexicon
automatically. See ratio/V2_PLAN.md Track A1.

Usage: python3 ratio/mine_candidates.py [--top-per-category N]
Python 3 stdlib only; no network, no model calls.
"""

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "classifier"))

import classify as clf  # noqa: E402
import validate_keywords as vk  # noqa: E402

OUT_CSV = HERE / "candidates.csv"
EXPERT = HERE / "expert" / "expert-labels.jsonl"

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "by", "at", "from", "as", "is", "are", "was", "were", "be", "been",
    "being", "this", "that", "these", "those", "it", "its", "their", "they",
    "we", "our", "us", "you", "your", "his", "her", "he", "she", "not",
    "no", "can", "will", "would", "may", "might", "must", "should", "has",
    "have", "had", "do", "does", "did", "but", "if", "then", "than", "so",
    "such", "into", "over", "under", "between", "within", "without",
    "through", "during", "after", "before", "more", "most", "other", "some",
    "any", "all", "both", "each", "how", "what", "which", "who", "when",
    "where", "why", "also", "using", "used", "use", "based", "new",
    "identify", "identified", "investigate", "investigating", "demonstrate",
    "demonstrated", "clearly", "likely", "possibly", "thus", "future",
    "common", "burden", "process", "processes", "setting", "settings",
    "seek", "seeking", "play", "plays", "role", "roles", "integration",
    "component", "components", "develop", "developing", "provide",
    "provides", "improve", "improves", "understanding", "understand",
    "study", "studies", "research", "project", "results", "result", "aim",
    "aims", "objective", "objectives", "approach", "methods", "method",
    "analysis", "data", "including", "include", "includes", "involved",
    "involving", "among", "however", "therefore", "whether", "while",
    "about", "many", "much", "well", "even", "still", "only", "first",
    "last", "long", "high", "low", "health", "related", "population",
    "life", "development", "science", "new", "healthy", "human",
    # Swedish function words
    "och", "i", "att", "det", "som", "en", "ett", "på", "är", "av", "för",
    "med", "till", "den", "har", "de", "inte", "om", "vi", "kan", "ska",
    "vid", "från", "eller", "men", "samt", "inom", "genom", "efter",
    "under", "över", "mellan", "hur", "vad", "projekt", "studie",
    "studien", "forskning", "resultat", "syfte", "mål", "metod", "analys",
}

TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
TOKEN_WORD_RE = re.compile(r"\b[^\W\d_]{3,}\b", re.UNICODE)
SENT_SPLIT = re.compile(r"(?<=[.!?;:])\s+|\n+")


def load_experts() -> dict:
    out = {}
    for line in EXPERT.open(encoding="utf-8"):
        rec = json.loads(line)
        out[rec["record_id"]] = rec["expert_label"]
    return out


def load_covered():
    lex = json.loads((vk.repo_root() / "classifier" / "keywords.json")
                     .read_text(encoding="utf-8"))
    covered, traps = [], set()
    for block in lex["categories"].values():
        for lang in ("en", "sv"):
            covered.extend(e["term"] for e in block.get(lang, []))
        traps.update(e["term"] for e in block.get("trap_terms", []))
    for lang in ("en", "sv"):
        covered.extend(e["term"] for e in lex["meta"]["broad_net"][lang])
    covered.extend(e["term"] for e in lex["meta"]["exclusion_markers"])
    patterns = [(t, vk.compile_term(t)) for t in covered
                if vk.term_error(t) is None]
    return patterns, traps


def proper_tokens(text: str) -> set:
    counts = defaultdict(lambda: [0, 0])
    for match in TOKEN_WORD_RE.finditer(text):
        token = match.group(0)
        key = token.lower()
        counts[key][0] += 1
        preceded = text[:match.start()].rstrip()
        at_start = not preceded or preceded[-1] in ".!?;:\n"
        if token[0].isupper() and not at_start:
            counts[key][1] += 1
    return {t for t, (total, upper) in counts.items()
            if total >= 2 and upper / total >= 0.8}


def grams(text: str) -> set:
    out = set()
    tokens = TOKEN_RE.findall(text.lower())
    for n in (1, 2, 3):
        for i in range(len(tokens) - n + 1):
            seq = tokens[i:i + n]
            if any(len(t) < 3 or t in STOPWORDS for t in seq):
                continue
            out.add(" ".join(seq))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--top-per-category", type=int, default=60)
    ap.add_argument("--min-pos", type=int, default=3)
    ap.add_argument("--min-lift", type=float, default=3.0)
    args = ap.parse_args()

    experts = load_experts()
    covered, traps = load_covered()
    ruleset = clf.load_ruleset()
    rows = clf.load_corpus()

    docs = []
    for r in rows:
        expert = experts.get(r["record_id"])
        if expert not in clf.CATEGORIES:
            continue
        text = (r["title"] or "") + " " + (r["llm_quote"] or "")
        rules_label = clf.classify(r["title"], r["llm_quote"], ruleset)["label"]
        try:
            amount = float(r.get("amount_eur") or 0.0)
        except ValueError:
            amount = 0.0
        docs.append({
            "record_id": r["record_id"], "expert": expert,
            "rules": rules_label, "text": text, "amount": amount,
            "grams": grams(text), "proper": proper_tokens(text),
            "title_key": re.sub(r"\W+", " ", (r["title"] or "").lower()),
        })
    blind = sum(1 for d in docs if d["rules"] == "ambiguous")
    print(f"expert-labelled records: {len(docs)} | rules-ambiguous within "
          f"them: {blind}")

    results = []
    for cat in clf.CATEGORIES:
        pos = [d for d in docs if d["expert"] == cat and
               d["rules"] == "ambiguous"]
        bg = [d for d in docs if d["expert"] != cat]
        if len(pos) < args.min_pos:
            print(f"{cat}: only {len(pos)} blind-spot records, skipped")
            continue
        n_pos = len({d["title_key"] for d in pos})
        n_bg = len({d["title_key"] for d in bg})
        pos_titles, bg_titles = Counter(), Counter()
        examples = {}
        for d in pos:
            for g in d["grams"]:
                pos_titles[g] += 1
                prev = examples.get(g)
                if prev is None or len(d["text"]) > len(prev["text"]):
                    examples[g] = d
        for d in bg:
            for g in d["grams"]:
                bg_titles[g] += 1
        kept = []
        for g, a in pos_titles.items():
            if a < args.min_pos or any(p.search(g) for _, p in covered):
                continue
            words = len(g.split())
            b = bg_titles[g]
            if words == 1 and b > 0:
                continue
            ex = examples[g]
            if any(t in g.split() for t in ex["proper"]):
                continue
            lift = ((a + 0.5) / (n_pos + 0.5)) / ((b + 0.5) / (n_bg + 0.5))
            if lift < args.min_lift:
                continue
            eur_pos, seen_titles = 0.0, set()
            for d in pos:
                if g in d["grams"] and d["title_key"] not in seen_titles:
                    seen_titles.add(d["title_key"])
                    eur_pos += d["amount"]
            match = vk.compile_term(g).search(ex["text"])
            context = ""
            if match:
                s = max(0, match.start() - 70)
                context = ex["text"][s:match.end() + 70].replace("\n", " ")
            kept.append({
                "category": cat, "term": g, "words": words,
                "n_pos": a, "n_bg": b, "lift": round(lift, 2),
                "eur_pos_m": round(eur_pos / 1e6, 2),
                "is_trap": g in traps,
                "example_record_id": ex["record_id"], "context": context,
            })
        kept.sort(key=lambda r: (-r["lift"], -r["n_pos"]))
        print(f"\n=== {cat}: {len(pos)} blind-spot records, "
              f"{len(kept)} candidates")
        for r in kept[:args.top_per_category][:15]:
            flag = "t" if r["is_trap"] else " "
            print(f"  lift={r['lift']:6.1f} {flag} {r['term']!r:42s} "
                  f"n_pos={r['n_pos']:3d} n_bg={r['n_bg']:4d} "
                  f"EUR={r['eur_pos_m']:6.1f}M")
        results.extend(kept[:args.top_per_category])

    # one term belongs to the category where it has the highest lift
    best = {}
    for r in results:
        prev = best.get(r["term"])
        if prev is None or r["lift"] > prev["lift"]:
            best[r["term"]] = r
    results = sorted(best.values(),
                     key=lambda r: (r["category"], -r["lift"]))

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "category", "term", "words", "n_pos", "n_bg", "lift",
            "eur_pos_m", "is_trap", "example_record_id", "context"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\nwrote {OUT_CSV} ({len(results)} candidates across "
          f"{len(clf.CATEGORIES)} categories)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
