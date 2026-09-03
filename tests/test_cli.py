from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from learning_os.cli import main


class CLISmokeTests(unittest.TestCase):
    def invoke(self, vault: str, *args: str) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--vault", vault, *args])
        return code, out.getvalue(), err.getvalue()

    def test_cli_concept_a0_dashboard_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            code, _, err = self.invoke(temp, "init")
            self.assertEqual((code, err), (0, ""))
            code, _, err = self.invoke(temp, "concept", "create", "c", "--name", "C", "--domain", "math")
            self.assertEqual((code, err), (0, ""))
            code, output, err = self.invoke(
                temp,
                "a0",
                "record",
                "c",
                "--dimension",
                "recall",
                "--correct",
                "--assistance",
                "A0",
                "--confidence",
                "75",
            )
            self.assertEqual((code, err), (0, ""))
            self.assertIn("a0_successes: 1", output)
            code, output, err = self.invoke(temp, "dashboard", "--json")
            self.assertEqual((code, err), (0, ""))
            payload = json.loads(output)
            self.assertEqual(payload["a0"]["a0_successes"], 1)
            self.assertEqual(payload["counts"]["concepts"], 1)
            code, output, err = self.invoke(temp, "validate", "--json")
            self.assertEqual((code, err), (0, ""))
            self.assertTrue(json.loads(output)["valid"])

    def test_cli_rejects_invalid_mastery_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.invoke(temp, "init")
            self.invoke(temp, "concept", "create", "c", "--name", "C", "--domain", "math")
            code, _, err = self.invoke(temp, "concept", "update", "c", "--status", "mastered")
            self.assertEqual(code, 2)
            self.assertIn("A0 mastery gate", err)

    def test_cli_validate_fails_closed_for_partial_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self.invoke(temp, "init")[0], 0)
            partial = Path(temp) / "Concepts" / ".incomplete.md.tmp"
            partial.write_text("---\nschema_version: 1\n", encoding="utf-8")
            code, output, err = self.invoke(temp, "validate", "--json")
            self.assertEqual(err, "")
            self.assertEqual(code, 1)
            payload = json.loads(output)
            self.assertFalse(payload["valid"])
            self.assertTrue(any("partial/temporary" in item for item in payload["errors"]))

    def test_strong_convexity_vertical_slice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self.invoke(temp, "init")[0], 0)
            for concept_id, name, domain in (
                ("convex-functions", "Convex Functions", "convex-optimization"),
                ("gradient", "Gradient", "calculus"),
            ):
                code, _, err = self.invoke(
                    temp,
                    "concept",
                    "create",
                    concept_id,
                    "--name",
                    name,
                    "--domain",
                    domain,
                )
                self.assertEqual((code, err), (0, ""))
            code, _, err = self.invoke(
                temp,
                "concept",
                "create",
                "strong-convexity",
                "--name",
                "Strong Convexity",
                "--domain",
                "convex-optimization",
                "--prerequisite",
                "convex-functions",
                "--prerequisite",
                "gradient",
            )
            self.assertEqual((code, err), (0, ""))
            code, _, err = self.invoke(
                temp,
                "session",
                "start",
                "strong-convexity-session",
                "--mode",
                "learning",
                "--concept",
                "strong-convexity",
                "--goal",
                "rebuild the strong convexity derivation",
            )
            self.assertEqual((code, err), (0, ""))
            self.assertEqual(
                self.invoke(
                    temp,
                    "session",
                    "attempt",
                    "strong-convexity-session",
                    "--text",
                    "I will start from the definition.",
                )[0],
                0,
            )
            self.assertEqual(
                self.invoke(
                    temp,
                    "session",
                    "hint",
                    "strong-convexity-session",
                    "--level",
                    "A2",
                    "--text",
                    "Check the curvature lower bound.",
                )[0],
                0,
            )
            code, output, err = self.invoke(
                temp,
                "session",
                "a0",
                "strong-convexity-session",
                "--dimension",
                "derivation",
                "--correct",
                "--confidence",
                "65",
                "--score",
                "3",
            )
            self.assertEqual((code, err), (0, ""))
            self.assertIn("successes=1", output)
            code, concept_output, err = self.invoke(temp, "concept", "show", "strong-convexity", "--json")
            self.assertEqual((code, err), (0, ""))
            concept = json.loads(concept_output)
            self.assertEqual(concept["a0_successes"], 1)
            self.assertIsNotNone(concept["next_review"])
            self.assertEqual(concept["assessments"][0]["dimension"], "derivation")
            self.assertEqual(
                self.invoke(
                    temp,
                    "session",
                    "finish",
                    "strong-convexity-session",
                    "--reflection",
                    "The definition and sufficient condition were still mixed.",
                    "--next-action",
                    "A0 recall tomorrow",
                )[0],
                0,
            )
            code, session_output, err = self.invoke(temp, "session", "show", "strong-convexity-session", "--json")
            self.assertEqual((code, err), (0, ""))
            session = json.loads(session_output)
            self.assertEqual(session["status"], "completed")
            self.assertEqual(session["hints"][0]["assistance"], "A2")
            self.assertEqual(len(session["a0_tests"]), 1)
            code, validate_output, err = self.invoke(temp, "validate", "--json")
            self.assertEqual((code, err), (0, ""))
            self.assertTrue(json.loads(validate_output)["valid"])

    def test_efim_paper_vertical_slice_supports_late_concept_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self.invoke(temp, "init")[0], 0)
            self.assertEqual(
                self.invoke(temp, "paper", "create", "efim-paper", "--title", "EFIM paper")[0],
                0,
            )
            code, _, err = self.invoke(
                temp,
                "paper",
                "blocker",
                "add",
                "efim-paper",
                "--type",
                "prerequisite",
                "--label",
                "EFIM",
                "--priority",
                "P0",
                "--id",
                "efim-blocker",
            )
            self.assertEqual((code, err), (0, ""))
            self.assertEqual(
                self.invoke(
                    temp,
                    "paper",
                    "dependency",
                    "efim-paper",
                    "--priority",
                    "P0",
                    "--dependency",
                    "fisher-information",
                )[0],
                0,
            )
            self.assertEqual(
                self.invoke(
                    temp,
                    "concept",
                    "create",
                    "fisher-information",
                    "--name",
                    "Fisher Information",
                    "--domain",
                    "probability-estimation",
                )[0],
                0,
            )
            code, _, err = self.invoke(
                temp,
                "paper",
                "blocker",
                "link",
                "efim-paper",
                "efim-blocker",
                "--concept",
                "fisher-information",
            )
            self.assertEqual((code, err), (0, ""))
            code, map_output, err = self.invoke(temp, "paper", "map", "efim-paper", "--json")
            self.assertEqual((code, err), (0, ""))
            dependency_map = json.loads(map_output)
            self.assertEqual(dependency_map["priorities"]["P0"], ["fisher-information"])
            self.assertEqual(dependency_map["blockers"][0]["concept_id"], "fisher-information")
            self.assertIn("repair open P0", dependency_map["next_action"])
            self.assertEqual(
                self.invoke(temp, "paper", "blocker", "resolve", "efim-paper", "efim-blocker")[0],
                0,
            )
            code, map_output, err = self.invoke(temp, "paper", "map", "efim-paper", "--json")
            self.assertEqual((code, err), (0, ""))
            dependency_map = json.loads(map_output)
            self.assertEqual(dependency_map["blockers"][0]["status"], "resolved")
            self.assertIn("return to the paper", dependency_map["next_action"])
            code, paper_output, err = self.invoke(temp, "paper", "show", "efim-paper", "--json")
            self.assertEqual((code, err), (0, ""))
            self.assertEqual(json.loads(paper_output)["status"], "reading")
            code, validate_output, err = self.invoke(temp, "validate", "--json")
            self.assertEqual((code, err), (0, ""))
            self.assertTrue(json.loads(validate_output)["valid"])


if __name__ == "__main__":
    unittest.main()
