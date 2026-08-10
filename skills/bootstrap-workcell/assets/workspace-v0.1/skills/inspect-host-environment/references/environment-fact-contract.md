# Environment Fact Contract V0.1

## Required metadata

Every fact must include:

```text
id
kind
source_type
source
observed_at
context
confidence
sensitivity
```

Allow `expires_at`, `supersedes`, `fingerprint`, and `notes` when needed. Use `declared`, `discovered`, `derived`, or `runtime` for `source_type`.

## V0.1 scope and context

Keep `facts` limited to these four keys:

```text
commands
toolchains
environment_variables
network
```

Do not add a platform or operating-system fact category in V0.1.

Allow only these execution contexts:

```text
system
login-shell
non-interactive-shell
ai-execution
workspace
project
task
```

## Seed capability catalog

`knowledge/tool-capabilities.toml` is release-managed seed knowledge. Use it to choose known command candidates, safe version arguments, capability mappings, and recommendation levels. A catalog entry is a declaration about how to inspect a tool, never evidence that the command is installed. Only a current contextual observation may create an availability fact.

## Command facts

Record availability independently from version. A command may be present while its safe version probe is unsupported or times out.

Treat the resolved executable path as private host information. Capture only the first meaningful version line to avoid leaking unrelated system details.

## Toolchain facts

Keep these fields distinct:

| Field | Meaning |
|---|---|
| `declared_version` | Required by a user, workspace, project, or checked-in config |
| `installed_versions` | Directly enumerated from an authoritative manager or location |
| `current_version` | Resolved by the current execution context |
| `manager` | Directly observed manager; otherwise `unknown` |
| `scope` | system, user, workspace, project, or task |

Do not infer that every runtime is controlled by a discovered version manager.

## Environment variable sensitivity

| Classification | Persistence rule |
|---|---|
| `public` | Store the name and, only if a later policy explicitly permits it, a harmless value |
| `private` | Store the name, presence, source, and optional approved fingerprint; omit the value |
| `secret` | Store only the name, presence, and classification metadata |
| `unknown` | Treat effectively as `secret` until confirmed |

Credential indicators include `password`, `passwd`, `secret`, `token`, `credential`, `private_key`, `access_key`, `api_key`, `cookie`, `session`, `bearer`, and `auth`. Identity, path, host, endpoint, proxy, account, tenant, organization, and project names are normally private.

## Network facts

Accept only explicit targets. A target declaration is not probe authorization.

For a runtime observation record:

```text
protocol
target_reference
method
status
response_code or connection_result
observed_at
expires_at or ttl_seconds
```

Reject credentials in URLs. Do not follow redirects, because a redirect may escape the approved target. Treat HTTP error responses as evidence that the endpoint was reached while preserving the response code.

## Snapshot shape

The bundled collector emits this logical structure:

```json
{
  "schema_version": "0.1",
  "snapshot": {
    "id": "host-<timestamp>",
    "observed_at": "<UTC timestamp>",
    "context": "ai-execution",
    "status": "verified"
  },
  "facts": {
    "commands": [],
    "toolchains": [],
    "environment_variables": [],
    "network": []
  }
}
```

Use `verified` when collection completed normally. A caller that has declared required commands, toolchains, variables, or network facts may downgrade the snapshot to `degraded` when one or more required items are missing. Preserve the missing-item explanation outside raw facts or in snapshot notes; never label a failed or malformed collection as verified.

The collector intentionally emits facts only. Build inferences, policies, capabilities, and recommendations as separate artifacts or sections.
