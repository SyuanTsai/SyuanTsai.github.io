---
title: "用 .gitconfig 隔離私人與工作 Git 身分"
date: 2026-09-03
last_modified_at: 2026-09-03
description: "使用條件式 Git 設定，依 Repository 位置自動切換私人與工作 Commit 身分。"
categories: [code]
tags: [maintainability]
draft: true
---

同一台電腦同時處理私人與工作 Repository 時，不要在全域設定共用的 Name 與 Email。
最直接的做法是依 Repository 所在目錄載入不同身分檔。

這只控制新 Commit 的作者與提交者身分；Push 使用哪個帳號，仍由 SSH 或 HTTPS 驗證決定。

## 核心設定

先將 Repository 分開存放：

- 私人：`C:/Git/Personal/`
- 工作：`C:/Git/Work/`

編輯 `C:/Users/USER/.gitconfig`：

```gitconfig
[user]
    useConfigOnly = true

[includeIf "gitdir/i:C:/Git/Personal/"]
    path = C:/Users/USER/.gitconfig-personal

[includeIf "gitdir/i:C:/Git/Work/"]
    path = C:/Users/USER/.gitconfig-work
```

重點只有三個：

- 主設定檔不放共用的 `user.name` 或 `user.email`。
- 私人與工作目錄分別載入自己的身分檔。
- 不符合已知目錄的 Repository 不應自動套用預設身分。

## 建立兩份身分檔

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

## 驗證結果

在目標 Repository 執行：

```powershell
git config --show-origin --get user.name
git config --show-origin --get user.email
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
```

輸出來源應指向正確的身分檔，Name 與 Email 也必須符合該 Repository 類型。

## 仍需注意

- Repository-local 的 `.git/config` 可以覆蓋條件式設定。
- `GIT_AUTHOR_EMAIL` 與 `GIT_COMMITTER_EMAIL` 等環境變數可以覆蓋 Git 設定。
- `.gitconfig` 不決定 Push 帳號；SSH Key 或 HTTPS Credential 必須另外隔離。
- Codex Cloud 使用獨立 Container，不會自動繼承 Host 的設定。
- 這項設定只影響後續 Commit，不會改寫歷史紀錄。

核心原則：先依目錄選擇身分，確認有效值後才 Commit。

## 參考資料

- [Git 官方文件：user.name 與 user.email](https://git-scm.com/docs/git-config#Documentation/git-config.txt-username)
- [Git 官方文件：Conditional includes](https://git-scm.com/docs/git-config#_conditional_includes)
- [OpenAI 文件：Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment)

## 更新紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-09-03 | 草稿。 |
