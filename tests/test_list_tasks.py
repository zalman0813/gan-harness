"""Tests for the `todo list` subcommand (vp-04).

Covers:
  - test_list_single_task                : one task, correct format.
  - test_list_multiple_tasks_in_order    : three tasks in insertion order.
  - test_list_missing_file_exits_zero    : no file → exit 0, empty stdout.
  - test_list_empty_file_exits_zero      : empty file → exit 0, empty stdout.
  - test_list_output_to_stdout           : output goes to stdout, not stderr.

Each test uses tempfile.mkdtemp() + os.environ['TODO_FILE'] injection to
isolate from ~/.todo.json, consistent with S01 tests/test_add_task.py setUp.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


class TestListSingleTask(unittest.TestCase):
    """vp-04 case: test_list_single_task — one task, correct format."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.todo_file = os.path.join(self.tmpdir, "todo.json")
        os.environ["TODO_FILE"] = self.todo_file

    def tearDown(self) -> None:
        del os.environ["TODO_FILE"]

    def test_list_single_task(self) -> None:
        import todo  # noqa: PLC0415

        # Pre-seed one task via the add subcommand (end-to-end chain).
        add_result = todo.main(["add", "buy milk"])
        self.assertEqual(add_result, 0)

        # Capture stdout and call list.
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            result = todo.main(["list"])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(result, 0)
        output = captured.getvalue()
        lines = [ln for ln in output.splitlines() if ln]
        self.assertEqual(len(lines), 1)
        # Line must start with [1] buy milk (
        self.assertTrue(
            lines[0].startswith("[1] buy milk ("),
            msg=f"Unexpected line format: {lines[0]!r}",
        )
        # Line must end with )
        self.assertTrue(
            lines[0].endswith(")"),
            msg=f"Line must end with ')': {lines[0]!r}",
        )


class TestListMultipleTasksInOrder(unittest.TestCase):
    """vp-04 case: test_list_multiple_tasks_in_order — three tasks, insertion order."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.todo_file = os.path.join(self.tmpdir, "todo.json")
        os.environ["TODO_FILE"] = self.todo_file

    def tearDown(self) -> None:
        del os.environ["TODO_FILE"]

    def test_list_multiple_tasks_in_order(self) -> None:
        import todo  # noqa: PLC0415

        # Pre-populate three tasks directly (faster than three add calls).
        tasks = [
            {"id": 1, "description": "task one", "timestamp": "2026-01-01T00:00:00+00:00"},
            {"id": 2, "description": "task two", "timestamp": "2026-01-01T00:01:00+00:00"},
            {"id": 3, "description": "task three", "timestamp": "2026-01-01T00:02:00+00:00"},
        ]
        Path(self.todo_file).write_text(json.dumps(tasks), encoding="utf-8")

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            result = todo.main(["list"])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(result, 0)
        lines = [ln for ln in captured.getvalue().splitlines() if ln]
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("[1] task one ("), msg=lines[0])
        self.assertTrue(lines[1].startswith("[2] task two ("), msg=lines[1])
        self.assertTrue(lines[2].startswith("[3] task three ("), msg=lines[2])


class TestListMissingFileExitsZero(unittest.TestCase):
    """vp-04 case: test_list_missing_file_exits_zero — no file, exit 0, empty stdout."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        # Point to a path that does not exist.
        self.todo_file = os.path.join(self.tmpdir, "nonexistent.json")
        os.environ["TODO_FILE"] = self.todo_file

    def tearDown(self) -> None:
        del os.environ["TODO_FILE"]

    def test_list_missing_file_exits_zero(self) -> None:
        import todo  # noqa: PLC0415

        self.assertFalse(Path(self.todo_file).exists(), "Setup: file must not exist")

        captured_out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_out
        try:
            result = todo.main(["list"])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(result, 0)
        self.assertEqual(captured_out.getvalue(), "", "stdout must be empty when no tasks file exists")


class TestListEmptyFileExitsZero(unittest.TestCase):
    """vp-04 case: test_list_empty_file_exits_zero — empty file, exit 0, empty stdout."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.todo_file = os.path.join(self.tmpdir, "todo.json")
        # Create the file as 0-byte empty.
        Path(self.todo_file).write_text("", encoding="utf-8")
        os.environ["TODO_FILE"] = self.todo_file

    def tearDown(self) -> None:
        del os.environ["TODO_FILE"]

    def test_list_empty_file_exits_zero(self) -> None:
        import todo  # noqa: PLC0415

        captured_out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_out
        try:
            result = todo.main(["list"])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(result, 0)
        self.assertEqual(captured_out.getvalue(), "", "stdout must be empty for empty todo file")


class TestListOutputToStdout(unittest.TestCase):
    """vp-04 case: test_list_output_to_stdout — output goes to stdout, not stderr."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.todo_file = os.path.join(self.tmpdir, "todo.json")
        tasks = [{"id": 1, "description": "check stream", "timestamp": "2026-01-01T00:00:00+00:00"}]
        Path(self.todo_file).write_text(json.dumps(tasks), encoding="utf-8")
        os.environ["TODO_FILE"] = self.todo_file

    def tearDown(self) -> None:
        del os.environ["TODO_FILE"]

    def test_list_output_to_stdout(self) -> None:
        import todo  # noqa: PLC0415

        captured_out = io.StringIO()
        captured_err = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = captured_out
        sys.stderr = captured_err
        try:
            result = todo.main(["list"])
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        self.assertEqual(result, 0)
        # Output must be on stdout.
        self.assertIn("check stream", captured_out.getvalue())
        # Nothing must go to stderr on success.
        self.assertEqual(captured_err.getvalue(), "", "stderr must be empty on successful list")


if __name__ == "__main__":
    unittest.main()
