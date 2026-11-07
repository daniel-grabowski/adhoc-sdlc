#!/usr/bin/env python3
"""Testy przyrostowego dziennika wykonania w JSON (execute-*.json) + dotknięte pliki.

Uruchom: python3 /home/dgrabowski/.claude/skills/adhoc-sdlc/scripts/test_execute_json.py
Stdlib-only (unittest, subprocess). Pokrywa: lifecycle CLI, agregację touched_files w packu,
walidację kontraktu nowych flag, mieszany korpus md+json oraz backward compat starych dzienników md.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

import adhoc_sdlc
import sdlc_doc

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ADHOC = os.path.join(SCRIPTS_DIR, "adhoc_sdlc.py")
TODAY_ISO = "2026-06-12T12:00:00+02:00"


def run(*args):
    return subprocess.run([sys.executable, ADHOC, *args], capture_output=True, text=True)


def adhoc_dir(tmp):
    return os.path.join(tmp, "adhoc-sdlc")


def the_execute_json(tmp):
    d = adhoc_dir(tmp)
    js = [f for f in os.listdir(d) if f.startswith("execute-") and f.endswith(".json")]
    assert len(js) == 1, js
    with open(os.path.join(d, js[0]), encoding="utf-8") as fh:
        return json.load(fh)


def seed_plan(tmp, name, kw="modal", tasks=None):
    """Plan przez CLI; `tasks` (lista linii) zastępuje placeholder sekcji ## Tasks."""
    r = run("plan", "--root", tmp, "--name", name, "--title", "T", "--keywords", kw)
    assert r.returncode == 0, r.stderr
    if tasks is not None:
        plan_path = next(line.split("=", 1)[1] for line in r.stdout.splitlines() if line.startswith("plan="))
        with open(plan_path, encoding="utf-8") as fh:
            text = fh.read()
        assert "## Tasks\n\nTODO\n" in text
        text = text.replace("## Tasks\n\nTODO\n", "## Tasks\n\n" + "\n".join(tasks) + "\n", 1)
        with open(plan_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return r


ONE_TASK = ["- [T1] Krok"]


def write_legacy_json_execute(tmp, name):
    """Dawny dziennik JSON sprzed listy zadań: bez pól schema i tasks, status in-progress."""
    d = adhoc_dir(tmp)
    os.makedirs(d, exist_ok=True)
    obj = {
        "type": "execute", "name": name, "title": "T", "project": "", "keywords": ["modal"],
        "original_prompt": "", "created": "2026-06-01T10:00:00+02:00", "updated": "2026-06-01T10:00:00+02:00",
        "status": "in-progress", "plan": f"adhoc-sdlc/plan-2026-06-01-{name}.md",
        "entries": [{"ts": "2026-06-01T10:00:00+02:00", "note": "start"}],
        "decisions": [], "verification": [], "final_result": None,
    }
    path = os.path.join(d, f"execute-2026-06-01-{name}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    return path


def write_legacy_md_execute(tmp, name, body_steps="- 2026-06-01: stary krok"):
    """Stary dziennik wykonania w markdown (sprzed JSON) - do testów backward compat / mixed corpus."""
    d = adhoc_dir(tmp)
    os.makedirs(d, exist_ok=True)
    fm = "\n".join([
        "---", "type: execute", f"name: {name}", f'title: "{name} md"', 'project: ""',
        "keywords: [modal]", "created: 2026-06-01T10:00:00+02:00",
        "updated: 2026-06-01T10:00:00+02:00", "status: done", "---", "",
    ])
    text = fm + "\n" + (
        f"Plan: `adhoc-sdlc/plan-2026-06-01-{name}.md`\n\n"
        f"## Steps\n\n{body_steps}\n\n## Decisions And Deviations\n\nNone.\n\n"
        "## Verification\n\nDone.\n\n## Final Result\n\nGotowe.\n"
    )
    path = os.path.join(d, f"execute-2026-06-01-{name}.md")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


class LifecycleTests(unittest.TestCase):
    def test_create_and_incremental_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "modal fix", tasks=ONE_TASK)
            r = run("execute", "--root", tmp, "--name", "modal fix", "--title", "T",
                    "--keywords", "modal", "--append", "Start", "--files", "A.pas,b.css", "--phase", "setup")
            self.assertEqual(r.returncode, 0, r.stderr)
            obj = the_execute_json(tmp)
            self.assertEqual(obj["type"], "execute")
            self.assertEqual(obj["plan"].endswith(".md"), True)
            self.assertEqual(len(obj["entries"]), 1)
            self.assertEqual(obj["entries"][0]["phase"], "setup")
            self.assertEqual([f["path"] for f in obj["entries"][0]["files"]], ["A.pas", "b.css"])

            r = run("execute", "--root", tmp, "--name", "modal fix", "--title", "T",
                    "--append", "krok 2", "--files", "b.css", "--change", "edit")
            self.assertEqual(r.returncode, 0, r.stderr)
            obj = the_execute_json(tmp)
            self.assertEqual(len(obj["entries"]), 2)
            self.assertGreaterEqual(obj["updated"], obj["created"])

    def test_decision_verification_final_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--keywords", "modal", "--append", "a")
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--decision", "bez globalu")
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--verification", "zielone", "--command", "npm test")
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--final", "gotowe ok", "--status", "done")
            obj = the_execute_json(tmp)
            self.assertEqual(obj["decisions"][0]["text"], "bez globalu")
            self.assertEqual(obj["verification"][0]["outcome"], "zielone")
            self.assertEqual(obj["verification"][0]["command"], "npm test")
            self.assertEqual(obj["final_result"], "gotowe ok")
            self.assertEqual(obj["status"], "done")

    def test_execute_requires_existing_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run("execute", "--root", tmp, "--name", "no plan", "--title", "T", "--append", "a")
            self.assertEqual(r.returncode, 2)
            self.assertIn("ERROR", r.stderr)


class TouchedFilesPackTests(unittest.TestCase):
    def test_touched_files_deduped_in_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x", tasks=ONE_TASK)
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--keywords", "modal",
                "--append", "a", "--files", "f1.pas,f2.pas")
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--append", "b", "--files", "f2.pas,f3.pas")
            pack = sdlc_doc.build_context_pack("history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO)
            item = next(it for it in pack["items"] if it["type"] == "execute")
            self.assertEqual([f["path"] for f in item["touched_files"]], ["f1.pas", "f2.pas", "f3.pas"])

    def test_execute_extracts_from_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x", tasks=ONE_TASK)
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--keywords", "modal", "--append", "a", "--files", "f1.pas",
                "--task", "T1", "--task-status", "done")
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--decision", "decyzja D")
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--final", "wynik W", "--status", "done")
            pack = sdlc_doc.build_context_pack("history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO)
            item = next(it for it in pack["items"] if it["type"] == "execute")
            headings = [e["heading"] for e in item["extracts"]]
            self.assertEqual(headings, ["Final Result", "Decisions And Deviations"])
            self.assertTrue(any("wynik W" in e["text"] for e in item["extracts"]))


class ContractTests(unittest.TestCase):
    def test_files_without_note_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            r = run("execute", "--root", tmp, "--name", "x", "--title", "T", "--files", "a.pas")
            self.assertEqual(r.returncode, 2)
            self.assertIn("ERROR", r.stderr)

    def test_bad_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            r = run("execute", "--root", tmp, "--name", "x", "--title", "T", "--append", "a", "--files", "a.pas", "--change", "frobnicate")
            self.assertEqual(r.returncode, 2)
            self.assertIn("ERROR", r.stderr)

    def test_phase_without_note_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            r = run("execute", "--root", tmp, "--name", "x", "--title", "T", "--phase", "setup")
            self.assertEqual(r.returncode, 2)
            self.assertIn("ERROR", r.stderr)

    def test_command_without_verification_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            r = run("execute", "--root", tmp, "--name", "x", "--title", "T", "--command", "npm test")
            self.assertEqual(r.returncode, 2)
            self.assertIn("ERROR", r.stderr)


class MixedCorpusTests(unittest.TestCase):
    def test_md_and_json_execute_coexist_in_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            # stary dziennik markdown (inna nazwa) + nowy json
            write_legacy_md_execute(tmp, "old-task")
            plan_path = seed_plan(tmp, "new task", tasks=ONE_TASK).stdout.split("plan=", 1)[1].splitlines()[0]
            # Plan i dziennik new-task to dwa rekordy o tej samej nazwie; ich kolejność w packu zależy od
            # tego, czy updated obu plików wypadł w tej samej sekundzie. Cofnięte updated planu ustala
            # kolejność (dziennik przed planem), w której wybór rekordu po samej nazwie dawał plan.
            with open(plan_path, encoding="utf-8") as fh:
                text = fh.read()
            text = re.sub(r"^updated: .*$", "updated: 2026-06-01T09:00:00+02:00", text, count=1, flags=re.M)
            with open(plan_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            r = run("execute", "--root", tmp, "--name", "new task", "--title", "T", "--keywords", "modal",
                    "--append", "nowy", "--files", "n.pas")
            self.assertEqual(r.returncode, 0, r.stderr)
            pack = sdlc_doc.build_context_pack("history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO)
            names = {it["name"] for it in pack["items"]}
            self.assertIn("old-task", names)
            self.assertIn("new-task", names)
            # touched_files tylko dla json; stary md ma pustą listę. Rekord wybierany po typie i nazwie,
            # bo plan o tej samej nazwie też jest w packu (bez touched_files).
            executes = [it for it in pack["items"] if it["type"] == "execute"]
            self.assertEqual(sorted(it["name"] for it in executes), ["new-task", "old-task"])
            by_name = {it["name"]: it for it in executes}
            self.assertEqual([f["path"] for f in by_name["new-task"]["touched_files"]], ["n.pas"])
            self.assertEqual(by_name["old-task"]["touched_files"], [])


class BackwardCompatMdTests(unittest.TestCase):
    def test_old_md_execute_append_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            # plan o tej samej nazwie + stary md execute -> kontynuacja samym --append
            seed_plan(tmp, "legacy")
            write_legacy_md_execute(tmp, "legacy")
            r = run("execute", "--root", tmp, "--name", "legacy", "--title", "T", "--append", "kolejny krok md")
            self.assertEqual(r.returncode, 0, r.stderr)
            md = os.path.join(adhoc_dir(tmp), "execute-2026-06-01-legacy.md")
            with open(md, encoding="utf-8") as fh:
                self.assertIn("kolejny krok md", fh.read())

    def test_old_md_execute_rejects_new_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "legacy")
            write_legacy_md_execute(tmp, "legacy")
            r = run("execute", "--root", tmp, "--name", "legacy", "--title", "T", "--append", "krok", "--files", "a.pas")
            self.assertEqual(r.returncode, 2)
            self.assertIn("markdown", r.stderr.lower())


def execute(tmp, name, *extra):
    return run("execute", "--root", tmp, "--name", name, "--title", "T", *extra)


class TaskSchemaTests(unittest.TestCase):
    """AC-001: dziennik schema 2 z zadaniami z ## Tasks planu."""

    def test_new_journal_has_schema_and_plan_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x", tasks=["- [T1] Dodać pole", "  - szczegół (podpunkt, nie zadanie)",
                                       "Proza sekcji nie jest zadaniem.", "* [T2] Weryfikacja: pytest"])
            r = execute(tmp, "x")
            self.assertEqual(r.returncode, 0, r.stderr)
            obj = the_execute_json(tmp)
            self.assertEqual(obj["schema"], 2)
            self.assertEqual([(t["id"], t["title"], t["status"], t["source"]) for t in obj["tasks"]],
                             [("T1", "Dodać pole", "pending", "plan"), ("T2", "Weryfikacja: pytest", "pending", "plan")])

    def test_plan_template_has_tasks_placeholder_and_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            r = execute(tmp, "x")
            self.assertEqual(r.returncode, 0, r.stderr)
            obj = the_execute_json(tmp)
            self.assertEqual(obj["schema"], 2)
            self.assertEqual(obj["tasks"], [])

    def test_plan_without_tasks_section_gives_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            d = adhoc_dir(tmp)
            plan = os.path.join(d, next(f for f in os.listdir(d) if f.startswith("plan-")))
            with open(plan, encoding="utf-8") as fh:
                text = fh.read().replace("## Tasks\n\nTODO\n\n", "")
            with open(plan, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            self.assertNotIn("## Tasks", text)
            self.assertEqual(execute(tmp, "x").returncode, 0)
            self.assertEqual(the_execute_json(tmp)["tasks"], [])

    def test_append_without_tasks_rejected_on_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            r = execute(tmp, "x", "--append", "start")
            self.assertEqual(r.returncode, 2)
            self.assertIn("ERROR", r.stderr)
            self.assertIn("--task-add", r.stderr)
            # odmowa bez efektów ubocznych: dziennik nie powstał
            self.assertFalse(any(f.startswith("execute-") for f in os.listdir(adhoc_dir(tmp))))

    def test_append_without_tasks_rejected_on_existing_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            self.assertEqual(execute(tmp, "x").returncode, 0)
            r = execute(tmp, "x", "--append", "krok")
            self.assertEqual(r.returncode, 2)
            self.assertEqual(the_execute_json(tmp)["entries"], [])

    def test_task_add_unlocks_append_and_records_deviation(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            execute(tmp, "x")
            r = execute(tmp, "x", "--task-add", "Krok spoza planu", "--task", "T1", "--append", "start")
            self.assertEqual(r.returncode, 0, r.stderr)
            obj = the_execute_json(tmp)
            self.assertEqual([(t["id"], t["source"]) for t in obj["tasks"]], [("T1", "added")])
            self.assertEqual(obj["entries"][0]["task"], "T1")
            self.assertEqual(obj["decisions"][0]["task"], "T1")
            self.assertIn("Odstępstwo od planu", obj["decisions"][0]["text"])

    def test_task_add_numbers_after_plan_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x", tasks=["- [T1] A", "- [T3] C"])
            execute(tmp, "x", "--task-add", "D")
            self.assertEqual([t["id"] for t in the_execute_json(tmp)["tasks"]], ["T1", "T3", "T4"])

    def test_bad_task_line_in_plan_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x", tasks=["- [T1] A", "- B bez identyfikatora"])
            r = execute(tmp, "x")
            self.assertEqual(r.returncode, 2)
            self.assertIn("## Tasks", r.stderr)

    def test_duplicate_task_id_in_plan_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x", tasks=["- [T1] A", "- [T1] B"])
            r = execute(tmp, "x")
            self.assertEqual(r.returncode, 2)
            self.assertIn("powtórzony", r.stderr)

    def test_empty_task_add_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            execute(tmp, "x")
            r = execute(tmp, "x", "--task-add", "  ")
            self.assertEqual(r.returncode, 2)
            self.assertEqual(the_execute_json(tmp)["tasks"], [])

    def test_unknown_schema_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x", tasks=ONE_TASK)
            execute(tmp, "x")
            d = adhoc_dir(tmp)
            path = os.path.join(d, next(f for f in os.listdir(d) if f.startswith("execute-")))
            obj = the_execute_json(tmp)
            obj["schema"] = 3
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(obj, fh)
            r = execute(tmp, "x", "--append", "krok")
            self.assertEqual(r.returncode, 2)
            self.assertIn("schematu", r.stderr)


class TaskValidationTests(unittest.TestCase):
    """AC-002: odmowy helpera (kod 2) przy wykonaniu zadań."""

    def _journal(self, tmp, tasks=("- [T1] A", "- [T2] B")):
        seed_plan(tmp, "x", tasks=list(tasks))
        r = execute(tmp, "x")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_happy_path_in_progress_done_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            self.assertEqual(execute(tmp, "x", "--task", "T1", "--task-status", "in_progress").returncode, 0)
            self.assertEqual(execute(tmp, "x", "--task", "T1", "--append", "zrobione A", "--task-status", "done").returncode, 0)
            self.assertEqual(execute(tmp, "x", "--task", "T2", "--verification", "zielone", "--command", "pytest",
                                     "--task-status", "done").returncode, 0)
            r = execute(tmp, "x", "--final", "gotowe", "--status", "done")
            self.assertEqual(r.returncode, 0, r.stderr)
            obj = the_execute_json(tmp)
            self.assertEqual([t["status"] for t in obj["tasks"]], ["done", "done"])
            self.assertEqual(obj["verification"][0]["task"], "T2")
            self.assertEqual(obj["status"], "done")

    def test_second_in_progress_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            execute(tmp, "x", "--task", "T1", "--task-status", "in_progress")
            r = execute(tmp, "x", "--task", "T2", "--task-status", "in_progress")
            self.assertEqual(r.returncode, 2)
            self.assertIn("in_progress", r.stderr)
            self.assertEqual([t["status"] for t in the_execute_json(tmp)["tasks"]], ["in_progress", "pending"])

    def test_same_task_in_progress_again_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            execute(tmp, "x", "--task", "T1", "--task-status", "in_progress")
            self.assertEqual(execute(tmp, "x", "--task", "T1", "--task-status", "in_progress").returncode, 0)

    def test_done_without_entry_or_verification_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            execute(tmp, "x", "--task", "T2", "--append", "praca nad B")
            r = execute(tmp, "x", "--task", "T1", "--task-status", "done")
            self.assertEqual(r.returncode, 2)
            self.assertIn("T1", r.stderr)
            self.assertEqual(the_execute_json(tmp)["tasks"][0]["status"], "pending")

    def test_untagged_entry_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            execute(tmp, "x", "--append", "wpis bez zadania")
            self.assertEqual(execute(tmp, "x", "--task", "T1", "--task-status", "done").returncode, 2)

    def test_final_with_open_tasks_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            execute(tmp, "x", "--task", "T1", "--append", "A", "--task-status", "done")
            r = execute(tmp, "x", "--final", "gotowe")
            self.assertEqual(r.returncode, 2)
            self.assertIn("T2", r.stderr)
            self.assertIsNone(the_execute_json(tmp)["final_result"])

    def test_status_done_with_open_tasks_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            r = execute(tmp, "x", "--status", "done")
            self.assertEqual(r.returncode, 2)
            self.assertIn("--status done", r.stderr)
            self.assertEqual(the_execute_json(tmp)["status"], "in-progress")

    def test_status_done_rejected_on_create_with_open_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x", tasks=ONE_TASK)
            self.assertEqual(execute(tmp, "x", "--status", "done").returncode, 2)
            self.assertFalse(any(f.startswith("execute-") for f in os.listdir(adhoc_dir(tmp))))

    def test_abandoned_with_open_tasks_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            self.assertEqual(execute(tmp, "x", "--status", "abandoned").returncode, 0)
            self.assertEqual(the_execute_json(tmp)["status"], "abandoned")

    def test_unknown_task_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            r = execute(tmp, "x", "--task", "T9", "--append", "krok")
            self.assertEqual(r.returncode, 2)
            self.assertIn("T9", r.stderr)
            self.assertEqual(the_execute_json(tmp)["entries"], [])

    def test_bad_task_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            self.assertEqual(execute(tmp, "x", "--task", "abc", "--append", "krok").returncode, 2)

    def test_bad_task_status_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            self.assertEqual(execute(tmp, "x", "--task", "T1", "--task-status", "completed").returncode, 2)

    def test_task_status_without_task_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            self.assertEqual(execute(tmp, "x", "--task-status", "done").returncode, 2)

    def test_task_alone_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._journal(tmp)
            self.assertEqual(execute(tmp, "x", "--task", "T1").returncode, 2)


class LegacyJournalTests(unittest.TestCase):
    """AC-003: dawny dziennik (bez pola schema) działa jak przed zmianą."""

    def test_legacy_append_final_status_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "legacy", tasks=ONE_TASK)  # zadania planu nie dotyczą dawnego dziennika
            write_legacy_json_execute(tmp, "legacy")
            self.assertEqual(execute(tmp, "legacy", "--append", "kolejny krok").returncode, 0)
            self.assertEqual(execute(tmp, "legacy", "--verification", "zielone").returncode, 0)
            r = execute(tmp, "legacy", "--final", "gotowe", "--status", "done")
            self.assertEqual(r.returncode, 0, r.stderr)
            obj = the_execute_json(tmp)
            self.assertNotIn("schema", obj)
            self.assertNotIn("tasks", obj)
            self.assertEqual([e["note"] for e in obj["entries"]], ["start", "kolejny krok"])
            self.assertEqual(obj["final_result"], "gotowe")
            self.assertEqual(obj["status"], "done")

    def test_legacy_rejects_task_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "legacy")
            write_legacy_json_execute(tmp, "legacy")
            for extra in (("--task", "T1", "--append", "k"), ("--task-add", "X"),
                          ("--task", "T1", "--task-status", "done")):
                r = execute(tmp, "legacy", *extra)
                self.assertEqual(r.returncode, 2, extra)
                self.assertIn("dawny dziennik", r.stderr)
            self.assertNotIn("tasks", the_execute_json(tmp))

    def test_old_md_journal_rejects_task_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "legacy")
            write_legacy_md_execute(tmp, "legacy")
            r = execute(tmp, "legacy", "--task-add", "X")
            self.assertEqual(r.returncode, 2)
            self.assertIn("markdown", r.stderr.lower())


class ParseKeywordsTests(unittest.TestCase):
    """parse_keywords deduplikuje tokeny zachowując kolejność pierwszego wystąpienia."""

    def test_dedup_preserves_first_order(self):
        self.assertEqual(
            adhoc_sdlc.parse_keywords("modal,ui,modal,build,ui", "plan"),
            ["modal", "ui", "build"],
        )

    def test_none_is_empty(self):
        self.assertEqual(adhoc_sdlc.parse_keywords(None, "plan"), [])

    def test_dedup_after_normalization(self):
        # "Modal" i "modal" normalizują się do tego samego tokenu -> jeden wpis.
        self.assertEqual(adhoc_sdlc.parse_keywords("Modal,modal", "plan"), ["modal"])


if __name__ == "__main__":
    unittest.main()
