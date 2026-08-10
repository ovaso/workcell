# AGENTS

> This file is the AI-platform adapter entry point for the Workcell workspace. Structured policies and facts live under `.ai-workspace/`, `environment/`, and `project/`. When they conflict with this adapter, current verified facts and the stricter safety policy prevail.

## Default rules

- Read `AI_WORKSPACE.md`, `.ai-workspace/workspace.toml`, and the current task manifest first.
- When the current state is `CREATED`, do not claim that the environment or project has been initialized.
- Capability does not imply authorization.
- Default to read-only and fail closed; do not act on unregistered targets or stale facts.
- Do not output credential values, copy them into reports, or write them into memory.
- Do not install tools, modify the shell, access remote systems, overwrite non-empty directories, or commit code automatically by default.
- Generate project rules through `adapt-project-workspace` from questions, facts, and code inspection.
- Generate diagnostic rules interactively through `configure-project-diagnostics`; when unconfigured, analyze only local code and existing files.
- Treat localized content as a reading aid. Canonical English policies, schemas, manifests, commands, and stable identifiers remain authoritative.

## Generated content

The Workcell workspace recompiles the section below from structured policy. Do not treat manual edits as the sole source of a rule.

<!-- ai-workspace:generated:start -->
### Current diagnostic boundary

- Diagnostic status: unconfigured.
- Remote shell: prohibited.
- Remote write: prohibited.
- Unregistered endpoints and nodes: access prohibited.
- Currently permitted: read local code, configuration, and existing local logs.
<!-- ai-workspace:generated:end -->
