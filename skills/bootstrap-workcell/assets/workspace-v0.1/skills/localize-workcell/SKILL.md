---
name: localize-workcell
description: Generate reviewed workspace localization through an explicit overlay or replace workflow while preserving stable tokens, policy semantics, integrity evidence, and rollback capability. Use when an operator asks to translate workspace guidance or display-only AI adapter text after Bootstrap creation; do not translate configuration, schemas, credentials, evidence, or code by default.
---

# Localize Workcell

Choose one explicit, auditable workflow. `overlay` is the default and remains the recommended option. It creates a subordinate reading layer; `replace` is for workspaces where the selected locale is the primary working language and intentionally records a Release-integrity exception.

| Mode | Output | Default |
|---|---|---|
| `overlay` | `locales/<locale>/` translation layer; English sources remain unchanged | Yes |
| `replace` | Replaces selected human-readable source files with reviewed translations | No; explicit confirmation required |

## Establish scope

1. Locate the workspace root and read `AI_WORKSPACE.md`, `.ai-workspace/workspace.toml`, `.ai-workspace/versions.lock`, and `.ai-workspace/ownership.toml`.
2. Require an explicit target language and a normalized locale identifier such as `fr`, `ja`, or `pt-BR`.
3. Ask which surfaces to localize: entry documents, standard documents, all `SKILL.md`, all `skills/*/references/*.md`, or display-only AI adapter text. “All readable documents” never includes configuration or data files.
4. Default to `overlay` and `locales/<locale>/`. Select `replace` only when the operator explicitly asks to make the locale the working language.
5. Treat source access and output writes as the only authorization granted. Network translation services, uploads, external glossaries, and third-party APIs require separate explicit authorization.

## Preserve the contract

- `replace` can process only selected user-readable Markdown, `SKILL.md`, and `references/*.md`. It excludes JSON, TOML, YAML, schemas, manifests, scripts, `.env`, ignore files, code, credentials, logs, and evidence by default.
- Keep file and directory names, stable IDs, schema keys, enum values, commands, code, paths, URLs, hashes, version strings, frontmatter `name` fields, and fenced code blocks unchanged.
- Preserve the normative force of `MUST`, `MUST NOT`, `SHOULD`, `MAY`, prohibitions, authorization conditions, and fail-closed rules.
- Preserve code fences, tables, links, anchors when practical, and source references.
- Do not translate raw evidence, logs, credentials, environment-variable values, or unreviewed project data.
- Do not infer facts or permissions while translating.
- When a term is ambiguous, keep the English term and record it for review rather than selecting a risky interpretation. Do not use a replacement to hide an ambiguity.

## Preview and write

1. Use the bundled offline tool to select scope and generate a preview. It inventories source files, shows a per-file unified diff, flags protected or untranslated tokens, displays policy-sensitive passages, and lists excluded content.
2. Obtain a separate approval after the preview. For `replace`, require an explicit confirmation and an approval record; do not infer either from the request to translate.
3. The tool validates UTF-8, links, fenced blocks, and stable tokens. Before `replace`, it creates a recoverable snapshot, then applies the approved files; it supports batch and per-file rollback from that snapshot.
4. `overlay` records source and translation digests in `locales/<locale>/localization.toml`. It refuses to refresh reviewed output without an explicit refresh authorization.
5. `replace` records every change in the independent workspace metadata file `.ai-workspace/localization-overrides.toml`: locale, mode, source Release, path, source digest, translation digest, time, snapshot, and approval. It must not modify the Release manifest to conceal the byte drift.

See [replace-workflow.md](references/replace-workflow.md) for the command contract and audit rules.

## Generated AI adapters

Generate localized AI adapter text only when the platform and user request it. For YAML adapters, localize only display fields and prompts such as `display_name`, `short_description`, and `default_prompt`; preserve keys, indentation, structure, and machine values exactly. If equivalence cannot be established, keep the English constraint alongside the translation and fail the localization review.

Localization does not advance the workspace lifecycle and does not make the localized adapter a source of truth.

## Complete

Report the locale, selected mode and surfaces, preview result, snapshot, rollback route, source versions, excluded sensitive content, unresolved terms, validation results, and review status. State that `overlay` leaves canonical English authoritative; state any `replace` Release-integrity exception explicitly.
