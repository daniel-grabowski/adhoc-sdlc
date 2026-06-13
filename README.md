# faktoria-sdlc

SDLC skills for AI coding agents: plan, keep a resumable execution journal, and hand off work between sessions. Works in Claude Code and Codex.

## Skills

### adhoc-sdlc

A lightweight SDLC for small, ad hoc work: too small for a formal issue, but worth a durable plan and a resumable execution history. It produces a confirmed plan and an incremental execution journal under `./adhoc-sdlc` in the project you run it in. See [claude/skills/adhoc-sdlc/README.md](claude/skills/adhoc-sdlc/README.md) for details.

## Layout

One directory per agent runtime, each mirroring that runtime's install paths:

```
claude/
  skills/adhoc-sdlc/      ->  ~/.claude/skills/adhoc-sdlc/
  commands/adhoc-sdlc/    ->  ~/.claude/commands/adhoc-sdlc/
codex/
  skills/adhoc-sdlc/      ->  ~/.codex/skills/adhoc-sdlc/
```

In Claude Code the commands live in a separate `commands/` tree; in Codex they live inside the skill. The two variants share the same Python helper.

## Install

Claude Code:

```
cp -r claude/skills/adhoc-sdlc ~/.claude/skills/
cp -r claude/commands/adhoc-sdlc ~/.claude/commands/
```

Codex:

```
cp -r codex/skills/adhoc-sdlc ~/.codex/skills/
```

Then reload skills in your agent.

## License

MIT. See [LICENSE](LICENSE).

## Author

Daniel Grabowski <daniel.grabowski@faktoria.io>
