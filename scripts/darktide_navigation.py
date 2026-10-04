"""Generate and apply metadata-only Darktide navigation assets.

The reader body is never serialized into navigation JSON. HTML is read as bytes
and only the marked directory prefix plus the external loader tag is replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


SCHEMA_VERSION = 1
DATA_SUBDIR = Path("assets/data/darktide-navigation/v1")
MANIFEST_NAME = ".generated-manifest.json"
HOME_URLS = {"zh-tw": "/darktide/", "en": "/darktide/en/"}
SKILLS_URL = "/darktide/skills/"


@dataclass(frozen=True)
class Page:
    path: Path
    url: str
    locale: str
    title: str
    is_skill: bool
    catalog_links: tuple = ()
    is_catalog: bool = False


@dataclass(frozen=True)
class Binding:
    page: Page
    kind: str
    category_url: str = ""
    branch_key: str = ""


class CatalogLinks(HTMLParser):
    """Collect only explicit catalogue links and their navigation labels."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.current = None
        self.primary_tag = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())
        if tag == "a" and classes.intersection({"category-link", "event-title-link"}):
            self.current = {"url": attributes.get("href", ""), "text": [], "primary": []}
        if self.current and (tag == "h3" or "category-title" in classes):
            self.primary_tag = tag

    def handle_endtag(self, tag):
        if tag == self.primary_tag:
            self.primary_tag = None
        if tag == "a" and self.current:
            label = " ".join(self.current["primary"] or self.current["text"])
            label = " ".join(label.split())
            if self.current["url"] and label:
                self.links.append((self.current["url"], label))
            self.current = None
            self.primary_tag = None

    def handle_data(self, data):
        if self.current:
            self.current["text"].append(data)
            if self.primary_tag:
                self.current["primary"].append(data)


