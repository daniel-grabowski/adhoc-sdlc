# adhoc-sdlc

*English · [Polski](README.pl.md)*

## What

`adhoc-sdlc` is a small SDLC toolkit for AI coding agents. It packages two reusable skills: `adhoc-sdlc` for lightweight implementation work with a durable plan and execution journal, and `cove` for Chain-of-Verification before factual claims reach a user.

## Why

AI coding is fast, but speed without a record is fragile. This repo gives Claude Code and Codex a shared workflow for planning, verifying, journaling, resuming, and handing off small tasks without turning every change into a formal issue.

## Harness, not vibe coding

Addy Osmani's [The New Software Lifecycle](https://addyosmani.com/blog/new-sdlc-vibe-coding/), and the [Google whitepaper](https://www.kaggle.com/whitepaper-the-new-SDLC-with-vibe-coding) behind it, frame an agent as a model plus a harness. The model is one input; the harness is the instructions, tools, context rules, and verification wrapped around it. The paper's rough split is 10% model, 90% harness. It also puts the line between vibe coding and engineering in one place: verification. Code that merely seems to work is vibe coding; code whose outputs get checked is engineering.

This repo is the harness, not the model. `adhoc-sdlc` is the record: a confirmed plan and a journal that outlive a pause or a context reset, so the work stays checkable instead of living only in a chat log. `cove` is the verification: it runs a draft through independent questions before any claim reaches you. The skills load the way the paper recommends too, a little metadata up front and the full instructions only once a task matches (progressive disclosure), so the context you pay for on every turn stays small.

None of that waits on a better model. It is configuration you can get right today, reviewed and versioned like the rest of the code.

## Skills

### adhoc-sdlc

What: a lightweight SDLC for small, ad hoc implementation work. Why: it keeps even quick fixes grounded in a confirmed plan, engineering checklist, optional verification gates, and a resumable execution journal under `./adhoc-sdlc`. See [claude/skills/adhoc-sdlc/README.md](claude/skills/adhoc-sdlc/README.md) for details.

<p align="center">
  <img src="assets/adhoc-sdlc.png" alt="adhoc-sdlc" width="320">
</p>

### CoVe

What: Chain-of-Verification for factual work. Why: it forces drafts through independent verification questions so final answers keep only verified or explicitly caveated facts. The Claude Code and Codex plugins ship this as the `cove` skill.

## Layout

One directory per agent runtime, each packaged in that runtime's native format. The Python helper is shared across variants and duplicated where plugin packaging requires a self-contained directory.

```
.claude-plugin/marketplace.json   Claude Code marketplace entry
.agents/plugins/marketplace.json  Codex marketplace entry
claude/                           Claude Code plugin: adhoc-sdlc + cove
  .claude-plugin/plugin.json
  skills/adhoc-sdlc/
  skills/cove/
  commands/                       /adhoc-sdlc:plan :exec :handoff :resume :history
plugins/adhoc-sdlc/            Codex plugin: adhoc-sdlc
  .codex-plugin/plugin.json
  skills/adhoc-sdlc/
  skills/cove/
antigravity/                      roadmap: extension format to be confirmed
```

In Claude Code the commands live in a top-level `commands/` tree (namespaced by the plugin to `/adhoc-sdlc:*`); in Codex they live inside the skill. The Claude variant references scripts through `${CLAUDE_PLUGIN_ROOT}`; the Codex variant resolves scripts relative to the installed skill directory.

## Install

### Claude Code (plugin)

From the marketplace:

```
/plugin marketplace add daniel-grabowski/adhoc-sdlc
/plugin install adhoc-sdlc@adhoc-sdlc
```

For local development against a checkout, load the plugin directory directly:

```
claude --plugin-dir ./claude
```

### Codex (plugin)

Recommended public install from GitHub:

```
codex plugin marketplace add daniel-grabowski/adhoc-sdlc --ref main
codex plugin add adhoc-sdlc@adhoc-sdlc
```

This does not use your local checkout. Codex fetches the `adhoc-sdlc` marketplace from GitHub, then resolves the plugin through `.agents/plugins/marketplace.json` inside that fetched repo. The marketplace entry intentionally uses a relative local path:

```json
"source": {
  "source": "local",
  "path": "./plugins/adhoc-sdlc"
}
```

That path is local to the downloaded marketplace snapshot, not to `/home/.../adhoc-sdlc` on your machine.

If you previously added the marketplace from a local checkout, switch it to GitHub:

```
codex plugin remove adhoc-sdlc@adhoc-sdlc
codex plugin marketplace remove adhoc-sdlc
codex plugin marketplace add daniel-grabowski/adhoc-sdlc --ref main
codex plugin add adhoc-sdlc@adhoc-sdlc
```

Verify the source:

```
codex plugin marketplace list --json
codex plugin list --marketplace adhoc-sdlc --available --json
```

For local development against a checkout:

```
codex plugin marketplace add .
codex plugin add adhoc-sdlc@adhoc-sdlc
```

### Antigravity CLI

Planned, most likely as a skill like the Codex variant rather than a plugin. The exact format is not finalized here yet; see [antigravity/README.md](antigravity/README.md) for the current status.

## License

MIT. See [LICENSE](LICENSE).

## Author

Daniel Grabowski <daniel.grabowski@faktoria.io>
