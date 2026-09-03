---
layout: post
title: "用 .gitconfig 隔離私人與公司 Git Commit 身分"
date: 2026-09-03
last_modified_at: 2026-09-03
description: "在同一台 Windows 電腦使用條件式 Git 設定，依 Repository 位置切換私人與公司 Commit 身分，並釐清 SSH 驗證與 Codex 執行環境的邊界。"
eyebrow: "Draft Preview"
permalink: /preview/gitconfig-identity-isolation/
unlisted: true
sitemap: false
---

<aside class="warning" aria-label="未列出預覽" markdown="1">
**未列出預覽：** 此頁只供草稿 Review，不會出現在首頁、文章列表、站內搜尋或 Sitemap。知道網址的人仍可直接開啟。
</aside>

同一台電腦同時處理私人與公司 Repository 時，最容易忽略的風險不是程式碼衝突，而是 Commit 使用了錯誤的 Name 或 Email。只在全域 `.gitconfig` 設定一組 `user.name` 與 `user.email`，會讓所有 Repository 共用同一個身分；一旦忘記切換，錯誤資料就會進入 Git 歷史。

這篇文章整理一套適合 Windows 的隔離方式：以 `includeIf` 根據 Repository 所在目錄載入不同身分，並以 `user.useConfigOnly` 阻止 Git 在設定缺失時自行猜測。同時也會區分 Commit 身分、SSH／HTTPS 驗證，以及 Codex Local、Worktree 與 Cloud 所使用的設定位置。

## 先分清楚三種不同身分

Git 操作裡常被混為一談的其實有三個層次：

| 層次 | 決定內容 | 主要設定位置 |
| --- | --- | --- |
| Commit 身分 | Commit 的 Author／Committer Name 與 Email | `.gitconfig` |
| 遠端驗證身分 | 使用哪個 GitHub、Bitbucket 帳號或 SSH Key | `.ssh/config`、Credential Manager |
| 執行環境 | Git 指令實際在哪一台電腦或 Container 執行 | Local Host、Remote Host、Cloud Container |

`user.name` 與 `user.email` 只會寫入 Commit metadata，不會決定 Push 時登入哪個網站帳號。Git 官方文件也將 Commit 身分設定和驗證用的 `credential.username` 明確區分。[^git-config-user]

因此，即使 Commit Email 正確，SSH Key 或 HTTPS Credential 仍可能屬於另一個帳號；反過來也一樣。

## Windows 上的設定檔位置

Windows 使用者 `carsu` 的主要檔案位置如下：

| Git 表示法 | Windows 路徑 | 用途 |
| --- | --- | --- |
| `~/.gitconfig` | `C:\\Users\\carsu\\.gitconfig` | 全域 Git 設定與條件式載入 |
| `~/.gitconfig-personal` | `C:\\Users\\carsu\\.gitconfig-personal` | 私人 Commit 身分 |
| `~/.gitconfig-company` | `C:\\Users\\carsu\\.gitconfig-company` | 公司 Commit 身分 |
| `~/.ssh/config` | `C:\\Users\\carsu\\.ssh\\config` | SSH Host 與 Key 的選擇 |

`.ssh/config` 是沒有副檔名的純文字檔，不是 `config.txt`。

## 用 includeIf 依 Repository 位置切換

主 `C:\\Users\\carsu\\.gitconfig` 不保存任何共用的 Name 或 Email，只負責啟用 fail-safe 並依路徑載入對應設定：

```gitconfig
[user]
    useConfigOnly = true

[includeIf "gitdir/i:C:/GitFile/Personal/"]
    path = C:/Users/carsu/.gitconfig-personal

[includeIf "gitdir/i:C:/GitFile/ROAR/"]
    path = C:/Users/carsu/.gitconfig-company
```

`gitdir/i` 代表依 Git directory 比對，並忽略大小寫。條件路徑以斜線結尾時，Git 會把它視為包含底下所有子目錄，因此公司 Repository 只要統一放在 `C:/GitFile/ROAR/` 下方，就會載入公司設定。[^git-config-includeif]

<aside class="warning" aria-label="注意" markdown="1">
**注意：** `C:/GitFile/Personal/` 是示意路徑。套用前必須替換成私人 Repository 的實際共同根目錄；若私人 Repository 沒有共同根目錄，應先整理目錄或對個別 Repository 設定 local identity。
</aside>

`user.useConfigOnly = true` 會要求 Git 只接受明確設定的 Name 與 Email。當 Repository 不符合任何已知路徑時，Commit 應失敗，而不是使用 Windows 帳號或主機名稱推測身分。[^git-config-user]

## 分開保存私人與公司身分

私人設定檔 `C:\\Users\\carsu\\.gitconfig-personal`：

```gitconfig
[user]
    name = YOUR_NAME
    email = YOUR_PERSONAL_EMAIL
```

公司設定檔 `C:\\Users\\carsu\\.gitconfig-company`：

```gitconfig
[user]
    name = YOUR_NAME
    email = YOUR_COMPANY_EMAIL
```

公開文章與公開 Repository 不應直接保存不必要的私人或公司資料，因此範例使用 placeholder。實際設定時再於本機檔案填入正確值。

## 設定優先順序仍可能造成覆寫

條件式全域設定不是絕對防護。常見優先順序可以簡化理解為：

```text
system
  ↓
global 與 includeIf
  ↓
repository-local
  ↓
worktree、命令列與 Git 身分環境變數
```

