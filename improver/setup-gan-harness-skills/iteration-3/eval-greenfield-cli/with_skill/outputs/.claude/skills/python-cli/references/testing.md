# pytest conventions for python-cli

## File layout

- Tests live under `tests/`, mirroring source structure where helpful.
- File names: `test_<module>.py`. Function names: `test_<behavior>`.
- One assertion family per test where possible; multiple `assert` lines
  are fine when they verify the same behavior end-to-end.

## Invoking the CLI in tests

Prefer calling `cli.main([...])` directly over `subprocess.run`. It is
faster, gives proper traceback, and lets pytest's `capsys` fixture
capture stdout/stderr.

```python
from <pkg> import cli


def test_help_exits_zero(capsys):
    exit_code = cli.main(["--help"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "usage" in captured.out.lower()
```

When you must test the installed entrypoint (e.g., to verify
`pyproject.toml [project.scripts]` wiring), use `subprocess.run([sys.executable, "-m", "<pkg>", ...])`
in one smoke test — not as the default style.

## Property-based testing (Hypothesis)

Hypothesis tests are decorated unit tests; they run through the same
`pytest` command (no separate `[pbt]` sensor key). Use them when:

- A function has a clear round-trip property (`parse(format(x)) == x`).
- An invariant must hold across an input domain (idempotency,
  monotonicity, commutativity).

```python
from hypothesis import given, strategies as st


@given(st.text())
def test_round_trip(s: str) -> None:
    assert decode(encode(s)) == s
```

Cap the example budget when a property test is slow:
`@settings(max_examples=50)`.

## What NOT to test

- argparse's own behavior (it has its own tests).
- Implementation details that don't affect user-observable behavior.
- Trivial getters / passthroughs.

## Coverage philosophy

Test coverage is a smell detector, not a target. A line uncovered after
a feature-complete pass is a hint to look harder, not a number to
chase.
