#!/usr/bin/env python3
"""Testy build_context_pack (read model) i CLI `pack` (krok 3 planu read-side).

Uruchom: python3 /home/dgrabowski/.claude/skills/adhoc-sdlc/scripts/test_pack.py
Stdlib-only (unittest, subprocess), bez zależności zewnętrznych.
"""

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest

import sdlc_doc


TODAY_ISO = "2026-06-11T12:00:00+02:00"
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ADHOC = os.path.join(SCRIPTS_DIR, "adhoc_sdlc.py")


def _days_ago(n: int) -> str:
    base = dt.datetime.fromisoformat(TODAY_ISO)
    return (base - dt.timedelta(days=n)).isoformat()


def _write_doc(root, kind, name, date_iso, keywords, project, status, body):
    target = os.path.join(root, "adhoc-sdlc")
    os.makedirs(target, exist_ok=True)
    fm = [
        "---",
        f"type: {kind}",
        f"name: {name}",
        f'title: "{name} title"',
        f'project: "{project}"',
        "keywords: [" + ", ".join(keywords) + "]",
        f"created: {date_iso}",
        f"updated: {date_iso}",
        f"status: {status}",
        "---",
        "",
    ]
    text = "\n".join(fm) + "\n" + body
    path = os.path.join(target, f"{kind}-{date_iso[:10]}-{name}.md")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def _execute_body(decision, result, verification="Done.", steps="- x: step"):
    return (
        f"Plan: `adhoc-sdlc/plan-x.md`\n\n"
        f"## Steps\n\n{steps}\n\n"
        f"## Decisions And Deviations\n\n{decision}\n\n"
        f"## Verification\n\n{verification}\n\n"
        f"## Final Result\n\n{result}\n"
    )


def _handoff_body(goal, nxt, worked="Worked X.", didnt="Failed Y."):
    return (
        f"## Goal\n\n{goal}\n\n"
        f"## Current Progress\n\nProgress.\n\n"
        f"## What Worked\n\n{worked}\n\n"
        f"## What Didn't Work\n\n{didnt}\n\n"
        f"## Next Steps\n\n{nxt}\n\n"
        f"## Suggested Skills\n\nnone\n"
    )


def _plan_body(summary):
    return f"## Summary\n\n{summary}\n\n## Key Changes\n\nTODO\n\n## Test Plan\n\nTODO\n\n## Assumptions\n\nTODO\n"


class HistoryPackTests(unittest.TestCase):
    def _corpus(self, root):
        _write_doc(root, "execute", "modal-fix", _days_ago(1), ["modal", "ui"], "app",
                   "done", _execute_body("Lokalna konfiguracja modala.", "Modal poprawiony."))
        _write_doc(root, "execute", "modal-width", _days_ago(3), ["modal"], "app",
                   "done", _execute_body("Bez globalnego komponentu.", "Szerokość ok."))
        _write_doc(root, "plan", "modal-rules", _days_ago(5), ["modal", "ui"], "app",
                   "in-progress", _plan_body("Ujednolicić modale."))
        _write_doc(root, "execute", "build-fix", _days_ago(2), ["build", "fpc"], "app",
                   "done", _execute_body("Zmieniono kolejność unitów.", "Build zielony."))

    def test_stats_and_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="modale", max_items=2,
                today_iso=TODAY_ISO,
            )
            self.assertEqual(pack["intent"], "history")
            self.assertEqual(pack["stats"]["matched"], 4)
            self.assertEqual(pack["stats"]["relevant"], 3)  # build-fix odsiane bramką (0 wspólnych keywords)
            self.assertEqual(pack["stats"]["included"], 2)
            self.assertEqual(pack["stats"]["omitted"], 1)  # relevant(3) - included(2)
            self.assertEqual(pack["stats"]["below_threshold"], 1)  # build-fix poza progiem trafności
            scores = [it["score"] for it in pack["items"]]
            self.assertEqual(scores, sorted(scores, reverse=True))
            # Najtrafniejszy item dotyczy modali, nie buildu.
            self.assertIn("modal", pack["items"][0]["keywords"])

    def test_execute_extracts_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="modale", today_iso=TODAY_ISO,
            )
            ex = next(it for it in pack["items"] if it["name"] == "modal-fix")
            headings = [e["heading"] for e in ex["extracts"]]
            self.assertEqual(headings, ["Final Result", "Decisions And Deviations"])

    def test_extract_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            long_decision = "x" * 1500
            _write_doc(tmp, "execute", "huge", _days_ago(1), ["modal"], "app",
                       "done", _execute_body(long_decision, "ok"))
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO,
            )
            dec = next(e for it in pack["items"] for e in it["extracts"]
                       if e["heading"] == "Decisions And Deviations")
            self.assertTrue(dec["truncated"])
            self.assertLessEqual(dec["chars"], 600)

    def test_empty_corpus_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO,
            )
            self.assertEqual(pack["stats"]["matched"], 0)
            self.assertEqual(pack["items"], [])
            self.assertIn("no_candidates", pack["warnings"])

    def test_keyword_cooccurrence_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal", "ui"], angle="m", today_iso=TODAY_ISO,
            )
            index = pack["signals"]["keyword_index"]
            # keyword 'modal' wskazuje >1 pakiet -> sygnał powtarzalności dla agenta.
            self.assertIn("modal", index)
            self.assertGreater(len(index["modal"]), 1)

    def test_presentation_contract_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="modale tematy", today_iso=TODAY_ISO,
            )
            pres = pack["presentation"]
            self.assertEqual(pres["audience"], "human")
            self.assertEqual(pres["output_contract"], "compact_report")
            self.assertEqual(pres["group_by"], "theme_then_date")
            self.assertEqual(pres["angle"], "modale tematy")
            self.assertLessEqual(pack["budget"]["used_chars"], pack["budget"]["max_total_chars"])

    def test_skeleton_is_english(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO,
            )
            # Pole machine-facing: spójny angielski (render i tak po polsku wg języka usera).
            self.assertEqual(
                pack["presentation"]["skeleton"],
                ["title_range_stats", "themed_groups", "conclusions", "next_steps"],
            )


