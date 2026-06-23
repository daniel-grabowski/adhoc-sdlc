# Współtworzenie

*[English](CONTRIBUTING.md) · Polski*

Repozytorium jest jedynym źródłem prawdy dla pluginu `adhoc-sdlc` oraz skilli `adhoc-sdlc`, `cove` i `temper`. Edytuj tutaj, testuj, potem publikuj. Nie edytuj zainstalowanych kopii w `~/.claude` ani `~/.codex` i nie kopiuj ich z powrotem; to rozdziela źródło i pozwala wariantom się rozjechać.

## Środowiska

Claude Code jest pakowany pod `claude/`; Codex jest pakowany jako publikowany plugin pod `plugins/adhoc-sdlc/`. Oba warianty są generowane z jednego źródła (`templates/` + `runtimes/<rt>.json`) przez `tools/render.py`. Ten generowany zestaw obejmuje teraz przegląd `README.md`/`README.pl.md` każdego skilla, więc edytuj je pod `templates/skills/<skill>/` i przerenderuj; nigdy nie edytuj ich ręcznie pod `claude/` ani `plugins/`. Planowany wariant `antigravity/` nadal jest placeholderem roadmapy. Helper w Pythonie pod `scripts/` jest wspólny, więc zmiana helpera musi trafić do każdego dostarczanego wariantu runtime.

## Konfiguracja lokalna (owner)

Dwie role naraz:

- Rozwój: ładuj plugin wprost z checkoutu, żeby edycje działały na żywo.
  - Skills-directory plugin (raz na zawsze): podlinkuj korzeń pluginu pod katalog skilli, na przykład `ln -s "$PWD/claude" ~/.claude/skills/adhoc-sdlc`. Ładuje się w następnej sesji jako `adhoc-sdlc@skills-dir`, w miejscu. Edycje `SKILL.md` działają od razu; zmiany komend lub skryptów wymagają `/reload-plugins`.
  - Albo per uruchomienie: `claude --plugin-dir ./claude`.
- Release: marketplace na GitHub (`.claude-plugin/marketplace.json`) obsługuje pozostałych. Nie instaluj go dodatkowo z marketplace na maszynie deweloperskiej, bo dwie kopie będą walczyć o `/adhoc-sdlc:*`.

Dev-symlink to teraz sam `~/.claude/skills/adhoc-sdlc`. Nie kładź obok drugiej kopii (instalacji pluginu z marketplace ani osobnego, ręcznie zainstalowanego `~/.claude/commands/adhoc-sdlc`), bo dwie kopie będą walczyć o `/adhoc-sdlc:*`.

Checkout jest relokowalny: trzymaj go gdziekolwiek (na przykład pod wspólnym drzewem `projects/harness/` z innym oprzyrządowaniem agentowym). Nic w repo nie zaszywa jego ścieżki - helper jest cwd-relative, komendy rozwiązują `${CLAUDE_PLUGIN_ROOT}`, narzędzia build pod `tools/` rozwiązują ścieżki względem siebie, a symlink używa `$PWD`. Po przeniesieniu checkoutu przepnij dev-symlink z nowej lokalizacji: `rm ~/.claude/skills/adhoc-sdlc && ln -s "$PWD/claude" ~/.claude/skills/adhoc-sdlc`, potem `/reload-plugins`. Git i jego remote pozostają nienaruszone (katalog `.git` wędruje razem z checkoutem).

## Pętla dev

1. Edytuj prompty w `templates/` (jedyne źródło) albo wspólny helper w `claude/skills/adhoc-sdlc/scripts`.
2. Renderuj: `python3 tools/render.py`, potem `python3 tools/render.py --check` (bramka driftu). Nie edytuj ręcznie generowanych plików w `claude/` ani `plugins/`; ostrzega o tym nagłówek `GENERATED`.
3. Zsynchronizuj helper i testuj: `tools/sync-helper.sh` kopiuje `scripts/*.py` z wariantu Claude do wariantu pluginu Codex, potem uruchom `python3 -m pytest -q` w `claude/skills/adhoc-sdlc/scripts` i w `plugins/adhoc-sdlc/skills/adhoc-sdlc/scripts` oraz `python3 -m pytest tools -q`. Sprawdź komendy przez `claude --plugin-dir ./claude`.
4. Podbij wersję w `claude/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` i `plugins/adhoc-sdlc/.codex-plugin/plugin.json`, gdy zmieniają się publiczne metadane lub zachowanie pluginu. Wersje Claude muszą się zgadzać: `claude plugin validate ./claude` i `claude plugin validate .` sprawdzają manifesty, a `claude plugin tag` sprawdza zgodność obu wersji przy release.
5. Commit i push.
6. Konsumenci pobierają release przez `/plugin update adhoc-sdlc` (w razie potrzeby najpierw `/plugin marketplace update adhoc-sdlc`).

## Wspólny helper

`tools/sync-helper.sh` kopiuje helper z `claude/skills/adhoc-sdlc/scripts/` (kopia kanoniczna) do `plugins/adhoc-sdlc/skills/adhoc-sdlc/scripts/`. Duplikacja jest celowa: pakiety pluginów nie mogą polegać na plikach spoza własnego drzewa instalacji, więc helper musi fizycznie leżeć w każdym wariancie runtime. Po każdej zmianie helpera uruchom skrypt i odpal testy w każdym dostarczanym wariancie, zanim zacommitujesz.
