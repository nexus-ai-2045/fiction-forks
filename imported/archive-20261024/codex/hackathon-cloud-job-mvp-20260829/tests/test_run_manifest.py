from __future__ import annotations

import json
import copy
import unittest
from pathlib import Path

from fiction_forks.run_manifest import validate_run_manifest
from fiction_forks.engine import ContractError

ROOT = Path(__file__).resolve().parents[1]


class RunManifestContractTests(unittest.TestCase):
    def test_existing_curated_manifests_share_the_canonical_contract(self) -> None:
        for path in sorted((ROOT / "artifacts/runs").glob("*.manifest.json")):
            with self.subTest(path=path.name):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(value, validate_run_manifest(value))

    def test_optional_artifact_paths_and_hashes_are_paired(self) -> None:
        value = json.loads(
            (ROOT / "artifacts/runs/haruhi-world-observation-fixture.manifest.json")
            .read_text(encoding="utf-8")
        )
        pairs = (
            ("comparison_artifact_path", "comparison_artifact_sha256"),
            ("delay_artifact_path", "delay_artifact_sha256"),
            ("replay_artifact_path", "replay_artifact_sha256"),
        )
        for path_field, hash_field in pairs:
            for missing_field in (path_field, hash_field):
                with self.subTest(pair=(path_field, hash_field), missing=missing_field):
                    candidate = copy.deepcopy(value)
                    candidate[path_field] = "artifact.json"
                    candidate[hash_field] = "a" * 64
                    del candidate[missing_field]
                    with self.assertRaisesRegex(ContractError, "must appear together"):
                        validate_run_manifest(candidate)


if __name__ == "__main__":
    unittest.main()
