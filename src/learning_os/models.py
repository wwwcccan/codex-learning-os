from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, ClassVar, Iterable

from .errors import ValidationError
from .utils import date_key, new_id, now_iso, parse_datetime


SCHEMA_VERSION = 1


class _ParsedEnum(str, Enum):
    @classmethod
    def parse(cls, value: str | Enum) -> str:
        if isinstance(value, cls):
            return value.value
        candidate = str(value).strip()
        for item in cls:
            if candidate.lower() in {item.value.lower(), item.name.lower()}:
                return item.value
        allowed = ", ".join(item.value for item in cls)
        raise ValidationError(f"invalid {cls.__name__} {value!r}; expected one of: {allowed}")


class AssistanceLevel(_ParsedEnum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A5 = "A5"


class Dimension(_ParsedEnum):
    RECALL = "recall"
    EXPLANATION = "explanation"
    DERIVATION = "derivation"
    TRANSFER = "transfer"
    DEBUG = "debug"


class EvidenceKind(_ParsedEnum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"
    SPECULATION = "SPECULATION"
    UNKNOWN = "UNKNOWN"


class BlockerType(_ParsedEnum):
    NOTATION = "notation"
    PREREQUISITE_CONCEPT = "prerequisite_concept"
    DERIVATION = "derivation"
    CLASSICAL_METHOD = "classical_method"
    BENCHMARK = "benchmark"
    RECENT_RELATED_WORK = "recent_related_work"

    @classmethod
    def parse(cls, value: str | Enum) -> str:
        aliases = {
            "prerequisite": cls.PREREQUISITE_CONCEPT.value,
            "prerequisite-concept": cls.PREREQUISITE_CONCEPT.value,
            "related_work": cls.RECENT_RELATED_WORK.value,
            "related-work": cls.RECENT_RELATED_WORK.value,
            "recent-related-work": cls.RECENT_RELATED_WORK.value,
            "classical-method": cls.CLASSICAL_METHOD.value,
        }
        candidate = str(value).strip().lower()
        if candidate in aliases:
            return aliases[candidate]
        return super().parse(value)


class DependencyPriority(_ParsedEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


CONCEPT_DIMENSIONS: tuple[str, ...] = tuple(item.value for item in Dimension)
ASSISTANCE_LEVELS: tuple[str, ...] = tuple(item.value for item in AssistanceLevel)
EVIDENCE_KINDS: tuple[str, ...] = tuple(item.value for item in EvidenceKind)
BLOCKER_TYPES: tuple[str, ...] = tuple(item.value for item in BlockerType)
PRIORITIES: tuple[str, ...] = tuple(item.value for item in DependencyPriority)

CONCEPT_STATUSES = {"inbox", "learning", "review", "mastered", "archived"}
PAPER_STATUSES = {"planned", "reading", "blocked", "paused", "completed", "archived"}
MISTAKE_STATUSES = {"unresolved", "retesting", "resolved", "archived"}
SESSION_MODES = {"learning", "research"}
SESSION_STATUSES = {"active", "completed", "abandoned"}
FOUNDATION_STATUSES = {"suggested", "active", "completed", "archived"}


def _record_id(value: Any, label: str = "id") -> str:
    result = str(value or "").strip()
    if not result:
        raise ValidationError(f"{label} is required")
    if result in {".", ".."} or "/" in result or "\\" in result:
        raise ValidationError(f"{label} must be a filename-safe ID without slashes")
    if result.endswith(".md"):
        raise ValidationError(f"{label} must not include the .md suffix")
    return result


def _string(value: Any, label: str, *, required: bool = False, default: str = "") -> str:
    result = str(value if value is not None else default).strip()
    if required and not result:
        raise ValidationError(f"{label} is required")
    return result


def _int(value: Any, label: str, *, default: int = 0) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise ValidationError(f"{label} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} must be an integer") from exc
    return result


def _optional_int(value: Any, label: str) -> int | None:
    if value is None or value == "":
        return None
    return _int(value, label)


def _score(value: Any, label: str) -> int:
    result = _int(value, label)
    if not 0 <= result <= 5:
        raise ValidationError(f"{label} must be between 0 and 5")
    return result


def _confidence(value: Any, label: str = "confidence") -> int:
    result = _int(value, label)
    if not 0 <= result <= 100:
        raise ValidationError(f"{label} must be between 0 and 100")
    return result


def _strings(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, (list, tuple)):
        raise ValidationError(f"{label} must be a list of strings")
    result = [str(item).strip() for item in value if str(item).strip()]
    return result


def _timestamp(value: Any, label: str, *, default: str | None = None) -> str:
    result = _string(value, label, default=default or now_iso())
    try:
        parse_datetime(result)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} must be an ISO-8601 timestamp") from exc
    return result


def _optional_timestamp(value: Any, label: str) -> str | None:
    if value in (None, ""):
        return None
    return _timestamp(value, label)


def _extra(data: dict[str, Any], known: Iterable[str]) -> dict[str, Any]:
    known_set = set(known)
    return {key: value for key, value in data.items() if key not in known_set}


def _validate_header(data: dict[str, Any], expected_type: str) -> None:
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValidationError(f"schema_version must be {SCHEMA_VERSION}, got {version!r}")
    actual_type = data.get("type")
    if actual_type != expected_type:
        raise ValidationError(f"type must be {expected_type!r}, got {actual_type!r}")


@dataclass
class A0Evidence:
    dimension: str
    correct: bool
    assistance: str
    confidence: int
    novel_problem: bool
    timestamp: str
    id: str = ""
    session_id: str | None = None
    note: str = ""
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    _KNOWN: ClassVar[set[str]] = {
        "id",
        "evidence_id",
        "dimension",
        "correct",
        "assistance",
        "confidence",
        "novel_problem",
        "novel",
        "timestamp",
        "session_id",
        "note",
    }

    def __post_init__(self) -> None:
        self.id = _record_id(self.id or new_id("a0", timestamp=self.timestamp), "evidence id")
        self.dimension = Dimension.parse(self.dimension)
        self.assistance = AssistanceLevel.parse(self.assistance)
        self.confidence = _confidence(self.confidence)
        self.timestamp = _timestamp(self.timestamp, "evidence timestamp")
        if not isinstance(self.correct, bool):
            raise ValidationError("evidence correct must be a boolean")
        if not isinstance(self.novel_problem, bool):
            raise ValidationError("evidence novel_problem must be a boolean")
        if self.session_id is not None:
            self.session_id = _record_id(self.session_id, "session id")
        self.note = str(self.note or "").strip()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "A0Evidence":
        if not isinstance(data, dict):
            raise ValidationError("a0 evidence entries must be mappings")
        timestamp = data.get("timestamp") or now_iso()
        return cls(
            id=data.get("id", data.get("evidence_id", "")),
            dimension=data.get("dimension", ""),
            correct=data.get("correct", False),
            assistance=data.get("assistance", "A5"),
            confidence=data.get("confidence", 50),
            novel_problem=data.get("novel_problem", data.get("novel", False)),
            timestamp=timestamp,
            session_id=data.get("session_id"),
            note=data.get("note", ""),
            extra=_extra(data, cls._KNOWN),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "dimension": self.dimension,
            "correct": self.correct,
            "assistance": self.assistance,
            "confidence": self.confidence,
            "novel_problem": self.novel_problem,
            "timestamp": self.timestamp,
        }
        if self.session_id:
            result["session_id"] = self.session_id
        if self.note:
            result["note"] = self.note
        result.update(self.extra)
        return result

    @property
    def is_a0_success(self) -> bool:
        return self.correct and self.assistance == AssistanceLevel.A0.value


@dataclass
class AssessmentEntry:
    dimension: str
    score: int
    assistance: str
    timestamp: str
    confidence: int | None = None
    id: str = ""
    note: str = ""
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    _KNOWN: ClassVar[set[str]] = {
        "id",
        "dimension",
        "score",
        "assistance",
        "timestamp",
        "confidence",
        "note",
    }

    def __post_init__(self) -> None:
        self.id = _record_id(self.id or new_id("assessment", timestamp=self.timestamp), "assessment id")
        self.dimension = Dimension.parse(self.dimension)
        self.score = _score(self.score, "assessment score")
        self.assistance = AssistanceLevel.parse(self.assistance)
        self.timestamp = _timestamp(self.timestamp, "assessment timestamp")
        if self.confidence is not None:
            self.confidence = _confidence(self.confidence)
        self.note = str(self.note or "").strip()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssessmentEntry":
        if not isinstance(data, dict):
            raise ValidationError("assessment entries must be mappings")
        return cls(
            id=data.get("id", ""),
            dimension=data.get("dimension", ""),
            score=data.get("score", 0),
            assistance=data.get("assistance", "A5"),
            timestamp=data.get("timestamp") or now_iso(),
            confidence=data.get("confidence"),
            note=data.get("note", ""),
            extra=_extra(data, cls._KNOWN),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "dimension": self.dimension,
            "score": self.score,
            "assistance": self.assistance,
            "timestamp": self.timestamp,
        }
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.note:
            result["note"] = self.note
        result.update(self.extra)
        return result


@dataclass
class ConceptRecord:
    id: str
    name: str
    domain: str
    status: str = "learning"
    recall: int = 0
    explanation: int = 0
    derivation: int = 0
    transfer: int = 0
    debug: int = 0
    assistance_required: str = "A5"
    a0_successes: int = 0
    last_review: str | None = None
    next_review: str | None = None
    weakness: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    a0_evidence: list[A0Evidence] = field(default_factory=list)
    assessments: list[AssessmentEntry] = field(default_factory=list)
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    _KNOWN: ClassVar[set[str]] = {
        "schema_version",
        "type",
        "id",
        "name",
        "domain",
        "status",
        *CONCEPT_DIMENSIONS,
        "assistance_required",
        "a0_successes",
        "last_review",
        "next_review",
        "weakness",
        "prerequisites",
        "a0_evidence",
        "assessments",
        "created",
        "updated",
    }

    def __post_init__(self) -> None:
        self.id = _record_id(self.id)
        self.name = _string(self.name, "name", required=True)
        self.domain = _string(self.domain, "domain", required=True)
        self.status = _string(self.status, "status", default="learning").lower()
        for dimension in CONCEPT_DIMENSIONS:
            setattr(self, dimension, _score(getattr(self, dimension), dimension))
        self.assistance_required = AssistanceLevel.parse(self.assistance_required)
        self.a0_successes = _int(self.a0_successes, "a0_successes")
        self.last_review = _optional_timestamp(self.last_review, "last_review")
        self.next_review = _optional_timestamp(self.next_review, "next_review")
        self.weakness = _strings(self.weakness, "weakness")
        self.prerequisites = _strings(self.prerequisites, "prerequisites")
        self.a0_evidence = [
            item if isinstance(item, A0Evidence) else A0Evidence.from_dict(item) for item in (self.a0_evidence or [])
        ]
        self.assessments = [
            item if isinstance(item, AssessmentEntry) else AssessmentEntry.from_dict(item)
            for item in (self.assessments or [])
        ]
        self.created = _timestamp(self.created, "created")
        self.updated = _timestamp(self.updated, "updated")

    @classmethod
    def new(cls, id: str, name: str, domain: str, prerequisites: list[str] | None = None) -> "ConceptRecord":
        current = now_iso()
        record = cls(id=id, name=name, domain=domain, prerequisites=prerequisites or [], created=current, updated=current)
        record.refresh_derived()
        return record

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConceptRecord":
        if not isinstance(data, dict):
            raise ValidationError("concept frontmatter must be a mapping")
        _validate_header(data, "concept")
        record = cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            domain=data.get("domain", ""),
            status=data.get("status", "learning"),
            recall=data.get("recall", 0),
            explanation=data.get("explanation", 0),
            derivation=data.get("derivation", 0),
            transfer=data.get("transfer", 0),
            debug=data.get("debug", 0),
            assistance_required=data.get("assistance_required", "A5"),
            a0_successes=data.get("a0_successes", 0),
            last_review=data.get("last_review"),
            next_review=data.get("next_review"),
            weakness=data.get("weakness", []),
            prerequisites=data.get("prerequisites", []),
            a0_evidence=data.get("a0_evidence", []),
            assessments=data.get("assessments", []),
            created=data.get("created") or now_iso(),
            updated=data.get("updated") or now_iso(),
            extra=_extra(data, cls._KNOWN),
        )
        record.validate()
        return record

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "type": "concept",
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "status": self.status,
            "recall": self.recall,
            "explanation": self.explanation,
            "derivation": self.derivation,
            "transfer": self.transfer,
            "debug": self.debug,
            "assistance_required": self.assistance_required,
            "a0_successes": self.a0_successes,
            "last_review": self.last_review,
            "next_review": self.next_review,
            "weakness": list(self.weakness),
            "prerequisites": list(self.prerequisites),
            "a0_evidence": [item.to_dict() for item in self.a0_evidence],
            "assessments": [item.to_dict() for item in self.assessments],
            "created": self.created,
            "updated": self.updated,
        }
        result.update(self.extra)
        return result

    def validate(self) -> None:
        if self.status not in CONCEPT_STATUSES:
            raise ValidationError(f"concept status must be one of: {', '.join(sorted(CONCEPT_STATUSES))}")
        if self.a0_successes < 0:
            raise ValidationError("a0_successes cannot be negative")
        actual_successes = sum(item.is_a0_success for item in self.a0_evidence)
        if self.a0_successes != actual_successes:
            raise ValidationError(
                f"a0_successes={self.a0_successes} does not match recorded A0 successes={actual_successes}"
            )
        for weakness in self.weakness:
            if weakness not in CONCEPT_DIMENSIONS:
                raise ValidationError(f"unknown weakness dimension: {weakness}")
        if len(self.weakness) != len(set(self.weakness)):
            raise ValidationError("weakness dimensions must be unique")
        if self.status == "mastered":
            if not self.mastery_eligible():
                raise ValidationError("a concept cannot be mastered without the A0 mastery gate")
            if self.open_a0_failure_dimensions():
                raise ValidationError("a concept with a latest failed A0 dimension cannot remain mastered")

    def refresh_derived(self) -> None:
        self.a0_successes = sum(item.is_a0_success for item in self.a0_evidence)
        successful_levels = [ASSISTANCE_LEVELS.index(item.assistance) for item in self.a0_evidence if item.correct]
        if successful_levels:
            self.assistance_required = ASSISTANCE_LEVELS[min(successful_levels)]
        weak_by_score = {dimension for dimension in CONCEPT_DIMENSIONS if getattr(self, dimension) < 4}
        weak_by_failure = set(self.open_a0_failure_dimensions())
        self.weakness = [dimension for dimension in CONCEPT_DIMENSIONS if dimension in weak_by_score or dimension in weak_by_failure]
        if self.mastery_eligible() and not weak_by_failure:
            self.status = "mastered"
        elif self.status == "mastered":
            self.status = "review"
        self.updated = now_iso()

    def open_a0_failure_dimensions(self) -> list[str]:
        """Return dimensions whose latest A0 attempt is incorrect."""

        latest: dict[str, A0Evidence] = {}
        for evidence in self.a0_evidence:
            if evidence.assistance == "A0":
                previous = latest.get(evidence.dimension)
                if previous is None or evidence.timestamp >= previous.timestamp:
                    latest[evidence.dimension] = evidence
        return [dimension for dimension in CONCEPT_DIMENSIONS if dimension in latest and not latest[dimension].correct]

    def mastery_eligible(self) -> bool:
        thresholds = {
            "recall": 4,
            "explanation": 4,
            "derivation": 4,
            "transfer": 4,
            "debug": 3,
        }
        if any(getattr(self, key) < value for key, value in thresholds.items()):
            return False
        successes = [item for item in self.a0_evidence if item.is_a0_success]
        if len({date_key(item.timestamp) for item in successes}) < 3:
            return False
        return any(item.novel_problem and item.dimension == "transfer" for item in successes)

    def update_scores(self, scores: dict[str, int], *, assistance: str = "A0", note: str = "") -> None:
        timestamp = now_iso()
        level = AssistanceLevel.parse(assistance)
        for dimension, value in scores.items():
            canonical = Dimension.parse(dimension)
            score = _score(value, canonical)
            setattr(self, canonical, score)
            self.assessments.append(
                AssessmentEntry(
                    dimension=canonical,
                    score=score,
                    assistance=level,
                    timestamp=timestamp,
                    note=note,
                )
            )
        self.refresh_derived()
        self.validate()


