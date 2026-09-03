from __future__ import annotations

from typing import Any

from .errors import ValidationError
from .models import (
    A0Evidence,
    AssessmentEntry,
    BlockerRecord,
    ConceptRecord,
    EvidenceKind,
    Dimension,
    FoundationTrackRecord,
    MistakeRecord,
    PaperRecord,
    SessionRecord,
)
from .policies import (
    FOUNDATION_BLOCKER_THRESHOLD,
    FixedIntervalScheduler,
    a0_statistics,
    ai_dependency_statistics,
    apply_a0_evidence,
    due_reviews,
    foundation_candidates,
    repeated_blockers,
)
from .repository import VaultRepository
from .utils import new_id, now_iso


def create_concept(
    repo: VaultRepository,
    *,
    concept_id: str,
    name: str,
    domain: str,
    prerequisites: list[str] | None = None,
    body: str | None = None,
) -> ConceptRecord:
    record = ConceptRecord.new(concept_id, name, domain, prerequisites)
    repo.create("concept", record, body=body)
    return record


def update_concept(
    repo: VaultRepository,
    concept_id: str,
    scores: dict[str, int] | None = None,
    *,
    assistance: str = "A0",
    status: str | None = None,
    note: str = "",
) -> ConceptRecord:
    record, body, _ = repo.load_document("concept", concept_id)
    if scores:
        record.update_scores(scores, assistance=assistance, note=note)
    if status is not None:
        candidate = status.lower()
        if candidate == "mastered" and not record.mastery_eligible():
            raise ValidationError("cannot manually mark a concept mastered before the A0 mastery gate")
        record.status = candidate
    record.refresh_derived()
    record.validate()
    repo.save("concept", record, body=body)
    return record


def record_a0(
    repo: VaultRepository,
    concept_id: str,
    *,
    dimension: str,
    correct: bool,
    assistance: str = "A0",
    confidence: int = 50,
    novel_problem: bool = False,
    timestamp: str | None = None,
    session_id: str | None = None,
    note: str = "",
    score: int | None = None,
) -> tuple[ConceptRecord, A0Evidence]:
    linked_session: tuple[SessionRecord, str] | None = None
    if session_id:
        session, session_body, _ = repo.load_document("session", session_id)
        if session.concept_id not in {None, concept_id}:
            raise ValidationError(f"session {session_id} is linked to {session.concept_id}, not {concept_id}")
        linked_session = (session, session_body)
    concept, concept_body, _ = repo.load_document("concept", concept_id)
    evidence = A0Evidence(
        dimension=dimension,
        correct=correct,
        assistance=assistance,
        confidence=confidence,
        novel_problem=novel_problem,
        timestamp=timestamp or now_iso(),
        session_id=session_id,
        note=note,
    )
    apply_a0_evidence(concept, evidence, scheduler=FixedIntervalScheduler())
    if score is not None:
        # An explicit score is a learner/mentor assessment. The evidence
        # record remains the proof of correctness; it is not inferred by code.
        concept.update_scores({evidence.dimension: score}, assistance=assistance, note=note)
    repo.save("concept", concept, body=concept_body)
    if linked_session:
        session, session_body = linked_session
        session.add_a0_test(evidence)
        repo.save("session", session, body=session_body)
    return concept, evidence


def record_assessment(
    repo: VaultRepository,
    concept_id: str,
    *,
    dimension: str,
    score: int,
    assistance: str = "A0",
    confidence: int | None = None,
    note: str = "",
) -> ConceptRecord:
    concept, body, _ = repo.load_document("concept", concept_id)
    timestamp = now_iso()
    canonical_dimension = Dimension.parse(dimension)
    concept.assessments.append(
        AssessmentEntry(
            dimension=canonical_dimension,
            score=score,
            assistance=assistance,
            confidence=confidence,
            timestamp=timestamp,
            note=note,
        )
    )
    setattr(concept, canonical_dimension, score)
    concept.refresh_derived()
    concept.validate()
    repo.save("concept", concept, body=body)
    return concept


