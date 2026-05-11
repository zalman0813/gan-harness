# Testing conventions (pytest)

Two tiers of tests for a CLI:

## Unit tests — `tests/unit/`

Cover `core/` (pure functions) and `commands/<verb>.py` (with mocked I/O).
Direct function calls; no subprocess.

```python
# tests/unit/test_get.py
import argparse
from pathlib import Path

from <pkg>.commands import get


def test_get_returns_value(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text('{"name": "alice"}')
    args = argparse.Namespace(file=str(cfg), key="name")
    assert get.run(args) == 0


def test_get_missing_file_returns_1(tmp_path: Path, capsys) -> None:
    args = argparse.Namespace(file=str(tmp_path / "missing.json"), key="x")
    assert get.run(args) == 1
    err = capsys.readouterr().err
    assert "not found" in err
```

Key idioms:

- `tmp_path` fixture for filesystem tests — automatic cleanup
- `capsys` to assert on stdout/stderr content
- Construct `argparse.Namespace` directly rather than calling `parse_args`
  — the parser is tested separately

## Smoke tests — `tests/smoke/`

End-to-end via subprocess. One test per user-observable flow. These are
slow (~100ms each); keep the suite small (≤5 tests).

```python
# tests/smoke/test_cli_smoke.py
import json
import subprocess
import sys
from pathlib import Path


def test_get_smoke(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"name": "alice"}))
    result = subprocess.run(
        [sys.executable, "-m", "<pkg>", "get", str(cfg), "name"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "alice" in result.stdout
```

## Running tests

The harness pre-commit hook drives `pytest` via `sensors.ini`. Manually:

```
pytest -x --tb=short                  # all tests, stop on first failure
pytest tests/unit/test_get.py         # one file
pytest -k "missing"                   # by keyword
```

## Property-based testing (optional)

If the project uses Hypothesis, place property tests under `tests/unit/`
with a `test_property_*.py` prefix. They run through the same `pytest`
command and need no `sensors.ini` change. Idempotency and round-trip
properties are the highest-value patterns for a config-inspection CLI
(e.g., `parse(serialize(x)) == x`).
