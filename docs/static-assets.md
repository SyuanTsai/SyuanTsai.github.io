# 靜態資源儲存與發布策略

本文件記錄本站圖片、PDF、附件與其他靜態資源的儲存、發布、備份及遷移策略。價格與服務限制的比較基準日為 2026-08-30；正式導入前必須再核對供應商官方文件。

## 現況

- Repository 目前只有一個文章 SVG，檔案約 2.1 KB。
- `assets/` 目錄連同目錄結構約 24 KB。
- 尚未使用 PDF、ZIP 或其他文章附件。
- 尚未依賴免費公共圖床或供應商專屬資源網址。
- 文章範本目前使用 `/assets/images/posts/<slug>/...` 站內相對網址。

現有規模不需要為容量或流量立即搬遷；本次工作的重點是先建立不綁定供應商、可備份且能長期維護的公開網址與作業方式。

## 方案比較

| 方案 | 目前成本與額度 | 優點 | 主要限制 | 維護負擔 | 結論 |
| --- | --- | --- | --- | --- | --- |
| GitHub Repository／Pages | Pages 發布內容上限 1 GB、每月 100 GB 軟性流量上限 | 現有流程即可使用；Git commit 本身可追蹤版本；不增加帳號與部署服務 | 大型二進位檔會擴大 Git 歷史；Cache 與資源網域控制有限；若要獨立使用 `assets.tw-syuan.com`，需建立另一個 Pages 站點 | 低 | 保留為來源與備援，不作長期公開資源主站 |
| Cloudflare R2 Standard | 每月 10 GB 儲存、100 萬次 Class A、1,000 萬次 Class B 免費；對外傳輸免費 | 可直接綁定自訂網域並使用 Cloudflare Cache；S3 相容 API 方便上傳與遷移；目前規模預期落在免費額度 | 不支援 S3 Bucket Versioning、原生 Bucket Replication 與 Object Lock；必須另做來源保存與備份 | 低至中 | **建議作為公開資源主方案** |
| Amazon S3＋CloudFront | CloudFront Free 固定方案包含 5 GB S3 儲存抵用、每月 100 GB 傳輸與 100 萬次請求 | S3 Versioning、生命週期與完整 AWS 生態成熟；CloudFront 可搭配私有 S3 Origin Access Control | Bucket、CloudFront、OAC、憑證與 DNS 設定較多；免費額度的請求數低於 R2 | 中至高 | 合格替代與未來遷移目標 |
| Azure Blob Storage＋Front Door | Blob、操作與流量另計；Front Door Standard 固定費用為每月 US$35，另計傳輸與請求 | Blob Versioning、冗餘與 Azure 整合完整；Front Door 支援自訂網域與 TLS | 固定費用遠高於目前需求，設定與維護亦較複雜 | 高 | 目前不採用 |

### 建議選擇

採用「Git Repository 保存來源，Cloudflare R2 負責公開傳遞」的混合方式：

1. Git Repository 保存可重新發布的最佳化檔案、檔案清單與 SHA-256，作為版本來源及第一層備份。
2. Cloudflare R2 Standard 保存公開物件，透過 `assets.tw-syuan.com` 提供內容。
3. 文章只引用自有網域，不引用 `r2.dev`、R2 API endpoint 或其他供應商專屬網址。
4. R2 發生故障或未來更換供應商時，將相同 object key 複製到新服務，再切換 `assets.tw-syuan.com` 的 DNS；文章不需要修改。

此建議以 `tw-syuan.com` 可由同一個 Cloudflare 帳號管理，或可安全移入該帳號為前提。若不符合此前提，主方案改評估 S3＋CloudFront，不應為了 R2 直接變更正式 DNS。

## 公開網址與目錄

公開網址固定使用：

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
- R2 綁定自訂網域後啟用 Cache；`r2.dev` 只可用於短期驗證，正式啟用前必須關閉。
- HTML、robots、sitemap 與 API 回應不放在本資源 Bucket。

## 權限與 CORS

