---
description: "adhoc-sdlc plan: interactive planning, save to file, and close the loop into execution"
allowed-tools: All
argument-hint: "--name \"desc\" --title \"title\" [--project P] [--keywords a,b]"
---

# /adhoc-sdlc:plan

Read this skill's `SKILL.md`: sections "Plan file", "Language", "Commands", "Native todo list". For the file contract read this skill's `reference.md` (Helper, Files). Resolve `<skill-dir>` to the directory containing that `SKILL.md`.

Interactive command: it settles the real design decisions with the user, saves the plan file, and finally closes the loop into execution (native task list + optional `exec` run). The file is ONLY a plan; implementation belongs to `exec`, but the plan can launch it right away.

Match the user's language for all output (questions, reports, plan prose). Keep the semantic name and filenames ASCII (the helper normalizes them).

## Argument parsing

From `$ARGUMENTS` extract:
- `--name "..."` short session/task description (the helper normalizes it to a semantic name),
- `--title "..."` human title,
- `--project P` optional project/area token (`[a-z0-9._-]`),
- `--keywords a,b,c` optional keywords (`[a-z0-9-]` tokens).

## Phase 0: mode gate

After a brief read of the prompt and before planning, ask one structured mode-selection question with six orthogonal toggles, each with a task-tailored recommendation. Use a native choice UI when the Codex surface provides one; otherwise ask in plain text with numbered options. Do not imply that this plugin provides its own custom form UI.

