# adhoc-sdlc

*[English](README.md) · Polski*

## Co to jest

`adhoc-sdlc` to mały zestaw SDLC dla agentów programujących AI. Dostarcza trzy skille: `adhoc-sdlc` do lekkiej pracy implementacyjnej z trwałym planem i dziennikiem wykonania, `cove` do Chain-of-Verification przed wypuszczeniem twierdzeń faktograficznych do użytkownika oraz `temper` do hartowania strategii planu pod kątem trybów awarii przed wykonaniem.

## Dlaczego

AI koduje szybko, ale szybkość bez zapisu decyzji jest krucha. To repo daje Claude Code i Codex wspólny workflow do planowania, weryfikacji, dziennikowania, wznawiania i przekazywania małych zadań bez zamieniania każdej zmiany w formalne issue.

## Harness, nie vibe-coding

Artykuł Addy'ego Osmaniego [The New Software Lifecycle](https://addyosmani.com/blog/new-sdlc-vibe-coding/) i stojący za nim [whitepaper Google](https://www.kaggle.com/whitepaper-the-new-SDLC-with-vibe-coding) ujmują agenta jako model plus harness. Model to jedno wejście; harness to instrukcje, narzędzia, reguły kontekstu i weryfikacja owinięte wokół niego. Zgrubny podział z artykułu to 10% model, 90% harness. Ten sam tekst stawia linię między vibe-codingiem a inżynierią w jednym miejscu: przy weryfikacji. Kod, który tylko wygląda na działający, to vibe-coding; kod, którego wyniki są sprawdzane, to inżynieria.

To repo jest harnessem, nie modelem. `adhoc-sdlc` to zapis: potwierdzony plan i dziennik, które przeżywają pauzę albo reset kontekstu, więc praca zostaje sprawdzalna, zamiast istnieć tylko w logu czatu. `cove` to weryfikacja: przepuszcza szkic przez niezależne pytania, zanim jakiekolwiek twierdzenie trafi do Ciebie. `temper` to próba wytrzymałości: poluje na tryby awarii planu, zanim staną się kodem. Skille ładują się też tak, jak zaleca artykuł: trochę metadanych z góry, a pełne instrukcje dopiero, gdy zadanie pasuje (progressive disclosure), więc kontekst, za który płacisz w każdej turze, zostaje mały.

Nic z tego nie czeka na lepszy model. To konfiguracja, którą możesz dopiąć już dziś, recenzowana i wersjonowana jak reszta kodu.

## Skille

### adhoc-sdlc

Co to jest: lekki cykl SDLC dla małej, doraźnej pracy implementacyjnej. 

#### Dlaczego

Nawet szybka poprawka ma mieć potwierdzony plan, checklistę inżynierską, opcjonalne bramy weryfikacyjne i wznawialny dziennik wykonania pod `./adhoc-sdlc`. Szczegóły w [claude/skills/adhoc-sdlc/README.pl.md](claude/skills/adhoc-sdlc/README.pl.md).

<p align="center">
  <img src="assets/adhoc-sdlc.png" alt="adhoc-sdlc" width="320">
</p>

### CoVe

#### Po co? 

Chain-of-Verification do pracy faktograficznej. 

#### Dlaczego 

Wymusza przejście od szkicu przez niezależne pytania weryfikacyjne, żeby finalna odpowiedź zawierała tylko fakty potwierdzone albo jawnie oznaczone jako niepewne. 
Pluginy Claude Code i Codex dostarczają to jako skill `cove`. Szczegóły w [claude/skills/cove/README.pl.md](claude/skills/cove/README.pl.md).

### Temper

#### Po co?

Hartowanie strategii planu, architektury i kierunku implementacji.

#### Dlaczego

Uruchamia skoncentrowany przebieg trybów awarii po weryfikacji faktów, a przed wykonaniem, żeby luki zostały zamknięte albo świadomie zaakceptowane, zanim staną się kodem. Dostarczany jako skill `temper` oraz jako bramka `strategy-temper` w `/adhoc-sdlc:plan`. Szczegóły w [claude/skills/temper/README.pl.md](claude/skills/temper/README.pl.md).

## Jak to działa razem

Trzy skille to jeden przepływ: zaplanuj zmianę, zweryfikuj fakty, na których się opiera, zahartuj strategię, a potem wykonaj z dziennikiem, który da się wznowić albo przekazać. `cove` i `temper` to bramki opcjonalne, wybierane per zadanie na liście trybów planu.

