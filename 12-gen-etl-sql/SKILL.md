---
name: gen-etl-sql
description: |
  生成数仓各层 ETL 可执行 SQL 脚本（ODS/DWD/DWS/ADS），支持 Hive SQL / Spark SQL / MySQL / ClickHouse / Doris 多方言。

  触发条件：用户提到「ETL 代码」「ETL 脚本」「SQL 生成」「ods_load」「dwd_transform」「dws_aggregate」「ads_query」时触发。

  适用阶段：Phase 12 系统开发

  绑定模板：
  - templates/12-etl-sql.md

  输入不足处理：
  - 若未提供 PDM，无法生成目标表结构相关代码
  - 若未提供目标引擎方言，生成 ANSI SQL 兼容的伪 SQL
  - 若未提供 Mapping 文档，标注「需先完成 Mapping 设计」
  - 严禁编造字段转换逻辑

  上游依赖（契约式输入）：
  - gen-etl-mapping → mapping_doc_md / mapping_xlsx_structure：字段映射的核心输入
  - gen-ddl-scripts → ddl_scripts：源表/目标表结构
  - gen-data-quality-report → data_quality_metrics：清洗规则强度
  - gen-data-cleaning-rules → cleaning_rules_yaml：字段级清洗规则（v1.2 新增，必填）
  - gen-project-config → cleaning_rules_path / reject_records_table：清洗规则文件路径与拒绝数据表
version: 1.2.0
category: etl-development
template_bound:
  - "templates/12-etl-sql.md"
related_skills:
  - gen-etl-mapping
  - gen-ddl-scripts
  - gen-data-quality-report
  - gen-data-cleaning-rules
  - gen-etl-workflow
  - gen-etl-unit-tests
  - gen-project-config
---

# 生成 ETL SQL 脚本 (ETL SQL Generator)

## 触发词

`ETL 代码`, `ETL 脚本`, `SQL 生成`, `ods_load`, `dwd_transform`, `dws_aggregate`, `ads_query`, `ETL SQL`, `数据转换 SQL`

---

## 模板绑定

---

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 12-etl-sql.md | `templates/12-etl-sql.md` | 参考/规范 |

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `target_engine` | enum | 目标引擎：hive / spark / mysql / clickhouse / doris / flink |
| `layer` | enum | 目标层：ODS / DWD / DWS / ADS |
| `target_table` | string | 目标表名 |
| `source_tables` | list | 源表清单 |
| `mapping_doc` | object | **来自 `gen-etl-mapping`** 的字段映射（必填） |
| `cleaning_rules_yaml` | object | **来自 `gen-data-cleaning-rules`** 的字段级清洗规则（v1.2 必填）|

> ⚠️ **关键约束**：`mapping_doc` 是核心输入，必须由 `gen-etl-mapping` 生成。SQL 字段转换、JOIN 关系、清洗规则均来源于此。

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `mapping` | dict | 字段映射（从 `mapping_doc` 提取的字段级映射）|
| `ddl_scripts` | object | 来自 `gen-ddl-scripts` 的目标表 DDL |
| `data_quality_metrics` | object | 来自 `gen-data-quality-report` 的清洗规则 |
| `filter_conditions` | string | WHERE 条件 |
| `partition_strategy` | dict | 分区策略 |
| `extraction_type` | enum | full / incremental / cdc |
| `incremental_key` | string | 增量键字段名 |
| `business_keys` | list | 业务主键（用于去重）|

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `ods_load_sql` | SQL | ODS 层加载脚本 |
| `dwd_transform_sql` | SQL | DWD 层转换脚本 |
| `dws_aggregate_sql` | SQL | DWS 层聚合脚本 |
| `ads_query_sql` | SQL | ADS 层应用脚本 |
| `dirty_data_rules` | Markdown | 脏数据处理规则说明 |
| `cleaning_audit_sql` | SQL | **v1.2 新增** 清洗审计日志写入 SQL（含数据值修正、拒绝数据记录）|
| `cleaning_summary_log` | Markdown | **v1.2 新增** 清洗执行汇总日志（每次 ETL 跑完生成一份）|

---

## 数据清洗集成（v1.2 核心改造）

> 📋 本章节由 `gen-data-cleaning-rules` 驱动，详见 [`gen-data-cleaning-rules/SKILL.md`](data-pipeline/projects/light-dw-toolkit/gen-data-cleaning-rules/SKILL.md)

### 清洗在 ETL 中的位置

```text
源系统 → [Step 1: 抽取] → [Step 2: 清洗] → [Step 3: 转换] → [Step 4: 加载] → ODS/DWD/DWS/ADS
                                  ↑
                          cleaning_rules.yaml
                          (gen-data-cleaning-rules)
```

