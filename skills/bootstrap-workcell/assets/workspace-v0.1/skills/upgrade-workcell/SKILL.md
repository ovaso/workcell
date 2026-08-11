---
name: upgrade-workcell
description: Safely preview and upgrade Workcell releases, schemas, runtime Skills, and generated adapters while fully protecting user, project, task, and localized content. Use to inspect or apply a stable Release upgrade, execute a Migration, validate or roll back an upgrade, or update the workspace standard version; require source verification, an impact preview, a recoverable snapshot, and explicit approval before applying changes.
---

# Upgrade Workcell

Treat an upgrade as a controlled migration, not a file overwrite. Replace only `distribution`, recompile `generated`, and preserve `workspace` completely.

## Enforce the boundary

- Accept only an immutable stable Release with an explicit version and complete file hashes. Do not use `main`, the latest commit, or an unverified directory as an automatic target.
- Inspect and preview by default. Download, write, overwrite, delete, migrate, switch, and roll back each require applicable authorization.
- The presence of Git, network, extraction, or copy capabilities does not authorize those actions.
- Do not overwrite the currently executing Skill in place. Put a candidate version in a temporary or sibling directory, validate it, then switch.
- The installed receipt is `.ai-workspace/release-manifest.json`. It does not hash itself and must gain trust from the matching Release's outer Bootstrap checksum.
- Fail closed when the current manifest, candidate manifest, ownership, Migration chain, checksums, or recovery plan is missing.
- Treat `managed_by` in `.ai-workspace/workspace.toml` and the Release version as compatibility gates. This preview can declare only a same-product, same-version file replacement safe; it does not implement or infer Migrations.
- Workcell 0.2.0 has no in-place Migration from Standard Workspace v0.1. Create a new Workcell instead, then transfer only selected `workspace`-owned material after explicit user authorization.

## Preflight and preview

1. Read `AI_WORKSPACE.md`, `.ai-workspace/workspace.toml`, `.ai-workspace/versions.lock`, `.ai-workspace/release-manifest.json`, and ownership rules. Confirm first that the installed receipt satisfies Schema V0.1 and does not list itself in `files`.
2. Run `$workcell-doctor` for the pre-upgrade baseline. Explain existing errors first; do not use an upgrade to overwrite unknown problems.
3. Obtain the user-specified candidate Release. Confirm authorization before network access or download, then validate version, provenance, manifest, SHA-256, and available signatures.
4. Compare the current and candidate product identities and Release versions before considering file actions. Stop on any product or version difference unless a separately verified formal Migration is available for execution; this bundled preview still reports that boundary as a conflict rather than applying or approving it.
5. Run the read-only preview:

   ```bash
   python3 skills/upgrade-workcell/scripts/preview_upgrade.py \
     --workspace /absolute/workspace \
     --current-manifest /absolute/workspace/.ai-workspace/release-manifest.json \
     --candidate-root /absolute/candidate-release \
     --candidate-manifest /absolute/candidate-release/.ai-workspace/release-manifest.json \
     --json
   ```

   On Windows, run the same cross-platform script with `py -3` or another verified Python 3 launcher and pass the arguments on one line or use PowerShell backtick continuations.

6. Follow [upgrade-protocol.md](references/upgrade-protocol.md) to show additions, replacements, removals, regeneration, preservation, ownership changes, conflicts, and the final `replace-receipt` action. The preview applies no files.
7. Keep local release-file modifications, unknown existing files, ownership changes, missing candidate files, hash mismatches, and every product or version boundary without a formal Migration blocked. Do not select "take the new version" automatically.

## Snapshot and confirm

1. Choose a snapshot that can genuinely restore the workspace: a complete file snapshot, or a trusted VCS checkpoint plus every affected untracked and workspace-metadata file.
2. Put the snapshot outside paths affected by the upgrade, generate a manifest and checksums, and verify it can be read.
3. Show target version, Migrations, exact file impact, conflict handling, generated-file reconstruction, snapshot location, rollback steps, and expected external actions.
4. Wait for explicit confirmation of this exact plan. An earlier generic request to upgrade does not replace confirmation after the impact preview.

## Apply

1. Validate candidate content in a sibling staging directory and record an upgrade transaction log.
2. Apply Migrations in order:
   - replace only unmodified `distribution` files;
   - rebuild `generated` through compilers rather than treating candidate generated files as authoritative;
   - do not overwrite, delete, or move `workspace`, including `locales/`; new workspace templates are optional seeds only;
   - apply the user-selected strategy to confirmed conflicts and record each decision.
3. After every step, verify that paths remain inside the workspace, hashes match the plan, and user content remains present. Stop on unplanned impact.
4. Recompile AI adapters after Migrations, then run the complete `$workcell-doctor` and release validation.
5. Update `.ai-workspace/versions.lock` and the current release pointer only after every validation passes.
6. Compare candidate `.ai-workspace/release-manifest.json` bytes again with the candidate protected by the outer checksum, then replace the installed receipt atomically. This is the transaction's final workspace write. Roll back if it fails.

## Failure and rollback

- Stop subsequent Migrations after any failure.
- By default, roll back applied actions from the verified snapshot and run the Doctor again.
- If the user requests preservation of the failed state, confirm it, keep the workspace `DEGRADED`, and identify fail-closed capabilities.
- Do not remove the candidate, snapshot, or transaction log until the user confirms stability and authorizes cleanup.

## Complete

Report current and target versions, Release verification, Migrations, actual file actions, preserved workspace content, conflict decisions, snapshot and rollback locations, Doctor result, and current lifecycle state. State which download, deletion, self-update, and external actions were not performed.
