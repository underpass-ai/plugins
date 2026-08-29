#!/usr/bin/env python3
"""Validate that the public KMP catalogs and Codex mirror are one reviewed tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
CLAUDE_LISTING = ROOT / ".claude-plugin/marketplace.json"
CODEX_LISTING = ROOT / ".agents/plugins/marketplace.json"
PLUGIN = ROOT / "plugins/kmp"
EXPECTED_CLAUDE_SOURCE = {
    "source": "git-subdir",
    "url": "https://github.com/underpass-ai/kmp.git",
    "path": "plugins/kmp",
}
EXPECTED_CODEX_SOURCE = {"source": "local", "path": "./plugins/kmp"}
KMP_REMOTE = "https://github.com/underpass-ai/kmp.git"
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
RETIRED_COUNT = re.compile(
    r"\b(?:ten|10)(?:\s+kmp)?\s+(?:mcp\s+)?(?:moves|tools)\b",
    re.I,
)


def display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: pathlib.Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"{display_path(path)} is not valid JSON: {error}")
    if not isinstance(value, dict):
        raise SystemExit(f"{display_path(path)} must contain a JSON object")
    return value


def kmp_entry(path: pathlib.Path) -> dict[str, object]:
    listing = read_json(path)
    plugins = listing.get("plugins")
    if not isinstance(plugins, list):
        raise SystemExit(f"{display_path(path)} has no plugins array")
    matches = [
        plugin
        for plugin in plugins
        if isinstance(plugin, dict) and plugin.get("name") == "kmp"
    ]
    if len(matches) != 1:
        raise SystemExit(f"{display_path(path)} must contain exactly one kmp entry")
    return matches[0]


def mirrored_version() -> str:
    versions = set()
    for relative in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        version = read_json(PLUGIN / relative).get("version")
        if not isinstance(version, str) or not version:
            raise SystemExit(f"{display_path(PLUGIN / relative)} has no version")
        versions.add(version.split("+", 1)[0])
    if len(versions) != 1:
        raise SystemExit(f"mirrored KMP host manifests disagree on version: {sorted(versions)}")
    return versions.pop()


def annotated_tag_commit(ref: str) -> str:
    result = subprocess.run(
        [
            "git",
            "ls-remote",
            "--tags",
            KMP_REMOTE,
            f"refs/tags/{ref}",
            f"refs/tags/{ref}^{{}}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "tag lookup failed"
        raise SystemExit(f"could not resolve KMP source tag {ref}: {detail}")
    refs = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 2 and COMMIT_SHA.fullmatch(fields[0]):
            refs[fields[1]] = fields[0]
    tag_ref = f"refs/tags/{ref}"
    if tag_ref not in refs:
        raise SystemExit(f"KMP source tag {ref} does not exist")
    peeled = refs.get(f"{tag_ref}^{{}}")
    if peeled is None:
        raise SystemExit(f"KMP source tag {ref} must be annotated")
    return peeled


def claude_source() -> tuple[dict[str, object], str, str]:
    entry = kmp_entry(CLAUDE_LISTING)
    source = entry.get("source")
    if not isinstance(source, dict):
        raise SystemExit("Claude kmp entry has no git-subdir source")
    stable = {key: source.get(key) for key in EXPECTED_CLAUDE_SOURCE}
    if stable != EXPECTED_CLAUDE_SOURCE:
        raise SystemExit("Claude kmp entry no longer resolves underpass-ai/kmp/plugins/kmp")
    ref = source.get("ref")
    expected_ref = f"v{mirrored_version()}"
    if ref != expected_ref:
        raise SystemExit(f"Claude kmp source must pin clonable immutable release tag {expected_ref}")
    verify_description("Claude marketplace entry", entry.get("description"))
    return entry, ref, annotated_tag_commit(ref)


def verify_description(label: str, value: object) -> None:
    if not isinstance(value, str) or "ChronoLoom" not in value:
        raise SystemExit(f"{label} must describe ChronoLoom")
    if RETIRED_COUNT.search(value):
        raise SystemExit(f"{label} still advertises the retired whole-surface count")


def tree(root: pathlib.Path) -> dict[str, tuple[bool, str]]:
    if not root.is_dir():
        raise SystemExit(f"plugin source does not exist: {root}")
    result = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        result[relative] = (
            bool(path.stat().st_mode & 0o111),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    return result


def verify_tree(source_root: pathlib.Path) -> None:
    expected = tree(source_root)
    observed = tree(PLUGIN)
    if observed == expected:
        return
    missing = sorted(expected.keys() - observed.keys())
    extra = sorted(observed.keys() - expected.keys())
    changed = sorted(
        path for path in expected.keys() & observed.keys() if expected[path] != observed[path]
    )
    raise SystemExit(
        "KMP Codex snapshot differs from its immutable Claude source: "
        f"missing={missing}, extra={extra}, changed={changed}"
    )


def verify_contract(source_root: pathlib.Path) -> None:
    _, ref, expected_commit = claude_source()
    codex = kmp_entry(CODEX_LISTING)
    if codex.get("source") != EXPECTED_CODEX_SOURCE:
        raise SystemExit("Codex kmp entry no longer resolves the reviewed plugins/kmp snapshot")

    verify_tree(source_root)

    checked_out_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source_root,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if checked_out_commit != expected_commit:
        raise SystemExit(
            f"Claude clone checked out {checked_out_commit or 'no commit'}, "
            f"not annotated tag commit {expected_commit}"
        )

    versions = set()
    for root in (PLUGIN, source_root):
        for relative in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            manifest = read_json(root / relative)
            version = manifest.get("version")
            if not isinstance(version, str) or not version:
                raise SystemExit(f"{root / relative} has no version")
            versions.add(version.split("+", 1)[0])
            verify_description(f"{root / relative}", manifest.get("description"))
    if len(versions) != 1:
        raise SystemExit(f"KMP host manifests disagree on version: {sorted(versions)}")

    capabilities = read_json(PLUGIN / "capabilities.json").get("mcp_tools")
    source_capabilities = read_json(source_root / "capabilities.json").get("mcp_tools")
    if capabilities != source_capabilities or not isinstance(capabilities, list):
        raise SystemExit("KMP capability map differs from its immutable source")
    if len(capabilities) != 13 or len(set(capabilities)) != 13:
        raise SystemExit("KMP marketplace must expose exactly thirteen unique MCP tools")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = [line for line in readme.splitlines() if line.startswith("| `kmp` |")]
    if len(rows) != 1:
        raise SystemExit(f"marketplace README must contain one kmp row, found {len(rows)}")
    row = rows[0]
    verify_description("marketplace README kmp row", row)
    for claim in ("thirteen MCP tools", "ten memory moves", "three shared ChronoLoom view tools"):
        if claim not in row:
            raise SystemExit(f"marketplace README kmp row must say {claim!r}")
    if RETIRED_COUNT.search(readme):
        raise SystemExit("marketplace README still contains retired whole-surface copy")

    print(f"KMP marketplace contract passed: {versions.pop()}, 13 tools, source {ref}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=pathlib.Path)
    parser.add_argument("--print-source-ref", action="store_true")
    args = parser.parse_args()
    _, ref, _ = claude_source()
    if args.print_source_ref:
        print(ref)
        return
    if args.source_root is None:
        parser.error("--source-root is required unless --print-source-ref is used")
    verify_contract(args.source_root)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(1)