@dataclass
class BlockerRecord:
    type: str
    label: str
    description: str = ""
    priority: str = "P0"
    status: str = "open"
    id: str = ""
    concept_id: str | None = None
    foundation_track: str | None = None
    created: str = field(default_factory=now_iso)
    resolved_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    _KNOWN: ClassVar[set[str]] = {
        "id",
        "type",
        "kind",
        "label",
        "title",
        "description",
        "priority",
        "status",
        "concept_id",
        "concept",
        "foundation_track",
        "created",
        "resolved_at",
    }

    def __post_init__(self) -> None:
        self.id = _record_id(self.id or new_id("blocker", timestamp=self.created), "blocker id")
        self.type = BlockerType.parse(self.type)
        self.label = _string(self.label, "blocker label", required=True)
        self.description = _string(self.description, "blocker description")
        self.priority = DependencyPriority.parse(self.priority)
        self.status = _string(self.status, "blocker status", default="open").lower()
        self.concept_id = _string(self.concept_id, "concept id") if self.concept_id else None
        self.foundation_track = _string(self.foundation_track, "foundation track") if self.foundation_track else None
        self.created = _timestamp(self.created, "blocker created")
        self.resolved_at = _optional_timestamp(self.resolved_at, "blocker resolved_at")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BlockerRecord":
        if not isinstance(data, dict):
            raise ValidationError("blockers must be mappings")
        return cls(
            id=data.get("id", ""),
            type=data.get("type", data.get("kind", "")),
            label=data.get("label", data.get("title", "")),
            description=data.get("description", ""),
            priority=data.get("priority", "P0"),
            status=data.get("status", "open"),
            concept_id=data.get("concept_id", data.get("concept")),
            foundation_track=data.get("foundation_track"),
            created=data.get("created") or now_iso(),
            resolved_at=data.get("resolved_at"),
            extra=_extra(data, cls._KNOWN),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "created": self.created,
        }
        if self.concept_id:
            result["concept_id"] = self.concept_id
        if self.foundation_track:
            result["foundation_track"] = self.foundation_track
        if self.resolved_at:
            result["resolved_at"] = self.resolved_at
        result.update(self.extra)
        return result

    def validate(self) -> None:
        if self.status not in {"open", "resolved", "ignored"}:
            raise ValidationError("blocker status must be open, resolved, or ignored")
        if self.status == "resolved" and not self.resolved_at:
            raise ValidationError("resolved blockers need resolved_at")


