---
name: initialize-standard-workspace
description: Initialize a newly bootstrapped Standard Workspace by validating its local structure, orchestrating read-only host inspection, reviewing facts separately from inferences and policies, persisting an approved environment snapshot, and advancing the workspace from CREATED to ENVIRONMENT_INITIALIZED. Use after expanding a standard workspace, when initialization was interrupted, or when the initial host snapshot must be rebuilt safely; use inspect-host-environment instead for routine fact refreshes after initialization.
---

# Initialize Standard Workspace

Establish the first verified host snapshot without installing software, changing the shell, contacting undeclared targets, or silently advancing lifecycle state.

## Enforce the safety boundary

- Treat discovery as read-only by default.
- Do not install tools, edit shell startup files, change environment variables, fetch repositories, or probe the network implicitly.
- Ask for explicit authorization before each local persistence step and before any allowlisted network probe.
- Never persist secret values. Preserve only permitted variable names, presence, classification, and safe references.
- Keep capability separate from authorization: finding a command never grants permission to use it for external or mutating work.
- Fail closed. If structure, state, snapshot validation, or persistence fails, leave the lifecycle unchanged.

## Follow the initialization workflow

### 1. Locate and validate the workspace

1. Resolve the intended workspace root from the user, current directory, or nearest `.ai-workspace/workspace.toml`.
2. Confirm that the root is the intended target before doing any work.
3. Read `AI_WORKSPACE.md`, `.ai-workspace/workspace.toml`, and `.ai-workspace/versions.lock` when present.
4. Verify that required standard directories exist and that the current lifecycle is `CREATED`, `DEGRADED`, or an explicitly approved repair state.
5. Stop instead of creating an assumed structure when required manifests are absent or contradictory. Report the exact missing or conflicting paths.

Read [references/initialization-contract.md](references/initialization-contract.md) before persisting snapshots or changing lifecycle state.

### 2. Confirm inspection scope

Ask only for information that cannot be established safely from the host:

- execution contexts that matter, such as non-interactive shell, AI execution, workspace, or project;
- additional command or toolchain candidates beyond the conservative default set;
- environment variable names whose sensitivity needs an explicit override;
- explicit network targets, probe method, and TTL, if network facts are required now.

Treat unanswered optional questions conservatively. Omit network probing and classify unknown variable names as secret.

### 3. Produce a read-only host preview

Invoke `$inspect-host-environment` for each required execution context. Require it to return a preview before any file write.

Present four separate sections:

1. **Facts** — direct declarations or observations with source, context, time, confidence, and sensitivity.
2. **Inferences** — derived conclusions that cite fact IDs and expose uncertainty.
3. **Policies** — user-confirmed or workspace-declared rules and authorizations.
4. **Recommendations** — non-binding improvements such as missing tool suggestions.

Do not promote historical documentation, inferred project needs, or tool availability into current facts or policy.

### 4. Resolve ambiguity

- Ask the user to resolve conflicting declared and discovered versions when the choice affects capability.
- Keep multiple contextual facts when login and non-interactive shells resolve different commands.
- Mark unverified requirements or manager ownership as unresolved instead of guessing.
- Show network targets and exact probe methods before requesting authorization.

### 5. Persist as one transaction

After the user approves the preview:

1. Write a new immutable file under `environment/snapshots/`.
2. Validate that the serialized snapshot parses and contains required fact metadata.
3. Atomically update the generated current pointer or current summary under `environment/current/`.
4. Derive capabilities and recommendations from the approved snapshot; do not mix them into raw facts.
5. Update `.ai-workspace/workspace.toml` from `CREATED` to `ENVIRONMENT_INITIALIZED` only after every artifact validates.
6. Record the snapshot ID, schema version, observation time, and initialization result.

Never overwrite a prior snapshot to simulate history. On failure, remove only incomplete temporary artifacts and retain the previous valid state.

## Finish with a concise handoff

Report:

- lifecycle before and after;
- snapshot path and observation contexts;
- commands and toolchains discovered or missing;
- counts of public, private, secret, and unknown-classified variable names without values;
- network targets probed or deliberately skipped;
- unresolved facts, degraded capabilities, and the next recommended skill.

Recommend `$adapt-project-workspace` only when initialization completed successfully. Do not mark the workspace `READY`; project adaptation and Doctor gates remain outstanding.
