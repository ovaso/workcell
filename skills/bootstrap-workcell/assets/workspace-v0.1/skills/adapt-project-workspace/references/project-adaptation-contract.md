# Project Adaptation Contract V0.1

## Contents

- Evidence model
- Reusable plugin versus local instance
- Candidate project plugin shape
- Required validation
- Project instance minimum

## Evidence model

Do not generate a project plugin from questions alone. Require both user intent and current local evidence for claims that can be checked in code, Git, or configuration.

Keep these layers separate:

| Layer | Examples |
|---|---|
| Facts | repository root, configured remote, manifest file, current branch, test source set |
| Inferences | module dependency order, likely release order, generated-code boundary |
| Policies | allowed merge direction, remote-action prohibition, mandatory test gate |
| Unresolved questions | remote default branch freshness, undocumented release owner, conflicting build command |

## Reusable plugin versus local instance

Put stable, shareable project behavior in `project/plugin/project-plugin.json`. Put absolute paths, current Git status, active environment bindings, and endpoint references in the local project instance.

Never place credentials or environment values in either artifact. Use variable-name or secret-provider references.

## Candidate project plugin shape

```json
{
  "schema_version": "0.1",
  "plugin": {
    "id": "example-project",
    "display_name": "Example Project",
    "version": "0.1.0",
    "api_version": "0.1",
    "repository_model": "multi"
  },
  "repositories": [
    {
      "id": "api",
      "path": "repositories/api",
      "default_branch": "main"
    }
  ],
  "modules": [
    {
      "id": "api-service",
      "repository": "api",
      "path": ".",
      "role": "edit",
      "technology_adapters": ["git", "java", "maven"]
    }
  ],
  "workflows": {
    "build": [
      {
        "id": "api-build",
        "working_directory": "repositories/api",
        "argv": ["mvn", "-DskipTests", "package"]
      }
    ],
    "test": [],
    "verify": [],
    "review": [],
    "release": [],
    "rollback": [],
    "close": []
  },
  "risk_areas": [],
  "knowledge": [],
  "capabilities": {"enabled": []},
  "facts": [],
  "inferences": [],
  "policies": [],
  "unresolved_questions": []
}
```

Use relative logical paths in the reusable plugin. The project instance binds those paths to the host.

## Required validation

- Require lowercase hyphenated IDs.
- Require unique repository, module, workflow, fact, inference, policy, risk, and question IDs within their collections.
- Require repository references to exist.
- Allow only `edit`, `verify`, and `reference` module roles.
- Reject absolute paths and `..` traversal in plugin paths.
- Represent commands as `argv` arrays, not shell strings.
- Require every inference to cite fact IDs.
- Require policies to identify a confirmed policy source.
- Reject credential-like keys and credential-bearing URLs.
- Preserve unresolved conflicts instead of selecting a convenient value.

## Project instance minimum

Record separately:

```text
project plugin ID and version
local repository IDs and absolute paths
configured remote names and sanitized references
current branch and dirty state
locally observed default-branch references
active environment snapshot ID
mirror and isolated-workspace bindings
observation time and context
```

Remote freshness, ahead/behind, and endpoint reachability are runtime facts with expiry. Do not copy them into the reusable plugin.
