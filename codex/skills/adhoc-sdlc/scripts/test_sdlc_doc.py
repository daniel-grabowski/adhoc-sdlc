#!/usr/bin/env python3
"""Testy jednostkowe parsera dokumentu sdlc_doc (krok 1 planu read-side).

Uruchom: python3 /home/dgrabowski/.codex/skills/adhoc-sdlc/scripts/test_sdlc_doc.py
(sys.path[0] = katalog skryptu, więc `import sdlc_doc` zadziała).
Stdlib-only (unittest), bez zależności zewnętrznych.
"""

import datetime as dt
import os
import tempfile
import unittest

import sdlc_doc


TODAY_ISO = "2026-06-11T12:00:00+02:00"


def _days_ago(n: int) -> str:
    base = dt.datetime.fromisoformat(TODAY_ISO)
    return (base - dt.timedelta(days=n)).isoformat()


# Realistyczny plik execute zgodny z szablonami helpera (frontmatter + body).
EXECUTE_FILE = (
    "---\n"
    "type: execute\n"
    "name: rest-state\n"
    'title: "REST state duration"\n'
    'project: "dflex-rest"\n'
    "keywords: [rest, rf001]\n"
    "created: 2026-06-05T10:00:00+02:00\n"
    "updated: 2026-06-05T16:20:00+02:00\n"
    "status: in-progress\n"
    "---\n"
    "\n"
    "Plan: `adhoc-sdlc/plan-2026-06-01-rest-state.md`\n"
    "\n"
    "## Steps\n"
    "\n"
    "- 2026-06-05T10:00:00+02:00: Started implementation.\n"
    "\n"
    "## Decisions And Deviations\n"
    "\n"
    "Nie ruszamy globalnego komponentu.\n"
    "\n"
    "## Verification\n"
    "\n"
    "Not run yet.\n"
    "\n"
    "## Final Result\n"
    "\n"
    "Pending.\n"
)


class SplitFrontmatterTests(unittest.TestCase):
    def test_splits_meta_and_body(self):
        meta, body = sdlc_doc.split_frontmatter(EXECUTE_FILE)
        self.assertEqual(meta["type"], "execute")
        self.assertEqual(meta["name"], "rest-state")
        self.assertEqual(meta["title"], "REST state duration")
        self.assertEqual(meta["project"], "dflex-rest")
        self.assertEqual(meta["keywords"], ["rest", "rf001"])
        self.assertEqual(meta["status"], "in-progress")
        # Body nie zawiera bloku frontmatter.
        self.assertNotIn("type: execute", body)
        self.assertIn("## Steps", body)
        self.assertIn("Plan: `adhoc-sdlc/plan-2026-06-01-rest-state.md`", body)

    def test_no_frontmatter_returns_empty_meta_and_original_body(self):
        text = "# Tytuł\n\nTreść bez frontmatter.\n"
        meta, body = sdlc_doc.split_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)


class ParseSectionsTests(unittest.TestCase):
    def test_basic_sections_and_preamble(self):
        _, body = sdlc_doc.split_frontmatter(EXECUTE_FILE)
        sections = sdlc_doc.parse_sections(body)
        headings = [s["heading"] for s in sections]
        # Preamble (link do planu) ma puste heading i jest pierwsza.
        self.assertEqual(headings[0], "")
        self.assertIn("Plan: `adhoc-sdlc/plan-2026-06-01-rest-state.md`", sections[0]["text"])
        # Sekcje poziomu 2 w kolejności.
        self.assertEqual(
            headings[1:],
            ["Steps", "Decisions And Deviations", "Verification", "Final Result"],
        )

    def test_section_text_captured(self):
        _, body = sdlc_doc.split_frontmatter(EXECUTE_FILE)
        sections = sdlc_doc.parse_sections(body)
        dec = sdlc_doc.get_section(sections, "Decisions And Deviations")
        self.assertIsNotNone(dec)
        self.assertIn("Nie ruszamy globalnego komponentu.", dec["text"])

    def test_nested_headings_stay_in_parent_text(self):
        body = (
            "## Key Changes\n\n"
            "Opis.\n\n"
            "### Podsekcja\n\n"
            "Szczegół podsekcji.\n\n"
            "## Test Plan\n\n"
            "Kroki.\n"
        )
        sections = sdlc_doc.parse_sections(body)
        headings = [s["heading"] for s in sections]
        # ### nie tworzy osobnej pozycji top-level.
        self.assertEqual(headings, ["Key Changes", "Test Plan"])
        key = sdlc_doc.get_section(sections, "Key Changes")
        self.assertIn("### Podsekcja", key["text"])
        self.assertIn("Szczegół podsekcji.", key["text"])

    def test_hash_inside_fence_is_not_heading(self):
        body = (
            "## Key Changes\n\n"
            "Przykład kodu:\n\n"
            "```bash\n"
            "## to nie jest nagłówek\n"
            "echo hi\n"
            "```\n\n"
            "Dalszy opis.\n\n"
            "## Summary\n\n"
            "Krótko.\n"
        )
        sections = sdlc_doc.parse_sections(body)
        headings = [s["heading"] for s in sections]
        self.assertEqual(headings, ["Key Changes", "Summary"])
        key = sdlc_doc.get_section(sections, "Key Changes")
        self.assertIn("## to nie jest nagłówek", key["text"])

    def test_empty_body_returns_no_sections(self):
        self.assertEqual(sdlc_doc.parse_sections(""), [])
        self.assertEqual(sdlc_doc.parse_sections("\n\n"), [])

    def test_crlf_handled_like_lf(self):
        body = "## A\r\n\r\nTekst A.\r\n\r\n## B\r\n\r\nTekst B.\r\n"
        sections = sdlc_doc.parse_sections(body)
        headings = [s["heading"] for s in sections]
        self.assertEqual(headings, ["A", "B"])
        a = sdlc_doc.get_section(sections, "A")
        self.assertIn("Tekst A.", a["text"])


