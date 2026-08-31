---
layout: post
title: "初版文章範本預覽"
date: 2026-08-30
last_modified_at: 2026-08-31
description: "以實際文章版型預覽文章資訊、起頭、自由內容章節、圖片資產、句尾引用、參考資料與更新紀錄。"
eyebrow: "Template Preview"
permalink: /preview/article-template/
unlisted: true
sitemap: false
image:
  path: /assets/images/posts/article-format-example/request-flow.svg
  alt: "HTTP 請求依序通過 Client、API 與下游服務"
---

<aside class="warning" aria-label="未列出預覽" markdown="1">
**未列出預覽：** 此頁只供文章範本 Review，不會出現在首頁、文章列表或導覽，也要求搜尋引擎不要建立索引。知道網址的人仍可直接開啟。
</aside>

這是一篇使用正式文章版型產生的範本預覽。起頭不顯示固定標題，而是直接交代問題情境、背景或撰寫動機。

接著說明讀者能從本文取得什麼；同一個核心概念維持在同一段，論述角度改變時才用空白行另起一段，不依固定字數手動斷行。

Jekyll 會把具有 Front Matter 的 Markdown 文章轉換成正式頁面。需要外部資料支持的敘述，可直接在所支持的句尾放入一個或多個引用；Kramdown 會依來源首次出現順序自動編號。[^jekyll-posts][^kramdown-footnotes][^kramdown-converter]

## 文章資訊與固定網址

每篇正式文章只有一個內容網址；分類、標籤與年月封存使用各自的集合頁列出文章摘要，不複製文章內容。分類或標籤日後調整時，文章網址仍保持不變。

```yaml
---
title: "文章標題"
date: 2026-08-30
last_modified_at: 2026-08-30
description: "用一到兩句話說明文章解決的問題與讀者能取得的結果。"
categories: [code]
tags: [code-review, maintainability]
---
```

| 資訊類型 | 數量規則 | 網址範例 |
| --- | --- | --- |
| 正式文章 | 每篇一個 | `/2026/08/30/article-slug.html` |
| 主分類 | 每篇一個 | `/categories/code/` |
| 標籤 | 每篇一至五個 | `/tags/code-review/` |
| 月份封存 | 由發布日期產生 | `/archives/2026/08/` |

已發布文章若需要一次轉換網址，使用 `redirect_from` 保留舊網址入口；新文章不需要自行設定 `permalink`。

## 依文章主題命名的主要章節

主要內容不使用固定的「內容」標題。作者可以依文章性質選擇適用範圍、前置條件、核心概念、根因分析、實作方式、驗證結果、限制、替代方案或結論。

### 關鍵步驟

程式碼區塊必須標示實際語言，讓 Rouge 套用對應的語法醒目提示：

```csharp
using var request = new HttpRequestMessage(HttpMethod.Get, endpoint);
request.Headers.Add("X-Correlation-ID", correlationId);

using var response = await httpClient.SendAsync(request, cancellationToken);
```

<aside class="note" role="note" markdown="1">
**提示：** 提示區塊用來補充能降低讀者誤解或重做成本的資訊。
</aside>

<aside class="warning" aria-label="注意" markdown="1">
**注意：** 公開記錄前必須移除 Token、Cookie、連線字串與個人資料。
</aside>

## 驗證結果與限制

表格、圖片、引用區塊與其他元素只在內容需要時使用，不要求每篇文章全部具備。

| 驗證項目 | 預期結果 |
| --- | --- |
| 桌面版面 | 引用徽章不影響文字行高 |
| 手機版面 | 引用徽章可點擊並跳至參考資料 |
| 未列出狀態 | 不出現在首頁、文章列表或導覽 |
| 外部圖片 | GitHub Issue 附件依原始比例自動縮放 |
| 內容網址 | 分類與標籤頁只連回唯一正式文章 |

### 圖片與媒體資產

一篇文章或一個使用單位對應 `Media-Assets` 的一個公開 Issue。Issue 標題固定使用 `YYYY-MM-DD | 專案 | 內容識別碼 | 資產集合類型`。

同篇文章有多張圖片時，使用穩定且可辨識的 Asset ID，並建立資產索引。第一筆資產可記在 Issue 本文，後續每張邏輯圖片或同圖尺寸版本各用一則 comment 管理。一般中文詞組會以原生排版搭配自動語意詞保護自然換行，作者不需要加入不可拆標記。

圖片引用必須使用 GitHub 產生的完整附件網址、能表達圖片資訊的替代文字，以及原始像素寬高。非首屏關鍵圖片加入 lazy loading；網站 CSS 會在窄螢幕依比例縮小，不需要手動建立換行。

![紫色火箭向右上方升空，尾部帶有橘色火焰](https://github.com/user-attachments/assets/becf7d8d-5487-4f6c-b55e-23b80312e508){: width="120" height="120" loading="lazy" }

此範例的 Asset ID 為 `article-template/rocket-example`，來源、雜湊與公開附件網址記錄於 [Media-Assets Issue #1](https://github.com/SyuanTsai/Media-Assets/issues/1) 及本站資產 manifest。

> 只有需要保留來源原句、規則或觀點時才使用引用區塊；一般來源標示使用句尾引用。

## 參考資料

[^jekyll-posts]: [Posts](https://jekyllrb.com/docs/posts/) — Jekyll
[^kramdown-footnotes]: [Footnotes](https://kramdown.gettalong.org/syntax.html#footnotes) — Kramdown
[^kramdown-converter]: [HTML Converter：Footnotes](https://kramdown.gettalong.org/converter/html.html#footnotes) — Kramdown

1. 引用資料由系統自動產生
{:footnotes}

## 更新紀錄

| 日期 | 更新內容 |
| --- | --- |
| 2026-08-30 | 初版發布 |
| 2026-08-30 | 加入 GitHub Issue 圖片資產規範與實際附件範例 |
| 2026-08-30 | 修正繁體中文詞組與標點的自然斷行 |
| 2026-08-30 | 補齊單一文章網址、分類、標籤與封存規則 |
| 2026-08-31 | 加入自動語意詞組保護，並限制一般內文閱讀寬度 |
{: .update-history}
