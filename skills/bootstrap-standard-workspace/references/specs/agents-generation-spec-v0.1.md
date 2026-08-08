# AI Instruction Generation Specification V0.1

## 1. Sources of truth

AI instruction files are not the sole fact source. Workspace policies, project plugins, diagnostic policies, and user overrides are structured sources of truth.

## 2. Standard sections

Generated files distinguish at least:

```text
GENERATED CORE
USER MANAGED
GENERATED PROJECT
GENERATED DIAGNOSTICS
```

Every generated section records source versions and a configuration hash. The Doctor must detect manual modifications to generated sections.

## 3. Platform-neutral entry point

`AI_WORKSPACE.md` holds the platform-neutral workspace entry point, mandatory read order, and lifecycle state. Platform adapters may generate `AGENTS.md`, `CLAUDE.md`, and similar files.

## 4. Compilation precedence

```text
core hard safety constraints
> explicit user restrictions
> project safety rules
> diagnostic hard constraints
> project workflow rules
> platform presentation
```

A platform adapter must not weaken a higher-level constraint.

## 5. Immediate diagnostic updates

After the user confirms a new diagnostic prohibition, update the structured policy first and atomically recompile the diagnostic-generated section. On failure, preserve the older, stricter rules.

## 6. Upgrade

An upgrade recompiles generated sections and preserves user-managed sections. It must not overwrite user edits with a complete template.
