from __future__ import annotations

from datetime import datetime, timedelta
import re
import unicodedata
from typing import Any
from uuid import uuid4


def now_iso() -> str:
    """Return a local, timezone-aware timestamp suitable for frontmatter."""

    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.astimezone()
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    result = datetime.fromisoformat(text)
    return result if result.tzinfo else result.astimezone()


def iso_after(base: str | datetime, *, days: int) -> str:
    return (parse_datetime(base) + timedelta(days=days)).isoformat(timespec="seconds")


def date_key(value: str | datetime) -> str:
    return parse_datetime(value).date().isoformat()


def slugify(value: str) -> str:
    """Make a stable, filesystem-safe ID while retaining non-Latin letters."""

    normalized = unicodedata.normalize("NFKC", str(value)).strip().lower()
    normalized = re.sub(r"[^\w\-.]+", "-", normalized, flags=re.UNICODE)
    normalized = re.sub(r"-+", "-", normalized).strip("-._")
    return normalized or f"record-{uuid4().hex[:8]}"


def new_id(prefix: str, *, timestamp: str | None = None) -> str:
    stamp = (timestamp or now_iso()).replace("-", "").replace(":", "").replace("+", "")
    stamp = re.sub(r"[^0-9T]", "", stamp)[:15]
    return f"{slugify(prefix)}-{stamp}-{uuid4().hex[:6]}"


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "yes", "y", "1", "on"}:
        return True
    if text in {"false", "no", "n", "0", "off"}:
        return False
    raise ValueError(f"not a boolean: {value!r}")


def compact_text(value: str | None, fallback: str = "") -> str:
    return " ".join((value or fallback).split())
