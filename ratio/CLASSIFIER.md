# Current classifier

The active four-category baseline is [instrument/classifier.py](instrument/classifier.py), built with `python3 -m ratio.instrument.build`. It uses PR #15's existing `classify.py` and lexicon for development candidates, then checks evidence in the stated aims before assigning a category. The complete available collected abstract is used. Ambiguity and low confidence are separate fields.

The optional [adjudicate.py](adjudicate.py) model runner uses the same versioned taxonomy. It checks its output schema and exact quotations, binds caches to source text and the full request, and marks every output as a model candidate. It never creates a human verdict. The new output location is `instrument/output/model-candidates.jsonl`, ignored by Git.

These are software and provenance safeguards, not classifier validation. Existing model-generated “expert” labels and within-model agreement cannot supply human accuracy. No external check has been completed. See [INSTRUMENT.md](INSTRUMENT.md) for boundaries, known failure modes and the evaluation plan.

The seven-category rule engine and historical numerical outputs remain development artifacts. They are not the current demo deliverable.
