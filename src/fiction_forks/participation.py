"""0.4 participation contracts shared by every transport and UI."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .engine import ContractError, ENGINE_VERSION, load_json


IDEA_DRAFT_SCHEMA = "fiction_forks_idea_draft.v1"
PROVISIONAL_REQUEST_SCHEMA = "fiction_forks_provisional_run_request.v1"
TEMPLATE_CONFIRMATION_SCHEMA = "fiction_forks_template_selection_confirmation.v1"
RUN_SUMMARY_SCHEMA = "fiction_forks_run_summary.v1"
CATALOG_SCHEMA = "fiction_forks_preview_template_catalog.v1"
IDEA_STATUS_SCHEMA = "fiction_forks_idea_status_projection.v1"
IDEA_LIFECYCLE = (
    "listed",
    "assigned",
    "implemented",
    "simulated",
    "reported_back",
)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{label} must be an object")
    return value


def _exact_fields(
    value: Mapping[str, Any], *, required: set[str], optional: set[str], label: str
) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required - optional)
    if missing:
        raise ContractError(f"{label} missing fields: {missing}")
    if unknown:
        raise ContractError(f"{label} has unknown fields: {unknown}")


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, label: str, *, maximum: int = 3) -> list[str]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be a list")
    if len(value) > maximum:
        raise ContractError(f"{label} must contain at most {maximum} items")
    result = [_string(item, f"{label} item") for item in value]
    if len(result) != len(set(result)):
        raise ContractError(f"{label} must not contain duplicates")
    return result


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{label} must be an integer")
    return value


def _utc_date(value: Any, label: str) -> str:
    text = _string(value, label)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ContractError(f"{label} must use YYYY-MM-DD")
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise ContractError(f"{label} must be a real UTC date") from exc
    return text


def _utc_datetime(value: Any, label: str) -> str:
    text = _string(value, label)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text):
        raise ContractError(f"{label} must use YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ContractError(f"{label} must be a real UTC datetime") from exc
    return text


def _canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_idea_draft(value: Any) -> dict[str, Any]:
    draft = _mapping(value, "IdeaDraft")
    required = {
        "schema_version",
        "entry_kind",
        "dialogue_mode",
        "idea_summary",
        "abstract_function",
        "target_doom",
        "unresolved_conditions",
        "side_effect_candidates",
        "user_confirmed",
    }
    optional = {"work_reference"}
    _exact_fields(draft, required=required, optional=optional, label="IdeaDraft")
    if draft["schema_version"] != IDEA_DRAFT_SCHEMA:
        raise ContractError("unsupported IdeaDraft schema_version")
    entry_kind = _string(draft["entry_kind"], "IdeaDraft.entry_kind")
    if entry_kind not in {"work", "problem"}:
        raise ContractError("IdeaDraft.entry_kind must be work or problem")
    dialogue_mode = _string(draft["dialogue_mode"], "IdeaDraft.dialogue_mode")
    if dialogue_mode not in {"guided", "local-codex"}:
        raise ContractError("IdeaDraft.dialogue_mode must be guided or local-codex")
    work_reference = draft.get("work_reference")
    if entry_kind == "work":
        work_reference = _string(work_reference, "IdeaDraft.work_reference")
    elif work_reference is not None:
        work_reference = _string(work_reference, "IdeaDraft.work_reference")
    if draft["user_confirmed"] is not True:
        raise ContractError("IdeaDraft must be confirmed by the participant")
    normalized = {
        "schema_version": IDEA_DRAFT_SCHEMA,
        "entry_kind": entry_kind,
        "dialogue_mode": dialogue_mode,
        "idea_summary": _string(draft["idea_summary"], "IdeaDraft.idea_summary"),
        "abstract_function": _string(
            draft["abstract_function"], "IdeaDraft.abstract_function"
        ),
        "target_doom": _string(draft["target_doom"], "IdeaDraft.target_doom"),
        "unresolved_conditions": _string_list(
            draft["unresolved_conditions"], "IdeaDraft.unresolved_conditions"
        ),
        "side_effect_candidates": _string_list(
            draft["side_effect_candidates"], "IdeaDraft.side_effect_candidates"
        ),
        "user_confirmed": True,
    }
    if work_reference is not None:
        normalized["work_reference"] = work_reference
    return normalized


def validate_template_catalog(value: Any, *, root: str | Path) -> dict[str, Any]:
    catalog = _mapping(value, "preview template catalog")
    _exact_fields(
        catalog,
        required={"schema_version", "catalog_version", "catalog_id", "templates"},
        optional=set(),
        label="preview template catalog",
    )
    if catalog["schema_version"] != CATALOG_SCHEMA:
        raise ContractError("unsupported preview template catalog schema_version")
    catalog_version = _integer(catalog["catalog_version"], "catalog_version")
    if catalog_version < 1:
        raise ContractError("catalog_version must be positive")
    catalog_id = _string(catalog["catalog_id"], "catalog_id")
    templates = catalog["templates"]
    if not isinstance(templates, list) or not templates:
        raise ContractError("templates must be a non-empty list")
    normalized_templates = []
    seen: set[str] = set()
    root_path = Path(root).resolve()
    for index, raw in enumerate(templates):
        template = _mapping(raw, f"template:{index}")
        required = {
            "template_id",
            "template_version",
            "status",
            "scenario_id",
            "intervention_id",
            "intervention_path",
            "intervention_sha256",
            "abstract_function",
            "target_doom",
            "side_effect_candidates",
            "allowed_seeds",
            "delay_profiles",
            "requires_user_confirmation",
            "idea_text_changes_engine_inputs",
        }
        _exact_fields(template, required=required, optional=set(), label=f"template:{index}")
        template_id = _string(template["template_id"], f"template:{index}.template_id")
        if template_id in seen:
            raise ContractError(f"duplicate template_id: {template_id}")
        seen.add(template_id)
        template_version = _integer(
            template["template_version"], f"template:{template_id}.template_version"
        )
        if template_version < 1:
            raise ContractError(f"template:{template_id} version must be positive")
        status = _string(template["status"], f"template:{template_id}.status")
        if status not in {"preview_allowed", "disabled"}:
            raise ContractError(f"template:{template_id} has unknown status")
        if template["requires_user_confirmation"] is not True:
            raise ContractError(f"template:{template_id} must require user confirmation")
        if template["idea_text_changes_engine_inputs"] is not False:
            raise ContractError(
                f"template:{template_id} must not let idea text change engine inputs"
            )
        scenario_id = _string(
            template["scenario_id"], f"template:{template_id}.scenario_id"
        )
        intervention_id = _string(
            template["intervention_id"], f"template:{template_id}.intervention_id"
        )
        abstract_function = _string(
            template["abstract_function"], f"template:{template_id}.abstract_function"
        )
        target_doom = _string(
            template["target_doom"], f"template:{template_id}.target_doom"
        )
        side_effect_candidates = _string_list(
            template["side_effect_candidates"],
            f"template:{template_id}.side_effect_candidates",
            maximum=3,
        )
        expected_digest = _string(
            template["intervention_sha256"],
            f"template:{template_id}.intervention_sha256",
        )
        if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
            raise ContractError(f"template:{template_id} has invalid intervention_sha256")
        seeds = template["allowed_seeds"]
        if not isinstance(seeds, list) or not seeds:
            raise ContractError(f"template:{template_id}.allowed_seeds must be non-empty")
        normalized_seeds = [_integer(seed, "allowed seed") for seed in seeds]
        if len(normalized_seeds) != len(set(normalized_seeds)):
            raise ContractError(f"template:{template_id} has duplicate seeds")
        delay_profiles = _string_list(
            template["delay_profiles"],
            f"template:{template_id}.delay_profiles",
            maximum=20,
        )
        if status == "preview_allowed" and not delay_profiles:
            raise ContractError(
                f"template:{template_id}.delay_profiles must be non-empty"
            )
        relative_path = Path(
            _string(template["intervention_path"], "intervention_path")
        )
        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or not re.fullmatch(
                r"interventions/[a-z0-9-]+\.json", relative_path.as_posix()
            )
        ):
            raise ContractError(f"template:{template_id} intervention_path is unsafe")
        intervention_path = (root_path / relative_path).resolve()
        if root_path not in intervention_path.parents:
            raise ContractError(f"template:{template_id} intervention_path escapes root")
        intervention = load_json(intervention_path)
        if intervention.get("id") != intervention_id:
            raise ContractError(f"template:{template_id} intervention_id mismatch")
        actual_digest = _canonical_digest(intervention)
        if actual_digest != expected_digest:
            raise ContractError(f"template:{template_id} intervention_sha256 mismatch")
        scenario_matches = []
        for scenario_path in root_path.glob("scenarios/**/scenario.json"):
            scenario = load_json(scenario_path)
            if scenario.get("id") == scenario_id:
                scenario_matches.append(scenario_path)
        if len(scenario_matches) != 1:
            raise ContractError(
                f"template:{template_id} scenario_id must resolve exactly once"
            )
        normalized_templates.append(
            {
                "template_id": template_id,
                "template_version": template_version,
                "status": status,
                "scenario_id": scenario_id,
                "intervention_id": intervention_id,
                "intervention_path": relative_path.as_posix(),
                "intervention_sha256": expected_digest,
                "abstract_function": abstract_function,
                "target_doom": target_doom,
                "side_effect_candidates": side_effect_candidates,
                "allowed_seeds": normalized_seeds,
                "delay_profiles": delay_profiles,
                "requires_user_confirmation": True,
                "idea_text_changes_engine_inputs": False,
            }
        )
    return {
        "schema_version": CATALOG_SCHEMA,
        "catalog_version": catalog_version,
        "catalog_id": catalog_id,
        "templates": normalized_templates,
    }


def load_template_catalog(path: str | Path, *, root: str | Path) -> dict[str, Any]:
    return validate_template_catalog(load_json(path), root=root)


def validate_idea_status_projection(value: Any) -> dict[str, Any]:
    projection = _mapping(value, "idea status projection")
    _exact_fields(
        projection,
        required={"schema_version", "observed_at", "repository", "ideas"},
        optional=set(),
        label="idea status projection",
    )
    if projection["schema_version"] != IDEA_STATUS_SCHEMA:
        raise ContractError("unsupported idea status projection schema_version")
    observed_at = _utc_date(projection["observed_at"], "observed_at")
    repository = _string(projection["repository"], "repository")
    ideas = projection["ideas"]
    if not isinstance(ideas, list):
        raise ContractError("ideas must be a list")
    normalized_ideas = []
    seen_numbers: set[int] = set()
    for index, raw in enumerate(ideas):
        idea = _mapping(raw, f"idea:{index}")
        required = {
            "issue_number",
            "issue_url",
            "source_updated_at",
            "lifecycle",
            "simulation_status",
            "missing_conditions",
            "next_action",
        }
        _exact_fields(idea, required=required, optional=set(), label=f"idea:{index}")
        number = _integer(idea["issue_number"], f"idea:{index}.issue_number")
        if number < 1 or number in seen_numbers:
            raise ContractError("issue_number must be positive and unique")
        seen_numbers.add(number)
        expected_url = f"https://github.com/{repository}/issues/{number}"
        if idea["issue_url"] != expected_url:
            raise ContractError(f"idea:{number} issue_url mismatch")
        updated_at = _utc_datetime(
            idea["source_updated_at"], f"idea:{number}.source_updated_at"
        )
        lifecycle = _mapping(idea["lifecycle"], f"idea:{number}.lifecycle")
        _exact_fields(
            lifecycle,
            required=set(IDEA_LIFECYCLE),
            optional=set(),
            label=f"idea:{number}.lifecycle",
        )
        values = []
        for field in IDEA_LIFECYCLE:
            state = lifecycle[field]
            if not isinstance(state, bool):
                raise ContractError(f"idea:{number}.lifecycle.{field} must be boolean")
            values.append(state)
        if not values[0]:
            raise ContractError(f"idea:{number} must be listed")
        if any(values[position] and not values[position - 1] for position in range(1, len(values))):
            raise ContractError(f"idea:{number} lifecycle cannot skip states")
        simulation_status = _string(
            idea["simulation_status"], f"idea:{number}.simulation_status"
        )
        if simulation_status not in {"not-ready", "candidate", "official"}:
            raise ContractError(f"idea:{number} has unknown simulation_status")
        missing = _string_list(
            idea["missing_conditions"],
            f"idea:{number}.missing_conditions",
            maximum=10,
        )
        if simulation_status == "not-ready" and not missing:
            raise ContractError(f"idea:{number} not-ready status needs missing_conditions")
        if simulation_status != "not-ready" and missing:
            raise ContractError(f"idea:{number} ready status cannot keep missing_conditions")
        if simulation_status == "not-ready" and lifecycle["simulated"]:
            raise ContractError(f"idea:{number} simulation_status conflicts with lifecycle")
        if simulation_status == "candidate" and (
            not lifecycle["simulated"] or lifecycle["reported_back"]
        ):
            raise ContractError(f"idea:{number} simulation_status conflicts with lifecycle")
        if simulation_status == "official":
            raise ContractError(
                f"idea:{number} simulation_status official requires the verified main-run promotion boundary"
            )
        normalized_idea = {
            "issue_number": number,
            "issue_url": expected_url,
            "source_updated_at": updated_at,
            "lifecycle": dict(lifecycle),
            "simulation_status": simulation_status,
            "missing_conditions": missing,
            "next_action": _string(
                idea["next_action"], f"idea:{number}.next_action"
            ),
        }
        normalized_ideas.append(normalized_idea)
    return {
        "schema_version": IDEA_STATUS_SCHEMA,
        "observed_at": observed_at,
        "repository": repository,
        "ideas": normalized_ideas,
    }


def _validate_template_confirmation(
    value: Any, *, selected: Mapping[str, Any]
) -> dict[str, Any]:
    confirmation = _mapping(value, "template selection confirmation")
    required = {
        "schema_version",
        "template_id",
        "template_version",
        "intervention_sha256",
        "user_confirmed",
    }
    _exact_fields(
        confirmation,
        required=required,
        optional=set(),
        label="template selection confirmation",
    )
    if confirmation["schema_version"] != TEMPLATE_CONFIRMATION_SCHEMA:
        raise ContractError("unsupported template selection confirmation schema_version")
    if confirmation["user_confirmed"] is not True:
        raise ContractError("template selection confirmation must be confirmed")
    expected = {
        "template_id": selected["template_id"],
        "template_version": selected["template_version"],
        "intervention_sha256": selected["intervention_sha256"],
    }
    observed = {
        "template_id": _string(confirmation["template_id"], "template_id"),
        "template_version": _integer(
            confirmation["template_version"], "template_version"
        ),
        "intervention_sha256": _string(
            confirmation["intervention_sha256"], "intervention_sha256"
        ),
    }
    for field, expected_value in expected.items():
        if observed[field] != expected_value:
            raise ContractError(f"template selection confirmation {field} mismatch")
    return {
        "schema_version": TEMPLATE_CONFIRMATION_SCHEMA,
        "template_id": observed["template_id"],
        "template_version": observed["template_version"],
        "intervention_sha256": observed["intervention_sha256"],
        "user_confirmed": True,
    }


def validate_provisional_request(
    value: Any, catalog_value: Any, *, root: str | Path
) -> dict[str, Any]:
    request = _mapping(value, "ProvisionalRunRequest")
    required = {
        "schema_version",
        "scenario_id",
        "template_id",
        "template_version",
        "catalog_id",
        "catalog_version",
        "intervention_id",
        "intervention_sha256",
        "seed",
        "delay_profile",
        "user_confirmed",
    }
    _exact_fields(request, required=required, optional=set(), label="ProvisionalRunRequest")
    if request["schema_version"] != PROVISIONAL_REQUEST_SCHEMA:
        raise ContractError("unsupported ProvisionalRunRequest schema_version")
    if request["user_confirmed"] is not True:
        raise ContractError("ProvisionalRunRequest must be confirmed")
    catalog = validate_template_catalog(catalog_value, root=root)
    template_id = _string(request["template_id"], "template_id")
    selected = next(
        (item for item in catalog["templates"] if item["template_id"] == template_id),
        None,
    )
    if selected is None:
        raise ContractError("template_id is not registered")
    if selected["status"] != "preview_allowed":
        raise ContractError("template is not preview_allowed")
    normalized = {
        "schema_version": PROVISIONAL_REQUEST_SCHEMA,
        "scenario_id": _string(request["scenario_id"], "scenario_id"),
        "template_id": template_id,
        "template_version": _integer(request["template_version"], "template_version"),
        "catalog_id": _string(request["catalog_id"], "catalog_id"),
        "catalog_version": _integer(request["catalog_version"], "catalog_version"),
        "intervention_id": _string(request["intervention_id"], "intervention_id"),
        "intervention_sha256": _string(
            request["intervention_sha256"], "intervention_sha256"
        ),
        "seed": _integer(request["seed"], "seed"),
        "delay_profile": _string(request["delay_profile"], "delay_profile"),
        "user_confirmed": True,
    }
    expected = {
        "scenario_id": selected["scenario_id"],
        "template_version": selected["template_version"],
        "catalog_id": catalog["catalog_id"],
        "catalog_version": catalog["catalog_version"],
        "intervention_id": selected["intervention_id"],
        "intervention_sha256": selected["intervention_sha256"],
    }
    for field, expected_value in expected.items():
        if normalized[field] != expected_value:
            raise ContractError(f"ProvisionalRunRequest {field} mismatch")
    if normalized["seed"] not in selected["allowed_seeds"]:
        raise ContractError("ProvisionalRunRequest seed is not allowed")
    if normalized["delay_profile"] not in selected["delay_profiles"]:
        raise ContractError("ProvisionalRunRequest delay_profile is not allowed")
    return normalized


def prepare_provisional_request(
    draft_value: Any,
    catalog_value: Any,
    template_confirmation_value: Any,
    *,
    root: str | Path,
    template_id: str,
    seed: int,
    delay_profile: str,
) -> dict[str, Any]:
    draft = validate_idea_draft(draft_value)
    catalog = validate_template_catalog(catalog_value, root=root)
    selected = next(
        (item for item in catalog["templates"] if item["template_id"] == template_id),
        None,
    )
    if selected is None:
        return {
            "schema_version": RUN_SUMMARY_SCHEMA,
            "status": "not-simulatable",
            "classification": "provisional",
            "missing_conditions": ["既知のtemplateを選択してください"],
        }
    _validate_template_confirmation(template_confirmation_value, selected=selected)
    missing = []
    if selected["status"] != "preview_allowed":
        missing.append("選択したtemplateはpreviewを許可していません")
    if draft["abstract_function"] != selected["abstract_function"]:
        missing.append("確認済みの抽象機能を既知templateへ完全に対応させてください")
    if draft["target_doom"] != selected["target_doom"]:
        missing.append("対象doomを既知templateへ完全に対応させてください")
    if draft["side_effect_candidates"] != selected["side_effect_candidates"]:
        missing.append("副作用候補を既知templateへ完全に対応させてください")
    if draft["unresolved_conditions"]:
        missing.append("未解決条件をすべて解消してください")
    if seed not in selected["allowed_seeds"]:
        missing.append("catalogで許可されたseedを選択してください")
    if delay_profile not in selected["delay_profiles"]:
        missing.append("catalogで許可されたdelay profileを選択してください")
    if missing:
        return {
            "schema_version": RUN_SUMMARY_SCHEMA,
            "status": "not-simulatable",
            "classification": "provisional",
            "missing_conditions": missing,
        }
    request = {
        "schema_version": PROVISIONAL_REQUEST_SCHEMA,
        "scenario_id": selected["scenario_id"],
        "template_id": selected["template_id"],
        "template_version": selected["template_version"],
        "catalog_id": catalog["catalog_id"],
        "catalog_version": catalog["catalog_version"],
        "intervention_id": selected["intervention_id"],
        "intervention_sha256": selected["intervention_sha256"],
        "seed": seed,
        "delay_profile": delay_profile,
        "user_confirmed": True,
    }
    request = validate_provisional_request(request, catalog, root=root)
    return {
        "schema_version": RUN_SUMMARY_SCHEMA,
        "status": "ready",
        "classification": "provisional",
        "engine_version": ENGINE_VERSION,
        "request": request,
        "request_digest": _canonical_digest(request),
        "unresolved_conditions": draft["unresolved_conditions"],
        "notice": "既存templateによる暫定比較です。公式結果ではありません。",
    }
