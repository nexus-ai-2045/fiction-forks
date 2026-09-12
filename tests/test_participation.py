from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from fiction_forks.engine import ContractError
from fiction_forks.participation import (
    IDEA_DRAFT_SCHEMA,
    PROVISIONAL_REQUEST_SCHEMA,
    RUN_SUMMARY_SCHEMA,
    TEMPLATE_CONFIRMATION_SCHEMA,
    prepare_provisional_request,
    resolve_template_inputs,
    validate_idea_draft,
    validate_idea_status_projection,
    validate_provisional_request,
    validate_template_catalog,
)


ROOT = Path(__file__).resolve().parents[1]


def _symlinks_are_creatable() -> bool:
    """symlinkを1本張ってみて権限の有無を判定する（Windowsでは特権が要る）。"""
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "target"
        target.write_text("{}", encoding="utf-8")
        try:
            (Path(directory) / "link").symlink_to(target)
        except (NotImplementedError, OSError):
            return False
    return True


SYMLINKS_ARE_CREATABLE = _symlinks_are_creatable()


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
        "template_version": 3,
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
        self.assertEqual(normalized["catalog_version"], 3)
        self.assertEqual(len(normalized["templates"]), 2)

    def test_catalog_rejects_non_object_root(self) -> None:
        with self.assertRaisesRegex(ContractError, "must be an object"):
            validate_template_catalog([], root=ROOT)

    def test_catalog_rejects_intervention_hash_drift(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["templates"][0]["intervention_sha256"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "sha256 mismatch"):
            validate_template_catalog(catalog, root=ROOT)

    def test_catalog_restricts_preview_templates_to_executable_contracts(self) -> None:
        for update, message in (
            (
                {"intervention_path": "fixtures/participation/not-an-intervention.json"},
                "intervention_path",
            ),
            ({"delay_profiles": []}, "delay_profiles"),
            ({"side_effect_candidates": ["a", "b", "c", "d"]}, "at most 3"),
        ):
            with self.subTest(update=update):
                catalog = copy.deepcopy(self.catalog)
                catalog["templates"][0].update(update)
                with self.assertRaisesRegex(ContractError, message):
                    validate_template_catalog(catalog, root=ROOT)

    def test_catalog_rejects_social_config_and_fixture_drift(self) -> None:
        for update, message in (
            ({"social_config_sha256": "0" * 64}, "social_config_sha256 mismatch"),
            ({"fixture_sha256": "0" * 64}, "fixture_sha256 mismatch"),
            ({"social_config_id": "other-dialogue"}, "social_config_id mismatch"),
        ):
            with self.subTest(update=update):
                catalog = copy.deepcopy(self.catalog)
                catalog["templates"][0].update(update)
                with self.assertRaisesRegex(ContractError, message):
                    validate_template_catalog(catalog, root=ROOT)

    def test_catalog_rejects_unsafe_social_config_and_fixture_paths(self) -> None:
        for update, message in (
            (
                {"social_config_path": "scenarios/japan-2036/../../etc/social.json"},
                "social_config_path is unsafe",
            ),
            (
                {"social_config_path": "/etc/social.json"},
                "social_config_path is unsafe",
            ),
            (
                {"social_config_path": "scenarios/japan-2036/scenario.json"},
                "social_config_path is unsafe",
            ),
            (
                {"fixture_path": "fixtures/social/../../escape.jsonl"},
                "fixture_path is unsafe",
            ),
            (
                {"fixture_path": "fixtures/participation/public-tools-idea-draft.v1.json"},
                "fixture_path is unsafe",
            ),
        ):
            with self.subTest(update=update):
                catalog = copy.deepcopy(self.catalog)
                catalog["templates"][0].update(update)
                with self.assertRaisesRegex(ContractError, message):
                    validate_template_catalog(catalog, root=ROOT)

    @unittest.skipUnless(SYMLINKS_ARE_CREATABLE, "symlinkの作成権限が無い")
    def test_repo_path_guard_rejects_targets_that_do_not_stay_under_root(self) -> None:
        """公開入口から、symlinkでrootを脱出するpathを拒否することを検査する。"""
        catalog = copy.deepcopy(self.catalog)
        catalog["templates"][0]["intervention_path"] = "interventions/escape.json"
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            root = Path(directory) / "repo"
            (root / "interventions").mkdir(parents=True)
            (root / "interventions/escape.json").symlink_to(outside)
            with self.assertRaisesRegex(ContractError, "escapes root"):
                validate_template_catalog(catalog, root=root)

    def _catalog_input_relatives(self) -> list[str]:
        """catalogがsha256でpinしているrepo相対pathと、参照先scenarioを列挙する。"""
        relatives = ["scenarios/japan-2036/scenario.json"]
        for template in self.catalog["templates"]:
            relatives.extend(
                template[field]
                for field in ("intervention_path", "social_config_path", "fixture_path")
            )
        return relatives

    def _copy_catalog_inputs(
        self, root: Path, relatives: list[str], *, newline: bytes
    ) -> Path:
        """catalogの入力fileを、指定した改行コードへ揃えてtmp rootへ複製する。"""
        for relative in relatives:
            source = (ROOT / relative).read_bytes()
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                source.replace(b"\r\n", b"\n").replace(b"\n", newline)
            )
        return root

    def test_catalog_digests_survive_crlf_rewrites(self) -> None:
        """LF版とCRLF版をtmpへ明示的に作り、どちらでもdigestが一致することを検査する。

        catalogがpinしているtracked fileは書き換えない。checkoutの改行コードが
        片方に寄っていると、repo上のfileを書き戻す形では何も検査できない。
        """
        relatives = self._catalog_input_relatives()
        with tempfile.TemporaryDirectory() as directory:
            roots = {
                newline: self._copy_catalog_inputs(
                    Path(directory) / name, relatives, newline=newline
                )
                for name, newline in (("lf", b"\n"), ("crlf", b"\r\n"))
            }
            for relative in relatives:
                with self.subTest(relative=relative):
                    self.assertNotEqual(
                        (roots[b"\n"] / relative).read_bytes(),
                        (roots[b"\r\n"] / relative).read_bytes(),
                    )
            normalized = [
                validate_template_catalog(self.catalog, root=roots[newline])
                for newline in (b"\n", b"\r\n")
            ]
            self.assertEqual(len(normalized[0]["templates"]), 2)
            self.assertEqual(normalized[0], normalized[1])

    def test_catalog_binds_each_social_config_to_its_own_intervention(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        borrowed = catalog["templates"][0]
        catalog["templates"][1].update(
            {
                "social_config_path": borrowed["social_config_path"],
                "social_config_id": borrowed["social_config_id"],
                "social_config_sha256": borrowed["social_config_sha256"],
            }
        )
        with self.assertRaisesRegex(ContractError, "node_requirements"):
            validate_template_catalog(catalog, root=ROOT)

    def test_template_inputs_resolve_to_repo_relative_posix_paths(self) -> None:
        inputs = resolve_template_inputs(
            self.catalog, "contested-world-observation.v1", root=ROOT
        )
        self.assertEqual(
            {
                "scenario": "scenarios/japan-2036/scenario.json",
                "intervention": "interventions/haruhi-world-observation.json",
                "social_config": "scenarios/japan-2036/social-haruhi-world-observation.json",
                "fixture": "fixtures/social/haruhi-world-observation.jsonl",
            },
            inputs,
        )
        for value in inputs.values():
            with self.subTest(value=value):
                self.assertTrue((ROOT / value).is_file())
                self.assertFalse(Path(value).is_absolute())
        with self.assertRaisesRegex(ContractError, "not registered"):
            resolve_template_inputs(self.catalog, "unknown.v1", root=ROOT)

    def test_template_inputs_refuse_a_disabled_template(self) -> None:
        """catalogのoff-switchを呼び出し順に依存せず効かせる。"""
        catalog = copy.deepcopy(self.catalog)
        catalog["templates"][1]["status"] = "disabled"
        with self.assertRaisesRegex(ContractError, "preview_allowed"):
            resolve_template_inputs(
                catalog, "contested-world-observation.v1", root=ROOT
            )

    def test_catalog_rejects_unknown_fields(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["templates"][0]["provider"] = "arbitrary"
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            validate_template_catalog(catalog, root=ROOT)

    def test_repo_participation_fixtures_match_the_shipped_catalog(self) -> None:
        """同梱fixture一式が現catalogと整合し、そのままreadyになることを検査する。

        catalogのtemplate_versionを上げるとconfirmation fixtureは必ず拒否される。
        fixture単体では気付けないため、実catalogと突き合わせて閉じる。
        """
        draft = json.loads(
            (ROOT / "fixtures/participation/public-tools-idea-draft.v1.json").read_text(
                encoding="utf-8"
            )
        )
        confirmation = json.loads(
            (
                ROOT
                / "fixtures/participation/public-tools-template-confirmation.v1.json"
            ).read_text(encoding="utf-8")
        )
        normalized = validate_template_catalog(self.catalog, root=ROOT)
        selected = next(
            item
            for item in normalized["templates"]
            if item["template_id"] == confirmation["template_id"]
        )
        self.assertEqual(
            confirmation["template_version"], selected["template_version"]
        )
        self.assertEqual(
            confirmation["intervention_sha256"], selected["intervention_sha256"]
        )
        result = prepare_provisional_request(
            draft,
            self.catalog,
            confirmation,
            root=ROOT,
            template_id="public-tools-access.v1",
            seed=2036,
            delay_profile="none",
        )
        self.assertEqual(result["status"], "ready")

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

    def test_pure_projection_cannot_promote_an_official_result(self) -> None:
        projection = json.loads(
            (ROOT / "catalogs/idea-status.v1.json").read_text(encoding="utf-8")
        )
        idea = projection["ideas"][0]
        idea["lifecycle"] = dict.fromkeys(idea["lifecycle"], True)
        idea["simulation_status"] = "official"
        idea["missing_conditions"] = []
        with self.assertRaisesRegex(ContractError, "verified main-run promotion"):
            validate_idea_status_projection(projection)

    def test_next_action_must_be_a_string(self) -> None:
        projection = json.loads(
            (ROOT / "catalogs/idea-status.v1.json").read_text(encoding="utf-8")
        )
        projection["ideas"][0]["next_action"] = None
        with self.assertRaisesRegex(ContractError, "next_action"):
            validate_idea_status_projection(projection)

    def test_disabled_template_request_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["templates"][0]["status"] = "disabled"
        ready = prepare_provisional_request(
            idea_draft(),
            self.catalog,
            template_confirmation(),
            root=ROOT,
            template_id="public-tools-access.v1",
            seed=2036,
            delay_profile="none",
        )["request"]
        with self.assertRaisesRegex(ContractError, "preview_allowed"):
            validate_provisional_request(ready, catalog, root=ROOT)

    def test_catalog_returns_normalized_template_ids(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["templates"][0]["template_id"] = "public-tools-access.v1 "
        normalized = validate_template_catalog(catalog, root=ROOT)
        self.assertEqual(
            normalized["templates"][0]["template_id"], "public-tools-access.v1"
        )
        result = prepare_provisional_request(
            idea_draft(),
            catalog,
            template_confirmation(),
            root=ROOT,
            template_id="public-tools-access.v1",
            seed=2036,
            delay_profile="none",
        )
        self.assertEqual(result["status"], "ready")

    def test_external_request_rejects_boolean_versions(self) -> None:
        ready = prepare_provisional_request(
            idea_draft(),
            self.catalog,
            template_confirmation(),
            root=ROOT,
            template_id="public-tools-access.v1",
            seed=2036,
            delay_profile="none",
        )["request"]
        with self.assertRaisesRegex(ContractError, "template_version"):
            validate_provisional_request(
                {**ready, "template_version": True}, self.catalog, root=ROOT
            )
        with self.assertRaisesRegex(ContractError, "catalog_version"):
            validate_provisional_request(
                {**ready, "catalog_version": True}, self.catalog, root=ROOT
            )

    def test_idea_status_rejects_impossible_timestamps(self) -> None:
        projection = json.loads(
            (ROOT / "catalogs/idea-status.v1.json").read_text(encoding="utf-8")
        )
        projection["observed_at"] = "2026-02-31"
        with self.assertRaisesRegex(ContractError, "UTC date"):
            validate_idea_status_projection(projection)
        projection = json.loads(
            (ROOT / "catalogs/idea-status.v1.json").read_text(encoding="utf-8")
        )
        projection["ideas"][0]["source_updated_at"] = "2026-02-31T99:99:99Z"
        with self.assertRaisesRegex(ContractError, "UTC datetime"):
            validate_idea_status_projection(projection)

    def test_idea_status_requires_zero_padded_timestamps(self) -> None:
        projection = json.loads(
            (ROOT / "catalogs/idea-status.v1.json").read_text(encoding="utf-8")
        )
        projection["observed_at"] = "2026-2-3"
        with self.assertRaisesRegex(ContractError, "YYYY-MM-DD"):
            validate_idea_status_projection(projection)
        projection = json.loads(
            (ROOT / "catalogs/idea-status.v1.json").read_text(encoding="utf-8")
        )
        projection["ideas"][0]["source_updated_at"] = "2026-2-3T1:2:3Z"
        with self.assertRaisesRegex(ContractError, "YYYY-MM-DDTHH:MM:SSZ"):
            validate_idea_status_projection(projection)


if __name__ == "__main__":
    unittest.main()
