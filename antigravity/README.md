# adhoc-sdlc for Antigravity CLI

## What

This directory contains the integration for the Antigravity CLI variant of the `adhoc-sdlc`
skill: the same confirmed plan plus incremental execution journal that the
Claude Code and Codex variants already run, driven by the shared, stdlib-only
Python helper.

## Why

Antigravity natively supports the skill structure and dynamically resolves paths through its `<skill-dir>` context. The plugin is 100% agnostic and shares the exact same `SKILL.md` and `commands` as the other environments, preventing any drifting workflows.

**Status: Shipped and verified.**

## What carries over

The behavioral core is runtime-agnostic and is fully shared with the Claude Code and Codex variants:

- the Python helper (`scripts/adhoc_sdlc.py`, `scripts/sdlc_doc.py`) and its tests,
- the file contract (plan markdown, JSON execution journal, handoff snapshots),
- the command contract (plan, exec, handoff, resume, history) and read-side authority rules.

Because Antigravity handles relative directory resolution intelligently, there are no special environment variables needed.

## Installation

Antigravity loads customizations globally from `~/.gemini/config/skills.json`. You can install the skills seamlessly without modifying any files in the repository.

Simply run the included installer from the root of this repository:

```bash
./antigravity/install.sh
```

This script safely registers the absolute path to `plugins/adhoc-sdlc/skills/` in your Antigravity configuration. The tool will instantly recognize `adhoc-sdlc`, `cove`, and `temper`.
