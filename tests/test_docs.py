from __future__ import annotations

import re
import unittest
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTests(unittest.TestCase):
    def test_design_ssot_documents_exist(self) -> None:
        required = (
            "docs/product-design.md",
            "docs/ux-flow.md",
            "docs/visual-system.md",
            "docs/architecture.md",
            "docs/security-model.md",
            "docs/social-simulation.md",
            "docs/adr/README.md",
            "RESULTS.md",
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
            "コードを書かずに参加する",
            "https://github.com/nexus-ai-2045/fiction-forks",
            "5人のAIエージェント",
            "PR作成はmergeや公開完了ではない",
            "反映確認済み",
            "決定論エンジン",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)

    def test_readme_hero_is_safe_self_contained_svg(self) -> None:
        hero = ROOT / "assets/readme/hero.svg"
        self.assertTrue(hero.is_file())
        root = ElementTree.parse(hero).getroot()
        self.assertTrue(root.tag.endswith("svg"))

        content = hero.read_text(encoding="utf-8")
        self.assertNotRegex(content, r"(?i)<script\b")
        self.assertNotRegex(content, r"(?i)(?:href|src)=[\"']https?://")
        self.assertIn("<title", content)
        self.assertIn("<desc", content)

    def test_live_agent_dependencies_are_exact_and_hash_locked(self) -> None:
        source = (ROOT / "requirements-agents.in").read_text(encoding="utf-8")
        lock = (ROOT / "requirements-agents.txt").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertRegex(source, r"(?m)^openai==\d+\.\d+\.\d+$")
        self.assertIn("--hash=sha256:", lock)
        self.assertIn("--require-hashes -r requirements-agents.txt", readme)

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
