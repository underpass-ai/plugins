#!/usr/bin/env python3
"""Regression fixtures for the pre-tag and annotated-tag marketplace contract."""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import tempfile


SCRIPT = pathlib.Path(__file__).with_name("kmp-contract.py")
SPEC = importlib.util.spec_from_file_location("kmp_contract", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit(f"could not load {SCRIPT}")
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)


def run(*args: object, cwd: pathlib.Path | None = None) -> None:
    subprocess.run(
        [str(argument) for argument in args],
        cwd=cwd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


with tempfile.TemporaryDirectory(prefix="kmp-marketplace-ref-") as raw_fixture:
    fixture = pathlib.Path(raw_fixture)
    remote = fixture / "remote.git"
    work = fixture / "work"
    run("git", "init", "--bare", remote)
    run("git", "init", "--initial-branch=main", work)
    run("git", "config", "user.name", "KMP contract", cwd=work)
    run("git", "config", "user.email", "kmp-contract@example.invalid", cwd=work)
    (work / "README.md").write_text("release-ref fixture\n", encoding="utf-8")
    run("git", "add", "README.md", cwd=work)
    run("git", "commit", "-m", "fixture: candidate", cwd=work)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=work,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    run("git", "remote", "add", "origin", remote.as_uri(), cwd=work)
    run("git", "push", "origin", "main", cwd=work)

    try:
        CONTRACT.release_commit("v0.5.1", remote.as_uri())
    except SystemExit as error:
        if "does not exist" not in str(error):
            raise
    else:
        raise SystemExit("strict marketplace contract accepted an unpublished tag")

    observed, published = CONTRACT.release_commit(
        "v0.5.1", remote.as_uri(), allow_unpublished_tag=True
    )
    if observed != commit or published:
        raise SystemExit("pre-tag marketplace contract did not bind remote main")

    run("git", "tag", "v0.5.1", cwd=work)
    run("git", "push", "origin", "refs/tags/v0.5.1", cwd=work)
    try:
        CONTRACT.release_commit(
            "v0.5.1", remote.as_uri(), allow_unpublished_tag=True
        )
    except SystemExit as error:
        if "must be annotated" not in str(error):
            raise
    else:
        raise SystemExit("marketplace contract accepted a lightweight release tag")

    run("git", "push", "origin", ":refs/tags/v0.5.1", cwd=work)
    run("git", "tag", "-d", "v0.5.1", cwd=work)
    run("git", "tag", "-a", "v0.5.1", "-m", "Release v0.5.1", cwd=work)
    run("git", "push", "origin", "refs/tags/v0.5.1", cwd=work)
    observed, published = CONTRACT.release_commit(
        "v0.5.1", remote.as_uri(), allow_unpublished_tag=True
    )
    if observed != commit or not published:
        raise SystemExit("annotated release tag did not peel to the reviewed commit")

print("KMP release-ref regressions passed: unpublished main, lightweight refusal, annotated tag")