def create_paper(
    repo: VaultRepository,
    *,
    paper_id: str,
    title: str,
    authors: list[str] | None = None,
    year: int | None = None,
    venue: str = "",
    body: str | None = None,
) -> PaperRecord:
    record = PaperRecord.new(paper_id, title, authors, year, venue)
    repo.create("paper", record, body=body)
    return record


def add_blocker(
    repo: VaultRepository,
    paper_id: str,
    *,
    blocker_type: str,
    label: str,
    priority: str = "P0",
    description: str = "",
    concept_id: str | None = None,
    foundation_track: str | None = None,
    blocker_id: str | None = None,
) -> tuple[PaperRecord, BlockerRecord]:
    if concept_id:
        repo.load("concept", concept_id)
    paper, body, _ = repo.load_document("paper", paper_id)
    blocker = BlockerRecord(
        id=blocker_id or new_id("blocker"),
        type=blocker_type,
        label=label,
        description=description,
        priority=priority,
        concept_id=concept_id,
        foundation_track=foundation_track,
    )
    paper.add_blocker(blocker)
    repo.save("paper", paper, body=body)
    return paper, blocker


def resolve_blocker(repo: VaultRepository, paper_id: str, blocker_id: str) -> PaperRecord:
    paper, body, _ = repo.load_document("paper", paper_id)
    paper.resolve_blocker(blocker_id)
    repo.save("paper", paper, body=body)
    return paper


def add_dependency(repo: VaultRepository, paper_id: str, *, priority: str, dependency: str) -> PaperRecord:
    paper, body, _ = repo.load_document("paper", paper_id)
    paper.add_dependency(priority, dependency)
    repo.save("paper", paper, body=body)
    return paper


def add_paper_evidence(
    repo: VaultRepository,
    paper_id: str,
    *,
    kind: str,
    statement: str,
    source: str = "",
    note: str = "",
) -> tuple[PaperRecord, dict[str, Any]]:
    paper, body, _ = repo.load_document("paper", paper_id)
    entry = {
        "id": new_id("evidence"),
        "kind": EvidenceKind.parse(kind),
        "statement": str(statement).strip(),
        "source": str(source or "").strip(),
        "timestamp": now_iso(),
    }
    if note:
        entry["note"] = str(note).strip()
    if not entry["statement"]:
        raise ValidationError("evidence statement is required")
    paper.evidence_notes.append(entry)
    paper.updated = now_iso()
    paper.validate()
    repo.save("paper", paper, body=body)
    return paper, entry


def add_formula(
    repo: VaultRepository,
    paper_id: str,
    *,
    formula_id: str,
    label: str,
    target_level: str,
    notes: str = "",
) -> PaperRecord:
    level = str(target_level).strip().upper()
    if level not in {"L1", "L2", "L3", "L4", "L5"}:
        raise ValidationError("formula target_level must be L1, L2, L3, L4, or L5")
    formula_id = str(formula_id).strip()
    label = str(label).strip()
    if not formula_id or not label:
        raise ValidationError("formula id and label are required")
    paper, body, _ = repo.load_document("paper", paper_id)
    if any(item.get("id") == formula_id for item in paper.formula_map):
        raise ValidationError(f"duplicate formula id on paper {paper_id}: {formula_id}")
    paper.formula_map.append(
        {
            "id": formula_id,
            "label": str(label).strip(),
            "target_level": level,
            "status": "not_started",
            "notes": str(notes or "").strip(),
        }
    )
    paper.updated = now_iso()
    paper.validate()
    repo.save("paper", paper, body=body)
    return paper


def add_prediction(
    repo: VaultRepository,
    paper_id: str,
    *,
    hypothesis: str,
    prediction: str,
    expected_result: str = "",
    expected_failure: str = "",
    falsification_condition: str = "",
    competing_explanations: str = "",
    prediction_id: str | None = None,
) -> tuple[PaperRecord, dict[str, Any]]:
    paper, body, _ = repo.load_document("paper", paper_id)
    entry = {
        "id": prediction_id or new_id("prediction"),
        "status": "planned",
        "hypothesis": str(hypothesis).strip(),
        "prediction": str(prediction).strip(),
        "expected_result": str(expected_result or "").strip(),
        "expected_failure": str(expected_failure or "").strip(),
        "falsification_condition": str(falsification_condition or "").strip(),
        "competing_explanations": str(competing_explanations or "").strip(),
        "created": now_iso(),
    }
    if not entry["hypothesis"] or not entry["prediction"]:
        raise ValidationError("hypothesis and prediction are required")
    paper.experiment_predictions.append(entry)
    paper.updated = now_iso()
    paper.validate()
    repo.save("paper", paper, body=body)
    return paper, entry


