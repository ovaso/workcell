# Data Serialization Specification V0.1

## 1. Purpose

The Workcell workspace uses both TOML and JSON. Prefer TOML for small configurations maintained by people, and JSON for deeply nested data that requires strict schemas and deterministic generation. JSON Schema validates JSON directly or validates the JSON-equivalent structure produced by parsing TOML.

## 2. Format responsibilities

- TOML: workspace identity, version locks, policies, diagnostic configuration, and task manifests.
- JSON: environment-fact snapshots, project plugins, and other deeply nested deterministic data.
- JSON Schema: field, type, enum, required-property, and compatible-version constraints.
- Markdown: specifications, knowledge, plans, explanations, and reports.
- Plain-text manifests: per-path lists of immutable release files.

Dynamic state must not exist only in Markdown. Secret values must not be written in any of these formats.

## 3. TOML-to-JSON mapping

Use standard TOML parsing semantics:

- a table maps to a JSON object;
- an array maps to a JSON array;
- an array of tables maps to an array of objects;
- strings, integers, floating-point numbers, and booleans retain their corresponding JSON types;
- date-time values are validated as RFC 3339 strings at the schema layer.

Implementations must not parse complete TOML with regular expressions. Bootstrap V0.1 may use constrained readers for a small number of fixed fields, but complete validation must use a standard TOML parser.

## 4. Null values and unknown facts

TOML has no `null`. Omit optional facts that have not been established instead of inventing times, paths, endpoints, or versions. When an unknown state must be represented, use an enum explicitly defined by the schema, such as `uninitialized`, `unknown`, or `not-probed`.

An empty string is allowed only for an explicitly permitted uninitialized reference and must not represent a verified fact.

## 5. Time

Observation times use RFC 3339 with a time zone, for example:

```text
2026-07-31T16:30:00+08:00
```

Do not substitute a file modification time for a fact observation time. Refreshing facts must create a new snapshot or explicitly record a supersession relationship.

## 6. Version compatibility

Every manifest must declare its schema or API version. Readers fail closed on an unknown major version. An unknown minor version is acceptable only when the schema explicitly declares compatibility.

## 7. Deterministic output

Generators must produce stable output:

- fixed table order;
- arrays sorted by stable ID;
- UTF-8 and LF line endings;
- exactly one trailing newline;
- no host-specific absolute paths unless a file explicitly stores local workspace facts and marks them as sensitive.

These constraints reduce meaningless diffs and support hashing, Doctor checks, and upgrade previews.
