---
name: inspect-host-environment
description: Collect and refresh platform-neutral host environment facts for commands, resolved toolchains, environment variable names with sensitivity classification, and explicitly allowlisted network targets. Use when initializing a Standard Workspace, diagnosing capability drift, comparing execution contexts, or rebuilding an environment snapshot; default to a read-only preview and never print secret values or probe undeclared targets.
---

# Inspect Host Environment

Collect evidence about what the current execution context can resolve. Produce facts, not installation actions or project policy.

## Apply the default safety rules

- Run only read-only discovery and known version commands.
- Never install, upgrade, configure, source, or activate a toolchain manager.
- Never print or persist environment variable values.
- Treat an unclassified variable name as secret.
- Do not probe any network target unless the user names the exact target and explicitly authorizes the probe.
- Do not scan address ranges, ports, local subnets, service registries, or neighboring hosts.
- Do not infer operational authorization from an installed command or reachable endpoint.
- Write no files unless the user approves the exact output path and candidate content.

Read [references/environment-fact-contract.md](references/environment-fact-contract.md) before classifying facts or persisting a snapshot.

Read `knowledge/tool-capabilities.toml` from the workspace when present. Treat it only as versioned seed knowledge for candidate commands, safe version probes, capability mappings, and recommendation levels; never report a catalog entry as an installed-command fact without observing it in the current execution context.

## Select the observation context

Record the context in every fact. Use one or more of:

- `system`
- `login-shell`
- `non-interactive-shell`
- `ai-execution`
- `workspace`
- `project`
- `task`

Do not merge results from different contexts. A command found in a login shell is not automatically available to the AI execution context.

## Inspect the first-phase fact set

Keep the V0.1 `facts` object closed to exactly four categories: `commands`, `toolchains`, `environment_variables`, and `network`. Do not add host platform, hardware, process, operating-system, or project facts to this snapshot.

### Commands

For each conservative default or user-declared command candidate, record:

- name, availability, resolved path, and observation context;
- the safe version probe used and its first meaningful output line;
- timeout, failure, or unsupported-version-probe status;
- source, observation time, confidence, and sensitivity.

Use `command -v`, `Get-Command`, `where`, language-standard APIs, or an equivalent read-only resolver appropriate to the host. Do not execute an unknown command merely to see what it does.

### Toolchains

Distinguish:

- declared version required by a workspace or project;
- versions installed according to an authoritative manager or filesystem source;
- version currently resolved in this execution context.

Record the manager and scope only when directly observed. If only the resolved executable is known, report the current version and leave manager ownership unresolved.

### Environment variables

Record only:

- variable name;
- whether it is set in the current process context;
- sensitivity classification and classification source;
- optional safe fingerprint only when separately authorized and necessary.

Do not record values. Classify credential-like names as `secret`, identity/path/endpoint names as `private`, explicitly harmless process settings as `public`, and all remaining names effectively as `secret` until confirmed.

### Network facts

Without probe authorization, record an exact user-declared target only as `declared-not-probed`.

With authorization:

- probe only `http`, `https`, or an explicit `tcp` host and port;
- reject embedded credentials, query strings, fragments, wildcards, ranges, and missing ports for TCP;
- prevent redirects from expanding the target allowlist;
- record method, response or connection status, timeout, observation time, and TTL;
- classify reachability as runtime evidence, not durable capability or permission.

## Use the deterministic collector when available

When Python 3 is already verified in the current context, resolve this Skill directory and run `scripts/inspect_host.py` by absolute path. Use `python3` on POSIX, `py -3` on Windows when the Python Launcher is available, or the verified Python 3 command for the current context. The script writes JSON to standard output by default.

Example read-only preview:

```text
python3 <skill-dir>/scripts/inspect_host.py \
  --context ai-execution \
  --command git \
  --command node
```

Declare targets without probing:

```text
python3 <skill-dir>/scripts/inspect_host.py \
  --context workspace \
  --network-target https://example.invalid/health
```

Add `--probe-network` only after explicit authorization. Add `--output <path>` only after approving persistence; the script refuses to overwrite an existing file unless `--force` is also explicitly chosen.

PowerShell uses the same arguments without POSIX line continuations, for example: `py -3 <skill-dir>/scripts/inspect_host.py --context ai-execution --command git --command node`.

The collector marks a normally completed snapshot as `verified`. After comparing the result with caller-declared required facts, the caller may request `--status degraded` when required items are missing. Do not use `degraded` to hide collection errors or unsupported contexts.

If Python 3 is unavailable, perform the same read-only discovery with native host commands and emit the contract manually. Do not claim script validation.

## Separate the result layers

Return:

1. **Facts** — collector output and direct user declarations.
2. **Inferences** — capability conclusions that cite fact IDs.
3. **Policies** — existing workspace policy and the exact scope of any probe authorization.
4. **Recommendations** — missing or inconsistent tools, with no automatic installation.

Preserve conflicting facts when they belong to different contexts. Mark stale runtime and network facts with an expiry instead of silently reusing them.

## Persist only an approved snapshot

Before writing:

1. Show the destination and candidate summary.
2. Confirm no environment values or credential-bearing URLs are present.
3. Validate JSON parsing and required metadata.
4. Write a new immutable snapshot, then update any generated current projection atomically.
5. Leave lifecycle transitions to `$initialize-standard-workspace` or the owning workflow.

Report what was not inspected and why. An incomplete but honest snapshot is preferable to guessed facts.
