from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from learning_os.errors import ValidationError
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
