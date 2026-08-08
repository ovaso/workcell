#!/usr/bin/env python3
"""Implement the dependency-free JSON Schema subset required by Workspace V0.1."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any


SUPPORTED_TYPES = {"null", "boolean", "object", "array", "number", "integer", "string"}
SUPPORTED_KEYWORDS = {
    "$schema",
    "$id",
    "$defs",
    "$ref",
    "$comment",
    "title",
    "description",
    "allOf",
    "not",
    "const",
    "enum",
    "type",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "minItems",
    "uniqueItems",
    "minLength",
    "maxLength",
    "pattern",
    "format",
    "propertyNames",
    "minimum",
}
DATE_TIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)


@dataclass(frozen=True)
class SchemaDefinitionIssue:
    """Represent a bundled schema outside the supported V0.1 subset."""

    schema_path: str
    message: str


@dataclass(frozen=True)
class SchemaViolation:
    """Represent one deterministic instance violation against a schema."""

    instance_path: str
    schema_path: str
    message: str


class JsonSchemaSubsetValidator:
    """Validate the product's V0.1 subset without silently ignoring constraints."""

    def __init__(self, schema: Any) -> None:
        """Retain the root schema for local JSON Pointer reference resolution."""

        self.schema = schema

    def inspect_schema(self) -> list[SchemaDefinitionIssue]:
        """Check schema structure, keyword parameters, and local references."""

        issues: list[SchemaDefinitionIssue] = []
        self._inspect_schema_node(self.schema, "#", issues, set())
        return issues

    def validate(self, instance: Any) -> list[SchemaViolation]:
        """Validate a JSON instance with the checked root schema."""

        violations: list[SchemaViolation] = []
        self._validate_node(instance, self.schema, "$", "#", violations, set())
        return violations

    def _inspect_schema_node(
        self,
        schema: Any,
        schema_path: str,
        issues: list[SchemaDefinitionIssue],
        visited: set[int],
    ) -> None:
        """Recursively check one schema node and its child schemas."""

        if isinstance(schema, bool):
            return
        if not isinstance(schema, dict):
            issues.append(SchemaDefinitionIssue(schema_path, "Schema node must be an object or boolean"))
            return
        schema_identity = id(schema)
        if schema_identity in visited:
            return
        visited.add(schema_identity)

        for keyword in schema:
            if keyword not in SUPPORTED_KEYWORDS:
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, keyword), f"Unsupported schema keyword: {keyword}"))

        self._inspect_metadata(schema, schema_path, issues)
        self._inspect_ref(schema, schema_path, issues, visited)
        self._inspect_type(schema, schema_path, issues)
        self._inspect_scalar_keywords(schema, schema_path, issues)

        definitions = schema.get("$defs")
        if definitions is not None:
            if not isinstance(definitions, dict):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "$defs"), "$defs must be an object"))
            else:
                for name, child in definitions.items():
                    self._inspect_schema_node(child, append_pointer(append_pointer(schema_path, "$defs"), name), issues, visited)

        properties = schema.get("properties")
        if properties is not None:
            if not isinstance(properties, dict):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "properties"), "properties must be an object"))
            else:
                for name, child in properties.items():
                    self._inspect_schema_node(child, append_pointer(append_pointer(schema_path, "properties"), name), issues, visited)

        for keyword in ("additionalProperties", "items", "not", "propertyNames"):
            if keyword not in schema:
                continue
            child = schema[keyword]
            if keyword == "additionalProperties" and isinstance(child, bool):
                continue
            self._inspect_schema_node(child, append_pointer(schema_path, keyword), issues, visited)

        all_of = schema.get("allOf")
        if all_of is not None:
            if not isinstance(all_of, list) or not all_of:
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "allOf"), "allOf must be a non-empty array of schemas"))
            else:
                for index, child in enumerate(all_of):
                    self._inspect_schema_node(child, append_pointer(append_pointer(schema_path, "allOf"), str(index)), issues, visited)

    def _inspect_metadata(
        self, schema: dict[str, Any], schema_path: str, issues: list[SchemaDefinitionIssue]
    ) -> None:
        """Check string metadata accepted by V0.1."""

        for keyword in ("$schema", "$id", "$comment", "title", "description"):
            if keyword in schema and not isinstance(schema[keyword], str):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, keyword), f"{keyword} must be a string"))

    def _inspect_ref(
        self,
        schema: dict[str, Any],
        schema_path: str,
        issues: list[SchemaDefinitionIssue],
        visited: set[int],
    ) -> None:
        """Check that `$ref` uses only resolvable local JSON Pointers."""

        if "$ref" not in schema:
            return
        reference = schema["$ref"]
        if not isinstance(reference, str):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "$ref"), "$ref must be a string"))
            return
        try:
            target, target_path = self._resolve_ref(reference)
        except ValueError as exc:
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "$ref"), str(exc)))
            return
        if not isinstance(target, (dict, bool)):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "$ref"), "$ref target is not a schema node"))
            return
        self._inspect_schema_node(target, target_path, issues, visited)

    def _inspect_type(
        self, schema: dict[str, Any], schema_path: str, issues: list[SchemaDefinitionIssue]
    ) -> None:
        """Check that type uses supported, non-duplicate JSON types."""

        if "type" not in schema:
            return
        value = schema["type"]
        values = [value] if isinstance(value, str) else value
        if not isinstance(values, list) or not values or not all(isinstance(item, str) for item in values):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "type"), "type must be a string or non-empty string array"))
            return
        if len(values) != len(set(values)):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "type"), "type array must not contain duplicates"))
        unsupported = sorted(set(values) - SUPPORTED_TYPES)
        if unsupported:
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "type"), f"Unsupported JSON type: {', '.join(unsupported)}"))

    def _inspect_scalar_keywords(
        self, schema: dict[str, Any], schema_path: str, issues: list[SchemaDefinitionIssue]
    ) -> None:
        """Check parameter types for array, string, object, and numeric constraints."""

        required = schema.get("required")
        if required is not None:
            if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "required"), "required must be an array of strings"))
            elif len(required) != len(set(required)):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "required"), "required must not contain duplicate fields"))

        enum = schema.get("enum")
        if enum is not None:
            if not isinstance(enum, list) or not enum:
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "enum"), "enum must be a non-empty array"))
            elif has_duplicate_json_values(enum):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "enum"), "enum must not contain JSON-equivalent values"))

        for keyword in ("minItems", "minLength", "maxLength"):
            if keyword in schema and not is_non_negative_integer(schema[keyword]):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, keyword), f"{keyword} must be a non-negative integer"))
        if is_non_negative_integer(schema.get("minLength")) and is_non_negative_integer(schema.get("maxLength")):
            if schema["maxLength"] < schema["minLength"]:
                issues.append(SchemaDefinitionIssue(schema_path, "maxLength must not be less than minLength"))
        if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "uniqueItems"), "uniqueItems must be a boolean"))
        if "pattern" in schema:
            pattern = schema["pattern"]
            if not isinstance(pattern, str):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "pattern"), "pattern must be a string"))
            else:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "pattern"), f"pattern cannot be compiled: {exc}"))
        if "format" in schema and schema["format"] != "date-time":
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "format"), "V0.1 supports only date-time format"))
        if "minimum" in schema and not is_json_number(schema["minimum"]):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "minimum"), "minimum must be a finite number"))

    def _resolve_ref(self, reference: str) -> tuple[Any, str]:
        """Resolve a JSON Pointer reference limited to the current schema document."""

        if reference == "#":
            return self.schema, "#"
        if not reference.startswith("#/"):
            raise ValueError(f"V0.1 supports only local JSON Pointer references: {reference!r}")
        current = self.schema
        display_path = "#"
        for raw_token in reference[2:].split("/"):
            token = decode_pointer_token(raw_token)
            display_path = append_pointer(display_path, token)
            if isinstance(current, dict) and token in current:
                current = current[token]
            elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
                current = current[int(token)]
            else:
                raise ValueError(f"Unable to resolve local reference: {reference!r}")
        return current, display_path

    def _validate_node(
        self,
        instance: Any,
        schema: Any,
        instance_path: str,
        schema_path: str,
        violations: list[SchemaViolation],
        active_pairs: set[tuple[int, int]],
    ) -> None:
        """Apply supported constraints recursively and prevent non-consuming cycles."""

        if isinstance(schema, bool):
            if not schema:
                violations.append(SchemaViolation(instance_path, schema_path, "Boolean schema false rejects this value"))
            return
        if not isinstance(schema, dict):
            return

        pair = (id(schema), id(instance))
        if pair in active_pairs:
            return
        active_pairs.add(pair)
        try:
            self._validate_composition(instance, schema, instance_path, schema_path, violations, active_pairs)
            self._validate_value(instance, schema, instance_path, schema_path, violations, active_pairs)
        finally:
            active_pairs.remove(pair)

    def _validate_composition(
        self,
        instance: Any,
        schema: dict[str, Any],
        instance_path: str,
        schema_path: str,
        violations: list[SchemaViolation],
        active_pairs: set[tuple[int, int]],
    ) -> None:
        """Apply `$ref`, `allOf`, and `not` composition constraints."""

        if "$ref" in schema and isinstance(schema["$ref"], str):
            target, target_path = self._resolve_ref(schema["$ref"])
            self._validate_node(instance, target, instance_path, target_path, violations, active_pairs)
        all_of = schema.get("allOf")
        if isinstance(all_of, list):
            for index, child in enumerate(all_of):
                self._validate_node(
                    instance,
                    child,
                    instance_path,
                    append_pointer(append_pointer(schema_path, "allOf"), str(index)),
                    violations,
                    active_pairs,
                )
        if "not" in schema:
            nested: list[SchemaViolation] = []
            self._validate_node(
                instance,
                schema["not"],
                instance_path,
                append_pointer(schema_path, "not"),
                nested,
                set(active_pairs),
            )
            if not nested:
                violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "not"), "Value matches the schema prohibited by not"))

    def _validate_value(
        self,
        instance: Any,
        schema: dict[str, Any],
        instance_path: str,
        schema_path: str,
        violations: list[SchemaViolation],
        active_pairs: set[tuple[int, int]],
    ) -> None:
        """Apply enum, type, and instance-type-specific constraints."""

        if "const" in schema and not json_values_equal(instance, schema["const"]):
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "const"), "Value is not equal to const"))
        if isinstance(schema.get("enum"), list) and not any(json_values_equal(instance, value) for value in schema["enum"]):
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "enum"), "Value is not in enum"))

        expected_types = schema.get("type")
        if expected_types is not None:
            type_names = [expected_types] if isinstance(expected_types, str) else expected_types
            if isinstance(type_names, list) and not any(instance_matches_type(instance, name) for name in type_names):
                violations.append(
                    SchemaViolation(instance_path, append_pointer(schema_path, "type"), f"Instance type does not match {type_names!r}")
                )
                return

        if isinstance(instance, dict):
            self._validate_object(instance, schema, instance_path, schema_path, violations, active_pairs)
        elif isinstance(instance, list):
            self._validate_array(instance, schema, instance_path, schema_path, violations, active_pairs)
        elif isinstance(instance, str):
            self._validate_string(instance, schema, instance_path, schema_path, violations)
        elif is_json_number(instance):
            self._validate_number(instance, schema, instance_path, schema_path, violations)

    def _validate_object(
        self,
        instance: dict[str, Any],
        schema: dict[str, Any],
        instance_path: str,
        schema_path: str,
        violations: list[SchemaViolation],
        active_pairs: set[tuple[int, int]],
    ) -> None:
        """Validate required fields, property names, known properties, and extras."""

        required = schema.get("required")
        if isinstance(required, list):
            for name in required:
                if name not in instance:
                    violations.append(
                        SchemaViolation(instance_path, append_pointer(schema_path, "required"), f"Missing required property {name!r}")
                    )
        property_names = schema.get("propertyNames")
        if property_names is not None:
            for name in instance:
                self._validate_node(
                    name,
                    property_names,
                    append_pointer(instance_path, name),
                    append_pointer(schema_path, "propertyNames"),
                    violations,
                    active_pairs,
                )
        properties = schema.get("properties")
        known_properties = properties if isinstance(properties, dict) else {}
        for name, child_schema in known_properties.items():
            if name in instance:
                self._validate_node(
                    instance[name],
                    child_schema,
                    append_pointer(instance_path, name),
                    append_pointer(append_pointer(schema_path, "properties"), name),
                    violations,
                    active_pairs,
                )
        additional = schema.get("additionalProperties", True)
        for name, value in instance.items():
            if name in known_properties:
                continue
            if additional is False:
                violations.append(
                    SchemaViolation(
                        append_pointer(instance_path, name),
                        append_pointer(schema_path, "additionalProperties"),
                        f"Additional property {name!r} is not allowed",
                    )
                )
            elif isinstance(additional, (dict, bool)) and additional is not True:
                self._validate_node(
                    value,
                    additional,
                    append_pointer(instance_path, name),
                    append_pointer(schema_path, "additionalProperties"),
                    violations,
                    active_pairs,
                )

    def _validate_array(
        self,
        instance: list[Any],
        schema: dict[str, Any],
        instance_path: str,
        schema_path: str,
        violations: list[SchemaViolation],
        active_pairs: set[tuple[int, int]],
    ) -> None:
        """Validate array minimum length, uniqueness, and item schemas."""

        minimum = schema.get("minItems")
        if is_non_negative_integer(minimum) and len(instance) < minimum:
            violations.append(
                SchemaViolation(instance_path, append_pointer(schema_path, "minItems"), f"Array has fewer than {minimum} items")
            )
        if schema.get("uniqueItems") is True and has_duplicate_json_values(instance):
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "uniqueItems"), "Array contains duplicate items"))
        if "items" in schema:
            for index, value in enumerate(instance):
                self._validate_node(
                    value,
                    schema["items"],
                    append_pointer(instance_path, str(index)),
                    append_pointer(schema_path, "items"),
                    violations,
                    active_pairs,
                )

    def _validate_string(
        self,
        instance: str,
        schema: dict[str, Any],
        instance_path: str,
        schema_path: str,
        violations: list[SchemaViolation],
    ) -> None:
        """Validate string length, pattern, and RFC 3339 time format."""

        minimum = schema.get("minLength")
        maximum = schema.get("maxLength")
        if is_non_negative_integer(minimum) and len(instance) < minimum:
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "minLength"), f"String is shorter than {minimum}"))
        if is_non_negative_integer(maximum) and len(instance) > maximum:
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "maxLength"), f"String is longer than {maximum}"))
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, instance) is None:
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "pattern"), "String does not match pattern"))
        if schema.get("format") == "date-time" and not is_rfc3339_date_time(instance):
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "format"), "String is not a valid RFC 3339 date-time"))

    def _validate_number(
        self,
        instance: int | float,
        schema: dict[str, Any],
        instance_path: str,
        schema_path: str,
        violations: list[SchemaViolation],
    ) -> None:
        """Validate the lower bound of a finite JSON number."""

        minimum = schema.get("minimum")
        if is_json_number(minimum) and instance < minimum:
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "minimum"), f"Number is less than {minimum}"))


