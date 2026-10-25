from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fiction_forks.engine import ContractError
from fiction_forks.job_runner import _source_revision, main
from fiction_forks.social import replay_equivalent


class JobRunnerTests(unittest.TestCase):
    SOURCE_REVISION = "a" * 40

    def invoke(self, directory: Path, worldline: str = "doraemon-public-tools"):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.dict(os.environ, {"FICTION_FORKS_ROOT": str(ROOT)}, clear=False), patch(
            "fiction_forks.job_runner._source_revision",
            return_value=self.SOURCE_REVISION,
        ):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["--worldline", worldline, "--output-dir", str(directory)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_happy_path_emits_one_line_summary_and_three_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            code, stdout, stderr = self.invoke(directory)
            self.assertEqual(0, code)
            self.assertEqual("", stderr)
            self.assertEqual(1, len(stdout.splitlines()))
            summary = json.loads(stdout)
            self.assertEqual("ok", summary["status"])
            self.assertEqual("doraemon-public-tools", summary["worldline"])
            self.assertEqual(
                {
                    "doraemon-public-tools.artifact.json",
                    "doraemon-public-tools.replay.json",
                    "doraemon-public-tools.manifest.json",
                },
                {path.name for path in directory.iterdir()},
            )

    def test_manifest_hashes_and_replay_are_verified(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            code, _, _ = self.invoke(directory, "haruhi-world-observation")
            self.assertEqual(0, code)
            artifact_path = directory / "haruhi-world-observation.artifact.json"
            replay_path = directory / "haruhi-world-observation.replay.json"
            manifest = json.loads(
                (directory / "haruhi-world-observation.manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            replay = json.loads(replay_path.read_text(encoding="utf-8"))
            self.assertEqual(
                "fiction_forks_run_manifest.v1", manifest["schema_version"]
            )
            self.assertEqual("fixture", manifest["run_kind"])
            self.assertFalse(manifest["ai_measured"])
            self.assertEqual(self.SOURCE_REVISION, manifest["engine_commit"])
            self.assertEqual(
                "japan-2036-world-observation-dialogue",
                manifest["social_config_id"],
            )
            self.assertEqual(artifact_path.name, manifest["artifact_path"])
            self.assertEqual(
                hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                manifest["artifact_sha256"],
            )
            self.assertTrue(manifest["replay_equivalent"])
            self.assertEqual(replay_path.name, manifest["replay_artifact_path"])
            self.assertEqual(
                hashlib.sha256(replay_path.read_bytes()).hexdigest(),
                manifest["replay_artifact_sha256"],
            )
            self.assertTrue(replay_equivalent(artifact, replay))

    def test_missing_source_revision_fails_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            stderr = io.StringIO()
            with patch(
                "fiction_forks.job_runner._source_revision",
                side_effect=ContractError("source revision is unavailable"),
            ), redirect_stderr(stderr):
                self.assertEqual(
                    2,
                    main(
                        [
                            "--worldline",
                            "doraemon-public-tools",
                            "--output-dir",
                            str(directory),
                        ]
                    ),
                )
            self.assertIn("source revision is unavailable", stderr.getvalue())
            self.assertEqual([], list(directory.iterdir()))

    def test_malformed_source_revision_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            root = Path(raw_directory)
            (root / ".source-revision").write_text("A" * 40, encoding="ascii")
            with self.assertRaisesRegex(ContractError, "lowercase hex commit"):
                _source_revision(root)

    def test_nonexistent_and_file_output_dirs_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            root = Path(raw_directory)
            missing = root / "missing" / ".." / "output"
            code, _, stderr = self.invoke(missing)
            self.assertEqual(2, code)
            self.assertIn("output-dir must already exist", stderr)
            file_path = root / "output.txt"
            file_path.write_text("x", encoding="utf-8")
            code, _, stderr = self.invoke(file_path)
            self.assertEqual(2, code)
            self.assertIn("output-dir must be a directory", stderr)

    def test_existing_output_is_refused_without_modifying_it(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            existing = directory / "doraemon-public-tools.artifact.json"
            existing.write_text("keep", encoding="utf-8")
            code, _, stderr = self.invoke(directory)
            self.assertEqual(2, code)
            self.assertIn("refusing to overwrite existing outputs", stderr)
            self.assertEqual("keep", existing.read_text(encoding="utf-8"))
            self.assertEqual([existing], list(directory.iterdir()))

    def test_publication_failure_rolls_back_partial_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            real_link = os.link
            calls = 0

            def fail_second_link(source, target):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise FileExistsError(target)
                return real_link(source, target)

            with patch("fiction_forks.job_runner.os.link", side_effect=fail_second_link):
                code, _, stderr = self.invoke(directory)
            self.assertEqual(2, code)
            self.assertIn("refusing to overwrite", stderr)
            self.assertEqual([], list(directory.iterdir()))

    def test_baked_revision_ignores_runtime_spoofing(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            root = Path(raw_directory)
            (root / ".source-revision").write_text(
                self.SOURCE_REVISION, encoding="ascii"
            )
            with patch.dict(os.environ, {"SOURCE_REVISION": "b" * 40}, clear=False):
                self.assertEqual(self.SOURCE_REVISION, _source_revision(root))


if __name__ == "__main__":
    unittest.main()
