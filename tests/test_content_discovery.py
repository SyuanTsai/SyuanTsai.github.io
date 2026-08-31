from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_discovery_pages import check, expected_pages  # noqa: E402
from validate_posts import parse_front_matter, post_output_url  # noqa: E402


class ContentDiscoveryTests(unittest.TestCase):
    def test_generated_taxonomy_and_archive_pages_are_current(self) -> None:
        pages = expected_pages(ROOT)

        self.assertEqual(9, len(pages))
        self.assertEqual([], check(ROOT, pages))

    def test_every_post_has_one_date_based_canonical_url_and_legacy_redirect(self) -> None:
        expected_urls = {
            "/2022/05/11/sql-server-merge.html",
            "/2025/12/14/code-review-alignment-for-long-term-maintenance.html",
        }
        expected_redirects = {
            "_posts/2022-05-11-sql-server-merge.markdown": {
                "/mssql/2022/05/11/sql-server-merge.html",
                "/MSSQL/2022/05/11/sql-server-merge.html",
            },
            "_posts/2025-12-14-code-review-alignment-for-long-term-maintenance.markdown": {
                "/code/review/2025/12/14/Code-Review-Alignment-for-Long-Term-Maintenance.html",
                "/Code/2025/12/14/Code-Review-Alignment-for-Long-Term-Maintenance.html",
            },
        }
        actual_urls: set[str] = set()

        for path in sorted((ROOT / "_posts").glob("*.markdown")):
            document = parse_front_matter(path)
            actual_urls.add(post_output_url(document))
            self.assertEqual(1, len(document.fields["categories"]))
            self.assertGreaterEqual(len(document.fields["tags"]), 1)
            self.assertEqual(
                expected_redirects[str(path.relative_to(ROOT))],
                set(document.fields["redirect_from"]),
            )

        self.assertEqual(expected_urls, actual_urls)

    def test_search_index_source_contains_only_required_public_fields(self) -> None:
        source = (ROOT / "search.json").read_text(encoding="utf-8")
        script = (ROOT / "assets/js/search.js").read_text(encoding="utf-8")

        for field in ("title", "description", "category", "tags", "date", "url"):
            self.assertIn(f'"{field}"', source)
        self.assertIn("post.title", script)
        self.assertIn("post.description", script)
        self.assertIn("post.tags", script)
        self.assertNotIn("post.content", source)

    def test_registered_taxonomy_slugs_are_unique_and_lowercase(self) -> None:
        taxonomy = json.loads((ROOT / "_data/taxonomy.json").read_text(encoding="utf-8"))

        for group in ("categories", "tags"):
            slugs = [entry["slug"] for entry in taxonomy[group]]
            self.assertEqual(len(slugs), len(set(slugs)))
            self.assertTrue(all(slug == slug.lower() for slug in slugs))

    def test_config_uses_supported_redirect_plugin_and_taxonomy_free_permalink(self) -> None:
        config = (ROOT / "_config.yml").read_text(encoding="utf-8")

        self.assertIn("permalink: /:year/:month/:day/:title:output_ext", config)
        self.assertIn("- jekyll-redirect-from", config)
        self.assertNotIn("permalink: /:categories/", config)

    def test_published_posts_leave_phrase_wrapping_to_the_browser(self) -> None:
        required_phrases = {
            "_posts/2022-05-11-sql-server-merge.markdown": (
                "更新目標資料",
                "queued updating replication",
                "`INSERT`、`UPDATE` 與 `DELETE`",
            ),
            "_posts/2025-12-14-code-review-alignment-for-long-term-maintenance.markdown": (
                "整體程式碼健康",
                "非必要建議",
                "理解成本只會更高、風險也更大",
            ),
        }

        for relative_path, phrases in required_phrases.items():
            source = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn('class="keep-phrase"', source)
            for phrase in phrases:
                with self.subTest(post=relative_path, phrase=phrase):
                    self.assertIn(phrase, source)


if __name__ == "__main__":
    unittest.main()
