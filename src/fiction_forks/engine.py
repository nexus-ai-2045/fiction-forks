"""透明で再現可能な状態遷移エンジン。"""

from __future__ import annotations

import json
import random
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


METRICS = (
    "living_systems",
    "strategic_autonomy",
    "cognitive_sovereignty",
    "legitimacy",
    "repair_capacity",
)


class ContractError(ValueError):
    """scenarioまたはinterventionが契約を満たさない。"""


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ContractError(f"JSON root must be an object: {path}")
    return value


def _validate_effects(effects: Mapping[str, Any], label: str) -> None:
    unknown = sorted(set(effects) - set(METRICS))
    if unknown:
        raise ContractError(f"{label} has unknown metrics: {unknown}")
    for metric, delta in effects.items():
        if not isinstance(delta, (int, float)):
            raise ContractError(f"{label}.{metric} must be numeric")


def validate_scenario(scenario: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "id",
        "title",
        "design_question",
        "causal_chain",
        "evidence_refs",
        "start_year",
        "end_year",
        "assumption_notice",
        "initial_state",
        "baseline_annual_effects",
        "capability_availability",
        "shocks",
        "collapse",
    }
    missing = sorted(required - set(scenario))
    if missing:
        raise ContractError(f"scenario missing fields: {missing}")
    if scenario["start_year"] > scenario["end_year"]:
        raise ContractError("start_year must be <= end_year")
    if not isinstance(scenario["design_question"], str) or not scenario[
        "design_question"
    ].strip():
        raise ContractError("design_question must be a non-empty string")
    if not isinstance(scenario["causal_chain"], list) or len(
        scenario["causal_chain"]
    ) < 2:
        raise ContractError("causal_chain must contain at least two steps")
    if not all(
        isinstance(step, str) and step.strip() for step in scenario["causal_chain"]
    ):
        raise ContractError("causal_chain steps must be non-empty strings")
    if not isinstance(scenario["evidence_refs"], list) or not scenario[
        "evidence_refs"
    ]:
        raise ContractError("evidence_refs must be a non-empty list")
    if set(scenario["initial_state"]) != set(METRICS):
        raise ContractError("initial_state must define exactly the five metrics")
    _validate_effects(scenario["initial_state"], "initial_state")
    for metric, value in scenario["initial_state"].items():
        if not 0 <= float(value) <= 100:
            raise ContractError(f"initial_state.{metric} must be between 0 and 100")
    _validate_effects(scenario["baseline_annual_effects"], "baseline_annual_effects")
    for shock in scenario["shocks"]:
        _validate_effects(shock["effects"], f"shock:{shock.get('id', 'unknown')}")
        if shock.get("variance", 0) < 0:
            raise ContractError("shock variance must be >= 0")
    collapse = scenario["collapse"]
    unknown = sorted(set(collapse["metrics"]) - set(METRICS))
    if unknown:
        raise ContractError(f"collapse has unknown metrics: {unknown}")
    if not 0 <= float(collapse["threshold"]) <= 100:
        raise ContractError("collapse threshold must be between 0 and 100")
    minimum_breaches = int(collapse["minimum_breaches"])
    if not 1 <= minimum_breaches <= len(collapse["metrics"]):
        raise ContractError("minimum_breaches must fit collapse.metrics")
    if int(collapse["consecutive_turns"]) < 1:
        raise ContractError("consecutive_turns must be >= 1")


