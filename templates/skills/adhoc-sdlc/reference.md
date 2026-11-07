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

Plan and handoff are markdown with the frontmatter above. The execution journal is native JSON (`execute-*.json`): the same meta fields at top level plus `schema` (`2` for journals with a task list; absent in older journals), `plan` (path), `original_prompt` (the verbatim request, inherited from the plan's `## Original Prompt` section), `tasks` (the execution task list, see Execution tasks), `entries` (incremental records: `ts`, `note`, optional `phase`, optional `task`, a `files` list of `{path, change}`), `decisions` (optional `task`), `verification` (optional `task`) and `final_result`. Touched files are a structural element, not loose text; `history`/`resume` return them as `touched_files`.

A plan may carry an optional `## Original Prompt` section (written by `plan --prompt "<verbatim request>"`): the user's own wording, stored durably so a later free-text `history` search can match it. It is additive and backward compatible; older artifacts without it stay searchable on their existing content.

Only the helper creates files under `adhoc-sdlc/` (the single source of truth for names, frontmatter and JSON). Do not write them by hand with `Write`. You may fill the markdown body sections (plan/handoff) with `Edit`, but `execute-*.json` changes only through the helper (`execute --append/--decision/--verification/--final/--task-status/--task-add`), never by manual `Edit`/`Write`. The helper is a hard contract guard: bad input gives exit 2 plus `ERROR/EXPECTED/EXAMPLE` on stderr, with zero side effects. After every call, check the exit code and fix the call per the hints when it is non-zero.

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
python3 {{SKILL_HOME}}/scripts/adhoc_sdlc.py plan \
  --name "operator panel start stop good button" \
  --title "Operator panel fixes: Start/Stop and Good" \
  --prompt "Fix the operator panel: Start/Stop buttons and the Good button"
```

`--prompt` is optional; when given, the verbatim text is stored in an `## Original Prompt` section of the plan and inherited into the journal's `original_prompt` field, so `history` can recall the session from the user's own wording.

Start or append execution:

```bash
python3 {{SKILL_HOME}}/scripts/adhoc_sdlc.py execute \
  --name "operator panel start stop good button" \
  --title "Operator panel fixes: Start/Stop and Good" \
  --task T1 --append "Implemented the Start/Stop button" \
  --files "OperatorPanel.pas,OperatorPanel.dfm" --phase "implementation"
```

Read the task state (no side effects):

```bash
python3 {{SKILL_HOME}}/scripts/adhoc_sdlc.py tasks \
  --name "operator panel start stop good button" --format tsv
```

The helper:

- resolves the target to `./adhoc-sdlc` in the current working directory and creates it if missing;
- normalizes the semantic name to ASCII lowercase kebab-case;
- creates only `plan-*` in `plan` mode;
- requires an existing plan before `execute` mode;
- creates `execute-*` only at execution start (with `schema: 2` and the tasks from the plan's `## Tasks`), and appends timestamped entries if it already exists;
- refuses ambiguous or duplicate semantic names.

## Execute journal (JSON)

The journal is `execute-*.json`, kept incrementally by the helper. After each finished task or phase, add an entry with a note and the touched files, instead of writing the whole journal at the end. All changes go through the helper (the single writer), never by manual `Edit`/`Write`.

Operations (`execute` mode):

- the first call creates the file (requires an existing plan of the same name);
- a step entry: `--append "<note>"` (alias `--note`), optionally `--phase "<label>"` and `--files a.pas,b.css` (with `--change edit|add|delete|rename`, default `edit`); files belong to the entry;
- `--decision "<text>"` appends a decision or deviation;
- `--verification "<outcome>"` (optionally `--command "<cmd>"`) appends a verification result;
- `--task Tn` ties an entry (`--append`) or a verification (`--verification`) to a task, and selects the task for `--task-status`;
- `--task Tn --task-status in_progress|done` changes a task's state;
- `--task-add "<task title>"` (repeatable) adds task `T<max+1>` (`pending`, source `added`) and a decision `Odstępstwo od planu: dodano zadanie Tn: <title>` tied to it;
- `--final "<text>" --status done` closes the journal; `--status abandoned` closes it without finishing.

Every call needs `--name` and `--title`. Operations in one call run in a fixed order: task-add, entry, verification, decision, task-status, final/status. For example `--task T1 --append "done the change" --task-status done`, or `--task-add "Fix the edge case" --task T3 --append "started"`.

Every operation updates `updated`. Touched files from `entries[].files` are aggregated and deduplicated into `touched_files` on the read side. If execution is interrupted, the JSON must be enough for another agent to resume safely.

Legacy `execute-*.md` journals (pre-JSON) are still read by `history`/`resume` and can be continued with `--append`; the helper will not write the new structural fields (`--files` etc.) into markdown (fail loud), so such a journal is best closed and replaced with a new one.

## Execution tasks

The plan's `## Tasks` section defines the tasks; the journal field `tasks` holds their state. Format in the plan: one unindented bullet per task, `- [T1] <title>` (also `* [T1] <title>`), ids `T<n>` unique. Indented sub-bullets and prose in the section are ignored; a numbered list is not read as tasks. Any other unindented bullet or a repeated id is refused when the journal is created (exit 2). No section, or the `TODO` placeholder, gives an empty list.

Journal field: `tasks` is a list of `{id, title, status, source}`; `status` is `pending`, `in_progress` or `done`; `source` is `plan` or `added`. Task status (`in_progress`, underscore) and journal status (`in-progress|done|abandoned`, hyphen) are separate vocabularies.

Validation (exit 2, `ERROR/EXPECTED/EXAMPLE`, nothing written):

- a second task `in_progress` (setting the same task `in_progress` again is allowed, also to reopen a `done` task);
- `done` for a task with no entry or verification carrying `--task` for it;
- `--final` or `--status done` while any task is not `done` (the message lists the open tasks); `--status abandoned` is allowed;
- `--append` on a schema 2 journal without tasks (also when creating the journal) until `--task-add`;
- an unknown task, `--task` outside `T<n>`, `--task-status` outside `in_progress|done`, `--task-status` without `--task`, `--task` with no entry, verification or status change, an empty `--task-add` title.

Read the state with `tasks --name <name> [--format json|tsv]` (no side effects). `json`: `semantic_name`, `execute`, `schema`, `legacy`, `items` (`{id, title, status, source}`), `open` (ids not `done`), `in_progress` (id or null). `tsv`: one `id<TAB>status<TAB>title` line per task.

Backward compatibility: a JSON journal without the `schema` field (created before task lists) keeps the old behavior: `--append`, `--verification`, `--final` and `--status done` work as before, and the task flags are refused. Such journals are not migrated.

## Handoff

A snapshot of session state for a new context window. Created by the helper (`handoff` -> `handoff-<ts>-name.md`, history, every call is a new file). Optional step 0: `pack --intent handoff --name <N> [--project P] [--keywords a,b]` returns `related` (plan/execute/handoff PATHS, no content); use them for Current Progress and to avoid duplication in Next Steps, but do not read those files. The agent fills the body: Goal, Current Progress (reference by path/URL, without copying plans/journals/commits), What Worked, What Didn't Work, Next Steps, Suggested Skills. Redact secrets (keys, passwords, tokens, PII). Read-side authority applies (see `SKILL.md`).

## Resume

Resume from one of up to 4 most recent sessions, in two steps:

1. `pack --intent resume --limit 4 --format json` returns candidates in `related` (metadata). The agent presents a choice via {{ASK}} (label = `updated` + `title`, description = project + keywords) plus an optional "include related history" choice.
2. After the choice: `pack --intent resume --name <chosen> [--include-history --history-angle "..."]` returns `primary` with `extracts` (Goal, Next Steps, What Worked/Didn't) and a top-level `tasks` field: the task state of the session's newest schema 2 journal (`{execute, schema, items, open, in_progress}`; null for the list step, without a journal, or for an older journal). The agent continues from Next Steps and the open tasks using only the pack, without `Read`-ing the file.

No candidates (`stats.matched=0` / `warnings:["no_candidates"]`) -> "no session to resume". Read-side authority applies (see `SKILL.md`).

## History

A read-only mechanism for returning to earlier work. The user types FREE TEXT (no keywords, title or project required) and the agent calls `search "<free text>" --format json [--project <P>] [--limit N]`. This is a deterministic, lexical full-text recall (Okapi BM25, k1=1.5, b=0.75), not the old keyword gate and not embedding-based semantic search; the practical "semantic" feel comes from indexing the whole content (summary, decisions, verification, steps) together with the persistent original prompt, not from any understanding of meaning. Python retrieves and ranks; the model only presents what Python returns and never searches the corpus itself.

### How matching works (exact mechanics)

The match unit is the WORD (a whole word, not a character n-gram or trigram), and the query is matched per word, never as one literal phrase. The ranking unit is the SESSION: all records sharing a `name` (plan + execute + handoff) are one document, so a result is a session you return to, not a file. The source of truth is `scripts/sdlc_doc.py`; the constants named below are its current defaults.

1. Query to words. The free text is split into individual words: runs of Unicode alphanumerics, also split on camelCase (`welcome-page` and `frWelcomePage` both yield `welcome`, `page`), lowercased, lightly de-pluralized, filtered by a small PL/EN stoplist; words shorter than `MIN_TERM_LEN` (2) are dropped. Each word is searched independently.
2. Corpus to words. The same tokenization runs over every record of a session merged into one document; section bodies are indexed, template HEADINGS are not (boilerplate, identical across files, so a `matched_field` always reflects real content); field weights boost keywords / name / title / original_prompt over body.
3. Best hit per query word, per session: either an exact word, or (when the query word is at least `FUZZY_MIN_TOKEN` (4) characters and fuzzy is on) a corpus word sharing a leading prefix of at least `FUZZY_MIN_PREFIX` (4) characters, with similarity (shared prefix divided by the longer word) of at least `FUZZY_MIN_SIM` (0.5). An exact word weighs 1.0; a stem hit weighs `FUZZY_PENALTY` (0.6) times similarity, so exact always wins, and the bridge shows as `query~corpus` in `matched_terms`. Words of 2-3 characters match exactly only (below the bridge threshold), and `--no-fuzzy` disables the bridge entirely.
4. Rank. COVERAGE first (how many distinct query words a session matched, so two words always beat one), then Okapi BM25 (`k1` 1.5, `b` 0.75; IDF over sessions) to break ties within the same coverage, then recency, then a deterministic key.

In short: it searches the query as separate words (not as one phrase), and it matches whole words (not four-character chunks or trigrams); the only role of "4" is the fuzzy stem-bridge threshold in step 3.

Result shape per session: `{session, title, project, updated, score, coverage, matched_terms, matched_fields, artifacts[], summary_slots{planned, decided, executed, verified, red_lights}, snippets[]}` (`coverage` = how many distinct query words matched), plus top-level `query`, `query_terms`, `mode: "bm25_fulltext"`, `fuzzy` (bool), `stats` (`files_scanned`, `files_in_scope`, `sessions`, `returned`) and `warnings` (`empty_query`, `no_matches`). `--limit` caps returned sessions (`0` = all).

Two modes: (1) SEARCH renders the ranking from the result above: per session, the score, why it matched (`matched_terms`/`matched_fields`), the artifacts (by `artifacts[].path`), the `summary_slots` (planned / decided / executed / verified / red light) and the best `snippets`; (2) SYNTHESIS, only when the user picks a session, writes a fuller narrative of that ONE session from its `summary_slots` and `snippets` (the history of decisions, not the code). `warnings:["no_matches"]` means the corpus has nothing for that text: say so plainly, do not invent matches and do not read files. The search is instant, so render inline and do not put an LLM in the hot path. End with at most 1-2 "which session to return to, and why" questions. Read-side authority applies (see `SKILL.md`): the only reader is the helper, in `search` mode for history.

PL/EN bridge and limits: the cross-language reach comes from the step-3 stem bridge (`ganta`~`gantt`, `skinowanie`~`skinowe`, `licencja`~`license`) together with the persistent original prompt (often the user's Polish wording), which is the main link to English-tagged plans. The limits: very short roots (under four characters, e.g. `tła`/`tło`) are not bridged, because Polish and English both inflect suffixes and the bridge is anchored on the leading stem; a four-character query word can over-reach to a longer unrelated word sharing those leading letters (the 0.6 penalty and the visible `query~corpus` keep that rare); the method is lexical recall rather than understanding; and artifacts saved before the original-prompt feature are recalled on their existing content only.