**清洗位置策略**:
| 层 | 清洗强度 | 原因 |
|----|----------|------|
| **ODS** | 轻度（仅类型转换 + 主键去重）| 保留原始数据，最大化可追溯 |
| **DWD** | 中度（值修正 + 格式归一 + 枚举映射）| 标准化后的明细层 |
| **DWS** | 重度（异常值检测 + 跨表一致性）| 汇总层需保证数据一致 |
| **ADS** | 轻度（脱敏 + 业务规则）| 应用层贴近业务 |

### 读取 cleaning_rules.yaml 并生成清洗 SQL

```sql
-- ============================================================
-- ETL 清洗段（DWD 层示例）
-- 输入: cleaning_rules.yaml
-- 输出: 清洗后的明细 + 拒绝数据落入 dw_reject_records
-- 审计: cleaning_audit.log（由 SkillLogger 写入）
-- ============================================================

-- Step 1: 抽取 + 轻度清洗（ODS 层）
INSERT OVERWRITE TABLE ods_orders_cleaned PARTITION (dt='${bizdate}')
SELECT 
    order_id,
    LOWER(TRIM(customer_name))              AS customer_name,  -- string_normalize
    REGEXP_REPLACE(order_date, '[/.]', '-') AS order_date,      -- format_normalize
    -- 枚举映射
    CASE status
        WHEN '0' THEN 'cancelled'
        WHEN '1' THEN 'paid'
        WHEN 'Paid' THEN 'paid'
        ELSE NULL  -- 未匹配 → 后续判定是否 reject
    END AS status,
    -- 数值裁剪
    CASE 
        WHEN order_amount < 0 OR order_amount > 9999999.99 THEN NULL
        ELSE order_amount
    END AS order_amount,
    region_id
FROM source_db.orders
WHERE dt = '${bizdate}';

-- Step 2: 重度清洗 + 拒绝数据落库（DWD 层）
INSERT OVERWRITE TABLE dwd_fact_sales PARTITION (dt='${bizdate}')
SELECT 
    order_id,
    customer_name,
    order_date,
    status,
    order_amount,
    region_id
FROM ods_orders_cleaned
WHERE dt = '${bizdate}'
  -- 拒绝 NULL 主键
  AND order_id IS NOT NULL
  -- 拒绝未映射的状态值
  AND status IS NOT NULL
  -- 拒绝异常的金额
  AND order_amount IS NOT NULL
  -- 拒绝未在 dim_region 的 region_id
  AND region_id IN (SELECT region_id FROM dim_region WHERE dt = '${bizdate}');

-- Step 3: 拒绝数据落库（同时记录到 dw_reject_records 和 cleaning_audit.log）
INSERT OVERWRITE TABLE dw_reject_records PARTITION (dt='${bizdate}')
SELECT 
    CONCAT('RJ-', UUID())                                       AS reject_id,
    'gen-etl-sql'                                               AS skill_name,
    'source_db.orders'                                          AS source_table,
    'dwd_fact_sales'                                            AS target_table,
    '${bizdate}'                                                AS bizdate,
    'DWD'                                                       AS layer,
    rule_field                                                  AS field_name,
    CAST(rule_value AS STRING)                                  AS field_value,
    rule_type                                                   AS reject_rule_type,
    rule_name                                                   AS reject_rule_name,
    rule_reason                                                 AS reject_reason,
    TO_JSON(NAMED_STRUCT('order_id', order_id, 'customer_name', customer_name, ...)) AS full_row,
    CURRENT_TIMESTAMP                                           AS rejected_at,
    FALSE                                                       AS resolved
FROM (
    -- 收集所有被规则拒绝的源行
    SELECT 'order_id' AS rule_field, order_id AS rule_value, 'deduplication' AS rule_type, 'pk_null' AS rule_name, '主键为空' AS rule_reason, * FROM ods_orders_cleaned WHERE order_id IS NULL
    UNION ALL
    SELECT 'status', status, 'enum_mapping', 'not_in_allowed', '状态值未在允许列表中', * FROM ods_orders_cleaned WHERE status IS NULL
    UNION ALL
    SELECT 'order_amount', CAST(order_amount AS STRING), 'value_clamp', 'out_of_range', '数值超出范围', * FROM ods_orders_cleaned WHERE order_amount IS NULL
) rejects
WHERE dt = '${bizdate}';
```

### 清洗审计日志写入（cleaning_audit.log）

每个清洗规则在执行时必须记录到 `cleaning_audit.log`：

