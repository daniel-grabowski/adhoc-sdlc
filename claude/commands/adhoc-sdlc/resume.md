---
description: "adhoc-sdlc resume: load session state from one of the 4 most recent handoffs"
allowed-tools: All
argument-hint: "[--project P]"
---

# /adhoc-sdlc:resume

Read `~/.claude/skills/adhoc-sdlc/reference.md` (Read tool): section "Resume". Read `~/.claude/skills/adhoc-sdlc/SKILL.md`: section "Read-side authority".

Loads the previous session state from a handoff to continue work. Shows up to the 4 most recent sessions and asks which to load. Match the user's language for the questions and summary.

## Execution

The helper (`pack`) is the only read-side authority: do NOT read `adhoc-sdlc/` files via `Read`/`Grep`.

1. Fetch candidates (step 1, list):
   ```bash
   python3 ~/.claude/skills/adhoc-sdlc/scripts/adhoc_sdlc.py pack \
     --intent resume --limit 4 --format json [--project <P>]
   ```
   Pass `--project` only if the user narrowed `$ARGUMENTS`.
2. When `stats.matched == 0` or `warnings` contains `no_candidates` -> "no session to resume" and stop.
3. Build an `AskUserQuestion` with items = pack `related` (max 4). Option label: `updated` + `title`; description with project and `keywords`. Add a separate question (checkbox): "include related history?" and, if yes, a short history angle.
4. Fetch the full state of the chosen session (step 2, detail):
   ```bash
   python3 ~/.claude/skills/adhoc-sdlc/scripts/adhoc_sdlc.py pack \
     --intent resume --name "<chosen name>" --format json \
     [--include-history --history-angle "<angle>"]
   ```
5. Continue using ONLY the pack: use `primary.extracts` (Goal, Next Steps, What Worked/Didn't), run "Suggested Skills" if indicated, and start from "Next Steps". Do NOT open the handoff file with `Read`: the extracts are in the pack.

## Note

This is a start-of-context-window command: it modifies no files, it only reads state and resumes.
