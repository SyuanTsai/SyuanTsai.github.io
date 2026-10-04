# Darktide 字幕正式交付

## 目標與已核實問題

延續已確認的深色聊天版型、固定角色側邊、參與角色列、編號與右上角單一語言切換，將 Mods Repository 的單一對話正文同步至網站。來源固定為 Source `7e662fcda16219d775b84af50322be2e9cd9d62e` 與 Build 25606770。PR #49 已合併，正式入口改為 `https://notes.tw-syuan.com/darktide/`，本次以新的 Draft PR 交付。

全量網站已採預先產生的完整 HTML，由 Jekyll 直接複製靜態檔；避免每個事件 render 時反覆掃描 `site.pages`，也避免 Liquid 解讀原始字幕。本次延續此結構與已確認的玩家版面。

## 變更與相容性

- `darktide/index.html`、英文入口、各類型 `index.html` 只列分類與標題，不收字幕；清單每頁最多 50 筆。
- 用途待確認字幕是上述分類清單的例外：中英各採每頁最多 25 筆的閱讀分頁，不再另產生每筆字幕的 HTML。每筆保留獨立區塊、來源編號與 hash 錨點，編號只表示來源索引順序，不構成連續對話。從原未對應索引確認用途的性格介紹及回應觸發條件引用另有分類與獨立頁。已確認官方事件的獨立網址與閱讀方式維持既有結構。
- `darktide/{locale}/{event-type}/{event-id}/index.html` 每檔只包含自己的字幕或回應索引；大型群組另拆回應分頁。檔案保持兩格縮排、屬性分行及原始 bubble 文字空白。
- 任務通訊直接分一般戰役任務、死神試煉（遊戲內）及莫羅、左拉、布拉姆斯、佐林四個具名角色頁。三人故事回聲為額外選集，連到同一正文，不增加事件數。
- 對話樣式為 `assets/css/darktide.css`，階層外框共用 `assets/css/darktide-reader.css`。所有分類、相鄰頁、角色首句與語言切換使用原生連結，不依賴 JavaScript。
- 依擁有者最新指示，移除舊 `preview/darktide/` 與入口 hash 相容邏輯，不保留轉址或字幕副本。舊預覽網址不再支援。
- 正式頭使用 index/follow 與 `/darktide/` canonical。Darktide 使用 `darktide/sitemap.xml` 索引與分拆 urlset，由 robots.txt 公告；`_config.yml` 的 Darktide `sitemap: false` 僅避免混入一般文章 sitemap，不禁止正式頁收錄。
- 官方附件沿用 Media-Assets Issue #15；`docs/static-assets-manifest.yml` 記錄新增素材。不加入圖片二進位、集中字幕 JSON、測試或對話驗證程式。
- 逐頁來源指向固定 SHA 的 Source Code；未對應事件字幕連既有語系資源復原文件。完整 key/hash、條件及碰撞記錄留 Mods 共用來源 MD。

## 未對應字幕的產生方式

`scripts/generate_darktide_unlinked_pages.py` 只讀 Mods 的權威對話來源，依 `source-catalog/unlinked-subtitles/*.md` 的編號配對 `zh-tw/events/` 與 `en/events/` 中的原始 HTML。缺漏說明及角色標示保留；區塊內的 ID 與錨點加上字幕 hash 前綴，避免同頁重複 ID。字幕依同批原始語系資源 `Game Info/releases/1.13.X/source/SteamBuild_25606770_1.13.1/jsonl/{locale}/subtitles.jsonl` 的 hash 取用原文，保留所有空白與換行，不使用 `strip` 或文字正規化。網站輸出由此產生，不另維護字幕副本，也不新增集中 JSON。

在完成一般來源同步後執行：

```powershell
python scripts/generate_darktide_unlinked_pages.py --dialogue-source "C:/Git/Personal/Darktide-Mods/Game Info/對話文本"
```

語系資源預設從同一個 `Game Info` 目錄查找；唯讀使用來源歸檔快照時，可用 `--locale-resources` 指定既有原始 `jsonl` 目錄。`.gitattributes` 對分頁與這兩種新增用途頁停用 Git 的文字換行轉換，避免 checkout 時改動泡泡內的原始換行。

此命令只更新網站的字幕用途分類、首頁相關分類卡與 Darktide sitemap，來源保持唯讀；其他官方事件、技能內容、技能產生流程與提示詞不在此產生器範圍。用途待確認字幕的中文入口為 `/darktide/unlinked-subtitles/`，英文入口為 `/darktide/en/unlinked-subtitles/`；後續頁使用 `page-002/` 等路徑，同頁中英直接切換。每筆可由 `#unlinked_subtitle_<hash>` 直接定位。原本每筆未對應字幕的獨立網址由分頁與錨點或已確認用途的獨立頁取代。

