# ADR: 保留並客製化 Jekyll／Minima

## 狀態

已接受，2026-09-01。

## 背景

本站目前由 GitHub Pages 使用 Jekyll 建置，內容以 Markdown 與 Front Matter 維護，版型以 Minima 為基礎客製化。既有文章、分類、標籤、封存、搜尋、SEO 與部署驗證皆依這套結構運作。

本次需要決定是維持現有架構，或遷移至其他靜態網站產生器與託管方式。網站目前規模小、沒有後端或資料庫需求，主要維護成本在內容與版型，而不是建置時間。

## 決策

保留 Jekyll 與 GitHub Pages，繼續客製化 Minima，不進行技術遷移。

* Ruby、GitHub Pages、Jekyll、remote theme 與 Actions 版本固定於 Repository。
* 內容維持 Markdown／Front Matter；版型、元件、樣式與資料各自集中管理。
* PR 使用 GitHub Pages 相同建置流程驗證，正式發布仍由 GitHub 管理的 Pages workflow 負責。
* 需要的新能力優先以建置期產物或小型驗證腳本完成，避免導入前端框架與額外託管服務。

## 理由

* 現有方案已符合純靜態技術筆記的內容與發布需求。
* GitHub Pages 可直接發布，帳號、權限、版本與故障紀錄集中在同一服務。
* 遷移會重做版型、網址相容、SEO、搜尋與部署驗證，現階段沒有足以抵銷成本的必要功能。
* 維持較少的執行環境與第三方服務，可降低安全、隱私與日常維護負擔。

## 影響

正面影響：

* 既有網址、內容格式與發布流程保持相容。
* 新文章不需學習新的內容模型或部署平台。
* 可重現建置與品質檢查可沿用現有 GitHub Actions。

限制與成本：

* 互動功能需使用瀏覽器端 JavaScript 或外部服務。
* 大量內容時，Jekyll 建置時間與純靜態搜尋可能需要重新評估。
* Minima 上游更新需持續檢查客製 Layout、Include 與 SCSS 的相容性。

## 重新評估條件

出現下列任一情況時再建立新 ADR：

* GitHub Pages 建置時間或限制明顯阻礙日常發布。
* 網站需要登入、後端 API、資料庫或伺服器端個人化。
* 內容規模使現有搜尋、分類或建置流程無法維持。
* GitHub Pages 或 Jekyll 的維護、安全或可用性不再符合需求。