class SkillCatalog(HTMLParser):
    """Read skill navigation labels from catalogue anchors, never article prose."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.article_depth = 0
        self.sections = []
        self.section = None
        self.heading_active = False
        self.link = None
        self.capture = None
        self.root_links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())
        if tag == "article" and "skill-content" in classes:
            self.article_depth += 1
        if self.article_depth == 0:
            return
        if tag == "section" and "skill-section" in classes:
            self.section = {"id": attributes.get("id", ""), "title_parts": [], "items": []}
            self.sections.append(self.section)
        elif self.section and tag == "h2":
            self.heading_active = True
        if tag == "a" and "skill-catalog-link" in classes and attributes.get("href"):
            self.link = {
                "url": attributes["href"],
                "title_parts": [],
                "title_en_parts": [],
                "text_parts": [],
            }
            self.capture = None
        elif self.link and tag == "strong":
            self.capture = "title"
        elif self.link and tag == "small" and attributes.get("lang", "").lower() == "en":
            self.capture = "title_en"

    def handle_endtag(self, tag):
        if tag == "strong" and self.capture == "title":
            self.capture = None
        elif tag == "small" and self.capture == "title_en":
            self.capture = None
        elif tag == "h2":
            self.heading_active = False
        elif tag == "a" and self.link:
            node = self._finish_link()
            if node:
                if self.section is not None:
                    self.section["items"].append(node)
                else:
                    self.root_links.append(node)
            self.link = None
            self.capture = None
        elif tag == "section" and self.section is not None:
            self.section["title"] = clean_label("".join(self.section["title_parts"]))
            self.section.pop("title_parts", None)
            self.section = None
            self.heading_active = False
        elif tag == "article" and self.article_depth:
            self.article_depth -= 1

    def handle_data(self, data):
        if self.article_depth and self.heading_active and self.section is not None:
            self.section["title_parts"].append(data)
        if self.link:
            self.link["text_parts"].append(data)
            if self.capture == "title":
                self.link["title_parts"].append(data)
            elif self.capture == "title_en":
                self.link["title_en_parts"].append(data)

    def _finish_link(self):
        href = local_navigation_url(self.link["url"])
        if not href:
            return None
        title = clean_label("".join(self.link["title_parts"])) or clean_label(
            "".join(self.link["text_parts"])
        )
        if not title:
            return None
        title_en = clean_label("".join(self.link["title_en_parts"]))
        node = {"title": title, "url": href}
        if title_en:
            node["titleEn"] = title_en
        return node


def clean_label(value):
    return " ".join(html.unescape(value).split())


def local_navigation_url(value):
    """Keep only local Darktide hrefs; preserve path, query and fragment."""
    parsed = urlsplit(html.unescape(value))
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/darktide/"):
        return ""
    return parsed.path + (("?" + parsed.query) if parsed.query else "") + (
        ("#" + parsed.fragment) if parsed.fragment else ""
    )


def route_path(url):
    return urlsplit(url).path


def category_key(url):
    parts = route_path(url).strip("/").split("/")
    if parts and parts[0] == "darktide":
        parts = parts[1:]
    if parts and parts[0] in {"en", "zh-tw"}:
        parts = parts[1:]
    return parts[0] if parts else ""


def locale_for_url(url):
    parts = route_path(url).strip("/").split("/")
    return "en" if len(parts) > 1 and parts[:2] == ["darktide", "en"] else "zh-tw"


def read_page(path, site):
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    canonical = re.search(
        r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*\bhref=["\']([^"\']+)["\']',
        text,
        re.IGNORECASE,
    )
    title = re.search(r"<title>(.*?)</title>", text, re.DOTALL | re.IGNORECASE)
    if not canonical or not title:
        raise ValueError(f"Missing canonical or title in {path.relative_to(site).as_posix()}")
    url = urlsplit(html.unescape(canonical.group(1))).path
    if not url.startswith("/darktide/") or not url.endswith("/"):
        raise ValueError(f"Unexpected Darktide canonical in {path.relative_to(site).as_posix()}")
    relative = path.relative_to(site / "darktide")
    is_skill = bool(relative.parts and relative.parts[0] == "skills")
    if is_skill:
        if "<!-- reader:start -->" not in text or "<!-- reader:body -->" not in text:
            raise ValueError(f"Missing existing skill reader markers in {path.relative_to(site).as_posix()}")
    elif "<!-- directory-reader:start -->" not in text and '<div class="preview-shell">' not in text:
        raise ValueError(f"Missing dialogue reader shell in {path.relative_to(site).as_posix()}")
    label = html.unescape(title.group(1)).removesuffix(" · Darktide")
    is_catalog = not is_skill and bool(
        re.search(r'\bclass=["\'][^"\']*\bevent-catalog\b', text)
    )
    catalog_links = ()
    if not is_skill and re.search(r'\bclass=["\'][^"\']*\b(category-link|event-title-link)\b', text):
        parser = CatalogLinks()
        parser.feed(text)
        catalog_links = tuple(parser.links)
    return Page(path, url, locale_for_url(url), label, is_skill, catalog_links, is_catalog)


def page_catalog_links(page):
    return list(page.catalog_links)


def parse_skill_catalog(page):
    parser = SkillCatalog()
    parser.feed(page.path.read_bytes().decode("utf-8"))
    for section in parser.sections:
        section["title"] = clean_label(section.get("title", ""))
    return parser


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def branch_filename(key):
    return "branch-" + digest(key.encode("utf-8")) + ".json"


def node_from_link(url, title, order, parent, kind):
    href = local_navigation_url(url)
    if not href:
        return None
    return {
        "title": clean_label(title),
        "url": href,
        "parent": parent,
        "order": order,
        "kind": kind,
    }


def find_category(url, categories):
    key = category_key(url)
    if not key:
        return None
    return next((item for item in categories if category_key(item["url"]) == key), None)


def build_model(site):
    dialogue_pages = []
    skill_pages = []
    pages_by_url = {}
    bindings = {}
    for path in sorted((site / "darktide").rglob("index.html")):
        page = read_page(path, site)
        prior = pages_by_url.get(page.url)
        if prior and prior.title != page.title:
            raise ValueError(f"Conflicting titles for canonical {page.url}")
        pages_by_url.setdefault(page.url, page)
        (skill_pages if page.is_skill else dialogue_pages).append(page)

    if not dialogue_pages or not skill_pages:
        raise ValueError("Both Darktide dialogue and skill page trees must exist")

    categories_by_locale = {}
    for locale, home_url in HOME_URLS.items():
        home = pages_by_url.get(home_url)
        if not home:
            raise ValueError(f"Missing locale home {home_url}")
        categories = []
        for order, (url, label) in enumerate(page_catalog_links(home)):
            if category_key(url) == "skills":
                continue
            node = node_from_link(url, label, order, home_url, "category")
            if node:
                categories.append(node)
        if not categories:
            raise ValueError(f"Missing category links for {locale}")
        categories_by_locale[locale] = categories

    skills_root = pages_by_url.get(SKILLS_URL)
    if not skills_root:
        raise ValueError(f"Missing skill directory {SKILLS_URL}")
    root_parser = parse_skill_catalog(skills_root)
    root_section = root_parser.sections[0] if root_parser.sections else None
    class_candidates = root_section["items"] if root_section else root_parser.root_links
    class_nodes = []
    for candidate in class_candidates:
        parts = route_path(candidate["url"]).strip("/").split("/")
        if candidate["url"].startswith(SKILLS_URL) and len(parts) == 3 and parts[:2] == ["darktide", "skills"]:
            node = {
                "title": candidate["title"],
                "url": candidate["url"],
                "parent": SKILLS_URL,
                "order": len(class_nodes),
                "kind": "skill-class",
            }
            if candidate.get("titleEn"):
                node["titleEn"] = candidate["titleEn"]
            class_nodes.append(node)
    if len(class_nodes) != 7 or len({node["url"] for node in class_nodes}) != 7:
        raise ValueError("The skill root must provide seven unique class links")

    classes_by_url = {node["url"]: node for node in class_nodes}
    class_pages = {page.url: page for page in skill_pages if page.url in classes_by_url}
    if set(class_pages) != set(classes_by_url):
        raise ValueError("A class landing page is missing from the skill tree")

    roots = {}
    branches = {}
    class_branch_by_url = {}
    skill_parent_branch = {}

    for class_url, class_node in classes_by_url.items():
        parsed = parse_skill_catalog(class_pages[class_url])
        category_nodes = []
        category_items = []
        for order, section in enumerate(parsed.sections):
            section_id = section.get("id") or ("section-" + str(order))
            section_url = class_url + ("#" + section_id if section.get("id") else "")
            items = []
            for item_order, candidate in enumerate(section["items"]):
                node = {
                    "title": candidate["title"],
                    "url": candidate["url"],
                    "parent": section_url,
                    "order": item_order,
                    "kind": "skill-page",
                }
                if candidate.get("titleEn"):
                    node["titleEn"] = candidate["titleEn"]
                items.append(node)
            category = {
                "title": section["title"] or section_id,
                "url": section_url,
                "parent": class_url,
                "order": order,
                "kind": "skill-category",
                "hasChildren": bool(items),
                "id": section_id,
            }
            category_nodes.append(category)
            category_items.append((category, items))

        class_key = "skill-class:" + class_url
        class_branch_by_url[class_url] = class_key
        branches[class_key] = {
            "schemaVersion": SCHEMA_VERSION,
            "key": class_key,
            "scope": "skill-class",
            "locale": "zh-tw",
            "class": class_node,
            "categories": category_nodes,
        }
        for category, items in category_items:
            key = "skill-category:" + class_url + "#" + category["id"]
            branches[key] = {
                "schemaVersion": SCHEMA_VERSION,
                "key": key,
                "scope": "skill-category",
                "locale": "zh-tw",
                "class": class_node,
                "categories": category_nodes,
                "currentCategory": category,
                "items": items,
            }
            for item in items:
                skill_parent_branch.setdefault(route_path(item["url"]), key)

    catalogs = {}
    parent_catalog = {}
    for page in dialogue_pages:
        if not page.is_catalog:
            continue
        items = []
        for order, (url, label) in enumerate(page_catalog_links(page)):
            node = node_from_link(url, label, order, page.url, "dialogue-page")
            if node:
                items.append(node)
                parent_catalog.setdefault(route_path(node["url"]), page.url)
        catalogs.setdefault(page.url, items)

    for page in dialogue_pages:
        categories = categories_by_locale[page.locale]
        category = find_category(page.url, categories)
        category_url = category["url"] if category else ""
        catalog_url = page.url if page.url in catalogs else parent_catalog.get(route_path(page.url), "")
        branch_key = ""
        if catalog_url and catalog_url in catalogs:
            branch_key = "dialogue-catalog:" + page.locale + ":" + catalog_url
            catalog_page = pages_by_url.get(catalog_url)
            branches[branch_key] = {
                "schemaVersion": SCHEMA_VERSION,
                "key": branch_key,
                "scope": "dialogue-catalog",
                "locale": page.locale,
                "category": category or {},
                "catalog": {
                    "title": catalog_page.title if catalog_page else (category or {}).get("title", ""),
                    "url": catalog_url,
                    "parent": category_url or HOME_URLS[page.locale],
                },
                "items": catalogs[catalog_url],
            }
        kind = "dialogue-home" if page.url == HOME_URLS[page.locale] else "dialogue"
        bindings[page.path] = Binding(page, kind, category_url, branch_key)

    for page in skill_pages:
        if page.url == SKILLS_URL:
            bindings[page.path] = Binding(page, "skill-root", SKILLS_URL, "")
            continue
        if page.url in classes_by_url:
            bindings[page.path] = Binding(
                page, "skill-class", SKILLS_URL, class_branch_by_url[page.url]
            )
            continue
        parts = route_path(page.url).strip("/").split("/")
        class_url = "/" + "/".join(parts[:3]) + "/" if len(parts) >= 3 else ""
        branch_key = skill_parent_branch.get(route_path(page.url), "")
        bindings[page.path] = Binding(
            page,
            "skill-page",
            SKILLS_URL,
            branch_key or class_branch_by_url.get(class_url, ""),
        )

    for locale, home_url in HOME_URLS.items():
        home = pages_by_url[home_url]
        roots[locale] = {
            "schemaVersion": SCHEMA_VERSION,
            "locale": locale,
            "home": {"title": home.title, "url": home_url},
            "categories": categories_by_locale[locale],
            "skills": {
                "title": skills_root.title,
                "titleEn": "Skills and talents (Traditional Chinese)",
                "url": SKILLS_URL,
                "parent": home_url,
                "classes": class_nodes,
            },
        }

    return {
        "roots": roots,
        "branches": branches,
        "bindings": bindings,
        "dialogueCount": len(dialogue_pages),
        "skillCount": len(skill_pages),
    }


def load_previous_manifest(manifest_path):
    if not manifest_path.exists():
        existing = [
            path.name for path in manifest_path.parent.glob("*.json")
            if path.name != MANIFEST_NAME
        ]
        if existing:
            raise ValueError("Navigation output contains unowned JSON; preserving it.")
        return set()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != SCHEMA_VERSION or not isinstance(manifest.get("files"), list):
        raise ValueError("Invalid generated navigation manifest")
    names = set()
    for name in manifest["files"]:
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
            raise ValueError("Invalid filename in generated navigation manifest")
        names.add(name)
    return names


def write_if_changed(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == payload:
        return False
    path.write_bytes(payload)
    return True


def write_assets(output_root, model):
    js_source = Path(__file__).resolve().parents[1] / "assets/js/darktide-navigation.js"
    if not js_source.is_file():
        raise ValueError("Missing assets/js/darktide-navigation.js beside the generator")
    js_payload = js_source.read_bytes()

    versionless = {
        "schemaVersion": SCHEMA_VERSION,
        "roots": model["roots"],
        "branches": {key: model["branches"][key] for key in sorted(model["branches"])},
    }
    version = digest(canonical_json(versionless))
    roots = {locale: {**value, "contentVersion": version} for locale, value in model["roots"].items()}
    branches = {key: {**value, "contentVersion": version} for key, value in model["branches"].items()}

    generated = {}
    for locale, value in roots.items():
        generated["root-" + locale + ".json"] = json_bytes(value)
    for key, value in branches.items():
        generated[branch_filename(key)] = json_bytes(value)

    data_dir = output_root / DATA_SUBDIR
    manifest_path = data_dir / MANIFEST_NAME
    old_files = load_previous_manifest(manifest_path)
    current_files = set(generated)
    for stale in sorted(old_files - current_files):
        candidate = data_dir / stale
        if candidate.parent.resolve() != data_dir.resolve() or candidate.name != stale:
            raise ValueError("Refusing to remove a file outside the navigation output directory")
        if candidate.is_file() and not candidate.is_symlink():
            candidate.unlink()

    root_urls = {
        locale: "/assets/data/darktide-navigation/v1/root-" + locale + ".json?v=" + version
        for locale in roots
    }
    branch_urls = {
        key: "/assets/data/darktide-navigation/v1/" + branch_filename(key) + "?v=" + version
        for key in branches
    }

    sizes = {}
    changed = 0
    for name, payload in generated.items():
        changed += int(write_if_changed(data_dir / name, payload))
        sizes[name] = len(payload)

    manifest_payload = json_bytes({
        "schemaVersion": SCHEMA_VERSION,
        "contentVersion": version,
        "files": sorted(current_files),
    })
    write_if_changed(manifest_path, manifest_payload)

    js_version = digest(js_payload)
    js_changed = write_if_changed(output_root / "assets/js/darktide-navigation.js", js_payload)
    branch_sizes = [size for name, size in sizes.items() if name.startswith("branch-")]
    return {
        "dataVersion": version,
        "rootUrls": root_urls,
        "branchUrls": branch_urls,
        "jsUrl": "/assets/js/darktide-navigation.js?v=" + js_version,
        "jsonChanged": changed,
        "jsChanged": js_changed,
        "rootBytes": sum(sizes["root-" + locale + ".json"] for locale in roots),
        "branchBytes": sum(branch_sizes),
        "maxBranchBytes": max(branch_sizes, default=0),
        "jsonFiles": len(generated),
        "jsBytes": len(js_payload),
    }


def escape_attr(value):
    return html.escape(value, quote=True)


def fallback_link(url, label, current_url):
    current = (
        ' aria-current="page"'
        if route_path(url) == route_path(current_url) and not urlsplit(url).fragment
        else ""
    )
    return '<a href="' + escape_attr(url) + '"' + current + ">" + html.escape(label) + "</a>"


def directory_prefix(binding, asset_info, newline):
    page = binding.page
    english = page.locale == "en"
    labels = (
        {
            "summary": "Browse directory",
            "nav": "Darktide directory",
            "home": "Archive home",
            "category": "Current category",
            "skills": "Class directory",
            "pending": "The complete directory is unavailable until it loads. Basic page links remain available.",
            "retry": "Reload to retry",
            "noscript": "JavaScript is disabled. Use the page navigation and catalogue links to continue.",
        }
        if english
        else {
            "summary": "瀏覽目錄",
            "nav": "Darktide 階層目錄",
            "home": "資料區首頁",
            "category": "目前分類",
            "skills": "七職業目錄",
            "pending": "完整目錄尚未載入；頁面基本導覽仍可使用。",
            "retry": "重新載入重試",
            "noscript": "JavaScript 已停用；請使用頁面基本導覽與分類連結。",
        }
    )
    home_url = HOME_URLS[page.locale]
    links = [(home_url, labels["home"])]
    if page.is_skill:
        links.append((SKILLS_URL, labels["skills"]))
        class_url = ""
        if binding.branch_key.startswith("skill-class:"):
            class_url = binding.branch_key.split(":", 1)[1]
        elif binding.branch_key.startswith("skill-category:"):
            class_url = binding.branch_key[len("skill-category:"):].split("#", 1)[0]
        else:
            parts = route_path(page.url).strip("/").split("/")
            if len(parts) >= 3 and parts[:2] == ["darktide", "skills"]:
                class_url = "/" + "/".join(parts[:3]) + "/"
        if class_url and page.url != class_url:
            class_label = page.title if binding.kind == "skill-class" else (
                "Class home" if english else "職業目錄"
            )
            links.append((class_url, class_label))
    elif binding.category_url:
        links.append((binding.category_url, labels["category"]))

    if not any(
        route_path(url) == route_path(page.url) and not urlsplit(url).fragment
        for url, _ in links
    ):
        links.append((page.url, page.title))

    root_url = asset_info["rootUrls"][page.locale]
    branch_url = asset_info["branchUrls"].get(binding.branch_key, "")
    start_marker = "<!-- reader:start -->" if page.is_skill else "<!-- directory-reader:start -->"
    body_marker = "<!-- reader:body -->" if page.is_skill else "<!-- directory-reader:body -->"
    data_attrs = (
        ' class="dt-directory"'
        ' data-navigation-root="' + escape_attr(root_url) + '"'
        ' data-navigation-branch="' + escape_attr(branch_url) + '"'
        ' data-navigation-branch-key="' + escape_attr(binding.branch_key) + '"'
        ' data-navigation-version="' + escape_attr(asset_info["dataVersion"]) + '"'
        ' data-navigation-locale="' + page.locale + '"'
        ' data-navigation-page="' + escape_attr(page.url) + '"'
        ' data-navigation-current-title="' + escape_attr(page.title) + '"'
        ' data-navigation-kind="' + binding.kind + '"'
        ' data-navigation-category="' + escape_attr(binding.category_url) + '"'
    )
    indent = "      " if page.is_skill else "        "
    lines = [
        start_marker,
        indent + '<div class="dt-layout">',
        indent + "  <details" + data_attrs + ">",
        indent + "    <summary>" + html.escape(labels["summary"]) + "</summary>",
        indent + '    <nav aria-label="' + html.escape(labels["nav"], quote=True) + '">',
        indent + '      <a class="dt-brand" href="' + escape_attr(home_url) + '">DARKTIDE</a>',
        indent + '      <div class="dt-level" data-navigation-content>',
        *[
            indent + "        " + fallback_link(url, label, page.url)
            for url, label in links
        ],
        indent + "      </div>",
        indent + '      <p class="dt-directory-status" role="status" aria-live="polite">',
        indent + '        <span data-navigation-status-text>' + html.escape(labels["pending"]) + "</span>",
        indent + '        <a data-navigation-retry href="' + escape_attr(page.url) + '">' + html.escape(labels["retry"]) + "</a>",
        indent + "      </p>",
        indent + "      <noscript><p>" + html.escape(labels["noscript"]) + "</p></noscript>",
        indent + "    </nav>",
        indent + "  </details>",
        indent + '  <div class="dt-reading">',
        indent + "  " + body_marker,
    ]
    return newline.join(lines)


def add_loader_script(text, js_url, newline):
    pattern = re.compile(
        r'[ \t]*<script\b(?=[^>]*\bdata-darktide-navigation(?:[ \t=]|>))[^>]*>\s*</script>[ \t]*(?:\r?\n)?',
        re.IGNORECASE,
    )
    text = pattern.sub("", text)
    closing = re.search(r"(?m)^([ \t]*)</body\s*>", text, re.IGNORECASE)
    if not closing:
        closing = re.search(r"</body\s*>", text, re.IGNORECASE)
        if not closing:
            raise ValueError("Missing </body> while adding the navigation loader")
        indent = ""
        insertion = closing.start()
    else:
        indent = closing.group(1)
        insertion = closing.start()
    script = indent + '<script defer data-darktide-navigation src="' + escape_attr(js_url) + '"></script>' + newline
    return text[:insertion] + script + text[insertion:]


def replace_reader_prefix(text, binding, asset_info, newline):
    page = binding.page
    start_marker = "<!-- reader:start -->" if page.is_skill else "<!-- directory-reader:start -->"
    body_marker = "<!-- reader:body -->" if page.is_skill else "<!-- directory-reader:body -->"
    start = text.find(start_marker)
    body = text.find(body_marker, start + len(start_marker)) if start >= 0 else -1
    if start >= 0 and body >= 0:
        prefix = directory_prefix(binding, asset_info, newline)
        return text[:start] + prefix + text[body + len(body_marker):]

    if page.is_skill:
        raise ValueError("Missing marked skill directory frame in " + page.path.as_posix())
    shell = re.search(r'<div class="preview-shell">', text)
    if not shell:
        raise ValueError("Missing preview shell in " + page.path.as_posix())
    prefix = directory_prefix(binding, asset_info, newline)
    text = text[:shell.end()] + newline + prefix + text[shell.end():]
    closing = re.search(r'(?m)^([ \t]*)</div>\r?\n([ \t]*)</body\s*>', text, re.IGNORECASE)
    if not closing:
        raise ValueError("Missing preview-shell closing marker in " + page.path.as_posix())
    ending = newline.join([
        "        <!-- directory-reader:end -->",
        "        </div>",
        "      </div>",
        "      <!-- /directory-reader:end -->",
        "",
    ])
    return text[:closing.start()] + ending + text[closing.start():]


def apply_page(binding, asset_info):
    original = binding.page.path.read_bytes()
    text = original.decode("utf-8")
    newline = "\r\n" if b"\r\n" in original else "\n"
    text = replace_reader_prefix(text, binding, asset_info, newline)
    text = add_loader_script(text, asset_info["jsUrl"], newline)
    rendered = text.encode("utf-8")
    if rendered != original:
        binding.page.path.write_bytes(rendered)
        return True
    return False


def generate_and_apply(site, output_root=None, apply_pages=True):
    site = Path(site).resolve()
    output_root = Path(output_root).resolve() if output_root else site
    if not (site / "darktide/index.html").is_file():
        raise ValueError("--site must point to a prepared website tree with darktide/index.html")
    if not (site / "assets/css/darktide-reader.css").is_file():
        raise ValueError("--site is missing assets/css/darktide-reader.css")
    if apply_pages and output_root != site:
        raise ValueError("Applying HTML requires assets in the same prepared website tree")

    model = build_model(site)
    asset_info = write_assets(output_root, model)
    changed = 0
    if apply_pages:
        for binding in model["bindings"].values():
            changed += int(apply_page(binding, asset_info))

    print(
        "Shared navigation generated: "
        + str(model["dialogueCount"])
        + " dialogue pages; "
        + str(model["skillCount"])
        + " skill pages; "
        + str(asset_info["jsonFiles"])
        + " JSON files; "
        + str(asset_info["rootBytes"])
        + " root JSON bytes; "
        + str(asset_info["branchBytes"])
        + " total branch JSON bytes; max branch "
        + str(asset_info["maxBranchBytes"])
        + " bytes; JS "
        + str(asset_info["jsBytes"])
        + " bytes; version "
        + asset_info["dataVersion"]
        + "; "
        + str(changed)
        + " HTML pages updated."
    )
    return asset_info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, help="Write generated assets under this directory.")
    parser.add_argument(
        "--assets-only",
        action="store_true",
        help="Generate JSON and JS without changing source HTML.",
    )
    args = parser.parse_args()
    generate_and_apply(args.site, output_root=args.output_dir, apply_pages=not args.assets_only)


if __name__ == "__main__":
    main()
