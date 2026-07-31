"""为 Skill Creator quick_validate 提供最小 YAML frontmatter 兼容层。"""

from __future__ import annotations

import json


class YAMLError(ValueError):
    """表示当前简单 frontmatter 无法解析。"""


def safe_load(source: str) -> dict[str, object]:
    """解析本仓库只含单行标量的 Skill frontmatter。"""

    result: dict[str, object] = {}
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise YAMLError(f"unsupported YAML line: {raw_line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            raise YAMLError("empty YAML key")
        if value.startswith(('"', "'")):
            try:
                if value.startswith('"'):
                    parsed: object = json.loads(value)
                elif value.endswith("'"):
                    parsed = value[1:-1].replace("''", "'")
                else:
                    raise YAMLError(f"unterminated quoted value: {raw_line}")
            except json.JSONDecodeError as error:
                raise YAMLError(str(error)) from error
        elif value in {"true", "false"}:
            parsed = value == "true"
        else:
            parsed = value
        result[key] = parsed
    return result
