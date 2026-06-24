#!/usr/bin/env python3
"""Testy full-text recall (BM25) grupowanego po sesji oraz subkomendy CLI `search`.

Uruchom: python3 /home/dgrabowski/.claude/skills/adhoc-sdlc/scripts/test_search.py
Stdlib-only (unittest, subprocess), bez zależności zewnętrznych.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

import sdlc_doc


TODAY_ISO = "2026-06-24T12:00:00+02:00"
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ADHOC = os.path.join(SCRIPTS_DIR, "adhoc_sdlc.py")


def _write_plan(root, name, body, *, date=TODAY_ISO, keywords=None, project=""):
    target = os.path.join(root, "adhoc-sdlc")
    os.makedirs(target, exist_ok=True)
    fm = [
        "---",
        "type: plan",
        f"name: {name}",
        f'title: "{name} tytuł"',
        f'project: "{project}"',
        "keywords: [" + ", ".join(keywords or []) + "]",
        f"created: {date}",
        f"updated: {date}",
        "status: in-progress",
        "---",
        "",
    ]
    path = os.path.join(target, f"plan-{date[:10]}-{name}.md")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(fm) + "\n" + body)
    return path


def _write_execute_json(root, name, *, date=TODAY_ISO, original_prompt="", final="",
                        decisions=None, keywords=None, project=""):
    target = os.path.join(root, "adhoc-sdlc")
    os.makedirs(target, exist_ok=True)
    obj = {
        "type": "execute", "name": name, "title": f"{name} tytuł",
        "project": project, "keywords": keywords or [],
        "original_prompt": original_prompt,
        "created": date, "updated": date, "status": "in-progress",
        "plan": f"adhoc-sdlc/plan-{date[:10]}-{name}.md",
        "entries": [{"ts": date, "note": "praca"}],
        "decisions": [{"ts": date, "text": d} for d in (decisions or [])],
        "verification": [], "final_result": final or None,
    }
    path = os.path.join(target, f"execute-{date[:10]}-{name}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False)
    return path


# Korpus współdzielony przez testy rankingu: sesja welcome + dwa niepowiązane szumy.
WELCOME_PLAN = (
    "## Summary\n\nEkran powitalny aplikacji oraz obraz tła startowego widoku.\n\n"
    "## Original Prompt\n\nZmiana obrazu tła na ekranie powitalnym (welcome page). "
    "Chodzi o skórka oraz motyw startowy.\n\n"
    "## Key Changes\n\nTODO\n"
)
BUILD_PLAN = "## Summary\n\nNaprawa błędów kompilacji fpc lazarus podczas budowania projektu.\n"
REST_PLAN = "## Summary\n\nEndpoint REST API zwracający dane DTO przez warstwę serwisu.\n"


def _seed_corpus(root):
    _write_plan(root, "welcome-page", WELCOME_PLAN, keywords=["welcome-page", "theme"])
    _write_plan(root, "build-fix", BUILD_PLAN, keywords=["build"])
    _write_plan(root, "rest-api", REST_PLAN, keywords=["rest"])


class TokenizerTests(unittest.TestCase):
    def test_hyphen_split(self):
        self.assertEqual(sdlc_doc._terms("welcome-page"), ["welcome", "page"])

    def test_camel_split(self):
        self.assertEqual(sdlc_doc._terms("frWelcomePage"), ["fr", "welcome", "page"])

    def test_plural_stem(self):
        # Lekki stem liczby mnogiej (reuż _stem_kw): colors->color, skins->skin.
        self.assertEqual(sdlc_doc._terms("colors skins"), ["color", "skin"])

    def test_stopwords_and_minlen(self):
        terms = sdlc_doc._terms("do na ze i welcome")
        self.assertEqual(terms, ["welcome"])  # stoplista PL + odsiew tokenów < 2 znaków

    def test_unicode_polish(self):
        self.assertEqual(sdlc_doc._terms("tło motyw skórka"), ["tło", "motyw", "skórka"])


class SearchRankingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        _seed_corpus(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _search(self, query, **kw):
        return sdlc_doc.search_corpus(self.root, query, today_iso=TODAY_ISO, **kw)

    def test_failing_to_passing_welcome(self):
        # Scenariusz, który dziś zawodzi (keyword gate): wolny tekst PL+EN ma trafić welcome.
        res = self._search("welcome page ekran powitalny")
        self.assertTrue(res["results"], "oczekiwano co najmniej jednego trafienia")
        self.assertEqual(res["results"][0]["session"], "welcome-page")
        self.assertEqual(res["mode"], "bm25_fulltext")

    def test_original_prompt_is_indexed(self):
        # 'skórka' występuje wyłącznie w Original Prompt - zapytanie PL musi trafić przez to pole.
        res = self._search("skórka")
        self.assertEqual([r["session"] for r in res["results"]], ["welcome-page"])
        top = res["results"][0]
        self.assertEqual(top["matched_terms"], ["skórka"])
        self.assertEqual(top["matched_fields"], ["original_prompt"])

    def test_noise_query_no_matches(self):
        res = self._search("kubernetes docker terraform")
        self.assertEqual(res["results"], [])
        self.assertIn("no_matches", res["warnings"])

    def test_boilerplate_heading_not_indexed(self):
        # Każdy plan ma nagłówek '## Summary'/'## Key Changes', ale to boilerplate szablonu:
        # samo słowo z nagłówka nie może stać się trafieniem.
        res = self._search("summary changes")
        self.assertEqual(res["results"], [])
        self.assertIn("no_matches", res["warnings"])

    def test_empty_query_warns(self):
        res = self._search("   ")
        self.assertIn("empty_query", res["warnings"])
        self.assertEqual(res["results"], [])

    def test_limit_zero_returns_all(self):
        # 'aplikacji projektu serwisu' dotyka wszystkich trzech sesji; limit 0 = bez limitu.
        res = self._search("aplikacji projektu serwisu", limit=0)
        self.assertEqual(res["stats"]["returned"], 3)


class SessionGroupingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_plan_and_execute_collapse_to_one_session(self):
        _write_plan(self.root, "welcome-page", WELCOME_PLAN, keywords=["welcome-page"])
        _write_execute_json(self.root, "welcome-page",
                            original_prompt="Zmiana obrazu tła na ekranie powitalnym, skórka motyw.",
                            final="Zrobione: nowy obraz tła.")
        res = sdlc_doc.search_corpus(self.root, "welcome ekran powitalny", today_iso=TODAY_ISO)
        self.assertEqual(len(res["results"]), 1, "plan + execute = jedna sesja")
        artifacts = res["results"][0]["artifacts"]
        self.assertEqual({a["type"] for a in artifacts}, {"plan", "execute"})

    def test_summary_slots_from_sections(self):
        _write_plan(self.root, "welcome-page", WELCOME_PLAN, keywords=["welcome-page"])
        _write_execute_json(self.root, "welcome-page", final="Zrobione: nowy obraz tła startowego.")
        res = sdlc_doc.search_corpus(self.root, "welcome ekran powitalny", today_iso=TODAY_ISO)
        slots = res["results"][0]["summary_slots"]
        self.assertIn("Ekran powitalny", slots["planned"])      # z sekcji Summary planu
        self.assertIn("nowy obraz tła", slots["executed"])      # z Final Result dziennika


class FuzzyAndCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _search(self, query, **kw):
        return sdlc_doc.search_corpus(self.root, query, today_iso=TODAY_ISO, **kw)

    def test_stem_bridge_finds_inflected(self):
        # Polska fleksja: zapytanie 'ganta' (dopełniacz) trafia korpusowe 'gantt' przez most rdzeniowy.
        _write_plan(self.root, "gantt-skin", "## Summary\n\nWidok gantt panelu i gantta nagłówka.\n",
                    keywords=["gantt"])
        res = self._search("ganta")
        self.assertEqual([r["session"] for r in res["results"]], ["gantt-skin"])
        # most pokazany jawnie jako zapytanie~token, nie udaje dopasowania dokładnego
        self.assertTrue(any("~" in t for t in res["results"][0]["matched_terms"]))

    def test_no_fuzzy_disables_bridge(self):
        _write_plan(self.root, "gantt-skin", "## Summary\n\nWidok gantt panelu.\n", keywords=["gantt"])
        res = self._search("ganta", fuzzy=False)
        self.assertEqual(res["results"], [])
        self.assertIn("no_matches", res["warnings"])

    def test_exact_outranks_stem(self):
        # Przy równym pokryciu dokładny rdzeń bije rdzeniowy.
        _write_plan(self.root, "exact", "## Summary\n\nWidok gantt oraz gantt panelu.\n", keywords=["a"])
        _write_plan(self.root, "stem", "## Summary\n\nWidok gantta nagłówka.\n", keywords=["b"])
        res = self._search("gantt")
        self.assertEqual(res["results"][0]["session"], "exact")

    def test_short_token_no_overreach(self):
        # 'plan'(4) nie sięga 'planetarium'(11): wspólny prefiks 4, pokrycie 4/11 < 0.5 -> odrzucone.
        _write_plan(self.root, "astro", "## Summary\n\nModel planetarium kopuły.\n", keywords=["astro"])
        res = self._search("plan")
        self.assertEqual(res["results"], [])
        self.assertIn("no_matches", res["warnings"])

    def test_coverage_dominates_bm25(self):
        # Reguła użytkownika: sesja z dwoma słowami bije sesję z jednym, choćby ta miała wyższy surowy BM25.
        _write_plan(self.root, "both", "## Summary\n\ngantt skin panel.\n", keywords=["both"])
        _write_plan(self.root, "gantt-only", "## Summary\n\n" + " ".join(["gantt"] * 30) + "\n",
                    keywords=["gonly"])
        res = self._search("gantt skin")
        by = {r["session"]: r for r in res["results"]}
        self.assertEqual(res["results"][0]["session"], "both")
        self.assertEqual(by["both"]["coverage"], 2)
        self.assertEqual(by["gantt-only"]["coverage"], 1)
        order = [r["session"] for r in res["results"]]
        self.assertLess(order.index("both"), order.index("gantt-only"))

    def test_coverage_field_present(self):
        _write_plan(self.root, "x", "## Summary\n\ngantt panel.\n", keywords=["x"])
        top = self._search("gantt")["results"][0]
        self.assertEqual(top["coverage"], 1)


class SearchCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        _seed_corpus(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        return subprocess.run([sys.executable, ADHOC, "search", "--root", self.root, *args],
                              capture_output=True, text=True)

    def test_cli_json_ranks_welcome(self):
        out = self._run("welcome page ekran powitalny", "--format", "json")
        self.assertEqual(out.returncode, 0, out.stderr)
        data = json.loads(out.stdout)
        self.assertEqual(data["mode"], "bm25_fulltext")
        self.assertEqual(data["results"][0]["session"], "welcome-page")

    def test_cli_text_default(self):
        out = self._run("welcome page")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("welcome-page", out.stdout)

    def test_cli_missing_query_is_contract_error(self):
        out = self._run("--format", "json")
        self.assertEqual(out.returncode, 2)
        self.assertIn("ERROR:", out.stderr)

    def test_cli_bad_format_is_contract_error(self):
        out = self._run("welcome", "--format", "tsv")
        self.assertEqual(out.returncode, 2)
        self.assertIn("niedozwolony --format", out.stderr)


if __name__ == "__main__":
    unittest.main()