class GetSectionTests(unittest.TestCase):
    def test_case_insensitive_match(self):
        sections = sdlc_doc.parse_sections("## Final Result\n\nGotowe.\n")
        self.assertIsNotNone(sdlc_doc.get_section(sections, "final result"))
        self.assertIsNotNone(sdlc_doc.get_section(sections, "FINAL RESULT"))

    def test_missing_returns_none(self):
        sections = sdlc_doc.parse_sections("## Summary\n\nX.\n")
        self.assertIsNone(sdlc_doc.get_section(sections, "Verification"))


class IsPlaceholderTests(unittest.TestCase):
    def test_known_placeholders(self):
        for ph in ("TODO", "None yet.", "Not run yet.", "Pending.", ""):
            self.assertTrue(sdlc_doc.is_placeholder(ph), ph)
        self.assertTrue(sdlc_doc.is_placeholder("  TODO  "))

    def test_real_text_is_not_placeholder(self):
        self.assertFalse(sdlc_doc.is_placeholder("TODO: napraw modal"))
        self.assertFalse(sdlc_doc.is_placeholder("Zrobione i zweryfikowane."))


class ValidateDocumentTests(unittest.TestCase):
    def test_warns_on_missing_frontmatter(self):
        warnings = sdlc_doc.validate_document({}, sdlc_doc.parse_sections("## Summary\n\nX.\n"))
        self.assertIn("no_frontmatter", warnings)

    def test_warns_when_all_sections_placeholder(self):
        body = "## Summary\n\nTODO\n\n## Key Changes\n\nTODO\n"
        meta = {"type": "plan"}
        warnings = sdlc_doc.validate_document(meta, sdlc_doc.parse_sections(body))
        self.assertIn("all_placeholder", warnings)

    def test_no_warnings_for_complete_doc(self):
        meta, body = sdlc_doc.split_frontmatter(EXECUTE_FILE)
        warnings = sdlc_doc.validate_document(meta, sdlc_doc.parse_sections(body))
        self.assertEqual(warnings, [])


class ExtractDocumentTests(unittest.TestCase):
    def test_reads_file_into_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "execute-2026-06-05-rest-state.md")
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(EXECUTE_FILE)
            doc = sdlc_doc.extract_document(path)
            self.assertEqual(doc["path"], path)
            self.assertEqual(doc["meta"]["name"], "rest-state")
            headings = [s["heading"] for s in doc["sections"]]
            self.assertIn("Decisions And Deviations", headings)
            self.assertEqual(doc["warnings"], [])


