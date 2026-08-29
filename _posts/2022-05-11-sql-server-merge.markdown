---
layout: post
title: "SQL Server MERGE 語法筆記"
date: 2022-05-11
categories: [MSSQL]
description: "使用 MERGE，依來源與目標資料的比對結果執行新增、更新或刪除。"
---

`MERGE` 可以根據來源表與目標表的比對結果，在同一個敘述中執行 `INSERT`、`UPDATE` 或 `DELETE`。

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
- `MERGE` 必須以分號 `;` 結束。

參考：[Microsoft MERGE 官方文件](https://learn.microsoft.com/en-us/sql/t-sql/statements/merge-transact-sql)
