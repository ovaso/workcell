# Product Vision

## Definition

Workcell is a personal AI development workspace standard that is as platform-neutral as possible, text-only, versioned, distributable, and upgradable. The deterministic V0.1 bootstrap layer supports POSIX `sh` and Windows PowerShell 5.1 or PowerShell 7; host operating-system coverage and AI-platform compatibility remain independent product dimensions.

The primary deliverable is not a fixed project archive or a plugin bound to one AI platform. It is a self-contained Bootstrap Skill: an AI reads its protocols, scripts, specifications, and assets, then expands a Workcell workspace into an empty directory. The workspace uses its own Skills to establish environment, project, diagnostic, and task facts.

## Goals

- Give new workspaces a consistent directory structure, fact model, security boundary, and lifecycle.
- Ensure that, before executing a task, an AI knows what the current machine can do, what the project is, what actions are allowed, and which gate comes next.
- Adapt different projects through project plugins without contaminating the generic workflow kernel.
- Compose diagnostics, review, release, and similar functionality as project capability plugins.
- Evolve specifications, templates, Skills, and schemas through one canonical repository.
- Let an expanded workspace self-host without an ongoing dependency on an external installer.

## Non-goals

- Build an enterprise approval, ticketing, or organizational-governance platform.
- Put the rules of any specific business project into the generic kernel.
- Install tools, modify system configuration, or access remote environments automatically.
- Let historical memory override currently verified facts.
- Let the model freely invent directories, manifests, or migration results on every run.

## AI-native principle

```text
AI: understand, ask, analyze, choose, orchestrate, and explain
tools: copy, inspect, validate, compile, migrate, compare, and roll back
```

AI-native does not mean driving everything with prompts. The AI is the decision and interaction entry point for a standard process, while fragile operations remain in deterministic tools.