@dataclass
class PaperRecord:
    id: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    status: str = "planned"
    research_question: str = ""
    core_claim: str = ""
    current_reading_status: str = "not_started"
    blockers: list[BlockerRecord] = field(default_factory=list)
    p0_dependencies: list[str] = field(default_factory=list)
    p1_dependencies: list[str] = field(default_factory=list)
    p2_dependencies: list[str] = field(default_factory=list)
    p3_dependencies: list[str] = field(default_factory=list)
    core_formulas: list[str] = field(default_factory=list)
    benchmarks: list[str] = field(default_factory=list)
    classical_methods: list[str] = field(default_factory=list)
    related_sota: list[str] = field(default_factory=list)
    evidence_notes: list[dict[str, Any]] = field(default_factory=list)
    formula_map: list[dict[str, Any]] = field(default_factory=list)
    experiment_predictions: list[dict[str, Any]] = field(default_factory=list)
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    _KNOWN: ClassVar[set[str]] = {
        "schema_version",
        "type",
        "id",
        "title",
        "authors",
        "year",
        "venue",
        "status",
        "research_question",
        "core_claim",
        "current_reading_status",
        "blockers",
        "p0_dependencies",
        "p1_dependencies",
        "p2_dependencies",
        "p3_dependencies",
        "core_formulas",
        "benchmarks",
        "classical_methods",
        "related_sota",
        "evidence_notes",
        "formula_map",
        "experiment_predictions",
        "created",
        "updated",
    }

    def __post_init__(self) -> None:
        self.id = _record_id(self.id)
        self.title = _string(self.title, "title", required=True)
        self.authors = _strings(self.authors, "authors")
        self.year = _optional_int(self.year, "year")
        if self.year is not None and not 0 < self.year < 3000:
            raise ValidationError("year must be a plausible four-digit year")
        self.venue = _string(self.venue, "venue")
        self.status = _string(self.status, "status", default="planned").lower()
        self.research_question = _string(self.research_question, "research_question")
        self.core_claim = _string(self.core_claim, "core_claim")
        self.current_reading_status = _string(self.current_reading_status, "current_reading_status", default="not_started")
        self.blockers = [item if isinstance(item, BlockerRecord) else BlockerRecord.from_dict(item) for item in (self.blockers or [])]
        for priority in PRIORITIES:
            value = getattr(self, f"{priority.lower()}_dependencies")
            setattr(self, f"{priority.lower()}_dependencies", _strings(value, f"{priority} dependencies"))
        self.core_formulas = _strings(self.core_formulas, "core_formulas")
        self.benchmarks = _strings(self.benchmarks, "benchmarks")
        self.classical_methods = _strings(self.classical_methods, "classical_methods")
        self.related_sota = _strings(self.related_sota, "related_sota")
        if not isinstance(self.evidence_notes, list) or not all(isinstance(item, dict) for item in self.evidence_notes):
            raise ValidationError("evidence_notes must be a list of mappings")
        if not isinstance(self.formula_map, list) or not all(isinstance(item, dict) for item in self.formula_map):
            raise ValidationError("formula_map must be a list of mappings")
        if not isinstance(self.experiment_predictions, list) or not all(isinstance(item, dict) for item in self.experiment_predictions):
            raise ValidationError("experiment_predictions must be a list of mappings")
        for note in self.evidence_notes:
            if "kind" in note:
                EvidenceKind.parse(note["kind"])
        for formula in self.formula_map:
            level = formula.get("target_level")
            if level is not None and str(level).upper() not in {"L1", "L2", "L3", "L4", "L5"}:
                raise ValidationError("formula target_level must be L1, L2, L3, L4, or L5")
        self.created = _timestamp(self.created, "created")
        self.updated = _timestamp(self.updated, "updated")

    @classmethod
    def new(cls, id: str, title: str, authors: list[str] | None = None, year: int | None = None, venue: str = "") -> "PaperRecord":
        current = now_iso()
        return cls(id=id, title=title, authors=authors or [], year=year, venue=venue, created=current, updated=current)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperRecord":
        if not isinstance(data, dict):
            raise ValidationError("paper frontmatter must be a mapping")
        _validate_header(data, "paper")
        record = cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            year=data.get("year"),
            venue=data.get("venue", ""),
            status=data.get("status", "planned"),
            research_question=data.get("research_question", ""),
            core_claim=data.get("core_claim", ""),
            current_reading_status=data.get("current_reading_status", "not_started"),
            blockers=data.get("blockers", []),
            p0_dependencies=data.get("p0_dependencies", []),
            p1_dependencies=data.get("p1_dependencies", []),
            p2_dependencies=data.get("p2_dependencies", []),
            p3_dependencies=data.get("p3_dependencies", []),
            core_formulas=data.get("core_formulas", []),
            benchmarks=data.get("benchmarks", []),
            classical_methods=data.get("classical_methods", []),
            related_sota=data.get("related_sota", []),
            evidence_notes=data.get("evidence_notes", []),
            formula_map=data.get("formula_map", []),
            experiment_predictions=data.get("experiment_predictions", []),
            created=data.get("created") or now_iso(),
            updated=data.get("updated") or now_iso(),
            extra=_extra(data, cls._KNOWN),
        )
        record.validate()
        return record

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "type": "paper",
            "id": self.id,
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "venue": self.venue,
            "status": self.status,
            "research_question": self.research_question,
            "core_claim": self.core_claim,
            "current_reading_status": self.current_reading_status,
            "blockers": [item.to_dict() for item in self.blockers],
            "p0_dependencies": list(self.p0_dependencies),
            "p1_dependencies": list(self.p1_dependencies),
            "p2_dependencies": list(self.p2_dependencies),
            "p3_dependencies": list(self.p3_dependencies),
            "core_formulas": list(self.core_formulas),
            "benchmarks": list(self.benchmarks),
            "classical_methods": list(self.classical_methods),
            "related_sota": list(self.related_sota),
            "evidence_notes": list(self.evidence_notes),
            "formula_map": list(self.formula_map),
            "experiment_predictions": list(self.experiment_predictions),
            "created": self.created,
            "updated": self.updated,
        }
        result.update(self.extra)
        return result

    def validate(self) -> None:
        if self.status not in PAPER_STATUSES:
            raise ValidationError(f"paper status must be one of: {', '.join(sorted(PAPER_STATUSES))}")
        for blocker in self.blockers:
            blocker.validate()
        blocker_ids = [item.id for item in self.blockers]
        if len(blocker_ids) != len(set(blocker_ids)):
            raise ValidationError("paper blocker IDs must be unique")

    def add_blocker(self, blocker: BlockerRecord) -> None:
        if any(item.id == blocker.id for item in self.blockers):
            raise ValidationError(f"duplicate blocker id: {blocker.id}")
        self.blockers.append(blocker)
        if blocker.concept_id and blocker.concept_id not in getattr(self, f"{blocker.priority.lower()}_dependencies"):
            getattr(self, f"{blocker.priority.lower()}_dependencies").append(blocker.concept_id)
        self.status = "blocked" if blocker.priority == "P0" else self.status
        self.updated = now_iso()
        self.validate()

    def resolve_blocker(self, blocker_id: str) -> BlockerRecord:
        for blocker in self.blockers:
            if blocker.id == blocker_id:
                blocker.status = "resolved"
                blocker.resolved_at = now_iso()
                self.updated = now_iso()
                if not any(item.status == "open" and item.priority == "P0" for item in self.blockers):
                    if self.status == "blocked":
                        self.status = "reading"
                self.validate()
                return blocker
        raise ValidationError(f"blocker not found in paper {self.id}: {blocker_id}")

    def add_dependency(self, priority: str, dependency: str) -> None:
        canonical = DependencyPriority.parse(priority)
        dependency = _string(dependency, "dependency", required=True)
        target = getattr(self, f"{canonical.lower()}_dependencies")
        if dependency not in target:
            target.append(dependency)
        self.updated = now_iso()
        self.validate()