原始正文歸檔 commit 為 `dc40cbfa80193fdfbdc759a4a9cd3378905b83ff`，角色來源沿用 `23c8cc124d2616d2956ae1734c67ce0c878c8fa4`；字幕仍從 Build 25606770 原始語系資源取回。完整原未對應索引共有 14,251 筆。依固定 Source `7e662fcda16219d775b84af50322be2e9cd9d62e` 的行為確認 38 筆角色建立性格介紹與 22 筆回應觸發條件引用後，其餘 14,191 筆分成每語系 568 頁，最後一頁 16 筆。原本缺中文的 30 筆在繁中頁顯示同一 hash 的官方英文原文，標註「尚無官方繁中翻譯，暫以英文原文顯示。」並以 `lang="en"` 標示氣泡語系；英文文字保留原始空白，不補造中文翻譯，Mods 原始缺漏紀錄維持不變。分頁、網址、hash 錨點與原始排序保持不變。分頁使用原生連結，不需要 JavaScript；每頁保持多行 HTML，沿用共用深色 CSS。

用途 metadata 唯一維護於 Mods Repository 的 `Game Info/對話文本/source-catalog/subtitle-usages/`，只有 TSV 參照資料，不含字幕正文。產生器預設從同一來源讀取；使用原始正文唯讀快照時，可用 `--classification-source` 指向同一權威來源的用途 TSV 目錄。網站不保存人工同步的用途清單或全字幕 JSON。

本次用途來源固定於 Mods commit [`619e0e36bdca5da302d658e6c60f1bf67150a34f`](https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/commit/619e0e36bdca5da302d658e6c60f1bf67150a34f)。重建需使用此提交的兩份用途 TSV 或其後續已確認版本；缺少用途 metadata 時產生器停止，避免把已分類條目重新混入待確認頁。

- `/darktide/character-personalities/` 與英文配對分類有 38 個獨立性格介紹頁，ID 由官方 character voice 建立。顯示官方職業／性格名稱與職業圖示；圖示不是固定人物肖像，畫面介紹未宣稱等同試聽音訊。
- `/darktide/response-trigger-references/` 與英文配對分類有 22 個獨立引用頁，保留 26 處官方回應規則的來源及既有候選閱讀入口。只證明規則會檢查這句話；原始播放事件與發話者未確認，不把回應者標作原說話者，也不拼接候選成線性劇情。
- 其餘「用途待確認」只表示固定版本中未找到可證引用，不能宣稱未使用或事件不存在。來源原編號保留，抽出已分類條目後頁內編號可能不連續。

## 共用階層閱讀外框

一般對話來源同步後，執行 `python scripts/apply_darktide_reader.py`；用途字幕產生器最後也呼叫相同外框。技能仍由 Mods 的技能匯出器讀固定 Markdown，不使用對話產生器。這兩個流程只共用 CSS 與導覽契約。

桌面目錄寬 250px，依事件類型、分類分頁與目前內容導覽，只列目前分支及最多五個鄰近入口；完整清單仍是獨立目錄。手機「瀏覽目錄」預設收合，右側保留原本 LINE 氣泡、角色列、語言按鈕、來源及原生前後頁。首頁以同一目錄進入內容，原完整分類清單收在可展開區。

外框讀取既有 canonical、title 與目錄連結作導航，不解析後重寫字幕。標記內只保存外框；重新套用先移除自身標記，原閱讀正文不變。網站整合依賴 [容量 PR #54](https://github.com/SyuanTsai/SyuanTsai.github.io/pull/54) 的 `f4db2525353dbb176f8855cc65842e49aa610a08` 與 [來源 PR #194](https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/pull/194) 的 `619e0e36bdca5da302d658e6c60f1bf67150a34f`，保留其25筆分頁、分類與網址，沒有合併 GitHub PR 或正式發布。

## 核對與交付

使用者明確要求沒有對話測試，故不採 TDD、不新增或恢復對話測試、verifier 或 CI 專用步驟。以來源文字回讀、正式 Jekyll 建置產物及桌面／390px 實際瀏覽核對：中英配對、標題與編號、角色列與固定側邊、首句錨點、分類零字幕、單一語言切換、分頁與來源連結，以及展開格式和長文字換行。

沿用既有文章與站點 CI，建置完整站點產物保存為 `darktide-production-<head-sha>`；交付至 Draft PR，不合併、不發布。推送前以核實的遠端 parent 建立隔離 index 精確提交，避免將本機 runtime instructions remediation 一併推送。

PR 建置成功不等於正式部署。取得擁有者合併授權後，合併至 `gh-pages`，由既有 GitHub 管理的 pages build and deployment 發布；不另建部署 workflow 或手動上傳 `_site`。發布後核對新部署 SHA、正式入口、中英事件及舊預覽移除狀態、canonical、robots、兩套 sitemap、CNAME 及輸出大小。回復時依站點發布文件建立 revert PR。

## 限制

候選池、分支、多根、循環與字幕缺漏依來源標示，編號表示閱讀順序；未對應 raw 字幕不虛構事件或角色。尚未逐場遊戲內播放，Source snapshot 未提供實際語音包。正式建置須核對總輸出大小，保留 GitHub Pages 1 GB 容量餘裕；本次 PR 的正式部署狀態須另依 Pages run 核實。

[正式遷移計畫](darktide-production-migration.md)｜[站點發布與回復](site-delivery.md)

[GitHub Pages 容量規則](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)｜[Mods 對話來源](https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/tree/codex/darktide-dialogue-archive/Game%20Info/%E5%B0%8D%E8%A9%B1%E6%96%87%E6%9C%AC)
