#!/usr/bin/env python3
"""Verify the rendered article-template preview stays unlisted and noindex."""

from __future__ import annotations

import argparse
import re
from html.parser import HTMLParser
from pathlib import Path


PREVIEW_URL = "/preview/article-template/"


class PreviewHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.robots: list[str] = []
        self.footnote_links = 0
        self.reverse_footnote_links = 0
        self.has_footnote_list = False
        self.has_update_history_table = False
        self.images: list[dict[str, str]] = []
        self._in_h1 = False
        self.h1_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        classes = set(attributes.get("class", "").split())
        if tag == "meta" and attributes.get("name", "").lower() == "robots":
            self.robots.append(attributes.get("content", ""))
        if tag == "a" and "footnote" in classes:
            self.footnote_links += 1
        if tag == "a" and "reversefootnote" in classes:
            self.reverse_footnote_links += 1
        if "footnotes" in classes or attributes.get("role") == "doc-endnotes":
            self.has_footnote_list = True
        if tag == "table" and "update-history" in classes:
            self.has_update_history_table = True
        if tag == "img":
            self.images.append(attributes)
        if tag == "h1":
            self._in_h1 = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._in_h1 = False

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self.h1_parts.append(data)

    @property
    def h1(self) -> str:
        return " ".join(part.strip() for part in self.h1_parts if part.strip())


def verify(site: Path) -> list[str]:
    errors: list[str] = []
    preview = site / "preview/article-template/index.html"
    if not preview.is_file():
        return [f"找不到未列出預覽輸出：{preview}"]

    html = preview.read_text(encoding="utf-8")
    parser = PreviewHtmlParser()
    parser.feed(html)

    if parser.h1 != "出版文章範本預覽":
        errors.append(f"預覽頁 H1 不正確：{parser.h1 or '(空白)'}")

    if len(parser.robots) != 1:
        errors.append("預覽頁必須且只能輸出一個 robots meta")
    else:
        directives = {
            directive.strip().lower()
            for directive in parser.robots[0].split(",")
            if directive.strip()
        }
        if directives != {"noindex", "nofollow", "noarchive"}:
            errors.append(f"預覽頁 robots meta 不正確：{parser.robots[0]}")

    if parser.footnote_links < 3:
        errors.append("預覽頁至少需要三個句尾引用徽章")
    if not parser.has_footnote_list:
        errors.append("預覽頁缺少產生後的參考資料清單")
    if parser.reverse_footnote_links < 3:
        errors.append("預覽頁參考資料缺少返回原文連結")
    if not parser.has_update_history_table:
        errors.append("預覽頁更新紀錄表格必須具有 `update-history` class")

    request_flow_images = [
        image
        for image in parser.images
        if image.get("src", "").endswith("/assets/images/posts/article-format-example/request-flow.svg")
    ]
    if len(request_flow_images) != 1:
        errors.append("預覽頁必須且只能輸出一張 HTTP 請求處理流程圖片")
    elif (
        request_flow_images[0].get("width") != "960"
        or request_flow_images[0].get("height") != "360"
    ):
        errors.append("預覽頁流程圖片必須輸出原始尺寸 width=960、height=360")

    footnotes = re.search(
        r"<(?:div|ol)\b[^>]*(?:class=[\"'][^\"']*\bfootnotes\b|role=[\"']doc-endnotes[\"'])",
        html,
        flags=re.IGNORECASE,
    )
    update_heading = re.search(r"<h2\b[^>]*>\s*更新紀錄\s*</h2>", html, flags=re.IGNORECASE)
    if footnotes and update_heading and footnotes.start() > update_heading.start():
        errors.append("參考資料清單必須出現在更新紀錄之前")
    if update_heading is None:
        errors.append("預覽頁缺少更新紀錄 H2")

    link_pattern = re.compile(
        r"href=[\"'](?:https://notes\.tw-syuan\.com)?/preview/article-template/?[\"']",
        flags=re.IGNORECASE,
    )
    for html_path in sorted(site.rglob("*.html")):
        if html_path == preview:
            continue
        if link_pattern.search(html_path.read_text(encoding="utf-8")):
            errors.append(f"公開頁面連到未列出預覽：{html_path.relative_to(site)}")

    sitemap = site / "sitemap.xml"
    if sitemap.is_file() and PREVIEW_URL in sitemap.read_text(encoding="utf-8"):
        errors.append("sitemap.xml 不可包含未列出預覽網址")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path, nargs="?", default=Path("_site"))
    args = parser.parse_args()

    errors = verify(args.site.resolve())
    if errors:
        print("Unlisted preview verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Verified unlisted article template preview at {PREVIEW_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
