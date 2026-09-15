---
name: gen-etl-unit-tests
description: |
  生成 ETL 单元测试脚本 — 行数校验、主键唯一性、空值率、数据类型、值域校验、跨表对账。

  触发条件：用户提到「单元测试」「ETL 测试」「data quality test」「行数校验」「主键校验」时触发。

  适用阶段：Phase 12 系统开发（单元测试环节）

  绑定模板：
  - templates/14-etl-unit-tests.sql

  输入不足处理：
  - 若未提供目标表 DDL，标注「需要 DDL 生成测试」
  - 若未提供预期行数，使用阈值（如「行数 > 0」）
  - 若未指定测试引擎，生成 ANSI SQL

  上游依赖（契约式输入）：
  - gen-etl-mapping → mapping_doc / business_keys：业务主键、字段映射
  - gen-ddl-scripts → ddl_scripts：目标表结构、主键、字段类型
  - gen-data-quality-report → data_quality_metrics：阈值（NULL 率、有效率）
  - gen-etl-sql → etl_sql_files：被测试的 ETL 脚本
  - gen-data-cleaning-rules → cleaning_rules_yaml（v1.2 新增）：验证清洗规则是否正确执行
version: 1.2.0
category: etl-testing
template_bound:
  - "templates/14-etl-unit-tests.sql"
related_skills:
  - gen-etl-mapping
  - gen-ddl-scripts
  - gen-data-quality-report
  - gen-data-cleaning-rules
  - gen-etl-sql
  - gen-etl-workflow
  - gen-sit-scripts
---

# 生成 ETL 单元测试 (ETL Unit Test Generator)

## 触发词

`单元测试`, `ETL 测试`, `data quality test`, `行数校验`, `主键校验`, `空值率检查`, `unittest`

---

## 模板绑定

---

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 14-etl-unit-tests.sql | `templates/14-etl-unit-tests.sql` | 参考/规范 |

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `target_table` | string | 目标表名 |
| `layer` | enum | 所属层：ODS / DWD / DWS / ADS |
| `ddl_scripts` | object | **来自 `gen-ddl-scripts`** 的目标表 DDL（必填）|
| `mapping_doc` | object | **来自 `gen-etl-mapping`** 的字段映射（必填，含 business_keys）|

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `data_quality_metrics` | object | 来自 `gen-data-quality-report` 的阈值 |
| `etl_sql_files` | object | 来自 `gen-etl-sql` 的 SQL 文件（用于交叉验证）|
| `primary_keys` | list | 主键字段列表（可从 DDL 推断）|
| `not_null_fields` | list | 必填字段列表（可从 DDL 推断）|
| `value_range_rules` | dict | 值域规则（字段 -> [min, max]）|
| `expected_row_count` | int | 预期行数 |
| `source_table` | string | 源表（用于对账，从 mapping_doc 推断）|
| `business_rules` | list | 业务规则 |
| `test_engine` | enum | 测试引擎：hive / spark / mysql / clickhouse |

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `unit_test_sql` | SQL | 单元测试脚本 |
| `test_report_template` | Markdown | 测试报告模板 |
| `check_rules` | Markdown | 校验规则说明 |

---

## 单元测试类型

### 1. 行数校验 (Row Count Check)

```sql
-- Test 1.1: 目标表行数 > 0
SELECT 
    'target_row_count' AS check_name,
    COUNT(*) AS actual_value,
    CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM {target_table}
WHERE dt = '${bizdate}';

-- Test 1.2: 源 vs 目标行数一致性
SELECT 
    'source_target_row_count_match' AS check_name,
    src.cnt AS source_count,
    tgt.cnt AS target_count,
    CASE WHEN src.cnt = tgt.cnt THEN 'PASS' ELSE 'FAIL' END AS status
FROM 
    (SELECT COUNT(*) AS cnt FROM {source_table} WHERE dt = '${bizdate}') src,
    (SELECT COUNT(*) AS cnt FROM {target_table} WHERE dt = '${bizdate}') tgt;

-- Test 1.3: 预期行数校验
SELECT 
    'expected_row_count' AS check_name,
    COUNT(*) AS actual_value,
    {expected_row_count} AS expected_value,
    CASE WHEN COUNT(*) = {expected_row_count} THEN 'PASS' ELSE 'FAIL' END AS status
FROM {target_table}
WHERE dt = '${bizdate}';
```

