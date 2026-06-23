# Dziennik projektu adhoc-sdlc

## 2026-06-23 - Pełna dokumentacja po konsolidacji 0.4.0: README skilli do generatora, mermaid, walidacja humanizer

Status: przygotowane lokalnie w tym commicie
Zakres: doprowadzenie całej dokumentacji do stanu zgodnego z rzeczywistością po konsolidacji generatora (0.4.0, trzy skille); README skilli przeniesione do generatora (jedno źródło, oba warianty); diagramy mermaid dla przepływów; walidacja stylu skillem `humanizer` dla PL i EN. Prowadzone przez dziennik adhoc-sdlc (`plan`/`execute-2026-06-23-docs-full-consolidation`).

### Przyczyna

Po konsolidacji 0.4.0 (trzy skille: `adhoc-sdlc`, `cove`, `temper`) dokumentacja była częściowo nieaktualna, częściowo niespójna, miejscami sprzeczna sama ze sobą: README mówiły o „dwóch skillach" (brak temper), `cove` nie miał README user-facing, README skilli były utrzymywane niejednolicie (adhoc-sdlc ręczny tylko w `claude/`, temper generowany i PL-only, cove brak), `antigravity/README.md` deklarował „Shipped and verified" sprzecznie z `active=false`, a README temper opisywał nieistniejącą komendę `/temper`.

### Co się zmieniło

