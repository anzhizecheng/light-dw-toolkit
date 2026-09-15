---
name: gen-data-cleaning-rules
description: |
  生成「数据清洗规则文档」(cleaning_rules.yaml) — 基于源端数据字典 (gen-source-data-dict)、数据质量评估报告 (gen-data-quality-report)、数据标准文档 (Excel)，自动生成字段级清洗规则，包括：值修正（trim/大小写转换/格式归一）、值域裁剪（枚举/数值范围/日期范围）、缺失值处理（默认值/拒绝/插值）、异常值检测（基于规则/基于统计）、主键去重、拒绝数据落入 dw_reject_records 表。

  触发条件：用户提到「数据清洗」「cleaning rules」「数据标准化」「数据修正」「拒绝数据」「数据质量规则」「清洗规则」「reject records」「value normalization」「缺失值处理」时触发。

  适用阶段：Phase 9 ETL 设计（在 gen-etl-mapping 之后、gen-etl-sql 之前）

  关键定位 — 这是 ETL 设计链路的「清洗规则源」：
  - gen-etl-mapping: 字段映射（结构）
  - **gen-data-cleaning-rules: 清洗规则（行为）** ← 本 skill
  - gen-etl-sql: 集成 cleaning_rules → 在 ETL 中执行清洗
  - gen-etl-workflow: 在 DAG 中加入清洗节点
  - gen-etl-unit-tests: 验证清洗后数据

  输入不足处理：
  - 若未提供数据标准文档，标注「待补充」
  - 若未提供数据质量报告，使用数据字典推断默认规则
  - 若未指定拒绝数据存储，使用默认表名 dw_reject_records
  - 严禁编造实际业务数据值

version: 1.0.0
category: etl-design
template_bound:
  - "templates/10-cleaning-rules.yaml"
template_optional:
  []
related_skills:
  - gen-source-data-dict
  - gen-data-quality-report
  - gen-etl-mapping
  - gen-etl-sql
  - gen-etl-workflow
  - gen-etl-unit-tests
  - gen-project-config
---

# 生成数据清洗规则 (Data Cleaning Rules Generator)

> 💡 **核心思想**：传统 ETL 中清洗逻辑散落在 SQL 里，规则不透明、不可审计。本 skill 将清洗规则**显式化、声明化、可审计** —— 输出 `cleaning_rules.yaml`，被 `gen-etl-sql` 自动读取并生成带清洗逻辑的 ETL 代码。

---

## 触发词

`数据清洗`, `cleaning rules`, `数据标准化`, `数据修正`, `拒绝数据`, `数据质量规则`, `清洗规则`, `reject records`, `value normalization`, `缺失值处理`, `异常值检测`, `trim`, `case normalization`, `enum mapping`

---

## 为什么需要这个 skill？

| 没有此 skill | 有此 skill |
|--------------|-----------|
| 清洗逻辑散落在 SQL 注释中 | 集中维护 `cleaning_rules.yaml` |
| 拒绝数据不知道去哪了 | 统一落入 `dw_reject_records` 表，可审计 |
| 规则变更需修改多处 SQL | 改一处配置即可，所有 ETL 自动生效 |
| 清洗效果无法量化 | 输出 `cleaning_log.md` 记录每条规则的执行情况 |
| 新人看不懂清洗逻辑 | 规则文件可读、可评审、可版本管理 |

---

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `data_dict` | object | **来自 `gen-source-data-dict`** 的源端数据字典（必填） |
| `quality_report` | object | **来自 `gen-data-quality-report`** 的质量评估报告（必填） |
| `cleaning_rules_path` | path | 输出文件路径（默认 `${project_root}/09_cleaning_rules/cleaning_rules.yaml`） |

