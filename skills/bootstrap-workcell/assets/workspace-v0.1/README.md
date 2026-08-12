# Workcell

This personal Workcell was created by `bootstrap-workcell`. It provides a generic workflow and fact protocols, but it does not yet represent the actual state of the current machine or any project.

## First use

1. Ask the AI to read `AI_WORKSPACE.md` and `.ai-workspace/workspace.toml`.
2. Use `initialize-workcell` to initialize the workspace and establish host environment facts.
3. Use `adapt-project-workspace` to attach code, remotes, and project rules.
4. If the project needs diagnostic capabilities, configure them interactively with `configure-project-diagnostics`.
5. Use `workcell-doctor` to inspect facts, policies, and structure. The workspace may enter `READY` only after it passes.
6. Use `localize-workcell` in default `overlay` mode when reviewed documentation or AI guidance is needed in another language. Use explicit, preview-first `replace` only for selected readable documents when the locale is the workspace's working language.

Runtime deterministic tools written in Python use one cross-platform implementation. On Windows, invoke them with `py -3`, `python`, or another Python 3 command verified by `inspect-host-environment`; no POSIX shell is required inside the expanded workspace.

## Important boundaries

- Initial state is `CREATED`; no project facts have been established.
- The presence of a local command does not authorize its use against an external system.
- When diagnostic capabilities are unconfigured, only local code and existing files may be analyzed.
- Structured facts and policies are authoritative; platform files such as `AGENTS.md` are compiled adapters.
- `requirements/` stores task records, `workspaces/` stores isolated execution directories, and `mirror/` stores read-only reference mirrors.
- English is canonical by default. Localized content under `locales/` is a reviewed, non-authoritative reading aid; an approved `replace` is a tracked, rollback-ready local integrity exception rather than a silent source-of-truth change.

This workspace template is distributed under the terms in `LICENSE`.

See `AI_WORKSPACE.md` for the detailed entry point and `.ai-workspace/specs/` for standard protocols.
