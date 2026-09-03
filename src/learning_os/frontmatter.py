"""Markdown plus YAML-frontmatter persistence.

PyYAML is used when available.  The fallback parser intentionally implements
the small, human-readable YAML subset emitted by this project so the core CLI
remains usable in a fresh Python environment without a network install.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
from typing import Any

from .errors import ValidationError


try:  # Optional enhancement; the runtime has a deterministic fallback.
    import yaml as _yaml  # type: ignore
except ImportError:  # pragma: no cover - exercised in the dependency-free env
    _yaml = None


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        raise ValidationError("Markdown record must start with YAML frontmatter delimiter ---")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValidationError("invalid frontmatter opening delimiter")
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            body = "".join(lines[index + 1 :])
            return "".join(lines[1:index]), body
    raise ValidationError("Markdown record has no closing frontmatter delimiter")


def load_markdown(path: str | Path) -> tuple[dict[str, Any], str]:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc
    frontmatter, body = split_frontmatter(text)
    data = load_yaml(frontmatter)
    if not isinstance(data, dict):
        raise ValidationError(f"frontmatter in {path} must be a mapping")
    return data, body


def dump_markdown(data: dict[str, Any], body: str = "") -> str:
    if not isinstance(data, dict):
        raise TypeError("frontmatter must be a mapping")
    normalized_body = body or ""
    if normalized_body and not normalized_body.endswith("\n"):
        normalized_body += "\n"
    return "---\n" + dump_yaml(data) + "---\n\n" + normalized_body


def write_markdown(path: str | Path, data: dict[str, Any], body: str = "") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = dump_markdown(data, body)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def load_yaml(text: str) -> Any:
    if _yaml is not None:
        try:
            value = _yaml.safe_load(text)
            return {} if value is None else value
        except Exception as exc:
            raise ValidationError(f"invalid YAML frontmatter: {exc}") from exc
    return _MiniYamlParser(text).parse()


def dump_yaml(data: dict[str, Any]) -> str:
    if _yaml is not None:
        try:
            return _yaml.safe_dump(
                data,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                indent=2,
            )
        except Exception as exc:
            raise ValidationError(f"cannot serialize YAML frontmatter: {exc}") from exc
    return _MiniYamlDumper().dump(data)


_SAFE_PLAIN = re.compile(r"^[A-Za-z0-9_./@+%][A-Za-z0-9_./@+% -]*$")


def _dump_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value)
    if text and _SAFE_PLAIN.match(text) and text.lower() not in {
        "null",
        "true",
        "false",
        "yes",
        "no",
        "on",
        "off",
        "~",
    } and not text[0] in "-?:!#{}[],&*|>'\"%@`":
        return text
    return json.dumps(text, ensure_ascii=False)


class _MiniYamlDumper:
    def dump(self, value: Any) -> str:
        lines = self._block(value, 0)
        return "\n".join(lines) + "\n"

    def _block(self, value: Any, indent: int) -> list[str]:
        prefix = " " * indent
        if isinstance(value, dict):
            lines: list[str] = []
            for key, item in value.items():
                key_text = str(key)
                if isinstance(item, (dict, list)) and item:
                    lines.append(f"{prefix}{key_text}:")
                    lines.extend(self._block(item, indent + 2))
                else:
                    scalar = "[]" if item == [] else "{}" if item == {} else _dump_scalar(item)
                    lines.append(f"{prefix}{key_text}: {scalar}")
            return lines
        if isinstance(value, list):
            lines = []
            for item in value:
                if isinstance(item, dict) and item:
                    first_key, first_value = next(iter(item.items()))
                    if isinstance(first_value, (dict, list)) and first_value:
                        lines.append(f"{prefix}- {first_key}:")
                        lines.extend(self._block(first_value, indent + 4))
                    else:
                        scalar = "[]" if first_value == [] else "{}" if first_value == {} else _dump_scalar(first_value)
                        lines.append(f"{prefix}- {first_key}: {scalar}")
                    remaining = dict(list(item.items())[1:])
                    if remaining:
                        lines.extend(self._block(remaining, indent + 2))
                elif isinstance(item, (dict, list)) and item:
                    lines.append(f"{prefix}-")
                    lines.extend(self._block(item, indent + 2))
                else:
                    scalar = "[]" if item == [] else "{}" if item == {} else _dump_scalar(item)
                    lines.append(f"{prefix}- {scalar}")
            return lines
        return [prefix + _dump_scalar(value)]


class _MiniYamlParser:
    """Small YAML parser for the project's frontmatter contract.

    It supports nested mappings/sequences, quoted strings, inline collections,
    booleans, numbers, null, and block strings. It deliberately rejects
    unsupported YAML features rather than silently interpreting them.
    """

    def __init__(self, text: str):
        self.lines: list[tuple[int, str, int]] = []
        for number, raw in enumerate(text.splitlines(), 1):
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            expanded = raw.expandtabs(2)
            indent = len(expanded) - len(expanded.lstrip(" "))
            content = expanded[indent:]
            self.lines.append((indent, content, number))
        self.index = 0

    def parse(self) -> Any:
        if not self.lines:
            return {}
        value = self._parse_block(self.lines[0][0])
        if self.index != len(self.lines):
            number = self.lines[self.index][2]
            raise ValidationError(f"unsupported or malformed YAML near line {number}")
        return value

    def _parse_block(self, indent: int) -> Any:
        if self.index >= len(self.lines):
            return {}
        current_indent, content, _ = self.lines[self.index]
        if current_indent != indent:
            raise ValidationError("invalid YAML indentation")
        if content == "-" or content.startswith("- "):
            return self._parse_list(indent)
        return self._parse_map(indent)

    def _parse_map(self, indent: int) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while self.index < len(self.lines):
            current_indent, content, number = self.lines[self.index]
            if current_indent < indent:
                break
            if current_indent != indent or content == "-" or content.startswith("- "):
                break
            colon = _mapping_colon(content)
            if colon < 0:
                raise ValidationError(f"expected mapping entry at YAML line {number}")
            key = content[:colon].strip()
            if not key:
                raise ValidationError(f"empty YAML key at line {number}")
            raw_value = content[colon + 1 :].strip()
            self.index += 1
            if raw_value in {"|", ">", "|-", ">-"}:
                result[key] = self._parse_block_string(indent, folded=raw_value.startswith(">"))
            elif raw_value:
                result[key] = _parse_scalar(raw_value)
            elif self.index < len(self.lines) and self.lines[self.index][0] > indent:
                result[key] = self._parse_block(self.lines[self.index][0])
            else:
                result[key] = {}
        return result

    def _parse_list(self, indent: int) -> list[Any]:
        result: list[Any] = []
        while self.index < len(self.lines):
            current_indent, content, number = self.lines[self.index]
            if current_indent != indent or not (content == "-" or content.startswith("- ")):
                break
            rest = content[1:].strip()
            self.index += 1
            if not rest:
                if self.index < len(self.lines) and self.lines[self.index][0] > indent:
                    result.append(self._parse_block(self.lines[self.index][0]))
                else:
                    result.append(None)
                continue
            colon = _mapping_colon(rest)
            if colon >= 0:
                key = rest[:colon].strip()
                raw_value = rest[colon + 1 :].strip()
                item: dict[str, Any] = {}
                if raw_value:
                    item[key] = _parse_scalar(raw_value)
                elif self.index < len(self.lines) and self.lines[self.index][0] > indent:
                    item[key] = self._parse_block(self.lines[self.index][0])
                else:
                    item[key] = {}
                if self.index < len(self.lines) and self.lines[self.index][0] > indent:
                    extra_indent = self.lines[self.index][0]
                    extra = self._parse_map(extra_indent)
                    item.update(extra)
                result.append(item)
            else:
                result.append(_parse_scalar(rest))
        return result

    def _parse_block_string(self, parent_indent: int, *, folded: bool) -> str:
        collected: list[str] = []
        while self.index < len(self.lines) and self.lines[self.index][0] > parent_indent:
            indent, content, _ = self.lines[self.index]
            collected.append(content if indent else "")
            self.index += 1
        return (" ".join(collected) if folded else "\n".join(collected)) + "\n"


def _mapping_colon(text: str) -> int:
    quote: str | None = None
    depth = 0
    for index, char in enumerate(text):
        if quote:
            if char == quote and (index == 0 or text[index - 1] != "\\"):
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == ":" and depth == 0 and (index + 1 == len(text) or text[index + 1].isspace()):
            return index
    return -1


def _parse_scalar(text: str) -> Any:
    text = _strip_comment(text).strip()
    if not text:
        return None
    if text in {"null", "Null", "NULL", "~"}:
        return None
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [] if not inner else [_parse_scalar(piece.strip()) for piece in _split_inline(inner)]
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        if not inner:
            return {}
        result: dict[str, Any] = {}
        for piece in _split_inline(inner):
            colon = _mapping_colon(piece)
            if colon < 0:
                raise ValidationError(f"invalid inline mapping: {text}")
            result[piece[:colon].strip().strip("'\"")] = _parse_scalar(piece[colon + 1 :].strip())
        return result
    if (text.startswith('"') and text.endswith('"')):
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"invalid quoted YAML scalar: {text}") from exc
    if text.startswith("'") and text.endswith("'"):
        try:
            return ast.literal_eval(text)
        except (SyntaxError, ValueError) as exc:
            raise ValidationError(f"invalid quoted YAML scalar: {text}") from exc
    if re.fullmatch(r"[-+]?\d+", text):
        return int(text)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", text):
        return float(text)
    return text


def _strip_comment(text: str) -> str:
    quote: str | None = None
    for index, char in enumerate(text):
        if quote:
            if char == quote and (index == 0 or text[index - 1] != "\\"):
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "#" and (index == 0 or text[index - 1].isspace()):
            return text[:index]
    return text


def _split_inline(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    quote: str | None = None
    depth = 0
    for index, char in enumerate(text):
        if quote:
            if char == quote and (index == 0 or text[index - 1] != "\\"):
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return parts
