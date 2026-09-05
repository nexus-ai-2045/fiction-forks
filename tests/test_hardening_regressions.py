"""Regressions for summary-cell escaping, atomic single-file writes, and replay typing."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fiction_forks import cli
from fiction_forks.agent_protocol import digest
from fiction_forks.engine import ContractError
from fiction_forks.pr_contract import (
    ContractResult,
    _safe_cell,
    render_contract_summary,
)
from fiction_forks.providers import ProviderError, ReplayProvider


def _unescaped_pipe_count(cell: str) -> int:
    """Count pipes GFM would treat as raw cell separators."""

    count = 0
    backslashes = 0
    for char in cell:
        if char == "\\":
            backslashes += 1
            continue
        if char == "|" and backslashes % 2 == 0:
            count += 1
        backslashes = 0
    return count


class SafeCellEscapingTests(unittest.TestCase):
    def test_backslash_is_escaped_before_pipe(self) -> None:
        self.assertEqual(_safe_cell(r"evil \| injected"), "evil \\\\\\| injected")

    def test_backslash_pipe_payload_cannot_split_a_cell(self) -> None:
        self.assertEqual(_unescaped_pipe_count(_safe_cell(r"evil \| injected")), 0)

    def test_trailing_backslash_cannot_escape_the_row_separator(self) -> None:
        self.assertEqual(_safe_cell("evil \\"), "evil \\\\")

    def test_newlines_and_plain_pipes_stay_neutralised(self) -> None:
        self.assertEqual(_safe_cell("a|b\nc\rd"), "a\\|b c d")

    def test_hostile_pr_title_stays_in_one_summary_row(self) -> None:
        event = {
            "pull_request": {
                "user": {"login": "attacker"},
                "number": 7,
                "title": r"title \| 種別 | `worldline` | injected",
            }
        }
        summary = render_contract_summary(
            event,
            ContractResult(kind="maintenance"),
            (),
        )
        pr_row = next(line for line in summary.splitlines() if line.startswith("| PR |"))
        # "| PR | ... |" has exactly two structural pipes plus the leading one.
        self.assertEqual(_unescaped_pipe_count(pr_row), 3)


class WriteOutputAtomicityTests(unittest.TestCase):
    def test_writes_and_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "out.json"
            cli._write_output(str(target), "first", overwrite=False)
            self.assertEqual(target.read_bytes(), b"first\n")
            cli._write_output(str(target), "second", overwrite=True)
            self.assertEqual(target.read_bytes(), b"second\n")

    def test_existing_target_is_rejected_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.json"
            target.write_text("keep", encoding="utf-8")
            with self.assertRaises(ContractError):
                cli._write_output(str(target), "new", overwrite=False)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")

    def test_concurrent_creation_after_the_exists_check_is_not_clobbered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.json"
            real_artifact_bytes = cli._artifact_bytes

            def racing_artifact_bytes(rendered: str) -> bytes:
                # Simulates a concurrent writer landing between the
                # path.exists() guard and the install step.
                target.write_text("winner", encoding="utf-8")
                return real_artifact_bytes(rendered)

            with patch.object(cli, "_artifact_bytes", racing_artifact_bytes):
                with self.assertRaises(ContractError):
                    cli._write_output(str(target), "loser", overwrite=False)
            self.assertEqual(target.read_text(encoding="utf-8"), "winner")
            self.assertEqual(
                sorted(p.name for p in Path(tmp).iterdir()),
                ["out.json"],
            )


class ReplayConditionCountTypingTests(unittest.TestCase):
    def _artifact(self, condition_count: object) -> dict[str, object]:
        input_digest = "d" * 64
        action = {
            "turn": 1,
            "agent_id": "role-1",
            "condition_count": condition_count,
            "text_redacted": True,
        }
        item = {
            "action": action,
            "intent_id": "intent-1",
            "valid": True,
            "invalid_reason": None,
            "state_before_hash": "a" * 64,
            "state_after_hash": "b" * 64,
        }
        previous_hash = digest({"input_digest": input_digest})
        receipt = {
            key: item[key]
            for key in (
                "intent_id",
                "action",
                "valid",
                "invalid_reason",
                "state_before_hash",
                "state_after_hash",
            )
        }
        item["previous_event_hash"] = previous_hash
        item["event_hash"] = digest(
            {"previous_event_hash": previous_hash, "receipt": receipt}
        )
        return {
            "schema_version": "fiction_forks_social_result.v1",
            "input_digest": input_digest,
            "actions": [item],
            "final_event_hash": item["event_hash"],
        }

    def _observation(self) -> dict[str, object]:
        return {
            "input_digest": "d" * 64,
            "turn": 1,
            "role": {"id": "role-1"},
        }

    def test_int_condition_count_is_accepted(self) -> None:
        provider = ReplayProvider(self._artifact(2))
        recorded = provider.choose(self._observation())
        self.assertEqual(len(recorded["conditions"]), 2)

    def test_bool_condition_count_is_rejected(self) -> None:
        provider = ReplayProvider(self._artifact(True))
        with self.assertRaises(ProviderError):
            provider.choose(self._observation())


if __name__ == "__main__":
    unittest.main()
