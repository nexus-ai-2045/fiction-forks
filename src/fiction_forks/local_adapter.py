"""Loopback-only HTTP adapter for the canonical simulation CLI.

The adapter deliberately accepts identifiers, never filesystem paths or model
names.  The run envelope carries an unmodified `ProvisionalRunRequest`, so the
local transport shares one participation contract with the public transport and
the preview template catalog stays the only place that declares an approved
worldline.  Every run is executed by the existing CLI in a temporary directory
so the browser cannot acquire broader authority than the server operator
granted at startup.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import hmac
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence

import rfc8785

from .engine import ContractError, load_json
from .participation import (
    resolve_template_inputs,
    validate_provisional_request,
    validate_template_catalog,
)

REQUEST_SCHEMA = "fiction_forks_local_run_request.v2"
RESPONSE_SCHEMA = "fiction_forks_local_run_response.v1"
MAX_REQUEST_BYTES = 4_096
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_SESSION_TTL_SECONDS = 900
CATALOG_PATH = "catalogs/intervention-templates.v1.json"
PROVIDER_IDS = ("fixture", "ollama", "vertex")
SUPPORTED_DELAY_PROFILE = "none"


def _exact_envelope(payload: Any) -> dict[str, Any]:
    """transport層のenvelopeだけを検査する。中身のrun_requestは participation が見る。"""

    if not isinstance(payload, Mapping):
        raise ContractError("request body must be an object")
    expected = {"schema_version", "run_request", "execution"}
    if set(payload) != expected:
        raise ContractError("request keys do not match the local run contract")
    if payload["schema_version"] != REQUEST_SCHEMA:
        raise ContractError("unsupported local run request schema")
    execution = payload["execution"]
    if not isinstance(execution, Mapping):
        raise ContractError("execution must be an object")
    if set(execution) != {"provider_id", "confirm_live"}:
        raise ContractError("execution keys do not match the local run contract")
    if execution["provider_id"] not in PROVIDER_IDS:
        raise ContractError("provider is not supported")
    if not isinstance(execution["confirm_live"], bool):
        raise ContractError("confirm_live must be boolean")
    return {
        "schema_version": REQUEST_SCHEMA,
        "run_request": payload["run_request"],
        "execution": dict(execution),
    }


class LocalRuntimeError(RuntimeError):
    """server側の要因で実行できない。requestが契約を満たしていても起こる。

    ContractErrorと分けるのは、operatorが「送ったrequestが悪い」と
    「serverが動いていない」を切り分けられるようにするためである。
    """

    status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR
    error_code: str = "local_run_failed"


class LocalBusyError(LocalRuntimeError):
    """先行runが実行中。同じrequestのまま再試行できるため500と区別する。"""

    status: HTTPStatus = HTTPStatus.CONFLICT
    error_code: str = "run_already_in_progress"


@dataclass(frozen=True)
class ProviderGrant:
    name: str
    model: str | None = None
    project: str | None = None
    location: str | None = None


def _token_bytes(value: str) -> bytes:
    """定数時間比較用のbytes化。

    `hmac.compare_digest`はstr同士だと非ASCII文字でTypeErrorを投げる。header値は
    latin-1でdecodeされて任意の非ASCII文字を含みうるため、比較前にbytesへ寄せる。
    surrogatepassはlone surrogateでも失敗させないためであり、値ごとに1対1で対応する。
    """

    return value.encode("utf-8", "surrogatepass")


@dataclass(frozen=True)
class SessionToken:
    """1 sessionだけ有効な短命capability token。"""

    value: str
    expires_at: float

    def matches(self, supplied: str, *, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        if current >= self.expires_at:
            return False
        return hmac.compare_digest(_token_bytes(supplied), _token_bytes(self.value))


def issue_session_token(ttl_seconds: int) -> SessionToken:
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or ttl_seconds < 1:
        raise ContractError("session token TTL must be a positive number of seconds")
    return SessionToken(secrets.token_urlsafe(32), time.monotonic() + ttl_seconds)


@dataclass
class LocalRunService:
    repo_root: Path
    source_revision: str
    grants: Mapping[str, ProviderGrant]
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        self.repo_root = self.repo_root.resolve()
        self._run_lock = threading.Lock()
        self._catalog = self._read_catalog()
        self._verified_catalog = self._verify_catalog()

    def _read_catalog(self) -> dict[str, Any]:
        return self._server_side(lambda: load_json(self.repo_root / CATALOG_PATH))

    def _verify_catalog(self) -> dict[str, Any]:
        """server側が用意したcatalogとその入力を検証する。

        catalogが壊れているのはoperatorの環境の問題であり、browserが送った
        requestの契約違反ではない。両方をContractErrorへ寄せると区別できなくなる。
        """

        return self._server_side(
            lambda: validate_template_catalog(self._catalog, root=self.repo_root)
        )

    @staticmethod
    def _server_side(action):
        """欠落file・壊れたJSON・壊れたcatalogをserver側の失敗として扱う。"""

        try:
            return action()
        except (OSError, json.JSONDecodeError, ContractError) as error:
            raise LocalRuntimeError("preview template catalog inputs are not usable") from error

    def _resolve_inputs(self, template_id: str) -> dict[str, str]:
        """検証済みcatalogからCLIへ渡すpathを取り出す。

        `resolve_template_inputs`は未登録templateとpreview不許可templateへ
        ContractErrorを投げる。これはrequest側の違反なので`_server_side`で
        包まない。包むと「あなたの要求は正しいがserverが壊れた」と逆向きに
        誤報する。file要因だけをserver側へ振る。
        """

        try:
            return resolve_template_inputs(
                self._catalog, template_id, root=self.repo_root
            )
        except (OSError, json.JSONDecodeError) as error:
            raise LocalRuntimeError("preview template catalog inputs are not usable") from error

    def health(self) -> dict[str, Any]:
        """browserがProvisionalRunRequestを組むための入力補助projection。

        承認そのものではない。返ってきたrequestは execute で再検証する。
        """

        return {
            "status": "ready",
            "schema_version": RESPONSE_SCHEMA,
            "providers": sorted(self.grants),
            "catalog_id": self._verified_catalog["catalog_id"],
            "catalog_version": self._verified_catalog["catalog_version"],
            "templates": [
                {
                    "template_id": template["template_id"],
                    "template_version": template["template_version"],
                    "scenario_id": template["scenario_id"],
                    "intervention_id": template["intervention_id"],
                    "intervention_sha256": template["intervention_sha256"],
                    "abstract_function": template["abstract_function"],
                    "allowed_seeds": list(template["allowed_seeds"]),
                    "delay_profiles": list(template["delay_profiles"]),
                }
                for template in self._verified_catalog["templates"]
                if template["status"] == "preview_allowed"
            ],
        }

    def execute(self, raw_payload: Any) -> dict[str, Any]:
        payload = _exact_envelope(raw_payload)
        execution = payload["execution"]
        # 先にcatalogを検証すると、この後のContractErrorはrequest側の違反だけになる。
        self._verify_catalog()
        run_request = validate_provisional_request(
            payload["run_request"], self._catalog, root=self.repo_root
        )
        provider_id = execution["provider_id"]
        grant = self.grants.get(provider_id)
        if grant is None:
            raise ContractError(f"provider {provider_id} was not granted at server startup")
        if execution["confirm_live"] is not (grant.name != "fixture"):
            raise ContractError("live providers require per-request confirmation")
        if run_request["delay_profile"] != SUPPORTED_DELAY_PROFILE:
            raise ContractError("local transport cannot honour this delay profile")
        inputs = self._resolve_inputs(run_request["template_id"])
        if not self._run_lock.acquire(blocking=False):
            raise LocalBusyError("another simulation is already running")
        try:
            return self._execute(run_request, inputs, grant)
        finally:
            self._run_lock.release()

    def _execute(
        self,
        run_request: Mapping[str, Any],
        inputs: Mapping[str, str],
        grant: ProviderGrant,
    ) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="fiction-forks-local-run-") as temp:
            output = Path(temp, "result.json")
            bundle_output = Path(temp, "bundle.json")
            command = [
                sys.executable,
                "-m",
                "fiction_forks",
                "social",
                "--scenario",
                inputs["scenario"],
                "--intervention",
                inputs["intervention"],
                "--social-config",
                inputs["social_config"],
                "--provider",
                grant.name,
                "--seed",
                str(run_request["seed"]),
                "--output",
                str(output),
                "--bundle-output",
                str(bundle_output),
                "--source-revision",
                self.source_revision,
            ]
            if grant.name == "fixture":
                command.extend(["--fixture", inputs["fixture"]])
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
                raise LocalRuntimeError("simulation timed out") from error
            if completed.returncode != 0:
                raise LocalRuntimeError("simulation failed without exposing provider output")
            try:
                result_bytes = output.read_bytes()
                bundle_bytes = bundle_output.read_bytes()
                result = json.loads(result_bytes)
                bundle = json.loads(bundle_bytes)
            except (OSError, json.JSONDecodeError) as error:
                raise LocalRuntimeError("simulation did not produce valid artifacts") from error
        result_sha = hashlib.sha256(result_bytes).hexdigest()
        bundle_sha = hashlib.sha256(bundle_bytes).hexdigest()
        event_stream_bytes = b"".join(
            rfc8785.dumps(event) + b"\n" for event in bundle["events"]
        )
        event_stream_sha = hashlib.sha256(event_stream_bytes).hexdigest()
        if (
            bundle.get("replay", {}).get("event_stream_sha256") != event_stream_sha
            or bundle.get("evidence", {}).get("event_stream_sha256") != event_stream_sha
        ):
            raise LocalRuntimeError("bundle event stream digest mismatch")
        execution_id = f"ffx-{uuid.uuid4().hex}"
        return {
            "schema_version": RESPONSE_SCHEMA,
            "run_id": result["run_id"],
            "execution_id": execution_id,
            "provider": result["provider"],
            "source_revision": self.source_revision,
            "result_sha256": result_sha,
            "bundle_sha256": bundle_sha,
            "result_artifact_base64": base64.b64encode(result_bytes).decode("ascii"),
            "bundle_artifact_base64": base64.b64encode(bundle_bytes).decode("ascii"),
            "event_stream_base64": base64.b64encode(event_stream_bytes).decode("ascii"),
            "result": result,
            "bundle": bundle,
        }


SESSION_HEADER = "X-Fiction-Forks-Session"


def _handler(service: LocalRunService, allowed_origin: str, session_token: SessionToken):
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
            self._json(HTTPStatus.OK, service.health())

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
            if not session_token.matches(self.headers.get(SESSION_HEADER, "")):
                self._json(HTTPStatus.FORBIDDEN, {"error": "session_not_allowed"})
                return
            if self.headers.get("Content-Type") != "application/json":
                self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "content_type_not_allowed"})
                return
            try:
                payload = json.loads(body)
                response = service.execute(payload)
            except (json.JSONDecodeError, ContractError):
                # envelopeとparticipationの検証失敗だけがrequest側の400になる。
                self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_run_request"})
                return
            except LocalRuntimeError as failure:
                # CLI失敗・timeout・server側入力の読み取り不能を400と混ぜない。
                self._json(failure.status, {"error": failure.error_code})
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
    parser.add_argument(
        "--session-ttl-seconds", default=DEFAULT_SESSION_TTL_SECONDS, type=int
    )
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
    session_token = issue_session_token(args.session_ttl_seconds)
    server = ThreadingHTTPServer(
        (args.host, args.port), _handler(service, args.origin, session_token)
    )
    print(f"Fiction Forks local adapter: http://{args.host}:{args.port}")
    print(f"{SESSION_HEADER}: {session_token.value}")
    print(f"session token expires after {args.session_ttl_seconds}s; restart to reissue")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
