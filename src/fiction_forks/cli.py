"""Fiction Forks command line interface."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from .engine import ContractError, compare_worlds, load_json, simulate


def _technology_delays(values: Sequence[str]) -> dict[str, int]:
    delays: dict[str, int] = {}
    for value in values:
        try:
            node_id, raw_years = value.rsplit("=", 1)
            years = int(raw_years)
        except ValueError as error:
            raise ContractError(
                "--delay-node must use NODE_ID=YEARS"
            ) from error
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fiction Forks simulation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate_parser = subparsers.add_parser("simulate", help="一つの世界線を実行する")
    simulate_parser.add_argument("--scenario", required=True)
    simulate_parser.add_argument("--intervention")
    simulate_parser.add_argument("--seed", type=int, default=2036)
    _add_delay_option(simulate_parser)

    compare_parser = subparsers.add_parser("compare", help="基準世界と介入世界を比較する")
    compare_parser.add_argument("--scenario", required=True)
    compare_parser.add_argument("--intervention", required=True)
    compare_parser.add_argument("--seed", type=int, default=2036)
    _add_delay_option(compare_parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        scenario = load_json(args.scenario)
        intervention = load_json(args.intervention) if args.intervention else None
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
    except (ContractError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0
