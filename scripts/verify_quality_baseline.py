#!/usr/bin/env python3
"""Verify deterministic site quality rules and optionally report external links."""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen


EXPECTED_SITE_URL = "https://notes.tw-syuan.com"
EXPECTED_HOST = urlparse(EXPECTED_SITE_URL).hostname
REQUIRED_METADATA_PATHS = (
    "index.html",
    "articles/index.html",
    "about/index.html",
    "404.html",
)
POST_OUTPUT_PATTERN = re.compile(r"^\d{4}/\d{2}/\d{2}/[^/]+\.html$")
REQUIRED_DOCUMENT_HEADINGS = {
    "docs/architecture-decision.md": (
        "# ADR:",
        "## 狀態",
        "## 背景",
        "## 決策",
        "## 影響",
    ),
    "docs/site-delivery.md": ("## 回復已上線的錯誤內容",),
}
REFERENCE_ATTRIBUTES = ("href", "src", "action", "poster")


class SiteHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []
        self.anchors: set[str] = set()
        self.canonicals: list[str] = []
        self.open_graph: dict[str, list[str]] = {}
        self.json_ld_blocks: list[str] = []
        self._json_ld_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): value or "" for name, value in attrs}
        anchor = attributes.get("id") or attributes.get("name")
        if anchor:
            self.anchors.add(anchor)

        for attribute in REFERENCE_ATTRIBUTES:
            value = attributes.get(attribute, "").strip()
            if value:
                self.references.append(value)
        if attributes.get("srcset"):
            for candidate in attributes["srcset"].split(","):
                value = candidate.strip().split()[0] if candidate.strip() else ""
                if value:
                    self.references.append(value)

        if tag.lower() == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonicals.append(attributes.get("href", "").strip())
        if tag.lower() == "meta":
            property_name = attributes.get("property", "").lower()
            if property_name.startswith("og:"):
                self.open_graph.setdefault(property_name, []).append(attributes.get("content", "").strip())
        if tag.lower() == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._json_ld_parts is not None:
            self.json_ld_blocks.append("".join(self._json_ld_parts).strip())
            self._json_ld_parts = None


def parse_html(path: Path) -> SiteHTMLParser:
    parser = SiteHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def web_path_for_file(relative_path: Path) -> str:
    value = relative_path.as_posix()
    if value == "index.html":
        return "/"
    if value.endswith("/index.html"):
        return "/" + value[: -len("index.html")]
    return "/" + value


def expected_canonical(relative_path: Path) -> str:
    return EXPECTED_SITE_URL + web_path_for_file(relative_path)


def metadata_pages(site_directory: Path) -> list[Path]:
    paths = {Path(value) for value in REQUIRED_METADATA_PATHS}
    for path in site_directory.rglob("*.html"):
        relative = path.relative_to(site_directory)
        if POST_OUTPUT_PATTERN.match(relative.as_posix()):
            paths.add(relative)
    return sorted(paths)


def find_json_ld_url(value: object) -> set[str]:
    urls: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"url", "@id"} and isinstance(child, str):
                urls.add(child)
            urls.update(find_json_ld_url(child))
    elif isinstance(value, list):
        for child in value:
            urls.update(find_json_ld_url(child))
    return urls


def verify_metadata(site_directory: Path) -> list[str]:
    errors: list[str] = []
    for relative in metadata_pages(site_directory):
        path = site_directory / relative
        if not path.is_file():
            errors.append(f"缺少主要頁面 `{relative.as_posix()}`")
            continue
        parser = parse_html(path)
        canonical = expected_canonical(relative)
        label = relative.as_posix()
        if parser.canonicals != [canonical]:
            errors.append(f"{label}: Canonical 應為 `{canonical}`；實際為 {parser.canonicals!r}")
        for property_name in ("og:title", "og:description", "og:url", "og:type"):
            values = parser.open_graph.get(property_name, [])
            if len(values) != 1 or not values[0]:
                errors.append(f"{label}: 必須有一個非空的 `{property_name}`")
        if parser.open_graph.get("og:url") != [canonical]:
            errors.append(f"{label}: `og:url` 必須與 Canonical 相同")

        parsed_blocks: list[object] = []
        for block in parser.json_ld_blocks:
            try:
                parsed_blocks.append(json.loads(block))
            except json.JSONDecodeError as error:
                errors.append(f"{label}: JSON-LD 無效：{error}")
        if not parsed_blocks:
            errors.append(f"{label}: 缺少有效 JSON-LD")
        elif canonical not in set().union(*(find_json_ld_url(block) for block in parsed_blocks)):
            errors.append(f"{label}: JSON-LD 未包含 Canonical `{canonical}`")

        for image_url in parser.open_graph.get("og:image", []):
            parsed_image = urlparse(image_url)
            if parsed_image.scheme != "https" or not parsed_image.netloc:
                errors.append(f"{label}: `og:image` 必須使用完整 HTTPS 網址；實際為 `{image_url}`")
    return errors


def candidate_output_paths(site_directory: Path, path: str) -> list[Path]:
    decoded = unquote(path)
    relative = PurePosixPath(decoded.lstrip("/"))
    if "\\" in decoded or ".." in relative.parts:
        return []
    candidate = site_directory.joinpath(*relative.parts)
    candidates = [candidate]
    if path.endswith("/") or not relative.parts:
        candidates = [candidate / "index.html"]
    elif not Path(relative.name).suffix:
        candidates.extend((candidate / "index.html", candidate.with_suffix(".html")))
    return candidates


def collect_site_documents(site_directory: Path) -> dict[Path, SiteHTMLParser]:
    return {
        path.relative_to(site_directory): parse_html(path)
        for path in sorted(site_directory.rglob("*.html"))
    }


