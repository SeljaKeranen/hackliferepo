"""Statistics for the study dashboard.

Four questions, kept apart because they answer to different people:

  1. Coverage. How many grants have enough judgments to say anything about.
  2. Human versus human. Where the researchers disagree with each other.
     This measures the RUBRIC, not the researchers: a high disagreement rate
     means the definition is unclear, and that is a finding about our
     instructions rather than about them.
  3. Human versus classifier. Whether the pipeline reproduces the human
     consensus. This is the validation result and the reason the study runs.
  4. Which grants are most contested, worst first. Disagreement clusters
     show where the rule fails, which is what gets fixed next.

Nothing here averages a grant's judgments into a single verdict for
display. Individual judgments are the evidence; a consensus is computed only
where one is needed to compare against the classifier, and it is explicitly
None when the labellers tie.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Sequence, Union

from label.taxonomy import GEROSCIENCE_ANSWERS, classifier_answer

MIN_JUDGMENTS_FOR_AGREEMENT = 2   # a pair is the minimum that can disagree
MIN_RECORDS_FOR_KAPPA = 10        # below this, kappa is noise
INSUFFICIENT = "insufficient_data"

# How far apart two answers are. Yes versus No is a real contradiction;
# either against Borderline is a softer disagreement about confidence, not
# about direction. Ranking by this rather than by "did they match" puts the
# genuine contradictions at the top of Andrew's queue.
ANSWER_DISTANCE = {
    ("yes", "no"): 2.0,
    ("yes", "borderline"): 1.0,
    ("no", "borderline"): 1.0,
}


def answer_distance(a: str, b: str) -> float:
    if a == b:
        return 0.0
    return ANSWER_DISTANCE.get((a, b)) or ANSWER_DISTANCE.get((b, a), 0.0)


def _answers(entries: Sequence[dict]) -> List[str]:
    return [e["geroscience"] for e in entries
            if e.get("geroscience") in GEROSCIENCE_ANSWERS]


def contention(entries: Sequence[dict]) -> float:
    """Mean pairwise distance between judgments, 0 (unanimous) to 2 (a clean
    yes/no split). Averaged over pairs rather than summed so a grant with
    five judgments is comparable with one that has two."""
    answers = _answers(entries)
    if len(answers) < 2:
        return 0.0
    pairs = [(answers[i], answers[j])
             for i in range(len(answers)) for j in range(i + 1, len(answers))]
    return sum(answer_distance(a, b) for a, b in pairs) / len(pairs)


def consensus(entries: Sequence[dict]) -> Optional[str]:
    """Strict majority answer, or None on a tie. None is a real result: it
    means the researchers could not settle the grant, and it must not be
    quietly broken in the classifier's favour."""
    answers = _answers(entries)
    if not answers:
        return None
    counts = Counter(answers).most_common()
    if len(counts) > 1 and counts[0][1] == counts[1][1]:
        return None
    return counts[0][0]


def observed_agreement(judgments: Dict[str, list]) -> Union[float, str]:
    """Share of labeller pairs that gave the same answer, across every grant
    with at least two judgments."""
    agree = total = 0
    for entries in judgments.values():
        answers = _answers(entries)
        for i in range(len(answers)):
            for j in range(i + 1, len(answers)):
                total += 1
                if answers[i] == answers[j]:
                    agree += 1
    return (agree / total) if total else INSUFFICIENT


def fleiss_kappa(judgments: Dict[str, list]) -> Union[float, str]:
    """Chance-corrected agreement, generalised to a variable number of
    raters per item. Returns "insufficient_data" rather than a number when
    there are too few multiply-rated records for it to mean anything --
    kappa on four records is theatre."""
    usable = {r: _answers(e) for r, e in judgments.items()}
    usable = {r: a for r, a in usable.items() if len(a) >= MIN_JUDGMENTS_FOR_AGREEMENT}
    if len(usable) < MIN_RECORDS_FOR_KAPPA:
        return INSUFFICIENT

    category_totals = Counter()
    total_ratings = 0
    per_item = []
    for answers in usable.values():
        counts = Counter(answers)
        n = len(answers)
        category_totals.update(counts)
        total_ratings += n
        agreement = sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))
        per_item.append(agreement)

    p_bar = sum(per_item) / len(per_item)
    p_e = sum((category_totals[c] / total_ratings) ** 2 for c in GEROSCIENCE_ANSWERS)
    if p_e >= 1.0:
        return INSUFFICIENT
    return (p_bar - p_e) / (1 - p_e)


