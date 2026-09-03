---
title: "用 .gitconfig 隔離私人與工作 Git 身分"
date: 2026-09-03
last_modified_at: 2026-09-03
description: "使用條件式 Git 設定，依 Repository 位置自動切換私人與工作 Commit 身分，避免 Name 或 Email 混用。"
categories: [code]
tags: [maintainability]
draft: true
---

同一台電腦同時處理私人與工作 Repository 時，不要在全域設定固定的 Name 與 Email。最簡單的做法是依 Repository 目錄載入不同身分。

本文只處理 Commit 的 Author／Committer 身分。SSH Key、HTTPS 登入帳號與歷史 Commit 不在這份設定的控制範圍內。

## 核心設定

先把 Repository 分到兩個根目錄：

```text
C:/Git/Personal/
C:/Git/Work/
```

接著設定 Windows 使用者的主檔案：

```text
C:/Users/USER/.gitconfig
```

內容如下：

```gitconfig
[user]
    useConfigOnly = true

[includeIf "gitdir/i:C:/Git/Personal/"]
    path = C:/Users/USER/.gitconfig-personal

[includeIf "gitdir/i:C:/Git/Work/"]
    path = C:/Users/USER/.gitconfig-work
```

這份主設定有三個重點：

- 不設定共用的 `user.name` 或 `user.email`。
- 私人與工作 Repository 分別載入不同檔案。
- 未符合規則的 Repository 無法靠系統資訊猜測身分。[^git-config-user]

`gitdir/i` 會忽略路徑大小寫。條件路徑以斜線結尾時，也會套用到底下所有子目錄。[^git-config-includeif]

## 建立兩份身分檔

私人身分檔：

```text
C:/Users/USER/.gitconfig-personal
```

```gitconfig
[user]
    name = YOUR_NAME
    email = YOUR_PERSONAL_EMAIL
```

工作身分檔：

```text
C:/Users/USER/.gitconfig-work
```

```gitconfig
[user]
    name = YOUR_NAME
    email = YOUR_WORK_EMAIL
```

`USER`、Name 與 Email 都必須換成自己的實際資料。公開 Repository 不應保存真正的 Email 或 SSH Key 路徑。

## 驗證結果

分別進入私人與工作 Repository，執行：

```powershell
git config --show-origin --get user.name
git config --show-origin --get user.email
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
```

前兩個指令會同時顯示設定值及來源檔案。私人 Repository 應來自 `.gitconfig-personal`，工作 Repository 應來自 `.gitconfig-work`。

## 仍需注意

- Repository 的 `.git/config` 可以覆蓋上述全域設定。
- `GIT_AUTHOR_EMAIL` 與 `GIT_COMMITTER_EMAIL` 等環境變數也能覆蓋 Commit 身分。[^git-config-user]
- `.gitconfig` 不決定 Push 使用哪一個帳號；SSH 與 HTTPS 驗證必須另外設定。
- Codex Local／Worktree 使用 Host 設定；Codex Cloud 是獨立 Container，必須另外設定 Environment。[^openai-cloud-environments]
- 修改設定只影響未來 Commit，不會改寫歷史紀錄。

核心原則只有一個：沒有明確符合私人或工作規則時，就不要讓 Git 建立 Commit。

## 參考資料

[^git-config-user]: [git-config：user.name、user.email 與 user.useConfigOnly](https://git-scm.com/docs/git-config#Documentation/git-config.txt-username) — Git
[^git-config-includeif]: [git-config：Conditional includes](https://git-scm.com/docs/git-config#_conditional_includes) — Git
[^openai-cloud-environments]: [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment) — OpenAI

1. 引用資料由系統自動產生
{:footnotes}

## 更新紀錄

| 日期 | 更新內容 |
| --- | --- |
| 2026-09-03 | 建立初版草稿 |
| 2026-09-03 | 移除個人與工作識別資訊，並精簡成核心設定流程 |
{: .update-history}
