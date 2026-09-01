from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]


def canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


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
            "catalogs/intervention-templates.v1.json",
            "catalogs/idea-status.v1.json",
            "fixtures/participation/public-tools-idea-draft.v1.json",
            "RESULTS.md",
            "web/index.html",
            "web/styles.css",
            "web/app.js",
            "notebooks/validate-worldline.ipynb",
        )
        for relative_path in required:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_adr_index_status_matches_each_record(self) -> None:
        index = (ROOT / "docs/adr/README.md").read_text(encoding="utf-8")
        rows = re.findall(
            r"(?m)^\| \[(\d{4})\]\((\d{4}[^)]+\.md)\) "
            r"\| (Accepted|Proposed|Superseded|Deprecated) \|",
            index,
        )
        self.assertGreaterEqual(len(rows), 6)
        indexed_links = re.findall(
            r"(?m)^\| \[\d{4}\]\((\d{4}[^)]+\.md)\) \|",
            index,
        )
        self.assertEqual(len(rows), len(indexed_links))
        self.assertEqual(len({adr_id for adr_id, _, _ in rows}), len(rows))
        for adr_id, link, indexed_status in rows:
            with self.subTest(adr=adr_id):
                adr = ROOT / "docs/adr" / link
                self.assertTrue(adr.is_file())
                content = adr.read_text(encoding="utf-8")
                record_statuses = re.findall(
                    r"(?m)^- Status: (Accepted|Proposed|Superseded|Deprecated)$",
                    content,
                )
                self.assertEqual(record_statuses, [indexed_status])

    def test_adr_index_lists_every_adr_record(self) -> None:
        index = (ROOT / "docs/adr/README.md").read_text(encoding="utf-8")
        indexed_links = set(
            re.findall(r"(?m)^\| \[\d{4}\]\((\d{4}[^)]+\.md)\) \|", index)
        )
        records = {
            path.name
            for path in (ROOT / "docs/adr").glob("[0-9][0-9][0-9][0-9]-*.md")
        }
        self.assertEqual(records, indexed_links)

    def test_chat_simulation_roadmap_keeps_state_and_safety_boundaries(self) -> None:
        adr = (
            ROOT
            / "docs/adr/0012-chat-first-provisional-simulation-and-local-codex-boundary.md"
        ).read_text(encoding="utf-8")
        product = (ROOT / "docs/product-design.md").read_text(encoding="utf-8")
        architecture = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
        security = (ROOT / "docs/security-model.md").read_text(encoding="utf-8")
        ssot = (ROOT / "PROJECT_SSOT.md").read_text(encoding="utf-8")

        for phrase in (
            "chat-draft",
            "understanding-check",
            "provisional-preview",
            "official-result",
            "doom-candidate",
            "この理解でよいか",
            "not-simulatable",
            "127.0.0.1",
            "raw Codex app-server",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, adr)

        self.assertIn("Vite + React + TypeScript", product)
        self.assertIn("0.4は複数PRをまとめる一つのmilestone", product)
        self.assertIn("現行scenarioにはレベル閾値と連鎖条件", product)
        self.assertIn("DialogueProvider", architecture)
        self.assertIn("loopback-only companion", architecture)
        self.assertIn("exact `main` commit", adr)
        self.assertIn("worldline PRがmerge", adr)
        self.assertIn("catalogs/intervention-templates.v1.json", architecture)
        self.assertIn("`main`に固定されたActions workflow", architecture)
        self.assertIn("forkまたはPRのcodeはcheckoutしない", architecture)
        self.assertIn("path、git ref、effect、model/provider、任意CLI引数は受け付けない", architecture)
        self.assertIn(
            "公開WebにOpenAI API key、GitHub token、Codex credentialを置かない",
            architecture,
        )
        self.assertIn("短命capability token", security)
        self.assertIn("exact Origin allowlist", security)
        self.assertIn("Origin: null", security)
        self.assertIn("同時run数", security)
        self.assertIn("Issue open/closedだけで推定しない", ssot)
        self.assertIn("catalogs/idea-status.v1.json", ssot)

        prohibited = adr.split("## Prohibited", 1)[1].split(
            "## Human Review Gate", 1
        )[0]
        self.assertIn(
            "公開WebへOpenAI API key、GitHub token、Codex credentialを置く",
            prohibited,
        )

    def test_preview_template_catalog_references_fixed_interventions(self) -> None:
        catalog = json.loads(
            (ROOT / "catalogs/intervention-templates.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            catalog["schema_version"],
            "fiction_forks_preview_template_catalog.v1",
        )
        self.assertEqual(catalog["catalog_version"], 3)
        scenario = json.loads(
            (ROOT / "scenarios/japan-2036/scenario.json").read_text(
                encoding="utf-8"
            )
        )
        templates = catalog["templates"]
        template_ids = [entry["template_id"] for entry in templates]
        self.assertEqual(len(template_ids), len(set(template_ids)))
        self.assertGreaterEqual(len(templates), 1)
        for entry in templates:
            with self.subTest(template=entry["template_id"]):
                self.assertIn(entry["status"], {"preview_allowed", "disabled"})
                self.assertGreaterEqual(entry["template_version"], 1)
                self.assertTrue(entry["requires_user_confirmation"])
                self.assertFalse(entry["idea_text_changes_engine_inputs"])
                self.assertEqual(entry["scenario_id"], scenario["id"])
                self.assertEqual(entry["allowed_seeds"], [2036])
                self.assertEqual(entry["delay_profiles"], ["none"])
                self.assertTrue(
                    entry["intervention_path"].startswith("interventions/")
                )
                self.assertNotIn("..", Path(entry["intervention_path"]).parts)
                intervention_path = ROOT / entry["intervention_path"]
                self.assertTrue(intervention_path.is_file())
                intervention = json.loads(
                    intervention_path.read_text(encoding="utf-8")
                )
                canonical = json.dumps(
                    intervention,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                self.assertEqual(
                    hashlib.sha256(canonical).hexdigest(),
                    entry["intervention_sha256"],
                )
                self.assertEqual(intervention["id"], entry["intervention_id"])

                self.assertRegex(
                    entry["social_config_path"],
                    r"^scenarios/[a-z0-9-]+/social(-[a-z0-9-]+)?\.json$",
                )
                self.assertRegex(
                    entry["fixture_path"], r"^fixtures/social/[a-z0-9-]+\.jsonl$"
                )
                social_config_path = ROOT / entry["social_config_path"]
                fixture_path = ROOT / entry["fixture_path"]
                self.assertTrue(social_config_path.is_file())
                self.assertTrue(fixture_path.is_file())
                social_config = json.loads(
                    social_config_path.read_text(encoding="utf-8")
                )
                self.assertEqual(social_config["id"], entry["social_config_id"])
                self.assertEqual(
                    canonical_digest(social_config), entry["social_config_sha256"]
                )
                records = [
                    json.loads(line)
                    for line in fixture_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                self.assertEqual(canonical_digest(records), entry["fixture_sha256"])

    def test_participation_entries_route_to_distinct_workflows(self) -> None:
        ux = (ROOT / "docs/ux-flow.md").read_text(encoding="utf-8")
        for edge in (
            'entry -->|作品| chat["Idea Chat / 作品 + アイデア"]',
            'entry -->|問題| problemChat["Problem Chat / 問題 + アイデア"]',
            'entry -->|専門| evidence["evidence / worldline草案"]',
            'entry -->|結果| simulationIssue["simulation Issue"]',
            'entry -->|次の破滅| doomIssue["doom-candidate Issue"]',
        ):
            with self.subTest(edge=edge):
                self.assertIn(edge, ux)
        self.assertNotIn('entry --> chat["Idea Chat"]', ux)
        self.assertIn(
            'problemChat --> problemUnderstanding{"この問題理解でよい？"}', ux
        )
        self.assertIn('problemUnderstanding -->|修正| problemChat', ux)
        self.assertIn('problemUnderstanding -->|確認| draft', ux)
        self.assertNotIn("problemChat --> understanding", ux)
        self.assertIn("DOOM LEVEL — CONTRACT PENDING", ux)
        self.assertIn('review --> merged["worldline PRをmerge"]', ux)
        self.assertIn('merged --> mainRun["exact main commitで公式run"]', ux)
        self.assertIn('mainRun --> result["公式結果をWebとIssueへ返す"]', ux)

    def test_readme_keeps_core_participation_contract(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "コードを書かずに参加する",
            "https://github.com/nexus-ai-2045/fiction-forks",
            "5人のAIエージェント",
            "PR作成はmergeや公開完了ではない",
            "反映確認済み",
            "決定論エンジン",
            "Idea = Issue",
            "Worldline = PR",
            "https://nexus-ai-2045.github.io/fiction-forks/",
            "https://github.com/nexus-ai-2045/fiction-forks/fork",
            "外部contributor",
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
        for element in root.iter():
            for raw_name, value in element.attrib.items():
                name = raw_name.rsplit("}", 1)[-1].lower()
                if name in {"href", "src"}:
                    self.assertTrue(
                        value.startswith("#"),
                        f"external SVG reference in {name}: {value}",
                    )
                for match in re.findall(r"(?i)url\(([^)]+)\)", value):
                    reference = match.strip().strip("\"'")
                    self.assertTrue(
                        reference.startswith("#"),
                        f"external CSS reference: {reference}",
                    )
            if element.tag.rsplit("}", 1)[-1].lower() == "style":
                for match in re.findall(r"(?i)url\(([^)]+)\)", element.text or ""):
                    reference = match.strip().strip("\"'")
                    self.assertTrue(
                        reference.startswith("#"),
                        f"external style reference: {reference}",
                    )
        self.assertIn("<title", content)
        self.assertIn("<desc", content)
        self.assertIn("BASELINE / 無介入", content)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "https://raw.githubusercontent.com/nexus-ai-2045/fiction-forks/"
            "main/assets/readme/hero.svg",
            readme,
        )

    def test_live_agent_dependencies_are_exact_and_hash_locked(self) -> None:
        source = (ROOT / "requirements-agents.in").read_text(encoding="utf-8")
        lock = (ROOT / "requirements-agents.txt").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertRegex(source, r"(?m)^openai==\d+\.\d+\.\d+$")
        self.assertIn("--hash=sha256:", lock)
        self.assertIn("--require-hashes -r requirements-agents.txt", readme)

    def test_relative_markdown_links_resolve(self) -> None:
        for markdown in ROOT.rglob("*.md"):
            if "node_modules" in markdown.parts:
                continue
            content = markdown.read_text(encoding="utf-8")
            for raw_target in re.findall(r"\[[^]]*\]\(([^)]+)\)", content):
                target = raw_target.split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                with self.subTest(document=markdown.relative_to(ROOT), link=raw_target):
                    self.assertTrue((markdown.parent / target).resolve().exists())

    def test_idea_builder_keeps_static_safety_boundary(self) -> None:
        html = (ROOT / "web/index.html").read_text(encoding="utf-8")
        script = (ROOT / "web/app.js").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        for phrase in (
            "GitHubでIssueを確認",
            "作品とアイデア",
            "作品名",
            "アイデア",
            "1 PR = 1 WORLDLINE",
            "Issueを作っただけではシミュレーションは走りません",
            "PRを追加したい人へ",
            "これまでのアイデア",
            "AIにworldline PR化を頼む",
            "Content-Security-Policy",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, html)
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("localStorage", script)
        self.assertIn("textContent", script)
        self.assertIn("field.value.trim().length === 0", script)
        self.assertNotIn("data-step-indicator", html)
        self.assertIn('href="workbench/"', html)
        self.assertIn('class="nav-handoff" href="#handoff"', html)
        self.assertNotIn(".site-header nav a:first-child", (ROOT / "web/styles.css").read_text(encoding="utf-8"))
        self.assertNotIn("借りたい機能</b>", html)
        self.assertNotIn("変えたい未来</b>", html)
        self.assertNotIn("条件・副作用</b>", html)
        self.assertIn('issueLink.href = "#"', script)
        self.assertIn("あとはIssue URLを貼るだけです", script)
        self.assertIn("https://github.com/${REPOSITORY}", script)
        self.assertIn("state=all", script)
        self.assertNotIn("state=open&labels=idea", script)
        implemented_items = re.findall(
            r'<article\s+class="implemented-item"([^>]*)>', html
        )
        listed_worldline_ids = []
        for attributes in implemented_items:
            match = re.search(r'data-worldline-id="([^"]*)"', attributes)
            self.assertIsNotNone(
                match,
                "implemented-itemにはdata-worldline-idが必要です",
            )
            worldline_id = match.group(1)
            self.assertRegex(worldline_id, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
            listed_worldline_ids.append(worldline_id)
        listed_worldlines = set(listed_worldline_ids)
        self.assertTrue(listed_worldlines)
        self.assertEqual(len(listed_worldline_ids), len(listed_worldlines))
        for worldline_id in listed_worldlines:
            with self.subTest(worldline=worldline_id):
                intervention_path = ROOT / "interventions" / f"{worldline_id}.json"
                self.assertTrue(
                    intervention_path.is_file(),
                    f"Idea Builderの実装済みworldlineに対応する介入がありません: {worldline_id}",
                )
                intervention = json.loads(intervention_path.read_text(encoding="utf-8"))
                self.assertEqual(intervention["id"], worldline_id)
        # REVIEWED cards are fail-closed: merely adding an intervention JSON
        # must not publish an unverified worldline into this section.
        self.assertNotIn("contents/interventions?ref=main", script)
        self.assertNotIn("loadImplementedWorldlines", script)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotRegex(workflow, r"(?m)^\s+push:\s*$")

    def test_colab_notebook_is_valid_json_without_embedded_credentials(self) -> None:
        notebook_path = ROOT / "notebooks/validate-worldline.ipynb"
        content = notebook_path.read_text(encoding="utf-8")
        notebook = json.loads(content)
        self.assertEqual(notebook["nbformat"], 4)
        self.assertNotIn("OPENAI_API_KEY", content)
        self.assertNotRegex(content, r"gh[pousr]_[A-Za-z0-9_]{20,}")
        self.assertIn('parent.get(\\"full_name\\")', content)
        self.assertIn("nexus-ai-2045/fiction-forksの公開fork", content)


if __name__ == "__main__":
    unittest.main()
