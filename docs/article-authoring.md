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

正式版型的未列出預覽來源是 `article-template-preview.markdown`，固定網址為 `/preview/article-template/`。它不屬於 posts，不會出現在首頁、文章列表或導覽，並輸出 `noindex, nofollow, noarchive`。這只是未列出網址，不是權限保護；任何知道網址的人仍可直接開啟。

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

新版文章範本會先讓 `last_modified_at` 與初版日期相同；日後更新時，必須同步修改成「更新紀錄」最新一列的日期。

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

## 文章內文結構

文章固定使用以下四個部分：

1. 起頭：固定需要，但不顯示「起頭」標題。用一到三段文字交代問題情境、背景或撰寫動機，以及讀者能取得什麼。
2. 主要內容：依主題自由組合，H2 必須描述實際目的，不使用「內容」作為標題。
3. 參考資料：固定為倒數第二個 H2。需要來源支持的敘述直接在句尾加入引用。
4. 更新紀錄：固定為最後一個 H2；初版也要保留一列紀錄。

主要內容可以依文章性質選用以下模組，不要求每篇全部具備：

- 適用範圍與前置條件。
- 核心概念或根因分析。
- 實作方式與程式碼。
- 驗證方式與結果。
- 限制、風險與常見錯誤。
- 替代方案與選擇理由。
- 結論。

基本骨架：

```markdown
第一段交代問題情境、背景或撰寫動機。

第二段說明讀者能從本文取得什麼，需要來源時直接在所支持的句尾加入引用。[^source-name]

## 依文章主題命名的主要章節

### 需要時才增加的子章節

## 參考資料

[^source-name]: [來源名稱](https://example.com/source) — 發布者

1. 引用資料由系統自動產生
{:footnotes}

## 更新紀錄

| 日期 | 更新內容 |
| --- | --- |
| YYYY-MM-DD | 初版發布 |
{: .update-history}
```

## Markdown 格式

### 標題

- 文章頁的 H1 由 `title` 自動產生，本文不要再寫 `# H1`。
- 主要段落從 `##` 開始，子段落依序使用 `###`、`####`，不要跳級。
- 標題應描述內容，不使用「內容」、「其他」等無法辨識目的的名稱。

### 分段與自然換行

- 同一段只處理一個核心概念，通常由 2–4 句組成；句數只是檢查訊號，不是固定字數限制。
- 主題、步驟或論述角度改變時，以一個 Markdown 空白行另起段落。
- 引用代號必須緊接其支持的句子，不可獨立成行。
- 不依固定字數斷行，也不使用 `<br>`、行尾雙空白或行尾反斜線控制一般內文版面。
- 原始 Markdown 可依編輯需要換行；一般單行換行是 soft wrap，只有空白行會建立新段落。
- 版面由瀏覽器依文章內容欄寬度自然換行；程式碼、表格、圖片與提示區塊仍可使用完整內容寬度。
- 全站使用繁體中文的嚴格標點斷行規則；支援詞組分析的瀏覽器會自動避免在常見中文詞組中間斷行。
- 若產品名稱、專有名詞或短複合詞被瀏覽器錯誤拆開，只標記必要的短語為 `<span class="keep-phrase">不可拆短語</span>`；不要包住完整句子或段落，以免窄螢幕溢出。

```markdown
這一段交代問題情境與讀者能取得的結果。

接著切換到實作或出版機制，因此另起一段，並把引用留在所支持的句尾。[^source-name]

這個短語在任何欄寬都不應拆開：<span class="keep-phrase">建立資產索引</span>。
```

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

網站主內容中的所有表格都會自動填滿內容欄；表格與程式碼區塊在內容過寬時會自行橫向捲動，不應用空白或硬換行破壞內容。

### 圖片

文章內文圖片優先上傳至公開 `SyuanTsai/Media-Assets` Issue，使用 GitHub 產生的完整匿名化附件網址。上傳前先以語意化檔名保存來源並計算 SHA-256，再依 `docs/static-assets.md` 更新 manifest。既有文章與文章代表圖片仍可使用 `/assets/images/posts/<slug>/`，不需要為了新規則搬移。

#### Issue 與多圖管理

