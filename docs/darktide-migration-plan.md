# 已遷技能內容的舊站清理計畫

## 目標與界線

以目前遠端預設分支為基準，逐項核對七職業 TSV 與獨立站已發布資料的 `(archetype, skill_id)`、內容類型及實際路由。已遷的 646 組玩家／機制頁改為小型 HTML 跳轉；保留 35 個補充頁、七職業及根目錄。現行 IO 未發布武器／祝福獨立頁，不製造清理量。英文、對話、文章、原始來源及共用資產保留。

## 變更

- `docs/darktide-migration/routes.json` 保存逐網址、內容 ID、類型、新落點與固定公開輸入摘要。
- `scripts/migrate_darktide_skills.py` 只接受精確白名單，輸出 noindex/follow、canonical、新站可點連結、meta refresh 與 replace 導航。這是 HTTP 200 的 HTML 跳轉，不能稱 301；舊段落 hash 不移植到新內容。
- 35 個補充頁正文保留；目錄、首頁及導覽清楚標示技能／武器／祝福已遷，對話仍在 IO。已遷網址從獨立 Darktide sitemap 移除，robots 繼續允許取得跳轉頁。
- 既有 reader 及分類再生入口接上遷移處理，跳過跳轉頁，避免舊正文重新進入產物。CI 檢查精確跳轉 bytes 與白名單。

## 驗證與測試

小型遷移邏輯採 unittest Red → Green → Refactor：未知／重複目標或越界來源拒絕，正確目標輸出安全跳轉，重跑不改結果、補充文字保留、sitemap 不重收舊網址。沿用既有文章與網站驗證；不新增對話測試。

同一次 PR CI 以 `actions/jekyll-build-pages@v1.0.13` 建置固定基準及本次來源，保存完整逐檔 path／raw bytes／SHA-256 清單、替換正文、跳轉殘留、保留共用資產及淨減量。比較不使用 ZIP、HTTP 壓縮、Git 歷史或新站容量冒充 Pages 減量。實際新站 JSON 存在及 ID／路由要核對，不能只以 SPA HTML 200 當內容存在。

桌面／390px 瀏覽代表跳轉、補充頁、舊站首頁與中英文保留入口；另驗停用 JavaScript 的可點連結。維持既有文章、SEO、CNAME、Feed 與完整建置檢查。

## 交付、發布與回復

交付 Draft PR、雲端 CI 與可下載清單、固定 commit 的交接文件。Draft／CI 成功不等於發布；合併與 Pages 發布需擁有者當次明確批准。批准後核對合併 SHA 的 Pages run 與線上舊址／新址／保留內容。若需回復，從最新預設分支建立 revert PR，沿用 `docs/site-delivery.md`，不改寫公開歷史。

## 風險與保留

新站原已接受的 SPA、來源、圖片、術語限制維持有效。35 補充頁沒有逐項等價新落點，故保留。共享 CSS、圖示、來源 metadata 若無完整引用證據不移除。GitHub Pages HTML 跳轉需要取得 HTML；舊 hash 不保證保留段落位置。Git 歷史與外站備份大小沒有因本次清理減少。
