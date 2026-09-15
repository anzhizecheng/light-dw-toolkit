---
name: gen-data-quality-report
description: |
  数据质量评估 — 基于源系统 DDL 和采样数据，生成数据质量评估报告，包含完整性、一致性、准确性、唯一性、时效性 5 维度评估。
  
  触发条件：用户提到「数据质量」「数据质量评估」「数据质量报告」「DQ 评估」「源数据检查」时触发。
  
  适用阶段：Phase 7 数据源分析
  
  绑定模板：
  - 数据源分析报告@BBB-CCC 103 20060823.doc
  - 数据特性性分析@BBB-CCC 103 20060823.xls
  - 字段代码及值域分析@BBB-CCC 103 20060823.xls
  - scripts/data_quality_check.sql
  
  输入不足处理：
  - 若未提供 DDL，无法生成字段级评估
  - 若未提供采样数据，标注「需要人工执行数据质量检查脚本」
  - 严禁编造数据质量指标
version: 1.0.0
category: data-quality
template_bound:
  - "templates/05-data-quality-report.yaml"
related_skills:
  - gen-source-data-dict
  - gen-etl-mapping
---

# 数据质量评估 (Data Quality Report Generator)

## 触发词

`数据质量`, `数据质量评估`, `数据质量报告`, `DQ 评估`, `源数据检查`, `data quality`, `DQ check`

---

## 模板绑定

---

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 05-data-quality-report.yaml | `templates/05-data-quality-report.yaml` | 参考/规范 |

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `source_systems` | list | 数据源系统列表 |
| `ddl_or_schema` | text | DDL 语句或表结构描述 |

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `sample_data` | file | 采样数据（CSV/Excel）|
| `check_thresholds` | dict | 自定义检查阈值 |
| `business_rules` | list | 业务规则（如"销售额不含税"）|

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `dq_checklist` | Markdown | 数据质量检查清单 |
| `dq_check_sql` | SQL | 数据质量检查脚本 |
| `dq_report` | Markdown | 数据质量评估报告 |
| `risk_summary` | list | 风险点摘要 |

---

## 评估维度

### 5 大维度

| 维度 | 说明 | 关键指标 |
|------|------|----------|
| **完整性 (Completeness)** | 必填字段是否有 NULL | NULL 率、记录数 |
| **一致性 (Consistency)** | 跨表/跨系统的关联键、字段值 | 外键覆盖率、格式一致性 |
| **准确性 (Accuracy)** | 字段值是否符合业务规则 | 值域偏离率、异常值比例 |
| **唯一性 (Uniqueness)** | 主键是否唯一 | 重复率 |
| **时效性 (Timeliness)** | 数据是否及时更新 | 延迟时间、缺失日期 |

---

## 自动执行步骤

1. **解析 DDL / 表结构**
2. **生成静态分析检查清单**
3. **生成可执行 SQL 脚本**
4. **等待用户执行并反馈结果**
5. **基于结果生成评估报告**

---

## 输出模板示例

### 1. 数据质量检查清单

```markdown
# 数据质量检查清单 — {source_system}

## 1. 表清单

| # | 表名 | 记录数 | 主键 | 数据量级 | 优先级 |
|---|------|--------|------|----------|--------|
| 1 | t_order | 1000万 | order_id | 大 | P0 |
| 2 | t_user | 500万 | user_id | 中 | P0 |
| 3 | t_product | 10万 | product_id | 小 | P1 |
| ... | ... | ... | ... | ... | ... |

## 2. 检查项

### 2.1 完整性检查
| 字段 | 表 | 是否必填 | 阈值 | 优先级 |
|------|-----|---------|------|--------|
| order_id | t_order | 是 | NULL率 < 0.1% | P0 |
| user_id | t_user | 是 | NULL率 < 0.1% | P0 |
| order_amt | t_order | 是 | NULL率 < 1% | P0 |
| ... | ... | ... | ... | ... |

### 2.2 一致性检查
| 字段 | 表 | 检查规则 | 优先级 |
|------|-----|---------|--------|
| user_id | t_order | 必须存在于 t_user | P0 |
| product_id | t_order | 必须存在于 t_product | P0 |
| region_code | t_order | 必须在地区字典中存在 | P1 |
| ... | ... | ... | ... |

### 2.3 准确性检查
| 字段 | 表 | 业务规则 | 优先级 |
|------|-----|---------|--------|
| order_amt | t_order | >= 0 | P0 |
| status | t_order | IN ('paid', 'pending', 'cancelled') | P0 |
| order_date | t_order | <= CURRENT_DATE | P0 |
| ... | ... | ... | ... |

### 2.4 唯一性检查
| 字段 | 表 | 是否主键 | 优先级 |
|------|-----|---------|--------|
| order_id | t_order | 是 | P0 |
| (order_id, product_id) | t_order_item | 联合主键 | P0 |
| ... | ... | ... | ... |

### 2.5 时效性检查
| 表 | 检查规则 | 优先级 |
|----|---------|--------|
| t_order | 每日 0:00 前应有昨日数据 | P0 |
| t_user | 实时更新 | P1 |
| ... | ... | ... |
```

### 2. 数据质量检查 SQL