def validate_intervention(
    intervention: Mapping[str, Any], scenario: Mapping[str, Any]
) -> None:
    required = {
        "schema_version",
        "id",
        "fiction_reference",
        "extracted_function",
        "realization_mode",
        "prerequisites",
        "activation_effects",
        "annual_effects",
        "costs",
        "side_effects",
        "failure_modes",
        "technology_tree",
    }
    missing = sorted(required - set(intervention))
    if missing:
        raise ContractError(f"intervention missing fields: {missing}")
    allowed_modes = {"literal", "functional_equivalent", "institutional_equivalent"}
    if intervention["realization_mode"] not in allowed_modes:
        raise ContractError("unknown realization_mode")
    unavailable = sorted(
        set(intervention["prerequisites"]) - set(scenario["capability_availability"])
    )
    if unavailable:
        raise ContractError(f"unknown prerequisites: {unavailable}")
    _validate_effects(intervention["activation_effects"], "activation_effects")
    _validate_effects(intervention["annual_effects"], "annual_effects")

    tree = intervention["technology_tree"]
    if not isinstance(tree, Mapping):
        raise ContractError("technology_tree must be an object")
    nodes = tree.get("nodes")
    activation_requires = tree.get("activation_requires")
    if not isinstance(nodes, list) or not nodes:
        raise ContractError("technology_tree.nodes must be a non-empty list")
    if not isinstance(activation_requires, list) or not activation_requires:
        raise ContractError(
            "technology_tree.activation_requires must be a non-empty list"
        )

    node_ids = [node.get("id") for node in nodes if isinstance(node, Mapping)]
    if len(node_ids) != len(nodes) or any(not value for value in node_ids):
        raise ContractError("every technology_tree node must have an id")
    if len(set(node_ids)) != len(node_ids):
        raise ContractError("technology_tree node ids must be unique")

    node_id_set = set(node_ids)
    external_capabilities = set(scenario["capability_availability"])
    referenced_external: set[str] = set()
    allowed_kinds = {"technology", "institution", "operations"}
    for node in nodes:
        if node.get("kind") not in allowed_kinds:
            raise ContractError(f"technology_tree:{node['id']} has unknown kind")
        if not isinstance(node.get("label"), str) or not node["label"].strip():
            raise ContractError(f"technology_tree:{node['id']} must have a label")
        if not isinstance(node.get("completion_evidence"), str) or not node[
            "completion_evidence"
        ].strip():
            raise ContractError(
                f"technology_tree:{node['id']} must have completion_evidence"
            )
        lead_time = node.get("lead_time_years")
        if not isinstance(lead_time, int) or lead_time < 0:
            raise ContractError(
                f"technology_tree:{node['id']}.lead_time_years must be a non-negative integer"
            )
        dependencies = node.get("depends_on")
        if not isinstance(dependencies, list):
            raise ContractError(
                f"technology_tree:{node['id']}.depends_on must be a list"
            )
        unknown_dependencies = sorted(
            set(dependencies) - node_id_set - external_capabilities
        )
        if unknown_dependencies:
            raise ContractError(
                f"technology_tree:{node['id']} has unknown dependencies: "
                f"{unknown_dependencies}"
            )
        referenced_external.update(set(dependencies) & external_capabilities)

    unknown_activation_nodes = sorted(set(activation_requires) - node_id_set)
    if unknown_activation_nodes:
        raise ContractError(
            "technology_tree.activation_requires has unknown nodes: "
            f"{unknown_activation_nodes}"
        )
    if set(intervention["prerequisites"]) != referenced_external:
        raise ContractError(
            "prerequisites must exactly match external capabilities used by technology_tree"
        )

    _technology_schedule(scenario, intervention)


def _apply_effects(
    state: dict[str, float], effects: Mapping[str, float]
) -> dict[str, float]:
    applied: dict[str, float] = {}
    for metric in sorted(effects):
        delta = float(effects[metric])
        state[metric] = min(100.0, max(0.0, state[metric] + delta))
        applied[metric] = delta
    return applied


def _shock_effects(
    shock: Mapping[str, Any], rng: random.Random
) -> dict[str, float]:
    variance = int(shock.get("variance", 0))
    return {
        metric: float(delta + (rng.randint(-variance, variance) if variance else 0))
        for metric, delta in sorted(shock["effects"].items())
    }


def _technology_schedule(
    scenario: Mapping[str, Any],
    intervention: Mapping[str, Any],
    delays: Mapping[str, int] | None = None,
) -> dict[str, int]:
    """技術・制度ノードの依存関係から最短完了年を決定する。"""

    nodes = {node["id"]: node for node in intervention["technology_tree"]["nodes"]}
    applied_delays = dict(delays or {})
    unknown_delays = sorted(set(applied_delays) - set(nodes))
    if unknown_delays:
        raise ContractError(f"technology delay has unknown nodes: {unknown_delays}")
    for node_id, delay in applied_delays.items():
        if not isinstance(delay, int) or delay < 0:
            raise ContractError(
                f"technology delay for {node_id} must be a non-negative integer"
            )
    external = {
        name: int(year)
        for name, year in scenario["capability_availability"].items()
    }
    schedule: dict[str, int] = {}
    visiting: set[str] = set()

    def completion_year(node_id: str) -> int:
        if node_id in schedule:
            return schedule[node_id]
        if node_id in visiting:
            raise ContractError(f"technology_tree has a cycle at: {node_id}")
        visiting.add(node_id)
        node = nodes[node_id]
        dependency_years = [int(scenario["start_year"])]
        for dependency in node["depends_on"]:
            if dependency in external:
                dependency_years.append(external[dependency])
            else:
                dependency_years.append(completion_year(dependency))
        completed = (
            max(dependency_years)
            + int(node["lead_time_years"])
            + applied_delays.get(node_id, 0)
        )
        visiting.remove(node_id)
        schedule[node_id] = completed
        return completed

    for node_id in nodes:
        completion_year(node_id)
    return schedule


def _activation_year(
    scenario: Mapping[str, Any],
    intervention: Mapping[str, Any],
    delays: Mapping[str, int] | None = None,
) -> int:
    schedule = _technology_schedule(scenario, intervention, delays)
    return max(
        schedule[node_id]
        for node_id in intervention["technology_tree"]["activation_requires"]
    )