### 可选输入

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `data_standard_doc` | xlsx | 数据标准文档（企业级 / 行业级） | null |
| `reject_records_table` | string | 拒绝数据落入表名 | `dw_reject_records` |
| `value_correction_mode` | enum | 值修正模式：strict / lenient / strict_with_log | `strict_with_log` |
| `default_missing_strategy` | enum | 缺失值默认处理：reject / use_default / interpolate | `reject` |
| `outlier_detection_method` | enum | 异常值检测：rule_based / statistical / both | `rule_based` |
| `statistical_outlier_zscore` | float | 基于 Z-Score 的异常值阈值 | 3.0 |
| `audit_log_path` | path | 清洗审计日志路径 | `${project_root}/logs/cleaning_audit.log` |

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `cleaning_rules_yaml` | YAML | 字段级清洗规则（核心输出）|
| `cleaning_rules_doc_md` | Markdown | 清洗规则说明文档（人类可读）|
| `reject_records_schema_sql` | SQL | 拒绝数据表的 DDL |
| `cleaning_log_template` | Markdown | 清洗日志模板（执行时填充）|
| `rule_execution_examples` | SQL | 每个规则的执行样例 |
| `cleaning_summary_report` | Markdown | 清洗规则汇总报告（多少字段、多少规则）|

---

## 自动执行步骤

1. **读取 3 路输入** — `gen-source-data-dict` 的字段定义 + `gen-data-quality-report` 的问题清单 + `data_standard_doc`（如有）
2. **识别需要清洗的字段** — 通过质量报告中的问题字段（NULL、格式错误、值越界、重复）
3. **自动推导规则** — 按规则优先级生成（见下文）
4. **人工补全关键规则** — 对关键业务字段（如金额、状态、主键）需要业务方确认
5. **生成 `cleaning_rules.yaml`** — 声明式规则
6. **生成 `reject_records_schema.sql`** — 拒绝数据表 DDL
7. **生成审计日志模板** — 清洗执行时的日志格式

---

## 清洗规则类型

| 类型 | 英文 | 说明 | 示例 |
|------|------|------|------|
| **1. 字符串处理** | `string_normalize` | trim / 大小写 / 去除特殊字符 | `" ABC "` → `"abc"` |
| **2. 格式归一** | `format_normalize` | 日期 / 电话 / 身份证格式 | `"2026/6/23"` → `"2026-06-23"` |
| **3. 枚举映射** | `enum_mapping` | 异常值 → 标准枚举 | `"M"`/`"男"` → `"male"` |
| **4. 数值裁剪** | `value_clamp` | 限定值域范围 | `amount > 0` 否则 reject |
| **5. 缺失值处理** | `missing_value` | 默认值 / 拒绝 / 插值 | `NULL` → `"unknown"` |
| **6. 异常值检测** | `outlier_detection` | 规则 / 统计 | `Z-Score > 3` → reject |
| **7. 主键去重** | `deduplication` | 重复主键处理策略 | `keep_first` / `keep_last` / `reject_all` |
| **8. 跨表一致性** | `cross_table_check` | 字段必须在某表存在 | `region_id IN dim_region` |
| **9. 业务规则** | `business_rule` | 自定义表达式 | `total = price × qty` |
| **10. 脱敏** | `masking` | 敏感字段脱敏 | `130****1234` |

---

## `cleaning_rules.yaml` 模板

