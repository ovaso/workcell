# Lifecycle

## Workspace lifecycle

```text
EMPTY
  -> CREATED
  -> ENVIRONMENT_INITIALIZED
  -> PROJECT_ATTACHED
  -> PROJECT_ADAPTED
  -> DIAGNOSTICS_CONFIGURED (optional)
  -> READY
  -> DEGRADED / PAUSED
  -> ARCHIVED
```

### EMPTY -> CREATED

Bootstrap expands standard assets only into an empty directory, records the release source, and performs structural validation. It does not inspect the environment, access the network, or attach a project.

### CREATED -> ENVIRONMENT_INITIALIZED

Collect commands, toolchains, environment-variable names, and network facts to produce the first environment snapshot and capability recommendations.

### ENVIRONMENT_INITIALIZED -> PROJECT_ATTACHED

Confirm a single-repository or multi-repository model, attach project code mirrors, and register remotes, existing rules, documentation, knowledge, and requirement material.

### PROJECT_ATTACHED -> PROJECT_ADAPTED

Generate a project plugin through interactive questions, code discovery, and fact verification. Establish the module, branch, build, test, review, release, and risk models.

### PROJECT_ADAPTED -> DIAGNOSTICS_CONFIGURED

When needed, interactively configure diagnostic targets, Providers, security boundaries, endpoints, identifiers, and collection workflows. Remote diagnostics fail closed when unconfigured.

### READY

The workspace may enter `READY` only after environment facts, project configuration, policies, AI rules, and all Doctor gates pass.

## Task lifecycle

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

Any active state may explicitly enter `PAUSED`. Discovery and repair are actions within states: scope discovery happens during `INBOX -> SCOPED`, and feedback repair happens in `DEV_FEEDBACK / TEST_FEEDBACK`. A project plugin may add transition gates but must not introduce incompatible project-specific state names.

## Standard evolution loop

After task completion or during a periodic retrospective, an explicitly authorized workspace may generate a redacted feedback candidate. The candidate remains in the workspace until the user deliberately gives it to the standard repository. Import first creates a proposal; only review, implementation, full validation, and upgrade-impact assessment can move it into a new Release. This loop does not change the main workspace lifecycle and never grants automatic upload, adoption, or upgrade authority.
