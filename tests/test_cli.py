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


if __name__ == "__main__":
    unittest.main()
