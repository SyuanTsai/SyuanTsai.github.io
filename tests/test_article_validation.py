from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_posts import parse_front_matter, post_output_url, validate_document  # noqa: E402
from verify_generated_seo import HeadMetadataParser, verify_post  # noqa: E402


class ArticleValidationTests(unittest.TestCase):
    def write_document(self, root: Path, relative_path: str, content: str) -> Path:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
        return path

    def test_parses_inline_lists_and_nested_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "assets/images/posts/example/cover.svg"
            image.parent.mkdir(parents=True)
            image.write_text("<svg/>", encoding="utf-8")
            path = self.write_document(
                root,
                "_posts/2026-08-29-valid-post.markdown",
                """
                ---
                title: "Valid post"
                date: 2026-08-29
                description: "A complete description."
                categories: [Code, Review]
                tags:
                  - testing
                  - jekyll
                image:
                  path: /assets/images/posts/example/cover.svg
                  alt: "Request flow"
                ---

                ## Result

                ```text
                ok
                ```
                """,
            )

            document = parse_front_matter(path)

            self.assertEqual(["Code", "Review"], document.fields["categories"])
            self.assertEqual(["testing", "jekyll"], document.fields["tags"])
            self.assertEqual("Request flow", document.fields["image"]["alt"])
            self.assertEqual([], validate_document(document, "post", root))

    def test_missing_description_returns_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_document(
                root,
                "_posts/2026-08-29-missing-description.markdown",
                """
                ---
                title: "Missing description"
                date: 2026-08-29
                ---

                ## Result
                """,
            )
            errors = validate_document(parse_front_matter(path), "post", root)

            self.assertTrue(any("description" in error and "缺少必要" in error for error in errors))

    def test_filename_and_front_matter_date_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_document(
                root,
                "_posts/2026-08-28-wrong-date.markdown",
                """
                ---
                title: "Wrong date"
                date: 2026-08-29
                description: "The dates do not match."
                ---

                ## Result
                """,
            )
            errors = validate_document(parse_front_matter(path), "post", root)

            self.assertIn("檔名日期必須與 Front Matter `date` 相同", errors)

    def test_draft_cannot_be_stored_as_published_post(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_document(
                root,
                "_posts/2026-08-29-hidden-post.markdown",
                """
                ---
                title: "Hidden post"
                date: 2026-08-29
                description: "This belongs in drafts."
                draft: true
                ---

                ## Result
                """,
            )
            errors = validate_document(parse_front_matter(path), "post", root)

            self.assertTrue(any("_drafts" in error for error in errors))

    def test_output_url_uses_categories_and_slug(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_document(
                root,
                "_posts/2026-08-29-debugging-timeouts.markdown",
                """
                ---
                title: "Debugging timeouts"
                date: 2026-08-29
                description: "A URL example."
                categories: [CSharp, HTTP]
                ---

                ## Result
                """,
            )

            self.assertEqual(
                "/csharp/http/2026/08/29/debugging-timeouts.html",
                post_output_url(parse_front_matter(path)),
            )

    def test_head_metadata_parser_reads_required_seo_elements(self) -> None:
        parser = HeadMetadataParser()
        parser.feed(
            """
            <html><head>
              <title>Article title | Site</title>
              <meta name="description" content="Article description">
              <link rel="canonical" href="https://example.com/article.html">
            </head><body></body></html>
            """
        )

        self.assertEqual("Article title | Site", parser.title)
        self.assertEqual(["Article description"], parser.descriptions)
        self.assertEqual(["https://example.com/article.html"], parser.canonicals)

    def test_verify_post_compares_generated_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = self.write_document(
                root,
                "_posts/2026-08-29-generated-metadata.markdown",
                """
                ---
                title: "Generated metadata"
                date: 2026-08-29
                description: "Metadata generated by the build."
                categories: [Code]
                ---

                ## Result
                """,
            )
            output = root / "_site/code/2026/08/29/generated-metadata.html"
            output.parent.mkdir(parents=True)
            output.write_text(
                """
                <html><head>
                  <title>Generated metadata | Site</title>
                  <meta name="description" content="Metadata generated by the build.">
                  <link rel="canonical" href="https://example.com/code/2026/08/29/generated-metadata.html">
                </head><body></body></html>
                """,
                encoding="utf-8",
            )

            errors = verify_post(post, root, root / "_site", "https://example.com")

            self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
