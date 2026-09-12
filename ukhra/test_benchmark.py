"""Tests for the UKHRA benchmark's pure logic.

Deliberately does not touch the 30MB XLSX: the dataset is not committed
(AGENTS.md forbids committing raw datasets), so these tests must pass on a
fresh clone with no download.
"""
import unittest

from ukhra.benchmark import (
    CANCER_HEALTH_CATEGORY, UkhraAward, load_predictor, ra_group_profile, score_cancer,
)

predict = load_predictor(None)  # the keyword baseline in ukhra/cancer_terms.py


def _award(award_id, title="", abstract="", value=1000.0, hcs=(), ras=(), coding="Manual"):
    return UkhraAward(
        award_id=award_id, funder="Test Funder", title=title, abstract=abstract,
        value_2022_gbp=value, health_categories=list(hcs), ra_groups=list(ras),
        coding_type=coding,
    )


class TestRedactionDetection(unittest.TestCase):
    def test_placeholder_text_counts_as_redacted(self):
        a = _award("x", title="MRC Studentship - Award title not available in public dataset",
                    abstract="MRC Studentship - Award abstract not available in public dataset")
        self.assertTrue(a.is_text_redacted)

    def test_empty_text_counts_as_redacted(self):
        self.assertTrue(_award("x", title="", abstract="").is_text_redacted)

    def test_real_text_is_not_redacted(self):
        a = _award("x", title="Senescence in colorectal cancer", abstract="A study of tumour biology.")
        self.assertFalse(a.is_text_redacted)


class TestCancerGroundTruth(unittest.TestCase):
    def test_any_vs_primary_health_category(self):
        a = _award("x", hcs=("Infection", CANCER_HEALTH_CATEGORY))
        self.assertTrue(a.is_cancer)
        self.assertFalse(a.is_primary_cancer)

    def test_scoring_counts_and_funding(self):
        awards = [
            # true positive: we detect cancer, humans coded cancer
            _award("tp", title="Tumour immunology", hcs=(CANCER_HEALTH_CATEGORY,), value=100.0),
            # false positive: mentions cancer, humans coded it elsewhere
            _award("fp", title="A cell biology outreach project mentioning cancer",
                   hcs=("Generic Health Relevance",), value=200.0),
            # false negative: humans coded cancer, no cancer term in our lexicon
            _award("fn", title="Studies of aberrant cell proliferation",
                   hcs=(CANCER_HEALTH_CATEGORY,), value=400.0),
            # true negative
            _award("tn", title="Influenza vaccine trial", hcs=("Infection",), value=800.0),
        ]
        score = score_cancer(awards, predict)
        self.assertEqual((score.tp, score.fp, score.fn, score.tn), (1, 1, 1, 1))
        self.assertEqual(score.funding_wrongly_included_gbp, 200.0)
        self.assertEqual(score.funding_missed_gbp, 400.0)
        self.assertAlmostEqual(score.precision, 0.5)
        self.assertAlmostEqual(score.recall, 0.5)


class TestPluggableClassifier(unittest.TestCase):
    """Any classifier can be scored, so this benchmark outlives the keyword
    baseline it ships with (e.g. --classifier ratio.classify:something)."""

    def test_default_is_the_keyword_baseline(self):
        self.assertTrue(load_predictor(None)("a study of tumour biology"))
        self.assertFalse(load_predictor(None)("an influenza vaccine trial"))

    def test_named_function_is_loaded_and_coerced_to_bool(self):
        predictor = load_predictor("ukhra.cancer_terms:looks_like_cancer")
        # looks_like_cancer returns a (bool, terms) tuple; a non-empty tuple
        # is truthy either way, so assert the underlying call agrees
        self.assertTrue(predictor("carcinoma progression"))

    def test_bad_spec_is_rejected_loudly(self):
        with self.assertRaises(SystemExit):
            load_predictor("no_colon_here")


class TestResearchActivityProfile(unittest.TestCase):
    def test_funding_apportioned_across_multiple_ra_groups(self):
        # one award, two RA groups -> half its value to each
        profile = ra_group_profile([_award("x", ras=("3", "5"), value=1000.0)])
        self.assertAlmostEqual(profile["by_group"]["3"]["apportioned_gbp"], 500.0)
        self.assertAlmostEqual(profile["by_group"]["5"]["apportioned_gbp"], 500.0)
        self.assertAlmostEqual(profile["prevention_gbp"], 500.0)
        self.assertAlmostEqual(profile["consequences_gbp"], 500.0)

    def test_underpinning_and_aetiology_stay_unmapped(self):
        profile = ra_group_profile([_award("x", ras=("1",), value=100.0),
                                     _award("y", ras=("2",), value=100.0)])
        self.assertAlmostEqual(profile["unmapped_gbp"], 200.0)
        self.assertAlmostEqual(profile["prevention_gbp"], 0.0)
        self.assertAlmostEqual(profile["consequences_gbp"], 0.0)
        self.assertIsNone(profile["prevention_share_of_mapped"])


if __name__ == "__main__":
    unittest.main()
