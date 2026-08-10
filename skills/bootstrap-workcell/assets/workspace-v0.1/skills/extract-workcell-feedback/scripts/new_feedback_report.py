#!/usr/bin/env python3
"""Create a non-overwriting single-candidate feedback report skeleton."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--workspace-release", required=True)
    parser.add_argument("--source-fingerprint", required=True, help="Irreversible SHA-256 fingerprint generated locally by the workspace")
    parser.add_argument("--mode", choices=["manual", "task-close", "periodic"], required=True)
    parser.add_argument("--source", action="append", choices=["task-records", "workspace-control-plane", "approved-project-material"], required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--kind", choices=["constraint", "capability", "specification", "local-practice"], required=True)
    parser.add_argument("--area", choices=["workspace", "task-lifecycle", "facts", "authorization", "diagnostics", "skills", "upgrade"], required=True)
    parser.add_argument("--scope", choices=["local", "project-plugin", "standard-candidate"], required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--confidence", choices=["observed", "confirmed"], required=True)
    parser.add_argument("--occurrences", type=int, required=True)
    parser.add_argument("--evidence-kind", choices=["task", "decision", "doctor", "test", "review", "manual"], required=True)
    parser.add_argument("--evidence-summary", required=True)
    arguments = parser.parse_args()
    output = Path(arguments.output)
    if output.exists():
        parser.error(f"Refusing to overwrite existing report: {output}")
    if arguments.occurrences < 1:
        parser.error("--occurrences must be at least 1")
    document = {"schema_version": "0.1", "feedback": {"id": arguments.id, "workspace_release": arguments.workspace_release, "source_fingerprint": arguments.source_fingerprint, "redaction_confirmed": True, "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}, "collection": {"mode": arguments.mode, "authorized_sources": sorted(set(arguments.source))}, "candidates": [{"id": arguments.candidate_id, "kind": arguments.kind, "area": arguments.area, "scope": arguments.scope, "title": arguments.title, "summary": arguments.summary, "confidence": arguments.confidence, "occurrences": arguments.occurrences, "evidence": [{"kind": arguments.evidence_kind, "summary": arguments.evidence_summary}]}]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
