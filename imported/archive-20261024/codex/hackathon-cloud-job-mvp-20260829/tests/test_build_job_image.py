from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "build_job_image.py"
SPEC = importlib.util.spec_from_file_location("build_job_image", SCRIPT)
assert SPEC and SPEC.loader
build_job_image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_job_image)


class BuildJobImageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        build_job_image.subprocess.run(
            ["git", "init", "-q"], cwd=self.repo, check=True
        )
        build_job_image.subprocess.run(
            ["git", "config", "user.email", "test@example.invalid"],
            cwd=self.repo,
            check=True,
        )
        build_job_image.subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=self.repo, check=True
        )
        (self.repo / "tracked.txt").write_text("clean\n", encoding="utf-8")
        build_job_image.subprocess.run(
            ["git", "add", "tracked.txt"], cwd=self.repo, check=True
        )
        build_job_image.subprocess.run(
            ["git", "commit", "-qm", "fixture"], cwd=self.repo, check=True
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_clean_repository_returns_exact_head(self) -> None:
        expected = build_job_image._git(self.repo, "rev-parse", "HEAD")
        self.assertEqual(build_job_image.verified_revision(self.repo), expected)

    def test_modified_tree_is_rejected(self) -> None:
        (self.repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "dirty working tree"):
            build_job_image.verified_revision(self.repo)

    def test_untracked_file_is_rejected(self) -> None:
        (self.repo / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "dirty working tree"):
            build_job_image.verified_revision(self.repo)

    def test_subdirectory_is_rejected_as_build_context(self) -> None:
        subdir = self.repo / "nested"
        subdir.mkdir()
        with self.assertRaisesRegex(RuntimeError, "repository root"):
            build_job_image.verified_revision(subdir)
