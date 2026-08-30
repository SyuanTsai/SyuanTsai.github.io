# 靜態資源儲存與發布策略

本文件記錄本站圖片、PDF、附件與其他靜態資源的儲存、發布、備份及遷移策略。價格與服務限制的比較基準日為 2026-08-30；正式導入前必須再核對供應商官方文件。

## 現況

- Repository 目前只有一個文章 SVG，檔案約 2.1 KB。
- `assets/` 目錄連同目錄結構約 24 KB。
- 尚未使用 PDF、ZIP 或其他文章附件。
- 尚未依賴免費公共圖床或供應商專屬資源網址。
- 文章範本目前使用 `/assets/images/posts/<slug>/...` 站內相對網址。

現有規模不需要為容量或流量立即搬遷；本次工作的重點是先建立不綁定供應商、可備份且能長期維護的公開網址與作業方式。

目前階段只進行方案盤點與比較。尚未選定供應商，也不建立 Bucket、不修改 DNS、不切換正式文章網址；下列設計均為評估草案，待選定方案後才執行 MVP。

## 方案比較

| 方案 | 目前成本與額度 | 優點 | 主要限制 | 維護負擔 | 本階段定位 |
| --- | --- | --- | --- | --- | --- |
| GitHub Repository／Pages | Pages 發布內容上限 1 GB、每月 100 GB 軟性流量上限 | 現有流程即可使用；Git commit 本身可追蹤版本；不增加帳號與部署服務 | 大型二進位檔會擴大 Git 歷史；Cache 與資源網域控制有限；若要獨立使用 `assets.tw-syuan.com`，需建立另一個 Pages 站點 | 低 | 零變更基準方案 |
| Cloudflare R2 Standard | 每月 10 GB 儲存、100 萬次 Class A、1,000 萬次 Class B 免費；對外傳輸免費 | 自訂網域可使用 Cloudflare Cache；S3 相容 API 方便上傳與遷移；目前規模預期落在免費額度 | `tw-syuan.com` 目前不由 Cloudflare 管理；Free／Pro 不支援保留既有權威 DNS 的 Partial CNAME setup。另不支援 S3 Bucket Versioning、原生 Bucket Replication 與 Object Lock | 低至中 | 若願意遷移權威 DNS，再列入低成本候選 |
| Amazon S3＋CloudFront | CloudFront Free 固定方案包含 5 GB S3 儲存抵用、每月 100 GB 傳輸與 100 萬次請求 | S3 Versioning、生命週期與完整 AWS 生態成熟；CloudFront 可搭配私有 S3 Origin Access Control；可沿用現有權威 DNS | Bucket、CloudFront、OAC、憑證與 DNS 設定較多 | 中至高 | 保留現有 DNS 時的成熟候選 |
| DigitalOcean Spaces＋CDN | 每月 US$5，含 250 GiB 儲存與 1 TiB 對外傳輸 | S3 相容、CDN 內建、費用結構簡單；外部 DNS 可使用自有憑證綁定自訂子網域 | 目前用量遠低於固定方案額度；外部 DNS 情境需自行建立、上傳及維護憑證 | 中 | 保留現有 DNS 時的簡化付費候選 |
| Azure Blob Storage＋Front Door | Blob、操作與流量另計；Front Door Standard 固定費用為每月 US$35，另計傳輸與請求 | Blob Versioning、冗餘與 Azure 整合完整；Front Door 支援自訂網域與 TLS | 固定費用遠高於目前需求，設定與維護亦較複雜 | 高 | Azure 生態需求出現時再評估 |

### 階段性結論（尚未選定）

本階段不指定主方案。依目前資訊，後續決策可分成以下情境：

| 決策條件 | 優先保留候選 | 需要再驗證 |
| --- | --- | --- |
| 不新增服務、成本與維護最小 | GitHub Repository／Pages | 獨立資源網域與長期 Repository 容量是否必要 |
| 保留現有權威 DNS，重視成熟的版本與權限能力 | Amazon S3＋CloudFront | 實際設定複雜度、免費方案條款與超額行為 |
| 保留現有權威 DNS，願意用固定月費換取較簡單操作 | DigitalOcean Spaces＋CDN | 自有憑證更新流程與台灣連線表現 |
| 願意把權威 DNS 移至 Cloudflare | Cloudflare R2 | DNS 遷移風險、備份與缺少 Bucket Versioning 的補償措施 |
| 已有 Azure 使用與維運需求 | Azure Blob Storage＋Front Door | 固定成本是否能由其他工作負載共同攤提 |

無論最後選哪一個外部方案，都可評估使用「Repository 保存可重新發布的檔案與 manifest，物件儲存／CDN 負責公開傳遞」的混合架構。文章只引用自有網域，不引用 `r2.dev`、S3 endpoint 或其他供應商專屬網址，才能在未來切換服務時保留文章網址。

## 公開網址與目錄

若採用獨立資源網域，候選公開網址為：

```text
https://assets.tw-syuan.com/<object-key>
```

Object key 使用以下結構：

```text
posts/<yyyy>/<article-slug>/<semantic-name>-<content-hash>.<ext>
shared/<category>/<semantic-name>-<content-hash>.<ext>
downloads/<yyyy>/<article-slug>/<semantic-name>-<content-hash>.<ext>
```

