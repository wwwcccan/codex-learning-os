from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .errors import ValidationError
from .models import (
    ASSISTANCE_LEVELS,
    CONCEPT_DIMENSIONS,
    A0Evidence,
    ConceptRecord,
)
from .utils import iso_after, parse_datetime, slugify


MASTERY_THRESHOLDS: dict[str, int] = {
    "recall": 4,
    "explanation": 4,
    "derivation": 4,
    "transfer": 4,
    "debug": 3,
}
MIN_A0_SUCCESS_DATES = 3
FOUNDATION_BLOCKER_THRESHOLD = 3


def mastery_eligible(concept: ConceptRecord) -> bool:
    """Pure policy function kept separate so it can be tested independently."""

    return concept.mastery_eligible()


class ReviewScheduler(Protocol):
    def next_review(self, *, now: str, a0_successes: int, correct: bool) -> str:
        """Return the next review timestamp for one assessment event."""


@dataclass(frozen=True)
class FixedIntervalScheduler:
    """Transparent fallback scheduler; replaceable by FSRS later."""

    success_intervals_days: tuple[int, ...] = (1, 3, 7, 14, 30, 60)
    failure_interval_days: int = 1

    def next_review(self, *, now: str, a0_successes: int, correct: bool) -> str:
        if not correct:
            return iso_after(now, days=self.failure_interval_days)
        index = max(0, min(a0_successes - 1, len(self.success_intervals_days) - 1))
        return iso_after(now, days=self.success_intervals_days[index])


def apply_a0_evidence(
    concept: ConceptRecord,
    evidence: A0Evidence,
    *,
    scheduler: ReviewScheduler | None = None,
) -> None:
    """Apply a learner evidence event using deterministic state transitions."""

    if any(item.id == evidence.id for item in concept.a0_evidence):
        raise ValueError(f"duplicate evidence id: {evidence.id}")
    concept.a0_evidence.append(evidence)
    concept.refresh_derived()
    scheduler = scheduler or FixedIntervalScheduler()
    concept.last_review = evidence.timestamp
    concept.next_review = scheduler.next_review(
        now=evidence.timestamp,
        a0_successes=concept.a0_successes,
        correct=evidence.is_a0_success,
    )
    concept.refresh_derived()
    concept.validate()


def weak_dimensions(concept: ConceptRecord, *, threshold: int = 4) -> list[str]:
    return [dimension for dimension in CONCEPT_DIMENSIONS if getattr(concept, dimension) < threshold]


def _normal_key(value: str) -> str:
    return slugify(" ".join(value.lower().split()))


def repeated_blockers(repo: Any, *, threshold: int = FOUNDATION_BLOCKER_THRESHOLD) -> list[dict[str, Any]]:
    """Aggregate blocker history by concept ID or normalized label.

    Count is the number of distinct papers, preventing two duplicate entries in
    one paper from pretending to be cross-paper structural evidence.
    """

    if threshold < 1:
        raise ValidationError("blocker threshold must be at least 1")
    grouped: dict[str, dict[str, Any]] = {}
    for paper in repo.records("paper"):
        seen_in_paper: set[str] = set()
        for blocker in paper.blockers:
            key = blocker.concept_id or f"label:{_normal_key(blocker.label)}"
            if key in seen_in_paper:
                continue
            seen_in_paper.add(key)
            item = grouped.setdefault(
                key,
                {
                    "key": key,
                    "label": blocker.label,
                    "type": blocker.type,
                    "count": 0,
                    "papers": [],
                    "concepts": [],
                    "foundation_tracks": [],
                    "statuses": [],
                },
            )
            item["count"] += 1
            item["papers"].append(paper.id)
            if blocker.concept_id and blocker.concept_id not in item["concepts"]:
                item["concepts"].append(blocker.concept_id)
            if blocker.foundation_track and blocker.foundation_track not in item["foundation_tracks"]:
                item["foundation_tracks"].append(blocker.foundation_track)
            item["statuses"].append(blocker.status)
    return sorted(
        (item for item in grouped.values() if item["count"] >= threshold),
        key=lambda item: (-item["count"], item["key"]),
    )


def foundation_candidates(repo: Any, *, threshold: int = FOUNDATION_BLOCKER_THRESHOLD) -> list[dict[str, Any]]:
    """Find cross-concept or cross-paper patterns that justify a foundation track."""

    if threshold < 1:
        raise ValidationError("foundation threshold must be at least 1")
    concept_by_id = {concept.id: concept for concept in repo.records("concept")}
    grouped: dict[str, dict[str, Any]] = {}
    for paper in repo.records("paper"):
        seen_in_paper: set[str] = set()
        for blocker in paper.blockers:
            concept = concept_by_id.get(blocker.concept_id or "")
            track = blocker.foundation_track or (concept.domain if concept else "")
            if not track:
                continue
            key = _normal_key(track)
            if key in seen_in_paper:
                continue
            seen_in_paper.add(key)
            item = grouped.setdefault(
                key,
                {
                    "track": track,
                    "count": 0,
                    "papers": [],
                    "concepts": [],
                    "blocker_labels": [],
                },
            )
            item["count"] += 1
            if paper.id not in item["papers"]:
                item["papers"].append(paper.id)
            if blocker.concept_id and blocker.concept_id not in item["concepts"]:
                item["concepts"].append(blocker.concept_id)
            if blocker.label not in item["blocker_labels"]:
                item["blocker_labels"].append(blocker.label)
    return sorted(
        (
            item
            for item in grouped.values()
            if item["count"] >= threshold and (len(item["concepts"]) >= 2 or len(item["blocker_labels"]) >= 2)
        ),
        key=lambda item: (-item["count"], _normal_key(item["track"])),
    )


def a0_statistics(repo: Any) -> dict[str, Any]:
    all_evidence: list[A0Evidence] = []
    for concept in repo.records("concept"):
        all_evidence.extend(concept.a0_evidence)
    a0_attempts = [item for item in all_evidence if item.assistance == "A0"]
    a0_successes = [item for item in a0_attempts if item.correct]
    assisted_successes = [item for item in all_evidence if item.correct and item.assistance != "A0"]
    by_assistance = {level: sum(item.correct for item in all_evidence if item.assistance == level) for level in ASSISTANCE_LEVELS}
    return {
        "all_evidence": len(all_evidence),
        "a0_attempts": len(a0_attempts),
        "a0_successes": len(a0_successes),
        "a0_success_rate": (len(a0_successes) / len(a0_attempts)) if a0_attempts else None,
        "assisted_successes": len(assisted_successes),
        "successes_by_assistance": by_assistance,
    }


def ai_dependency_statistics(repo: Any) -> dict[str, Any]:
    concepts = repo.records("concept")
    required = [concept.assistance_required for concept in concepts if concept.a0_evidence]
    distribution = {level: required.count(level) for level in ASSISTANCE_LEVELS}
    independent = sum(level == "A0" for level in required)
    return {
        "concepts_with_evidence": len(required),
        "concepts_independent_at_a0": independent,
        "independence_rate": (independent / len(required)) if required else None,
        "minimum_assistance_distribution": distribution,
    }


def due_reviews(repo: Any, *, now: str | None = None) -> list[ConceptRecord]:
    current = datetime.now().astimezone() if now is None else parse_datetime(now)
    result: list[ConceptRecord] = []
    for concept in repo.records("concept"):
        if concept.next_review:
            next_dt = parse_datetime(concept.next_review)
            if next_dt <= current:
                result.append(concept)
    return sorted(result, key=lambda item: item.next_review or "")