### 2. 主键唯一性 (Primary Key Uniqueness)

```sql
-- Test 2.1: 主键无重复
SELECT 
    pk_col,
    COUNT(*) AS dup_count,
    'FAIL' AS status
FROM {target_table}
WHERE dt = '${bizdate}'
GROUP BY pk_col
HAVING COUNT(*) > 1
LIMIT 100;

-- Test 2.2: 主键无 NULL
SELECT 
    'pk_null_check' AS check_name,
    COUNT(*) AS null_count,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM {target_table}
WHERE dt = '${bizdate}'
  AND pk_col IS NULL;
```

### 3. 空值率校验 (Null Rate Check)

```sql
-- Test 3.1: 必填字段 NULL 率
SELECT 
    field_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN field_name IS NULL THEN 1 ELSE 0 END) AS null_count,
    SUM(CASE WHEN field_name IS NULL THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS null_rate,
    threshold,
    CASE 
        WHEN SUM(CASE WHEN field_name IS NULL THEN 1 ELSE 0 END) * 1.0 / COUNT(*) <= threshold 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END AS status
FROM {target_table}
WHERE dt = '${bizdate}'
GROUP BY field_name, threshold;
```

### 4. 数据类型校验 (Data Type Validation)

```sql
-- Test 4.1: 数值字段无负数
SELECT 
    'amount_negative_check' AS check_name,
    COUNT(*) AS invalid_count,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM {target_table}
WHERE dt = '${bizdate}'
  AND amount_field < 0;

-- Test 4.2: 日期字段格式正确
SELECT 
    'date_format_check' AS check_name,
    COUNT(*) AS invalid_count,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM {target_table}
WHERE dt = '${bizdate}'
  AND date_field NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$';
```

### 5. 值域校验 (Value Range)

```sql
-- Test 5.1: 枚举值校验
SELECT 
    'enum_value_check' AS check_name,
    status,
    COUNT(*) AS cnt
FROM {target_table}
WHERE dt = '${bizdate}'
  AND status NOT IN ('paid', 'pending', 'cancelled')
GROUP BY status;

-- Test 5.2: 数值范围校验
SELECT 
    'value_range_check' AS check_name,
    COUNT(*) AS out_of_range_count,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM {target_table}
WHERE dt = '${bizdate}'
  AND (amount < 0 OR amount > 9999999);
```

### 6. 跨表对账 (Cross-Table Reconciliation)

```sql
-- Test 6.1: 汇总值与明细求和一致
SELECT 
    'dws_dwd_reconciliation' AS check_name,
    dws.total_amt AS dws_total,
    dwd.detail_sum AS dwd_sum,
    ABS(dws.total_amt - dwd.detail_sum) AS diff,
    CASE 
        WHEN ABS(dws.total_amt - dwd.detail_sum) < 0.01 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END AS status
FROM 
    (SELECT SUM(amt) AS total_amt FROM dws_summary_table WHERE dt = '${bizdate}') dws,
    (SELECT SUM(amt) AS detail_sum FROM dwd_fact_table WHERE dt = '${bizdate}') dwd;

-- Test 6.2: 源系统 vs 数仓
SELECT 
    'source_dw_reconciliation' AS check_name,
    src.amt AS source_total,
    dw.amt AS dw_total,
    ABS(src.amt - dw.amt) AS diff
FROM 
    (SELECT SUM(amount) AS amt FROM source_db.orders WHERE dt = '${bizdate}') src,
    (SELECT SUM(order_amt) AS amt FROM dwd_fact_sales WHERE dt = '${bizdate}') dw;
```

