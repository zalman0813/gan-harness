# Testing — pytest conventions for kvstore

## Tooling

- **Runner**: `pytest`. No extra plugins required for the baseline.
- **Layout**: `tests/` sibling to `src/`. One test file per source
  module (`test_cli.py`, `test_loader.py`, `test_inspector.py`).
- **Discovery**: pytest's defaults work given `src/` layout + editable
  install (`pip install -e .`).

## Invoke `main()` in-process

Do NOT shell out via `subprocess` for unit tests — slow and brittle.
Call `main()` with an explicit argv list and assert on the return code
and captured stdout/stderr.

```python
# tests/test_cli.py
import json
from pathlib import Path

import pytest

from kvstore.cli import main


def test_get_returns_value(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"db": {"host": "localhost"}}))

    rc = main(["get", str(cfg), "db.host"])

    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out == "localhost"


def test_get_missing_key_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text("{}")

    rc = main(["get", str(cfg), "db.host"])

    assert rc != 0
    err = capsys.readouterr().err
    assert "db.host" in err
```

## Argparse error paths

When argparse rejects an arg, it calls `sys.exit(2)`. Capture it:

```python
def test_missing_subcommand_errors() -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
```

## Fixtures via `tmp_path`

The stdlib `tmp_path` fixture is plenty for kvstore — no need for
`pyfakefs`. Real filesystem ops are fast and exercise the real OS-level
behaviour (case sensitivity, line endings) the CLI will see in
production.

## Coverage of AC literals

The evaluator looks for AC literal-id mentions in test names or
docstrings. When writing tests for a feature whose AC id is `F01.AC03`,
include the id in the test docstring or name:

```python
def test_get_dotted_path_F01_AC03(...) -> None:
    """F01.AC03: `kvstore get` supports dotted key paths."""
    ...
```

The pre-commit gate's AC-literal-coverage stage greps for these.
