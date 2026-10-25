"""Validate Fiction Forks PR kinds and render GitHub Actions summaries."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


PR_MARKER = re.compile(
    r"<!--\s*fiction-forks-pr-type:\s*(worldline|maintenance)\s*-->",
    re.IGNORECASE,
)
SLUG = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?")


class ContractError(ValueError):
    """Raised when a PR mixes contribution contracts."""


@dataclass(frozen=True)
class Change:
    status: str
    path: str

    @property
    def added(self) -> bool:
        return self.status.startswith("A")


@dataclass(frozen=True)
class ContractResult:
    kind: str
    intervention: str = ""
    slug: str = ""
    social_config: str = ""
    fixture: str = ""


def _git(*args: str, cwd: Path) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="strict",
    )
    if process.returncode:
        raise ContractError(process.stderr.strip() or "git command failed")
    return process.stdout


def changed_files(base: str, head: str, *, cwd: Path) -> list[Change]:
    raw = _git("diff", "--name-status", f"{base}...{head}", cwd=cwd)
    changes: list[Change] = []
    for line in raw.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            raise ContractError(f"変更pathを解析できません: {line!r}")
        status = fields[0]
        path = fields[-1].replace("\\", "/")
        changes.append(Change(status=status, path=path))
    if not changes:
        raise ContractError("PRに変更fileがありません。")
    return changes


def pr_kind(body: str) -> str:
    markers = PR_MARKER.findall(body or "")
    if len(markers) != 1:
        raise ContractError(
            "PR templateの種別markerを一つだけ残してください: "
            "worldline または maintenance"
        )
    return markers[0].lower()


def validate_contract(kind: str, changes: Sequence[Change], *, root: Path) -> ContractResult:
    added_interventions = [
        change.path
        for change in changes
        if change.added
        and change.path.startswith("interventions/")
        and change.path.endswith(".json")
    ]
    added_idea_files = [
        change.path for change in changes if change.added and change.path.startswith("ideas/")
    ]
    added_social_inputs = [
        change.path
        for change in changes
        if change.added
        and (
            re.fullmatch(r"scenarios/japan-2036/social-[a-z0-9-]+\.json", change.path)
            or re.fullmatch(r"fixtures/social/[a-z0-9-]+\.jsonl", change.path)
        )
    ]

    if added_idea_files:
        raise ContractError("アイデアはPRではなくidea Issueへ追加してください。")

    if kind == "maintenance":
        if added_interventions or added_social_inputs:
            raise ContractError(
                "maintenance PRに新しいintervention、social config、fixtureを混在できません。"
            )
        return ContractResult(kind=kind)

    if kind != "worldline":
        raise ContractError(f"未知のPR種別です: {kind}")
    if len(added_interventions) != 1:
        raise ContractError(
            "worldline PRはinterventions/へ新しいJSONを一件だけ追加してください。"
        )

    intervention = added_interventions[0]
    slug = Path(intervention).stem
    if not SLUG.fullmatch(slug):
        raise ContractError(
            "intervention slugは小文字英数字とhyphenだけで、1〜64文字にしてください。"
        )

    social_config = f"scenarios/japan-2036/social-{slug}.json"
    fixture = f"fixtures/social/{slug}.jsonl"
    changed_paths = {change.path for change in changes}
    missing_changes = [
        path for path in (social_config, fixture) if path not in changed_paths
    ]
    if missing_changes:
        raise ContractError(
            "worldline PRには同じslugのsocial configとfixtureが必要です: "
            + ", ".join(missing_changes)
        )
    missing_files = [
        path for path in (intervention, social_config, fixture) if not (root / path).is_file()
    ]
    if missing_files:
        raise ContractError("必須fileがcheckoutにありません: " + ", ".join(missing_files))

    return ContractResult(
        kind=kind,
        intervention=intervention,
        slug=slug,
        social_config=social_config,
        fixture=fixture,
    )


def _event(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"GitHub event JSONを読めません: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError("GitHub event JSONのrootはobjectである必要があります。")
    return data


def _safe_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _append(path: Path | None, text: str) -> None:
    if path is None:
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text.rstrip() + "\n")


def _write_outputs(path: Path | None, result: ContractResult) -> None:
    if path is None:
        return
    values = {
        "kind": result.kind,
        "intervention": result.intervention,
        "slug": result.slug,
        "social_config": result.social_config,
        "fixture": result.fixture,
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            if "\n" in value or "\r" in value:
                raise ContractError(f"GitHub output {key}に改行を含められません。")
            handle.write(f"{key}={value}\n")


def _pr_identity(event: dict[str, Any]) -> tuple[str, object, str]:
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        raise ContractError("pull_request eventではありません。")
    user = pull_request.get("user")
    author = user.get("login") if isinstance(user, dict) else "unknown"
    return str(author), pull_request.get("number", event.get("number", "?")), str(
        pull_request.get("title", "")
    )


def render_contract_summary(
    event: dict[str, Any],
    result: ContractResult,
    changes: Sequence[Change],
) -> str:
    author, number, title = _pr_identity(event)
    lines = [
        "# Fiction Forks PR contract",
        "",
        "| 項目 | 値 |",
        "|---|---|",
        f"| 投稿者 | @{_safe_cell(author)} |",
        f"| PR | #{_safe_cell(number)} — {_safe_cell(title)} |",
        f"| 種別 | `{_safe_cell(result.kind)}` |",
        f"| 変更file | {len(changes)} |",
    ]
    if result.kind == "worldline":
        lines.extend(
            [
                f"| intervention | `{result.intervention}` |",
                f"| social config | `{result.social_config}` |",
                f"| fixture | `{result.fixture}` |",
                "",
                "> 次のcheckで、この投稿者の5役×3ターンfixtureと2036年比較を実行します。",
                "> fixtureはプロトコル検証であり、live LLM実測ではありません。",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "> maintenance PRは新しい世界線として数えず、投稿者別simulationを実行しません。",
            ]
        )
    return "\n".join(lines) + "\n"


def render_failure_summary(event: dict[str, Any], message: str) -> str:
    try:
        author, number, title = _pr_identity(event)
    except ContractError:
        author, number, title = "unknown", "?", ""
    return (
        "# Fiction Forks PR contract: blocked\n\n"
        f"- 投稿者: @{_safe_cell(author)}\n"
        f"- PR: #{_safe_cell(number)} — {_safe_cell(title)}\n"
        f"- 理由: {_safe_cell(message)}\n\n"
        "`idea`はIssue、実装は`worldline` PR、保守は`maintenance` PRへ分けてください。\n"
    )


def render_worldline_summary(
    event: dict[str, Any], result: ContractResult, artifact: dict[str, Any]
) -> str:
    author, number, title = _pr_identity(event)
    actions = artifact.get("actions")
    if not isinstance(actions, list):
        raise ContractError("worldline artifactにactions arrayがありません。")
    valid = sum(1 for item in actions if isinstance(item, dict) and item.get("valid") is True)
    world = artifact.get("world_comparison")
    if not isinstance(world, dict):
        raise ContractError("worldline artifactにworld_comparisonがありません。")
    baseline = world.get("baseline")
    fork = world.get("fork")
    deltas = world.get("state_delta_at_comparison_year")
    if not isinstance(baseline, dict) or not isinstance(fork, dict) or not isinstance(deltas, dict):
        raise ContractError("worldline comparisonの必須objectがありません。")
    provider = artifact.get("provider")
    provider_name = provider.get("name") if isinstance(provider, dict) else "unknown"

    def verdict(state: dict[str, Any]) -> str:
        if state.get("collapsed") is True:
            return f"破滅（{state.get('collapse_year', '年不明')}）"
        return "回避"

    lines = [
        "# 投稿者のWORLDLINEを実行しました",
        "",
        "| 項目 | 実測値 |",
        "|---|---|",
        f"| 投稿者 | @{_safe_cell(author)} |",
        f"| PR | #{_safe_cell(number)} — {_safe_cell(title)} |",
        f"| intervention | `{result.slug}` |",
        f"| provider | `{_safe_cell(provider_name)}`（live LLMではありません） |",
        f"| AI役・ターン | {len(artifact.get('roles', []))}役 × {artifact.get('turn_count', '?')}ターン |",
        f"| 行動 | {valid}/{len(actions)} valid |",
        f"| 無介入2036 | {verdict(baseline)} |",
        f"| 介入2036 | {verdict(fork)} |",
        f"| 発動年 | {fork.get('activation_year', '未発動')} |",
        "",
        "## 2036年の指標差分",
        "",
        "| 指標 | 介入 − 無介入 |",
        "|---|---:|",
    ]
    for metric in sorted(deltas):
        delta = deltas[metric]
        prefix = "+" if isinstance(delta, (int, float)) and delta > 0 else ""
        lines.append(f"| `{_safe_cell(metric)}` | {prefix}{_safe_cell(delta)} |")
    lines.extend(
        [
            "",
            "> この結果はPRの入力とfixtureを同じseedで実行したMVPモデル上の比較です。",
            "> 未来予測、政策助言、作品の正解、権利者による認定ではありません。",
        ]
    )
    return "\n".join(lines) + "\n"


def check_command(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    event = _event(Path(args.event))
    summary = Path(args.summary) if args.summary else None
    try:
        changes = changed_files(args.base, args.head, cwd=root)
        kind = pr_kind(str(event.get("pull_request", {}).get("body") or ""))
        result = validate_contract(kind, changes, root=root)
        _write_outputs(Path(args.github_output) if args.github_output else None, result)
        _append(summary, render_contract_summary(event, result, changes))
    except ContractError as exc:
        _append(summary, render_failure_summary(event, str(exc)))
        print(f"PR contract blocked: {exc}", file=sys.stderr)
        return 2
    return 0


def summary_command(args: argparse.Namespace) -> int:
    event = _event(Path(args.event))
    artifact_path = Path(args.artifact)
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        if not isinstance(artifact, dict):
            raise ContractError("worldline artifactのrootはobjectである必要があります。")
        result = ContractResult(kind="worldline", slug=args.slug)
        _append(Path(args.summary), render_worldline_summary(event, result, artifact))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"worldline summary blocked: {exc}", file=sys.stderr)
        return 2
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="PR種別と変更pathを検査する")
    check.add_argument("--repo", default=".")
    check.add_argument("--base", required=True)
    check.add_argument("--head", required=True)
    check.add_argument("--event", required=True)
    check.add_argument("--github-output")
    check.add_argument("--summary")
    check.set_defaults(handler=check_command)

    summary = commands.add_parser("worldline-summary", help="実行済みworldlineを表示する")
    summary.add_argument("--event", required=True)
    summary.add_argument("--artifact", required=True)
    summary.add_argument("--slug", required=True)
    summary.add_argument("--summary", required=True)
    summary.set_defaults(handler=summary_command)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
