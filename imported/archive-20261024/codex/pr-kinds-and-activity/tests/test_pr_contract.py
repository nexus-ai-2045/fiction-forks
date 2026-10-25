from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fiction_forks.pr_contract import (
    Change,
    ContractError,
    ContractResult,
    pr_kind,
    render_worldline_summary,
    validate_contract,
)


class PullRequestContractTests(unittest.TestCase):
    def test_pr_kind_requires_exactly_one_marker(self) -> None:
        self.assertEqual(
            pr_kind("<!-- fiction-forks-pr-type: worldline -->"), "worldline"
        )
        with self.assertRaises(ContractError):
            pr_kind("")
        with self.assertRaises(ContractError):
            pr_kind(
                "<!-- fiction-forks-pr-type: worldline -->\n"
                "<!-- fiction-forks-pr-type: maintenance -->"
            )

    def test_worldline_requires_one_intervention_and_matching_social_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = (
                "interventions/test-lens.json",
                "scenarios/japan-2036/social-test-lens.json",
                "fixtures/social/test-lens.jsonl",
            )
            for relative in expected:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            result = validate_contract(
                "worldline",
                [Change("A", path) for path in expected],
                root=root,
            )
        self.assertEqual(result.slug, "test-lens")
        self.assertEqual(result.social_config, expected[1])
        self.assertEqual(result.fixture, expected[2])

    def test_worldline_rejects_missing_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            intervention = root / "interventions/test-lens.json"
            intervention.parent.mkdir(parents=True)
            intervention.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "fixture"):
                validate_contract(
                    "worldline",
                    [Change("A", "interventions/test-lens.json")],
                    root=root,
                )

    def test_maintenance_rejects_new_worldline_input(self) -> None:
        with self.assertRaisesRegex(ContractError, "maintenance"):
            validate_contract(
                "maintenance",
                [Change("A", "interventions/new-world.json")],
                root=Path("."),
            )

    def test_idea_files_are_never_pull_request_content(self) -> None:
        with self.assertRaisesRegex(ContractError, "idea Issue"):
            validate_contract(
                "maintenance",
                [Change("A", "ideas/example.md")],
                root=Path("."),
            )

    def test_worldline_summary_names_author_and_fixture_boundary(self) -> None:
        event = {
            "number": 12,
            "pull_request": {
                "number": 12,
                "title": "未来分岐を追加",
                "user": {"login": "participant"},
            },
        }
        artifact = {
            "provider": {"name": "fixture", "model": None},
            "roles": ["a", "b", "c", "d", "e"],
            "turn_count": 3,
            "actions": [{"valid": True}, {"valid": False}],
            "world_comparison": {
                "baseline": {"collapsed": True, "collapse_year": 2036},
                "fork": {"collapsed": False, "activation_year": 2032},
                "state_delta_at_comparison_year": {"repair_capacity": 10.0},
            },
        }
        summary = render_worldline_summary(
            event, ContractResult(kind="worldline", slug="test-lens"), artifact
        )
        self.assertIn("@participant", summary)
        self.assertIn("5役 × 3ターン", summary)
        self.assertIn("1/2 valid", summary)
        self.assertIn("live LLMではありません", summary)


if __name__ == "__main__":
    unittest.main()
