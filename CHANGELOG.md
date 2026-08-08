# Changelog

This file records release-level changes to the AI Native Standard Workspace product. Design-session history is preserved in `docs/session-summary.md` and is not repeated here.

## [Unreleased]

## [0.1.0] - 2026-08-08

- Add the workspace-practice feedback and standard-evolution protocol: feedback is redacted and exported, then imported as a reviewable proposal; automatic upload, adoption, and upgrade remain prohibited.
- Establish English as the canonical product language and add a controlled post-bootstrap localization Skill.
- Add PowerShell counterparts for every POSIX shell entry point, including Bootstrap, repository maintenance, packaging, and test surfaces; keep Bootstrap execution dependency-free and offline on Windows.
- Adopt the MIT License and add GitHub community health files, contribution governance, issue and pull-request templates, Linux and Windows CI, CodeQL, dependency review, Dependabot, and a manual Release Candidate workflow.
- Establish an independent standard Git source repository.
- Define workspace, serialization, environment-fact, project-plugin, diagnostic, task, AI-instruction, and upgrade specifications.
- Provide a self-contained `bootstrap-standard-workspace` Skill and V0.1 workspace assets.
- Provide runtime Skills for environment initialization, environment inspection, project adaptation, diagnostic configuration, Doctor checks, task start, and upgrades.
- Provide Bootstrap creation, validation, repair planning, schema validation, packaging, and black-box tests.
- Add an installed Release integrity receipt, first-match ownership hashes, and the last-step receipt-replacement upgrade protocol.
- Harden fail-closed tests for bundle metadata, ancestor symlinks, non-empty targets, and creation races.
- Make the Doctor validate environment facts, templates, and project plugins through a dependency-free JSON Schema subset.
- Keep design-session history in the source repository while the distributed Skill carries only generic documentation, decisions, and tool-capability seed knowledge.
- Distinguish AI-platform neutrality from host-platform support; the V0.1 bootstrap baseline is POSIX `sh`.
