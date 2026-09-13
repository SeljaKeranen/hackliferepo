"""Tests for the labelling taxonomy, storage and statistics.

No batch file and no server needed: everything here runs on fixtures.
"""
import json
import tempfile
import unittest
from pathlib import Path

from label import agreement, store
from label.taxonomy import classifier_answer


def j(who, answer, cancer=False, cant_tell=False, reason=""):
    return {"labeller_id": who, "geroscience": answer, "cancer": cancer,
            "cant_tell": cant_tell, "reason": reason, "labelled_at": "2026-09-13T09:00:00Z",
            "record_fingerprint": "0123456789abcdef"}


def batch(*records):
    return {"records": [dict(r) for r in records]}


def rec(record_id, clf="", expert="", amount=1000.0, title="t"):
    return {"record_id": record_id, "title": title, "funder": "F", "year": 2023,
            "amount_eur": amount, "url": "", "abstract": "a",
            "_hidden": {"classifier_label": clf, "expert_label": expert, "stratum": "s"}}


class TestTaxonomy(unittest.TestCase):
    def test_numerator_categories_map_to_yes(self):
        # fundamental_aging and intervention are the funding-gap numerator and
        # are exactly "causes of ageing, and attempts to intervene in it"
        self.assertEqual(classifier_answer("fundamental_aging"), "yes")
        self.assertEqual(classifier_answer("intervention"), "yes")

    def test_ambiguous_maps_to_borderline_not_no(self):
        self.assertEqual(classifier_answer("ambiguous"), "borderline")

    def test_unknown_label_returns_empty_rather_than_guessing(self):
        self.assertEqual(classifier_answer("some_new_category"), "")


class TestContention(unittest.TestCase):
    def test_unanimous_is_zero(self):
        self.assertEqual(agreement.contention([j("a", "yes"), j("b", "yes")]), 0.0)

    def test_yes_no_split_is_maximal(self):
        self.assertEqual(agreement.contention([j("a", "yes"), j("b", "no")]), 2.0)

    def test_borderline_disagreement_counts_half_of_a_yes_no_split(self):
        self.assertEqual(agreement.contention([j("a", "yes"), j("b", "borderline")]), 1.0)

    def test_single_judgment_cannot_be_contested(self):
        self.assertEqual(agreement.contention([j("a", "yes")]), 0.0)

    def test_averaged_over_pairs_so_rater_counts_are_comparable(self):
        two = agreement.contention([j("a", "yes"), j("b", "no")])
        four = agreement.contention([j("a", "yes"), j("b", "no"), j("c", "yes"), j("d", "no")])
        self.assertGreater(two, four)  # 4 raters include 2 agreeing pairs
        self.assertLessEqual(four, 2.0)


class TestConsensus(unittest.TestCase):
    def test_majority_wins(self):
        self.assertEqual(agreement.consensus([j("a", "yes"), j("b", "yes"), j("c", "no")]), "yes")

    def test_tie_returns_none_rather_than_picking(self):
        self.assertIsNone(agreement.consensus([j("a", "yes"), j("b", "no")]))

    def test_no_judgments_is_none(self):
        self.assertIsNone(agreement.consensus([]))


class TestAgreementStats(unittest.TestCase):
    def test_observed_agreement_counts_pairs(self):
        judgments = {"r1": [j("a", "yes"), j("b", "yes"), j("c", "no")]}
        # pairs: a-b agree, a-c differ, b-c differ -> 1/3
        self.assertAlmostEqual(agreement.observed_agreement(judgments), 1 / 3)

    def test_kappa_refuses_small_samples(self):
        judgments = {f"r{i}": [j("a", "yes"), j("b", "no")] for i in range(3)}
        self.assertEqual(agreement.fleiss_kappa(judgments), "insufficient_data")

    def test_kappa_computed_once_enough_records(self):
        judgments = {f"r{i}": [j("a", "yes"), j("b", "yes")] for i in range(12)}
        value = agreement.fleiss_kappa(judgments)
        # everyone agrees on everything, but on one category only, so chance
        # agreement is also 1 and kappa is undefined rather than perfect
        self.assertEqual(value, "insufficient_data")

    def test_kappa_is_a_number_with_spread_across_categories(self):
        judgments = {}
        for i in range(12):
            answer = ["yes", "no", "borderline"][i % 3]
            judgments[f"r{i}"] = [j("a", answer), j("b", answer)]
        value = agreement.fleiss_kappa(judgments)
        self.assertIsInstance(value, float)
        self.assertGreater(value, 0.9)  # perfect agreement, three categories used


