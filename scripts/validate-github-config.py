#!/usr/bin/env python3
"""Validate GitHub community, automation, security, and release configuration."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path


REQUIRED_PATHS = (
    "LICENSE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "SUPPORT.md",
    "GOVERNANCE.md",
    ".github/CODEOWNERS",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/documentation.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/dependabot.yml",
    ".github/release.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/dependency-review.yml",
    ".github/workflows/release-candidate.yml",
)
ACTION_REFERENCE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_./-]+)?@[0-9a-f]{40}$")


def read_text(path: Path, errors: list[str]) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{path}: cannot read UTF-8 text: {exc}")
        return ""
    if not text.strip():
        errors.append(f"{path}: file must not be empty")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "\t" in line:
            errors.append(f"{path}:{line_number}: tabs are not allowed")
        if line.rstrip() != line:
            errors.append(f"{path}:{line_number}: trailing whitespace is not allowed")
    return text


def action_references(text: str) -> list[str]:
    return re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", text, re.MULTILINE)


def validate_workflow(path: Path) -> list[str]:
    errors: list[str] = []
    text = read_text(path, errors)
    if not text:
        return errors

    for field in ("name:", "on:", "permissions:"):
        if re.search(rf"^{re.escape(field)}", text, re.MULTILINE) is None:
            errors.append(f"{path}: missing top-level {field}")
    if "pull_request_target:" in text:
        errors.append(f"{path}: pull_request_target is prohibited")
    if re.search(r"^\s*contents:\s*write\s*$", text, re.MULTILINE):
        errors.append(f"{path}: contents write permission is prohibited")
    if re.search(r"^permissions:\s*write-all\s*$", text, re.MULTILINE):
        errors.append(f"{path}: write-all permission is prohibited")
    if re.search(r"^\s*contents:\s*read\s*$", text, re.MULTILINE) is None:
        errors.append(f"{path}: workflows must declare contents: read")

    for reference in action_references(text):
        if reference.startswith("./"):
            continue
        if ACTION_REFERENCE.fullmatch(reference) is None:
            errors.append(f"{path}: action must be pinned to a full commit SHA: {reference}")

    if path.name != "codeql.yml" and re.search(r"^\s*[a-z-]+:\s*write\s*$", text, re.MULTILINE):
        errors.append(f"{path}: write permission is allowed only in the CodeQL workflow")

    if path.name == "ci.yml":
        for required in ("ubuntu-latest", "windows-latest", "tests/run.sh", "tests/run.ps1"):
            if required not in text:
                errors.append(f"{path}: CI matrix is missing {required}")
    elif path.name == "codeql.yml":
        for required in ("security-events: write", "javascript-typescript", "python"):
            if required not in text:
                errors.append(f"{path}: CodeQL workflow is missing {required}")
    elif path.name == "dependency-review.yml":
        if re.search(r"^\s{2}pull_request:\s*$", text, re.MULTILINE) is None:
            errors.append(f"{path}: dependency review must run for pull requests")
    elif path.name == "release-candidate.yml":
        if "workflow_dispatch:" not in text:
            errors.append(f"{path}: release candidates must be manually dispatched")
        if re.search(r"^\s{2}(?:push|release):\s*$", text, re.MULTILINE):
            errors.append(f"{path}: release candidates must not run on push or release events")
        if "actions/upload-artifact" not in text:
            errors.append(f"{path}: release candidates must upload an artifact")

    return errors


def validate_product_metadata(root: Path) -> list[str]:
    errors: list[str] = []
    product_file = root / "product.toml"
    try:
        document = tomllib.loads(product_file.read_text(encoding="utf-8"))
        product = document["product"]
        release = document["release"]
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError) as exc:
        return [f"{product_file}: cannot read [product] metadata: {exc}"]

    expected = {
        "status": "stable",
        "license": "MIT",
        "cross_host_platform_bootstrap": True,
    }
    for key, value in expected.items():
        if product.get(key) != value:
            errors.append(f"{product_file}: product.{key} must be {value!r}")
    profiles = product.get("bootstrap_host_profiles")
    if profiles != ["posix-sh-v0.1", "powershell-v0.1"]:
        errors.append(
            f"{product_file}: product.bootstrap_host_profiles must declare POSIX and PowerShell"
        )
    if release.get("canonical_repository") != "https://github.com/ovaso/workcell":
        errors.append(
            f"{product_file}: release.canonical_repository must be "
            "'https://github.com/ovaso/workcell'"
        )
    return errors


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_PATHS:
        path = root / relative_path
        if not path.is_file():
            errors.append(f"missing required repository file: {relative_path}")
            continue
        read_text(path, errors)

    license_file = root / "LICENSE"
    if license_file.is_file():
        license_text = license_file.read_text(encoding="utf-8")
        for required in ("MIT License", "Permission is hereby granted", "THE SOFTWARE IS PROVIDED \"AS IS\""):
            if required not in license_text:
                errors.append(f"{license_file}: incomplete MIT license text")

    issue_forms = root / ".github/ISSUE_TEMPLATE"
    for name in ("bug_report.yml", "feature_request.yml", "documentation.yml"):
        path = issue_forms / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for field in ("name:", "description:", "body:"):
            if re.search(rf"^{re.escape(field)}", text, re.MULTILINE) is None:
                errors.append(f"{path}: issue form is missing {field}")
    config_file = issue_forms / "config.yml"
    if config_file.is_file() and "blank_issues_enabled: false" not in config_file.read_text(encoding="utf-8"):
        errors.append(f"{config_file}: blank issues must be disabled")

    dependabot_file = root / ".github/dependabot.yml"
    if dependabot_file.is_file():
        dependabot = dependabot_file.read_text(encoding="utf-8")
        required_values = {
            "package-ecosystem": "github-actions",
            "directory": "/",
            "interval": "weekly",
        }
        for key, value in required_values.items():
            pattern = rf"^\s*(?:-\s*)?{re.escape(key)}:\s*['\"]?{re.escape(value)}['\"]?\s*$"
            if re.search(pattern, dependabot, re.MULTILINE) is None:
                errors.append(f"{dependabot_file}: missing {key}: {value}")

    for path in sorted((root / ".github/workflows").glob("*.yml")):
        errors.extend(validate_workflow(path))

    errors.extend(validate_product_metadata(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root (defaults to this script's repository)",
    )
    args = parser.parse_args()
    errors = validate_repository(args.root.resolve())
    if errors:
        for error in errors:
            print(f"GitHub configuration error: {error}", file=sys.stderr)
        return 1
    print("GitHub repository configuration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
