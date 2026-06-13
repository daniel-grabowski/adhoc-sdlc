#!/usr/bin/env python3
"""Test regresji append_step (krok 4 planu read-side).

Charakteryzuje zachowanie append_step: wpis trafia na koniec sekcji Steps,
updated/status w frontmatter aktualizowane, reszta body bajtowo nienaruszona.
Test przechodzi na starej (marker) i nowej (parser) implementacji -> dowód
równoważności refaktoru.

Uruchom: python3 /home/dgrabowski/.codex/skills/adhoc-sdlc/scripts/test_append.py
"""

import os
import tempfile
import unittest

import adhoc_sdlc


FIXED = "2026-06-11T12:00:00+02:00"

EXECUTE_OLD = (
    "---\n"
    "type: execute\n"
    "name: rest-state\n"
    'title: "REST state duration"\n'
    'project: "dflex-rest"\n'
    "keywords: [rest, rf001]\n"
    "created: 2026-06-05T10:00:00+02:00\n"
    "updated: 2026-06-05T10:00:00+02:00\n"
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
    "None yet.\n"
    "\n"
    "## Verification\n"
    "\n"
    "Not run yet.\n"
    "\n"
    "## Final Result\n"
    "\n"
    "Pending.\n"
)


class AppendStepRegressionTests(unittest.TestCase):
    def setUp(self):
        self._orig_now = adhoc_sdlc.now
        adhoc_sdlc.now = lambda: FIXED

    def tearDown(self):
        adhoc_sdlc.now = self._orig_now

    def _expected_old_behavior(self, content, entry, status):
        """Referencyjna stara logika (marker-based) do porównania."""
        marker = "## Decisions And Deviations"
        line = f"- {FIXED}: {entry}\n\n"
        out = content.replace(marker, line + marker, 1)
        out = adhoc_sdlc.update_frontmatter_field(out, "updated", FIXED)
        if status is not None:
            out = adhoc_sdlc.update_frontmatter_field(out, "status", status)
        return out

    def _run_append(self, content, entry, status):
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path
            path = Path(tmp) / "execute-2026-06-05-rest-state.md"
            path.write_text(content, encoding="utf-8", newline="\n")
            adhoc_sdlc.append_step(path, entry, status)
            return path.read_text(encoding="utf-8")

    def test_append_matches_old_behavior_no_status(self):
        result = self._run_append(EXECUTE_OLD, "Nowy krok wykonania", None)
        expected = self._expected_old_behavior(EXECUTE_OLD, "Nowy krok wykonania", None)
        self.assertEqual(result, expected)

    def test_append_matches_old_behavior_with_status(self):
        result = self._run_append(EXECUTE_OLD, "Skończone", "done")
        expected = self._expected_old_behavior(EXECUTE_OLD, "Skończone", "done")
        self.assertEqual(result, expected)

    def test_entry_lands_inside_steps_before_next_heading(self):
        result = self._run_append(EXECUTE_OLD, "Krok X", None)
        steps_idx = result.index("## Steps")
        dec_idx = result.index("## Decisions And Deviations")
        entry_idx = result.index("- 2026-06-11T12:00:00+02:00: Krok X")
        self.assertTrue(steps_idx < entry_idx < dec_idx)

    def test_updated_field_changed(self):
        result = self._run_append(EXECUTE_OLD, "Krok", None)
        self.assertIn(f"updated: {FIXED}", result)
        self.assertNotIn("updated: 2026-06-05T10:00:00+02:00", result)

    def test_missing_steps_raises(self):
        broken = (
            "---\ntype: execute\nname: x\ntitle: \"x\"\nproject: \"\"\n"
            "keywords: []\ncreated: 2026-06-05T10:00:00+02:00\n"
            "updated: 2026-06-05T10:00:00+02:00\nstatus: in-progress\n---\n\n"
            "Plan: `x`\n\nBrak sekcji Steps.\n"
        )
        with self.assertRaises(RuntimeError):
            self._run_append(broken, "cokolwiek", None)


if __name__ == "__main__":
    unittest.main()
