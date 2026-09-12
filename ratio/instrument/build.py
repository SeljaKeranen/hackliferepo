"""Build a static review instrument from the unchanged three-source corpus.

python3 -m ratio.instrument.build
Generated text and predictions stay in ignored ratio/instrument/output/.
"""
import argparse
import collections
import gzip
import json
import random
from pathlib import Path

from ratio import classify as legacy
from ratio.data.census_common import source_url
from ratio.instrument.classifier import TAXONOMY, VERSION, classify, digest, source_version

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = ('swecris', 'cordis', 'reporter')


def load_corpus(root=ROOT):
    records, seen, counts = [], {}, {}
    for source in SOURCES:
        path = root / 'ratio' / 'data' / f'census_{source}.jsonl.gz'
        with gzip.open(path, 'rt', encoding='utf-8') as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        counts[source] = len(rows)
        for row in rows:
            rid = row['record_id']
            if row['source'] != source:
                raise ValueError('Source mismatch: ' + rid)
            if rid in seen:
                if row != seen[rid]:
                    raise ValueError('Conflicting duplicate: ' + rid)
                continue
            seen[rid] = dict(row)
            row = {**row, 'url': source_url(row)}
            records.append(row)
    return sorted(records, key=lambda r: r['record_id']), counts


def sample(records, predictions, per_source=20, seed=42):
    """Source/category strata for development review, not a held-out test."""
    rng = random.Random(seed)
    selected, strata = [], {}
    for source in SOURCES:
        groups = collections.defaultdict(list)
        for row in records:
            if row['source'] == source:
                groups[predictions[row['record_id']]['label']].append(row['record_id'])
        for values in groups.values():
            rng.shuffle(values)
        chosen = collections.defaultdict(list)
        for _ in range(min(per_source, sum(map(len, groups.values())))):
            available = [key for key in sorted(groups) if len(chosen[key]) < len(groups[key])]
            key = min(available, key=lambda k: (len(chosen[k]), k))
            chosen[key].append(groups[key][len(chosen[key])])
        for key, ids in chosen.items():
            name = source + ':' + key
            strata[name] = {'population': len(groups[key]), 'selected': len(ids),
                            'inclusion_probability': len(ids) / len(groups[key])}
            selected.extend((rid, name) for rid in ids)
    rng.shuffle(selected)
    return selected, strata


def apply_model_candidates(path, records, predictions):
    """Only current four-label, source/request-bound model candidates apply."""
    if path is None:
        return {}, 0
    from types import SimpleNamespace
    from ratio.adjudicate import validated_result
    by_id = {r['record_id']: r for r in records}
    applied, failures = {}, 0
    with Path(path).open() as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            if 'error' in item:
                failures += 1
                continue
            rid = item.get('record_id')
            config = item.get('request_config', {})
            if rid not in by_id or set(config) != {'model', 'base_url', 'max_tokens'}:
                raise ValueError('Unknown or unversioned model candidate: ' + str(rid))
            if not validated_result(item, SimpleNamespace(**config), by_id[rid]):
                raise ValueError('Stale or invalid model candidate: ' + rid)
            applied[rid] = item
    for rid, item in applied.items():
        predictions[rid] = {**predictions[rid], **item, 'evidence': [item['quote']] if item['quote'] else []}
    return applied, failures


