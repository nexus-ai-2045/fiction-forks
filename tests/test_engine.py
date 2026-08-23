from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fiction_forks.engine import (
    ContractError,
    compare_worlds,
    load_json,
    simulate,
    validate_intervention,
    validate_scenario,
)


class SimulationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = load_json(ROOT / "scenarios/japan-2036/scenario.json")
        cls.intervention = load_json(ROOT / "interventions/doraemon-public-tools.json")

    def test_same_seed_is_reproducible(self) -> None:
        first = simulate(self.scenario, seed=2036)
        second = simulate(self.scenario, seed=2036)
        self.assertEqual(first, second)

    def test_baseline_collapses_from_declared_gate(self) -> None:
        result = simulate(self.scenario, seed=2036)
        self.assertTrue(result["collapsed"])
        self.assertEqual(2036, result["collapse_year"])
        gate = result["timeline"][-1]["collapse_gate"]
        self.assertGreaterEqual(len(gate["breached_metrics"]), 2)
        self.assertEqual(2, gate["consecutive_danger_turns"])

    def test_intervention_waits_for_technology_tree(self) -> None:
        result = simulate(self.scenario, self.intervention, seed=2036)
        self.assertEqual(2032, result["activation_year"])
        self.assertEqual(
            {
                "joint-governance-and-drills": 2032,
                "local-data-governance": 2030,
                "public-ai-reference-stack": 2029,
                "regional-fabrication-cells": 2030,
            },
            result["technology_schedule"],
        )
        before = [
            event
            for turn in result["timeline"]
            if turn["year"] < 2032
            for event in turn["events"]
            if event["kind"].startswith("intervention")
        ]
        self.assertEqual([], before)

    def test_cyclic_technology_tree_fails_closed(self) -> None:
        broken = json.loads(json.dumps(self.intervention))
        broken["technology_tree"]["nodes"][0]["depends_on"] = [
            "joint-governance-and-drills"
        ]
        broken["prerequisites"].remove("auditable_public_ai")
        with self.assertRaisesRegex(ContractError, "cycle"):
            simulate(self.scenario, broken)

    def test_technology_delay_can_miss_intervention_window(self) -> None:
        result = simulate(
            self.scenario,
            self.intervention,
            seed=2036,
            technology_delays={"joint-governance-and-drills": 5},
        )
        self.assertEqual(2037, result["activation_year"])
        self.assertTrue(result["collapsed"])
        self.assertEqual(2036, result["collapse_year"])

    def test_technology_node_requires_completion_evidence(self) -> None:
        broken = json.loads(json.dumps(self.intervention))
        del broken["technology_tree"]["nodes"][0]["completion_evidence"]
        with self.assertRaisesRegex(ContractError, "completion_evidence"):
            simulate(self.scenario, broken)

    def test_example_fork_changes_outcome_and_keeps_declared_costs(self) -> None:
        result = compare_worlds(self.scenario, self.intervention, seed=2036)
        self.assertTrue(result["baseline"]["collapsed"])
        self.assertFalse(result["fork"]["collapsed"])
        delta = result["state_delta_at_comparison_year"]
        self.assertLess(delta["living_systems"], 0)
        self.assertGreater(delta["repair_capacity"], 0)
        self.assertTrue(result["declared_side_effects"])
        self.assertTrue(result["declared_failure_modes"])
        self.assertEqual(2036, result["comparison_year"])

    def test_all_versioned_inputs_satisfy_contract(self) -> None:
        scenarios = [load_json(path) for path in (ROOT / "scenarios").rglob("*.json")]
        self.assertTrue(scenarios)
        for scenario in scenarios:
            validate_scenario(scenario)
        for path in (ROOT / "interventions").glob("*.json"):
            validate_intervention(load_json(path), self.scenario)

    def test_unknown_metric_fails_closed(self) -> None:
        broken = json.loads(json.dumps(self.scenario))
        broken["baseline_annual_effects"]["unknown_metric"] = 1
        with self.assertRaises(ContractError):
            simulate(broken)

    def test_public_files_do_not_contain_windows_home_path(self) -> None:
        forbidden = "C:" + os.sep + "Users" + os.sep
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            if path.suffix.lower() not in {".md", ".py", ".json", ".toml", ".txt", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, text, str(path))


if __name__ == "__main__":
    unittest.main()
