# Bundle contract

## Canonical layout

```text
bootstrap-standard-workspace/
├── SKILL.md
├── agents/openai.yaml
├── bundle.toml
├── checksums/workspace-v0.1.sha256
├── scripts/
├── references/
└── assets/workspace-v0.1/
    ├── AI_WORKSPACE.md
    ├── AGENTS.md
    ├── .ai-workspace/
    │   ├── workspace.toml
    │   ├── versions.lock
    │   ├── release-manifest.json
    │   └── distribution.manifest
    └── skills/
```

The Git repository is the editable source form. A packaged Skill directory is the distributable form. The package must be self-contained and must not depend on paths outside the Skill.

## Runtime requirements

Use a POSIX-compatible `sh` plus standard file utilities (`awk`, `cmp`, `cp`, `diff`, `find`, `grep`, `sed`, and `sort`). Require either `sha256sum` or `shasum` for bundle integrity verification. Do not require Python, a package manager, network access, or a project-specific toolchain. Checking that these direct script dependencies exist is not host-environment initialization.

## Bundle metadata

Keep these identities synchronized:

- `bundle.version`, repository `VERSION`/`product.toml`, and workspace `[versions].product` during release builds;
- bundle `[versions]`, both workspace version files, and the project/diagnostic plugin API versions;
- `payload.workspace_asset` and the actual asset directory;
- `payload.required_entries` and the minimum workspace entry set;
- `bundle.format` and the text-only asset rules;
- the executable scripts documented by `SKILL.md`.

Treat `bundle.toml` as release metadata, not as runtime project state. Keep it valid against `.ai-workspace/schemas/bundle.schema.json`. Do not place machine paths, credentials, endpoints, project-specific rules, or observed host facts in it.

## Asset rules

- Keep assets text-only for V0.1.
- Do not include symlinks, sockets, devices, or generated caches.
- Keep the SHA-256 manifest synchronized with the exact asset file set; reject missing, extra, or mismatched files.
- Generate `.ai-workspace/release-manifest.json` deterministically from every other regular asset file and first-match ownership. Keep it self-excluded and protect it with the external workspace checksum manifest.
- Use relative paths in manifests and references.
- Keep runtime Skills under `assets/workspace-v0.1/skills/`; they belong to the expanded workspace, not to the external Bootstrap execution context.
- Include empty-directory keepers only when the directory is part of the declared workspace structure.
- Keep the asset initial state reproducible: no timestamps, hostnames, random identifiers, or discovered environment values.

## Release checks

Run, in order:

```sh
scripts/validate-bundle.sh
tests/test-bootstrap.sh
```

Then run Skill Creator's `quick_validate.py` against the external Skill and every bundled runtime Skill. Stable releases must additionally be built from an immutable tag with a file manifest and SHA-256 checksums; those release-signing mechanics are outside the V0.1 Bootstrap runtime.