def observe_prediction(
    repo: VaultRepository,
    paper_id: str,
    prediction_id: str,
    *,
    observation: str,
    prediction_match: str = "unknown",
    unexpected_result: str = "",
    possible_causes: str = "",
    next_discriminating_experiment: str = "",
) -> PaperRecord:
    paper, body, _ = repo.load_document("paper", paper_id)
    for entry in paper.experiment_predictions:
        if entry.get("id") == prediction_id:
            match = str(prediction_match).strip().lower()
            if match not in {"yes", "no", "partial", "unknown"}:
                raise ValidationError("prediction_match must be yes, no, partial, or unknown")
            entry.update(
                {
                    "status": "observed",
                    "observation": str(observation).strip(),
                    "prediction_match": match,
                    "unexpected_result": str(unexpected_result or "").strip(),
                    "possible_causes": str(possible_causes or "").strip(),
                    "next_discriminating_experiment": str(next_discriminating_experiment or "").strip(),
                    "observed_at": now_iso(),
                }
            )
            if not entry["observation"]:
                raise ValidationError("observation is required")
            paper.updated = now_iso()
            paper.validate()
            repo.save("paper", paper, body=body)
            return paper
    raise ValidationError(f"prediction not found on paper {paper_id}: {prediction_id}")


def dependency_map(repo: VaultRepository, paper_id: str) -> dict[str, Any]:
    paper = repo.load("paper", paper_id)
    return {
        "paper_id": paper.id,
        "title": paper.title,
        "priorities": {
            "P0": list(paper.p0_dependencies),
            "P1": list(paper.p1_dependencies),
            "P2": list(paper.p2_dependencies),
            "P3": list(paper.p3_dependencies),
        },
        "blockers": [
            {
                "id": blocker.id,
                "type": blocker.type,
                "label": blocker.label,
                "priority": blocker.priority,
                "status": blocker.status,
                "concept_id": blocker.concept_id,
            }
            for blocker in paper.blockers
        ],
        "next_action": "repair P0 dependencies before returning to the paper"
        if paper.p0_dependencies
        else "return to the paper and run an A0 explanation check",
    }


def create_mistake(
    repo: VaultRepository,
    *,
    mistake_id: str,
    concept_id: str,
    error_type: str,
    severity: str = "medium",
    assistance: str = "A5",
    confidence: int = 50,
    retest: str | None = None,
    fields: dict[str, str] | None = None,
    body: str | None = None,
) -> MistakeRecord:
    repo.load("concept", concept_id)
    record = MistakeRecord.new(
        mistake_id,
        concept_id,
        error_type,
        severity=severity,
        assistance=assistance,
        confidence=confidence,
        retest=retest,
        **(fields or {}),
    )
    repo.create("mistake", record, body=body)
    return record


def resolve_mistake(repo: VaultRepository, mistake_id: str) -> MistakeRecord:
    record, body, _ = repo.load_document("mistake", mistake_id)
    record.mark_resolved()
    repo.save("mistake", record, body=body)
    return record


def start_session(
    repo: VaultRepository,
    *,
    session_id: str,
    mode: str,
    title: str = "",
    topic: str = "",
    concept_id: str | None = None,
    paper_id: str | None = None,
    goal: str = "",
    initial_belief: str = "",
    body: str | None = None,
) -> SessionRecord:
    if concept_id:
        repo.load("concept", concept_id)
    if paper_id:
        repo.load("paper", paper_id)
    record = SessionRecord.new(
        session_id,
        mode,
        title=title,
        topic=topic,
        concept_id=concept_id,
        paper_id=paper_id,
        goal=goal,
        initial_belief=initial_belief,
    )
    repo.create("session", record, body=body)
    return record