```yaml
# ============================================================================
# 数据清洗规则 — Project: ${project_name}
# Generated: ${generate_timestamp}
# Generated-by: gen-data-cleaning-rules v1.0.0
# ============================================================================

# ---------- 全局配置 ----------
global:
  reject_table: dw_reject_records
  value_correction_mode: strict_with_log
  default_missing_strategy: reject
  outlier_detection_method: rule_based
  statistical_outlier_zscore: 3.0
  audit_log: ${project_root}/logs/cleaning_audit.log
  fail_fast: false                      # 任一规则失败是否立即停止

# ---------- 源表 → 目标表 ----------
tables:
  - source_table: source_db.orders
    target_table: ods_orders
    layer: ODS
    primary_key: order_id
    cleaning_rules:
      # ----- 规则 1: 主键去重 -----
      - field: order_id
        type: deduplication
        strategy: keep_first
        reject_if: not_unique
      
      # ----- 规则 2: 字符串处理 -----
      - field: customer_name
        type: string_normalize
        operations:
          - trim
          - lower
        reject_if: empty_after_trim
      
      # ----- 规则 3: 格式归一 -----
      - field: order_date
        type: format_normalize
        target_format: "yyyy-MM-dd"
        source_formats: ["yyyy/MM/dd", "yyyy.MM.dd", "yyyyMMdd"]
        reject_if: parse_failed
      
      # ----- 规则 4: 枚举映射 -----
      - field: status
        type: enum_mapping
        mapping:
          "0": "cancelled"
          "1": "paid"
          "2": "shipped"
          "paid": "paid"
          "Paid": "paid"
        allowed_values: ["cancelled", "paid", "shipped", "pending", "refunded"]
        reject_if: not_in_allowed_values
      
      # ----- 规则 5: 数值裁剪 -----
      - field: order_amount
        type: value_clamp
        min: 0
        max: 9999999.99
        reject_if: out_of_range
        reject_if: null
      
      # ----- 规则 6: 缺失值处理 -----
      - field: region_id
        type: missing_value
        strategy: reject
        reject_if: null
      
      # ----- 规则 7: 异常值检测 -----
      - field: order_amount
        type: outlier_detection
        method: statistical
        algorithm: zscore
        threshold: 3.0
        action: reject
      
      # ----- 规则 8: 跨表一致性 -----
      - field: region_id
        type: cross_table_check
        reference_table: dim_region
        reference_key: region_id
        reject_if: not_in_reference
      
      # ----- 规则 9: 业务规则 -----
      - field: total_amount
        type: business_rule
        expression: "total_amount = price * quantity - discount"
        reject_if: violated
      
      # ----- 规则 10: 脱敏 -----
      - field: customer_phone
        type: masking
        algorithm: middle_mask
        keep_prefix: 3
        keep_suffix: 4
        mask_char: "*"
```

---

## 拒绝数据表 DDL 示例

```sql
-- 拒绝数据统一落入此表
CREATE TABLE IF NOT EXISTS dw_reject_records (
    reject_id           STRING          COMMENT '拒绝记录唯一 ID (UUID)',
    skill_name          STRING          COMMENT '产生拒绝的 skill 名',
    source_table        STRING          COMMENT '源表名',
    target_table        STRING          COMMENT '目标表名',
    bizdate             STRING          COMMENT '业务日期 (yyyy-MM-dd)',
    layer               STRING          COMMENT '层级 (ODS/DWD/DWS/ADS)',
    field_name          STRING          COMMENT '被拒绝的字段名',
    field_value         STRING          COMMENT '被拒绝的字段值',
    reject_rule_type    STRING          COMMENT '规则类型 (deduplication/format_normalize/...)',
    reject_rule_name    STRING          COMMENT '具体规则名',
    reject_reason       STRING          COMMENT '拒绝原因（人类可读）',
    full_row            STRING          COMMENT '完整源行 (JSON 格式)',
    rejected_at         TIMESTAMP       COMMENT '拒绝时间',
    resolved            BOOLEAN         COMMENT '是否已处理 (false=待处理)',
    resolved_at         TIMESTAMP       COMMENT '处理时间',
    resolved_by         STRING          COMMENT '处理人',
    resolution_note     STRING          COMMENT '处理备注'
)
PARTITIONED BY (dt STRING)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');
```

---

## 清洗审计日志格式

```text
# cleaning_audit.log 行格式
[timestamp] [level] [source_table→target_table] [rule_type] [field] [action] [details]

# 示例
[2026-06-23T02:30:15.123Z] [INFO] [source_db.orders→ods_orders] [deduplication] [order_id] [REJECT] {reject_count: 12, sample: ["12345", "67890"]}
[2026-06-23T02:30:15.456Z] [INFO] [source_db.orders→ods_orders] [string_normalize] [customer_name] [CORRECT] {corrected_count: 234, examples: [{from: " ABC ", to: "abc"}]}
[2026-06-23T02:30:15.789Z] [INFO] [source_db.orders→ods_orders] [value_clamp] [order_amount] [REJECT] {reject_count: 3, examples: [{value: -100, reason: "out_of_range_min"}]}
[2026-06-23T02:30:16.012Z] [INFO] [source_db.orders→ods_orders] [format_normalize] [order_date] [REJECT] {reject_count: 5, examples: [{value: "2026/13/45", reason: "parse_failed"}]}
[2026-06-23T02:30:16.234Z] [WARN] [source_db.orders→ods_orders] [outlier_detection] [order_amount] [REJECT] {reject_count: 2, zscore_max: 5.7, examples: [{value: 9999999, reason: "zscore>3"}]}
[2026-06-23T02:30:16.456Z] [INFO] [source_db.orders→ods_orders] [SUMMARY] - Total processed: 100000, Corrected: 234, Rejected: 22, Pass: 99744
```

