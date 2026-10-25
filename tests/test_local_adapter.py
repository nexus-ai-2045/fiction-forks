from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fiction_forks.engine import ContractError
from fiction_forks.local_adapter import (
    CATALOG_PATH,
    REQUEST_SCHEMA,
    SESSION_HEADER,
    LocalRunService,
    LocalRuntimeError,
    ProviderGrant,
    SessionToken,
    _exact_envelope,
    _handler,
    issue_session_token,
)
from fiction_forks.participation import PROVISIONAL_REQUEST_SCHEMA
from fiction_forks.run_bundle import event_stream_sha256
from http.server import ThreadingHTTPServer


ROOT = Path(__file__).resolve().parents[1]
CATALOG_INPUTS = (
    CATALOG_PATH,
    "interventions/doraemon-public-tools.json",
    "interventions/haruhi-world-observation.json",
    "scenarios/japan-2036/scenario.json",
    "scenarios/japan-2036/social.json",
    "scenarios/japan-2036/social-haruhi-world-observation.json",
    "fixtures/social/japan-2036-cooperation.jsonl",
    "fixtures/social/haruhi-world-observation.jsonl",
)


def session(value: str = "test-session-token", *, ttl_seconds: int = 900) -> SessionToken:
    import time

    return SessionToken(value, time.monotonic() + ttl_seconds)


def mirror_catalog_inputs(destination: Path) -> None:
    """catalogが参照する入力一式だけをtemp repoへ複製する。"""

    for relative in CATALOG_INPUTS:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)


def run_request(**updates) -> dict:
    value = {
        "schema_version": PROVISIONAL_REQUEST_SCHEMA,
        "scenario_id": "japan-2036-centralization",
        "template_id": "contested-world-observation.v1",
        "template_version": 3,
        "catalog_id": "japan-2036-preview-templates",
        "catalog_version": 3,
        "intervention_id": "haruhi-world-observation",
        "intervention_sha256": "6b9420240ae02129b4fd24f679aef0a9e79dbd53dca052f58700e1a7d5c79d70",
        "seed": 2036,
        "delay_profile": "none",
        "user_confirmed": True,
    }
    value.update(updates)
    return value


def request(provider: str = "fixture", *, confirm_live: bool = False, **updates) -> dict:
    return {
        "schema_version": REQUEST_SCHEMA,
        "run_request": run_request(**updates),
        "execution": {"provider_id": provider, "confirm_live": confirm_live},
    }


def fixture_service(root: Path = ROOT) -> LocalRunService:
    return LocalRunService(root, "a" * 40, {"fixture": ProviderGrant("fixture")})


