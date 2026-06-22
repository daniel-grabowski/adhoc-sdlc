# adhoc-sdlc integration notes for temper

This file describes how to integrate `temper` into the existing `adhoc-sdlc` flow without rewriting the whole skill.

## 1. Add a new mode toggle

In `SKILL.md`, section `Phase 0: mode gate`, add a sixth toggle after `Plan CoVe` and before `Execution CoVe`:

```text
6. Strategy Tempering.
Yes: run a focused failure-mode pass after Plan CoVe and before saving the plan. It checks whether the strategy survives edge cases, retries/idempotency, partial failure, migration/existing state, integration boundaries, verification gaps, reversibility, architecture responsibility leaks, and Harness-specific workflow drift.
No: rely on the normal planning review.
```

Variant note: the separate-toggle form above matches the Codex and Codex-plugin `SKILL.md`, where Phase 0 lists each mode as its own yes/no toggle, so `strategy-temper` becomes a sixth toggle. The Claude variant packs the gates into one `AskUserQuestion` bound by a four-question limit, so there `strategy-temper` is added as a third item inside the planning-gates multi-select (Plan CoVe, Strategy Temper, Execution CoVe), not as a sixth question. Both forms record the same `strategy-temper` key in `## Mode`.

## 2. Extend the Mode section written into plans

Existing mode keys:

```text
brainstorming
deep-code-verification
test-execution
plan-cove
execution-cove
```

Add:

```text
strategy-temper
```

Example:

```yaml
## Mode

brainstorming: off
deep-code-verification: on
test-execution: on
plan-cove: on
strategy-temper: on
execution-cove: on
```

## 3. Run order in planning

Recommended planning order:

```text
Phase 1 design decisions
  -> Plan CoVe, if ON
  -> Strategy Tempering, if ON
  -> revise plan body
  -> save plan
```

Important boundary:

- `plan-cove` verifies facts and assumptions.
- `strategy-temper` checks the strategy against failure modes.
- If `strategy-temper` finds a risk that depends on an unverified fact, send it back to CoVe or mark it as assumption-based.

## 4. Add plan sections

When `strategy-temper` is ON, insert these sections into the plan body:

```markdown
## Tempered Risks

- <condition> -> <fix>

## Accepted Risks

- <condition> -> <why acceptable>
```

The final plan must already include the fixes. Do not leave `Tempered Risks` as a detached TODO list.

## 5. Execution behavior

`strategy-temper` belongs primarily to planning. `exec` should not re-run it automatically unless the user asks or the implementation strategy changes materially.

If execution deviates from the tempered plan, record the deviation in the execution journal using the helper, for example:

```bash
python3 <skill-dir>/scripts/adhoc_sdlc.py execute \
  --name "<name>" \
  --title "<title>" \
  --decision "Changed implementation strategy after tempering found <risk>; accepted/fixed because <reason>."
```

## 6. History angles unlocked by temper

Useful `/adhoc-sdlc:history` angles after this integration:

```text
recurring accepted risks
repeated plan failure modes
implementation deviations after tempering
skipped tests that later caused fixes
strategy risks by module
Harness workflow drift
```
