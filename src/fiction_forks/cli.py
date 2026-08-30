"""Fiction Forks command line interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .engine import ContractError, compare_worlds, load_json, simulate
from .providers import FixtureProvider, OpenAIProvider, ProviderError, ReplayProvider
from .participation import load_template_catalog, prepare_provisional_request
from .social import run_social_simulation


def _technology_delays(values: Sequence[str]) -> dict[str, int]:
    delays: dict[str, int] = {}
    for value in values:
        try:
            node_id, raw_years = value.rsplit("=", 1)
            years = int(raw_years)
        except ValueError as error:
            raise ContractError("--delay-node must use NODE_ID=YEARS") from error
        if not node_id or years < 0:
            raise ContractError("--delay-node years must be a non-negative integer")
        delays[node_id] = years
    return delays


def _add_delay_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--delay-node",
        action="append",
        default=[],
        metavar="NODE_ID=YEARS",
        help="技術ツリーノードの完了を指定年数だけ遅らせる（複数指定可）",
    )


def _add_output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output")
    parser.add_argument("--overwrite", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fiction Forks simulation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate_parser = subparsers.add_parser("simulate", help="一つの世界線を実行する")
    simulate_parser.add_argument("--scenario", required=True)
    simulate_parser.add_argument("--intervention")
    simulate_parser.add_argument("--seed", type=int, default=2036)
    _add_delay_option(simulate_parser)
    _add_output_options(simulate_parser)

    compare_parser = subparsers.add_parser(
        "compare", help="基準世界と介入世界を比較する"
    )
    compare_parser.add_argument("--scenario", required=True)
    compare_parser.add_argument("--intervention", required=True)
    compare_parser.add_argument("--seed", type=int, default=2036)
    _add_delay_option(compare_parser)
    _add_output_options(compare_parser)

    social_parser = subparsers.add_parser(
        "social", help="複数の社会役が対話する世界線を実行する"
    )
    social_parser.add_argument("--scenario", required=True)
    social_parser.add_argument("--intervention", required=True)
    social_parser.add_argument("--social-config", required=True)
    social_parser.add_argument(
        "--provider", choices=("fixture", "replay", "openai"), required=True
    )
    social_parser.add_argument("--fixture")
    social_parser.add_argument("--replay")
    social_parser.add_argument("--model")
    social_parser.add_argument("--confirm-live", action="store_true")
    social_parser.add_argument("--seed", type=int, default=2036)
    social_parser.add_argument("--bundle-output")
    social_parser.add_argument("--source-revision")
    _add_output_options(social_parser)
    preview_parser = subparsers.add_parser(
        "prepare-preview", help="確認済みIdeaDraftを暫定run requestへ変換する"
    )
    preview_parser.add_argument("--idea-draft", required=True)
    preview_parser.add_argument("--catalog", required=True)
    preview_parser.add_argument("--template-confirmation", required=True)
    preview_parser.add_argument("--template-id", required=True)
    preview_parser.add_argument("--seed", type=int, required=True)
    preview_parser.add_argument("--delay-profile", required=True)
    preview_parser.add_argument("--repo-root", default=".")
    return parser


def _social_provider(args: argparse.Namespace):
    if args.provider == "fixture":
        if not args.fixture:
            raise ContractError("fixture provider requires --fixture")
        return FixtureProvider.from_jsonl(args.fixture)
    if args.provider == "replay":
        if not args.replay:
            raise ContractError("replay provider requires --replay")
        return ReplayProvider.from_path(args.replay)
    if not args.model:
        raise ContractError("openai provider requires --model")
    return OpenAIProvider(
        model=args.model,
        confirm_live=args.confirm_live,
    )


def _artifact_bytes(rendered: str) -> bytes:
    # Artifact bytes are part of the replay/provenance contract. Text-mode
    # writes would emit CRLF on Windows and LF on Linux, producing different
    # SHA-256 values for the same logical run.
    return (rendered + "\n").encode("utf-8")


def _owns_installed_target(entry: dict[str, object], target: Path) -> bool:
    """Return True only if target is still the file this transaction installed.

    Linux can reuse an inode immediately after unlink. Matching device/inode is
    therefore not enough; the staged digest must match as well.
    """

    try:
        stat = target.stat()
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
    except OSError:
        return False
    identity_matches = entry.get("staged_identity") == (stat.st_dev, stat.st_ino)
    digest_matches = entry.get("staged_digest") == digest
    return identity_matches and digest_matches


def _write_output(path_value: str, rendered: str, *, overwrite: bool) -> None:
    path = Path(path_value)
    if path.exists() and not overwrite:
        raise ContractError("output already exists; pass --overwrite to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise ContractError(f"temporary output already exists: {temporary}")
    temporary.write_bytes(_artifact_bytes(rendered))
    temporary.replace(path)


def _write_output_pair(
    first_path_value: str,
    first_rendered: str,
    second_path_value: str,
    second_rendered: str,
    *,
    overwrite: bool,
) -> None:
    """Stage and commit a result/bundle pair, restoring the old pair on failure."""

    entries = [
        (Path(first_path_value), first_rendered),
        (Path(second_path_value), second_rendered),
    ]
    staged: list[dict[str, object]] = []
    try:
        if not overwrite:
            existing = [str(target) for target, _rendered in entries if target.exists()]
            if existing:
                raise ContractError(
                    "output already exists; pass --overwrite to replace it: "
                    + ", ".join(existing)
                )
        for target, rendered in entries:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.tmp")
            backup = target.with_name(f".{target.name}.{uuid.uuid4().hex}.bak")
            if temporary.exists():
                raise ContractError(f"transaction file already exists: {temporary}")
            entry: dict[str, object] = {
                "target": target,
                "temporary": temporary,
                "backup": backup,
                "existed": target.exists(),
                "backed_up": False,
                "backup_owned": False,
                "installed": False,
                "staged_identity": None,
                "staged_digest": None,
                "temporary_owned": False,
            }
            staged.append(entry)
            payload = _artifact_bytes(rendered)
            with temporary.open("xb") as handle:
                entry["temporary_owned"] = True
                handle.write(payload)
            stat = temporary.stat()
            entry["staged_identity"] = (stat.st_dev, stat.st_ino)
            entry["staged_digest"] = hashlib.sha256(payload).hexdigest()

        for entry in staged:
            target = entry["target"]
            backup = entry["backup"]
            if entry["existed"]:
                target.replace(backup)
                entry["backed_up"] = True
                entry["backup_owned"] = True
        for entry in staged:
            target = entry["target"]
            temporary = entry["temporary"]
            if overwrite:
                temporary.replace(target)
                entry["installed"] = True
                entry["temporary_owned"] = False
            else:
                # A hard link is an atomic no-replace install on the same
                # volume. It closes the target.exists()/replace() race without
                # taking ownership of a concurrently-created output.
                target.hardlink_to(temporary)
                entry["installed"] = True
                temporary.unlink()
                entry["temporary_owned"] = False
    except (OSError, ContractError) as error:
        rollback_errors: list[str] = []
        for entry in reversed(staged):
            target = entry["target"]
            temporary = entry["temporary"]
            backup = entry["backup"]
            try:
                if entry["temporary_owned"]:
                    temporary.unlink(missing_ok=True)
                restore_allowed = not target.exists()
                if entry["installed"] and target.exists():
                    if _owns_installed_target(entry, target):
                        target.unlink()
                        restore_allowed = True
                    else:
                        rollback_errors.append(
                            f"target ownership changed during rollback: {target}"
                        )
                elif entry["backed_up"] and target.exists():
                    rollback_errors.append(
                        f"target was concurrently recreated during rollback: {target}"
                    )
                if entry["backed_up"] and entry["backup_owned"] and backup.exists():
                    if restore_allowed:
                        backup.replace(target)
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            raise ContractError(
                "output pair failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from error
        raise ContractError("output pair was not committed") from error
    else:
        # The pair is committed at this point. Backup cleanup is maintenance,
        # so a transient unlink failure must not report a successful pair as
        # uncommitted.
        for entry in staged:
            try:
                if entry["backup_owned"]:
                    entry["backup"].unlink(missing_ok=True)
            except OSError:
                pass


def _write_stdout_bytes(payload: bytes) -> None:
    """Write auditable UTF-8/LF bytes while preserving StringIO-based tests."""

    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(payload.decode("utf-8"))
        return
    buffer.write(payload)
    buffer.flush()


def _verified_source_revision(expected: str) -> str:
    """Bind live evidence to the exact, clean runtime source checkout."""

    root = Path(__file__).resolve().parents[2]
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--",
                "src",
                "pyproject.toml",
                "requirements-runtime.txt",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ContractError(
            "bundle evidence requires a readable Git checkout"
        ) from error
    if expected != head:
        raise ContractError("--source-revision must match the executing Git HEAD")
    if status:
        raise ContractError("bundle evidence requires clean runtime source files")
    return head


def _preflight_social_outputs(args: argparse.Namespace) -> None:
    if args.bundle_output and not args.output:
        raise ContractError("--bundle-output requires --output")
    paths = [
        Path(value).resolve() for value in (args.output, args.bundle_output) if value
    ]
    if len(paths) == 2:
        if paths[0] == paths[1]:
            raise ContractError("--output and --bundle-output must be different paths")
    if not args.overwrite:
        existing = [str(path) for path in paths if path.exists()]
        if existing:
            raise ContractError(
                "output already exists; pass --overwrite to replace it: "
                + ", ".join(existing)
            )


def main(argv: Sequence[str] | None = None) -> int:
    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(effective_argv)
    requested_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    started_at = requested_at
    source_revision: str | None = None
    try:
        if args.command == "social":
            _preflight_social_outputs(args)
            if bool(args.bundle_output) != bool(args.source_revision):
                raise ContractError(
                    "--bundle-output and --source-revision must be specified together"
                )
            if args.bundle_output:
                source_revision = _verified_source_revision(args.source_revision)
        if args.command == "prepare-preview":
            result = prepare_provisional_request(
                load_json(args.idea_draft),
                load_template_catalog(args.catalog, root=args.repo_root),
                load_json(args.template_confirmation),
                root=args.repo_root,
                template_id=args.template_id,
                seed=args.seed,
                delay_profile=args.delay_profile,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0 if result["status"] == "ready" else 3
        scenario = load_json(args.scenario)
        intervention = load_json(args.intervention) if args.intervention else None
        if args.command == "social":
            if intervention is None:
                raise ContractError("social command requires --intervention")
            result = run_social_simulation(
                scenario,
                intervention,
                load_json(args.social_config),
                _social_provider(args),
                seed=args.seed,
            )
            rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
            if args.bundle_output:
                if source_revision is None:  # narrowed by the preflight contract above
                    raise ContractError("bundle source revision was not verified")
                from .run_bundle import build_run_bundle

                completed_at = (
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                )
                stdout_bytes = (rendered + "\n").encode("utf-8")
                bundle = build_run_bundle(
                    result,
                    command=[sys.executable, "-m", "fiction_forks", *effective_argv],
                    requested_at=requested_at,
                    started_at=started_at,
                    completed_at=completed_at,
                    generated_at=completed_at,
                    source_revision=source_revision,
                    stdout_sha256=hashlib.sha256(stdout_bytes).hexdigest(),
                )
                bundle_rendered = json.dumps(
                    bundle, ensure_ascii=False, indent=2, sort_keys=True
                )
                _write_output_pair(
                    args.output,
                    rendered,
                    args.bundle_output,
                    bundle_rendered,
                    overwrite=args.overwrite,
                )
                _write_stdout_bytes(stdout_bytes)
            else:
                if args.output:
                    _write_output(args.output, rendered, overwrite=args.overwrite)
                print(rendered)
            return 0
        delays = _technology_delays(args.delay_node)
        if delays and intervention is None:
            raise ContractError("--delay-node requires --intervention")
        if args.command == "compare":
            result = compare_worlds(
                scenario,
                intervention,
                seed=args.seed,
                technology_delays=delays,
            )
        else:
            result = simulate(
                scenario,
                intervention,
                seed=args.seed,
                technology_delays=delays,
            )
    except (ContractError, ProviderError, OSError, json.JSONDecodeError) as error:
        print(
            json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False)
        )
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    try:
        if args.output:
            _write_output(args.output, rendered, overwrite=args.overwrite)
    except (ContractError, OSError) as error:
        print(
            json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False)
        )
        return 2
    print(rendered)
    return 0
