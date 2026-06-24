---
description: "adhoc-sdlc history: full-text recall (BM25) over the journal corpus, grouped by session (read-only)"
allowed-tools: All
argument-hint: "<free text: what you are looking for> [--project P]"
---

# /adhoc-sdlc:history

Read `{{SKILL_HOME}}/reference.md` (Read tool): section "History". Read `{{SKILL_HOME}}/SKILL.md`: section "Read-side authority".

A READ-ONLY mechanism for returning to earlier work: it creates and modifies nothing. You type FREE TEXT (no keywords, no title, no project required) and a deterministic Python full-text search (BM25, grouped by SESSION) ranks the past sessions, returning for each what was planned, decided, executed, verified and where the red light was. This is the "history of decisions, not code": the diff shows WHAT changed, `adhoc-sdlc` shows WHY. The model presents and (on request) synthesizes; it never scans the corpus itself. Match the user's language for the rendered report.

If {{ASK}} fails with an input-validation error, retry the call once with the same content (a transient serialization glitch, not a mistake in your input) before falling back to plain-text questions.

## Two modes

1. SEARCH (retrieval, default, the hot path): Python ranks sessions for your free text. This is `search`, a full-text recall, NOT the old keyword gate and NOT embedding-based semantic search.
2. SYNTHESIS (presentation, on demand): once you pick a session, the model writes a fuller narrative of that ONE session FROM the artifacts the search already returned (`summary_slots` + `snippets`), not from a fresh corpus scan.

Python does the retrieval and the model does the presentation, never the reverse.

## Query (free text)

Take the query VERBATIM from `$ARGUMENTS`. Do NOT extract keywords and do NOT invent an "angle": the whole point is that plain free text works (the persistent original prompt bridges Polish wording to English-tagged plans). When `$ARGUMENTS` is empty -> ask the user {{ASK}} for a short free-text phrase (what you are trying to recall).

## Execution

The helper (`search`) is the only read-side authority: do NOT use `Read`/`Grep`/`Glob` on `adhoc-sdlc/`.

1. Run the full-text recall:
   ```bash
   python3 {{SKILL_HOME}}/scripts/adhoc_sdlc.py search "<free text>" --format json [--project <P>] [--limit N]
   ```
   CHECK the exit code; on non-zero read `ERROR/EXPECTED/EXAMPLE` and fix the flags. The default `--limit` is fine; raise it only for a wider sweep.
2. Read `stats` and `warnings`:
   - `warnings: ["empty_query"]` -> ask the user for a real phrase.
   - `warnings: ["no_matches"]` (empty `results`) -> say plainly nothing in the corpus matches this text; suggest a different phrasing or a broader term. Do NOT invent matches and do NOT read files.
3. Present the ranking (mode 1) using ONLY the search result:
   - header: the `query`, `query_terms`, sessions in scope and returned (from `stats`).
   - per session, in ranked order: `coverage` (how many distinct query words matched) and `score`, `session`, `title`, project, `updated`; `matched_terms` and `matched_fields` (WHY it matched: keywords / name / title / original_prompt / summary / decisions / steps / ...); `artifacts` (plan / execute / handoff, referenced by `artifacts[].path`); the `summary_slots` (planned / decided / executed / verified / red_lights) and the best `snippets` (type + heading + excerpt).
   - honesty: the query is split into individual words and matched per word over whole words (not as a literal phrase, not character n-grams). Ranking is coverage-first (a session matching two query words ranks above one matching a single word; `score` only breaks ties within the same `coverage`). `matched_fields` reflects real content hits (boilerplate template headings are not indexed). A stem bridge shows as `query~corpus` in `matched_terms` (a fuzzy root match, not an exact one); a `score` much lower than its coverage peers means a thinner overlap, so say so. The result is lexical recall, not understanding.
4. SYNTHESIS (mode 2, only if the user picks a session or asks to go deeper on one): write a fuller narrative of that ONE session FROM its `summary_slots` and `snippets` already in the result (the goal, what was decided and why, what was verified, where it stopped / the red light). Still no corpus reads.
5. Write NOTHING. State incompleteness (`no_matches`, a thin top score) as fact; if needed, re-run `search` with a different phrase or a wider `--limit`. End with {{ASK}} (max 1-2): "which session do you want to return to, and why that one?" -> resume it (`/adhoc-sdlc:resume`), open a new plan (`/adhoc-sdlc:plan`), search again with a different phrase, or nothing.

## Performance and routing

The expensive part (discovery, parsing, ranking) is the deterministic Python search, and it is instant; the model only presents the pre-digested result. Run `search` and render the ranking INLINE in the main loop. That is the fix for the old slow path, where keyword extraction plus a heavy render subagent sat in front of the corpus. Do not put an LLM in the hot search path. Only for an unusually wide sweep (large `--limit`, many sessions) may you offload the rendering to a read-only subagent with `model: sonnet`{{SUBAGENT_VIA}}, carrying the verbatim query, the read-side authority rule (only the helper `search`; never `Read`/`Grep`/`Glob` the corpus `./adhoc-sdlc`), the presentation contract above and the editorial rules (Polish with full diacritics, no em-dash, no emoji); it returns only the finished report. Asking "what next" via {{ASK}} always stays in the main loop.

## Note

Read-only by definition: a reconnaissance tool over your own work history (what was agreed, done, verified, and where it stopped), not an implementation step. Safe under plan mode: the helper only searches and prints, it creates and changes nothing.
