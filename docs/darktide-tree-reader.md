# Darktide 階層導覽版型

## 實作計畫與契約

網站基準為 `14afb3484026bc4562f335f33d05259c5d35603d`；技能匯出器基準為 Mods `326ce1308dc020c414b4805da04761f1d72312d9`。技能正文固定讀取知識 Commit `23c8cc124d2616d2956ae1734c67ce0c878c8fa4`，Source SHA 為 `7e662fcda16219d775b84af50322be2e9cd9d62e`。

1. 主控修改 `render_skill_pages.mjs` 的共用外框及炸藥儲備特殊產生路徑，加入可重建的階層目錄；`darktide-reader.css` 只管理共用左右版型與目錄，技能與對話正文樣式分別維護。
2. 技能左側依職業、分類與目前技能展開；目前分類僅列鄰近入口，其餘連回獨立職業目錄。右側保留標題、麵包屑、本頁段落、玩家／機制往返與完整正文。目錄使用原生連結及 details/summary，桌面寬 250px，手機預設收合為「瀏覽目錄」。
3. 職業分工為 Arbites、Ogryn/Psyker、Scum、Skitarii、Veteran/Zealot。各職業由單一代理執行限定 `--classes`，只能寫自己的 HTML 與 TSV；共用程式、CSS、根入口、提交及 PR 由主控處理。
4. 第一階段保留 646 組玩家／機制頁、35 補充、7 職業目錄與既有兩根入口；原 Markdown、URL、錨點、公式、表格、例外與來源限制不變。UNUSED 只列技術入口，不計入當前可選技能。
5. 等未對應字幕每頁最多 25 筆的依賴提交與驗收可核對後，接入本工作分支，再整合 Darktide 首頁及中英對話的共用目錄。語言切換、聊天泡泡、角色位置與原文空白保留；不恢復暫緩的全面 HTML 精簡，不加入未交付英文技能。

## 驗收與交付

此為靜態版型與既有匯出流程調整，依本次明確要求不新增技能／對話測試、verifier 或 CI。以修改前的單欄目錄作呈現基線，使用固定 Git 來源回讀、完整正文與映射比較、原生連結／錨點及實際瀏覽驗收；臨時 QA 不提交。全部技能頁檢查桌面與 390px，代表長內容再查 320px、表格捲動、焦點、目錄收合、無 JavaScript 與瀏覽器返回。

沿用 `docs/site-delivery.md` 的既有 unittest、文章、discovery、Jekyll、SEO、delivery 與品質驗證及 PR CI。本機 `bundle exec jekyll build --strict_front_matter` 回報沒有 Jekyll 執行檔，保留環境、不安裝套件；本機 HTTP 視覺結果與真正 Jekyll CI 分別記錄。以相同 CI 建置方法及精確 SHA 的未壓縮檔案數／bytes 比較容量分頁減量、技能目錄增量與對話目錄增量，不混用 Git 或 ZIP 容量。

所有交付為非預設分支及 Draft PR。精確提交排除 runtime artifacts、bootstrap remediation、私人路徑／信箱與本機 QA；提交前閱讀差異與祖先。回復使用交付 commits 的精確 revert，保留原正文及既有網站流程，不改寫公開歷史。正式合併與發布另需擁有者批准。

## 交付證據

第一階段已產生全部 1,335 個技能 HTML（包含技能根入口）。既有 Darktide 首頁留待容量交付後整合，因此原來包含兩根入口的 1,336 HTML 計數仍成立。

| 職業 | 玩家／機制配對 | 補充 | 職業入口 | HTML |
| --- | ---: | ---: | ---: | ---: |
| Arbites | 91 | 5 | 1 | 188 |
| Ogryn | 93 | 5 | 1 | 192 |
| Psyker | 81 | 5 | 1 | 168 |
| Scum | 115 | 5 | 1 | 236 |
| Skitarii | 101 | 5 | 1 | 208 |
| Veteran | 83 | 5 | 1 | 172 |
| Zealot | 82 | 5 | 1 | 170 |

618 筆 README 索引包括 587 筆付費主天賦、29 筆付費配方、2 筆零點記錄；另有 28 筆基礎效果，共 646 組。Scum 配方的 Celerity、Combat、Concentration、Durability 分支分別為 7、9、7、6 筆，另有零點裝備說明，沒有把全部記錄稱為付費天賦。

全 1,335 頁的完整 article 與公開基準建置產物一致（僅比較時處理 CRLF），包含全部 681 份機制／補充來源正文。66,938 個本機連結與錨點通過，TSV 內容沒有改變；618 個既有 GitHub 圖示網址全部回應 HTTP 200 `image/*`，1,236 個圖片標籤均有替代文字。原 Markdown 與圖示網址不變。

既有 unittest 46 項、文章來源、9 個 discovery 來源檢查通過。停用 JavaScript 的桌面／390px 全量瀏覽與代表 320px 長表格、長識別碼、焦點、details、玩家／機制往返及瀏覽器返回另記於審閱結果；IAB 已確認 320px 表格可用方向鍵橫捲。本機 HTTP 不是 Jekyll 建置證據。

容量比較基準為既有 `Test Jekyll site` run `37165370815`，輸入 `58cd2e185579d6022c46d03a3624eacc22193d07` 的 source tree 與公開基準 `14afb3484026bc4562f335f33d05259c5d35603d` 相同。其未壓縮產物為 53,767 檔、626,308,578 bytes，其中技能 HTML 1,335 檔、11,880,334 bytes，未對應字幕區 29,074 檔、103,715,263 bytes。後續新 CI 使用同一工作流程及 artifact 成員大小比較。

容量依賴、首頁與對話整合仍未交付；技能版型完成不代表整體完成。精確提交、Draft PR、CI 及新產物容量在各階段驗證後補入。