class ScoreRecordTests(unittest.TestCase):
    """Deterministyczny scoring 0..1. Wagi: kw 0.45, project 0.25, name 0.15, recency 0.15.

    Nieaktywny sygnał (brak w query) -> jego waga redystrybuowana. Recency aktywny zawsze.
    """

    def _rec(self, **kw):
        rec = {"keywords": [], "project": "", "name": "", "updated": _days_ago(0), "created": ""}
        rec.update(kw)
        return rec

    # --- keyword (Jaccard), tylko kw aktywne + recency(today=1.0) -> denom 0.6 ---
    def test_keyword_full_match(self):
        rec = self._rec(keywords=["a", "b"])
        query = {"keywords": ["a", "b"], "project": "", "name": ""}
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 1.0, places=3)

    def test_keyword_partial_match(self):
        rec = self._rec(keywords=["a", "c"])
        query = {"keywords": ["a", "b"], "project": "", "name": ""}
        # Jaccard {a}/{a,b,c}=1/3 -> (0.45/3 + 0.15)/0.6 = 0.5
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 0.5, places=3)

    def test_keyword_disjoint(self):
        rec = self._rec(keywords=["b"])
        query = {"keywords": ["a"], "project": "", "name": ""}
        # (0 + 0.15)/0.6 = 0.25
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 0.25, places=3)

    # --- project, tylko project aktywny + recency -> denom 0.4 ---
    def test_project_match(self):
        rec = self._rec(project="dflex-rest")
        query = {"keywords": [], "project": "dflex-rest", "name": ""}
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 1.0, places=3)

    def test_project_mismatch(self):
        rec = self._rec(project="other")
        query = {"keywords": [], "project": "dflex-rest", "name": ""}
        # (0 + 0.15)/0.4 = 0.375
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 0.375, places=3)

    # --- name, tylko name aktywne + recency -> denom 0.3 ---
    def test_name_exact(self):
        rec = self._rec(name="rest-state")
        query = {"keywords": [], "project": "", "name": "rest-state"}
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 1.0, places=3)

    def test_name_substring(self):
        rec = self._rec(name="rest-state-v2")
        query = {"keywords": [], "project": "", "name": "rest-state"}
        # (0.15*0.5 + 0.15)/0.3 = 0.75
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 0.75, places=3)

    def test_name_none(self):
        rec = self._rec(name="other")
        query = {"keywords": [], "project": "", "name": "rest-state"}
        # (0 + 0.15)/0.3 = 0.5
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 0.5, places=3)

    # --- recency, query puste -> tylko recency aktywne -> score == recency ---
    def test_recency_today(self):
        rec = self._rec(updated=_days_ago(0))
        query = {"keywords": [], "project": "", "name": ""}
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 1.0, places=3)

    def test_recency_half_window(self):
        rec = self._rec(updated=_days_ago(45))
        query = {"keywords": [], "project": "", "name": ""}
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 0.5, places=3)

    def test_recency_beyond_window_is_zero(self):
        rec = self._rec(updated=_days_ago(200))
        query = {"keywords": [], "project": "", "name": ""}
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 0.0, places=3)

    def test_recency_missing_date_is_zero(self):
        rec = self._rec(updated="", created="")
        query = {"keywords": [], "project": "", "name": ""}
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 0.0, places=3)

    def test_recency_falls_back_to_created(self):
        rec = self._rec(updated="", created=_days_ago(45))
        query = {"keywords": [], "project": "", "name": ""}
        self.assertAlmostEqual(sdlc_doc.score_record(rec, query, TODAY_ISO), 0.5, places=3)

    def test_deterministic(self):
        rec = self._rec(keywords=["a", "b"], project="p", name="rest-state")
        query = {"keywords": ["a"], "project": "p", "name": "rest-state"}
        first = sdlc_doc.score_record(rec, query, TODAY_ISO)
        second = sdlc_doc.score_record(rec, query, TODAY_ISO)
        self.assertEqual(first, second)


class ReadRetryTests(unittest.TestCase):
    """_read_text ponawia odczyt na transient OSError (EIO na WSL 9P)."""

    def setUp(self):
        self._open = getattr(sdlc_doc, "open", None)
        self._delays = sdlc_doc.READ_DELAYS
        sdlc_doc.READ_DELAYS = ()  # bez czekania w testach

    def tearDown(self):
        if self._open is None:
            if "open" in vars(sdlc_doc):
                del sdlc_doc.open
        else:
            sdlc_doc.open = self._open
        sdlc_doc.READ_DELAYS = self._delays

    def test_retries_attempts_times_then_raises(self):
        calls = []

        def fake(*args, **kwargs):
            calls.append(1)
            raise OSError(5, "Input/output error")

        sdlc_doc.open = fake
        with self.assertRaises(OSError):
            sdlc_doc._read_text("nieistotne")
        self.assertEqual(len(calls), sdlc_doc.READ_ATTEMPTS)

    def test_succeeds_on_second_attempt(self):
        import io
        calls = []

        def fake(*args, **kwargs):
            calls.append(1)
            if len(calls) < 2:
                raise OSError(5, "Input/output error")
            return io.StringIO("zawartość")

        sdlc_doc.open = fake
        self.assertEqual(sdlc_doc._read_text("x"), "zawartość")
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