如果某個 Repository 的 `.git/config` 已有錯誤的 `user.email`，local 設定仍會覆蓋 `includeIf` 載入的身分。使用 `git config --local` 寫入的內容就是保存在該 Repository 的 `.git/config`。[^git-config-local]

下列環境變數也能覆蓋設定檔中的 Commit 身分：[^git-config-user]

```text
GIT_AUTHOR_NAME
GIT_AUTHOR_EMAIL
GIT_COMMITTER_NAME
GIT_COMMITTER_EMAIL
EMAIL
```

因此，完成 Host 設定後仍應檢查既有 Repository 是否含有 local override，也不要在 IDE、CI 或 Cloud Environment 長期保存共用的 Git 身分環境變數。

## SSH 設定處理的是 Push 驗證

如果 GitHub 與 Bitbucket 各自使用不同 SSH Key，可以在 `C:\\Users\\carsu\\.ssh\\config` 依 Host 選擇：

```sshconfig
Host github.com
    HostName github.com
    User git
    IdentityFile C:/Users/carsu/.ssh/YOUR_PERSONAL_KEY
    IdentitiesOnly yes

Host bitbucket.org
    HostName bitbucket.org
    User git
    IdentityFile C:/Users/carsu/.ssh/YOUR_COMPANY_KEY
    IdentitiesOnly yes
```

`IdentitiesOnly yes` 可避免 ssh-agent 載入多把 Key 時，SSH 嘗試使用非預期的 Key。[^github-multiple-accounts]

這份設定只有在 Remote 使用 SSH 格式時生效：

```text
git@github.com:OWNER/REPOSITORY.git
git@bitbucket.org:WORKSPACE/REPOSITORY.git
```

如果 Remote 使用 `https://`，驗證身分通常由 Git Credential Manager 或其他 Credential Helper 管理，`.ssh/config` 不會參與。

## Codex Local、Worktree 與 Cloud 的差異

Codex Local 與 Windows 上的 Worktree 仍在本機執行 Git，因此會使用該 Windows 使用者的 `~/.gitconfig`。Worktree 雖然有獨立工作目錄，但 Git 會依實際 Git directory 判斷 `includeIf` 條件。[^openai-worktrees]

Connected Remote Host 則使用遠端主機帳號的 `~/.gitconfig`，不會自動讀取 Windows 本機設定。

Codex Cloud 會建立獨立 Container、簽出 Repository，再執行 Environment Setup Script，因此不會讀取 Windows 的 `C:\\Users\\carsu\\.gitconfig`。Cloud 必須在 Repository-local config 或對應 Environment Script 另外設定，而且不能假設 Host 設定已經存在。[^openai-cloud-environments]

## 驗證目前生效的身分

設定完成後，可以在每個 Repository 內執行以下唯讀檢查：

```powershell
git remote -v
git config --show-origin --get user.name
git config --show-origin --get user.email
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
```

`--show-origin` 很重要，因為它不只顯示值，還會顯示該值來自哪一個設定檔。若結果來自 Repository-local `.git/config`，就要確認它是否刻意覆蓋 Host 設定。

若要進一步檢查是否存在環境變數覆寫，可以在 PowerShell 查看：

```powershell
Get-ChildItem Env: |
    Where-Object Name -in @(
        'GIT_AUTHOR_NAME',
        'GIT_AUTHOR_EMAIL',
        'GIT_COMMITTER_NAME',
        'GIT_COMMITTER_EMAIL',
        'EMAIL'
    )
```

## 實務上的安全原則

建議將身分隔離維持在以下幾條簡單規則：

1. 主 `.gitconfig` 不保存共用的 Name 或 Email。
2. 私人與公司 Repository 放在不同的共同根目錄。
3. 使用 `includeIf "gitdir/i:..."` 載入個別身分。
4. 全域啟用 `user.useConfigOnly = true`。
5. 逐一清查既有 Repository 的 local identity。
6. Commit 身分與 Push 驗證分開檢查。
7. Codex Cloud 使用獨立 Environment 設定，不依賴 Windows Host。
8. 不因歷史 Commit 的 Email 錯誤而直接重寫 Git 歷史。

這套配置的目的不是自動判斷所有未知情況，而是讓未知 Repository 無法悄悄使用預設身分。當規則無法分類時，讓 Commit 失敗通常比留下難以清理的錯誤作者紀錄更安全。

## 參考資料

[^git-config-user]: [git-config：user.name、user.email 與 user.useConfigOnly](https://git-scm.com/docs/git-config#Documentation/git-config.txt-username) — Git
[^git-config-includeif]: [git-config：Conditional includes](https://git-scm.com/docs/git-config#_conditional_includes) — Git
[^git-config-local]: [git-config：--local](https://git-scm.com/docs/git-config#Documentation/git-config.txt---local) — Git
[^github-multiple-accounts]: [Managing multiple accounts](https://docs.github.com/en/account-and-profile/how-tos/account-management/managing-multiple-accounts) — GitHub Docs
[^openai-worktrees]: [Worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees) — OpenAI
[^openai-cloud-environments]: [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment) — OpenAI

1. 引用資料由系統自動產生
{:footnotes}

## 更新紀錄

| 日期 | 更新內容 |
| --- | --- |
| 2026-09-03 | 建立初版草稿，整理 Windows 條件式 Git 身分、SSH 驗證與 Codex 環境差異 |
{: .update-history}
