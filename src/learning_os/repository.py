from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, TypeVar

from .errors import DuplicateRecordError, RecordNotFoundError, ValidationError
from .frontmatter import load_markdown, write_markdown
from .models import (
    ConceptRecord,
    FoundationTrackRecord,
    MistakeRecord,
    PaperRecord,
    SessionRecord,
)


Record = TypeVar("Record")


@dataclass(frozen=True)
class RecordSpec:
    folder: str
    record_type: str
    model: type[Any]


SPECS: dict[str, RecordSpec] = {
    "concept": RecordSpec("Concepts", "concept", ConceptRecord),
    "paper": RecordSpec("Papers", "paper", PaperRecord),
    "mistake": RecordSpec("Mistakes", "mistake", MistakeRecord),
    "session": RecordSpec("Sessions", "session", SessionRecord),
    "foundation": RecordSpec("Foundation", "foundation_track", FoundationTrackRecord),
}


DEFAULT_BODIES: dict[str, str] = {
    "concept": """## Definition\n\n## Intuition\n\n## Examples\n\n## Counterexamples\n\n## Derivation notes\n\n## Open questions\n""",
    "paper": """## Core Problem\n\n## Main Claim\n\n## Method\n\n## Evidence\n\n## Assumptions\n\n## Dependency Map\n\n## Formula Map\n\n## Open Questions\n\n## My Critique\n""",
    "mistake": """## Problem\n\n## My Answer\n\n## What Was Wrong\n\n## Why I Made This Mistake\n\n## Correct Mental Model\n\n## Retest Question\n""",
    "session": """## Goal\n\n## Initial Belief\n\n## Questions\n\n## My Attempts\n\n## Hints Received\n\n## A0 Test\n\n## Revised Understanding\n\n## End-of-session Reflection\n\n## Next Action\n""",
    "foundation": """## Why this track exists\n\n## Minimal path\n\n## Evidence to collect\n\n## Exit criteria\n""",
}


class VaultRepository:
    """Filesystem adapter for the Markdown vault.

    Each record type has one directory and one `<id>.md` file.  Bodies are
    preserved across frontmatter updates unless a caller explicitly supplies a
    replacement body.
    """

    folders = tuple(spec.folder for spec in SPECS.values()) + ("Sources", "Templates")

    def __init__(self, root: str | Path = "."):
        self.root = Path(root).expanduser().resolve()

    def ensure_layout(self) -> None:
        for folder in self.folders:
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def spec(self, kind: str) -> RecordSpec:
        try:
            return SPECS[kind]
        except KeyError as exc:
            raise ValidationError(f"unknown record kind: {kind}") from exc

    def path_for(self, kind: str, record_id: str) -> Path:
        spec = self.spec(kind)
        if not record_id or "/" in record_id or "\\" in record_id or record_id.endswith(".md"):
            raise ValidationError("record ID must be a filename-safe value without .md")
        return self.root / spec.folder / f"{record_id}.md"

    def exists(self, kind: str, record_id: str) -> bool:
        return self.path_for(kind, record_id).is_file()

    def create(self, kind: str, record: Any, *, body: str | None = None) -> Path:
        path = self.path_for(kind, record.id)
        if path.exists():
            raise DuplicateRecordError(f"{kind} already exists: {record.id}")
        self.ensure_layout()
        self._validate_type(kind, record)
        record.validate()
        write_markdown(path, record.to_dict(), DEFAULT_BODIES[kind] if body is None else body)
        return path

    def save(self, kind: str, record: Any, *, body: str | None = None) -> Path:
        path = self.path_for(kind, record.id)
        self._validate_type(kind, record)
        record.validate()
        if body is None and path.exists():
            _, body = load_markdown(path)
        write_markdown(path, record.to_dict(), DEFAULT_BODIES[kind] if body is None else body)
        return path

    def load_document(self, kind: str, record_id: str) -> tuple[Any, str, Path]:
        path = self.path_for(kind, record_id)
        if not path.is_file():
            raise RecordNotFoundError(f"{kind} not found: {record_id} ({path})")
        data, body = load_markdown(path)
        spec = self.spec(kind)
        actual_type = data.get("type")
        if actual_type != spec.record_type:
            raise ValidationError(f"{path} declares type {actual_type!r}, expected {spec.record_type!r}")
        try:
            record = spec.model.from_dict(data)
        except ValidationError as exc:
            raise ValidationError(f"{path}: {exc}") from exc
        return record, body, path

    def load(self, kind: str, record_id: str) -> Any:
        return self.load_document(kind, record_id)[0]

    def list_paths(self, kind: str) -> list[Path]:
        spec = self.spec(kind)
        directory = self.root / spec.folder
        if not directory.is_dir():
            return []
        return sorted(path for path in directory.glob("*.md") if path.is_file())

    def iter_records(self, kind: str) -> Iterator[Any]:
        spec = self.spec(kind)
        for path in self.list_paths(kind):
            data, _ = load_markdown(path)
            if data.get("type") != spec.record_type:
                raise ValidationError(f"{path} declares unexpected type {data.get('type')!r}")
            yield spec.model.from_dict(data)

    def records(self, kind: str) -> list[Any]:
        return list(self.iter_records(kind))

    def validate_all(self) -> list[str]:
        errors: list[str] = []
        for kind in SPECS:
            for path in self.list_paths(kind):
                try:
                    self.load_document(kind, path.stem)
                except (ValidationError, RecordNotFoundError) as exc:
                    errors.append(str(exc))
        # A second mastery JSON/database would make the source of truth
        # ambiguous. Report it explicitly so `learning-os validate` can fail
        # closed without deleting a user file.
        for forbidden in ("Mastery", "mastery.json", "learning_os.db"):
            candidate = self.root / forbidden
            if candidate.exists():
                errors.append(f"duplicate source-of-truth candidate exists: {candidate}")
        return errors

    def _validate_type(self, kind: str, record: Any) -> None:
        spec = self.spec(kind)
        if not isinstance(record, spec.model):
            raise ValidationError(f"expected {spec.model.__name__} for kind {kind}")


def record_body(path: str | Path) -> str:
    """Return the current body for callers that need explicit preservation."""

    _, body = load_markdown(path)
    return body
