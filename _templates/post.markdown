---
title: "文章標題"
date: YYYY-MM-DD
last_modified_at: YYYY-MM-DD
description: "用一到兩句話說明文章解決的問題與讀者能取得的結果。"
categories: [Category]
tags: [tag-one, tag-two]
draft: false
# image:
#   path: /assets/images/posts/article-slug/cover.svg
#   alt: "描述圖片傳達的資訊"
---

<!--
分段原則：同一核心概念通常寫成 2–4 句；主題、步驟或論述角度改變時，以空白行另起一段。
不要依固定字數斷行，也不要用 <br>、行尾雙空白或行尾反斜線控制換行；引用代號必須跟著所支持的句子。
-->

第一段交代問題情境、背景或撰寫動機。起頭固定需要，但不顯示「起頭」標題。

第二段說明讀者能從本文取得什麼。需要來源支持的敘述，直接在所支持的句尾加入引用。[^source-name]

## 依文章主題命名的主要章節

內容章節依文章性質自由組合，不要使用無法辨識目的的「內容」作為標題。可選擇的內容包括適用範圍、前置條件、核心概念、根因分析、實作方式、驗證結果、限制、替代方案與結論。

### 關鍵步驟

```text
將 text 改成實際語言，例如 csharp、sql、json 或 bash。
```

<aside class="note" role="note" markdown="1">
**提示：** 補充能降低讀者誤解或重做成本的資訊。
</aside>

## 驗證結果

| 驗證項目 | 結果 |
| --- | --- |
| 功能 | 通過 |
| 回歸 | 通過 |

<!--
圖片資產規則：
1. 一篇文章或一個使用單位對應 Media-Assets 的一個公開 Issue。
2. Issue 標題使用「YYYY-MM-DD | 專案 | 內容識別碼 | article-assets」；日期為首次建立日，後續補圖不更改。
3. 同篇文章有多張圖時，為每張邏輯圖片或同圖尺寸版本建立穩定的 Asset ID，並記在 Issue 索引與個別 comment；第一筆資產可直接記在 Issue 本文。
4. 將下列網址替換成 GitHub 上傳完成後產生的完整附件網址，並同步更新 docs/static-assets-manifest.yml。
5. 替代文字必須描述圖片傳達的資訊；width 與 height 使用原始像素尺寸。非首屏關鍵圖片保留 loading="lazy"。
-->
![替代文字](https://github.com/user-attachments/assets/REPLACE_WITH_GITHUB_UUID){: width="960" height="540" loading="lazy" }

> 只在需要保留來源語意時使用引用區塊。

## 參考資料

[^source-name]: [具體且可辨識的來源名稱](https://example.com/source) — 發布者

1. 引用資料由系統自動產生
{:footnotes}

## 更新紀錄

| 日期 | 更新內容 |
| --- | --- |
| YYYY-MM-DD | 初版發布 |
{: .update-history}
