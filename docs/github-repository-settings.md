# GitHub Repository Settings

Repository files cannot enforce every GitHub setting. A repository administrator should apply this checklist before public launch.

## General

- Keep `main` as the default branch.
- Enable Issues and private vulnerability reporting.
- Enable Discussions only when maintainers are prepared to moderate and support it.
- Use a concise description and topics such as `ai-workspace`, `developer-tools`, `workflow`, `skills`, and `platform-neutral`.
- Keep the repository URL in `product.toml` synchronized with the canonical GitHub repository.

## Ruleset for `main`

- Require pull requests; prohibit direct pushes except documented emergency recovery.
- Require at least one approving review and dismiss stale approvals after new commits.
- Require conversation resolution.
- Require the Linux and Windows CI checks after their exact check names appear in GitHub.
- Require CodeQL checks when code scanning is enabled.
- Block force pushes and branch deletion.
- Apply the rule to administrators unless a documented recovery procedure requires a temporary exception.

## Actions

- Set default `GITHUB_TOKEN` permissions to read-only.
- Allow GitHub-authored actions and require actions to be pinned to full commit SHAs.
- Require approval for workflows submitted from first-time external contributors.
- Do not provide repository secrets to fork pull-request workflows.

## Security

- Enable the dependency graph, Dependabot alerts, and Dependabot security updates.
- Enable secret scanning and push protection.
- Enable CodeQL default setup only if the repository does not use the checked-in advanced CodeQL workflow; do not run duplicate configurations.
- Enable private vulnerability reporting.
- Review CODEOWNERS and branch-rule bypass permissions periodically.

## Releases

- Create immutable signed tags manually after all required checks pass.
- Run the Release Candidate workflow explicitly and verify the ZIP and SHA-256 artifact.
- Create the GitHub Release only after reviewing the candidate; attach the verified archive and checksum.
- Keep automatic publication and self-update disabled until their security protocols are complete.
