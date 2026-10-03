#!/usr/bin/env python3
"""Verify independent Darktide preview output against its source documents."""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit

from validate_posts import Document, FrontMatterError, parse_front_matter


PREVIEW_PREFIX = "/preview/darktide/"
LOCALE_LANG = {"en": "en", "zh-tw": "zh-Hant"}
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class DialogueParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text = {"bubble": [], "speaker": [], "timestamp": []}
        self.avatars: list[tuple[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.assets: list[str] = []
        self.canonicals: list[str] = []
        self.robots: list[str] = []
        self.html_lang = ""
        self.body: dict[str, str] = {}
        self.transcripts: list[str] = []
        self.sequences: list[str] = []
        self.template_count = 0
        self.script_count = 0
        self._stack: list[str] = []
        self._captures: list[tuple[str, int, list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        classes = set(values.get("class", "").split())
        if tag not in VOID_TAGS:
            self._stack.append(tag)
        for name in self.text:
            if name in classes:
                self._captures.append((name, len(self._stack), []))
        if tag == "html":
            self.html_lang = values.get("lang", "")
        elif tag == "body":
            self.body = values
        elif tag == "a":
            self.links.append(values)
        elif tag == "template":
            self.template_count += 1
        elif tag == "script":
            self.script_count += 1
        if "transcript" in classes:
            self.transcripts.append(values.get("lang", ""))
        if "message" in classes:
            self.sequences.append(values.get("data-sequence", ""))
        if tag == "img" and "avatar" in classes:
            self.avatars.append((values.get("src", ""), values.get("alt", "")))
        if tag in {"img", "script"} and values.get("src"):
            self.assets.append(values["src"])
        if tag == "link":
            relations = values.get("rel", "").lower().split()
            if "canonical" in relations:
                self.canonicals.append(values.get("href", ""))
            if "stylesheet" in relations and values.get("href"):
                self.assets.append(values["href"])
        if tag == "meta" and values.get("name", "").lower() == "robots":
            self.robots.append(values.get("content", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag not in self._stack:
            return
        depth = len(self._stack) - 1 - self._stack[::-1].index(tag)
        remaining = []
        for name, capture_depth, parts in self._captures:
            if capture_depth > depth:
                self.text[name].append("".join(parts))
            else:
                remaining.append((name, capture_depth, parts))
        self._captures = remaining
        del self._stack[depth:]

    def handle_data(self, data: str) -> None:
        for _, _, parts in self._captures:
            parts.append(data)


def parse_dialogue(markup: str) -> DialogueParser:
    parser = DialogueParser()
    parser.feed(markup)
    parser.close()
    return parser


def source_documents(root: Path) -> tuple[list[Document], list[str]]:
    paths = [root / "darktide-preview.html"]
    paths.extend(sorted((root / "darktide-preview").rglob("*.html")))
    documents = []
    errors = []
    for path in paths:
        label = path.relative_to(root).as_posix()
        try:
            documents.append(parse_front_matter(path))
        except (OSError, FrontMatterError) as error:
            errors.append(f"{label}: cannot read source: {error}")
    return documents, errors


def output_path(site: Path, permalink: str) -> Path:
    parsed = urlsplit(permalink)
    relative = PurePosixPath(unquote(parsed.path).lstrip("/"))
    if (
        parsed.scheme or parsed.netloc or parsed.query or parsed.fragment
        or not permalink.startswith(PREVIEW_PREFIX)
        or ".." in relative.parts or "\\" in parsed.path
    ):
        raise ValueError("permalink must be a local Darktide preview URL")
    path = site.joinpath(*relative.parts)
    return path / "index.html" if parsed.path.endswith("/") else path


def positive_integer(value: object) -> int | None:
    text = str(value)
    return int(text) if re.fullmatch(r"[1-9][0-9]*", text) else None


def link_path(href: str, permalink: str, site_url: str) -> str:
    if not href:
        return ""
    parsed = urlsplit(urljoin(site_url + permalink, href))
    if parsed.netloc != urlsplit(site_url).netloc:
        return ""
    return unquote(parsed.path)


def verify(site: Path, root: Path | None = None) -> list[str]:
    root = (root or Path(__file__).resolve().parents[1]).resolve()
    site = site.resolve()
    documents, errors = source_documents(root)
    config = root / "_config.yml"
    config_text = config.read_text(encoding="utf-8") if config.is_file() else ""
    url_match = re.search(r'^url:\s*["\']?(https?://[^"\'\s#]+)', config_text, re.MULTILINE)
    site_url = url_match.group(1).rstrip("/") if url_match else ""
    if not site_url:
        errors.append("site configuration has no absolute url")
        site_url = "https://invalid.test"

    rendered: dict[str, DialogueParser] = {}
    events: dict[tuple[str, str, str], Document] = {}
    groups: dict[tuple[str, str], list[Document]] = defaultdict(list)
    indexes: list[Document] = []
    expected_paths: set[Path] = set()
    layout_bytes = sum(
        path.stat().st_size for path in (
            root / "_layouts/darktide-preview.html",
            root / "_layouts/darktide-dialogue.html",
        ) if path.is_file()
    )
    shell_budget = max(16_384, layout_bytes * 2 + 8_192)

    for document in documents:
        fields = document.fields
        label = document.path.relative_to(root).as_posix()
        permalink = str(fields.get("permalink", ""))
        if fields.get("unlisted") is not True or fields.get("sitemap") is not False:
            errors.append(f"{label}: source must be unlisted with sitemap false")
        try:
            path = output_path(site, permalink)
        except ValueError as error:
            errors.append(f"{label}: {error}")
            continue
        if path in expected_paths:
            errors.append(f"{label}: duplicate permalink")
        expected_paths.add(path)
        source = parse_dialogue(document.body)
        is_event = fields.get("darktide_event") is True
        if is_event:
            event_type = str(fields.get("event_type", ""))
            event_id = str(fields.get("event_id", ""))
            locale = str(fields.get("locale", ""))
            order = positive_integer(fields.get("event_order"))
            line_count = positive_integer(fields.get("line_count"))
            if locale not in LOCALE_LANG or not event_type or not event_id or order is None:
                errors.append(f"{label}: invalid event metadata")
            if line_count is None or line_count != len(source.text["bubble"]):
                errors.append(f"{label}: line_count does not match source transcript")
            if source.template_count or source.script_count or len(source.transcripts) != 1:
                errors.append(f"{label}: source must contain one transcript without script/template")
            key = (event_type, event_id, locale)
            if key in events:
                errors.append(f"{label}: duplicate event/locale")
            events[key] = document
            groups[(event_type, locale)].append(document)
        else:
            indexes.append(document)
            if source.text["bubble"] or source.transcripts or source.template_count:
                errors.append(f"{label}: source index contains dialogue")
        if not path.is_file():
            errors.append(f"{label}: missing output {permalink}")
            continue
        markup = path.read_text(encoding="utf-8")
        page = parse_dialogue(markup)
        rendered[permalink] = page
        if page.canonicals != [site_url + permalink]:
            errors.append(f"{label}: canonical mismatch")
        directives = {
            value.strip().lower() for value in page.robots[0].split(",")
        } if len(page.robots) == 1 else set()
        if directives != {"noindex", "nofollow", "noarchive"}:
            errors.append(f"{label}: robots must be noindex,nofollow,noarchive")
        for asset in page.assets:
            parsed = urlsplit(urljoin(site_url + permalink, asset))
            if parsed.scheme in {"http", "https"} and parsed.netloc != urlsplit(site_url).netloc:
                continue
            relative = PurePosixPath(unquote(parsed.path).lstrip("/"))
            if ".." in relative.parts or not site.joinpath(*relative.parts).is_file():
                errors.append(f"{label}: missing local asset {asset}")
        if not is_event:
            if page.text["bubble"] or page.transcripts or page.template_count:
                errors.append(f"{label}: index contains dialogue")
            continue
        for component in source.text:
            if page.text[component] != source.text[component]:
                errors.append(f"{label}: {component} mismatch")
        if page.avatars != source.avatars:
            errors.append(f"{label}: avatar mismatch")
        locale = str(fields.get("locale", ""))
        expected_lang = LOCALE_LANG.get(locale, "")
        if (
            page.html_lang != expected_lang
            or page.body.get("data-locale") != locale
            or page.transcripts != [expected_lang]
            or page.body.get("data-event-id") != str(fields.get("event_id", ""))
        ):
            errors.append(f"{label}: event/locale identity mismatch")
        if page.template_count:
            errors.append(f"{label}: event contains template")
        if page.script_count:
            errors.append(f"{label}: event contains script")
        expected_sequences = [str(index + 1) for index in range(len(source.text["bubble"]))]
        if page.sequences != expected_sequences:
            errors.append(f"{label}: message sequence mismatch")
        source_links = [link.get("href", "") for link in page.links if link.get("id") == "dialogue-source"]
        if source_links != [str(fields.get("source_url", ""))]:
            errors.append(f"{label}: dialogue source link mismatch")
        if not re.fullmatch(
            r"https://github\.com/Aussiemon/Darktide-Source-Code/blob/[0-9a-f]{40}/.+",
            str(fields.get("source_url", "")),
        ):
            errors.append(f"{label}: dialogue source is not pinned to a commit")
        if len(markup.encode("utf-8")) > len(document.body.encode("utf-8")) * 3 + shell_budget:
            errors.append(f"{label}: payload exceeds own transcript/common-layout budget")

    if not events:
        errors.append("no Darktide event sources found")
    for (event_type, event_id, locale), document in events.items():
        label = document.path.relative_to(root).as_posix()
        fields = document.fields
        other_locale = "zh-tw" if locale == "en" else "en"
        counterpart = events.get((event_type, event_id, other_locale))
        if counterpart is None:
            errors.append(f"{label}: missing counterpart source")
            continue
        counterpart_url = str(counterpart.fields.get("permalink", ""))
        if fields.get("counterpart_url") != counterpart_url:
            errors.append(f"{label}: counterpart metadata mismatch")
        if fields.get("event_order") != counterpart.fields.get("event_order"):
            errors.append(f"{label}: counterpart event order mismatch")
        page = rendered.get(str(fields.get("permalink", "")))
        if page is not None:
            permalink = str(fields["permalink"])
            current_links = [
                (link_path(link.get("href", ""), permalink, site_url), link.get("aria-current"))
                for link in page.links if link.get("hreflang") == LOCALE_LANG.get(locale)
            ]
            if current_links != [(permalink, "page")]:
                errors.append(f"{label}: current language navigation mismatch")
            language_links = [
                link_path(link.get("href", ""), str(fields["permalink"]), site_url)
                for link in page.links if link.get("hreflang") == LOCALE_LANG.get(other_locale)
            ]
            if language_links != [counterpart_url]:
                errors.append(f"{label}: counterpart navigation mismatch")

    for group in groups.values():
        ordered = sorted(group, key=lambda document: positive_integer(document.fields.get("event_order")) or 0)
        orders = [positive_integer(document.fields.get("event_order")) for document in ordered]
        if len(set(orders)) != len(orders):
            errors.append("duplicate event_order within event type/locale")
        for index, document in enumerate(ordered):
            permalink = str(document.fields.get("permalink", ""))
            page = rendered.get(permalink)
            if page is None:
                continue
            label = document.path.relative_to(root).as_posix()
            for relation, target_index in (("prev", index - 1), ("next", index + 1)):
                expected = [str(ordered[target_index].fields["permalink"])] if 0 <= target_index < len(ordered) else []
                actual = [
                    link_path(link.get("href", ""), permalink, site_url)
                    for link in page.links if relation in link.get("rel", "").split()
                ]
                if actual != expected:
                    errors.append(f"{label}: {relation} navigation mismatch")

    type_indexes = {str(document.fields.get("event_type")): document for document in indexes if document.fields.get("event_type")}
    for document in indexes:
        permalink = str(document.fields.get("permalink", ""))
        page = rendered.get(permalink)
        if page is None:
            continue
        hrefs = {link_path(link.get("href", ""), permalink, site_url) for link in page.links}
        event_type = str(document.fields.get("event_type", ""))
        expected_links = (
            {str(event.fields["permalink"]) for key, event in events.items() if key[0] == event_type}
            if event_type else {str(index.fields["permalink"]) for index in type_indexes.values()}
        )
        if not expected_links.issubset(hrefs):
            errors.append(f"{document.path.relative_to(root).as_posix()}: index navigation incomplete")
    for event_type in {key[0] for key in events}:
        if event_type not in type_indexes:
            errors.append(f"missing event type index: {event_type}")

    actual_paths = set((site / PREVIEW_PREFIX.strip("/")).rglob("*.html"))
    for extra in sorted(actual_paths - expected_paths):
        errors.append(f"unexpected preview output: {extra.relative_to(site).as_posix()}")
    sitemap = site / "sitemap.xml"
    if not sitemap.is_file():
        errors.append("missing Sitemap output")
    else:
        try:
            for node in ET.parse(sitemap).iter():
                if node.tag.rsplit("}", 1)[-1] == "loc" and urlsplit(node.text or "").path.startswith(PREVIEW_PREFIX):
                    errors.append("Sitemap includes an unlisted Darktide preview")
        except ET.ParseError as error:
            errors.append(f"invalid Sitemap: {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path, nargs="?", default=Path("_site"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    errors = verify(args.site, root)
    if errors:
        print("Darktide preview verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    documents, _ = source_documents(root)
    events = [document for document in documents if document.fields.get("darktide_event") is True]
    subtitles = sum(int(str(document.fields["line_count"])) for document in events)
    print(f"Verified Darktide preview: {len(events)} event pages, {subtitles} source subtitles, {len(documents) - len(events)} indexes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
