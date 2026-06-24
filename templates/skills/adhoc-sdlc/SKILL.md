---
name: adhoc-sdlc
description: "What: lightweight SDLC for small implementation work with a confirmed plan and resumable execution journal. Why: use it when ad hoc fixes, quick features, or refactors need durable context, touched-file history, verification, and safe handoff without a formal issue."
---

# Adhoc SDLC

## What

`adhoc-sdlc` turns small implementation work into a guided plan plus an incremental execution journal in the current project.

## Why

Use it when a task is too small for a formal issue but still needs durable decisions, touched-file history, verification evidence, resume support, and handoff safety.

## Overview

Use this skill for lightweight ad hoc work in the current project: too small for a formal issue workflow, but worth a durable plan and a resumable execution history. It produces two files under `./adhoc-sdlc`: a confirmed plan (`plan-*.md`) and an incremental execution journal (`execute-*.json`). The helper owns both; you do the work.{{SKILL_HOME_NOTE}}

The full file contract (frontmatter, files, helper flags, journal operations, handoff/resume/history mechanics) is in `reference.md`; read the section a command points you to.

## Language

Instructions in this skill and its commands are English; that is the source of truth. The behavior adapts to the conversation:

- Match the user's language for all user-facing output: questions asked via {{ASK}}, status reports, and the prose body of plan files and journal entries.
- Keep machine-facing identifiers ASCII: semantic names and filenames are always lowercase ASCII kebab-case (the helper normalizes them).

## Commands (router)

The skill exposes sub-commands invoked with a colon. Files live in `{{COMMANDS_HOME}}/`:

| Command | Helper mode | Role |
|---------|-------------|------|
| `/adhoc-sdlc:plan` | `plan` | save a confirmed plan to a file |
| `/adhoc-sdlc:exec` | `execute` | run the plan + execution journal |
| `/adhoc-sdlc:handoff` | `handoff` | snapshot session state (history, many files) |
| `/adhoc-sdlc:resume` | `pack --intent resume` | load one of the 4 most recent sessions |
| `/adhoc-sdlc:history` | `search` | full-text recall (BM25) over the corpus, grouped by session (read-only) |

## Lifecycle

1. Discuss and confirm the plan.
2. Create only the plan file.
3. When implementation starts, create the execution journal AND a native todo list, both seeded from the plan's key changes and test-plan steps. Seeding the list is mandatory before the first code change.
4. During work, keep both in sync (see Native todo list); append journal entries incrementally via the helper.
5. At the end, mark the final todos completed, then update verification and final status.

Do not create `execute-*` as a placeholder when only saving a plan. See `reference.md` for the helper and journal operations.

## Native todo list

The native todo list ({{TODO}}) is the live progress view; the journal (`execute-*`) is the durable, resumable record. Maintain both.

- Seed it at execution start: one item per plan key change plus one for verification/testing. Phrase items as concrete actions.
- Keep exactly one item `in_progress`; mark it `completed` the moment it is done, before the next. Do not batch.
- Append the matching journal entry as you finish each task or phase (`execute --append "<note>" --files <touched files>`).
- If the plan changes mid-flight, adjust the todos and note the deviation in the journal.
- Every `completed` todo maps to at least one journal entry, so a session can resume from `execute-*` alone (the todo list does not persist).
- For a plan-only save (no implementation yet), do not create a todo list.

## Plan file

Write the confirmed plan into `plan-*` with: title, summary, key changes, test plan, assumptions. Run the plan command as a guided conversation, not a form. Optionally pass `--prompt "<verbatim request>"` to persist the user's original wording in an `## Original Prompt` section; it is durable context and the main bridge that lets later free-text `history` searches (often Polish) find an English-tagged plan.

### Engineering checklist

Use this as a light decision filter, not a mandatory report for every item:

- **KISS:** choose the simplest design that satisfies the task.
- **YAGNI:** do not add options, layers, or configuration without a concrete need.
- **DRY with judgment:** remove meaningful duplication, but avoid premature abstractions.
- **Local conventions first:** prefer existing repo patterns, helpers, and style.
- **Separation of concerns:** keep responsibilities in the right layer or module.
- **Cohesion over cleverness:** make the code locally understandable before making it clever.
- **Explicit contracts:** keep inputs, outputs, errors, and side effects clear.
- **Testability:** make the verification path concrete and realistic.
- **Security and data safety:** do not weaken validation, authorization, privacy, or secret handling.
- **Performance with evidence:** optimize when there is a real risk or measurement, not by guesswork.

### Phase 0: mode gate (before planning)

After a brief read of the prompt and before planning, ask the user to choose the six modes via {{ASK}}, each with a recommendation tailored to the task.{{ASK_NOTE}} Three are orthogonal yes/no toggles; the other three are quality gates. If the surface limits how many questions can be asked at once, pack the three quality gates into a single multi-select so all six modes fit; otherwise ask them however the surface allows:

