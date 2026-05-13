"""todo CLI — stdlib-only personal task manager.

Single-file CLI using argparse subcommand dispatch and JSON persistence.
Entry point is guarded by __main__ so the module is importable in tests
without side effects.

Storage: ~/.todo.json (or the path given by TODO_FILE env var for tests).
Schema: list of {"id": int, "description": str, "timestamp": str (UTC ISO-8601)}
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _todo_path() -> Path:
    """Return the path to the todo JSON file.

    Respects TODO_FILE env var so tests can inject a temporary path.
    """
    env = os.environ.get("TODO_FILE")
    if env:
        return Path(env)
    return Path.home() / ".todo.json"


def _load_tasks(path: Path) -> list[dict[str, object]]:
    """Load task list from *path*.

    Returns an empty list if the file does not exist or is empty.
    """
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8") as fh:
        data: list[dict[str, object]] = json.load(fh)
    return data


def _save_tasks(path: Path, tasks: list[dict[str, object]]) -> None:
    """Persist *tasks* to *path* as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(tasks, fh, indent=2)


def cmd_add(args: argparse.Namespace) -> int:
    """Handle the `add` subcommand.

    Appends a new task with auto-incremented id and UTC timestamp.
    Returns 0 on success.
    """
    # args.description is a list of tokens when nargs='+'; join into one string.
    description: str = " ".join(args.description)
    path = _todo_path()
    tasks = _load_tasks(path)
    next_id = (tasks[-1]["id"] if tasks else 0)
    assert isinstance(next_id, int)
    next_id += 1
    timestamp = datetime.now(timezone.utc).isoformat()
    task: dict[str, object] = {
        "id": next_id,
        "description": description,
        "timestamp": timestamp,
    }
    tasks.append(task)
    _save_tasks(path, tasks)
    return 0


def cmd_list(args: argparse.Namespace) -> int:  # noqa: ARG001
    """Handle the `list` subcommand.

    Prints each task on its own line as `[id] description (timestamp)`,
    in insertion order.  Missing or empty file exits 0 with no output.
    All output goes to stdout; nothing is written to stderr on success.
    Returns 0 always.
    """
    path = _todo_path()
    tasks = _load_tasks(path)
    for task in tasks:
        task_id = task["id"]
        description = task["description"]
        timestamp = task["timestamp"]
        sys.stdout.write(f"[{task_id}] {description} ({timestamp})\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="todo",
        description="A minimal personal task manager backed by ~/.todo.json.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    # add subcommand
    add_parser = subparsers.add_parser("add", help="Add a new task.")
    add_parser.add_argument(
        "description",
        nargs="+",
        help="Text description of the task to add (one or more words).",
    )

    # list subcommand
    subparsers.add_parser("list", help="List all tasks in insertion order.")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the appropriate subcommand handler."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "add":
        return cmd_add(args)

    if args.command == "list":
        return cmd_list(args)

    # No subcommand supplied — print help to stderr and exit non-zero.
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