```python
# SkillLogger 自动生成以下审计日志
# (详细 API 见 LOGGING-CONVENTION.md)

logger.cleaning_audit({
    "source_table": "source_db.orders",
    "target_table": "dwd_fact_sales",
    "rule_type": "string_normalize",
    "field": "customer_name",
    "action": "CORRECT",  # CORRECT / REJECT / PASS
    "corrected_count": 234,
    "examples": [
        {"from": " ABC ", "to": "abc"},
        {"from": "DEF\t", "to": "def"}
    ]
})
```

**写入 cleaning_audit.log 的内容**:
```text
[2026-06-23T02:30:15.456Z] [INFO] [source_db.orders→dwd_fact_sales] [string_normalize] [customer_name] [CORRECT] {corrected_count: 234, examples: [{from:" ABC ", to:"abc"}]}
[2026-06-23T02:30:15.789Z] [INFO] [source_db.orders→dwd_fact_sales] [value_clamp] [order_amount] [REJECT] {reject_count: 3, examples: [{value:-100, reason:"out_of_range_min"}]}
[2026-06-23T02:30:15.012Z] [INFO] [source_db.orders→dwd_fact_sales] [format_normalize] [order_date] [REJECT] {reject_count: 5, examples: [{value:"2026/13/45", reason:"parse_failed"}]}
[2026-06-23T02:30:16.234Z] [WARN] [source_db.orders→dwd_fact_sales] [outlier_detection] [order_amount] [REJECT] {reject_count: 2, zscore_max: 5.7}
[2026-06-23T02:30:16.456Z] [INFO] [source_db.orders→dwd_fact_sales] [SUMMARY] - Total processed: 100000, Corrected: 234, Rejected: 22, Pass: 99744
```

### 清洗汇总日志（cleaning_summary_log）

每次 ETL 完成后生成一份 Markdown 格式的汇总：

```markdown
# 清洗执行汇总日志 — dwd_fact_sales

**业务日期**: 2026-06-22
**执行时间**: 2026-06-23T02:30:15 ~ 02:30:16
**耗时**: 1.0 秒
**总处理行数**: 100,000

## 清洗结果统计

| 规则类型 | 字段 | 动作 | 数量 | 占比 |
|---------|------|------|------|------|
| string_normalize | customer_name | CORRECT | 234 | 0.23% |
| format_normalize | order_date | REJECT | 5 | 0.005% |
| value_clamp | order_amount | REJECT | 3 | 0.003% |
| enum_mapping | status | REJECT | 10 | 0.01% |
| outlier_detection | order_amount | REJECT | 2 | 0.002% |
| cross_table_check | region_id | REJECT | 2 | 0.002% |
| **TOTAL** | - | - | **256** | **0.26%** |

## 详细清洗明细

### string_normalize.customer_name (234 条修正)
| 原值 | 修正值 | 出现次数 |
|------|--------|---------|
| " ABC " | "abc" | 156 |
| "DEF\t" | "def" | 78 |

### value_clamp.order_amount (3 条拒绝)
| 值 | 原因 |
|----|------|
| -100 | out_of_range_min |
| 99999999.99 | out_of_range_max |
| 99999999.99 | out_of_range_max |

### format_normalize.order_date (5 条拒绝)
| 值 | 原因 |
|----|------|
| "2026/13/45" | parse_failed (月份越界) |
| "not_a_date" | parse_failed (非日期) |

## 拒绝数据去向

- **目标表**: dw_reject_records
- **拒绝总数**: 22 条
- **示例**:
  - order_id=12345, field=status, value="未知", reason=enum_not_mapped
  - order_id=67890, field=order_amount, value=-100, reason=out_of_range

## 下一步行动

- [ ] 通知业务方评估 22 条拒绝数据
- [ ] 修正源系统或调整清洗规则
- [ ] 重新跑 ETL 验证
```

### 与 gen-etl-workflow 协同

`gen-etl-workflow` 在 DAG 中按以下顺序调度：

```python
extract_task >> clean_task >> transform_task >> load_task >> audit_task
                                  ↑
                          读取 cleaning_rules.yaml
                          写入 cleaning_audit.log
                          拒绝数据落 dw_reject_records
```

---

## 各层代码结构

### ODS 层

```sql
-- ODS Load: 源数据原始镜像
-- 引擎: {target_engine}
-- 抽取策略: {extraction_type}

-- ========== 增量抽取 ==========
INSERT OVERWRITE TABLE ods_{source}_{table} PARTITION (dt='${bizdate}')
SELECT 
    *,
    -- 审计字段
    '${bizdate}' AS etl_date,
    CURRENT_TIMESTAMP AS etl_timestamp
FROM {source_db}.{source_table}
WHERE 1=1
{filter_conditions}
[AND update_time >= '${last_date}']  -- 增量条件
;
```

