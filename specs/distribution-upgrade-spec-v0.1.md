# Distribution and Upgrade Specification V0.1

## 1. Product form

```text
single canonical Git source repository
-> stable tag
-> validation and packaging
-> Bootstrap Skill ZIP
-> installation and expansion
-> independent standard workspace instance
```

## 2. Versions

Maintain at least the product version, workspace schema, Release Manifest schema, environment-fact schema, project-plugin API, diagnostic-capability API, and task schema independently.

## 3. Release requirements

- Build a Release from a stable tag.
- Keep the distribution immutable.
- Deterministically generate `.ai-workspace/release-manifest.json` inside the workspace. Cover every regular asset file except the manifest itself and record first-match ownership and SHA-256.
- Generate an outer Bootstrap SHA-256 manifest that covers the complete asset, including the workspace Release Manifest. The workspace Release Manifest must not hash itself.
- Do not use the latest `main` commit as an automatic upgrade target.
- Verify the repository license and complete third-party notices before every public release.

## 4. Workspace upgrade

```text
verify the current installation receipt and candidate outer checksum
-> read versions
-> select a Migration
-> generate the upgrade plan and file impact
-> obtain user confirmation
-> create a recoverable snapshot
-> apply the Migration
-> recompile generated files
-> run the Doctor
-> update version locks and the release pointer
-> atomically replace the installation receipt last, or roll back
```

The upgrade preview must use the current workspace `.ai-workspace/release-manifest.json` directly as `--current-manifest`. The candidate manifest must satisfy the same schema and gain trust from the candidate Release's outer checksum or signature. The manifest itself does not appear in `files`; previews and transaction logs represent it as a separate, final `replace-receipt` action. After a successful replacement, no generation, formatting, or other workspace write may occur. A failed replacement is an upgrade failure and triggers rollback.

## 5. Self-update

Enable self-update only after the canonical repository, production standard, and formal Release process are stable. Automatic checks may be enabled by default, automatic downloads may be configured, and automatic application must remain disabled by default.

Do not overwrite a currently executing Skill in place. Install a new version in a temporary or sibling directory, validate it, then switch while preserving rollback capability.

## 6. File ownership

- `distribution` may be replaced by a Migration.
- `generated` is recompiled.
- `workspace` is preserved completely.
