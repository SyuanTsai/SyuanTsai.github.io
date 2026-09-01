from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_site_delivery import verify_site_delivery


class SiteDeliveryVerificationTests(unittest.TestCase):
    def create_fixture(self, directory: Path) -> tuple[Path, Path]:
        root = directory
        site = root / "_site"
        (root / "_posts").mkdir()
        site.mkdir()
        (root / "_config.yml").write_text(
            """lang: \"zh-tw\"
title: SyuanTsai's Blog
description: Personal work notes.
baseurl: \"\"
url: \"https://notes.tw-syuan.com\"
plugins:
  - jekyll-feed
  - jekyll-sitemap
""",
            encoding="utf-8",
        )
        (root / "CNAME").write_text("Notes.Tw-Syuan.com\n", encoding="utf-8")
        (site / "CNAME").write_text("Notes.Tw-Syuan.com\n", encoding="utf-8")
        (root / "_posts" / "2026-09-01-delivery-check.markdown").write_text(
            "---\ntitle: Delivery check\ndate: 2026-09-01\n---\n",
            encoding="utf-8",
        )
        post_url = "https://notes.tw-syuan.com/2026/09/01/delivery-check.html"
        (site / "sitemap.xml").write_text(
            f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{post_url}</loc></url></urlset>',
            encoding="utf-8",
        )
        (site / "feed.xml").write_text(
            f'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><link rel="self" href="https://notes.tw-syuan.com/feed.xml"/><entry><link href="{post_url}"/></entry></feed>''',
            encoding="utf-8",
        )
        (site / "index.html").write_text(
            '<link rel="alternate" type="application/atom+xml" href="https://notes.tw-syuan.com/feed.xml">',
            encoding="utf-8",
        )
        return root, site

    def test_valid_delivery_artifacts_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, site = self.create_fixture(Path(temporary_directory))
            self.assertEqual([], verify_site_delivery(root, site))

    def test_missing_feed_and_built_cname_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, site = self.create_fixture(Path(temporary_directory))
            (site / "feed.xml").unlink()
            (site / "CNAME").unlink()
            errors = verify_site_delivery(root, site)
            self.assertTrue(any("feed.xml" in error for error in errors))
            self.assertTrue(any("建置輸出缺少 `CNAME`" in error for error in errors))

    def test_sitemap_must_include_published_posts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root, site = self.create_fixture(Path(temporary_directory))
            (site / "sitemap.xml").write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
                encoding="utf-8",
            )
            errors = verify_site_delivery(root, site)
            self.assertTrue(any("Sitemap 缺少文章網址" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
