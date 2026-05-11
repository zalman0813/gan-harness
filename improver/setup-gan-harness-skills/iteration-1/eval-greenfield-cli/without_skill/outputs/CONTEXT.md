# Context

The domain ubiquitous language for `kvstore`. AI agents read this before
exploring code so terms used in output (specs, contracts, ADRs, code
identifiers) stay consistent with the project's actual vocabulary.

The codebase is the source of truth for code (signatures, tests, runtime
behaviour). This file fills what code cannot express: what the user
means, which words collapse to one canonical, and how concepts relate.

This file is seeded by `/init` and grows as `/finalize` merges new
domain terms surfaced during each epic. Initial entries below describe
the seed concepts; expand them as the project matures.

## Language

**Config file**:
A local JSON file on disk that holds key-value configuration data. The
input to every `kvstore` invocation. Assumed UTF-8 encoded; assumed
top-level object (not a top-level array or scalar) unless a sprint
explicitly extends this.
_Avoid_: settings file, config, store (store is reserved for the in-memory
view).

**Store**:
The in-memory representation of a loaded config file. Produced by the
loader from a config file's bytes; consumed by the inspector. Not
persisted back to disk in v1 (kvstore is read-only).
_Avoid_: config (config = on-disk), state, model.

**Key path**:
A dotted string identifying one position in the store, e.g.
`db.host` selects `store["db"]["host"]`. The canonical address format
across all subcommands.
_Avoid_: path, selector, query (path is overloaded with filesystem path).

**Subcommand**:
One verb under the `kvstore` CLI (`get`, `keys`, etc.). Each subcommand
maps to one handler in `src/kvstore/cli.py` that takes an
`argparse.Namespace` and returns an int exit code.
_Avoid_: command (overloaded), action, operation.

## Relationships

- A **Config file** is loaded into exactly one **Store** per invocation.
- A **Store** is queried by zero or more **Key path**s, one per
  **Subcommand** invocation that takes a key argument.
- A **Subcommand** is dispatched from `main()` based on the parsed
  `args.command` field; it may read the **Store** but never writes
  back to the **Config file** in v1.
