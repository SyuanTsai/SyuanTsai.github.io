from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_posts import (  # noqa: E402
    parse_front_matter,
    post_output_url,
    validate_article_structure,
    validate_document,
)
from verify_generated_seo import HeadMetadataParser, verify_post  # noqa: E402
from verify_unlisted_preview import verify as verify_unlisted_preview  # noqa: E402


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

                ![Request flow](/assets/images/posts/example/cover.svg){: width="960" height="360" }

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

    def test_body_image_requires_intrinsic_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_document(
                root,
                "_posts/2026-08-29-image-without-size.markdown",
                """
                ---
                title: "Image without size"
                date: 2026-08-29
                description: "The body image does not reserve layout space."
                ---

                ## Result

                ![Request flow](/assets/images/posts/example/request-flow.svg)
                """,
            )

            errors = validate_document(parse_front_matter(path), "post", root)

            self.assertTrue(any("原始像素尺寸" in error for error in errors))

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

    def test_article_structure_accepts_opening_citations_and_update_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_document(
                root,
                "article-template-preview.markdown",
                """
                ---
                title: "Article structure"
                date: 2026-08-29
                last_modified_at: 2026-08-30
                description: "A complete article structure."
                ---

                Opening context with a source.[^official-source]

                ## Topic-specific section

                Main content.

                ## 參考資料

                [^official-source]: [Official source](https://example.com/official) — Publisher

                1. References are generated here
                {:footnotes}

                ## 更新紀錄

                | 日期 | 更新內容 |
                | --- | --- |
                | 2026-08-29 | 初版發布 |
                | 2026-08-30 | 補充官方來源 |
                """,
            )

            errors = validate_article_structure(
                parse_front_matter(path),
                require_citation=True,
            )

            self.assertEqual([], errors)

    def test_article_structure_requires_opening_and_final_section_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_document(
                root,
                "invalid-structure.markdown",
                """
                ---
                title: "Invalid structure"
                date: 2026-08-29
                last_modified_at: 2026-08-29
                description: "The sections are out of order."
                ---

                ## 參考資料

                ## Topic after references

                ## 更新紀錄

                | 日期 | 更新內容 |
                | --- | --- |
                | 2026-08-29 | 初版發布 |
                """,
            )

            errors = validate_article_structure(parse_front_matter(path))

            self.assertTrue(any("起頭文字" in error for error in errors))
            self.assertTrue(any("最後兩個 H2" in error for error in errors))

    def test_article_structure_requires_latest_history_date_to_match_front_matter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_document(
                root,
                "wrong-modified-date.markdown",
                """
                ---
                title: "Wrong modified date"
                date: 2026-08-29
                last_modified_at: 2026-08-29
                description: "The latest dates do not match."
                ---

                Opening context.

                ## Topic

                Main content.

                ## 參考資料

                ## 更新紀錄

                | 日期 | 更新內容 |
                | --- | --- |
                | 2026-08-29 | 初版發布 |
                | 2026-08-30 | 補充內容 |
                """,
            )

            errors = validate_article_structure(parse_front_matter(path))

            self.assertIn("`last_modified_at` 必須與更新紀錄的最新日期相同", errors)

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

    def test_unlisted_preview_verifier_accepts_noindex_and_no_public_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            preview = site / "preview/article-template/index.html"
            preview.parent.mkdir(parents=True)
            preview.write_text(
                """
                <html><head>
                  <meta name="robots" content="noindex, nofollow, noarchive">
                </head><body>
                  <h1>出版文章範本預覽</h1>
                  <p>
                    Claim<a class="footnote" href="#fn:a">1</a>
                    <a class="footnote" href="#fn:b">2</a>
                    <a class="footnote" href="#fn:c">3</a>
                  </p>
                  <h2>參考資料</h2>
                  <div class="footnotes" role="doc-endnotes">
                    <a class="reversefootnote" href="#fnref:a">back</a>
                    <a class="reversefootnote" href="#fnref:b">back</a>
                    <a class="reversefootnote" href="#fnref:c">back</a>
                  </div>
                  <h2>更新紀錄</h2>
                  <table class="update-history"><tbody><tr><td>2026-08-30</td><td>初版發布</td></tr></tbody></table>
                  <img src="/assets/images/posts/article-format-example/request-flow.svg"
                       alt="HTTP 請求處理流程" width="960" height="360">
                </body></html>
                """,
                encoding="utf-8",
            )
            (site / "index.html").write_text("<html><body>Home</body></html>", encoding="utf-8")

            self.assertEqual([], verify_unlisted_preview(site))


if __name__ == "__main__":
    unittest.main()
