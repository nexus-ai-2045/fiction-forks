from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from fiction_forks.engine import ContractError
from fiction_forks.participation import (
    IDEA_DRAFT_SCHEMA,
    PROVISIONAL_REQUEST_SCHEMA,
    RUN_SUMMARY_SCHEMA,
    TEMPLATE_CONFIRMATION_SCHEMA,
    prepare_provisional_request,
    validate_idea_draft,
    validate_idea_status_projection,
    validate_provisional_request,
    validate_template_catalog,
)


ROOT = Path(__file__).resolve().parents[1]


def idea_draft(**updates):
    value = {
        "schema_version": IDEA_DRAFT_SCHEMA,
        "entry_kind": "work",
        "dialogue_mode": "guided",
        "work_reference": "ドラえもん",
        "idea_summary": "高度な道具を公共インフラとして使う",
        "abstract_function": "高度な道具へのアクセスを監査可能な公共基盤として広げる",
        "target_doom": "生活基盤と戦略的自律性の破滅連鎖",
        "unresolved_conditions": [],
        "side_effect_candidates": ["単一技術依存"],
        "user_confirmed": True,
    }
    value.update(updates)
    return value


def template_confirmation(**updates):
    value = {
        "schema_version": TEMPLATE_CONFIRMATION_SCHEMA,
        "template_id": "public-tools-access.v1",
        "template_version": 2,
        "intervention_sha256": "2e116cde3f8ad9547261cc58fd1b88c594f8bbefcc0d34961687dc47d21cf455",
        "user_confirmed": True,
    }
    value.update(updates)
    return value


class ParticipationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads(
            (ROOT / "catalogs/intervention-templates.v1.json").read_text(
                encoding="utf-8"
            )
        )

    def test_confirmed_draft_is_normalized(self) -> None:
        normalized = validate_idea_draft(idea_draft())
        self.assertEqual(normalized["schema_version"], IDEA_DRAFT_SCHEMA)
        self.assertEqual(normalized["dialogue_mode"], "guided")

    def test_unconfirmed_draft_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "confirmed"):
            validate_idea_draft(idea_draft(user_confirmed=False))

    def test_unknown_fields_cannot_smuggle_engine_inputs(self) -> None:
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_idea_draft(idea_draft(metric_delta={"legitimacy": 100}))

    def test_catalog_is_read_back_against_fixed_interventions(self) -> None:
        normalized = validate_template_catalog(self.catalog, root=ROOT)
        self.assertEqual(normalized["catalog_version"], 2)
        self.assertEqual(len(normalized["templates"]), 2)

    def test_catalog_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an object"):
            validate_template_catalog([], root=ROOT)

    def test_catalog_rejects_intervention_hash_drift(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["templates"][0]["intervention_sha256"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "sha256 mismatch"):
            validate_template_catalog(catalog, root=ROOT)

    def test_catalog_rejects_unknown_fields(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["templates"][0]["provider"] = "arbitrary"
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_template_catalog(catalog, root=ROOT)

    def test_confirmed_exact_mapping_creates_stable_request(self) -> None:
        first = prepare_provisional_request(
            idea_draft(), self.catalog, template_confirmation(), root=ROOT,
            template_id="public-tools-access.v1", seed=2036, delay_profile="none",
        )
        second = prepare_provisional_request(
            idea_draft(idea_summary="別の自由記述"), self.catalog,
            template_confirmation(), root=ROOT,
            template_id="public-tools-access.v1", seed=2036, delay_profile="none",
        )
        self.assertEqual(first["schema_version"], RUN_SUMMARY_SCHEMA)
        self.assertEqual(first["status"], "ready")
        self.assertEqual(first["request"]["schema_version"], PROVISIONAL_REQUEST_SCHEMA)
        self.assertEqual(first["request_digest"], second["request_digest"])
        self.assertNotIn("idea_summary", first["request"])
        self.assertIn("intervention_sha256", first["request"])
        self.assertEqual(
            validate_provisional_request(first["request"], self.catalog, root=ROOT),
            first["request"],
        )

    def test_unmapped_idea_returns_not_simulatable_without_numbers(self) -> None:
        result = prepare_provisional_request(
            idea_draft(abstract_function="未知の効果を自由に生成する"),
            self.catalog, template_confirmation(), root=ROOT,
            template_id="public-tools-access.v1",
            seed=2036, delay_profile="none",
        )
        self.assertEqual(result["status"], "not-simulatable")
        self.assertNotIn("request", result)
        self.assertNotIn("engine_version", result)

    def test_unapproved_seed_is_not_simulatable(self) -> None:
        result = prepare_provisional_request(
            idea_draft(), self.catalog, template_confirmation(), root=ROOT,
            template_id="public-tools-access.v1", seed=9999, delay_profile="none",
        )
        self.assertEqual(result["status"], "not-simulatable")
        self.assertIn("seed", result["missing_conditions"][0])

    def test_incomplete_mapping_is_not_simulatable(self) -> None:
        for updates in (
            {"target_doom": "別の破滅"},
            {"side_effect_candidates": ["未知の副作用"]},
            {"unresolved_conditions": ["制度設計が未解決"]},
        ):
            with self.subTest(updates=updates):
                result = prepare_provisional_request(
                    idea_draft(**updates),
                    self.catalog,
                    template_confirmation(),
                    root=ROOT,
                    template_id="public-tools-access.v1",
                    seed=2036,
                    delay_profile="none",
                )
                self.assertEqual(result["status"], "not-simulatable")

    def test_template_selection_requires_bound_confirmation(self) -> None:
        with self.assertRaisesRegex(ContractError, "confirmation"):
            prepare_provisional_request(
                idea_draft(), self.catalog,
                template_confirmation(template_id="other.v1"), root=ROOT,
                template_id="public-tools-access.v1", seed=2036,
                delay_profile="none",
            )

    def test_catalog_rejects_unknown_scenario(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["templates"][0]["scenario_id"] = "missing-scenario"
        with self.assertRaisesRegex(ContractError, "scenario_id"):
            validate_template_catalog(catalog, root=ROOT)

    def test_external_request_rejects_unknown_fields_and_drift(self) -> None:
        ready = prepare_provisional_request(
            idea_draft(), self.catalog, template_confirmation(), root=ROOT,
            template_id="public-tools-access.v1", seed=2036,
            delay_profile="none",
        )["request"]
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_provisional_request(
                {**ready, "metric_delta": 100}, self.catalog, root=ROOT
            )
        with self.assertRaisesRegex(ContractError, "intervention_id"):
            validate_provisional_request(
                {**ready, "intervention_id": "other"}, self.catalog, root=ROOT
            )

    def test_issue_12_is_listed_without_false_progress(self) -> None:
        projection = json.loads(
            (ROOT / "catalogs/idea-status.v1.json").read_text(encoding="utf-8")
        )
        validated = validate_idea_status_projection(projection)
        idea = validated["ideas"][0]
        self.assertEqual(idea["issue_number"], 12)
        self.assertEqual(idea["simulation_status"], "not-ready")
        self.assertEqual(
            idea["lifecycle"],
            {
                "listed": True,
                "assigned": False,
                "implemented": False,
                "simulated": False,
                "reported_back": False,
            },
        )

    def test_idea_lifecycle_cannot_skip_implementation(self) -> None:
        projection = json.loads(
            (ROOT / "catalogs/idea-status.v1.json").read_text(encoding="utf-8")
        )
        projection["ideas"][0]["lifecycle"]["simulated"] = True
        with self.assertRaisesRegex(ContractError, "cannot skip states"):
            validate_idea_status_projection(projection)

    def test_simulation_status_must_match_lifecycle(self) -> None:
        projection = json.loads(
            (ROOT / "catalogs/idea-status.v1.json").read_text(encoding="utf-8")
        )
        projection["ideas"][0]["simulation_status"] = "official"
        projection["ideas"][0]["missing_conditions"] = []
        with self.assertRaisesRegex(ContractError, "simulation_status"):
            validate_idea_status_projection(projection)

    def test_next_action_must_be_a_string(self) -> None:
        projection = json.loads(
            (ROOT / "catalogs/idea-status.v1.json").read_text(encoding="utf-8")
        )
        projection["ideas"][0]["next_action"] = None
        with self.assertRaisesRegex(ContractError, "next_action"):
            validate_idea_status_projection(projection)


if __name__ == "__main__":
    unittest.main()
