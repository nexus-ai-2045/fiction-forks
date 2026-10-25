"""Fail-closed, canonical builder for the Fiction Forks job image."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def verified_revision(repo: Path) -> str:
    root = Path(_git(repo, "rev-parse", "--show-toplevel")).resolve()
    if root != repo.resolve():
        raise RuntimeError("build context must be the repository root")
    revision = _git(repo, "rev-parse", "HEAD")
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise RuntimeError("HEAD is not a full lowercase commit SHA")
    if _git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("refusing to build from a dirty working tree")
    return revision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag-prefix", default="fiction-forks-job")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    revision = verified_revision(repo)
    tag = f"{args.tag_prefix}:{revision}"
    subprocess.run(
        [
            "docker",
            "build",
            "--build-arg",
            f"SOURCE_REVISION={revision}",
            "--label",
            f"org.opencontainers.image.revision={revision}",
            "--tag",
            tag,
            ".",
        ],
        cwd=repo,
        check=True,
    )
    print(tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
