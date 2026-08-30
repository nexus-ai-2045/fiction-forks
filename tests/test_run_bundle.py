from __future__ import annotations

import hashlib
import io
import json
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

from fiction_forks.engine import load_json
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


def subprocess_result(stdout: str):
    return type("Completed", (), {"stdout": stdout})()


if __name__ == "__main__":
    unittest.main()
