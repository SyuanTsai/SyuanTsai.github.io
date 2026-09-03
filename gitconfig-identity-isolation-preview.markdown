---
layout: post
title: "同一台電腦分開管理個人與公司 Git 身分"
date: 2026-09-03
last_modified_at: 2026-09-03
description: "用 Git 的 includeIf 依資料夾套用不同的姓名與 Email，避免 Commit 留下錯誤身分。"
eyebrow: "Draft Preview"
permalink: /preview/gitconfig-identity-isolation/
unlisted: true
sitemap: false
---

> 這是未列在網站導覽與 Sitemap 的預覽頁。只要知道網址仍看得到，因此內容一樣必須當成公開資料處理。

同一台電腦同時處理個人專案和公司專案，最容易踩到的雷，就是 Commit 帶到錯的姓名或 Email。

解法很單純：把兩類專案放在不同資料夾，再用 Git 的 `includeIf` 依路徑載入對應的身分設定。

這篇只處理 Commit 身分。Push 實際使用哪個帳號，仍由 SSH 或 HTTPS 的登入方式決定。

## 先把專案分開放

例如：

- 個人專案：`C:/Git/Personal/`
- 公司專案：`C:/Git/Work/`

只要專案放在對應的根目錄下，Git 就能自動選到正確身分。

## 讓主設定檔只負責分流

編輯 `C:/Users/USER/.gitconfig`：

```gitconfig
[user]
    useConfigOnly = true

[includeIf "gitdir/i:C:/Git/Personal/"]
    path = C:/Users/USER/.gitconfig-personal

[includeIf "gitdir/i:C:/Git/Work/"]
    path = C:/Users/USER/.gitconfig-work
```

這裡有三個重點：

- 主 `.gitconfig` 不設定共用的 `user.name` 和 `user.email`。
- `gitdir/i` 會依專案路徑比對，而且不分英文字母大小寫。
- 路徑最後的 `/` 不要省略，這樣才會包含該目錄底下的所有專案。

`user.useConfigOnly = true` 會阻止 Git 自行猜測身分。專案如果不在已設定的目錄內，Git 會要求先設定姓名和 Email，避免在不知情的情況下留下錯誤紀錄。

## 個人和公司各用一份設定

`C:/Users/USER/.gitconfig-personal`：

```gitconfig
[user]
    name = YOUR_NAME
    email = YOUR_PERSONAL_EMAIL
```

`C:/Users/USER/.gitconfig-work`：

```gitconfig
[user]
    name = YOUR_NAME
    email = YOUR_WORK_EMAIL
```

之後新增其他專案時，只要放進正確的資料夾，不必再逐一設定。

## Commit 前先確認

進入要操作的專案後執行：

```powershell
git config --show-origin --get user.name
git config --show-origin --get user.email
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
```

前兩行可以確認姓名與 Email 是從哪個設定檔載入；後兩行則會顯示下一次 Commit 實際使用的身分。

如果結果不對，先檢查專案內的 `.git/config`。Repo 自己的設定優先權較高，可能會蓋掉 `includeIf` 載入的內容。

## 這項設定不會處理的事

- `GIT_AUTHOR_EMAIL`、`GIT_COMMITTER_EMAIL` 等環境變數仍可能蓋掉 Git 設定。
- SSH Key 或 HTTPS Credential 決定 Push 使用哪個帳號，必須另外設定。
- Codex Cloud 在獨立的 Container 中執行，不會自動讀取電腦上的 `.gitconfig`。
- 這些設定只影響之後建立的 Commit，不會修改歷史紀錄。

簡單說：資料夾決定 Commit 身分，SSH 或 HTTPS 決定 Push 帳號。兩邊都要分開確認。

## 參考資料

- [Git 官方文件：user.name 與 user.email](https://git-scm.com/docs/git-config#Documentation/git-config.txt-username)
- [Git 官方文件：Conditional includes](https://git-scm.com/docs/git-config#_conditional_includes)
- [OpenAI 文件：Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment)

## 更新紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-09-03 | 調整文章結構與用詞。 |
