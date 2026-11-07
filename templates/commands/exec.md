---
description: "adhoc-sdlc exec: run a saved plan + execution journal"
allowed-tools: All
argument-hint: "--name \"desc\" --title \"title\" [--task T1 --append \"entry\" --files a,b] [--task T1 --task-status done] [--status done]"
---

# /adhoc-sdlc:exec

Read `{{SKILL_HOME}}/SKILL.md` (Read tool): sections "Execution tasks" and "Plan file" (the `## Mode` contract). Read `{{SKILL_HOME}}/reference.md`: sections "Execute journal (JSON)" and "Execution tasks".

Runs a previously saved plan and keeps the execution journal. Maps to the helper's `execute` mode. Match the user's language for all output; keep filenames ASCII.

## Argument parsing

From `$ARGUMENTS` extract `--name` (the same name as the plan), `--title`, and optionally: `--append "entry"` (alias `--note`) with `--phase "label"` and `--files a.pas,b.css` (`--change edit|add|delete|rename`, default edit); `--decision`, `--verification` (+ `--command`), `--final`, `--status {in-progress|done|abandoned}`; task operations `--task Tn` (with `--append`, `--verification` or `--task-status {in_progress|done}`) and `--task-add "title"`. The journal is native JSON (`execute-*.json`).

## Execution

1. Create or open the execution journal with the helper (creates it on the first call, appends with `--append`):
   ```bash
   python3 {{SKILL_HOME}}/scripts/adhoc_sdlc.py execute \
     --name "<name>" --title "<title>" [--task <Tn> --append "<entry>" --files <a,b> --phase "<label>"] [--status <s>]
   ```
2. CHECK the exit code after EVERY helper call. On non-zero (exit 2), read `ERROR/EXPECTED/EXAMPLE`, fix the call and repeat it; a refused call writes nothing. The most common case on the first call is no plan of that name (create it first with `/adhoc-sdlc:plan`).
3. Read the returned `plan=...` and `execute=...`. Read the plan and realize its steps. Read the plan's `## Mode` section to learn the execution modes (the `test-execution` toggle governs automated tests; `execution-cove` governs the final CoVe; brainstorming, deep-code-verification, plan-cove, and strategy-temper belong to planning). If there is no `## Mode` section, treat every mode as OFF.
4. Task list, REQUIRED before the first change. The plan's `## Tasks` (bullets `- [T1] <title>`) were loaded into the journal when it was created; the helper is the only task list (there is no native task-tracking tool to keep in sync). Read the state with `python3 {{SKILL_HOME}}/scripts/adhoc_sdlc.py tasks --name "<name>" --format tsv` (one `id<TAB>status<TAB>title` line per task; `--format json` adds `open` and `in_progress`). Below, `execute ...` stands for `python3 {{SKILL_HOME}}/scripts/adhoc_sdlc.py execute --name "<name>" --title "<title>"` (both flags are required on every call). Then:
   - Empty list (a plan without `## Tasks`): add the tasks with `execute ... --task-add "<task title>"` (repeatable, one per key change plus one verification task) BEFORE the first entry; the helper refuses `--append` on a journal without tasks and records each added task as a plan deviation. Use `--task-add` the same way for work discovered mid-flight.
   - Start one task: `execute ... --task T1 --task-status in_progress`. Exactly one task is `in_progress` at a time; the helper refuses a second one.
   - Finish it: `execute ... --task T1 --task-status done`, right after the work is done and before starting the next task. The helper refuses `done` while the task has no entry or verification with `--task T1`; an entry without `--task` does not count. One call can do both: `execute ... --task T1 --append "<what was done>" --files <files> --task-status done`.
   - Reopening a `done` task (setting it back to `in_progress`) is allowed when rework turns up. Before marking it `done` again, append a new entry with `--task <Tn>` that describes the rework; the helper already accepts `done` on the earlier entry, so this rule is yours to keep.
   - Two separate vocabularies: the journal status is `in-progress|done|abandoned` (hyphen, `--status`), the task status is `in_progress|done` (underscore, `--task-status`; a task starts as `pending`). For example `--task T2 --task-status in_progress` starts a task, while `--final "<result>" --status done` closes the journal.
   - A journal created before task lists (`tasks --format json` reports `legacy: true`) refuses the task flags: continue it with plain entries as before, or close it and start a new plan.
5. Keep the journal INCREMENTAL and ONLY through the helper (never manual `Edit`/`Write` on the JSON). After each finished step, append an entry for the current task with the touched files: `execute ... --task <Tn> --append "<what was done>" --files <files> [--phase "<phase>"]`. Decisions and deviations via `--decision`, verification outcomes via `--verification "<outcome>" [--command "<cmd>"]` (add `--task <Tn>` when the outcome belongs to a task, for example the verification task). If execution discovers a material strategy change, record it as a decision/deviation through the helper; when the change affects architecture, contracts, migration, retry/idempotency, data safety, or reversibility, recommend a compact Temper pass before continuing, but do not run it automatically unless the user requested auto-selected gates.
6. Testing (per `## Mode`):
   - `test-execution` = ON: pick a method for the stack (UI: agent-browser or Playwright depending on availability; logic: the project's unit-test framework), run existing tests and write or adjust unit tests as needed. Record outcomes with `--verification` (and `--command`).
   - `test-execution` = OFF: skip automated tests.
7. Final self-check, ALWAYS (regardless of the test toggle): review what was actually done against the plan and the `SKILL.md` Engineering checklist, then record it with `--verification` so the trace lives in the journal. If the implementation intentionally violates the checklist (for example extra abstraction, skipped tests, or a security/performance tradeoff), record the reason with `--decision` or `--verification`; do not leave it implicit.
8. If `execution-cove` is ON, run a compact CoVe pass before the final close:
   - draft the final report as provisional;
   - ask independent verification questions against the actual diff/status, journal entries, task states from `tasks`, and command outputs;
   - mark claims as consistent, inconsistent, or inconclusive;
   - revise the final report to keep only verified or explicitly caveated claims;
   - record the outcome with `--verification "<CoVe outcome>"` (and `--command` when a command was used).
9. Close the journal only after every task is `done` (`tasks --format json` shows an empty `open`): `--final "<result>" --status done`. The helper refuses `--final` and `--status done` while any task is open; to stop without finishing, use `--status abandoned` and say why.

## Output

A report per the rules (goal, changed, verified, remaining/limitations). The journal path.

## Note

This command WRITES to the project corpus `./adhoc-sdlc` through the helper (it creates and appends the execution journal). It is not read-only: under plan mode, be aware the helper still creates and updates the journal via Bash, even though `Edit`/`Write` are gated.
