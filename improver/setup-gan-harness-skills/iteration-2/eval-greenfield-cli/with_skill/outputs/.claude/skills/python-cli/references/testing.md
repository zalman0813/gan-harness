# Python CLI — Testing Patterns

## Unit tests — pure functions

Test the parsing/transform layer as plain functions, not via the CLI entry point.
Fast (<10ms per test), no subprocess, no I/O.

```python
# tests/unit/test_inspector.py
from kvstore.inspector import get_value

def test_get_value_returns_nested_key() -> None:
    data = {"a": {"b": 42}}
    assert get_value(data, "a.b") == 42
```

## CLI tests — in-process runner

Prefer in-process invocation over subprocess for speed. Click and Typer ship
`CliRunner`; argparse can be tested by calling `main()` directly with patched
`sys.argv`.

### typer / click

```python
# tests/unit/test_cli.py
from typer.testing import CliRunner
from kvstore.cli import app

runner = CliRunner()

def test_get_prints_value(tmp_path) -> None:
    config = tmp_path / "c.json"
    config.write_text('{"a": 1}')
    result = runner.invoke(app, ["get", str(config), "a"])
    assert result.exit_code == 0
    assert "1" in result.stdout
```

### argparse

```python
# tests/unit/test_cli.py
import sys
from kvstore.cli import main

def test_get_prints_value(tmp_path, capsys, monkeypatch) -> None:
    config = tmp_path / "c.json"
    config.write_text('{"a": 1}')
    monkeypatch.setattr(sys, "argv", ["kvstore", "get", str(config), "a"])
    rc = main()
    assert rc == 0
    assert "1" in capsys.readouterr().out
```

## Smoke tests — real subprocess

L5 smoke tests invoke the installed entry point or `python -m <pkg>` via
`subprocess.run`. Catches packaging/entry-point bugs the in-process runner
misses.

```python
# tests/smoke/test_smoke.py
import subprocess

def test_help_prints_usage() -> None:
    result = subprocess.run(
        ["python", "-m", "kvstore", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "Usage" in result.stdout
```

## Property-based testing (optional)

If using Hypothesis, decorate unit tests:

```python
from hypothesis import given, strategies as st

@given(st.dictionaries(st.text(), st.integers()))
def test_round_trip_serialization(d: dict[str, int]) -> None:
    import json
    assert json.loads(json.dumps(d)) == d
```

Property tests run through the existing `[test] unit` pytest command —
no extra wiring in sensors.ini.

## Scope hygiene with the harness gate

The pre-commit hook substitutes `{scope}` with `git diff --name-only`. pytest's
positional filter is substring match against test filenames, so source-file
changes won't auto-select related tests. The GAN-pattern default: accept gen-
side weakness; evaluator's full L2 sweep is the safety net. Consider
`pytest-testmon` if false-PASS becomes a real problem.
