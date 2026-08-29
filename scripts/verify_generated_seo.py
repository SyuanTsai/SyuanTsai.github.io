#!/usr/bin/env python3
"""Verify generated post Title, Description, and Canonical URL metadata."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from validate_posts import discover_markdown, parse_front_matter, parse_scalar, post_output_url


class HeadMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_parts: list[str] = []
        self.descriptions: list[str] = []
        self.canonicals: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): value or "" for name, value in attrs}
        if tag.lower() == "title":
            self.in_title = True
        elif tag.lower() == "meta" and attributes.get("name", "").lower() == "description":
            self.descriptions.append(attributes.get("content", "").strip())
        elif tag.lower() == "link":
            rel_values = attributes.get("rel", "").lower().split()
            if "canonical" in rel_values:
                self.canonicals.append(attributes.get("href", "").strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())


def read_site_url(config_path: Path) -> str:
    for line in config_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^url:\s*(.+?)\s*(?:#.*)?$", line)
        if match:
            return str(parse_scalar(match.group(1))).rstrip("/")
    raise ValueError("_config.yml 缺少 `url`")


def output_file_for_url(site_directory: Path, url: str) -> Path:
    relative = url.lstrip("/")
    if not relative or relative.endswith("/"):
        relative += "index.html"
    return site_directory / relative


def verify_post(document_path: Path, root: Path, site_directory: Path, site_url: str) -> list[str]:
    document = parse_front_matter(document_path)
    output_url = post_output_url(document)
    output_path = output_file_for_url(site_directory, output_url)
    relative_source = document_path.relative_to(root)
    errors: list[str] = []

    if not output_path.is_file():
        return [f"{relative_source}: 找不到建置輸出 `{output_path.relative_to(root)}`"]

    parser = HeadMetadataParser()
    parser.feed(output_path.read_text(encoding="utf-8"))

    expected_title = str(document.fields["title"])
    expected_description = " ".join(str(document.fields["description"]).split())
    expected_canonical = site_url + output_url

    if not parser.title or expected_title not in parser.title:
        errors.append(f"{relative_source}: `<title>` 未包含文章標題 `{expected_title}`")
    if parser.descriptions != [expected_description]:
        errors.append(
            f"{relative_source}: 必須產生一個與 Front Matter 相同的 Description；實際為 {parser.descriptions!r}"
        )
    if parser.canonicals != [expected_canonical]:
        errors.append(
            f"{relative_source}: Canonical 應為 `{expected_canonical}`；實際為 {parser.canonicals!r}"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_directory", nargs="?", type=Path, default=Path("_site"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)

    root = args.root.resolve()
    site_directory = (root / args.site_directory).resolve() if not args.site_directory.is_absolute() else args.site_directory.resolve()
    try:
        site_url = read_site_url(root / "_config.yml")
    except ValueError as error:
        print(f"SEO verification failed: {error}", file=sys.stderr)
        return 1

    errors: list[str] = []
    post_paths = discover_markdown(root / "_posts")
    for post_path in post_paths:
        errors.extend(verify_post(post_path, root, site_directory, site_url))

    if errors:
        print("SEO verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Verified Title, Description, and Canonical URL for {len(post_paths)} generated posts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