def add_session_attempt(repo: VaultRepository, session_id: str, text: str, *, source: str = "learner") -> SessionRecord:
    record, body, _ = repo.load_document("session", session_id)
    record.add_attempt(text, source=source)
    repo.save("session", record, body=body)
    return record


def add_session_hint(repo: VaultRepository, session_id: str, level: str, text: str) -> SessionRecord:
    record, body, _ = repo.load_document("session", session_id)
    record.add_hint(level, text)
    repo.save("session", record, body=body)
    return record


def add_session_a0(repo: VaultRepository, session_id: str, evidence: A0Evidence, *, expected_concept: str | None = None) -> SessionRecord:
    record, body, _ = repo.load_document("session", session_id)
    if expected_concept and record.concept_id not in {None, expected_concept}:
        raise ValidationError(f"session {session_id} is linked to {record.concept_id}, not {expected_concept}")
    record.add_a0_test(evidence)
    repo.save("session", record, body=body)
    return record


def add_session_mistake(repo: VaultRepository, session_id: str, mistake_id: str) -> SessionRecord:
    repo.load("mistake", mistake_id)
    record, body, _ = repo.load_document("session", session_id)
    if mistake_id not in record.mistakes:
        record.mistakes.append(mistake_id)
    record.updated = now_iso()
    record.validate()
    repo.save("session", record, body=body)
    return record


def finish_session(
    repo: VaultRepository,
    session_id: str,
    *,
    reflection: str = "",
    next_action: str = "",
    revised_understanding: str = "",
) -> SessionRecord:
    record, body, _ = repo.load_document("session", session_id)
    record.finish(reflection=reflection, next_action=next_action, revised_understanding=revised_understanding)
    repo.save("session", record, body=body)
    return record


def create_foundation_track(
    repo: VaultRepository,
    *,
    track_id: str,
    name: str,
    trigger: str = "",
    concepts: list[str] | None = None,
    goal: str = "",
    status: str = "suggested",
    body: str | None = None,
) -> FoundationTrackRecord:
    for concept_id in concepts or []:
        repo.load("concept", concept_id)
    record = FoundationTrackRecord(
        id=track_id,
        name=name,
        trigger=trigger,
        concepts=concepts or [],
        goal=goal,
        status=status,
    )
    repo.create("foundation", record, body=body)
    return record


def dashboard_snapshot(repo: VaultRepository, *, now: str | None = None) -> dict[str, Any]:
    concepts = repo.records("concept")
    papers = repo.records("paper")
    mistakes = repo.records("mistake")
    sessions = repo.records("session")
    due = due_reviews(repo, now=now)
    weak = sorted(
        (
            {
                "id": concept.id,
                "name": concept.name,
                "weakness": list(concept.weakness),
                "scores": {dimension: getattr(concept, dimension) for dimension in ("recall", "explanation", "derivation", "transfer", "debug")},
                "assistance_required": concept.assistance_required,
            }
            for concept in concepts
            if concept.status != "archived" and concept.weakness
        ),
        key=lambda item: (len(item["weakness"]), item["id"]),
        reverse=True,
    )
    unresolved = [
        {"id": mistake.id, "concept_id": mistake.concept_id, "error_type": mistake.error_type, "severity": mistake.severity}
        for mistake in mistakes
        if mistake.status in {"unresolved", "retesting"}
    ]
    return {
        "counts": {
            "concepts": len(concepts),
            "papers": len(papers),
            "mistakes": len(mistakes),
            "sessions": len(sessions),
        },
        "due_reviews": [
            {"id": concept.id, "name": concept.name, "next_review": concept.next_review} for concept in due
        ],
        "weak_concepts": weak,
        "unresolved_mistakes": unresolved,
        "repeated_blockers": repeated_blockers(repo),
        "ai_dependency": ai_dependency_statistics(repo),
        "a0": a0_statistics(repo),
        "foundation_track_candidates": foundation_candidates(repo),
    }
