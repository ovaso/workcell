# AGENTS

> The Standard Workspace compiles this file from structured policy. Safety policy and current verified facts take precedence over historical documentation.

## Default rules

- Read `AI_WORKSPACE.md`, `.ai-workspace/workspace.toml`, and the current task manifest first.
- Capability does not imply authorization.
- Default to read-only and fail closed; do not act on unregistered targets or stale facts.
- Do not output credential values, copy them into reports, or write them into memory.
- Do not install tools, modify the shell, access remote systems, overwrite non-empty directories, or commit code automatically by default.
- Treat localized content as a reading aid; canonical English control-plane content remains authoritative.

<!-- ai-workspace:generated:start -->
### Current diagnostic boundary

- Diagnostic status: unconfigured.
- Remote shell: prohibited.
- Remote write: prohibited.
- Currently permitted: read local code, configuration, and existing local logs.
<!-- ai-workspace:generated:end -->
