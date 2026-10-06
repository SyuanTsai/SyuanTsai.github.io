#!/usr/bin/env python3
"""Generate per-page dialogue JSON from the pinned Darktide dialogue source.

Reads authoritative source and restored resources; every write is confined to --site.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import os
from html.parser import HTMLParser
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, unquote, urlsplit, urlunsplit

GAME_SOURCE_COMMIT = "7e662fcda16219d775b84af50322be2e9cd9d62e"
SCHEMA_VERSION = 3
LOCALES = ("en", "zh-tw")
PLAYBACK_STATES = ("confirmed", "conditional-reference-only", "unconfirmed")
UNKNOWN_SPEAKER_IDS = {"unknown", "unspecified", "unknown_speaker", "speaker_unknown"}
SOURCE_GIT_INDEX_CACHE: dict[tuple[str, str, str], set[str]] = {}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}
DROP = {"script", "style", "iframe", "object", "embed", "form"}
BT = chr(96)


class SourceError(RuntimeError):
    pass


class Node:
    def __init__(self, tag: str, attrs=None, parent=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children: list[Node | str] = []
        self.parent = parent


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = Node("document")
        self.stack = [self.root]
        self.drop_depth = 0

    def _start(self, tag, attrs, self_close=False):
        tag = tag.lower()
        if tag in DROP:
            if not self_close and tag not in VOID:
                self.drop_depth += 1
            return
        if self.drop_depth:
            return
        clean = {}
        for key, value in attrs:
            key = key.lower()
            if not key.startswith("on") and key != "style":
                clean[key] = value
        node = Node(tag, clean, self.stack[-1])
        self.stack[-1].children.append(node)
        if not self_close and tag not in VOID:
            self.stack.append(node)

    def handle_starttag(self, tag, attrs):
        self._start(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self._start(tag, attrs, True)

    def handle_endtag(self, tag):
        if tag.lower() in DROP and self.drop_depth:
            self.drop_depth -= 1
            return
        if self.drop_depth:
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag.lower():
                del self.stack[index:]
                return

    def handle_data(self, data):
        if not self.drop_depth:
            self.stack[-1].children.append(data)

    def handle_entityref(self, name):
        if not self.drop_depth:
            self.stack[-1].children.append(html.unescape("&" + name + ";"))

    def handle_charref(self, name):
        if not self.drop_depth:
            self.stack[-1].children.append(html.unescape("&#" + name + ";"))


def resolve(path: Path) -> Path:
    return path.expanduser().resolve()


def inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def reject_overlap(site: Path, inputs: list[tuple[str, Path]]) -> None:
    site = resolve(site)
    for label, path in inputs:
        path = resolve(path)
        if site == path or inside(site, path) or inside(path, site):
            raise SourceError(f"--site and {label} must be separate, non-nested paths")


def dialogue_root(path: Path) -> Path:
    path = resolve(path)
    for candidate in (path, path / "對話文本", path / "Game Info" / "對話文本"):
        if (candidate / "en" / "events").is_dir() and (candidate / "zh-tw" / "events").is_dir():
            return candidate
    raise SourceError("--dialogue-source must contain en/events and zh-tw/events")


def dialogue_repository_info(root: Path) -> tuple[Path | None, str | None]:
    probe = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True, check=False)
    if probe.returncode != 0:
        return None, None
    repository = Path(probe.stdout.strip()).resolve()
    remote = subprocess.run(["git", "-C", str(repository), "remote", "get-url", "origin"],
                             capture_output=True, text=True, check=False)
    return repository, remote.stdout.strip() if remote.returncode == 0 else None


def github_repository_base(remote_url: str | None) -> str | None:
    if not remote_url:
        return None
    value = remote_url.strip()
    if value.startswith("git@github.com:"):
        path = value.split(":", 1)[1]
    else:
        parsed = urlsplit(value)
        if (parsed.hostname or "").lower() not in {"github.com", "www.github.com"}:
            return None
        path = parsed.path.lstrip("/")
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return None
    owner, repository = parts[:2]
    if repository.endswith(".git"):
        repository = repository[:-4]
    return f"https://github.com/{owner}/{repository}"


def pinned_source_paths(source_root: Path, commit: str,
                        repository_root: Path | None) -> set[str] | None:
    if repository_root is None:
        return None
    repository_root = resolve(repository_root)
    source_root = resolve(source_root)
    if not inside(source_root, repository_root):
        return None
    source_relative = source_root.relative_to(repository_root).as_posix()
    cache_key = (str(repository_root), commit, source_relative)
    cached = SOURCE_GIT_INDEX_CACHE.get(cache_key)
    if cached is not None:
        return cached
    probe = subprocess.run(
        ["git", "-C", str(repository_root), "ls-tree", "-r", "-z", "--name-only",
         commit, "--", source_relative],
        capture_output=True, check=False,
    )
    if probe.returncode != 0:
        raise SourceError("could not enumerate pinned dialogue source files")
    paths = {os.fsdecode(value) for value in probe.stdout.split(b"\0") if value}
    SOURCE_GIT_INDEX_CACHE[cache_key] = paths
    return paths


def resolve_source_reference(source_root: Path, source_path: Path, reference: str,
                             commit: str, repository_root: Path | None,
                             repository_base: str | None, locale: str,
                             event_urls: dict[str, tuple[str, str]] | None = None) -> str:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
        return reference
    target = resolve(source_path.parent / unquote(parsed.path))
    if not inside(target, source_root) or not target.is_file():
        return reference
    if repository_root and repository_base and inside(target, repository_root):
        relative = target.relative_to(repository_root).as_posix()
        committed_paths = pinned_source_paths(source_root, commit, repository_root)
        if committed_paths is not None and relative in committed_paths:
            blob_path = "/".join((repository_base.split("github.com/", 1)[1], "blob",
                                   commit, quote(relative, safe="/")))
            return urlunsplit(("https", "github.com", "/" + blob_path,
                               parsed.query, parsed.fragment))
    relative = target.relative_to(source_root).parts
    if len(relative) >= 3 and relative[0] in LOCALES and relative[1] == "events" and event_urls:
        event_id = Path(relative[-1]).stem
        locale_urls = event_urls.get(relative[0], event_urls)
        mapped = locale_urls.get(event_id) if isinstance(locale_urls, dict) else None
        if mapped:
            target_url, default_anchor = mapped
            destination = urlsplit(target_url)
            return urlunsplit((destination.scheme, destination.netloc, destination.path,
                               parsed.query or destination.query,
                               parsed.fragment or default_anchor or destination.fragment))
    return reference


def resolve_source_metadata_links(source_root: Path, event_id: str, metadata: dict[str, Any],
                                  commit: str, repository_root: Path | None,
                                  repository_base: str | None, locale: str,
                                  event_urls: dict[str, tuple[str, str]] | None = None) -> None:
    source_path = source_root / "source" / f"{event_id}.md"
    for link in metadata.get("links", []):
        reference = link.get("url")
        if not isinstance(reference, str):
            continue
        link["reference"] = reference
        link["url"] = resolve_source_reference(
            source_root, source_path, reference, commit, repository_root,
            repository_base, locale, event_urls,
        )


def validate_commit(root: Path, value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise SourceError("--dialogue-commit must be a full 40-character commit SHA")
    probe = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True, check=False)
    if probe.returncode == 0:
        repo = Path(probe.stdout.strip()).resolve()
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=False)
        actual = head.stdout.strip().lower() if head.returncode == 0 else "unavailable"
        if actual != value:
            raise SourceError(f"dialogue checkout HEAD is {actual}; expected {value}")
    else:
        review = root.parent / f"authority-snapshot-review-{value[:4]}.json"
        marker = root / ".dialogue-commit"
        verified = marker.is_file() and marker.read_text(encoding="ascii").strip().lower() == value
        if review.is_file():
            try:
                report = json.loads(review.read_text(encoding="utf-8-sig"))
                verified = verified or (
                    report.get("authorityCommit") == value and
                    report.get("unmatched") == 0
                )
            except (OSError, json.JSONDecodeError):
                pass
        if not verified:
            raise SourceError("source needs a Git HEAD or matching authority-snapshot review")
    return value


def descendants(node: Node) -> Iterable[Node]:
    for child in node.children:
        if isinstance(child, Node):
            yield child
            yield from descendants(child)


def get_first(node: Node, predicate) -> Node | None:
    if predicate(node):
        return node
    for child in node.children:
        if isinstance(child, Node):
            found = get_first(child, predicate)
            if found:
                return found
    return None


def has_class(node: Node, name: str) -> bool:
    return name in (node.attrs.get("class") or "").split()


def has_any_class(node: Node, names: Iterable[str]) -> bool:
    classes = (node.attrs.get("class") or "").split()
    return any(name in classes for name in names)


def text_content(node: Node | None) -> str:
    parts = []
    def visit(item: Node | str):
        if isinstance(item, str):
            parts.append(item)
        elif item.tag != "br":
            for child in item.children:
                visit(child)
    if node:
        visit(node)
    return "".join(parts)


def text_content_without(node: Node | None, excluded: Node | None) -> str:
    parts = []

    def visit(item: Node | str):
        if item is excluded:
            return
        if isinstance(item, str):
            parts.append(item)
        elif item.tag != "br":
            for child in item.children:
                visit(child)

    if node:
        visit(node)
    return "".join(parts)


def text_parts_without(node: Node | None, excluded: Node | None) -> list[str]:
    parts = []

    def visit(item: Node | str):
        if item is excluded:
            return
        if isinstance(item, str):
            if item:
                parts.append(item)
        elif item.tag != "br":
            for child in item.children:
                visit(child)

    if node:
        visit(node)
    return parts


def prefixed_id(value: str, prefix: str) -> str:
    return value if value.startswith(prefix + "-") else prefix + "-" + value


def prefixed_idrefs(value: str, prefix: str) -> str:
    return " ".join(prefixed_id(part, prefix) for part in value.split())


def node_contains(ancestor: Node | None, node: Node | None) -> bool:
    current = node
    while current:
        if current is ancestor:
            return True
        current = current.parent
    return False


def prefixed_attributes(attrs, anchor_prefix):
    result = dict(attrs)
    if not anchor_prefix:
        return result
    if result.get("id"):
        result["id"] = prefixed_id(result["id"], anchor_prefix)
    for key in ("aria-labelledby", "aria-describedby", "aria-controls", "aria-owns",
                "for", "headers"):
        if result.get(key):
            result[key] = prefixed_idrefs(result[key], anchor_prefix)
    if result.get("href", "").startswith("#"):
        result["href"] = "#" + prefixed_id(result["href"][1:], anchor_prefix)
    return result


def json_node(node: Node | str, anchor_prefix=None, variant_refs=None) -> dict[str, Any]:
    if isinstance(node, str):
        return {"type": "text", "value": node}
    attrs = prefixed_attributes(node.attrs, anchor_prefix)
    variant_id = (variant_refs or {}).get(id(node))
    if node.tag == "img" and has_class(node, "participant-avatar") and variant_id:
        attrs = ({"id": attrs["id"]} if attrs.get("id") else {})
        attrs["data-speaker-variant-ref"] = variant_id
        children = []
    elif has_class(node, "participant-name") and variant_id:
        suffix = get_first(node, lambda child: has_any_class(child, PARTICIPANT_SUFFIX_CLASSES))
        attrs["data-speaker-variant-ref"] = variant_id

        def name_child(item):
            if suffix and isinstance(item, Node) and node_contains(suffix, item):
                return json_node(item, anchor_prefix, variant_refs)
            if isinstance(item, str):
                if not item:
                    return json_node(item, anchor_prefix, variant_refs)
                part_index = name_child.next_index
                name_child.next_index += 1
                return {"type": "element", "tag": "span",
                        "attrs": {"class": "participant-name-value",
                                  "data-reader-variant-part": str(part_index)},
                        "children": []}
            return {"type": "element", "tag": item.tag,
                    "attrs": prefixed_attributes(item.attrs, anchor_prefix),
                    "children": [name_child(child) for child in item.children]}

        name_child.next_index = 0
        children = [name_child(item) for item in node.children]
    else:
        children = [json_node(item, anchor_prefix, variant_refs) for item in node.children]
    return {"type": "element", "tag": node.tag, "attrs": attrs,
            "children": children}


def parse_html_document(path: Path) -> tuple[Node, Node, str, str]:
    parser = TreeParser()
    parser.feed(path.read_bytes().decode("utf-8-sig"))
    root = get_first(parser.root, lambda n: n.tag == "html")
    title = get_first(parser.root, lambda n: n.tag == "title")
    transcript = get_first(parser.root, lambda n: has_class(n, "transcript"))
    if transcript is None:
        raise SourceError(f"source event has no transcript: {path.name}")
    lang = (root.attrs.get("lang") if root else None) or path.parent.parent.name
    return parser.root, transcript, text_content(title).strip() if title else path.stem, lang


def parse_html(path: Path) -> tuple[Node, str, str]:
    _, transcript, title, lang = parse_html_document(path)
    return transcript, title, lang


def class_nodes(root: Node, name: str) -> list[Node]:
    return [node for node in descendants(root) if has_class(node, name)]


PARTICIPANT_SUFFIX_CLASSES = (
    "participant-suffix", "participant-role-suffix", "participant-voice",
    "participant-voice-label", "participant-subtitle", "speaker-suffix",
    "voice-label",
)


def participant_bar_record(section: Node, variant_refs, anchor_prefix=None):
    heading = get_first(section, lambda node: node.tag in {"h1", "h2", "h3", "h4"})
    hint = get_first(section, lambda node: has_class(node, "participant-hint"))
    listing = get_first(section, lambda node: node.tag in {"ol", "ul"})
    list_root = listing or section
    links = [node for node in descendants(list_root)
             if node.tag == "a" and has_class(node, "participant-link")]
    rows = []
    for order, link in enumerate(links, 1):
        name = get_first(link, lambda node: has_class(node, "participant-name"))
        suffix = get_first(link, lambda node: has_any_class(node, PARTICIPANT_SUFFIX_CLASSES))
        side_label = get_first(link, lambda node: has_class(node, "participant-side"))
        portrait = get_first(link, lambda node: node.tag == "img" and
                             has_class(node, "participant-avatar"))
        item = link.parent
        while item and item is not section and item.tag != "li":
            item = item.parent
        if item is section:
            item = None
        source_href = link.attrs.get("href")
        source_anchor = source_href[1:] if source_href and source_href.startswith("#") else None
        href = source_href
        first_anchor = link.attrs.get("data-first-anchor") or source_anchor
        if anchor_prefix and first_anchor:
            first_anchor = prefixed_id(first_anchor, anchor_prefix)
        if anchor_prefix and href and href.startswith("#"):
            href = "#" + prefixed_id(href[1:], anchor_prefix)
        link_attributes = dict(link.attrs)
        if anchor_prefix and link_attributes.get("href", "").startswith("#"):
            link_attributes["href"] = href
        rows.append({
            "speakerId": link.attrs.get("data-speaker-id"),
            "variantId": (link.attrs.get("data-speaker-variant-ref") or
                          variant_refs.get(id(link))),
            "side": link.attrs.get("data-side"), "sideLabel": text_content(side_label) if side_label else None,
            "order": order, "firstAnchor": first_anchor, "href": href,
            "sourceFirstAnchor": source_anchor, "sourceHref": source_href,
            "name": text_content(name) if name and not variant_refs.get(id(name)) else None,
            "suffix": text_content(suffix) if suffix else None,
            "nameAttributes": dict(name.attrs) if name else {},
            "suffixAttributes": dict(suffix.attrs) if suffix else {},
            "sideAttributes": dict(side_label.attrs) if side_label else {},
            "portraitAttributes": (dict(portrait.attrs) if portrait and not variant_refs.get(id(portrait))
                                    else {}),
            "itemTag": item.tag if item else "li",
            "itemAttributes": dict(item.attrs) if item else {},
            "linkTag": link.tag, "linkAttributes": link_attributes,
        })
    return {
        "tree": json_node(section, anchor_prefix=anchor_prefix, variant_refs=variant_refs),
        "sectionTag": section.tag, "sectionAttributes": dict(section.attrs),
        "heading": ({"tag": heading.tag, "text": text_content(heading),
                     "attributes": dict(heading.attrs)} if heading else None),
        "hint": ({"tag": hint.tag, "text": text_content(hint),
                  "attributes": dict(hint.attrs)} if hint else None),
        "list": ({"tag": listing.tag, "attributes": dict(listing.attrs)} if listing else None),
        "rows": rows,
    }


def parse_messages(transcript: Node) -> list[dict[str, Any]]:
    result = []
    for message in class_nodes(transcript, "message"):
        bubble = get_first(message, lambda n: has_class(n, "bubble"))
        speaker = get_first(message, lambda n: has_class(n, "speaker"))
        avatar = get_first(message, lambda n: n.tag == "img" and has_class(n, "avatar"))
        timestamp = get_first(message, lambda n: has_class(n, "timestamp"))
        record = {
            "anchorId": message.attrs.get("id"),
            "speakerId": message.attrs.get("data-speaker-id"),
            "side": message.attrs.get("data-side") or message.attrs.get("data-role"),
            "sourceVariant": message.attrs.get("data-speaker-variant") or message.attrs.get("data-variant"),
            "sequence": message.attrs.get("data-sequence"),
            "order": (int(message.attrs["data-sequence"])
                      if re.fullmatch(r"\d+", message.attrs.get("data-sequence") or "")
                      else message.attrs.get("data-sequence")),
            "sourceHash": (message.attrs.get("data-hash") or message.attrs.get("data-subtitle-hash")),
            "sourceKey": (message.attrs.get("data-key") or message.attrs.get("data-loc-key")),
            "timestamp": text_content(timestamp) if timestamp else None,
        }
        result.append({key: value for key, value in record.items() if value is not None})
    return result


def parse_tables(markdown: str) -> list[dict[str, str]]:
    lines = markdown.splitlines()
    tables = []
    pos = 0
    voice_profile = None
    while pos + 1 < len(lines):
        header, rule = lines[pos].strip(), lines[pos + 1].strip()
        profile_match = re.search(
            r"(?:voice\s+profile|聲線)\s*[:：]\s*" + BT + r"([^" + BT + r";；]+)",
            lines[pos], re.I,
        )
        if profile_match:
            voice_profile = profile_match.group(1).strip()
        if header.startswith("|") and rule.startswith("|") and re.search(r"-{3,}", rule):
            keys = [part.strip() for part in header.strip("|").split("|")]
            pos += 2
            while pos < len(lines) and lines[pos].strip().startswith("|"):
                cells = [part.strip() for part in lines[pos].strip().strip("|").split("|")]
                if len(keys) == len(cells):
                    row = dict(zip(keys, cells))
                    row["__sourceLine"] = str(pos + 1)
                    if voice_profile:
                        row["__voiceProfile"] = voice_profile
                    tables.append(row)
                pos += 1
        else:
            pos += 1
    return tables


def uncode(text: str) -> str:
    return re.sub(BT + r"([^" + BT + r"]*)" + BT, r"\1", text).strip()


def hashes_in(metadata: dict[str, Any]) -> set[str]:
    result = set()
    for row in metadata.get("tables", []):
        for key, value in row.items():
            if "hash" in key.lower():
                match = re.search(r"\b[0-9a-fA-F]{8,40}\b", uncode(value))
                if match:
                    result.add(match.group(0).lower())
    result.update(metadata.get("explicitHashes", []))
    return result


def parse_source_md(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"markdown": None, "links": [], "tables": [], "evidenceGaps": [],
                "warnings": ["event source Markdown is missing"]}
    raw_bytes = path.read_bytes()
    raw = raw_bytes.decode("utf-8-sig")
    links = []
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", raw):
        links.append({
            "label": match.group(1), "url": match.group(2),
            "sourceLine": raw.count("\n", 0, match.start()) + 1,
        })
    gaps, heading, body = [], None, []
    def save():
        if heading and re.search(r"限制|缺口|待確認|limitation|warning|evidence gap", heading, re.I):
            gaps.append({"heading": heading, "text": "\n".join(body).strip()})
    for line in raw.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            save()
            heading, body = match.group(1), []
        elif heading:
            body.append(line)
    save()
    warnings = []
    for line in raw.splitlines():
        if re.search(r"^\s*>?\s*(?:\[!WARNING\]|警告|Warning:)", line, re.I):
            warnings.append(line.strip().lstrip("> ").strip())
    explicit_hash_evidence = []
    for match in re.finditer(
        r"(?i)(?:^|[;；,，\s])(?:hash|字幕hash)\s*[:：=]\s*" +
        BT + r"?([0-9a-fA-F]{8,40})" + BT + r"?",
        raw,
    ):
        explicit_hash_evidence.append({
            "hash": match.group(1).lower(),
            "sourceLine": raw.count("\n", 0, match.start()) + 1,
        })
    return {
        "markdown": raw, "links": links,
        "tables": [{k: uncode(v) for k, v in row.items()} for row in parse_tables(raw)],
        "explicitHashes": sorted({item["hash"] for item in explicit_hash_evidence}),
        "explicitHashEvidence": explicit_hash_evidence,
        "evidenceGaps": gaps, "sourceWarnings": warnings, "warnings": [],
        "sourceSha256": hashlib.sha256(raw_bytes).hexdigest(),
    }


def evidence_records(value):
    result = {}
    if isinstance(value, list):
        for item in value:
            for key, record in evidence_records(item).items():
                if key in result and result[key] != record:
                    raise SourceError(f"subtitle usage evidence ID has conflicting records: {key}")
                result[key] = record
    elif isinstance(value, dict):
        shared = next((item for key, item in value.items()
                       if re.sub(r"[^a-z0-9]", "", key.lower()) == "sharedevidence"), None)
        if isinstance(shared, dict):
            for raw_id, record in shared.items():
                evidence_id = str(raw_id).strip().casefold()
                if not evidence_id or not isinstance(record, dict):
                    continue
                if evidence_id in result and result[evidence_id] != record:
                    raise SourceError(f"subtitle usage evidence ID has conflicting records: {evidence_id}")
                result[evidence_id] = record
        id_value = next((item for key, item in value.items()
                         if re.sub(r"[^a-z0-9]", "", key.lower()) in
                         {"evidenceid"}), None)
        if id_value is not None and str(id_value).strip():
            evidence_id = str(id_value).strip().casefold()
            if evidence_id in result and result[evidence_id] != value:
                raise SourceError(f"subtitle usage evidence ID has conflicting records: {evidence_id}")
            result[evidence_id] = value
        for item in value.values():
            if isinstance(item, (list, dict)):
                for key, record in evidence_records(item).items():
                    if key in result and result[key] != record:
                        raise SourceError(f"subtitle usage evidence ID has conflicting records: {key}")
                    result[key] = record
    return result


def read_usage(classification: Path) -> tuple[
    list[dict[str, Any]], dict[str, Any] | None, dict[str, dict[str, Any]]
]:
    if not classification.is_dir():
        raise SourceError("--classification-source must be a TSV directory")
    paths = sorted(classification.rglob("*.tsv"))
    audit_paths = [path for path in paths if path.name.lower() == "subtitle-usages-audit.tsv"]
    if audit_paths:
        if len(audit_paths) > 1:
            raise SourceError("classification source has multiple authoritative usage audit TSVs")
        paths = audit_paths + [path for path in paths
                               if path not in audit_paths and "personality" in path.name.lower()]
    nested_evidence_paths = sorted(classification.rglob("subtitle-usage-evidence.json"))
    if len(nested_evidence_paths) > 1:
        raise SourceError("classification source has multiple subtitle usage evidence JSON files")
    evidence_path = nested_evidence_paths[0] if nested_evidence_paths else next((
        candidate for parent in (classification, classification.parent, *list(classification.parents)[:3])
        for candidate in (parent / "subtitle-usage-evidence.json",)
        if candidate.is_file()
    ), None)
    evidence_index = {}
    audit_info = {}
    if audit_paths:
        audit_bytes = audit_paths[0].read_bytes()
        audit_info.update({
            "table": audit_paths[0].name,
            "tableSha256": hashlib.sha256(audit_bytes).hexdigest(),
        })
    if evidence_path:
        try:
            evidence_bytes = evidence_path.read_bytes()
            evidence_document = json.loads(evidence_bytes.decode("utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise SourceError(f"could not read subtitle usage evidence JSON: {error}") from error
        evidence_index = evidence_records(evidence_document)
        audit_info.update({
            "evidence": evidence_path.name,
            "evidenceSha256": hashlib.sha256(evidence_bytes).hexdigest(),
        })
    result: list[dict[str, Any]] = []
    for path in paths:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            for source_line, row in enumerate(csv.DictReader(stream, delimiter="\t"), 2):
                value = {str(k): str(v or "") for k, v in row.items()}
                value["_source"] = path.relative_to(classification).as_posix()
                value["_sourceLine"] = str(source_line)
                result.append(value)
    if not result:
        raise SourceError("classification source contains no usage TSV rows")
    return result, audit_info or None, evidence_index


def row_hashes(row: dict[str, str]) -> set[str]:
    result = set()
    for key, value in row.items():
        if "hash" in key.lower():
            match = re.search(r"\b[0-9a-fA-F]{8,40}\b", uncode(value))
            if match:
                result.add(match.group(0).lower())
    return result


def usage_hashes(row: dict[str, str]) -> set[str]:
    result = set()
    for key, value in row.items():
        normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
        if normalized not in {"hash", "subtitle_hash", "source_hash", "event_hash"}:
            continue
        match = re.fullmatch(r"\s*([0-9a-fA-F]{8,40})\s*", value)
        if match:
            result.add(match.group(1).lower())
    return result


def usage_value(row: dict[str, Any], *names: str) -> str:
    wanted = {re.sub(r"[^a-z0-9]", "", name.lower()) for name in names}
    for key, value in row.items():
        normalized = re.sub(r"[^a-z0-9]", "", key.lower())
        if normalized in wanted and isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def classification_record(row: dict[str, str]) -> dict[str, Any]:
    relevant = {
        "hash", "subtitlehash", "sourcehash", "eventhash", "usageclassification",
        "referencerelation", "playbackeligibility", "currentplaybackproven",
        "conditionoperator", "type", "sourcepath", "sourceline", "responsegroup",
        "eventrule", "speakerevidence", "speakerstatus",
        "eventstatus", "playbackstatus", "evidenceref", "evidenceid",
        "classificationsourcepath", "classificationsourceline", "remaininggap",
        "evidencegap", "charactervoice", "speakeren", "speakerzhtw",
        "archetypeen", "archetypezhtw",
    }
    fields = {}
    for key, value in row.items():
        normalized = re.sub(r"[^a-z0-9]", "", key.lower())
        if (not value.strip() or key.startswith("_") or normalized not in relevant or
                "url" in normalized or "link" in normalized):
            continue
        if normalized.endswith("count") and value.strip() == "0":
            continue
        fields[key] = value
    return {
        "sourceTable": Path(row.get("_source", "")).name,
        "sourceRow": int(row["_sourceLine"]) if row.get("_sourceLine", "").isdigit() else None,
        "fields": fields,
    }


def parse_manifest(root: Path):
    start = root if root.is_dir() else root.parent
    for parent in (start, *list(start.parents)[:6]):
        for name in ("restoration_manifest.json", "files.sha256.json"):
            path = parent / name
            if path.is_file():
                return path, json.loads(path.read_text(encoding="utf-8-sig"))
    return None, None


def manifest_entry(manifest, rel):
    files = manifest.get("files")
    if isinstance(files, list):
        for row in files:
            if isinstance(row, dict) and row.get("path", "").replace("\\", "/") == rel:
                return row
    if isinstance(files, dict):
        row = files.get(rel)
        return {"sha256": row} if isinstance(row, str) else row
    return None


def locate_jsonl(root: Path, locale: str) -> Path:
    root = resolve(root)
    candidates = [root] if root.is_file() else [
        root / locale / "subtitles.jsonl",
        root / "jsonl" / locale / "subtitles.jsonl",
        *[p / "jsonl" / locale / "subtitles.jsonl" for p in (root, *list(root.parents)[:5])],
    ]
    for path in candidates:
        if path.is_file() and path.name == "subtitles.jsonl" and path.parent.name == locale:
            return path
    raise SourceError(f"could not locate {locale}/subtitles.jsonl")


def verify_jsonl(path: Path, resource_root: Path) -> dict[str, Any]:
    manifest_path, manifest = parse_manifest(resource_root)
    if not manifest_path or not manifest:
        raise SourceError("locale resources need restoration_manifest.json checksum evidence")
    rel = "/".join(path.parts[-3:])
    row = manifest_entry(manifest, rel)
    if not row:
        raise SourceError(f"resource manifest lacks {rel}")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != str(row.get("sha256", "")).lower() or (
        row.get("size") is not None and len(data) != int(row["size"])
    ):
        raise SourceError(f"resource checksum or size mismatch for {rel}")
    return {"sha256": digest, "size": len(data), "manifest": "restoration_manifest.json"}


def load_resource_index(path: Path, needed: set[str]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    if not needed:
        return result
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for number, line in enumerate(stream, 1):
            row = json.loads(line)
            value = str(row.get("hash", "")).lower()
            if value in needed:
                result.setdefault(value, []).append({
                    "hash": value, "locKey": row.get("loc_key") or row.get("key"),
                    "entryIndex": row.get("entry_index"), "text": row.get("text"),
                    "sourceLine": number,
                })
    return result


def speakers_from(root: Path) -> list[dict[str, Any]]:
    path = root / "SPEAKERS.md"
    if not path.is_file():
        return []
    raw = path.read_bytes().decode("utf-8-sig")
    result = []
    for row in parse_tables(raw):
        cooked = {re.sub(r"\s+", " ", k.strip().lower()): uncode(v) for k, v in row.items()}
        profile = next((v for k, v in cooked.items() if "profile" in k or "voice" in k or "設定檔" in k), "")
        if not profile or profile.lower() in {"profile", "voice profile"}:
            continue
        names = {}
        for key, value in cooked.items():
            if key in {"english", "english name", "en", "en name"}:
                names["en"] = value
            if any(token in key for token in ("繁中", "traditional chinese", "zh-tw", "中文名稱")):
                names["zh-tw"] = value
        image_html = next((value for value in row.values() if "<img" in value.lower()), "")
        image = re.search(r"\bsrc=[\"']([^\"']+)", image_html, re.I)
        urls = re.findall(r"https?://[^\s)>|]+", " ".join(cooked.values()))
        result.append({
            "speakerId": profile.strip(BT), "labels": names,
            "portrait": image.group(1) if image else None, "sourceUrls": urls,
            "sourcePath": "SPEAKERS.md",
            "sourceLine": int(row.get("__sourceLine", "0") or 0) or None,
        })
    return result


def make_speaker_variant(locale, role, label_node, portrait_node,
                         excluded_label_node=None, shared_name_parts=False):
    display_parts = (text_parts_without(label_node, excluded_label_node)
                     if label_node and shared_name_parts else None)
    display_label = ("".join(display_parts) if display_parts is not None else
                     text_content_without(label_node, excluded_label_node)
                     if label_node and excluded_label_node else
                     text_content(label_node) if label_node else "")
    portrait_attributes = ({key: value for key, value in portrait_node.attrs.items()
                            if key != "id"} if portrait_node else {})
    portrait = portrait_attributes.get("src")
    portrait_alt = portrait_attributes.get("alt")
    if not display_label and portrait is None and portrait_alt is None:
        return None
    signature = json.dumps(
        [locale, role, display_label, display_parts, portrait_attributes],
        ensure_ascii=False, separators=(",", ":"),
    )
    variant_id = "speaker-variant-" + hashlib.sha256(signature.encode("utf-8")).hexdigest()[:20]
    record = {
        "variantId": variant_id, "speakerId": role, "locale": locale,
        "displayName": display_label,
        "portrait": portrait, "portraitAlt": portrait_alt,
        "portraitAttributes": portrait_attributes,
    }
    if display_parts is not None:
        record["displayNameParts"] = display_parts
    return record


def collect_speaker_variants(transcript, locale, speakers, participant_roots=()):
    known_speakers = {str(item.get("speakerId") or "") for item in speakers}
    records, node_refs, message_refs = {}, {}, {}

    for message in class_nodes(transcript, "message"):
        role = str(message.attrs.get("data-speaker-id") or "")
        if not role or role.lower() in UNKNOWN_SPEAKER_IDS or role not in known_speakers:
            continue
        label = get_first(message, lambda n: has_class(n, "speaker"))
        portrait = get_first(message, lambda n: n.tag == "img" and has_class(n, "avatar"))
        variant = make_speaker_variant(locale, role, label, portrait)
        if variant is None:
            continue
        variant_id = variant["variantId"]
        records[variant_id] = variant
        message_key = message.attrs.get("id") or f"sequence:{message.attrs.get('data-sequence')}"
        message_refs[message_key] = variant_id
        if label:
            node_refs[id(label)] = variant_id
        if portrait and (portrait.attrs.get("src") or portrait.attrs.get("alt") is not None):
            node_refs[id(portrait)] = variant_id

    participant_nodes = []
    seen_participants = set()
    for root in (transcript, *participant_roots):
        for participant in descendants(root):
            if id(participant) in seen_participants:
                continue
            seen_participants.add(id(participant))
            participant_nodes.append(participant)
    for participant in participant_nodes:
        if not (has_class(participant, "participant") or has_class(participant, "participant-link")):
            continue
        role = str(participant.attrs.get("data-speaker-id") or "")
        if not role or role.lower() in UNKNOWN_SPEAKER_IDS or role not in known_speakers:
            continue
        label = get_first(participant, lambda n: has_class(n, "participant-name"))
        portrait = get_first(participant, lambda n: n.tag == "img" and has_class(n, "participant-avatar"))
        suffix = get_first(label, lambda n: has_any_class(n, PARTICIPANT_SUFFIX_CLASSES)) if label else None
        variant = make_speaker_variant(
            locale, role, label, portrait, suffix, shared_name_parts=True,
        )
        if variant is None:
            continue
        variant_id = variant["variantId"]
        records[variant_id] = variant
        node_refs[id(participant)] = variant_id
        if label:
            node_refs[id(label)] = variant_id
        if portrait and (portrait.attrs.get("src") or portrait.attrs.get("alt") is not None):
            node_refs[id(portrait)] = variant_id

    return records, node_refs, message_refs


def row_hash(row):
    for key, value in row.items():
        if "hash" in key.lower():
            match = re.search(r"\b[0-9a-fA-F]{8,40}\b", uncode(value))
            if match:
                return match.group(0).lower()
    return None


def row_sequence(row):
    for key, value in row.items():
        if any(token in key.lower() for token in ("sequence", "order", "順序", "序號", "排序", "slot")):
            match = re.search(r"\b\d+\b", uncode(value))
            if match:
                return str(int(match.group(0)))
    return None


def associate_message_hashes(messages, metadata):
    linked = {}
    rows = metadata.get("tables", [])
    for message in messages:
        source_hash = str(message.get("sourceHash") or "").lower()
        if re.fullmatch(r"[0-9a-f]{8,40}", source_hash):
            linked[message.get("anchorId") or f"sequence:{message.get('sequence')}"] = source_hash
    for row in rows:
        source_hash = row_hash(row)
        if not source_hash:
            continue
        sequence = row_sequence(row)
        if sequence is None:
            continue
        profile = row.get("__voiceProfile")
        if profile:
            profile_messages = [message for message in messages
                                if message.get("speakerId") == profile and
                                re.fullmatch(r"\d+", str(message.get("sequence") or ""))]
            profile_messages.sort(key=lambda message: int(message["sequence"]))
            slot = int(sequence)
            if 1 <= slot <= len(profile_messages):
                message = profile_messages[slot - 1]
                linked[message.get("anchorId") or f"sequence:{message.get('sequence')}"] = source_hash
                continue
        candidates = [message for message in messages
                      if re.fullmatch(r"\d+", str(message.get("sequence") or "")) and
                      int(message["sequence"]) == int(sequence)]
        if len(candidates) == 1:
            message = candidates[0]
            linked[message.get("anchorId") or f"sequence:{message.get('sequence')}"] = source_hash
    source_hashes = {row_hash(row) for row in rows if row_hash(row)}
    source_hashes.update(metadata.get("explicitHashes", []))
    if len(messages) == 1 and len(source_hashes) == 1 and not linked:
        only = messages[0]
        linked[only.get("anchorId") or f"sequence:{only.get('sequence')}"] = next(iter(source_hashes))
    return linked


def source_text_for(hash_value, resource_index):
    rows = resource_index.get(hash_value, [])
    texts = {row.get("text") for row in rows if isinstance(row.get("text"), str)}
    if len(texts) == 1:
        return next(iter(texts))
    return None


def resolve_event_link(value, event_urls):
    parsed = urlsplit(value)
    if not parsed.path:
        return value
    path = unquote(parsed.path).rstrip("/")
    leaf = Path(path).name
    if leaf.lower() == "index.html":
        leaf = Path(path).parent.name
    event_id = Path(leaf).stem if leaf.lower().endswith(".html") else leaf
    if event_id not in event_urls and parsed.fragment in event_urls:
        event_id = parsed.fragment
    target = event_urls.get(event_id)
    if not target:
        return value
    target_url, default_anchor = target
    destination = urlsplit(target_url)
    if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:
        return value
    if parsed.netloc and parsed.netloc.lower() != destination.netloc.lower():
        return value
    return urlunsplit((
        "", "", destination.path,
        parsed.query or destination.query,
        parsed.fragment or default_anchor or destination.fragment,
    ))


def serialize_transcript(transcript, messages, links, resource_index,
                         variant_refs, locale, fallback_resource_index=None,
                         anchor_prefix=None, event_urls=None):
    by_anchor = {message["anchorId"]: message for message in messages if message.get("anchorId")}
    by_sequence = {}
    for message in messages:
        if message.get("sequence") is not None:
            by_sequence.setdefault(str(message["sequence"]), []).append(message)

    def visit(item, active_message=None, active_role=None):
        if isinstance(item, str):
            return item
        if has_class(item, "message"):
            active_message = by_anchor.get(item.attrs.get("id"))
            if active_message is None:
                candidates = by_sequence.get(str(item.attrs.get("data-sequence")), [])
                active_message = candidates[0] if len(candidates) == 1 else None
            active_role = item.attrs.get("data-speaker-id")
        elif item.attrs.get("data-speaker-id"):
            active_role = item.attrs.get("data-speaker-id")
        attrs = dict(item.attrs)
        if anchor_prefix:
            if attrs.get("id"):
                attrs["id"] = prefixed_id(attrs["id"], anchor_prefix)
            for key in ("aria-labelledby", "aria-describedby", "aria-controls", "aria-owns",
                        "for", "headers"):
                if attrs.get(key):
                    attrs[key] = prefixed_idrefs(attrs[key], anchor_prefix)
            if attrs.get("href", "").startswith("#"):
                attrs["href"] = "#" + prefixed_id(attrs["href"][1:], anchor_prefix)
        if event_urls and attrs.get("href"):
            attrs["href"] = resolve_event_link(attrs["href"], event_urls)
        children = item.children
        link_key = None
        if active_message:
            link_key = active_message.get("anchorId") or f"sequence:{active_message.get('sequence')}"
        if has_class(item, "bubble") and link_key in links:
            source_hash = links[link_key]
            raw_text = source_text_for(source_hash, resource_index)
            has_local_text = any(isinstance(row.get("text"), str)
                                 for row in resource_index.get(source_hash, []))
            if raw_text is None and not has_local_text and locale == "zh-tw" and fallback_resource_index:
                raw_text = source_text_for(source_hash, fallback_resource_index)
                if raw_text is not None:
                    attrs["lang"] = "en"
            if raw_text is not None:
                children = [raw_text]
        elif has_class(item, "line") and link_key in links:
            source_hash = links[link_key]
            local_text = source_text_for(source_hash, resource_index)
            has_local_text = any(isinstance(row.get("text"), str)
                                 for row in resource_index.get(source_hash, []))
            fallback_text = (source_text_for(source_hash, fallback_resource_index)
                             if not has_local_text and locale == "zh-tw" and fallback_resource_index else None)
            has_bubble = get_first(item, lambda n: has_class(n, "bubble")) is not None
            if local_text is None and not has_local_text and fallback_text is not None and not has_bubble:
                warning = Node("p", {"class": "note"})
                warning.children = ["尚無官方繁中翻譯，暫以英文原文顯示。"]
                bubble = Node("div", {"class": "bubble", "lang": "en"})
                bubble.children = [fallback_text]
                children = [warning, bubble]
        variant_id = variant_refs.get(id(item))
        if has_class(item, "speaker") and variant_id:
            attrs["data-speaker-variant-ref"] = variant_id
            children = []
        elif item.tag == "img" and variant_id and has_class(item, "participant-avatar"):
            attrs = {key: value for key, value in attrs.items() if key in {"class", "id"}}
            attrs["data-speaker-variant-ref"] = variant_id
        elif item.tag == "img" and variant_id:
            attrs.pop("src", None)
            attrs.pop("alt", None)
            attrs["data-speaker-variant-ref"] = variant_id
        elif has_class(item, "participant-name") and variant_id:
            attrs["data-speaker-variant-ref"] = variant_id
            suffix = get_first(item, lambda n: has_any_class(n, PARTICIPANT_SUFFIX_CLASSES))

            def name_child(child):
                if suffix and isinstance(child, Node) and node_contains(suffix, child):
                    return child
                if isinstance(child, str):
                    if not child:
                        return child
                    part_index = name_child.next_index
                    name_child.next_index += 1
                    return Node("span", {
                        "class": "participant-name-value",
                        "data-reader-variant-part": str(part_index),
                    })
                clone = Node(child.tag, dict(child.attrs))
                clone.children = [name_child(nested) for nested in child.children]
                return clone

            name_child.next_index = 0
            children = [name_child(child) for child in item.children]
        return [item.tag, attrs,
                [visit(child, active_message, active_role) for child in children]]

    return [visit(child) for child in transcript.children]


def catalog_for(root: Path, event_ids: set[str]) -> dict[str, list[dict[str, Any]]]:
    result = {event_id: [] for event_id in event_ids}
    base = root / "source-catalog"
    if not base.is_dir():
        return result
    for path in sorted(base.rglob("*.md")):
        raw_bytes = path.read_bytes()
        raw = raw_bytes.decode("utf-8-sig")
        links_by_event: dict[str, list[dict[str, str]]] = {}
        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", raw):
            label, url = match.group(1), match.group(2)
            target = re.split(r"[?#]", url, maxsplit=1)[0]
            event_id = Path(target).stem
            if event_id not in event_ids or not re.search(r"(?:^|/)(?:events|source)/", target):
                continue
            links_by_event.setdefault(event_id, []).append({
                "label": label, "url": url,
                "sourceLine": raw.count("\n", 0, match.start()) + 1,
            })
        for event_id, links in links_by_event.items():
            result[event_id].append({
                "source": path.relative_to(base).as_posix(),
                "sourceSha256": hashlib.sha256(raw_bytes).hexdigest(),
                "links": links,
            })
    return result


def site_pages(site: Path, locale: str) -> dict[str, Path]:
    result = []
    base = site / "darktide"
    if not base.is_dir():
        return result
    for path in base.rglob("*.html"):
        parts = path.relative_to(base).parts
        if parts and parts[0] == "skills":
            continue
        if locale == "en" and (not parts or parts[0] != "en"):
            continue
        if locale == "zh-tw" and parts and parts[0] == "en":
            continue
        parser = TreeParser()
        try:
            parser.feed(path.read_bytes().decode("utf-8-sig"))
        except (OSError, UnicodeError):
            continue
        if not class_nodes(parser.root, "transcript"):
            continue
        html_node = get_first(parser.root, lambda n: n.tag == "html")
        body_node = get_first(parser.root, lambda n: n.tag == "body")
        lang = (body_node.attrs.get("data-locale") if body_node else None) or (
            html_node.attrs.get("lang") if html_node else None
        )
        page_locale = "en" if lang == "en" or (parts and parts[0] == "en") else "zh-tw"
        if page_locale == locale:
            result.append(path)
    return sorted(result)


def page_source_ids(path: Path, event_ids: set[str], personality_events: dict[str, str]) -> tuple[list[str], str]:
    page_id = path.parent.name if path.name.lower() == "index.html" else path.stem
    relative = "/".join(path.parts).lower()
    if "unlinked-subtitles" in relative:
        parser = TreeParser()
        parser.feed(path.read_bytes().decode("utf-8-sig"))
        ids = [node.attrs.get("id") for node in descendants(parser.root)
               if node.attrs.get("id", "").startswith("unlinked_subtitle_")]
        return [value for value in dict.fromkeys(ids) if value in event_ids], "paginated-unlinked"
    if page_id in personality_events:
        source_id = personality_events[page_id]
        return ([source_id] if source_id in event_ids else []), "personality-alias"
    if page_id in event_ids:
        return [page_id], "direct-event"
    return [], "unmapped"


def groups_and_participants(transcript: Node, messages: list[dict[str, Any]], variant_refs,
                            message_variant_refs=None):
    message_order = list(dict.fromkeys(
        m["anchorId"] for m in messages if m.get("anchorId")
    ))
    groups = []
    for node in descendants(transcript):
        classes = (node.attrs.get("class") or "").lower()
        if node.tag in {"section", "fieldset", "details"} and (
            node.attrs.get("id") or any(word in classes for word in ("candidate", "option", "response", "branch", "group"))
        ):
            nested = {child.attrs.get("id") for child in descendants(node)}
            groups.append({
                "id": node.attrs.get("id"), "class": node.attrs.get("class"),
                "messageAnchors": [anchor for anchor in message_order if anchor in nested],
            })
    first_anchors = {}
    for message in messages:
        speaker_id = message.get("speakerId")
        if speaker_id and speaker_id not in first_anchors and message.get("anchorId"):
            first_anchors[speaker_id] = message["anchorId"]
    participant_nodes = [n for n in descendants(transcript)
                         if has_class(n, "participant") or has_class(n, "participant-link")]
    participants = []
    for order, node in enumerate(participant_nodes, 1):
        speaker_id = node.attrs.get("data-speaker-id")
        href = node.attrs.get("href")
        first_anchor = href[1:] if href and href.startswith("#") else first_anchors.get(speaker_id)
        participants.append({
            "speakerId": speaker_id,
            "variantId": variant_refs.get(id(node)),
            "side": node.attrs.get("data-side"),
            "order": order,
            "firstAnchor": first_anchor,
            "href": href,
        })
    if not participant_nodes:
        variant_by_speaker = {}
        for message in messages:
            speaker_id = message.get("speakerId")
            key = message.get("anchorId") or f"sequence:{message.get('sequence')}"
            variant_id = (message_variant_refs or {}).get(key)
            if (speaker_id and speaker_id.lower() not in UNKNOWN_SPEAKER_IDS and variant_id):
                variant_by_speaker.setdefault(speaker_id, (message, variant_id))
        for order, (speaker_id, (message, variant_id)) in enumerate(variant_by_speaker.items(), 1):
            first_anchor = message.get("anchorId")
            participants.append({
                "speakerId": speaker_id,
                "variantId": variant_id,
                "side": message.get("side") or "left",
                "order": order,
                "firstAnchor": first_anchor,
                "href": ("#" + first_anchor) if first_anchor else None,
            })
    return groups, participants


def playback(rows):
    enum_aliases = {
        "confirmed": "confirmed",
        "conditional-reference-only": "conditional-reference-only",
        "unconfirmed": "unconfirmed",
    }
    enums = {
        enum_aliases.get(re.sub(r"[_\s]+", "-", value.strip().lower()), "unconfirmed")
        for row in rows for key, value in row.items()
        if key.lower() == "playback_eligibility" and value.strip()
    }
    proven = any(
        value.strip().lower() in {"yes", "true", "confirmed", "是"}
        for row in rows for key, value in row.items()
        if key.lower() == "current_playback_proven"
    )
    condition_reference = any(
        row.get("reference_relation", "").strip().lower() == "response_condition_reference"
        or (
            row.get("condition_operator", "").strip() and
            row.get("source_path", "").strip() and
            row.get("source_line", "").strip().isdigit() and
            row.get("type", "").strip().lower() == "heard_speak_sound_event_condition"
        )
        for row in rows
    )
    if enums == {"confirmed"}:
        status = "confirmed"
    elif enums == {"conditional-reference-only"}:
        status = "conditional-reference-only"
    elif enums:
        status = "unconfirmed"
    elif proven:
        status = "confirmed"
    elif condition_reference:
        status = "conditional-reference-only"
    else:
        status = "unconfirmed"
    return status


def apply_personality_transcript(transcript, row, locale):
    chinese = locale == "zh-tw"
    note_text = (
        "角色建立畫面顯示的性格介紹文字。圖示代表職業，並非固定人物肖像；"
        "試聽另有音訊設定，尚未確認與此段文字完全一致。"
        if chinese else
        "Personality introduction text displayed during character creation. The icon identifies "
        "the class, not a fixed person. Voice samples are configured separately; an exact spoken "
        "match to this text has not been confirmed."
    )
    note = get_first(transcript, lambda n: has_class(n, "note"))
    message = get_first(transcript, lambda n: has_class(n, "message"))
    if note is None or message is None:
        raise SourceError(f"personality alias {row.get('event_id')} has no note or message")
    note.children = [note_text]

    avatar = get_first(message, lambda n: has_class(n, "avatar"))
    if avatar is None or avatar.parent is None or "portrait-missing" not in (avatar.attrs.get("class") or "").split():
        raise SourceError(f"personality alias {row.get('event_id')} has no explicit missing portrait slot")
    name_field = "speaker_zh_tw" if chinese else "speaker_en"
    archetype_field = "archetype_zh_tw" if chinese else "archetype_en"
    role = row.get("character_voice", "").strip()
    portrait_url = row.get("portrait_url", "").strip()
    display_name = row.get(name_field, "")
    portrait_alt = row.get(archetype_field, "")
    if not role or not portrait_url or not display_name or not portrait_alt:
        raise SourceError(f"personality alias {row.get('event_id')} lacks localized speaker evidence")

    replacement = Node("img", {
        "class": "avatar", "src": portrait_url, "alt": portrait_alt,
        "loading": "lazy",
    }, parent=avatar.parent)
    avatar.parent.children[avatar.parent.children.index(avatar)] = replacement
    speaker = get_first(message, lambda n: has_class(n, "speaker"))
    if speaker is None:
        raise SourceError(f"personality alias {row.get('event_id')} has no speaker label")
    speaker.children = [display_name + ("：" if chinese else ":")]
    message.attrs["data-speaker-id"] = role


def anchor_metadata(node):
    return {"url": node.attrs.get("href"), "label": text_content(node).strip()}


def heading_text_without(node, excluded):
    parts = []

    def visit(item):
        if item is excluded:
            return
        if isinstance(item, str):
            parts.append(item)
        elif item.tag != "br":
            for child in item.children:
                visit(child)

    if node:
        visit(node)
    return "".join(parts).strip()


def page_metadata(site_root, site_page, locale, event_ids):
    tree = TreeParser()
    tree.feed(site_page.read_bytes().decode("utf-8-sig"))
    canonical = get_first(tree.root, lambda n: n.tag == "link" and
                          "canonical" in (n.attrs.get("rel") or "").split())
    canonical_url = canonical.attrs.get("href") if canonical else None
    title_node = get_first(tree.root, lambda n: n.tag == "title")
    title = text_content(title_node).strip() if title_node else ""
    if not title:
        heading = get_first(tree.root, lambda n: n.tag == "h1")
        title = text_content(heading).strip() if heading else None
    description_node = get_first(tree.root, lambda n: n.tag == "meta" and
                                 (n.attrs.get("name") or "").lower() == "description")
    description = description_node.attrs.get("content") if description_node else None
    relative = "/" + site_page.relative_to(site_root).as_posix()
    url = canonical_url or relative
    page_id = site_page.parent.name if site_page.name.lower() == "index.html" else site_page.stem

    language_url = None
    home_url = None
    breadcrumb = get_first(tree.root, lambda n: n.tag == "nav" and
                           "dt-breadcrumb" in (n.attrs.get("class") or "").split())
    breadcrumb_links = [n for n in descendants(breadcrumb)] if breadcrumb else []
    breadcrumb_links = [n for n in breadcrumb_links if n.tag == "a" and n.attrs.get("href")]
    category_anchor = breadcrumb_links[-1] if len(breadcrumb_links) > 1 else None
    if category_anchor is None:
        back = get_first(tree.root, lambda n: n.tag == "a" and
                         "preview-back" in (n.attrs.get("class") or "").split())
        category_anchor = back
    if category_anchor:
        category_url = category_anchor.attrs.get("href")
    else:
        category_url = None

    for node in descendants(tree.root):
        if node.tag != "link" or "alternate" not in (node.attrs.get("rel") or "").split():
            continue
        hreflang = (node.attrs.get("hreflang") or "").lower()
        if hreflang and ((locale == "en" and hreflang.startswith("zh")) or
                         (locale == "zh-tw" and hreflang.startswith("en"))):
            language_url = node.attrs.get("href")
            break
    if not language_url:
        language_toggle = get_first(tree.root, lambda n: n.tag == "a" and n.attrs.get("href") and
                                    ("language-toggle" in (n.attrs.get("class") or "").split() or
                                     "language" in (n.attrs.get("class") or "").split()))
        if language_toggle:
            language_url = language_toggle.attrs.get("href")
    brand = get_first(tree.root, lambda n: n.tag == "a" and
                      "dt-brand" in (n.attrs.get("class") or "").split())
    if brand:
        home_url = brand.attrs.get("href")
    if not home_url:
        home_url = "/darktide/"

    def local_path(value):
        return re.sub(r"^https?://[^/]+", "", value or "")

    if not category_url or local_path(category_url).rstrip("/") in {"/darktide", "/darktide/en"}:
        route_parts = [part for part in local_path(url).split("/") if part]
        if route_parts[:1] == ["darktide"]:
            route_parts = route_parts[1:]
        if route_parts[:1] == ["en"]:
            route_parts = route_parts[1:]
        if route_parts and route_parts[-1].lower() == "index.html":
            route_parts.pop()
        if len(route_parts) > 1:
            route_parts.pop()
        locale_prefix = "/darktide/en" if locale == "en" else "/darktide"
        category_url = locale_prefix + ("/" + "/".join(route_parts) if route_parts else "") + "/"

    def relation_link(relation):
        node = get_first(tree.root, lambda n: n.tag == "a" and
                         relation in (n.attrs.get("rel") or "").split() and n.attrs.get("href"))
        return anchor_metadata(node) if node else None

    def page_link(node):
        return {
            "label": text_content(node), "url": node.attrs.get("href"),
            "target": node.attrs.get("target"), "rel": node.attrs.get("rel"),
            "attributes": dict(node.attrs),
        }

    footer_links = []
    for footer in (node for node in descendants(tree.root)
                   if node.tag == "footer" and has_class(node, "dialogue-footer")):
        footer_links.extend(
            page_link(node) for node in descendants(footer)
            if node.tag == "a" and node.attrs.get("href")
        )
    preview_toolbar = get_first(tree.root, lambda n: has_class(n, "preview-toolbar"))
    back_node = get_first(preview_toolbar, lambda n: n.tag == "a" and
                          has_class(n, "preview-back") and n.attrs.get("href")) if preview_toolbar else None
    back_link = page_link(back_node) if back_node else None

    source_links = []
    for node in descendants(tree.root):
        if node.tag != "a" or not node.attrs.get("href"):
            continue
        label = text_content(node).strip()
        href = node.attrs["href"]
        if not (re.search(r"(?:來源|source|evidence)", label, re.I) or
                re.search(r"(?:^|/)(?:source|source-catalog)(?:/|$)", href, re.I)):
            continue
        item = anchor_metadata(node)
        if item not in source_links:
            source_links.append(item)

    path = re.sub(r"^https?://[^/]+", "", url)
    path_parts = [part for part in path.split("/") if part]
    if path_parts[:1] == ["darktide"]:
        path_parts = path_parts[1:]
    if path_parts[:1] == ["en"]:
        path_parts = path_parts[1:]
    category = None
    if category_url:
        category_path = local_path(category_url)
        category_parts = [part for part in category_path.split("/") if part]
        if category_parts[:1] == ["darktide"]:
            category_parts = category_parts[1:]
        if category_parts[:1] == ["en"]:
            category_parts = category_parts[1:]
        category = category_parts[-1] if category_parts else None
    if not category and path_parts:
        category = path_parts[-2] if re.fullmatch(r"page-\d+", page_id) and len(path_parts) > 1 else path_parts[0]

    preview_header = get_first(tree.root, lambda n: n.tag == "header" and
                               "preview-header" in (n.attrs.get("class") or "").split())
    heading_node = get_first(preview_header, lambda n: n.tag == "h1") if preview_header else None
    number_node = get_first(heading_node, lambda n: n.tag in {"span", "strong"} and
                            has_any_class(n, ("event-number", "preview-number", "heading-number", "number"))) if heading_node else None
    title_node = get_first(heading_node, lambda n: n.tag in {"span", "strong"} and
                           has_any_class(n, ("preview-title", "heading-title", "event-title"))) if heading_node else None
    subtitle_node = get_first(preview_header, lambda n: n.tag in {"p", "span"} and
                              has_any_class(n, ("preview-summary", "preview-subtitle", "subtitle"))) if preview_header else None
    kicker_node = get_first(preview_header, lambda n: n.tag in {"p", "span"} and
                            has_any_class(n, ("preview-eyebrow", "preview-kicker", "kicker"))) if preview_header else None

    def heading_value(node):
        return text_content(node).strip() or None if node else None

    heading = {
        "number": heading_value(number_node),
        "title": (text_content(title_node).strip() if title_node else
                  heading_text_without(heading_node, number_node)) or None,
        "subtitle": heading_value(subtitle_node),
        "kicker": heading_value(kicker_node),
    }

    return {
        "url": url, "locale": locale, "category": category,
        "eventId": event_ids[0] if len(event_ids) == 1 else None,
        "pageId": page_id, "title": title, "description": description,
        "heading": heading,
        "languageUrl": language_url, "homeUrl": home_url,
        "categoryUrl": category_url, "previous": relation_link("prev"),
        "next": relation_link("next"), "sourceLinks": source_links,
        "footerLinks": footer_links, "backLink": back_link,
    }


def source_event_number(title):
    match = re.search(r"(?:subtitle|字幕)\s*(\d+)\b", title or "", re.I)
    return match.group(1) if match else None


def explicit_voice_profile(metadata, speakers):
    profile_rows = []
    for line_number, line in enumerate(metadata.get("markdown", "").splitlines(), 1):
        matches = re.findall(
            r"\bvoice\s+profile\s*[:：]\s*`([A-Za-z][A-Za-z0-9_]*)`",
            line, re.I,
        )
        for profile_id in matches:
            contextual = bool(re.search(r"(?:說話者|speaker)\s*[:：]", line, re.I))
            profile_rows.append((profile_id, line_number, contextual))
    if len(profile_rows) != 1 or not profile_rows[0][2]:
        return None
    profile_id, line_number, _ = profile_rows[0]
    known_profiles = {str(item.get("speakerId") or "") for item in speakers}
    if profile_id.lower() in UNKNOWN_SPEAKER_IDS or profile_id not in known_profiles:
        return None
    return {
        "speakerId": profile_id,
        "sourceLine": line_number,
        "relation": "explicit single voice-profile mapping in event speaker context",
    }


def source_evidence_for(event_id, metadata, catalog, usage_rows, speakers):
    document_path = f"source/{event_id}.md"
    evidence = []

    def add(path, line, relation, url=None, source_sha=None, hash_value=None,
            evidence_id=None, speaker_id=None, reference=None):
        number = int(line) if str(line or "").isdigit() else None
        safe_path = str(path).replace("\\", "/") if path else None
        if safe_path and (re.match(r"^(?:[A-Za-z]:/|/|//|file:)", safe_path, re.I) or
                          re.search(r"(?:^|/)Users/[^/]+/", safe_path, re.I)):
            safe_path = None
        safe_url = str(url).strip() if url else None
        if safe_url and (re.match(r"^(?:[A-Za-z]:[\\/]|\\\\|file:)", safe_url, re.I) or
                         re.search(r"(?:^|[/\\])Users[/\\][^/\\]+[/\\]", safe_url, re.I)):
            safe_url = None
        item = {
            "url": safe_url, "path": safe_path,
            "startLine": number, "endLine": number,
            "relation": relation,
        }
        if source_sha:
            item["sourceSha256"] = source_sha
        if hash_value:
            item["hash"] = hash_value
        if evidence_id:
            item["evidenceId"] = evidence_id
        if speaker_id:
            item["speakerId"] = speaker_id
        if reference is not None:
            item["reference"] = reference
        if item not in evidence:
            evidence.append(item)

    for item in metadata.get("explicitHashEvidence", []):
        add(document_path, item.get("sourceLine"), "explicit subtitle hash identity",
            source_sha=metadata.get("sourceSha256"), hash_value=item.get("hash"))
    for row in metadata.get("tables", []):
        value = row_hash(row)
        if value:
            add(document_path, row.get("__sourceLine"), "explicit source hash/sequence relation",
                source_sha=metadata.get("sourceSha256"), hash_value=value)
    speaker_mapping = explicit_voice_profile(metadata, speakers)
    if speaker_mapping:
        add(document_path, speaker_mapping["sourceLine"], speaker_mapping["relation"],
            source_sha=metadata.get("sourceSha256"), speaker_id=speaker_mapping["speakerId"])
    for link in metadata.get("links", []):
        add(document_path, link.get("sourceLine"), link.get("label") or "source link",
            url=link.get("url"), source_sha=metadata.get("sourceSha256"),
            reference=link.get("reference"))
    for entry in catalog:
        catalog_path = f"source-catalog/{entry['source']}"
        for link in entry.get("links", []):
            add(catalog_path, link.get("sourceLine"), link.get("label") or "catalog link",
                url=link.get("url"), source_sha=entry.get("sourceSha256"))
    for row in usage_rows:
        source_path = (usage_value(row, "source_path", "classification_source_path",
                                   "source_catalog_doc_path") or
                       Path(row.get("_source", "")).name)
        source_line = usage_value(row, "source_line", "sourceLine", "line")
        relation = (usage_value(row, "reference_relation", "usage_classification", "type") or
                    "usage evidence")
        url = usage_value(row, "authority_source_link_from_catalog", "source_link", "source_url")
        evidence_id = usage_value(row, "evidence_ref", "evidence_id", "evidenceId")
        if source_path or url or evidence_id:
            add(source_path, source_line, relation, url=url, evidence_id=evidence_id,
                hash_value=next(iter(sorted(usage_hashes(row))), None))
    return evidence


def speaker_evidence_for(messages, speakers, dialogue_evidence_refs=None):
    profiles = {str(item.get("speakerId")): item for item in speakers}
    evidence = {}
    for message in messages:
        speaker_id = str(message.get("speakerId") or "")
        if not speaker_id or speaker_id.lower() in UNKNOWN_SPEAKER_IDS:
            continue
        profile = profiles.get(speaker_id)
        if not profile:
            continue
        variant_id = message.get("variantId")
        if speaker_id not in evidence:
            evidence[speaker_id] = {
                "path": profile.get("sourcePath"),
                "sourceLine": profile.get("sourceLine"),
                "url": next((value for value in profile.get("sourceUrls", [])
                             if "/blob/" in value), None),
                "relation": "explicit source speaker profile",
                "variantIds": [],
            }
        if variant_id and variant_id not in evidence[speaker_id]["variantIds"]:
            evidence[speaker_id]["variantIds"].append(variant_id)
    for speaker_id, references in (dialogue_evidence_refs or {}).items():
        profile = profiles.get(speaker_id)
        if not profile:
            continue
        if speaker_id not in evidence:
            evidence[speaker_id] = {
                "path": profile.get("sourcePath"),
                "sourceLine": profile.get("sourceLine"),
                "url": next((value for value in profile.get("sourceUrls", [])
                             if "/blob/" in value), None),
                "relation": "explicit source speaker profile",
                "variantIds": [],
            }
        evidence[speaker_id]["dialogueEvidenceRefs"] = list(dict.fromkeys(references))
    return evidence


def provenance_for(commit):
    return {
        "dialogueRepository": "authoritative-dialogue-source",
        "dialogueCommit": commit,
        "sourceCommit": GAME_SOURCE_COMMIT,
        "steamBuild": "25606770",
    }


def resource_snapshot_for(event_ids, source_metadata, resource_index, resource_info, page_locale):
    hashes = set().union(*(hashes_in(source_metadata[event_id]) for event_id in event_ids))
    locales = {
        locale: {
            "path": f"jsonl/{locale}/subtitles.jsonl",
            "sha256": resource_info[locale]["sha256"],
            "size": resource_info[locale]["size"],
            "manifest": resource_info[locale]["manifest"],
        }
        for locale in LOCALES
    }
    entries = {}
    for hash_value in sorted(hashes):
        entry = {
            locale: [{
                "locKey": row.get("locKey"),
                "entryIndex": row.get("entryIndex"),
                "sourceLine": row.get("sourceLine"),
            } for row in resource_index[locale].get(hash_value, [])]
            for locale in LOCALES
        }
        primary_rows = resource_index[page_locale].get(hash_value, [])
        has_primary_text = any(isinstance(row.get("text"), str) for row in primary_rows)
        if not has_primary_text and page_locale == "zh-tw" and source_text_for(hash_value, resource_index["en"]) is not None:
            entry["displayLocale"] = "en"
        entries[hash_value] = entry
    return {"locales": locales, "entries": entries}


def make_page(root, event_id, locale, source_file, resource_index,
              usage_rows, speakers, catalog, variant_registry,
              fallback_resource_index=None,
              personality_row=None, anchor_prefix=None, event_urls=None,
              commit=None, repository_root=None, repository_base=None,
              source_event_urls=None):
    source_root, transcript, title, _ = parse_html_document(source_file)
    participant_sections = []
    inline_participant_bars = False
    for node in descendants(source_root):
        if not has_class(node, "participants"):
            continue
        if node_contains(transcript, node):
            inline_participant_bars = True
            continue
        if any(node_contains(section, node) for section in participant_sections):
            continue
        participant_sections.append(node)
    if personality_row is not None:
        apply_personality_transcript(transcript, personality_row, locale)
    metadata = parse_source_md(root / "source" / (event_id + ".md"))
    if commit:
        resolve_source_metadata_links(
            root, event_id, metadata, commit, repository_root,
            repository_base, locale, source_event_urls or event_urls,
        )
    hashes = hashes_in(metadata)
    profile_mapping = explicit_voice_profile(metadata, speakers)
    if profile_mapping:
        message_nodes = class_nodes(transcript, "message")
        existing_roles = {node.attrs.get("data-speaker-id") for node in message_nodes
                          if node.attrs.get("data-speaker-id")}
        if not existing_roles or existing_roles == {profile_mapping["speakerId"]}:
            for order, node in enumerate(message_nodes, 1):
                if not node.attrs.get("data-speaker-id"):
                    node.attrs["data-speaker-id"] = profile_mapping["speakerId"]
                if not node.attrs.get("id"):
                    sequence = node.attrs.get("data-sequence") or str(order)
                    node.attrs["id"] = f"{event_id}-message-{sequence}"
                if not node.attrs.get("data-side") and not node.attrs.get("data-role"):
                    node.attrs["data-side"] = "left"
    messages = parse_messages(transcript)
    variant_records, variant_refs, message_variant_refs = collect_speaker_variants(
        transcript, locale, speakers, participant_roots=participant_sections,
    )
    for variant_id, record in variant_records.items():
        previous = variant_registry.get(variant_id)
        if previous is not None and previous != record:
            raise SourceError(f"speaker variant ID collision: {variant_id}")
        variant_registry[variant_id] = record
    warnings = list(metadata["warnings"])
    known_speaker_ids = {str(item.get("speakerId") or "") for item in speakers}
    speaker_evidence_gaps = []
    unknown_speaker_count = sum(
        1 for message in messages
        if message.get("speakerId") not in known_speaker_ids or
        str(message.get("speakerId") or "").lower() in UNKNOWN_SPEAKER_IDS
    )
    if unknown_speaker_count:
        speaker_evidence_gaps.append({
            "kind": "speaker-mapping",
            "messageCount": unknown_speaker_count,
            "reason": "No explicit source profile mapping is available for these message speaker IDs.",
        })
    missing = hashes - resource_index.keys()
    if missing:
        warnings.append(f"{len(missing)} cited hash(es) are absent from {locale} subtitles JSONL")
    message_links = associate_message_hashes(messages, metadata)
    for message in messages:
        link_key = message.get("anchorId") or f"sequence:{message.get('sequence')}"
        source_hash = message_links.get(link_key)
        if source_hash is not None:
            message["sourceHash"] = source_hash
        else:
            message.pop("sourceHash", None)
        if source_hash is None:
            warnings.append(f"message {message.get('anchorId') or message.get('sequence') or 'without anchor'} has no explicit hash mapping")
        elif source_text_for(source_hash, resource_index) is None:
            fallback_text = (source_text_for(source_hash, fallback_resource_index)
                             if locale == "zh-tw" and fallback_resource_index else None)
            has_local_text = any(isinstance(row.get("text"), str)
                                 for row in resource_index.get(source_hash, []))
            if fallback_text is not None and not has_local_text:
                warnings.append(f"hash {source_hash} is shown from the English source because zh-tw has no subtitle resource")
            else:
                warnings.append(f"hash {source_hash} has conflicting or missing {locale} resource text")
            message_node = next((node for node in class_nodes(transcript, "message")
                                 if node.attrs.get("id") == message.get("anchorId")), None)
            line = get_first(message_node, lambda n: has_class(n, "line")) if message_node else None
            has_bubble = get_first(line, lambda n: has_class(n, "bubble")) if line else None
            if fallback_text is not None and not has_local_text and line is None:
                raise SourceError(f"message for fallback hash {source_hash} has no line slot")
            if fallback_text is not None and not has_local_text and has_bubble:
                raise SourceError(f"message for fallback hash {source_hash} unexpectedly has a source bubble")
        variant_id = message_variant_refs.get(link_key)
        if variant_id:
            message["variantId"] = variant_id
        else:
            message.pop("variantId", None)
        if anchor_prefix and message.get("anchorId"):
            message["anchorId"] = prefixed_id(message["anchorId"], anchor_prefix)
    usage = usage_rows
    groups, participants = groups_and_participants(
        transcript, parse_messages(transcript), variant_refs, message_variant_refs,
    )
    participant_bars = [participant_bar_record(section, variant_refs, anchor_prefix)
                        for section in participant_sections]
    if participant_bars:
        participants = []
        for bar_index, bar in enumerate(participant_bars):
            rows = bar.pop("rows")
            participant_indexes = []
            for row in rows:
                row["barIndex"] = bar_index
                participant_indexes.append(len(participants))
                participants.append(row)
            bar["participantIndexes"] = participant_indexes
    if anchor_prefix:
        for group in groups:
            group["messageAnchors"] = [prefixed_id(value, anchor_prefix)
                                       for value in group["messageAnchors"]]
        for participant in participants:
            if participant.get("firstAnchor"):
                participant["firstAnchor"] = prefixed_id(participant["firstAnchor"], anchor_prefix)
            if participant.get("href", "").startswith("#"):
                participant["href"] = "#" + prefixed_id(participant["href"][1:], anchor_prefix)
    transcript_data = serialize_transcript(
        transcript, parse_messages(transcript), message_links, resource_index,
        variant_refs, locale, fallback_resource_index=fallback_resource_index,
        anchor_prefix=anchor_prefix, event_urls=event_urls,
    )
    page = {
        "eventId": event_id,
        "eventNumber": source_event_number(title),
        "title": title,
        "firstAnchor": next((message.get("anchorId") for message in messages
                             if message.get("anchorId")), None),
        "transcript": transcript_data,
        "scenes": [{"anchorId": n.attrs.get("id"), "index": i}
                   for i, n in enumerate(class_nodes(transcript, "scene"))],
        "messages": messages, "participants": participants, "candidateGroups": groups,
        "participantBars": participant_bars,
        "hasInlineParticipantBars": inline_participant_bars,
        "playbackEligibility": playback(usage),
        "classification": usage,
        "sourceDocument": {"path": f"source/{event_id}.md",
                           "sha256": metadata.get("sourceSha256")},
        "sourceEvidence": source_evidence_for(
            event_id, metadata, catalog.get(event_id, []), usage, speakers,
        ),
        "evidenceGaps": metadata["evidenceGaps"],
        "sourceWarnings": metadata.get("sourceWarnings", []),
        "speakerEvidenceGaps": speaker_evidence_gaps,
        "resourceHashes": sorted(hashes),
        "warnings": warnings,
    }
    return page, transcript


class TranscriptRangeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.offset = 0
        self.active = False
        self.depth = 0
        self.participant_depth = 0
        self.participant_root_tag = None
        self.inner_start = 0
        self.ids = []
        self.ranges = []

    def pos(self):
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self.pos()
        raw = self.get_starttag_text() or ""
        data = dict(attrs)
        if not self.active and tag.lower() == "div" and "transcript" in (data.get("class") or "").split():
            self.active = True
            self.depth = 1
            self.inner_start = start + len(raw)
            self.ids = []
            return
        if self.active:
            if self.participant_depth:
                if tag.lower() not in VOID:
                    self.participant_depth += 1
                return
            if "participants" in (data.get("class") or "").split():
                self.participant_depth = 1
                self.participant_root_tag = tag.lower()
                if tag.lower() == "div":
                    self.depth += 1
                return
            if tag.lower() == "div":
                self.depth += 1
            if data.get("id"):
                self.ids.append(data["id"])

    def handle_startendtag(self, tag, attrs):
        if self.active:
            if self.participant_depth:
                return
            data = dict(attrs)
            if "participants" in (data.get("class") or "").split():
                return
            if data.get("id"):
                self.ids.append(data["id"])

    def handle_endtag(self, tag):
        start = self.pos()
        if self.active and self.participant_depth:
            if tag.lower() not in VOID:
                self.participant_depth -= 1
                if self.participant_depth == 0:
                    if self.participant_root_tag == "div":
                        self.depth -= 1
                    self.participant_root_tag = None
            return
        if self.active and tag.lower() == "div":
            self.depth -= 1
            if self.depth == 0:
                self.ranges.append((self.inner_start, start, list(dict.fromkeys(self.ids))))
                self.active = False
                self.ids = []

    def handle_data(self, data):
        pass

    def handle_entityref(self, name):
        pass

    def handle_charref(self, name):
        pass

    def handle_comment(self, data):
        pass

    def feed_source(self, value):
        self.source = value
        self.lines = value.splitlines(keepends=True)
        self.line_starts = []
        offset = 0
        for line in self.lines:
            self.line_starts.append(offset)
            offset += len(line)
        super().feed(value)


def static_anchors(page_html: str):
    parser = TranscriptRangeParser()
    parser.feed_source(page_html)
    if not parser.ranges:
        raise SourceError("prepared site HTML has no transcript div")
    return parser.ranges


class ParticipantRangeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.active_tag = None
        self.depth = 0
        self.start = 0
        self.ids = []
        self.targets = []
        self.ranges = []

    def pos(self):
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    @staticmethod
    def is_participant_container(tag, attrs):
        return (tag.lower() in {"section", "div", "aside"} and
                "participants" in (dict(attrs).get("class") or "").split())

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if self.active_tag:
            if data.get("id"):
                self.ids.append(data["id"])
            href = data.get("href") or ""
            if tag.lower() == "a" and href.startswith("#"):
                self.targets.append(unquote(href[1:]))
            if tag.lower() == self.active_tag and tag.lower() not in VOID:
                self.depth += 1
            return
        if self.is_participant_container(tag, attrs):
            self.active_tag = tag.lower()
            self.depth = 1
            self.start = self.pos()
            self.ids = [data["id"]] if data.get("id") else []
            self.targets = []

    def handle_startendtag(self, tag, attrs):
        data = dict(attrs)
        if self.active_tag:
            if data.get("id"):
                self.ids.append(data["id"])
            href = data.get("href") or ""
            if tag.lower() == "a" and href.startswith("#"):
                self.targets.append(unquote(href[1:]))
            return
        if not self.is_participant_container(tag, attrs):
            return
        start = self.pos()
        end = self.source.find(">", start)
        if end < 0:
            raise SourceError("participant section has an unterminated start tag")
        self.ranges.append((start, end + 1, [data["id"]] if data.get("id") else [], []))

    def handle_endtag(self, tag):
        if not self.active_tag or tag.lower() != self.active_tag:
            return
        self.depth -= 1
        if self.depth == 0:
            start = self.pos()
            end = self.source.find(">", start)
            if end < 0:
                raise SourceError("participant section has an unterminated end tag")
            self.ranges.append((self.start, end + 1,
                                list(dict.fromkeys(self.ids)),
                                list(dict.fromkeys(self.targets))))
            self.active_tag = None
            self.ids = []
            self.targets = []

    def feed_source(self, value):
        self.source = value
        self.lines = value.splitlines(keepends=True)
        self.line_starts = []
        offset = 0
        for line in self.lines:
            self.line_starts.append(offset)
            offset += len(line)
        super().feed(value)


def static_participant_ranges(page_html: str):
    parser = ParticipantRangeParser()
    parser.feed_source(page_html)
    if parser.active_tag:
        raise SourceError("prepared page has an unterminated participants section")
    return parser.ranges


def anchor_placeholders(ids: list[str], role=False) -> str:
    result = []
    for value in ids:
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]*", value):
            result.append('<span class="reader-anchor-target" data-reader-anchor id="' +
                          html.escape(value, quote=True) + '" aria-hidden="true"' +
                          (' data-reader-role-anchor' if role else '') + '></span>')
    return "\n".join(result)


def install_page(path: Path, locale: str, content_version: str, reader_version: str,
                 event_ids=None, mapping_kind="direct-event") -> list[str]:
    source = path.read_bytes().decode("utf-8-sig")
    ranges = static_anchors(source)
    participant_ranges = static_participant_ranges(source)
    event_ids = list(event_ids or [])
    if len(ranges) != len(event_ids):
        raise SourceError("transcript containers do not match their participant-anchor event mapping")
    prefix_ids = mapping_kind in {"paginated-unlinked", "personality-alias"}
    loading = "Loading dialogue…" if locale == "en" else "正在載入對話…"
    noscript = "Enable JavaScript to load this dialogue." if locale == "en" else "啟用 JavaScript 以載入對話。"
    updated = source
    all_ids = []
    replacements = []
    transcript_anchor_ids = []
    for index, (inner_start, inner_end, ids) in enumerate(ranges):
        prefix = event_ids[index] if prefix_ids else None
        installed_ids = [prefixed_id(value, prefix) for value in ids] if prefix else ids
        transcript_anchor_ids.extend(installed_ids)
        all_ids.extend(installed_ids)
        body = (anchor_placeholders(installed_ids) +
                '\n<div class="reader-status" role="status" aria-live="polite">' +
                html.escape(loading) +
                '</div>\n<noscript><p class="reader-noscript">' + html.escape(noscript) +
                "</p></noscript>")
        replacements.append((inner_start, inner_end, body))
    role_anchor_ids = set()
    for participant_start, participant_end, ids, targets in participant_ranges:
        nested_in_transcript = any(
            inner_start <= participant_start and participant_end <= inner_end
            for inner_start, inner_end, _ in ranges
        )
        overlaps_transcript = any(
            participant_start < inner_end and inner_start < participant_end
            for inner_start, inner_end, _ in ranges
        )
        if nested_in_transcript:
            continue
        if overlaps_transcript:
            raise SourceError("participants section overlaps a transcript boundary")
        prefix = None
        if prefix_ids:
            target_indexes = {
                index for target in targets
                for index, (_, _, transcript_ids) in enumerate(ranges)
                if target in transcript_ids
            }
            if len(target_indexes) > 1:
                raise SourceError("participant bar points to more than one transcript event")
            if target_indexes:
                prefix = event_ids[next(iter(target_indexes))]
            elif len(event_ids) == 1:
                prefix = event_ids[0]
            else:
                raise SourceError("multi-event participant bar has no unique source-event anchor")
        installed_ids = [prefixed_id(value, prefix) for value in ids] if prefix else ids
        if any(value in role_anchor_ids or value in transcript_anchor_ids
               for value in installed_ids):
            raise SourceError("participant and transcript anchors contain a duplicate ID")
        role_anchor_ids.update(installed_ids)
        replacements.append((participant_start, participant_end,
                             anchor_placeholders(installed_ids, role=True)))
    for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        updated = updated[:start] + replacement + updated[end:]
    tag = ('<script src="/assets/js/darktide-dialogue.js?v=' + reader_version +
           '" defer data-locale="' + locale + '" data-json="data.json?v=' +
           content_version + '" data-speakers="/darktide/data/speakers/' + locale +
           '.json?v=' + content_version + '" data-content-version="' +
           content_version + '" data-reader-version="' + reader_version + '"></script>')
    old_script = re.compile(r'<script\b[^>]*darktide-dialogue(?:-reader)?\.js[^>]*>\s*</script>', re.I)
    if old_script.search(updated):
        updated = old_script.sub(tag, updated)
    else:
        close = re.search(r"</body\s*>", updated, re.I)
        if not close:
            raise SourceError(f"prepared page has no closing body: {path}")
        updated = updated[:close.start()] + tag + "\n" + updated[close.start():]
    path.write_text(updated, encoding="utf-8", newline="")
    return list(dict.fromkeys(all_ids))


def compact_dialogue_wire(metadata: dict[str, Any], transcripts: list[list[Any]]) -> tuple[dict[str, Any], list[list[Any]]]:
    metadata = dict(metadata)
    source_documents = metadata.get("sourceDocuments", {})
    source_evidence = metadata.get("sourceEvidence", {})
    evidence_gaps = metadata.get("evidenceGaps", {})
    if all(isinstance(value, dict) for value in
           (source_documents, source_evidence, evidence_gaps)):
        document_ids = list(source_documents)
        evidence_ids = list(source_evidence)
        gap_ids = list(evidence_gaps)
        document_indexes = {value: index for index, value in enumerate(document_ids)}
        evidence_indexes = {value: index for index, value in enumerate(evidence_ids)}
        gap_indexes = {value: index for index, value in enumerate(gap_ids)}
        document_rows = []
        for document_id in document_ids:
            row = dict(source_documents[document_id])
            if "evidenceRefs" in row:
                try:
                    row["evidenceRefs"] = [evidence_indexes[value]
                                            for value in row["evidenceRefs"]]
                except KeyError as error:
                    raise SourceError(f"source document references unknown evidence ID: {error}") from error
            if "evidenceGapRefs" in row:
                try:
                    row["evidenceGapRefs"] = [gap_indexes[value]
                                               for value in row["evidenceGapRefs"]]
                except KeyError as error:
                    raise SourceError(f"source document references unknown evidence gap ID: {error}") from error
            document_rows.append(row)
        evidence_rows = []
        for evidence_id in evidence_ids:
            row = dict(source_evidence[evidence_id])
            document_ref = row.get("documentRef")
            if document_ref is not None:
                try:
                    row["documentRef"] = document_indexes[document_ref]
                except KeyError as error:
                    raise SourceError(f"source evidence references unknown document ID: {error}") from error
            evidence_rows.append(row)
        metadata["sourceDocuments"] = {
            "ids": document_ids, "rows": document_rows,
            "references": {
                "evidenceRefs": "sourceEvidence.ids",
                "evidenceGapRefs": "evidenceGaps.ids",
            },
        }
        metadata["sourceEvidence"] = {
            "ids": evidence_ids, "rows": evidence_rows,
            "references": {"documentRef": "sourceDocuments.ids"},
        }
        metadata["evidenceGaps"] = {"ids": gap_ids,
                                    "rows": [dict(evidence_gaps[value]) for value in gap_ids]}

    field_counts = Counter()
    string_counts = Counter()
    tag_counts = Counter()
    attribute_counts = Counter()

    def collect_metadata(value):
        if isinstance(value, dict):
            for key, item in value.items():
                field_counts[key] += 1
                collect_metadata(item)
        elif isinstance(value, list):
            for item in value:
                collect_metadata(item)
        elif isinstance(value, str):
            string_counts[value] += 1

    def collect_transcript(value):
        if isinstance(value, str):
            string_counts[value] += 1
            return
        tag, attrs, children = value
        tag_counts[tag] += 1
        for key, item in attrs.items():
            attribute_counts[key] += 1
            if isinstance(item, str):
                string_counts[item] += 1
        for child in children:
            collect_transcript(child)

    collect_metadata(metadata)
    for transcript in transcripts:
        for node in transcript:
            collect_transcript(node)

    fields = sorted(field_counts, key=lambda key: (-field_counts[key], key))
    field_indexes = {key: index for index, key in enumerate(fields)}
    tags = sorted(tag_counts, key=lambda tag: (-tag_counts[tag], tag))
    tag_indexes = {tag: index for index, tag in enumerate(tags)}
    attributes = sorted(attribute_counts, key=lambda key: (-attribute_counts[key], key))
    attribute_indexes = {key: index for index, key in enumerate(attributes)}

    def encoded_size(value):
        return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    candidates = sorted(
        (value for value, count in string_counts.items() if count > 1),
        key=lambda value: (-(string_counts[value] - 1) * encoded_size(value), value),
    )
    strings = []
    for value in candidates:
        index = len(strings)
        source_size = encoded_size(value)
        reference_size = encoded_size(["s", index])
        count = string_counts[value]
        if count * source_size > source_size + 1 + count * reference_size:
            strings.append(value)
    string_indexes = {value: index for index, value in enumerate(strings)}

    def encode_value(value):
        if isinstance(value, dict):
            row = ["#"]
            for key, item in value.items():
                row.extend((field_indexes[key], encode_value(item)))
            return row
        if isinstance(value, list):
            row = [encode_value(item) for item in value]
            if row and isinstance(row[0], str) and row[0] in {"#", "~", "s"}:
                return ["~", *row]
            return row
        if isinstance(value, str) and value in string_indexes:
            return ["s", string_indexes[value]]
        return value

    def encode_transcript(value):
        if isinstance(value, str):
            return encode_value(value)
        tag, attrs, children = value
        packed_attrs = []
        for key, item in attrs.items():
            packed_attrs.extend((attribute_indexes[key], encode_value(item)))
        return [
            tag_indexes[tag], packed_attrs,
            [encode_transcript(child) for child in children],
        ]

    wire = {
        "version": 2,
        "fields": fields,
        "strings": strings,
        "tags": tags,
        "attributes": attributes,
        "metadata": encode_value(metadata),
    }
    return wire, [[encode_transcript(node) for node in transcript] for transcript in transcripts]


def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
                    encoding="utf-8", newline="")


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--site", required=True, type=Path)
    cli.add_argument("--dialogue-source", required=True, type=Path)
    cli.add_argument("--locale-resources", required=True, type=Path)
    cli.add_argument("--classification-source", required=True, type=Path)
    cli.add_argument("--dialogue-commit", required=True)
    args = cli.parse_args()

    site = resolve(args.site)
    source = dialogue_root(args.dialogue_source)
    resources = resolve(args.locale_resources)
    classifications = resolve(args.classification_source)
    if not site.is_dir():
        raise SourceError("--site must be an existing prepared website tree")
    reject_overlap(site, [
        ("dialogue source", source), ("locale resources", resources),
        ("classification source", classifications),
    ])
    commit = validate_commit(source, args.dialogue_commit)
    repository_root, repository_remote = dialogue_repository_info(source)
    repository_base = github_repository_base(repository_remote)
    source_ids = {p.stem for locale in LOCALES
                  for p in (source / locale / "events").glob("*.html")}
    usage, usage_audit, usage_evidence_index = read_usage(classifications)
    usage_by_hash = {}
    for row in usage:
        for hash_value in usage_hashes(row):
            usage_by_hash.setdefault(hash_value, []).append(row)
    personality_events = {}
    personality_rows = {}
    for row in usage:
        personality_source = " ".join((
            row.get("_source", ""),
            usage_value(row, "usage_classification", "reference_relation",
                        "classification_source_path", "source_catalog_doc_path"),
        )).lower()
        if "personality" not in personality_source:
            continue
        personality_fields = (
            "character_voice", "speaker_zh_tw", "speaker_en", "portrait_url",
            "archetype_zh_tw", "archetype_en",
        )
        if not all(usage_value(row, field) for field in personality_fields):
            continue
        page_id = usage_value(row, "event_id", "personality_page_id", "page_id")
        if not page_id:
            source_doc = usage_value(row, "source_catalog_doc_path", "classification_source_path")
            page_match = re.search(r"(character_personality_[a-z0-9_]+)", source_doc, re.I)
            page_id = page_match.group(1) if page_match else ""
        hash_values = usage_hashes(row)
        if page_id and len(hash_values) == 1:
            event_id = "unlinked_subtitle_" + next(iter(hash_values))
            existing = personality_events.get(page_id)
            if existing and existing != event_id:
                raise SourceError(f"personality alias {page_id} has conflicting source hashes")
            personality_events[page_id] = event_id
            previous_row = personality_rows.get((page_id, event_id))
            if previous_row and previous_row != row:
                raise SourceError(f"personality alias {page_id} has conflicting speaker evidence")
            personality_rows[(page_id, event_id)] = row
    page_rows = []
    for locale in LOCALES:
        locale_source_ids = {p.stem for p in (source / locale / "events").glob("*.html")}
        for target in site_pages(site, locale):
            ids, kind = page_source_ids(target, source_ids, personality_events)
            page_rows.append((locale, target, ids, kind, locale_source_ids))
    if not page_rows:
        raise SourceError("no prepared dialogue pages were found")
    page_info_by_target = {}
    event_urls_by_locale = {locale: {} for locale in LOCALES}
    event_url_priorities = {}
    kind_priority = {
        "direct-event": 3,
        "paginated-unlinked": 2,
        "personality-alias": 1,
    }
    for locale, target, ids, kind, _ in page_rows:
        if not ids:
            continue
        page_info = page_metadata(site, target, locale, ids)
        page_info_by_target[target] = page_info
        priority = kind_priority.get(kind, 0)
        for event_id in ids:
            key = (locale, event_id)
            if priority <= event_url_priorities.get(key, -1):
                continue
            event_url_priorities[key] = priority
            event_urls_by_locale[locale][event_id] = (
                page_info["url"], event_id if kind == "paginated-unlinked" else "",
            )
    mapped_ids = set().union(*(set(row[2]) for row in page_rows))
    metadata = {}
    for event_id in mapped_ids:
        event_metadata = parse_source_md(source / "source" / (event_id + ".md"))
        resolve_source_metadata_links(
            source, event_id, event_metadata, commit, repository_root,
            repository_base, "en", event_urls_by_locale,
        )
        metadata[event_id] = event_metadata
    event_usage_by_id = {}
    for event_id in mapped_ids:
        matching_rows = {}
        for hash_value in hashes_in(metadata[event_id]):
            for row in usage_by_hash.get(hash_value, []):
                row_key = (row.get("_source", ""), row.get("_sourceLine", ""))
                matching_rows[row_key] = row
        event_usage_by_id[event_id] = list(matching_rows.values())
    all_hashes = set().union(*(hashes_in(value) for value in metadata.values()))
    locale_jsonl = {locale: locate_jsonl(resources, locale) for locale in LOCALES}
    resource_info = {locale: verify_jsonl(locale_jsonl[locale], resources) for locale in LOCALES}
    resource_index = {
        locale: load_resource_index(locale_jsonl[locale], all_hashes)
        for locale in LOCALES
    }
    speakers = speakers_from(source)
    catalog = catalog_for(source, mapped_ids)

    reader_source = Path(__file__).resolve().parents[1] / "assets" / "js" / "darktide-dialogue.js"
    if not reader_source.is_file():
        raise SourceError("assets/js/darktide-dialogue.js must accompany this generator")
    reader_bytes = reader_source.read_bytes()
    reader_version = hashlib.sha256(reader_bytes).hexdigest()[:16]
    generator_version = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
    content_version = hashlib.sha256(
        f"{commit}:{GAME_SOURCE_COMMIT}:{reader_version}:{generator_version}".encode("ascii")
    ).hexdigest()[:24]
    reader_target = site / "assets" / "js" / "darktide-dialogue.js"
    reader_target.parent.mkdir(parents=True, exist_ok=True)
    reader_target.write_bytes(reader_bytes)
    speaker_target = site / "darktide" / "data" / "speakers"
    variant_registry = {locale: {} for locale in LOCALES}

    generated, skipped = [], []
    for locale, target, ids, kind, locale_source_ids in page_rows:
        if not ids:
            skipped.append({"page": target.relative_to(site).as_posix(), "locale": locale,
                            "reason": "no authoritative source-page mapping"})
            continue
        ranges = static_anchors(target.read_bytes().decode("utf-8-sig"))
        if len(ranges) != len(ids):
            raise SourceError(
                f"{target.relative_to(site)} has {len(ranges)} transcript containers "
                f"but its source mapping has {len(ids)} entries"
            )
        events, transcripts, page_warnings = [], [], []
        page_info = page_info_by_target[target]
        source_documents = {}
        source_evidence = {}
        evidence_gaps = {}
        source_links = list(page_info.get("sourceLinks", []))
        all_messages = []
        speaker_mapping_refs = {}
        usage_evidence = {}
        usage_evidence_keys = {}
        resource_refs = {
            event_id: sorted(hashes_in(metadata[event_id]))
            for event_id in ids
        }

        def add_source_evidence(item):
            record = dict(item)
            url = record.pop("url", None)
            path = record.pop("path", None)
            source_sha = record.pop("sourceSha256", None)
            document_ref = None
            if path:
                document_ref = next((event_id for event_id in ids
                                     if path == f"source/{event_id}.md"), None)
                if document_ref is None:
                    document_ref = "d" + hashlib.sha256(
                        path.encode("utf-8")
                    ).hexdigest()[:12]
                    source_documents.setdefault(document_ref, {
                        "path": path,
                    })
                document = source_documents[document_ref]
                if source_sha:
                    previous_sha = document.get("sha256")
                    if previous_sha and previous_sha != source_sha:
                        raise SourceError(f"source document checksum conflict: {path}")
                    document["sha256"] = source_sha
                record["documentRef"] = document_ref
            if url:
                link = next((existing for existing in source_links
                             if existing.get("url") == url), None)
                if link is None:
                    link = {"url": url, "label": record.get("relation") or "source evidence"}
                    source_links.append(link)
                record["urlRef"] = source_links.index(link)
            signature = json.dumps(record, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"))
            key = "e" + hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]
            previous = source_evidence.get(key)
            if previous is not None and previous != record:
                raise SourceError(f"source evidence ID collision: {key}")
            source_evidence[key] = record
            speaker_id = item.get("speakerId")
            if speaker_id:
                speaker_mapping_refs.setdefault(speaker_id, []).append(key)
            return key

        def add_evidence_gap(event_id, gap):
            signature = json.dumps(gap, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"))
            key = "g" + hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]
            previous = evidence_gaps.get(key)
            if previous is not None and previous != gap:
                raise SourceError(f"evidence gap ID collision: {key}")
            evidence_gaps[key] = gap
            references = source_documents[event_id].setdefault("evidenceGapRefs", [])
            if key not in references:
                references.append(key)

        for event_id in ids:
            event_usage = event_usage_by_id[event_id]
            source_documents[event_id] = {
                "path": f"source/{event_id}.md",
                "sha256": metadata[event_id].get("sourceSha256"),
                "evidenceRefs": [],
                "warnings": list(dict.fromkeys(
                    metadata[event_id].get("sourceWarnings", []) +
                    metadata[event_id].get("warnings", [])
                )),
            }
            for gap in metadata[event_id].get("evidenceGaps", []):
                add_evidence_gap(event_id, gap)
            evidence_records_for_event = source_evidence_for(
                event_id, metadata[event_id], catalog.get(event_id, []), event_usage, speakers,
            )
            for item in evidence_records_for_event:
                reference = add_source_evidence(item)
                if reference not in source_documents[event_id]["evidenceRefs"]:
                    source_documents[event_id]["evidenceRefs"].append(reference)
            for row in event_usage:
                evidence_id = usage_value(row, "evidence_ref", "evidence_id", "evidenceId")
                canonical_evidence_id = evidence_id.casefold()
                if not canonical_evidence_id:
                    continue
                record = usage_evidence_index.get(canonical_evidence_id)
                if record is None:
                    page_warnings.append(f"usage evidence record {evidence_id} is missing from the evidence index")
                    continue
                previous_key = usage_evidence_keys.get(canonical_evidence_id)
                previous = usage_evidence.get(previous_key) if previous_key else None
                if previous is not None and previous != record:
                    raise SourceError(f"usage evidence ID has conflicting records: {evidence_id}")
                if previous_key is None:
                    usage_evidence[evidence_id] = record
                    usage_evidence_keys[canonical_evidence_id] = evidence_id

        for event_id in ids:
            source_html = source / locale / "events" / f"{event_id}.html"
            if event_id not in locale_source_ids or not source_html.is_file():
                transcripts.append([])
                events.append({"eventId": event_id, "localeAvailable": False,
                               "sourceRef": event_id, "resourceRefs": resource_refs[event_id],
                               "playbackEligibility": {"status": "unconfirmed"},
                               "warnings": [f"pinned {locale} source page is missing"]})
                page_warnings.append(f"pinned {locale} source page is missing for {event_id}")
                add_evidence_gap(event_id, {
                    "kind": "playback-eligibility", "status": "unconfirmed",
                    "reason": "The pinned locale source page is missing.",
                })
                continue
            counterpart = source / ("zh-tw" if locale == "en" else "en") / "events" / f"{event_id}.html"
            counterpart_title = parse_html(counterpart)[1] if counterpart.is_file() else None
            page_id = target.parent.name if target.name.lower() == "index.html" else target.stem
            event_page, _ = make_page(
                source, event_id, locale, source_html, resource_index[locale],
                event_usage_by_id[event_id], speakers, catalog, variant_registry[locale],
                fallback_resource_index=resource_index["en"] if locale == "zh-tw" else None,
                personality_row=personality_rows.get((page_id, event_id)) if kind == "personality-alias" else None,
                anchor_prefix=event_id if kind in {"paginated-unlinked", "personality-alias"} else None,
                event_urls=event_urls_by_locale[locale],
                source_event_urls=event_urls_by_locale,
                commit=commit, repository_root=repository_root,
                repository_base=repository_base,
            )
            transcripts.append(event_page["transcript"])
            all_messages.extend(event_page["messages"])
            for gap in event_page["speakerEvidenceGaps"]:
                add_evidence_gap(event_id, gap)
            playback_status = event_page["playbackEligibility"]
            if playback_status != "confirmed":
                add_evidence_gap(event_id, {
                    "kind": "playback-eligibility", "status": playback_status,
                    "reason": "Current playback has not been confirmed by the supplied usage evidence.",
                })
            events.append({
                "eventId": event_id, "localeAvailable": True,
                "title": event_page["title"], "eventNumber": event_page["eventNumber"],
                "counterpartTitle": counterpart_title,
                "firstAnchor": event_page["firstAnchor"],
                "messages": event_page["messages"],
                "participants": event_page["participants"],
                "participantBars": event_page["participantBars"],
                "hasInlineParticipantBars": event_page["hasInlineParticipantBars"],
                "candidateGroups": event_page["candidateGroups"],
                "playbackEligibility": {"status": playback_status},
                "classification": [classification_record(row)
                                   for row in event_page["classification"]],
                "sourceRef": event_id,
                "resourceRefs": resource_refs[event_id],
                "warnings": event_page["warnings"],
            })
            page_warnings.extend(event_page["warnings"])
        resource_snapshot = resource_snapshot_for(
            ids, metadata, resource_index, resource_info, locale,
        )
        speaker_evidence = speaker_evidence_for(all_messages, speakers, speaker_mapping_refs)
        for record in speaker_evidence.values():
            url = record.pop("url", None)
            if url:
                link = next((existing for existing in source_links
                             if existing.get("url") == url), None)
                if link is None:
                    link = {"url": url, "label": record.get("relation") or "speaker source"}
                    source_links.append(link)
                record["urlRef"] = source_links.index(link)
        page_info["sourceLinks"] = source_links
        provenance = provenance_for(commit)
        page_metadata_record = {
            "page": page_info, "provenance": provenance,
            "sourceDocuments": source_documents, "sourceEvidence": source_evidence,
            "evidenceGaps": evidence_gaps,
            "resourceSnapshot": resource_snapshot,
            "playbackStates": list(PLAYBACK_STATES),
            "speakerEvidence": speaker_evidence,
            "usageAudit": usage_audit, "usageEvidence": usage_evidence,
            "eventIds": ids, "events": events,
            "firstAnchor": next((event.get("firstAnchor") for event in events
                                 if event.get("firstAnchor")), None),
            "warnings": list(dict.fromkeys(page_warnings)),
            "mappingKind": kind,
        }
        wire, compact_transcripts = compact_dialogue_wire(page_metadata_record, transcripts)
        page = {
            "schemaVersion": SCHEMA_VERSION, "contentVersion": content_version,
            "wire": wire, "transcripts": compact_transcripts,
        }
        data_path = target.parent / "data.json"
        write_json(data_path, page)
        anchor_ids = install_page(
            target, locale, content_version, reader_version, ids, kind,
        )
        generated.append({
            "locale": locale, "page": target.relative_to(site).as_posix(),
            "data": data_path.relative_to(site).as_posix(),
            "mappingKind": kind, "sourceEntries": len(ids),
            "staticAnchors": len(anchor_ids), "warnings": page_metadata_record["warnings"],
        })
    speaker_target.mkdir(parents=True, exist_ok=True)
    for locale in LOCALES:
        variants = [variant_registry[locale][key]
                    for key in sorted(variant_registry[locale])]
        used_speaker_ids = sorted({str(item["speakerId"]) for item in variants})
        write_json(speaker_target / f"{locale}.json", {
            "schemaVersion": SCHEMA_VERSION, "locale": locale,
            "contentVersion": content_version, "provenance": provenance_for(commit),
            "speakers": [{"speakerId": speaker_id} for speaker_id in used_speaker_ids],
            "variants": variants,
        })
    print(json.dumps({
        "schemaVersion": SCHEMA_VERSION, "provenance": provenance_for(commit),
        "contentVersion": content_version,
        "readerVersion": reader_version, "generatorVersion": generator_version,
        "pagesGenerated": len(generated),
        "readerAsset": reader_target.relative_to(site).as_posix(),
        "coverage": {
            "preparedDialoguePages": len(page_rows),
            "directEventPages": sum(row[3] == "direct-event" for row in page_rows),
            "paginatedUnlinkedPages": sum(row[3] == "paginated-unlinked" for row in page_rows),
            "personalityAliasPages": sum(row[3] == "personality-alias" for row in page_rows),
            "unmappedPages": len(skipped),
            "sourceEntriesMapped": sum(len(row[2]) for row in page_rows),
        },
        "pages": generated, "skipped": skipped,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SourceError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
