# Project Plugin Specification V0.1

## 1. Definition

A project plugin is the Workcell workspace's internal project-adaptation protocol; it is not an AI-platform plugin. It describes stable project differences. Current-machine paths, secrets, and dynamic Git state belong to the project instance.

## 2. Minimum content

- Project ID, display name, and plugin version.
- Single-repository or multi-repository model.
- Repositories, modules, default branches, and module roles.
- Technology stack and composition of generic adapters.
- Build, test, review, release, and rollback rules.
- High-risk project paths and knowledge entry points.
- Enabled project capability plugins.
- Compatible workflow and capability-plugin API versions.

The V0.1 canonical file is `project/plugin/project-plugin.json`, validated by `.ai-workspace/schemas/project-plugin.schema.json`. Absolute local paths, the current branch, dirty/ahead/behind state, environment bindings, and endpoint references belong only to the project instance, not the reusable plugin.

## 3. Module roles

- `edit`: a task may modify the module.
- `verify`: the module may be used only for contract, compilation, and integration-path verification.
- `reference`: read-only reference.

A task may narrow these roles but must not expand them without authorization.

## 4. Evidence layers

A project plugin separates:

- `facts`: facts directly confirmed by user statements, code, Git, or configuration;
- `inferences`: conclusions that cite fact IDs;
- `policies`: project rules or user restrictions with explicit provenance;
- `unresolved_questions`: conflicts and unconfirmed matters.

Do not turn a single questionnaire answer into a code fact that can be inspected, and do not turn an inference into a policy.

## 5. Workflow commands

Represent build, test, verification, review, release, rollback, and close workflows with declarative `argv` arrays and relative working directories. Do not persist unreviewed shell-concatenation strings.

Project adaptation supports these standard stages:

```text
discover
scope
prepare
context
plan
verify
diagnose
review
release
close
```

Prefer declarative configuration. Add scripts or project-specific Skills only for complex behavior.

## 6. Generation process

Project adaptation combines:

1. interactive user confirmation;
2. read-only discovery from code, Git, and configuration;
3. fact verification within the permitted safety boundary;
4. explicit resolution of conflicting facts.

Historical documentation must not be promoted directly to current fact.
