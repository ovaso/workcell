# Doctor Check Catalog

## Severity

- `ERROR`: invalid structure or source of truth, permissive safety policy, authority escalation, ownership conflict, or a condition missing for the current lifecycle. Blocks `READY`.
- `WARN`: the workspace remains usable read-only, but evidence, optional metadata, expiration protection, or maintenance is incomplete.
- `INFO`: confirmed healthy facts.

## Deterministic structural checks

- Required non-empty entry points exist: `AI_WORKSPACE.md`, `AGENTS.md`, `.ai-workspace/workspace.toml`, `.ai-workspace/versions.lock`, and `skills/`.
- Standard directories exist: `environment`, `project`, `mirror`, `remotes`, `requirements`, `workspaces`, `diagnostics`, `tools`, `knowledge`, `docs`, `memory`, `feedback`, and `locales`.
- TOML and JSON sources of truth parse successfully; paths are safe workspace-relative paths.
- Workspace state belongs to the standard state set; writing `READY` directly must not hide missing gates.
- Runtime Skill directory names, frontmatter names, and descriptions are valid and contain no template TODOs.
- Platform adapter metadata such as `agents/openai.yaml` is not a generic workspace runtime-health condition. The applicable platform or product-repository tests validate distribution integrity; the Doctor does not warn solely because a platform adapter is absent.
- Rules in `.ai-workspace/ownership.toml` are unique and path-safe, and owners belong to `distribution/generated/workspace`. Paths in `.ai-workspace/distribution.manifest` exist, remain inside the workspace, and each have an exact `distribution` rule rather than depending only on a broad `/**` rule.

## JSON Schema consistency checks

- Use the bundled `.ai-workspace/schemas/environment-facts.schema.json` and `.ai-workspace/schemas/project-plugin.schema.json` directly. Do not depend on a separately installed schema library or an external repository copy.
- The environment-fact schema accepts both `.ai-workspace/templates/host-facts.json` and `environment/current/host-facts.json`.
- The project-plugin schema accepts `.ai-workspace/templates/project-plugin.json` and, when present, `project/plugin/project-plugin.json`.
- The V0.1 validation subset covers `$ref`, `allOf`, `not`, `const`, `enum`, `type`, `required`, `properties`, `additionalProperties`, `items`, `minItems`, `uniqueItems`, `minLength`, `maxLength`, `pattern`, `format: date-time`, `propertyNames`, and `minimum`.
- `$ref` may point only to a JSON Pointer in the current schema document. Report `ERROR` for missing schemas, invalid JSON, duplicate object keys, unresolved references, invalid constraint parameters, and unsupported keywords, so an older Doctor cannot silently ignore new constraints after an upgrade.
- Report `schema.instance-invalid` when any template or instance field violates its bundled schema. Preserve instance and schema JSON Pointers in errors to distinguish schema drift, template drift, and runtime-fact drift.
- Schema validation is read-only, offline, cache-free, and performs no automatic repair or JSON rewrite.

## Installed Release receipt checks

- `.ai-workspace/release-manifest.json` is a required self-hosting receipt and must satisfy `.ai-workspace/schemas/release-manifest.schema.json`.
- Receipt `release_version` exactly matches `.ai-workspace/versions.lock` `versions.product`.
- For every regular file with `files[].owner = "distribution"`, reject missing paths, any symlink component, directories or other non-regular files, and mismatched streaming SHA-256. The receipt does not hash itself.
- `generated` and `workspace` entries record the installation baseline only. They may be created, modified, or removed at runtime; hash changes are not distribution drift.
- If a file object or metadata changes during hashing, fail closed with a race error. The Doctor does not restore release files automatically.

## Task checks

- `requirements/<task-id>/task.toml` parses, its task ID matches the directory, and status belongs to `INBOX`, `SCOPED`, `PLANNED`, `READY`, `IMPLEMENTING`, `VERIFYING`, `DEV_FEEDBACK`, `TEST_FEEDBACK`, `QC_READY`, `RELEASE_READY`, `DONE`, `PAUSED`, or `ARCHIVED`.
- Module roles use only `scope.edit/verify/reference/excluded`; a module cannot appear more than once.
- `task.project_plugin_ref` points exactly to `project/plugin/project-plugin.json`; no path component is a symlink, and the JSON parses strictly and satisfies the project-plugin schema.
- A task role cannot exceed project-plugin `modules[].role`: `reference < verify < edit`.
- Task scope, authorization, risks, gates, and evidence paths are machine-readable. Missing data is a warning or an error depending on current state.
- A task after `READY` has confirmed scope and a plan. `DONE` has verification evidence. `ARCHIVED` preserves a final summary and traceable commit information.

## Diagnostic checks

- In `unconfigured`, only local code and existing-file analysis are allowed; remote actions are disabled.
- A `verified` profile was configured interactively and uses `default_action = "deny"`; credentials are references only.
- Target, Provider, authorization, and fact-expiration conditions are complete; referenced files exist and paths are safe.
- Hard diagnostic constraints reached the effective AI adapter rules.
- Provider availability, endpoint connectivity, and current authorization are three different facts and cannot substitute for each other.

## Localization checks

- Canonical control-plane content remains English and is not overwritten by locale output.
- Locale directories use normalized identifiers and contain only workspace-owned or declared generated content.
- Localized adapters preserve stable tokens and hard safety semantics, reference their canonical English source, and fail review when equivalence cannot be established.
- Localization does not change lifecycle state, schemas, manifests, policies, commands, or stable IDs.

## Read-only manual checks

The script cannot independently prove these matters; inspect them when applicable:

- whether generated adapters such as `AGENTS.md` share structured policy provenance and are current;
- whether project modules, default branches, build, tests, and high-risk paths still match the code;
- whether Git worktree state, ahead/behind, remote URLs, and the current branch comply with project policy;
- whether environment facts remain valid in the applicable context and lifetime;
- whether an upgrade candidate comes from an immutable Release and its hash or signature is valid;
- whether task evidence corresponds to the current commit and environment;
- whether localized safety language remains equivalent to canonical English.

Explain and obtain authorization before any check that accesses the network, refreshes remote references, runs a service, or queries an external platform.

## Repair priority

1. Repair unsafe defaults, parse failures, path escape, and role escalation.
2. Repair lifecycle gates, ownership, and generated-file drift.
3. Add missing facts, task evidence, and UI metadata.
4. Address formatting, informational warnings, and optional maintenance last.

Run all checks after every repair so a local pass does not hide another error.
