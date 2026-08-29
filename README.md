# Underpass AI plugins

The plugin marketplace for [Underpass AI](https://underpassai.com), with
native catalogs for Claude Code and Codex.

```text
/plugin marketplace add underpass-ai/plugins
/plugin install kmp@underpass
/plugin install made@underpass
```

```bash
codex plugin marketplace add underpass-ai/plugins
codex plugin add kmp@underpass
```

## What is here

Claude Code reads `.claude-plugin/marketplace.json`, whose entries point at
the plugin directory in each product repository. Codex reads
`.agents/plugins/marketplace.json`; its local plugin source is packaged under
`plugins/` because Codex marketplace entries resolve inside the marketplace
snapshot.

| Plugin | Claude source | Codex source | What it gives your agent |
|---|---|---|---|
| `kmp` | [underpass-ai/kmp](https://github.com/underpass-ai/kmp/tree/main/plugins/kmp) | [`plugins/kmp`](./plugins/kmp) | Local-first agent memory over thirteen MCP tools: ten memory moves plus three shared ChronoLoom view tools, with routing and setup diagnostics. |
| `made` | [underpass-ai/made](https://github.com/underpass-ai/made/tree/main/plugins/made) | Not cataloged yet | The MADE deliberation engine in process: design a ceremony from intent, publish it, and run it step by step. |

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

For Claude Code, add a `git-subdir` entry that points at the owning product
repository. For Codex, place the validated plugin under `plugins/<name>` and
append a local entry to `.agents/plugins/marketplace.json` with installation,
authentication and category policy.

## Legal

Copyright © 2026 Tirso García Ibáñez. Apache-2.0, matching the repositories
this manifest points at.
