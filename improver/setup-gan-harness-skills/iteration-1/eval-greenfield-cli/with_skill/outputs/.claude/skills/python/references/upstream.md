# Provenance

This Starter stack skill was scaffolded by setup-gan-harness-skills on
2026-05-11 for project `kvstore`. No web pages were fetched during
scaffolding — the references encode well-known, canonical Python
conventions paraphrased here (not vendored verbatim from upstream).

| File | Source | Notes |
|---|---|---|
| layout.md | Canonical `src/` layout pattern (Python Packaging Authority guides) | Not vendored verbatim — re-vendor PyPA "Packaging Python Projects" tutorial for verbatim text |
| cli.md | Canonical argparse + PEP 621 `[project.scripts]` patterns | Not vendored verbatim — re-vendor `docs.python.org/3/library/argparse.html` and `packaging.python.org` for verbatim |
| testing.md | pytest canonical patterns | Re-vendor `docs.pytest.org/en/stable` for verbatim test discovery rules |
| lint-typecheck.md | Ruff + mypy default configs | Re-vendor `docs.astral.sh/ruff` and `mypy.readthedocs.io` for authoritative rule lists |

When a downstream agent needs an exact rule from upstream (e.g., the
literal text of a Ruff rule code), the operator should run
stack-skill-creator's Comprehensive scope to WebFetch the canonical
page and append to this table with `fetched_at` + revision.