1. Brainstorming dialog. Yes: run a light inline brainstorm (intent, variants, edge cases, convergence). No: draft the plan yourself, using the anchors below as an internal checklist and asking only about critical blockers.
2. Deep code verification. Yes: dispatch a read-only subagent{{SUBAGENT_VIA}} to check assumptions against the codebase, then analyze and show its findings. No: handle it yourself and decide whether to read code at all.
3. Test the execution. Yes: pick a method per stack (UI: agent-browser or Playwright depending on availability; logic: the project's unit-test framework), run existing tests and write or adjust unit tests as needed. No: skip tests, but always run a final self-check and record the trace in the journal.
4. Quality gates (multi-select, any combination):
   - Plan CoVe. Selected: before saving the plan, verify the draft plan's factual claims and assumptions with CoVe-style independent questions. Not selected: rely on the normal planning review.
   - Strategy Temper. Selected: after Plan CoVe and before saving the plan, run a focused failure-mode pass on the strategy (edge cases, partial failure, retries/idempotency, migration/existing state, integration boundaries, verification gaps, reversibility, security/data safety, architecture responsibility leaks). Not selected: rely on the normal planning review and the required final self-check.
   - Execution CoVe. Selected: before closing execution as done, verify the final report against the diff, journal entries, todo completion, and actual verification commands. Not selected: rely on tests plus the required final self-check.

Record the chosen modes in a `## Mode` section of the plan file; that section is the contract `exec` reads. Include all six: `brainstorming`, `deep-code-verification`, `test-execution`, `plan-cove`, `strategy-temper`, and `execution-cove` (the last three derived from the quality-gates multi-select). If the user has said "don't ask" (or Phase 0 is skipped), default every mode to OFF (draft the plan, no subagent, no tests, no CoVe gates; always a final self-check + journal) and list the assumed modes explicitly.

### Design decisions

Before writing the file, surface the real design decisions and ask about the open ones. Anchors: scope, approach/variants, edge cases, test plan. Think for the user: propose resolutions with a recommendation, verify assumptions in code and data sources instead of guessing, and call out risks and edge cases proactively. Never assume silently. If the user says "don't ask", record the chosen assumptions visibly instead of hiding them.

After writing the file, close the loop: offer to add or change anything, then offer to run execution now. Running execution makes seeding the native task list mandatory before any code change.

## Read-side authority

For `history`, `resume` and `handoff`, the agent must not scan `adhoc-sdlc/` files directly (`Read`/`Grep`/`Glob`). The helper is the only read-side authority through two modes: `pack` (resume/handoff: discovery, frontmatter parsing, section extraction, relevance scoring, budgeting) and `search` (history: deterministic BM25 full-text recall over the whole corpus, grouped by session). The agent receives a ready context pack or a ready ranking and renders or synthesizes only from it - never the reverse.

Reading `adhoc-sdlc/` files for resume/handoff/history is a layering violation, regardless of being read-only. The letter of the rule is the spirit of the rule.

Two directories share the name `adhoc-sdlc`; do not conflate them. The CORPUS `./adhoc-sdlc` (under the project working directory: `plan-*`, `execute-*`, `handoff-*`) is the data this rule protects: never `Read`/`Grep`/`Glob` it for resume/history/handoff. The SKILL directory `{{SKILL_HOME}}/` (`SKILL.md`, `reference.md`, `scripts/`) holds instructions and helper code: reading it is expected and required, because the commands point you to its sections. The ban is about the project corpus, never about the skill's own files.

Does the pack or the search ranking look incomplete? That is not an invitation to `Read`. Incompleteness is a FACT in `stats`/`warnings`/`budget`. The response: fix the flags and re-run the helper (`pack`: `--max-items`, `--days`, broader `--keywords`; `search`: a different free-text phrase or a wider `--limit`), or report a helper bug. `search` returning `no_matches` means the corpus has nothing for that text, not that you should grep it. Never bypass the helper.

| Excuse | Reality |
|--------|---------|
| "The extract is truncated, I'll read the file" | Truncation is a deliberate budget, not missing data. The extract is a teaser; reach for a specific file's full content only via the narrow exception (the user asks for the raw file), not an unilateral `Read`. |
| "omitted: N, I might miss something, I'll grep the rest" | `omitted` is a fact about scope. Narrow the angle (`--keywords`) or `--days` and re-run `pack`. |
| "The file is right there, one `Read` won't hurt" | One `Read` breaks the layer. The pack is the authority, not a shortcut. |
| "It's only a read, so it's safe" | It's about the layer, not side effects. Read-only does not lift the rule. |
| "The helper might fail, I'll grep as a plan B" | Fix the `pack` call first. Grepping the corpus is not a fallback. |
| "I'll quote the truncated extract as final content" | Need the full content? Re-run `pack` with a larger budget, not `Read`. |

Red flags, STOP if you catch yourself:

- `Read`/`Grep`/`Glob` on `adhoc-sdlc/` during resume/handoff/history,
- "I'll read the corpus by hand because the pack isn't enough",
- "the file is right next to me / one grep just to be sure",
- treating `truncated`/`omitted` as a reason to read files.

Narrow exception: you may `Read` a SPECIFIC file only when the user explicitly asks to inspect the raw file, or the helper reports it cannot build a pack.
