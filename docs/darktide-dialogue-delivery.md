# Darktide 字幕正式交付

## 目標與已核實問題

延續已確認的深色聊天版型、固定角色側邊、參與角色列、編號與右上角單一語言切換，將 Mods Repository 的單一對話正文同步至網站。來源固定為 Source `7e662fcda16219d775b84af50322be2e9cd9d62e` 與 Build 25606770。PR #49 已合併，正式入口改為 `https://notes.tw-syuan.com/darktide/`，本次以新的 Draft PR 交付。

全量網站已採預先產生的完整 HTML，由 Jekyll 直接複製靜態檔；避免每個事件 render 時反覆掃描 `site.pages`，也避免 Liquid 解讀原始字幕。本次延續此結構與已確認的玩家版面。

## 變更與相容性

- `darktide/index.html`、英文入口、各類型 `index.html` 只列分類與標題，不收字幕；清單每頁最多 50 筆。
- `darktide/{locale}/{event-type}/{event-id}/index.html` 每檔只包含自己的字幕或回應索引；大型群組另拆回應分頁。檔案保持兩格縮排、屬性分行及原始 bubble 文字空白。
- 任務通訊直接分一般戰役任務、死神試煉（遊戲內）及莫羅、左拉、布拉姆斯、佐林四個具名角色頁。三人故事回聲為額外選集，連到同一正文，不增加事件數。
- 共用資產為 `assets/css/darktide.css`。所有分類、相鄰頁、角色首句與語言切換使用原生連結，不依賴 JavaScript。
- 依擁有者最新指示，移除舊 `preview/darktide/` 與入口 hash 相容邏輯，不保留轉址或字幕副本。舊預覽網址不再支援。
- 正式頭使用 index/follow 與 `/darktide/` canonical。Darktide 使用 `darktide/sitemap.xml` 索引與分拆 urlset，由 robots.txt 公告；`_config.yml` 的 Darktide `sitemap: false` 僅避免混入一般文章 sitemap，不禁止正式頁收錄。
- 官方附件沿用 Media-Assets Issue #15；`docs/static-assets-manifest.yml` 記錄新增素材。不加入圖片二進位、集中字幕 JSON、測試或對話驗證程式。
- 逐頁來源指向固定 SHA 的 Source Code；未對應事件字幕連既有語系資源復原文件。完整 key/hash、條件及碰撞記錄留 Mods 共用來源 MD。

## 核對與交付

使用者明確要求沒有對話測試，故不採 TDD、不新增或恢復對話測試、verifier 或 CI 專用步驟。以來源文字回讀、正式 Jekyll 建置產物及桌面／390px 實際瀏覽核對：中英配對、標題與編號、角色列與固定側邊、首句錨點、分類零字幕、單一語言切換、分頁與來源連結，以及展開格式和長文字換行。

沿用既有文章與站點 CI，建置完整站點產物保存為 `darktide-production-<head-sha>`；交付至 Draft PR，不合併、不發布。推送前以核實的遠端 parent 建立隔離 index 精確提交，避免將本機 runtime instructions remediation 一併推送。

PR 建置成功不等於正式部署。取得擁有者合併授權後，合併至 `gh-pages`，由既有 GitHub 管理的 pages build and deployment 發布；不另建部署 workflow 或手動上傳 `_site`。發布後核對新部署 SHA、正式入口、中英事件及舊預覽移除狀態、canonical、robots、兩套 sitemap、CNAME 及輸出大小。回復時依站點發布文件建立 revert PR。

## 限制

候選池、分支、多根、循環與字幕缺漏依來源標示，編號表示閱讀順序；未對應 raw 字幕不虛構事件或角色。尚未逐場遊戲內播放，Source snapshot 未提供實際語音包。正式建置須核對總輸出大小，保留 GitHub Pages 1 GB 容量餘裕；本次 PR 的正式部署狀態須另依 Pages run 核實。

[正式遷移計畫](darktide-production-migration.md)｜[站點發布與回復](site-delivery.md)

[GitHub Pages 容量規則](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)｜[Mods 對話來源](https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/tree/codex/darktide-dialogue-archive/Game%20Info/%E5%B0%8D%E8%A9%B1%E6%96%87%E6%9C%AC)
