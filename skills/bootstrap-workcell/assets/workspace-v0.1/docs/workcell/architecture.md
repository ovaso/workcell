# Architecture

## Source repository and nested Skills

`workcell` is an independent Git source repository, not an expanded Workcell workspace. Repository-level documentation, licenses, specifications, schemas, build logic, and tests are siblings of `skills/`. The Workcell protocols target multiple AI platforms, while V0.1 deterministic bootstrap scripts provide equivalent POSIX `sh` and PowerShell entry points:

```text
workcell/
├── README.md
├── LICENSE
├── LICENSES/
├── docs/
├── specs/
├── schemas/
├── scripts/
├── tests/
└── skills/
    └── bootstrap-workcell/
        ├── SKILL.md
        └── assets/workspace-v0.1/
            └── skills/   # runtime Skills carried by the expanded workspace
```

The outer Bootstrap Skill is the distribution and self-bootstrap entry point. The inner Skills belong to the expanded workspace. Their responsibilities and lifecycles are distinct.

## Overall structure

```text
Bootstrap distribution layer
  -> Workcell workflow kernel
  -> host environment fact layer
  -> generic technology adapters
  -> project plugin
  -> project instance
  -> project capability plugins
  -> task instance
```

## Bootstrap distribution layer

Responsible for `create / validate / repair / upgrade`, with secure self-update added only after releases are stable. Bootstrap is installation media and does not perform daily project development.

## Workcell workflow kernel

Defines workspace and task lifecycles, the evidence model, file ownership, AI context assembly, security constraints, and multi-agent collaboration boundaries. The kernel must not contain project names, server addresses, or business rules.

## Host environment fact layer

The first release manages only installed commands, toolchains, environment variables, and network facts. Every fact records its source, context, observation time, confidence, sensitivity, and expiration information.

## Generic technology adapters

Provide cross-project capabilities for Git, Maven, Spring Boot, Node, SQL, Docker, Kubernetes, and similar technologies. Project plugins compose and override these adapters rather than duplicating them.

## Project plugin and project instance

The project plugin stores stable project differences: repositories, modules, branches, build, tests, risks, and specialized capabilities. The project instance stores local bindings and live state: paths, remotes, environment-variable references, mirrors, workspaces, and dirty/ahead/behind status.

## Project capability plugins

Diagnostics are the first formally defined capability plugin. Future plugins may cover review, release, migration, performance, and security. A project plugin enables and configures capability plugins through a uniform API.

## Task instance

Requirements, defects, diagnostics, and reviews are all tasks. A task records status, plan, module roles, risks, next action, gates, environment snapshot, and evidence.

## File ownership

```text
distribution: maintained by the release
generated: compiled from structured facts
workspace: maintained by users, projects, and tasks
```

An upgrade may replace only `distribution`, recompile `generated`, and must preserve `workspace` completely.

## Localization layer

English is the canonical language for product and control-plane content. `localize-workcell` may generate reviewed target-language documentation and adapter text under workspace-owned or generated localization paths. It must preserve stable IDs, schemas, commands, paths, policy semantics, and the English source, and it must never turn a translation into an independent source of truth.

## Practice feedback and Workcell evolution

The workspace uses `extract-workcell-feedback` to derive redacted candidates from explicitly authorized material and writes them under `feedback/`. This neither changes Workcell nor uploads data automatically. The Workcell repository's `integrate-workcell-feedback` handles only candidates explicitly imported by the user and creates reviewable proposals. Specifications, schemas, Skills, assets, and versions may change only after independent evidence has been aggregated, compatibility and ownership have been assessed, and the user has confirmed the change.
