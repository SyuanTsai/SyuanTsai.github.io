from __future__ import annotations

import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def text_content(fragment: str) -> str:
    parser = TextExtractor()
    parser.feed(fragment)
    return unescape("".join(parser.parts))


def span_texts(html: str, attribute_pattern: str) -> set[str]:
    pattern = re.compile(
        rf"<span(?=[^>]*{attribute_pattern})[^>]*>(.*?)</span>",
        re.DOTALL,
    )
    return {text_content(fragment) for fragment in pattern.findall(html)}


def verify(html_path: Path, fallback_words: set[str]) -> list[str]:
    html = html_path.read_text(encoding="utf-8")
    errors: list[str] = []

    uses_native_wrapping = 'data-word-segmentation="native"' in html
    uses_fallback_wrapping = 'data-word-segmentation="fallback"' in html

    if not uses_native_wrapping and not uses_fallback_wrapping:
        errors.append(f"{html_path}: 詞組斷行模式未完成初始化")

    if "keep-phrase" in html:
        errors.append(f"{html_path}: 不應以手動不可拆片語干擾自然斷行")

    rendered_words = span_texts(html, r"\bdata-word-segment(?:=\"\")?")

    if uses_native_wrapping and rendered_words:
        errors.append(f"{html_path}: 原生斷行模式不應再插入詞組 span")

    if uses_fallback_wrapping:
        for word in sorted(fallback_words - rendered_words):
            errors.append(f"{html_path}: 備援模式缺少詞內保護「{word}」")

    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print("用法：verify_rendered_word_breaks.py CODE_REVIEW_DOM SQL_MERGE_DOM")
        return 2

    errors = verify(
        Path(sys.argv[1]),
        fallback_words={"程式碼"},
    )
    errors.extend(
        verify(
            Path(sys.argv[2]),
            fallback_words={"擴充性"},
        )
    )

    if errors:
        print("\n".join(errors))
        return 1

    print("文章原生詞組斷行與備援模式已通過瀏覽器 DOM 驗證。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
