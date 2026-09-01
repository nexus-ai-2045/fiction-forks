from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.emergence_metrics import (  # noqa: E402
    NOT_MEASURED,
    aggregate,
    build_report,
    contains_prose,
    identity_key,
    main,
    render_markdown,
    summarize_document,
)


LIVE_SUMMARY = {
    "schema_version": "fiction_forks_live_run_summary.v1",
    "provider": "vertex",
    "model": "gemini-2.5-flash",
    "runtime_revision": "abc",
    "seed": 2036,
    "event_count": 1,
    "valid_action_count": 1,
    "invalid_action_count": 0,
    "interaction_edge_count": 0,
    "activation_year": 2037,
    "collapsed": True,
    "turns": [
        {
            "turn": 1,
            "agent_id": "civic_challenger",
            "action_id": "establish-contestation-rights",
            "valid": True,
        }
    ],
}


class EmergenceMetricsTests(unittest.TestCase):
    def test_provider_model_requires_both_identity_fields(self) -> None:
        rows = [
            {"identity": {"provider": NOT_MEASURED, "model": NOT_MEASURED}},
            {"identity": {"provider": "fixture", "model": NOT_MEASURED}},
            {"identity": {"provider": NOT_MEASURED, "model": "model-only"}},
            {"identity": {"provider": "vertex", "model": "gemini-2.5-flash"}},
        ]
        for row in rows:
            row.update(
                {
                    "action_diversity": NOT_MEASURED,
                    "capability_coverage": NOT_MEASURED,
                    "interaction_edge_count": NOT_MEASURED,
                    "interaction_density": NOT_MEASURED,
                    "stances": {
                        "support": NOT_MEASURED,
                        "condition": NOT_MEASURED,
                        "oppose": NOT_MEASURED,
                        "abstain": NOT_MEASURED,
                    },
                    "fail_closed_rate": NOT_MEASURED,
                    "activation_year": NOT_MEASURED,
                    "collapsed": NOT_MEASURED,
                }
            )

        distribution = aggregate(rows)["provider_model"]

        self.assertEqual(1, distribution["measured"])
        self.assertEqual(3, distribution["not_measured"])
        self.assertEqual({"vertex/gemini-2.5-flash": 1}, distribution["counts"])

    def test_action_diversity_counts_only_valid_non_abstain_actions(self) -> None:
        row = summarize_document(
            {
                "schema_version": "fiction_forks_live_run_summary.v1",
                "event_count": 3,
                "valid_action_count": 2,
                "invalid_action_count": 1,
                "turns": [
                    {"turn": 1, "action_id": "keep", "valid": True},
                    {"turn": 1, "action_id": "invalid-must-not-count", "valid": False},
                    {"turn": 2, "action_id": "abstain", "valid": True},
                ],
            }
        )
        self.assertEqual(["keep", "abstain"], row["action_ids"])
        self.assertEqual(1, row["action_diversity"])

        missing_valid = summarize_document(
            {
                "schema_version": "fiction_forks_live_run_summary.v1",
                "turns": [{"turn": 1, "action_id": "unknown"}],
            }
        )
        self.assertEqual(NOT_MEASURED, missing_valid["action_ids"])
        self.assertEqual(NOT_MEASURED, missing_valid["action_diversity"])

    def test_actual_artifact_sha_is_identity_and_declared_sha_is_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            common = {
                "schema_version": "fiction_forks_live_run_summary.v1",
                "run_id": "same-run",
                "provider": "vertex",
                "result_sha256": "same-declared-value",
            }
            first = root / "first.json"
            second = root / "second.json"
            first.write_text(json.dumps({**common, "seed": 1}), encoding="utf-8")
            second.write_text(json.dumps({**common, "seed": 2}), encoding="utf-8")
            report = build_report([root], repo_root=root)
            self.assertEqual(2, report["n_executions"])
            identities = [row["identity"] for row in report["executions"]]
            self.assertEqual(
                {"same-declared-value"},
                {identity["declared_result_sha256"] for identity in identities},
            )
            self.assertEqual(2, len({identity["artifact_sha256"] for identity in identities}))
            self.assertEqual(
                {False},
                {
                    identity["declared_result_sha256_matches_artifact"]
                    for identity in identities
                },
            )

    def test_untrusted_world_shapes_and_numeric_inconsistency_fail_closed(self) -> None:
        row = summarize_document(
            {
                "schema_version": "fiction_forks_social_result.v1",
                "event_count": 2,
                "valid_action_count": True,
                "invalid_action_count": -1,
                "interaction_edge_count": 3,
                "roles": ["a", "b"],
                "turn_count": 1,
                "missing_actions_by_node": {"safe-node": ["safe-action", "raw prose secret"]},
                "technology_delays": {"safe-node": False},
            }
        )
        self.assertEqual(NOT_MEASURED, row["event_count"])
        self.assertEqual(NOT_MEASURED, row["valid_action_count"])
        self.assertEqual(NOT_MEASURED, row["invalid_action_count"])
        self.assertEqual(NOT_MEASURED, row["fail_closed_rate"])
        self.assertEqual(NOT_MEASURED, row["interaction_density"])
        self.assertEqual(NOT_MEASURED, row["missing_actions_by_node"])
        self.assertEqual(NOT_MEASURED, row["technology_delays"])

    def test_count_mismatch_fails_closed(self) -> None:
        row = summarize_document(
            {
                "schema_version": "fiction_forks_live_run_summary.v1",
                "event_count": 3,
                "valid_action_count": 1,
                "invalid_action_count": 1,
            }
        )
        self.assertEqual(NOT_MEASURED, row["event_count"])
        self.assertEqual(NOT_MEASURED, row["fail_closed_rate"])

    def test_same_run_id_is_split_by_provider_and_hashes(self) -> None:
        fixture = summarize_document(
            {
                "schema_version": "fiction_forks_social_result.v1",
                "run_id": "ff-c705e4136e2fce00",
                "seed": 2036,
                "provider": {"name": "fixture", "model": None},
                "metrics": {
                    "action_count": 15,
                    "valid_action_count": 15,
                    "invalid_action_count": 0,
                    "capability_coverage": 7,
                    "interaction_edge_count": 10,
                },
                "roles": ["a", "b", "c", "d", "e"],
                "turn_count": 3,
                "actions": [
                    {
                        "valid": True,
                        "action": {"action_id": "deploy-observation-mesh", "stance": "condition"},
                    }
                ],
                "world_comparison": {
                    "fork": {"activation_year": 2032, "collapsed": False}
                },
                "result_sha256": "aaa",
                "event_stream_sha256": "event-a",
            }
        )
        live = summarize_document(
            {
                "schema_version": "fiction_forks_live_run_summary.v1",
                "run_id": "ff-c705e4136e2fce00",
                "provider": "vertex",
                "model": "gemini-2.5-flash",
                "runtime_revision": "2f5b91e4",
                "seed": 2036,
                "event_count": 15,
                "valid_action_count": 12,
                "invalid_action_count": 3,
                "interaction_edge_count": 9,
                "activation_year": 2037,
                "collapsed": True,
                "result_sha256": "bbb",
                "event_stream_sha256": "event-b",
                "turns": [
                    {"turn": 1, "agent_id": "civic_challenger", "action_id": "establish-contestation-rights", "valid": True}
                ],
            }
        )
        self.assertEqual(fixture["identity"]["run_id"], live["identity"]["run_id"])
        self.assertNotEqual(identity_key(fixture["identity"]), identity_key(live["identity"]))
        self.assertEqual("fixture", fixture["source_class"])
        self.assertEqual("live", live["source_class"])

    def test_missing_worldline_fields_are_not_filled_with_zero(self) -> None:
        row = summarize_document(
            {
                "schema_version": "fiction_forks_live_run_summary.v1",
                "run_id": "ff-c705e4136e2fce00",
                "provider": "ollama",
                "model": "qwen2.5vl:3b",
                "seed": 2036,
                "event_count": 15,
                "valid_action_count": 14,
                "invalid_action_count": 1,
                "interaction_edge_count": 16,
                "turns": [],
            }
        )
        self.assertEqual(NOT_MEASURED, row["activation_year"])
        self.assertEqual(NOT_MEASURED, row["collapsed"])
        self.assertEqual(NOT_MEASURED, row["capability_coverage"])
        self.assertEqual(NOT_MEASURED, row["stances"]["support"])
        self.assertEqual(NOT_MEASURED, row["interaction_density"])
        self.assertNotEqual(0, row["collapsed"])
        self.assertNotEqual(0, row["capability_coverage"])

    def test_report_separates_fixture_and_live_and_omits_prose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fixture.json").write_text(
                json.dumps(
                    {
                        "schema_version": "fiction_forks_social_result.v1",
                        "run_id": "ff-fixture",
                        "seed": 2036,
                        "provider": {"name": "fixture", "model": None},
                        "metrics": {
                            "action_count": 2,
                            "valid_action_count": 2,
                            "invalid_action_count": 0,
                            "capability_coverage": 2,
                            "interaction_edge_count": 1,
                        },
                        "roles": ["a", "b"],
                        "turn_count": 1,
                        "actions": [
                            {
                                "valid": True,
                                "action": {
                                    "action_id": "publish-provenance-ledger",
                                    "stance": "condition",
                                },
                            },
                            {
                                "valid": True,
                                "action": {
                                    "action_id": "compare-rival-hypotheses",
                                    "stance": "support",
                                },
                            },
                        ],
                        "world_comparison": {
                            "fork": {"activation_year": 2032, "collapsed": False}
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "live.json").write_text(
                json.dumps(
                    {
                        "schema_version": "fiction_forks_live_run_summary.v1",
                        "run_id": "ff-fixture",
                        "provider": "vertex",
                        "model": "gemini-2.5-flash",
                        "runtime_revision": "abc",
                        "seed": 2036,
                        "event_count": 2,
                        "valid_action_count": 1,
                        "invalid_action_count": 1,
                        "interaction_edge_count": 0,
                        "activation_year": 2037,
                        "collapsed": True,
                        "result_sha256": "live-sha",
                        "event_stream_sha256": "live-event",
                        "turns": [
                            {
                                "turn": 1,
                                "agent_id": "civic_challenger",
                                "action_id": "establish-contestation-rights",
                                "valid": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = build_report([root], repo_root=root)
            self.assertFalse(contains_prose(report))
            self.assertEqual(2, report["n_executions"])
            self.assertIn("fixture", report["aggregates"]["by_source_class"])
            self.assertIn("live", report["aggregates"]["by_source_class"])
            self.assertEqual(
                1.0, report["aggregates"]["by_source_class"]["live"]["collapse_rate"]
            )
            self.assertEqual(
                0.0, report["aggregates"]["by_source_class"]["fixture"]["collapse_rate"]
            )

    def test_inputs_outside_curated_root_are_marked_uncurated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            curated_dir = root / "artifacts/runs"
            uncurated_dir = root / "evaluation/outputs"
            curated_dir.mkdir(parents=True)
            uncurated_dir.mkdir(parents=True)
            (curated_dir / "curated.json").write_text(
                json.dumps({**LIVE_SUMMARY, "run_id": "ff-curated"}), encoding="utf-8"
            )
            (uncurated_dir / "candidate.json").write_text(
                json.dumps({**LIVE_SUMMARY, "run_id": "ff-candidate"}), encoding="utf-8"
            )

            report = build_report([curated_dir, uncurated_dir], repo_root=root)

            self.assertEqual(2, report["n_executions"])
            curation = report["input_curation"]
            self.assertEqual("artifacts/runs", curation["curated_root"])
            self.assertFalse(curation["curated_only"])
            self.assertEqual(1, curation["curated"])
            self.assertEqual(1, curation["uncurated"])
            curated_by_path = {
                row["identity"]["source_path"]: row["curated"]
                for row in report["executions"]
            }
            self.assertEqual(
                {
                    "artifacts/runs/curated.json": True,
                    "evaluation/outputs/candidate.json": False,
                },
                curated_by_path,
            )
            live = report["aggregates"]["by_source_class"]["live"]
            self.assertEqual(1, live["curated"])
            self.assertEqual(1, live["uncurated"])
            self.assertIn("curated root の外", render_markdown(report))

    def test_curated_root_only_report_declares_curated_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            curated_dir = root / "artifacts/runs"
            curated_dir.mkdir(parents=True)
            (curated_dir / "curated.json").write_text(
                json.dumps({**LIVE_SUMMARY, "run_id": "ff-curated"}), encoding="utf-8"
            )

            report = build_report([curated_dir], repo_root=root)

            self.assertTrue(report["input_curation"]["curated_only"])
            self.assertEqual(0, report["input_curation"]["uncurated"])
            self.assertEqual([True], [row["curated"] for row in report["executions"]])
            self.assertEqual(0, report["aggregates"]["all"]["uncurated"])
            self.assertNotIn("curated root の外", render_markdown(report))

    def test_cli_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "vertex.json"
            artifact.write_text(
                (ROOT / "artifacts/runs/vertex-live-run-summary.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            json_out = root / "out.json"
            md_out = root / "out.md"
            self.assertEqual(
                0,
                main(
                    [
                        "--input",
                        str(artifact),
                        "--output-json",
                        str(json_out),
                        "--output-md",
                        str(md_out),
                        "--repo-root",
                        str(root),
                    ]
                ),
            )
            payload = json.loads(json_out.read_text(encoding="utf-8"))
            markdown = md_out.read_text(encoding="utf-8")
            self.assertEqual("live", payload["executions"][0]["source_class"])
            self.assertEqual(2037, payload["executions"][0]["activation_year"])
            self.assertIn("創発性の断定ではない", markdown)
            self.assertNotIn("C:\\Users", json_out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
