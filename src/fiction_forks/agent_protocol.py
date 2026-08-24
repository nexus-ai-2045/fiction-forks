"""Bounded action protocol for the social-agent simulation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .engine import ContractError

ACTION_SCHEMA_VERSION = "fiction_forks_action.v1"
OBSERVATION_SCHEMA_VERSION = "fiction_forks_observation.v2"
SOCIAL_CONFIG_SCHEMA_VERSION = "fiction_forks_social_config.v1"
MAX_ROLES = 12
MAX_TURNS = 12
MAX_EVIDENCE = 100
MAX_ACTIONS = 100
MAX_TEXT_CHARS = 2_000
MAX_CONFIG_BYTES = 128_000
MAX_PROVIDER_CALLS = 60


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ContractError(
            f"{label} keys mismatch: missing={missing}, unknown={unknown}"
        )


def _require_unique_ids(items: list[Mapping[str, Any]], label: str) -> set[str]:
    ids: list[str] = []
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise ContractError(f"{label}.id must be a non-empty string")
        ids.append(item_id)
    if len(ids) != len(set(ids)):
        raise ContractError(f"{label} ids must be unique")
    return set(ids)


def validate_social_config(
    config: Mapping[str, Any], intervention: Mapping[str, Any]
) -> None:
    encoded = canonical_json(config).encode("utf-8")
    if len(encoded) > MAX_CONFIG_BYTES:
        raise ContractError(
            f"social_config exceeds {MAX_CONFIG_BYTES} UTF-8 bytes"
        )

    def validate_text_budget(value: Any, label: str) -> None:
        if isinstance(value, str) and len(value) > MAX_TEXT_CHARS:
            raise ContractError(f"{label} exceeds {MAX_TEXT_CHARS} characters")
        if isinstance(value, Mapping):
            for key, child in value.items():
                validate_text_budget(child, f"{label}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                validate_text_budget(child, f"{label}[{index}]")

    validate_text_budget(config, "social_config")
    _require_exact_keys(
        config,
        {
            "schema_version",
            "id",
            "title",
            "assumption_notice",
            "turns",
            "roles",
            "evidence",
            "actions",
            "node_requirements",
            "missing_action_delay_years",
        },
        "social_config",
    )
    if config["schema_version"] != SOCIAL_CONFIG_SCHEMA_VERSION:
        raise ContractError("unsupported social_config schema_version")
    for field in ("id", "title", "assumption_notice"):
        if not isinstance(config[field], str) or not config[field]:
            raise ContractError(f"social_config.{field} must be a non-empty string")

    turns = config["turns"]
    if not isinstance(turns, list) or not 1 <= len(turns) <= MAX_TURNS:
        raise ContractError("social_config.turns must be a non-empty list")
    for index, turn in enumerate(turns, start=1):
        if not isinstance(turn, Mapping):
            raise ContractError(f"turn:{index} must be an object")
        _require_exact_keys(turn, {"id", "event"}, f"turn:{index}")
        if not all(isinstance(turn[key], str) and turn[key] for key in turn):
            raise ContractError(f"turn:{index} values must be non-empty strings")

    roles = config["roles"]
    if not isinstance(roles, list) or not 2 <= len(roles) <= MAX_ROLES:
        raise ContractError(
            f"social_config.roles must contain 2 to {MAX_ROLES} roles"
        )
    role_ids = _require_unique_ids(roles, "roles")
    if len(roles) * len(turns) > MAX_PROVIDER_CALLS:
        raise ContractError(
            f"social_config exceeds {MAX_PROVIDER_CALLS} provider calls per run"
        )
    for role in roles:
        _require_exact_keys(
            role,
            {"id", "title", "objective", "private_context"},
            f"role:{role['id']}",
        )
        if not all(isinstance(role[key], str) and role[key] for key in role):
            raise ContractError(f"role:{role['id']} values must be non-empty strings")

    evidence = config["evidence"]
    if not isinstance(evidence, list) or len(evidence) > MAX_EVIDENCE:
        raise ContractError(
            f"social_config.evidence must contain at most {MAX_EVIDENCE} items"
        )
    _require_unique_ids(evidence, "evidence")
    for item in evidence:
        _require_exact_keys(
            item,
            {"id", "summary", "visibility", "audience"},
            f"evidence:{item['id']}",
        )
        if item["visibility"] not in {"public", "private"}:
            raise ContractError(f"evidence:{item['id']} has invalid visibility")
        if not isinstance(item["summary"], str) or not item["summary"]:
            raise ContractError(f"evidence:{item['id']}.summary must be a string")
        audience = item["audience"]
        if not isinstance(audience, list) or not set(audience).issubset(role_ids):
            raise ContractError(f"evidence:{item['id']} has invalid audience")
        if item["visibility"] == "private" and not audience:
            raise ContractError(f"evidence:{item['id']} private audience is empty")

    actions = config["actions"]
    if not isinstance(actions, list) or not 1 <= len(actions) <= MAX_ACTIONS:
        raise ContractError(
            f"social_config.actions must contain 1 to {MAX_ACTIONS} items"
        )
    action_ids = _require_unique_ids(actions, "actions")
    if "abstain" not in action_ids:
        raise ContractError("social_config.actions must define abstain")
    for action in actions:
        _require_exact_keys(
            action,
            {"id", "title", "allowed_roles", "capability", "reversible"},
            f"action:{action['id']}",
        )
        if not isinstance(action["allowed_roles"], list) or not set(
            action["allowed_roles"]
        ).issubset(role_ids):
            raise ContractError(f"action:{action['id']} has invalid allowed_roles")
        for field in ("title", "capability"):
            if not isinstance(action[field], str) or not action[field]:
                raise ContractError(
                    f"action:{action['id']}.{field} must be a non-empty string"
                )
        if not isinstance(action["reversible"], bool):
            raise ContractError(f"action:{action['id']}.reversible must be boolean")

    nodes = {
        node["id"] for node in intervention["technology_tree"]["nodes"]
    }
    requirements = config["node_requirements"]
    if not isinstance(requirements, Mapping) or set(requirements) != nodes:
        raise ContractError("node_requirements must cover every technology node")
    for node_id, required_actions in requirements.items():
        if not isinstance(required_actions, list) or not required_actions:
            raise ContractError(f"node_requirements:{node_id} must not be empty")
        if not set(required_actions).issubset(action_ids - {"abstain"}):
            raise ContractError(f"node_requirements:{node_id} has unknown action")

    delay = config["missing_action_delay_years"]
    if isinstance(delay, bool) or not isinstance(delay, int) or delay < 1:
        raise ContractError("missing_action_delay_years must be a positive integer")


def action_json_schema(observation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "string", "const": ACTION_SCHEMA_VERSION},
            "run_id": {"type": "string", "const": observation["run_id"]},
            "turn": {"type": "integer", "const": observation["turn"]},
            "agent_id": {"type": "string", "const": observation["role"]["id"]},
            "action_id": {
                "type": "string",
                "enum": [item["id"] for item in observation["allowed_actions"]],
            },
            "stance": {
                "type": "string",
                "enum": ["support", "condition", "oppose", "abstain"],
            },
            "responds_to": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        item["intent_id"]
                        for item in observation["prior_public_actions"]
                    ],
                },
                "maxItems": 2,
                "uniqueItems": True,
            },
            "target_ids": {
                "type": "array",
                "items": {"type": "string", "enum": observation["peer_ids"]},
                "maxItems": 2,
                "uniqueItems": True,
            },
            "evidence_ids": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [item["id"] for item in observation["evidence"]],
                },
                "maxItems": 3,
                "uniqueItems": True,
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "conditions": {
                "type": "array",
                "items": {"type": "string", "maxLength": 160},
                "maxItems": 3,
            },
            "text": {"type": "string", "minLength": 1, "maxLength": 280},
        },
        "required": [
            "schema_version",
            "run_id",
            "turn",
            "agent_id",
            "action_id",
            "stance",
            "responds_to",
            "target_ids",
            "evidence_ids",
            "confidence",
            "conditions",
            "text",
        ],
    }


def validate_action(
    action: Mapping[str, Any], observation: Mapping[str, Any]
) -> dict[str, Any]:
    expected = set(action_json_schema(observation)["required"])
    _require_exact_keys(action, expected, "action")
    fixed = {
        "schema_version": ACTION_SCHEMA_VERSION,
        "run_id": observation["run_id"],
        "turn": observation["turn"],
        "agent_id": observation["role"]["id"],
    }
    for key, expected_value in fixed.items():
        if action[key] != expected_value:
            raise ContractError(f"action.{key} does not match observation")

    allowed_actions = {item["id"] for item in observation["allowed_actions"]}
    if action["action_id"] not in allowed_actions:
        raise ContractError("action.action_id is not allowed for this role")
    for key, allowed, limit in (
        ("target_ids", set(observation["peer_ids"]), 2),
        ("evidence_ids", {item["id"] for item in observation["evidence"]}, 3),
        (
            "responds_to",
            {item["intent_id"] for item in observation["prior_public_actions"]},
            2,
        ),
    ):
        values = action[key]
        if not isinstance(values, list) or len(values) > limit:
            raise ContractError(f"action.{key} has invalid shape")
        if len(values) != len(set(values)) or not set(values).issubset(allowed):
            raise ContractError(f"action.{key} contains unavailable values")

    confidence = action["confidence"]
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0 <= float(confidence) <= 1
    ):
        raise ContractError("action.confidence must be between 0 and 1")
    conditions = action["conditions"]
    if (
        not isinstance(conditions, list)
        or len(conditions) > 3
        or any(not isinstance(item, str) or len(item) > 160 for item in conditions)
    ):
        raise ContractError("action.conditions has invalid shape")
    stance = action["stance"]
    if stance not in {"support", "condition", "oppose", "abstain"}:
        raise ContractError("action.stance is invalid")
    if stance == "condition" and not conditions:
        raise ContractError("conditional action requires conditions")
    if stance == "oppose" and not action["responds_to"]:
        raise ContractError("opposition requires responds_to")
    if stance in {"oppose", "abstain"} and action["action_id"] != "abstain":
        raise ContractError("oppose/abstain stance must use abstain action")
    if stance in {"support", "condition"} and action["action_id"] == "abstain":
        raise ContractError("support/condition stance cannot use abstain action")
    text = action["text"]
    if not isinstance(text, str) or not 1 <= len(text) <= 280:
        raise ContractError("action.text must contain 1 to 280 characters")
    return dict(action)
