"""Publish source-backed subtitle uses and paginated entries awaiting classification."""

import argparse
import csv
import html
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote


PAGE_SIZE = 25
SITE_URL = "https://notes.tw-syuan.com"
SOURCE_COMMIT = "7e662fcda16219d775b84af50322be2e9cd9d62e"
CODE_URL = f"https://github.com/Aussiemon/Darktide-Source-Code/blob/{SOURCE_COMMIT}/"
SOURCE_URL = (
    "https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/"
    "blob/21d2a025cd15ff2ff1ab7ac15796b1cef0ae9b07/"
    "Game%20Info/releases/1.13.X/source/README.md"
)
CATALOG_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|.*?\[來源\]"
    r"\(../../source/(unlinked_subtitle_[0-9a-f]{8})\.md\)\s*\|$"
)
TRANSCRIPT = re.compile(
    r'(<div class="transcript">.*?</div>)\s*</main>', re.DOTALL
)
BUBBLE = re.compile(r'(<div class="bubble">)(.*?)(</div>)', re.DOTALL)


def read_literal(path):
    return path.read_bytes().decode("utf-8-sig")


def scoped_transcript(path, event_id, raw_text, fallback_text=None):
    match = TRANSCRIPT.search(read_literal(path))
    if match is None:
        raise ValueError(f"No transcript in {path.name}")

    def scope_tag(match):
        tag = match.group(0)
        tag = re.sub(
            r'(?<=\s)id="([^"]+)"',
            lambda value: f'id="{event_id}-{value.group(1)}"',
            tag,
        )
        return re.sub(
            r'(?<=\s)href="#([^"]+)"',
            lambda value: f'href="#{event_id}-{value.group(1)}"',
            tag,
        )

    # Format markup with LF before reinserting untouched original locale text.
    block = match.group(1).replace("\r\n", "\n")
    bubbles = BUBBLE.findall(block)
    if raw_text is None:
        if bubbles:
            raise ValueError(f"Missing original locale text for {event_id}")
        if fallback_text is not None:
            block, count = re.subn(
                r'(<div class="line">)\s*<p class="note">.*?</p>\s*(</div>)',
                lambda line: (
                    '<p class="note">'
                    + '尚無官方繁中翻譯，暫以英文原文顯示。</p>'
                    + '\n                '
                    + line.group(1)
                    + '\n                  <div class="bubble" lang="en">'
                    + html.escape(fallback_text)
                    + '</div>\n                '
                    + line.group(2)
                ),
                block, count=1, flags=re.DOTALL,
            )
            if count != 1:
                raise ValueError(f"Expected one missing subtitle block for {event_id}")
    else:
        if len(bubbles) != 1:
            raise ValueError(f"Expected one original subtitle for {event_id}")
        # Take text directly from the locale resource, including original newlines.
        block = BUBBLE.sub(
            lambda bubble: bubble.group(1) + html.escape(raw_text) + bubble.group(3),
            block,
        )
    # Change only tag attributes; raw subtitle text and its whitespace stay literal.
    return re.sub(r"<[^>]+>", scope_tag, block)


