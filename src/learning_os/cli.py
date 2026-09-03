from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .errors import LearningOSError, ValidationError
from .models import ASSISTANCE_LEVELS, BLOCKER_TYPES, CONCEPT_DIMENSIONS, EVIDENCE_KINDS, PRIORITIES
from .repository import VaultRepository
from .services import (
    add_blocker,
    add_dependency,
    add_session_attempt,
    add_session_hint,
    add_session_mistake,
    create_concept,
    create_foundation_track,
    create_mistake,
    create_paper,
    dashboard_snapshot,
    dependency_map,
    add_formula,
    add_paper_evidence,
    add_prediction,
    observe_prediction,
    finish_session,
    record_a0,
    record_assessment,
    resolve_blocker,
    resolve_mistake,
    start_session,
    update_concept,
)
from .policies import due_reviews


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="learning-os",
        description="Markdown-first personal AI learning and research training system",
    )
    parser.add_argument("--vault", default=".", help="vault/project root (default: current directory)")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init", help="create the Markdown vault directories")

    concept = commands.add_parser("concept", help="manage learning concepts")
    concept_actions = concept.add_subparsers(dest="action", required=True)
    create = concept_actions.add_parser("create", help="create a concept Markdown file")
    create.add_argument("id")
    create.add_argument("--name", required=True)
    create.add_argument("--domain", required=True)
    create.add_argument("--prerequisite", action="append", default=[])
    create.add_argument("--body")
    show = concept_actions.add_parser("show", help="show a concept")
    show.add_argument("id")
    show.add_argument("--json", action="store_true")
    update = concept_actions.add_parser("update", help="update dimension scores and status")
    update.add_argument("id")
    _add_score_flags(update)
    update.add_argument("--score", action="append", default=[], metavar="DIMENSION=SCORE")
    update.add_argument("--assistance", choices=ASSISTANCE_LEVELS, default="A0")
    update.add_argument("--status", choices=["inbox", "learning", "review", "mastered", "archived"])
    update.add_argument("--note", default="")
    validate_concept = concept_actions.add_parser("validate", help="validate one or all concept records")
    validate_concept.add_argument("id", nargs="?")
    concept_list = concept_actions.add_parser("list", help="list concepts")
    concept_list.add_argument("--json", action="store_true")

    paper = commands.add_parser("paper", help="manage research papers and blockers")
    paper_actions = paper.add_subparsers(dest="action", required=True)
    create_paper_parser = paper_actions.add_parser("create", help="create a paper Markdown file")
    create_paper_parser.add_argument("id")
    create_paper_parser.add_argument("--title", required=True)
    create_paper_parser.add_argument("--author", action="append", default=[])
    create_paper_parser.add_argument("--year", type=int)
    create_paper_parser.add_argument("--venue", default="")
    create_paper_parser.add_argument("--body")
    show_paper = paper_actions.add_parser("show", help="show a paper")
    show_paper.add_argument("id")
    show_paper.add_argument("--json", action="store_true")
    paper_list = paper_actions.add_parser("list", help="list papers")
    paper_list.add_argument("--json", action="store_true")
    blocker = paper_actions.add_parser("blocker", help="add or resolve a paper blocker")
    blocker_actions = blocker.add_subparsers(dest="blocker_action", required=True)
    blocker_add = blocker_actions.add_parser("add")
    blocker_add.add_argument("paper_id")
    blocker_add.add_argument("--type", required=True, choices=BLOCKER_TYPES + ("prerequisite",))
    blocker_add.add_argument("--label", required=True)
    blocker_add.add_argument("--priority", choices=PRIORITIES, default="P0")
    blocker_add.add_argument("--description", default="")
    blocker_add.add_argument("--concept")
    blocker_add.add_argument("--foundation-track")
    blocker_add.add_argument("--id", dest="blocker_id")
    blocker_resolve = blocker_actions.add_parser("resolve")
    blocker_resolve.add_argument("paper_id")
    blocker_resolve.add_argument("blocker_id")
    dependency = paper_actions.add_parser("dependency", help="add a dependency to a priority bucket")
    dependency.add_argument("paper_id")
    dependency.add_argument("--priority", choices=PRIORITIES, required=True)
    dependency.add_argument("--dependency", required=True)
    paper_map = paper_actions.add_parser("map", help="print a paper dependency map")
    paper_map.add_argument("paper_id")
    paper_map.add_argument("--json", action="store_true")
    evidence = paper_actions.add_parser("evidence", help="record a labeled research evidence note")
    evidence.add_argument("paper_id")
    evidence.add_argument("--kind", required=True, choices=EVIDENCE_KINDS)
    evidence.add_argument("--statement", required=True)
    evidence.add_argument("--source", default="")
    evidence.add_argument("--note", default="")
    formula = paper_actions.add_parser("formula", help="record target depth for a core formula")
    formula.add_argument("paper_id")
    formula.add_argument("--id", dest="formula_id", required=True)
    formula.add_argument("--label", required=True)
    formula.add_argument("--target-level", required=True, choices=["L1", "L2", "L3", "L4", "L5"])
    formula.add_argument("--notes", default="")
    prediction = paper_actions.add_parser("prediction", help="record predictions before experiments")
    prediction_actions = prediction.add_subparsers(dest="prediction_action", required=True)
    prediction_add = prediction_actions.add_parser("add")
    prediction_add.add_argument("paper_id")
    prediction_add.add_argument("--hypothesis", required=True)
    prediction_add.add_argument("--prediction", required=True)
    prediction_add.add_argument("--expected-result", default="")
    prediction_add.add_argument("--expected-failure", default="")
    prediction_add.add_argument("--falsification-condition", default="")
    prediction_add.add_argument("--competing-explanations", default="")
    prediction_add.add_argument("--id", dest="prediction_id")
    prediction_observe = prediction_actions.add_parser("observe")
    prediction_observe.add_argument("paper_id")
    prediction_observe.add_argument("prediction_id")
    prediction_observe.add_argument("--observation", required=True)
    prediction_observe.add_argument("--prediction-match", default="unknown", choices=["yes", "no", "partial", "unknown"])
    prediction_observe.add_argument("--unexpected-result", default="")
    prediction_observe.add_argument("--possible-causes", default="")
    prediction_observe.add_argument("--next-discriminating-experiment", default="")

    mistake = commands.add_parser("mistake", help="manage cognitive bugs")
    mistake_actions = mistake.add_subparsers(dest="action", required=True)
    create_mistake_parser = mistake_actions.add_parser("create")
    create_mistake_parser.add_argument("id")
    create_mistake_parser.add_argument("--concept", required=True, dest="concept_id")
    create_mistake_parser.add_argument("--error-type", required=True)
    create_mistake_parser.add_argument("--severity", choices=["low", "medium", "high", "critical"], default="medium")
    create_mistake_parser.add_argument("--assistance", choices=ASSISTANCE_LEVELS, default="A5")
    create_mistake_parser.add_argument("--confidence", type=int, default=50)
    create_mistake_parser.add_argument("--retest")
    for option, dest in (
        ("problem", "problem"),
        ("my-answer", "my_answer"),
        ("what-was-wrong", "what_was_wrong"),
        ("why-i-made-it", "why_i_made_it"),
        ("correct-mental-model", "correct_mental_model"),
        ("retest-question", "retest_question"),
    ):
        create_mistake_parser.add_argument(f"--{option}", dest=dest, default="")
    create_mistake_parser.add_argument("--body")
    show_mistake = mistake_actions.add_parser("show")
    show_mistake.add_argument("id")
    show_mistake.add_argument("--json", action="store_true")
    resolve_mistake_parser = mistake_actions.add_parser("resolve")
    resolve_mistake_parser.add_argument("id")
    mistake_list = mistake_actions.add_parser("list")
    mistake_list.add_argument("--json", action="store_true")
    link_mistake = mistake_actions.add_parser("link")
    link_mistake.add_argument("session_id")
    link_mistake.add_argument("mistake_id")

    session = commands.add_parser("session", help="record learning/research process")
    session_actions = session.add_subparsers(dest="action", required=True)
    session_start = session_actions.add_parser("start")
    session_start.add_argument("id")
    session_start.add_argument("--mode", required=True, choices=["learning", "research"])
    session_start.add_argument("--title", default="")
    session_start.add_argument("--topic", default="")
    session_start.add_argument("--concept", dest="concept_id")
    session_start.add_argument("--paper", dest="paper_id")
    session_start.add_argument("--goal", default="")
    session_start.add_argument("--initial-belief", default="")
    session_start.add_argument("--body")
    session_show = session_actions.add_parser("show")
    session_show.add_argument("id")
    session_show.add_argument("--json", action="store_true")
    session_list = session_actions.add_parser("list")
    session_list.add_argument("--json", action="store_true")
    session_attempt = session_actions.add_parser("attempt")
    session_attempt.add_argument("id")
    session_attempt.add_argument("--text", required=True)
    session_attempt.add_argument("--source", default="learner")
    session_hint = session_actions.add_parser("hint")
    session_hint.add_argument("id")
    session_hint.add_argument("--level", required=True, choices=ASSISTANCE_LEVELS)
    session_hint.add_argument("--text", required=True)
    session_a0 = session_actions.add_parser("a0")
    session_a0.add_argument("id")
    session_a0.add_argument("--concept", dest="concept_id")
    _add_a0_flags(session_a0)
    session_finish = session_actions.add_parser("finish")
    session_finish.add_argument("id")
    session_finish.add_argument("--reflection", default="")
    session_finish.add_argument("--next-action", default="")
    session_finish.add_argument("--revised-understanding", default="")

    a0 = commands.add_parser("a0", help="record independent-performance evidence")
    a0_actions = a0.add_subparsers(dest="action", required=True)
    a0_record = a0_actions.add_parser("record")
    a0_record.add_argument("concept_id")
    _add_a0_flags(a0_record, include_session=True)

    assessment = commands.add_parser("assessment", help="record a five-dimension assessment")
    assessment_actions = assessment.add_subparsers(dest="action", required=True)
    assessment_record = assessment_actions.add_parser("record")
    assessment_record.add_argument("concept_id")
    assessment_record.add_argument("--dimension", required=True, choices=CONCEPT_DIMENSIONS)
    assessment_record.add_argument("--score", required=True, type=int)
    assessment_record.add_argument("--assistance", choices=ASSISTANCE_LEVELS, default="A0")
    assessment_record.add_argument("--confidence", type=int)
    assessment_record.add_argument("--note", default="")

    review = commands.add_parser("review", help="show concepts whose review is due")
    review.add_argument("--json", action="store_true")
    dashboard = commands.add_parser("dashboard", help="show current learning/research dashboard")
    dashboard.add_argument("--json", action="store_true")
    foundation = commands.add_parser("foundation", help="suggest or create foundation tracks")
    foundation_actions = foundation.add_subparsers(dest="action", required=True)
    foundation_suggest = foundation_actions.add_parser("suggest")
    foundation_suggest.add_argument("--threshold", type=int, default=3)
    foundation_suggest.add_argument("--json", action="store_true")
    foundation_create = foundation_actions.add_parser("create")
    foundation_create.add_argument("id")
    foundation_create.add_argument("--name", required=True)
    foundation_create.add_argument("--trigger", default="")
    foundation_create.add_argument("--concept", action="append", default=[])
    foundation_create.add_argument("--goal", default="")
    foundation_create.add_argument("--status", choices=["suggested", "active", "completed", "archived"], default="suggested")
    foundation_create.add_argument("--body")

    validate = commands.add_parser("validate", help="validate all Markdown records and source-of-truth invariants")
    validate.add_argument("--json", action="store_true")
    return parser


