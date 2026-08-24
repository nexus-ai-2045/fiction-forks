from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fiction_forks.engine import compare_worlds, load_json, simulate
from fiction_forks.cli import main as cli_main
from fiction_forks.providers import FixtureProvider, ReplayProvider
from fiction_forks.social import replay_equivalent, run_social_simulation


class WorldObservationForkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = load_json(ROOT / "scenarios/japan-2036/scenario.json")
        cls.intervention = load_json(
            ROOT / "interventions/haruhi-world-observation.json"
        )
        cls.social_config = load_json(
            ROOT / "scenarios/japan-2036/social-world-observation.json"
        )
        cls.fixture_path = (
            ROOT / "fixtures/social/japan-2036-world-observation.jsonl"
        )

    def test_same_seed_baseline_and_observation_fork_are_comparable(self) -> None:
        result = compare_worlds(
            self.scenario,
            self.intervention,
            seed=2036,
        )
        self.assertEqual(2036, result["seed"])
        self.assertTrue(result["baseline"]["collapsed"])
        self.assertFalse(result["fork"]["collapsed"])
        self.assertGreater(
            result["state_delta_at_comparison_year"]["cognitive_sovereignty"],
            0,
        )
        self.assertGreater(
            result["state_delta_at_comparison_year"]["repair_capacity"],
            0,
        )
        self.assertLess(
            result["state_delta_at_comparison_year"]["living_systems"],
            0,
        )

    def test_technology_institution_and_operations_gate_activation(self) -> None:
        result = simulate(self.scenario, self.intervention, seed=2036)
        self.assertEqual(2032, result["activation_year"])
        self.assertEqual(
            {
                "federated-observation-probes": 2029,
                "observation-data-charter": 2030,
                "local-verification-labs": 2030,
                "contested-evidence-protocol": 2031,
                "cross-observer-anomaly-drills": 2032,
            },
            result["technology_schedule"],
        )

    def test_delayed_contestation_misses_the_intervention_window(self) -> None:
        result = compare_worlds(
            self.scenario,
            self.intervention,
            seed=2036,
            technology_delays={"contested-evidence-protocol": 5},
        )
        self.assertEqual(2037, result["fork"]["activation_year"])
        self.assertTrue(result["fork"]["collapsed"])
        self.assertEqual(2036, result["fork"]["collapse_year"])

    def test_fixture_dialogue_is_bounded_reproducible_and_replayable(self) -> None:
        provider = FixtureProvider.from_jsonl(self.fixture_path)
        first = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            provider,
            seed=2036,
        )
        second = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            FixtureProvider.from_jsonl(self.fixture_path),
            seed=2036,
        )
        self.assertEqual(first, second)
        self.assertEqual(5, len(first["roles"]))
        self.assertEqual(3, first["turn_count"])
        self.assertEqual(15, first["metrics"]["action_count"])
        self.assertEqual(0, first["metrics"]["invalid_action_count"])
        self.assertTrue(
            all(delay == 0 for delay in first["technology_delays"].values())
        )
        self.assertFalse(first["world_comparison"]["fork"]["collapsed"])
        replay = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            ReplayProvider(first),
            seed=2036,
        )
        self.assertTrue(replay_equivalent(first, replay))

    def test_curated_artifacts_match_declared_inputs(self) -> None:
        manifest = json.loads(
            (
                ROOT
                / "artifacts/runs/haruhi-world-observation-fixture.manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(manifest["ai_measured"])
        for name, expected_delays in (
            ("haruhi-world-observation-comparison.json", {}),
            (
                "haruhi-world-observation-contestation-delay.json",
                {"contested-evidence-protocol": 5},
            ),
        ):
            with self.subTest(name=name):
                artifact = json.loads(
                    (ROOT / "artifacts/runs" / name).read_text(encoding="utf-8")
                )
                self.assertEqual(2036, artifact["seed"])
                self.assertEqual("haruhi-world-observation", artifact["intervention_id"])
                self.assertEqual(expected_delays, artifact["fork"]["technology_delays"])
                path = ROOT / "artifacts/runs" / name
                manifest_hash_key = (
                    "comparison_artifact_sha256"
                    if not expected_delays
                    else "delay_artifact_sha256"
                )
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    manifest[manifest_hash_key],
                )

        social = json.loads(
            (
                ROOT
                / "artifacts/runs/haruhi-world-observation-fixture.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual("fixture", social["provider"]["name"])
        self.assertEqual("haruhi-world-observation", social["intervention_id"])
        self.assertEqual(2036, social["seed"])
        self.assertEqual(0, social["metrics"]["invalid_action_count"])
        self.assertEqual(social["run_id"], manifest["run_id"])
        self.assertEqual(social["input_digest"], manifest["input_digest"])
        self.assertEqual(social["final_event_hash"], manifest["final_event_hash"])
        self.assertEqual(
            hashlib.sha256(
                (
                    ROOT
                    / "artifacts/runs/haruhi-world-observation-fixture.json"
                ).read_bytes()
            ).hexdigest(),
            manifest["artifact_sha256"],
        )

    def test_compare_output_is_atomic_and_requires_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "comparison.json"
            args = [
                "compare",
                "--scenario",
                str(ROOT / "scenarios/japan-2036/scenario.json"),
                "--intervention",
                str(ROOT / "interventions/haruhi-world-observation.json"),
                "--seed",
                "2036",
                "--output",
                str(output),
            ]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(0, cli_main(args))
                self.assertEqual(2, cli_main(args))
                self.assertEqual(0, cli_main([*args, "--overwrite"]))
            artifact = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("haruhi-world-observation", artifact["intervention_id"])
            self.assertNotIn(b"\r\n", output.read_bytes())


if __name__ == "__main__":
    unittest.main()
