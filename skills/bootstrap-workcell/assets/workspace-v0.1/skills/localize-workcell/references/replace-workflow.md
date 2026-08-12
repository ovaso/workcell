# Localization replace workflow

`overlay` is the default because it keeps English documents byte-identical to their installed Release receipt. Use `replace` only after deciding that the selected locale is the workspace's working language.

## Scope and exclusions

The offline tool accepts only these explicit scopes:

- `entry-documents`: `AI_WORKSPACE.md` and `README.md` when present;
- `standard-documents`: `docs/**/*.md`;
- `skill-instructions`: every `skills/*/SKILL.md`;
- `skill-references`: every `skills/*/references/**/*.md`;
- `ai-adapters`: `skills/*/agents/*.yaml` and `.yml`, with display fields and prompts only;
- `all-readable-documents`: the first four scopes, not adapters or configuration.

It never expands “all” to JSON, TOML, arbitrary YAML, schemas, manifests, scripts, `.env`, ignore files, code, credentials, logs, evidence, or project data. A separate capability and separate confirmation are required before any configuration or data localization.

## Preview, approval, and application

Supply reviewed local translation files in a source-relative directory, then preview before writing:

```bash
python3 -B skills/localize-workcell/scripts/localize.py preview \
  --workspace /absolute/workspace --locale zh-CN --mode replace \
  --scope entry-documents --scope skill-instructions \
  --translations /absolute/reviewed-zh-CN --json
```

The preview reports selected files, exclusions, a unified diff per translated file, protected-token failures, and source passages containing safety or authorization language. It is read-only and performs no network translation.

After reviewing that output, an operator must record approval and confirm the destructive workflow explicitly:

```bash
python3 -B skills/localize-workcell/scripts/localize.py apply \
  --workspace /absolute/workspace --locale zh-CN --mode replace \
  --scope entry-documents --translations /absolute/reviewed-zh-CN \
  --apply --confirm-replace --approval "operator ticket LOC-42"
```

The tool rejects a change that drops frontmatter `name`, code fences, commands, paths, URLs, IDs, state values, enum-like stable tokens, versions, or hashes. It also rejects adapter YAML changes outside the three allowed display/prompt scalar fields.

Before `replace` writes, it creates `.ai-workspace/localization-snapshots/<snapshot-id>/`. Restore a complete snapshot or selected files only with explicit rollback confirmation:

```bash
python3 -B skills/localize-workcell/scripts/localize.py rollback \
  --workspace /absolute/workspace --snapshot 20260812T000000Z-zh-CN \
  --path skills/example/SKILL.md --apply --confirm-rollback \
  --approval "operator ticket LOC-42 rollback"
```

## Integrity and Doctor results

Do not edit `.ai-workspace/release-manifest.json` after a replacement. Its original digest remains the source baseline. `replace` stores the approved source and translation digests in `.ai-workspace/localization-overrides.toml`, which is workspace-owned metadata, rather than weakening the distribution ownership model.

Doctor accepts a distribution digest difference only when the registry record is well-formed, points to an eligible document, has the current source Release and receipt digest, and its translation digest equals the file's current bytes. It emits `release.distribution-file-localization-override` at `WARN` by default, or `INFO` when `.ai-workspace/policies/core.toml` sets:

```toml
[localization]
registered_replace_severity = "INFO"
```

An unregistered change, stale source digest, changed translation after registration, malformed registry, or registry path outside the installed distribution remains an `ERROR`.