- 匿名使用者只可透過 `assets.tw-syuan.com` 讀取公開資源。
- 不允許匿名 `PUT`、`POST` 或 `DELETE`。
- 上傳 Token 僅能寫入指定 Bucket，不授予帳號層級管理權限。
- Token 只保存在 GitHub Actions Secrets 或本機安全憑證儲存區，不寫入 Repository、文章或建置輸出。
- 關閉正式 Bucket 的 `r2.dev` 公開網址，避免繞過自訂網域的 Cache 與安全規則。
- CORS 預設只允許 `GET`、`HEAD`，來源限制為 `https://notes.tw-syuan.com`；若一般 `<img>` 不需要跨來源讀取內容，則不額外放寬 CORS。
- PDF 預設使用 `Content-Disposition: inline`；強制下載的附件才使用 `attachment`。

## 發布流程

1. 將來源檔案最佳化並計算 SHA-256。
2. 依規則建立 object key，更新資源 manifest。
3. 在本機執行路徑、格式、大小、重複 hash 與敏感資料檢查。
4. 使用 Bucket-scoped Token 將檔案 copy 至 R2；自動流程不得以 `sync --delete` 刪除遠端物件。
5. 設定正確的 `Content-Type`、`Cache-Control` 與必要的 `Content-Disposition`。
6. 透過 `https://assets.tw-syuan.com/...` 執行 `HEAD` 與實際下載驗證。
7. 確認桌機、手機、深色模式、替代文字與版面無誤後，再把新網址加入文章。
8. 未被引用的舊物件至少保留 90 天；刪除必須人工 Review。

## 備份、故障與遷移

### 備份

- Git Repository 保存所有已發布資源及 manifest，R2 只視為傳遞副本。
- manifest 至少記錄 object key、SHA-256、大小、Content-Type 與來源檔路徑。
- 每月執行一次遠端清單與 SHA-256／ETag 核對。
- 大型原始素材若不適合進入 Git，必須先保存於另一個受控備份位置，才可發布最佳化版本。

### 故障

- 單一檔案損毀或誤刪：由 Git 保存版本依相同 object key 還原。
- R2 服務異常：文章先維持原網址；若達到需要切換的故障門檻，將 manifest 所列物件複製至備援服務並切換 DNS。
- 自訂網域憑證或 DNS 異常：先修復 `assets.tw-syuan.com`，不把文章改成供應商臨時網址。

### 遷移

1. 以 S3 API 或 `rclone copy` 將 manifest 中的物件複製到新供應商。
2. 核對 object key、SHA-256、Content-Type、Cache-Control 與 Content-Disposition。
3. 使用暫時測試 hostname 驗證圖片、PDF、Range request 與 CORS。
4. 降低 `assets.tw-syuan.com` DNS TTL，切換至新 CDN／Origin。
5. 觀察錯誤率後再停用舊服務；文章網址全程保持不變。

## 最小可行驗證

主方案確認後執行：

1. 建立一個 R2 Standard Bucket，名稱不出現在文章網址中。
2. 綁定 `assets.tw-syuan.com`，關閉 `r2.dev` 正式存取。
3. 將 `request-flow.svg` 以包含 content hash 的 object key 上傳。
4. 在未列出文章範本加入測試資源網址。
5. 驗證 HTTPS、Content-Type、Cache-Control、ETag、CORS、桌機／手機顯示與不存在物件的回應。
6. 驗證可由 Repository 保存檔案重新上傳並得到相同 SHA-256。
7. MVP 通過後，才決定是否遷移既有站內 `/assets/` 網址；不在驗證階段破壞現有網址。

## 官方資料

- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [GitHub repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits)
- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- [Cloudflare R2 public buckets and custom domains](https://developers.cloudflare.com/r2/buckets/public-buckets/)
- [Cloudflare R2 S3 API compatibility](https://developers.cloudflare.com/r2/api/s3/api/)
- [Cloudflare R2 object lifecycles](https://developers.cloudflare.com/r2/buckets/object-lifecycles/)
- [CloudFront flat-rate pricing plans](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/flat-rate-pricing-plan.html)
- [Restrict access to an Amazon S3 origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [Amazon S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
- [Azure Blob Storage pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/)
- [Azure Front Door pricing](https://azure.microsoft.com/en-us/pricing/details/frontdoor/)
- [Reliability in Azure Blob Storage](https://learn.microsoft.com/en-us/azure/reliability/reliability-storage-blob)
