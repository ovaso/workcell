---
name: workcell-doctor
description: Run read-only-first health checks on a Workcell, covering structure, the installed Release receipt and distribution hashes, manifests, lifecycle, Skills, task roles, diagnostic safety, and file ownership. Use for acceptance after initialization or adaptation, before entering READY or starting a task, before and after upgrades, while investigating configuration drift, or when a user asks to inspect, diagnose, or repair a Workcell.
---

# Workcell Doctor

Establish facts with deterministic read-only checks, then recommend the smallest repair. Discovering a repair does not grant write authority.

## Run by default

1. Locate a workspace root containing `AI_WORKSPACE.md` and `.ai-workspace/workspace.toml`. Stop if it cannot be found; do not misclassify an ordinary project directory as a Workcell.
2. Read `AI_WORKSPACE.md`, `.ai-workspace/workspace.toml`, `.ai-workspace/versions.lock`, `.ai-workspace/release-manifest.json`, and project and diagnostic configuration without reading credential values.
3. Run the read-only checker:

   ```bash
   python3 -B skills/workcell-doctor/scripts/doctor.py /absolute/workspace/path --json
   ```

   On Windows, run the same cross-platform script with `py -3 -B skills/workcell-doctor/scripts/doctor.py C:\absolute\workspace\path --json` or another verified Python 3 launcher.

4. Use [checks.md](references/checks.md) for code, Git, generation-chain, and external-fact checks that the script cannot decide. Every external verification still requires applicable authorization.
5. Report issues by severity with evidence paths, impact, fail-closed scope, and recommended actions.
6. Pass the structural gate only when no `ERROR` exists. Do not mark the workspace `READY` while authorization is unresolved, facts are stale, or a critical condition cannot be verified.

## Read-only boundary

- Do not create missing files, modify manifests, format, delete, install tools, access the network, update Git references, or start services automatically.
- Do not execute configured diagnostic Providers. The Doctor validates their declarations and locally visible structure only. Endpoint health checks require user authorization and run through the diagnostic workflow.
- Do not silently downgrade warnings. Unparseable sources of truth, invalid lifecycle transitions, task-role escalation, permissive diagnostic defaults, and ownership conflicts are errors.
- Do not follow unknown symlinks to scan outside the workspace.

## Repair mode

Enter repair mode only after the user explicitly requests repair:

1. Classify every repair as pure generation, workspace configuration change, user-content change, or external action.
2. Preview exact file impact and commands. For overwrite, deletion, migration, or external state, create a recoverable snapshot and confirm again.
3. Apply only authorized repairs and preserve unknown and project-owned content.
4. Run the complete Doctor again. Do not bypass errors by changing status to `READY` manually.

## Output

Lead with `PASS`, `PASS_WITH_WARNINGS`, or `FAIL`. Then list `ERROR`, `WARN`, and `INFO` items with check code, path, factual evidence, and recommendation. Finish with:

- current workspace lifecycle state;
- capabilities that fail closed;
- whether conditions for `READY` are satisfied;
- whether any modification was made;
- repair actions still awaiting authorization.
