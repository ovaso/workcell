# Diagnostic Target Profiles

Read only the sections relevant to the current target. Model each component of a hybrid system separately, then declare their relationships.

## Local CLI, batch job, and local process

- Inspect entry commands, argument parsing, exit codes, standard output and error, configuration search order, working directories, and temporary files.
- Verify the actual binary or script path, version, environment-variable scope, and minimal reproduction input.
- Authorize process start, signal delivery, debugger attachment, performance sampling, and local-state modification separately.
- By default, prohibit commands that may write a database, send messages, call production endpoints, or create charges.

## Desktop application

- Inspect bundle identity, launch entry point, application sandbox, system logs, crash reports, automatic update, and local database locations.
- Distinguish authorization for UI observation, application launch, automated clicks, file export, screen recording, and accessibility control.
- Verify operating system, application version, window state, account environment, and reproduction steps.
- By default, prohibit reading unauthorized personal directories, keychains, browser data, and other application sandboxes.

## Library and embedded component

- Inspect callers, version resolution, initialization order, log bridging, thread or event model, and error propagation.
- Prefer unit tests, a minimal host program, and existing traces. Confirm side effects before running a host program.
- Do not infer permission to access a resource from a library's network or file capabilities.

## Bare-metal or virtual-machine service

- Inspect service manager, process user, deployment directory, log rotation, listening ports, health checks, and configuration sources.
- Authorize remote file reads, process inspection, system logs, network probes, and remote shell separately. An open SSH port does not authorize login.
- Verify host identity, environment, service instance, and time synchronization; do not depend on a stale host inventory.
- By default, prohibit sudo, restart, configuration changes, writes to log directories, and unbounded large-file collection.

## Container

- Inspect image, entry point, runtime arguments, mounts, network, health checks, log driver, and resource limits.
- Verify container runtime, container ID, image digest, environment, and read-only collection method.
- Authorize exec, file copy, packet capture, profiling, and host-namespace access separately.
- By default, prohibit modifying running containers, committing images, restart, and reading unauthorized mounts.

## Kubernetes

- Inspect workloads, namespaces, Services, Ingresses, ConfigMap/Secret references, probes, logs, and telemetry configuration.
- Verify current context, cluster identity, namespace, RBAC, and resource UID. Do not infer the environment from a context name alone.
- Authorize API metadata reads, logs, events, port-forward, exec, ephemeral containers, and resource changes separately.
- By default, prohibit Secret-value reads, cross-namespace queries, exec, rollout, scale, delete, and apply.

## Observability

- Inspect logging, metrics and tracing SDKs, exporters, sampling policies, service names, resource attributes, and correlation identifiers.
- Verify data source, tenant or account, time range, time zone, index, query limits, and data delay.
- Authorize queries, saved queries, alert creation, raw-data export, and production-tenant access separately.
- Limit time windows, result volume, and polling frequency by default. Query capability does not authorize every dataset.

## Distributed and hybrid systems

- Select a target type above for every component rather than creating one large target with implicit global authority.
- Declare synchronous and asynchronous boundaries, message keys, trace propagation, clock differences, retries, and duplicate events.
- Set a shared time window, data volume, and stop condition for cross-target collection.
- When a component's permissions or facts become invalid, close only the affected path. Do not expand permissions on other targets to compensate.
