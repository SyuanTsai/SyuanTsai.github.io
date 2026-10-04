# Darktide 七職業技能展示

保留 Mods Repository 的原技能 Markdown，接續炸藥儲備範本，展示 Release 1.13.1／1.13.X 的全部七職業既有技能、升級、巢都渣滓配方、基礎效果及技術補充。繁中正文與英文技能名稱沿用原文件，沒有另作完整英文翻譯。

## 固定來源與維護

- 知識 Commit：`23c8cc124d2616d2956ae1734c67ce0c878c8fa4`，目錄 `Game Info/releases/1.13.X/skills/talents/`。
- Source SHA：`7e662fcda16219d775b84af50322be2e9cd9d62e`。
- 網站分支：`codex/darktide-skill-pages`；範本起始基準 `363bc59dcd5112311817041677242dc07884a8b3`，交付已整合最新 `gh-pages` Commit `bf53d47c36831a8e330b6deced2cb79fead07e91`。
- [展示流程](https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/blob/52266f37c9fea095a6d2dc095f0eacd089f110a3/AI%20Prompt/Skill-Pages-Workflow.md)與[匯出工具](https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/blob/52266f37c9fea095a6d2dc095f0eacd089f110a3/scripts/game-info/render_skill_pages.mjs)固定到實際提交；機制內容只維護原 Git Markdown。

每技能有獨立玩家頁與 `mechanics/` 詳細頁。玩家頁由 README 的原段落或 BASE_EFFECTS 的既有段落產生，保留效果、公式、算例、單位與必要例外。炸藥儲備沿用既有排版、數值及兩個算例，只增加完整機制入口。機制頁完整轉換逐技能 Markdown，保留確認／推導狀態、作用對象、計時、結算、上限、例外、顯示差異、待確認事項與固定原始碼引用，提供返回玩家頁、固定 Git 文件及 Source Code 連結。

原技能 Markdown 不刪除、不搬移，也不以 HTML 取代。已網頁化的相對文件與技能錨點轉到對應網頁；其他引用連到確實存在的固定知識 Commit。完整版本說明仍連原 Git 文件。

## 全量清單與計數

| 職業 | README／SOURCE_INDEX 入口 | 額外基礎／條件效果 | 玩家／機制頁組數 | 技術補充頁 |
| --- | ---: | ---: | ---: | ---: |
| Arbites／法務官 | 86 | 5 | 91 | 5 |
| Ogryn／歐格林 | 86 | 7 | 93 | 5 |
| Psyker／靈能者 | 81 | 0 | 81 | 5 |
| Scum／巢都渣滓 | 109 | 6 | 115 | 5 |
| Skitarii／護教軍 | 97 | 4 | 101 | 5 |
| Veteran／老兵 | 77 | 6 | 83 | 5 |
| Zealot／狂信徒 | 82 | 0 | 82 | 5 |
| 合計 | 618 | 28 | 646 | 35 |

618 筆索引入口包括 587 個付費主天賦節點、29 個付費配方、老兵零點起始能力及巢都渣滓零點裝備說明。巢都渣滓主樹為 79 筆，配方分類為 30 筆；四個付費配方分支是 Celerity 7、Combat 9、Concentration 7、Durability 6。零點裝備不是另一個可升級配方。

基礎效果已由索引技能承載的職業不重複加算，例如靈能者與狂信徒；完整 BASE_EFFECTS 仍有入口。`UNUSED_DEFINITIONS` 只列技術補充，不能當作當前可選技能或計入完成數。總計 646 玩家頁、646 機制頁、35 補充頁、7 職業目錄及2個根入口，為 1,336 HTML。

每職業 TSV 位於 `docs/darktide-skills/`，逐筆記錄類型、分類、識別碼、中英名稱、玩家來源及錨點、機制來源 SHA-256、玩家 URL 與機制 URL。每職業另外五個補充文件分別對應 `source-index/`、`base-effects/`、`unused-definitions/`、`localization-comparison/`、`damage-percentage-review/`；README 轉成分類目錄。688 個原 Markdown 因而對應 646 個機制正文、35 個完整補充正文及7個 README 目錄／玩家段落來源。映射供維護與審閱，沒有集中載入所有技能的巨大 HTML 或 JSON。

## 網址與呈現

階層版型由同一匯出工具再產生；最新契約與分階段交付見 [階層導覽版型](darktide-tree-reader.md)。桌面左側250px展開技能與天賦 → 目前職業 → 分類 → 技能，其他職業可另展開；較大分類連回獨立職業目錄，每頁最多列七個鄰近技能。右側保留完整本頁內容與可收合段落目錄、麵包屑、玩家／機制往返及固定來源。手機以預設收合的「瀏覽目錄」進入導覽，原生details/summary不依賴JavaScript。

共用左右外框與目錄樣式位於 `assets/css/darktide-reader.css`，技能正文仍在 `darktide-skills.css`。對話來源、產生流程及聊天樣式維持獨立；首頁與對話的實際套版須先核對25筆分頁的容量交付。尚未完成的英文技能正文不在此次版型中自行翻譯或發布。

