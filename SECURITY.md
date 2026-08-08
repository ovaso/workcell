# Security Policy

## Supported versions

Security fixes target the current `main` branch and the latest published GitHub Release when one exists. Older drafts, tags, generated archives, forks, and modified workspace copies are not guaranteed to receive security fixes.

| Version | Supported |
| --- | --- |
| Current `main` | Yes |
| Latest published release | Yes |
| Older versions and drafts | No |

## Report a vulnerability

Do not disclose vulnerabilities, credentials, private paths, endpoint details, or exploit material in a public issue.

Use [GitHub private vulnerability reporting](https://github.com/ovaso/workcell/security/advisories/new). If that feature is unavailable, contact the maintainer privately through a contact method listed on the [maintainer's GitHub profile](https://github.com/ovaso) and share only enough information to establish a secure channel.

Include, when possible:

- affected version or commit;
- affected files and execution profile;
- impact and realistic attack conditions;
- minimal reproduction steps;
- suggested mitigation;
- whether the issue is already public.

The project aims to acknowledge a complete report within seven days and provide an initial assessment within fourteen days. These are best-effort targets, not guaranteed service levels.

## Scope

In scope are Bootstrap containment, manifest and checksum validation, ownership enforcement, upgrade safety, generated policy integrity, unsafe path handling, credential exposure, and GitHub Actions supply-chain risks.

Configuration mistakes in third-party AI platforms, unauthorized external-system access, unsupported modified copies, and social-engineering attacks outside project-controlled channels may be out of scope, but reports are still welcome when the boundary is unclear.

## Disclosure

Coordinate public disclosure with the maintainers. A fix may include a security advisory, patched release, mitigation guidance, affected-version statement, and credit to the reporter unless anonymity is requested.
