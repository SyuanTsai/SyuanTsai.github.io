"""Unit contracts for independently rendered Darktide preview pages."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from verify_darktide_preview import verify


class DarktidePreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.site = self.root / "_site"
        self.site.mkdir()
        (self.root / "_config.yml").write_text(
            'url: "https://example.test"\nbaseurl: ""\n', encoding="utf-8"
        )
        assets = self.site / "assets/css"
        assets.mkdir(parents=True)
        (assets / "darktide-preview.css").write_text("body {}\n", encoding="utf-8")
        self.event_urls: list[str] = []
        for locale in ("en", "zh-tw"):
            for order in (1, 2):
                event_id = f"debriefing_{order:02d}"
                url = f"/preview/darktide/{locale}/mission-debrief/{event_id}/"
                self.event_urls.append(url)
                other_locale = "zh-tw" if locale == "en" else "en"
                counterpart = url.replace(f"/{locale}/", f"/{other_locale}/")
                source_url = (
                    "https://github.com/Aussiemon/Darktide-Source-Code/blob/"
                    + "a" * 40
                    + f"/scripts/settings/cinematic_video/templates/{event_id}.lua#L1"
                )
                html_lang = "en" if locale == "en" else "zh-Hant"
                text = f"Event {order}, {locale}. "
                body = (
                    f'<div class="transcript" lang="{html_lang}">\n'
                    '  <article class="message" data-sequence="1">\n'
                    '    <img class="avatar" src="https://github.com/user-attachments/assets/example" alt="Morrow">\n'
                    '    <div class="speaker">Morrow:</div>\n'
                    f'    <div class="bubble">{text}</div>\n'
                    '    <span class="timestamp">00:01.00</span>\n'
                    '  </article>\n'
                    '</div>\n'
                )
                fields = {
                    "layout": "darktide-dialogue",
                    "title": f"Event {order}",
                    "other_title": f"Other event {order}",
                    "permalink": url,
                    "darktide_event": "true",
                    "event_id": event_id,
                    "event_order": str(order),
                    "event_type": "mission-debrief",
                    "locale": locale,
                    "html_lang": html_lang,
                    "line_count": "1",
                    "counterpart_url": counterpart,
                    "source_url": source_url,
                    "unlisted": "true",
                    "sitemap": "false",
                }
                source_path = (
                    self.root / "darktide-preview" / locale / "mission-debrief"
                    / f"{event_id}.html"
                )
                self.write_source(source_path, fields, body)
                previous = (
                    f'<a rel="prev" href="{url.replace(event_id, "debriefing_01")}">Previous</a>'
                    if order == 2 else ""
                )
                following = (
                    f'<a rel="next" href="{url.replace(event_id, "debriefing_02")}">Next</a>'
                    if order == 1 else ""
                )
                other_lang = "zh-Hant" if locale == "en" else "en"
                rendered = self.head(url) + (
                    f'<body data-event-id="{event_id}" data-locale="{locale}">'
                    + body
                    + f'<a id="language-toggle" class="language-toggle" hreflang="{other_lang}" href="{counterpart}" aria-label="Switch language">Other language</a>'
                    + f'<a id="dialogue-source" href="{source_url}">Source</a>'
                    + previous + following
                    + '</body></html>'
                )
                rendered = rendered.replace('<html lang="zh-Hant">', f'<html lang="{html_lang}">')
                self.write_output(url, rendered)

        for locale in ("en", "zh-tw"):
            prefix = "/preview/darktide/en/" if locale == "en" else "/preview/darktide/"
            other_prefix = "/preview/darktide/" if locale == "en" else "/preview/darktide/en/"
            html_lang = "en" if locale == "en" else "zh-Hant"
            other_lang = "zh-Hant" if locale == "en" else "en"
            for category in (False, True):
                url = prefix + ("mission-debrief/" if category else "")
                counterpart = other_prefix + ("mission-debrief/" if category else "")
                body = (
                    "\n".join(f'<a href="{event_url}">Event</a>' for event_url in self.event_urls if f'/{locale}/' in event_url)
                    if category else f'<a href="{prefix}mission-debrief/">Mission debrief</a>'
                )
                fields = {
                    "layout": "darktide-preview",
                    "title": "Mission debrief" if category else "Darktide",
                    "permalink": url,
                    "locale": locale,
                    "html_lang": html_lang,
                    "counterpart_url": counterpart,
                    "unlisted": "true",
                    "sitemap": "false",
                }
                if category:
                    fields["event_type"] = "mission-debrief"
                    fields["darktide_catalog"] = "true"
                if not category and locale == "zh-tw":
                    source_path = self.root / "darktide-preview.html"
                else:
                    source_path = self.root / "darktide-preview"
                    if locale == "en":
                        source_path /= "en"
                    if category:
                        source_path /= "mission-debrief"
                    source_path /= "index.html"
                self.write_source(source_path, fields, body)
                toggle = f'<a id="language-toggle" class="language-toggle" hreflang="{other_lang}" href="{counterpart}" aria-label="Switch language">Other language</a>'
                rendered = self.head(url) + f'<body data-locale="{locale}">' + toggle + body + '</body></html>'
                rendered = rendered.replace('<html lang="zh-Hant">', f'<html lang="{html_lang}">')
                self.write_output(url, rendered)
        (self.site / "sitemap.xml").write_text('<urlset></urlset>', encoding="utf-8")

    @staticmethod
    def head(url: str) -> str:
        return (
            '<!doctype html><html lang="zh-Hant"><head>'
            '<meta name="robots" content="noindex,nofollow,noarchive">'
            f'<link rel="canonical" href="https://example.test{url}">'
            '<link rel="stylesheet" href="/assets/css/darktide-preview.css">'
            '</head>'
        )

    @staticmethod
    def write_source(path: Path, fields: dict[str, str], body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        metadata = "\n".join(f"{key}: {value}" for key, value in fields.items())
        path.write_text(f"---\n{metadata}\n---\n{body}", encoding="utf-8")

    def output_path(self, url: str) -> Path:
        return self.site / url.strip("/") / "index.html"

    def write_output(self, url: str, markup: str) -> None:
        path = self.output_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markup, encoding="utf-8")

    def change_output(self, url: str, old: str, new: str) -> None:
        path = self.output_path(url)
        path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    def test_UnitT00_accepts_dynamic_event_count(self) -> None:
        """UnitT00: Rendered pages exactly match a two-event source set.

        Scenario: Two events have both locales and complete index/navigation output.
        Purpose: Accept a valid small corpus without hardcoding ten events or 112 lines.
        """
        self.assertEqual([], verify(self.site, self.root))

    def test_UnitT10_rejects_missing_rendered_event(self) -> None:
        """UnitT10: Missing language/event output is reported.

        Scenario: One source event has no generated HTML file.
        Purpose: Detect partial Jekyll builds and incomplete exports.
        """
        self.output_path(self.event_urls[0]).unlink()
        self.assertTrue(any("missing output" in error for error in verify(self.site, self.root)))

    def test_UnitT20_preserves_subtitle_tail_and_roles(self) -> None:
        """UnitT20: Subtitle whitespace, roles and timestamps remain exact.

        Scenario: The render trims a subtitle and changes its speaker and timestamp.
        Purpose: Prevent formatting or layout filters from rewriting official dialogue.
        """
        url = self.event_urls[0]
        self.change_output(url, 'en. </div>', 'en.</div>')
        self.change_output(url, 'Morrow:</div>', 'Someone:</div>')
        self.change_output(url, '00:01.00</span>', '00:02.00</span>')
        errors = verify(self.site, self.root)
        for component in ("bubble", "speaker", "timestamp"):
            self.assertTrue(any(component + " mismatch" in error for error in errors), errors)

    def test_UnitT30_rejects_bulk_transcripts_in_indexes(self) -> None:
        """UnitT30: Indexes contain navigation rather than hidden dialogue collections.

        Scenario: A root index includes a template containing subtitle content.
        Purpose: Keep each event transcript in its own generated page.
        """
        self.change_output(
            "/preview/darktide/", '</body>',
            '<template><div class="bubble">Hidden bulk</div></template></body>',
        )
        self.assertTrue(any("index contains dialogue" in error for error in verify(self.site, self.root)))

    def test_UnitT40_checks_counterpart_and_adjacent_navigation(self) -> None:
        """UnitT40: Language and previous/next links resolve to the intended pages.

        Scenario: An event links to itself for the other language and next event.
        Purpose: Detect metadata/layout navigation mistakes beyond generic link existence.
        """
        url = self.event_urls[0]
        self.change_output(url, url.replace('/en/', '/zh-tw/'), url)
        self.change_output(url, url.replace('debriefing_01', 'debriefing_02'), url)
        errors = verify(self.site, self.root)
        self.assertTrue(any("counterpart" in error for error in errors), errors)
        self.assertTrue(any("next navigation" in error for error in errors), errors)

    def test_UnitT45_checks_single_accessible_language_toggle(self) -> None:
        """UnitT45: Each page has a single accessible counterpart control.

        Scenario: A page duplicates the toggle and loses its accessible label.
        Purpose: Protect direct language switching without duplicate language choices.
        """
        url = self.event_urls[0]
        self.change_output(url, 'aria-label="Switch language"', 'aria-label=""')
        self.change_output(url, '</body>', '<a class="language-toggle" href="/">Duplicate</a></body>')
        self.assertTrue(any("language toggle" in error for error in verify(self.site, self.root)))

    def test_UnitT47_checks_index_locale_and_counterpart(self) -> None:
        """UnitT47: Indexes keep their selected locale and matching counterpart.

        Scenario: An English category links to the Chinese event and wrong index.
        Purpose: Keep title navigation and global switching in the intended language.
        """
        url = "/preview/darktide/en/mission-debrief/"
        self.change_output(url, self.event_urls[0], self.event_urls[0].replace('/en/', '/zh-tw/'))
        self.change_output(url, 'href="/preview/darktide/mission-debrief/"', 'href="/preview/darktide/"')
        errors = verify(self.site, self.root)
        self.assertTrue(any("index navigation incomplete" in error for error in errors), errors)
        self.assertTrue(any("language toggle" in error for error in errors), errors)

    def test_UnitT50_checks_noindex_canonical_and_sitemap(self) -> None:
        """UnitT50: Every preview stays unlisted with its own canonical URL.

        Scenario: A page becomes indexable, has another canonical, and enters Sitemap.
        Purpose: Prevent a multi-page preview from leaking into public discovery metadata.
        """
        url = self.event_urls[0]
        self.change_output(url, 'noindex,nofollow,noarchive', 'index,follow')
        self.change_output(url, f'https://example.test{url}', 'https://example.test/')
        (self.site / 'sitemap.xml').write_text(
            f'<urlset><url><loc>https://example.test{url}</loc></url></urlset>', encoding="utf-8"
        )
        errors = verify(self.site, self.root)
        for component in ("robots", "canonical", "Sitemap"):
            self.assertTrue(any(component in error for error in errors), errors)

    def test_UnitT60_checks_avatar_and_local_asset(self) -> None:
        """UnitT60: Portrait provenance and local assets survive the Jekyll export.

        Scenario: A portrait URL changes and the required CSS asset is missing.
        Purpose: Detect incorrect character media and broken preview asset paths.
        """
        self.change_output(self.event_urls[0], '/assets/example', '/assets/wrong')
        (self.site / 'assets/css/darktide-preview.css').unlink()
        errors = verify(self.site, self.root)
        self.assertTrue(any("avatar mismatch" in error for error in errors), errors)
        self.assertTrue(any("missing local asset" in error for error in errors), errors)

    def test_UnitT70_rejects_other_locale_and_client_transcripts(self) -> None:
        """UnitT70: Event documents identify exactly their own server-rendered locale.

        Scenario: An English event declares Chinese and includes a client-side script.
        Purpose: Prevent mixed pages and a return to loading all dialogue in JavaScript.
        """
        self.change_output(self.event_urls[0], 'data-locale="en"', 'data-locale="zh-tw"')
        self.change_output(self.event_urls[0], '</body>', '<script>loadAll()</script></body>')
        errors = verify(self.site, self.root)
        self.assertTrue(any("locale identity" in error for error in errors), errors)
        self.assertTrue(any("event contains script" in error for error in errors), errors)

    def test_UnitT80_limits_payload_to_own_transcript_and_shell(self) -> None:
        """UnitT80: An event payload does not grow with unrelated event content.

        Scenario: A short transcript gains a large hidden unrelated payload.
        Purpose: Bound server output by the event's own source and common layout size.
        """
        self.change_output(self.event_urls[0], '</body>', '<!--' + 'x' * 40_000 + '--></body>')
        self.assertTrue(any("payload exceeds" in error for error in verify(self.site, self.root)))


if __name__ == "__main__":
    unittest.main()
