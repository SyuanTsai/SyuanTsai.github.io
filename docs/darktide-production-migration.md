# Darktide 正式路徑遷移

## 目標與範圍

正式入口改為 `https://notes.tw-syuan.com/darktide/`。將 PR #49 已合併的完整靜態字幕網站，連同後續已確認的任務通訊六個分類與四位死神試煉角色頁，移至正式路徑。字幕、角色映射、深色版型與事件 ID 保持既有來源。

本次交付為新的 Draft PR；合併及正式部署另依擁有者授權。文章、技能內容、素材附件與遊戲原始碼不在修改範圍。

## 已核實基線與修改

- `gh-pages` 的 PR #49 已合併；現有正文仍在 `preview/darktide/`，canonical 及所有內部連結沿用預覽路徑，robots 為 noindex。
- 完整 HTML 不含 front matter，避免 Liquid 解讀原始字幕；正式正文仍採此方式。
- 正文移至 `darktide/`，只修改 URL 屬性及 robots。共用 CSS 改用 `darktide.css`；移除舊入口 hash 腳本。字幕文字節點保持逐字一致。
- 依擁有者最新指示，直接移除 `preview/darktide/` 及舊 hash 相容邏輯，不保留轉址或第二份字幕。舊網址不再支援，新的正式入口為 `/darktide/`。
- 全站主要導覽與文章搜尋頁提供正式 Darktide 入口；共用導覽允許換行，避免新增入口後在手機寬度溢出。文章搜尋 JSON 的既有範圍不變。
- 正式頁使用 index/follow 與自己的正式 canonical。超過五萬筆的網址使用 `darktide/sitemap.xml` 索引及分拆 urlset；`robots.txt` 同時公告文章及 Darktide sitemap。舊預覽網址不列入 sitemap。
- `_config.yml` 將 Darktide 從一般 Jekyll sitemap 排除，僅由上述獨立 sitemap 收錄，避免單份 sitemap 超過容量。這不禁止正式頁收錄。
- 既有 PR workflow 僅調整建置產物保存路徑；不新增部署 workflow、對話測試、verifier 或對話專用 CI 驗證步驟。

## 核對方式

依使用者明確要求，不採對話 TDD、不建立測試。核對原文、URL 屬性及 sitemap 實際內容，並以桌面及 390px 瀏覽正式入口、任務通訊分類、角色頁、字幕頁、語言切換；確認舊預覽已移除。沿用既有站點 CI 確認 Jekyll 建置、文章、搜尋、站內連結、SEO 與品質基線；以該次確切 head 的建置產物作交付證據。

## 發布與回復

1. 工作分支提交精確變更，排除本機 runtime instructions remediation，開新的 Draft PR。
2. PR 建置成功不等於正式部署。取得合併授權後，合併至 `gh-pages`，由既有 GitHub 管理的 pages build and deployment 發布。
3. 發布後核對 Pages run 的 SHA、正式入口、中英深層頁、舊預覽移除狀態、canonical、robots、兩套 sitemap、CNAME 及實際輸出大小。
4. 如需回復，依 `docs/site-delivery.md` 建立 revert PR，等待既有建置後再合併；不 force-push 或手動上傳 `_site`。

## 容量與限制

舊路徑直接移除，避免全量字幕重複。交付需記錄實際建置大小與 sitemap 分拆筆數。大量路徑遷移會產生大型 diff，應配合逐頁原文回讀及共用導覽／樣式的差異審閱。

[Sitemap 格式與分拆規範](https://www.sitemaps.org/protocol.html)｜[Jekyll sitemap 靜態檔案處理](https://github.com/jekyll/jekyll-sitemap/blob/v1.4.0/lib/jekyll/jekyll-sitemap.rb)｜[公開內容與 PR 規範](public-content-and-pr-policy.md)
