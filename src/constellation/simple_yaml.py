from __future__ import annotations

from pathlib import Path
from typing import Any


class YamlError(ValueError):
    """Raised when the small YAML subset parser cannot parse a file."""


def load_yaml(path: Path) -> dict[str, Any]:
    """Load the simple YAML subset used by Constellation scaffold files."""

    lines = _prepare_lines(path)
    if not lines:
        return {}
    value, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise YamlError(f"Unexpected content at line {lines[index][2]} in {path}")
    if not isinstance(value, dict):
        raise YamlError(f"Top-level YAML value must be a mapping in {path}")
    return value


def _prepare_lines(path: Path) -> list[tuple[int, str, int]]:
    prepared: list[tuple[int, str, int]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            raise YamlError(f"Tabs are not supported in YAML indentation at {path}:{line_number}")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        prepared.append((indent, raw_line.strip(), line_number))
    return prepared


def _parse_block(lines: list[tuple[int, str, int]], index: int, indent: int) -> tuple[Any, int]:
    if lines[index][0] != indent:
        raise YamlError(f"Expected indent {indent} at line {lines[index][2]}")
    if lines[index][1].startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines: list[tuple[int, str, int]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        current_indent, text, line_number = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise YamlError(f"Unexpected indentation at line {line_number}")
        if text.startswith("- "):
            break
        key, value = _parse_key_value(text, line_number)
        index += 1
        if value is None:
            if index < len(lines) and lines[index][0] > current_indent:
                child, index = _parse_block(lines, index, lines[index][0])
                result[key] = child
            else:
                result[key] = None
        else:
            result[key] = value
    return result, index


def _parse_list(lines: list[tuple[int, str, int]], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        current_indent, text, line_number = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise YamlError(f"Unexpected indentation at line {line_number}")
        if not text.startswith("- "):
            break

        item_text = text[2:].strip()
        index += 1
        if not item_text:
            if index < len(lines) and lines[index][0] > current_indent:
                item, index = _parse_block(lines, index, lines[index][0])
            else:
                item = None
            result.append(item)
            continue

        if ":" in item_text and not _is_quoted(item_text):
            key, value = _parse_key_value(item_text, line_number)
            item_dict: dict[str, Any] = {key: value}
            while index < len(lines) and lines[index][0] > current_indent:
                child, index = _parse_block(lines, index, lines[index][0])
                if not isinstance(child, dict):
                    raise YamlError(f"Expected mapping continuation for list item at line {line_number}")
                item_dict.update(child)
            result.append(item_dict)
        else:
            result.append(_parse_scalar(item_text))
    return result, index


def _parse_key_value(text: str, line_number: int) -> tuple[str, Any]:
    if ":" not in text:
        raise YamlError(f"Expected key/value pair at line {line_number}")
    key, raw_value = text.split(":", 1)
    key = key.strip()
    if not key:
        raise YamlError(f"Empty key at line {line_number}")
    raw_value = raw_value.strip()
    if raw_value == "":
        return key, None
    return key, _parse_scalar(raw_value)


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "None", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _is_quoted(value: str) -> bool:
    return (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'"))