@dataclass
class MistakeRecord:
    id: str
    concept_id: str
    error_type: str
    severity: str = "medium"
    status: str = "unresolved"
    assistance: str = "A5"
    confidence: int = 50
    created: str = field(default_factory=now_iso)
    retest: str | None = None
    problem: str = ""
    my_answer: str = ""
    what_was_wrong: str = ""
    why_i_made_it: str = ""
    correct_mental_model: str = ""
    retest_question: str = ""
    updated: str = field(default_factory=now_iso)
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    _KNOWN: ClassVar[set[str]] = {
        "schema_version",
        "type",
        "id",
        "concept_id",
        "concept",
        "error_type",
        "severity",
        "status",
        "assistance",
        "confidence",
        "created",
        "retest",
        "problem",
        "my_answer",
        "what_was_wrong",
        "why_i_made_it",
        "correct_mental_model",
        "retest_question",
        "updated",
    }

    def __post_init__(self) -> None:
        self.id = _record_id(self.id)
        self.concept_id = _record_id(self.concept_id, "concept_id")
        self.error_type = _string(self.error_type, "error_type", required=True)
        self.severity = _string(self.severity, "severity", default="medium").lower()
        self.status = _string(self.status, "status", default="unresolved").lower()
        self.assistance = AssistanceLevel.parse(self.assistance)
        self.confidence = _confidence(self.confidence)
        self.created = _timestamp(self.created, "created")
        self.retest = _optional_timestamp(self.retest, "retest")
        self.updated = _timestamp(self.updated, "updated")
        for name in (
            "problem",
            "my_answer",
            "what_was_wrong",
            "why_i_made_it",
            "correct_mental_model",
            "retest_question",
        ):
            setattr(self, name, _string(getattr(self, name), name))

    @classmethod
    def new(cls, id: str, concept_id: str, error_type: str, **kwargs: Any) -> "MistakeRecord":
        current = now_iso()
        return cls(id=id, concept_id=concept_id, error_type=error_type, created=current, updated=current, **kwargs)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MistakeRecord":
        if not isinstance(data, dict):
            raise ValidationError("mistake frontmatter must be a mapping")
        _validate_header(data, "mistake")
        record = cls(
            id=data.get("id", ""),
            concept_id=data.get("concept_id", data.get("concept", "")),
            error_type=data.get("error_type", ""),
            severity=data.get("severity", "medium"),
            status=data.get("status", "unresolved"),
            assistance=data.get("assistance", "A5"),
            confidence=data.get("confidence", 50),
            created=data.get("created") or now_iso(),
            retest=data.get("retest"),
            problem=data.get("problem", ""),
            my_answer=data.get("my_answer", ""),
            what_was_wrong=data.get("what_was_wrong", ""),
            why_i_made_it=data.get("why_i_made_it", ""),
            correct_mental_model=data.get("correct_mental_model", ""),
            retest_question=data.get("retest_question", ""),
            updated=data.get("updated") or now_iso(),
            extra=_extra(data, cls._KNOWN),
        )
        record.validate()
        return record

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "type": "mistake",
            "id": self.id,
            "concept_id": self.concept_id,
            "error_type": self.error_type,
            "severity": self.severity,
            "status": self.status,
            "assistance": self.assistance,
            "confidence": self.confidence,
            "created": self.created,
            "retest": self.retest,
            "problem": self.problem,
            "my_answer": self.my_answer,
            "what_was_wrong": self.what_was_wrong,
            "why_i_made_it": self.why_i_made_it,
            "correct_mental_model": self.correct_mental_model,
            "retest_question": self.retest_question,
            "updated": self.updated,
        }
        result.update(self.extra)
        return result

    def validate(self) -> None:
        if self.status not in MISTAKE_STATUSES:
            raise ValidationError(f"mistake status must be one of: {', '.join(sorted(MISTAKE_STATUSES))}")
        if self.severity not in {"low", "medium", "high", "critical"}:
            raise ValidationError("mistake severity must be low, medium, high, or critical")

    def mark_resolved(self) -> None:
        self.status = "resolved"
        self.updated = now_iso()
        self.validate()


