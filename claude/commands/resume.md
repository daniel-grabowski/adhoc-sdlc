---
description: "adhoc-sdlc resume: load session state from one of the 4 most recent handoffs"
allowed-tools: All
argument-hint: "[--project P]"
---

# /adhoc-sdlc:resume

Read `${CLAUDE_PLUGIN_ROOT}/skills/adhoc-sdlc/reference.md` (Read tool): section "Resume". Read `${CLAUDE_PLUGIN_ROOT}/skills/adhoc-sdlc/SKILL.md`: section "Read-side authority".

Loads the previous session state from a handoff to continue work. Shows up to the 4 most recent sessions and asks which to load. Match the user's language for the questions and summary.

## Execution

The helper (`pack`) is the only read-side authority: do NOT read `adhoc-sdlc/` files via `Read`/`Grep`.

1. Fetch candidates (step 1, list):
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/adhoc-sdlc/scripts/adhoc_sdlc.py pack \
     --intent resume --limit 4 --format json [--project <P>]
   ```
   Pass `--project` only if the user narrowed `$ARGUMENTS`.
2. When `stats.matched == 0` or `warnings` contains `no_candidates` -> "no session to resume" and stop.
3. Build a structured question prompt with items = pack `related` (max 4). Option label: `updated` + `title`; description with project and `keywords`. Add a separate question (checkbox): "include related history?" and, if yes, a short history angle.
4. Fetch the full state of the chosen session (step 2, detail):
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/adhoc-sdlc/scripts/adhoc_sdlc.py pack \
     --intent resume --name "<chosen name>" --format json \
     [--include-history --history-angle "<angle>"]
   ```
5. Continue using ONLY the pack: use `primary.extracts` (Goal, Next Steps, What Worked/Didn't), run "Suggested Skills" if indicated, and start from "Next Steps". Do NOT open the handoff file with `Read`: the extracts are in the pack.

## Model routing (Claude Code)

The detail pack render is mechanical; delegate it to keep the main loop (Opus) free of the ~10 KB detail pack.

- Step 1 (list candidates) and step 3 (structured question which session) stay in the MAIN loop: the candidate list is small and the choice is user interaction.
- Steps 4-5 (fetch the detail pack for the chosen session and render the continuation context from `primary.extracts`) go to a SUBAGENT: dispatch one read-only agent with `model: sonnet` (Agent tool, `subagent_type: general-purpose`). Its prompt must carry: the chosen `--name` (and `--include-history --history-angle` if selected), the read-side authority rule (only the helper `pack`; never read the corpus `./adhoc-sdlc`), the instruction to summarize Goal / progress / Next Steps from the pack only, and the editorial rules (Polish with full diacritics, no em-dash, no emoji). It returns ONLY the continuation summary (Goal, Next Steps, What Worked/Didn't) as a string and writes nothing.
- After the subagent returns, the MAIN loop continues the actual work from "Next Steps" (that work is NOT delegated - it needs live session context).

Boundary (do NOT delegate): the resumed implementation itself, planning, and journaling stay on the main model. Only the read/recon render is routed to Sonnet.

Fallback: if the Agent tool is unavailable (e.g. Codex) or the user asked to keep it inline, run steps 4-5 yourself. The routing is an optimization, not a contract change.

## Note

This is a start-of-context-window command: it modifies no files, it only reads state and resumes. Read-only (no file writes), so it is safe to run under plan mode.
