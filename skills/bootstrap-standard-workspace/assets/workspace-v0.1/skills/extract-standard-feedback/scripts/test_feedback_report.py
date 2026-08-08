#!/usr/bin/env python3
"""Validate redaction and structural gates for feedback reports."""

from __future__ import annotations

import unittest

from validate_feedback_report import validate


def report(summary: str = "A redacted generic conclusion.") -> dict:
    return {"schema_version": "0.1", "feedback": {"id": "feedback-test", "workspace_release": "0.1.0", "source_fingerprint": "a" * 64, "redaction_confirmed": True, "created_at": "2026-07-31T12:00:00Z"}, "collection": {"mode": "manual", "authorized_sources": ["task-records"]}, "candidates": [{"id": "candidate-test", "scope": "standard-candidate", "evidence": [{"kind": "task", "summary": summary}]}]}


class FeedbackReportTest(unittest.TestCase):
    def test_valid_minimum_report_passes(self) -> None:
        self.assertEqual([], validate(report()))

    def test_unredacted_report_is_rejected(self) -> None:
        document = report()
        document["feedback"]["redaction_confirmed"] = False
        self.assertTrue(validate(document))

    def test_absolute_path_is_rejected(self) -> None:
        self.assertTrue(validate(report("See /" + "Users" + "/example/private.txt")))


if __name__ == "__main__":
    unittest.main()
