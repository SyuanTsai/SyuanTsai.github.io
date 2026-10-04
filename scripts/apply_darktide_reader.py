"""Apply the shared directory frame without serializing dialogue content."""

import argparse
import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


class CatalogLinks(HTMLParser):
    """Read navigation labels only; never use this parser to rewrite a page."""

    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None
        self.primary_tag = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "a" and set(classes) & {"category-link", "event-title-link"}:
            self.current = {"url": attrs["href"], "text": [], "primary": []}
        if self.current and (tag == "h3" or "category-title" in classes):
            self.primary_tag = tag

    def handle_endtag(self, tag):
        if tag == self.primary_tag:
            self.primary_tag = None
        if tag == "a" and self.current:
            label = " ".join(self.current["primary"] or self.current["text"])
            self.links.append((self.current["url"], " ".join(label.split())))
            self.current = None
            self.primary_tag = None

    def handle_data(self, data):
        if self.current:
            self.current["text"].append(data)
            if self.primary_tag:
                self.current["primary"].append(data)


@dataclass
class Page:
    path: Path
    url: str
    locale: str
    title: str


def metadata(path, text):
    canonical = re.search(r'<link\b(?=[^>]*\brel="canonical")[^>]*\bhref="([^"]+)"', text)
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    if not canonical or not title:
        raise ValueError("Every dialogue page needs its existing canonical and title")
    url = urlsplit(html.unescape(canonical.group(1))).path
    if not url.startswith("/darktide/") or not url.endswith("/"):
        raise ValueError("Unexpected dialogue canonical")
    locale = "en" if url.startswith("/darktide/en/") else "zh-tw"
    label = html.unescape(title.group(1)).removesuffix(" · Darktide")
    return Page(path, url, locale, label)


def strip_frame(text):
    # Remove only our own markup, leaving every original byte between the markers.
    text = re.sub(r'\n[ \t]*<!-- directory-reader:start -->.*?<!-- directory-reader:body -->', "", text, flags=re.S)
    text = re.sub(r'[ \t]*<!-- directory-reader:end -->.*?<!-- /directory-reader:end -->\n', "", text, flags=re.S)
    text = re.sub(r'[ \t]*<!-- directory-reader:crumb -->.*?<!-- /directory-reader:crumb -->\n', "", text, flags=re.S)
    text = re.sub(r'\n[ \t]*<!-- directory-reader:home -->.*?<!-- directory-reader:catalog -->', "", text, flags=re.S)
    return re.sub(r'[ \t]*<!-- directory-reader:catalog-end -->.*?<!-- /directory-reader:home -->\n', "", text, flags=re.S)


def link(url, label, current):
    selected = ' aria-current="page"' if url == current else ""
    return f'<a href="{html.escape(url, quote=True)}"{selected}>{html.escape(label)}</a>'


def category_key(url):
    parts = url.strip("/").split("/")[1:]
    if parts and parts[0] in {"en", "zh-tw"}:
        parts = parts[1:]
    return parts[0] if parts else ""


def skill_classes(site):
    text = (site / "darktide/skills/index.html").read_bytes().decode("utf-8")
    result = []
    for match in re.finditer(r'<a class="skill-catalog-link" href="([^"]+)"><span><strong>(.*?)</strong><small lang="en">(.*?)</small>', text):
        result.append(tuple(html.unescape(value) for value in match.groups()))
    if len(result) != 7 or len({url for url, _, _ in result}) != 7:
        raise ValueError("The skill root must retain its seven class catalog links")
    return result


def directory(page, categories, catalogs, parents, pages, classes):
    english = page.locale == "en"
    home = "/darktide/en/" if english else "/darktide/"
    labels = ("Browse directory", "Skills and talents (Traditional Chinese)", "Dialogue and subtitles", "Archive home", "Category directory", "Other categories", "Complete directory →") if english else ("瀏覽目錄", "技能與天賦", "對話與字幕", "資料區首頁", "分類目錄", "其他分類", "完整目錄 →")
    active = next(((url, name) for url, name in categories if category_key(url) == category_key(page.url)), None)
    lines = [
        '        <details class="dt-directory">',
        f'          <summary>{labels[0]}</summary>',
        f'          <nav aria-label="{"Darktide directory" if english else "Darktide 階層目錄"}">',
        f'            <a class="dt-brand" href="{home}">DARKTIDE</a>',
        '            <details>',
        f'              <summary>{labels[1]}</summary>',
        '              <div class="dt-level">',
        f'                {link("/darktide/skills/", "Class directory" if english else "七職業目錄", page.url)}',
        *[f'                {link(url, en if english else zh + " · " + en, page.url)}' for url, zh, en in classes],
        '              </div>',
        '            </details>',
        '            <details open>',
        f'              <summary>{labels[2]}</summary>',
        '              <div class="dt-level">',
        f'                {link(home, labels[3], page.url)}',
    ]
    if active:
        root, name = active
        lines += ['                <details open>', f'                  <summary>{html.escape(name)}</summary>', '                  <div class="dt-level">', f'                    {link(root, labels[4], page.url)}']
        catalog = page.url if page.url in catalogs else parents.get(page.url)
        entries = catalogs.get(catalog, [])
        position = next((i for i, (url, _) in enumerate(entries) if url == page.url), 0)
        nearby = entries[max(0, position - 2):position + 3]
        if catalog and catalog != root and catalog != page.url:
            lines.append(f'                    {link(catalog, pages[catalog].title, page.url)}')
        for url, label in nearby:
            if url != root:
                lines.append(f'                    {link(url, label, page.url)}')
        if page.url != root and page.url not in {url for url, _ in nearby}:
            lines.append(f'                    {link(page.url, page.title, page.url)}')
        if catalog and catalog != page.url and len(entries) > len(nearby):
            lines.append(f'                    {link(catalog, labels[6], page.url)}')
        lines += ['                  </div>', '                </details>', '                <details>', f'                  <summary>{labels[5]}</summary>', '                  <div class="dt-level">']
        lines += [f'                    {link(url, label, page.url)}' for url, label in categories if url != root]
        lines += ['                  </div>', '                </details>']
    else:
        lines += [f'                {link(url, label, page.url)}' for url, label in categories]
    lines += ['              </div>', '            </details>', '          </nav>', '        </details>']
    return "\n".join(lines)


