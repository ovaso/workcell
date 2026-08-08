# Contributing

Thank you for helping improve AI Native Standard Workspace. Contributions are welcome through GitHub issues and pull requests.

## Before contributing

- Read `README.md`, `AGENTS.md`, and `docs/architecture.md`.
- Search existing issues and pull requests before opening a new one.
- Use the security policy for vulnerabilities and sensitive reports; do not disclose them in a public issue.
- Keep all canonical repository content in English. Localized reading aids belong under an expanded workspace's `locales/<locale>/` directory, not in this source repository.
- By submitting a contribution, you confirm that you have the right to license it under the repository's MIT License.

## Choose the right change surface

The root `docs/`, `specs/`, `schemas/`, and `facts/` directories are canonical sources. Several copies inside `skills/bootstrap-standard-workspace/` are generated. Do not edit generated copies directly; see `docs/repository-maintenance.md` for the complete list.

Ownership rules apply inside the workspace template:

- `distribution`: maintained by this repository and replaceable through a reviewed migration;
- `generated`: compiled from structured facts and policies;
- `workspace`: maintained by users and preserved across upgrades.

New templates, manifests, and specifications must state their ownership.

## Development workflow

1. Fork the repository and create a focused branch.
2. Make the smallest coherent change.
3. Add or update tests when changing scripts, schemas, templates, or validation behavior.
4. Rebuild generated assets.
5. Run the full test suite.
6. Open a pull request using the repository template.

POSIX:

```sh
scripts/build-bootstrap-assets.sh
tests/run.sh
```

PowerShell:

```powershell
& ./scripts/build-bootstrap-assets.ps1
& ./tests/run.ps1
```

Every operator-facing `.sh` file must have a same-basename `.ps1` counterpart. Python and Node.js scripts remain single cross-platform implementations.

## Change requirements

- Script changes require corresponding tests.
- Schema changes require JSON parsing, example validation, and TOML mapping checks where applicable.
- Template changes require Bootstrap black-box tests and Workspace Doctor validation.
- Skill changes must pass the repository validator and Skill Creator's `quick_validate.py` before release.
- Generated assets, the installed Release manifest, and SHA-256 checksums must be synchronized.
- Network access, tool installation, external writes, and release publication must remain explicit and separately authorized.

## Pull request expectations

Describe the problem, the chosen approach, compatibility impact, security impact, and validation evidence. Keep unrelated changes out of the pull request. Maintainers may request a Change Set for modifications to stable specifications, schemas, ownership, lifecycle rules, or upgrade behavior.

Be respectful and follow `CODE_OF_CONDUCT.md` in every project space.
