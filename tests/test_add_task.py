"""Tests for the `todo add` subcommand (vp-03).

Covers:
  - test_add_first_task                   : happy path, id=1 entry created.
  - test_add_increments_id                : second add yields id=2.
  - test_add_no_description_exits_nonzero : error path; stderr mentions 'description'.
  - test_add_empty_file_succeeds          : empty existing file treated as empty list.
  - test_importable_without_side_effects  : importing todo must not create any file.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestAddFirstTask(unittest.TestCase):
    """vp-03 case: test_add_first_task — happy path, first entry gets id=1."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.todo_file = os.path.join(self.tmpdir, "todo.json")
        os.environ["TODO_FILE"] = self.todo_file

    def tearDown(self) -> None:
        del os.environ["TODO_FILE"]

    def test_add_first_task(self) -> None:
        import todo  # noqa: PLC0415

        result = todo.main(["add", "buy milk"])
        self.assertEqual(result, 0)

        path = Path(self.todo_file)
        self.assertTrue(path.exists())
        tasks = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task["id"], 1)
        self.assertEqual(task["description"], "buy milk")
        # UTC ISO-8601 timestamp must be a non-empty string
        ts: object = task["timestamp"]
        self.assertIsInstance(ts, str)
        self.assertTrue(str(ts).endswith("+00:00") or str(ts).endswith("Z"))


class TestAddIncrementsId(unittest.TestCase):
    """vp-03 case: test_add_increments_id — second add yields id=2."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.todo_file = os.path.join(self.tmpdir, "todo.json")
        os.environ["TODO_FILE"] = self.todo_file

    def tearDown(self) -> None:
        del os.environ["TODO_FILE"]

    def test_add_increments_id(self) -> None:
        import todo  # noqa: PLC0415

        # Pre-seed one existing task directly (mocking by writing the file)
        existing = [{"id": 1, "description": "first task", "timestamp": "2026-01-01T00:00:00+00:00"}]
        Path(self.todo_file).write_text(json.dumps(existing), encoding="utf-8")

        result = todo.main(["add", "fix tests"])
        self.assertEqual(result, 0)

        tasks = json.loads(Path(self.todo_file).read_text(encoding="utf-8"))
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[1]["id"], 2)
        self.assertEqual(tasks[1]["description"], "fix tests")


class TestAddNoDescriptionExitsNonzero(unittest.TestCase):
    """vp-03 case: test_add_no_description_exits_nonzero — error path."""

    def test_add_no_description_exits_nonzero(self) -> None:
        import todo  # noqa: PLC0415

        # Capture stderr to assert it mentions 'description'
        captured_stderr = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_stderr
        try:
            with self.assertRaises(SystemExit) as ctx:
                todo.main(["add"])
        finally:
            sys.stderr = old_stderr

        exit_code = ctx.exception.code
        self.assertNotEqual(exit_code, 0)

        stderr_output = captured_stderr.getvalue()
        self.assertTrue(len(stderr_output) > 0, "stderr must be non-empty")
        self.assertIn("description", stderr_output)


class TestAddEmptyFileSucceeds(unittest.TestCase):
    """vp-03 case: test_add_empty_file_succeeds — empty file treated as empty list."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.todo_file = os.path.join(self.tmpdir, "todo.json")
        # Pre-create the file as empty (0 bytes)
        Path(self.todo_file).write_text("", encoding="utf-8")
        os.environ["TODO_FILE"] = self.todo_file

    def tearDown(self) -> None:
        del os.environ["TODO_FILE"]

    def test_add_empty_file_succeeds(self) -> None:
        import todo  # noqa: PLC0415

        result = todo.main(["add", "buy milk"])
        self.assertEqual(result, 0)

        tasks = json.loads(Path(self.todo_file).read_text(encoding="utf-8"))
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], 1)


class TestImportableWithoutSideEffects(unittest.TestCase):
    """vp-03 case: test_importable_without_side_effects — no file on import."""

    def test_importable_without_side_effects(self) -> None:
        home = Path.home()
        default_path = home / ".todo.json"
        existed_before = default_path.exists()

        import todo  # noqa: PLC0415, F401

        # Importing todo must not create any new file at the default path
        if not existed_before:
            self.assertFalse(
                default_path.exists(),
                "Importing todo must not create ~/.todo.json as a side effect.",
            )
        # If it already existed, we simply confirm we haven't deleted it
        else:
            self.assertTrue(default_path.exists())


class TestAddMultiWordDescriptionViaSubprocess(unittest.TestCase):
    """vp-02 regression: multi-word description must survive real shell tokenization.

    Invokes todo.py as a subprocess with argv split exactly as a shell would
    produce it (no pre-joining).  R1 showed that argparse rejected 'milk' as
    an unrecognised argument when description was a single positional token.
    This test closes that §1.6 vacuous-pass gap.
    """

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.todo_file = os.path.join(self.tmpdir, "todo.json")

    def test_multiword_description_persisted(self) -> None:
        # Invoke via subprocess so argv tokenization is real, not pre-joined.
        todo_py = str(Path(__file__).parent.parent / "todo.py")
        env = dict(os.environ, TODO_FILE=self.todo_file)
        result = subprocess.run(
            [sys.executable, todo_py, "add", "buy", "milk"],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")

        tasks = json.loads(Path(self.todo_file).read_text(encoding="utf-8"))
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["description"], "buy milk")


if __name__ == "__main__":
    unittest.main()
