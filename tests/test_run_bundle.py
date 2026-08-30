from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fiction_forks.engine import ContractError, load_json
from fiction_forks.providers import FixtureProvider
from fiction_forks.run_bundle import build_run_bundle, event_stream_sha256
from fiction_forks.social import run_social_simulation


class RunBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = load_json(ROOT / "scenarios/japan-2036/scenario.json")
        cls.intervention = load_json(ROOT / "interventions/doraemon-public-tools.json")
        cls.social_config = load_json(ROOT / "scenarios/japan-2036/social.json")
        cls.fixture_path = ROOT / "fixtures/social/japan-2036-cooperation.jsonl"

    def run_fixture(self) -> dict:
        return run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            FixtureProvider.from_jsonl(self.fixture_path),
            seed=2036,
        )

    def bundle(self, result: dict) -> dict:
        return build_run_bundle(
            result,
            command=["python", "-m", "fiction_forks", "social"],
            requested_at="2026-08-30T00:00:00Z",
            started_at="2026-08-30T00:00:00Z",
            completed_at="2026-08-30T00:00:01Z",
            generated_at="2026-08-30T00:00:01Z",
            source_revision="a" * 40,
            stdout_sha256="b" * 64,
        )

    def test_bundle_binds_all_records_to_canonical_run(self) -> None:
        result = self.run_fixture()
        bundle = self.bundle(result)
        run_id = result["run_id"]
        self.assertEqual("meta-security-run-bundle/v1", bundle["schema"])
        self.assertEqual(run_id, bundle["run_request"]["run_id"])
        self.assertTrue(all(event["run_id"] == run_id for event in bundle["events"]))
        self.assertEqual(run_id, bundle["replay"]["run_id"])
        self.assertEqual(run_id, bundle["evidence"]["run_id"])
        self.assertEqual(
            list(range(15)), [event["sequence"] for event in bundle["events"]]
        )
        digest = event_stream_sha256(bundle["events"])
        self.assertEqual(digest, bundle["replay"]["event_stream_sha256"])
        self.assertEqual(digest, bundle["evidence"]["event_stream_sha256"])

    def test_same_seed_preserves_domain_result_event_order_and_bundle_digest(
        self,
    ) -> None:
        first = self.run_fixture()
        second = self.run_fixture()
        self.assertEqual(first, second)
        first_bundle = self.bundle(first)
        second_bundle = self.bundle(second)
        self.assertEqual(first_bundle["events"], second_bundle["events"])
        self.assertEqual(
            first_bundle["replay"]["event_stream_sha256"],
            second_bundle["replay"]["event_stream_sha256"],
        )

    def test_cli_writes_bundle_and_hashes_exact_stdout_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            bundle_path = Path(directory) / "bundle.json"
            argv = [
                sys.executable,
                "-m",
                "fiction_forks",
                "social",
                "--scenario",
                str(ROOT / "scenarios/japan-2036/scenario.json"),
                "--intervention",
                str(ROOT / "interventions/doraemon-public-tools.json"),
                "--social-config",
                str(ROOT / "scenarios/japan-2036/social.json"),
                "--provider",
                "fixture",
                "--fixture",
                str(self.fixture_path),
                "--seed",
                "2036",
                "--output",
                str(output),
                "--bundle-output",
                str(bundle_path),
                "--source-revision",
                "a" * 40,
            ]
            cli_argv = argv[3:]
            with (
                patch(
                    "fiction_forks.cli._verified_source_revision",
                    return_value="a" * 40,
                ),
                redirect_stdout(io.StringIO()) as stdout,
            ):
                from fiction_forks.cli import main as cli_main

                self.assertEqual(0, cli_main(cli_argv))
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            stdout_bytes = stdout.getvalue().encode("utf-8")
            expected = hashlib.sha256(stdout_bytes).hexdigest()
            self.assertEqual(expected, bundle["evidence"]["execution"]["stdout_sha256"])
            self.assertEqual(output.read_bytes(), stdout_bytes)
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["run_id"],
                bundle["run_request"]["run_id"],
            )
            self.assertEqual(
                "python", bundle["evidence"]["execution"]["command"][0]
            )

    def test_cli_rejects_colliding_output_paths_before_writing(self) -> None:
        from fiction_forks.cli import main as cli_main

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "same.json"
            args = [
                "social",
                "--scenario",
                str(ROOT / "scenarios/japan-2036/scenario.json"),
                "--intervention",
                str(ROOT / "interventions/doraemon-public-tools.json"),
                "--social-config",
                str(ROOT / "scenarios/japan-2036/social.json"),
                "--provider",
                "fixture",
                "--fixture",
                str(self.fixture_path),
                "--output",
                str(output),
                "--bundle-output",
                str(output),
                "--source-revision",
                "a" * 40,
            ]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(2, cli_main(args))
            self.assertFalse(output.exists())

    def test_cli_rejects_existing_bundle_before_writing_result(self) -> None:
        from fiction_forks.cli import main as cli_main

        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            bundle_path = Path(directory) / "bundle.json"
            bundle_path.write_text("existing", encoding="utf-8")
            args = [
                "social",
                "--scenario",
                str(ROOT / "scenarios/japan-2036/scenario.json"),
                "--intervention",
                str(ROOT / "interventions/doraemon-public-tools.json"),
                "--social-config",
                str(ROOT / "scenarios/japan-2036/social.json"),
                "--provider",
                "fixture",
                "--fixture",
                str(self.fixture_path),
                "--output",
                str(result_path),
                "--bundle-output",
                str(bundle_path),
                "--source-revision",
                "a" * 40,
            ]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(2, cli_main(args))
            self.assertFalse(result_path.exists())
            self.assertEqual("existing", bundle_path.read_text(encoding="utf-8"))

    def test_source_revision_must_match_clean_runtime_checkout(self) -> None:
        from fiction_forks.cli import _verified_source_revision

        clean = subprocess_result("a" * 40 + "\n")
        with patch(
            "fiction_forks.cli.subprocess.run",
            side_effect=[clean, subprocess_result("")],
        ):
            self.assertEqual("a" * 40, _verified_source_revision("a" * 40))
        with patch(
            "fiction_forks.cli.subprocess.run",
            side_effect=[clean, subprocess_result("")],
        ):
            with self.assertRaisesRegex(Exception, "must match"):
                _verified_source_revision("b" * 40)
        with patch(
            "fiction_forks.cli.subprocess.run",
            side_effect=[clean, subprocess_result(" M src/fiction_forks/social.py\n")],
        ):
            with self.assertRaisesRegex(Exception, "clean runtime source"):
                _verified_source_revision("a" * 40)

    def test_output_pair_rolls_back_when_second_replace_fails(self) -> None:
        from fiction_forks.cli import _write_output_pair

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "result.json"
            second = Path(directory) / "bundle.json"
            first.write_text("old-result\n", encoding="utf-8")
            second.write_text("old-bundle\n", encoding="utf-8")
            original_replace = Path.replace

            def fail_second_temporary(path: Path, target: Path):
                if path.name == ".bundle.json.tmp":
                    raise OSError("simulated bundle replace failure")
                return original_replace(path, target)

            with patch.object(Path, "replace", fail_second_temporary):
                with self.assertRaisesRegex(ContractError, "not committed"):
                    _write_output_pair(
                        str(first),
                        "new-result",
                        str(second),
                        "new-bundle",
                        overwrite=True,
                    )
            self.assertEqual("old-result\n", first.read_text(encoding="utf-8"))
            self.assertEqual("old-bundle\n", second.read_text(encoding="utf-8"))
            self.assertEqual([], list(Path(directory).glob(".*.tmp")))
            self.assertEqual([], list(Path(directory).glob(".*.bak")))

    def test_non_bundle_cli_imports_without_rfc8785_installed(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(SRC)
        command = [
            sys.executable,
            "-S",
            "-c",
            "from fiction_forks.cli import main; raise SystemExit(main(['simulate','--scenario',r'"
            + str(ROOT / "scenarios/japan-2036/scenario.json")
            + "','--seed','2036']))",
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr.decode("utf-8"))

    def test_output_pair_cleans_partial_second_stage_write(self) -> None:
        from fiction_forks.cli import _write_output_pair

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "result.json"
            second = Path(directory) / "bundle.json"
            first.write_text("old-result\n", encoding="utf-8")
            second.write_text("old-bundle\n", encoding="utf-8")
            original_open = Path.open

            def fail_second_open(path: Path, *args, **kwargs):
                if path.name == ".bundle.json.tmp":
                    handle = original_open(path, *args, **kwargs)

                    class PartialWrite:
                        def __enter__(self):
                            handle.__enter__()
                            return self

                        def __exit__(self, *exc):
                            return handle.__exit__(*exc)

                        def write(self, data: bytes):
                            handle.write(data[:1])
                            raise OSError("simulated partial stage write")

                    return PartialWrite()
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", fail_second_open):
                with self.assertRaisesRegex(ContractError, "not committed"):
                    _write_output_pair(
                        str(first),
                        "new-result",
                        str(second),
                        "new-bundle",
                        overwrite=True,
                    )
            self.assertEqual("old-result\n", first.read_text(encoding="utf-8"))
            self.assertEqual("old-bundle\n", second.read_text(encoding="utf-8"))
            self.assertEqual([], list(Path(directory).glob(".*.tmp")))
            self.assertEqual([], list(Path(directory).glob(".*.bak")))

    def test_output_pair_preserves_concurrent_owner_target(self) -> None:
        from fiction_forks.cli import _write_output_pair

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "result.json"
            second = Path(directory) / "bundle.json"
            original_open = Path.open

            def concurrent_second_open(path: Path, *args, **kwargs):
                if path.name == ".bundle.json.tmp":
                    second.write_text("concurrent-owner\n", encoding="utf-8")
                    raise OSError("simulated concurrent owner")
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", concurrent_second_open):
                with self.assertRaisesRegex(ContractError, "not committed"):
                    _write_output_pair(
                        str(first),
                        "new-result",
                        str(second),
                        "new-bundle",
                        overwrite=False,
                    )
            self.assertFalse(first.exists())
            self.assertEqual("concurrent-owner\n", second.read_text(encoding="utf-8"))
            self.assertEqual([], list(Path(directory).glob(".*.tmp")))
            self.assertEqual([], list(Path(directory).glob(".*.bak")))

    def test_output_pair_cleanup_failure_does_not_relabel_commit(self) -> None:
        from fiction_forks.cli import _write_output_pair

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "result.json"
            second = Path(directory) / "bundle.json"
            first.write_text("old-result\n", encoding="utf-8")
            second.write_text("old-bundle\n", encoding="utf-8")
            original_unlink = Path.unlink

            def fail_backup_cleanup(path: Path, *args, **kwargs):
                if path.name.startswith(".bundle.json.") and path.name.endswith(".bak"):
                    raise OSError("simulated cleanup failure")
                return original_unlink(path, *args, **kwargs)

            with patch.object(Path, "unlink", fail_backup_cleanup):
                _write_output_pair(
                    str(first),
                    "new-result",
                    str(second),
                    "new-bundle",
                    overwrite=True,
                )
            self.assertEqual("new-result\n", first.read_text(encoding="utf-8"))
            self.assertEqual("new-bundle\n", second.read_text(encoding="utf-8"))

    def test_output_pair_rolls_back_when_installed_link_cleanup_fails(self) -> None:
        from fiction_forks.cli import _write_output_pair

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "result.json"
            second = Path(directory) / "bundle.json"
            original_unlink = Path.unlink
            failed_once = False

            def fail_first_temp_unlink(path: Path, *args, **kwargs):
                nonlocal failed_once
                if path.name == ".result.json.tmp" and not failed_once:
                    failed_once = True
                    raise OSError("simulated installed-link cleanup failure")
                return original_unlink(path, *args, **kwargs)

            with patch.object(Path, "unlink", fail_first_temp_unlink):
                with self.assertRaisesRegex(ContractError, "not committed"):
                    _write_output_pair(
                        str(first),
                        "new-result",
                        str(second),
                        "new-bundle",
                        overwrite=False,
                    )
            self.assertFalse(first.exists())
            self.assertFalse(second.exists())
            self.assertEqual([], list(Path(directory).glob(".*.tmp")))
            self.assertEqual([], list(Path(directory).glob(".*.bak")))

    def test_output_pair_preserves_foreign_exclusive_temp(self) -> None:
        from fiction_forks.cli import _write_output_pair

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "result.json"
            second = Path(directory) / "bundle.json"
            foreign_temp = Path(directory) / ".bundle.json.tmp"
            original_open = Path.open

            def race_exclusive_open(path: Path, *args, **kwargs):
                if path == foreign_temp and args and args[0] == "xb":
                    foreign_temp.write_text("foreign-owner\n", encoding="utf-8")
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", race_exclusive_open):
                with self.assertRaisesRegex(ContractError, "not committed"):
                    _write_output_pair(
                        str(first),
                        "new-result",
                        str(second),
                        "new-bundle",
                        overwrite=False,
                    )
            self.assertFalse(first.exists())
            self.assertFalse(second.exists())
            self.assertEqual(
                "foreign-owner\n", foreign_temp.read_text(encoding="utf-8")
            )

    def test_output_pair_preserves_foreign_fixed_backup(self) -> None:
        from fiction_forks.cli import _write_output_pair

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "result.json"
            second = Path(directory) / "bundle.json"
            first.write_text("old-result\n", encoding="utf-8")
            second.write_text("old-bundle\n", encoding="utf-8")
            foreign_backup = Path(directory) / ".result.json.bak"
            foreign_backup.write_text("foreign-backup\n", encoding="utf-8")

            _write_output_pair(
                str(first),
                "new-result",
                str(second),
                "new-bundle",
                overwrite=True,
            )

            self.assertEqual("new-result\n", first.read_text(encoding="utf-8"))
            self.assertEqual("new-bundle\n", second.read_text(encoding="utf-8"))
            self.assertEqual(
                "foreign-backup\n", foreign_backup.read_text(encoding="utf-8")
            )

    def test_output_pair_does_not_overwrite_replaced_target_during_rollback(
        self,
    ) -> None:
        from fiction_forks.cli import _write_output_pair

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "result.json"
            second = Path(directory) / "bundle.json"
            first.write_text("old-result\n", encoding="utf-8")
            second.write_text("old-bundle\n", encoding="utf-8")
            original_replace = Path.replace

            def replace_then_fail(path: Path, target: Path):
                if path.name == ".bundle.json.tmp":
                    first.unlink()
                    first.write_text("concurrent-owner\n", encoding="utf-8")
                    raise OSError("simulated concurrent replacement")
                return original_replace(path, target)

            with patch.object(Path, "replace", replace_then_fail):
                with self.assertRaisesRegex(ContractError, "rollback was incomplete"):
                    _write_output_pair(
                        str(first),
                        "new-result",
                        str(second),
                        "new-bundle",
                        overwrite=True,
                    )

            self.assertEqual("concurrent-owner\n", first.read_text(encoding="utf-8"))
            self.assertEqual("old-bundle\n", second.read_text(encoding="utf-8"))
            self.assertEqual(1, len(list(Path(directory).glob(".result.json.*.bak"))))

    def test_installed_ownership_rejects_reused_inode_with_foreign_bytes(
        self,
    ) -> None:
        from fiction_forks.cli import _owns_installed_target

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            payload = b"new-result\n"
            path.write_bytes(payload)
            stat = path.stat()
            entry = {
                "staged_identity": (stat.st_dev, stat.st_ino),
                "staged_digest": hashlib.sha256(payload).hexdigest(),
            }
            path.unlink()
            path.write_bytes(b"concurrent-owner\n")
            reused = path.stat()
            entry["staged_identity"] = (reused.st_dev, reused.st_ino)
            self.assertFalse(_owns_installed_target(entry, path))


def subprocess_result(stdout: str):
    return type("Completed", (), {"stdout": stdout})()


if __name__ == "__main__":
    unittest.main()