def build(output=HERE / 'output', per_source=20, model_candidates=None):
    records, counts = load_corpus()
    rules = legacy.load_ruleset()
    rules_version = digest([Path(legacy.__file__).read_text(), legacy.KEYWORDS_JSON.read_text(),
                            (HERE / 'classifier.py').read_text(), TAXONOMY])
    output = Path(output)
    cache_path = output / 'rule-cache.json'
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    if cache.get('rules_version') != rules_version:
        cache = {'rules_version': rules_version, 'records': {}}
    predictions = {}
    for index, r in enumerate(records):
        text_hash = digest({k: r.get(k) for k in ('record_id', 'title', 'abstract')})
        entry = cache['records'].get(r['record_id'], {})
        candidate = entry.get('candidate') if entry.get('text_hash') == text_hash else None
        if candidate is None:
            candidate = classify(r, rules)
        predictions[r['record_id']] = {**candidate, 'source_version': source_version(r)}
        cache['records'][r['record_id']] = {'text_hash': text_hash, 'candidate': candidate}
        if (index + 1) % 2000 == 0:
            print(f'Classified {index + 1}/{len(records)} records', file=__import__('sys').stderr)
    output.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False))
    applied_models, model_failures = apply_model_candidates(model_candidates, records, predictions)
    source_hash = digest([(r['record_id'], source_version(r)) for r in records])
    pipeline_hash = digest([Path(legacy.__file__).read_text(),
                            legacy.KEYWORDS_JSON.read_text(),
                            (HERE / 'classifier.py').read_text(),
                            (HERE / 'build.py').read_text(), applied_models, TAXONOMY])
    selected, strata = sample(records, predictions, per_source)
    by_id = {r['record_id']: r for r in records}
    packet_id = digest({'corpus': source_hash, 'pipeline': pipeline_hash,
                        'sample': selected, 'taxonomy': TAXONOMY})
    blind, candidates = [], []
    for rid, stratum in selected:
        r = by_id[rid]
        blind.append({k: r.get(k) for k in ('record_id', 'source', 'title', 'abstract',
                                           'url', 'year', 'retrieved_at')})
        blind[-1]['source_version'] = source_version(r)
        blind[-1]['text_status'] = ('missing_abstract' if not r.get('abstract') else
                                   'possibly_truncated' if len(r['abstract']) >= 6000 else
                                   'as_collected_completeness_unverified')
        candidates.append({**predictions[rid], 'stratum': stratum,
                           'selection_probability': strata[stratum]['inclusion_probability']})
    common = {'format': 'longview-instrument-v1', 'packet_id': packet_id,
              'taxonomy_version': VERSION, 'taxonomy': TAXONOMY,
              'corpus_version': source_hash, 'pipeline_version': pipeline_hash,
              'validation_status': 'unvalidated', 'purpose': 'development_review'}
    audit = {'records': len(records), 'source_counts': counts, 'sample_size': len(blind),
             'missing_abstracts': sum(not r.get('abstract') for r in records),
             'possibly_truncated_abstracts': sum(len(r.get('abstract', '')) >= 6000 for r in records),
             'corpus_scope': 'Existing keyword-filtered SweCRIS, CORDIS and NIH RePORTER records, 2015–2025. Not complete national funding coverage.',
             'text_note': 'Original collected text; no new translation. Some source fetchers preferred English and capped abstracts at 6,000 characters. Completeness has not been verified.',
             'source_register': '../INSTRUMENT.md',
             'model_candidates_applied': len(applied_models), 'failed_model_attempts_skipped': model_failures,
             'sampling_note': 'Seed 42; random within source × rule-label strata, balanced toward sparse labels. Shared development sample for overlapping human review. Unweighted agreement is descriptive only.',
             'external_validation': 'None. UKHRA/HRCS and cancer calibration have not been implemented.',
             'funding_results': 'Not produced. No funding number is a hackathon deliverable.'}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, value in [('packet.json', {**common, 'audit': audit, 'records': blind}),
                        ('predictions.json', {**common, 'strata': strata, 'predictions': candidates}),
                        ('audit.json', audit)]:
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    with (output / 'candidates.jsonl').open('w') as handle:
        for p in predictions.values():
            handle.write(json.dumps(p, ensure_ascii=False) + '\n')
    print(json.dumps({'packet_id': packet_id, **audit}, indent=2))
    return common


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'output')
    parser.add_argument('--per-source', type=int, default=20)
    parser.add_argument('--model-candidates', type=Path, help='Optional current four-label model output; old seven-label files are rejected')
    args = parser.parse_args()
    if args.per_source < 1:
        parser.error('--per-source must be positive')
    build(args.output, args.per_source, args.model_candidates)


if __name__ == '__main__':
    main()
