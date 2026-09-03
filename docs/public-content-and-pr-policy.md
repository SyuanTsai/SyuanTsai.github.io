# 公開內容與 Pull Request 安全規範

本 Repository 為公開內容。Draft、未列出的預覽頁、Branch、Commit 與 Pull Request diff 都可能被外部讀取；「未發布」不等於「非公開」。

## 禁止寫入的資訊

任何追蹤檔案、Commit 或 Pull Request 都不得包含：

- 真實的私人或工作 Email。
- 作業系統使用者名稱、Home 路徑或裝置名稱。
- 雇主、客戶、內部組織、Repository 或專案名稱。
- 內部 URL、Host、Ticket ID 或網路拓樸。
- Token、密碼、私鑰、實際 Key 檔名或其他 Credential。
- 含有上述資訊的 Screenshot、Log 或指令輸出。

## 公開範例統一代稱

| 資訊類型 | 使用代稱 |
| --- | --- |
| 作業系統使用者 | `USER` |
| Git Name | `YOUR_NAME` |
| 私人 Email | `YOUR_PERSONAL_EMAIL` |
| 工作 Email | `YOUR_WORK_EMAIL` |
| 私人／工作目錄 | `C:/Git/Personal/`、`C:/Git/Work/` |
| 組織／Repository | `OWNER/REPOSITORY`、`WORKSPACE/REPOSITORY` |
| SSH Key | `YOUR_PERSONAL_KEY`、`YOUR_WORK_KEY` |

不得在規範、範例或清除說明中重複列出真實敏感值。

## Commit 前檢查

1. 只檢查準備提交的差異。
2. 搜尋 `@`、`C:/Users/`、URL、組織名稱、Repository 名稱、Ticket 格式與疑似 Secret。
3. 確認 Screenshot、Log、Front Matter、連結文字與程式碼區塊均使用通用代稱。
4. 無法確認是否可公開時，停止提交並詢問 Repository 擁有者。

## Pull Request 流程

1. 從目前 Default Branch 建立新的非預設 Branch。
2. 所有變更只提交至該 Branch。
3. 開啟 Draft Pull Request，先保留審閱狀態。
4. PR 說明必須列出公開資訊檢查、驗證結果與發布影響。
5. 等待 CI 完成並檢查完整 diff。
6. 未取得當次明確批准前，不得標記 Ready、Merge、Publish、Force Push、改寫 Default Branch 或刪除 Branch。
7. Merge 前再次檢查最終 diff 與 Commit 清單。

## 發現資訊暴露時

1. 立即停止後續寫入。
2. 回報受影響的 Branch、Commit、檔案與 Pull Request。
3. 不得宣稱後續覆蓋或刪檔已清除舊 Commit 或 PR diff。
4. 等待 Repository 擁有者決定 Reset、歷史清理或 GitHub Support 等處理方式。
