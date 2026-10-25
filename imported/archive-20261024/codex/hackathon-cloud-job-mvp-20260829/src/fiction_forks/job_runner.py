"""Fixed-input Cloud Job entry point for reproducible fixture simulations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .engine import ENGINE_VERSION, ContractError, load_json
from .providers import FixtureProvider, ReplayProvider
from .run_manifest import RUN_MANIFEST_SCHEMA_VERSION, validate_run_manifest
from .social import replay_equivalent, run_social_simulation

WORLDLINES = {
    "doraemon-public-tools": {
        "scenario": "scenarios/japan-2036/scenario.json",
        "intervention": "interventions/doraemon-public-tools.json",
        "social_config": "scenarios/japan-2036/social.json",
        "fixture": "fixtures/social/japan-2036-cooperation.jsonl",
    },
    "haruhi-world-observation": {
        "scenario": "scenarios/japan-2036/scenario.json",
        "intervention": "interventions/haruhi-world-observation.json",
        "social_config": "scenarios/japan-2036/social-haruhi-world-observation.json",
        "fixture": "fixtures/social/haruhi-world-observation.jsonl",
    },
}


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repo_root() -> Path:
    configured_root = os.environ.get("FICTION_FORKS_ROOT") or os.getcwd()
    return Path(configured_root).resolve(strict=True)


def _repo_file(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ContractError(f"repository input is outside the allowed root: {relative_path}")
    return path


def _output_directory(raw_path: str) -> Path:
    path = Path(raw_path)
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ContractError("output-dir must already exist") from error
    if not resolved.is_dir():
        raise ContractError("output-dir must be a directory")
    return resolved


def _publish_outputs_no_replace(outputs: Mapping[Path, bytes]) -> None:
    existing = [path.name for path in outputs if path.exists()]
    if existing:
        raise ContractError(f"refusing to overwrite existing outputs: {', '.join(existing)}")

    temporary: list[tuple[Path, Path]] = []
    published: list[Path] = []
    try:
        for target, data in outputs.items():
            descriptor, raw_temp = tempfile.mkstemp(
                prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
            )
            temp_path = Path(raw_temp)
            temporary.append((temp_path, target))
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        # Atomic hard-link creation fails if a concurrent writer published first.
        # The manifest is inserted last and acts as the completed-bundle marker.
        for temp_path, target in temporary:
            try:
                os.link(temp_path, target)
            except FileExistsError as error:
                raise ContractError(f"refusing to overwrite existing output: {target.name}") from error
            published.append(target)
    except Exception:
        for target in reversed(published):
            try:
                target.unlink()
            except FileNotFoundError:
                pass
        raise
    finally:
        for temp_path, _ in temporary:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def _source_revision(root: Path) -> str:
    baked = root / ".source-revision"
    if baked.is_file():
        revision = baked.read_text(encoding="ascii").strip()
    else:
        try:
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True,
                capture_output=True, text=True,
            ).stdout.strip()
            dirty = subprocess.run(
                ["git", "status", "--porcelain"], cwd=root, check=True,
                capture_output=True, text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise ContractError("source revision is unavailable") from error
        if dirty:
            raise ContractError("source tree must be clean before recording provenance")
    if len(revision) != 40 or any(
        character not in "0123456789abcdef" for character in revision
    ):
        raise ContractError("source revision must be a 40-character lowercase hex commit")
    return revision


def run_job(*, worldline: str, output_dir: str, seed: int = 2036) -> dict[str, Any]:
    root = _repo_root()
    source_revision = _source_revision(root)
    destination = _output_directory(output_dir)
    config = WORLDLINES[worldline]
    scenario = load_json(_repo_file(root, config["scenario"]))
    intervention = load_json(_repo_file(root, config["intervention"]))
    social_config = load_json(_repo_file(root, config["social_config"]))
    fixture = FixtureProvider.from_jsonl(_repo_file(root, config["fixture"]))

    artifact = run_social_simulation(
        scenario, intervention, social_config, fixture, seed=seed
    )
    replay_artifact = run_social_simulation(
        scenario, intervention, social_config, ReplayProvider(artifact), seed=seed
    )
    equivalent = replay_equivalent(artifact, replay_artifact)
    if not equivalent:
        raise ContractError("fixture replay is not equivalent")

    artifact_bytes = _canonical_bytes(artifact)
    replay_bytes = _canonical_bytes(replay_artifact)
    basename = worldline
    artifact_path = destination / f"{basename}.artifact.json"
    replay_path = destination / f"{basename}.replay.json"
    manifest_path = destination / f"{basename}.manifest.json"
    manifest = {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "recorded_at": datetime.now(timezone.utc).date().isoformat(),
        "run_kind": "fixture",
        "ai_measured": False,
        "engine_commit": source_revision,
        "engine_version": ENGINE_VERSION,
        "scenario_id": scenario["id"],
        "intervention_id": intervention["id"],
        "social_config_id": social_config["id"],
        "seed": seed,
        "run_id": artifact["run_id"],
        "input_digest": artifact["input_digest"],
        "final_event_hash": artifact["final_event_hash"],
        "artifact_path": artifact_path.name,
        "artifact_sha256": _sha256(artifact_bytes),
        "replay_artifact_path": replay_path.name,
        "replay_artifact_sha256": _sha256(replay_bytes),
        "replay_equivalent": equivalent,
    }
    manifest = validate_run_manifest(manifest)
    manifest_bytes = _canonical_bytes(manifest)
    _publish_outputs_no_replace(
        {
            artifact_path: artifact_bytes,
            replay_path: replay_bytes,
            manifest_path: manifest_bytes,
        }
    )
    return {
        "status": "ok",
        "run_id": artifact["run_id"],
        "worldline": worldline,
        "manifest": str(manifest_path),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worldline", required=True, choices=sorted(WORLDLINES))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=2036)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = run_job(
            worldline=args.worldline, output_dir=args.output_dir, seed=args.seed
        )
    except (ContractError, KeyError, OSError, ValueError) as error:
        print(f"job_runner: {error}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
