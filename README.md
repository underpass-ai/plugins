# Underpass AI plugins

The plugin marketplace for [Underpass AI](https://underpassai.com). One source,
both planes.

```text
/plugin marketplace add underpass-ai/plugins
/plugin install kmp@underpass
/plugin install made@underpass
```

For Codex CLI, which has no plugin system, each repository ships an installer
script — see the links below.

## What is here

This repository contains **no plugin code**. It is a manifest that points at
the plugin directory inside each product repository, so a plugin is always
released and versioned by the repo that owns it.

| Plugin | Lives in | What it gives your agent |
|---|---|---|
| `kmp` | [underpass-ai/kmp](https://github.com/underpass-ai/kmp/tree/main/plugins/kmp) | Navigable agent memory over MCP: the ten KMP moves, a skill that teaches when to reach for memory, and `/kmp:doctor` to diagnose a broken setup. |
| `made` | [underpass-ai/made](https://github.com/underpass-ai/made/tree/main/plugins/made) | The MADE deliberation engine in process: design a ceremony from intent, publish it, and run it step by step. |

Both plugins run their engine **in process**. Neither needs a service, a
database or an API key to start.

## Binaries

A plugin launcher runs the binary bundled in a release package when there is
one, and otherwise falls back to the one on your `PATH`:

```bash
cargo install kmp-mcp     # for the kmp plugin
cargo install made-mcp    # for the made plugin
```

Release packages with a pinned binary are attached to each product repository's
GitHub Releases.

## Adding a plugin here

Entries use a `git-subdir` source so the manifest never carries a copy of the
plugin. Point it at the repository, the path inside it, and the ref to track.
Nothing else in this repository needs to change when a plugin releases.

## Legal

Copyright © 2026 Tirso García Ibáñez. Apache-2.0, matching the repositories
this manifest points at.