class RelevanceGateTests(unittest.TestCase):
    """Bramka trafności: z keywords tylko niezerowe pokrycie wchodzi do items, reszta below_threshold."""

    def _corpus(self, root):
        _write_doc(root, "execute", "modal-fix", _days_ago(1), ["modal", "ui"], "app",
                   "done", _execute_body("Modal.", "OK."))
        _write_doc(root, "execute", "build-fix", _days_ago(2), ["build", "fpc"], "app",
                   "done", _execute_body("Build.", "OK."))
        _write_doc(root, "execute", "color-fix", _days_ago(3), ["colors", "skin"], "app",
                   "done", _execute_body("Kolory.", "OK."))

    def test_zero_overlap_records_go_below_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO)
            self.assertEqual({it["name"] for it in pack["items"]}, {"modal-fix"})
            self.assertEqual(pack["stats"]["matched"], 3)
            self.assertEqual(pack["stats"]["relevant"], 1)
            self.assertEqual(pack["stats"]["below_threshold"], 2)

    def test_plural_singular_match_via_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            # query "color" (l. poj.) trafia rekord z keyword "colors" (l. mn.) po normalizacji.
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["color"], angle="m", today_iso=TODAY_ISO)
            self.assertIn("color-fix", {it["name"] for it in pack["items"]})
            self.assertEqual(pack["stats"]["relevant"], 1)

    def test_no_relevant_warns_and_empties_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["nonexistent"], angle="m", today_iso=TODAY_ISO)
            self.assertEqual(pack["items"], [])
            self.assertEqual(pack["stats"]["relevant"], 0)
            self.assertEqual(pack["stats"]["below_threshold"], 3)
            self.assertIn("no_relevant", pack["warnings"])

    def test_no_keywords_disables_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            # Bez keywords (sam angle) bramka nieaktywna -> ranking recency, wszystko relevant.
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=[], angle="cokolwiek", today_iso=TODAY_ISO)
            self.assertEqual(pack["stats"]["relevant"], 3)
            self.assertEqual(pack["stats"]["below_threshold"], 0)
            self.assertNotIn("no_relevant", pack["warnings"])


