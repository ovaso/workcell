# Initialization Contract V0.1

## Preconditions

- Operate on a user-confirmed Standard Workspace root.
- Require readable workspace identity and version manifests.
- Accept `CREATED` for first initialization. Accept another state only for an explicit repair or migration flow.
- Keep all discovery local and read-only until the user separately authorizes network probes or persistence.

## Required separation

| Layer | Meaning | Allowed sources |
|---|---|---|
| Facts | Direct declaration or observation | user declaration, read-only command, local file, explicitly authorized probe |
| Inferences | A conclusion derived from facts | one or more fact IDs with confidence and uncertainty |
| Policies | A rule or authorization | confirmed user decision or structured workspace policy |
| Recommendations | Optional improvement | facts plus adapter or project requirements |

Never store an inference as a discovered fact. Never turn a recommendation into authorization.

## Snapshot artifacts

Use these logical artifacts even if a later schema revision changes the serialization format:

```text
environment/snapshots/<snapshot-id>.json   immutable approved facts
environment/current/host-facts.json        generated pointer or current projection
environment/current/capabilities.json      generated capability projection
.ai-workspace/workspace.toml                lifecycle and active snapshot reference
```

Classify `environment/snapshots/*` as workspace-owned evidence. Classify current projections as generated. Preserve both during distribution upgrades.

## Transaction order

1. Render the candidate snapshot to a temporary path in the destination directory.
2. Parse and validate the candidate.
3. Move it atomically to its immutable snapshot path.
4. Render and validate current projections.
5. Atomically replace current projections.
6. Update the workspace manifest with the active snapshot ID.
7. Advance lifecycle to `ENVIRONMENT_INITIALIZED`.

If steps 1–5 fail, leave the manifest and lifecycle unchanged. If manifest replacement fails, retain the new immutable snapshot as unreferenced evidence and report it; do not claim initialization completed.

## Lifecycle gate

Allow `CREATED -> ENVIRONMENT_INITIALIZED` only when:

- required workspace structure is valid;
- at least one execution context was inspected;
- every persisted fact has source, context, observation time, confidence, and sensitivity;
- environment variable values are absent;
- every network observation refers to an explicitly authorized target;
- active snapshot and capability projections parse successfully.

Do not advance directly to `PROJECT_ATTACHED`, `PROJECT_ADAPTED`, or `READY`.

## Reinitialization

For an already initialized workspace, prefer `$inspect-host-environment` to create a refreshed snapshot. Use this Skill again only when repairing an interrupted initialization or rebuilding the initial baseline with explicit approval. Preserve and supersede prior facts; do not rewrite them.
