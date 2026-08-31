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


def verify(html_path: Path, automatic_words: set[str], kept_phrases: set[str]) -> list[str]:
    html = html_path.read_text(encoding="utf-8")
    errors: list[str] = []

    if 'data-word-segmentation="ready"' not in html:
        errors.append(f"{html_path}: 自動詞組分析未完成")

    rendered_words = span_texts(html, r"\bdata-word-segment(?:=\"\")?")
    rendered_phrases = span_texts(html, r'\bclass="[^"]*\bkeep-phrase\b[^"]*"')

    for word in sorted(automatic_words - rendered_words):
        errors.append(f"{html_path}: 缺少自動保護詞「{word}」")

    for phrase in sorted(kept_phrases - rendered_phrases):
        errors.append(f"{html_path}: 缺少不可拆片語「{phrase}」")

    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print("用法：verify_rendered_word_breaks.py CODE_REVIEW_DOM SQL_MERGE_DOM")
        return 2

    errors = verify(
        Path(sys.argv[1]),
        automatic_words={"程式碼"},
        kept_phrases={
            "整體程式碼健康",
            "非必要建議",
            "理解成本只會更高、風險也更大",
        },
    )
    errors.extend(
        verify(
            Path(sys.argv[2]),
            automatic_words={"擴充性"},
            kept_phrases={
                "更新目標資料",
                "queued updating replication",
                "INSERT、UPDATE 與 DELETE",
            },
        )
    )

    if errors:
        print("\n".join(errors))
        return 1

    print("文章詞內保護與不可拆片語已通過瀏覽器 DOM 驗證。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
