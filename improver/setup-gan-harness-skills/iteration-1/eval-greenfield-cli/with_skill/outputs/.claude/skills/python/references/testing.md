# Testing — pytest

`kvstore` uses **pytest** as the test runner. No fancy plugins required
for a small CLI inspector; add them as gaps appear.

## Layout

```
tests/
├── conftest.py        # shared fixtures
├── test_cli.py        # CLI behaviour via `main(argv=[...])`
└── test_inspector.py  # unit tests for the loader / lookup logic
```

Keep `tests/` outside `src/` (see layout.md).

## conftest.py — shared fixtures

```python
# tests/conftest.py
import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_config(tmp_path: Path) -> Path:
    """A small JSON kv-store used by multiple tests."""
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "server": {"host": "localhost", "port": 8080},
        "feature_flags": {"login_v2": True},
    }))
    return path
```

## Test patterns

**Black-box CLI test** — invoke `main(argv=[...])` and assert on the
returned exit code + captured stdout. Avoid subprocess unless you need
real `sys.argv` parsing or shell quoting tested.

```python
from kvstore.cli import main


def test_get_nested_key(sample_config, capsys):
    rc = main(["get", str(sample_config), "server.host"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "localhost"


def test_missing_key_returns_user_error(sample_config, capsys):
    rc = main(["get", str(sample_config), "missing.key"])
    assert rc == 1
```

**Unit test** — import the module directly, no I/O monkeypatching beyond
`tmp_path`.

## Property-based testing (Hypothesis) — optional

For the JSON loader, a round-trip property is a high-value PBT:

```python
from hypothesis import given, strategies as st
import json
from kvstore.inspector import load

@given(st.dictionaries(st.text(min_size=1), st.integers()))
def test_load_roundtrip(tmp_path, data):
    p = tmp_path / "x.json"
    p.write_text(json.dumps(data))
    assert load(p) == data
```

Hypothesis is a dev-extra; add only when the slice warrants it.

## What to NOT test

- The Python stdlib itself (`json.loads` correctness, etc.)
- argparse's own behaviour — test only `kvstore`'s wiring
- File-permission edge cases on platforms you don't ship to