@dataclass
class SessionRecord:
    id: str
    mode: str
    status: str = "active"
    title: str = ""
    topic: str = ""
    concept_id: str | None = None
    paper_id: str | None = None
    goal: str = ""
    initial_belief: str = ""
    questions: list[dict[str, Any]] = field(default_factory=list)
    attempts: list[dict[str, Any]] = field(default_factory=list)
    hints: list[dict[str, Any]] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)
    a0_tests: list[dict[str, Any]] = field(default_factory=list)
    revised_understanding: str = ""
    reflection: str = ""
    next_action: str = ""
    started_at: str = field(default_factory=now_iso)
    finished_at: str | None = None
    updated: str = field(default_factory=now_iso)
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    _KNOWN: ClassVar[set[str]] = {
        "schema_version",
        "type",
        "id",
        "mode",
        "status",
        "title",
        "topic",
        "concept_id",
        "paper_id",
        "goal",
        "initial_belief",
        "questions",
        "attempts",
        "hints",
        "mistakes",
        "a0_tests",
        "revised_understanding",
        "reflection",
        "next_action",
        "started_at",
        "finished_at",
        "updated",
    }

    def __post_init__(self) -> None:
        self.id = _record_id(self.id)
        self.mode = _string(self.mode, "mode", required=True).lower()
        self.status = _string(self.status, "status", default="active").lower()
        self.title = _string(self.title, "title")
        self.topic = _string(self.topic, "topic")
        self.concept_id = _string(self.concept_id, "concept_id") if self.concept_id else None
        self.paper_id = _string(self.paper_id, "paper_id") if self.paper_id else None
        for name in ("goal", "initial_belief", "revised_understanding", "reflection", "next_action"):
            setattr(self, name, _string(getattr(self, name), name))
        for name in ("questions", "attempts", "hints", "a0_tests"):
            value = getattr(self, name)
            if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
                raise ValidationError(f"{name} must be a list of mappings")
        self.mistakes = _strings(self.mistakes, "mistakes")
        self.started_at = _timestamp(self.started_at, "started_at")
        self.finished_at = _optional_timestamp(self.finished_at, "finished_at")
        self.updated = _timestamp(self.updated, "updated")

    @classmethod
    def new(cls, id: str, mode: str, **kwargs: Any) -> "SessionRecord":
        current = now_iso()
        return cls(id=id, mode=mode, started_at=current, updated=current, **kwargs)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionRecord":
        if not isinstance(data, dict):
            raise ValidationError("session frontmatter must be a mapping")
        _validate_header(data, "session")
        record = cls(
            id=data.get("id", ""),
            mode=data.get("mode", ""),
            status=data.get("status", "active"),
            title=data.get("title", ""),
            topic=data.get("topic", ""),
            concept_id=data.get("concept_id"),
            paper_id=data.get("paper_id"),
            goal=data.get("goal", ""),
            initial_belief=data.get("initial_belief", ""),
            questions=data.get("questions", []),
            attempts=data.get("attempts", []),
            hints=data.get("hints", []),
            mistakes=data.get("mistakes", []),
            a0_tests=data.get("a0_tests", []),
            revised_understanding=data.get("revised_understanding", ""),
            reflection=data.get("reflection", ""),
            next_action=data.get("next_action", ""),
            started_at=data.get("started_at") or now_iso(),
            finished_at=data.get("finished_at"),
            updated=data.get("updated") or now_iso(),
            extra=_extra(data, cls._KNOWN),
        )
        record.validate()
        return record

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "type": "session",
            "id": self.id,
            "mode": self.mode,
            "status": self.status,
            "title": self.title,
            "topic": self.topic,
            "concept_id": self.concept_id,
            "paper_id": self.paper_id,
            "goal": self.goal,
            "initial_belief": self.initial_belief,
            "questions": list(self.questions),
            "attempts": list(self.attempts),
            "hints": list(self.hints),
            "mistakes": list(self.mistakes),
            "a0_tests": list(self.a0_tests),
            "revised_understanding": self.revised_understanding,
            "reflection": self.reflection,
            "next_action": self.next_action,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "updated": self.updated,
        }
        result.update(self.extra)
        return result

    def validate(self) -> None:
        if self.mode not in SESSION_MODES:
            raise ValidationError("session mode must be learning or research")
        if self.status not in SESSION_STATUSES:
            raise ValidationError("session status must be active, completed, or abandoned")
        if self.status == "completed" and not self.finished_at:
            raise ValidationError("completed sessions need finished_at")
        if self.concept_id and self.paper_id:
            raise ValidationError("a session may link to a concept or a paper, not both")

    def add_attempt(self, text: str, *, source: str = "learner") -> None:
        self.attempts.append({"timestamp": now_iso(), "source": source, "text": str(text).strip()})
        self.updated = now_iso()
        self.validate()

    def add_hint(self, level: str, text: str) -> None:
        self.hints.append({"timestamp": now_iso(), "assistance": AssistanceLevel.parse(level), "text": str(text).strip()})
        self.updated = now_iso()
        self.validate()

    def add_a0_test(self, evidence: A0Evidence) -> None:
        if any(item.get("evidence_id") == evidence.id for item in self.a0_tests):
            raise ValidationError(f"duplicate session evidence id: {evidence.id}")
        self.a0_tests.append(
            {
                "evidence_id": evidence.id,
                "dimension": evidence.dimension,
                "correct": evidence.correct,
                "assistance": evidence.assistance,
                "confidence": evidence.confidence,
                "novel_problem": evidence.novel_problem,
                "timestamp": evidence.timestamp,
            }
        )
        self.updated = now_iso()
        self.validate()

    def finish(self, *, reflection: str = "", next_action: str = "", revised_understanding: str = "") -> None:
        self.status = "completed"
        self.finished_at = now_iso()
        self.reflection = str(reflection or "").strip()
        self.next_action = str(next_action or "").strip()
        self.revised_understanding = str(revised_understanding or "").strip()
        self.updated = now_iso()
        self.validate()