def resolve_reference(source_relative: Path, reference: str) -> tuple[str, str] | None:
    if reference.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None
    source_url = EXPECTED_SITE_URL + web_path_for_file(source_relative)
    parsed = urlparse(urljoin(source_url, reference))
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.hostname != EXPECTED_HOST:
        return None
    return parsed.path or "/", unquote(parsed.fragment)


def verify_internal_references(site_directory: Path) -> list[str]:
    errors: list[str] = []
    documents = collect_site_documents(site_directory)
    anchors_by_path = {relative: parser.anchors for relative, parser in documents.items()}
    for source_relative, parser in documents.items():
        for reference in parser.references:
            resolved = resolve_reference(source_relative, reference)
            if resolved is None:
                continue
            target_path, fragment = resolved
            candidates = candidate_output_paths(site_directory, target_path)
            existing = next((candidate for candidate in candidates if candidate.is_file()), None)
            if existing is None:
                errors.append(f"{source_relative.as_posix()}: 站內連結不存在 `{reference}`")
                continue
            if fragment and existing.suffix.lower() == ".html":
                relative_target = existing.relative_to(site_directory)
                if fragment not in anchors_by_path.get(relative_target, set()):
                    errors.append(f"{source_relative.as_posix()}: 錨點不存在 `{reference}`")
    return errors


def verify_robots(site_directory: Path) -> list[str]:
    path = site_directory / "robots.txt"
    if not path.is_file():
        return ["建置輸出缺少 `robots.txt`"]
    lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")}
    required = {
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {EXPECTED_SITE_URL}/sitemap.xml",
    }
    missing = required - lines
    return ["`robots.txt` 缺少：" + ", ".join(sorted(missing))] if missing else []


def verify_documents(root: Path) -> list[str]:
    errors: list[str] = []
    for relative, headings in REQUIRED_DOCUMENT_HEADINGS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"缺少必要文件 `{relative}`")
            continue
        content = path.read_text(encoding="utf-8")
        for heading in headings:
            if heading not in content:
                errors.append(f"{relative}: 缺少必要章節 `{heading}`")
    return errors


def collect_external_urls(site_directory: Path) -> list[str]:
    urls: set[str] = set()
    for parser in collect_site_documents(site_directory).values():
        for reference in parser.references:
            parsed = urlparse(reference)
            if parsed.scheme in {"http", "https"} and parsed.hostname != EXPECTED_HOST:
                urls.add(reference.split("#", 1)[0])
    return sorted(urls)


def check_external_url(url: str) -> dict[str, object]:
    headers = {"User-Agent": "SyuanNotesQualityCheck/1.0"}
    try:
        request = Request(url, headers=headers, method="HEAD")
        with urlopen(request, timeout=5) as response:
            return {"url": url, "status": response.status, "error": None}
    except HTTPError as error:
        if error.code not in {403, 405}:
            return {"url": url, "status": error.code, "error": str(error)}
    except (URLError, TimeoutError, ValueError) as error:
        return {"url": url, "status": None, "error": str(error)}

    try:
        request = Request(url, headers={**headers, "Range": "bytes=0-0"}, method="GET")
        with urlopen(request, timeout=5) as response:
            return {"url": url, "status": response.status, "error": None}
    except HTTPError as error:
        return {"url": url, "status": error.code, "error": str(error)}
    except (URLError, TimeoutError, ValueError) as error:
        return {"url": url, "status": None, "error": str(error)}


def write_external_report(site_directory: Path, output_path: Path) -> int:
    urls = collect_external_urls(site_directory)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(check_external_url, urls))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(urls)


def verify_lighthouse_accessibility(report_path: Path) -> list[str]:
    if not report_path.is_file():
        return [f"缺少 Lighthouse 報告 `{report_path}`"]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"Lighthouse 報告不是有效 JSON：{error}"]

    accessibility = report.get("categories", {}).get("accessibility", {})
    audit_references = accessibility.get("auditRefs", [])
    audits = report.get("audits", {})
    if not audit_references:
        return ["Lighthouse 報告缺少 accessibility audit references"]

    errors: list[str] = []
    for reference in audit_references:
        audit_id = reference.get("id", "")
        audit = audits.get(audit_id, {})
        if audit.get("score") != 0:
            continue
        title = audit.get("title") or audit_id
        errors.append(f"Lighthouse accessibility audit 失敗：{title} (`{audit_id}`)")
    return errors


def verify_quality_baseline(root: Path, site_directory: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(verify_robots(site_directory))
    errors.extend(verify_metadata(site_directory))
    errors.extend(verify_internal_references(site_directory))
    errors.extend(verify_documents(root))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_directory", nargs="?", type=Path, default=Path("_site"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--external-report", type=Path)
    parser.add_argument("--external-only", action="store_true")
    parser.add_argument("--lighthouse-accessibility-report", type=Path)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    site_directory = args.site_directory if args.site_directory.is_absolute() else root / args.site_directory
    if args.external_report:
        output_path = args.external_report if args.external_report.is_absolute() else root / args.external_report
        count = write_external_report(site_directory, output_path)
        print(f"Wrote report-only results for {count} external URLs to {output_path}.")
    if args.external_only:
        return 0

    errors = verify_quality_baseline(root, site_directory)
    if args.lighthouse_accessibility_report:
        report_path = args.lighthouse_accessibility_report
        if not report_path.is_absolute():
            report_path = root / report_path
        errors.extend(verify_lighthouse_accessibility(report_path))
    if errors:
        print("Quality baseline verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Verified robots, metadata, JSON-LD, internal links, assets, ADR, and rollback documentation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
