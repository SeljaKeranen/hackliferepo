"""Software fixtures only. These decisions are not human validation evidence."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from ratio.instrument.classifier import classify, source_version, digest
from ratio.instrument.build import sample, load_corpus, apply_model_candidates
from ratio.data.census_common import swecris_project_url, source_url
from ratio import adjudicate


def record(title='Ageing project', abstract='We aim to study biological ageing.', **extra):
    return {'record_id': 'swecris:fixture_VR', 'source_id': 'fixture_VR', 'source': 'swecris',
            'title': title, 'abstract': abstract, 'url': 'https://example.org/fixture',
            'retrieved_at': '2026-09-12', 'year': 2024, **extra}


class ClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ratio import classify as legacy
        cls.rules = legacy.load_ruleset()

    def test_model_organism_ageing_is_not_excluded(self):
        p = classify(record('Ageing mechanisms in worms', 'We aim to study biological ageing in C. elegans.'), self.rules)
        self.assertEqual(p['label'], 'preventing_slowing')
        self.assertFalse(p['human_verified'])

    def test_lifelong_battery_is_neither(self):
        p = classify(record('Life-long battery cells', 'We aim to extend battery cell life using electrolyte chemistry.'), self.rules)
        self.assertEqual(p['label'], 'neither')

    def test_swedish_material_aim(self):
        p = classify(record('Långlivade batterier', 'Vi ska undersöka batteriers livslängd och elektroder.'), self.rules)
        self.assertEqual(p['label'], 'neither')

    def test_swedish_biology_aim(self):
        p = classify(record('Cellernas förändring', 'Syftet är att studera åldrandets biologi.'), self.rules)
        self.assertEqual(p['label'], 'preventing_slowing')

    def test_generic_background_does_not_make_biology(self):
        p = classify(record('A cancer diagnostic', 'Biological ageing motivates public interest. We aim to detect cancer with a new imaging sensor.'), self.rules)
        self.assertNotEqual(p['label'], 'preventing_slowing')

    def test_low_confidence_independent_of_ambiguity(self):
        p = classify(record('Research aims', 'We aim to study biological ageing. Our goal is to improve dementia care for older adults.'), self.rules)
        self.assertEqual(p['label'], 'ambiguous')
        self.assertFalse(p['low_confidence'])

    def test_missing_text_abstains(self):
        p = classify(record(abstract=''), self.rules)
        self.assertEqual(p['label'], 'ambiguous')
        self.assertTrue(p['low_confidence'])
        self.assertIn('missing_abstract', p['uncertainty_reasons'])

    def test_aim_after_3000_characters_is_read(self):
        p = classify(record('Methods study', ('Prior work is described here. ' * 130) + 'We aim to study biological ageing.'), self.rules)
        self.assertEqual(p['label'], 'preventing_slowing')

    def test_negated_aim_requires_review(self):
        p = classify(record('Mechanistic study', 'We will not study biological ageing.'), self.rules)
        self.assertEqual(p['label'], 'ambiguous')

    def test_changed_text_or_url_invalidates_review(self):
        r = record()
        self.assertNotEqual(source_version(r), source_version({**r, 'abstract': 'New text'}))
        self.assertNotEqual(source_version(r), source_version({**r, 'url': 'https://example.org/corrected'}))


class SourceAndSamplingTests(unittest.TestCase):
    def test_swecris_deep_link(self):
        url = swecris_project_url('2023-01125_Forte')
        self.assertEqual(url, 'https://www.vr.se/english/swecris.html#/project/2023-01125_Forte')
        self.assertNotIn('searchText=', url)

    def test_url_uses_source_id_not_collision_suffix(self):
        self.assertTrue(source_url(record(record_id='swecris:fixture_VR:12345')).endswith('/fixture_VR'))
        self.assertEqual(source_url({'source': 'cordis', 'url': 'https://cordis.europa.eu/project/id/1'}), 'https://cordis.europa.eu/project/id/1')
        self.assertTrue(swecris_project_url('A/B ?').endswith('A%2FB%20%3F'))
        with self.assertRaises(ValueError):
            swecris_project_url('')

    def test_stratified_sample_reproducible_and_probabilities(self):
        rows = [record(record_id=f'{source}:{i}', source=source) for source in ('swecris', 'cordis', 'reporter') for i in range(40)]
        predictions = {r['record_id']: {'label': 'neither' if i % 4 else 'ambiguous'} for i, r in enumerate(rows)}
        chosen, strata = sample(rows, predictions)
        self.assertEqual((chosen, strata), sample(rows, predictions))
        self.assertEqual(len(chosen), 60)
        self.assertEqual(len(set(rid for rid, _ in chosen)), 60)
        for values in strata.values():
            self.assertEqual(values['inclusion_probability'], values['selected'] / values['population'])

    def test_duplicate_detection_before_sampling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); data = root / 'ratio/data'; data.mkdir(parents=True)
            for source in ('swecris', 'cordis', 'reporter'):
                r = record(record_id=f'{source}:fixture', source=source)
                with gzip.open(data / f'census_{source}.jsonl.gz', 'wt') as out:
                    for row in [r, r]: out.write(json.dumps(row) + '\n')
            records, _ = load_corpus(root)
            self.assertEqual(len(records), 3)
            with gzip.open(data / 'census_swecris.jsonl.gz', 'at') as out:
                out.write(json.dumps(record(record_id='swecris:fixture', title='Changed duplicate')) + '\n')
            with self.assertRaisesRegex(ValueError, 'Conflicting duplicate'):
                load_corpus(root)


class ModelBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.record = record()
        self.args = SimpleNamespace(model='test-model', base_url='https://example.org/v1', max_tokens=500, attempts=1)
        self.candidate = {'label': 'preventing_slowing', 'low_confidence': False,
                          'quote': 'We aim to study biological ageing.', 'reason': 'Stated aim.', 'uncertainty_reasons': []}

    def test_prompt_keeps_full_collected_text_and_new_rubric(self):
        r = record(abstract='x' * 4000 + 'FINAL AIM')
        prompt = adjudicate.make_prompt(r)
        self.assertIn('FINAL AIM', prompt[1]['content'])
        self.assertIn('low_confidence', prompt[0]['content'])
        self.assertIn('Model organisms qualify', prompt[0]['content'])

    def test_strict_schema_and_quote(self):
        self.assertEqual(adjudicate.validate_candidate(self.candidate, self.record), self.candidate)
        for changes in [{'label': 'fundamental_aging'}, {'low_confidence': 'false'}, {'quote': 'Invented quote'}, {'human_verified': True}, {'quote': self.candidate['quote'].upper()}]:
            with self.assertRaises(ValueError):
                adjudicate.validate_candidate({**self.candidate, **changes}, self.record)

    def test_empty_quote_only_for_insufficient_text_abstention(self):
        candidate = {**self.candidate, 'label': 'ambiguous', 'low_confidence': True, 'quote': '', 'uncertainty_reasons': ['insufficient_text']}
        adjudicate.validate_candidate(candidate, record(abstract=''))
        with self.assertRaises(ValueError):
            adjudicate.validate_candidate(self.candidate, record(abstract=''))
        with self.assertRaises(ValueError):
            adjudicate.validate_candidate({**candidate, 'low_confidence': False}, record(abstract=''))

    def test_request_cache_binds_text_model_prompt_and_settings(self):
        original = adjudicate.request_version(self.args, self.record)
        self.assertNotEqual(original, adjudicate.request_version(self.args, record(abstract='new text')))
        for field, value in [('model', 'different'), ('max_tokens', 1000), ('base_url', 'https://another.example/v1')]:
            new = SimpleNamespace(**{**vars(self.args), field: value})
            self.assertNotEqual(original, adjudicate.request_version(new, self.record))
        from unittest.mock import patch
        with patch.object(adjudicate, 'SYSTEM_PROMPT', 'changed rubric'):
            self.assertNotEqual(original, adjudicate.request_version(self.args, self.record))

    def test_cache_revalidated_and_model_never_human(self):
        session = Mock()
        response = session.post.return_value
        response.json.return_value = {'choices': [{'message': {'content': json.dumps(self.candidate)}}], 'model': 'test-model'}
        with tempfile.TemporaryDirectory() as tmp:
            result = adjudicate.call_api(session, self.args, self.record, tmp)
            self.assertEqual(result['label_origin'], 'model')
            self.assertFalse(result['human_verified'])
            self.assertEqual(session.post.call_count, 1)
            self.assertEqual(result, adjudicate.call_api(session, self.args, self.record, tmp))
            self.assertEqual(session.post.call_count, 1)
            cache = Path(tmp) / (result['request_version'] + '.json')
            cache.write_text(json.dumps({**result, 'label': 'made_up'}))
            adjudicate.call_api(session, self.args, self.record, tmp)
            self.assertEqual(session.post.call_count, 2)

    def test_build_applies_only_current_model_candidates(self):
        session = Mock()
        session.post.return_value.json.return_value = {'choices': [{'message': {'content': json.dumps(self.candidate)}}]}
        with tempfile.TemporaryDirectory() as tmp:
            result = adjudicate.call_api(session, self.args, self.record, tmp)
            path = Path(tmp) / 'outputs.jsonl'
            path.write_text(json.dumps(result) + '\n')
            predictions = {self.record['record_id']: {'label': 'ambiguous', 'label_origin': 'rule'}}
            applied, failed = apply_model_candidates(path, [self.record], predictions)
            self.assertEqual(len(applied), 1)
            self.assertEqual(failed, 0)
            self.assertEqual(predictions[self.record['record_id']]['label_origin'], 'model')
            path.write_text(json.dumps({**result, 'source_version': 'stale'}) + '\n')
            with self.assertRaisesRegex(ValueError, 'Stale'):
                apply_model_candidates(path, [self.record], predictions)
            path.write_text(json.dumps({'record_id': self.record['record_id'], 'error': 'failure'}) + '\n')
            self.assertEqual(apply_model_candidates(path, [self.record], predictions), ({}, 1))

    def test_api_failure_not_a_successful_ambiguous_label(self):
        session = Mock()
        session.post.return_value.json.return_value = {'choices': [{'message': {'content': 'not JSON'}}]}
        with tempfile.TemporaryDirectory() as tmp:
            result = adjudicate.call_api(session, self.args, self.record, tmp)
        self.assertIn('error', result)
        self.assertNotIn('label', result)
        self.assertFalse(adjudicate.validated_result(result, self.args, self.record))


if __name__ == '__main__':
    unittest.main()