```mermaid
flowchart LR
    cove{{"cove: weryfikacja faktów"}} -.->|opcjonalnie| plan
    temper{{"temper: hartowanie strategii"}} -.->|opcjonalnie| plan
    plan(["/adhoc-sdlc:plan"]) --> exec(["/adhoc-sdlc:exec"])
    exec --> ecove{{"weryfikacja wykonania"}}
    exec -->|reset kontekstu| handoff(["/adhoc-sdlc:handoff"])
    handoff -.->|"/adhoc-sdlc:resume"| exec
    plan ==> disk[("plan + dziennik<br/>na dysku")]
    exec ==> disk
    disk -.->|tylko odczyt| history(["/adhoc-sdlc:history"])

    classDef cmd fill:#e3f2fd,stroke:#1565c0,color:#0d2b45
    classDef gate fill:#fff3cd,stroke:#b8860b,color:#3d2f00
    classDef store fill:#eceff1,stroke:#37474f,color:#1c2833
    class plan,exec,handoff,history cmd
    class cove,temper,ecove gate
    class disk store
```

Znaczenie niosą kształty: zaokrąglony to komenda, sześciokąt to opcjonalna bramka (`cove` i `temper` przed zapisem planu, `cove` wykonania przed zamknięciem wykonania), a walec to zapis na dysku. Krawędzie ciągłe to główny przepływ, kropkowane to opcjonalne albo tylko do odczytu, a grube zapisują plan i dziennik, które przeżywają reset kontekstu. Ten most budują `handoff` i `resume`.

## Układ

Jeden katalog na środowisko agenta, każdy spakowany w natywnym formacie tego środowiska. Helper w Pythonie jest wspólny dla wariantów i zduplikowany tam, gdzie plugin musi być samowystarczalnym katalogiem.

```
.claude-plugin/marketplace.json   wpis marketplace Claude Code
.agents/plugins/marketplace.json  wpis marketplace Codex
claude/                           plugin Claude Code: adhoc-sdlc + cove + temper
  .claude-plugin/plugin.json
  skills/adhoc-sdlc/
  skills/cove/
  skills/temper/
  commands/                       /adhoc-sdlc:plan :exec :handoff :resume :history
plugins/adhoc-sdlc/            plugin Codex: adhoc-sdlc + cove + temper
  .codex-plugin/plugin.json
  skills/adhoc-sdlc/
  skills/cove/
  skills/temper/
antigravity/                      plany: format rozszerzenia do ustalenia
```

W Claude Code komendy leżą w osobnym drzewie `commands/` (z namespace pluginu `/adhoc-sdlc:*`); w Codex leżą wewnątrz skilla. Wariant Claude wskazuje skrypty przez `${CLAUDE_PLUGIN_ROOT}`, a wariant Codex rozwiązuje skrypty względem katalogu zainstalowanego skilla.

## Instalacja

### Claude Code (plugin)

Z marketplace:

```
/plugin marketplace add daniel-grabowski/adhoc-sdlc
/plugin install adhoc-sdlc@adhoc-sdlc
```

Do lokalnej pracy na checkoucie załaduj katalog pluginu wprost:

```
claude --plugin-dir ./claude
```

### Codex (plugin)

Zalecana publiczna instalacja z GitHuba:

```
codex plugin marketplace add daniel-grabowski/adhoc-sdlc --ref main
codex plugin add adhoc-sdlc@adhoc-sdlc
```

To nie używa lokalnego checkoutu. Codex pobiera marketplace `adhoc-sdlc` z GitHuba, a potem rozwiązuje plugin przez `.agents/plugins/marketplace.json` z pobranego repo. Wpis marketplace celowo używa relatywnej ścieżki lokalnej:

```json
"source": {
  "source": "local",
  "path": "./plugins/adhoc-sdlc"
}
```

Ta ścieżka jest lokalna względem pobranej migawki marketplace, nie względem `/home/.../adhoc-sdlc` na Twojej maszynie.

Jeśli wcześniej dodałeś marketplace z lokalnego checkoutu, przełącz go na GitHub:

```
codex plugin remove adhoc-sdlc@adhoc-sdlc
codex plugin marketplace remove adhoc-sdlc
codex plugin marketplace add daniel-grabowski/adhoc-sdlc --ref main
codex plugin add adhoc-sdlc@adhoc-sdlc
```

Sprawdzenie źródła:

```
codex plugin marketplace list --json
codex plugin list --marketplace adhoc-sdlc --available --json
```

Do lokalnej pracy na checkoucie:

```
codex plugin marketplace add .
codex plugin add adhoc-sdlc@adhoc-sdlc
```

### Antigravity CLI

W planach, najpewniej jako skill (jak wariant Codex), nie plugin. Dokładny format nie został tu jeszcze ustalony; aktualny status w [antigravity/README.md](antigravity/README.md).

## Licencja

MIT. Zobacz [LICENSE](LICENSE).

## Autor

Daniel Grabowski <daniel.grabowski@faktoria.io>
