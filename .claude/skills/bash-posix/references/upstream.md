# Provenance

| File | Source URL | Revision (commit SHA) | License | Fetched at |
|---|---|---|---|---|
| google-shell-style-guide.md | https://raw.githubusercontent.com/google/styleguide/gh-pages/shellguide.md | 3c5c895c68bfb108cd5d936937dc36e2dfbdbcc2 (refs/heads/gh-pages HEAD at fetch time) | Apache 2.0 (Google styleguide) | 2026-05-13 |

## Notes

- `google-shell-style-guide.md` is 1343 lines — over the soft 500-line
  cap, but per stack-skill-creator vendoring rule the verbatim-canonical
  content precedence keeps it whole.
- Vendored via `curl -sL` against the GitHub raw URL — no LLM in the
  middle, true verbatim text.
- The Google style guide is broader than POSIX bash strictly — it
  recommends bash 4+ idioms (associative arrays, `[[ ]]`, etc.). When
  the target stack must run under POSIX `sh`, the bash-specific sections
  serve as anti-patterns rather than guidance; the generator should
  reason about which subset applies given the spec.md cross-cutting
  constraints.