- Generator: nowy placeholder `{{ASSETS}}` (prefiks ścieżki do `assets/`, różny per runtime, bo README skilli leżą na różnej głębokości): `claude.json` -> `../../../assets`, `codex.json` -> `../../../../assets`, `antigravity.json` -> `TODO-confirm` (`active=false`, render pomija). `render.py` bez zmian (obsługuje nowy placeholder i nowe pary `files` generycznie).
- README skilli wciągnięte do `templates/skills/` i generowane do OBU wariantów (EN+PL, nagłówek GENERATED): `adhoc-sdlc/README.md` + `README.pl.md` (lista trybów Phase 0 uzupełniona do pełnych 6, w tym strategy temper; obraz przez `{{ASSETS}}`; sekcja „Related skills"), `cove/README.md` + `README.pl.md` (NOWE, pierwsze README user-facing dla cove), `temper/README.md` (PL -> EN kanon) + `README.pl.md` (NOWY). Usunięto opis nieistniejącej komendy `/temper` (inwokacja jako skill albo bramka `strategy-temper`).
- Diagramy mermaid (8 sztuk w 5 miejscach): główny README (przepływ adhoc-sdlc EN+PL), `struktura-repozytorium.md` (pipeline generatora), `cove/README` (proces CoVe EN+PL), `temper/README` (kolejność w Harness EN+PL), `adhoc-sdlc/README` (przepływ sesji).
- Dokumenty repo-level: `README.md`/`README.pl.md` („dwa/two" -> trzy skille, sekcja `### Temper`, blok Layout z `skills/temper/`), `CONTRIBUTING.md`/`.pl.md` (lista trzech skilli; nota, że README skilli są generowane), `docs/struktura-repozytorium.md` (drzewa `templates/` i wariantów z README skilli, wiersz `{{ASSETS}}` w tabeli placeholderów, sekcja 9 długu), `antigravity/README.md` („Shipped and verified" -> „experimental (roadmap)", zgodnie z `active=false`).
- Walidacja humanizer (12 dokumentów, każdy w swoim języku, tryb `--auto`): 9x bez zmian (proza już zwięzła), 3 chirurgiczne poprawki stylu (nie faktów): temper PL anglicyzm „Inwokujesz" -> „Wywołujesz", struktura PL pleonazm „Cel docelowy" -> „Cel" i aforyzm „serce repo" -> „główny mechanizm repo", antigravity EN promocyjny slop (100% agnostic, seamlessly, simply, safely, instantly, intelligently) -> rzeczowa proza.

### Czego nie zmieniono

- Helper Python (`adhoc_sdlc.py`, `sdlc_doc.py`) i jego testy, format `plan-*`/`execute-*`, manifesty i wersja pluginu (zmiana docs + generator, bez bumpa: pozostaje 0.4.0).
- `antigravity.json` nadal `active=false` (narzędzia `TODO-confirm`, zakaz zgadywania); `docs/struktura-repozytorium.md` pozostaje PL (rozstrzygnięty konflikt: polityka językowa „architektura wewnętrzna = PL" ma pierwszeństwo nad wzmianką o wersji EN).

### Weryfikacja

- `python3 tools/render.py` -> „rendered 35 files for: claude, codex"; `--check` -> „check OK: claude, codex up to date" (zero drift).
- 0 placeholderów `{{` w `claude/` i `plugins/`; 0 „two skills"/„dwa skille" w README; `temper` obecny w sekcji Skills i w Layout obu README; JSON 3/3 parsowalne.
- Ścieżki obrazu per wariant: `claude/.../README.md` -> `../../../assets/adhoc-sdlc.png`, `plugins/.../README.md` -> `../../../../assets/adhoc-sdlc.png` (oba wskazują `assets/` w roocie).
- Mermaid: 8/8 diagramów `valid:true` (Mermaid MCP).
- `pytest`: helper Claude 95 passed, helper plugin Codex 95 passed, generator `tools` 9 passed.
- Spójność statusu antigravity: główny README („roadmap"/„Planned") i `antigravity/README.md` („experimental (roadmap)") zgodne; brak deklaracji „shipped" dla integracji Antigravity.



Status: przygotowane lokalnie w tym commicie, push na main
Zakres: konsolidacja generatora tak, by oba realne warianty (Claude Code i plugin Codex) wraz ze skillami `cove` i `temper` powstawały z jednego źródła (`templates/` + `runtimes/`); usunięcie legacy wariantu `codex/`; bump 0.3.4 -> 0.4.0

### Przyczyna

`cove` i `temper` były utrzymywane podwójnie (`claude/` i `plugins/`, treść identyczna), wariant `codex/` był martwym duplikatem „plain skill" bez `cove`/`temper`, a generator produkował tylko `claude/`. Cel: maszyna z jednym źródłem, zero ręcznie utrzymywanej prozy dystrybucyjnej, instalacja i aktualizacja z GitHuba.

### Co się zmieniło

- `templates/`: dodano `skills/cove` i `skills/temper` (kanon, identyczne z dotychczasowymi wariantami) oraz `skills/cove/agents/openai.yaml` (metadane Codex).
- Placeholdery ścieżek rozbite: `{{PLUGIN_ROOT}}/skills/adhoc-sdlc` -> `{{SKILL_HOME}}`, `{{PLUGIN_ROOT}}/commands` -> `{{COMMANDS_HOME}}` (różny layout komend: Claude w roocie pluginu, Codex w skillu).
- Neutralizacja gramatyki dla generowania prozy Codex: bramka modów bez twardego „four questions" (warunkowe pakowanie bramek w multi-select); `{{ASK}}` sprowadzone do jednej roli gramatycznej; nowe placeholdery `{{SUBAGENT_VIA}}` (pusty dla Codex), `{{ASK_NOTE}}`, `{{SKILL_HOME_NOTE}}` (puste dla Claude). To lekko przeredagowało shipowaną prozę Claude (znaczenie i jawne `AskUserQuestion` zachowane, egzekwowane testem regresji).
- `tools/render.py`: nagłówek zależny od rozszerzenia (`.yaml`/`.yml` -> `#`, reszta -> `<!-- -->`), żeby generować `openai.yaml` bez psucia YAML; +2 testy w `test_render.py`.
- `runtimes/claude.json`: nowy zestaw placeholderów + `files` dla `cove`/`temper`. `runtimes/codex.json`: `active=true`, retarget na `plugins/adhoc-sdlc/`, frazy opisowe, `files` dla `cove` (+`openai.yaml`) i `temper`. `runtimes/antigravity.json`: klucze placeholderów wyrównane do nowego zestawu (wartości nadal `TODO-confirm`, `active=false`).
- Usunięto `codex/` (legacy). `sync-helper.sh`: cel tylko `plugins/`. `README`/`CONTRIBUTING` (EN+PL) i `docs/struktura-repozytorium.md` zaktualizowane.
- Bump 0.3.4 -> 0.4.0 w 3 manifestach.

### Czego nie zmieniono

- Antigravity nadal `active=false` (narzędzia nieustalone, zakaz zgadywania); reużywa `plugins/`.
- Format `plan-*`/`execute-*`, API helpera, manifesty marketplace (źródła `./claude` i `./plugins/adhoc-sdlc`).
- `README*.md` skilla Claude (poza generatorem).

### Weryfikacja

- `python3 tools/render.py --check` -> „check OK: claude, codex up to date" (zero drift).
- `pytest`: helper Claude 95 passed, helper plugin Codex 95 passed, generator `tools` 9 passed (z nowymi testami nagłówka; YAML przeszedł).
- 0 placeholderów `{{...}}` w `claude/` i `plugins/`; 0 `PLUGIN_ROOT`/`SUBAGENT_TOOL` w źródłach; `openai.yaml` z nagłówkiem `# GENERATED`; wersja 0.4.0 w 3 manifestach, 0.3.4 = 0; JSON 7/7 parsowalne.
- `git diff claude/` minimalny (reword słowny; `exec.md` i `handoff.md` bez zmian bajtowych).

## 2026-06-22 - Generator build-time: deterministyczne wiązanie akcji z narzędziami

Status: przygotowane lokalnie w tym commicie
Zakres: przywrócenie determinizmu wyboru narzędzi w promptach przez generator (templates/ + runtimes/<rt>.json -> render), plus config domyślnych trybów; w tej iteracji renderowany wariant Claude

### Przyczyna

Commit `70d56b1` zamienił jawne nazwy narzędzi na opisy akcji (`AskUserQuestion` -> „structured-question prompt", `Agent`/`Explore` -> „read-only subagent", `TodoWrite`/`update_plan` -> „native task-tracking tool"). Nazwa narzędzia w prompcie to jedyny twardy wyzwalacz; opis akcji jest sygnałem miękkim, który model realizuje tekstem albo wcale, więc zniknął mode gate i domknięcie pętli pytaniem o egzekucję. Teza commita („mapowanie zostaje przy superpowers") jest fałszywa: `using-superpowers/references/claude-code-tools.md` nie mapuje pytania do użytkownika na `AskUserQuestion`.

### Co się zmieniło

- `templates/` - neutralne źródło prozy z czterema placeholderami (`{{ASK}}`, `{{TODO}}`, `{{SUBAGENT_TOOL}}`, `{{PLUGIN_ROOT}}`), parametryzującymi tylko frazy różnicujące runtime; reszta treści 1:1 z `claude/`.
- `runtimes/claude.json` (active) plus `codex.json`/`antigravity.json` (szkielety, `active: false`). Mapowanie akcja->narzędzie per runtime. Claude: ASK=`AskUserQuestion`, TODO=`TaskCreate`/`TaskUpdate`, SUBAGENT_TOOL=`Agent` tool + `subagent_type: general-purpose`, PLUGIN_ROOT=`${CLAUDE_PLUGIN_ROOT}`.
- `tools/render.py` - renderer build-time (templates + runtimes -> warianty), nagłówek GENERATED, tryb `--check` (bramka driftu). Render Claude przywraca jawne nazwy narzędzi.
- `adhoc_sdlc.py` - subkomenda `config` + `load_config` (warstwa B): domyślne tryby z `config.json` (projekt > global > OFF), prefill mode gate; wpięte w źródle `plan` Phase 0.
- Testy: `tools/test_render.py`, `scripts/test_config.py`; `pytest.ini` rozszerzony o `tools/`. `tools/sync-helper.sh` wskazuje render jako osobny krok build.

### Czego nie zmieniono

- Render wariantów `codex/`/`plugins/` (`.md`) - zostają ręczne do czasu wypełnienia ich tabel mapowania; nadal niedeterministyczne na tych runtime. Helper `.py` nadal synchronizowany przez `sync-helper.sh`.
- Format `plan-*`/`execute-*`, manifesty, wersja pluginu (0.3.3).

### Weryfikacja

- `python3 tools/render.py --check` -> claude up to date po renderze; przed renderem DRIFT 7 plików, exit 1.
- Render idempotentny (hash H1=H2); `git diff claude/` = tylko przywrócenie nazw narzędzi + nagłówek GENERATED, treść 1:1.
- `python3 -m pytest -q` -> 102 passed.
- `bash tools/sync-helper.sh` -> 7 plików do 2 miejsc (14 kopii); `config --get-modes` działa w wariancie codex po sync.
- `grep AskUserQuestion claude/commands/plan.md` -> jawne wystąpienia w Phase 0 (mode gate) i Phase 3 (close the loop).

## 2026-06-22 - Rename: faktoria-sdlc -> adhoc-sdlc (repo, plugin, marketplace, branding)

Status: przygotowane lokalnie w tym commicie; push po przemianowaniu zdalnego repo (Część C)
Zakres: nazwa repo, pluginu, marketplace i branding zmienione z `faktoria-sdlc` na `adhoc-sdlc` we wszystkich wariantach (Claude, Codex, marketplace); bez zmian funkcjonalnych i bez bumpa wersji

### Co się zmieniło

- `git mv plugins/faktoria-sdlc plugins/adhoc-sdlc` (wariant pluginu Codex), historia zachowana.
- Manifesty: `.claude-plugin/marketplace.json` (name + opis), `.agents/plugins/marketplace.json` (name, displayName, path), `claude/.claude-plugin/plugin.json` (homepage URL), `plugins/adhoc-sdlc/.codex-plugin/plugin.json` (name, opis, homepage/repository/websiteURL, displayName, longDescription). Nazwa wyświetlana `Faktoria SDLC` -> `Ad Hoc SDLC`.
- Dokumentacja: `README.md`/`README.pl.md`, `CONTRIBUTING.md`/`CONTRIBUTING.pl.md` (w tym dev-symlink i ostrzeżenie o podwójnej instalacji), `docs/analiza-forge-init.md` (ścieżka symlinka), `tools/sync-helper.sh` (ścieżka wariantu Codex).
- Dev-symlink: docelowo `~/.claude/skills/adhoc-sdlc -> <repo>/claude` (decyzja: pełna spójność nazwy; CONTRIBUTING zaktualizowane). Namespace komend `/adhoc-sdlc:*` bierze się z `name` w `plugin.json`, nie z nazwy repo ani symlinka.
- Tytuł tego dziennika zaktualizowany do `adhoc-sdlc`.

### Czego nie zmieniono

- Email autora `daniel.grabowski@faktoria.io` (tożsamość, nie nazwa produktu) - bez zmian we wszystkich manifestach i stopkach README.
- Wersja pluginu (0.3.3) - rename nie jest zmianą funkcjonalną.
- Struktura skilli i komend (już zgodna z celem: jeden plugin, dwa skille `adhoc-sdlc` + `cove`, komendy plan/exec/handoff/resume/history) oraz helper Pythona (cwd-relative, bez zaszytych ścieżek).
- Wpisy historyczne tego dziennika (dawny remote URL, dawna nazwa pluginu, cytowany commit `5d64d2b`) - zostają jako zapis stanu z tamtego momentu.

### Operacje poza repo (Część B i C, poza tym commitem)

- Część B (użytkownik): rename zdalnego repo GitHub `faktoria-sdlc` -> `adhoc-sdlc`; `mv /home/dgrabowski/faktoria-sdlc /home/dgrabowski/adhoc-sdlc` (zalecane między sesjami, bo `mv` aktywnego katalogu zaburza CWD i klucz katalogu projektu).
- Część C (po rename): `git remote set-url origin https://github.com/daniel-grabowski/adhoc-sdlc.git`; `rm ~/.claude/skills/faktoria-sdlc && ln -s /home/dgrabowski/adhoc-sdlc/claude ~/.claude/skills/adhoc-sdlc`; `git push`; w Claude Code `/reload-plugins` i test `/adhoc-sdlc:plan`.

### Weryfikacja (Część A, przed rename)

- `bash tools/sync-helper.sh` -> 6 plików do 2 miejsc docelowych (12 kopii).
- `python3 -m py_compile` helpera (kanon Claude) -> OK.
- `pytest` w trzech wariantach (claude, codex, plugins/adhoc-sdlc) -> 87 passed każdy.
- `claude plugin validate ./claude` -> passed; `claude plugin validate .` -> passed.
- `validate_plugin.py plugins/adhoc-sdlc` -> plugin valid. Uwaga: `quick_validate.py` (per skill) nie istnieje już w toolchainie plugin-creator - walidację skilli pokrywa `validate_plugin.py`.
- grep kontrolny: `faktoria-sdlc` i `Faktoria SDLC` tylko w historycznych wpisach tego dziennika; `@faktoria.io` zachowany w 4 plikach.

## 2026-06-21 - Przepisanie README i dokumentacji: framing harness, nie vibe-coding

Status: przygotowane w tym commicie, push na `main`
Zakres: dokumentacja human-facing (root README EN/PL, README skilla adhoc-sdlc EN/PL, antigravity/README) plus `.gitignore`; bez zmian w plikach instrukcyjnych skilli i helperze

### Co się zmieniło

- Root README EN i PL dostały sekcję pozycjonującą „Harness, not vibe coding" / „Harness, nie vibe-coding" (po sekcji „Why" / „Dlaczego"), z odniesieniem do artykułu Addy'ego Osmaniego „The New Software Lifecycle" i whitepapera Google. Sekcja mapuje repo na ramy z artykułu: `adhoc-sdlc` jako trwały zapis (harness), `cove` jako weryfikacja (linia między vibe-codingiem a inżynierią), progressive disclosure skilli jako kontekst ładowany na żądanie.
- README skilla `adhoc-sdlc` EN i PL: w sekcji „Why" / „Dlaczego" wzmocniono jednym zdaniem akcent, że trwały zapis czyni pracę sprawdzalną, bez przebudowy struktury.
- `antigravity/README.md`: usunięto zduplikowany akapit placeholder (powtarzał sekcję „What"), a detal „stdlib-only Python helper" przeniesiono do „What". Plik pozostaje EN-only (roadmap).
- Prozę przepuszczono przez skill `humanizer` (PL i EN) w trybie self-audytu. Tam, gdzie tekst był już czysty (m.in. CONTRIBUTING EN/PL i większość README), nie wprowadzano kosmetycznych zmian, żeby nie ryzykować regresji w instrukcjach.
- `.gitignore`: dodano regułę `/adhoc-sdlc/`, żeby katalog roboczy SDLC (plan i dziennik tej sesji) nie trafiał do repozytorium pluginu.

### Czego nie zmieniono

- Plików instrukcyjnych agenta (`SKILL.md`, `reference.md`, `commands/*.md`) we wszystkich wariantach runtime, helpera Pythona, formatu `plan-*`/`execute-*`, manifestów i wersji pluginów. To zmiana docs-only, bez bumpa wersji (pozostaje 0.3.3).

### Weryfikacja

- `git diff --stat` -> 6 plików: `.gitignore`, `README.md`, `README.pl.md`, `antigravity/README.md`, `claude/skills/adhoc-sdlc/README.md`, `claude/skills/adhoc-sdlc/README.pl.md`.
- Skan em-dash/en-dash (`grep -P`) w zmienionych plikach docs -> brak trafień.
- Linki do źródeł potwierdzone z treści artykułu: `addyosmani.com/blog/new-sdlc-vibe-coding/` oraz `kaggle.com/whitepaper-the-new-SDLC-with-vibe-coding`.
- Zgodność dwujęzyczna: sekcja pozycjonująca EN i PL mają po trzy lustrzane akapity; nagłówki nawigacyjne EN/PL nietknięte.
- Reguły stylu PL: bez em-dash/en-dash, polskie cudzysłowy „ ", akapit = jedna linia.

## 2026-06-21 - Opisy What/Why w skillach i manifestach

Status: opublikowane na `main`
Zakres: opisy repozytorium, skill frontmatter/body, manifesty Claude/Codex, roadmap Antigravity, instrukcje contributorskie

### Co się zmieniło

- Główne README EN/PL zaczyna się od sekcji `What` / `Why` (`Co to jest` / `Dlaczego`) i opisuje dwa skille: `adhoc-sdlc` oraz `cove`.
- README skilla `adhoc-sdlc` EN/PL zaczyna się od tego samego kontekstu: co to jest i po co istnieje.
- Wszystkie `SKILL.md` dla dostarczanych wariantów (`claude`, `codex`, `plugins/faktoria-sdlc`) mają frontmatter `description` zaczynający się od `What:` i `Why:`.
- Skill `cove` w wariantach Claude i Codex ma na początku treści sekcje `## What` i `## Why`, żeby sens Chain-of-Verification był widoczny przed instrukcjami proceduralnymi.
- Manifesty pluginów Claude i Codex oraz marketplace Claude mają opisy zaczynające się od `What:` i `Why:`.
- Podbito wersje publicznych manifestów pluginów z `0.3.2` do `0.3.3`.
- `antigravity/README.md` dostał sekcje `What` i `Why`, mimo że runtime pozostaje roadmapą.
- `CONTRIBUTING` EN/PL urealniono do obecnego układu: Claude plugin, Codex plain skill, Codex plugin i roadmap Antigravity.
- `tools/sync-helper.sh` synchronizuje helper z kopii kanonicznej Claude do obu wariantów Codex (`codex/skills/...` i `plugins/faktoria-sdlc/skills/...`), zgodnie z opisem contributorskim.
- Skorygowano statusy wcześniejszych wpisów dziennika, które po commicie `b7aac5e` nadal mówiły `lokalnie przygotowane, niecommitowane`.

### Weryfikacja

- `quick_validate.py` dla `plugins/faktoria-sdlc/skills/adhoc-sdlc` -> skill valid
- `quick_validate.py` dla `plugins/faktoria-sdlc/skills/cove` -> skill valid
- `quick_validate.py` dla `codex/skills/adhoc-sdlc` -> skill valid
- `quick_validate.py` dla `claude/skills/adhoc-sdlc` -> skill valid
- `quick_validate.py` dla `claude/skills/cove` -> skill valid
- `validate_plugin.py plugins/faktoria-sdlc` -> plugin valid
- `python3 -m json.tool` dla trzech manifestów plugin/marketplace -> poprawny JSON
- `claude plugin validate ./claude` -> validation passed
- `claude plugin validate .` -> validation passed
- `./tools/sync-helper.sh` -> zsynchronizowano 6 plików Python do 2 destynacji
- `python3 -m pytest -q` -> `87 passed`

## 2026-06-21 - Publikacja pluginu Codex faktoria-sdlc z CoVe

Status: opublikowane na `main`
Commit: `5d64d2b Add Codex Faktoria SDLC plugin with CoVe`
Remote: `https://github.com/daniel-grabowski/faktoria-sdlc.git`

### Co się zmieniło

- Dodano marketplace Codex w `.agents/plugins/marketplace.json`, dzięki czemu repo może być dodane jako zdalne źródło pluginów.
- Dodano plugin Codex `plugins/faktoria-sdlc` z manifestem `.codex-plugin/plugin.json`.
- Przeniesiono i spakowano workflow `adhoc-sdlc` jako skill wewnątrz pluginu Codex.
- Dodano skill `CoVe` jako pluginowy skill `cove`, przeznaczony do Chain-of-Verification dla pracy faktograficznej.
- Zaktualizowano README po polsku i angielsku, aby publiczna instalacja prowadziła przez GitHub, a lokalny checkout był tylko wariantem developerskim.
- Dodano `pytest.ini`, aby domyślny `pytest` uruchamiał kanoniczny zestaw testów i nie kolekcjonował jednocześnie zduplikowanych kopii testów z wariantów runtime.

### Instalacja z GitHuba

Publiczna instrukcja instalacji dla użytkownika Codex:

```bash
codex plugin marketplace add https://github.com/daniel-grabowski/faktoria-sdlc.git --ref main
codex plugin add faktoria-sdlc@faktoria-sdlc
```

Po instalacji należy uruchomić nowy wątek Codex, żeby plugin i jego skille zostały załadowane.

### Weryfikacja

- `python3 -m pytest -q` -> `87 passed`
- `python3 /home/dgrabowski/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/faktoria-sdlc` -> plugin valid
- `quick_validate.py` dla `plugins/faktoria-sdlc/skills/cove` -> skill valid
- `quick_validate.py` dla `plugins/faktoria-sdlc/skills/adhoc-sdlc` -> skill valid
- `quick_validate.py` dla `codex/skills/adhoc-sdlc` -> skill valid
- `git diff --check` -> bez błędów
- `git ls-remote origin main` potwierdził commit `5d64d2bec0adc732c9fe6011c558bd719e2b0fa5` na `refs/heads/main`

### Następne kroki

- Utrzymywać ten plik jako główny dziennik decyzji i publikacji projektu.
- Przy kolejnych zmianach pluginu dopisywać nowy wpis przed commitem albo w tym samym commicie co zmiana.
- Jeżeli zmieni się publiczna instrukcja instalacji, aktualizować równocześnie README i ten dziennik.

## 2026-06-21 - Planowane CoVe gates w adhoc-sdlc dla Codex

Status: opublikowane na `main` w `b7aac5e`
Zakres: tylko warianty Codex `adhoc-sdlc`

### Co się zmieniło

- Rozszerzono Phase 0 w Codexowym `adhoc-sdlc` z trzech do pięciu trybów.
- Dodano opcjonalny tryb `plan-cove`, który weryfikuje faktyczne twierdzenia i założenia szkicu planu przed zapisem planu.
- Dodano opcjonalny tryb `execution-cove`, który weryfikuje raport wykonania przed zamknięciem execution journal jako `done`.
- Doprecyzowano, że Codex może użyć natywnego wyboru opcji, jeśli dana powierzchnia go wspiera, ale plugin nie dostarcza własnego formularza UI.
- Podbito wersję pluginu Codex `faktoria-sdlc` do `0.3.1`.

### Czego nie zmieniono

- Nie zmieniano wariantu Claude Code: `claude/skills/adhoc-sdlc`, `claude/commands` i `.claude-plugin` pozostają poza zakresem tej iteracji.
- Nie zmieniano helpera `adhoc_sdlc.py` ani formatu plików `plan-*` / `execute-*`; CoVe działa jako instrukcyjny gate agenta, a nie jako nowy format danych.

### Weryfikacja

- `quick_validate.py` dla `plugins/faktoria-sdlc/skills/adhoc-sdlc` -> skill valid
- `quick_validate.py` dla `codex/skills/adhoc-sdlc` -> skill valid
- `quick_validate.py` dla `plugins/faktoria-sdlc/skills/cove` -> skill valid
- `validate_plugin.py plugins/faktoria-sdlc` -> plugin valid
- `python3 -m pytest -q` -> `87 passed`
- `git diff --check` -> bez błędów
- `git diff --name-only -- claude .claude-plugin` -> brak zmian

## 2026-06-21 - Engineering checklist w adhoc-sdlc dla Codex

Status: opublikowane na `main` w `b7aac5e`
Zakres: tylko warianty Codex `adhoc-sdlc`

### Co się zmieniło

- Dodano krótki Engineering checklist do Codexowego `adhoc-sdlc`.
- Checklist obejmuje: KISS, YAGNI, DRY with judgment, local conventions first, separation of concerns, cohesion over cleverness, explicit contracts, testability, security/data safety oraz performance with evidence.
- W planowaniu checklist działa jako lekki filtr decyzji; agent ma wpisywać tylko konsekwencje istotne dla zadania, bez tworzenia obowiązkowego raportu z każdego punktu.
- W egzekucji final self-check ma porównać rezultat z planem i checklistą; świadome odstępstwa mają trafić do journalu jako decyzja lub weryfikacja.
- Podbito wersję pluginu Codex `faktoria-sdlc` do `0.3.2`.

### Czego nie zmieniono

- Nie zmieniano wariantu Claude Code.
- Nie dodawano nowego reference ani osobnego podręcznika zasad; checklist pozostaje krótki, żeby nie rozpychać skilla.
- Nie zmieniano helpera ani formatu planu/journalu.

### Weryfikacja

- `quick_validate.py` dla `plugins/faktoria-sdlc/skills/adhoc-sdlc` -> skill valid
- `quick_validate.py` dla `codex/skills/adhoc-sdlc` -> skill valid
- `validate_plugin.py plugins/faktoria-sdlc` -> plugin valid
- `python3 -m pytest -q` -> `87 passed`
- `git diff --check` -> bez błędów
- `git diff --name-only -- claude .claude-plugin` -> brak zmian

## 2026-06-21 - Parytet wariantu Claude Code z Codex (checklist + CoVe + skill cove)

Status: opublikowane na `main` w `b7aac5e`
Zakres: tylko wariant Claude Code (`claude/`, `.claude-plugin/marketplace.json`, root README EN/PL)

### Co się zmieniło

- Dodano Engineering checklist do `claude/skills/adhoc-sdlc/SKILL.md` (sekcja pod `## Plan file`) oraz jako lekki filtr w komendach: `plan` (Faza 1) i `exec` (final self-check + zapis świadomych odstępstw).
- Dodano bramki CoVe: Phase 0 rozszerzona z trzech do pięciu trybów (`plan-cove`, `execution-cove`), z przebiegiem `plan-cove` przed zapisem planu (`plan`) i `execution-cove` przed zamknięciem journala (`exec`).
- Adaptacja platformowa (różnica względem Codex): `AskUserQuestion` w Claude ma twardy limit czterech pytań na wywołanie, więc Phase 0 pyta czterema pytaniami - trzy toggle'e plus jedno multi-select na bramki CoVe (Plan CoVe / Execution CoVe). Sekcja `## Mode` planu i tak zapisuje pięć nazwanych trybów.
- Dodano skill `cove` (Chain-of-Verification) jako drugi skill pluginu w `claude/skills/cove/SKILL.md`, zaadaptowany z wariantu Codex (słownictwo Codex -> Claude, bez `agents/openai.yaml`).
- Podbito wersję pluginu Claude `adhoc-sdlc` do `0.3.2` (parytet z pluginem Codex) i `metadata.version` marketplace do `0.3.2`; dodano keywords `verification`, `cove`; opisy pluginu wzmiankują CoVe.
- Zaktualizowano README: root EN/PL (sekcja CoVe „Claude Code i Codex", układ z `claude/skills/cove/`) oraz skill EN/PL (pięć trybów Phase 0).
- Usunięto niedozwolony klucz `author` z frontmatter `claude/skills/adhoc-sdlc/SKILL.md` (zgodność ze specyfikacją frontmatter i parytet z Codex/`cove`).
- Dodano logo repo (`assets/adhoc-sdlc.png`, 800x800 PNG) i podpięto je w czterech README (root EN/PL + skill EN/PL) jako wyśrodkowany baner, żeby było widoczne na GitHubie.

### Czego nie zmieniono

- BEZ rename: plugin zostaje `adhoc-sdlc`, komendy `/adhoc-sdlc:*` (standardowy namespacing Claude Code = nazwa pluginu + nazwa komendy), `~/.claude/CLAUDE.md` użytkownika dalej działa.
- Nie zmieniano helpera (`adhoc_sdlc.py`, `sdlc_doc.py`) ani formatu plików `plan-*`/`execute-*`; CoVe to gate instrukcyjny agenta, nie nowy format danych. `tools/sync-helper.sh` nie uruchamiany.
- Nie zmieniano wariantów Codex (`codex/`, `plugins/faktoria-sdlc/`) ani Antigravity.
- Zachowano przewagi Claude: model routing do Sonneta w `history`/`resume`, kontrakt Stats, uwagi o plan mode, sekcje `## Note`, ostrzeżenie korpus-vs-katalog-skilla.

### Decyzja

- Klucz `author` we frontmatter `claude/skills/adhoc-sdlc/SKILL.md` był niedozwolony wg specyfikacji (dozwolone: allowed-tools, description, license, metadata, name) i został usunięty. Po usunięciu `quick_validate.py` dla obu skilli zwraca `Skill is valid!`. Tożsamość autora pozostaje w sekcji `## Author` README i w manifeście pluginu (`plugin.json`).

### Weryfikacja

- `python3 -m pytest -q` -> `87 passed` (zmiana docs-only, helper nietknięty)
- `json.load` dla `claude/.claude-plugin/plugin.json` i `.claude-plugin/marketplace.json` -> poprawny JSON
- `quick_validate.py` dla `claude/skills/cove` -> `Skill is valid!`
- `quick_validate.py` dla `claude/skills/adhoc-sdlc` -> `Skill is valid!` (po usunięciu `author`)
- `git diff --check` -> bez błędów
