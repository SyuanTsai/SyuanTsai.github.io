"""Compact tag syntax in generated Darktide HTML without serializing its body."""
from html.parser import HTMLParser
from pathlib import Path


SPACE = " \t\r\n\f"
PROTECTED = {"script", "style", "pre", "textarea", "title", "noscript", "xmp", "iframe", "noembed", "noframes", "plaintext", "svg", "math"}
TAGS = set("a abbr address area article aside audio b base bdi bdo blockquote body br button canvas caption cite code col colgroup data datalist dd del details dfn dialog div dl dt em embed fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 head header hgroup hr html i img input ins kbd label legend li link main map mark menu meta meter nav noscript object ol optgroup option output p param picture progress q rp rt ruby s samp section select slot small source span strong sub summary sup table tbody td template tfoot th thead time title tr track u ul var video wbr".split())


def compact_tag(raw):
    """Replace only runs of HTML syntax whitespace outside attribute quotes."""
    parts, quote, index = [], None, 0
    while index < len(raw):
        char = raw[index]
        if quote:
            parts.append(char)
            if char == quote:
                quote = None
            index += 1
        elif char in "\"'":
            quote = char
            parts.append(char)
            index += 1
        elif char in SPACE:
            end = index + 1
            while end < len(raw) and raw[end] in SPACE:
                end += 1
            parts.append(" ")
            index = end
        else:
            parts.append(char)
            index += 1
    return raw if quote else "".join(parts)


class TagSlices(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0] + [index + 1 for index, char in enumerate(source) if char == "\n"]
        self.protected = []
        self.edits = []

    def handle_starttag(self, tag, attrs):
        if tag in PROTECTED:
            self.protected.append(tag)
            return
        if self.protected or tag not in TAGS:
            return
        raw = self.get_starttag_text()
        replacement = compact_tag(raw)
        if replacement != raw:
            line, column = self.getpos()
            start = self.offsets[line - 1] + column
            self.edits.append((start, start + len(raw), replacement))

    def handle_startendtag(self, tag, attrs):
        if tag in PROTECTED:
            # HTML raw-text elements are not void even when spelled with />.
            # Keep the whole source when its tokenizer state is ambiguous.
            raise ValueError("Ambiguous self-closing protected element")
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.protected and tag == self.protected[-1]:
            self.protected.pop()


def format_html(source):
    """Preserve text, values, comments, declarations and protected regions."""
    parser = TagSlices(source)
    try:
        parser.feed(source)
        parser.close()
    except (ValueError, AssertionError):
        return source
    parts, cursor = [], 0
    for start, end, replacement in parser.edits:
        parts.extend((source[cursor:start], replacement))
        cursor = end
    parts.append(source[cursor:])
    return "".join(parts)


def apply_format(site):
    changed, saved = 0, 0
    for path in sorted((Path(site) / "darktide").rglob("*.html")):
        original = path.read_bytes()
        output = format_html(original.decode("utf-8")).encode("utf-8")
        if output != original:
            path.write_bytes(output)
            changed += 1
            saved += len(original) - len(output)
    print(f"Darktide tag formatting: {changed} HTML files updated; {saved} bytes saved.")
    return {"changed": changed, "saved": saved}
