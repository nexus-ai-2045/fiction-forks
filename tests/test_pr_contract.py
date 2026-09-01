from __future__ import annotations

import hashlib
import json
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


FIXED_PREVIEW_INTERVENTION = {
    "id": "fixed-preview",
    "technology_tree": {"nodes": []},
}
FIXED_PREVIEW_SOCIAL_CONFIG = {
    "schema_version": "fiction_forks_social_config.v1",
    "id": "fixed-preview-dialogue",
    "title": "fixed preview dialogue",
    "assumption_notice": "テスト用の固定social configです。",
    "turns": [{"id": "turn-1", "event": "fixed preview turn"}],
    "roles": [
        {
            "id": "role-1",
            "title": "role one",
            "objective": "observe",
            "private_context": "none",
        },
        {
            "id": "role-2",
            "title": "role two",
            "objective": "observe",
            "private_context": "none",
        },
    ],
    "evidence": [],
    "actions": [
        {
            "id": "abstain",
            "title": "abstain",
            "allowed_roles": ["role-1", "role-2"],
            "capability": "none",
            "reversible": True,
        }
    ],
    "node_requirements": {},
    "missing_action_delay_years": 1,
}
FIXED_PREVIEW_FIXTURE = [
    {"turn": 1, "agent_id": "role-1"},
    {"turn": 1, "agent_id": "role-2"},
]


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


