from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from learning_os.errors import RecordNotFoundError, ValidationError
from learning_os.frontmatter import dump_markdown, load_markdown
from learning_os.models import ConceptRecord
from learning_os.policies import FixedIntervalScheduler, foundation_candidates, repeated_blockers
from learning_os.repository import VaultRepository
from learning_os.services import (
    add_blocker,
    create_concept,
    create_mistake,
    create_paper,
    dashboard_snapshot,
    finish_session,
    record_a0,
    start_session,
)


class CoreModelTests(unittest.TestCase):
    def test_frontmatter_round_trip_handles_nested_records_and_unicode(self) -> None:
        source = dump_markdown(
            {
                "schema_version": 1,
                "type": "paper",
                "id": "demo",
                "title": "中文 paper",
                "blockers": [
                    {
                        "id": "b1",
                        "type": "notation",
                        "label": "EFIM",
                        "priority": "P0",
                        "status": "open",
                    }
                ],
            },
            "## Core Problem\n\nbody\n",
        )
        data, body = load_markdown_from_text(source)
        self.assertEqual(data["title"], "中文 paper")
        self.assertEqual(data["blockers"][0]["label"], "EFIM")
        self.assertIn("Core Problem", body)

    def test_validate_fails_closed_for_malformed_missing_typed_and_partial_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            concepts = Path(temp) / "Concepts"
            (concepts / "missing-name.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "concept",
                        "id": "missing-name",
                        "domain": "math",
                    }
                ),
                encoding="utf-8",
            )
            (concepts / "bad-yaml.md").write_text(
                "---\n"
                "schema_version: 1\n"
                "type: concept\n"
                "id: bad-yaml\n"
                "name: Bad\n"
                "domain: math\n"
                "  recall: 1\n"
                "---\n",
                encoding="utf-8",
            )
            (concepts / "wrong-type.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "concept",
                        "id": "wrong-type",
                        "name": ["not", "a", "string"],
                        "domain": "math",
                    }
                ),
                encoding="utf-8",
            )
            (concepts / "truncated.md").write_text(
                "---\nschema_version: 1\ntype: concept\nid: truncated\n",
                encoding="utf-8",
            )
            (concepts / ".concept.md.tmp").write_text("---\nid: partial\n", encoding="utf-8")

            errors = repo.validate_all()
            joined = "\n".join(errors)
            self.assertIn("missing-name", joined)
            self.assertIn("invalid YAML", joined)
            self.assertIn("wrong-type", joined)
            self.assertIn("no closing frontmatter delimiter", joined)
            self.assertIn("partial/temporary record file", joined)

    def test_validate_checks_explicit_links_and_filename_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            root = Path(temp)
            (root / "Concepts" / "broken-prereq.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "concept",
                        "id": "broken-prereq",
                        "name": "Broken prerequisite",
                        "domain": "math",
                        "prerequisites": ["missing-concept"],
                    }
                ),
                encoding="utf-8",
            )
            (root / "Papers" / "broken-paper.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "paper",
                        "id": "broken-paper",
                        "title": "Broken paper",
                        "status": "blocked",
                        "blockers": [
                            {
                                "id": "missing-concept-blocker",
                                "type": "prerequisite_concept",
                                "label": "Missing concept",
                                "priority": "P0",
                                "status": "open",
                                "concept_id": "missing-concept",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "Sessions" / "broken-session.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "session",
                        "id": "broken-session",
                        "mode": "learning",
                        "concept_id": "missing-concept",
                        "mistakes": ["missing-mistake"],
                    }
                ),
                encoding="utf-8",
            )
            (root / "Mistakes" / "broken-mistake.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "mistake",
                        "id": "broken-mistake",
                        "concept_id": "missing-concept",
                        "error_type": "missing link",
                    }
                ),
                encoding="utf-8",
            )
            (root / "Foundation" / "broken-track.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "foundation_track",
                        "id": "broken-track",
                        "name": "Broken track",
                        "concepts": ["missing-concept"],
                    }
                ),
                encoding="utf-8",
            )
            (root / "Concepts" / "wrong-filename.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "concept",
                        "id": "actual-id",
                        "name": "Filename mismatch",
                        "domain": "math",
                    }
                ),
                encoding="utf-8",
            )

            errors = repo.validate_all()
            joined = "\n".join(errors)
            self.assertGreaterEqual(joined.count("broken link"), 5)
            self.assertIn("prerequisites", joined)
            self.assertIn("blocker.concept_id", joined)
            self.assertIn("mistakes", joined)
            self.assertIn("concept_id", joined)
            self.assertIn("concepts", joined)
            self.assertIn("frontmatter id 'actual-id'", joined)

    def test_validate_rejects_duplicate_frontmatter_and_nested_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            create_concept(repo, concept_id="same", name="Same", domain="math")
            root = Path(temp)
            (root / "Concepts" / "copy.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "concept",
                        "id": "same",
                        "name": "Copy",
                        "domain": "math",
                    }
                ),
                encoding="utf-8",
            )
            duplicate_evidence = {
                "id": "evidence-1",
                "dimension": "recall",
                "correct": False,
                "assistance": "A0",
                "confidence": 50,
                "novel_problem": False,
                "timestamp": "2026-09-01T09:00:00+08:00",
            }
            (root / "Concepts" / "nested.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "concept",
                        "id": "nested",
                        "name": "Nested duplicate",
                        "domain": "math",
                        "a0_evidence": [duplicate_evidence, duplicate_evidence],
                    }
                ),
                encoding="utf-8",
            )
            (root / "Papers" / "nested-paper.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "paper",
                        "id": "nested-paper",
                        "title": "Nested duplicate paper",
                        "status": "blocked",
                        "blockers": [
                            {
                                "id": "same-blocker",
                                "type": "notation",
                                "label": "notation",
                                "priority": "P0",
                                "status": "open",
                            },
                            {
                                "id": "same-blocker",
                                "type": "notation",
                                "label": "notation again",
                                "priority": "P0",
                                "status": "open",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            errors = repo.validate_all()
            joined = "\n".join(errors)
            self.assertIn("duplicate concept ID 'same'", joined)
            self.assertIn("concept A0 evidence IDs must be unique", joined)
            self.assertIn("paper blocker IDs must be unique", joined)

    def test_validate_rejects_inconsistent_mastery_and_assistance_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            root = Path(temp) / "Concepts"
            root.joinpath("manual-mastered.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "concept",
                        "id": "manual-mastered",
                        "name": "Manual mastered",
                        "domain": "math",
                        "status": "mastered",
                    }
                ),
                encoding="utf-8",
            )
            root.joinpath("assisted-count.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "concept",
                        "id": "assisted-count",
                        "name": "Assisted count",
                        "domain": "math",
                        "assistance_required": "A9",
                    }
                ),
                encoding="utf-8",
            )
            root.joinpath("counter-mismatch.md").write_text(
                dump_markdown(
                    {
                        "schema_version": 1,
                        "type": "concept",
                        "id": "counter-mismatch",
                        "name": "Counter mismatch",
                        "domain": "math",
                        "a0_successes": 1,
                        "a0_evidence": [
                            {
                                "id": "assisted-evidence",
                                "dimension": "recall",
                                "correct": True,
                                "assistance": "A2",
                                "confidence": 80,
                                "novel_problem": False,
                                "timestamp": "2026-09-01T09:00:00+08:00",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            errors = repo.validate_all()
            joined = "\n".join(errors)
            self.assertIn("A0 mastery gate", joined)
            self.assertIn("invalid AssistanceLevel", joined)
            self.assertIn("does not match recorded A0 successes", joined)

    def test_repeated_blockers_count_distinct_papers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            create_concept(repo, concept_id="fisher", name="Fisher Information", domain="probability")
            create_paper(repo, paper_id="paper-1", title="Paper 1")
            create_paper(repo, paper_id="paper-2", title="Paper 2")
            add_blocker(
                repo,
                "paper-1",
                blocker_type="prerequisite",
                label="Fisher Information",
                priority="P0",
                concept_id="fisher",
                blocker_id="fisher-1",
            )
            add_blocker(
                repo,
                "paper-1",
                blocker_type="prerequisite",
                label="Fisher Information duplicate note",
                priority="P0",
                concept_id="fisher",
                blocker_id="fisher-1b",
            )
            self.assertEqual(repeated_blockers(repo, threshold=2), [])
            add_blocker(
                repo,
                "paper-2",
                blocker_type="prerequisite",
                label="Fisher Information",
                priority="P0",
                concept_id="fisher",
                blocker_id="fisher-2",
            )
            repeated = repeated_blockers(repo, threshold=2)
            self.assertEqual(len(repeated), 1)
            self.assertEqual(repeated[0]["count"], 2)

    def test_invalid_score_and_assistance_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ConceptRecord.from_dict(
                {
                    "schema_version": 1,
                    "type": "concept",
                    "id": "bad",
                    "name": "Bad",
                    "domain": "test",
                    "recall": 6,
                }
            )

    def test_concept_creation_rejects_unknown_prerequisite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            with self.assertRaises(RecordNotFoundError) as context:
                create_concept(
                    repo,
                    concept_id="strong-convexity",
                    name="Strong Convexity",
                    domain="convex-optimization",
                    prerequisites=["missing-concept"],
                )
            self.assertIn("concept not found", str(context.exception))
        with self.assertRaises(ValidationError):
            ConceptRecord.from_dict(
                {
                    "schema_version": 1,
                    "type": "concept",
                    "id": "bad",
                    "name": "Bad",
                    "domain": "test",
                    "assistance_required": "A9",
                }
            )

    def test_prioritized_weakness_subset_from_user_schema_is_valid(self) -> None:
        record = ConceptRecord.from_dict(
            {
                "schema_version": 1,
                "type": "concept",
                "id": "strong-convexity",
                "name": "Strong Convexity",
                "domain": "convex-optimization",
                "status": "learning",
                "recall": 3,
                "explanation": 4,
                "derivation": 2,
                "transfer": 1,
                "debug": 2,
                "assistance_required": "A2",
                "a0_successes": 0,
                "weakness": ["derivation", "transfer"],
                "prerequisites": ["convex-functions"],
                "a0_evidence": [],
            }
        )
        self.assertEqual(record.weakness, ["derivation", "transfer"])

    def test_assisted_correctness_does_not_count_as_a0(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            create_concept(repo, concept_id="c", name="C", domain="math")
            record, evidence = record_a0(
                repo,
                "c",
                dimension="recall",
                correct=True,
                assistance="A2",
                confidence=80,
            )
            self.assertFalse(evidence.is_a0_success)
            self.assertEqual(record.a0_successes, 0)
            self.assertEqual(record.status, "learning")

    def test_mastery_requires_scores_three_dates_and_novel_transfer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            create_concept(repo, concept_id="c", name="C", domain="math")
            concept = repo.load("concept", "c")
            concept.update_scores(
                {"recall": 4, "explanation": 4, "derivation": 4, "transfer": 4, "debug": 3},
                assistance="A0",
            )
            repo.save("concept", concept)
            for index, timestamp in enumerate(
                ("2026-09-01T09:00:00+08:00", "2026-09-02T09:00:00+08:00", "2026-09-03T09:00:00+08:00")
            ):
                record_a0(
                    repo,
                    "c",
                    dimension="transfer",
                    correct=True,
                    assistance="A0",
                    confidence=70,
                    novel_problem=index == 2,
                    timestamp=timestamp,
                )
            result = repo.load("concept", "c")
            self.assertEqual(result.a0_successes, 3)
            self.assertTrue(result.mastery_eligible())
            self.assertEqual(result.status, "mastered")

            # A failed A0 test reopens the dimension for review even though
            # historical successes remain auditable.
            failed, _ = record_a0(
                repo,
                "c",
                dimension="transfer",
                correct=False,
                assistance="A0",
                confidence=90,
                timestamp="2026-09-04T09:00:00+08:00",
            )
            self.assertEqual(failed.status, "review")
            self.assertIn("transfer", failed.weakness)

    def test_scheduler_is_transparent_and_replaceable(self) -> None:
        scheduler = FixedIntervalScheduler()
        self.assertTrue(scheduler.next_review(now="2026-09-03T00:00:00+08:00", a0_successes=1, correct=True).startswith("2026-09-04"))
        self.assertTrue(scheduler.next_review(now="2026-09-03T00:00:00+08:00", a0_successes=2, correct=True).startswith("2026-09-06"))
        self.assertTrue(scheduler.next_review(now="2026-09-03T00:00:00+08:00", a0_successes=0, correct=False).startswith("2026-09-04"))

    def test_dashboard_reports_due_review_at_requested_time(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            create_concept(repo, concept_id="c", name="C", domain="math")
            record_a0(
                repo,
                "c",
                dimension="recall",
                correct=True,
                assistance="A0",
                confidence=50,
                timestamp="2026-09-01T09:00:00+08:00",
            )
            snapshot = dashboard_snapshot(repo, now="2026-09-03T09:00:00+08:00")
            self.assertEqual(snapshot["due_reviews"][0]["id"], "c")

    def test_paper_blocker_repetition_and_foundation_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            create_concept(repo, concept_id="fisher-information", name="Fisher Information", domain="probability-estimation")
            create_concept(repo, concept_id="crlb", name="CRLB", domain="probability-estimation")
            create_concept(repo, concept_id="gaussian-likelihood", name="Gaussian likelihood", domain="probability-estimation")
            for index, concept_id, label in (
                (1, "fisher-information", "Fisher Information"),
                (2, "crlb", "CRLB"),
                (3, "gaussian-likelihood", "Gaussian likelihood"),
            ):
                paper_id = f"paper-{index}"
                create_paper(repo, paper_id=paper_id, title=paper_id)
                add_blocker(
                    repo,
                    paper_id,
                    blocker_type="prerequisite",
                    label=label,
                    priority="P0",
                    concept_id=concept_id,
                    foundation_track="Probability & Estimation",
                )
            candidates = foundation_candidates(repo, threshold=3)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["count"], 3)
            self.assertEqual(len(repeated_blockers(repo, threshold=1)), 3)

    def test_paper_evidence_formula_and_prediction_are_structured(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            create_paper(repo, paper_id="p", title="Paper")
            from learning_os.services import add_formula, add_paper_evidence, add_prediction, observe_prediction

            _, evidence = add_paper_evidence(repo, "p", kind="FACT", statement="Table 1 reports the result", source="Table 1")
            self.assertEqual(evidence["kind"], "FACT")
            add_formula(repo, "p", formula_id="eq1", label="core equation", target_level="L3")
            _, prediction = add_prediction(repo, "p", hypothesis="H", prediction="P")
            observe_prediction(repo, "p", prediction["id"], observation="O", prediction_match="partial")
            paper = repo.load("paper", "p")
            self.assertEqual(paper.formula_map[0]["target_level"], "L3")
            self.assertEqual(paper.experiment_predictions[0]["status"], "observed")

    def test_mistake_link_and_session_process_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            create_concept(repo, concept_id="c", name="C", domain="math")
            session = start_session(repo, session_id="s", mode="learning", concept_id="c", goal="test")
            mistake = create_mistake(repo, mistake_id="m", concept_id="c", error_type="confusion")
            from learning_os.services import add_session_attempt, add_session_hint, add_session_mistake

            add_session_attempt(repo, "s", "my attempt")
            add_session_hint(repo, "s", "A2", "use the definition")
            add_session_mistake(repo, "s", mistake.id)
            finish_session(repo, "s", reflection="need a retest", next_action="A0 tomorrow")
            stored_session = repo.load("session", "s")
            self.assertEqual(stored_session.status, "completed")
            self.assertEqual(stored_session.mistakes, ["m"])
            self.assertEqual(repo.load("concept", "c").a0_successes, 0)

    def test_validate_rejects_parallel_mastery_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = VaultRepository(temp)
            repo.ensure_layout()
            create_concept(repo, concept_id="c", name="C", domain="math")
            (Path(temp) / "Mastery").mkdir()
            errors = repo.validate_all()
            self.assertTrue(any("duplicate source-of-truth" in item for item in errors))


def load_markdown_from_text(text: str):
    """Use the public splitter without creating a file for a parser unit test."""

    from learning_os.frontmatter import split_frontmatter, load_yaml

    frontmatter, body = split_frontmatter(text)
    return load_yaml(frontmatter), body


if __name__ == "__main__":
    unittest.main()
