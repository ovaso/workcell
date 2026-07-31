#!/usr/bin/env python3
"""实现标准工作区 V0.1 所需的无依赖 JSON Schema 子集。"""

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
    """表示随包 Schema 自身不属于受支持 V0.1 子集。"""

    schema_path: str
    message: str


@dataclass(frozen=True)
class SchemaViolation:
    """表示实例相对 Schema 的一条确定性违例。"""

    instance_path: str
    schema_path: str
    message: str


class JsonSchemaSubsetValidator:
    """校验本产品 V0.1 Schema 子集，不静默忽略未知约束。"""

    def __init__(self, schema: Any) -> None:
        """保存根 Schema，供本地 JSON Pointer 引用解析。"""

        self.schema = schema

    def inspect_schema(self) -> list[SchemaDefinitionIssue]:
        """检查 Schema 结构、关键字参数与本地引用是否受支持。"""

        issues: list[SchemaDefinitionIssue] = []
        self._inspect_schema_node(self.schema, "#", issues, set())
        return issues

    def validate(self, instance: Any) -> list[SchemaViolation]:
        """使用已检查的根 Schema 校验一个 JSON 实例。"""

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
        """递归检查单个 Schema 节点及其子 Schema。"""

        if isinstance(schema, bool):
            return
        if not isinstance(schema, dict):
            issues.append(SchemaDefinitionIssue(schema_path, "Schema 节点必须是对象或布尔值"))
            return
        schema_identity = id(schema)
        if schema_identity in visited:
            return
        visited.add(schema_identity)

        for keyword in schema:
            if keyword not in SUPPORTED_KEYWORDS:
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, keyword), f"不支持的 Schema 关键字：{keyword}"))

        self._inspect_metadata(schema, schema_path, issues)
        self._inspect_ref(schema, schema_path, issues, visited)
        self._inspect_type(schema, schema_path, issues)
        self._inspect_scalar_keywords(schema, schema_path, issues)

        definitions = schema.get("$defs")
        if definitions is not None:
            if not isinstance(definitions, dict):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "$defs"), "$defs 必须是对象"))
            else:
                for name, child in definitions.items():
                    self._inspect_schema_node(child, append_pointer(append_pointer(schema_path, "$defs"), name), issues, visited)

        properties = schema.get("properties")
        if properties is not None:
            if not isinstance(properties, dict):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "properties"), "properties 必须是对象"))
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
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "allOf"), "allOf 必须是非空 Schema 数组"))
            else:
                for index, child in enumerate(all_of):
                    self._inspect_schema_node(child, append_pointer(append_pointer(schema_path, "allOf"), str(index)), issues, visited)

    def _inspect_metadata(
        self, schema: dict[str, Any], schema_path: str, issues: list[SchemaDefinitionIssue]
    ) -> None:
        """检查 V0.1 接受的字符串元数据。"""

        for keyword in ("$schema", "$id", "$comment", "title", "description"):
            if keyword in schema and not isinstance(schema[keyword], str):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, keyword), f"{keyword} 必须是字符串"))

    def _inspect_ref(
        self,
        schema: dict[str, Any],
        schema_path: str,
        issues: list[SchemaDefinitionIssue],
        visited: set[int],
    ) -> None:
        """检查 `$ref` 仅使用可解析的本地 JSON Pointer。"""

        if "$ref" not in schema:
            return
        reference = schema["$ref"]
        if not isinstance(reference, str):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "$ref"), "$ref 必须是字符串"))
            return
        try:
            target, target_path = self._resolve_ref(reference)
        except ValueError as exc:
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "$ref"), str(exc)))
            return
        if not isinstance(target, (dict, bool)):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "$ref"), "$ref 目标不是 Schema 节点"))
            return
        self._inspect_schema_node(target, target_path, issues, visited)

    def _inspect_type(
        self, schema: dict[str, Any], schema_path: str, issues: list[SchemaDefinitionIssue]
    ) -> None:
        """检查 type 使用受支持且不重复的 JSON 类型。"""

        if "type" not in schema:
            return
        value = schema["type"]
        values = [value] if isinstance(value, str) else value
        if not isinstance(values, list) or not values or not all(isinstance(item, str) for item in values):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "type"), "type 必须是字符串或非空字符串数组"))
            return
        if len(values) != len(set(values)):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "type"), "type 数组不能包含重复值"))
        unsupported = sorted(set(values) - SUPPORTED_TYPES)
        if unsupported:
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "type"), f"不支持的 JSON 类型：{', '.join(unsupported)}"))

    def _inspect_scalar_keywords(
        self, schema: dict[str, Any], schema_path: str, issues: list[SchemaDefinitionIssue]
    ) -> None:
        """检查数组、字符串、对象和数值约束自身的参数类型。"""

        required = schema.get("required")
        if required is not None:
            if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "required"), "required 必须是字符串数组"))
            elif len(required) != len(set(required)):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "required"), "required 不能包含重复字段"))

        enum = schema.get("enum")
        if enum is not None:
            if not isinstance(enum, list) or not enum:
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "enum"), "enum 必须是非空数组"))
            elif has_duplicate_json_values(enum):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "enum"), "enum 不能包含 JSON 等价值"))

        for keyword in ("minItems", "minLength", "maxLength"):
            if keyword in schema and not is_non_negative_integer(schema[keyword]):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, keyword), f"{keyword} 必须是非负整数"))
        if is_non_negative_integer(schema.get("minLength")) and is_non_negative_integer(schema.get("maxLength")):
            if schema["maxLength"] < schema["minLength"]:
                issues.append(SchemaDefinitionIssue(schema_path, "maxLength 不能小于 minLength"))
        if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "uniqueItems"), "uniqueItems 必须是布尔值"))
        if "pattern" in schema:
            pattern = schema["pattern"]
            if not isinstance(pattern, str):
                issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "pattern"), "pattern 必须是字符串"))
            else:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "pattern"), f"pattern 无法编译：{exc}"))
        if "format" in schema and schema["format"] != "date-time":
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "format"), "V0.1 仅支持 date-time format"))
        if "minimum" in schema and not is_json_number(schema["minimum"]):
            issues.append(SchemaDefinitionIssue(append_pointer(schema_path, "minimum"), "minimum 必须是有限数字"))

    def _resolve_ref(self, reference: str) -> tuple[Any, str]:
        """解析仅限当前 Schema 文档的 JSON Pointer 引用。"""

        if reference == "#":
            return self.schema, "#"
        if not reference.startswith("#/"):
            raise ValueError(f"V0.1 只支持本地 JSON Pointer 引用：{reference!r}")
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
                raise ValueError(f"无法解析本地引用：{reference!r}")
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
        """递归应用受支持约束，并防止不消耗实例的引用环。"""

        if isinstance(schema, bool):
            if not schema:
                violations.append(SchemaViolation(instance_path, schema_path, "布尔 Schema false 拒绝该值"))
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
        """应用 `$ref`、`allOf` 与 `not` 组合约束。"""

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
                violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "not"), "值命中了 not 禁止的 Schema"))

    def _validate_value(
        self,
        instance: Any,
        schema: dict[str, Any],
        instance_path: str,
        schema_path: str,
        violations: list[SchemaViolation],
        active_pairs: set[tuple[int, int]],
    ) -> None:
        """应用枚举、类型及按实例类型生效的约束。"""

        if "const" in schema and not json_values_equal(instance, schema["const"]):
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "const"), "值不等于 const"))
        if isinstance(schema.get("enum"), list) and not any(json_values_equal(instance, value) for value in schema["enum"]):
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "enum"), "值不属于 enum"))

        expected_types = schema.get("type")
        if expected_types is not None:
            type_names = [expected_types] if isinstance(expected_types, str) else expected_types
            if isinstance(type_names, list) and not any(instance_matches_type(instance, name) for name in type_names):
                violations.append(
                    SchemaViolation(instance_path, append_pointer(schema_path, "type"), f"实例类型不符合 {type_names!r}")
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
        """验证对象必填字段、属性名、已知属性和额外属性。"""

        required = schema.get("required")
        if isinstance(required, list):
            for name in required:
                if name not in instance:
                    violations.append(
                        SchemaViolation(instance_path, append_pointer(schema_path, "required"), f"缺少必填属性 {name!r}")
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
                        f"不允许额外属性 {name!r}",
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
        """验证数组最小长度、唯一性和元素 Schema。"""

        minimum = schema.get("minItems")
        if is_non_negative_integer(minimum) and len(instance) < minimum:
            violations.append(
                SchemaViolation(instance_path, append_pointer(schema_path, "minItems"), f"数组元素数少于 {minimum}")
            )
        if schema.get("uniqueItems") is True and has_duplicate_json_values(instance):
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "uniqueItems"), "数组包含重复项"))
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
        """验证字符串长度、正则和 RFC 3339 时间格式。"""

        minimum = schema.get("minLength")
        maximum = schema.get("maxLength")
        if is_non_negative_integer(minimum) and len(instance) < minimum:
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "minLength"), f"字符串短于 {minimum}"))
        if is_non_negative_integer(maximum) and len(instance) > maximum:
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "maxLength"), f"字符串长于 {maximum}"))
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, instance) is None:
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "pattern"), "字符串不匹配 pattern"))
        if schema.get("format") == "date-time" and not is_rfc3339_date_time(instance):
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "format"), "字符串不是有效 RFC 3339 date-time"))

    def _validate_number(
        self,
        instance: int | float,
        schema: dict[str, Any],
        instance_path: str,
        schema_path: str,
        violations: list[SchemaViolation],
    ) -> None:
        """验证有限 JSON 数字的下界。"""

        minimum = schema.get("minimum")
        if is_json_number(minimum) and instance < minimum:
            violations.append(SchemaViolation(instance_path, append_pointer(schema_path, "minimum"), f"数值小于 {minimum}"))