class PullRequestContractTests(unittest.TestCase):
    def _write_preview_catalog(
        self, root: Path, *, digest_override: str | None = None
    ) -> str:
        intervention_path = root / "interventions/fixed-preview.json"
        intervention_path.parent.mkdir(parents=True, exist_ok=True)
        intervention_path.write_text(
            json.dumps(FIXED_PREVIEW_INTERVENTION), encoding="utf-8"
        )
        digest = _canonical_digest(FIXED_PREVIEW_INTERVENTION)
        social_config_path = root / "scenarios/test/social-fixed-preview.json"
        social_config_path.parent.mkdir(parents=True, exist_ok=True)
        social_config_path.write_text(
            json.dumps(FIXED_PREVIEW_SOCIAL_CONFIG), encoding="utf-8"
        )
        fixture_path = root / "fixtures/social/fixed-preview.jsonl"
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(
            "\n".join(json.dumps(item) for item in FIXED_PREVIEW_FIXTURE) + "\n",
            encoding="utf-8",
        )
        catalog_path = root / "catalogs/intervention-templates.v1.json"
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        catalog_path.write_text(
            json.dumps(
                {
                    "schema_version": "fiction_forks_preview_template_catalog.v1",
                    "catalog_version": 1,
                    "catalog_id": "test-preview-templates",
                    "templates": [
                        {
                            "template_id": "fixed-preview.v1",
                            "template_version": 1,
                            "status": "preview_allowed",
                            "scenario_id": "japan-2036-centralization",
                            "intervention_id": "fixed-preview",
                            "intervention_path": "interventions/fixed-preview.json",
                            "intervention_sha256": digest_override or digest,
                            "social_config_path": "scenarios/test/social-fixed-preview.json",
                            "social_config_id": FIXED_PREVIEW_SOCIAL_CONFIG["id"],
                            "social_config_sha256": _canonical_digest(
                                FIXED_PREVIEW_SOCIAL_CONFIG
                            ),
                            "fixture_path": "fixtures/social/fixed-preview.jsonl",
                            "fixture_sha256": _canonical_digest(FIXED_PREVIEW_FIXTURE),
                            "abstract_function": "fixed preview",
                            "target_doom": "fixed doom",
                            "side_effect_candidates": ["fixed side effect"],
                            "requires_user_confirmation": True,
                            "idea_text_changes_engine_inputs": False,
                            "allowed_seeds": [2036],
                            "delay_profiles": ["none"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        scenario_path = root / "scenarios/test/scenario.json"
        scenario_path.parent.mkdir(parents=True, exist_ok=True)
        scenario_path.write_text(
            json.dumps({"id": "japan-2036-centralization"}), encoding="utf-8"
        )
        return "catalogs/intervention-templates.v1.json"

    def _write_worldline_inputs(
        self,
        root: Path,
        *,
        role_count: int = 5,
        turn_count: int = 3,
        omit_last_fixture: bool = False,
    ) -> tuple[str, str, str]:
        expected = (
            "interventions/test-lens.json",
            "scenarios/japan-2036/social-test-lens.json",
            "fixtures/social/test-lens.jsonl",
        )
        intervention = root / expected[0]
        intervention.parent.mkdir(parents=True, exist_ok=True)
        intervention.write_text("{}", encoding="utf-8")
        roles = [{"id": f"role-{index}"} for index in range(1, role_count + 1)]
        turns = [{"id": f"turn-{index}"} for index in range(1, turn_count + 1)]
        config = root / expected[1]
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            json.dumps({"roles": roles, "turns": turns}), encoding="utf-8"
        )
        entries = [
            {"turn": turn, "agent_id": role["id"]}
            for turn in range(1, turn_count + 1)
            for role in roles
        ]
        if omit_last_fixture:
            entries.pop()
        fixture = root / expected[2]
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(
            "\n".join(json.dumps(item) for item in entries) + "\n",
            encoding="utf-8",
        )
        return expected

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
            expected = self._write_worldline_inputs(root)
            result = validate_contract(
                "worldline",
                [Change("A", path) for path in expected],
                root=root,
            )
        self.assertEqual(result.slug, "test-lens")
        self.assertEqual(result.social_config, expected[1])
        self.assertEqual(result.fixture, expected[2])

    def test_worldline_requires_exact_five_role_three_turn_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = self._write_worldline_inputs(root, role_count=2, turn_count=1)
            with self.assertRaisesRegex(ContractError, "5役"):
                validate_contract(
                    "worldline",
                    [Change("A", path) for path in expected],
                    root=root,
                )

    def test_worldline_fixture_requires_all_fifteen_role_turn_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = self._write_worldline_inputs(root, omit_last_fixture=True)
            with self.assertRaisesRegex(ContractError, "15組"):
                validate_contract(
                    "worldline",
                    [Change("A", path) for path in expected],
                    root=root,
                )

    def test_worldline_rejects_maintenance_owned_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = self._write_worldline_inputs(root)
            with self.assertRaisesRegex(ContractError, "保守変更"):
                validate_contract(
                    "worldline",
                    [Change("A", path) for path in expected]
                    + [Change("M", "src/fiction_forks/engine.py")],
                    root=root,
                )

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

    def test_maintenance_validates_preview_catalog_as_explicit_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self._write_preview_catalog(root)
            result = validate_contract(
                "maintenance",
                [Change("A", catalog), Change("M", "docs/architecture.md")],
                root=root,
            )
        self.assertEqual(result.kind, "maintenance")

    def test_maintenance_rejects_preview_catalog_digest_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self._write_preview_catalog(root, digest_override="0" * 64)
            with self.assertRaisesRegex(ContractError, "sha256"):
                validate_contract(
                    "maintenance",
                    [Change("M", catalog)],
                    root=root,
                )

    def test_maintenance_accepts_preview_catalog_across_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self._write_preview_catalog(root)
            intervention_path = root / "interventions/fixed-preview.json"
            intervention_path.write_bytes(
                json.dumps(FIXED_PREVIEW_INTERVENTION, indent=2)
                .replace("\n", "\r\n")
                .encode("utf-8")
                + b"\r\n"
            )
            fixture_path = root / "fixtures/social/fixed-preview.jsonl"
            fixture_path.write_bytes(
                b"".join(
                    json.dumps(item).encode("utf-8") + b"\r\n"
                    for item in FIXED_PREVIEW_FIXTURE
                )
            )
            result = validate_contract(
                "maintenance",
                [Change("M", catalog)],
                root=root,
            )
        self.assertEqual(result.kind, "maintenance")

    def test_maintenance_rejects_unknown_catalog_path(self) -> None:
        with self.assertRaisesRegex(ContractError, "未登録のcatalog path"):
            validate_contract(
                "maintenance",
                [Change("A", "catalogs/unreviewed.json")],
                root=Path("."),
            )

    def test_maintenance_validates_idea_status_catalog_as_explicit_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "catalogs/idea-status.v1.json"
            catalog.parent.mkdir(parents=True)
            catalog.write_text(
                json.dumps(
                    {
                        "schema_version": "fiction_forks_idea_status_projection.v1",
                        "observed_at": "2026-08-28",
                        "repository": "nexus-ai-2045/fiction-forks",
                        "ideas": [],
                    }
                ),
                encoding="utf-8",
            )
            result = validate_contract(
                "maintenance",
                [Change("A", "catalogs/idea-status.v1.json")],
                root=root,
            )
        self.assertEqual(result.kind, "maintenance")

    def test_maintenance_rejects_invalid_idea_status_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "catalogs/idea-status.v1.json"
            catalog.parent.mkdir(parents=True)
            catalog.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "missing fields"):
                validate_contract(
                    "maintenance",
                    [Change("A", "catalogs/idea-status.v1.json")],
                    root=root,
                )

    def test_worldline_rejects_preview_catalog_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = self._write_worldline_inputs(root)
            catalog = self._write_preview_catalog(root)
            with self.assertRaisesRegex(ContractError, "maintenance PR"):
                validate_contract(
                    "worldline",
                    [Change("A", path) for path in expected]
                    + [Change("M", catalog)],
                    root=root,
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
            "actions": [{"valid": True} for _ in range(15)],
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
        self.assertIn("15/15 valid", summary)
        self.assertIn("live LLMではありません", summary)

    def test_worldline_summary_rejects_invalid_or_missing_actions(self) -> None:
        event = {
            "pull_request": {
                "number": 12,
                "title": "未来分岐を追加",
                "user": {"login": "participant"},
            }
        }
        artifact = {
            "provider": {"name": "fixture"},
            "roles": ["a", "b", "c", "d", "e"],
            "turn_count": 3,
            "actions": [{"valid": True} for _ in range(14)] + [{"valid": False}],
        }
        with self.assertRaisesRegex(ContractError, "15/15"):
            render_worldline_summary(
                event, ContractResult(kind="worldline", slug="test-lens"), artifact
            )


if __name__ == "__main__":
    unittest.main()