- `/darktide/`：Darktide 正式入口。
- `/darktide/skills/`：七職業入口。
- `/darktide/skills/<class>/`：依閃擊、光環、能力、鑰石、技能分類；配方及基礎效果另列。
- `/darktide/skills/<class>/<skill>/`：玩家頁。
- `/darktide/skills/<class>/<skill>/mechanics/`：完整原始碼依據。

英文 slug 重名時以技能 ID 消歧，保留 `/darktide/skills/veteran/demolition-stockpile/`。尚未發布的舊技能預覽網址直接捨棄，沒有轉址或別名；技能正文皆在 `darktide/skills/`，canonical 使用正式網域對應路徑。已發布的正式 Darktide 對話入口保留原分類與網址，增加原生技能連結；不復原已移除的對話預覽。

沿用 `assets/css/darktide-skills.css` 的近黑背景、深灰面板與低亮度青藍色。HTML／CSS 展開、兩格縮排。長識別碼與連結可換行；寬表格在獨立可鍵盤聚焦的容器內捲動，390px 整頁沒有橫向溢出。圖示沿用 618 個既有 GitHub Issue 附件，metadata 由既有技能稽核收據補入 `docs/static-assets-manifest.yml`，沒有提交圖片二進位。缺圖的基礎記錄照原資料呈現，不猜測圖示。

## 再產生與驗收

在 Mods 工作樹執行；先保留 Pages 的炸藥儲備範本與 CSS，使用既有 Node.js 與已安裝 `marked` 17.0.5 ESM：

```powershell
node scripts/game-info/render_skill_pages.mjs `
  --mods-root . `
  --pages-root "<Pages 工作樹>" `
  --knowledge-sha 23c8cc124d2616d2956ae1734c67ce0c878c8fa4 `
  --source-sha 7e662fcda16219d775b84af50322be2e9cd9d62e `
  --markdown-module "<已安裝 marked/lib/marked.esm.js>"
```

`--classes` 可限縮職業；省略時產生全部七職業及跨職業入口。工具不清除其他檔案，版本或 slug 更新需先對照既有 TSV。靜態 HTML 無 JavaScript 或 Front Matter；HTTP 預覽可以檢查呈現，Jekyll 建置與品質檢查仍依 [site-delivery.md](site-delivery.md)。未新增技能專用測試、verifier 或 CI 步驟。

已驗收來源：681 個機制／補充正文與獨立 Markdown 呈現的完整文字一致，原技能目錄 `git diff` 無差異；1,336 HTML 的本機連結及錨點無錯誤；3,986 組唯一固定 Source 行號範圍涉及258個檔案，全部存在。全部頁面以 JavaScript 停用在1280px及390px瀏覽，無整頁橫向溢出；618個圖示附件全部可載入。代表頁另檢查公式、表格、長文字、跳至正文、焦點、段落錨點、玩家／機制往返及瀏覽器上一頁。

既有46項 unittest、文章驗證與9個 discovery pages檢查通過。本機 Ruby 3.4.10 與 Gemfile 3.3.4 不同，未改動環境；完整 Jekyll／SEO／discovery／preview／delivery／quality 驗收由原 PR CI 核實，結果記於 Draft PR。工作分支與 Draft PR 不代表合併或正式部署。

## 證據限制與回復

沿用原文件中的翻譯勘誤、程式推導及待確認事項；本次核對的 55 項名稱已按同版英文／zh-tw 名稱鍵與 hash 取得；其餘名稱沿用既有詞表。Low Profile 的 zh-tw 項目仍標記未翻譯，保留英文；未做遊戲內實測。計時例為原文件的近似推導，圖示只供辨識。原文件的機制與特殊例外以各頁完整正文為準。

回復使用本次網站 Commit 的精確 revert；若日後已部署，依站點回復流程另開 PR。原 Git 技能內容、對話頁、主題及部署設定不因本次轉移而刪除或重建；不 force-push 公開歷史。

## 2026-10-04 名稱修正

名稱修正來源為 [Mods PR #196](https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/pull/196) 的固定知識 Commit `d1c961ab802ca25e5091d79e28304d826e1ffca5`；Release 1.13.1 Source SHA 與 Steam Build 25606770 保持一致。本次補齊 55 項文本名稱，實際需要更名的 33 項包含嵌入基礎文件的次元危險及未翻譯的 Low Profile。同步玩家頁、機制頁、目錄、相關補充文件與 TSV；相同名稱的小型節點一起修正。

名稱變更保留全部 646 組既有玩家／機制網址，舊標題錨點保留為別名。修正過的 Markdown 連結指向新知識 Commit，未修改的文件繼續使用原固定來源；不改動技能效果、公式、點數、分類或網站樣式。後續完整再產生時，需以 TSV 的技能 ID 保留已發布的 URL，不能直接按新英文名稱重建 slug。

逐頁來源與驗證摘要見 [名稱修正紀錄](darktide-skills/2026-10-04-name-corrections.json)。兩個 PR 分別審閱；本 PR 合併至 `gh-pages` 後才會觸發既有正式發布流程。
