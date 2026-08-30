#!/usr/bin/env python3
"""Verify generated taxonomy, archive, search, and legacy redirect outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_posts import discover_markdown, parse_front_matter, post_output_url
from verify_generated_seo import output_file_for_url


def verify(root: Path, site_directory: Path) -> list[str]:
    errors: list[str] = []
    expected_search: dict[str, dict[str, object]] = {}
    expected_collection_links: dict[str, set[str]] = {
        "/categories/": set(),
        "/tags/": set(),
        "/archives/": set(),
    }

    taxonomy = json.loads((root / "_data/taxonomy.json").read_text(encoding="utf-8"))
    category_names = {entry["slug"]: entry["name"] for entry in taxonomy["categories"]}

    for post_path in discover_markdown(root / "_posts"):
        document = parse_front_matter(post_path)
        url = post_output_url(document)
        category = document.fields["categories"][0]
        tags = document.fields["tags"]
        published = str(document.fields["date"])

        expected_search[url] = {
            "title": document.fields["title"],
            "description": document.fields["description"],
            "category": category_names[category],
            "tags": tags,
            "date": published,
            "url": url,
        }

        collection_urls = [
            f"/categories/{category}/",
            *(f"/tags/{tag}/" for tag in tags),
            f"/archives/{published[:4]}/{published[5:7]}/",
        ]
        for collection_url in collection_urls:
            page_path = output_file_for_url(site_directory, collection_url)
            if not page_path.is_file():
                errors.append(f"缺少集合頁 `{collection_url}`")
                continue
            if url not in page_path.read_text(encoding="utf-8"):
                errors.append(f"集合頁 `{collection_url}` 未連回文章 `{url}`")

        for legacy_url in document.fields.get("redirect_from", []):
            redirect_path = output_file_for_url(site_directory, str(legacy_url))
            if not redirect_path.is_file():
                errors.append(f"缺少舊網址轉址 `{legacy_url}`")
                continue
            if url not in redirect_path.read_text(encoding="utf-8"):
                errors.append(f"舊網址 `{legacy_url}` 未指向 `{url}`")

    for root_url in expected_collection_links:
        if not output_file_for_url(site_directory, root_url).is_file():
            errors.append(f"缺少探索總覽 `{root_url}`")

    search_page = output_file_for_url(site_directory, "/search/")
    if not search_page.is_file():
        errors.append("缺少搜尋頁 `/search/`")

    search_path = site_directory / "search.json"
    if not search_path.is_file():
        errors.append("缺少搜尋索引 `/search.json`")
    else:
        try:
            search_entries = json.loads(search_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            errors.append(f"搜尋索引不是有效 JSON：{error}")
        else:
            actual_search = {entry.get("url"): entry for entry in search_entries}
            if actual_search != expected_search:
                errors.append("搜尋索引必須且只能包含公開文章的 title、description、category、tags、date、url")

    not_found = site_directory / "404.html"
    if not not_found.is_file() or "/search/" not in not_found.read_text(encoding="utf-8"):
        errors.append("404 頁面必須提供搜尋入口")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_directory", nargs="?", type=Path, default=Path("_site"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    site_directory = (
        (root / args.site_directory).resolve()
        if not args.site_directory.is_absolute()
        else args.site_directory.resolve()
    )

    try:
        errors = verify(root, site_directory)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError) as error:
        errors = [f"驗證失敗：{error}"]

    if errors:
        print("Content discovery verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Verified canonical articles, taxonomy, archives, search index, and legacy redirects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
