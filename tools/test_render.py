#!/usr/bin/env python3
"""Testy renderera tools/render.py (warstwa A: deterministyczne wiązanie narzędzi).

Sprawdza: render podstawia placeholdery na jawne nazwy narzędzi, nie zostawia żadnego
{{...}}, jest idempotentny, brak mapowania to fail loud, oraz - jako regresja na bug
commita 70d56b1 - wyrenderowany plan zawiera jawne `AskUserQuestion` w mode gate i
close-the-loop. test_disk_matches_render to odpowiednik `render.py --check`: pliki na
dysku muszą zgadzać się z renderem (bramka przeciw ręcznej edycji wyniku / pominięciu renderu).
"""

import json
import unittest

import render


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = json.loads((render.RUNTIMES_DIR / "claude.json").read_text(encoding="utf-8"))
        cls.placeholders = spec["placeholders"]
        cls.files = spec["files"]

    def _render_plan(self) -> str:
        return render.render_one("commands/plan.md", self.placeholders, "claude")

    def test_no_leftover_placeholders(self):
        for template_rel, _ in self.files:
            out = render.render_one(template_rel, self.placeholders, "claude")
            self.assertNotIn("{{", out, f"niepodstawiony placeholder w {template_rel}")

    def test_substitutes_explicit_tool_names(self):
        out = self._render_plan()
        self.assertIn("`AskUserQuestion`", out)
        self.assertIn("`Agent` tool", out)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", out)

    def test_task_list_through_helper_not_native_tool(self):
        # AC-005/AC-006 (#7935, DEC-001, DEC-004): lista zadań w planie (## Tasks) i w helperze, bez natywnego narzędzia.
        codex_spec = json.loads((render.RUNTIMES_DIR / "codex.json").read_text(encoding="utf-8"))
        for runtime, placeholders in (("claude", self.placeholders), ("codex", codex_spec["placeholders"])):
            self.assertNotIn("TODO", placeholders, f"{runtime}: klucz TODO w runtimes")
            plan = render.render_one("commands/plan.md", placeholders, runtime)
            exec_ = render.render_one("commands/exec.md", placeholders, runtime)
            skill = render.render_one("skills/adhoc-sdlc/SKILL.md", placeholders, runtime)
            reference = render.render_one("skills/adhoc-sdlc/reference.md", placeholders, runtime)
            phase2 = plan.split("## Phase 2")[1].split("## Phase 3")[0]
            close_loop = plan.split("## Phase 3")[1]
            for phrase in ("Write `## Tasks` as the execution task list", "- [T1] <first key change as an action>", "A numbered list (`1. ...`) is not read as tasks"):
                self.assertIn(phrase, phase2, f"{runtime}: plan.md Phase 2: {phrase}")
            for phrase in ("adhoc_sdlc.py tasks --name", "--task-add", "--task T1 --task-status in_progress", "--task-status done", "Close the journal only after every task is `done`"):
                self.assertIn(phrase, close_loop, f"{runtime}: plan.md Phase 3: {phrase}")
            for phrase in (
                "adhoc_sdlc.py tasks --name",
                "--task-add \"<task title>\"",
                "--task T1 --task-status in_progress",
                "Exactly one task is `in_progress` at a time",
                "--task <Tn> --append",
                "Reopening a `done` task",
                "the journal status is `in-progress|done|abandoned`",
                "the task status is `in_progress|done`",
                "Close the journal only after every task is `done`",
            ):
                self.assertIn(phrase, exec_, f"{runtime}: exec.md: {phrase}")
            self.assertIn("## Execution tasks", skill)
            self.assertNotIn("## Native todo list", skill)
            self.assertIn("## Execution tasks", reference)
            self.assertIn("`tasks --name <name> [--format json|tsv]`", reference)
            for name, text in (("plan.md", plan), ("exec.md", exec_), ("SKILL.md", skill), ("reference.md", reference)):
                for banned in ("TaskCreate", "TaskUpdate", "native todo", "native task list"):
                    self.assertNotIn(banned, text, f"{runtime}: {name}: {banned}")
        # Źródła: placeholder listy zadań nie wraca w żadnym szablonie.
        for path in render.TEMPLATES_DIR.rglob("*"):
            if path.is_file():
                self.assertNotIn("{{TODO}}", path.read_text(encoding="utf-8"), str(path))

    def test_regression_mode_gate_and_close_loop_explicit(self):
        # Bug 70d56b1: mode gate i close-the-loop straciły jawne AskUserQuestion.
        out = self._render_plan()
        self.assertNotIn("structured-question prompt", out)
        self.assertNotIn("structured question prompt", out)
        # Phase 0 (mode gate) i Phase 3 (close the loop) muszą jawnie wołać narzędzie.
        mode_gate = out.split("## Phase 1")[0]
        close_loop = out.split("## Phase 3")[1]
        self.assertIn("`AskUserQuestion`", mode_gate)
        self.assertIn("`AskUserQuestion`", close_loop)

    def test_generated_header_present(self):
        out = self._render_plan()
        self.assertIn("GENERATED by tools/render.py", out)

    def test_md_output_uses_html_header(self):
        # .md: nagłówek HTML '<!-- -->', nie komentarz YAML '#'.
        out = self._render_plan()
        self.assertIn("<!-- GENERATED by tools/render.py", out)
        self.assertNotIn("\n# GENERATED by tools/render.py", out)

    def test_yaml_output_uses_hash_header(self):
        # .yaml: nagłówek to komentarz YAML '#'; '<!-- -->' zepsułby plik.
        out = render.render_one("skills/cove/agents/openai.yaml", self.placeholders, "codex")
        self.assertTrue(out.startswith("# GENERATED by tools/render.py"))
        self.assertNotIn("<!--", out)

    def test_idempotent(self):
        first = self._render_plan()
        second = render.render_one("commands/plan.md", self.placeholders, "claude")
        self.assertEqual(first, second)

    def test_unmapped_placeholder_raises(self):
        incomplete = {k: v for k, v in self.placeholders.items() if k != "ASK"}
        with self.assertRaises(SystemExit):
            render.render_one("commands/plan.md", incomplete, "claude")

    def test_intention_hardening_contract_phrases(self):
        # AC-001 (#7557): kontrakt bramki zamiaru w szablonie skilla.
        out = render.render_one("skills/intention-hardening/SKILL.md", self.placeholders, "claude")
        for phrase in (
            "name: intention-hardening",
            "Goal in one sentence, plus the success criterion",
            "Load-bearing terms: for each, its meaning in this project and the source",
            "ask one question that shows the concrete difference",
            "assumption labelled `interpretacja`",
            "Name every narrowing or widening",
            "Deepen when any of these holds",
            "Skip deepening for a small unambiguous change",
            "A memory hit is background to confirm, not evidence",
            "Memory never replaces the user's current intent",
            "One bounded memory read following the `memory` skill",
            "`sources unavailable` (`źródła niedostępne`)",
            "Once the budget is spent, ask instead of searching further",
            "scope: what is in and what is out",
            "`korekta intencji (plan|kod|odbiór)`",
            "P0 block `Kandydaci do pamięci` as `[hipoteza]`",
            "The skill never writes to memory itself",
            "Under \"don't ask\"",
            "Return to the caller, without writing anything",
            "IPR Assumptions with owner `interpretacja` or `operator`",
            "the Mode key `intent`",
            "Summary, Assumptions, and Original Prompt",
            "It is not `/forge:harden`",
            "intention-hardening -> cove -> temper",
        ):
            self.assertIn(phrase, out, f"brak frazy kontraktu: {phrase}")

    def test_skill_via_binds_per_runtime(self):
        # AC-002 (#7557): SKILL_VIA jawnie wiąże wywołanie skilla per runtime (DEC-002).
        claude = render.render_one("skills/intention-hardening/SKILL.md", self.placeholders, "claude")
        self.assertIn("the `cove` skill (via the `Skill` tool; skills shipped in this plugin are named `adhoc-sdlc:<name>`)", claude)
        # Skill memory jest skillem użytkownika spoza pluginu: bez sugestii nazwy adhoc-sdlc:memory (#7559).
        self.assertIn("the `memory` skill (a user skill outside this plugin, invoked by its own name `memory`)", claude)
        self.assertNotIn("the `memory` skill (via the `Skill` tool;", claude)
        codex_spec = json.loads((render.RUNTIMES_DIR / "codex.json").read_text(encoding="utf-8"))
        codex = render.render_one("skills/intention-hardening/SKILL.md", codex_spec["placeholders"], "codex")
        self.assertIn("the `temper` skill (invoke it as `$<name>`)", codex)
        self.assertNotIn("`Skill` tool", codex)
        for files, prefix in ((self.files, "claude/"), (codex_spec["files"], "plugins/adhoc-sdlc/")):
            outputs = [o for t, o in files if t.startswith("skills/intention-hardening/")]
            self.assertEqual(
                sorted(outputs),
                sorted(prefix + "skills/intention-hardening/" + n for n in ("SKILL.md", "README.md", "README.pl.md")),
            )

    def test_temper_fix_stays_within_goal(self):
        # AC-003 (#7558, DEC-005): fix tylko w granicach celu, zmiana spoza celu do Operator options albo Accepted Risks.
        codex_spec = json.loads((render.RUNTIMES_DIR / "codex.json").read_text(encoding="utf-8"))
        for runtime, placeholders in (("claude", self.placeholders), ("codex", codex_spec["placeholders"])):
            out = render.render_one("skills/temper/SKILL.md", placeholders, runtime)
            for phrase in (
                "resolution: fix | accept | reject | verify-with-cove",
                "a specific change within the plan's goal",
                "Goal boundary: a `fix` changes only how the plan reaches its goal",
                "it is not a `fix` and does not enter the plan automatically",
                "error handling for a step the plan already has, a retry guard on a planned call) is within the goal and resolves as `fix`",
                "\"Would add behavior\" means behavior the goal does not cover",
                "list the change only under `Operator options` for the operator to decide, with a short reason and its cost",
                "state it explicitly as `Widening: <change>`",
                "when the operator declines it, or under \"don't ask\", resolve it as `accept` and record it under Accepted Risks",
                "The plan grows only when the operator takes an option",
                "## Operator options\n- <change beyond the goal> -> <why it would help>; cost: <cost>",
                "Operator options are not a plan section",
                "instead of offering it under `Operator options` for the operator's decision",
                "An item in `Operator options` gets its resolution only after the operator decides",
                "resolution: pending operator decision; Operator options: add an atomic write",
                "declined or \"don't ask\" -> accept:",
                "taken -> Widening: atomic write with recovery; resolution: fix",
            ):
                self.assertIn(phrase, out, f"{runtime}: brak frazy kontraktu: {phrase}")
            self.assertNotIn("expand the feature by default", out)
            self.assertNotIn("resolution: accept, the goal is the handoff format", out)
            self.assertNotIn("or recording it under Accepted Risks", out)
            for readme, old in (("README.md", "grow the feature by\ndefault"), ("README.pl.md", "domyślnie\nnie rozszerza funkcji")):
                text = render.render_one("skills/temper/" + readme, placeholders, runtime)
                self.assertNotIn(old, text, f"{runtime}: stary opis w {readme}")
                self.assertIn("`Operator options`", text, f"{runtime}: brak Operator options w {readme}")

    def test_plan_calls_intention_hardening_and_dont_ask_keeps_gates(self):
        # AC-004 (#7559, DEC-006, DEC-008, DEC-005): Phase 1 woła bramkę zamiaru, "nie pytaj" zostawia CoVe i Temper.
        codex_spec = json.loads((render.RUNTIMES_DIR / "codex.json").read_text(encoding="utf-8"))
        for runtime, placeholders in (("claude", self.placeholders), ("codex", codex_spec["placeholders"])):
            via = placeholders["SKILL_VIA"]
            plan = render.render_one("commands/plan.md", placeholders, runtime)
            skill = render.render_one("skills/adhoc-sdlc/SKILL.md", placeholders, runtime)
            phase1 = plan.split("## Phase 1")[1].split("## Phase 2")[0]
            design = skill.split("### Design decisions")[1].split("## Read-side authority")[0]
            for name, text in (("plan.md Phase 1", phase1), ("SKILL.md Design decisions", design)):
                self.assertIn("run the `intention-hardening` skill" + via + " on the request", text, f"{runtime}: {name}")
            self.assertIn("the goal and success criterion in `## Summary`", phase1)
            self.assertIn("the interpretations and assumptions in `## Assumptions`", phase1)
            self.assertIn("`## Original Prompt` through the helper's `--prompt` flag", phase1)
            self.assertIn("[--prompt \"<verbatim request>\"]", plan)
            self.assertIn("run the `cove` skill" + via + " on the draft plan", phase1)
            self.assertIn("run the `temper` skill" + via + " on the draft plan", phase1)
            self.assertIn("follows the skill's Goal boundary rule", phase1)
            self.assertIn("`<condition> -> operator option not taken: <change>`", phase1)
            self.assertIn("Operator options belong in the temper response, outside the plan file", phase1)
            mode_gate = plan.split("## Phase 1")[0]
            for name, text in (("plan.md mode gate", mode_gate), ("SKILL.md", skill)):
                self.assertIn("`plan-cove` and `strategy-temper` are ON, the other four modes take the project defaults", text, f"{runtime}: {name}")
                self.assertIn("request reading still runs", text, f"{runtime}: {name}")
            for name, text in (("plan.md", plan), ("SKILL.md", skill)):
                self.assertNotIn("default every mode to OFF", text, f"{runtime}: {name}")
                self.assertNotIn("proves the original scope is too small", text, f"{runtime}: {name}")
        # Źródła: fraza nie wraca w żadnym szablonie.
        for path in render.TEMPLATES_DIR.rglob("*.md"):
            self.assertNotIn("default every mode to OFF", path.read_text(encoding="utf-8"), str(path))

    def test_disk_matches_render(self):
        # Odpowiednik `render.py --check`: dysk == render dla aktywnego runtime claude.
        for template_rel, output_rel in self.files:
            rendered = render.render_one(template_rel, self.placeholders, "claude")
            disk = (render.REPO_ROOT / output_rel).read_text(encoding="utf-8")
            self.assertEqual(rendered, disk, f"drift w {output_rel} (uruchom tools/render.py)")


if __name__ == "__main__":
    unittest.main()
