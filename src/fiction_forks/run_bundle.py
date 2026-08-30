"""Project a canonical social result into meta-security-run-bundle/v1."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

import rfc8785

from .engine import ContractError

BUNDLE_SCHEMA = "meta-security-run-bundle/v1"
PRODUCT_ID = "fiction-forks"
SOURCE_REPOSITORY = "nexus-ai-2045/fiction-forks"
ADAPTER_ID = "fiction-forks/social-result-v1"


def event_stream_sha256(events: Sequence[Mapping[str, Any]]) -> str:
    """Hash RFC 8785 event records, each terminated by one LF byte."""

    try:
        payload = b"".join(rfc8785.dumps(event) + b"\n" for event in events)
    except (rfc8785.CanonicalizationError, UnicodeEncodeError) as error:
        raise ContractError("event stream is not canonical JSON") from error
    return hashlib.sha256(payload).hexdigest()


def build_run_bundle(
    result: Mapping[str, Any],
    *,
    command: Sequence[str],
    requested_at: str,
    started_at: str,
    completed_at: str,
    generated_at: str,
    source_revision: str,
    stdout_sha256: str,
) -> dict[str, Any]:
    """Build the Studio exchange envelope without changing domain results."""

    required = {"run_id", "scenario_id", "intervention_id", "seed", "actions"}
    missing = sorted(required - result.keys())
    if missing:
        raise ContractError(
            f"social result is missing bundle fields: {', '.join(missing)}"
        )
    if not isinstance(result["run_id"], str) or not result["run_id"]:
        raise ContractError("social result run_id must be a nonempty string")
    if type(result["seed"]) is not int or result["seed"] < 0:
        raise ContractError("social result seed must be a non-negative integer")
    if not isinstance(result["actions"], list) or not result["actions"]:
        raise ContractError("social result actions must be a nonempty list")
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise ContractError("bundle command must contain nonempty strings")
    if len(source_revision) != 40 or any(
        c not in "0123456789abcdef" for c in source_revision
    ):
        raise ContractError("source revision must be a 40-character lowercase SHA-1")
    if len(stdout_sha256) != 64 or any(
        c not in "0123456789abcdef" for c in stdout_sha256
    ):
        raise ContractError("stdout digest must be a 64-character lowercase SHA-256")

    run_id = result["run_id"]
    events = [
        {
            "run_id": run_id,
            "sequence": sequence,
            "event_type": (
                "social.action.committed"
                if receipt.get("valid")
                else "social.action.rejected"
            ),
            "occurred_at": completed_at,
            "payload": {"receipt": receipt},
        }
        for sequence, receipt in enumerate(result["actions"])
    ]
    stream_digest = event_stream_sha256(events)
    return {
        "schema": BUNDLE_SCHEMA,
        "product_id": PRODUCT_ID,
        "run_request": {
            "run_id": run_id,
            "scenario_id": result["scenario_id"],
            "seed": result["seed"],
            "requested_at": requested_at,
            "parameters": {
                "intervention_id": result["intervention_id"],
                "provider": result.get("provider", {}),
            },
        },
        "events": events,
        "replay": {
            "run_id": run_id,
            "product_id": PRODUCT_ID,
            "seed": result["seed"],
            "event_count": len(events),
            "event_stream_sha256": stream_digest,
            "deterministic": True,
        },
        "evidence": {
            "run_id": run_id,
            "product_id": PRODUCT_ID,
            "verification": "live-command",
            "generated_at": generated_at,
            "source_repository": SOURCE_REPOSITORY,
            "event_stream_sha256": stream_digest,
            "execution": {
                "adapter_id": ADAPTER_ID,
                "command": list(command),
                "exit_code": 0,
                "started_at": started_at,
                "completed_at": completed_at,
                "source_revision": source_revision,
                "stdout_sha256": stdout_sha256,
            },
        },
    }
