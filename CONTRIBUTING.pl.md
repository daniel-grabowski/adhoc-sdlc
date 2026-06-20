# Współtworzenie

*[English](CONTRIBUTING.md) · Polski*

Repozytorium jest jedynym źródłem prawdy dla narzędzia `adhoc-sdlc`. Edytuj tutaj, testuj, potem publikuj. Nie edytuj zainstalowanych kopii w `~/.claude` ani `~/.codex` i nie kopiuj ich z powrotem; to rozdziela źródło i pozwala wariantom się rozjechać.

## Środowiska

Tylko Claude Code ma system pluginów. Wariant `codex/` to zwykły skill, a planowany wariant `antigravity/` najpewniej też nim będzie. Helper w Pythonie pod `scripts/` jest wspólny, więc zmiana helpera musi trafić do każdego wariantu.

## Konfiguracja lokalna (owner)

Dwie role naraz:

- Rozwój: ładuj plugin wprost z checkoutu, żeby edycje działały na żywo.
  - Skills-directory plugin (raz na zawsze): podlinkuj korzeń pluginu pod katalog skilli, na przykład `ln -s "$PWD/claude" ~/.claude/skills/faktoria-sdlc`. Ładuje się w następnej sesji jako `adhoc-sdlc@skills-dir`, w miejscu. Edycje `SKILL.md` działają od razu; zmiany komend lub skryptów wymagają `/reload-plugins`.
  - Albo per uruchomienie: `claude --plugin-dir ./claude`.
- Release: marketplace na GitHub (`.claude-plugin/marketplace.json`) obsługuje pozostałych. Nie instaluj go dodatkowo z marketplace na maszynie deweloperskiej, bo dwie kopie będą walczyć o `/adhoc-sdlc:*`.

Trzymaj stary, ręcznie zainstalowany skill z dala: obok pluginu nie może być `~/.claude/skills/adhoc-sdlc` ani `~/.claude/commands/adhoc-sdlc`.

## Pętla dev

1. Edytuj w `claude/skills/adhoc-sdlc` albo `claude/commands`.
2. Testuj: `cd claude/skills/adhoc-sdlc/scripts && python3 -m pytest -q` i sprawdź komendy przez `claude --plugin-dir ./claude`.
3. Zsynchronizuj wspólny helper: `tools/sync-helper.sh` kopiuje `scripts/*.py` z wariantu Claude do wariantu Codex. Potem `cd codex/skills/adhoc-sdlc/scripts && python3 -m pytest -q`.
4. Podbij wersję w `claude/.claude-plugin/plugin.json` oraz w odpowiednim wpisie `.claude-plugin/marketplace.json`. Muszą się zgadzać: `claude plugin validate ./claude` i `claude plugin validate .` sprawdzają manifesty, a `claude plugin tag` sprawdza zgodność obu wersji przy release.
5. Commit i push.
6. Konsumenci pobierają release przez `/plugin update adhoc-sdlc` (w razie potrzeby najpierw `/plugin marketplace update faktoria-sdlc`).

## Wspólny helper

`tools/sync-helper.sh` kopiuje helper z `claude/skills/adhoc-sdlc/scripts/` (kopia kanoniczna) do `codex/skills/adhoc-sdlc/scripts/`. Duplikacja jest celowa: plugin Claude nie może referować plików spoza własnego katalogu, więc helper musi fizycznie leżeć w każdym wariancie. Po każdej zmianie helpera uruchom skrypt i odpal testy w obu wariantach, zanim zacommitujesz.
