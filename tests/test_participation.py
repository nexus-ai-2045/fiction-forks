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
    prepare_provisional_request,
    validate_idea_draft,
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
        "unresolved_conditions": ["本人確認"],
        "side_effect_candidates": ["単一技術依存"],
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
        self.assertEqual(normalized["catalog_version"], 1)
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
            idea_draft(), self.catalog, root=ROOT,
            template_id="public-tools-access.v1", seed=2036, delay_profile="none",
        )
        second = prepare_provisional_request(
            idea_draft(idea_summary="別の自由記述"), self.catalog, root=ROOT,
            template_id="public-tools-access.v1", seed=2036, delay_profile="none",
        )
        self.assertEqual(first["schema_version"], RUN_SUMMARY_SCHEMA)
        self.assertEqual(first["status"], "ready")
        self.assertEqual(first["request"]["schema_version"], PROVISIONAL_REQUEST_SCHEMA)
        self.assertEqual(first["request_digest"], second["request_digest"])
        self.assertNotIn("idea_summary", first["request"])

    def test_unmapped_idea_returns_not_simulatable_without_numbers(self) -> None:
        result = prepare_provisional_request(
            idea_draft(abstract_function="未知の効果を自由に生成する"),
            self.catalog, root=ROOT, template_id="public-tools-access.v1",
            seed=2036, delay_profile="none",
        )
        self.assertEqual(result["status"], "not-simulatable")
        self.assertNotIn("request", result)
        self.assertNotIn("engine_version", result)

    def test_unapproved_seed_is_not_simulatable(self) -> None:
        result = prepare_provisional_request(
            idea_draft(), self.catalog, root=ROOT,
            template_id="public-tools-access.v1", seed=9999, delay_profile="none",
        )
        self.assertEqual(result["status"], "not-simulatable")
        self.assertIn("seed", result["missing_conditions"][0])


if __name__ == "__main__":
    unittest.main()
