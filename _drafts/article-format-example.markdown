---
title: "技術文章完整格式範例"
date: 2026-08-29
description: "以 HTTP 請求診斷情境示範本站文章的標題、程式碼、表格、圖片、連結、引用與提示區塊。"
categories: [Documentation]
tags: [markdown, jekyll, example]
last_modified_at: 2026-08-29
draft: true
image:
  path: /assets/images/posts/article-format-example/request-flow.svg
  alt: "HTTP 請求依序通過 Client、API 與下游服務"
---

這篇草稿用一個簡化的 HTTP Timeout 情境，示範新文章可直接採用的所有共用元素。它只用於本機預覽與自動驗證，不會由正式 GitHub Pages 建置發布。

## 問題情境

API 偶爾回報 Timeout，但僅看例外訊息無法判斷限制發生在 Client、API 或下游服務。

> Timeout 是觀察到的結果，不等於已經找到根因。

![HTTP 請求處理流程](/assets/images/posts/article-format-example/request-flow.svg)

## 診斷程式碼

以下範例保留每次請求的 Correlation ID 與耗時，讓記錄可以對應到下游服務：

```csharp
using var request = new HttpRequestMessage(HttpMethod.Get, endpoint);
request.Headers.Add("X-Correlation-ID", correlationId);

var startedAt = Stopwatch.GetTimestamp();
using var response = await httpClient.SendAsync(request, cancellationToken);
var elapsed = Stopwatch.GetElapsedTime(startedAt);
```

<aside class="note" role="note" markdown="1">
**提示：** 先保存請求時間、Correlation ID 與各服務耗時，再比較 Timeout 設定。
</aside>

<aside class="warning" aria-label="注意" markdown="1">
**注意：** 公開記錄前必須移除 Token、Cookie、連線字串與個人資料。
</aside>

## 驗證矩陣

| 驗證項目 | 預期結果 | 記錄欄位 |
| --- | --- | --- |
| Client 取消 | API 收到取消訊號 | Correlation ID、取消時間 |
| API Timeout | 回傳一致的錯誤格式 | Status、Elapsed |
| 下游變慢 | 可定位到特定相依服務 | Dependency、Duration |

## 參考資料

- [Jekyll 文章格式官方文件](https://jekyllrb.com/docs/posts/)
- [Microsoft HttpClient 指南](https://learn.microsoft.com/en-us/dotnet/fundamentals/networking/http/httpclient-guidelines)