---

## 关键设计原则

### 1. 显式优于隐式

```yaml
# ✅ 正确 — 显式声明
- field: order_amount
  type: value_clamp
  min: 0
  max: 9999999.99
  reject_if: out_of_range

# ❌ 错误 — 隐藏在 SQL 中
WHERE order_amount >= 0 AND order_amount <= 9999999.99
```

### 2. 可审计性 (Auditability)

每条数据修正或拒绝都记录到 `cleaning_audit.log`，包括：
- 数据值修正（value correction）：原值 → 新值
- 拒绝数据记录（rejected records）：值、原因、源行

### 3. 规则版本管理

`cleaning_rules.yaml` 纳入 Git 版本管理，每次变更可追溯：
- 改了什么规则
- 谁改的
- 改的原因
- 影响范围（哪些表）

### 4. 规则可被 ETL SQL 自动消费

`gen-etl-sql` 读取 `cleaning_rules.yaml` → 生成带清洗逻辑的 SQL，**不需要人工重新翻译**。

---

## 10 大规则详解

### 1. 字符串处理 (`string_normalize`)

```yaml
- field: customer_name
  type: string_normalize
  operations:
    - trim                    # 去除首尾空格
    - lower                   # 转小写
    - remove_special_chars    # 去除特殊字符
  reject_if: empty_after_trim
```

生成的 SQL（Hive）:
```sql
CASE 
  WHEN LOWER(TRIM(customer_name)) = '' THEN NULL  -- 或 reject
  ELSE REGEXP_REPLACE(LOWER(TRIM(customer_name)), '[^a-z0-9一-龥]', '')
END AS customer_name
```

### 2. 格式归一 (`format_normalize`)

```yaml
- field: order_date
  type: format_normalize
  target_format: "yyyy-MM-dd"
  source_formats: ["yyyy/MM/dd", "yyyy.MM.dd", "yyyyMMdd"]
  reject_if: parse_failed
```

### 3. 枚举映射 (`enum_mapping`)

```yaml
- field: status
  type: enum_mapping
  mapping:
    "0": "cancelled"
    "1": "paid"
    "M": "male"
    "F": "female"
  allowed_values: ["cancelled", "paid", "shipped"]
  reject_if: not_in_allowed_values
```

### 4. 数值裁剪 (`value_clamp`)

```yaml
- field: order_amount
  type: value_clamp
  min: 0
  max: 9999999.99
  reject_if: out_of_range
  reject_if: null
```

### 5. 缺失值处理 (`missing_value`)

```yaml
- field: region_id
  type: missing_value
  strategy: reject     # reject / use_default / interpolate
  default_value: null  # 当 strategy=use_default
```

### 6. 异常值检测 (`outlier_detection`)

```yaml
- field: order_amount
  type: outlier_detection
  method: statistical  # rule_based / statistical / both
  algorithm: zscore    # zscore / iqr / percentile
  threshold: 3.0
  action: reject
```

### 7. 主键去重 (`deduplication`)

```yaml
- field: order_id
  type: deduplication
  strategy: keep_first  # keep_first / keep_last / reject_all / keep_max_field
  keep_max_field: order_time  # 当 strategy=keep_max_field
  reject_if: not_unique
```

### 8. 跨表一致性 (`cross_table_check`)

```yaml
- field: region_id
  type: cross_table_check
  reference_table: dim_region
  reference_key: region_id
  join_type: left_anti   # left_anti / inner
  reject_if: not_in_reference
```

### 9. 业务规则 (`business_rule`)

```yaml
- field: total_amount
  type: business_rule
  expression: "total_amount = price * quantity - discount"
  tolerance: 0.01       # 浮点容差
  reject_if: violated
```

### 10. 脱敏 (`masking`)

