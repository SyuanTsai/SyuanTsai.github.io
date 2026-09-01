from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_quality_baseline import (
    collect_external_urls,
    verify_lighthouse_accessibility,
    verify_quality_baseline,
)


class QualityBaselineTests(unittest.TestCase):
    def page(self, canonical: str, body: str = "") -> str:
        return f'''<!doctype html><html><head>
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="Title">
<meta property="og:description" content="Description">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<script type="application/ld+json">{json.dumps({"@type": "WebPage", "url": canonical})}</script>
</head><body>{body}</body></html>'''

    def create_fixture(self, root: Path) -> Path:
        site = root / "_site"
        paths = {
            "index.html": "https://notes.tw-syuan.com/",
            "articles/index.html": "https://notes.tw-syuan.com/articles/",
            "about/index.html": "https://notes.tw-syuan.com/about/",
            "404.html": "https://notes.tw-syuan.com/404.html",
            "2026/09/01/example.html": "https://notes.tw-syuan.com/2026/09/01/example.html",
        }
        for relative, canonical in paths.items():
            path = site / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            body = '<a href="/articles/#list">Articles</a><img src="/assets/logo.svg" alt="Logo">' if relative == "index.html" else ""
            if relative == "articles/index.html":
                body = '<section id="list"><a href="https://example.com/docs">Docs</a></section>'
            path.write_text(self.page(canonical, body), encoding="utf-8")
        (site / "assets").mkdir()
        (site / "assets" / "logo.svg").write_text("<svg></svg>", encoding="utf-8")
        (site / "robots.txt").write_text(
            "User-agent: *\nAllow: /\nSitemap: https://notes.tw-syuan.com/sitemap.xml\n",
            encoding="utf-8",
        )
        (root / "docs").mkdir()
        (root / "docs" / "architecture-decision.md").write_text(
            "# ADR: Keep Jekyll\n## 狀態\n## 背景\n## 決策\n## 影響\n",
            encoding="utf-8",
        )
        (root / "docs" / "site-delivery.md").write_text(
            "# Delivery\n## 回復已上線的錯誤內容\n",
            encoding="utf-8",
        )
        return site

    def test_valid_quality_baseline_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            site = self.create_fixture(root)
            self.assertEqual([], verify_quality_baseline(root, site))

    def test_broken_internal_link_and_fragment_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            site = self.create_fixture(root)
            (site / "index.html").write_text(
                self.page(
                    "https://notes.tw-syuan.com/",
                    '<a href="/missing/">Missing</a><a href="/articles/#missing">Anchor</a>',
                ),
                encoding="utf-8",
            )
            errors = verify_quality_baseline(root, site)
            self.assertTrue(any("站內連結不存在" in error for error in errors))
            self.assertTrue(any("錨點不存在" in error for error in errors))

    def test_encoded_parent_traversal_cannot_escape_site_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            site = self.create_fixture(root)
            (root / "outside.html").write_text("outside", encoding="utf-8")
            (site / "index.html").write_text(
                self.page(
                    "https://notes.tw-syuan.com/",
                    '<a href="/%2e%2e/outside.html">Outside</a>',
                ),
                encoding="utf-8",
            )
            errors = verify_quality_baseline(root, site)
            self.assertTrue(any("站內連結不存在" in error for error in errors))

    def test_missing_open_graph_and_invalid_json_ld_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            site = self.create_fixture(root)
            (site / "about" / "index.html").write_text(
                '<link rel="canonical" href="https://notes.tw-syuan.com/about/">'
                '<script type="application/ld+json">{invalid}</script>',
                encoding="utf-8",
            )
            errors = verify_quality_baseline(root, site)
            self.assertTrue(any("og:title" in error for error in errors))
            self.assertTrue(any("JSON-LD 無效" in error for error in errors))

    def test_robots_and_document_sections_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            site = self.create_fixture(root)
            (site / "robots.txt").unlink()
            (root / "docs" / "architecture-decision.md").write_text("# ADR: Incomplete\n", encoding="utf-8")
            errors = verify_quality_baseline(root, site)
            self.assertIn("建置輸出缺少 `robots.txt`", errors)
            self.assertTrue(any("缺少必要章節" in error for error in errors))

    def test_external_links_are_collected_without_becoming_internal_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            site = self.create_fixture(root)
            self.assertEqual(["https://example.com/docs"], collect_external_urls(site))
            self.assertEqual([], verify_quality_baseline(root, site))

    def test_lighthouse_accessibility_passes_without_failed_audits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            report = Path(temporary_directory) / "lighthouse.json"
            report.write_text(
                json.dumps(
                    {
                        "categories": {"accessibility": {"auditRefs": [{"id": "image-alt"}]}},
                        "audits": {"image-alt": {"score": 1, "title": "Images have alt text"}},
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual([], verify_lighthouse_accessibility(report))

    def test_lighthouse_accessibility_reports_failed_audits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            report = Path(temporary_directory) / "lighthouse.json"
            report.write_text(
                json.dumps(
                    {
                        "categories": {"accessibility": {"auditRefs": [{"id": "color-contrast"}]}},
                        "audits": {"color-contrast": {"score": 0, "title": "Colors have sufficient contrast"}},
                    }
                ),
                encoding="utf-8",
            )
            errors = verify_lighthouse_accessibility(report)
            self.assertEqual(1, len(errors))
            self.assertIn("color-contrast", errors[0])


if __name__ == "__main__":
    unittest.main()
