# Darktide 全量字幕分頁交付

## 目標與已核實問題

延續已確認的深色聊天版型、固定角色側邊、參與角色列、編號與右上角單一語言切換，將 Mods Repository 的單一對話正文同步至 Draft PR #49。來源固定為 Source `7e662fcda16219d775b84af50322be2e9cd9d62e` 與 Build 25606770。

現有 `_layouts/darktide-dialogue.html` 每次 render 都掃描 `site.pages` 查分類和前後頁；全量數萬頁會反覆扫描全部頁面。改為預先產生各自完整 HTML，Jekyll 直接複製靜態檔；維持既有網址與玩家版面。

## 變更與相容性

- `preview/darktide/index.html`、英文入口、各類型 `index.html` 只列分類與標題，不收字幕；清單每頁最多 50 筆。
- `preview/darktide/{locale}/{event-type}/{event-id}/index.html` 每檔只包含自己的字幕或回應索引；大型群組另拆回應分頁。檔案保持兩格縮排、屬性分行及原始 bubble 文字空白。
- 原 12 組網址維持不變；既有入口 hash 轉址仍由 `assets/js/darktide-preview.js` 處理。所有分類、相鄰頁、角色首句與語言切換使用原生連結。
- 靜態頭保留 noindex/nofollow/noarchive。`_config.yml` 的 preview 範圍設 `sitemap: false`，避免預覽列入正式 sitemap。
- 官方附件沿用 Media-Assets Issue #15；`docs/static-assets-manifest.yml` 記錄新增素材。不加入圖片二進位、集中字幕 JSON、測試或對話驗證程式。
- 逐頁來源指向固定 SHA 的 Source Code；未對應事件字幕連既有語系資源復原文件。完整 key/hash、條件及碰撞記錄留 Mods 共用來源 MD。

## 核對與交付

使用者明確要求沒有對話測試，故不採 TDD、不新增或恢復對話測試、verifier 或 CI 專用步驟。以來源文字回讀、正式 Jekyll 建置產物及桌面／390px 實際瀏覽核對：中英配對、標題與編號、角色列與固定側邊、首句錨點、分類零字幕、單一語言切換、分頁與來源連結，以及展開格式和長文字換行。

沿用既有文章與站點 CI；交付至 Draft PR，不合併、不發布。推送前以遠端 PR HEAD 為 parent 的隔離 index 精確提交，避免將本機 runtime instructions remediation 一併推送。回復時可 revert 本次 task commit，保留原有文章與網站設定。

## 限制

候選池、分支、多根、循環與字幕缺漏依來源標示，編號表示閱讀順序；未對應 raw 字幕不虛構事件或角色。尚未逐場遊戲內播放。正式建置須核對總輸出大小，保留 GitHub Pages 1 GB 容量餘裕；目前僅完成預覽交付。

[GitHub Pages 容量規則](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)｜[Mods 對話來源](https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/tree/codex/darktide-dialogue-archive/Game%20Info/%E5%B0%8D%E8%A9%B1%E6%96%87%E6%9C%AC)
