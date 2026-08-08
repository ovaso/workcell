# Task Contract

## Source of truth and directories

```text
requirements/<task-id>/
  task.toml
  requirement.md
  plans/
  decisions/
  changes/
  evidence/
  logs/
  reviews/
  memory/
workspaces/<task-id>/
  ...created only when the task prepares isolated code...
```

Create only the subdirectories required by the task type; `task.toml` must exist. It is the state source of truth and must satisfy `.ai-workspace/schemas/task.schema.json`. Start from `.ai-workspace/templates/task.toml`; do not maintain a second field definition.

All task content is `workspace`-owned and must not be overwritten by a release upgrade.

## `task` table

Record stable `id`, display name, title, task type, standard `status`, project-plugin reference, and timestamps. Use the task ID for directories, branches, and correlation. The display name may be localized.

Task type uses only `requirement`, `defect`, `diagnostic`, `review`, `maintenance`, or `research`.

## `scope` table

Represent module roles with four arrays of unique strings:

```toml
[scope]
edit = ["service-app"]
verify = ["service-api"]
reference = ["shared-library"]
excluded = ["deployment"]
```

Role ordering is:

```text
excluded / reference < verify < edit
```

- `edit`: modules that the current task may modify; does not include commit, push, release, or external writes automatically.
- `verify`: contract, build, test, and integration-path verification without source modification.
- `reference`: read-only search and context.
- `excluded`: explicitly out of scope, preventing unsupported task expansion.

Project-plugin `modules[].role` in `project/plugin/project-plugin.json` is the ceiling and uses only `edit`, `verify`, or `reference`. A task may narrow but not expand the role, and a module appears in only one scope array. `task.project_plugin_ref` points to that JSON, for example:

```toml
[task]
project_plugin_ref = "project/plugin/project-plugin.json"
```

## `workflow` table

- `current_plan` points to the active versioned plan; use an empty string or null when no plan exists.
- Create a new file for a new plan and append the old path to `superseded_plans`; do not overwrite in place.
- `next_action` and `next_gate` match the current state.
- Derive `branch` from the stable task ID; do not maintain conflicting values in multiple documents.

## `gates` and `evidence`

Gate status uses only `pending`, `passed`, `failed`, `waived`, or `not-applicable`. A `passed` or `waived` gate should provide `evidence_refs`.

Evidence type uses only `requirement`, `plan`, `code`, `test`, `log`, `metric`, `trace`, `review`, `decision`, or `release`. Evidence references identify actual locations and observation times. Memory and verbal conclusions are not sources of truth for state.

The task manifest stores neither credentials nor broad capability switches. Determine whether an action is allowed from core policy, project-plugin policy, diagnostic configuration, and the current user authorization together. Capability does not imply authorization.

## Parallel writes

Record participants, modules, file groups, and read-only or write mode in the plan or `decisions/` evidence, then include the decision file in `evidence`. Only one participant may hold write authority for a file at a time, and no participant may write outside `scope.edit`.

Parallel scheduling is a collaboration boundary and does not change project roles, task scope, or user authorization.
