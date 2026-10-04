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

第一階段網站提交 `0f15bdd24cd2a47d376747013277ec752fc2dd07` 為 [Draft PR #53](https://github.com/SyuanTsai/SyuanTsai.github.io/pull/53)，匯出器提交 `d4fe489a4ba03ee8cf7604ce07e2f614d52ccd5d` 為 [Mods Draft PR #193](https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/pull/193)。公開祖先鏈排除本機 instructions remediation；原工作樹與本機 index 保留。

[Test Jekyll site run 37180456216](https://github.com/SyuanTsai/SyuanTsai.github.io/actions/runs/37180456216) 全部成功，包括 SEO、discovery、delivery、deterministic quality、Lighthouse accessibility 及既有視覺／搜尋檢查。實際 artifact `11294068589` 對應網站 head `0f15bdd24cd2a47d376747013277ec752fc2dd07`；兩份 CI 產物的全部 1,335 個技能 article byte 完全相同，不只本機來源比較。其餘文章輸出只改變既有建置時間戳，內容未修改。

| 相同 CI 方法的未壓縮產物 | 檔案數 | bytes |
| --- | ---: | ---: |
| 公開基準全站 | 53,767 | 626,308,578 |
| 第一階段全站 | 53,768 | 633,936,541 |
| 公開基準技能 HTML | 1,335 | 11,880,334 |
| 第一階段技能 HTML | 1,335 | 19,505,467 |

技能 HTML 的目錄增量為 7,625,133 bytes；包含 CSS 的全站增量為 7,627,963 bytes。未對應字幕區仍是 29,074 檔、103,715,263 bytes，尚未接入容量減量。最後全量重生後再執行限定 Veteran，172 個 HTML 的 SHA-256 全部相同，炸藥儲備特殊範本沒有累積外框、目錄或空白。

以上是第一階段交付快照；全站整合的依賴與驗收另記如下。

## 全站整合

接入容量網站 head `f4db2525353dbb176f8855cc65842e49aa610a08`（[容量 PR #54](https://github.com/SyuanTsai/SyuanTsai.github.io/pull/54)）與其來源 `619e0e36bdca5da302d658e6c60f1bf67150a34f`（[Mods 來源 PR #194](https://github.com/SyuanTsai/Warhammer-40-000-DARKTIDE-Mods/pull/194)）。整合採獨立 Draft PR，以公開 `gh-pages` 為 base；包含第一階段 `0f15bdd24cd2a47d376747013277ec752fc2dd07`、容量提交與明列的正常合併提交，再追加共用導覽差異。容量 PR #54 與 Mods #193／#194 已由其他交付流程合併；本任務正常接入最新網站公開基準 `ca9023512191d1de33e9cfd5f67d78d32f8f8622`，未執行 GitHub 合併。來源匯出器的最後變更另從 Mods `6660e776647c4a1d310243bfb0dc1875d4af1bbb` 開 Draft PR，不向已合併分支追加。

`scripts/apply_darktide_reader.py` 從既有首頁分類、技能根職業連結、canonical、title 與分類分頁讀取導航 metadata。對話外框與技能外框共用 `darktide-reader.css`，正文流程保持分離；用途字幕產生器在更新 sitemap 後呼叫同一外框，避免重建時遺失導覽。沒有集中載入全部技能或字幕正文。

首頁、24,562 個對話／目錄頁與中英配對入口使用相同左右閱讀版型，總計24,564個非技能頁。桌面目錄250px，手機原生收合；目前事件類型、父目錄與最多五個鄰近入口可見，其他類型可展開。技能入口也可展開七職業。原完整首頁分類清單保留在可展開區；個別事件的聊天正文、角色列、固定左右位置、原始順序、語言切換與前後頁不變。

容量交付保留14,251個hash：38個性格介绍、22個回應規則引用與14,191個用途待確認條目。用途待確認每語系568頁、最多25筆、末頁16筆；缺中文的30筆仍維持缺漏說明。性格介紹使用官方職業圖示，不宣稱人物肖像或音訊已驗證；回應引用不推定原始發話者或串成播放劇情。sitemap沿用交付的25,899個網址。

[容量 Test Jekyll site run 37181281886](https://github.com/SyuanTsai/SyuanTsai.github.io/actions/runs/37181281886)全部成功，artifact `11295247047`對應容量精確head。使用與第一階段相同工作流程、未壓縮artifact成員計量，容量變更本身為25,952檔、555,099,057 bytes，比公開基準減少27,815檔、71,209,521 bytes。用途待確認1,136檔、35,358,479 bytes，新用途頁124檔、548,523 bytes；技能正文與容量前相同。完整導覽的增量在整合CI後另記，沒有恢復暫緩的全面HTML精簡。

本機46個既有單元檢查、文章來源與9個discovery來源通過。加入對話分類入口後，全部1,335個技能article、681份完整機制／補充內容與圖示列表保持原樣，85,628個技能本機連結與錨點通過。完整對話原文、整合瀏覽與既有CI結果在實際驗證後補入；來源HTTP預覽不作Jekyll證據。
