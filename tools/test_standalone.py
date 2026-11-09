#!/usr/bin/env python3
"""Testy niezależności pluginu (O27, R-043, AC-020 #8000).

adhoc-sdlc nie zależy od niczego spoza pluginu: Forge zależy od adhoc-sdlc, nigdy odwrotnie.
Sprawdza trzy rzeczy, w środowisku bez binarki `forge` (i `rh`) w PATH oraz bez pamięci
(HOME wskazuje pusty katalog, więc nie ma skilla `memory` ani konfiguracji użytkownika):

1. każdy wyrenderowany skill albo komenda, która odwołuje się do skilla `memory` albo binarki
   `forge`, ma jawny tryb „źródła niedostępne” (`sources unavailable`);
2. helper w obu wariantach runtime'u wykonuje pełny cykl (plan, execute, tasks, handoff, list,
   pack, search, config) bez `forge` i bez pamięci;
3. helper nie woła procesów zewnętrznych i importuje wyłącznie bibliotekę standardową.

Uruchom: python3 -m pytest tools -q (test sam usuwa `forge` z PATH podprocesów, więc nie zależy
od środowiska wywołania; test_sanitized_env_has_no_forge pilnuje, że to usunięcie zadziałało).
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import render

# Binarki procesu Forge, których plugin nie może wymagać.
FORGE_TOOLS = ("forge", "rh")

# Odwołanie do zewnętrznego źródła: skill `memory`, binarka albo komenda `forge`.
EXTERNAL_SOURCE_RE = re.compile(r"`memory` skill|`forge` (?:binary|command)|`forge [a-z]")

UNAVAILABLE_MARKER = "`sources unavailable` (`źródła niedostępne`)"

HELPER_DIRS = (
    render.REPO_ROOT / "claude/skills/adhoc-sdlc/scripts",
    render.REPO_ROOT / "plugins/adhoc-sdlc/skills/adhoc-sdlc/scripts",
)


def sanitized_path() -> str:
    # Usuwa z PATH każdy katalog, w którym leży forge albo rh.
    kept = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        if any(os.access(os.path.join(entry, tool), os.X_OK) for tool in FORGE_TOOLS):
            continue
        kept.append(entry)
    return os.pathsep.join(kept)


def sanitized_env(home: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("FORGE_", "CLAUDE_", "CODEX_"))}
    env["PATH"] = sanitized_path()
    env["HOME"] = home
    env.pop("XDG_CONFIG_HOME", None)
    return env


def runtime_specs():
    for runtime in ("claude", "codex"):
        spec = json.loads((render.RUNTIMES_DIR / f"{runtime}.json").read_text(encoding="utf-8"))
        yield runtime, spec


class SanitizedEnvTests(unittest.TestCase):
    def test_sanitized_env_has_no_forge(self):
        # Bez tego strażnika test helpera mógłby przejść z forge w PATH i niczego nie dowodzić.
        with tempfile.TemporaryDirectory() as home:
            env = sanitized_env(home)
            for tool in FORGE_TOOLS:
                self.assertIsNone(shutil.which(tool, path=env["PATH"]), f"{tool} nadal w PATH")
            self.assertFalse((Path(home) / ".claude/skills/memory").exists())
            self.assertFalse((Path(home) / ".codex/skills/memory").exists())


class ExternalSourcesOptionalTests(unittest.TestCase):
    def test_external_sources_have_unavailable_mode(self):
        # Każdy skill i komenda z odwołaniem do memory albo forge ma jawny tryb źródeł niedostępnych.
        checked = []
        for runtime, spec in runtime_specs():
            for template_rel, _ in spec["files"]:
                if not template_rel.endswith(".md") or template_rel.endswith(("README.md", "README.pl.md")):
                    continue
                out = render.render_one(template_rel, spec["placeholders"], runtime)
                if not EXTERNAL_SOURCE_RE.search(out):
                    continue
                checked.append(f"{runtime}:{template_rel}")
                self.assertIn(UNAVAILABLE_MARKER, out, f"{runtime}: {template_rel} bez trybu źródeł niedostępnych")
        # Strażnik przed pustym przebiegiem: dziś odwołuje się intention-hardening w obu runtime'ach.
        self.assertIn("claude:skills/intention-hardening/SKILL.md", checked)
        self.assertIn("codex:skills/intention-hardening/SKILL.md", checked)

    def test_intention_hardening_unavailable_mode_contract(self):
        for runtime, spec in runtime_specs():
            out = render.render_one("skills/intention-hardening/SKILL.md", spec["placeholders"], runtime)
            mode = out.split("Sources unavailable mode:")[1].split("### 4.")[0]
            for phrase in (
                "this plugin depends on nothing outside itself",
                "optional sources, never prerequisites",
                "the `forge` command is not on `PATH`, or the call fails or is refused",
                "do not retry, install, or work around the missing source",
                "record " + UNAVAILABLE_MARKER + " in the output, naming the missing source",
                "continue on local sources",
                "every other step runs unchanged",
            ):
                self.assertIn(phrase, mode, f"{runtime}: brak frazy trybu: {phrase}")
            output = out.split("## Output")[1]
            self.assertIn(UNAVAILABLE_MARKER + " with the missing source", output, runtime)


class HelperStandaloneTests(unittest.TestCase):
    def _run(self, helper_dir: Path, cwd: str, env: dict, *args: str) -> subprocess.CompletedProcess:
        proc = subprocess.run(
            [sys.executable, str(helper_dir / "adhoc_sdlc.py"), *args],
            cwd=cwd, env=env, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, f"{helper_dir.parent.parent.parent.name}: {args[0]}: {proc.stderr}")
        return proc

    def test_helper_full_cycle_without_forge_and_memory(self):
        for helper_dir in HELPER_DIRS:
            with self.subTest(helper=str(helper_dir)), tempfile.TemporaryDirectory() as tmp:
                home = os.path.join(tmp, "home")
                work = os.path.join(tmp, "work")
                os.makedirs(home)
                os.makedirs(work)
                env = sanitized_env(home)
                name = ["--name", "standalone-check", "--title", "Standalone check"]
                self._run(helper_dir, work, env, "plan", *name, "--project", "demo", "--keywords", "standalone")
                self._run(helper_dir, work, env, "execute", *name, "--task-add", "Verify standalone run",
                          "--decision", "added during the standalone test")
                self._run(helper_dir, work, env, "execute", *name, "--task", "T1", "--task-status", "in_progress")
                self._run(helper_dir, work, env, "execute", *name, "--task", "T1", "--append", "step done",
                          "--verification", "standalone ok", "--command", "pytest")
                self._run(helper_dir, work, env, "execute", *name, "--task", "T1", "--task-status", "done")
                tasks = json.loads(self._run(helper_dir, work, env, "tasks", "--name", "standalone-check").stdout)
                self.assertEqual([t["status"] for t in tasks["items"]], ["done"])
                self._run(helper_dir, work, env, "handoff", *name)
                listing = json.loads(self._run(helper_dir, work, env, "list").stdout)
                self.assertTrue(listing, "list: pusty wynik")
                self._run(helper_dir, work, env, "pack", "--intent", "resume", "--keywords", "standalone")
                found = self._run(helper_dir, work, env, "search", "--format", "json", "standalone").stdout
                self.assertIn("standalone-check", found)
                self._run(helper_dir, work, env, "config", "--get-modes")

    def test_helper_uses_stdlib_only_and_no_processes(self):
        allowed_local = {"adhoc_sdlc", "sdlc_doc"}
        banned_calls = {("os", "system"), ("os", "popen"), ("os", "execv"), ("os", "execvp"), ("os", "spawnv")}
        for helper_dir in HELPER_DIRS:
            for name in ("adhoc_sdlc.py", "sdlc_doc.py"):
                tree = ast.parse((helper_dir / name).read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                        for module in modules:
                            top = module.split(".")[0]
                            self.assertNotEqual(top, "subprocess", f"{helper_dir}/{name}: import subprocess")
                            self.assertTrue(top in sys.stdlib_module_names or top in allowed_local or top == "__future__",
                                            f"{helper_dir}/{name}: import spoza stdlib: {module}")
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                        self.assertNotIn((node.value.id, node.attr), banned_calls, f"{helper_dir}/{name}: {node.value.id}.{node.attr}")


if __name__ == "__main__":
    unittest.main()