@dataclass
class FoundationTrackRecord:
    id: str
    name: str
    status: str = "suggested"
    trigger: str = ""
    concepts: list[str] = field(default_factory=list)
    goal: str = ""
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    _KNOWN: ClassVar[set[str]] = {
        "schema_version",
        "type",
        "id",
        "name",
        "status",
        "trigger",
        "concepts",
        "goal",
        "created",
        "updated",
    }

    def __post_init__(self) -> None:
        self.id = _record_id(self.id)
        self.name = _string(self.name, "name", required=True)
        self.status = _string(self.status, "status", default="suggested").lower()
        self.trigger = _string(self.trigger, "trigger")
        self.concepts = _strings(self.concepts, "concepts")
        self.goal = _string(self.goal, "goal")
        self.created = _timestamp(self.created, "created")
        self.updated = _timestamp(self.updated, "updated")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FoundationTrackRecord":
        if not isinstance(data, dict):
            raise ValidationError("foundation track frontmatter must be a mapping")
        _validate_header(data, "foundation_track")
        record = cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            status=data.get("status", "suggested"),
            trigger=data.get("trigger", ""),
            concepts=data.get("concepts", []),
            goal=data.get("goal", ""),
            created=data.get("created") or now_iso(),
            updated=data.get("updated") or now_iso(),
            extra=_extra(data, cls._KNOWN),
        )
        record.validate()
        return record

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "type": "foundation_track",
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "trigger": self.trigger,
            "concepts": list(self.concepts),
            "goal": self.goal,
            "created": self.created,
            "updated": self.updated,
        }
        result.update(self.extra)
        return result

    def validate(self) -> None:
        if self.status not in FOUNDATION_STATUSES:
            raise ValidationError(f"foundation status must be one of: {', '.join(sorted(FOUNDATION_STATUSES))}")
