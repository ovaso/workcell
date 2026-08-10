# Workcell Specification V0.1

## 1. Purpose

Define the minimum structure, lifecycle, states, and file ownership of a workspace expanded by the Bootstrap Skill. Directory structure is a representation of the standard; manifests and schemas are the machine-readable authority.

## 2. Required entry points

- `AI_WORKSPACE.md`: platform-neutral AI entry point.
- `AGENTS.md`: adapter entry point for Codex and other systems that support AGENTS.
- `.ai-workspace/workspace.toml`: workspace identity and current state.
- `.ai-workspace/versions.lock`: release and schema versions.
- `.ai-workspace/release-manifest.json`: complete installed-Release integrity manifest and upgrade receipt.
- `skills/`: workspace runtime Skills.

## 3. Standard directories

```text
environment/   host environment facts and snapshots
project/       project instance, project plugin, and capability configuration
mirror/        mainline or reference code mirrors
remotes/       repository remotes and default-branch registration
requirements/  requirement, defect, diagnostic, and review task records
workspaces/    isolated development workspaces
diagnostics/   non-task-specific diagnostic configuration, Providers, and knowledge
tools/         deterministic project or workspace tools
knowledge/     confirmed reusable knowledge
docs/          project and workspace documentation
memory/        workspace-level session and evolution memory
feedback/      redacted workspace-practice candidates
locales/       reviewed, non-authoritative localized content
```

## 4. Lifecycle

Allowed states:

```text
CREATED
ENVIRONMENT_INITIALIZED
PROJECT_ATTACHED
PROJECT_ADAPTED
DIAGNOSTICS_CONFIGURED
READY
DEGRADED
PAUSED
ARCHIVED
```

Bootstrap may enter only `CREATED`. The workspace may enter `READY` only after the Doctor passes.

## 5. File ownership

- `distribution`: maintained by the release and replaceable through a Migration.
- `generated`: compiled from facts and prohibited as the sole hand-edited source.
- `workspace`: maintained by users, projects, or tasks and preserved by upgrades.

The manifest must determine ownership for every file affected by an upgrade.

V0.1 uses `.ai-workspace/distribution.manifest` to list immutable release paths that support byte-for-byte validation and repair. `.ai-workspace/ownership.toml` describes complete ownership. Runtime-changing files such as `workspace.toml`, `versions.lock`, `AGENTS.md`, environment facts, and diagnostic policies must not appear in the byte-for-byte repair manifest; their initial release values live in `.ai-workspace/templates/`.

V0.1 also uses `.ai-workspace/release-manifest.json` as the installed Release receipt. It satisfies Release Manifest Schema V0.1, records `schema_version = 0.1` and the product `release_version`, and lists every regular file in the release asset except itself with `path`, first-match `owner`, and SHA-256. The receipt does not hash itself. The Bootstrap Skill's outer `checksums/workspace-v0.1.sha256` protects the candidate copy. An upgrade transaction replaces the receipt atomically as its final workspace write, only after every other file, version lock, and validation gate succeeds.

Ownership rules use ordered `first-match` resolution. A rule for a specific file precedes a broader directory rule. Unmatched paths default to `workspace`. Every path in `.ai-workspace/distribution.manifest` must have an exact `distribution` rule; separate `/**` rules cover directory descendants. The Release Manifest resolves ownership for every regular file with the same first-match policy.

Localized content is non-authoritative. Locale profiles and approved translations are `workspace`-owned unless a future immutable locale pack explicitly declares them as `distribution`. Generated language adapters are `generated`. Canonical English specifications, schemas, policies, manifests, commands, IDs, and paths are never replaced by localization.

## 6. Default security state

- Remote actions are denied by default.
- When diagnostics are unconfigured, only local code and existing files may be analyzed.
- Environment initialization must not install tools or modify the shell.
- Before project adaptation, branch, release, diagnostic, and write rules must not be inferred.
- Bootstrap must not overwrite a non-empty directory.

## 7. Platform adapters

Structured policies are sources of truth. `AGENTS.md`, `CLAUDE.md`, and similar files are compiled adapters. When a platform does not read them automatically, it must read `AI_WORKSPACE.md` explicitly.
