# AI Native Standard Workspace

This personal AI-native standard workspace was created by `bootstrap-standard-workspace`. It provides a generic workflow and fact protocols, but it does not yet represent the actual state of the current machine or any project.

## First use

1. Ask the AI to read `AI_WORKSPACE.md` and `.ai-workspace/workspace.toml`.
2. Use `initialize-standard-workspace` to initialize the workspace and establish host environment facts.
3. Use `adapt-project-workspace` to attach code, remotes, and project rules.
4. If the project needs diagnostic capabilities, configure them interactively with `configure-project-diagnostics`.
5. Use `standard-workspace-doctor` to inspect facts, policies, and structure. The workspace may enter `READY` only after it passes.
6. Use `localize-standard-workspace` when reviewed documentation or AI guidance is needed in another language.

Runtime deterministic tools written in Python use one cross-platform implementation. On Windows, invoke them with `py -3`, `python`, or another Python 3 command verified by `inspect-host-environment`; no POSIX shell is required inside the expanded workspace.

## Important boundaries

- Initial state is `CREATED`; no project facts have been established.
- The presence of a local command does not authorize its use against an external system.
- When diagnostic capabilities are unconfigured, only local code and existing files may be analyzed.
- Structured facts and policies are authoritative; platform files such as `AGENTS.md` are compiled adapters.
- `requirements/` stores task records, `workspaces/` stores isolated execution directories, and `mirror/` stores read-only reference mirrors.
- English is canonical. Localized content under `locales/` is a reviewed, non-authoritative reading aid.

This workspace template is distributed under the terms in `LICENSE`.

See `AI_WORKSPACE.md` for the detailed entry point and `.ai-workspace/specs/` for standard protocols.
