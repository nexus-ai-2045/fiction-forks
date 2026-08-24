"""透明で再現可能な状態遷移エンジン。"""

from __future__ import annotations

import json
import math
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
ENGINE_VERSION = "0.3.0"


class ContractError(ValueError):
    """scenarioまたはinterventionが契約を満たさない。"""


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ContractError(f"JSON root must be an object: {path}")
    return value


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{label} must be an object")
    return value


def _require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{label} must be an integer")
    return value


def _require_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{label} must be a finite number")
    try:
        number = float(value)
    except OverflowError as error:
        raise ContractError(f"{label} must be a finite number") from error
    if not math.isfinite(number):
        raise ContractError(f"{label} must be a finite number")
    return number


def _require_string_list(
    value: Any, label: str, *, non_empty: bool = True
) -> list[str]:
    if not isinstance(value, list) or (non_empty and not value):
        requirement = "a non-empty list" if non_empty else "a list"
        raise ContractError(f"{label} must be {requirement}")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ContractError(f"{label} must contain non-empty strings")
    return value


def _validate_effects(effects: Any, label: str) -> None:
    effects = _require_mapping(effects, label)
    unknown = sorted(set(effects) - set(METRICS))
    if unknown:
        raise ContractError(f"{label} has unknown metrics: {unknown}")
    for metric, delta in effects.items():
        try:
            _require_number(delta, f"{label}.{metric}")
        except ContractError as error:
            raise ContractError(
                f"{label}.{metric} must be numeric and finite"
            ) from error


def validate_scenario(scenario: Mapping[str, Any]) -> None:
    scenario = _require_mapping(scenario, "scenario")
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
    for field in ("schema_version", "id", "title", "assumption_notice"):
        if not isinstance(scenario[field], str) or not scenario[field].strip():
            raise ContractError(f"scenario.{field} must be a non-empty string")
    start_year = _require_int(scenario["start_year"], "start_year")
    end_year = _require_int(scenario["end_year"], "end_year")
    if start_year > end_year:
        raise ContractError("start_year must be <= end_year")
    if (
        not isinstance(scenario["design_question"], str)
        or not scenario["design_question"].strip()
    ):
        raise ContractError("design_question must be a non-empty string")
    if (
        not isinstance(scenario["causal_chain"], list)
        or len(scenario["causal_chain"]) < 2
    ):
        raise ContractError("causal_chain must contain at least two steps")
    if not all(
        isinstance(step, str) and step.strip() for step in scenario["causal_chain"]
    ):
        raise ContractError("causal_chain steps must be non-empty strings")
    _require_string_list(scenario["evidence_refs"], "evidence_refs")
    initial_state = _require_mapping(scenario["initial_state"], "initial_state")
    if set(initial_state) != set(METRICS):
        raise ContractError("initial_state must define exactly the five metrics")
    _validate_effects(initial_state, "initial_state")
    for metric, value in initial_state.items():
        if not 0 <= _require_number(value, f"initial_state.{metric}") <= 100:
            raise ContractError(f"initial_state.{metric} must be between 0 and 100")
    _validate_effects(scenario["baseline_annual_effects"], "baseline_annual_effects")
    capabilities = _require_mapping(
        scenario["capability_availability"], "capability_availability"
    )
    for capability, year in capabilities.items():
        if not isinstance(capability, str) or not capability.strip():
            raise ContractError(
                "capability_availability keys must be non-empty strings"
            )
        _require_int(year, f"capability_availability.{capability}")

    shocks = scenario["shocks"]
    if not isinstance(shocks, list):
        raise ContractError("shocks must be a list")
    for index, raw_shock in enumerate(shocks):
        shock = _require_mapping(raw_shock, f"shock:{index}")
        shock_id = shock.get("id", "unknown")
        label = f"shock:{shock_id}"
        if not isinstance(shock_id, str) or not shock_id.strip():
            raise ContractError(f"shock:{index}.id must be a non-empty string")
        if not isinstance(shock.get("label"), str) or not shock["label"].strip():
            raise ContractError(f"{label}.label must be a non-empty string")
        if "year" not in shock:
            raise ContractError(f"{label}.year is required")
        _require_int(shock["year"], f"{label}.year")
        if "effects" not in shock:
            raise ContractError(f"{label}.effects is required")
        _validate_effects(shock["effects"], f"{label}.effects")
        variance = _require_int(shock.get("variance", 0), f"{label}.variance")
        if variance < 0:
            raise ContractError("shock variance must be >= 0")
    collapse = _require_mapping(scenario["collapse"], "collapse")
    collapse_metrics = _require_string_list(collapse.get("metrics"), "collapse.metrics")
    unknown = sorted(set(collapse_metrics) - set(METRICS))
    if unknown:
        raise ContractError(f"collapse has unknown metrics: {unknown}")
    threshold = _require_number(collapse.get("threshold"), "collapse.threshold")
    if not 0 <= threshold <= 100:
        raise ContractError("collapse threshold must be between 0 and 100")
    minimum_breaches = _require_int(
        collapse.get("minimum_breaches"), "collapse.minimum_breaches"
    )
    if not 1 <= minimum_breaches <= len(collapse_metrics):
        raise ContractError("minimum_breaches must fit collapse.metrics")
    consecutive_turns = _require_int(
        collapse.get("consecutive_turns"), "collapse.consecutive_turns"
    )
    if consecutive_turns < 1:
        raise ContractError("consecutive_turns must be >= 1")


