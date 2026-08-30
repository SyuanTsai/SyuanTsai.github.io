# 靜態資源儲存與發布策略

本文件記錄本站圖片、PDF、附件與其他靜態資源的儲存、發布、備份及遷移策略。價格與服務限制的比較基準日為 2026-08-30；正式導入前必須再核對供應商官方文件。

## 現況

- Repository 目前只有一個文章 SVG，檔案約 2.1 KB。
- `assets/` 目錄連同目錄結構約 24 KB。
- 尚未使用 PDF、ZIP 或其他文章附件。
- 尚未依賴免費公共圖床或供應商專屬資源網址。
- 文章範本目前使用 `/assets/images/posts/<slug>/...` 站內相對網址。

現有規模不需要為容量或流量建立物件儲存服務。本站選擇以公開 GitHub Issue 附件作為文章內文圖片的主要發布方式，既有 Repository 檔案作為來源與備份；正式文章目前使用的 `/assets/` 網址維持不變，先以未列出範本完成 MVP。

## 方案比較

| 方案 | 目前成本與額度 | 優點 | 主要限制 | 維護負擔 | 本階段定位 |
| --- | --- | --- | --- | --- | --- |
| GitHub Issue 附件 | 使用獨立 GitHub machine user；圖片與 GIF 單檔上限 10 MB，其他檔案上限 25 MB | 貼上或拖曳後立即取得匿名化網址；不增加 Git 歷史；公開 Repository 的附件不需登入即可讀取 | 附件不是 Git tree 內的檔案；網址、Cache、CORS、目錄與檔名均由 GitHub 控制；沒有自訂網域或服務 SLA；遷移時必須更新文章網址 | 低 | **文章內文圖片主方案** |
| GitHub Repository／Pages | Pages 發布內容上限 1 GB、每月 100 GB 軟性流量上限 | 現有流程即可使用；Git commit 本身可追蹤版本；不增加帳號與部署服務 | 大型二進位檔會擴大 Git 歷史；Cache 與資源網域控制有限；若要獨立使用 `assets.tw-syuan.com`，需建立另一個 Pages 站點 | 低 | 零變更基準方案 |
| Cloudflare R2 Standard | 每月 10 GB 儲存、100 萬次 Class A、1,000 萬次 Class B 免費；對外傳輸免費 | 自訂網域可使用 Cloudflare Cache；S3 相容 API 方便上傳與遷移；目前規模預期落在免費額度 | `tw-syuan.com` 目前不由 Cloudflare 管理；Free／Pro 不支援保留既有權威 DNS 的 Partial CNAME setup。另不支援 S3 Bucket Versioning、原生 Bucket Replication 與 Object Lock | 低至中 | 若願意遷移權威 DNS，再列入低成本候選 |
| Amazon S3＋CloudFront | CloudFront Free 固定方案包含 5 GB S3 儲存抵用、每月 100 GB 傳輸與 100 萬次請求 | S3 Versioning、生命週期與完整 AWS 生態成熟；CloudFront 可搭配私有 S3 Origin Access Control；可沿用現有權威 DNS | Bucket、CloudFront、OAC、憑證與 DNS 設定較多 | 中至高 | 保留現有 DNS 時的成熟候選 |
| DigitalOcean Spaces＋CDN | 每月 US$5，含 250 GiB 儲存與 1 TiB 對外傳輸 | S3 相容、CDN 內建、費用結構簡單；外部 DNS 可使用自有憑證綁定自訂子網域 | 目前用量遠低於固定方案額度；外部 DNS 情境需自行建立、上傳及維護憑證 | 中 | 保留現有 DNS 時的簡化付費候選 |
| Azure Blob Storage＋Front Door | Blob、操作與流量另計；Front Door Standard 固定費用為每月 US$35，另計傳輸與請求 | Blob Versioning、冗餘與 Azure 整合完整；Front Door 支援自訂網域與 TLS | 固定費用遠高於目前需求，設定與維護亦較複雜 | 高 | Azure 生態需求出現時再評估 |

### 選定方案

採用「公開 GitHub Issue 附件負責文章內文圖片傳遞，Repository 保存可重新發布的來源與 manifest」：

1. 主帳號 `SyuanTsai` 建立並持有公開 `SyuanTsai/notes-assets` Repository，開啟 Issues。
2. 另建專用 GitHub machine user，只在雲端瀏覽器登入；不加入 `SyuanTsai.github.io`，也不成為 `notes-assets` collaborator。
3. 專用帳號以一般公開使用者身分建立靜態資源登錄 Issue；每篇文章以一則 comment 記錄文章 slug、語意化檔名、SHA-256 與附件。
4. 上傳後只使用 GitHub 產生的完整匿名化網址，不自行拼接網址。
5. `docs/static-assets-manifest.yml` 記錄來源檔案與 GitHub 附件網址的對應。
6. 圖片內容更新時重新上傳並取得新網址，不覆寫或重複利用舊網址。

