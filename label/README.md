# Grant labelling study

A blind labelling tool for external researchers, and a dashboard for
whoever is running the study. Built to Andrew Steele's cut of the question,
settled by email on 2026-09-13:

> I think I'd split it into 'geroscience' (ie research into the causes of
> ageing, and attempts to intervene in it or develop treatments), then
> choose a specific disease (cancer is the most common referent) to compare
> to … You might find it's more successful to have one prompt ask 'is this
> ageing?' and another ask 'is this cancer?' rather than one prompt for
> both.

**Status: the instrument works, and holds no results.** No judgments have
been collected. Every statistic on the dashboard is computed from whatever
arrives; nothing in this directory is seeded, simulated or illustrative.

## Run it

```sh
python3 -m label.sample --batch batch_001     # already done; rebuilds the batch
python3 label/server.py                        # http://localhost:8002
```

Then send each researcher their own link — the name in it is how their
judgments stay separate:

```
http://localhost:8002/?batch=batch_001&who=r-lindqvist
```

The dashboard is at `/admin?batch=batch_001`.

## The question

One question, three answers, plus two independent ticks:

| | |
| --- | --- |
| **Is this geroscience?** | Yes · No · Borderline |
| **Cancer research?** | a separate tick, not a rival answer |
| **Couldn't tell from this text?** | a separate flag, not an answer |

Two distinctions the design turns on:

- **Cancer is independent.** A senolytic trialled on tumours is both. It is
  the comparator field, there so ageing funding can be read against
  something of known size.
- **Borderline is not "couldn't tell".** Borderline means the text was clear
  and the *grant* reads both ways. Couldn't-tell means the *text* failed the
  reader. They need opposite responses — adjudication versus better source
  text — so collapsing them destroys the signal. The flag is how we find out
  which abstracts are too thin for any method, human or machine.

"Fighting the consequences of ageing", from an earlier draft, is gone.
Andrew's objection: unbounded, and hard to explain to someone why it was a
useful category.

## Why every researcher sees every grant

Inter-rater agreement is the thing worth measuring, and it cannot be
computed from a partitioned queue. Where the researchers disagree with each
other is a reading of **our definition**, not of them — a high disagreement
rate means the instructions need work. So the batch is not split up; it is
shown whole to everyone.

## Blind by construction

`/api/records` strips the `_hidden` block before serving, so the classifier
label, the expert label and the sampling stratum cannot reach the labelling
page even if its JavaScript asked. A labeller also sees their own previous
answers but never anyone else's. Both properties are covered by
`test_server.py`, which fails loudly if either leaks.

This is why the tool is worth building rather than reusing the review loop
in `eval-classifier/`: that one shows the pipeline's answer and asks the
reviewer to agree or disagree, which is the right instrument for checking a
pipeline and the wrong one for collecting independent expert judgment.

## Identity, not authentication

`?who=` attributes a judgment; it does not authenticate anyone. Whoever has
a link can write under any name. That is the correct trade for a handful of
trusted colleagues doing a favour, and the wrong one for anything else. Put
it behind real authentication before it holds anything sensitive, and note
that `--host 0.0.0.0` exposes it with no auth at all.

## The batch

`batches/batch_001.json` — 40 real grants with **full abstracts**, drawn
from `ratio/data/census_*.jsonl.gz`. Earlier layers of this project judged
grants from a title plus a short extracted quote, which both
`ratio/expert/README.md` and `classifier/KEYWORDS.md` name as a limitation;
the census files carry the real text, so the researchers get it.

Sampling is seeded and stratified over the classifier's label, weighted
toward records where the classifier and the expert pass disagree, because
those are where a human read is worth the most. The manifest records which
stratum each grant came from, so the draw is reproducible and its bias is
legible rather than hidden.

## What the dashboard answers

1. **Coverage** — how many grants have enough judgments to say anything about.
2. **Human versus human** — observed pairwise agreement, and Fleiss κ once at
   least 10 grants carry two or more judgments. Below that it reports
   `insufficient_data` rather than a number, because κ on four records is
   theatre.
3. **Human versus classifier** — a confusion matrix and per-answer
   precision/recall against the human consensus. Grants where the labellers
   tie are excluded and counted, never broken in the classifier's favour.
4. **Most contested, worst first** — ranked by mean pairwise distance between
   answers, where a yes/no split counts double a borderline split, then by
   funding amount. This list is the scientific product: disagreement
   clusters show exactly where the rule fails.

Plus a CSV of everything, at `/api/export.csv?batch=…`.

`ratio/classify.py` emits no cancer judgment, so the cancer tick has no
classifier counterpart to be scored against. The dashboard says so rather
than inventing a comparison.

## Tests

```sh
python3 -m unittest label.test_agreement    # 23 tests, no server needed
python3 label/test_server.py                 # HTTP contract, incl. the blind guarantee
```

## Layout

- `taxonomy.py` — the answers, and how classifier labels project onto them
- `sample.py` — builds a batch from the census + classifier + expert labels
- `store.py` — batch and judgment files, atomic writes, content fingerprints
- `agreement.py` — contention, consensus, κ, classifier comparison
- `server.py` — the HTTP layer, blind on one side and open on the other
- `static/index.html` — the labelling tool
- `static/admin.html` — the dashboard

A sibling of `eval/` and `eval-classifier/`, sharing no code or data with
either, per the decoupling rule in `AGENTS.md`.