def validate_intervention(
    intervention: Mapping[str, Any], scenario: Mapping[str, Any]
) -> None:
    intervention = _require_mapping(intervention, "intervention")
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
    for field in ("schema_version", "id", "fiction_reference", "extracted_function"):
        if not isinstance(intervention[field], str) or not intervention[field].strip():
            raise ContractError(f"intervention.{field} must be a non-empty string")
    allowed_modes = {"literal", "functional_equivalent", "institutional_equivalent"}
    if intervention["realization_mode"] not in allowed_modes:
        raise ContractError("unknown realization_mode")
    prerequisites = _require_string_list(
        intervention["prerequisites"], "prerequisites", non_empty=False
    )
    capabilities = _require_mapping(
        scenario["capability_availability"], "capability_availability"
    )
    unavailable = sorted(set(prerequisites) - set(capabilities))
    if unavailable:
        raise ContractError(f"unknown prerequisites: {unavailable}")
    _validate_effects(intervention["activation_effects"], "activation_effects")
    _validate_effects(intervention["annual_effects"], "annual_effects")
    for field in ("costs", "side_effects", "failure_modes"):
        _require_string_list(intervention[field], field)

    tree = _require_mapping(intervention["technology_tree"], "technology_tree")
    nodes = tree.get("nodes")
    activation_requires = tree.get("activation_requires")
    if not isinstance(nodes, list) or not nodes:
        raise ContractError("technology_tree.nodes must be a non-empty list")
    activation_requires = _require_string_list(
        activation_requires, "technology_tree.activation_requires"
    )

    node_ids = [node.get("id") for node in nodes if isinstance(node, Mapping)]
    if len(node_ids) != len(nodes) or any(
        not isinstance(value, str) or not value.strip() for value in node_ids
    ):
        raise ContractError("every technology_tree node must have an id")
    if len(set(node_ids)) != len(node_ids):
        raise ContractError("technology_tree node ids must be unique")

    node_id_set = set(node_ids)
    external_capabilities = set(capabilities)
    referenced_external: set[str] = set()
    allowed_kinds = {"technology", "institution", "operations"}
    for node in nodes:
        if node.get("kind") not in allowed_kinds:
            raise ContractError(f"technology_tree:{node['id']} has unknown kind")
        if not isinstance(node.get("label"), str) or not node["label"].strip():
            raise ContractError(f"technology_tree:{node['id']} must have a label")
        if (
            not isinstance(node.get("completion_evidence"), str)
            or not node["completion_evidence"].strip()
        ):
            raise ContractError(
                f"technology_tree:{node['id']} must have completion_evidence"
            )
        lead_time = node.get("lead_time_years")
        if (
            isinstance(lead_time, bool)
            or not isinstance(lead_time, int)
            or lead_time < 0
        ):
            raise ContractError(
                f"technology_tree:{node['id']}.lead_time_years must be a non-negative integer"
            )
        dependencies = node.get("depends_on")
        if not isinstance(dependencies, list):
            raise ContractError(
                f"technology_tree:{node['id']}.depends_on must be a list"
            )
        if not all(isinstance(dependency, str) for dependency in dependencies):
            raise ContractError(
                f"technology_tree:{node['id']}.depends_on must contain strings"
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
    if set(prerequisites) != referenced_external:
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


def _shock_effects(shock: Mapping[str, Any], rng: random.Random) -> dict[str, float]:
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
        if isinstance(delay, bool) or not isinstance(delay, int) or delay < 0:
            raise ContractError(
                f"technology delay for {node_id} must be a non-negative integer"
            )
    external = {
        name: int(year) for name, year in scenario["capability_availability"].items()
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

        if (
            intervention is not None
            and activation_year is not None
            and year >= activation_year
        ):
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
        "engine_version": ENGINE_VERSION,
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
        turn["state"]
        for turn in baseline["timeline"]
        if turn["year"] == comparison_year
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
        "engine_version": ENGINE_VERSION,
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
