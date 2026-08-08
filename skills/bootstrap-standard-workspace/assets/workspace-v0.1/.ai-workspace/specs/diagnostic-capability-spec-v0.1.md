# Diagnostic Capability Specification V0.1

## 1. Definition

A diagnostic capability collects, correlates, and analyzes runtime facts for a software target. It is a project capability plugin and is not synonymous with server troubleshooting.

## 2. Target types

```text
local-cli
desktop-app
local-process
library
batch-job
baremetal-service
container
kubernetes
distributed-system
observability-backed
hybrid
```

## 3. Configuration prerequisite

When a user requests project diagnostic configuration, begin an interactive questionnaire. The first questions establish only security and permission boundaries, which are then compiled immediately into project-level AI rules.

Question order:

1. absolute prohibitions and permitted actions;
2. target type;
3. deployment, runtime, and environment model;
4. log, metric, trace, crash, and local-state sources;
5. business correlation identifiers;
6. collection, reproduction, redaction, storage, and retention workflow.

## 4. Fact sources

```text
user-declared
code-discovered
config-discovered
endpoint-verified
runtime-observed
historical
```

Security prohibitions and user-confirmed permissions have the highest precedence. Reachability is not authorization.

## 5. Provider interface

```text
discover
questionnaire
requirements
validate
plan
collect
poll
correlate
sanitize
index
summarize
health
```

## 6. Structured files

The aggregate source of truth is fixed at:

```text
project/diagnostics/diagnostic-profile.toml
```

Detailed target, Provider, and knowledge resources may live under:

```text
diagnostics/targets/
diagnostics/providers/
diagnostics/knowledge/
```

The aggregate file records `schema_version`, profile identity, fail-closed policy, targets, Providers, correlation identifiers, per-action authorization, facts, and evidence-retention rules. The project plugin references the capability and does not copy diagnostic facts.

Profile status is one of `unconfigured / configuring / draft / verified / degraded / stale / disabled`. Only `verified` can support workspace state `DIAGNOSTICS_CONFIGURED`.

## 7. Execution conditions

```text
environment capability is present
AND the Provider supports the action
AND project policy permits it
AND the current task authorizes it
```

Fail closed when any condition is unmet.

Authorization is narrowed to an action, target, and environment, with source, confirmation time, and optional expiration. A generic `diagnostics = true` does not constitute authorization.

## 8. AGENTS integration

Structured diagnostic policy is the source of truth. Prohibitions on login and remote shell, read-only collection rules, credential protection, allowed endpoints, and stale-fact stop conditions must be compiled into the project-level AI rule file.

## 9. Unconfigured state

When diagnostic status is `unconfigured`:

- only local code and existing files may be analyzed;
- all remote diagnostic actions are prohibited;
- unregistered endpoints, directories, nodes, and Providers are prohibited.
