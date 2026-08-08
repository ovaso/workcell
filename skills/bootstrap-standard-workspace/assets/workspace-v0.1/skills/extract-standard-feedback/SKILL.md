---
name: extract-standard-feedback
description: Derive redacted practice feedback from authorized task records, control-plane files, and project material in a Standard Workspace, producing reviewable candidates for generic capabilities, specifications, or constraints. Use during post-task retrospectives, periodic workspace reviews, or when preparing practice feedback for the standard repository; do not use it for automatic upload, adoption, or modification of the standard.
---

# Extract Standard Feedback

Convert current workspace practice into machine-readable candidate reports under `feedback/candidates/`. A report is a review signal, not a standard change, and does not replace task, project, or environment facts.

## Collect within the boundary

1. Read `AI_WORKSPACE.md`, workspace policies, and current task authorization. Read only task records and the workspace control plane by default.
2. Obtain explicit authorization for this run before reading project documentation, code, or configuration, and declare `approved-project-material` in the report.
3. Exclude credentials, private variables, remote content, complete logs, business data, source code, project names, repository and host paths, and endpoints by default. Stop without producing a report when reliable redaction is not possible.
4. Do not access the network, upload, read another workspace, modify the standard repository, or change current task state.

## Derive and classify

1. Record only verifiable friction, repeated constraints, capability gaps, and compatibility problems. Separate observations from confirmed conclusions.
2. Assign each candidate scope `local`, `project-plugin`, or `standard-candidate`. Project terms, environment preferences, and one-off experiences cannot be `standard-candidate`.
3. Record a minimal redacted evidence summary, occurrence count, and counterexamples for every candidate. A `standard-candidate` normally requires multiple independent workspaces, except for one confirmed security, integrity, or compatibility defect.
4. Create the report with `scripts/new_feedback_report.py`, then run `scripts/validate_feedback_report.py`. See [feedback-contract.md](references/feedback-contract.md) for fields.

## Output and handoff

1. Write the report to `feedback/candidates/<report-id>.json` without overwriting an existing report.
2. Give the user a short Markdown summary of source categories, candidate count, excluded content, candidate scopes, and unresolved points.
3. Hand the redacted report to a standard-repository maintainer only when the user explicitly requests it. `$integrate-workspace-feedback` creates the proposal. Handoff is not automatic adoption or upgrade.