def per_record(batch: dict, judgments: Dict[str, list]) -> List[dict]:
    """One row per grant, ranked most contested first. Ties break on funding
    amount, because a contested EUR 15M institute grant moves the headline
    ratio far more than a contested EUR 200k fellowship."""
    rows = []
    for record in batch.get("records", []):
        record_id = record["record_id"]
        entries = judgments.get(record_id, [])
        answers = _answers(entries)
        hidden = record.get("_hidden", {})
        clf_label = hidden.get("classifier_label", "")
        clf_answer = classifier_answer(clf_label)
        agreed = consensus(entries)
        rows.append({
            "record_id": record_id,
            "title": record.get("title", ""),
            "funder": record.get("funder", ""),
            "year": record.get("year"),
            "amount_eur": record.get("amount_eur") or 0,
            "url": record.get("url", ""),
            "n_judgments": len(entries),
            "answers": answers,
            "split": dict(Counter(answers)),
            "contention": round(contention(entries), 3),
            "consensus": agreed,
            "cancer_ticks": sum(1 for e in entries if e.get("cancer")),
            "flags": sum(1 for e in entries if e.get("cant_tell")),
            "classifier_label": clf_label,
            "classifier_answer": clf_answer,
            "classifier_agrees": (None if agreed is None or not clf_answer
                                   else clf_answer == agreed),
            "expert_label": hidden.get("expert_label", ""),
            "stratum": hidden.get("stratum", ""),
            "thin": len(entries) < MIN_JUDGMENTS_FOR_AGREEMENT,
        })
    rows.sort(key=lambda r: (-r["contention"], -r["amount_eur"]))
    return rows


def classifier_comparison(rows: Sequence[dict]) -> dict:
    """Confusion matrix and per-answer precision/recall of the classifier
    against the human consensus. Only grants with a consensus count: a tied
    grant has no human answer to be right or wrong about."""
    scored = [r for r in rows if r["consensus"] and r["classifier_answer"]]
    matrix = {h: {c: 0 for c in GEROSCIENCE_ANSWERS} for h in GEROSCIENCE_ANSWERS}
    for row in scored:
        matrix[row["consensus"]][row["classifier_answer"]] += 1

    per_answer = {}
    for answer in GEROSCIENCE_ANSWERS:
        true_pos = matrix[answer][answer]
        actual = sum(matrix[answer].values())
        predicted = sum(matrix[h][answer] for h in GEROSCIENCE_ANSWERS)
        per_answer[answer] = {
            "n_human": actual,
            "recall": (true_pos / actual) if actual else None,
            "precision": (true_pos / predicted) if predicted else None,
            "thin": actual < MIN_RECORDS_FOR_KAPPA,
        }
    return {
        "n_scored": len(scored),
        "n_no_consensus": sum(1 for r in rows if r["n_judgments"] and not r["consensus"]),
        "matrix": matrix,
        "per_answer": per_answer,
        "overall_agreement": (
            sum(matrix[a][a] for a in GEROSCIENCE_ANSWERS) / len(scored)
            if scored else INSUFFICIENT),
        "cancer_note": ("ratio/classify.py emits no cancer judgment, so the cancer "
                         "tick has no classifier counterpart to be scored against. "
                         "Human cancer ticks are reported on their own."),
    }


def summarise(batch: dict, judgments: Dict[str, list]) -> dict:
    rows = per_record(batch, judgments)
    labellers = sorted({e["labeller_id"] for entries in judgments.values()
                        for e in entries if e.get("labeller_id")})
    multi = [r for r in rows if r["n_judgments"] >= MIN_JUDGMENTS_FOR_AGREEMENT]
    return {
        "coverage": {
            "records": len(rows),
            "labellers": labellers,
            "n_labellers": len(labellers),
            "records_with_any": sum(1 for r in rows if r["n_judgments"]),
            "records_with_two_or_more": len(multi),
            "total_judgments": sum(r["n_judgments"] for r in rows),
            "note": ("Only records with two or more judgments can show "
                      "disagreement; the rest are single opinions."),
        },
        "human_vs_human": {
            "observed_agreement": observed_agreement(judgments),
            "fleiss_kappa": fleiss_kappa(judgments),
            "kappa_note": (f"Reported only once at least {MIN_RECORDS_FOR_KAPPA} records "
                            "carry two or more judgments."),
            "cancer_ticks": sum(r["cancer_ticks"] for r in rows),
            "text_flags": sum(r["flags"] for r in rows),
        },
        "human_vs_classifier": classifier_comparison(rows),
        "contested": rows,
    }
