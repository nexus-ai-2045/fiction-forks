from __future__ import annotations

import base64
import hashlib
import json
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
    REQUEST_SCHEMA,
    SESSION_HEADER,
    LocalRunService,
    ProviderGrant,
    _exact_request,
    _handler,
)
from fiction_forks.run_bundle import event_stream_sha256
from http.server import ThreadingHTTPServer


def request(provider: str = "fixture", *, confirm_live: bool = False) -> dict:
    return {
        "schema_version": REQUEST_SCHEMA,
        "worldline_id": "haruhi-world-observation",
        "provider": provider,
        "seed": 2036,
        "confirm_live": confirm_live,
    }


class LocalAdapterContractTests(unittest.TestCase):
    def test_request_rejects_unknown_fields_paths_and_boolean_seed(self) -> None:
        for bad in (
            {**request(), "output": "../../escape.json"},
            {**request(), "worldline_id": "../../escape"},
            {**request(), "seed": True},
        ):
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                _exact_request(bad)

    def test_live_provider_requires_per_request_and_startup_grants(self) -> None:
        with self.assertRaisesRegex(ContractError, "per-request confirmation"):
            _exact_request(request("ollama"))
        service = LocalRunService(Path.cwd(), "a" * 40, {"fixture": ProviderGrant("fixture")})
        with self.assertRaisesRegex(ContractError, "not granted"):
            service.execute(request("ollama", confirm_live=True))

    def test_service_uses_fixed_catalog_and_returns_distinct_execution_ids(self) -> None:
        service = LocalRunService(Path.cwd(), "a" * 40, {"fixture": ProviderGrant("fixture")})

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


class LocalAdapterHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        service = LocalRunService(Path.cwd(), "a" * 40, {"fixture": ProviderGrant("fixture")})
        self.token = "test-session-token"
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            _handler(service, "http://127.0.0.1:4173", self.token),
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
            self.assertEqual("ready", json.load(response)["status"])
        bad = Request(f"{self.base}/api/health", headers={"Host": "attacker.example"})
        with self.assertRaises(HTTPError) as raised:
            urlopen(bad, timeout=2)
        self.assertEqual(403, raised.exception.code)

    def test_post_rejects_cross_origin_wrong_type_and_oversize(self) -> None:
        body = json.dumps(request()).encode()
        cases = (
            ({"Origin": "https://attacker.example", "Content-Type": "application/json", SESSION_HEADER: self.token}, body, 403),
            ({"Origin": "http://127.0.0.1:4173", "Content-Type": "text/plain", SESSION_HEADER: self.token}, body, 415),
            (
                {"Origin": "http://127.0.0.1:4173", "Content-Type": "application/json", SESSION_HEADER: self.token},
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


if __name__ == "__main__":
    unittest.main()
