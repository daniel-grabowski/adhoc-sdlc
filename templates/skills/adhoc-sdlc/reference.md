# Adhoc SDLC reference

The detailed contract for the `adhoc-sdlc` skill. The overview, language rule, lifecycle, planning flow and read-side authority live in `SKILL.md`. This file holds the file contract, helper details, the journal operations, and the handoff/resume/history mechanics. Read the relevant section when a command points you here.

## Metadata (YAML frontmatter, the file contract)

Markdown files (plan, handoff) carry explicit frontmatter, parsed by `list`/`resume`/`history`:

```yaml
---
type: plan | execute | handoff
name: <semantic-name>
title: <title>
project: <token [a-z0-9._-] or empty>
keywords: [kw1, kw2]
created: <ISO8601>
updated: <ISO8601>
status: in-progress | done | abandoned
---
```

Plan and handoff are markdown with the frontmatter above. The execution journal is native JSON (`execute-*.json`): the same meta fields at top level plus `plan` (path), `entries` (incremental records: `ts`, `note`, optional `phase`, a `files` list of `{path, change}`), `decisions`, `verification` and `final_result`. Touched files are a structural element, not loose text; `history`/`resume` return them as `touched_files`.

Only the helper creates files under `adhoc-sdlc/` (the single source of truth for names, frontmatter and JSON). Do not write them by hand with `Write`. You may fill the markdown body sections (plan/handoff) with `Edit`, but `execute-*.json` changes only through the helper (`execute --append/--decision/--verification/--final`), never by manual `Edit`/`Write`. The helper is a hard contract guard: bad input gives exit 2 plus `ERROR/EXPECTED/EXAMPLE` on stderr, with zero side effects. After every call, check the exit code and fix the call per the hints when it is non-zero.

## Files

Directory (created automatically if missing, in the current working directory): `./adhoc-sdlc`

Names:

- `plan-YYYY-MM-DD-semantic-name.md`
- `execute-YYYY-MM-DD-semantic-name.json` (execution journal, native JSON)

The semantic name is a short, meaningful kebab-case name, for example `operator-panel-start-stop-good-button`, `rf001-task-options`, `diagnostics-badge`.

Never create two plans with the same semantic name. Before creating a plan, check for existing `plan-*-semantic-name.md` and `execute-*-semantic-name.{md,json}`.

## Helper

Use the bundled helper instead of rewriting file creation logic. It defaults to the current working directory, so run it from the project root (or pass `--root <dir>`).

Create a confirmed plan:

```bash
python3 {{PLUGIN_ROOT}}/skills/adhoc-sdlc/scripts/adhoc_sdlc.py plan \
  --name "operator panel start stop good button" \
  --title "Operator panel fixes: Start/Stop and Good"
```

Start or append execution:

```bash
python3 {{PLUGIN_ROOT}}/skills/adhoc-sdlc/scripts/adhoc_sdlc.py execute \
  --name "operator panel start stop good button" \
  --title "Operator panel fixes: Start/Stop and Good" \
  --append "Implemented the Start/Stop button" \
  --files "OperatorPanel.pas,OperatorPanel.dfm" --phase "implementation"
```

The helper:

- resolves the target to `./adhoc-sdlc` in the current working directory and creates it if missing;
- normalizes the semantic name to ASCII lowercase kebab-case;
- creates only `plan-*` in `plan` mode;
- requires an existing plan before `execute` mode;
- creates `execute-*` only at execution start, and appends timestamped entries if it already exists;
- refuses ambiguous or duplicate semantic names.

## Execute journal (JSON)

The journal is `execute-*.json`, kept incrementally by the helper. After each finished task or phase, add an entry with a note and the touched files, instead of writing the whole journal at the end. All changes go through the helper (the single writer), never by manual `Edit`/`Write`.

Operations (`execute` mode):

- the first call creates the file (requires an existing plan of the same name);
- a step entry: `--append "<note>"` (alias `--note`), optionally `--phase "<label>"` and `--files a.pas,b.css` (with `--change edit|add|delete|rename`, default `edit`); files belong to the entry;
- `--decision "<text>"` appends a decision or deviation;
- `--verification "<outcome>"` (optionally `--command "<cmd>"`) appends a verification result;
- `--final "<text>" --status done` closes the journal.

Every operation updates `updated`. Touched files from `entries[].files` are aggregated and deduplicated into `touched_files` on the read side. If execution is interrupted, the JSON must be enough for another agent to resume safely.

Legacy `execute-*.md` journals (pre-JSON) are still read by `history`/`resume` and can be continued with `--append`; the helper will not write the new structural fields (`--files` etc.) into markdown (fail loud), so such a journal is best closed and replaced with a new one.

## Handoff

A snapshot of session state for a new context window. Created by the helper (`handoff` -> `handoff-<ts>-name.md`, history, every call is a new file). Optional step 0: `pack --intent handoff --name <N> [--project P] [--keywords a,b]` returns `related` (plan/execute/handoff PATHS, no content); use them for Current Progress and to avoid duplication in Next Steps, but do not read those files. The agent fills the body: Goal, Current Progress (reference by path/URL, without copying plans/journals/commits), What Worked, What Didn't Work, Next Steps, Suggested Skills. Redact secrets (keys, passwords, tokens, PII). Read-side authority applies (see `SKILL.md`).

## Resume

Resume from one of up to 4 most recent sessions, in two steps:

1. `pack --intent resume --limit 4 --format json` returns candidates in `related` (metadata). The agent builds an {{ASK}} prompt (label = `updated` + `title`, description = project + keywords) plus an optional "include related history" choice.
2. After the choice: `pack --intent resume --name <chosen> [--include-history --history-angle "..."]` returns `primary` with `extracts` (Goal, Next Steps, What Worked/Didn't). The agent continues from Next Steps using only the pack, without `Read`-ing the file.

No candidates (`stats.matched=0` / `warnings:["no_candidates"]`) -> "no session to resume". Read-side authority applies (see `SKILL.md`).

## History

Retrospective analysis of the corpus (read-only). Requires an "angle". The agent extracts keywords from the angle (judgment) and calls `pack --intent history --angle "<angle>" --keywords a,b [--project] [--days]`. The pack returns `items` with `extracts` (narrowed, scored, budgeted), `signals.keyword_index` (a recurrence signal for grouping) and `presentation` (compact_report, group_by theme_then_date).

Stats contract: `matched` = records in scope (time/project), `relevant` = records with a non-zero keyword overlap (the topical hits), `included` = shown after budget, `omitted` = relevant minus included, `below_threshold` = matched minus relevant (in scope, zero keyword overlap, removed by the relevance gate). When keywords are given the `items` are gated to relevant records only; `warnings:["no_relevant"]` means scope is non-empty but nothing matches the theme. Keyword matching is normalized for simple plural/singular (`colors` matches `color`), so a near-miss token still scores. The agent renders a human report per `presentation`: a title with the angle plus date range plus the stats above (lead with `relevant`/`included`; `below_threshold` is the filtered-out noise, never bare `matched`), thematic groups, a Conclusions section (recurrence, "already done", SSoT candidates) and at most 1-2 "what next" questions. References come from `items[].path` + `extracts[].heading`. Read-side authority applies (see `SKILL.md`).