- 一篇文章或一個使用單位只建立一個 Issue，不因圖片數量增加而拆成多個 Issue。
- Issue 標題使用 `YYYY-MM-DD | 專案 | 內容識別碼 | article-assets`；日期代表首次建立日，後續補圖或換圖不更改標題日期。
- Issue 本文保存 Target project、Content identifier、Asset index 與公開性確認。第一筆資產可直接記在本文；後續每張邏輯圖片或同圖的尺寸／格式版本各使用一則 comment。
- 每張圖使用穩定且可辨識的 Asset ID，例如 `article-template/rocket-example`，不可使用 `image-01`、`new` 或 `final`。
- 共用 Logo、作者頭像或跨文章圖示不掛在個別文章 Issue，另建 `shared-assets` Issue。
- 文章發布並驗證完成後可關閉 Issue；後續補圖時重新開啟，完成後再關閉。

目前的實際範例為 [Media-Assets Issue #1](https://github.com/SyuanTsai/Media-Assets/issues/1)，標題是 `2026-08-30 | notes.tw-syuan.com | article-template | article-assets`。

圖片必須提供能說明資訊的替代文字，並填入原始像素寬高。瀏覽器會在下載前依這組尺寸預留空間，避免內容載入時發生版面位移；CSS 仍會讓圖片在窄螢幕等比例縮小。將下列網址替換成 GitHub 上傳完成後產生的實際網址：

```markdown
![紫色火箭向右上方升空，尾部帶有橘色火焰](https://github.com/user-attachments/assets/<github-generated-uuid>){: width="120" height="120" loading="lazy" }
```

- 公開 Repository 的附件不需登入即可讀取；因此禁止上傳任何敏感或內部資料。
- GitHub 的圖片與 GIF 單檔上限為 10 MB；本站仍以最佳化後 500 KB 內為原則。
- GitHub 附件沒有自訂檔名、Cache 或 CORS 控制；圖片內容改變時必須重新上傳並更換網址。
- 不自行拼接附件網址，也不可只在文章保存網址而漏掉 Issue 索引與 manifest 紀錄。

### 連結、句尾引用與引用區塊

- 連結文字需描述目的，例如 `[HttpClient 官方文件](https://learn.microsoft.com/)`，不要只寫「這裡」。
- 一般來源標示使用 Kramdown footnote：在句尾放 `[^source-name]`，並在「參考資料」定義來源。
- 同一句可連續使用 `[^source-a][^source-b]`；相同來源代號重複出現時會維持同一筆參考資料。
- 來源代號使用可辨識的英文 kebab-case，不手動使用顯示編號；畫面編號由第一次引用順序自動產生。
- 需要保留來源原句、規則或觀點時才使用 `>`；一般重點不要濫用引用區塊。

```markdown
SQL Server 最多允許兩個 `WHEN MATCHED`。[^microsoft-merge]

## 參考資料

[^microsoft-merge]: [MERGE (Transact-SQL)](https://learn.microsoft.com/sql/t-sql/statements/merge-transact-sql) — Microsoft Learn

1. 引用資料由系統自動產生
{:footnotes}
```

`{:footnotes}` 會把引用清單固定在「參考資料」內；若省略，Kramdown 會把引用清單移到整份文件最後，導致它出現在「更新紀錄」後方。

引用區塊範例：

```markdown
> Timeout 是結果；必須再確認限制發生在 Client、API 或下游服務。
```

### 更新紀錄

- 固定放在文章最後一個 H2。
- 第一列記錄初版發布，日期與 `date` 相同。
- 後續只記錄對讀者有意義的內容變更，不記錄純排版或拼字修正。
- `last_modified_at` 必須等於最新一列日期。
- 表格後固定保留 `{: .update-history}`，讓更新紀錄填滿文章內容寬度。

```markdown
## 更新紀錄

| 日期 | 更新內容 |
| --- | --- |
| 2026-08-29 | 初版發布 |
| 2026-08-30 | 補充限制與官方文件引用 |
{: .update-history}
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
- 一般內文是否使用 `<br>`、行尾雙空白或行尾反斜線強制換行。
- 新範本與完整元素範例是否有起頭，以及「參考資料」與「更新紀錄」是否位於最後兩個 H2。
- 句尾引用是否都有來源定義，引用清單是否固定在「參考資料」。
- 更新紀錄是否包含初版日期，且最新日期是否與 `last_modified_at` 相同。
- 產出的更新紀錄表格是否具有 `update-history` class 並使用完整內容寬度。
- 完整元素範例是否涵蓋程式碼、表格、圖片、連結、引用與提示區塊。

檢查失敗時會列出檔名與明確原因並回傳非零結束碼。CI 會在 Jekyll 建置後再執行 `scripts/verify_generated_seo.py`，確認每篇已發布文章的 Title、Description 與 Canonical URL 都存在且符合 Front Matter。
