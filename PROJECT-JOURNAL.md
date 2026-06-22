# Dziennik projektu adhoc-sdlc

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
