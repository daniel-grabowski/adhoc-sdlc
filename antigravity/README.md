# adhoc-sdlc for Antigravity CLI (roadmap)

Status: planned, not yet implemented.

This directory is a placeholder for the Antigravity CLI variant of the `adhoc-sdlc`
skill. The goal is the same as the other runtimes: a confirmed plan plus an
incremental, resumable execution journal under `./adhoc-sdlc` in the project,
driven by the shared, stdlib-only Python helper.

## What carries over

The behavioral core is runtime-agnostic and is already shared by the Claude Code
and Codex variants:

- the Python helper (`scripts/adhoc_sdlc.py`, `scripts/sdlc_doc.py`) and its tests,
- the file contract (plan markdown, JSON execution journal, handoff snapshots),
- the command contract (plan, exec, handoff, resume, history) and read-side
  authority rules.

Only the packaging and the path references differ per runtime (Claude Code uses
`${CLAUDE_PLUGIN_ROOT}`; Codex uses its install path).

## What is open

The extension/skill/plugin mechanism for the Antigravity CLI has not been verified
in this repository yet, so the packaging is intentionally left undefined here
rather than guessed. Before building this variant:

1. Confirm how Antigravity CLI loads skills/commands and how it references bundled
   scripts (path variable or fixed install location). A starting point is the
   `antigravity-tools.md` platform mapping in the superpowers skill references.
2. Adapt the command markdown to Antigravity's path convention (mirroring what the
   Claude and Codex variants do), keeping the Python helper byte-for-byte identical.
3. Add an install path and verification steps to the repository `README.md`.

Until those are confirmed, treat this variant as not shipped.
