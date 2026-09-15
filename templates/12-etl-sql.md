# ETL SQL 脚本规范 — 精简模板

## 脚本头部注释
```sql
-- ============================================
-- ETL 脚本: {layer}_{target_table}
-- 引擎: {target_engine}
-- 抽取策略: {extraction_type}
-- 生成时间: {timestamp}
-- ============================================
```

## ODS 层（源数据镜像 + 轻度清洗）
```sql
-- Step 1: 抽取
INSERT OVERWRITE TABLE ods_xxx PARTITION (dt='${bizdate}')
SELECT *, '${bizdate}' AS etl_date, CURRENT_TIMESTAMP AS etl_timestamp
FROM src_db.xxx WHERE dt = '${bizdate}';

-- Step 2: 轻度清洗（string_normalize / format_normalize）
-- 具体规则从 cleaning_rules.yaml 读取
```

## DWD 层（重度清洗 + 转换 + 拒绝数据落库）
```sql
-- Step 3: 转换
INSERT OVERWRITE TABLE dwd_xxx PARTITION (dt='${bizdate}')
WITH dedup AS (
    SELECT *, ROW_NUMBER() OVER(PARTITION BY pk ORDER BY update_time DESC) AS rn
    FROM ods_xxx WHERE dt='${bizdate}'
)
SELECT {mappings_from_mapping_doc}
FROM dedup WHERE rn = 1;

-- Step 4: 拒绝数据落库
INSERT OVERWRITE TABLE dw_reject_records PARTITION (dt='${bizdate}')
SELECT ... FROM (
    SELECT 'pk' AS field, pk AS val, 'deduplication' AS rule
    FROM ods_xxx WHERE pk IS NULL
) rejects;
```

## 清洗集成点
- cleaning_rules.yaml 驱动
- 每次清洗写入 cleaning_audit.log
- REJECT 数据同时落 dw_reject_records 表
