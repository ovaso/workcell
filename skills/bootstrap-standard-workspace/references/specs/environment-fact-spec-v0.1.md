# Environment Fact Specification V0.1

## 1. Initial scope

Environment facts cover only commands, toolchains, environment variables, and network targets. Future extensions must preserve the existing fact metadata contract.

## 2. Fact source types

- `declared`: stated by a user, workspace, or project.
- `discovered`: found through read-only commands, files, or configuration.
- `derived`: inferred from multiple facts.
- `runtime`: current state that can change quickly.

## 3. Common metadata

Every fact records at least:

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

Optional metadata includes `expires_at / supersedes / fingerprint / notes`.

## 4. Execution context

A fact must not be used outside its observation context. Recommended contexts are:

```text
system
login-shell
non-interactive-shell
ai-execution
workspace
project
task
```

## 5. Command facts

Record the command name, availability, resolved path, version, probe method, and capability mappings. The presence of a command does not grant authorization to execute it.

## 6. Toolchain facts

Distinguish the declared version, installed versions, and currently resolved version. Record the manager and scope when directly observed.

## 7. Environment-variable facts

Sensitivity levels:

- `public`: V0.1 still stores only the name and presence; a later policy may explicitly allow harmless values.
- `private`: store presence, source, and an optional safe fingerprint.
- `secret`: store only the name and whether it resolves.
- `unknown`: treat as `secret`.

V0.1 prohibits persisting raw environment-variable values.

## 8. Network facts

Probe only explicitly allowlisted targets. Record protocol, target reference, status, probe method, observation time, and TTL. Do not scan unknown addresses or ports.

## 9. Capabilities and recommendations

The environment layer normalizes facts into capabilities. Projects and adapters declare required, recommended, and optional capabilities, which produce missing-capability, degradation, or installation recommendations. A recommendation never becomes installation authorization automatically.

The expanded workspace carries `knowledge/tool-capabilities.toml` as versioned seed knowledge. It describes safe version probes, capability mappings, and recommendation levels for known commands; it does not claim that any tool is installed on the current machine. Environment-refresh workflows may use it to select candidate commands and generate recommendations. Actual availability always comes from observations in the current execution context.
