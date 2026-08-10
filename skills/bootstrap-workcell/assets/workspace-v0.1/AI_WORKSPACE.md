# AI Workspace Entry

## Startup order

Whenever entering this workspace:

1. Read `.ai-workspace/workspace.toml` and `.ai-workspace/versions.lock`.
2. Read the current policies under `.ai-workspace/policies/`.
3. Load only the environment, project, diagnostic, and task facts relevant to the current task; do not read all historical content by default.
4. Read the applicable project plugin and current task manifest.
5. Validate authorization before writing, accessing external systems, or performing diagnostic actions.

## Truth and precedence

Resolve conflicts in this order:

```text
hard safety prohibitions
> explicit user authorization for the current task
> current runtime or endpoint verification
> current project configuration
> project-plugin declarations
> code-derived conclusions
> historical plans, documentation, and memory
```

Do not use historical records as substitutes for current facts. Do not select an interpretation with broader permissions or higher risk. When facts conflict, expire, or are missing, stop the affected action and request confirmation or collect new evidence.

## State machine

The Workcell workspace follows this primary path:

```text
CREATED
-> ENVIRONMENT_INITIALIZED
-> PROJECT_ATTACHED
-> PROJECT_ADAPTED
-> DIAGNOSTICS_CONFIGURED (optional)
-> READY
```

Only `workcell-doctor` may gate entry into `READY`. Mark the workspace `DEGRADED` when critical facts drift; do not continue silently.

## Capability and authorization

An action is executable only when all conditions hold:

```text
the host environment has the capability
AND the Provider supports the action
AND project policy permits it
AND the current task authorizes it
```

The presence of commands, credentials, or network access is only a capability fact and does not grant authorization. Remote shells, remote writes, tool installation, shell modification, non-empty-directory overwrites, and credential output are denied by default.

## Directory responsibilities

- `.ai-workspace/`: standards, schemas, policies, versions, and lifecycle control plane.
- `environment/`: current host environment facts and historical snapshots.
- `project/`: project plugin, project instance, and project capability configuration.
- `requirements/`: task records for requirements, defects, diagnostics, and reviews.
- `mirror/`: project mainline or read-only reference mirrors.
- `workspaces/`: isolated task execution directories.
- `remotes/`: remote registry; never stores credential values directly.
- `diagnostics/`: cross-task diagnostic Providers and knowledge.
- `knowledge/`: verified reusable knowledge.
- `memory/`: workspace evolution memory; not a dynamic fact source.
- `feedback/`: redacted workspace-practice candidates; not adopted standards.
- `locales/`: reviewed localized content that remains subordinate to canonical English.
- `skills/`: runtime Skills carried by the expanded workspace.

## Runtime Skills

- `initialize-workcell`: initialize identity and foundational facts.
- `inspect-host-environment`: safely collect or refresh host environment facts.
- `adapt-project-workspace`: ask, inspect, and generate the project plugin.
- `configure-project-diagnostics`: interactively configure diagnostic capabilities and hard constraints.
- `workcell-doctor`: inspect structure, facts, state, and drift.
- `start-workcell-task`: create machine-readable tasks and isolation boundaries.
- `upgrade-workcell`: preview, snapshot, and apply controlled upgrades.
- `extract-workcell-feedback`: generate redacted feedback candidates from authorized practice.
- `localize-workcell`: generate reviewed target-language documentation and adapters without changing canonical English sources.

If the platform does not discover Skills automatically, read the applicable `SKILL.md` explicitly before executing it.
