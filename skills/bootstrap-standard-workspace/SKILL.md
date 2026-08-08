---
name: bootstrap-standard-workspace
description: Create and validate a portable AI-native standard workspace, plan safe repairs for distribution-managed files, and gate versioned upgrades. Use when an AI must expand this bundled workspace into an explicit empty directory, audit an existing standard workspace, recover damaged distribution files, or assess an upgrade without binding the workflow to one AI platform or project.
---

# Bootstrap Standard Workspace

Use this Skill only as the distribution and recovery layer. After creation, use the Skills inside the expanded workspace for environment discovery, project adaptation, diagnostics, tasks, and daily work.

## Enforce the boundary

- Persist content only in the target directory explicitly supplied by the user; allow the create script to use and remove its derived sibling staging directory for atomic installation.
- Treat `assets/workspace-v0.1/` as immutable release content.
- Keep creation offline: do not inspect the host, install tools, modify the shell, attach projects, or configure diagnostics.
- Treat capability as separate from authorization. Never infer permission for remote or destructive actions.
- Preserve `workspace`-owned content during repair or upgrade. Replace only paths proven to be `distribution`-owned.
- Stop on ambiguous ownership, unsafe manifest paths, unsupported versions, missing migrations, or a non-empty creation target.

Read [references/operation-contract.md](references/operation-contract.md) before repair or upgrade. Read [references/bundle-contract.md](references/bundle-contract.md) when auditing, packaging, or changing the bundle.

## Select the operation

### Create

1. Resolve an explicit destination path and confirm the request authorizes creating it.
2. Select the host-native entry point: use `scripts/*.sh` on POSIX hosts and `scripts/*.ps1` from Windows PowerShell 5.1 or PowerShell 7.
3. Run `scripts/validate-bundle.sh` followed by `scripts/create-workspace.sh <target>`, or run `& ./scripts/validate-bundle.ps1` followed by `& ./scripts/create-workspace.ps1 <target>`.
4. Report that the workspace is in `CREATED`, not `READY`.
5. Direct the next AI session to read `AI_WORKSPACE.md` and run the workspace initialization Skill.

Never use the create operation to merge into, seed, or overwrite a non-empty directory.

### Validate

- Run `scripts/validate-bundle.sh` or `& ./scripts/validate-bundle.ps1` to validate this installed Skill and its release assets.
- Run `scripts/validate-workspace.sh <target>` or `& ./scripts/validate-workspace.ps1 <target>` to validate an expanded workspace against this exact bundle version.
- Keep validation read-only. A successful structural validation does not grant operational permissions or prove that the workspace is `READY`.

### Repair

1. Run `scripts/plan-repair.sh <target>` or `& ./scripts/plan-repair.ps1 <target>` and inspect every reported path.
2. Classify the drift using `.ai-workspace/distribution.manifest` and the file-ownership rules.
3. Present the exact replacements and backup location to the user.
4. Obtain explicit approval before writing.
5. Restore only approved `distribution` paths from this exact version's assets.
6. Recompile generated files with workspace runtime Skills instead of copying over them.
7. Re-run validation and the workspace Doctor.

The bundled repair script is intentionally plan-only. Do not turn it into an implicit apply operation.

### Upgrade

1. Read `.ai-workspace/versions.lock` and identify the exact installed version.
2. Select an immutable target release and verify that a complete migration path exists.
3. Produce a file-impact plan separating `distribution`, `generated`, and `workspace` ownership.
4. Require explicit approval and a recoverable snapshot before applying a migration.
5. Apply migrations in order, recompile generated files, validate, and run the Doctor.
6. Roll back on any failed gate.

V0.1 defines the upgrade protocol but ships no cross-version migration and no self-update. If the source and target versions differ, stop rather than improvising an upgrade.

## Interpret results

- Exit `0`: the requested check completed successfully.
- Exit `1`: expected drift or a rejected precondition, such as a non-empty target.
- Exit `2`: invalid invocation, unsafe metadata, or a malformed bundle/workspace.

Report failures with the affected path and the failed invariant. Do not weaken a check merely to continue.
