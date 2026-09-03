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
        if not path.is_file():
            raise RecordNotFoundError(f"{kind} not found: {record.id} ({path})")
        if body is None:
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
        except Exception as exc:
            raise ValidationError(f"{path}: malformed record data: {exc}") from exc
        if record.id != path.stem:
            raise ValidationError(
                f"{path}: frontmatter id {record.id!r} does not match filename stem {path.stem!r}"
            )
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
        for path in self.list_paths(kind):
            yield self.load_document(kind, path.stem)[0]

    def records(self, kind: str) -> list[Any]:
        return list(self.iter_records(kind))

    def validate_all(self) -> list[str]:
        errors: list[str] = []
        loaded: dict[str, list[tuple[Any, Path]]] = {kind: [] for kind in SPECS}
        ids: dict[str, set[str]] = {kind: set() for kind in SPECS}
        for kind in SPECS:
            directory = self.root / self.spec(kind).folder
            if directory.is_dir():
                for candidate in sorted(directory.iterdir()):
                    if candidate.is_file() and self._is_partial_path(candidate):
                        errors.append(
                            f"partial/temporary record file must be removed or completed: {candidate}"
                        )
            for path in self.list_paths(kind):
                try:
                    # Parse the file directly here instead of calling
                    # load_document().  A filename/ID mismatch is itself an
                    # error, but we still need the parsed ID to detect a
                    # second file claiming the same frontmatter ID.
                    data, _ = load_markdown(path)
                    spec = self.spec(kind)
                    if data.get("type") != spec.record_type:
                        raise ValidationError(
                            f"{path} declares type {data.get('type')!r}, expected {spec.record_type!r}"
                        )
                    record = spec.model.from_dict(data)
                    if record.id != path.stem:
                        errors.append(
                            f"{path}: frontmatter id {record.id!r} does not match filename stem {path.stem!r}"
                        )
                except Exception as exc:
                    # A validation command must fail closed for user-authored
                    # malformed files instead of crashing halfway through a
                    # vault scan.  Model and parser errors are already
                    # user-facing LearningOS errors; the fallback also turns
                    # unexpected type errors from malformed YAML into a
                    # diagnosable validation result.
                    message = str(exc) or exc.__class__.__name__
                    if not message.startswith(str(path)):
                        message = f"{path}: {message}"
                    errors.append(message)
                    continue
                if record.id in ids[kind]:
                    previous = next(
                        previous_path
                        for previous_record, previous_path in loaded[kind]
                        if previous_record.id == record.id
                    )
                    errors.append(
                        f"duplicate {kind} ID {record.id!r}: {previous} and {path}"
                    )
                else:
                    ids[kind].add(record.id)
                loaded[kind].append((record, path))

        self._validate_links(loaded, ids, errors)
        # A second mastery JSON/database would make the source of truth
        # ambiguous. Report it explicitly so `learning-os validate` can fail
        # closed without deleting a user file.
        for forbidden in ("Mastery", "mastery.json", "learning_os.db"):
            candidate = self.root / forbidden
            if candidate.exists():
                errors.append(f"duplicate source-of-truth candidate exists: {candidate}")
        return errors

    @staticmethod
    def _is_partial_path(path: Path) -> bool:
        """Recognize the temporary names used by atomic writes and editors."""

        return path.name.endswith((".tmp", ".partial", ".part"))

    @staticmethod
    def _validate_links(
        loaded: dict[str, list[tuple[Any, Path]]],
        ids: dict[str, set[str]],
        errors: list[str],
    ) -> None:
        """Validate explicit cross-record references after local parsing.

        Dependency bucket entries remain human-readable labels and are not
        treated as links.  Only fields whose schema names a target record are
        resolved here.
        """

        def link(source: Path, field: str, target_kind: str, target_id: str | None) -> None:
            if target_id and target_id not in ids[target_kind]:
                errors.append(
                    f"{source}: broken link {field}={target_id!r}; "
                    f"no {target_kind} record with that ID"
                )

        for concept, path in loaded["concept"]:
            for prerequisite in concept.prerequisites:
                link(path, "prerequisites", "concept", prerequisite)
            for evidence in concept.a0_evidence:
                link(path, "a0_evidence.session_id", "session", evidence.session_id)

        for paper, path in loaded["paper"]:
            for blocker in paper.blockers:
                link(path, "blocker.concept_id", "concept", blocker.concept_id)

        for mistake, path in loaded["mistake"]:
            link(path, "concept_id", "concept", mistake.concept_id)

        for session, path in loaded["session"]:
            link(path, "concept_id", "concept", session.concept_id)
            link(path, "paper_id", "paper", session.paper_id)
            for mistake_id in session.mistakes:
                link(path, "mistakes", "mistake", mistake_id)
            for index, test in enumerate(session.a0_tests):
                evidence_id = test.get("evidence_id")
                if not evidence_id:
                    errors.append(f"{path}: a0_tests[{index}] is missing evidence_id")
                    continue
                if session.concept_id:
                    concept_records = {
                        concept.id: concept for concept, _ in loaded["concept"]
                    }
                    concept = concept_records.get(session.concept_id)
                    if concept is not None and evidence_id not in {
                        evidence.id for evidence in concept.a0_evidence
                    }:
                        errors.append(
                            f"{path}: broken link a0_tests[{index}].evidence_id={evidence_id!r}; "
                            f"no evidence in concept {session.concept_id!r}"
                        )

        for foundation, path in loaded["foundation"]:
            for concept_id in foundation.concepts:
                link(path, "concepts", "concept", concept_id)

    def _validate_type(self, kind: str, record: Any) -> None:
        spec = self.spec(kind)
        if not isinstance(record, spec.model):
            raise ValidationError(f"expected {spec.model.__name__} for kind {kind}")


def record_body(path: str | Path) -> str:
    """Return the current body for callers that need explicit preservation."""

    _, body = load_markdown(path)
    return body
