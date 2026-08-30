"""Aggregate observable social-run metrics without claiming emergence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

NOT_MEASURED = "not_measured"
SCHEMA_VERSION = "fiction_forks_emergence_report.v1"
DISCLAIMER = (
    "この報告は創発性の断定ではない。"
    "観測できた行動の多様性、相互作用、契約棄却、技術遅延、発動年、破滅判定の分散だけを集計する。"
    "LLM生成そのものの決定論性は主張しない。"
    "同じ入力run_idでも provider / model / runtime_revision / result SHA / event SHA が違えば別実行である。"
)
PROSE_KEYS = {
    "text",
    "conditions",
    "private_context",
    "assumption_notice",
    "objective",
    "event",
    "summary",
    "label",
    "completion_evidence",
    "implementation_hypothesis",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _as_mapping(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, Mapping) else None


def measured(value: Any) -> bool:
    return value not in (None, NOT_MEASURED)


def _ratio(numerator: Any, denominator: Any) -> Any:
    if not measured(numerator) or not measured(denominator):
        return NOT_MEASURED
    if not isinstance(numerator, (int, float)) or not isinstance(denominator, (int, float)):
        return NOT_MEASURED
    if denominator == 0:
        return NOT_MEASURED
    return round(float(numerator) / float(denominator), 4)


def _unique_count(values: Any) -> Any:
    if values == NOT_MEASURED or values is None:
        return NOT_MEASURED
    if not isinstance(values, list):
        return NOT_MEASURED
    return len({item for item in values if item not in (None, "", "abstain")})


def relative_source_path(path: Path | None, repo_root: Path | None) -> Any:
    if path is None:
        return NOT_MEASURED
    resolved = path.resolve()
    if repo_root is not None:
        try:
            return resolved.relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            return resolved.name
    return path.name


def execution_identity(
    document: Mapping[str, Any],
    *,
    path: Path | None = None,
    file_sha256: str | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    provider = document.get("provider")
    if isinstance(provider, Mapping):
        provider_name = provider.get("name", NOT_MEASURED)
        model = provider.get("model", NOT_MEASURED)
    else:
        provider_name = document.get("provider", NOT_MEASURED)
        model = document.get("model", NOT_MEASURED)
    if model is None:
        model = NOT_MEASURED
    identity = {
        "run_id": document.get("run_id", NOT_MEASURED),
        "provider": provider_name if provider_name not in (None, "") else NOT_MEASURED,
        "model": model if model not in (None, "") else NOT_MEASURED,
        "runtime_revision": document.get("runtime_revision", NOT_MEASURED),
        "seed": document.get("seed", NOT_MEASURED),
        "result_sha256": document.get("result_sha256", file_sha256 or NOT_MEASURED),
        "event_stream_sha256": document.get(
            "event_stream_sha256", document.get("final_event_hash", NOT_MEASURED)
        ),
        "source_path": relative_source_path(path, repo_root),
    }
    if identity["result_sha256"] in (None, ""):
        identity["result_sha256"] = file_sha256 or NOT_MEASURED
    if identity["event_stream_sha256"] in (None, ""):
        identity["event_stream_sha256"] = NOT_MEASURED
    return identity


def identity_key(identity: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        identity.get("run_id", NOT_MEASURED),
        identity.get("provider", NOT_MEASURED),
        identity.get("model", NOT_MEASURED),
        identity.get("runtime_revision", NOT_MEASURED),
        identity.get("result_sha256", NOT_MEASURED),
        identity.get("event_stream_sha256", NOT_MEASURED),
    )


def source_class(document: Mapping[str, Any], identity: Mapping[str, Any]) -> str:
    schema = document.get("schema_version")
    provider = identity.get("provider")
    if schema == "fiction_forks_live_run_summary.v1":
        return "live"
    if schema == "fiction_forks_comparison.v1":
        return "deterministic_comparison"
    if provider == "fixture":
        return "fixture"
    if provider == "replay":
        return "replay"
    if provider in {"ollama", "openai", "vertex"}:
        return "live"
    return "unknown"


def _stance_counts(actions: list[Mapping[str, Any]] | None) -> dict[str, Any]:
    empty = {
        "support": NOT_MEASURED,
        "condition": NOT_MEASURED,
        "oppose": NOT_MEASURED,
        "abstain": NOT_MEASURED,
    }
    if actions is None:
        return empty
    observed: list[str] = []
    for item in actions:
        payload = item.get("action", item) if isinstance(item, Mapping) else None
        if not isinstance(payload, Mapping) or "stance" not in payload:
            continue
        observed.append(str(payload["stance"]))
    if not observed:
        return empty
    counts = Counter(observed)
    return {
        "support": counts.get("support", 0),
        "condition": counts.get("condition", 0),
        "oppose": counts.get("oppose", 0),
        "abstain": counts.get("abstain", 0),
    }


def _action_ids(document: Mapping[str, Any]) -> Any:
    if "turns" in document and isinstance(document["turns"], list):
        return [
            item.get("action_id", NOT_MEASURED)
            for item in document["turns"]
            if isinstance(item, Mapping)
        ]
    actions = document.get("actions")
    if not isinstance(actions, list):
        return NOT_MEASURED
    ids = []
    for item in actions:
        if not isinstance(item, Mapping):
            continue
        action = item.get("action", item)
        if isinstance(action, Mapping):
            ids.append(action.get("action_id", NOT_MEASURED))
    return ids


def _valid_flags(document: Mapping[str, Any]) -> Any:
    if "turns" in document and isinstance(document["turns"], list):
        flags = []
        for item in document["turns"]:
            if isinstance(item, Mapping) and "valid" in item:
                flags.append(bool(item["valid"]))
        return flags or NOT_MEASURED
    actions = document.get("actions")
    if not isinstance(actions, list):
        return NOT_MEASURED
    flags = []
    for item in actions:
        if isinstance(item, Mapping) and "valid" in item:
            flags.append(bool(item["valid"]))
    return flags or NOT_MEASURED


def _world_fields(document: Mapping[str, Any]) -> dict[str, Any]:
    world = document.get("world_comparison")
    fork = None
    if isinstance(world, Mapping):
        fork = world.get("fork")
    elif document.get("schema_version") == "fiction_forks_comparison.v1":
        fork = document.get("fork")
    if not isinstance(fork, Mapping):
        fork = {}
    return {
        "activation_year": fork.get("activation_year", document.get("activation_year", NOT_MEASURED)),
        "collapse_year": fork.get("collapse_year", document.get("collapse_year", NOT_MEASURED)),
        "collapsed": fork.get("collapsed", document.get("collapsed", NOT_MEASURED)),
        "missing_actions_by_node": document.get("missing_actions_by_node", NOT_MEASURED),
        "technology_delays": (
            document.get("technology_delays")
            if isinstance(document.get("technology_delays"), Mapping)
            else fork.get("technology_delays", NOT_MEASURED)
        ),
    }


def _interaction_density(edge_count: Any, role_count: Any, turn_count: Any) -> Any:
    if not all(measured(value) for value in (edge_count, role_count, turn_count)):
        return NOT_MEASURED
    if not all(isinstance(value, int) for value in (edge_count, role_count, turn_count)):
        return NOT_MEASURED
    possible = role_count * max(role_count - 1, 0) * turn_count
    if possible == 0:
        return NOT_MEASURED
    return round(edge_count / possible, 4)


def summarize_document(
    document: Mapping[str, Any],
    *,
    path: Path | None = None,
    file_sha256: str | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    identity = execution_identity(
        document, path=path, file_sha256=file_sha256, repo_root=repo_root
    )
    metrics = document.get("metrics") if isinstance(document.get("metrics"), Mapping) else {}
    action_ids = _action_ids(document)
    valid_flags = _valid_flags(document)
    event_count = document.get("event_count", metrics.get("action_count", NOT_MEASURED))
    if event_count == NOT_MEASURED and isinstance(action_ids, list):
        event_count = len(action_ids)
    valid_count = document.get("valid_action_count", metrics.get("valid_action_count", NOT_MEASURED))
    invalid_count = document.get(
        "invalid_action_count", metrics.get("invalid_action_count", NOT_MEASURED)
    )
    if valid_count == NOT_MEASURED and isinstance(valid_flags, list):
        valid_count = sum(1 for flag in valid_flags if flag)
        invalid_count = len(valid_flags) - valid_count
    edge_count = document.get(
        "interaction_edge_count", metrics.get("interaction_edge_count", NOT_MEASURED)
    )
    if edge_count == NOT_MEASURED and isinstance(document.get("interaction_edges"), list):
        edge_count = len(document["interaction_edges"])
    capability_coverage = metrics.get("capability_coverage", NOT_MEASURED)
    role_count = len(document["roles"]) if isinstance(document.get("roles"), list) else NOT_MEASURED
    turn_count = document.get("turn_count", NOT_MEASURED)
    if turn_count == NOT_MEASURED and isinstance(document.get("turns"), list):
        turn_ids = {
            item.get("turn")
            for item in document["turns"]
            if isinstance(item, Mapping) and "turn" in item
        }
        turn_count = len(turn_ids) if turn_ids else NOT_MEASURED
    world = _world_fields(document)
    actions = document.get("actions") if isinstance(document.get("actions"), list) else None
    if actions is None and isinstance(document.get("turns"), list):
        actions = document["turns"]
    return {
        "identity": identity,
        "source_class": source_class(document, identity),
        "schema_version": document.get("schema_version", NOT_MEASURED),
        "action_ids": action_ids,
        "action_diversity": _unique_count(action_ids),
        "capability_coverage": capability_coverage,
        "interaction_edge_count": edge_count,
        "interaction_density": _interaction_density(edge_count, role_count, turn_count),
        "stances": _stance_counts(actions),
        "event_count": event_count,
        "valid_action_count": valid_count,
        "invalid_action_count": invalid_count,
        "fail_closed_rate": _ratio(invalid_count, event_count),
        "missing_actions_by_node": world["missing_actions_by_node"],
        "technology_delays": world["technology_delays"],
        "activation_year": world["activation_year"] if world["activation_year"] is not None else NOT_MEASURED,
        "collapse_year": world["collapse_year"] if world["collapse_year"] is not None else NOT_MEASURED,
        "collapsed": world["collapsed"] if world["collapsed"] is not None else NOT_MEASURED,
        "replay_verified": document.get("replay_verified", NOT_MEASURED),
        "bundle_contract_verified": document.get("bundle_contract_verified", NOT_MEASURED),
    }


def _mean(values: list[Any]) -> Any:
    numbers = [value for value in values if isinstance(value, (int, float))]
    if not numbers:
        return NOT_MEASURED
    return round(sum(numbers) / len(numbers), 4)


def _distribution(values: list[Any]) -> dict[str, Any]:
    measured_values = [value for value in values if measured(value)]
    unknown = len(values) - len(measured_values)
    counts = Counter(str(value) for value in measured_values)
    return {
        "measured": len(measured_values),
        "not_measured": unknown,
        "counts": dict(counts),
    }


def _collapse_rate(values: list[Any]) -> Any:
    booleans = [value for value in values if isinstance(value, bool)]
    if not booleans:
        return NOT_MEASURED
    return round(sum(1 for value in booleans if value) / len(booleans), 4)


def aggregate(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "action_diversity": {
            "mean": _mean([row["action_diversity"] for row in rows]),
            "distribution": _distribution([row["action_diversity"] for row in rows]),
        },
        "capability_coverage": {
            "mean": _mean([row["capability_coverage"] for row in rows]),
            "not_measured": sum(
                1 for row in rows if not measured(row["capability_coverage"])
            ),
        },
        "interaction_edge_count": {
            "mean": _mean([row["interaction_edge_count"] for row in rows]),
            "distribution": _distribution([row["interaction_edge_count"] for row in rows]),
        },
        "interaction_density": {
            "mean": _mean([row["interaction_density"] for row in rows]),
            "not_measured": sum(
                1 for row in rows if not measured(row["interaction_density"])
            ),
        },
        "stances": {
            stance: {
                "mean": _mean([row["stances"][stance] for row in rows]),
                "not_measured": sum(
                    1 for row in rows if not measured(row["stances"][stance])
                ),
            }
            for stance in ("support", "condition", "oppose", "abstain")
        },
        "fail_closed_rate": {
            "mean": _mean([row["fail_closed_rate"] for row in rows]),
            "not_measured": sum(
                1 for row in rows if not measured(row["fail_closed_rate"])
            ),
        },
        "activation_year": _distribution([row["activation_year"] for row in rows]),
        "collapse_rate": _collapse_rate([row["collapsed"] for row in rows]),
        "collapsed": _distribution([row["collapsed"] for row in rows]),
        "provider_model": _distribution(
            [
                f"{row['identity']['provider']}/{row['identity']['model']}"
                for row in rows
            ]
        ),
    }


def contains_prose(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in PROSE_KEYS:
                return True
            if contains_prose(nested):
                return True
        return False
    if isinstance(value, list):
        return any(contains_prose(item) for item in value)
    return False


def load_recognized(path: Path) -> dict[str, Any] | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(document, Mapping):
        return None
    schema = document.get("schema_version")
    if schema in {
        "fiction_forks_social_result.v1",
        "fiction_forks_live_run_summary.v1",
        "fiction_forks_comparison.v1",
    }:
        return dict(document)
    return None


def collect_inputs(
    paths: list[Path], *, repo_root: Path | None = None
) -> list[tuple[Path, dict[str, Any], str]]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.json")))
        elif path.is_file():
            files.append(path)
    collected: list[tuple[Path, dict[str, Any], str]] = []
    seen: set[tuple[Any, ...]] = set()
    for file_path in files:
        document = load_recognized(file_path)
        if document is None:
            continue
        digest = sha256_file(file_path)
        row = summarize_document(
            document, path=file_path, file_sha256=digest, repo_root=repo_root
        )
        key = identity_key(row["identity"])
        if key in seen:
            continue
        seen.add(key)
        collected.append((file_path, row, digest))
    return collected


def build_report(paths: list[Path], *, repo_root: Path | None = None) -> dict[str, Any]:
    collected = collect_inputs(paths, repo_root=repo_root)
    rows = [row for _path, row, _digest in collected]
    by_class: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_class.setdefault(row["source_class"], []).append(row)
    report = {
        "schema_version": SCHEMA_VERSION,
        "disclaimer": DISCLAIMER,
        "n_executions": len(rows),
        "executions": rows,
        "aggregates": {
            "all": aggregate(rows),
            "by_source_class": {
                name: aggregate(items) for name, items in sorted(by_class.items())
            },
        },
    }
    if contains_prose(report):
        raise ValueError("emergence report must not include raw model or fixture prose")
    return report


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# 行動多様性・相互作用・結果分散の観測報告",
        "",
        report["disclaimer"],
        "",
        f"- 実行数: {report['n_executions']}",
        "",
        "## 実行ごとの識別",
        "",
        "| source_class | run_id | provider | model | seed | activation_year | collapsed | result SHA |",
        "|---|---|---|---|---:|---:|---|---|",
    ]
    for row in report["executions"]:
        identity = row["identity"]
        lines.append(
            "| {source} | `{run_id}` | {provider} | {model} | {seed} | {activation} | {collapsed} | `{sha}` |".format(
                source=row["source_class"],
                run_id=identity["run_id"],
                provider=identity["provider"],
                model=identity["model"],
                seed=identity["seed"],
                activation=row["activation_year"],
                collapsed=row["collapsed"],
                sha=str(identity["result_sha256"])[:12],
            )
        )
    lines.extend(["", "## 分離集計", ""])
    for name, aggregate_row in report["aggregates"]["by_source_class"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                f"- n: {aggregate_row['n']}",
                f"- action diversity 平均: {aggregate_row['action_diversity']['mean']}",
                f"- capability coverage 平均: {aggregate_row['capability_coverage']['mean']}",
                f"- interaction edge 平均: {aggregate_row['interaction_edge_count']['mean']}",
                f"- fail-closed rate 平均: {aggregate_row['fail_closed_rate']['mean']}",
                f"- collapse rate: {aggregate_row['collapse_rate']}",
                f"- activation year: {aggregate_row['activation_year']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 指標定義",
            "",
            "- action diversity: 有効行動のうち `abstain` を除いたユニーク `action_id` 数。行動が無い入力は `not_measured`。",
            "- capability coverage: social result の `metrics.capability_coverage`。無ければ `not_measured`。0で埋めない。",
            "- interaction density: `interaction_edge_count / (roles × (roles-1) × turns)`。欠けた項があれば `not_measured`。",
            "- fail-closed rate: invalid / event_count。分母が無ければ `not_measured`。",
            "- collapse rate: `collapsed` が真偽値として測定できた実行だけの割合。未知は分母に入れない。",
            "- 実行の区別: `run_id` は世界入力ID。実行差は provider / model / runtime_revision / result SHA / event SHA。",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate observable social-run metrics without claiming emergence"
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="artifact file or directory (repeatable)",
    )
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    inputs = [Path(item) for item in (args.input or [repo_root / "artifacts/runs"])]
    report = build_report(inputs, repo_root=repo_root)
    json_path = Path(args.output_json)
    md_path = Path(args.output_md)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