### DWD 层

```sql
-- DWD Transform: 清洗、转换、标准化
-- 引擎: {target_engine}
-- 来源映射: mapping_doc 来自 gen-etl-mapping
-- 加载策略: 待 gen-etl-mapping 中 dim_* 维表全部加载完成后执行

INSERT OVERWRITE TABLE dwd_{layer}_{table} PARTITION (dt='${bizdate}')
WITH source_data AS (
    SELECT * FROM ods_{source}_{table} WHERE dt = '${bizdate}'
),
dedup AS (
    -- 业务主键去重（来自 mapping_doc.business_keys）
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY {business_keys} 
            ORDER BY update_time DESC
        ) AS rn
    FROM source_data
),
cleaned AS (
    SELECT 
        -- 字段映射来自 mapping_doc（禁止编造）
        {field_mappings_from_mapping_doc},
        -- 维度键查找（来自 mapping_doc 中的 *_key 字段）
        u.user_key,
        p.product_key,
        d.date_key,
        -- 清洗规则（来自 data_quality_metrics）
        CASE WHEN {field} IS NULL THEN '{default}' ELSE {field} END AS {field},
        -- 字段合并
        CONCAT_WS('-', col_a, col_b) AS combined_col,
        -- 类型转换
        CAST(amount AS DECIMAL(18,2)) AS amount,
        -- 日期标准化
        TO_DATE(order_date, 'yyyy-MM-dd') AS order_date
    FROM dedup src
    LEFT JOIN dim_user u ON src.user_id = u.user_id AND u.is_current = 'Y'
    LEFT JOIN dim_product p ON src.product_id = p.product_id AND p.is_current = 'Y'
    LEFT JOIN dim_date d ON TO_DATE(src.order_date) = d.date_value
    WHERE rn = 1
)
SELECT * FROM cleaned;
```

### DWS 层

```sql
-- DWS Aggregate: 轻度/高度汇总
-- 引擎: {target_engine}

INSERT OVERWRITE TABLE dws_{subject}_{granularity} PARTITION (dt='${bizdate}')
SELECT 
    user_dk,
    COUNT(DISTINCT order_id) AS order_cnt_1d,
    SUM(order_amt) AS amt_sum_1d,
    COUNT(DISTINCT product_id) AS product_cnt_1d,
    MAX(order_amt) AS max_order_amt,
    MIN(order_amt) AS min_order_amt,
    '1d' AS granularity
FROM dwd_fact_sales
WHERE dt = '${bizdate}'
GROUP BY user_dk;
```

### ADS 层

```sql
-- ADS Query: 应用层报表
-- 引擎: {target_engine}

INSERT OVERWRITE TABLE ads_{report_name}
SELECT 
    region_id,
    region_name,
    sales_amt,
    order_cnt,
    user_cnt,
    -- 同环比
    sales_amt / NULLIF(lag_sales_amt, 0) - 1 AS sales_yoy_ratio,
    sales_amt / NULLIF(lag_7d_sales_amt, 0) - 1 AS sales_wow_ratio
FROM (
    SELECT 
        *,
        LAG(sales_amt, 365) OVER (PARTITION BY region_id ORDER BY dt) AS lag_sales_amt,
        LAG(sales_amt, 7) OVER (PARTITION BY region_id ORDER BY dt) AS lag_7d_sales_amt
    FROM dws_sales_by_region
) t
WHERE dt = '${bizdate}';
```

---

## 引擎方言适配

| 引擎 | 关键语法差异 |
|------|--------------|
| **Hive** | `INSERT OVERWRITE TABLE ... PARTITION`, `STORED AS ORC`, `LATERAL VIEW EXPLODE` |
| **Spark SQL** | 与 Hive 类似，但支持 `MERGE INTO` |
| **MySQL** | 不支持分区，使用 `INSERT INTO ... ON DUPLICATE KEY UPDATE` |
| **ClickHouse** | `INSERT INTO ... SELECT`, 使用 `ENGINE = MergeTree()` |
| **Doris** | `INSERT INTO ... SELECT`, 支持 `DUPLICATE KEY` |
| **Flink** | 流处理语义，使用 `INSERT INTO` 配合 watermark |

---

## Input Validation — 输入不足处理

### 情况 1: 未指定目标引擎
**处理**: 生成 ANSI SQL 兼容的伪 SQL，标注差异