def simulate(
    scenario: Mapping[str, Any],
    intervention: Mapping[str, Any] | None = None,
    *,
    seed: int = 2036,
    technology_delays: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    validate_scenario(scenario)
    if intervention is not None:
        validate_intervention(intervention, scenario)

    rng = random.Random(seed)
    state = {metric: float(scenario["initial_state"][metric]) for metric in METRICS}
    collapse_streak = 0
    collapsed = False
    collapse_year: int | None = None
    timeline: list[dict[str, Any]] = []
    activation_year = (
        _activation_year(scenario, intervention, technology_delays)
        if intervention is not None
        else None
    )
    technology_schedule = (
        _technology_schedule(scenario, intervention, technology_delays)
        if intervention is not None
        else None
    )

    shocks_by_year: dict[int, list[Mapping[str, Any]]] = {}
    for shock in scenario["shocks"]:
        shocks_by_year.setdefault(int(shock["year"]), []).append(shock)

    for year in range(int(scenario["start_year"]), int(scenario["end_year"]) + 1):
        events: list[dict[str, Any]] = []
        baseline_effects = _apply_effects(state, scenario["baseline_annual_effects"])
        events.append({"kind": "baseline", "effects": baseline_effects})

        for shock in shocks_by_year.get(year, []):
            effects = _shock_effects(shock, rng)
            _apply_effects(state, effects)
            events.append(
                {
                    "kind": "shock",
                    "id": shock["id"],
                    "label": shock["label"],
                    "effects": effects,
                }
            )

        if intervention is not None and activation_year is not None and year >= activation_year:
            if year == activation_year:
                effects = _apply_effects(state, intervention["activation_effects"])
                events.append(
                    {
                        "kind": "intervention_activation",
                        "id": intervention["id"],
                        "effects": effects,
                    }
                )
            effects = _apply_effects(state, intervention["annual_effects"])
            events.append(
                {
                    "kind": "intervention_annual",
                    "id": intervention["id"],
                    "effects": effects,
                }
            )

        collapse_rule = scenario["collapse"]
        breached = sorted(
            metric
            for metric in collapse_rule["metrics"]
            if state[metric] < float(collapse_rule["threshold"])
        )
        danger = len(breached) >= int(collapse_rule["minimum_breaches"])
        collapse_streak = collapse_streak + 1 if danger else 0
        if collapse_streak >= int(collapse_rule["consecutive_turns"]):
            collapsed = True
            collapse_year = year

        timeline.append(
            {
                "year": year,
                "state": {metric: round(state[metric], 2) for metric in METRICS},
                "events": events,
                "collapse_gate": {
                    "breached_metrics": breached,
                    "danger": danger,
                    "consecutive_danger_turns": collapse_streak,
                },
            }
        )
        if collapsed:
            break

    return {
        "schema_version": "fiction_forks_result.v1",
        "engine_version": "0.1.0",
        "scenario_id": scenario["id"],
        "intervention_id": intervention["id"] if intervention else None,
        "seed": seed,
        "activation_year": activation_year,
        "technology_schedule": technology_schedule,
        "technology_delays": dict(technology_delays or {}),
        "collapsed": collapsed,
        "collapse_year": collapse_year,
        "final_state": deepcopy(timeline[-1]["state"]),
        "timeline": timeline,
        "assumption_notice": scenario["assumption_notice"],
    }


def compare_worlds(
    scenario: Mapping[str, Any],
    intervention: Mapping[str, Any],
    *,
    seed: int = 2036,
    technology_delays: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    baseline = simulate(scenario, seed=seed)
    fork = simulate(
        scenario,
        intervention,
        seed=seed,
        technology_delays=technology_delays,
    )
    comparison_year = min(
        baseline["timeline"][-1]["year"], fork["timeline"][-1]["year"]
    )
    baseline_state = next(
        turn["state"] for turn in baseline["timeline"] if turn["year"] == comparison_year
    )
    fork_state = next(
        turn["state"] for turn in fork["timeline"] if turn["year"] == comparison_year
    )
    deltas = {
        metric: round(fork_state[metric] - baseline_state[metric], 2)
        for metric in METRICS
    }
    return {
        "schema_version": "fiction_forks_comparison.v1",
        "scenario_id": scenario["id"],
        "intervention_id": intervention["id"],
        "seed": seed,
        "comparison_year": comparison_year,
        "baseline": {
            "collapsed": baseline["collapsed"],
            "collapse_year": baseline["collapse_year"],
            "final_state": baseline["final_state"],
            "state_at_comparison_year": baseline_state,
        },
        "fork": {
            "collapsed": fork["collapsed"],
            "collapse_year": fork["collapse_year"],
            "activation_year": fork["activation_year"],
            "technology_schedule": fork["technology_schedule"],
            "technology_delays": fork["technology_delays"],
            "final_state": fork["final_state"],
            "state_at_comparison_year": fork_state,
        },
        "state_delta_at_comparison_year": deltas,
        "declared_costs": intervention["costs"],
        "declared_side_effects": intervention["side_effects"],
        "declared_failure_modes": intervention["failure_modes"],
    }
