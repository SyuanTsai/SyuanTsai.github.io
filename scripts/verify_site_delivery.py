#!/usr/bin/env python3
"""Verify the production-facing GitHub Pages delivery artifacts."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse


EXPECTED_SITE_URL = "https://notes.tw-syuan.com"
REQUIRED_PLUGINS = {"jekyll-feed", "jekyll-sitemap"}
POST_FILENAME = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.(?:md|markdown)$",
    re.IGNORECASE,
)


def strip_yaml_scalar(value: str) -> str:
    value = value.split(" #", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def read_setting(config_text: str, key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.*?)\s*$")
    for line in config_text.splitlines():
        match = pattern.match(line)
        if match:
            return strip_yaml_scalar(match.group(1))
    return None


def read_plugins(config_text: str) -> set[str]:
    plugins: set[str] = set()
    in_plugins = False
    for line in config_text.splitlines():
        if line == "plugins:":
            in_plugins = True
            continue
        if not in_plugins:
            continue
        match = re.match(r"^\s{2}-\s*([^#\s]+)", line)
        if match:
            plugins.add(strip_yaml_scalar(match.group(1)))
            continue
        if line and not line.startswith((" ", "\t", "#")):
            break
    return plugins


def normalize_url(value: str) -> str:
    parsed = urlparse(value.strip())
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return f"{scheme}://{hostname}{port}{path}"


def read_front_matter_value(path: Path, key: str) -> str | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(rf"^{re.escape(key)}:\s*(.*?)\s*$", line)
        if match:
            return strip_yaml_scalar(match.group(1))
    return None


def published_post_urls(root: Path, site_url: str) -> set[str]:
    urls: set[str] = set()
    posts_directory = root / "_posts"
    if not posts_directory.is_dir():
        return urls
    for path in sorted(posts_directory.iterdir()):
        if not path.is_file():
            continue
        match = POST_FILENAME.match(path.name)
        if not match:
            continue
        if (read_front_matter_value(path, "draft") or "").lower() == "true":
            continue
        permalink = read_front_matter_value(path, "permalink")
        if permalink:
            output_path = permalink if permalink.startswith("/") else f"/{permalink}"
        else:
            parts = match.groupdict()
            output_path = "/{year}/{month}/{day}/{slug}.html".format(**parts)
        urls.add(normalize_url(site_url + output_path))
    return urls


def xml_values(path: Path, element_name: str, attribute: str | None = None) -> set[str]:
    root = ET.parse(path).getroot()
    values: set[str] = set()
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != element_name:
            continue
        value = element.attrib.get(attribute, "") if attribute else (element.text or "")
        if value.strip():
            values.add(normalize_url(value))
    return values


def verify_site_delivery(root: Path, site_directory: Path) -> list[str]:
    errors: list[str] = []
    config_path = root / "_config.yml"
    source_cname_path = root / "CNAME"
    built_cname_path = site_directory / "CNAME"

    if not config_path.is_file():
        return ["找不到 `_config.yml`"]
    config_text = config_path.read_text(encoding="utf-8")
    site_url = read_setting(config_text, "url") or ""
    baseurl = read_setting(config_text, "baseurl")
    lang = read_setting(config_text, "lang") or ""
    title = read_setting(config_text, "title") or ""
    description = read_setting(config_text, "description")

    if normalize_url(site_url) != normalize_url(EXPECTED_SITE_URL):
        errors.append(f"`url` 必須是 `{EXPECTED_SITE_URL}`；實際為 `{site_url}`")
    if baseurl not in {"", None}:
        errors.append(f"自訂根網域部署的 `baseurl` 必須為空；實際為 `{baseurl}`")
    if lang.lower() != "zh-tw":
        errors.append(f"`lang` 必須是 `zh-TW`；實際為 `{lang}`")
    if not title:
        errors.append("`title` 不可為空")
    if description is None:
        errors.append("`description` 不可缺少")

    missing_plugins = REQUIRED_PLUGINS - read_plugins(config_text)
    if missing_plugins:
        errors.append("缺少必要 Jekyll plugin：" + ", ".join(sorted(missing_plugins)))

    if not source_cname_path.is_file():
        errors.append("來源根目錄缺少 `CNAME`")
        source_cname = ""
    else:
        source_cname = source_cname_path.read_text(encoding="utf-8").strip()
        if source_cname.lower() != "notes.tw-syuan.com":
            errors.append(f"`CNAME` 必須是 `Notes.Tw-Syuan.com`；實際為 `{source_cname}`")

    if not built_cname_path.is_file():
        errors.append("建置輸出缺少 `CNAME`，部署可能覆寫自訂網域")
    elif built_cname_path.read_text(encoding="utf-8").strip().lower() != source_cname.lower():
        errors.append("建置輸出的 `CNAME` 與來源不一致")

    sitemap_path = site_directory / "sitemap.xml"
    feed_path = site_directory / "feed.xml"
    homepage_path = site_directory / "index.html"
    post_urls = published_post_urls(root, site_url or EXPECTED_SITE_URL)

    if not sitemap_path.is_file():
        errors.append("建置輸出缺少 `sitemap.xml`")
    else:
        try:
            sitemap_urls = xml_values(sitemap_path, "loc")
            missing_posts = post_urls - sitemap_urls
            if missing_posts:
                errors.append("Sitemap 缺少文章網址：" + ", ".join(sorted(missing_posts)))
        except ET.ParseError as error:
            errors.append(f"`sitemap.xml` 不是有效 XML：{error}")

    if not feed_path.is_file():
        errors.append("建置輸出缺少 `feed.xml`")
    else:
        try:
            feed_links = xml_values(feed_path, "link", "href")
            expected_feed_url = normalize_url((site_url or EXPECTED_SITE_URL) + "/feed.xml")
            if expected_feed_url not in feed_links:
                errors.append(f"Feed 缺少正式 self link `{expected_feed_url}`")
            if post_urls and not (post_urls & feed_links):
                errors.append("Feed 未包含任何已發布文章網址")
        except ET.ParseError as error:
            errors.append(f"`feed.xml` 不是有效 XML：{error}")

    if not homepage_path.is_file():
        errors.append("建置輸出缺少首頁 `index.html`")
    else:
        homepage = homepage_path.read_text(encoding="utf-8")
        if "application/atom+xml" not in homepage or "/feed.xml" not in homepage:
            errors.append("首頁 `<head>` 缺少 Feed discovery link")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_directory", nargs="?", type=Path, default=Path("_site"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)

    root = args.root.resolve()
    site_directory = args.site_directory
    if not site_directory.is_absolute():
        site_directory = (root / site_directory).resolve()

    errors = verify_site_delivery(root, site_directory)
    if errors:
        print("Site delivery verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Verified production URL, CNAME, Sitemap, Feed, and Feed discovery metadata.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
