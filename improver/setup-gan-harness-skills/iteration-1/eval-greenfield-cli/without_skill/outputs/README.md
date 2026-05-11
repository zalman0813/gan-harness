# kvstore

A small command-line inspector for local JSON config files. Reads a
`.json` file as a key-value store and lets you query individual values
by dotted key path.

## Status

Scaffolded skeleton. The first features will be planned by running
`/init` followed by `/loop` (see the gan-harness flow in `CLAUDE.md`).

## Install

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
kvstore --help
```

Once subcommands are implemented (sprint S01 onward), expected shape:

```bash
kvstore get path/to/config.json db.host
```

## Develop

```bash
ruff check src tests       # lint
mypy --strict src          # typecheck
pytest                     # tests
```

## Layout

```
kvstore/
├── pyproject.toml
├── src/kvstore/            # package source
│   ├── __init__.py
│   ├── __main__.py         # python -m kvstore
│   └── cli.py              # argparse parser + main()
├── tests/                  # pytest suite
├── CLAUDE.md               # agent instructions + behavioral foundation
├── CONTEXT.md              # ubiquitous language
└── .claude/                # harness substrate (agents / skills / hooks / commands)
```
