"""Enforce the reviewed legacy skill migration after any static regeneration."""
from __future__ import annotations
import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

MAP_PATH = Path("docs/darktide-migration/routes.json")
DESTINATION = "https://darktide.tw-syuan.com"
MARKER = '<meta name="darktide-migration" content="skill-v1">'
CLASSES = {"arbites", "ogryn", "psyker", "scum", "skitarii", "veteran", "zealot"}


def validate_routes(routes):
    seen = set()
    targets = set()
    for row in routes:
        old, new = row["old"], row["new"]
        parts = old.strip("/").split("/")
        if (not old.startswith("/darktide/skills/") or not old.endswith("/")
                or len(parts) not in (4, 5) or parts[2] not in CLASSES
                or any(not re.fullmatch(r"[a-z0-9_-]+", part) for part in parts)
                or (len(parts) == 5 and parts[4] != "mechanics")):
            raise ValueError("Invalid legacy skill route")
        kind = "mechanics" if len(parts) == 5 else "skill"
        if row["kind"] != kind or row["content_key"].split("/")[0] != parts[2]:
            raise ValueError("Skill identity or kind mismatch")
        expected = DESTINATION + "/skills/" + row["content_key"] + "/" + ("mechanics/" if kind == "mechanics" else "")
        if new != expected or not re.fullmatch(r"[a-z0-9_-]+/[a-z0-9_-]+", row["content_key"]):
            raise ValueError("Invalid verified destination")
        if old in seen or new in targets:
            raise ValueError("Duplicate migration route")
        seen.add(old)
        targets.add(new)
    return routes


def load_routes(site):
    path = Path(site) / MAP_PATH
    if not path.exists():
        path = Path(__file__).resolve().parents[1] / MAP_PATH
    return validate_routes(json.loads(path.read_text(encoding="utf-8"))["routes"]) if path.exists() else []


def redirect_html(row):
    target = html.escape(row["new"], quote=True)
    return (f'<!doctype html>\n<html lang="zh-Hant"><head>\n'
            f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'{MARKER}\n<meta name="robots" content="noindex,follow">\n'
            f'<title>技能資料已遷移 · 黑潮</title>\n<link rel="canonical" href="{target}">\n'
            f'<meta http-equiv="refresh" content="0;url={target}">\n'
            f'<script>location.replace({json.dumps(row["new"])});</script>\n'
            f'</head><body><main><h1>技能資料已遷移</h1>\n'
            f'<p><a href="{target}">前往黑潮繁體資料庫的對應內容</a></p>\n'
            f'<p><a href="/darktide/skills/">舊站技術補充</a> · <a href="/darktide/">對話與字幕</a></p>\n'
            f'</main></body></html>\n').encode("utf-8")


def rewrite_links(text, mapping):
    def replace(match):
        url = html.unescape(match[2])
        parsed = urlsplit(url)
        local = not parsed.netloc or parsed.netloc.lower() == "notes.tw-syuan.com"
        target = mapping.get(parsed.path) if local else None
        return match[1] + (html.escape(target, quote=True) if target else match[2]) + match[3]
    return re.sub(r'(\bhref=["\'])([^"\']+)(["\'])', replace, text)


def apply_migration(site, check=False):
    site = Path(site).resolve()
    rows = load_routes(site)
    mapping = {row["old"]: row["new"] for row in rows}
    changes = []
    for row in rows:
        path = site / row["old"].strip("/") / "index.html"
        if not path.resolve().is_relative_to(site / "darktide/skills"):
            raise ValueError("Migration path escaped skill tree")
        expected = redirect_html(row)
        if not path.exists() or path.read_bytes() != expected:
            changes.append(path.relative_to(site).as_posix())
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
    # Only retained skill directories/supplements are edited. No dialogue prose is parsed.
    for path in sorted((site / "darktide/skills").rglob("index.html")):
        route = "/" + path.parent.relative_to(site).as_posix() + "/"
        if route in mapping:
            continue
        original = path.read_bytes()
        text = rewrite_links(original.decode("utf-8"), mapping)
        if 'id="migration-notice"' not in text:
            notice = ('<aside id="migration-notice"><p>繁中技能／天賦、武器與祝福已遷至 '
                      '<a href="https://darktide.tw-syuan.com/skills/">黑潮繁體資料庫</a>。'
                      '本頁保留舊站技術補充；技能連結前往新站。</p></aside>')
            text = re.sub(r'(<article\b[^>]*>)', lambda m: m[1] + notice, text, count=1)
        expected = text.encode("utf-8")
        if original != expected:
            changes.append(path.relative_to(site).as_posix())
            if not check:
                path.write_bytes(expected)
    for path in sorted((site / "darktide").glob("sitemap-[0-9][0-9][0-9].xml")):
        original = path.read_bytes()
        def remove(match):
            loc = re.search(r'<loc>(.*?)</loc>', match[0])
            return "" if loc and urlsplit(html.unescape(loc[1])).path in mapping else match[0]
        expected = re.sub(r'[ \t]*<url>.*?</url>\r?\n?', remove, original.decode("utf-8"), flags=re.S).encode("utf-8")
        if expected != original:
            changes.append(path.relative_to(site).as_posix())
            if not check:
                path.write_bytes(expected)
    if check and changes:
        raise ValueError("Migration output is stale: " + ", ".join(changes[:8]))
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changes = apply_migration(args.site, args.check)
    print(f"Migration: {len(load_routes(args.site))} exact redirects; {len(changes)} files updated.")

if __name__ == "__main__":
    main()
