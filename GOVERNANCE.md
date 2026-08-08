# Governance

## Model

AI Native Standard Workspace uses a maintainer-led governance model. The current project maintainer is [@ovaso](https://github.com/ovaso).

Maintainers are responsible for repository access, issue and pull-request triage, specification integrity, security response, releases, and enforcement of project policies. Contributors propose and review changes through GitHub issues and pull requests.

## Decision process

Routine fixes may be accepted through normal review. Material changes to schemas, stable IDs, lifecycle rules, ownership, security boundaries, migrations, compatibility, or release policy require:

1. a documented problem and evidence;
2. compatibility and security analysis;
3. a reviewable Change Set when required by the evolution specification;
4. passing validation and migration planning;
5. explicit maintainer approval.

Consensus is preferred. When consensus cannot be reached, the maintainer records the decision and rationale. Rejected proposals may be revised with new evidence.

## Maintainer changes

New maintainers are selected based on sustained, constructive contributions, sound security judgment, and demonstrated understanding of the product's source-of-truth and ownership rules. Maintainer additions or removals must be documented publicly unless security or privacy requires a limited record.

## Releases

Releases follow semantic versioning. Release candidates must be built from reviewed source, pass Linux and Windows gates, include checksums, and preserve generated-asset reproducibility. Tagging, GitHub Release creation, and publication remain explicit maintainer actions; CI does not publish automatically.

## Amendments

Governance changes use the same pull-request review process and require maintainer approval. Significant changes should remain open long enough for community feedback unless an urgent security issue requires faster action.