這個方案接受 GitHub 供應商網址與無法自訂 Cache 的限制，以換取目前規模下最低的成本與操作負擔。若未來需要自訂網域、可控 Cache、大量檔案、自動部署或獨立 SLA，再重新評估 R2、S3＋CloudFront、DigitalOcean Spaces 或 Azure。

### 權限邊界

| 身分／介面 | 可操作範圍 | 明確禁止 |
| --- | --- | --- |
| `@GitHub` 連接器（主帳號） | `SyuanTsai.github.io` 的程式碼、PR 與 Jira 對應工作 | 不保存或使用專用帳號密碼 |
| 雲端瀏覽器（專用帳號） | `notes-assets` 的公開 Issue、comment 與附件 | 不授予 `SyuanTsai.github.io` 存取權，不授予任何 Repository collaborator 權限 |
| `SyuanTsai` 主帳號 | 持有及管理兩個 Repository，必要時進行復原與撤銷 | 不在雲端瀏覽器保存主帳號 session |

專用帳號必須使用獨立信箱、唯一密碼與 2FA；密碼、TOTP secret 與恢復碼只由擁有者保管，不寫入對話、Repository、Jira 或 manifest。

## 公開網址與檔名

正式內文使用 GitHub 上傳後產生的匿名化網址，常見格式如下：

```text
https://github.com/user-attachments/assets/<uuid>
```

GitHub 附件網址不保留可讀檔名，也沒有可由本站管理的目錄結構。語意化名稱與來源仍使用以下結構：

```text
assets/images/posts/<article-slug>/<semantic-name>-<content-hash>.<ext>
```

例如：

```text
assets/images/posts/debugging-http-timeouts/request-flow-a1b2c3d4.svg
```

規則：

- 路徑與檔名只使用小寫英文字母、數字、連字號、斜線及副檔名的句點。
- `article-slug` 與文章檔名使用相同 slug。
- 檔名描述內容，不使用 `image1`、`final`、`new` 等無法辨識用途的名稱。
- `content-hash` 使用檔案 SHA-256 的前 8 碼。
- 每個 GitHub 附件網址都必須記錄於 manifest，不可只存在文章內文。
- 已發布內容不得假設附件可以覆寫；內容變更時產生新的 hash 與 GitHub 網址。
- 不刪除登錄 Issue，也不把所屬 Repository 改成 Private；這兩種變更都必須先完成附件遷移。

## 檔案格式與壓縮

| 內容 | 優先格式 | 規則 |
| --- | --- | --- |
| 架構圖、流程圖、線條圖 | SVG | 移除腳本、外部資源與不必要 metadata；必須可在深色與淺色背景閱讀 |
| 畫面截圖 | WebP | 保留足以閱讀文字的解析度；PNG 只在 WebP 無法保留必要細節時使用 |
| 照片或大面積漸層 | AVIF＋WebP fallback | 使用 `<picture>` 與 `srcset`；不得只提供 AVIF |
| 透明或需要完全無損的點陣圖 | PNG | 上傳前執行 lossless 壓縮 |
| 文件 | PDF | 移除不需要的個人資料與 metadata；確認字型可正常顯示 |
| 其他附件 | 依實際格式 | 不提供可執行檔；壓縮檔必須記錄內容與 SHA-256 |

圖片必須提供 `alt`、原始寬高，且非首屏關鍵圖片使用 lazy loading。響應式圖片至少考慮 480、960 與 1440 像素寬的實際需求，不可只用 CSS 縮小超大原圖。

建議最佳化後的單張文章圖片控制在 500 KB 內；超過 1 MB 時必須說明無法再縮小的原因。PDF 或附件超過 10 MB 時，發布前必須額外 Review。

## Cache 規則

GitHub Issue 附件的回應標頭與 Cache 行為由 GitHub 控制，本站無法指定 `Cache-Control` 或執行 purge。因此採用下列規則：

- 已發布的附件視為不可變內容。
- 修正圖片時重新上傳，取得新網址並更新 manifest 與文章引用。
- 不使用 query string 模擬版本，也不假設同一網址會更新內容。
- 若日後必須自行控制 Cache，即視為重新評估物件儲存／CDN 的觸發條件。

## 權限與公開性

- 只在公開 `SyuanTsai/notes-assets` 的 Issue 上傳正式文章附件，確保讀者不需登入。
- 附件網址是公開資訊；上傳前必須移除工作信箱、Token、Cookie、個人資料、內部網址與不需要的 metadata。
- 專用帳號只以一般公開使用者身分新增 Issue／comment，不授予 collaborator、Token 或程式碼寫入權限。
- 本站無法設定 GitHub 附件的 CORS；一般 `<img>` 顯示可直接使用，需要 JavaScript 讀取內容或 Canvas 操作時必須逐案驗證。
- 文章代表圖片暫時維持 `/assets/images/` 站內路徑，避免同時變更 SEO／社群分享圖片規則。