class TestClassifierComparison(unittest.TestCase):
    def test_tied_records_are_excluded_not_broken_toward_the_classifier(self):
        b = batch(rec("r1", clf="fundamental_aging"))
        judgments = {"r1": [j("a", "yes"), j("b", "no")]}   # tie -> no consensus
        rows = agreement.per_record(b, judgments)
        comparison = agreement.classifier_comparison(rows)
        self.assertEqual(comparison["n_scored"], 0)
        self.assertEqual(comparison["n_no_consensus"], 1)

    def test_matrix_counts_human_rows_against_classifier_columns(self):
        b = batch(rec("r1", clf="fundamental_aging"), rec("r2", clf="not_relevant"))
        judgments = {
            "r1": [j("a", "yes"), j("b", "yes")],   # human yes, classifier yes
            "r2": [j("a", "yes"), j("b", "yes")],   # human yes, classifier no
        }
        comparison = agreement.classifier_comparison(agreement.per_record(b, judgments))
        self.assertEqual(comparison["matrix"]["yes"]["yes"], 1)
        self.assertEqual(comparison["matrix"]["yes"]["no"], 1)
        self.assertAlmostEqual(comparison["overall_agreement"], 0.5)

    def test_ranking_puts_most_contested_first_then_biggest_money(self):
        b = batch(rec("calm", clf="", amount=9_000_000.0),
                  rec("split", clf="", amount=1000.0),
                  rec("split_rich", clf="", amount=500_000.0))
        judgments = {
            "calm": [j("a", "yes"), j("b", "yes")],
            "split": [j("a", "yes"), j("b", "no")],
            "split_rich": [j("a", "yes"), j("b", "no")],
        }
        rows = agreement.per_record(b, judgments)
        self.assertEqual([r["record_id"] for r in rows], ["split_rich", "split", "calm"])


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._judgment_dir = store.JUDGMENT_DIR
        store.JUDGMENT_DIR = Path(self.tmp.name)

    def tearDown(self):
        store.JUDGMENT_DIR = self._judgment_dir
        self.tmp.cleanup()

    def test_second_labeller_does_not_overwrite_the_first(self):
        store.save_judgment("b", "r1", j("alice", "yes"))
        data = store.save_judgment("b", "r1", j("bob", "no"))
        self.assertEqual(len(data["r1"]), 2)
        self.assertEqual({e["labeller_id"] for e in data["r1"]}, {"alice", "bob"})

    def test_relabelling_replaces_only_your_own_entry(self):
        store.save_judgment("b", "r1", j("alice", "yes"))
        store.save_judgment("b", "r1", j("bob", "no"))
        data = store.save_judgment("b", "r1", j("alice", "borderline"))
        self.assertEqual(len(data["r1"]), 2)
        alice = next(e for e in data["r1"] if e["labeller_id"] == "alice")
        self.assertEqual(alice["geroscience"], "borderline")

    def test_unreadable_file_raises_instead_of_clobbering_evidence(self):
        path = store.judgments_path("b")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ this is not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            store.save_judgment("b", "r1", j("alice", "yes"))

    def test_slug_rules_keep_ids_filename_safe(self):
        self.assertTrue(store.is_slug("batch_001"))
        self.assertTrue(store.is_slug("r-lindqvist"))
        self.assertFalse(store.is_slug("../etc/passwd"))
        self.assertFalse(store.is_slug("Capitals"))
        self.assertFalse(store.is_slug(""))

    def test_fingerprint_changes_when_the_text_changes(self):
        a = store.record_fingerprint({"record_id": "r", "title": "t", "abstract": "x"})
        b = store.record_fingerprint({"record_id": "r", "title": "t", "abstract": "y"})
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
