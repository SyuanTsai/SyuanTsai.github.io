---
title: "SQL Server MERGE 語法筆記"
date: 2022-05-11
last_modified_at: 2026-08-31
categories: [database]
tags: [sql-server, merge, t-sql]
description: "使用 MERGE，依來源與目標資料的比對結果執行新增、更新或刪除。"
redirect_from:
  - /mssql/2022/05/11/sql-server-merge.html
---

需要將一批來源資料同步至目標表時，分別撰寫新增、更新與刪除敘述，容易讓比對條件散落在不同位置。

SQL Server 的 `MERGE` 可以根據來源表與目標表的比對結果，在同一個敘述中執行 `INSERT`、`UPDATE` 或 `DELETE`。[^microsoft-merge]

本文整理 `MERGE` 的基本語法、多欄位比對、條件更新與刪除限制，並補充哪些情況適合改用個別 DML 敘述。

## 基本語法

```sql
MERGE INTO #tmp1 AS target
USING #tmp2 AS source
ON target.Key1 = source.Key1

WHEN MATCHED THEN
    UPDATE SET
        target.Name = source.Name,
        target.Phone = source.Phone

WHEN NOT MATCHED BY TARGET THEN
    INSERT (Key1, Name, Phone)
    VALUES (source.Key1, source.Name, source.Phone);
```

其中：

- `MERGE INTO`：指定要新增、更新或刪除資料的目標表。
- `USING`：指定提供資料的來源表。
- `ON`：定義來源與目標資料的比對條件。
- `WHEN MATCHED`：找到相符資料時執行更新或刪除。
- `WHEN NOT MATCHED BY TARGET`：來源資料不存在於目標表時執行新增。

## 使用多個欄位比對

如果資料由多個 Key 組成，可以在 `ON` 條件中使用 `AND`：

```sql
ON target.Key1 = source.Key1
AND target.Key2 = source.Key2
```

## `WHEN MATCHED` 常見寫法

以下是不同使用情境，使用時應依需求選擇，不是全部同時放進同一個 `MERGE`。

### 找到資料就更新

```sql
WHEN MATCHED THEN
    UPDATE SET
        target.Name = source.Name,
        target.Phone = source.Phone
```

### 資料內容不同時才更新

```sql
WHEN MATCHED
     AND target.Name <> source.Name THEN
    UPDATE SET
        target.Name = source.Name,
        target.Phone = source.Phone
```

### 符合條件時刪除

```sql
WHEN MATCHED
     AND target.Name = ''
     AND source.Name = '' THEN
    DELETE
```

## 同時處理條件更新與刪除

SQL Server 允許兩個 `WHEN MATCHED`，但必須分別執行 `UPDATE` 與 `DELETE`：

```sql
MERGE INTO #tmp1 AS target
USING #tmp2 AS source
ON target.Key1 = source.Key1
AND target.Key2 = source.Key2

WHEN MATCHED
     AND target.Name = ''
     AND source.Name = '' THEN
    DELETE

WHEN MATCHED
     AND (
         target.Name <> source.Name
         OR target.Phone <> source.Phone
     ) THEN
    UPDATE SET
        target.Name = source.Name,
        target.Phone = source.Phone

WHEN NOT MATCHED BY TARGET THEN
    INSERT (Key1, Key2, Name, Phone)
    VALUES (
        source.Key1,
        source.Key2,
        source.Name,
        source.Phone
    );
```

## 語法限制

- 最多只能有兩個 `WHEN MATCHED`。
- 使用兩個時，一個必須是 `UPDATE`，另一個必須是 `DELETE`。
- 第一個 `WHEN MATCHED` 必須包含 `AND` 條件。
- 同一筆目標資料不能被多筆來源資料重複更新。
- `MERGE` 必須以分號 `;` 結束。[^microsoft-merge]

## 使用前的判斷

`MERGE` 適合來源與目標同時包含多種比對結果，需要在一個敘述中處理新增、更新或刪除的情境。若需求只是依另一張表<span class="keep-phrase">更新目標資料</span>，Microsoft 建議評估分開使用 `INSERT`、`UPDATE` 與 `DELETE`，可能具有更好的效能與擴充性。[^microsoft-merge]

實際使用前仍應確認來源比對鍵唯一、索引與執行計畫，並以符合正式資料量的案例驗證結果；使用 <span class="keep-phrase">queued updating replication</span> 時則不應使用 `MERGE`。[^microsoft-merge]

## 參考資料

[^microsoft-merge]: [MERGE (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/statements/merge-transact-sql?view=sql-server-ver17) — Microsoft Learn

1. 引用資料由系統自動產生
{:footnotes}

## 更新紀錄

| 日期 | 更新內容 |
| --- | --- |
| 2022-05-11 | 初版發布 |
| 2026-08-30 | 對齊正式文章範本，補充使用限制、適用判斷與官方文件引用 |
| 2026-08-31 | 修正中文短詞組與英文專有名詞的不自然斷行 |
{: .update-history}
