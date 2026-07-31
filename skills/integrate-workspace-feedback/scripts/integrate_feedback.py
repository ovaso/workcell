#!/usr/bin/env python3
"""归一化反馈、按独立工作区聚合证据，并生成待审核 Change Set 提案。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

FORBIDDEN = re.compile(r"/Users/|/home/[^/]+/|\\\\Users\\\\|https?://|(?:api[_-]?key|password|secret|token)\\s*[:=]", re.I)


def walk_strings(value: Any):
    if isinstance(value, str): yield value
    elif isinstance(value, dict):
        for child in value.values(): yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value: yield from walk_strings(child)


def safe_report(document: Any) -> bool:
    feedback = document.get("feedback", {}) if isinstance(document, dict) else {}
    return bool(isinstance(document, dict) and document.get("schema_version") == "0.1" and feedback.get("redaction_confirmed") is True and re.fullmatch(r"[0-9a-f]{64}", feedback.get("source_fingerprint", "")) and not any(FORBIDDEN.search(value) for value in walk_strings(document)))


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists(): return {"schema_version": "0.1", "candidates": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def merge(ledger: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
    """按稳定候选 ID 合并，并只用不可逆指纹计数独立工作区。"""
    source = report["feedback"]["source_fingerprint"]
    changed = []
    for item in report["candidates"]:
        if item.get("scope") != "standard-candidate": continue
        key = f"{item.get('area')}:{item.get('id')}"
        entry = ledger["candidates"].setdefault(key, {"id": item["id"], "area": item["area"], "kind": item["kind"], "title": item["title"], "summary": item["summary"], "sources": [], "reports": [], "evidence": []})
        if source not in entry["sources"]: entry["sources"].append(source)
        report_id = report["feedback"]["id"]
        if report_id not in entry["reports"]: entry["reports"].append(report_id)
        for evidence in item["evidence"]:
            if evidence not in entry["evidence"]: entry["evidence"].append(evidence)
        changed.append(entry)
    return changed


def proposal(entries: list[dict[str, Any]]) -> str:
    lines = ["# Evolution Change Set Proposal", "", "状态：待审核，未采纳、未实施。", ""]
    for entry in entries:
        sources = len(entry["sources"])
        eligibility = "可进入采纳评审" if sources >= 2 else "待聚合更多独立工作区证据"
        lines += [f"## {entry['title']}", "", f"- 规范化 ID：`{entry['area']}:{entry['id']}`", f"- 独立工作区：{sources}；报告数：{len(entry['reports'])}", f"- 结论：{eligibility}", f"- 摘要：{entry['summary']}", "- 受影响对象：待审核（Spec / Schema / Skill / Asset / Migration / 平台适配）。", "- 采纳前门禁：反例、兼容性、所有权、迁移、完整回归和用户确认。", ""]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: integrate_feedback.py REPORT.json", file=sys.stderr); return 2
    try: report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: print(f"无法读取反馈报告：{error}", file=sys.stderr); return 1
    if not safe_report(report): print("反馈报告未通过脱敏、来源指纹或基本结构检查。", file=sys.stderr); return 1
    root = Path(__file__).resolve().parents[3]
    ledger_path = root / "evolution/ledger/evidence.json"; ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = load_ledger(ledger_path); entries = merge(ledger, report)
    if not entries: print("报告没有可导入的 standard-candidate。", file=sys.stderr); return 1
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output = root / "evolution/proposals" / f"{report['feedback']['id']}.md"
    if output.exists(): print(f"拒绝覆盖已有提案：{output}", file=sys.stderr); return 1
    output.write_text(proposal(entries), encoding="utf-8"); print(output); return 0


if __name__ == "__main__": raise SystemExit(main())
