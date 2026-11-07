---
name: cleanup-codebase
description: "What: evidence-based cleanup assessment for a given goal and scope: finds dead code, equivalent implementations, unneeded dependencies, and leftovers of changes, checks each candidate against the categories of implicit entry points, and returns a candidate register with the verdicts remove, merge, keep, or unresolved. Why: use it before cleaning up code, so the process that edits files (an adhoc-sdlc exec or a FORGE run) removes only what the evidence supports; the skill itself only assesses. Trigger phrases: cleanup codebase, cleanup assessment, dead code, unused code, duplicates, porządki w kodzie, martwy kod, ocena porządków."
---

# Cleanup Codebase

## What

`cleanup-codebase` assesses what can be cleaned up safely in a given scope and returns a candidate register with a verdict for every candidate. It assesses only: it does not edit files, does not run git, does not build, and does not run tests. The process that leads the work applies the changes under its own verification rules: `exec` in adhoc-sdlc, or the builder in a FORGE run.

The skill is stack-agnostic. Knowledge of a concrete stack (registration mechanisms, resource files, generated code, build configuration) comes from the project's rules and skills, not from this skill.

## Why

Unused implementations, duplicated logic, unneeded dependencies, and leftovers of earlier changes make code harder to understand, raise the cost of the next change, and load the agent's context. Removing them on the strength of an empty search is risky: code can be reached through paths no search shows. The goal is a lower maintenance cost and easier navigation, not the number of deleted lines.

## Input

- Goal: why the cleanup is wanted (for example: leftovers of the current task, a module before a rewrite, dependency diet).
- Scope: files, modules, an area, or the change of a task (the files it touched).

When the scope is not given, or does not name a bounded area, return that as a blocker (`scope undefined`) and stop. Never widen the scope yourself. A finding outside the agreed scope is a proposal for further work, not a candidate.

## What it assesses

- Dead code: symbols, files, unreachable branches, stale blocks of commented-out implementation.
- Equivalent implementations: only when they represent one shared responsibility and merging them adds no unjustified dependency.
- Unneeded project dependencies, taking configuration, build, tests, and tooling into account.
- Leftovers of changes in the given area, including the current task.

Out of scope: wider architecture changes, behavior changes, replacing a library with own code (each needs a separate request), and cleanup of sessions, worktrees, or disk.

## Process

### 1. Scope and entry points

Establish the scope, its contracts, its entry points, and the supported configurations (build variants, platforms, feature flags) before looking for candidates.

### 2. Candidates

Search the scope for candidates in the four groups above. Record each with its location (path and line, symbol, or dependency name).

### 3. Evidence per candidate

For every candidate collect evidence: repository search, reachability, use by tests, and use by configuration. For equivalent implementations also record the differences in behavior.

No search hits and green tests are never on their own evidence that a candidate is unneeded. Check every candidate against each category of implicit entry points:

- dynamic calls and reflection (lookup by name, RTTI, `eval`, dependency injection by type);
- registrations (plugin, factory, route, command, or event registration; module initialization sections);
- references by name in data, resources, and configuration (database rows, form and resource files, JSON and XML, scripts);
- generated code (code generators, templates, build steps that produce or consume the symbol);
- public API (exported symbols, packages, endpoints, or files other repositories or customers may use).

How to check a category in this stack follows from the project's rules and skills. Record for each category what was checked and how, or why it could not be checked.

### 4. Verdict

Give every candidate exactly one verdict. The tokens are canonical in English; describe them in the user's language.

- `remove`: every category is checked and the evidence shows the candidate is not used.
- `merge`: equivalent implementations of one responsibility; the differences in behavior are recorded and merging adds no unjustified dependency.
- `keep`: the evidence shows the candidate is used or required.
- `unresolved`: the evidence is incomplete or contradictory.

A category that cannot be checked gives the verdict `unresolved` with the reason, never `remove`.

The assessment ends when every candidate in the agreed scope has a verdict.

## Register

Return the register to the caller, without writing anything. State the assessment date and the scope at the top, then one row per candidate:

```markdown
Assessment date: YYYY-MM-DD
Goal: <goal>
Scope: <files, modules, area, or the task's change>

| Location | Verdict | Evidence per category | Risk | Reach |
|----------|---------|-----------------------|------|-------|
| path:line or symbol | remove/merge/keep/unresolved | search: ...; reachability: ...; tests: ...; configuration: ...; dynamic calls: ...; registrations: ...; references by name: ...; generated code: ...; public API: ... | low/medium/high: why | files: N; dependencies: ... |

Out of scope (proposals): <finding> -> <why it may matter>
```

- Evidence per category names the source of each check (a file and line, a command and its result, a rule of the project); a category that could not be checked says so with the reason.
- Reach is the estimated extent of the change: files and dependencies it touches.
- Report a smaller install or build size only after measuring it; never estimate it.

## Invocation points

- On demand, with a goal and a scope.
- In adhoc-sdlc, through the optional `cleanup-codebase` mode of `/adhoc-sdlc:plan` (default OFF). Variant A, in planning: the register goes into the plan's `## Cleanup Register` section, and only `remove` and `merge` verdicts become `## Key Changes` that `exec` carries out and journals, after re-checking their key evidence. Variant B, in `exec`: before the final self-check the skill assesses the leftovers of the change in the files the journal records; a candidate is carried out only after the user confirms it.
- In FORGE, the register becomes the scope of a task and its acceptance criterion is "every candidate accounted for"; execution and verification belong to the run.

The `cove` skill{{SKILL_VIA}} can verify the claims a verdict rests on, and the `temper` skill{{SKILL_VIA}} can check the strategy and risks of the cleanup. Neither replaces the analysis of the code.