def load_entries(source, resources):
    rows = []
    for path in sorted((source / "source-catalog/unlinked-subtitles").glob("*.md")):
        for line in read_literal(path).splitlines():
            match = CATALOG_ROW.match(line)
            if match:
                rows.append((int(match.group(1)), match.group(2)))
    rows.sort()
    if not rows or [number for number, _ in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("The source catalog must contain each numbered entry once")
    if len({event_id for _, event_id in rows}) != len(rows):
        raise ValueError("The source catalog contains repeated entry IDs")

    selected = {event_id.removeprefix("unlinked_subtitle_") for _, event_id in rows}
    texts = {}
    for locale in ("zh-tw", "en"):
        values = {}
        with (resources / locale / "subtitles.jsonl").open(encoding="utf-8-sig") as stream:
            for line in stream:
                row = json.loads(line)
                key = row["hash"]
                if key not in selected:
                    continue
                if key in values and values[key] != row["text"]:
                    raise ValueError(f"Ambiguous original locale text for {locale}/{key}")
                values[key] = row["text"]
        texts[locale] = values

    def render_entry(row):
        number, event_id = row
        key = event_id.removeprefix("unlinked_subtitle_")
        return (
            number,
            event_id,
            {
                locale: scoped_transcript(
                    source / locale / "events" / f"{event_id}.html",
                    event_id,
                    texts[locale].get(key),
                    fallback_text=texts["en"].get(key) if locale == "zh-tw" else None,
                )
                for locale in ("zh-tw", "en")
            },
        )

    with ThreadPoolExecutor(max_workers=8) as readers:
        return list(readers.map(render_entry, rows))


def page_url(locale, number):
    prefix = "/darktide/" if locale == "zh-tw" else "/darktide/en/"
    suffix = "" if number == 1 else f"page-{number:03d}/"
    return f"{prefix}unlinked-subtitles/{suffix}"


def usage_url(locale, category, event_id=""):
    prefix = "/darktide/" if locale == "zh-tw" else "/darktide/en/"
    suffix = f"{event_id}/" if event_id else ""
    return f"{prefix}{category}/{suffix}"


def load_usages(directory, entries):
    personalities, triggers = {}, {}
    known = {event_id.removeprefix("unlinked_subtitle_") for _, event_id, _ in entries}
    for filename, kind in (
        ("personality-introductions.tsv", "personality"),
        ("response-trigger-references.tsv", "trigger"),
    ):
        with (directory / filename).open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                key = row["hash"]
                if key not in known or row["source_commit"] != SOURCE_COMMIT:
                    raise ValueError("Usage metadata must match the fixed source and catalog")
                if kind == "personality":
                    if key in personalities or not re.fullmatch(
                        r"character_personality_[a-z0-9_]+", row["event_id"]
                    ):
                        raise ValueError("Invalid or repeated personality metadata")
                    personalities[key] = row
                else:
                    triggers.setdefault(key, []).append(row)
    if set(personalities) & set(triggers):
        raise ValueError("An entry cannot have conflicting usage classifications")
    return personalities, triggers


def pagination(locale, number, total, position):
    labels = (
        ("第一頁", "← 上一頁", "下一頁 →", "最後一頁", "分頁")
        if locale == "zh-tw"
        else ("First page", "← Previous page", "Next page →", "Last page", "Pagination")
    )
    parts = []
    if number > 1:
        parts.append(f'          <a href="{page_url(locale, 1)}">{labels[0]}</a>')
        parts.append(
            f'          <a href="{page_url(locale, number - 1)}" rel="prev">{labels[1]}</a>'
        )
    parts.append(f"          <span>{number} / {total}</span>")
    if number < total:
        parts.append(
            f'          <a href="{page_url(locale, number + 1)}" rel="next">{labels[2]}</a>'
        )
        parts.append(f'          <a href="{page_url(locale, total)}">{labels[3]}</a>')
    return (
        f'        <nav class="dialogue-footer unlinked-pagination" '
        f'aria-label="{labels[4]} · {position}">\n'
        + "\n".join(parts)
        + "\n        </nav>"
    )


def render_page(locale, number, total, entries):
    chinese = locale == "zh-tw"
    other = "en" if chinese else "zh-tw"
    lang = "zh-Hant" if chinese else "en"
    other_lang = "en" if chinese else "zh-Hant"
    title = "用途待確認字幕" if chinese else "Subtitles awaiting classification"
    page_title = f"{title} · {'第 ' + str(number) + ' 頁' if chinese else 'Page ' + str(number)}"
    back = "← 事件類型" if chinese else "← Event types"
    home = "/darktide/" if chinese else "/darktide/en/"
    toggle = "English" if chinese else "繁體中文"
    skip = "跳至內容" if chinese else "Skip to content"
    first, last = entries[0][0], entries[-1][0]
    summary = (
        f"第 {number}／{total} 頁 · 來源編號 {first}–{last} · 本頁 {len(entries)} 筆"
        if chinese
        else f"Page {number} of {total} · Source numbers {first}–{last} · {len(entries)} entries"
    )
    note = (
        "以下每筆是獨立的原始字幕，目前尚未從固定版本程式碼確認用途或說話者。"
        "查不到引用不代表遊戲沒有使用。每頁最多 25 筆；編號沿用來源索引，不代表連續對話。"
        if chinese
        else "Each entry is a separate original subtitle whose use and speaker remain unconfirmed "
        "in the fixed source version. No matching reference does not mean it is unused. "
        "Each page holds up to 25 entries; source numbers do not represent a continuous conversation."
    )
    panels = []
    for entry_number, event_id, transcripts in entries:
        entry_title = (
            f"用途待確認字幕 {entry_number:05d}"
            if chinese
            else f"Unclassified subtitle {entry_number:05d}"
        )
        panels.append(
            f'''        <section class="dialogue-panel unlinked-entry" id="{event_id}">
          <header class="dialogue-header">
            <h2 class="unlinked-title">
              <a href="#{event_id}">{entry_title}</a>
            </h2>
          </header>
          {transcripts[locale]}
        </section>'''
        )
    body = "\n".join(panels)
    top_nav = pagination(locale, number, total, "top")
    bottom_nav = pagination(locale, number, total, "bottom")
    source_label = "原始語系資源與版本來源" if chinese else "Original locale resources and version"
    description = html.escape(summary, quote=True)
    return f'''<!doctype html>
<html lang="{lang}">
  <head>
    <meta charset="utf-8">
    <meta
      name="viewport"
      content="width=device-width,initial-scale=1"
    >
    <meta
      name="robots"
      content="index,follow"
    >
    <meta
      name="description"
      content="{description}"
    >
    <title>{page_title} · Darktide</title>
    <link
      rel="canonical"
      href="{SITE_URL}{page_url(locale, number)}"
    >
    <link
      rel="alternate"
      hreflang="{other_lang}"
      href="{SITE_URL}{page_url(other, number)}"
    >
    <link
      rel="stylesheet"
      href="/assets/css/darktide.css"
    >
  </head>
  <body
    class="darktide-preview dialogue-reader unlinked-subtitle-reader"
    data-locale="{locale}"
  >
    <a class="skip-link" href="#darktide-content">{skip}</a>
    <div class="preview-shell">
      <header class="preview-header">
        <nav class="preview-toolbar">
          <a class="preview-back" href="{home}">{back}</a>
          <a
            class="language-toggle"
            id="language-toggle"
            href="{page_url(other, number)}"
            hreflang="{other_lang}"
            lang="{other_lang}"
          >
            <span aria-hidden="true">⇄</span>
            <span>{toggle}</span>
          </a>
        </nav>
        <p class="preview-eyebrow">WARHAMMER 40,000 · DARKTIDE</p>
        <h1>{title}</h1>
        <p class="preview-summary">{summary}</p>
        <p class="note">{note}</p>
      </header>
      <main id="darktide-content" tabindex="-1">
{top_nav}
{body}
{bottom_nav}
      </main>
      <footer class="dialogue-footer">
        <a
          href="{SOURCE_URL}"
          target="_blank"
          rel="noopener"
        >{source_label}</a>
      </footer>
    </div>
  </body>
</html>
'''


def usage_document(locale, category, event_id, title, summary, body, evidence=""):
    chinese = locale == "zh-tw"
    other = "en" if chinese else "zh-tw"
    lang, other_lang = ("zh-Hant", "en") if chinese else ("en", "zh-Hant")
    back_url = usage_url(locale, category) if event_id else (
        "/darktide/" if chinese else "/darktide/en/"
    )
    back = ("← 返回分類" if event_id else "← 事件類型") if chinese else (
        "← Back to category" if event_id else "← Event types"
    )
    toggle, skip = ("English", "跳至內容") if chinese else ("繁體中文", "Skip to content")
    title, summary = html.escape(title), html.escape(summary)
    source_label = "原始語系資源與版本來源" if chinese else "Original locale resources and version"
    return f'''<!doctype html>
<html lang="{lang}">
  <head>
    <meta charset="utf-8">
    <meta
      name="viewport"
      content="width=device-width,initial-scale=1"
    >
    <meta
      name="robots"
      content="index,follow"
    >
    <meta
      name="description"
      content="{summary}"
    >
    <title>{title} · Darktide</title>
    <link
      rel="canonical"
      href="{SITE_URL}{usage_url(locale, category, event_id)}"
    >
    <link
      rel="alternate"
      hreflang="{other_lang}"
      href="{SITE_URL}{usage_url(other, category, event_id)}"
    >
    <link
      rel="stylesheet"
      href="/assets/css/darktide.css"
    >
  </head>
  <body
    class="darktide-preview dialogue-reader unlinked-subtitle-reader"
    data-locale="{locale}"
  >
    <a class="skip-link" href="#darktide-content">{skip}</a>
    <div class="preview-shell">
      <header class="preview-header">
        <nav class="preview-toolbar">
          <a class="preview-back" href="{back_url}">{back}</a>
          <a
            class="language-toggle"
            id="language-toggle"
            href="{usage_url(other, category, event_id)}"
            hreflang="{other_lang}"
            lang="{other_lang}"
          >
            <span aria-hidden="true">⇄</span>
            <span>{toggle}</span>
          </a>
        </nav>
        <p class="preview-eyebrow">WARHAMMER 40,000 · DARKTIDE</p>
        <h1>{title}</h1>
        <p class="preview-summary">{summary}</p>
      </header>
      <main id="darktide-content" tabindex="-1">
{body}
      </main>
      <footer class="dialogue-footer">
        <a
          href="{SOURCE_URL}"
          target="_blank"
          rel="noopener"
        >{source_label}</a>
{evidence}
      </footer>
    </div>
  </body>
</html>
'''


def code_link(path, line, label):
    return f'''        <a
          href="{CODE_URL}{quote(path, safe='/')}#L{int(line)}"
          target="_blank"
          rel="noopener"
        >{html.escape(label)}</a>'''


def personality_transcript(locale, transcript, row):
    chinese = locale == "zh-tw"
    note = (
        "角色建立畫面顯示的性格介紹文字。圖示代表職業，並非固定人物肖像；"
        "試聽另有音訊設定，尚未確認與此段文字完全一致。"
        if chinese else
        "Personality introduction text displayed during character creation. The icon identifies "
        "the class, not a fixed person. Voice samples are configured separately; an exact spoken "
        "match to this text has not been confirmed."
    )
    transcript = re.sub(
        r'<p class="note">.*?</p>',
        lambda _: f'<p class="note">{html.escape(note)}</p>',
        transcript, count=1, flags=re.DOTALL,
    )
    label = row["archetype_zh_tw" if chinese else "archetype_en"]
    avatar = f'''<img
                class="avatar"
                src="{html.escape(row['portrait_url'], quote=True)}"
                alt="{html.escape(label, quote=True)}"
                loading="lazy"
              >'''
    transcript = re.sub(
        r'<span class="avatar portrait-missing">.*?</span>',
        lambda _: avatar, transcript, count=1, flags=re.DOTALL,
    )
    speaker = row["speaker_zh_tw" if chinese else "speaker_en"]
    transcript = re.sub(
        r'<div class="speaker">.*?</div>',
        lambda _: f'<div class="speaker">{html.escape(speaker)}:</div>',
        transcript, count=1, flags=re.DOTALL,
    )
    return transcript.replace('data-speaker-id="unspecified"',
                              f'data-speaker-id="{row["character_voice"]}"', 1)


def render_usage_index(locale, category, entries, metadata):
    chinese = locale == "zh-tw"
    personality = category == "character-personalities"
    title = (
        ("角色性格介紹" if personality else "回應觸發條件引用") if chinese else
        ("Character personality introductions" if personality else "Response trigger references")
    )
    summary = (
        f"{len(entries)} 筆 · 每筆獨立閱讀；分類依固定版本程式碼的實際用途。"
        if chinese else f"{len(entries)} entries · Separate reading pages classified by fixed source behavior."
    )
    cards = []
    for number, original_id, _ in entries:
        key = original_id.removeprefix("unlinked_subtitle_")
        row = metadata[key]
        event_id = row["event_id"] if personality else original_id
        label = row["speaker_zh_tw" if chinese else "speaker_en"] if personality else (
            f"回應條件引用 {number:05d}" if chinese else f"Trigger reference {number:05d}"
        )
        cards.append(f'''            <li>
              <a class="category-link" href="{usage_url(locale, category, event_id)}">
                <span class="category-title">{html.escape(label)}</span>
              </a>
            </li>''')
    body = '''        <section class="dialogue-panel">
          <ul class="category-list">
''' + "\n".join(cards) + '''
          </ul>
        </section>'''
    return usage_document(locale, category, "", title, summary, body)


def render_personality(locale, entry, row):
    chinese = locale == "zh-tw"
    number, _, transcripts = entry
    title = row["speaker_zh_tw" if chinese else "speaker_en"]
    summary = ("角色建立 · 性格介紹" if chinese else "Character creation · Personality introduction")
    transcript = personality_transcript(locale, transcripts[locale], row)
    body = f'''        <section class="dialogue-panel unlinked-entry">
          {transcript}
        </section>'''
    evidence = "\n".join((
        code_link(row["source_path"], row["source_line"], "性格介紹設定" if chinese else "Personality description setting"),
        code_link(row["display_path"], row["display_line"], "畫面顯示依據" if chinese else "Display behavior"),
        code_link(row["sample_path"], row["sample_line"], "試聽設定依據" if chinese else "Separate voice sample behavior"),
    ))
    return usage_document(locale, "character-personalities", row["event_id"], title, summary, body, evidence)


def render_trigger(locale, entry, references):
    chinese = locale == "zh-tw"
    number, original_id, transcripts = entry
    title = f"回應條件引用 {number:05d}" if chinese else f"Trigger reference {number:05d}"
    note = (
        "程式碼會在回應判斷中檢查是否聽到這句話。尚未確認這句話本身的播放事件與說話者。"
        "下面連結是符合條件時的相關回應候選，不代表每次都播放，也不是固定接續的劇情。"
        if chinese else
        "Response rules check whether this line was heard. Its own playback event and speaker "
        "remain unconfirmed. The links below lead to related response candidates, not guaranteed "
        "replies or a fixed story sequence."
    )
    transcript = re.sub(
        r'<p class="note">.*?</p>', lambda _: f'<p class="note">{html.escape(note)}</p>',
        transcripts[locale], count=1, flags=re.DOTALL,
    )
    links, evidence = [], []
    for index, row in enumerate(references, 1):
        href = row["existing_response_url_zh_tw" if chinese else "existing_response_url_en"]
        label = f"查看相關回應候選 {index}" if chinese else f"Read related response candidates {index}"
        links.append(f'''            <li>
              <a href="{html.escape(href, quote=True)}">{label}</a>
            </li>''')
        evidence.append(code_link(row["source_path"], row["source_line"],
                                  f"回應條件依據 {index}" if chinese else f"Response condition source {index}"))
    body = f'''        <section class="dialogue-panel unlinked-entry">
          {transcript}
          <ul>
''' + "\n".join(links) + '''
          </ul>
        </section>'''
    summary = "回應判斷中被引用的原始字幕" if chinese else "Original subtitle referenced in response conditions"
    return usage_document(locale, "response-trigger-references", original_id, title, summary, body, "\n".join(evidence))


def update_home(site, locale, counts):
    path = site / ("darktide/index.html" if locale == "zh-tw" else "darktide/en/index.html")
    text = read_literal(path).replace("\r\n", "\n")
    cards = []
    definitions = (
        ("character-personalities", "角色性格介紹", "Character personality introductions"),
        ("response-trigger-references", "回應觸發條件引用", "Response trigger references"),
        ("unlinked-subtitles", "用途待確認字幕", "Subtitles awaiting classification"),
    )
    for category, title_zh, title_en in definitions:
        if not counts[category]:
            continue
        title, subtitle = (title_zh, title_en) if locale == "zh-tw" else (title_en, title_zh)
        count_label = f"{counts[category]} 筆" if locale == "zh-tw" else f"{counts[category]} entries"
        cards.append(f'''            <li>
              <a class="category-link" href="{usage_url(locale, category)}">
                <span class="category-title">{title}</span>
                <span class="category-subtitle">{subtitle}</span>
                <span class="category-count">{count_label}</span>
              </a>
            </li>''')
    # Replace only these generated category cards; preserve all other home content.
    pattern = re.compile(
        r'            <li>\s*<a class="category-link" href="'
        r'/darktide/(?:en/)?(?:character-personalities|response-trigger-references|unlinked-subtitles)/"'
        r'>.*?</a>\s*</li>', re.DOTALL,
    )
    first = pattern.search(text)
    if first is None:
        raise ValueError("The existing subtitle category card is missing")
    before, after = text[:first.start()], pattern.sub("", text[first.start():])
    return path, before + "\n".join(cards) + "\n" + after.lstrip("\n")


def regenerate_sitemap(site):
    darktide = site / "darktide"
    urls = [
        SITE_URL + "/" + path.parent.relative_to(site).as_posix() + "/"
        for path in sorted(darktide.rglob("index.html"))
    ]
    chunks = [urls[start : start + 30000] for start in range(0, len(urls), 30000)]
    expected = set()
    for number, chunk in enumerate(chunks, 1):
        name = f"sitemap-{number:03d}.xml"
        expected.add(name)
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"  <url><loc>{html.escape(url)}</loc></url>\n" for url in chunk)
            + "</urlset>\n"
        )
        (darktide / name).write_bytes(xml.encode("utf-8"))
    for path in darktide.glob("sitemap-[0-9][0-9][0-9].xml"):
        if path.name not in expected:
            path.unlink()
    index = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(
            f"  <sitemap><loc>{SITE_URL}/darktide/{name}</loc></sitemap>\n"
            for name in sorted(expected)
        )
        + "</sitemapindex>\n"
    )
    (darktide / "sitemap.xml").write_bytes(index.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dialogue-source", type=Path, required=True)
    parser.add_argument("--locale-resources", type=Path)
    parser.add_argument("--classification-source", type=Path)
    parser.add_argument("--site", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    source, site = args.dialogue_source.resolve(), args.site.resolve()
    if not (site / ".git").exists() or source == site or site in source.parents:
        parser.error("Use a website checkout and a separate authoritative dialogue source")
    if not (source / "source-catalog/unlinked-subtitles").is_dir():
        parser.error("The authoritative unlinked subtitle catalog directory is missing")
    resources = args.locale_resources or (
        source.parent / "releases/1.13.X/source/SteamBuild_25606770_1.13.1/jsonl"
    )
    for locale in ("zh-tw", "en"):
        if not (resources / locale / "subtitles.jsonl").is_file():
            parser.error("The authoritative original locale subtitle resources are missing")
    classifications = args.classification_source or (source / "source-catalog/subtitle-usages")
    if not classifications.is_dir():
        parser.error("The authoritative subtitle usage metadata directory is missing")
    entries = load_entries(source, resources)
    personalities, triggers = load_usages(classifications, entries)
    classified = set(personalities) | set(triggers)
    remaining = [row for row in entries if row[1].removeprefix("unlinked_subtitle_") not in classified]
    intro_entries = [row for row in entries if row[1].removeprefix("unlinked_subtitle_") in personalities]
    intro_entries.sort(key=lambda row: int(personalities[
        row[1].removeprefix("unlinked_subtitle_")
    ]["personality_option_id"].removeprefix("option_")))
    trigger_entries = [row for row in entries if row[1].removeprefix("unlinked_subtitle_") in triggers]
    total = (len(remaining) + PAGE_SIZE - 1) // PAGE_SIZE
    outputs = []
    for locale in ("zh-tw", "en"):
        for number, start in enumerate(range(0, len(remaining), PAGE_SIZE), 1):
            path = site / page_url(locale, number).lstrip("/") / "index.html"
            outputs.append((path, render_page(locale, number, total, remaining[start : start + PAGE_SIZE])))
        for category, selected, metadata in (
            ("character-personalities", intro_entries, personalities),
            ("response-trigger-references", trigger_entries, triggers),
        ):
            if selected:
                path = site / usage_url(locale, category).lstrip("/") / "index.html"
                outputs.append((path, render_usage_index(locale, category, selected, metadata)))
            for entry in selected:
                key = entry[1].removeprefix("unlinked_subtitle_")
                row = metadata[key]
                event_id = row["event_id"] if category == "character-personalities" else entry[1]
                content = render_personality(locale, entry, row) if category == "character-personalities" else render_trigger(locale, entry, row)
                path = site / usage_url(locale, category, event_id).lstrip("/") / "index.html"
                outputs.append((path, content))
        outputs.append(update_home(site, locale, {
            "character-personalities": len(intro_entries),
            "response-trigger-references": len(trigger_entries),
            "unlinked-subtitles": len(remaining),
        }))

    # Remove only superseded subtitle leaves and numbered pages in these categories.
    cleanup_roots = [
        site / "darktide/unlinked-subtitles",
        site / "darktide/zh-tw/unlinked-subtitles",
        site / "darktide/en/unlinked-subtitles",
    ]
    expected_paths = {path for path, _ in outputs}
    legacy = []
    for root in cleanup_roots:
        candidates = list(root.glob("unlinked_subtitle_*/index.html")) + [
            path for path in root.glob("page-[0-9][0-9][0-9]/index.html")
            if path not in expected_paths
        ]
        for path in candidates:
            if path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(site):
                raise ValueError("Refusing to remove a path outside the website checkout")
            if not re.fullmatch(r"(?:unlinked_subtitle_[0-9a-f]{8}|page-[0-9]{3})", path.parent.name):
                raise ValueError("Unexpected legacy subtitle directory")
            legacy.append(path)
    for path, content in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
    for path in legacy:
        path.unlink()
        if not any(path.parent.iterdir()):
            path.parent.rmdir()
    regenerate_sitemap(site)
    from apply_darktide_reader import apply_reader
    apply_reader(site)
    print(f"Published {len(personalities)} personality introductions, {len(triggers)} trigger references, "
          f"and {len(remaining)} awaiting classification in {total} pages per language; "
          f"removed {len(legacy)} superseded pages.")


if __name__ == "__main__":
    main()
