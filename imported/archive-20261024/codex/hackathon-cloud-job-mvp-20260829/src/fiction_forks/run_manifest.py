"""Canonical contract for curated and job-produced run manifests."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date
from pathlib import PurePosixPath
from typing import Any

from .engine import ContractError

RUN_MANIFEST_SCHEMA_VERSION = "fiction_forks_run_manifest.v1"

REQUIRED_FIELDS = {
    "schema_version",
    "recorded_at",
    "run_kind",
    "ai_measured",
    "engine_commit",
    "engine_version",
    "scenario_id",
    "intervention_id",
    "seed",
    "run_id",
    "input_digest",
    "final_event_hash",
    "artifact_path",
    "artifact_sha256",
    "replay_equivalent",
}
OPTIONAL_FIELDS = {
    "social_config_id",
    "comparison_artifact_path",
    "comparison_artifact_sha256",
    "delay_artifact_path",
    "delay_artifact_sha256",
    "replay_artifact_path",
    "replay_artifact_sha256",
}
HASH_FIELDS = {
    "input_digest",
    "final_event_hash",
    "artifact_sha256",
    "comparison_artifact_sha256",
    "delay_artifact_sha256",
    "replay_artifact_sha256",
}
PATH_FIELDS = {
    "artifact_path",
    "comparison_artifact_path",
    "delay_artifact_path",
    "replay_artifact_path",
}
ARTIFACT_PAIRS = (
    ("comparison_artifact_path", "comparison_artifact_sha256"),
    ("delay_artifact_path", "delay_artifact_sha256"),
    ("replay_artifact_path", "replay_artifact_sha256"),
)


def validate_run_manifest(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError("run manifest must be an object")
    missing = sorted(REQUIRED_FIELDS - set(value))
    unknown = sorted(set(value) - REQUIRED_FIELDS - OPTIONAL_FIELDS)
    if missing or unknown:
        raise ContractError(
            f"run manifest fields mismatch: missing={missing}, unknown={unknown}"
        )
    if value["schema_version"] != RUN_MANIFEST_SCHEMA_VERSION:
        raise ContractError("unsupported run manifest schema_version")
    recorded_at = value["recorded_at"]
    if not isinstance(recorded_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", recorded_at):
        raise ContractError("run manifest recorded_at must use YYYY-MM-DD")
    try:
        date.fromisoformat(recorded_at)
    except ValueError as error:
        raise ContractError("run manifest recorded_at must be a real date") from error
    if value["run_kind"] not in {"fixture", "live"}:
        raise ContractError("run manifest run_kind must be fixture or live")
    if not isinstance(value["ai_measured"], bool):
        raise ContractError("run manifest ai_measured must be boolean")
    if value["ai_measured"] != (value["run_kind"] == "live"):
        raise ContractError("run manifest run_kind and ai_measured conflict")
    commit = value["engine_commit"]
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ContractError("run manifest engine_commit must be a full commit")
    for field in HASH_FIELDS & set(value):
        digest = value[field]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ContractError(f"run manifest {field} must be sha256")
    for field in PATH_FIELDS & set(value):
        path = value[field]
        parsed = PurePosixPath(path) if isinstance(path, str) else None
        if (
            parsed is None
            or not path
            or "\\" in path
            or parsed.is_absolute()
            or ".." in parsed.parts
        ):
            raise ContractError(f"run manifest {field} must be a relative POSIX path")
    for field in (
        "engine_version",
        "scenario_id",
        "intervention_id",
        "run_id",
    ):
        if not isinstance(value[field], str) or not value[field]:
            raise ContractError(f"run manifest {field} must be a non-empty string")
    if "social_config_id" in value and (
        not isinstance(value["social_config_id"], str) or not value["social_config_id"]
    ):
        raise ContractError("run manifest social_config_id must be a non-empty string")
    seed = value["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ContractError("run manifest seed must be an integer")
    if value["replay_equivalent"] is not True:
        raise ContractError("run manifest replay_equivalent must be true")
    for path_field, hash_field in ARTIFACT_PAIRS:
        if (path_field in value) != (hash_field in value):
            raise ContractError(
                f"run manifest {path_field} and {hash_field} must appear together"
            )
    return dict(value)
