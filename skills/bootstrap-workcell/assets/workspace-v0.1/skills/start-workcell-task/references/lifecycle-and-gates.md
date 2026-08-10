# Task Lifecycle and Gates

## Single state machine

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

Any active state may explicitly enter `PAUSED`. Discovery is an action within `INBOX`. Repair is an action within `DEV_FEEDBACK` or `TEST_FEEDBACK`; do not create extra states for these actions.

## Transition gates

### INBOX -> SCOPED

- Original requirement, task type, stable ID, and project-plugin reference are recorded.
- Required code, configuration, and project-fact discovery is complete.
- `scope.edit/verify/reference/excluded` has no duplicates and does not expand project roles.
- The user confirmed inclusions, exclusions, unknowns, and safety boundaries.

### SCOPED -> PLANNED

- `current_plan` points to a non-overwriting versioned plan.
- The plan covers every `edit` module and matching tests, verification, compatibility, and rollback.
- Old plans appear in `superseded_plans`.
- Plan evidence and the planning gate are recorded.

### PLANNED -> READY

- Scope and current plan gates are `passed`, or `waived` with explicit decision evidence.
- Required isolated workspace, branch, tools, and environment snapshot are verified.
- Required source writes, remote reads, and diagnostic actions have current task authorization.
- Parallel write scopes do not overlap, and fail-closed conditions are explicit.

### READY -> IMPLEMENTING

- The user explicitly requests implementation.
- The code baseline still matches the plan; on drift, remain in or return to the appropriate earlier state and scope again.
- Every write stays inside `scope.edit`.

### IMPLEMENTING -> VERIFYING

- Planned changes are complete or unfinished work is recorded explicitly.
- The diff matches `scope.edit` and contains no out-of-scope write.
- Matching tests and the verification checklist are complete.

### VERIFYING -> DEV_FEEDBACK / TEST_FEEDBACK / QC_READY

- Development-environment feedback enters `DEV_FEEDBACK`; test-environment feedback enters `TEST_FEEDBACK`.
- Diagnose, repair, and regress within the applicable feedback state, then return to `VERIFYING`.
- Enter `QC_READY` when every required verification passes and residual risks are acceptable.
- Do not enter `QC_READY` when a critical verification cannot run unless an explicit `waived` gate and decision evidence exist.

### QC_READY -> RELEASE_READY

- Independent review and project-specific gates pass.
- Change, test, database, configuration, compatibility, rollback, and release-order material is complete.
- Required manual release actions are listed, and unauthorized actions were not performed.

### RELEASE_READY -> DONE

- The delivery objective defined by the task is complete.
- Final code, test, review, release, or decision evidence is traceable.
- No failed gate or unresolved blocker remains.

### DONE -> ARCHIVED

- Final commits, branches, environments, and delivery summary are traceable.
- The workspace has no unsaved changes, unhandled commits, or unarchived evidence.
- Deleting, compressing, or moving an isolated workspace has separate confirmation. Archiving the task record is not deletion of source copies.

## PAUSED

Use decision evidence to record the state before pause, reason, resume conditions, and unfinished actions. Resume to the earlier state and recheck its gates; do not skip forward.

## Prohibited behavior

- Do not move directly from `INBOX` to `IMPLEMENTING`.
- Do not bypass `workflow.next_gate` and gate evidence by changing only `task.status`.
- Do not wrap feedback repair in a new state name.
- Do not move directly from a feedback state to `DONE`.
- Treat `ARCHIVED` as immutable by default; restoration requires an explicit restore decision or a new task.