def _add_score_flags(parser: argparse.ArgumentParser) -> None:
    for dimension in CONCEPT_DIMENSIONS:
        parser.add_argument(f"--{dimension}", type=int)


def _add_a0_flags(parser: argparse.ArgumentParser, *, include_session: bool = False) -> None:
    result = parser.add_mutually_exclusive_group(required=True)
    result.add_argument("--correct", action="store_true", dest="correct")
    result.add_argument("--incorrect", action="store_false", dest="correct")
    parser.add_argument("--dimension", required=True, choices=CONCEPT_DIMENSIONS)
    parser.add_argument("--assistance", choices=ASSISTANCE_LEVELS, default="A0")
    parser.add_argument("--confidence", required=True, type=int)
    parser.add_argument("--novel", action="store_true", dest="novel_problem")
    parser.add_argument("--timestamp")
    parser.add_argument("--note", default="")
    parser.add_argument("--score", type=int)
    if include_session:
        parser.add_argument("--session", dest="session_id")


def _extract_vault(argv: list[str]) -> tuple[list[str], str | None]:
    """Allow `--vault` before or after the command for shell ergonomics."""

    remaining: list[str] = []
    vault: str | None = None
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--vault":
            if index + 1 >= len(argv):
                raise ValidationError("--vault needs a path")
            vault = argv[index + 1]
            index += 2
            continue
        if item.startswith("--vault="):
            vault = item.split("=", 1)[1]
            index += 1
            continue
        remaining.append(item)
        index += 1
    return remaining, vault


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        normalized_argv, extracted_vault = _extract_vault(raw_argv)
        parser = build_parser()
        args = parser.parse_args(normalized_argv)
        vault_path = extracted_vault or args.vault
        repo = VaultRepository(vault_path)
        return _dispatch(repo, args)
    except (LearningOSError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _dispatch(repo: VaultRepository, args: argparse.Namespace) -> int:
    command = args.command
    if command == "init":
        repo.ensure_layout()
        print(f"initialized Markdown vault: {repo.root}")
        return 0
    if command == "concept":
        return _concept(repo, args)
    if command == "paper":
        return _paper(repo, args)
    if command == "mistake":
        return _mistake(repo, args)
    if command == "session":
        return _session(repo, args)
    if command == "a0":
        return _a0(repo, args)
    if command == "assessment":
        return _assessment(repo, args)
    if command == "review":
        snapshot = [{"id": item.id, "name": item.name, "next_review": item.next_review} for item in due_reviews(repo)]
        _print_data(snapshot, args.json)
        return 0
    if command == "dashboard":
        _print_data(dashboard_snapshot(repo), args.json)
        return 0
    if command == "foundation":
        return _foundation(repo, args)
    if command == "validate":
        errors = repo.validate_all()
        payload = {"valid": not errors, "errors": errors}
        _print_data(payload, args.json)
        return 0 if not errors else 1
    raise ValidationError(f"unsupported command: {command}")


def _concept(repo: VaultRepository, args: argparse.Namespace) -> int:
    if args.action == "create":
        record = create_concept(repo, concept_id=args.id, name=args.name, domain=args.domain, prerequisites=args.prerequisite, body=args.body)
        print(f"created concept {record.id}: {repo.path_for('concept', record.id)}")
        return 0
    if args.action == "show":
        record = repo.load("concept", args.id)
        _print_data(record.to_dict(), args.json)
        return 0
    if args.action == "list":
        records = [record.to_dict() for record in repo.records("concept")]
        _print_data(records, args.json)
        return 0
    if args.action == "validate":
        if args.id:
            record = repo.load("concept", args.id)
            record.validate()
            print(f"valid concept: {record.id}")
            return 0
        errors = repo.validate_all()
        _print_data({"valid": not errors, "errors": errors}, False)
        return 0 if not errors else 1
    if args.action == "update":
        scores = {dimension: getattr(args, dimension) for dimension in CONCEPT_DIMENSIONS if getattr(args, dimension) is not None}
        scores.update(_parse_score_pairs(args.score))
        if not scores and args.status is None:
            raise ValidationError("provide at least one dimension score, --score DIMENSION=SCORE, or --status")
        record = update_concept(repo, args.id, scores, assistance=args.assistance, status=args.status, note=args.note)
        _print_data(record.to_dict(), False)
        return 0
    raise ValidationError(f"unsupported concept action: {args.action}")


def _paper(repo: VaultRepository, args: argparse.Namespace) -> int:
    if args.action == "create":
        record = create_paper(repo, paper_id=args.id, title=args.title, authors=args.author, year=args.year, venue=args.venue, body=args.body)
        print(f"created paper {record.id}: {repo.path_for('paper', record.id)}")
        return 0
    if args.action == "show":
        record = repo.load("paper", args.id)
        _print_data(record.to_dict(), args.json)
        return 0
    if args.action == "list":
        records = [record.to_dict() for record in repo.records("paper")]
        _print_data(records, args.json)
        return 0
    if args.action == "blocker":
        if args.blocker_action == "add":
            paper, blocker = add_blocker(
                repo,
                args.paper_id,
                blocker_type=args.type,
                label=args.label,
                priority=args.priority,
                description=args.description,
                concept_id=args.concept,
                foundation_track=args.foundation_track,
                blocker_id=args.blocker_id,
            )
            print(f"recorded blocker {blocker.id} on {paper.id} ({blocker.priority})")
            return 0
        if args.blocker_action == "resolve":
            resolve_blocker(repo, args.paper_id, args.blocker_id)
            print(f"resolved blocker {args.blocker_id} on {args.paper_id}")
            return 0
    if args.action == "dependency":
        add_dependency(repo, args.paper_id, priority=args.priority, dependency=args.dependency)
        print(f"added {args.priority} dependency to {args.paper_id}: {args.dependency}")
        return 0
    if args.action == "map":
        _print_data(dependency_map(repo, args.paper_id), args.json)
        return 0
    if args.action == "evidence":
        _, entry = add_paper_evidence(
            repo,
            args.paper_id,
            kind=args.kind,
            statement=args.statement,
            source=args.source,
            note=args.note,
        )
        print(f"recorded {entry['kind']} evidence {entry['id']} on {args.paper_id}")
        return 0
    if args.action == "formula":
        add_formula(
            repo,
            args.paper_id,
            formula_id=args.formula_id,
            label=args.label,
            target_level=args.target_level,
            notes=args.notes,
        )
        print(f"recorded formula {args.formula_id} on {args.paper_id}; target={args.target_level}")
        return 0
    if args.action == "prediction":
        if args.prediction_action == "add":
            _, entry = add_prediction(
                repo,
                args.paper_id,
                hypothesis=args.hypothesis,
                prediction=args.prediction,
                expected_result=args.expected_result,
                expected_failure=args.expected_failure,
                falsification_condition=args.falsification_condition,
                competing_explanations=args.competing_explanations,
                prediction_id=args.prediction_id,
            )
            print(f"recorded prediction {entry['id']} on {args.paper_id}")
            return 0
        if args.prediction_action == "observe":
            observe_prediction(
                repo,
                args.paper_id,
                args.prediction_id,
                observation=args.observation,
                prediction_match=args.prediction_match,
                unexpected_result=args.unexpected_result,
                possible_causes=args.possible_causes,
                next_discriminating_experiment=args.next_discriminating_experiment,
            )
            print(f"recorded observation for prediction {args.prediction_id} on {args.paper_id}")
            return 0
    raise ValidationError(f"unsupported paper action: {args.action}")


def _mistake(repo: VaultRepository, args: argparse.Namespace) -> int:
    if args.action == "create":
        fields = {
            "problem": args.problem,
            "my_answer": args.my_answer,
            "what_was_wrong": args.what_was_wrong,
            "why_i_made_it": args.why_i_made_it,
            "correct_mental_model": args.correct_mental_model,
            "retest_question": args.retest_question,
        }
        record = create_mistake(
            repo,
            mistake_id=args.id,
            concept_id=args.concept_id,
            error_type=args.error_type,
            severity=args.severity,
            assistance=args.assistance,
            confidence=args.confidence,
            retest=args.retest,
            fields=fields,
            body=args.body,
        )
        print(f"created mistake {record.id}: {repo.path_for('mistake', record.id)}")
        return 0
    if args.action == "show":
        record = repo.load("mistake", args.id)
        _print_data(record.to_dict(), args.json)
        return 0
    if args.action == "resolve":
        resolve_mistake(repo, args.id)
        print(f"resolved mistake {args.id}")
        return 0
    if args.action == "list":
        records = [record.to_dict() for record in repo.records("mistake")]
        _print_data(records, args.json)
        return 0
    if args.action == "link":
        add_session_mistake(repo, args.session_id, args.mistake_id)
        print(f"linked mistake {args.mistake_id} to session {args.session_id}")
        return 0
    raise ValidationError(f"unsupported mistake action: {args.action}")


def _session(repo: VaultRepository, args: argparse.Namespace) -> int:
    if args.action == "start":
        record = start_session(
            repo,
            session_id=args.id,
            mode=args.mode,
            title=args.title,
            topic=args.topic,
            concept_id=args.concept_id,
            paper_id=args.paper_id,
            goal=args.goal,
            initial_belief=args.initial_belief,
            body=args.body,
        )
        print(f"started {record.mode} session {record.id}: {repo.path_for('session', record.id)}")
        return 0
    if args.action == "show":
        record = repo.load("session", args.id)
        _print_data(record.to_dict(), args.json)
        return 0
    if args.action == "list":
        records = [record.to_dict() for record in repo.records("session")]
        _print_data(records, args.json)
        return 0
    if args.action == "attempt":
        add_session_attempt(repo, args.id, args.text, source=args.source)
        print(f"recorded attempt in session {args.id}")
        return 0
    if args.action == "hint":
        add_session_hint(repo, args.id, args.level, args.text)
        print(f"recorded {args.level} hint in session {args.id}")
        return 0
    if args.action == "a0":
        concept_id = args.concept_id or repo.load("session", args.id).concept_id
        if not concept_id:
            raise ValidationError("session A0 requires --concept or a session linked to a concept")
        concept, evidence = record_a0(repo, concept_id, **_a0_kwargs(args, session_id=args.id))
        print(f"recorded A0 evidence {evidence.id}; {concept.id} successes={concept.a0_successes}, next_review={concept.next_review}")
        return 0
    if args.action == "finish":
        record = finish_session(repo, args.id, reflection=args.reflection, next_action=args.next_action, revised_understanding=args.revised_understanding)
        print(f"finished session {record.id} at {record.finished_at}")
        return 0
    raise ValidationError(f"unsupported session action: {args.action}")


def _a0(repo: VaultRepository, args: argparse.Namespace) -> int:
    if args.action != "record":
        raise ValidationError(f"unsupported a0 action: {args.action}")
    concept, evidence = record_a0(repo, args.concept_id, **_a0_kwargs(args, session_id=args.session_id))
    _print_data(
        {
            "evidence": evidence.to_dict(),
            "concept_id": concept.id,
            "a0_successes": concept.a0_successes,
            "status": concept.status,
            "next_review": concept.next_review,
        },
        False,
    )
    return 0


def _assessment(repo: VaultRepository, args: argparse.Namespace) -> int:
    if args.action != "record":
        raise ValidationError(f"unsupported assessment action: {args.action}")
    record_assessment(
        repo,
        args.concept_id,
        dimension=args.dimension,
        score=args.score,
        assistance=args.assistance,
        confidence=args.confidence,
        note=args.note,
    )
    print(f"recorded {args.dimension} assessment for {args.concept_id}: {args.score}/5")
    return 0


def _foundation(repo: VaultRepository, args: argparse.Namespace) -> int:
    if args.action == "suggest":
        from .policies import foundation_candidates

        candidates = foundation_candidates(repo, threshold=args.threshold)
        _print_data(candidates, args.json)
        return 0
    if args.action == "create":
        record = create_foundation_track(
            repo,
            track_id=args.id,
            name=args.name,
            trigger=args.trigger,
            concepts=args.concept,
            goal=args.goal,
            status=args.status,
            body=args.body,
        )
        print(f"created foundation track {record.id}: {repo.path_for('foundation', record.id)}")
        return 0
    raise ValidationError(f"unsupported foundation action: {args.action}")


def _parse_score_pairs(values: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise ValidationError(f"score must look like dimension=number: {value}")
        dimension, raw_score = value.split("=", 1)
        if dimension not in CONCEPT_DIMENSIONS:
            raise ValidationError(f"unknown concept dimension: {dimension}")
        try:
            result[dimension] = int(raw_score)
        except ValueError as exc:
            raise ValidationError(f"score must be an integer: {value}") from exc
    return result


def _a0_kwargs(args: argparse.Namespace, *, session_id: str | None = None) -> dict[str, Any]:
    return {
        "dimension": args.dimension,
        "correct": args.correct,
        "assistance": args.assistance,
        "confidence": args.confidence,
        "novel_problem": args.novel_problem,
        "timestamp": args.timestamp,
        "session_id": session_id,
        "note": args.note,
        "score": args.score,
    }


def _print_data(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            print(f"{key}: {item}")
        return
    if isinstance(value, list):
        if not value:
            print("(none)")
            return
        for item in value:
            if isinstance(item, dict):
                summary = ", ".join(f"{key}={item[key]}" for key in item if not isinstance(item[key], (dict, list)))
                print(f"- {summary or item}")
            else:
                print(f"- {item}")
        return
    print(value)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
