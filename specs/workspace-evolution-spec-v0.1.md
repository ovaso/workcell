# Workcell Evolution Specification V0.1

## 1. Boundary

Workspace practice may produce candidates for Workcell evolution, but the Workcell repository remains the sole source of truth. Feedback export, import, proposal, adoption, and release are separate operations. A workspace must not modify the Workcell repository automatically, upload feedback, or trigger an upgrade.

Feedback contains only redacted abstract conclusions and minimal evidence summaries. It must not contain project names, repository or host paths, remote addresses, credentials, business data, complete logs, source code, or unauthorized material.

## 2. Feedback report

`feedback-report.schema.json` defines the exchangeable JSON report. A workspace writes reports to the workspace-owned `feedback/candidates/` directory. A report does not replace task, project, or environment facts.

- `redaction_confirmed` must be `true`; otherwise export is prohibited.
- `source_fingerprint` is an irreversible fingerprint generated locally by the workspace and used only for deduplication and independent-source counting. It must not carry workspace, project, or personal identifiers.
- `authorized_sources` declares only categories of authorized sources and records no paths or content.
- Every candidate records scope, confidence, occurrence count, and a minimal evidence summary.
- `standard-candidate` means eligible for review, never already part of the standard.

## 3. Ownership and adoption

| Scope | Handling |
| --- | --- |
| `local` | Keep in workspace knowledge or policy; do not import into the standard. |
| `project-plugin` | Maintain in the project plugin; do not add to generic assets. |
| `standard-candidate` | May be imported into the Workcell repository to create a proposal; still requires review. |

A generic proposal requires evidence from at least two independent workspaces, or one confirmed security, integrity, or compatibility defect. A one-off practice, project terminology, environment preference, or unverified inference must not become a generic constraint.

## 4. Integration and versioning

A maintainer places explicitly provided reports into the local, Git-ignored `evolution/inbox/`. `integrate-workcell-feedback` validates schema, redaction, scope, and duplicate IDs before writing reviewable evidence to `evolution/ledger/evidence.json`. It deduplicates by normalized candidate ID and counts independent workspace evidence with unique `source_fingerprint` values. It then creates a non-overwriting Change Set proposal under `evolution/proposals/`. It does not modify the product definition directly.

Only an adopted, reviewed change may modify specifications, schemas, Skills, or assets. Adoption also requires asset synchronization, full validation, upgrade-impact assessment, and version and release-record updates. Patch versions are only for behavior-preserving fixes; compatible additions use minor versions. Before the first `1.0.0` release, an incompatible product evolution may use a new minor version only when it is explicitly recorded as unreleased or released without an in-place Migration; every affected cross-product or cross-version installation must fail closed and require creation of a new workspace or a separately reviewed formal Migration. Starting with `1.0.0`, breaking changes to schemas, state machines, ownership, or default security semantics use a major version and require a Migration.