def append_pointer(base: str, token: str) -> str:
    """把属性或索引安全追加到展示用 JSON Pointer。"""

    escaped = str(token).replace("~", "~0").replace("/", "~1")
    return f"{base}/{escaped}"


def decode_pointer_token(token: str) -> str:
    """严格解码 JSON Pointer token，拒绝未知波浪线转义。"""

    if re.search(r"~(?:[^01]|$)", token):
        raise ValueError(f"JSON Pointer 含非法转义：{token!r}")
    return token.replace("~1", "/").replace("~0", "~")


def is_non_negative_integer(value: Any) -> bool:
    """判断值是否为非布尔的非负整数。"""

    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def is_json_number(value: Any) -> bool:
    """判断值是否为 JSON 可表达的有限数字。"""

    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def instance_matches_type(value: Any, type_name: str) -> bool:
    """按 JSON Schema 语义判断实例类型。"""

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
    """按 JSON 值语义比较，避免 Python 把 true 与 1 当作相等。"""

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
    """检测数组中是否存在 JSON 语义相等的两个值。"""

    for index, value in enumerate(values):
        if any(json_values_equal(value, previous) for previous in values[:index]):
            return True
    return False


def is_rfc3339_date_time(value: str) -> bool:
    """验证 V0.1 使用的 RFC 3339 date-time 常规表示。"""

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
    """拒绝 Python JSON 解析器默认接受的 NaN 与 Infinity。"""

    raise ValueError(f"JSON 含非标准数值常量：{value}")


def reject_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """构造 JSON 对象时拒绝会造成解释歧义的重复键。"""

    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"JSON 对象包含重复键：{key!r}")
        document[key] = value
    return document


def load_json_document(text: str) -> Any:
    """严格解析 JSON 文本，不接受重复键或非有限数字常量。"""

    return json.loads(
        text,
        object_pairs_hook=reject_duplicate_object_keys,
        parse_constant=reject_non_json_constant,
    )
