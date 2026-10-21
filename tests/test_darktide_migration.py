"""Small migration-contract tests; no dialogue content fixtures."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from migrate_darktide_skills import validate_routes, redirect_html, apply_migration

class MigrationTests(unittest.TestCase):
    def route(self):
        return {"old": "/darktide/skills/veteran/example/", "new": "https://darktide.tw-syuan.com/skills/veteran/example_id/", "content_key": "veteran/example_id", "kind": "skill"}

    # Scenario: an untrusted map names an unrelated file or target host.
    # Purpose: keep migration writes inside the exact skill route contract.
    def test_UnitT10_rejects_outside_routes_and_duplicate_sources(self):
        for change in ({"old": "/darktide/en/example/"}, {"old": "/darktide/skills/veteran/../example/"}, {"new": "https://example.invalid/skills/veteran/example_id/"}, {"new": "https://darktide.tw-syuan.com/skills/veteran/wrong/"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_routes([dict(self.route(), **change)])
        with self.assertRaises(ValueError):
            validate_routes([self.route(), self.route()])

    # Scenario: a generated contract accidentally loses its entire route list.
    # Purpose: fail closed instead of silently permitting retired prose to return.
    def test_UnitT15_empty_migration_contract_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_routes([])

    # Scenario: a verified skill has an explicit destination.
    # Purpose: offer a no-JavaScript route and prevent indexing duplicate prose.
    def test_UnitT20_redirect_has_exact_canonical_and_manual_fallback(self):
        output = redirect_html(self.route()).decode()
        self.assertIn('name="robots" content="noindex,follow"', output)
        self.assertIn('rel="canonical" href="' + self.route()["new"] + '"', output)
        self.assertIn('http-equiv="refresh"', output)
        self.assertIn('location.replace(', output)
        self.assertIn('href="' + self.route()["new"] + '"', output)
        self.assertNotIn('nofollow', output)

    # Scenario: generated old prose reappears before maintenance reruns.
    # Purpose: restore redirect deterministically and preserve unrelated supplement text.
    def test_UnitT30_overlay_is_idempotent_and_preserves_supplement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "docs/darktide-migration/routes.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({"routes": [self.route()]}))
            page = root / self.route()["old"].strip("/") / "index.html"
            page.parent.mkdir(parents=True)
            page.write_text("old prose")
            supplement = root / "darktide/skills/veteran/source-index/index.html"
            supplement.parent.mkdir(parents=True)
            supplement.write_text('<p>KEEP</p><a href="' + self.route()["old"] + '">example</a>')
            sitemap = root / "darktide/sitemap-001.xml"
            sitemap.write_text('<urlset><url><loc>https://notes.tw-syuan.com' + self.route()["old"] + '</loc></url><url><loc>https://notes.tw-syuan.com/darktide/</loc></url></urlset>')
            apply_migration(root)
            first = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            apply_migration(root)
            self.assertEqual(first, {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()})
            self.assertIn("KEEP", supplement.read_text())
            self.assertIn(self.route()["new"], supplement.read_text())
            self.assertNotIn(self.route()["old"], sitemap.read_text())
            self.assertIn("https://notes.tw-syuan.com/darktide/", sitemap.read_text())
