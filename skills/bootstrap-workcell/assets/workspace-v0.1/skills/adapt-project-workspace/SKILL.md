---
name: adapt-project-workspace
description: Interactively attach and adapt an existing local single-repository or multi-repository project to a Workcell by asking targeted questions, verifying answers against Git, code, build files, tests, and project rules, separating facts from inferences and policies, and generating a validated project plugin plus project instance bindings. Use after host initialization, when onboarding or migrating a project, or when repository structure, workflows, or risk rules materially change; do not fetch, clone, or modify project code by default.
---

# Adapt Project Workspace

Build a project-specific plugin from confirmed intent and current code evidence. Keep stable project rules out of the generic workspace core and keep host-specific paths out of the reusable plugin.

## Enforce the safety boundary

- Default to local, read-only inspection.
- Do not clone, fetch, pull, checkout, merge, install dependencies, run builds, or edit project code without separate explicit authorization.
- Do not treat a configured remote as proof that network access or mutation is allowed.
- Do not persist credentials, credential-bearing URLs, environment values, or private host paths in the reusable project plugin.
- Treat existing AGENTS, plans, memory, and documentation as declared or historical evidence until current code and user confirmation resolve conflicts.
- Preview every generated project artifact before writing it.
- Leave lifecycle unchanged when required facts remain contradictory or plugin validation fails.

Read [references/project-adaptation-contract.md](references/project-adaptation-contract.md) before proposing the project plugin.

## Verify the workspace precondition

1. Resolve and confirm the Workcell root.
2. Read the workspace manifest, active environment snapshot, and policies.
3. Require `ENVIRONMENT_INITIALIZED`, `PROJECT_ATTACHED`, `DEGRADED`, or an explicitly approved repair state.
4. Confirm that every inspection command is available in the active execution context; otherwise use a safe alternative or mark the check unresolved.

## Ask targeted questions

Ask in small groups and verify answers later. Cover:

### Identity and repository model

- project ID and display name;
- single repository, monorepo, or coordinated multi-repository model;
- existing local repository roots and which are authoritative;
- expected default branches and whether remotes are reference-only or may later be synchronized.

### Module intent

- modules that may normally be edited;
- modules limited to verification or read-only reference;
- generated, vendored, third-party, or archived paths;
- dependency and release ordering between modules.

### Workflows and policy

- build, unit-test, integration-test, lint, Review, release, and rollback commands;
- branch protection and allowed merge directions;
- required task isolation and workspace layout;
- high-risk contracts, data migrations, serialization, billing, security, or runtime paths;
- explicit prohibitions and authorization boundaries.

Treat an unanswered question as unresolved. Do not fill it from habit or another project.

## Perform code and Git discovery

Inspect only the confirmed local roots. Prefer fast read-only discovery such as `rg --files`, `rg`, repository-native manifest readers, and Git plumbing commands.

Verify at least:

- repository boundaries, worktrees, configured remotes, current branches, local default-branch refs, and dirty state;
- build manifests, lockfiles, workspace definitions, language versions, and toolchain manager files;
- test source sets, test runners, lint/static-analysis configuration, and CI workflow commands;
- module dependencies and generated-code boundaries;
- database migration locations and naming conventions when present;
- checked-in AI instructions, contribution rules, release scripts, diagnostic configuration, and risk documentation.

Do not run `git fetch` merely to discover a remote default branch. Record locally observed refs and mark remote freshness unresolved.

## Separate facts, inferences, and policies

Maintain three explicit sets throughout adaptation:

1. **Facts** — user declarations, Git/config/code observations, source, time, context, confidence, and sensitivity.
2. **Inferences** — conclusions such as module ownership or workflow ordering, each citing supporting fact IDs.
3. **Policies** — confirmed rules and authorization boundaries with their authoritative source.

Resolve conflicts in this order unless a stronger safety rule applies:

```text
current explicit user confirmation
> current runtime or endpoint verification
> current checked-in configuration and code
> existing project plugin declaration
> project documentation
> historical plans and memory
```

Never use that order to weaken a core safety prohibition.

## Propose project artifacts

Generate two logically separate artifacts:

### Reusable project plugin

Store stable project differences only:

- identity, plugin/API version, and repository model;
- logical repositories, modules, default branches, and maximum module roles;
- selected technology adapters;
- build, test, verify, review, release, rollback, and close workflows;
- high-risk areas, knowledge entry points, enabled capabilities, policies, and unresolved questions;
- evidence references for non-obvious claims.

Use `edit`, `verify`, and `reference` roles. A task may narrow these roles but must not silently expand them.

### Local project instance

Store host-specific and runtime bindings separately:

- absolute local paths;
- configured remote names and sanitized URL references;
- current branch, dirty state, ahead/behind state when locally knowable;
- active environment snapshot and variable-name references;
- mirror and task-workspace bindings.

Do not place these dynamic bindings in the reusable plugin.

## Generate and validate the plugin

When Python 3 is verified, resolve this Skill directory and use `scripts/build_project_plugin.py` by absolute path.

1. Prepare a candidate JSON document following the reference contract.
2. Run the script without `--output` to validate and preview canonical JSON.
3. Show the user the plugin, unresolved questions, and any excluded sensitive or runtime fields.
4. After explicit approval, run with `--output <project/plugin/project-plugin.json>`.
5. Write the local project instance separately and validate all referenced repository and module IDs.

The script refuses invalid roles, duplicate IDs, absolute plugin paths, credential-like fields, and overwrites without `--force`.

If Python 3 is unavailable, produce the same candidate manually and report that deterministic validation was unavailable. Do not claim the plugin is validated.

## Advance lifecycle conservatively

1. Record `PROJECT_ATTACHED` only after local repository bindings are confirmed and persisted.
2. Record `PROJECT_ADAPTED` only after the approved plugin and project instance both validate.
3. Do not mark the workspace `READY`; diagnostics and Doctor may still be required.
4. On partial failure, retain validated evidence but leave the previous lifecycle state active.

## Finish with a concise handoff

Report:

- repository model and confirmed roots;
- edit, verify, and reference modules;
- verified build/test/Review/release workflows;
- policy conflicts resolved and unresolved questions remaining;
- plugin and instance paths;
- lifecycle transition performed or withheld;
- recommended next Skill, normally project diagnostics or workspace Doctor.
