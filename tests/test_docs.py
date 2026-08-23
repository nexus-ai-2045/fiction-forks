from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTests(unittest.TestCase):
    def test_design_ssot_documents_exist(self) -> None:
        required = (
            "docs/product-design.md",
            "docs/ux-flow.md",
            "docs/architecture.md",
            "docs/security-model.md",
            "docs/adr/README.md",
        )
        for relative_path in required:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_adr_index_links_to_existing_accepted_records(self) -> None:
        index = (ROOT / "docs/adr/README.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\((\d{4}[^)]+\.md)\)", index)
        self.assertGreaterEqual(len(links), 6)
        for link in links:
            with self.subTest(adr=link):
                adr = ROOT / "docs/adr" / link
                self.assertTrue(adr.is_file())
                self.assertIn("- Status: Accepted", adr.read_text(encoding="utf-8"))

    def test_readme_keeps_core_participation_contract(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "一つのPull Requestが、一つの未来分岐",
            "3分で試す",
            "未来をforkする",
            "作品を知らない人",
            "決定的ルールエンジン",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)

    def test_relative_markdown_links_resolve(self) -> None:
        for markdown in ROOT.rglob("*.md"):
            content = markdown.read_text(encoding="utf-8")
            for raw_target in re.findall(r"\[[^]]*\]\(([^)]+)\)", content):
                target = raw_target.split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                with self.subTest(document=markdown.relative_to(ROOT), link=raw_target):
                    self.assertTrue((markdown.parent / target).resolve().exists())


if __name__ == "__main__":
    unittest.main()
