#!/usr/bin/env python3
"""Testy pętli raport cleanup-codebase -> plan -> dziennik.

Uruchom: python3 -m pytest -q (w katalogu scripts). Stdlib-only (unittest, subprocess). Pokrywa:
plan --source-report (sekcja ## Source ze skrótem SHA-256), odmowę dla brakującego pliku,
odwołanie `(ref: <raport>#<ID>)` w ## Tasks i w --task-add, przeniesienie source_report do
dziennika, stan zgodności skrótu w `tasks --format json` oraz zgodność wstecz bez Source i ref.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ADHOC = os.path.join(SCRIPTS_DIR, "adhoc_sdlc.py")


def run(*args):
    return subprocess.run([sys.executable, ADHOC, *args], capture_output=True, text=True)


def plan_path_of(result):
    return next(line.split("=", 1)[1] for line in result.stdout.splitlines() if line.startswith("plan="))


def set_tasks(plan_path, lines):
    with open(plan_path, encoding="utf-8") as fh:
        text = fh.read()
    assert "## Tasks\n\nTODO\n" in text
    text = text.replace("## Tasks\n\nTODO\n", "## Tasks\n\n" + "\n".join(lines) + "\n", 1)
    with open(plan_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def tasks_json(tmp, name):
    r = run("tasks", "--root", tmp, "--name", name, "--format", "json")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class SourceReportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        os.makedirs(os.path.join(self.tmp, "research"))
        self.report = os.path.join(self.tmp, "research", "cleanup-api-2026-11-08-1200.md")
        with open(self.report, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# Cleanup\n\n## remove\n\n| ID | Location |\n|---|---|\n| R1 | a.py |\n")
        with open(self.report, "rb") as fh:
            self.sha = hashlib.sha256(fh.read()).hexdigest()

    def tearDown(self):
        self._tmp.cleanup()

    def make_plan(self, name, tasks):
        r = run("plan", "--root", self.tmp, "--name", name, "--title", "T", "--source-report", self.report)
        self.assertEqual(r.returncode, 0, r.stderr)
        path = plan_path_of(r)
        set_tasks(path, tasks)
        return path

    def test_plan_writes_source_section_with_relative_path_and_sha(self):
        path = self.make_plan("cleanup-a", ["- [T1] R1: usunąć a (ref: research/cleanup-api-2026-11-08-1200.md#R1)"])
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("## Source\n\n- report: research/cleanup-api-2026-11-08-1200.md\n- sha256: " + self.sha, text)

    def test_missing_report_is_refused_without_creating_plan(self):
        r = run("plan", "--root", self.tmp, "--name", "cleanup-b", "--title", "T",
                "--source-report", os.path.join(self.tmp, "research", "brak.md"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("--source-report", r.stderr)
        self.assertFalse(any(f.startswith("plan-") for f in os.listdir(os.path.join(self.tmp, "adhoc-sdlc"))))

    def test_journal_carries_ref_and_source_report_with_matching_hash(self):
        self.make_plan("cleanup-c", [
            "- [T1] R1: usunąć a (ref: research/cleanup-api-2026-11-08-1200.md#R1)",
            "- [T2] Weryfikacja: pytest",
        ])
        r = run("execute", "--root", self.tmp, "--name", "cleanup-c", "--title", "T")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = tasks_json(self.tmp, "cleanup-c")
        t1, t2 = out["items"]
        self.assertEqual(t1["title"], "R1: usunąć a")
        self.assertEqual(t1["ref"], "research/cleanup-api-2026-11-08-1200.md#R1")
        self.assertEqual(t1["source"], "plan")
        self.assertNotIn("ref", t2)
        state = out["source_report"]
        self.assertEqual(state["path"], "research/cleanup-api-2026-11-08-1200.md")
        self.assertEqual(state["sha256"], self.sha)
        self.assertTrue(state["match"])

    def test_changed_or_missing_report_gives_match_false(self):
        self.make_plan("cleanup-d", ["- [T1] R1: usunąć a (ref: research/cleanup-api-2026-11-08-1200.md#R1)"])
        self.assertEqual(run("execute", "--root", self.tmp, "--name", "cleanup-d", "--title", "T").returncode, 0)
        with open(self.report, "a", encoding="utf-8") as fh:
            fh.write("| R2 | b.py |\n")
        state = tasks_json(self.tmp, "cleanup-d")["source_report"]
        self.assertFalse(state["match"])
        self.assertNotEqual(state["sha256_now"], self.sha)
        os.remove(self.report)
        state = tasks_json(self.tmp, "cleanup-d")["source_report"]
        self.assertFalse(state["match"])
        self.assertIsNone(state["sha256_now"])

    def test_task_add_accepts_ref_for_variant_b(self):
        self.make_plan("cleanup-e", ["- [T1] Krok"])
        r = run("execute", "--root", self.tmp, "--name", "cleanup-e", "--title", "T",
                "--task-add", "R1: usunąć pozostałość (ref: adhoc-sdlc/execute-2026-11-08-cleanup-e.json#R1)")
        self.assertEqual(r.returncode, 0, r.stderr)
        t2 = tasks_json(self.tmp, "cleanup-e")["items"][1]
        self.assertEqual(t2["source"], "added")
        self.assertEqual(t2["ref"], "adhoc-sdlc/execute-2026-11-08-cleanup-e.json#R1")
        self.assertEqual(t2["title"], "R1: usunąć pozostałość")

    def test_plan_without_source_and_ref_keeps_previous_behaviour(self):
        r = run("plan", "--root", self.tmp, "--name", "plain", "--title", "T")
        self.assertEqual(r.returncode, 0, r.stderr)
        path = plan_path_of(r)
        with open(path, encoding="utf-8") as fh:
            self.assertNotIn("## Source", fh.read())
        set_tasks(path, ["- [T1] Krok (bez odwołania)"])
        self.assertEqual(run("execute", "--root", self.tmp, "--name", "plain", "--title", "T").returncode, 0)
        out = tasks_json(self.tmp, "plain")
        self.assertIsNone(out["source_report"])
        self.assertEqual(out["items"][0]["title"], "Krok (bez odwołania)")
        self.assertNotIn("ref", out["items"][0])

    def test_ref_with_unknown_prefix_stays_in_title(self):
        self.make_plan("cleanup-f", ["- [T1] Krok (ref: raport.md#X1)"])
        self.assertEqual(run("execute", "--root", self.tmp, "--name", "cleanup-f", "--title", "T").returncode, 0)
        item = tasks_json(self.tmp, "cleanup-f")["items"][0]
        self.assertEqual(item["title"], "Krok (ref: raport.md#X1)")
        self.assertNotIn("ref", item)


if __name__ == "__main__":
    unittest.main()
