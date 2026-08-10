# Diagnostic Configuration Contract

## Sources of truth

```text
project/diagnostics/diagnostic-profile.toml
.ai-workspace/schemas/diagnostic-profile.schema.json
.ai-workspace/templates/diagnostic-profile.toml
.ai-workspace/policies/diagnostics.toml
diagnostics/targets/
diagnostics/providers/
diagnostics/knowledge/
```

The profile is the source of truth for project diagnostic configuration and must satisfy Schema V0.1. The policy file stores the workspace's current fail-closed boundary. `AGENTS.md` is a platform adapter compiled from this structured content. Put task-specific evidence under the applicable `requirements/<task-id>/`, not in the long-lived profile.

## Profile status

The aggregate file has top-level `schema_version = "0.1"`. Profile status uses only:

- `unconfigured`: questionnaire not complete; only local code and existing-file analysis is permitted;
- `configuring`: safety boundaries confirmed; questions, inspection, or candidate configuration are in progress;
- `draft`: configuration is in progress or critical facts remain unverified; remote actions cannot be opened;
- `verified`: mandatory questionnaire, code inspection, authorized fact validation, and gates complete;
- `degraded`: a formerly verified capability has partially failed or conflicts; retain only read-only capabilities that remain fully proven and authorized;
- `stale`: dependent facts expired or drifted; affected actions fail closed;
- `disabled`: all Providers explicitly disabled.

`verified` requires `profile.configured_by_interview = true` and a recorded `verified_at`. Only `verified` supports workspace state `DIAGNOSTICS_CONFIGURED`; do not use `configured` as a completion state.

## `policies` table

```toml
[policies]
default_action = "deny"
remote_shell = "deny"       # deny | ask | allow
remote_write = "deny"       # deny | ask | allow
credential_output = "deny"
unknown_target = "deny"
allowed_collection_modes = ["local-read"]
forbidden_actions = []
```

`default_action`, `credential_output`, and `unknown_target` must be `deny`. `allow` expresses only a project-level ceiling and still requires current task authorization. Production access, writes, restart, deployment, deletion, and data replay require separate confirmation.

Collection modes use only `local-read`, `local-process-inspect`, `file-copy-read-only`, `api-read-only`, `observability-query`, and `remote-command-read-only`.

## `targets` array

Every target records at least:

```toml
[[targets]]
id = "service-test"
type = "container"
environment = "test"
fact_status = "code-verified"
endpoint_refs = []
log_locations = []
```

Target type uses only the schema enum: `local-cli`, `desktop-app`, `local-process`, `library`, `batch-job`, `baremetal-service`, `container`, `kubernetes`, `distributed-system`, `observability-backed`, or `hybrid`.

Fact status uses only `declared`, `code-verified`, `endpoint-verified`, `runtime-observed`, or `stale`. Add provenance, code location, observation time, sensitivity, confidence, and expiration conditions in task evidence or diagnostic knowledge. Historical material alone cannot receive a verified status.

`endpoint_refs` stores endpoint references, not credentials or credential-bearing URLs. `log_locations` must match the target type and environment.

Detailed discovery for complex targets may live under `diagnostics/targets/`, but `project/diagnostics/diagnostic-profile.toml` remains the only aggregate source of truth.

## `providers` array

```toml
[[providers]]
id = "local-files"
kind = "local-files"
enabled = true
authorization = "task-scoped"
target_refs = ["service-test"]
credential_refs = []
```

Provider kind uses only `local-files`, `local-process`, `file-transfer`, `remote-command`, `container-runtime`, `kubernetes-api`, `logs-api`, `metrics-api`, `traces-api`, or `custom`.

Authorization uses only `denied`, `read-only`, `ask-each-time`, or `task-scoped`. Even when `enabled = true`, all of the following remain required: environment capability, Provider interface support, project policy, valid target facts, and current task authorization.

Store credential references such as `env://NAME`, `keychain://...`, `file-ref://...`, or `vault://...`. Never print values while validating.

Detailed configuration for a complex Provider may live under `diagnostics/providers/` and be referenced or summarized by the aggregate profile. A Provider file must not create a second aggregate project diagnostic state.

## `authorizations` and `facts`

`authorizations` stores user-confirmed actions, targets, environments, read-only or task-scoped modes, provenance, confirmation time, and expiration time. It may only narrow core and project policy and cannot override prohibitions.

`facts` stores declarations, code and configuration inspection, endpoint verification, runtime observations, and their evidence, observation time, confidence, sensitivity, and expiration conditions. Reusable detailed knowledge may live under `diagnostics/knowledge/`, but a fact in the profile must establish provenance for it.

## `correlations` and `retention`

`correlations` records business correlation identifiers usable across logs, metrics, traces, and task evidence. Mark sensitive identifiers with `sensitive`. At least one source is required to establish correlation.

`retention.evidence_directory` uses a safe workspace-relative path. Retention days must not exceed the user-confirmed range. Keep `redaction_required` true by default.

## Action decision

Every diagnostic action evaluates:

```text
environment facts prove the capability
AND the Provider explicitly supports the action
AND the profile permits the target, environment, and collection mode
AND core and project policies permit it
AND the current task explicitly authorizes it
AND dependent facts have not expired
```

Deny on any unknown, conflict, or stale value. Connectivity and credential availability cannot expand authorization.

## Completion gates

- The mandatory questionnaire is complete and the profile has `configured_by_interview = true`.
- Code and configuration inspection established the target model.
- Authorized validations have current evidence; unverified facts do not support remote actions.
- The profile satisfies `.ai-workspace/schemas/diagnostic-profile.schema.json`.
- No credential values are stored; default action and unknown targets remain denied.
- The profile and `.ai-workspace/policies/diagnostics.toml` agree.
- Diagnostic hard constraints are recompiled into effective AI instructions.
- The minimal dry run stays within authority, writes nothing to the target, and is auditable.
- `$workcell-doctor` passes.

When any gate fails, keep status `unconfigured`, `configuring`, `draft`, `degraded`, or `stale` and prohibit affected remote actions. Only a `verified` profile supports workspace state `DIAGNOSTICS_CONFIGURED`.
