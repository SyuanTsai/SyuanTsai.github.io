# 舊站已遷技能內容交接

目前為 Draft PR 交付，尚未合併或正式發布。公開網址的 HTML 跳轉要待 Pages 發布後生效；新獨立站既有服務持續運作。

## 精確範圍

- [逐項舊新路由與固定輸入](routes.json)：646 個 `(archetype, skill_id)`，646 玩家頁及646機制頁，共1,292個唯一來源及目標。固定 IO 基準 `76472d21e8d542c2710840ce74215b1ce6a35006`；固定新站內容 commit `9e9e2ec26b71e296a8a4165fcf81fe2ad45fec63`。
- [線上 JSON 逐項驗證](live-target-verification.json)：1,292個目標均核對 live catalog 的內容 ID／類型、JSON HTTP 200、MIME、raw size及 artifact manifest SHA-256。不是只以 SPA HTML 回殼判斷內容存在。
- IO目前沒有武器／祝福獨立頁；新站70類武器及167項祝福不計舊站移除量。
- 保留35個技術補充頁、七職業目錄與根目錄；未證明逐頁等價新落點，故保留。補充正文只調整已遷連結及遷移提示。
- 中英文對話、字幕、性格、引用及用途 metadata、文章及共用CSS／素材保留。沒有刪除共享資產、私人來源或其他Repository內容。

## 網址、導航與收錄

舊網址提供 `noindex,follow`、新站 canonical、meta refresh、`location.replace` 及可手動點擊的精確目標。GitHub Pages回傳HTTP 200；這是HTML跳轉，不是HTTP 301。跳轉不複製技能正文，不移植舊段落hash。未知舊網址不改為任意首頁；不擴大新站SPA既有行為。

舊首頁與共用導覽標示已遷內容，舊站技術補充與中英文對話入口仍可使用。1,292個跳轉網址移出Darktide獨立sitemap；保留內容繼續收錄。`robots.txt`繼續公告既有兩套sitemap並允許取得跳轉頁，讓noindex及canonical能被讀取；不加入Disallow阻斷它們。

## 再生與驗證

一般Pages建置直接複製這些靜態HTML，沒有來源抓取或技能再生。歷史外部renderer若重寫舊正文，網站後處理必須套用遷移覆層；`apply_darktide_reader.py`已接上，導航跳過精確已遷網址，sitemap產生器也排除它們。不要單獨發布renderer輸出。

```text
python -m unittest discover -s tests -v
python scripts/validate_posts.py
python scripts/generate_discovery_pages.py --check
python scripts/migrate_darktide_skills.py --check
```

修復再生結果使用 `python scripts/migrate_darktide_skills.py`。`--site`可選完整Pages來源或建置根目錄；`--check`驗證應輸出的精確bytes及保留頁連結。對照表只接受已核對職業、來源路徑、內容ID與固定新站host，拒絕重複、越界及錯誤目標。

## 完整publication清單與容量

PR CI用同一 `actions/jekyll-build-pages@v1.0.13`，分別建置固定清理前commit與本次來源；`compare_publication.py`保存每個發布檔的path／raw bytes／SHA-256。`before-publication.csv.gz`、`after-publication.csv.gz`是完整CSV的壓縮保存，計量欄仍為原始檔案bytes；`changed-files.csv`列出所有正文替換及導航／sitemap差額，`retained-shared-assets.csv.gz`列出保留共享資產。Jekyll的feed／一般sitemap時間欄位會因建置時間而異，亦如實列帳。

正式量測結果與CI連結會在建置完成後補入。本次沒有移除網址檔案，而是移除其舊正文並保留輕量跳轉。新站raw產物、離站備份壓縮包、Cloudflare保留版本及Git歷史分列於[獨立儲存帳](separate-storage-accounts.json)；Cloudflare未公開實體保留版本儲存bytes，明列未量測，不宣稱回收。歷史全站520.23MB、ZIP與HTTP壓縮不作本期可移除量。

## 發布、回復及接續

取得擁有者當次明確批准後才合併；由既有Pages workflow發布。核對正式Pages run SHA與合併commit，再檢查代表舊玩家／機制網址確實跳至對應新站內容，補充頁、中英文對話、文章、CNAME、robots及兩套sitemap仍正確。新站不以IO提供runtime或素材。

回復從最新預設分支建立revert PR，revert本次merge或清理commit，執行既有建置／品質檢查後依批准發布。以固定基準清單核對恢復，不force-push、不手動覆蓋 `_site`，詳見[發布回復流程](../site-delivery.md)。保留本次完整manifest與來源commit，避免僅靠本機檔案接續。