def breadcrumb(page, categories, parents, pages):
    english = page.locale == "en"
    home = "/darktide/en/" if english else "/darktide/"
    name = "Current location" if english else "目前位置"
    items = [(home, "Darktide")]
    category = next(((url, label) for url, label in categories if category_key(url) == category_key(page.url)), None)
    if category and category[0] != page.url:
        items.append(category)
    parent = parents.get(page.url)
    if parent and parent != page.url and parent not in {url for url, _ in items}:
        items.append((parent, pages[parent].title))
    anchors = "\n".join(f'          <li>{link(url, label, page.url)}</li>' for url, label in items if url != page.url)
    return f'''      <!-- directory-reader:crumb -->
      <nav class="dt-breadcrumb" aria-label="{name}">
        <ol>
{anchors}
          <li aria-current="page">{html.escape(page.title)}</li>
        </ol>
      </nav>
      <!-- /directory-reader:crumb -->
'''


def home_frame(text, english):
    heading, note, summary = ("Choose a reading section", "Use the directory to browse skills, event types and individual conversations. On a small screen, open Browse directory first. Each subtitle awaiting classification remains an independent entry on a page of up to 25 entries.", "Complete dialogue category list") if english else ("選擇閱讀內容", "從目錄進入技能、事件類型與個別對話。手機可先展開「瀏覽目錄」。用途待確認字幕每頁最多25筆，每筆仍是獨立條目，不串成連續劇情。", "完整對話類型清單")
    opening = re.search(r'<main\b[^>]*>', text)
    closing = text.rfind("      </main>")
    if not opening or closing < opening.end():
        raise ValueError("Missing home reading landmark")
    intro = f'''
        <!-- directory-reader:home -->
        <section class="catalog-panel dt-home-intro">
          <h2>{heading}</h2>
          <p>{note}</p>
        </section>
        <details class="dt-home-catalog">
          <summary>{summary}</summary>
        <!-- directory-reader:catalog -->'''
    end = '''        <!-- directory-reader:catalog-end -->
        </details>
        <!-- /directory-reader:home -->
'''
    return text[:opening.end()] + intro + text[opening.end():closing] + end + text[closing:]


def apply_reader(site):
    site = Path(site).resolve()
    if not (site / ".git").exists() or not (site / "assets/css/darktide-reader.css").is_file():
        raise ValueError("Use the website checkout with the shared reader stylesheet")
    classes = skill_classes(site)
    pages, catalogs, parents, categories = {}, {}, {}, {}
    for locale, url in [("zh-tw", "/darktide/"), ("en", "/darktide/en/")]:
        parser = CatalogLinks()
        parser.feed((site / url.lstrip("/") / "index.html").read_bytes().decode("utf-8"))
        categories[locale] = [(target, label) for target, label in parser.links if category_key(target) != "skills"]
        if not categories[locale] or any(not target.startswith(url) for target, _ in categories[locale]):
            raise ValueError("Home must retain its locale-specific category catalog")
    for path in sorted((site / "darktide").rglob("index.html")):
        if "skills" in path.relative_to(site / "darktide").parts:
            continue
        text = path.read_bytes().decode("utf-8")
        page = metadata(path, text)
        pages[page.url] = page
        if 'class="event-catalog"' in text:
            parser = CatalogLinks()
            parser.feed(text)
            catalogs[page.url] = parser.links
            for target, _ in parser.links:
                parents.setdefault(target, page.url)
    changed = 0
    for page in pages.values():
        original = page.path.read_bytes()
        text = strip_frame(original.decode("utf-8"))
        if page.url in {"/darktide/", "/darktide/en/"}:
            text = home_frame(text, page.locale == "en")
        if 'href="/assets/css/darktide-reader.css"' not in text:
            text = text.replace("  </head>", '    <link rel="stylesheet" href="/assets/css/darktide-reader.css">\n  </head>')
        crumb = breadcrumb(page, categories[page.locale], parents, pages)
        text = text.replace('      <main ', crumb + '      <main ', 1)
        start = '\n      <!-- directory-reader:start -->\n      <div class="dt-layout">\n' + directory(page, categories[page.locale], catalogs, parents, pages, classes) + '\n        <div class="dt-reading">\n        <!-- directory-reader:body -->'
        text = text.replace('    <div class="preview-shell">', '    <div class="preview-shell">' + start, 1)
        end = '        <!-- directory-reader:end -->\n        </div>\n      </div>\n      <!-- /directory-reader:end -->\n'
        marker = re.search(r'    </div>\r?\n  </body>', text)
        if not marker or 'class="dt-layout"' not in text:
            raise ValueError("Missing original dialogue shell")
        text = text[:marker.start()] + end + text[marker.start():]
        rendered = text.encode("utf-8")
        if rendered != original:
            page.path.write_bytes(rendered)
            changed += 1
    print(f"Shared directory: {len(pages)} dialogue/home pages; {changed} updated; original content retained.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path(__file__).resolve().parents[1])
    apply_reader(parser.parse_args().site)
