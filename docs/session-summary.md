# Session Summary: AI Native Standard Workspace Product Concept

## 1. Starting point

The design began with recurring problems in AI-assisted software workflows. Multi-repository code, requirement records, isolated workspaces, plans, memory, logs, and diagnostic material are often scattered across different media. State is mostly implicit in Markdown, Git, and personal memory, with no unified control plane.

The product objective therefore became a reusable, continuously upgradable personal AI workflow standard rather than a workspace customized for any existing project.

## 2. Final product definition

The product was ultimately defined as:

> A versioned, self-contained, text-only Bootstrap Skill that is as AI-platform-neutral as possible. It is both an AI-readable installation protocol and the distribution medium for a standard workspace. An AI expands its assets into an empty directory. The expanded workspace carries its own specifications, Skills, tools, schemas, and fact-management capabilities, then establishes host environment, project, and diagnostic facts through initialization. V0.1 deterministic scripts provide matching POSIX `sh` and PowerShell execution profiles.

Recommended operating model:

```text
single canonical source repository
  -> Tag / Release
  -> Bootstrap Skill directory or ZIP
  -> expand standard workspace
  -> initialize host environment
  -> attach and adapt project
  -> configure diagnostic capabilities
  -> Doctor
  -> READY
```

## 3. Core layers

The effective capability for a task is composed from:

```text
generic workflow kernel
+ current machine capabilities
+ generic technology adapters
+ project plugin
+ project instance facts
+ project capability plugins
+ current task state
```

### 3.1 Bootstrap distribution layer

Responsible for creation, validation, repair, and upgrade. Secure self-update is added only after production standards, the canonical repository, and the Release process are stable. Bootstrap is installation media and does not perform daily project work.

### 3.2 Standard workflow kernel

The kernel knows no specific project. It defines workspace and task lifecycles, workspace isolation, context assembly, the evidence model, security constraints, multi-agent ownership, and Doctor/Repair/Upgrade capabilities.

### 3.3 Host environment fact layer

Describes what the current machine can actually do in the current execution context. Initial facts cover:

- installed commands;
- toolchains and version managers;
- environment variables;
- network environment and reachability of approved targets.

### 3.4 Generic technology adapters

Provide cross-project support for Git, Maven, Spring Boot, Node, SQL, Docker, Kubernetes, and similar technologies. Project plugins compose and configure these adapters rather than copying generic implementations.

### 3.5 Project plugin

Stores stable project differences, including identity, repositories, modules, dependencies, branches, build, tests, review, release, high-risk paths, project knowledge, and project-specific Skills.

A project plugin is an internal standard-workspace protocol, not a Codex Plugin.

### 3.6 Project instance

Stores dynamic bindings on the current machine, including local paths, remotes, environment-variable references, mirrors, workspaces, and live Git state.

### 3.7 Project capability plugins

Diagnostics are the first project capability that requires a formal plugin definition. Future capabilities may cover review, release, migration, performance tests, and security checks.

### 3.8 Task instance

Requirements, defects, diagnostics, and reviews are all tasks. A task stores type, status, current plan, module roles, next action, gates, risks, workflow version, project-plugin version, environment snapshot, and execution evidence.

## 4. Important design corrections

### 4.1 Keep the generic kernel generic

The generic kernel contains no project facts, terms, directory conventions, or runtime assumptions. A specific project can enter only through a separate project plugin, project instance, and integration tests.

### 4.2 Do not make a Codex Plugin the product

A Codex Plugin is platform-specific and can only be an optional future installation channel. The product is a Bootstrap Skill that is as platform-neutral as possible. An AI without automatic Skill discovery can still read `SKILL.md` explicitly.

### 4.3 Do not build one giant Skill

The external Bootstrap Skill handles only `create / validate / repair / upgrade`. The expanded workspace contains multiple narrow runtime Skills, so daily work does not continuously depend on the external Bootstrap.

### 4.4 A ZIP is only an immutable distribution artifact

A static ZIP cannot perform initialization, adaptation, or upgrades by itself. The complete system combines a Git source repository, Bootstrap Skill, versioned assets, specifications and schemas, deterministic scripts, migrations, and a ZIP Release.

### 4.5 AGENTS is not the sole source of truth

Structured policy and fact files are authoritative. `AI_WORKSPACE.md` is the platform-neutral entry point. `AGENTS.md` and similar files are compiled adapters for specific AIs. Hard safety constraints must reach the effective AI instruction file.

### 4.6 Diagnostics are not synonymous with server logs

Diagnostics collect, correlate, and analyze runtime facts for a software target. Targets include local CLIs, desktop clients, local processes, codebases, batch jobs, bare-metal services, containers, Kubernetes, distributed systems, and observability systems.

### 4.7 Capability is not authorization

An action is executable only when:

```text
the host environment has the capability
AND the Provider supports it
AND project policy permits it
AND the current task authorizes it
```

The presence of an SSH command does not imply permission to log in to a server.

## 5. Bootstrap and self-hosting

The Bootstrap Skill is a seed package:

```text
Bootstrap Skill = installation medium
Standard Workspace = installed runtime system
Workspace Skills = built-in system tools
Project Plugin = project driver and adapter
```

Bootstrap expansion must not assume Node, Python, or mise is already present. The first release supports POSIX shell, Windows PowerShell 5.1 or PowerShell 7, direct copying through AI file tools, and manual archive extraction as a fallback. A future standalone bootstrapper remains optional.

Bootstrap does not access the network, install software, modify the shell, write outside an explicitly specified empty directory, or overwrite existing content by default.

## 6. Workspace lifecycle

```text
EMPTY
  -> CREATED
  -> ENVIRONMENT_INITIALIZED
  -> PROJECT_ATTACHED
  -> PROJECT_ADAPTED
  -> DIAGNOSTICS_CONFIGURED (optional)
  -> READY
```

