# adhoc-sdlc integration notes for temper

This file describes how to integrate `temper` into the existing `adhoc-sdlc` flow without rewriting the whole skill.

## 1. Strategy Temper as a Phase 0 quality gate

In `SKILL.md` and the `plan` command, section `Phase 0: mode gate`, `strategy-temper` is one of the four gates, alongside `Plan CoVe`, `Execution CoVe`, and the cleanup assessment (`cleanup-codebase`):

```text
Strategy Temper.
Selected: run a focused failure-mode pass after Plan CoVe and before saving the plan. It checks whether the strategy survives edge cases, retries/idempotency, partial failure, migration/existing state, integration boundaries, verification gaps, reversibility, architecture responsibility leaks, and Harness-specific workflow drift.
Not selected: rely on the normal planning review.
```

The four gates are presented together. When the runtime's question affordance caps how many questions can be asked at once, they are packed into a single multi-select (four options) so all seven modes fit, and `strategy-temper` is one item inside that gates group rather than a separate question; when the surface allows it, the modes can be asked as individual toggles. Either way the same `strategy-temper` key is recorded in `## Mode`.

## 2. Extend the Mode section written into plans

Existing mode keys:

```text
brainstorming
deep-code-verification
test-execution
plan-cove
execution-cove
cleanup-codebase
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
cleanup-codebase: off
```

## 3. Run order in planning

Recommended planning order:

```text
Phase 1 design decisions (intention-hardening)
  -> cleanup assessment (cleanup-codebase), if ON
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

A fix stays within the plan's goal. A change that would add behavior or scope beyond it is not inserted into the plan: `temper` lists it under `Operator options` in its response, an option the user takes is stated as `Widening: <change>`, and an option the user declines (or any option under "don't ask") is recorded under `## Accepted Risks`.

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
