"""Multi-agent social simulation constrained by deterministic world physics."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .agent_protocol import (
    ACTION_SCHEMA_VERSION,
    OBSERVATION_SCHEMA_VERSION,
    canonical_json,
    digest,
    validate_action,
    validate_social_config,
)
from .engine import (
    ENGINE_VERSION,
    ContractError,
    compare_worlds,
    validate_intervention,
    validate_scenario,
)
from .providers import ActionProvider

SOCIAL_RESULT_SCHEMA_VERSION = "fiction_forks_social_result.v1"
PROTOCOL_VERSION = "1.0.0"


def _accessible_evidence(
    config: Mapping[str, Any], role_id: str
) -> list[dict[str, str]]:
    visible: list[dict[str, str]] = []
    for item in config["evidence"]:
        if item["visibility"] == "public" or role_id in item["audience"]:
            visible.append({"id": item["id"], "summary": item["summary"]})
    return visible


def _build_observation(
    *,
    config: Mapping[str, Any],
    input_digest: str,
    run_id: str,
    turn_number: int,
    role: Mapping[str, Any],
    prior_public_actions: list[Mapping[str, Any]],
) -> dict[str, Any]:
    allowed_actions = [
        {
            "id": action["id"],
            "title": action["title"],
            "capability": action["capability"],
            "reversible": action["reversible"],
        }
        for action in config["actions"]
        if role["id"] in action["allowed_roles"]
    ]
    return {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "input_digest": input_digest,
        "run_id": run_id,
        "turn": turn_number,
        "turn_event": config["turns"][turn_number - 1],
        "role": dict(role),
        "peer_ids": [
            candidate["id"]
            for candidate in config["roles"]
            if candidate["id"] != role["id"]
        ],
        "evidence": _accessible_evidence(config, role["id"]),
        "allowed_actions": allowed_actions,
        "prior_public_actions": deepcopy(prior_public_actions),
    }


def _abstain(observation: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "schema_version": ACTION_SCHEMA_VERSION,
        "run_id": observation["run_id"],
        "turn": observation["turn"],
        "agent_id": observation["role"]["id"],
        "action_id": "abstain",
        "stance": "abstain",
        "responds_to": [],
        "target_ids": [],
        "evidence_ids": [],
        "confidence": 0.0,
        "conditions": [],
        "text": f"abstain:{reason}",
    }


def _safe_reason(error: Exception) -> str:
    if isinstance(error, ContractError):
        return "contract_error"
    return "provider_error"


def _public_receipt_action(
    action: Mapping[str, Any], public_evidence_ids: set[str]
) -> dict[str, Any]:
    """Project untrusted model prose and role-scoped evidence out of artifacts."""
    return {
        "schema_version": action["schema_version"],
        "run_id": action["run_id"],
        "turn": action["turn"],
        "agent_id": action["agent_id"],
        "action_id": action["action_id"],
        "stance": action["stance"],
        "responds_to": list(action["responds_to"]),
        "target_ids": list(action["target_ids"]),
        "evidence_ids": [
            evidence_id
            for evidence_id in action["evidence_ids"]
            if evidence_id in public_evidence_ids
        ],
        "confidence": action["confidence"],
        "condition_count": len(action["conditions"]),
        "text_redacted": True,
    }


def run_social_simulation(
    scenario: Mapping[str, Any],
    intervention: Mapping[str, Any],
    social_config: Mapping[str, Any],
    provider: ActionProvider,
    *,
    seed: int = 2036,
) -> dict[str, Any]:
    validate_scenario(scenario)
    validate_intervention(intervention, scenario)
    validate_social_config(social_config, intervention)

    run_inputs = {
        "protocol_version": PROTOCOL_VERSION,
        "engine_version": ENGINE_VERSION,
        "scenario": scenario,
        "intervention": intervention,
        "social_config": social_config,
        "seed": seed,
    }
    input_digest = digest(run_inputs)
    run_id = f"ff-{input_digest[:16]}"
    action_catalog = {item["id"]: item for item in social_config["actions"]}
    social_state: dict[str, Any] = {
        "committed_intent_ids": [],
        "interaction_edges": [],
    }
    receipts: list[dict[str, Any]] = []
    prior_public_actions: list[dict[str, Any]] = []
    chain_hash = digest({"input_digest": input_digest})
    public_evidence_ids = {
        item["id"]
        for item in social_config["evidence"]
        if item["visibility"] == "public"
    }

    for turn_number, _turn in enumerate(social_config["turns"], start=1):
        pending: list[tuple[dict[str, Any], bool, str | None]] = []
        for role in social_config["roles"]:
            observation = _build_observation(
                config=social_config,
                input_digest=input_digest,
                run_id=run_id,
                turn_number=turn_number,
                role=role,
                prior_public_actions=prior_public_actions,
            )
            try:
                action = validate_action(provider.choose(observation), observation)
                pending.append((action, True, None))
            except Exception as error:  # provider data is an untrusted boundary
                reason = _safe_reason(error)
                pending.append((_abstain(observation, reason), False, reason))

        committed_this_turn: list[dict[str, Any]] = []
        for action, valid, invalid_reason in sorted(
            pending, key=lambda item: item[0]["agent_id"]
        ):
            intent_id = f"t{turn_number}:{action['agent_id']}"
            receipt_action = _public_receipt_action(action, public_evidence_ids)
            before_hash = digest(social_state)
            if valid:
                social_state["committed_intent_ids"].append(intent_id)
                for target_intent_id in action["responds_to"]:
                    social_state["interaction_edges"].append(
                        {
                            "from_intent_id": intent_id,
                            "to_intent_id": target_intent_id,
                            "stance": action["stance"],
                        }
                    )
            after_hash = digest(social_state)
            receipt_without_hash = {
                "intent_id": intent_id,
                "action": receipt_action,
                "valid": valid,
                "invalid_reason": invalid_reason,
                "state_before_hash": before_hash,
                "state_after_hash": after_hash,
            }
            event_hash = digest(
                {
                    "previous_event_hash": chain_hash,
                    "receipt": receipt_without_hash,
                }
            )
            receipt = {
                **receipt_without_hash,
                "previous_event_hash": chain_hash,
                "event_hash": event_hash,
            }
            chain_hash = event_hash
            receipts.append(receipt)
            public_action = deepcopy(action)
            public_action["evidence_ids"] = [
                evidence_id
                for evidence_id in public_action["evidence_ids"]
                if evidence_id in public_evidence_ids
            ]
            committed_this_turn.append(
                {"intent_id": intent_id, **public_action}
            )
        prior_public_actions.extend(committed_this_turn)

    opposed_intents = {
        target_intent_id
        for item in receipts
        if item["valid"] and item["action"]["stance"] == "oppose"
        for target_intent_id in item["action"]["responds_to"]
    }
    selected = {
        item["action"]["action_id"]
        for item in receipts
        if item["valid"]
        and item["intent_id"] not in opposed_intents
        and item["action"]["stance"] in {"support", "condition"}
        and item["action"]["action_id"] != "abstain"
    }
    capabilities = sorted(
        {action_catalog[action_id]["capability"] for action_id in selected}
    )
    missing_by_node: dict[str, list[str]] = {}
    technology_delays: dict[str, int] = {}
    for node_id, requirements in social_config["node_requirements"].items():
        missing = sorted(set(requirements) - selected)
        missing_by_node[node_id] = missing
        technology_delays[node_id] = (
            len(missing) * int(social_config["missing_action_delay_years"])
        )

    world_comparison = compare_worlds(
        scenario,
        intervention,
        seed=seed,
        technology_delays=technology_delays,
    )
    non_abstain = [
        item
        for item in receipts
        if item["valid"] and item["action"]["action_id"] != "abstain"
    ]
    reversible_count = sum(
        1
        for item in non_abstain
        if action_catalog[item["action"]["action_id"]]["reversible"]
    )
    evidence_ids = {
        evidence_id
        for item in receipts
        for evidence_id in item["action"]["evidence_ids"]
    }
    metrics = {
        "action_count": len(receipts),
        "valid_action_count": sum(1 for item in receipts if item["valid"]),
        "invalid_action_count": sum(1 for item in receipts if not item["valid"]),
        "abstention_count": sum(
            1 for item in receipts if item["action"]["action_id"] == "abstain"
        ),
        "referenced_evidence_count": len(evidence_ids),
        "capability_coverage": len(capabilities),
        "interaction_edge_count": len(social_state["interaction_edges"]),
        "conditioned_intent_count": sum(
            1
            for item in receipts
            if item["valid"] and item["action"]["stance"] == "condition"
        ),
        "opposed_intent_count": len(opposed_intents),
        "reversible_action_ratio": round(
            reversible_count / len(non_abstain), 3
        )
        if non_abstain
        else 0.0,
    }
    result = {
        "schema_version": SOCIAL_RESULT_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "engine_version": ENGINE_VERSION,
        "run_id": run_id,
        "input_digest": input_digest,
        "scenario_id": scenario["id"],
        "intervention_id": intervention["id"],
        "seed": seed,
        "provider": {"name": provider.name, "model": provider.model},
        "roles": [role["id"] for role in social_config["roles"]],
        "turn_count": len(social_config["turns"]),
        "actions": receipts,
        "final_event_hash": chain_hash,
        "selected_action_ids": sorted(selected),
        "interaction_edges": deepcopy(social_state["interaction_edges"]),
        "missing_actions_by_node": missing_by_node,
        "technology_delays": technology_delays,
        "metrics": metrics,
        "world_comparison": world_comparison,
        "assumption_notice": social_config["assumption_notice"],
    }
    verifier = getattr(provider, "verify_result", None)
    if callable(verifier):
        verifier(result)
    return result


def replay_equivalent(
    original: Mapping[str, Any], replayed: Mapping[str, Any]
) -> bool:
    keys = (
        "run_id",
        "input_digest",
        "actions",
        "final_event_hash",
        "selected_action_ids",
        "interaction_edges",
        "technology_delays",
        "metrics",
        "world_comparison",
    )
    return canonical_json({key: original[key] for key in keys}) == canonical_json(
        {key: replayed[key] for key in keys}
    )