1. Brainstorming dialog. Yes: run a light inline brainstorm (intent, variants, edge cases, convergence). No: draft the plan yourself, using the Phase 1 anchors as an internal checklist and asking only about critical blockers.
2. Deep code verification. Yes: dispatch an `Explore` subagent (read-only) to check assumptions against the codebase, then analyze its findings and show them to the user. No: handle it yourself and decide whether to read code at all.
3. Test the execution. Yes: pick a method per stack (UI: agent-browser or Playwright depending on availability; logic: the project's unit-test framework), run existing tests and write or adjust unit tests as needed. No: skip tests, but `exec` always runs a final self-check and records the trace in the journal.
4. Plan CoVe. Yes: before saving the plan, verify the draft plan's factual claims and assumptions with CoVe-style independent questions. No: rely on the normal planning review.
5. Strategy Temper. Yes: run a focused strategy hardening pass after Plan CoVe and before saving the plan. Use it when the task has meaningful architecture, integration, data-safety, reversibility, retry/idempotency, migration, or workflow risk. No: rely on normal planning review and the required final self-check.
6. Execution CoVe. Yes: before closing execution as done, verify the final report against the diff, journal entries, todo completion, and actual verification commands. No: rely on tests plus the required final self-check.

If the user has already said "don't ask" in this session, do not block: default every toggle to OFF (draft the plan, no subagent, no tests, no CoVe gates; always a final self-check + journal) and list the assumed modes explicitly.

Record the chosen modes; they are written into the plan body in Phase 2 as the contract `exec` reads.

## Phase 1: design decisions (anchors + judgment)

Before saving the plan, review the task against the ANCHORS and surface the real open decisions:
- **Scope** what is in, what is out,
- **Approach / variants** when there is more than one sensible path,
- **Edge cases** boundary situations (empty, off-screen, error, zero-length list),
- **Test plan** what verifies the result and how.

Use the `SKILL.md` Engineering checklist as a light filter while making these decisions. Apply KISS, YAGNI, DRY with judgment, local conventions first, separation of concerns, cohesion over cleverness, explicit contracts, testability, security/data safety, and evidence-based performance. Put only task-relevant consequences into `## Key Changes` or `## Assumptions`; do not create a checklist report unless the user asks for one.

Think for the user: propose resolutions with a recommendation, verify assumptions in code and data sources instead of guessing, and call out risks and edge cases proactively. For each anchor with an OPEN decision ask `AskUserQuestion` (concise, recommendation first, labeled "(rec.)"). Skip an anchor that is obvious or has no variant; do not ask about the obvious. When no anchor has an open decision, say so plainly ("no open design decisions") and move on.

Do not assume decisions silently. If the user explicitly says "don't ask / just do it", do NOT block them with questions, but LIST the adopted resolutions as explicit assumptions (open to veto); never hide them only in the file. Adopted decisions go into the plan sections (Assumptions / Key Changes).

If `plan-cove` is ON, run a compact CoVe pass before saving the plan body:
- draft the plan as provisional, not as truth;
- ask independent verification questions for factual claims and assumptions, such as which files/API/tests actually exist, which constraints are confirmed, and which plan claims still need caveats;
- answer those questions from the source of truth for the task (repo inspection, docs, tests, databases, web only when appropriate);
- revise the plan so unverified claims move to `## Assumptions` or are explicitly caveated.

If `strategy-temper` is ON, run a compact Temper pass before saving the plan body:
- Treat the draft plan as a strategy under test, not as final truth.
- Use verified facts from Plan CoVe when available; treat unverified factual claims as assumptions, not facts.
- Enumerate concrete failure modes as `condition -> what breaks -> consequence -> resolution`.
- Cover only relevant categories: edge cases, partial failure, retries/idempotency, migration/existing state, integration boundaries, verification gaps, reversibility, security/data safety, and architecture responsibility leaks.
- For each failure mode either update the plan, move an unverified factual dependency to `## Assumptions`, adjust the test plan, record an accepted risk with a reason, or reject it as speculative noise.
- When risks are worth recording, add `## Tempered Risks` and `## Accepted Risks` sections to the plan body (`condition -> fix` / `condition -> why acceptable`); the fixes must already be incorporated into the plan, not left as a detached TODO.
- Do not expand the feature unless a failure mode proves the original scope is too small to be safe. No fallback sprawl, abstraction creep, or speculative defensive layers.

## Phase 2: save the plan file

1. Create the plan file with the helper:
   ```bash
   python3 <skill-dir>/scripts/adhoc_sdlc.py plan \
     --name "<name>" --title "<title>" [--project <P>] [--keywords <a,b>]
   ```
2. CHECK the exit code. On non-zero, read `ERROR/EXPECTED/EXAMPLE` from stderr and fix the call (e.g. unique name, allowed status/keywords/project); do not create the file by hand.
3. Read the returned `plan=...` path and fill the body sections (`## Summary`, `## Key Changes`, `## Test Plan`, `## Assumptions`) with `Edit`, incorporating the Phase 1 decisions and any `plan-cove` revisions. Then add a `## Mode` section recording the Phase 0 toggles (`brainstorming`, `deep-code-verification`, `test-execution`, `plan-cove`, `strategy-temper`, `execution-cove`, plus any defaults assumed under "don't ask"). When `strategy-temper` is ON and there are risks worth recording, also add the optional `## Tempered Risks` and `## Accepted Risks` sections. Do NOT touch the frontmatter block.

## Phase 3: close the loop

After saving the plan, ALWAYS close the loop with two points: (1) add/change anything in the plan, (2) run execution. Ask them via `AskUserQuestion` by default (max 2 questions). If the user explicitly asked "don't ask" in this session, ask the same two points concisely as text instead of `AskUserQuestion`; closing the loop is mandatory, only the form adapts.

1. "Add or change anything in the plan?" If yes, apply with `Edit` on the body sections and show the change.
2. "Run execution now?":
   - **YES** -> move into execution (like `/adhoc-sdlc:exec`):
     1. create the journal: `python3 <skill-dir>/scripts/adhoc_sdlc.py execute --name "<name>" --title "<title>"`,
     2. FORCE the native task list (Claude Code: `TodoWrite`; Codex: `update_plan`) seeded from `Key Changes` + a verification step. This is MANDATORY before the first code change. Time pressure or a "skip the list / just do it" request does NOT lift it: without the native list, do not start implementation,
     3. execute per the plan; append each significant step incrementally with `execute --append "..." --files <touched files>`; keep exactly one list item `in_progress`, mark it `completed` right after it is done.
   - **NO** -> show the plan path and suggest `/adhoc-sdlc:exec --name <name>` for later.

## Output

The plan path and a 1-2 sentence summary. If execution was launched, report per the rules (goal, changed, verified, remaining/limitations) plus the journal path.
