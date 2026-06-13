---
description: "adhoc-sdlc history: analyze the journal corpus for a given angle (read-only)"
allowed-tools: All
argument-hint: "<the angle / what you are looking for> [--project P]"
---

# /adhoc-sdlc:history

Read `~/.codex/skills/adhoc-sdlc/reference.md` (Read tool): section "History". Read `~/.codex/skills/adhoc-sdlc/SKILL.md`: section "Read-side authority".

An ANALYTICAL, READ-ONLY command: it creates and modifies nothing. It searches the journal corpus (plans, execution journals, handoffs) for the ANGLE given by the user, focused on recurring problems and things already done. It ends by asking "what next". Match the user's language for the rendered report.

## Analysis angle (required)

Take the angle from `$ARGUMENTS` (e.g. "recurring build problems", "what was already done on RF-001"). When `$ARGUMENTS` is empty -> `AskUserQuestion` with common angles:
- (a) recurring problems / blockers,
- (b) what was already done / duplicates of earlier approaches,
- (c) decisions and deviations from the plan,
- (d) verifications and outcomes (what passed / did not).

## Execution

The helper (`pack`) is the only read-side authority: do NOT use `Read`/`Grep`/`Glob` on `adhoc-sdlc/`.

1. Extract domain keywords from the angle (this is judgment, e.g. "fpc build problems" -> `build,fpc`).
2. Build the context pack:
   ```bash
   python3 ~/.codex/skills/adhoc-sdlc/scripts/adhoc_sdlc.py pack \
     --intent history --angle "<angle>" --keywords <a,b,c> --format json [--project <P>] [--days <N>]
   ```
   CHECK the exit code; on non-zero read `ERROR/EXPECTED/EXAMPLE` and fix the flags.
3. When `stats.matched == 0` / `warnings:["no_candidates"]` -> say plainly "no corpus for this angle", do not invent. Otherwise render a human report using ONLY the pack, per `presentation` (compact_report, `group_by: theme_then_date`):
   - header: angle + date range (from `items[].updated`) + `matched/included/omitted` stats,
   - thematic groups: cluster `items` by shared keywords (signal `signals.keyword_index`), sort within a group by date descending, name each group (judgment),
   - per item: date, name, type, status, intent/decision/outcome from `extracts`, reference `items[].path` (+ `extracts[].heading`),
   - Conclusions section: RECURRENCE (the same themes over time), "ALREADY DONE" (decisions and their outcome), SSoT candidates.
4. Write NOTHING. State incompleteness (`omitted`, `truncated`) as fact: do not read files; if needed narrow `--keywords`/`--days` and re-run `pack`.
5. End with an `AskUserQuestion` "what next" (max 1-2 questions): create a plan (`/adhoc-sdlc:plan`) / resume a session (`/adhoc-sdlc:resume`) / deepen the analysis (another angle) / nothing.

## Note

Read-only by definition. This is a reconnaissance tool over your own work history, not an implementation step.
