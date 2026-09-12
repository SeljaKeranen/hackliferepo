"""Tests for the negative-control report's pure logic.

Uses a stub classifier and monkeypatched loader so nothing here needs the
30MB XLSX or ratio/classify.py's ruleset.
"""
import unittest
from unittest.mock import patch

from ukhra import negative_control
from ukhra.benchmark import UkhraAward


def _award(award_id, title="t", abstract="a", value=1000.0, hcs=(), coding="Manual"):
    return UkhraAward(
        award_id=award_id, funder="F", title=title, abstract=abstract,
        value_2022_gbp=value, health_categories=list(hcs), ra_groups=[],
        coding_type=coding,
    )


AWARDS = [
    # numerator label on a non-ageing human category -> flagged suspicious
    _award("leak", hcs=("Infection",), value=100.0),
    # numerator label on an age-related category -> not flagged
    _award("ok", hcs=("Cancer and Neoplasms",), value=200.0),
    # denominator-only label
    _award("ard", hcs=("Cardiovascular",), value=700.0),
    # outside the ratio entirely
    _award("irrelevant", hcs=("Infection",), value=9999.0),
    # excluded before scoring: algorithmically coded
    _award("auto", hcs=("Infection",), value=5000.0, coding="Automated"),
]

LABELS = {
    "leak": "intervention",
    "ok": "fundamental_aging",
    "ard": "age_related_disease",
    "irrelevant": "not_relevant",
    "auto": "fundamental_aging",
}


def _stub_classifier(title, abstract):
    award_id = title  # the stub encodes the id in the title
    return {"label": LABELS[award_id], "matched_keywords": {LABELS[award_id]: ["rapamycin"]}}


class TestNegativeControl(unittest.TestCase):
    def setUp(self):
        self.awards = [
            _award(a.award_id, title=a.award_id, hcs=a.health_categories,
                   value=a.value_2022_gbp, coding=a.coding_type)
            for a in AWARDS
        ]

    def _run(self):
        with patch.object(negative_control, "load_ukhra", return_value=self.awards):
            return negative_control.run("ignored.xlsx", _stub_classifier)

    def test_excludes_algorithmically_coded_rows(self):
        report = self._run()
        self.assertEqual(report["corpus"]["awards_scored"], 4)

    def test_ratio_uses_only_substantive_labels_in_denominator(self):
        report = self._run()
        # numerator 100 + 200; denominator adds age_related_disease 700.
        # The not_relevant award's 9,999 must stay out of both.
        self.assertAlmostEqual(report["funding_gap_ratio_on_ukhra"], 300.0 / 1000.0)

    def test_flags_numerator_label_on_non_ageing_category_only(self):
        report = self._run()
        flagged = report["suspicious_numerator_labels"]
        self.assertEqual(flagged["count"], 1)
        self.assertEqual(flagged["examples"][0]["award_id"], "leak")

    def test_reports_keyword_drivers_per_label(self):
        report = self._run()
        self.assertEqual(report["keyword_drivers"]["age_related_disease"]["rapamycin"], 1)

    def test_numerator_share_counts_awards_not_funding(self):
        report = self._run()
        self.assertAlmostEqual(report["numerator_share_of_awards"], 2 / 4)


if __name__ == "__main__":
    unittest.main()