```sql
-- ⚠️ 未指定目标引擎，以下为 ANSI SQL 兼容伪 SQL
-- 请根据目标引擎调整:
-- - Hive: 添加 PARTITIONED BY (dt STRING) STORED AS ORC
-- - MySQL: 删除 PARTITION 子句
-- - ClickHouse: 改用 ENGINE = MergeTree() PARTITION BY dt

INSERT INTO target_table
SELECT ... FROM source_table;
```

### 情况 2: 未提供 Mapping
**处理**: 生成代码框架，标注「待补充 Mapping」

```sql
INSERT INTO dwd_fact_xxx
SELECT 
    -- ⚠️ 待补充：源字段到目标字段的映射
    src.field1,
    src.field2,
    -- ...
FROM ods_xxx src;
```

### 情况 3: 未提供数据质量规则
**处理**: 标注「需根据实际数据质量调整」

```markdown
> ⚠️ 未提供数据质量规则，以下为通用模板：
> - NULL 值处理: COALESCE(field, default_value)
> - 去重: ROW_NUMBER() OVER (PARTITION BY pk ORDER BY ts DESC) = 1
> - 异常值过滤: field >= 0 AND field <= 999999
```

---

## 禁止编造

- ❌ 字段映射关系
- ❌ 业务主键组合
- ❌ 增量键字段名
- ❌ 业务规则（金额计算公式、状态过滤条件）
- ❌ 表/字段名（必须用户提供）

---

## 示例对话

```
用户: "生成 DWD 层订单表的 ETL 代码"
助手: "我需要以下信息：

必需：
1. 目标引擎（Hive / Spark / MySQL / ClickHouse）
2. 目标表名
3. 源表清单

可选：
4. 字段映射（推荐提供）
5. 增量策略（全量/增量/CDC）
6. 数据质量规则
7. 业务主键
"
```

```
用户: "Hive，DWD 层 dwd_fact_sales，源表是 ods_crm_order。Mapping 在 mapping.xlsx"
助手: "正在生成 Hive SQL 脚本..."
```

---

## 关联 Skill

- **gen-etl-mapping** - 前置：生成 Mapping 文档
- **gen-etl-workflow** - 后置：生成调度 DAG
- **gen-etl-unit-tests** - 后置：生成单元测试

---


## 日志机制

> 📋 详细规范见 [`LOGGING-CONVENTION.md`](data-pipeline/projects/light-dw-toolkit/LOGGING-CONVENTION.md)

本 skill 执行时遵循统一日志机制 v1.2：

### 日志路径查找

```yaml
1. 读取 project_config.yaml 中的 logging 节:
   - skill_execution_log: 所有 skill 执行的统一入口
   - error_log: 错误日志
2. 若 project_config.yaml 不存在 → 使用默认 ./logs/ 目录
3. 优先级: project_config > 环境变量 DW_PROJECT_CONFIG > 默认
```

### 必须记录的事件

| # | 事件 | 何时 | 字段 |
|---|------|------|------|
| 1 | **START** | skill 启动时 | 时间戳、skill 名、项目名、关键输入参数 |
| 2 | **PROGRESS** | 每完成 10% 进度 | 阶段描述、累计进度 |
| 3 | **END** | skill 主体逻辑完成 | 完成时间、耗时、输出物清单 |
| 4 | **REPORT** | END 之后立即 | 成功/部分/失败、警告数、错误数 |
| 5 | **ERROR** | 任何失败（写入 error.log） | 错误码（E0xx-E9xx）、错误消息、上下文 |

### 任务完成报告

完成后输出：

```markdown
## 任务完成报告 — {skill_name}

| 项目 | 值 |
|------|-----|
| 项目名 | {project.name} |
| Skill | {skill_name} v{version} |
| 启动时间 | {start_time ISO8601} |
| 完成时间 | {end_time ISO8601} |
| 耗时 | {duration_seconds} 秒 |
| 结果 | ✅ 成功 / ⚠️ 部分成功 / ❌ 失败 |
| 警告 | {warning_count} |
| 错误 | {error_count} |
```

### 与其他 skill 的日志协同

- 读取 `project_config.yaml` 的 `logging.skill_execution_log` 作为本 skill 的主日志
- 失败时同时写 `error.log`（与所有 skill 共享）
- ETL 类 skill 还会写 `etl_runtime.log`；质量类写 `quality_check.log`；清洗类写 `cleaning_audit.log`
- 如适用，将执行状态写回 `project_config.yaml` 的 `etl_status.tables`

---


## 验证清单

- [ ] SQL 可在目标引擎直接执行
- [ ] 分区字段正确
- [ ] 字段映射完整无遗漏
- [ ] 数据质量规则已应用
- [ ] 增量策略明确
- [ ] 审计字段已添加
- [ ] 业务主键用于去重
