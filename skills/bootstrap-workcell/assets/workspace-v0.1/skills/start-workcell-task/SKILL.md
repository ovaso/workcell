---
name: start-workcell-task
description: Create and advance machine-readable requirement, defect, diagnostic, review, maintenance, or research tasks in a Workcell, including the task record, standard lifecycle, edit/verify/reference module roles, authorization, risks, plans, evidence, and isolated workspace. Use when starting a task, converting an inbox item into executable work, resuming a paused task, or reconfirming scope and module responsibilities before implementation.
---

# Start Standard Task

Turn a user request into a traceable, pausable, parallelizable task that does not expand permissions by default. `requirements/<task-id>/task.toml` is the source of truth for task state.

## Check prerequisites

1. Read `AI_WORKSPACE.md`, `.ai-workspace/workspace.toml`, the project plugin, environment facts, and applicable project rules.
2. Require workspace state `READY`. For `DEGRADED`, `PAUSED`, or an earlier state, run `$workcell-doctor` and resolve blockers instead of bypassing gates by creating a task.
3. Check whether the task ID already exists. If it does, read and resume it; do not overwrite the record or reset the lifecycle.
4. Treat the current user request as the authorization boundary. Installed tools, reachable remotes, and project module roles do not automatically grant write, push, deployment, or production access.

## Create the INBOX task

1. Confirm title, type, stable ID, and original request. Use type `requirement`, `defect`, `diagnostic`, `review`, `maintenance`, or `research`.
2. Copy and fill `.ai-workspace/templates/task.toml`, then create the minimum directory defined by [task-contract.md](references/task-contract.md).
3. Write the user's original description to `requirement.md`, preserving provenance, attachments, and unresolved points. Do not rewrite inferences as user facts.
4. Set initial status `INBOX`, `workflow.next_action`, and `workflow.next_gate = "SCOPED"`. Project policy continues to deny unconfirmed remote reads, source writes, and external side effects.

## Discover and scope

1. During `INBOX`, perform authorized local read-only discovery across code, Git, configuration, project knowledge, and historical tasks. Separate facts, inferences, and unresolved points.
2. Read role ceilings from the project plugin and place module IDs in the machine-readable task `scope` arrays:
   - `edit`: modules explicitly authorized for modification by this task;
   - `verify`: modules used for contracts, compilation, tests, and integration-path verification without source modification;
   - `reference`: read-only search and context;
   - `excluded`: modules or scope explicitly outside this task.
3. Default unregistered modules and modules with insufficient evidence to `reference` and mark the issue as a blocker. Project-plugin `modules[].role` is the ceiling for the matching task role: `reference` cannot become `verify` or `edit`, and `verify` cannot become `edit`.
4. Ask the user to confirm scope, exclusions, module roles, risks, environments, and new authorization. Advance to `SCOPED` after confirmation.

## Plan and gate READY

1. Create a non-overwriting versioned plan under `plans/` that records the code baseline, implementation steps, corresponding tests, compatibility, rollback, and required verification evidence.
2. Point `current_plan` to the latest plan and advance to `PLANNED` after plan confirmation.
3. Prepare `workspaces/<task-id>/`, read remotes, create branches, or install task tools only after explicit authorization. Record authorization and results separately for every action.
4. Follow [lifecycle-and-gates.md](references/lifecycle-and-gates.md) to check scope, plan, modules, workspace, tests, and write-authorization gates. Advance the task to `READY` only after all pass.
5. Do not start business implementation automatically in this Skill. Enter `IMPLEMENTING` only when the user continues with an implementation request.

## Parallel collaboration

- Split work by module or non-overlapping file group, and record owner, role, scope, and status in the versioned plan or decision evidence.
- Permit only one write owner for a module or file group at a time; other participants use `verify` or `reference`.
- A child task cannot expand parent authorization, module roles, or environment scope.
- Before accepting results, the integrator checks actual files, Git diff, test evidence, and the task manifest. Do not treat an agent's narrative as completion evidence.

## Update state

- On every state change, update `task.status`, `task.updated_at`, `workflow.next_action`, `workflow.next_gate`, gates, and decision evidence together. Do not change only Markdown descriptions.
- Do not skip lifecycle states. Route failures and test feedback through the standard feedback states.
- When pausing, write `PAUSED` and record the previous state, reason, resume conditions, and unfinished actions in decision evidence.
- Follow [lifecycle-and-gates.md](references/lifecycle-and-gates.md) for completion, `QC_READY`, `RELEASE_READY`, and archive. Do not substitute "code is written" for verification evidence.

## Complete

Report task ID, current status, task directory, module roles, current authorization, prohibited actions, active plan, isolated workspace, risks, next gate, and next action. State whether this run modified source or external state.
