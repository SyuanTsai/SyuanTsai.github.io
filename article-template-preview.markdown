---
layout: post
title: "出版文章範本預覽"
date: 2026-08-30
last_modified_at: 2026-08-30
description: "以實際文章版型預覽起頭、自由內容章節、句尾引用、參考資料與更新紀錄。"
categories: [Template, Preview]
tags: [markdown, jekyll, citation]
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

這是一篇使用正式文章版型產生的範本預覽。起頭不顯示固定標題，而是直接交代問題情境、背景或撰寫動機，以及讀者能從本文取得什麼。Jekyll 會把具有 Front Matter 的 Markdown 文章轉換成正式頁面。[^jekyll-posts]

需要外部資料支持的敘述，可以在句尾直接放入一個或多個引用；Kramdown 會依來源第一次出現的順序自動編號。[^kramdown-footnotes][^kramdown-converter]

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

![HTTP 請求處理流程](/assets/images/posts/article-format-example/request-flow.svg){: width="960" height="360" }

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
{: .update-history}
