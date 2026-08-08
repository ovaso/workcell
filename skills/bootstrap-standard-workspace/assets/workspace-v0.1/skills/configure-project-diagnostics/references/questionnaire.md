# Diagnostic Configuration Questionnaire

## Group 1: safety and authorization

Ask this group first and wait for explicit answers. Do not substitute default answers for user choices.

1. Which actions are absolutely prohibited? Confirm remote shell, file writes, configuration changes, restart, deployment, scaling, deletion, data replay, tool installation, and production access separately.
2. Which action categories are currently allowed? Distinguish local file reads, local commands, process inspection, remote metadata reads, log reads, metric queries, trace queries, network probes, and sample reproduction.
3. Which projects, targets, and environments does authorization cover? Identify development, test, staging, production, and exceptions.
4. Is authorization a long-lived project policy or valid only for the current task? Record confirmation time, confirmer semantics, and expiration conditions.
5. Which data is sensitive? Establish redaction requirements for credentials, personal information, customer data, business content, recordings, dumps, stack traces, and database content.
6. Where may collected results be stored, for how long, and who may read them?

Compile answers into a deny-by-default policy. Treat ambiguous answers as unauthorized and restate the current boundary before continuing.

## Group 2: target and runtime model

1. Which target types apply, and is the path hybrid?
2. How is each target started, stopped, reproduced, and judged healthy?
3. Which environment, instance, node, namespace, cluster, account, or tenant boundaries exist?
4. How do code repositories, build artifacts, deployment units, and runtime targets map to each other?
5. Which targets are reference-only, and which allow actual collection?

## Group 3: evidence sources

1. Are logs in files, standard output, system logs, application sandboxes, or platform query APIs?
2. Where do metrics, traces, events, crash reports, dumps, local databases, and caches come from?
3. What are the format, timestamp, time zone, rotation, sampling, and retention rules for every evidence type?
4. Are there known health endpoints, diagnostic commands, read-only APIs, or query templates?
5. Which sources require manual export, and which may be read by a Provider?

## Group 4: correlation and reproduction

1. Which business correlation identifiers are used: request ID, trace ID, call ID, job ID, user or tenant ID, window ID, process ID, pod UID, or others?
2. How do identifiers propagate from entry points to logs, metrics, traces, and persistent data?
3. Can reproduction create external side effects, real traffic, charges, messages, notifications, or data writes?
4. What is the smallest safe reproduction environment, input, and stop condition?
5. What are polling frequency, maximum duration, maximum download size, and concurrency limits?

## Group 5: Provider and credentials

1. Which Provider is planned, and which interface actions can it perform?
2. Is the Provider actually available in the current host environment, or does it exist only in the capability catalog?
3. Which reference supplies credentials, and what is their scope and least privilege?
4. Does the Provider cache, upload, or further process collected data?
5. How should the workflow stop and preserve evidence when the Provider fails, times out, is rate-limited, or returns partial results?

## Group 6: storage and maintenance

1. Where are raw evidence, redacted copies, indexes, and summaries stored?
2. Which files are long-term project knowledge, and which belong only to the current task?
3. When do endpoints, nodes, permissions, and credential references expire, and how are they revalidated?
4. Who is responsible for disabling, revoking, or reconfiguring diagnostic capabilities?

## Conflict handling

- The user's latest explicit prohibition overrides historical configuration and documentation.
- When project policy is broader than task authorization, task authorization prevails; task authorization cannot expand project policy.
- When code, configuration, and runtime facts conflict, record the conflict and stop the affected action.
- When the production boundary, credential permissions, or data sensitivity cannot be confirmed, prohibit remote collection.
