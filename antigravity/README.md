# adhoc-sdlc for Antigravity CLI

## What

This directory contains the integration for the Antigravity CLI variant of the `adhoc-sdlc`
skill: the same confirmed plan plus incremental execution journal that the
Claude Code and Codex variants already run, driven by the shared, stdlib-only
Python helper.

## Why

Antigravity natively supports the skill structure and resolves paths through its `<skill-dir>` context. The plugin is fully agnostic and shares the exact same `SKILL.md` and `commands` as the other environments, so workflows do not drift.

**Status: experimental (roadmap).** The skills here are the shipped Codex plugin variant under `plugins/adhoc-sdlc/skills/`, registered into Antigravity by `install.sh`. Antigravity is not yet a first-class generated runtime: its `runtimes/antigravity.json` is inactive (`active=false`) and its tool bindings are still to be confirmed, so `tools/render.py` skips it and the end-to-end integration has not been verified.

## What carries over

The behavioral core is runtime-agnostic and is fully shared with the Claude Code and Codex variants:

- the Python helper (`scripts/adhoc_sdlc.py`, `scripts/sdlc_doc.py`) and its tests,
- the file contract (plan markdown, JSON execution journal, handoff snapshots),
- the command contract (plan, exec, handoff, resume, history) and read-side authority rules.

Because Antigravity resolves relative directories on its own, there are no special environment variables needed.

## Installation

Antigravity loads customizations globally from `~/.gemini/config/skills.json`. You can install the skills without modifying any files in the repository.

Run the included installer from the root of this repository:

```bash
./antigravity/install.sh
```

This script registers the absolute path to `plugins/adhoc-sdlc/skills/` in your Antigravity configuration. Antigravity then recognizes `adhoc-sdlc`, `cove`, and `temper`.