```sql
-- ==========================================
-- 数据质量检查脚本
-- 数据源: {source_system}
-- 生成时间: {generated_at}
-- ==========================================

-- Check 1: 完整性 — 关键字段 NULL 率
SELECT 
    't_order.order_id' AS check_item,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) AS null_count,
    SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS null_rate,
    CASE 
        WHEN SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) * 1.0 / COUNT(*) < 0.001
        THEN 'PASS'
        ELSE 'FAIL'
    END AS status
FROM source_db.t_order;

-- Check 2: 一致性 — 外键覆盖率
SELECT 
    't_order.user_id 存在于 t_user' AS check_item,
    COUNT(*) AS total,
    SUM(CASE WHEN u.user_id IS NULL THEN 1 ELSE 0 END) AS orphaned,
    SUM(CASE WHEN u.user_id IS NULL THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS orphan_rate
FROM source_db.t_order o
LEFT JOIN source_db.t_user u ON o.user_id = u.user_id;

-- Check 3: 准确性 — 业务规则
SELECT 
    't_order.order_amt >= 0' AS check_item,
    COUNT(*) AS total,
    SUM(CASE WHEN order_amt < 0 THEN 1 ELSE 0 END) AS invalid_count
FROM source_db.t_order;

-- Check 4: 唯一性 — 主键
SELECT 
    order_id,
    COUNT(*) AS dup_count
FROM source_db.t_order
GROUP BY order_id
HAVING COUNT(*) > 1
LIMIT 100;

-- Check 5: 时效性 — 每日数据更新
SELECT 
    dt,
    COUNT(*) AS row_count
FROM source_db.t_order
WHERE dt >= DATE_SUB(CURRENT_DATE, 7)
GROUP BY dt
ORDER BY dt DESC;
```

### 3. 数据质量评估报告

```markdown
# 数据质量评估报告 — {source_system}

## 1. 评估概述
- 数据源: {source_system}
- 评估时间: {evaluation_date}
- 评估方法: 静态分析 + 动态检查（需人工执行 SQL）
- 整体评级: 【待执行】

## 2. 评估结果

### 2.1 完整性
- 整体评估: 【待执行】
- 高风险字段: 【待执行】
- 建议措施: ...

### 2.2 一致性
- 整体评估: 【待执行】
- 高风险关联: 【待执行】
- 建议措施: ...

### 2.3 准确性
- 整体评估: 【待执行】
- 异常字段: 【待执行】
- 建议措施: ...

### 2.4 唯一性
- 整体评估: 【待执行】
- 重复风险: 【待执行】
- 建议措施: ...

### 2.5 时效性
- 整体评估: 【待执行】
- 延迟情况: 【待执行】
- 建议措施: ...

## 3. 风险点摘要

| # | 风险 | 严重程度 | 建议措施 | 责任人 |
|---|------|----------|----------|--------|
| R1 | 主键 order_id 存在重复 | 高 | 通知源系统修复 | DBA |
| R2 | 字段 user_id NULL 率 5% | 中 | 源系统添加非空约束 | BA |
| ... | ... | ... | ... | ... |

## 4. 数据源准入建议
- [ ] 准入（数据质量符合要求）
- [ ] 有条件准入（修复指定问题后准入）
- [ ] 不准入（存在严重质量问题）

## 5. 后续 Action Items
- [ ] 通知源系统修复 R1
- [ ] 在 ETL 层添加脏数据处理规则
- [ ] 制定数据质量监控告警
```

---

## Input Validation — 输入不足处理

### 情况 1: 未提供 DDL
**处理**: 无法生成字段级评估

```
⚠️ 缺少 DDL 信息。

请提供以下任一：
1. CREATE TABLE 语句
2. 数据字典文件（CSV/Excel）
3. 表结构描述（字段名 + 类型 + 注释）

在收到 DDL 之前，我只能输出【数据质量检查框架】。
```

### 情况 2: 未提供采样数据
**处理**: 标注「待人工执行」

```markdown
> ⚠️ 静态分析已完成，动态数据质量检查需人工执行 data_quality_check.sql，
> 并将结果反馈回来以生成最终评估报告。
```

---

## 禁止编造

- ❌ 数据质量指标的具体数值（NULL 率、重复率等）
- ❌ 业务规则（如"金额必须 > 0"）
- ❌ 字段含义（无注释字段）

---

## 示例对话

```
用户: "评估一下 CRM 系统的数据质量"
助手: "我需要以下信息：

必需：
1. CRM 系统的 DDL（CREATE TABLE）
2. 主要业务表清单

可选：
3. 采样数据（CSV/Excel，可提高评估准确度）
4. 业务规则（如状态值域）
5. 自定义阈值

我可以先做静态分析，生成数据质量检查 SQL，由您执行后反馈结果。
"
```

---

## 关联 Skill

- **gen-source-data-dict** - 数据字典生成
- **gen-etl-mapping** - 评估结果用于制定清洗规则
- **gen-ddl-scripts** - 评估影响建模决策

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

- [ ] 所有主要表已包含
- [ ] 5 大维度都有检查项
- [ ] SQL 脚本可独立执行
- [ ] 风险点有明确建议
- [ ] 准入决策有依据
