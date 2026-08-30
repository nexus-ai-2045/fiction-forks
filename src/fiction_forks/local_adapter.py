"""Loopback-only HTTP adapter for the canonical simulation CLI.

The adapter deliberately accepts identifiers, never filesystem paths or model
names.  Every run is executed by the existing CLI in a temporary directory so
the browser cannot acquire broader authority than the server operator granted
at startup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import hmac
import secrets
import subprocess
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence

from .engine import ContractError

REQUEST_SCHEMA = "fiction_forks_local_run_request.v1"
RESPONSE_SCHEMA = "fiction_forks_local_run_response.v1"
MAX_REQUEST_BYTES = 4_096
DEFAULT_TIMEOUT_SECONDS = 180
WORLDLINES = {
    "haruhi-world-observation": {
        "scenario": "scenarios/japan-2036/scenario.json",
        "intervention": "interventions/haruhi-world-observation.json",
        "social_config": "scenarios/japan-2036/social-haruhi-world-observation.json",
        "fixture": "fixtures/social/haruhi-world-observation.jsonl",
    }
}


def _exact_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ContractError("request body must be an object")
    expected = {"schema_version", "worldline_id", "provider", "seed", "confirm_live"}
    if set(payload) != expected:
        raise ContractError("request keys do not match the local run contract")
    if payload["schema_version"] != REQUEST_SCHEMA:
        raise ContractError("unsupported local run request schema")
    if payload["worldline_id"] not in WORLDLINES:
        raise ContractError("worldline_id is not allowlisted")
    if payload["provider"] not in {"fixture", "ollama", "vertex"}:
        raise ContractError("provider is not supported")
    if not isinstance(payload["confirm_live"], bool):
        raise ContractError("confirm_live must be boolean")
    if (payload["provider"] == "fixture") != (payload["confirm_live"] is False):
        raise ContractError("live providers require per-request confirmation")
    seed = payload["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**31 - 1:
        raise ContractError("seed must be a non-negative 32-bit integer")
    return dict(payload)


@dataclass(frozen=True)
class ProviderGrant:
    name: str
    model: str | None = None
    project: str | None = None
    location: str | None = None


@dataclass
class LocalRunService:
    repo_root: Path
    source_revision: str
    grants: Mapping[str, ProviderGrant]
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        self.repo_root = self.repo_root.resolve()
        self._run_lock = threading.Lock()

    def execute(self, raw_payload: Any) -> dict[str, Any]:
        payload = _exact_request(raw_payload)
        provider = payload["provider"]
        grant = self.grants.get(provider)
        if grant is None:
            raise ContractError(f"provider {provider} was not granted at server startup")
        if not self._run_lock.acquire(blocking=False):
            raise ContractError("another simulation is already running")
        try:
            return self._execute(payload, grant)
        finally:
            self._run_lock.release()

    def _execute(self, payload: Mapping[str, Any], grant: ProviderGrant) -> dict[str, Any]:
        worldline = WORLDLINES[payload["worldline_id"]]
        with tempfile.TemporaryDirectory(prefix="fiction-forks-local-run-") as temp:
            output = Path(temp, "result.json")
            bundle_output = Path(temp, "bundle.json")
            command = [
                sys.executable,
                "-m",
                "fiction_forks",
                "social",
                "--scenario",
                worldline["scenario"],
                "--intervention",
                worldline["intervention"],
                "--social-config",
                worldline["social_config"],
                "--provider",
                grant.name,
                "--seed",
                str(payload["seed"]),
                "--output",
                str(output),
                "--bundle-output",
                str(bundle_output),
                "--source-revision",
                self.source_revision,
            ]
            if grant.name == "fixture":
                command.extend(["--fixture", worldline["fixture"]])
            elif grant.name == "ollama":
                command.extend(["--model", grant.model or "", "--confirm-live"])
            elif grant.name == "vertex":
                command.extend(
                    [
                        "--model",
                        grant.model or "",
                        "--project",
                        grant.project or "",
                        "--location",
                        grant.location or "",
                        "--confirm-live",
                    ]
                )
            try:
                completed = subprocess.run(
                    command,
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="strict",
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise ContractError("simulation timed out") from error
            if completed.returncode != 0:
                raise ContractError("simulation failed without exposing provider output")
            try:
                result_bytes = output.read_bytes()
                bundle_bytes = bundle_output.read_bytes()
                result = json.loads(result_bytes)
                bundle = json.loads(bundle_bytes)
            except (OSError, json.JSONDecodeError) as error:
                raise ContractError("simulation did not produce valid artifacts") from error
        result_sha = hashlib.sha256(result_bytes).hexdigest()
        bundle_sha = hashlib.sha256(bundle_bytes).hexdigest()
        execution_id = f"ffx-{uuid.uuid4().hex}"
        return {
            "schema_version": RESPONSE_SCHEMA,
            "run_id": result["run_id"],
            "execution_id": execution_id,
            "provider": result["provider"],
            "source_revision": self.source_revision,
            "result_sha256": result_sha,
            "bundle_sha256": bundle_sha,
            "result": result,
            "bundle": bundle,
        }


SESSION_HEADER = "X-Fiction-Forks-Session"


def _handler(service: LocalRunService, allowed_origin: str, session_token: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "FictionForksLocal/1"

        def _host_allowed(self) -> bool:
            port = self.server.server_address[1]
            return self.headers.get("Host") in {
                f"127.0.0.1:{port}",
                f"localhost:{port}",
                f"[::1]:{port}",
            }

        def _json(self, status: HTTPStatus, payload: Mapping[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            origin = self.headers.get("Origin")
            if origin == allowed_origin:
                self.send_header("Access-Control-Allow-Origin", allowed_origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if not self._host_allowed():
                self._json(HTTPStatus.FORBIDDEN, {"error": "host_not_allowed"})
                return
            if self.path != "/api/health":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            self._json(
                HTTPStatus.OK,
                {
                    "status": "ready",
                    "schema_version": RESPONSE_SCHEMA,
                    "providers": sorted(service.grants),
                    "worldlines": sorted(WORLDLINES),
                },
            )

        def do_POST(self) -> None:  # noqa: N802
            if not self._host_allowed():
                self._json(HTTPStatus.FORBIDDEN, {"error": "host_not_allowed"})
                return
            if self.path != "/api/runs":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 1 <= length <= MAX_REQUEST_BYTES:
                if 0 < length <= MAX_REQUEST_BYTES + 1:
                    self.rfile.read(length)
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid_request_size"})
                return
            body = self.rfile.read(length)
            if self.headers.get("Origin") != allowed_origin:
                self._json(HTTPStatus.FORBIDDEN, {"error": "origin_not_allowed"})
                return
            supplied_token = self.headers.get(SESSION_HEADER, "")
            if not hmac.compare_digest(supplied_token, session_token):
                self._json(HTTPStatus.FORBIDDEN, {"error": "session_not_allowed"})
                return
            if self.headers.get("Content-Type") != "application/json":
                self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "content_type_not_allowed"})
                return
            try:
                payload = json.loads(body)
                response = service.execute(payload)
            except (json.JSONDecodeError, ContractError):
                self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_run_request"})
                return
            self._json(HTTPStatus.OK, response)

        def do_OPTIONS(self) -> None:  # noqa: N802
            if not self._host_allowed() or self.path != "/api/runs":
                self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})
                return
            if self.headers.get("Origin") != allowed_origin:
                self._json(HTTPStatus.FORBIDDEN, {"error": "origin_not_allowed"})
                return
            if self.headers.get("Access-Control-Request-Method") != "POST":
                self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"})
                return
            requested_headers = {
                item.strip().lower()
                for item in self.headers.get("Access-Control-Request-Headers", "").split(",")
                if item.strip()
            }
            if requested_headers != {"content-type", SESSION_HEADER.lower()}:
                self._json(HTTPStatus.FORBIDDEN, {"error": "headers_not_allowed"})
                return
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Access-Control-Allow-Origin", allowed_origin)
            self.send_header("Access-Control-Allow-Methods", "POST")
            self.send_header("Access-Control-Allow-Headers", f"Content-Type, {SESSION_HEADER}")
            self.send_header("Access-Control-Max-Age", "300")
            self.send_header("Vary", "Origin")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def _source_revision(repo_root: Path) -> str:
    try:
        value = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ContractError("local adapter requires a readable Git checkout") from error
    if len(value) != 40:
        raise ContractError("local adapter could not resolve a source revision")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fiction Forks loopback run adapter")
    parser.add_argument("--host", default="127.0.0.1", choices=("127.0.0.1",))
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--origin", default="http://127.0.0.1:4173")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--allow-ollama-model")
    parser.add_argument("--allow-vertex-model")
    parser.add_argument("--vertex-project")
    parser.add_argument("--vertex-location", default="us-central1")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    grants: dict[str, ProviderGrant] = {"fixture": ProviderGrant("fixture")}
    if args.allow_ollama_model:
        grants["ollama"] = ProviderGrant("ollama", model=args.allow_ollama_model)
    if bool(args.allow_vertex_model) != bool(args.vertex_project):
        raise ContractError("Vertex requires both model and project startup grants")
    if args.allow_vertex_model:
        grants["vertex"] = ProviderGrant(
            "vertex",
            model=args.allow_vertex_model,
            project=args.vertex_project,
            location=args.vertex_location,
        )
    service = LocalRunService(root, _source_revision(root), grants)
    session_token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(
        (args.host, args.port), _handler(service, args.origin, session_token)
    )
    print(f"Fiction Forks local adapter: http://{args.host}:{args.port}")
    print(f"{SESSION_HEADER}: {session_token}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
