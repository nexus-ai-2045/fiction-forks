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

from fiction_forks.agent_protocol import (
    ACTION_SCHEMA_VERSION,
    OBSERVATION_SCHEMA_VERSION,
)
from fiction_forks.cli import main as cli_main
from fiction_forks.engine import ENGINE_VERSION, ContractError, load_json
from fiction_forks.providers import (
    FixtureProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderError,
    ReplayProvider,
    VertexProvider,
)
from fiction_forks.social import (
    PROTOCOL_VERSION,
    replay_equivalent,
    run_social_simulation,
)


class CaptureProvider:
    name = "capture"
    model = None

    def __init__(self, inner: FixtureProvider) -> None:
        self.inner = inner
        self.observations: list[dict] = []

    def choose(self, observation: dict) -> dict:
        self.observations.append(json.loads(json.dumps(observation)))
        return dict(self.inner.choose(observation))


class MalformedProvider:
    name = "malformed"
    model = None

    def choose(self, observation: dict) -> dict:
        return {
            "schema_version": ACTION_SCHEMA_VERSION,
            "run_id": observation["run_id"],
            "turn": observation["turn"],
            "agent_id": observation["role"]["id"],
            "action_id": "audit-assumptions",
            "stance": "support",
            "responds_to": [],
            "target_ids": [],
            "evidence_ids": [],
            "confidence": 1,
            "conditions": [],
            "text": "I should not control world metrics.",
            "metric_delta": {"repair_capacity": 100},
        }


class OppositionOnlyProvider:
    """t2 の反対だけを差し込み、t3 の同一 action_id 再提案は fixture のまま通す。"""

    name = "opposition-only"
    model = None

    def __init__(self, inner: FixtureProvider) -> None:
        self.inner = inner

    def choose(self, observation: dict) -> dict:
        action = dict(self.inner.choose(observation))
        key = (observation["turn"], observation["role"]["id"])
        if key == (2, "threat_analyst"):
            action.update(
                {
                    "action_id": "abstain",
                    "stance": "oppose",
                    "responds_to": ["t1:infra_engineer"],
                    "target_ids": ["infra_engineer"],
                    "evidence_ids": ["public-technology-tree"],
                    "confidence": 0.8,
                    "conditions": [],
                    "text": "未検証の依存があるため、この提案へ反対します。",
                }
            )
        return action


class OppositionProvider:
    name = "opposition"
    model = None

    def __init__(self, inner: FixtureProvider) -> None:
        self.inner = inner

    def choose(self, observation: dict) -> dict:
        action = dict(self.inner.choose(observation))
        key = (observation["turn"], observation["role"]["id"])
        if key == (2, "threat_analyst"):
            action.update(
                {
                    "action_id": "abstain",
                    "stance": "oppose",
                    "responds_to": ["t1:infra_engineer"],
                    "target_ids": ["infra_engineer"],
                    "evidence_ids": ["public-technology-tree"],
                    "confidence": 0.8,
                    "conditions": [],
                    "text": "未検証の依存があるため、この提案へ反対します。",
                }
            )
        elif key == (3, "infra_engineer"):
            action.update(
                {
                    "action_id": "abstain",
                    "stance": "abstain",
                    "responds_to": [],
                    "target_ids": [],
                    "evidence_ids": [],
                    "confidence": 0,
                    "conditions": [],
                    "text": "反対を解消できないため保留します。",
                }
            )
        return action


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        observation = json.loads(kwargs["input"])
        action = {
            "schema_version": ACTION_SCHEMA_VERSION,
            "run_id": observation["run_id"],
            "turn": observation["turn"],
            "agent_id": observation["role"]["id"],
            "action_id": "abstain",
            "stance": "abstain",
            "responds_to": [],
            "target_ids": [],
            "evidence_ids": [],
            "confidence": 0,
            "conditions": [],
            "text": "判断材料が不足しているため保留します。",
        }
        return type("Response", (), {"output_text": json.dumps(action)})()


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


class SocialSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = load_json(ROOT / "scenarios/japan-2036/scenario.json")
        cls.intervention = load_json(ROOT / "interventions/doraemon-public-tools.json")
        cls.social_config = load_json(ROOT / "scenarios/japan-2036/social.json")
        cls.fixture_path = ROOT / "fixtures/social/japan-2036-cooperation.jsonl"

    def run_fixture(self):
        return run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            FixtureProvider.from_jsonl(self.fixture_path),
            seed=2036,
        )

    def test_five_roles_three_turns_produce_bounded_world_fork(self) -> None:
        result = self.run_fixture()
        self.assertEqual(5, len(result["roles"]))
        self.assertEqual(3, result["turn_count"])
        self.assertEqual(15, result["metrics"]["action_count"])
        self.assertEqual(0, result["metrics"]["invalid_action_count"])
        self.assertTrue(
            all(delay == 0 for delay in result["technology_delays"].values())
        )
        self.assertTrue(result["world_comparison"]["baseline"]["collapsed"])
        self.assertFalse(result["world_comparison"]["fork"]["collapsed"])
        self.assertEqual(10, result["metrics"]["interaction_edge_count"])
        self.assertEqual(15, result["metrics"]["conditioned_intent_count"])

    def test_fixture_is_reproducible_and_replay_is_equivalent(self) -> None:
        first = self.run_fixture()
        second = self.run_fixture()
        self.assertEqual(first, second)
        replay = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            ReplayProvider(first),
            seed=2036,
        )
        self.assertTrue(replay_equivalent(first, replay))

    def test_curated_fixture_manifest_matches_artifact(self) -> None:
        artifact_path = ROOT / "artifacts/runs/japan-2036-fixture.json"
        manifest = json.loads(
            (ROOT / "artifacts/runs/japan-2036-fixture.manifest.json").read_text(
                encoding="utf-8"
            )
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertFalse(manifest["ai_measured"])
        self.assertEqual(ENGINE_VERSION, manifest["engine_version"])
        self.assertEqual(ENGINE_VERSION, artifact["engine_version"])
        self.assertEqual(PROTOCOL_VERSION, artifact["protocol_version"])
        self.assertEqual(artifact["run_id"], manifest["run_id"])
        self.assertEqual(artifact["input_digest"], manifest["input_digest"])
        self.assertEqual(artifact["final_event_hash"], manifest["final_event_hash"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            manifest["artifact_sha256"],
        )

    def test_unknown_metric_delta_is_rejected_and_state_does_not_change(self) -> None:
        result = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            MalformedProvider(),
            seed=2036,
        )
        self.assertEqual(15, result["metrics"]["invalid_action_count"])
        self.assertEqual(15, result["metrics"]["abstention_count"])
        self.assertEqual([], result["selected_action_ids"])
        self.assertTrue(result["world_comparison"]["fork"]["collapsed"])
        for receipt in result["actions"]:
            self.assertEqual(receipt["state_before_hash"], receipt["state_after_hash"])

    def test_private_evidence_is_only_visible_to_its_audience(self) -> None:
        provider = CaptureProvider(FixtureProvider.from_jsonl(self.fixture_path))
        run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            provider,
            seed=2036,
        )
        for observation in provider.observations:
            self.assertEqual(
                OBSERVATION_SCHEMA_VERSION,
                observation["schema_version"],
            )
            evidence_ids = {item["id"] for item in observation["evidence"]}
            if observation["role"]["id"] == "civic_auditor":
                self.assertIn("private-audit-note", evidence_ids)
            else:
                self.assertNotIn("private-audit-note", evidence_ids)
            for prior_action in observation["prior_public_actions"]:
                self.assertNotIn("private-audit-note", prior_action["evidence_ids"])
                self.assertNotIn("text", prior_action)
                self.assertNotIn("conditions", prior_action)
                self.assertTrue(prior_action["text_redacted"])
                self.assertTrue(prior_action["conditions_redacted"])
                self.assertTrue(prior_action["action_title"])
                self.assertTrue(prior_action["capability"])

        result = self.run_fixture()
        for receipt in result["actions"]:
            action = receipt["action"]
            self.assertNotIn("private-audit-note", action["evidence_ids"])
            self.assertNotIn("text", action)
            self.assertNotIn("conditions", action)
            self.assertTrue(action["text_redacted"])

    def test_opposition_changes_the_deterministic_world_outcome(self) -> None:
        result = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            OppositionProvider(FixtureProvider.from_jsonl(self.fixture_path)),
            seed=2036,
        )
        self.assertEqual(1, result["metrics"]["opposed_intent_count"])
        self.assertNotIn("prototype-repair-network", result["selected_action_ids"])
        self.assertEqual(
            ["prototype-repair-network"],
            result["missing_actions_by_node"]["regional-fabrication-cells"],
        )
        self.assertTrue(result["world_comparison"]["fork"]["collapsed"])

    def test_opposition_survives_duplicate_action_reproposal(self) -> None:
        result = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            OppositionOnlyProvider(FixtureProvider.from_jsonl(self.fixture_path)),
            seed=2036,
        )
        self.assertEqual(1, result["metrics"]["opposed_intent_count"])
        self.assertNotIn("prototype-repair-network", result["selected_action_ids"])
        self.assertEqual(
            ["prototype-repair-network"],
            result["missing_actions_by_node"]["regional-fabrication-cells"],
        )
        self.assertTrue(result["world_comparison"]["fork"]["collapsed"])

    def test_malformed_provider_files_fail_with_contract_errors(self) -> None:
        with self.assertRaisesRegex(ContractError, "fixture entries"):
            FixtureProvider([{"agent_id": "missing-turn"}])
        with self.assertRaisesRegex(ContractError, "malformed receipts"):
            ReplayProvider(
                {
                    "schema_version": "fiction_forks_social_result.v1",
                    "input_digest": "digest",
                    "actions": [{}],
                    "final_event_hash": "invalid",
                }
            )

    def test_tampered_replay_hash_chain_is_rejected(self) -> None:
        artifact = self.run_fixture()
        artifact["actions"][0]["action"]["action_id"] = "abstain"
        with self.assertRaisesRegex(ContractError, "event_hash mismatch"):
            ReplayProvider(artifact)

    def test_replay_preserves_a_fail_closed_live_receipt(self) -> None:
        original = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            MalformedProvider(),
            seed=2036,
        )
        replayed = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            ReplayProvider(original),
            seed=2036,
        )
        self.assertEqual(15, original["metrics"]["invalid_action_count"])
        self.assertTrue(replay_equivalent(original, replayed))

    def test_replay_preserves_provider_error_receipts_and_event_hashes(self) -> None:
        class FailingProvider:
            name = "failing"
            model = None

            def choose(self, observation):
                raise ProviderError("upstream unavailable")

        original = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            FailingProvider(),
            seed=2036,
        )
        replayed = run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            ReplayProvider(original),
            seed=2036,
        )
        self.assertTrue(
            all(
                receipt["invalid_reason"] == "provider_error"
                for receipt in original["actions"]
            )
        )
        self.assertEqual(original["final_event_hash"], replayed["final_event_hash"])
        self.assertTrue(replay_equivalent(original, replayed))

    def test_openai_boundary_uses_structured_output_and_disables_storage(self) -> None:
        fake_client = FakeClient()
        provider = OpenAIProvider(
            model="gpt-5.4-mini",
            confirm_live=True,
            client=fake_client,
        )
        capture = CaptureProvider(FixtureProvider.from_jsonl(self.fixture_path))
        run_social_simulation(
            self.scenario,
            self.intervention,
            self.social_config,
            capture,
            seed=2036,
        )
        action = provider.choose(capture.observations[0])
        self.assertEqual("abstain", action["action_id"])
        kwargs = fake_client.responses.kwargs
        self.assertIsNotNone(kwargs)
        self.assertFalse(kwargs["store"])
        self.assertEqual("json_schema", kwargs["text"]["format"]["type"])
        self.assertTrue(kwargs["text"]["format"]["strict"])

    def test_ollama_boundary_is_loopback_structured_and_seeded(self) -> None:
        calls = []

        def transport(url, payload, **kwargs):
            calls.append((url, payload, kwargs))
            observation = json.loads(payload["messages"][1]["content"])
            action = FixtureProvider.from_jsonl(self.fixture_path).choose(observation)
            return {"message": {"content": json.dumps(action)}}

        capture = CaptureProvider(FixtureProvider.from_jsonl(self.fixture_path))
        run_social_simulation(
            self.scenario, self.intervention, self.social_config, capture, seed=2036
        )
        provider = OllamaProvider(
            model="qwen2.5vl:7b", confirm_live=True, transport=transport
        )
        action = provider.choose(capture.observations[0])
        self.assertEqual(capture.observations[0]["run_id"], action["run_id"])
        self.assertEqual("http://127.0.0.1:11434/api/chat", calls[0][0])
        self.assertFalse(calls[0][1]["stream"])
        self.assertEqual(0, calls[0][1]["options"]["temperature"])
        self.assertIsInstance(calls[0][1]["options"]["seed"], int)
        self.assertEqual("object", calls[0][1]["format"]["type"])
        with self.assertRaisesRegex(ProviderError, "loopback"):
            OllamaProvider(
                model="qwen2.5vl:7b",
                confirm_live=True,
                endpoint="https://example.com",
            )

    def test_ollama_endpoint_rejects_authority_and_path_confusion(self) -> None:
        invalid_endpoints = (
            "http://127.0.0.1:11434@example.com",
            "http://localhost:11434@example.com",
            "http://user@127.0.0.1:11434",
            "http://127.0.0.1:11434/api/chat",
            "http://127.0.0.1:11434?target=example.com",
            "http://127.0.0.1",
        )
        for endpoint in invalid_endpoints:
            with self.subTest(endpoint=endpoint):
                with self.assertRaisesRegex(ProviderError, "loopback"):
                    OllamaProvider(
                        model="qwen2.5vl:7b",
                        confirm_live=True,
                        endpoint=endpoint,
                    )

        provider = OllamaProvider(
            model="qwen2.5vl:7b",
            confirm_live=True,
            endpoint="http://[::1]:11434/",
        )
        self.assertEqual("http://[::1]:11434", provider.endpoint)

    def test_vertex_boundary_uses_controlled_json_and_same_seed(self) -> None:
        calls = []

        def transport(url, payload, **kwargs):
            calls.append((url, payload, kwargs))
            observation = json.loads(payload["contents"][0]["parts"][0]["text"])
            action = FixtureProvider.from_jsonl(self.fixture_path).choose(observation)
            return {
                "candidates": [{"content": {"parts": [{"text": json.dumps(action)}]}}]
            }

        capture = CaptureProvider(FixtureProvider.from_jsonl(self.fixture_path))
        run_social_simulation(
            self.scenario, self.intervention, self.social_config, capture, seed=2036
        )
        provider = VertexProvider(
            project="nexus-ai-2045",
            location="us-central1",
            model="gemini-2.5-flash",
            confirm_live=True,
            access_token="test-token",
            transport=transport,
        )
        action = provider.choose(capture.observations[0])
        self.assertEqual(capture.observations[0]["run_id"], action["run_id"])
        self.assertIn("gemini-2.5-flash:generateContent", calls[0][0])
        config = calls[0][1]["generationConfig"]
        self.assertEqual("application/json", config["responseMimeType"])
        self.assertEqual(0, config["temperature"])
        self.assertEqual({"thinkingBudget": 0}, config["thinkingConfig"])
        self.assertIsInstance(config["seed"], int)
        schema = config["responseJsonSchema"]
        self.assertNotIn("const", json.dumps(schema))
        self.assertEqual(
            [capture.observations[0]["run_id"]],
            schema["properties"]["run_id"]["enum"],
        )
        self.assertEqual("Bearer test-token", calls[0][2]["headers"]["Authorization"])

    def test_vertex_resource_identifiers_are_validated_before_token_use(self) -> None:
        invalid_values = (
            {"project": "nexus-ai-2045/locations/evil"},
            {"project": "UPPERCASE-project"},
            {"location": "us-central1@evil.example/x"},
            {"location": "us-central1/../global"},
            {"model": "gemini-2.5-flash:generateContent"},
            {"model": "../models/evil"},
        )
        defaults = {
            "project": "nexus-ai-2045",
            "location": "us-central1",
            "model": "gemini-2.5-flash",
        }
        for override in invalid_values:
            arguments = {**defaults, **override}
            with self.subTest(**override):
                with self.assertRaisesRegex(ProviderError, "invalid"):
                    VertexProvider(
                        **arguments,
                        confirm_live=True,
                        access_token="test-token",
                    )

    def test_vertex_resolves_the_windows_gcloud_launcher(self) -> None:
        completed = type("Completed", (), {"stdout": "token\n"})()
        with (
            patch("fiction_forks.providers.os.name", "nt"),
            patch(
                "fiction_forks.providers.shutil.which",
                return_value=r"C:\\gcloud\\gcloud.cmd",
            ) as which,
            patch(
                "fiction_forks.providers.subprocess.run", return_value=completed
            ) as run,
        ):
            VertexProvider(
                project="nexus-ai-2045",
                location="us-central1",
                model="gemini-2.5-flash",
                confirm_live=True,
            )
        which.assert_called_once_with("gcloud.cmd")
        self.assertEqual(r"C:\\gcloud\\gcloud.cmd", run.call_args.args[0][0])

    def test_role_count_is_bounded_before_provider_calls(self) -> None:
        broken = json.loads(json.dumps(self.social_config))
        broken["roles"] = [
            {
                "id": f"role-{index}",
                "title": "role",
                "objective": "objective",
                "private_context": "context",
            }
            for index in range(13)
        ]
        with self.assertRaisesRegex(ContractError, "2 to 12"):
            run_social_simulation(
                self.scenario,
                self.intervention,
                broken,
                FixtureProvider.from_jsonl(self.fixture_path),
            )

    def test_oversized_config_string_is_rejected_before_provider_calls(self) -> None:
        broken = json.loads(json.dumps(self.social_config))
        broken["roles"][0]["private_context"] = "x" * 2_001
        with self.assertRaisesRegex(ContractError, "exceeds 2000 characters"):
            run_social_simulation(
                self.scenario,
                self.intervention,
                broken,
                FixtureProvider.from_jsonl(self.fixture_path),
            )

    def test_cli_does_not_overwrite_artifact_without_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.json"
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
            ]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(0, cli_main(args))
                self.assertEqual(2, cli_main(args))
                self.assertEqual(0, cli_main([*args, "--overwrite"]))
            self.assertTrue(output.is_file())
            self.assertNotIn(b"\r\n", output.read_bytes())
            self.assertFalse((output.parent / ".run.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
