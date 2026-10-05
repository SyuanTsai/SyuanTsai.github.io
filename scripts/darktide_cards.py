"""Compact generated Darktide event-card markup in a built site tree.

Only non-skill catalogue cards are changed. Card text, links, IDs, attributes,
and element order remain source-preserved; unsupported card shapes are skipped.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Tuple


VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

CLASS_ATTRIBUTE_RE = re.compile(
    r"(?P<leading>[\t\r\n ]+)class[\t\r\n ]*=[\t\r\n ]*"
    r"(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
CLASS_TOKEN_RE = re.compile(r"(?<!\S)event-card(?!\S)")


@dataclass
class _TitleLink:
    start: int
    end: int
    has_heading: bool = False
    close_start: Optional[int] = None
    close_end: Optional[int] = None


@dataclass
class _Card:
    start: int
    open_end: int
    open_tag: str
    links: List[_TitleLink] = field(default_factory=list)
    close_start: Optional[int] = None
    close_end: Optional[int] = None


@dataclass
class _Node:
    tag: str
    classes: set
    card: Optional[_Card]
    card_candidate: Optional[_Card] = None
    title_link: Optional[_TitleLink] = None


class _CardParser(HTMLParser):
    """Locate card boundaries without serializing or normalizing HTML."""

    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.cards: List[_Card] = []
        self.stack: List[_Node] = []
        self.line_offsets = [0]
        self.line_offsets.extend(
            match.end() for match in re.finditer("\n", source)
        )

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        raw_tag = self.get_starttag_text()
        start = self._offset()
        parent = self.stack[-1] if self.stack else None
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())
        parent_card = parent.card if parent else None
        candidate = None

        if (
            tag == "li"
            and parent is not None
            and parent.tag == "ul"
            and "event-catalog" in parent.classes
            and "event-card" in classes
        ):
            candidate = _Card(start, start + len(raw_tag), raw_tag)
            parent_card = candidate

        title_link = None
        if (
            tag == "a"
            and parent is not None
            and parent.card_candidate is parent_card
            and parent_card is not None
            and "event-title-link" in classes
        ):
            title_link = _TitleLink(start, start + len(raw_tag))
            parent_card.links.append(title_link)

        if tag == "h3" and parent_card is not None:
            for node in reversed(self.stack):
                if node.card is parent_card and node.title_link is not None:
                    node.title_link.has_heading = True
                    break

        node = _Node(tag, classes, parent_card, candidate, title_link)
        if tag not in VOID_ELEMENTS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        match_index = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                match_index = index
                break
        if match_index is None:
            return

        close_start = self._offset()
        close_end = self.source.find(">", close_start)
        close_end = close_end + 1 if close_end >= 0 else close_start
        closing_nodes = self.stack[match_index:]
        for node in reversed(closing_nodes):
            if node.tag != tag:
                continue
            if node.title_link is not None:
                node.title_link.close_start = close_start
                node.title_link.close_end = close_end
            if node.card_candidate is not None:
                node.card_candidate.close_start = close_start
                node.card_candidate.close_end = close_end
                self.cards.append(node.card_candidate)
        del self.stack[match_index:]


def _remove_event_card_class(open_tag: str) -> Tuple[str, bool]:
    matches = list(CLASS_ATTRIBUTE_RE.finditer(open_tag))
    if len(matches) != 1:
        return open_tag, False

    match = matches[0]
    value = match.group("value")
    tokens = value.split()
    if tokens.count("event-card") != 1:
        return open_tag, False

    if len(tokens) == 1:
        start = match.start("leading")
        return open_tag[:start] + open_tag[match.end() :], True

    token = CLASS_TOKEN_RE.search(value)
    if token is None:
        return open_tag, False

    start = token.start()
    end = token.end()
    if start:
        while start and value[start - 1].isspace():
            start -= 1
    else:
        while end < len(value) and value[end].isspace():
            end += 1

    value_start = match.start("value")
    value_end = match.end("value")
    stripped_value = value[:start] + value[end:]
    return (
        open_tag[:value_start] + stripped_value + open_tag[value_end:],
        True,
    )


def _is_multiline_gap(value: str) -> bool:
    return value.isspace() and ("\n" in value or "\r" in value)


def optimize_html(source: str) -> Tuple[str, int, int]:
    """Return compacted HTML, changed-card count, and skipped-card count."""
    parser = _CardParser(source)
    parser.feed(source)
    parser.close()

    edits = []
    changed_cards = 0
    skipped_cards = 0
    for card in parser.cards:
        links = [
            link
            for link in card.links
            if link.has_heading
            and link.close_start is not None
            and link.close_end is not None
        ]
        if (
            card.close_start is None
            or card.close_end is None
            or not links
        ):
            skipped_cards += 1
            continue

        card_edits = 0
        new_open_tag, class_removed = _remove_event_card_class(card.open_tag)
        if class_removed:
            edits.append((card.start, card.open_end, new_open_tag))
            card_edits += 1

        link = links[0]
        open_gap = source[card.open_end : link.start]
        if _is_multiline_gap(open_gap):
            edits.append((card.open_end, link.start, ""))
            card_edits += 1

        close_gap = source[link.close_end : card.close_start]
        if _is_multiline_gap(close_gap):
            edits.append((link.close_end, card.close_start, ""))
            card_edits += 1

        if card_edits:
            changed_cards += 1

    result = source
    for start, end, replacement in sorted(edits, reverse=True):
        result = result[:start] + replacement + result[end:]
    return result, changed_cards, skipped_cards


def apply_cards(site_root: Path) -> dict:
    """Compact eligible cards under ``site_root/darktide`` in place."""
    site_root = Path(site_root).resolve()
    darktide_root = site_root / "darktide"
    if not darktide_root.is_dir():
        raise ValueError("site root must contain a darktide/ directory")

    files_scanned = 0
    files_changed = 0
    cards_changed = 0
    cards_skipped = 0
    bytes_before = 0
    bytes_after = 0
    for path in sorted(darktide_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".html":
            continue
        relative_parts = path.relative_to(darktide_root).parts
        if any(part.casefold() == "skills" for part in relative_parts):
            continue

        original = path.read_bytes()
        try:
            source = original.decode("utf-8")
        except UnicodeDecodeError:
            continue

        files_scanned += 1
        optimized, changed, skipped = optimize_html(source)
        cards_changed += changed
        cards_skipped += skipped
        output = optimized.encode("utf-8")
        bytes_before += len(original)
        bytes_after += len(output)
        if output != original:
            path.write_bytes(output)
            files_changed += 1

    return {
        "files_scanned": files_scanned,
        "files_changed": files_changed,
        "cards_changed": cards_changed,
        "cards_skipped": cards_skipped,
        "bytes_before": bytes_before,
        "bytes_after": bytes_after,
        "bytes_saved": bytes_before - bytes_after,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "site",
        type=Path,
        help="generated site root containing the darktide/ directory",
    )
    result = apply_cards(parser.parse_args().site)
    print(
        "Scanned {files_scanned} HTML files; changed {files_changed} files and "
        "{cards_changed} cards; skipped {cards_skipped} unsupported cards; "
        "saved {bytes_saved} bytes.".format(**result)
    )


if __name__ == "__main__":
    main()

