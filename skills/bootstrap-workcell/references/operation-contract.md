# Bootstrap operation contract

## Ownership model

Treat the ownership class as the write authority:

| Ownership | Meaning | Bootstrap behavior |
| --- | --- | --- |
| `distribution` | Immutable files supplied by a release | May restore or replace only through an approved repair or migration |
| `generated` | Files compiled from structured facts and policies | Recompile; never use a template as the sole source of truth |
| `workspace` | User, project, environment, and task state | Preserve across repair and upgrade |

Use `.ai-workspace/distribution.manifest` as the allowlist for distribution-managed relative paths. Reject absolute paths, traversal segments, duplicates, symlinks, and entries absent from the matching release asset.

## Create contract

Accept only an absent or empty explicit target directory. Validate the bundle first, copy through a sibling staging directory, validate the staged workspace, and then rename it into place. Leave the target untouched on precondition or validation failure.

Treat any target change between the emptiness check and installation as a race. Verify that the installed directory has the staged directory identity; if another directory captured the move, recover only the known staged directory and fail without deleting the raced target or reporting success.

Creation ends at `CREATED`. It must not:

- inspect commands, toolchains, environment variables, or network state;
- make network requests;
- install software or modify shell configuration;
- attach repositories, infer project rules, or configure diagnostics;
- claim that the workspace is initialized or ready.

## Validation contract

Keep validation read-only. Validate:

- required entry files and directories;
- supported product and schema versions;
- a recognized lifecycle status;
- manifest syntax and path containment;
- agreement between the repair manifest and `ownership.toml`;
- presence and byte identity of distribution-managed files;
- presence and basic frontmatter identity of bundled runtime Skills.

Validation against this Bootstrap release is exact-version validation. A workspace from another product or product version requires the matching Bootstrap or a declared Migration path. Do not infer a product match from similar paths or matching hashes; establish it from `.ai-workspace/workspace.toml` `managed_by` and the installed Release version.

## Repair contract

Run the plan-only script first. Interpret results as:

| Status | Meaning | Default action |
| --- | --- | --- |
| `OK` | Target matches the release asset | None |
| `MISSING` | Managed path is absent | Propose restoring it |
| `MODIFIED` | Managed file differs | Propose backup, then replacement |
| `TYPE_MISMATCH` | File/directory type differs | Stop for manual resolution |
| `BUNDLE_MISSING` | Manifest references no release asset | Reject the bundle |

Before applying any repair, show the exact paths, create a recoverable backup outside the replaced paths, and obtain explicit user approval. Never repair paths absent from the distribution manifest. Recompile generated content through runtime Skills.

When a manifest entry is a directory and the planner reports `MODIFIED`, expand it with a recursive read-only diff and list the affected child files. Do not treat the directory-level status as approval to replace the whole tree.

## Upgrade contract

Use the following gate sequence:

```text
read installed versions
-> select immutable target release
-> verify migration chain
-> classify file ownership and impact
-> obtain approval
-> create recoverable snapshot
-> apply ordered migrations
-> recompile generated files
-> validate
-> run workspace Doctor
-> keep result or roll back
```

Do not target an unpinned branch head. Do not overwrite the currently executing Skill. Do not apply a cross-product or cross-version change without a formal Migration. The V0.1 preview is fail-closed: it can declare only same-product, same-version replacement safe, and it must report a compatibility conflict rather than silently preserving workspace-owned metadata at another boundary. Workcell 0.3.0 has no in-place Migration from Standard Workspace v0.1; create a new Workcell and transfer only explicitly user-authorized `workspace`-owned material through a recoverable procedure. Treat `.ai-workspace/release-manifest.json` as the installed receipt: it excludes its own hash, inherits trust from the external release checksum, and must be atomically replaced as the final successful upgrade write. V0.1 has no cross-version migration and keeps self-update disabled.

## Failure policy

Fail closed when authorization, ownership, version compatibility, or path safety is unclear. A missing optimization may degrade capability; it never expands authority.