class LocalAdapterContractTests(unittest.TestCase):
    def test_envelope_rejects_unknown_fields_and_unsupported_schema(self) -> None:
        for bad in (
            {**request(), "output": "../../escape.json"},
            {**request(), "schema_version": "fiction_forks_local_run_request.v1"},
            {**request(), "execution": {"provider_id": "fixture"}},
            {
                **request(),
                "execution": {
                    "provider_id": "fixture",
                    "confirm_live": False,
                    "model": "gpt",
                },
            },
            {**request(), "execution": {"provider_id": "openai", "confirm_live": True}},
        ):
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                _exact_envelope(bad)

    def test_run_request_is_validated_by_the_participation_contract(self) -> None:
        service = fixture_service()
        for bad, message in (
            (request(template_id="../../escape"), "not registered"),
            (request(seed=9999), "seed is not allowed"),
            (request(seed=True), "seed must be an integer"),
            (request(delay_profile="institution-5y"), "delay_profile is not allowed"),
            (request(intervention_sha256="0" * 64), "intervention_sha256 mismatch"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ContractError, message):
                    service.execute(bad)

    def test_transport_fails_closed_on_delay_profiles_the_cli_cannot_honour(self) -> None:
        service = fixture_service()
        catalog = json.loads((ROOT / CATALOG_PATH).read_text(encoding="utf-8"))
        for template in catalog["templates"]:
            template["delay_profiles"] = ["none", "institution-5y"]
        service._catalog = catalog
        with self.assertRaisesRegex(ContractError, "cannot honour this delay profile"):
            service.execute(request(delay_profile="institution-5y"))

    def test_live_provider_requires_startup_grant_and_matching_confirmation(self) -> None:
        service = fixture_service()
        with self.assertRaisesRegex(ContractError, "not granted"):
            service.execute(request("ollama", confirm_live=True))
        with self.assertRaisesRegex(ContractError, "per-request confirmation"):
            service.execute(request("fixture", confirm_live=True))
        live = LocalRunService(
            ROOT, "a" * 40, {"ollama": ProviderGrant("ollama", model="qwen3")}
        )
        with self.assertRaisesRegex(ContractError, "per-request confirmation"):
            live.execute(request("ollama", confirm_live=False))

    def test_missing_catalog_inputs_are_server_side_failures(self) -> None:
        """catalog入力を読めないのはserver側要因である。requestの契約違反へ寄せない。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(LocalRuntimeError) as startup:
                fixture_service(root)
            self.assertNotIsInstance(startup.exception, ContractError)
            mirror_catalog_inputs(root)
            service = fixture_service(root)
            (root / "interventions/haruhi-world-observation.json").unlink()
            with self.assertRaises(LocalRuntimeError) as raised:
                service.execute(request())
            self.assertNotIsInstance(raised.exception, ContractError)

    def test_template_selection_failures_stay_on_the_request_side(self) -> None:
        """未登録・preview不許可のtemplateはrequest側の違反である。

        path解決をserver側の失敗として一括で包むと、正しく動いているadapterが
        「あなたの要求は正しいがserverが壊れた」と逆向きに誤報する。
        """

        service = fixture_service()
        with self.assertRaises(ContractError) as unknown:
            service._resolve_inputs("no-such-template.v1")
        self.assertNotIsInstance(unknown.exception, LocalRuntimeError)

        catalog = json.loads((ROOT / CATALOG_PATH).read_text(encoding="utf-8"))
        for template in catalog["templates"]:
            template["status"] = "disabled"
        service._catalog = catalog
        with self.assertRaisesRegex(ContractError, "not preview_allowed") as disabled:
            service._resolve_inputs(catalog["templates"][0]["template_id"])
        self.assertNotIsInstance(disabled.exception, LocalRuntimeError)

    def test_cli_failures_and_timeouts_are_server_side_failures(self) -> None:
        """CLI異常終了とtimeoutはserver側要因である。requestの契約違反へ寄せない。"""

        service = fixture_service()

        def failing_run(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, "", "")

        def timing_out_run(command, **kwargs):
            raise subprocess.TimeoutExpired(command, 1)

        for side_effect, message in (
            (failing_run, "simulation failed"),
            (timing_out_run, "simulation timed out"),
        ):
            with self.subTest(message=message):
                with patch(
                    "fiction_forks.local_adapter.subprocess.run", side_effect=side_effect
                ):
                    with self.assertRaisesRegex(LocalRuntimeError, message) as raised:
                        service.execute(request())
                self.assertNotIsInstance(raised.exception, ContractError)

    def test_service_resolves_every_input_from_the_catalog(self) -> None:
        service = fixture_service()

        def fake_run(command, **kwargs):
            self.assertEqual("utf-8", kwargs["encoding"])
            self.assertEqual("strict", kwargs["errors"])
            output = Path(command[command.index("--output") + 1])
            bundle_output = Path(command[command.index("--bundle-output") + 1])
            result = {
                "run_id": "ff-test",
                "provider": {"name": "fixture", "model": None},
            }
            bundle = {
                "schema": "meta-security-run-bundle/v1",
                "run_request": {"run_id": "ff-test"},
                "events": [{"run_id": "ff-test", "sequence": 0}],
                "replay": {"run_id": "ff-test"},
                "evidence": {"run_id": "ff-test"},
            }
            stream_digest = event_stream_sha256(bundle["events"])
            bundle["replay"]["event_stream_sha256"] = stream_digest
            bundle["evidence"]["event_stream_sha256"] = stream_digest
            output.write_text(json.dumps(result), encoding="utf-8")
            bundle_output.write_text(json.dumps(bundle), encoding="utf-8")
            self.assertIn("scenarios/japan-2036/scenario.json", command)
            self.assertIn("interventions/haruhi-world-observation.json", command)
            self.assertIn(
                "scenarios/japan-2036/social-haruhi-world-observation.json", command
            )
            self.assertIn("fixtures/social/haruhi-world-observation.jsonl", command)
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch("fiction_forks.local_adapter.subprocess.run", side_effect=fake_run):
            first = service.execute(request())
            second = service.execute(request())
        self.assertEqual("ff-test", first["run_id"])
        self.assertNotEqual(first["execution_id"], second["execution_id"])
        self.assertRegex(first["execution_id"], r"^ffx-[0-9a-f]{32}$")
        self.assertEqual("meta-security-run-bundle/v1", first["bundle"]["schema"])
        self.assertEqual(first["result_sha256"], hashlib.sha256(base64.b64decode(first["result_artifact_base64"])).hexdigest())
        self.assertEqual(first["bundle_sha256"], hashlib.sha256(base64.b64decode(first["bundle_artifact_base64"])).hexdigest())

    def test_health_projects_the_catalog_without_paths_or_input_digests(self) -> None:
        health = fixture_service().health()
        self.assertEqual("ready", health["status"])
        self.assertNotIn("worldlines", health)
        self.assertEqual("japan-2036-preview-templates", health["catalog_id"])
        self.assertEqual(3, health["catalog_version"])
        self.assertEqual(
            {"public-tools-access.v1", "contested-world-observation.v1"},
            {template["template_id"] for template in health["templates"]},
        )
        for template in health["templates"]:
            with self.subTest(template=template["template_id"]):
                self.assertEqual(
                    {
                        "template_id",
                        "template_version",
                        "scenario_id",
                        "intervention_id",
                        "intervention_sha256",
                        "abstract_function",
                        "allowed_seeds",
                        "delay_profiles",
                    },
                    set(template),
                )

    def test_adapter_source_declares_no_worldline_path_literals(self) -> None:
        source = (ROOT / "src/fiction_forks/local_adapter.py").read_text(encoding="utf-8")
        for literal in ("scenarios/", "interventions/", "fixtures/"):
            with self.subTest(literal=literal):
                self.assertNotIn(literal, source)
        self.assertEqual(1, source.count(CATALOG_PATH))


class LocalAdapterSessionTokenTests(unittest.TestCase):
    def test_session_token_expires_and_rejects_other_values(self) -> None:
        token = issue_session_token(900)
        self.assertTrue(token.matches(token.value))
        self.assertFalse(token.matches("wrong"))
        self.assertFalse(token.matches("é*43"))
        self.assertFalse(token.matches(token.value, now=token.expires_at))
        self.assertFalse(token.matches(token.value, now=token.expires_at + 1))

    def test_session_token_ttl_must_be_a_positive_number_of_seconds(self) -> None:
        for bad in (0, -1, True):
            with self.subTest(bad=bad), self.assertRaisesRegex(ContractError, "TTL"):
                issue_session_token(bad)


class LocalAdapterHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.token = session()
        self.service = fixture_service()
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            _handler(self.service, "http://127.0.0.1:4173", self.token),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_health_is_loopback_host_bounded(self) -> None:
        with urlopen(f"{self.base}/api/health", timeout=2) as response:
            self.assertEqual(200, response.status)
            payload = json.load(response)
            self.assertEqual("ready", payload["status"])
            self.assertIn("templates", payload)
        bad = Request(f"{self.base}/api/health", headers={"Host": "attacker.example"})
        with self.assertRaises(HTTPError) as raised:
            urlopen(bad, timeout=2)
        self.assertEqual(403, raised.exception.code)

    def test_post_rejects_cross_origin_wrong_type_and_oversize(self) -> None:
        body = json.dumps(request()).encode()
        cases = (
            ({"Origin": "https://attacker.example", "Content-Type": "application/json", SESSION_HEADER: self.token.value}, body, 403),
            ({"Origin": "http://127.0.0.1:4173", "Content-Type": "text/plain", SESSION_HEADER: self.token.value}, body, 415),
            (
                {"Origin": "http://127.0.0.1:4173", "Content-Type": "application/json", SESSION_HEADER: self.token.value},
                b"x" * 4097,
                413,
            ),
        )
        for headers, data, status in cases:
            with self.subTest(status=status):
                req = Request(f"{self.base}/api/runs", data=data, headers=headers, method="POST")
                with self.assertRaises(HTTPError) as raised:
                    urlopen(req, timeout=2)
                self.assertEqual(status, raised.exception.code)

    def test_post_rejects_the_retired_v1_request_shape_as_bad_request(self) -> None:
        body = json.dumps(
            {
                "schema_version": "fiction_forks_local_run_request.v1",
                "worldline_id": "haruhi-world-observation",
                "provider": "fixture",
                "seed": 2036,
                "confirm_live": False,
            }
        ).encode()
        req = Request(
            f"{self.base}/api/runs",
            data=body,
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Content-Type": "application/json",
                SESSION_HEADER: self.token.value,
            },
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(req, timeout=2)
        self.assertEqual(400, raised.exception.code)

    def test_server_side_failures_do_not_blame_the_run_request(self) -> None:
        """CLIが失敗した実行を400として返さない。operatorが原因を切り分けられなくなる。"""

        def failing_run(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, "", "")

        req = Request(
            f"{self.base}/api/runs",
            data=json.dumps(request()).encode(),
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Content-Type": "application/json",
                SESSION_HEADER: self.token.value,
            },
            method="POST",
        )
        with patch("fiction_forks.local_adapter.subprocess.run", side_effect=failing_run):
            with self.assertRaises(HTTPError) as raised:
                urlopen(req, timeout=2)
        self.assertEqual(500, raised.exception.code)
        self.assertEqual("local_run_failed", json.load(raised.exception)["error"])

    def test_a_busy_adapter_reports_a_conflict_rather_than_a_bad_request(self) -> None:
        req = Request(
            f"{self.base}/api/runs",
            data=json.dumps(request()).encode(),
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Content-Type": "application/json",
                SESSION_HEADER: self.token.value,
            },
            method="POST",
        )
        self.service._run_lock.acquire()
        try:
            with self.assertRaises(HTTPError) as raised:
                urlopen(req, timeout=2)
        finally:
            self.service._run_lock.release()
        self.assertEqual(409, raised.exception.code)
        self.assertEqual("run_already_in_progress", json.load(raised.exception)["error"])

    def test_non_ascii_session_header_is_refused_without_dropping_the_connection(self) -> None:
        """非ASCIIのheader値はTypeErrorではなくsession_not_allowedへ寄せる。"""

        req = Request(
            f"{self.base}/api/runs",
            data=json.dumps(request()).encode(),
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Content-Type": "application/json",
                SESSION_HEADER: "é*43",
            },
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(req, timeout=2)
        self.assertEqual(403, raised.exception.code)
        self.assertEqual("session_not_allowed", json.load(raised.exception)["error"])

    def test_session_token_and_browser_preflight_are_required(self) -> None:
        body = json.dumps(request()).encode()
        missing = Request(
            f"{self.base}/api/runs",
            data=body,
            headers={"Origin": "http://127.0.0.1:4173", "Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(missing, timeout=2)
        self.assertEqual(403, raised.exception.code)

        preflight = Request(
            f"{self.base}/api/runs",
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": f"content-type, {SESSION_HEADER}",
            },
            method="OPTIONS",
        )
        with urlopen(preflight, timeout=2) as response:
            self.assertEqual(204, response.status)
            self.assertEqual("POST", response.headers["Access-Control-Allow-Methods"])
            self.assertIn(SESSION_HEADER, response.headers["Access-Control-Allow-Headers"])


class LocalAdapterExpiredSessionTests(unittest.TestCase):
    def test_expired_session_token_stops_accepting_runs(self) -> None:
        expired = session(ttl_seconds=-1)
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            _handler(fixture_service(), "http://127.0.0.1:4173", expired),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            req = Request(
                f"http://127.0.0.1:{server.server_address[1]}/api/runs",
                data=json.dumps(request()).encode(),
                headers={
                    "Origin": "http://127.0.0.1:4173",
                    "Content-Type": "application/json",
                    SESSION_HEADER: expired.value,
                },
                method="POST",
            )
            with self.assertRaises(HTTPError) as raised:
                urlopen(req, timeout=2)
            self.assertEqual(403, raised.exception.code)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