### 6.1 Expansion

Copy standard assets, record the release source and version, and validate structure. Do not inspect the environment or attach a project.

### 6.2 Environment initialization

Discover commands, toolchains, variables, and network targets; normalize them into capabilities; create the first snapshot and optimization recommendations.

### 6.3 Project attachment

Confirm a single-repository or multi-repository model, attach a read-only mainline mirror, and register remotes, existing rules, documentation, knowledge, and requirement material.

### 6.4 Project adaptation

Generate a project plugin through questionnaires, code discovery, and validation. Establish module, branch, build, test, review, release, and risk models.

### 6.5 Diagnostic configuration

When needed, interactively confirm security boundaries, target types, deployment model, observability, business identifiers, and collection workflow. All remote diagnostics remain denied until configured.

### 6.6 Final validation

The workspace may enter `READY` only after environment facts, the project plugin, AI rules, directories, policies, and security gates all pass.

## 7. Task lifecycle

```text
INBOX
  -> SCOPED
  -> PLANNED
  -> READY
  -> IMPLEMENTING
  -> VERIFYING
  -> DEV_FEEDBACK / TEST_FEEDBACK
  -> QC_READY
  -> RELEASE_READY
  -> DONE
  -> ARCHIVED
```

An active state may explicitly enter `PAUSED`. Discovery and feedback repair are actions within states and do not require extra state names. A project plugin may add transition gates but should not invent an incompatible project-specific state machine.

## 8. Environment fact model

Distinguish:

```text
declaration: the project requires Java 17
fact: the current context resolves Java 17
capability: the current context provides JVM Runtime >= 17
recommendation: pin the project toolchain with mise
```

The seed package may include knowledge about recognizing tools but cannot predeclare that a tool is installed on the current machine.

Classify environment variables as `public / private / secret / unknown`, treating unknown as secret. V0.1 does not persist raw values. Probe only allowlisted network targets, record a TTL, and do not scan unknown addresses or ports.

Facts include an execution context such as system, login shell, non-interactive shell, AI execution environment, workspace, project, or task.

## 9. Generic fact model

Fact source types include:

- `declared`: explicitly stated by a user or project;
- `discovered`: found in Git, files, or configuration;
- `derived`: inferred from code and other facts;
- `runtime`: current dynamic state.

Common metadata includes source, observation time, confidence, context, expiration, supersession, and sensitivity.

Recommended precedence:

```text
hard safety prohibitions
> user-confirmed permissions and workflow
> current runtime or endpoint verification
> current project configuration
> project-plugin declarations
> code-derived conclusions
> historical plans, documentation, and memory
```

## 10. Project plugin

Recommended project-plugin extension points:

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

Standard module roles:

- `edit`: modification allowed;
- `verify`: contract, compilation, and integration-path verification only;
- `reference`: read-only reference.

These roles also define future multi-agent write boundaries.

## 11. Diagnostic capability plugin

Diagnostic configuration requires an interactive questionnaire and combines user declarations, code/configuration discovery, and authorized endpoint verification.

Question order:

1. absolute security boundaries;
2. diagnostic target type;
3. deployment and environment model;
4. observability capabilities;
5. business correlation identifiers;
6. collection, reproduction, storage, redaction, and retention workflow.

When diagnostics are unconfigured, only local code and existing files may be analyzed. Remote actions, unregistered endpoints, and unknown Providers are prohibited.

Structured diagnostic policy is authoritative. Hard constraints such as prohibited login, prohibited remote shell, read-only download, credential protection, and endpoint allowlists are compiled into project-level AGENTS adapters.

Project-specific diagnostic resources register as project capability plugins rather than entering generic kernel directories.

## 12. File ownership and upgrade

Every file is classified as:

- `distribution`: release-maintained and replaceable by a Migration;
- `generated`: recompiled from facts;
- `workspace`: maintained by users, projects, and tasks and preserved by upgrades.

Workspace upgrade flow:

```text
read versions
-> select Migration
-> show differences and file impact
-> obtain user confirmation
-> create a recoverable snapshot
-> apply migration
-> recompile generated files
-> run Doctor
-> commit success or roll back failure
```

## 13. Distribution and self-update

Formal release model:

```text
single canonical Git repository
-> stable tag
-> complete validation
-> file manifest and hashes
-> immutable Release
-> Bootstrap Skill ZIP
```

Maintain product version, workspace schema, environment-fact schema, project-plugin API, diagnostic-capability API, and task schema independently.

Self-update is deferred until the canonical repository, formal Releases, and complete verification mechanisms are stable. Automatic checks may be enabled by default, automatic downloads may be configurable, and automatic application remains prohibited by default. Upgrade only to a formal Release; never overwrite from the latest `main` commit.

## 14. Cross-AI strategy

The standard consists of `SKILL.md / bundle.toml / AI_WORKSPACE.md / references / schemas / assets / scripts / migrations`. AGENTS, CLAUDE, and similar files are derived adapters.

An AI with Skill support may trigger Skills automatically. Other AIs can read `SKILL.md` explicitly. A Codex Plugin may package the same Skill but cannot become a specification dependency.

English is canonical. Localized documentation and adapters are generated through an explicit localization Skill, retain links to their English sources, and never change stable identifiers or policy semantics.

## 15. Current implementation boundary

V0.1 implements the product skeleton, Bootstrap, foundational fact/plugin/diagnostic protocols, standard template, core Skills, and validation. Complete migrations, self-update, cross-platform bootstrappers, remote diagnostics, and automatic project development are outside this release.

This summary records product decisions. It does not assert that facts about any current machine, project, endpoint, or tool have been validated through initialization.
