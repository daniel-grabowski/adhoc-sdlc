#!/usr/bin/env python3
"""Testy przyrostowego dziennika wykonania w JSON (execute-*.json) + dotknięte pliki.

Uruchom: python3 /home/dgrabowski/.claude/skills/adhoc-sdlc/scripts/test_execute_json.py
Stdlib-only (unittest, subprocess). Pokrywa: lifecycle CLI, agregację touched_files w packu,
walidację kontraktu nowych flag, mieszany korpus md+json oraz backward compat starych dzienników md.
"""

import json
import os
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


def seed_plan(tmp, name, kw="modal"):
    r = run("plan", "--root", tmp, "--name", name, "--title", "T", "--keywords", kw)
    assert r.returncode == 0, r.stderr
    return r


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
            seed_plan(tmp, "modal fix")
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
            seed_plan(tmp, "x")
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--keywords", "modal",
                "--append", "a", "--files", "f1.pas,f2.pas")
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--append", "b", "--files", "f2.pas,f3.pas")
            pack = sdlc_doc.build_context_pack("history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO)
            item = next(it for it in pack["items"] if it["type"] == "execute")
            self.assertEqual([f["path"] for f in item["touched_files"]], ["f1.pas", "f2.pas", "f3.pas"])

    def test_execute_extracts_from_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_plan(tmp, "x")
            run("execute", "--root", tmp, "--name", "x", "--title", "T", "--keywords", "modal", "--append", "a", "--files", "f1.pas")
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
            seed_plan(tmp, "new task")
            run("execute", "--root", tmp, "--name", "new task", "--title", "T", "--keywords", "modal",
                "--append", "nowy", "--files", "n.pas")
            pack = sdlc_doc.build_context_pack("history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO)
            names = {it["name"] for it in pack["items"]}
            self.assertIn("old-task", names)
            self.assertIn("new-task", names)
            # touched_files tylko dla json; stary md ma pustą listę
            by_name = {it["name"]: it for it in pack["items"]}
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
