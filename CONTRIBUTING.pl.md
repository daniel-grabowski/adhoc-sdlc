# Współtworzenie

*[English](CONTRIBUTING.md) · Polski*

Repozytorium jest jedynym źródłem prawdy dla pluginu `adhoc-sdlc` oraz skilli `adhoc-sdlc` i `cove`. Edytuj tutaj, testuj, potem publikuj. Nie edytuj zainstalowanych kopii w `~/.claude` ani `~/.codex` i nie kopiuj ich z powrotem; to rozdziela źródło i pozwala wariantom się rozjechać.

## Środowiska

Claude Code jest pakowany pod `claude/`. Codex ma zwykły skill kompatybilnościowy pod `codex/` oraz publikowany plugin pod `plugins/adhoc-sdlc/`. Planowany wariant `antigravity/` nadal jest placeholderem roadmapy. Helper w Pythonie pod `scripts/` jest wspólny, więc zmiana helpera musi trafić do każdego dostarczanego wariantu runtime.

## Konfiguracja lokalna (owner)

Dwie role naraz:

- Rozwój: ładuj plugin wprost z checkoutu, żeby edycje działały na żywo.
  - Skills-directory plugin (raz na zawsze): podlinkuj korzeń pluginu pod katalog skilli, na przykład `ln -s "$PWD/claude" ~/.claude/skills/adhoc-sdlc`. Ładuje się w następnej sesji jako `adhoc-sdlc@skills-dir`, w miejscu. Edycje `SKILL.md` działają od razu; zmiany komend lub skryptów wymagają `/reload-plugins`.
  - Albo per uruchomienie: `claude --plugin-dir ./claude`.
- Release: marketplace na GitHub (`.claude-plugin/marketplace.json`) obsługuje pozostałych. Nie instaluj go dodatkowo z marketplace na maszynie deweloperskiej, bo dwie kopie będą walczyć o `/adhoc-sdlc:*`.

Dev-symlink to teraz sam `~/.claude/skills/adhoc-sdlc`. Nie kładź obok drugiej kopii (instalacji pluginu z marketplace ani osobnego, ręcznie zainstalowanego `~/.claude/commands/adhoc-sdlc`), bo dwie kopie będą walczyć o `/adhoc-sdlc:*`.

## Pętla dev

1. Edytuj w `claude/skills/adhoc-sdlc` albo `claude/commands`.
2. Testuj: `cd claude/skills/adhoc-sdlc/scripts && python3 -m pytest -q` i sprawdź komendy przez `claude --plugin-dir ./claude`.
3. Zsynchronizuj wspólny helper: `tools/sync-helper.sh` kopiuje `scripts/*.py` z wariantu Claude do wariantów Codex. Potem `cd codex/skills/adhoc-sdlc/scripts && python3 -m pytest -q`.
4. Podbij wersję w `claude/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` i `plugins/adhoc-sdlc/.codex-plugin/plugin.json`, gdy zmieniają się publiczne metadane lub zachowanie pluginu. Wersje Claude muszą się zgadzać: `claude plugin validate ./claude` i `claude plugin validate .` sprawdzają manifesty, a `claude plugin tag` sprawdza zgodność obu wersji przy release.
5. Commit i push.
6. Konsumenci pobierają release przez `/plugin update adhoc-sdlc` (w razie potrzeby najpierw `/plugin marketplace update adhoc-sdlc`).

## Wspólny helper

`tools/sync-helper.sh` kopiuje helper z `claude/skills/adhoc-sdlc/scripts/` (kopia kanoniczna) do `codex/skills/adhoc-sdlc/scripts/` i `plugins/adhoc-sdlc/skills/adhoc-sdlc/scripts/`. Duplikacja jest celowa: pakiety pluginów nie mogą polegać na plikach spoza własnego drzewa instalacji, więc helper musi fizycznie leżeć w każdym wariancie runtime. Po każdej zmianie helpera uruchom skrypt i odpal testy w każdym dostarczanym wariancie, zanim zacommitujesz.
