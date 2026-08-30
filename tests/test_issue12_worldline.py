from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fiction_forks.engine import compare_worlds, load_json, simulate, validate_intervention
from fiction_forks.providers import FixtureProvider, ReplayProvider
from fiction_forks.social import replay_equivalent, run_social_simulation


CANDIDATE = ROOT / "evaluation/worldline-issue12"
FORBIDDEN = (
    "タケコプター",
    "たけこぷたー",
    "のび太",
    "ドラえもん!",
    "夢のロボット",
)


class Issue12WorldlineCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = load_json(ROOT / "scenarios/japan-2036/scenario.json")
        cls.intervention = load_json(CANDIDATE / "low-altitude-public-mobility.json")
        cls.social_config = load_json(
            CANDIDATE / "social-low-altitude-public-mobility.json"
        )
        cls.fixture_path = CANDIDATE / "low-altitude-public-mobility.jsonl"

    def test_candidate_stays_outside_merged_worldline_paths(self) -> None:
        self.assertFalse(
            (ROOT / "interventions/low-altitude-public-mobility.json").exists()
        )
        self.assertTrue(CANDIDATE.joinpath("low-altitude-public-mobility.json").is_file())

    def test_function_is_institutional_and_avoids_character_imitation(self) -> None:
        validate_intervention(self.intervention, self.scenario)
        self.assertEqual("institutional_equivalent", self.intervention["realization_mode"])
        self.assertIn("近距離の低空移動", self.intervention["extracted_function"])
        self.assertNotIn("便利", self.intervention["extracted_function"])
        kinds = {node["kind"] for node in self.intervention["technology_tree"]["nodes"]}
        self.assertEqual({"technology", "institution", "operations"}, kinds)
        self.assertGreaterEqual(len(self.intervention["costs"]), 2)
        self.assertGreaterEqual(len(self.intervention["side_effects"]), 3)
        self.assertGreaterEqual(len(self.intervention["failure_modes"]), 3)
        blob = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                CANDIDATE / "low-altitude-public-mobility.json",
                CANDIDATE / "social-low-altitude-public-mobility.json",
                CANDIDATE / "low-altitude-public-mobility.jsonl",
            )
        )
        for phrase in FORBIDDEN:
            self.assertNotIn(phrase, blob)

    def test_same_seed_comparison_is_reproducible_and_not_only_success(self) -> None:
        first = compare_worlds(self.scenario, self.intervention, seed=2036)
        second = compare_worlds(self.scenario, self.intervention, seed=2036)
        self.assertEqual(first, second)
        self.assertTrue(first["baseline"]["collapsed"])
        self.assertFalse(first["fork"]["collapsed"])
        self.assertLess(first["state_delta_at_comparison_year"]["living_systems"], 0)
        self.assertGreater(first["state_delta_at_comparison_year"]["repair_capacity"], 0)
        delayed = compare_worlds(
            self.scenario,
            self.intervention,
            seed=2036,
            technology_delays={"child-consent-and-airspace-charter": 5},
        )
        self.assertEqual(2037, delayed["fork"]["activation_year"])
        self.assertTrue(delayed["fork"]["collapsed"])
        self.assertEqual(2036, delayed["fork"]["collapse_year"])

    def test_schedule_requires_consent_before_activation(self) -> None:
        result = simulate(self.scenario, self.intervention, seed=2036)
        self.assertEqual(2032, result["activation_year"])
        self.assertEqual(2030, result["technology_schedule"]["child-consent-and-airspace-charter"])
        self.assertEqual(2032, result["technology_schedule"]["joint-search-rescue-drills"])

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
        self.assertTrue(all(delay == 0 for delay in first["technology_delays"].values()))
        self.assertFalse(first["world_comparison"]["fork"]["collapsed"])
        replay = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            ReplayProvider(first),
            seed=2036,
        )
        self.assertTrue(replay_equivalent(first, replay))
        for receipt in first["actions"]:
            self.assertTrue(receipt["action"]["text_redacted"])
            self.assertNotIn("text", receipt["action"])
            self.assertNotIn("conditions", receipt["action"])


if __name__ == "__main__":
    unittest.main()