def append_pointer(base: str, token: str) -> str:
    """Append a property or index safely to a display JSON Pointer."""

    escaped = str(token).replace("~", "~0").replace("/", "~1")
    return f"{base}/{escaped}"


def decode_pointer_token(token: str) -> str:
    """Decode a JSON Pointer token strictly and reject unknown tilde escapes."""

    if re.search(r"~(?:[^01]|$)", token):
        raise ValueError(f"JSON Pointer contains an invalid escape: {token!r}")
    return token.replace("~1", "/").replace("~0", "~")


def is_non_negative_integer(value: Any) -> bool:
    """Return whether a value is a non-boolean non-negative integer."""

    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def is_json_number(value: Any) -> bool:
    """Return whether a value is a finite number representable in JSON."""

    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def instance_matches_type(value: Any, type_name: str) -> bool:
    """Determine instance type according to JSON Schema semantics."""

    if type_name == "null":
        return value is None
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "number":
        return is_json_number(value)
    if type_name == "integer":
        if isinstance(value, int) and not isinstance(value, bool):
            return True
        return isinstance(value, float) and math.isfinite(value) and value.is_integer()
    return False


def json_values_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without treating true and 1 as equal."""

    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if is_json_number(left) and is_json_number(right):
        return left == right
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, list) or isinstance(right, list):
        return (
            isinstance(left, list)
            and isinstance(right, list)
            and len(left) == len(right)
            and all(json_values_equal(a, b) for a, b in zip(left, right))
        )
    if isinstance(left, dict) or isinstance(right, dict):
        return (
            isinstance(left, dict)
            and isinstance(right, dict)
            and left.keys() == right.keys()
            and all(json_values_equal(left[key], right[key]) for key in left)
        )
    return left == right


def has_duplicate_json_values(values: list[Any]) -> bool:
    """Detect two JSON-semantically equal values in an array."""

    for index, value in enumerate(values):
        if any(json_values_equal(value, previous) for previous in values[:index]):
            return True
    return False


def is_rfc3339_date_time(value: str) -> bool:
    """Validate the conventional RFC 3339 date-time form used by V0.1."""

    if DATE_TIME_PATTERN.fullmatch(value) is None:
        return False
    normalized = value[:10] + "T" + value[11:]
    if normalized.endswith(("Z", "z")):
        normalized = normalized[:-1] + "+00:00"
    if normalized[17:19] == "60":
        normalized = normalized[:17] + "59" + normalized[19:]
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def reject_non_json_constant(value: str) -> None:
    """Reject NaN and Infinity accepted by Python's JSON parser by default."""

    raise ValueError(f"JSON contains a non-standard numeric constant: {value}")


def reject_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate keys that make JSON object interpretation ambiguous."""

    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"JSON object contains a duplicate key: {key!r}")
        document[key] = value
    return document


def load_json_document(text: str) -> Any:
    """Parse JSON strictly, rejecting duplicate keys and non-finite constants."""

    return json.loads(
        text,
        object_pairs_hook=reject_duplicate_object_keys,
        parse_constant=reject_non_json_constant,
    )
