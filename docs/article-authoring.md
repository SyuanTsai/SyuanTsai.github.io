# 文章撰寫與發布規範

本文件定義本站技術文章的檔名、Front Matter、Markdown 與基本 SEO 規則。新增文章時，只需要新增文章與其圖片，不需要修改 Layout、Include 或 SCSS。

## 快速開始

1. 複製 `_templates/post.markdown` 到 `_posts/YYYY-MM-DD-lowercase-kebab-case.markdown`。
2. 將檔名日期、Front Matter 的 `date` 與文章內容改為實際值。
3. 執行 `python3 scripts/validate_posts.py`。
4. 執行 `bundle exec jekyll build --strict_front_matter`。
5. 執行 `python3 scripts/verify_generated_seo.py _site`。
6. 在桌機與手機寬度預覽文章，確認圖片、表格與程式碼區塊沒有造成整頁水平捲動。

完整元素範例位於 `_drafts/article-format-example.markdown`。使用 `bundle exec jekyll serve --drafts` 可在本機預覽；標準建置與 GitHub Pages 不會發布 `_drafts` 內容。

## 檔名、Slug 與 Permalink

### 已發布文章

- 位置：`_posts/`
- 格式：`YYYY-MM-DD-lowercase-kebab-case.markdown`
- 日期必須與 Front Matter 的 `date` 相同。
- Slug 只使用小寫英文字母、數字與單一連字號，不使用空白、底線或連續連字號。
- 本站固定的預設 Permalink 為 `/:categories/:year/:month/:day/:title:output_ext`。

例如：

```text
_posts/2026-08-29-debugging-http-timeouts.markdown
```

搭配 `categories: [CSharp, HTTP]` 時，網址會是：

```text
/csharp/http/2026/08/29/debugging-http-timeouts.html
```

文章發布後不要任意修改檔名、分類或網址。若為了整理檔名而必須保留既有網址，請在 Front Matter 明確設定 `permalink`。

### 草稿

- 位置：`_drafts/`
- 格式：`lowercase-kebab-case.markdown`
- Front Matter 必須設定 `draft: true`，並保留預計發布的 `date`。
- 發布時移至 `_posts/YYYY-MM-DD-slug.markdown`，並將 `draft` 改為 `false` 或移除。

## Front Matter Schema

| 欄位 | 必要 | 格式 | 用途 |
| --- | --- | --- | --- |
| `title` | 是 | 非空字串 | 頁面 H1、HTML Title 與 SEO Title。 |
| `date` | 是 | `YYYY-MM-DD` | 發布日期；已發布文章需與檔名日期一致。 |
| `description` | 是 | 建議 50–160 字的單行字串 | 首頁／文章列表摘要與 SEO Description。 |
| `categories` | 否 | YAML 陣列 | 穩定的大分類，也會形成預設網址路徑；每個值只使用英文字母、數字與單一連字號。 |
| `tags` | 否 | YAML 陣列 | 較細的文章主題標籤。 |
| `last_modified_at` | 否 | `YYYY-MM-DD` | 內容有實質更新時填寫，不得早於 `date`。 |
| `draft` | 否 | `true` 或 `false` | 編輯狀態；`true` 只能放在 `_drafts/`。 |
| `image` | 否 | 含 `path` 與 `alt` 的 mapping | 文章代表圖片；路徑使用 `/assets/images/...`，替代文字不得為空。 |
| `permalink` | 否 | 以 `/` 開頭的站內路徑 | 只用於保留既有網址或必要的固定網址。 |
| `canonical_url` | 否 | 完整 HTTPS URL | 只有內容原始來源不是本站時才覆寫 Canonical。 |

`layout` 已由 `_config.yml` 對所有 posts 預設為 `post`，新文章不需要重複設定。

建議格式：

```yaml
---
title: "診斷 HTTP Timeout 的實作紀錄"
date: 2026-08-29
description: "整理 HTTP Timeout 的觀察方式、根因定位與修正驗證。"
categories: [CSharp, HTTP]
tags: [timeout, diagnostics]
last_modified_at: 2026-08-30
draft: false
image:
  path: /assets/images/posts/debugging-http-timeouts/request-flow.svg
  alt: "HTTP 請求依序通過 Client、API 與下游服務"
---
```

## Markdown 格式

### 標題

- 文章頁的 H1 由 `title` 自動產生，本文不要再寫 `# H1`。
- 主要段落從 `##` 開始，子段落依序使用 `###`、`####`，不要跳級。
- 標題應描述內容，不使用「內容」、「其他」等無法辨識目的的名稱。

### 程式碼

程式碼一律使用 fenced code block，並指定語言：

````markdown
```csharp
using var response = await httpClient.SendAsync(request);
```
````

### 表格

```markdown
| 狀態 | 判斷方式 |
| --- | --- |
| Timeout | 檢查取消權杖與下游耗時 |
| 5xx | 檢查服務端記錄與相依服務 |
```

表格與程式碼區塊會在內容過寬時自行橫向捲動，不應用空白或硬換行破壞內容。

### 圖片

圖片放在 `assets/images/posts/<slug>/`，必須提供能說明資訊的替代文字：

```markdown
![HTTP 請求處理流程](/assets/images/posts/debugging-http-timeouts/request-flow.svg)
```

### 連結與引用

- 連結文字需描述目的，例如 `[HttpClient 官方文件](https://learn.microsoft.com/)`，不要只寫「這裡」。
- 引用來源或需要保留原句語意時使用 `>`；一般重點不要濫用引用格式。

```markdown
> Timeout 是結果；必須再確認限制發生在 Client、API 或下游服務。
```

### 提示與警告

一般補充使用 `note`，可能造成錯誤或資料風險的內容使用 `warning`：

```html
<aside class="note" role="note" markdown="1">
**提示：** 先保存失敗請求的時間與 Correlation ID。
</aside>

<aside class="warning" aria-label="注意" markdown="1">
**注意：** 不要把 Token、Cookie 或個人資料寫入公開文章。
</aside>
```

## 基本 SEO 行為

`_includes/head.html` 使用 `jekyll-seo-tag`。文章建置後會自動產生：

- `<title>`：取自文章 `title` 與網站名稱。
- `<meta name="description">`：取自文章 `description`。
- `<link rel="canonical">`：預設由 `_config.yml` 的 `url` 加上文章網址組成。

除非內容的原始來源確實在其他網址，否則不要設定 `canonical_url`。來源規則可參考 [Jekyll Posts 文件](https://jekyllrb.com/docs/posts/) 與 [jekyll-seo-tag 使用說明](https://github.com/jekyll/jekyll-seo-tag/blob/master/docs/usage.md)。

## 驗證與錯誤處理

`python3 scripts/validate_posts.py` 會檢查：

- 檔名、Slug 與日期格式。
- 必要 Front Matter 是否存在且非空。
- categories、tags、draft、image 與 permalink 格式。
- 本文是否誤用 H1、程式碼區塊是否缺少語言、圖片是否缺少替代文字。
- 完整元素範例是否涵蓋程式碼、表格、圖片、連結、引用與提示區塊。

檢查失敗時會列出檔名與明確原因並回傳非零結束碼。CI 會在 Jekyll 建置後再執行 `scripts/verify_generated_seo.py`，確認每篇已發布文章的 Title、Description 與 Canonical URL 都存在且符合 Front Matter。
