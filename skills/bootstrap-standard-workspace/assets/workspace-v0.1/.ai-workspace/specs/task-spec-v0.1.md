# Standard Task Specification V0.1

## 1. Purpose

Requirements, defects, diagnostics, reviews, maintenance, and research are represented as independent task instances. The task manifest is the only machine-readable entry point for current state. Plans, memory, Git, and logs are evidence and must not be used to infer task state in reverse.

## 2. Stable ID and display name

Every task maintains:

- `id`: a stable machine ID used for directories, branches, commands, and correlation;
- `display_name`: a human-readable localized name;
- `title`: a concise objective for this task.

Derive directories and branches from `id`; do not maintain inconsistent copies manually.

V0.1 machine IDs contain only lowercase ASCII letters, digits, dots, underscores, and hyphens. Spaces and localized display characters belong in `display_name`. A project plugin may define a branch prefix but must not change the task ID.

## 3. Lifecycle

```text
INBOX
-> SCOPED
-> PLANNED
-> READY
-> IMPLEMENTING
-> VERIFYING
-> DEV_FEEDBACK / TEST_FEEDBACK
-> QC_READY
-> RELEASE_READY
-> DONE
-> ARCHIVED
```

Any active state may explicitly enter `PAUSED`. Every transition records the next action and next gate; changing only the status field is invalid.

## 4. Module roles

- `edit`: modules that the current task may modify.
- `verify`: modules used only for contracts, builds, or integration-path verification.
- `reference`: read-only reference modules.
- `excluded`: modules or scope explicitly excluded from the task.

Parallel-agent write ownership must stay within `edit`, and the same file must not be owned by multiple agents simultaneously.

## 5. Plans and history

- `current_plan` points explicitly to the active plan.
- A new plan must not overwrite an older version in place; older plans move to `superseded_plans`.
- Plans describe intended work, verification, and risks. Execution facts belong in change records and evidence.
- Memory may help resume a session but is not the source of truth for task state.

## 6. Gates and evidence

Gate status is one of `pending / passed / failed / waived / not-applicable`. Every `passed` or `waived` status should reference evidence or a decision record.

Evidence types include at least requirement, plan, code, test, log, metric, trace, review, decision, and release material. A raw-log manifest records provenance, time window, correlation identifiers, redaction, and retention policy.

## 7. Security boundary

Task authorization may narrow or temporarily open a registered project capability but cannot bypass core prohibitions. The presence of a command in the environment or a configured Provider in the project does not authorize its use for the current task.

## 8. Recommended directory

```text
requirements/<task-id>/
├── task.toml
├── requirement.md
├── plans/
├── decisions/
├── changes/
├── evidence/
├── logs/
├── reviews/
└── memory/
```

The task type determines which optional subdirectories are created; `task.toml` must always exist.
