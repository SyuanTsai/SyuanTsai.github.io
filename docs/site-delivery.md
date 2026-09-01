# GitHub Pages 建置、發布與排錯

本站維持最小發布模式：`gh-pages` 是預設分支，也是 GitHub Pages 的來源。文章或網站設定合併／Push 到 `gh-pages` 後，由 GitHub 管理的 **pages build and deployment** 自動執行 Jekyll 建置並發布；Repository 內不再建立第二套正式部署 workflow。

## 正式環境基線

| 項目 | 設定 |
| --- | --- |
| 正式網址 | `https://notes.tw-syuan.com` |
| 部署路徑 | 網域根目錄，因此 `_config.yml` 的 `baseurl` 為空 |
| 內容語系 | `zh-TW` |
| Pages 來源 | `gh-pages` |
| 自訂網域檔案 | Repository 根目錄的 `CNAME`，內容為 `Notes.Tw-Syuan.com` |
| Sitemap | `https://notes.tw-syuan.com/sitemap.xml` |
| Feed | `https://notes.tw-syuan.com/feed.xml` |

`CNAME` 必須保留在來源根目錄。每次 PR 建置都會檢查 `_site/CNAME` 與來源一致，避免正式部署時遺失自訂網域。

## 一般文章發布

1. 依 `docs/article-authoring.md` 新增或修改 Markdown。
2. 執行分類／標籤入口產生及來源驗證。
3. 在本機完成 GitHub Pages 相同版本的 Jekyll 建置。
4. Push 至工作分支並建立 PR；Repository 的 `Test Jekyll site` 會執行完整建置驗證。
5. 合併或直接 Push 到 `gh-pages` 後，GitHub 的 `pages build and deployment` 會自動發布。

不要求每篇文章都經過 PR；若直接 Push 到 `gh-pages`，仍會觸發 GitHub Pages 建置。PR 的用途是讓正式發布前先取得相同的建置與內容驗證結果。

## 本機預覽與完整驗證

第一次使用或 Gemfile 變更後執行：

```bash
bundle install
```

日常預覽：

```bash
bundle exec jekyll serve --livereload
```

`_config.yml` 變更後必須停止並重新啟動 Jekyll；該檔案不支援執行中的自動重新載入。

提交前的最小完整檢查：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_posts.py
python3 scripts/generate_discovery_pages.py --check
bundle exec jekyll build --strict_front_matter
python3 scripts/verify_generated_seo.py _site
python3 scripts/verify_content_discovery.py _site
python3 scripts/verify_unlisted_preview.py _site
python3 scripts/verify_site_delivery.py _site
```

最後一項會檢查正式 `url`、空的 `baseurl`、語系、CNAME、Sitemap、Feed、所有文章是否進入 Sitemap，以及首頁是否提供 Feed discovery link。

## GitHub 上的失敗定位

### PR 建置失敗

1. 開啟 PR 的 **Checks** 或 Repository 的 **Actions**。
2. 選擇 `Test Jekyll site`。
3. 展開第一個失敗步驟；驗證腳本會列出檔名、缺少的產物或不符合的網址。
4. 若 `Build with GitHub Pages` 失敗，優先檢查 Front Matter、Liquid、YAML、Gemfile 與 `_config.yml`。
5. 若建置成功但後續檢查失敗，依失敗步驟修正來源，不要手動修改 `_site`。

### 正式部署失敗

1. 在 **Actions** 開啟最新的 `pages build and deployment`。
2. 確認該次執行的 commit SHA 是否等於 `gh-pages` 最新 commit。
3. 展開失敗的 build 或 deploy job；GitHub Pages 顯示的第一個錯誤通常是實際根因。
4. 修正後再次 Push；不要重新上傳 `_site`，也不要建立另一套部署 workflow 覆蓋 GitHub Pages。

### 部署成功但網站看不到更新

1. 確認 `pages build and deployment` 結果為 `success`。
2. 確認正式網址使用 `https://notes.tw-syuan.com`，不是 Repository 預設網址或舊文章網址。
3. GitHub Pages 回應可能帶有約十分鐘的快取；先等待快取期限，再以新的 query string 驗證，例如 `?verify=<commit-sha>`。
4. 檢查正式 HTML 載入的 CSS／JavaScript 是否為新版本，再判斷是否為瀏覽器或 CDN 快取。

## 自訂網域與 HTTPS

- DNS 與 GitHub Pages 的 Custom domain 必須共同指向 `notes.tw-syuan.com`。
- Repository 根目錄必須保留 `CNAME`；CI 也必須確認建置輸出仍包含它。
- 正式驗收使用 HTTPS 網址；若憑證或 DNS 異常，到 Repository **Settings → Pages** 檢查 Custom domain 與 Enforce HTTPS 狀態。
- 不以修改 `CNAME` 大小寫、手動上傳 `_site` 或新增第二套發布 workflow 作為排錯方式。

## 已確認的自動發布證據

2026-08-31 的 `gh-pages` commit `bf3b44c35ddd831077f33b9185176df393ef7daa` 包含 Markdown 與網站資產變更，GitHub 管理的 `pages build and deployment` run `33364299438` 自動執行並成功完成。這可作為「Push／合併至 `gh-pages` 後自動建置與發布」的既有基線；SYP-124 合併後仍需以新 commit 的 Pages run 與正式 Sitemap／Feed 完成最終驗收。