例如：

```text
posts/2026/debugging-http-timeouts/request-flow-a1b2c3d4.svg
downloads/2026/debugging-http-timeouts/benchmark-result-e5f6a7b8.pdf
```

規則：

- 路徑與檔名只使用小寫英文字母、數字、連字號、斜線及副檔名的句點。
- `article-slug` 與文章檔名使用相同 slug。
- 檔名描述內容，不使用 `image1`、`final`、`new` 等無法辨識用途的名稱。
- `content-hash` 使用檔案 SHA-256 的前 8 碼。
- 已公開物件不得覆寫；內容變更時產生新的 hash 與網址。
- 已被文章引用的 object key 不得重新指向不同內容。

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

使用包含 content hash 的不可變網址：

```http
Cache-Control: public, max-age=31536000, immutable
```

若未來需要公開可變動的 manifest，使用：

```http
Cache-Control: public, max-age=300, must-revalidate
```

- 不以 purge 取代版本化網址。
- 修正已發布檔案時，上傳新 object key 並更新文章引用。
- 正式資源透過自訂網域與 CDN Cache 提供；供應商預設公開網址只用於短期驗證，正式啟用前應關閉或限制。
- HTML、robots、sitemap 與 API 回應不放在本資源 Bucket。

## 權限與 CORS

- 匿名使用者只可透過 `assets.tw-syuan.com` 讀取公開資源。
- 不允許匿名 `PUT`、`POST` 或 `DELETE`。
- 上傳 Token 僅能寫入指定 Bucket，不授予帳號層級管理權限。
- Token 只保存在 GitHub Actions Secrets 或本機安全憑證儲存區，不寫入 Repository、文章或建置輸出。
- 關閉或限制正式 Bucket 的供應商預設公開網址，避免繞過自訂網域的 Cache 與安全規則。
- CORS 預設只允許 `GET`、`HEAD`，來源限制為 `https://notes.tw-syuan.com`；若一般 `<img>` 不需要跨來源讀取內容，則不額外放寬 CORS。
- PDF 預設使用 `Content-Disposition: inline`；強制下載的附件才使用 `attachment`。

## 發布流程

1. 將來源檔案最佳化並計算 SHA-256。
2. 依規則建立 object key，更新資源 manifest。
3. 在本機執行路徑、格式、大小、重複 hash 與敏感資料檢查。
4. 使用 Bucket-scoped Token 將檔案 copy 至選定服務；自動流程不得以 `sync --delete` 刪除遠端物件。
5. 設定正確的 `Content-Type`、`Cache-Control` 與必要的 `Content-Disposition`。
6. 透過 `https://assets.tw-syuan.com/...` 執行 `HEAD` 與實際下載驗證。
7. 確認桌機、手機、深色模式、替代文字與版面無誤後，再把新網址加入文章。
8. 未被引用的舊物件至少保留 90 天；刪除必須人工 Review。

## 備份、故障與遷移

### 備份

- 若採用混合架構，Git Repository 保存所有已發布資源及 manifest，物件儲存／CDN 只視為傳遞副本。
- manifest 至少記錄 object key、SHA-256、大小、Content-Type 與來源檔路徑。
- 每月執行一次遠端清單與 SHA-256／ETag 核對。
- 大型原始素材若不適合進入 Git，必須先保存於另一個受控備份位置，才可發布最佳化版本。

### 故障

- 單一檔案損毀或誤刪：由 Git 保存版本依相同 object key 還原。
- 公開傳遞服務異常：文章先維持原網址；若達到需要切換的故障門檻，將 manifest 所列物件複製至備援服務並切換 DNS。
- 自訂網域憑證或 DNS 異常：先修復 `assets.tw-syuan.com`，不把文章改成供應商臨時網址。

### 遷移

1. 以 S3 API 或 `rclone copy` 將 manifest 中的物件複製到新供應商。
2. 核對 object key、SHA-256、Content-Type、Cache-Control 與 Content-Disposition。
3. 使用暫時測試 hostname 驗證圖片、PDF、Range request 與 CORS。
4. 降低 `assets.tw-syuan.com` DNS TTL，切換至新 CDN／Origin。
5. 觀察錯誤率後再停用舊服務；文章網址全程保持不變。

## 最小可行驗證（方案選定後執行）

目前不執行 Bucket、DNS 或正式網址變更。選定方案後才進行下列共通 MVP：

1. 建立測試用 Bucket／Origin，名稱不出現在文章的長期公開網址中。
2. 先以測試 hostname 驗證；確認全部項目後才評估綁定 `assets.tw-syuan.com`。
3. 將 `request-flow.svg` 以包含 content hash 的 object key 上傳。
4. 在未列出文章範本加入測試資源網址，不修改正式文章。
5. 驗證 HTTPS、Content-Type、Cache-Control、ETag、CORS、桌機／手機顯示與不存在物件的回應。
6. 驗證可由 Repository 保存檔案重新上傳並得到相同 SHA-256。
7. 驗證 Bucket 權限、供應商預設公開網址及 Token 權限不會繞過預期限制。
8. MVP 通過後，才決定是否遷移既有站內 `/assets/` 網址；不在驗證階段破壞現有網址。

## 官方資料

- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [GitHub repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits)
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