### 7. 业务规则校验 (Business Rule)

```sql
-- Test 7.1: 业务规则
-- 示例：销售额 = 订单金额 - 退款金额
SELECT 
    'sales_calculation_check' AS check_name,
    COUNT(*) AS invalid_count
FROM dwd_fact_sales f
LEFT JOIN dwd_fact_refund r ON f.order_id = r.order_id
WHERE f.dt = '${bizdate}'
  AND ABS(f.sale_amt - (f.order_amt - COALESCE(r.refund_amt, 0))) > 0.01;
```

---

## 测试报告模板

```markdown
# ETL 单元测试报告 — {target_table}

## 1. 测试基本信息
- 目标表: {target_table}
- 所属层: {layer}
- 测试日期: {test_date}
- 测试执行人: 【待补充】
- 业务日期: ${bizdate}

## 2. 测试结果总览

| # | 测试项 | 实际值 | 预期值 | 状态 | 备注 |
|---|--------|--------|--------|------|------|
| 1 | 行数校验 | {row_count} | {expected} | ✅/❌ | |
| 2 | 主键唯一性 | {dup_count} | 0 | ✅/❌ | |
| 3 | 主键非空 | {null_count} | 0 | ✅/❌ | |
| 4 | 必填字段 NULL 率 | {null_rate}% | < 5% | ✅/❌ | |
| 5 | 数值范围 | {invalid} | 0 | ✅/❌ | |
| 6 | 跨表对账 | {diff} | < 0.01 | ✅/❌ | |
| ... | ... | ... | ... | ... | |

## 3. 失败项详情

### 失败项 1: ...
- 失败原因: 
- 影响范围: 
- 修复方案: 
- 修复人: 
- 修复日期: 

## 4. 总体结论

- [ ] 通过（所有 P0 测试项 PASS）
- [ ] 有条件通过（部分 P1 失败，需修复后重测）
- [ ] 不通过（P0 失败）

## 5. 下一步
- [ ] 提交测试报告
- [ ] 通知开发人员修复
- [ ] 修复后重新执行
```

---

## Input Validation — 输入不足处理

### 情况 1: 未提供主键
**处理**: 标注「需要 DDL」

```
⚠️ 未提供主键字段。

请提供以下任一：
1. 主键字段列表（如 [order_id, tenant_id]）
2. 目标表 DDL（从 DDL 中自动提取主键）
```

### 情况 2: 未提供预期行数
**处理**: 使用阈值「行数 > 0」

```sql
-- 默认阈值: 行数 > 0
COUNT(*) > 0
```

### 情况 3: 未提供业务规则
**处理**: 跳过业务规则校验

```markdown
> ⚠️ 业务规则校验跳过（未提供业务规则）。
> 建议补充：
> - 业务计算公式
> - 数据约束（如金额 = 订单 - 退款）
> - 状态流转规则
```

---

## 引擎方言适配

| 引擎 | 关键差异 |
|------|----------|
| **Hive** | `REGEXP` 语法不同，需用 `RLIKE` |
| **Spark SQL** | 与 Hive 类似 |
| **MySQL** | 不支持 `REGEXP` 的某些高级用法 |
| **ClickHouse** | 使用 `match()` 函数 |

---

## 禁止编造

- ❌ 主键字段名
- ❌ 预期行数（不能编造具体数字）
- ❌ 业务规则
- ❌ NULL 率阈值

---

## 关联 Skill

- **gen-etl-sql** - 前置：被测 SQL
- **gen-etl-workflow** - 后置：在 DAG 中调度

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

- [ ] 测试脚本语法正确
- [ ] 所有 P0 测试项已覆盖
- [ ] 阈值合理（非 0 容差）
- [ ] 测试报告模板完整
- [ ] 失败项有明确修复建议