```yaml
- field: customer_phone
  type: masking
  algorithm: middle_mask
  keep_prefix: 3
  keep_suffix: 4
  mask_char: "*"
```

---

## 与其他 skill 的契约

### 上游（消费）

| Skill | 提供的输入 | 用途 |
|-------|------------|------|
| `gen-source-data-dict` | `data_dict` | 字段类型、源表结构 |
| `gen-data-quality-report` | `quality_report` | 问题字段清单（NULL 率、格式错误、值越界） |
| `data_standard_doc` (xlsx) | 标准枚举、值域 | 枚举映射、数值范围的依据 |
| `gen-project-config` | `cleaning_rules_path`、`audit_log_path`、`reject_records_table` | 输出路径与拒绝表名 |

### 下游（被消费）

| Skill | 读取的内容 | 用途 |
|-------|-----------|------|
| `gen-etl-sql` | `cleaning_rules_yaml` | 在 ETL 中嵌入清洗逻辑，生成修正/拒绝 SQL |
| `gen-etl-workflow` | `cleaning_rules_yaml` (DAG 节点) | 调度时按规则执行清洗 |
| `gen-etl-unit-tests` | `cleaning_rules_yaml` | 验证清洗后数据 |
| `gen-sit-scripts` | `reject_records_table` | 验证拒绝数据是否落入 |

---

## Input Validation — 输入不足处理

### 情况 1: 未提供数据标准文档
**处理**: 标注「使用源端数据字典推断」

```yaml
# ⚠️ 未提供 data_standard_doc，规则来源仅基于 data_dict + quality_report
# 建议补充：企业级数据标准文档（通常为 Excel）
# 精简模板: templates/10-cleaning-rules.yaml
```

### 情况 2: 未提供数据质量报告
**处理**: 使用通用默认规则（保守清洗）

```yaml
# ⚠️ 未提供 quality_report，使用通用默认规则
global:
  value_correction_mode: strict_with_log
  default_missing_strategy: reject
  default_rules:
    - all_string_fields: trim
    - all_date_fields: format_check
    - all_numeric_fields: non_negative
    - all_primary_keys: deduplication
```

### 情况 3: 数据字典与质量报告字段不匹配
**处理**: 以质量报告为主，缺失字段从数据字典推断

```
⚠️ 字段对齐问题:
- quality_report 中有 5 个字段在 data_dict 中找不到
- data_dict 中有 12 个字段在 quality_report 中未评估
处理: 使用 LEFT JOIN 策略，以 quality_report 为主
```

---

## 禁止编造

- ❌ 实际业务数据值（订单金额、客户名等）
- ❌ 字段的实际统计量（NULL 率、distinct 数）— 必须来自数据质量报告
- ❌ 实际业务规则表达式（除非用户明确提供）
- ❌ 拒绝数据内容（必须从实际 ETL 执行时生成）
- ❌ 数据标准文档中的枚举值（必须用户提供）

---

## 关联 Skill

- **gen-source-data-dict** (上游) — 提供字段定义
- **gen-data-quality-report** (上游) — 提供问题清单
- **gen-etl-mapping** (并行) — 字段映射
- **gen-etl-sql** (下游) — 消费清洗规则生成 SQL
- **gen-etl-workflow** (下游) — 调度清洗节点
- **gen-etl-unit-tests** (下游) — 验证清洗效果
- **gen-project-config** (基础设施) — 提供路径与配置

---

## 验证清单

- [ ] `cleaning_rules.yaml` 已生成且符合 YAML 规范
- [ ] 至少覆盖质量报告中标记的所有「问题字段」
- [ ] 每条规则都有 `type` 和明确的 `reject_if` 条件
- [ ] `reject_records_schema.sql` 已生成
- [ ] 清洗审计日志路径已配置
- [ ] 关键业务字段（金额、状态、主键）有清洗规则
- [ ] 跨表一致性规则有 `reference_table` 指向具体维表
- [ ] 业务规则有清晰的 `expression` 和容差
- [ ] 脱敏规则有明确的算法和保留位数
- [ ] 规则文件可被 `gen-etl-sql` 自动消费（结构兼容）
