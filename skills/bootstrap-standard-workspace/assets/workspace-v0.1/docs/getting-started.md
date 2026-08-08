# Getting Started

## 1. Confirm the initial state

Verify that `.ai-workspace/workspace.toml` has status `CREATED` and that Bootstrap did not overwrite an existing directory.

## 2. Establish environment facts

Use `initialize-standard-workspace` and `inspect-host-environment`. Inspection records only commands, toolchains, environment-variable names with sensitivity classifications, and explicitly authorized network-probe results. Never write credential values to files.

On Windows, use `py -3`, `python`, or another verified Python 3 command for the cross-platform runtime scripts. Do not assume a POSIX shell is installed.

## 3. Attach the project

Use `adapt-project-workspace`. Confirm objectives and boundaries first, then inspect code, build files, Git configuration, and existing documentation. Generate the project plugin, project instance, and evidence index. Do not inherit facts from examples or historical projects.

## 4. Configure diagnostics when needed

Use `configure-project-diagnostics`. First confirm prohibitions, target type, deployment model, observability, correlation identifiers, evidence storage, and redaction rules. Generate policy before compiling diagnostic hard constraints into `AGENTS.md`.

## 5. Run the Doctor and enter READY

Run `standard-workspace-doctor`. Enter `READY` only after required facts, policies, structure, and versions all pass.

## 6. Generate localized content when needed

Use `localize-standard-workspace` after choosing an explicit target locale. Keep generated translations under `locales/<locale>/`, preserve English sources and machine-readable identifiers, and review the translation before treating it as operator guidance.
