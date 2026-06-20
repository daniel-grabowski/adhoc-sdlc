# faktoria-sdlc

*English · [Polski](README.pl.md)*

SDLC skills for AI coding agents: plan, keep a resumable execution journal, and hand off work between sessions. Packaged as a Claude Code plugin, a Codex skill, and (on the roadmap) an Antigravity CLI extension.

## Skills

### adhoc-sdlc

A lightweight SDLC for small, ad hoc work: too small for a formal issue, but worth a durable plan and a resumable execution history. It produces a confirmed plan and an incremental execution journal under `./adhoc-sdlc` in the project you run it in. See [claude/skills/adhoc-sdlc/README.md](claude/skills/adhoc-sdlc/README.md) for details.

## Layout

One directory per agent runtime, each packaged in that runtime's native format. The Python helper is shared across variants.

```
.claude-plugin/marketplace.json   Claude Code marketplace entry
claude/                           Claude Code plugin: adhoc-sdlc
  .claude-plugin/plugin.json
  skills/adhoc-sdlc/
  commands/                       /adhoc-sdlc:plan :exec :handoff :resume :history
codex/                            Codex skill (cp -r install)
  skills/adhoc-sdlc/
antigravity/                      roadmap: extension format to be confirmed
```

In Claude Code the commands live in a top-level `commands/` tree (namespaced by the plugin to `/adhoc-sdlc:*`); in Codex they live inside the skill. The Claude variant references scripts through `${CLAUDE_PLUGIN_ROOT}`; the Codex variant uses its install path.

## Install

### Claude Code (plugin)

From the marketplace:

```
/plugin marketplace add daniel-grabowski/faktoria-sdlc
/plugin install adhoc-sdlc@faktoria-sdlc
```

For local development against a checkout, load the plugin directory directly:

```
claude --plugin-dir ./claude
```

### Codex

```
cp -r codex/skills/adhoc-sdlc ~/.codex/skills/
```

Then reload skills in your agent.

### Antigravity CLI

Planned. The Antigravity extension format has not been finalized here yet; see [antigravity/README.md](antigravity/README.md) for the current status.

## License

MIT. See [LICENSE](LICENSE).

## Author

Daniel Grabowski <daniel.grabowski@faktoria.io>
