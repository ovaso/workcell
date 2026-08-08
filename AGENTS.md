# AGENTS

## Scope

This file governs only the `std-workspace` product source. It does not modify or replace the business rules of any external project.

## Product principles

- Remain platform-neutral. Platform files for Codex, Claude Code, and similar systems are adapters and must not become the sole source of truth.
- Remain text-only, reviewable, and distributable or upgradable through Git.
- The Bootstrap Skill is responsible only for creation, validation, repair, and upgrade. Daily runtime capabilities belong to the Skills in the expanded workspace.
- Structured manifests, schemas, facts, and policies are sources of truth. Files such as AGENTS are generated AI adapters.
- Environment, project, and diagnostic runtime facts must be established by initialization and must not be inferred directly from historical documentation.
- Capability does not imply authorization. Diagnostic and external actions must satisfy environment capability, Provider support, project policy, and task authorization.
- Default to read-only and fail closed. Installing tools, modifying the environment, accessing remote systems, overwriting user content, and applying upgrades require explicit authorization.

## Language convention

- Canonical product documentation, specifications, operator messages, metadata, code comments, and error messages use English.
- Skill names, directory names, file names, schema fields, state enums, commands, and stable IDs use English ASCII.
- Localized content is generated only through an explicit localization workflow. It must remain separate from the canonical English control plane and must not change machine-readable identifiers.

## File ownership

- `distribution`: maintained by the release and replaceable through a Migration.
- `generated`: compiled from structured facts and not maintained manually.
- `workspace`: maintained by the workspace, project, or user and preserved by upgrades.

Every new template or specification must declare its ownership.

## Skill rules

- Every Skill must contain a valid `SKILL.md`; names use lowercase hyphen-case.
- Keep `SKILL.md` concise and place detailed specifications in `references/`.
- Put repeatable, fragile, or consistency-sensitive behavior in `scripts/` whenever practical.
- Put files intended for expansion in `assets/`.
- Do not add README files, installation guides, or duplicated explanations inside a Skill.
- Every Skill must pass Skill Creator's `quick_validate.py`.

## Changes and validation

- Limit all modifications to this repository.
- When modifying scripts, add or update the corresponding tests.
- When modifying schemas, run JSON parsing and example validation.
- When modifying templates, run the Bootstrap tests and Workspace Doctor.
- Do not commit, push, or publish automatically.

## Current security boundary

- The V0.1 Bootstrap does not access the network, install software, or modify the shell. It writes only to an explicitly specified empty directory.
- When V0.1 diagnostic capabilities are unconfigured, all remote diagnostic actions are denied by default.
- Self-update defines a protocol only. Do not apply updates automatically until there is a unique repository, formal releases, and signature or hash verification.
