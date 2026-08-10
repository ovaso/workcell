---
name: integrate-workcell-feedback
description: Validate redacted workspace feedback explicitly imported into the Workcell source repository and generate reviewable Workcell-evolution proposals. Use when aggregating practices from multiple workspaces, deciding candidate ownership, or preparing a later version; do not use it for automatic adoption, release-asset modification, publication, or workspace upgrade.
---

# Integrate Workcell Feedback

Process reports that a user explicitly places in `evolution/inbox/` of the Workcell source repository. The inbox is local and Git-ignored; only proposals may enter reviewable history.

## Import

1. Read `specs/workspace-evolution-spec-v0.1.md` and the report schema.
2. Confirm that the user explicitly supplied the report and that it contains only redacted JSON. Do not scan other directories, access the network, or collect workspace content.
3. Run `scripts/integrate_feedback.py REPORT.json`. Process only `standard-candidate`; `local` and `project-plugin` candidates remain in their original workspace.
4. Review generated `evolution/proposals/<report-id>.md`. Source counts, counterexamples, evidence strength, compatibility, ownership, affected files, Migration plan, and test plan must be complete.
5. A report or proposal is not adoption. Modify specifications, schemas, Skills, assets, versions, or distributions only in a separate change after user confirmation.

## Safety and integrity

- Reject reports containing URLs, absolute paths, or common credential markers. Automated checks are defense in depth and do not replace human redaction review.
- Do not overwrite an existing proposal or reuse a proposal ID.
- One report cannot prove a cross-workspace pattern. Keep the proposal pending aggregation until it meets the independent-source threshold.
- See [evolution-protocol.md](references/evolution-protocol.md) for thresholds and versioning rules.
