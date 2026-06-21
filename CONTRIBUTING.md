# Contributing

*English · [Polski](CONTRIBUTING.pl.md)*

The repository is the single source of truth for the `faktoria-sdlc` plugin and its `adhoc-sdlc` and `cove` skills. Edit it here, test, then publish. Do not edit the installed copies under `~/.claude` or `~/.codex` and copy them back; that splits the source and lets the variants drift.

## Runtimes

Claude Code is packaged under `claude/`. Codex has both a plain compatibility skill under `codex/` and the published plugin under `plugins/faktoria-sdlc/`. The planned `antigravity/` variant is still a roadmap placeholder. The Python helper under `scripts/` is shared, so a helper change has to land in every shipped runtime variant.

## Local setup (owner)

Two roles, useful at the same time:

- Develop: load the plugin straight from the checkout so edits are live.
  - Skills-directory plugin (set once): symlink the plugin root under a skills directory, for example `ln -s "$PWD/claude" ~/.claude/skills/faktoria-sdlc`. It loads next session as `adhoc-sdlc@skills-dir`, in place. Edits to `SKILL.md` apply immediately; changes to commands or scripts need `/reload-plugins`.
  - Or per launch: `claude --plugin-dir ./claude`.
- Release: the GitHub marketplace (`.claude-plugin/marketplace.json`) serves everyone else. Do not also install it from the marketplace on the dev machine, or two copies will both claim `/adhoc-sdlc:*`.

Keep the old hand-installed skill out of the way: there must be no `~/.claude/skills/adhoc-sdlc` or `~/.claude/commands/adhoc-sdlc` next to the plugin.

## Dev loop

1. Edit under `claude/skills/adhoc-sdlc` or `claude/commands`.
2. Test: `cd claude/skills/adhoc-sdlc/scripts && python3 -m pytest -q`, and exercise the commands with `claude --plugin-dir ./claude`.
3. Sync the shared helper: `tools/sync-helper.sh` copies `scripts/*.py` from the Claude variant into the Codex variants. Then `cd codex/skills/adhoc-sdlc/scripts && python3 -m pytest -q`.
4. Bump the version in `claude/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and `plugins/faktoria-sdlc/.codex-plugin/plugin.json` when public plugin metadata or behavior changes. Claude versions must agree: `claude plugin validate ./claude` and `claude plugin validate .` check the manifests, and `claude plugin tag` checks that the two Claude versions match at release time.
5. Commit and push.
6. Consumers pull the release with `/plugin update adhoc-sdlc` (after `/plugin marketplace update faktoria-sdlc` if needed).

## The shared helper

`tools/sync-helper.sh` copies the helper from `claude/skills/adhoc-sdlc/scripts/` (the canonical copy) into `codex/skills/adhoc-sdlc/scripts/` and `plugins/faktoria-sdlc/skills/adhoc-sdlc/scripts/`. The duplication is deliberate: plugin packages cannot rely on files outside their own install tree, so the helper has to physically live inside each runtime variant. Run the script after every helper change and run the tests in each shipped variant before you commit.
