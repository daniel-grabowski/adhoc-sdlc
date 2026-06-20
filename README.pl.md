# faktoria-sdlc

*[English](README.md) · Polski*

Skille SDLC dla agentów programujących AI: zaplanuj pracę, prowadź wznawialny dziennik wykonania i przekazuj robotę między sesjami. Dostarczane jako plugin Claude Code, skill Codex oraz (w planach) rozszerzenie Antigravity CLI.

## Skille

### adhoc-sdlc

Lekki cykl SDLC dla małej, doraźnej pracy: za małej na formalny issue, ale wartej trwałego planu i wznawialnej historii wykonania. Tworzy potwierdzony plan i przyrostowy dziennik wykonania pod `./adhoc-sdlc` w projekcie, w którym go uruchamiasz. Szczegóły w [claude/skills/adhoc-sdlc/README.pl.md](claude/skills/adhoc-sdlc/README.pl.md).

## Układ

Jeden katalog na środowisko agenta, każdy spakowany w natywnym formacie tego środowiska. Helper w Pythonie jest wspólny dla wszystkich wariantów.

```
.claude-plugin/marketplace.json   wpis marketplace Claude Code
claude/                           plugin Claude Code: adhoc-sdlc
  .claude-plugin/plugin.json
  skills/adhoc-sdlc/
  commands/                       /adhoc-sdlc:plan :exec :handoff :resume :history
codex/                            skill Codex (instalacja cp -r)
  skills/adhoc-sdlc/
antigravity/                      plany: format rozszerzenia do ustalenia
```

W Claude Code komendy leżą w osobnym drzewie `commands/` (z namespace pluginu `/adhoc-sdlc:*`); w Codex leżą wewnątrz skilla. Wariant Claude wskazuje skrypty przez `${CLAUDE_PLUGIN_ROOT}`, a wariant Codex przez ścieżkę instalacji.

## Instalacja

### Claude Code (plugin)

Z marketplace:

```
/plugin marketplace add daniel-grabowski/faktoria-sdlc
/plugin install adhoc-sdlc@faktoria-sdlc
```

Do lokalnej pracy na checkoucie załaduj katalog pluginu wprost:

```
claude --plugin-dir ./claude
```

### Codex

```
cp -r codex/skills/adhoc-sdlc ~/.codex/skills/
```

Następnie przeładuj skille w swoim agencie.

### Antigravity CLI

W planach. Format rozszerzenia Antigravity nie został tu jeszcze ustalony; aktualny status w [antigravity/README.md](antigravity/README.md).

## Licencja

MIT. Zobacz [LICENSE](LICENSE).

## Autor

Daniel Grabowski <daniel.grabowski@faktoria.io>
