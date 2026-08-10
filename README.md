# Workcell

[![CI](https://github.com/ovaso/workcell/actions/workflows/ci.yml/badge.svg)](https://github.com/ovaso/workcell/actions/workflows/ci.yml)
[![CodeQL](https://github.com/ovaso/workcell/actions/workflows/codeql.yml/badge.svg)](https://github.com/ovaso/workcell/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

This repository contains the V0.1 release source for the Workcell product. It is not a business project and is not bound to any specific project or AI platform.

The primary deliverable is a text-only, versioned, self-contained Bootstrap Skill. An AI uses the Skill to expand the Workcell template into an empty directory. The expanded workspace carries its own Skills, specifications, schemas, fact management, project adaptation, diagnostic integration, and validation capabilities.

## Current capabilities

- Define a Workcell workspace structure and lifecycle that are as independent as possible from AI platforms.
- Define fact models for the host environment, project plugins, diagnostic capabilities, and tasks.
- Provide Skills for bootstrapping, initialization, environment inspection, project adaptation, diagnostic configuration, Doctor checks, task creation, and upgrades.
- Provide a reproducible V0.1 workspace template.
- Provide Bootstrap safety validation, an installed Release receipt, structural Doctor checks, and upgrade-impact previews.
- Provide versioned seed knowledge about tool capabilities for environment fact collection and non-binding optimization recommendations.
- Provide a controlled feedback loop from workspace practice to Workcell proposals and version evolution.
- Provide equivalent offline Bootstrap, validation, repair-planning, build, test, and packaging entry points for POSIX shell and PowerShell hosts.

## Product layers

```text
Bootstrap Skill
  -> expand the Workcell workspace
  -> initialize host environment facts
  -> attach and adapt a project
  -> configure project capability plugins
  -> compile AI rules
  -> enter READY after the Doctor passes
```

Runtime capabilities are composed from:

```text
generic workflow kernel
+ current machine capabilities
+ generic technology adapters
+ project plugin
+ project instance facts
+ project capability plugins
+ current task state
```

## Repository layout

- `skills/`: the Bootstrap Skill and, under `assets/workspace-v0.1/skills/`, the runtime Skills carried by an expanded workspace.
- `specs/`: workspace, serialization, task, fact, project-plugin, diagnostic, AGENTS-generation, and upgrade protocols.
- `schemas/`: machine-readable base JSON Schemas.
- `facts/`: product decisions, reusable seed knowledge, and observations retained only for source traceability.
- `docs/`: product vision, architecture, lifecycle, maintenance guidance, roadmap, and the complete design-session summary.
- `scripts/`: product build and validation scripts.
- `tests/`: Bootstrap, schema, runtime, and repository-structure tests.
- `CHANGELOG.md`: release-level product changes; it does not replace task memory or design facts.

## Current stage

V0.1 focuses on fixing the design into a reviewable, verifiable text product skeleton. The standards and assets are not bound to a specific AI platform. Deterministic Bootstrap entry points are provided for POSIX `sh` and Windows PowerShell 5.1 or PowerShell 7. Self-update, cross-version migrations, and a complete AI-instruction compiler remain protocol definitions rather than production implementations in this release.

Bootstrap creation and validation do not require Python or Node.js on either host profile. Deterministic scripts carried by the expanded workspace use Python 3 as one cross-platform implementation; on Windows they can be invoked through `py -3`, `python`, or another Python 3 command verified by environment inspection.

## Intended use

1. Use `skills/bootstrap-workcell` to expand the template into an empty directory.
2. In the new workspace, use `initialize-workcell` to establish host environment facts.
3. Use `adapt-project-workspace` to attach code mirrors, remotes, and the project plugin.
4. Use `configure-project-diagnostics` when diagnostic capabilities are needed.
5. Run `workcell-doctor`; after all gates pass, mark the workspace `READY`.
6. At task completion or during periodic retrospectives, use `extract-workcell-feedback` to generate redacted candidates; review them in the Workcell repository before incorporating them into a later version.
7. Use `localize-workcell` to generate reviewed, non-authoritative language adaptations without changing the canonical English control plane.

## Repository and distribution

`workcell` is the independent canonical Git repository for specifications, schemas, documentation, and build logic. The formal distribution is the `bootstrap-workcell` Skill ZIP built from this repository; they are not two parallel products.

```text
workcell Git repository
  -> build + validate
  -> bootstrap-workcell Skill
  -> expand into an empty directory
  -> self-hosted Workcell workspace
```

The root-level `docs/session-summary.md` preserves design history and is not included in the Bootstrap Skill ZIP. The distribution carries only generic specifications, product documentation, and reusable seed knowledge.

On POSIX hosts, run `scripts/build-bootstrap-assets.sh` and `tests/run.sh`. From PowerShell, run `& ./scripts/build-bootstrap-assets.ps1` and `& ./tests/run.ps1`. Both paths synchronize the same sources and enforce the same release contracts.

The project is available under the [MIT License](LICENSE). See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md), [GOVERNANCE.md](GOVERNANCE.md), and the [GitHub repository settings checklist](docs/github-repository-settings.md) before contributing or publishing a release.
