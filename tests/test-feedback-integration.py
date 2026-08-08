#!/usr/bin/env python3
"""Validate that feedback import creates pending-review information only."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "skills/integrate-workspace-feedback/scripts/integrate_feedback.py"
SPEC = importlib.util.spec_from_file_location("integrate_feedback", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def report() -> dict:
    return {"schema_version": "0.1", "feedback": {"id": "feedback-test", "workspace_release": "0.1.0", "source_fingerprint": "a" * 64, "redaction_confirmed": True}, "collection": {"mode": "manual", "authorized_sources": ["task-records"]}, "candidates": [{"id": "candidate-test", "kind": "constraint", "area": "skills", "scope": "standard-candidate", "title": "Generic candidate", "summary": "Redacted conclusion.", "confidence": "confirmed", "occurrences": 2, "evidence": [{"kind": "review", "summary": "Redacted evidence."}]}]}


class FeedbackIntegrationTest(unittest.TestCase):
    def test_safe_report_generates_pending_proposal(self) -> None:
        self.assertTrue(MODULE.safe_report(report()))
        ledger = {"schema_version": "0.1", "candidates": {}}
        output = MODULE.proposal(MODULE.merge(ledger, report()))
        self.assertIn("Status: pending review; not adopted or implemented.", output)
        self.assertIn("Pre-adoption gates", output)

    def test_path_in_report_is_rejected(self) -> None:
        document = report()
        document["candidates"][0]["summary"] = "/home/user/private"
        self.assertFalse(MODULE.safe_report(document))


if __name__ == "__main__":
    unittest.main()
