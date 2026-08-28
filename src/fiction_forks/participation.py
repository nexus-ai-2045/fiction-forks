"""0.4 participation contracts shared by every transport and UI."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .engine import ContractError, ENGINE_VERSION, load_json


IDEA_DRAFT_SCHEMA = "fiction_forks_idea_draft.v1"
PROVISIONAL_REQUEST_SCHEMA = "fiction_forks_provisional_run_request.v1"
RUN_SUMMARY_SCHEMA = "fiction_forks_run_summary.v1"
CATALOG_SCHEMA = "fiction_forks_preview_template_catalog.v1"


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
        _string(template["scenario_id"], f"template:{template_id}.scenario_id")
        _string(template["intervention_id"], f"template:{template_id}.intervention_id")
        _string(template["abstract_function"], f"template:{template_id}.abstract_function")
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
        _string_list(
            template["delay_profiles"],
            f"template:{template_id}.delay_profiles",
            maximum=20,
        )
        relative_path = Path(
            _string(template["intervention_path"], "intervention_path")
        )
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ContractError(f"template:{template_id} intervention_path is unsafe")
        intervention_path = (root_path / relative_path).resolve()
        if root_path not in intervention_path.parents:
            raise ContractError(f"template:{template_id} intervention_path escapes root")
        intervention = load_json(intervention_path)
        if intervention.get("id") != template["intervention_id"]:
            raise ContractError(f"template:{template_id} intervention_id mismatch")
        actual_digest = _canonical_digest(intervention)
        if actual_digest != expected_digest:
            raise ContractError(f"template:{template_id} intervention_sha256 mismatch")
        normalized_templates.append(dict(template))
    return {
        "schema_version": CATALOG_SCHEMA,
        "catalog_version": catalog_version,
        "catalog_id": catalog_id,
        "templates": normalized_templates,
    }


def load_template_catalog(path: str | Path, *, root: str | Path) -> dict[str, Any]:
    return validate_template_catalog(load_json(path), root=root)


def prepare_provisional_request(
    draft_value: Any,
    catalog_value: Any,
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
    missing = []
    if selected["status"] != "preview_allowed":
        missing.append("選択したtemplateはpreviewを許可していません")
    if draft["abstract_function"] != selected["abstract_function"]:
        missing.append("確認済みの抽象機能を既知templateへ完全に対応させてください")
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
        "catalog_version": catalog["catalog_version"],
        "seed": seed,
        "delay_profile": delay_profile,
        "user_confirmed": True,
    }
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
