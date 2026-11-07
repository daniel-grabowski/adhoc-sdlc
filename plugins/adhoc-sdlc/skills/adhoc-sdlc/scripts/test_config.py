#!/usr/bin/env python3
"""Testy load_config / cmd_config (warstwa B: domyślne tryby).

Kontrakt: brak pliku -> wszystkie tryby OFF (zachowanie sprzed configu); projekt
nadpisuje global; nieznane klucze i wartości nie-bool są ignorowane; uszkodzony
config to fail loud (ContractError). _config_paths jest mockowane, żeby nie dotykać
prawdziwego ~/.adhoc-sdlc.
"""

import json
import tempfile
import unittest
from pathlib import Path

import adhoc_sdlc


class LoadConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.global_path = base / "global" / "config.json"
        self.project_path = base / "project" / "adhoc-sdlc" / "config.json"
        self.root = base / "project"
        self._orig_paths = adhoc_sdlc._config_paths
        adhoc_sdlc._config_paths = lambda root: (self.global_path, self.project_path)

    def tearDown(self):
        adhoc_sdlc._config_paths = self._orig_paths
        self._tmp.cleanup()

    def _write(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_no_file_all_off(self):
        modes = adhoc_sdlc.load_config(self.root)
        self.assertEqual(modes, {k: False for k in adhoc_sdlc.MODE_KEYS})

    def test_cleanup_codebase_off_without_config(self):
        # AC-010 (#7937): tryb cleanup-codebase istnieje i bez configu jest OFF.
        self.assertIn("cleanup-codebase", adhoc_sdlc.MODE_KEYS)
        self.assertIs(adhoc_sdlc.load_config(self.root)["cleanup-codebase"], False)

    def test_cleanup_codebase_off_for_legacy_config(self):
        # AC-010 (#7937): config sprzed 0.7.0 (sześć kluczy, bez cleanup-codebase) daje OFF, pozostałe tryby bez zmian.
        legacy = {"brainstorming": True, "deep-code-verification": True, "test-execution": True,
                  "plan-cove": True, "strategy-temper": True, "execution-cove": True}
        self._write(self.project_path, {"modes": legacy})
        modes = adhoc_sdlc.load_config(self.root)
        self.assertIs(modes["cleanup-codebase"], False)
        for key in legacy:
            self.assertTrue(modes[key], key)

    def test_cleanup_codebase_on_from_config(self):
        self._write(self.project_path, {"modes": {"cleanup-codebase": True}})
        self.assertTrue(adhoc_sdlc.load_config(self.root)["cleanup-codebase"])

    def test_get_modes_cli_prints_cleanup_codebase_off(self):
        # AC-010 (#7937): wyjście `config --get-modes` (CLI), brak configu i dawny config.
        import contextlib
        import io
        for data in (None, {"modes": {"plan-cove": True}}):
            if data is not None:
                self._write(self.project_path, data)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = adhoc_sdlc.main(["config", "--get-modes", "--root", str(self.root)])
            self.assertEqual(rc, 0)
            modes = json.loads(buf.getvalue())["modes"]
            self.assertIs(modes["cleanup-codebase"], False, data)

    def test_project_overrides_default(self):
        self._write(self.project_path, {"modes": {"plan-cove": True}})
        modes = adhoc_sdlc.load_config(self.root)
        self.assertTrue(modes["plan-cove"])
        self.assertFalse(modes["brainstorming"])

    def test_project_beats_global(self):
        self._write(self.global_path, {"modes": {"plan-cove": True, "strategy-temper": True}})
        self._write(self.project_path, {"modes": {"plan-cove": False}})
        modes = adhoc_sdlc.load_config(self.root)
        self.assertFalse(modes["plan-cove"], "projekt powinien nadpisać global")
        self.assertTrue(modes["strategy-temper"], "tryb tylko z global zostaje")

    def test_unknown_keys_ignored(self):
        self._write(self.project_path, {"modes": {"nieistniejacy-tryb": True, "plan-cove": True}})
        modes = adhoc_sdlc.load_config(self.root)
        self.assertNotIn("nieistniejacy-tryb", modes)
        self.assertEqual(set(modes), set(adhoc_sdlc.MODE_KEYS))
        self.assertTrue(modes["plan-cove"])

    def test_non_bool_value_ignored(self):
        self._write(self.project_path, {"modes": {"plan-cove": "yes"}})
        modes = adhoc_sdlc.load_config(self.root)
        self.assertFalse(modes["plan-cove"], "wartość nie-bool nie ustawia trybu")

    def test_corrupt_json_raises(self):
        self.project_path.parent.mkdir(parents=True, exist_ok=True)
        self.project_path.write_text("{ not valid json", encoding="utf-8")
        with self.assertRaises(adhoc_sdlc.ContractError):
            adhoc_sdlc.load_config(self.root)

    def test_modes_not_object_raises(self):
        self._write(self.project_path, {"modes": [1, 2, 3]})
        with self.assertRaises(adhoc_sdlc.ContractError):
            adhoc_sdlc.load_config(self.root)

    def test_top_level_not_object_raises(self):
        self.project_path.parent.mkdir(parents=True, exist_ok=True)
        self.project_path.write_text("[1, 2, 3]", encoding="utf-8")
        with self.assertRaises(adhoc_sdlc.ContractError):
            adhoc_sdlc.load_config(self.root)


if __name__ == "__main__":
    unittest.main()
