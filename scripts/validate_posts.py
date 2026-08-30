#!/usr/bin/env python3
"""Validate the article contract without third-party Python packages."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


REQUIRED_FIELDS = ("title", "date", "description")
POST_FILENAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.(?:md|markdown)$"
)
DRAFT_FILENAME_RE = re.compile(
    r"^(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.(?:md|markdown)$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TOP_LEVEL_FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$")
NESTED_FIELD_RE = re.compile(r"^[ \t]+([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$")
FENCE_RE = re.compile(r"^\s*```(?P<language>[^`]*)$")
MARKDOWN_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)]+)\)")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\([^)]+\)")
FOOTNOTE_MARKER_RE = re.compile(r"\[\^(?P<name>[A-Za-z0-9][A-Za-z0-9-]*)\]")
FOOTNOTE_DEFINITION_RE = re.compile(
    r"^\s*\[\^(?P<name>[A-Za-z0-9][A-Za-z0-9-]*)\]:\s*(?P<content>.+)$"
)
UPDATE_ROW_RE = re.compile(
    r"^\s*\|\s*(?P<date>\d{4}-\d{2}-\d{2}|YYYY-MM-DD)\s*\|\s*(?P<content>[^|]+?)\s*\|\s*$"
)


class FrontMatterError(ValueError):
    """Raised when a Markdown document cannot be parsed safely."""


@dataclass(frozen=True)
class Document:
    path: Path
    fields: dict[str, Any]
    body: str


def _parse_inline_list(value: str) -> list[str]:
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [
        _unquote(item.strip())
        for item in next(csv.reader([inner], skipinitialspace=True))
        if item.strip()
    ]


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value.strip()


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return _parse_inline_list(value)
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return _unquote(value)


def _parse_indented_block(lines: list[str]) -> Any:
    meaningful = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if not meaningful:
        return ""

    if all(line.lstrip().startswith("-") for line in meaningful):
        return [
            _unquote(line.lstrip()[1:].strip())
            for line in meaningful
            if line.lstrip()[1:].strip()
        ]

    nested: dict[str, Any] = {}
    for line in meaningful:
        match = NESTED_FIELD_RE.match(line)
        if not match:
            return " ".join(item.strip() for item in meaningful)
        nested[match.group(1)] = parse_scalar(match.group(2) or "")
    return nested


def parse_front_matter(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontMatterError("檔案必須以 Front Matter 分隔線 `---` 開始")

    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as error:
        raise FrontMatterError("找不到 Front Matter 結束分隔線 `---`") from error

    front_matter = lines[1:closing_index]
    fields: dict[str, Any] = {}
    index = 0

    while index < len(front_matter):
        line = front_matter[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue

        match = TOP_LEVEL_FIELD_RE.match(line)
        if not match:
            raise FrontMatterError(f"無法解析 Front Matter 第 {index + 2} 行：{line.strip()}")

        key = match.group(1)
        raw_value = (match.group(2) or "").strip()
        if key in fields:
            raise FrontMatterError(f"Front Matter 欄位 `{key}` 重複宣告")

        next_index = index + 1
        indented: list[str] = []
        while next_index < len(front_matter):
            candidate = front_matter[next_index]
            if TOP_LEVEL_FIELD_RE.match(candidate):
                break
            if candidate and not candidate[0].isspace() and not candidate.lstrip().startswith("#"):
                break
            indented.append(candidate)
            next_index += 1

        if raw_value in {">", ">-", ">+", "|", "|-", "|+"}:
            value = " ".join(item.strip() for item in indented if item.strip())
            fields[key] = value
            index = next_index
            continue

        if not raw_value and indented:
            fields[key] = _parse_indented_block(indented)
            index = next_index
            continue

        fields[key] = parse_scalar(raw_value)
        index += 1

    body = "\n".join(lines[closing_index + 1 :]).lstrip("\n")
    return Document(path=path, fields=fields, body=body)


def _is_present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def _validate_date(value: Any, field_name: str, errors: list[str]) -> date | None:
    text = str(value).strip()
    if not DATE_RE.fullmatch(text):
        errors.append(f"`{field_name}` 必須使用 YYYY-MM-DD 格式")
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        errors.append(f"`{field_name}` 不是有效日期：{text}")
        return None


def _validate_body(document: Document, errors: list[str]) -> None:
    in_fence = False
    prose_lines: list[str] = []
    for line_number, line in enumerate(document.body.splitlines(), start=1):
        fence = FENCE_RE.match(line)
        if fence:
            if not in_fence and not fence.group("language").strip():
                errors.append(f"本文第 {line_number} 行的程式碼區塊缺少語言名稱")
            in_fence = not in_fence
            prose_lines.append("")
            continue
        if not in_fence and re.match(r"^\s*#\s+", line):
            errors.append(f"本文第 {line_number} 行使用 H1；文章本文必須從 H2 (`##`) 開始")
        prose_lines.append("" if in_fence else line)

    if in_fence:
        errors.append("本文有未關閉的 fenced code block")

    prose_body = "\n".join(prose_lines)
    prose_body = re.sub(
        r"<!--.*?-->",
        lambda match: "\n" * match.group(0).count("\n"),
        prose_body,
        flags=re.DOTALL,
    )
    prose_without_inline_code = re.sub(r"`[^`\n]*`", "", prose_body)

    for line_number, line in enumerate(prose_without_inline_code.splitlines(), start=1):
        if re.search(r"<br\s*/?>", line, flags=re.IGNORECASE):
            errors.append(
                f"本文第 {line_number} 行不可使用 HTML `<br>` 控制換行；請用空白行分段"
            )
        if re.search(r" {2,}$", line):
            errors.append(
                f"本文第 {line_number} 行不可使用行尾雙空白強制換行；請用空白行分段"
            )
        if re.search(r"(?<!\\)\\\s*$", line):
            errors.append(
                f"本文第 {line_number} 行不可使用行尾反斜線強制換行；請用空白行分段"
            )

    for image in MARKDOWN_IMAGE_RE.finditer(prose_body):
        if not image.group("alt").strip():
            errors.append("Markdown 圖片必須提供非空的替代文字")

        line_end = prose_body.find("\n", image.end())
        if line_end == -1:
            line_end = len(prose_body)
        suffix = prose_body[image.end() : line_end]
        attributes = re.match(r"\s*\{:\s*(?P<attributes>[^}\n]*)\}", suffix)
        width = None
        height = None
        if attributes:
            attribute_text = attributes.group("attributes")
            width = re.search(r"\bwidth\s*=\s*([\"']?)([1-9]\d*)\1", attribute_text)
            height = re.search(r"\bheight\s*=\s*([\"']?)([1-9]\d*)\1", attribute_text)
        if not width or not height:
            errors.append(
                "Markdown 圖片後必須緊接原始像素尺寸，例如 "
                '`{: width="960" height="540" }`'
            )

    for image_tag in re.finditer(r"<img\b[^>]*>", prose_body, flags=re.IGNORECASE):
        if not re.search(r"\balt\s*=\s*(['\"]).+?\1", image_tag.group(0), flags=re.IGNORECASE):
            errors.append("HTML `<img>` 必須提供非空的 `alt` 屬性")


def _h2_sections(body: str) -> list[tuple[str, int]]:
    sections: list[tuple[str, int]] = []
    in_fence = False
    for line_number, line in enumerate(body.splitlines()):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^\s*##(?!#)\s+(.+?)\s*$", line)
        if match:
            sections.append((match.group(1).strip(), line_number))
    return sections


def validate_article_structure(
    document: Document,
    *,
    allow_placeholders: bool = False,
    require_citation: bool = False,
) -> list[str]:
    """Validate the reviewed article body contract for new template artifacts."""

    errors: list[str] = []
    lines = document.body.splitlines()
    sections = _h2_sections(document.body)

    if not sections:
        return ["文章內文至少需要一個 H2"]

    first_heading_line = sections[0][1]
    opening = "\n".join(lines[:first_heading_line])
    opening = re.sub(r"<!--.*?-->", "", opening, flags=re.DOTALL)
    opening = re.sub(r"<[^>]+>", "", opening).strip()
    if not opening:
        errors.append("第一個 H2 前必須有不顯示標題的起頭文字")

    names = [name for name, _ in sections]
    if any(re.sub(r"[`*_]", "", name).strip() == "內容" for name in names):
        errors.append("主要章節不可使用無法辨識目的的 `內容` 作為標題")

    if names.count("參考資料") != 1:
        errors.append("文章必須且只能有一個 `## 參考資料`")
    if names.count("更新紀錄") != 1:
        errors.append("文章必須且只能有一個 `## 更新紀錄`")

    reference_line = next((line for name, line in sections if name == "參考資料"), None)
    update_line = next((line for name, line in sections if name == "更新紀錄"), None)
    if len(names) < 2 or names[-2:] != ["參考資料", "更新紀錄"]:
        errors.append("`參考資料` 與 `更新紀錄` 必須依序為最後兩個 H2")

    definitions: dict[str, int] = {}
    markers: set[str] = set()
    for line_number, line in enumerate(lines):
        definition = FOOTNOTE_DEFINITION_RE.match(line)
        if definition:
            name = definition.group("name")
            if name in definitions:
                errors.append(f"引用來源代號 `[^{name}]` 重複定義")
            definitions[name] = line_number
            continue
        markers.update(match.group("name") for match in FOOTNOTE_MARKER_RE.finditer(line))

    if require_citation and not markers:
        errors.append("文章範例至少需要一個句尾引用")

    for name in sorted(markers - definitions.keys()):
        errors.append(f"句尾引用 `[^{name}]` 缺少來源定義")
    for name in sorted(definitions.keys() - markers):
        errors.append(f"來源定義 `[^{name}]` 沒有被內文引用")

    placeholder_lines = [
        index
        for index, line in enumerate(lines)
        if line.strip() == "{:footnotes}"
        and index > 0
        and re.match(r"^\s*(?:\d+\.|[-*+])\s+", lines[index - 1])
    ]
    if markers and len(placeholder_lines) != 1:
        errors.append("使用句尾引用時，參考資料必須包含一個 `{:footnotes}` 引用清單定位")

    if reference_line is not None and update_line is not None and reference_line < update_line:
        for name, line_number in definitions.items():
            if not reference_line < line_number < update_line:
                errors.append(f"來源定義 `[^{name}]` 必須放在 `參考資料` 章節內")
        for line_number in placeholder_lines:
            if not reference_line < line_number < update_line:
                errors.append("`{:footnotes}` 必須放在 `參考資料` 章節內")

    history_rows: list[tuple[str, str]] = []
    if update_line is not None:
        for line in lines[update_line + 1 :]:
            row = UPDATE_ROW_RE.match(line)
            if row:
                history_rows.append((row.group("date"), row.group("content").strip()))
    if not history_rows:
        errors.append("`更新紀錄` 必須包含日期與更新內容表格，初版也要保留一列")

    if "last_modified_at" not in document.fields or not _is_present(document.fields["last_modified_at"]):
        errors.append("新版文章結構必須設定 `last_modified_at`")

    if not allow_placeholders and history_rows:
        parsed_history_dates: list[date] = []
        for history_date, _ in history_rows:
            try:
                parsed_history_dates.append(date.fromisoformat(history_date))
            except ValueError:
                errors.append(f"更新紀錄日期不是有效日期：{history_date}")

        publish_date = str(document.fields.get("date", "")).strip()
        if publish_date and publish_date not in {row_date for row_date, _ in history_rows}:
            errors.append("更新紀錄必須包含與 Front Matter `date` 相同的初版日期")

        modified_date = str(document.fields.get("last_modified_at", "")).strip()
        if parsed_history_dates and modified_date != max(parsed_history_dates).isoformat():
            errors.append("`last_modified_at` 必須與更新紀錄的最新日期相同")

    return errors


def validate_document(document: Document, kind: str, root: Path) -> list[str]:
    errors: list[str] = []
    fields = document.fields

    for field in REQUIRED_FIELDS:
        if field not in fields or not _is_present(fields[field]):
            errors.append(f"缺少必要 Front Matter 欄位 `{field}` 或其值為空")

    for text_field in ("title", "description"):
        if text_field in fields and _is_present(fields[text_field]) and not isinstance(fields[text_field], str):
            errors.append(f"`{text_field}` 必須是字串")

    publish_date = None
    if "date" in fields and _is_present(fields["date"]):
        publish_date = _validate_date(fields["date"], "date", errors)

    filename_match = POST_FILENAME_RE.fullmatch(document.path.name) if kind == "post" else DRAFT_FILENAME_RE.fullmatch(document.path.name)
    if filename_match is None:
        expected = "YYYY-MM-DD-lowercase-kebab-case.markdown" if kind == "post" else "lowercase-kebab-case.markdown"
        errors.append(f"檔名必須符合 `{expected}`")
    elif kind == "post" and publish_date is not None:
        if filename_match.group("date") != publish_date.isoformat():
            errors.append("檔名日期必須與 Front Matter `date` 相同")

    if fields.get("layout") not in (None, "post"):
        errors.append("文章 `layout` 只能省略或設為 `post`")

    for list_field in ("categories", "tags"):
        if list_field in fields:
            value = fields[list_field]
            if not isinstance(value, list) or not value or any(not str(item).strip() for item in value):
                errors.append(f"`{list_field}` 必須是非空 YAML 陣列，例如 `[Code, Review]`")

    categories = fields.get("categories")
    if isinstance(categories, list):
        for category in categories:
            if not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", str(category)):
                errors.append(
                    f"分類 `{category}` 會形成網址路徑，必須只使用英文字母、數字與單一連字號"
                )

    modified_date = None
    if "last_modified_at" in fields:
        modified_date = _validate_date(fields["last_modified_at"], "last_modified_at", errors)
    if publish_date and modified_date and modified_date < publish_date:
        errors.append("`last_modified_at` 不得早於 `date`")

    draft = fields.get("draft")
    if draft is not None and not isinstance(draft, bool):
        errors.append("`draft` 只能是布林值 `true` 或 `false`")
    if kind == "post" and draft is True:
        errors.append("已發布文章不可設定 `draft: true`；請移至 `_drafts/`")
    if kind == "draft" and draft is not True:
        errors.append("`_drafts/` 內的文章必須設定 `draft: true`")

    permalink = fields.get("permalink")
    if permalink is not None:
        permalink_text = str(permalink)
        if not permalink_text.startswith("/") or "?" in permalink_text or "#" in permalink_text:
            errors.append("`permalink` 必須是以 `/` 開頭且不含 query 或 fragment 的站內路徑")

    canonical_url = fields.get("canonical_url")
    if canonical_url is not None and not str(canonical_url).startswith("https://"):
        errors.append("`canonical_url` 必須是完整的 HTTPS URL")

    image = fields.get("image")
    if image is not None:
        if not isinstance(image, dict):
            errors.append("`image` 必須包含 `path` 與 `alt` 子欄位")
        else:
            image_path = str(image.get("path", "")).strip()
            image_alt = str(image.get("alt", "")).strip()
            if not image_path.startswith("/assets/images/"):
                errors.append("`image.path` 必須使用 `/assets/images/` 下的站內絕對路徑")
            elif not (root / image_path.lstrip("/")).is_file():
                errors.append(f"`image.path` 指向不存在的檔案：{image_path}")
            if not image_alt:
                errors.append("`image.alt` 不得為空")

    _validate_body(document, errors)
    if kind == "post" and not _h2_sections(document.body):
        errors.append("已發布文章至少需要一個 H2，才能在初始版面保留目錄欄")
    return errors


def validate_example(document: Document) -> list[str]:
    requirements: tuple[tuple[str, bool], ...] = (
        ("至少一個 H2 標題", bool(re.search(r"^##\s+", document.body, flags=re.MULTILINE))),
        ("具語言名稱的程式碼區塊", bool(re.search(r"^```[A-Za-z0-9_+.#-]+\s*$", document.body, flags=re.MULTILINE))),
        ("Markdown 表格", bool(re.search(r"^\s*\|?.+\|.+\n\s*\|?\s*:?-{3,}", document.body, flags=re.MULTILINE))),
        ("含替代文字的圖片", any(match.group("alt").strip() for match in MARKDOWN_IMAGE_RE.finditer(document.body))),
        ("具描述文字的連結", bool(MARKDOWN_LINK_RE.search(document.body))),
        ("引用區塊", bool(re.search(r"^>\s+", document.body, flags=re.MULTILINE))),
        ("note 提示區塊", 'class="note"' in document.body),
        ("warning 警告區塊", 'class="warning"' in document.body),
    )
    return [f"完整元素範例缺少：{name}" for name, passed in requirements if not passed]


def discover_markdown(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted((*directory.glob("*.md"), *directory.glob("*.markdown")))


def _format_errors(path: Path, root: Path, errors: Iterable[str]) -> list[str]:
    relative = path.relative_to(root)
    return [f"{relative}: {error}" for error in errors]


def validate_repository(root: Path) -> tuple[list[str], int, int]:
    errors: list[str] = []
    post_paths = discover_markdown(root / "_posts")
    draft_paths = discover_markdown(root / "_drafts")

    required_files = (
        root / "docs/article-authoring.md",
        root / "_templates/post.markdown",
        root / "_drafts/article-format-example.markdown",
        root / "article-template-preview.markdown",
    )
    for required_file in required_files:
        if not required_file.is_file():
            errors.append(f"{required_file.relative_to(root)}: 必要檔案不存在")

    post_urls: dict[str, Path] = {}
    for kind, paths in (("post", post_paths), ("draft", draft_paths)):
        for path in paths:
            try:
                document = parse_front_matter(path)
            except FrontMatterError as error:
                errors.append(f"{path.relative_to(root)}: {error}")
                continue
            errors.extend(_format_errors(path, root, validate_document(document, kind, root)))
            if kind == "post":
                try:
                    output_url = post_output_url(document)
                except (KeyError, TypeError, ValueError):
                    continue
                if output_url in post_urls:
                    errors.append(
                        f"{path.relative_to(root)}: 文章網址 `{output_url}` 與 "
                        f"{post_urls[output_url].relative_to(root)} 重複"
                    )
                else:
                    post_urls[output_url] = path

    template_path = root / "_templates/post.markdown"
    if template_path.is_file():
        try:
            template = parse_front_matter(template_path)
            for field in REQUIRED_FIELDS:
                if field not in template.fields or not _is_present(template.fields[field]):
                    errors.append(f"{template_path.relative_to(root)}: 範本缺少 `{field}`")
            if re.search(r"^\s*#\s+", template.body, flags=re.MULTILINE):
                errors.append(f"{template_path.relative_to(root)}: 範本本文不可包含 H1")
            template_body_errors: list[str] = []
            _validate_body(template, template_body_errors)
            errors.extend(_format_errors(template_path, root, template_body_errors))
            errors.extend(
                _format_errors(
                    template_path,
                    root,
                    validate_article_structure(
                        template,
                        allow_placeholders=True,
                        require_citation=True,
                    ),
                )
            )
        except FrontMatterError as error:
            errors.append(f"{template_path.relative_to(root)}: {error}")

    example_path = root / "_drafts/article-format-example.markdown"
    if example_path.is_file():
        try:
            example = parse_front_matter(example_path)
            errors.extend(_format_errors(example_path, root, validate_example(example)))
            errors.extend(
                _format_errors(
                    example_path,
                    root,
                    validate_article_structure(example, require_citation=True),
                )
            )
        except FrontMatterError:
            pass

    preview_path = root / "article-template-preview.markdown"
    if preview_path.is_file():
        try:
            preview = parse_front_matter(preview_path)
            preview_errors = validate_document(preview, "preview", root)
            preview_errors.extend(validate_article_structure(preview, require_citation=True))
            if preview.fields.get("permalink") != "/preview/article-template/":
                preview_errors.append("未列出預覽必須固定使用 `/preview/article-template/`")
            if preview.fields.get("unlisted") is not True:
                preview_errors.append("未列出預覽必須設定 `unlisted: true`")
            if preview.fields.get("sitemap") is not False:
                preview_errors.append("未列出預覽必須設定 `sitemap: false`")
            errors.extend(_format_errors(preview_path, root, preview_errors))
        except FrontMatterError as error:
            errors.append(f"{preview_path.relative_to(root)}: {error}")

    return errors, len(post_paths), len(draft_paths)


def post_output_url(document: Document) -> str:
    permalink = document.fields.get("permalink")
    if permalink:
        return str(permalink)

    filename = POST_FILENAME_RE.fullmatch(document.path.name)
    if filename is None:
        raise ValueError(f"無法由檔名計算文章網址：{document.path.name}")

    category_parts = []
    for category in document.fields.get("categories", []):
        slug = re.sub(r"[^a-z0-9]+", "-", str(category).lower()).strip("-")
        if slug:
            category_parts.append(slug)

    published = date.fromisoformat(str(document.fields["date"]))
    parts = [*category_parts, f"{published:%Y}", f"{published:%m}", f"{published:%d}", f"{filename.group('slug')}.html"]
    return "/" + "/".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    root = args.root.resolve()

    errors, post_count, draft_count = validate_repository(root)
    if errors:
        print("Article validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Validated {post_count} published posts, {draft_count} drafts, "
        "the reusable template, the unlisted preview, and the authoring guide."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
