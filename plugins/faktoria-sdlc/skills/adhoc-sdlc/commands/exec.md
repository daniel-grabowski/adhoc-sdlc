---
description: "adhoc-sdlc exec: run a saved plan + execution journal"
allowed-tools: All
argument-hint: "--name \"desc\" --title \"title\" [--append \"entry\" --files a,b] [--status done]"
---

# /adhoc-sdlc:exec

Read this skill's `SKILL.md`: sections "Native todo list" and "Plan file" (the `## Mode` contract). Read this skill's `reference.md`: section "Execute journal (JSON)". Resolve `<skill-dir>` to the directory containing that `SKILL.md`.

Runs a previously saved plan and keeps the execution journal. Maps to the helper's `execute` mode. Match the user's language for all output; keep filenames ASCII.

## Argument parsing

From `$ARGUMENTS` extract `--name` (the same name as the plan), `--title`, and optionally: `--append "entry"` (alias `--note`) with `--phase "label"` and `--files a.pas,b.css` (`--change edit|add|delete|rename`, default edit); `--decision`, `--verification` (+ `--command`), `--final`, `--status {in-progress|done|abandoned}`. The journal is native JSON (`execute-*.json`).

## Execution

1. Create or open the execution journal with the helper (creates it on the first call, appends with `--append`):
   ```bash
   python3 <skill-dir>/scripts/adhoc_sdlc.py execute \
     --name "<name>" --title "<title>" [--append "<entry>" --files <a,b> --phase "<label>"] [--status <s>]
   ```
2. CHECK the exit code. On non-zero, read `ERROR/EXPECTED/EXAMPLE`; the most common case is no plan of that name (create it first with `/adhoc-sdlc:plan`).
3. Read the returned `plan=...` and `execute=...`. Read the plan and realize its steps. Read the plan's `## Mode` section to learn the execution modes (the test toggle governs this command; brainstorming and deep-verify belong to planning). If there is no `## Mode` section, treat every mode as OFF.
4. Native todo list, REQUIRED before the first change: seed it from the plan's key changes + a verification step. Claude Code: `TodoWrite`; Codex: `update_plan`. Exactly one `in_progress`; mark `completed` immediately when done. Every `completed` maps to at least one journal entry.
5. Keep the journal INCREMENTAL and ONLY through the helper (never manual `Edit`/`Write` on the JSON). After each finished task or phase, append an entry with the touched files: `execute --append "<what was done>" --files <files> [--phase "<phase>"]`. Decisions and deviations via `--decision`, verification outcomes via `--verification "<outcome>" [--command "<cmd>"]`.
6. Testing (per `## Mode`):
   - test = ON: pick a method for the stack (UI: agent-browser or Playwright depending on availability; logic: the project's unit-test framework), run existing tests and write or adjust unit tests as needed. Record outcomes with `--verification` (and `--command`).
   - test = OFF: skip automated tests.
7. Final self-check, ALWAYS (regardless of the test toggle): review what was actually done against the plan, then record it with `--verification` so the trace lives in the journal.
8. Close the journal: `--final "<result>" --status done`.

## Output

A report per the rules (goal, changed, verified, remaining/limitations). The journal path.
