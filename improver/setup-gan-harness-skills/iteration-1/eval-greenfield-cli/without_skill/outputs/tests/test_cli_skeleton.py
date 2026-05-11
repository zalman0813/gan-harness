"""Skeleton smoke tests for the kvstore CLI.

These exist only to confirm the toolchain (pytest discovery, src layout,
editable install) is wired correctly. Real feature tests are added by
the generator per sprint contract.
"""

from __future__ import annotations

import pytest

from kvstore.cli import build_parser, main


def test_build_parser_returns_parser() -> None:
    """Sanity: build_parser() returns a configured argparse.ArgumentParser."""
    parser = build_parser()
    assert parser.prog == "kvstore"


def test_version_flag_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """--version uses argparse's built-in action, which exits 0."""
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "kvstore" in out


def test_main_with_no_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    """No-arg invocation prints help and returns 0 (no subcommands yet)."""
    rc = main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "usage:" in out.lower()
