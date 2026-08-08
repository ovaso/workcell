---
name: configure-project-diagnostics
description: Configure project diagnostic targets, Providers, security boundaries, and collection workflows for a Standard Workspace through a mandatory interactive questionnaire, code inspection, and fact verification. Use when first enabling or reconfiguring diagnostics for a local CLI, desktop application, local process, batch job, bare-metal service, container, Kubernetes workload, observability-backed system, or hybrid system, and whenever endpoints, credential references, permissions, deployment models, or diagnostic workflows change.
---

# Configure Project Diagnostics

Establish a reviewable, verifiable, deny-by-default diagnostic capability for a project. Treat structured configuration as authoritative; capability does not imply authorization.

## Enforce the boundary

- Read `AI_WORKSPACE.md`, `.ai-workspace/workspace.toml`, the project plugin, environment facts, and existing diagnostic configuration first.
- Configure diagnostics only after the workspace reaches at least `PROJECT_ADAPTED`; otherwise stop and return to project adaptation.
- Run an explicit questionnaire for initial configuration and every security-boundary change. Historical documentation, old configuration, and tool availability do not replace user confirmation.
- Before the user answers the first safety questions, do not probe remote systems, validate endpoints, read credentials, start reproductions, or collect evidence.
- Evaluate each action separately: environment capability is present, the Provider supports it, project policy permits it, and the current task explicitly authorizes it. Deny the action when any condition is unknown or unmet.
- Store credential references only; never store tokens, passwords, private keys, or kubeconfig content.
- Treat unconfigured state, failed validation, stale facts, and permission conflicts as fail-closed. Only local code and existing files may be analyzed in that state.

## Configure

1. Read [questionnaire.md](references/questionnaire.md), ask the first safety and permission questions, and wait for explicit answers.
2. Immediately preview confirmed prohibitions, default actions, environment boundaries, and authorization lifetimes. Ask the user to review them before any diagnostic action.
3. Read the applicable section of [target-profiles.md](references/target-profiles.md) and continue asking about runtime, deployment, evidence sources, correlation identifiers, redaction, and retention.
4. Inspect project code and configuration read-only. Locate launch points, logging configuration, telemetry SDKs, health checks, crash handling, container or cluster manifests, business correlation identifiers, and environment-selection logic.
5. Separate declarations from facts. Record source, evidence, observation time, sensitivity, confidence, and expiration conditions for every fact. Do not promote historical documentation directly to a current runtime fact.
6. Run the minimum read-only verification only when the user authorizes that specific verification. Prefer local static checks. Obtain separate authorization for remote metadata, endpoint probes, sample collection, and polling.
7. Select a Provider that meets the requirements and verify its `discover/questionnaire/requirements/validate/plan/collect/poll/correlate/sanitize/index/summarize/health` capabilities. Stop when a required capability is missing; do not bypass policy temporarily.
8. Follow [configuration-contract.md](references/configuration-contract.md) to preview changes to `project/diagnostics/diagnostic-profile.toml`, diagnostic policy, unverified facts, expiration conditions, and prohibited actions.
9. After explicit approval of the preview, write a schema-valid diagnostic profile and `.ai-workspace/policies/diagnostics.toml`. Make the project plugin's diagnostic capability reference `project/diagnostics/diagnostic-profile.toml`, then recompile project-level AI adapter rules so hard constraints reach effective entry points such as `AGENTS.md`.
10. Validate the configuration and run one explicitly authorized minimal dry run. Successful connectivity does not grant additional authority.
11. Run `$standard-workspace-doctor`. Advance to `DIAGNOSTICS_CONFIGURED` only after configuration, generated rules, and Doctor checks pass. The complete Doctor still gates entry into `READY`.

## Code and fact evidence

- Give the repository, file, and symbol location for every code conclusion.
- Give the target, environment, source, verification method, and observation time for every runtime fact.
- Keep the profile `draft` or mark it `stale` when code declarations conflict with runtime facts. Mark the workspace `DEGRADED` when critical capabilities are affected, then request a decision or continue verification.
- Keep production access, writes, remote shell, restart, scaling, deployment, deletion, configuration changes, and data replay under separate authorization. Do not interpret permission to diagnose as permission for those actions.

## Complete

Report configured targets and Providers, active authorization, explicit prohibitions, code evidence, verified facts, unverified or stale facts, dry-run results, Doctor results, and actions that remain fail-closed. Do not output credential values.