## 發布流程

1. 將來源檔案最佳化並計算 SHA-256。
2. 使用語意化檔名保存來源，執行格式、大小、重複 hash 與敏感資料檢查。
3. 以專用帳號在 `notes-assets` 靜態資源登錄 Issue 新增一則包含文章 slug、檔名與 SHA-256 的 comment。
4. 將檔案貼上或拖曳至 comment，等待 GitHub 完成上傳並取得完整匿名化網址。
5. 更新 `docs/static-assets-manifest.yml`，再把相同網址加入文章。
6. 驗證未登入可存取、HTTPS、Content-Type、桌機／手機、深色模式、替代文字與版面。
7. Issue comment 與 manifest 一起提交 Review；不得只保存匿名化網址而沒有來源對應。

## 備份、故障與遷移

### 備份

- Git Repository 保存所有已發布來源及 manifest，GitHub Issue 附件只視為傳遞副本。
- manifest 至少記錄文章 slug、語意化名稱、GitHub URL、SHA-256、大小、Content-Type、來源檔路徑與登錄 Issue comment。
- 每月抽查附件 URL 是否仍可匿名存取，並比對下載內容的 SHA-256。
- 大型原始素材若不適合進入 Git，必須先保存於另一個受控備份位置，才可發布最佳化版本。

### 故障

- 單一附件失效：由 Repository 保存版本重新上傳，更新 manifest 與引用該網址的文章。
- Repository 被改為 Private 或即將刪除：在變更前依 manifest 完成全部附件遷移。
- GitHub 服務異常：本站沒有獨立 Origin fallback；若穩定性不符合需求，啟動外部物件儲存遷移。

### 遷移

1. 依 manifest 從 Repository 來源檔案重新發布到新服務。
2. 核對新舊檔案的 SHA-256、Content-Type 與顯示結果。
3. 建立「舊 GitHub URL → 新 URL」對照表，批次更新文章與 manifest。
4. 完成 Jekyll 建置及桌機／手機視覺驗證後再發布。
5. GitHub 附件沒有自訂網域抽象層，因此遷移必然需要修改文章；這是本方案已接受的主要代價。

## 最小可行驗證

1. 主帳號建立公開 `SyuanTsai/notes-assets` 並開啟 Issues。
2. 擁有者手動建立專用 GitHub machine user、啟用 2FA，並在雲端瀏覽器登入一次。
3. 專用帳號在 `notes-assets` 建立靜態資源登錄 Issue，不接受 collaborator 邀請。
4. 將既有 `request-flow.svg` 上傳為 Issue 附件並取得匿名化網址。
5. 建立第一筆 `docs/static-assets-manifest.yml` 紀錄。
6. 只在未列出文章範本替換這張測試圖片，不修改兩篇正式文章。
7. 驗證未登入存取、HTTPS、Content-Type、桌機／手機顯示、深色模式、替代文字與版面。
8. 從 Repository 來源重新計算 SHA-256，確認與 manifest 及下載附件一致。
9. MVP 通過後，再決定新文章開始採用的日期；既有 `/assets/` 網址不強制搬遷。

## 官方資料

- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [GitHub repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits)
- [GitHub attaching files](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files)
- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- [Cloudflare R2 public buckets and custom domains](https://developers.cloudflare.com/r2/buckets/public-buckets/)
- [Cloudflare R2 S3 API compatibility](https://developers.cloudflare.com/r2/api/s3/api/)
- [Cloudflare R2 object lifecycles](https://developers.cloudflare.com/r2/buckets/object-lifecycles/)
- [Cloudflare DNS partial setup](https://developers.cloudflare.com/dns/zone-setups/partial-setup/)
- [CloudFront flat-rate pricing plans](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/flat-rate-pricing-plan.html)
- [Restrict access to an Amazon S3 origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [Amazon S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
- [DigitalOcean Spaces pricing](https://www.digitalocean.com/pricing/spaces-object-storage)
- [DigitalOcean Spaces CDN and custom subdomains](https://docs.digitalocean.com/products/spaces/how-to/enable-cdn/)
- [Azure Blob Storage pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/)
- [Azure Front Door pricing](https://azure.microsoft.com/en-us/pricing/details/frontdoor/)
- [Reliability in Azure Blob Storage](https://learn.microsoft.com/en-us/azure/reliability/reliability-storage-blob)

## 參考案例

- [Will 保哥：使用 GitHub Issue 上傳部落格圖片](https://www.facebook.com/will.fans/posts/1087965440024211/)
