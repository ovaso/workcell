# Feedback Report Contract

The report must satisfy `.ai-workspace/schemas/feedback-report.schema.json`.

- `feedback.id` is a stable report ID and contains no workspace, project, or personal identifier.
- Set `redaction_confirmed` to `true` only after a person reviews the redaction.
- `authorized_sources` lists source categories and records no paths, URLs, or source text.
- `evidence[].summary` is a minimal abstract description and contains no raw logs, code, or business data.
- `scope = standard-candidate` means only eligible for review and does not imply adoption.

Before export, run:

```bash
python3 skills/extract-workcell-feedback/scripts/validate_feedback_report.py feedback/candidates/<report-id>.json
```

On Windows, use `py -3` or another verified Python 3 launcher with the same script and arguments.