class ResumePackTests(unittest.TestCase):
    def _corpus(self, root):
        _write_doc(root, "handoff", "rest-state", _days_ago(1), ["rest"], "dflex-rest",
                   "in-progress", _handoff_body("Dokończyć REST.", "1. Test 2. Deploy"))
        _write_doc(root, "handoff", "gantt-bug", _days_ago(2), ["gantt"], "dgantt",
                   "in-progress", _handoff_body("Naprawić gantt.", "1. Repro"))
        _write_doc(root, "handoff", "old-task", _days_ago(9), ["misc"], "app",
                   "done", _handoff_body("Stare.", "1. Nic"))
        _write_doc(root, "plan", "rest-state", _days_ago(6), ["rest"], "dflex-rest",
                   "in-progress", _plan_body("REST."))

    def test_list_mode_returns_handoff_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack("resume", root=tmp, today_iso=TODAY_ISO)
            self.assertIsNone(pack["primary"])
            self.assertTrue(all(r["type"] == "handoff" for r in pack["related"]))
            self.assertLessEqual(len(pack["related"]), 4)
            # Najświeższy handoff pierwszy.
            self.assertEqual(pack["related"][0]["name"], "rest-state")

    def test_detail_mode_returns_primary_with_extracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack(
                "resume", root=tmp, name="rest-state", today_iso=TODAY_ISO,
            )
            self.assertIsNotNone(pack["primary"])
            self.assertEqual(pack["primary"]["name"], "rest-state")
            headings = [e["heading"] for e in pack["primary"]["extracts"]]
            self.assertIn("Goal", headings)
            self.assertIn("Next Steps", headings)

    def test_list_mode_honors_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack("resume", root=tmp, limit=2, today_iso=TODAY_ISO)
            self.assertEqual(len(pack["related"]), 2)
            # limit=0 oznacza brak limitu - obowiązuje sam budżet (max 4); korpus ma 3 handoffy
            pack = sdlc_doc.build_context_pack("resume", root=tmp, limit=0, today_iso=TODAY_ISO)
            self.assertEqual(len(pack["related"]), 3)

    def test_include_history_populates_related(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            pack = sdlc_doc.build_context_pack(
                "resume", root=tmp, name="rest-state", include_history=True,
                history_angle="rest", today_iso=TODAY_ISO,
            )
            self.assertTrue(len(pack["related"]) >= 1)
            self.assertLessEqual(len(pack["related"]), 5)


class HandoffPackTests(unittest.TestCase):
    def test_related_paths_without_extracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_doc(tmp, "plan", "rest-state", _days_ago(6), ["rest"], "dflex-rest",
                       "in-progress", _plan_body("REST."))
            _write_doc(tmp, "execute", "rest-state", _days_ago(3), ["rest"], "dflex-rest",
                       "in-progress", _execute_body("Decyzja.", "Wynik."))
            _write_doc(tmp, "execute", "other", _days_ago(2), ["misc"], "app",
                       "done", _execute_body("X.", "Y."))
            pack = sdlc_doc.build_context_pack(
                "handoff", root=tmp, name="rest-state", project="dflex-rest",
                keywords=["rest"], today_iso=TODAY_ISO,
            )
            self.assertIsNone(pack["primary"])
            self.assertEqual(pack["items"], [])
            names = {r["name"] for r in pack["related"]}
            self.assertIn("rest-state", names)
            for r in pack["related"]:
                self.assertEqual(r["extracts"], [])
            self.assertLessEqual(len(pack["related"]), 5)


class RobustnessTests(unittest.TestCase):
    """EIO/nieczytelny plik (retry+skip) i raportowanie niekompletnych dzienników."""

    def test_unreadable_file_is_skipped_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Poprawny dziennik, żeby pack miał z czego zbudować wynik.
            _write_doc(tmp, "execute", "modal-fix", _days_ago(1), ["modal"], "app",
                       "done", _execute_body("Decyzja.", "Wynik."))
            # Deterministycznie nieczytelny "plik": katalog o nazwie pliku .md.
            # open() rzuca IsADirectoryError (podtyp OSError) niezależnie od uid.
            bad = os.path.join(tmp, "adhoc-sdlc", "execute-2026-06-01-bad.md")
            os.makedirs(bad)
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO,
            )
            self.assertGreaterEqual(pack["stats"]["unreadable"], 1)
            self.assertIn("unreadable_files", pack["warnings"])

    def test_incomplete_frontmatter_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_doc(tmp, "execute", "modal-fix", _days_ago(1), ["modal"], "app",
                       "done", _execute_body("Decyzja.", "Wynik."))
            # Plik bez frontmatter (stary korpus sprzed kontraktu metadanych).
            target = os.path.join(tmp, "adhoc-sdlc")
            legacy = os.path.join(target, "execute-2026-06-02-legacy.md")
            with open(legacy, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("## Summary\n\nStary dziennik bez frontmatter.\n")
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO,
            )
            self.assertGreaterEqual(pack["stats"]["incomplete_frontmatter"], 1)
            self.assertIn("incomplete_frontmatter", pack["warnings"])

    def test_keywords_as_bare_string_is_listified(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "adhoc-sdlc")
            os.makedirs(target, exist_ok=True)
            # Frontmatter z keywords bez nawiasów (uszkodzony/ręcznie pisany korpus).
            text = (
                "---\ntype: execute\nname: bare-kw\n"
                'title: "bare"\nproject: "app"\n'
                f"keywords: modal\ncreated: {_days_ago(1)}\nupdated: {_days_ago(1)}\n"
                "status: done\n---\n\n" + _execute_body("Decyzja.", "Wynik.")
            )
            with open(os.path.join(target, "execute-2026-06-10-bare-kw.md"), "w",
                      encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO,
            )
            # String "modal" -> ["modal"], a nie zbiór znaków -> item trafia i ma poprawne keywords.
            item = next(it for it in pack["items"] if it["name"] == "bare-kw")
            self.assertEqual(item["keywords"], ["modal"])
            self.assertGreater(item["score"], 0.0)

    def test_keyword_index_dedups_duplicate_keywords(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_doc(tmp, "execute", "dup-kw", _days_ago(1), ["modal", "modal"], "app",
                       "done", _execute_body("Decyzja.", "Wynik."))
            pack = sdlc_doc.build_context_pack(
                "history", root=tmp, keywords=["modal"], angle="m", today_iso=TODAY_ISO,
            )
            index = pack["signals"]["keyword_index"]
            # Duplikat keyworda w rekordzie nie powiela ścieżki w indeksie.
            self.assertEqual(len(index["modal"]), 1)


class CliPackTests(unittest.TestCase):
    def _run(self, *args, root):
        return subprocess.run(
            [sys.executable, ADHOC, "pack", "--root", root, *args],
            capture_output=True, text=True,
        )

    def _corpus(self, root):
        _write_doc(root, "execute", "modal-fix", _days_ago(1), ["modal"], "app",
                   "done", _execute_body("Decyzja.", "Wynik."))

    def test_history_without_angle_or_keywords_is_contract_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            res = self._run("--intent", "history", root=tmp)
            self.assertEqual(res.returncode, 2)
            self.assertIn("ERROR", res.stderr)

    def test_angle_with_non_history_intent_is_contract_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            res = self._run("--intent", "resume", "--angle", "coś", root=tmp)
            self.assertEqual(res.returncode, 2)
            self.assertIn("ERROR", res.stderr)

    def test_history_with_angle_returns_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._corpus(tmp)
            res = self._run("--intent", "history", "--angle", "modale", "--keywords", "modal", root=tmp)
            self.assertEqual(res.returncode, 0, res.stderr)
            pack = json.loads(res.stdout)
            self.assertEqual(pack["intent"], "history")
            self.assertEqual(pack["stats"]["matched"], 1)

    def test_empty_corpus_returns_no_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = self._run("--intent", "history", "--keywords", "modal", root=tmp)
            self.assertEqual(res.returncode, 0, res.stderr)
            pack = json.loads(res.stdout)
            self.assertEqual(pack["stats"]["matched"], 0)
            self.assertIn("no_candidates", pack["warnings"])

    def test_resume_list_mode_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_doc(tmp, "handoff", "rest-state", _days_ago(1), ["rest"], "dflex-rest",
                       "in-progress", _handoff_body("Cel.", "Kroki."))
            res = self._run("--intent", "resume", root=tmp)
            self.assertEqual(res.returncode, 0, res.stderr)
            pack = json.loads(res.stdout)
            self.assertEqual(pack["intent"], "resume")
            self.assertEqual(len(pack["related"]), 1)



def _write_execute_json(root, name, date_iso, *, tasks=None, legacy=False):
    """Dziennik execute-*.json; legacy=True -> bez pól schema i tasks (tryb dawny)."""
    target = os.path.join(root, "adhoc-sdlc")
    os.makedirs(target, exist_ok=True)
    obj = {"type": "execute", "name": name, "title": f"{name} title", "project": "", "keywords": ["rest"],
           "original_prompt": "", "created": date_iso, "updated": date_iso, "status": "in-progress",
           "plan": f"adhoc-sdlc/plan-x-{name}.md", "entries": [], "decisions": [], "verification": [],
           "final_result": None}
    if not legacy:
        obj["schema"] = 2
        obj["tasks"] = tasks or []
    path = os.path.join(target, f"execute-{date_iso[:10]}-{name}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    return path


TASKS = [
    {"id": "T1", "title": "Pole tasks", "status": "done", "source": "plan"},
    {"id": "T2", "title": "Walidacje", "status": "in_progress", "source": "plan"},
    {"id": "T3", "title": "Poprawka spoza planu", "status": "pending", "source": "added"},
]


class TaskStatePackTests(unittest.TestCase):
    """AC-004: pack resume i odczyt stanu pokazują zadania dziennika z ich stanem."""

    def test_resume_detail_includes_journal_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_doc(tmp, "handoff", "rest-state", _days_ago(1), ["rest"], "dflex-rest",
                       "in-progress", _handoff_body("Cel.", "Kroki."))
            path = _write_execute_json(tmp, "rest-state", _days_ago(2), tasks=TASKS)
            pack = sdlc_doc.build_context_pack("resume", root=tmp, name="rest-state", today_iso=TODAY_ISO)
            tasks = pack["tasks"]
            self.assertEqual(tasks["execute"], path)
            self.assertEqual([(t["id"], t["status"]) for t in tasks["items"]],
                             [("T1", "done"), ("T2", "in_progress"), ("T3", "pending")])
            self.assertEqual(tasks["open"], ["T2", "T3"])
            self.assertEqual(tasks["in_progress"], "T2")

    def test_resume_tasks_none_for_legacy_or_list_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_doc(tmp, "handoff", "rest-state", _days_ago(1), ["rest"], "dflex-rest",
                       "in-progress", _handoff_body("Cel.", "Kroki."))
            _write_execute_json(tmp, "rest-state", _days_ago(2), legacy=True)
            pack = sdlc_doc.build_context_pack("resume", root=tmp, name="rest-state", today_iso=TODAY_ISO)
            self.assertIsNone(pack["tasks"])
            pack = sdlc_doc.build_context_pack("resume", root=tmp, today_iso=TODAY_ISO)
            self.assertIsNone(pack["tasks"])

    def test_synthetic_tasks_section_only_for_schema2(self):
        with tempfile.TemporaryDirectory() as tmp:
            new = sdlc_doc.extract_document(_write_execute_json(tmp, "a", _days_ago(1), tasks=TASKS))
            sec = sdlc_doc.get_section(new["sections"], "Tasks")
            self.assertIn("- [T2] (in_progress) Walidacje", sec["text"])
            old = sdlc_doc.extract_document(_write_execute_json(tmp, "b", _days_ago(1), legacy=True))
            self.assertIsNone(sdlc_doc.get_section(old["sections"], "Tasks"))
            self.assertIsNone(old["tasks"])


class CliTasksTests(unittest.TestCase):
    def _run(self, *args, root):
        return subprocess.run([sys.executable, ADHOC, "tasks", "--root", root, *args],
                              capture_output=True, text=True)

    def test_tasks_json_and_tsv(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_execute_json(tmp, "rest-state", _days_ago(1), tasks=TASKS)
            res = self._run("--name", "rest-state", root=tmp)
            self.assertEqual(res.returncode, 0, res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out["schema"], 2)
            self.assertFalse(out["legacy"])
            self.assertEqual(out["open"], ["T2", "T3"])
            self.assertEqual(out["in_progress"], "T2")
            res = self._run("--name", "rest-state", "--format", "tsv", root=tmp)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(res.stdout.splitlines()[1], "T2\tin_progress\tWalidacje")

    def test_tasks_legacy_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_execute_json(tmp, "old", _days_ago(1), legacy=True)
            out = json.loads(self._run("--name", "old", root=tmp).stdout)
            self.assertTrue(out["legacy"])
            self.assertEqual(out["items"], [])

    def test_tasks_without_journal_is_contract_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = self._run("--name", "nic", root=tmp)
            self.assertEqual(res.returncode, 2)
            self.assertIn("ERROR", res.stderr)

    def test_tasks_bad_format_is_contract_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_execute_json(tmp, "rest-state", _days_ago(1), tasks=TASKS)
            self.assertEqual(self._run("--name", "rest-state", "--format", "xml", root=tmp).returncode, 2)

if __name__ == "__main__":
    unittest.main()
