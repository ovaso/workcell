---
name: localize-workcell
description: Generate and refresh reviewed target-language documentation and AI adapter text for an expanded Workcell while preserving canonical English sources, machine-readable identifiers, commands, schemas, policy semantics, ownership, and lifecycle state. Use when an operator asks to translate or localize workspace guidance, project documentation, task-facing instructions, or generated AI rules after Bootstrap creation; do not use it to translate code identifiers, manifests, schemas, credentials, evidence, or authoritative policy in place.
---

# Localize Workcell

Create a non-authoritative language layer for people and AI platforms without forking the English control plane.

## Establish scope

1. Locate the workspace root and read `AI_WORKSPACE.md`, `.ai-workspace/workspace.toml`, `.ai-workspace/versions.lock`, and `.ai-workspace/ownership.toml`.
2. Require an explicit target language and a normalized locale identifier such as `fr`, `ja`, or `pt-BR`.
3. Ask which surfaces to localize: workspace introduction, standard documentation, project documentation, task guidance, or generated AI adapter text.
4. Default the output root to `locales/<locale>/`. Never overwrite canonical English files.
5. Treat source access and output writes as the only authorization granted. Network translation services, uploads, external glossaries, and third-party APIs require separate explicit authorization.

## Preserve the contract

- Keep file and directory names, stable IDs, schema keys, enum values, commands, code, paths, URLs, hashes, version strings, and frontmatter `name` fields unchanged.
- Preserve the normative force of `MUST`, `MUST NOT`, `SHOULD`, `MAY`, prohibitions, authorization conditions, and fail-closed rules.
- Preserve code fences, tables, links, anchors when practical, and source references.
- Do not translate raw evidence, logs, credentials, environment-variable values, or unreviewed project data.
- Do not infer facts or permissions while translating.
- When a term is ambiguous, keep the English term and record it for review rather than selecting a risky interpretation.

## Preview and write

1. Inventory the selected English sources and record their versions or SHA-256 values in `locales/<locale>/localization.toml`.
2. Produce a translation preview with changed files, untranslated terms, policy-sensitive passages, and excluded content.
3. Obtain approval before writing the localized files.
4. Write new files under `locales/<locale>/` using the source-relative layout. Refuse to overwrite an existing reviewed translation unless the user approves a refresh.
5. Mark every localized document as subordinate to its canonical English source and include the source-relative path and source version or digest.
6. Validate UTF-8, links, fenced blocks, stable tokens, and one-to-one coverage of selected headings and safety rules.
7. Record locale, source release, generation time, review status, source digests, and unresolved terminology in `localization.toml`.

## Generated AI adapters

Generate localized AI adapter text only when the platform and user request it. Keep hard constraints equivalent to the canonical English policy and store the localized adapter under the locale tree or a declared `generated` path. If equivalence cannot be established, keep the English constraint alongside the translation and fail the localization review.

Localization does not advance the workspace lifecycle and does not make the localized adapter a source of truth.

## Complete

Report the locale, localized surfaces, output paths, source versions, excluded sensitive content, unresolved terms, validation results, and review status. Explicitly state that canonical English remains authoritative.
