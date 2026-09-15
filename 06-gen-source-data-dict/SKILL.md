---
name: gen-source-data-dict
description: |
  生成《源端数据字典》— 描述源系统的表结构、字段定义、值域分布、数据特性（有效性/完全性/一致性），是 ETL 设计的输入基础。
  
  触发条件：用户提到「源端数据字典」「数据源调研」「字段代码及值域」「数据特性分析」「source data dictionary」时触发。
  
  适用阶段：Phase 7 数据源分析（也可独立运行）
  
  绑定模板：
  - 数据源结构调查报告@BBB-CCC 102 20060823.xls
  - 表字段代码及值域分析@BBB-CCC 102 20060823.xls
  - 数据特性分析@BBB-CCC 102 20060823.xls
  - 系统环境调查报告@BBB-CCC 102 20061106.doc
  
  输入不足处理：
  - 若未提供源系统清单，输出数据源调研框架
  - 若未提供表结构，自动生成表骨架 + 标注「待补充字段」
  - 若未提供值域分布，标注「需抽取样本分析」
  - 严禁编造字段含义、字段类型、值域分布
version: 1.0.0
category: data-source-analysis
template_bound:
  - "templates/06-source-data-dict.yaml"
related_skills:
  - gen-data-quality-report
  - gen-etl-mapping
  - gen-etl-sql
---

# 生成源端数据字典 (Source Data Dictionary Generator)

## 触发词

`源端数据字典`, `数据源调研`, `字段代码及值域`, `数据特性分析`, `source data dictionary`, `data source survey`, `字段值域分析`, `代码表`

---

## 模板绑定

---

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 06-source-data-dict.yaml | `templates/06-source-data-dict.yaml` | 参考/规范 |

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `source_systems` | list | 源系统清单（如 CRM / ERP / SCM）|

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `table_list` | list | 表清单（系统名 -> 表名列表）|
| `table_structures` | dict | 表结构（表名 -> 字段定义列表）|
| `value_distribution` | dict | 值域分布（表名.字段名 -> 分布数据）|
| `code_tables` | dict | 代码表（代码 -> 含义映射）|
| `data_quality_metrics` | dict | 数据质量指标（完全率/有效率/一致性）|
| `data_volume` | dict | 数据规模（表名 -> 行数/日增量）|
| `extraction_method` | dict | 抽取方式（全量/增量/CDC/Sqoop/Flume）|
| `environment_info` | dict | 系统环境（DB 类型、版本、网络）|

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `source_data_dict_md` | Markdown | 源端数据字典主文档 |
| `value_distribution_table` | Markdown | 值域分布表 |
| `data_characteristics_report` | Markdown | 数据特性分析报告 |
| `outstanding_items` | list | 待补充/待确认项 |

---

## 自动执行步骤

1. **识别源系统清单** — 收集所有需分析的源系统
2. **梳理表清单** — 列出每个系统的关键表
3. **提取表结构** — 字段名、类型、长度、是否主键、是否可空
4. **分析值域分布** — 抽取样本，统计值域、枚举值、NULL 率
5. **整理代码表** — 汇总所有代码字段及代码含义
6. **评估数据质量** — 5 维度评估（完全性/有效性/一致性/唯一性/及时性）
7. **记录数据规模** — 总行数、日增量、峰值 QPS
8. **标注采集方式** — 全量/增量/CDC，离线/实时
9. **输出待确认项** — 列出需源系统提供方确认的字段或规则

---

## 输出模板示例

### Markdown 格式（源端数据字典）

```markdown
# 源端数据字典 v1.0 — {项目名称}

> 数据采集日期：{采集日期}
> 数据源系统：{源系统清单}
> 责任人：{源系统 DBA/业务方}

---

## 1. 数据源总览

| 系统代号 | 系统名称 | DB 类型 | 版本 | 数据规模 | 抽取方式 | 责任方 |
|----------|----------|---------|------|----------|----------|--------|
| CRM | 客户关系系统 | MySQL | 5.7 | 1.2 亿行/日增 50 万 | Binlog CDC | DBA 张三 |
| ERP | 企业资源计划 | Oracle | 11g | 8000 万行/日增 10 万 | Sqoop 全量+增量 | DBA 李四 |
| ... | ... | ... | ... | ... | ... | ... |

## 2. 表清单（按系统分组）

### 2.1 CRM 系统
- ods_crm_customer（客户主档）
- ods_crm_order（订单表）
- ods_crm_product（商品表）
- ods_crm_order_item（订单明细）

### 2.2 ERP 系统
- ods_erp_finance（财务凭证）
- ods_erp_inventory（库存表）

## 3. 表结构详解（示例：ods_crm_order）

| 序号 | 字段名 | 字段描述 | 类型 | 长度 | 主键 | 可空 | 默认值 | 备注 |
|------|--------|----------|------|------|------|------|--------|------|
| 1 | order_id | 订单号 | VARCHAR | 32 | ✓ | ✗ | — | 业务主键 |
| 2 | user_id | 用户 ID | BIGINT | 20 | ✗ | ✗ | — | |
| 3 | order_amount | 订单金额 | DECIMAL | 18,2 | ✗ | ✓ | 0.00 | 含税 |
| 4 | order_status | 订单状态 | VARCHAR | 16 | ✗ | ✗ | — | 代码表见 §4.1 |
| 5 | create_time | 创建时间 | DATETIME | — | ✗ | ✗ | — | 增量键 |
| 6 | update_time | 更新时间 | DATETIME | — | ✗ | ✓ | — | |
| 7 | is_deleted | 是否删除 | TINYINT | 1 | ✗ | ✗ | 0 | 软删除标志 |

## 4. 代码表与值域

### 4.1 order_status 订单状态

| 代码 | 含义 | 出现频率（抽样）| 备注 |
|------|------|-----------------|------|
| PENDING | 待支付 | 5% | |
| PAID | 已支付 | 60% | |
| SHIPPED | 已发货 | 20% | |
| COMPLETED | 已完成 | 10% | |
| CANCELLED | 已取消 | 5% | |
| REFUNDED | 已退款 | <1% | |

### 4.2 其他代码表
- user_gender: M(男), F(女), U(未知)
- product_category: 参见商品类目代码表

## 5. 数据特性分析

### 5.1 完整性

| 表名 | 主键 NULL 率 | 关键字段 NULL 率 | 评估 |
|------|--------------|------------------|------|
| ods_crm_order | 0% | order_amount: 0.01% | 优 |
| ods_crm_customer | 0% | phone: 8% | 良 |

### 5.2 有效性

| 表名.字段 | 有效值范围 | 无效值数量 | 评估 |
|-----------|------------|------------|------|
| order_amount | 0 < x ≤ 999999 | 1234 (0.001%) | 优 |
| phone | 11 位手机号 | 5432 (0.5%) | 良 |

### 5.3 一致性

| 关系 | 不一致记录数 | 评估 |
|------|--------------|------|
| order.user_id = customer.user_id | 234 | 中（需清洗）|

## 6. 采集策略

| 表名 | 抽取方式 | 增量键 | 调度频率 | 备注 |
|------|----------|--------|----------|------|
| ods_crm_order | 增量 | update_time | 5 分钟 | Binlog 订阅 |
| ods_crm_customer | 全量 | — | 每日 | 数据量小 |
| ods_erp_finance | 增量 | etl_time | 每日 | Sqoop 抽取 |

## 7. 待确认项

- ⚠️ `order_status` 中 `REFUNDED` 状态与 `CANCELLED` 的业务区分需业务方确认
- ⚠️ `order_amount` 是否含税需业务方确认
- ⚠️ `is_deleted=1` 的订单是否需要进入 ODS 层
```

---

## 数据特性分析 5 维度

| 维度 | 含义 | 检查方法 |
|------|------|----------|
| **完整性** | 字段值是否存在 | 统计 NULL/空字符串占比 |
| **有效性** | 字段值是否符合业务规则 | 正则、范围、枚举检查 |
| **一致性** | 跨表/跨系统关联是否一致 | 外键关联、引用一致性 |
| **唯一性** | 主键/唯一键是否重复 | COUNT(DISTINCT) vs COUNT(*) |
| **及时性** | 数据更新是否及时 | 时间戳分布、延迟统计 |

---

## 抽取策略判定原则

| 场景 | 推荐策略 | 原因 |
|------|----------|------|
| 数据量小（< 1000 万行）| 全量 | 实现简单，无需处理增量合并 |
| 数据量大 + 无更新时间戳 | 全量 | 无法识别增量 |
| 数据量大 + 有 update_time | 增量 | 减少 I/O |
| 实时性要求高 | CDC（Binlog）| 实时同步 |
| 财务/审计类 | 全量 + 增量双写 | 防止丢数 |

---

## Input Validation — 输入不足处理

### 情况 1: 未提供源系统清单
**处理**: 输出数据源调研框架

```markdown
# 源系统调研框架

请提供以下信息：

1. **源系统清单**
   - 系统名称
   - 系统代号
   - DB 类型与版本
   - 责任 DBA/业务方

2. **调研范围**
   - 关键业务表清单
   - 抽取的优先级
   - 同步的实时性要求
```

### 情况 2: 未提供表结构
**处理**: 生成表骨架

```markdown
| 序号 | 字段名 | 字段描述 | 类型 | 长度 | 主键 | 可空 | 备注 |
|------|--------|----------|------|------|------|------|------|
| 1 | 【待补充】 | — | — | — | — | — | |
```

### 情况 3: 未提供值域分布
**处理**: 标注「需抽取样本分析」

```markdown
⚠️ 未提供值域分布数据。

请执行：
1. 从源系统抽取 10000 条样本
2. 运行 `SELECT field, COUNT(*) FROM table GROUP BY field`
3. 补充到本字典
```

### 情况 4: 未提供数据质量评估
**处理**: 标注「待评估」并提示评估方法

```markdown
⚠️ 建议使用 `gen-data-quality-report` skill 完成质量评估
```

---

## 禁止编造

- ❌ 表/字段名（必须用户提供或从源系统 DDL 提取）
- ❌ 字段类型与长度
- ❌ 业务含义（"order_status=PAID 是什么意思"）
- ❌ 值域分布（"PAID 占 60%"）
- ❌ 代码表内容（"01=男, 02=女"）
- ❌ 数据量估算（"日增 50 万"）

---

## 关键规范

### 表/字段命名规范

| 层级 | 命名规则 | 示例 |
|------|----------|------|
| 源表 | `ods_{系统代号}_{表名}` | `ods_crm_order` |
| 字段 | 沿用源系统原始命名 | `order_id` |
| 注释 | 必填，使用业务术语 | `订单号（业务唯一）` |

### 字段类型映射（异构源 → 数仓）

| 源类型 | Hive 类型 | 备注 |
|--------|-----------|------|
| MySQL `INT` | `BIGINT` | 统一为 BIGINT |
| MySQL `VARCHAR(n)` | `STRING` | 取消长度限制 |
| MySQL `DATETIME` | `TIMESTAMP` | |
| MySQL `DECIMAL(p,s)` | `DECIMAL(p,s)` | 保留精度 |
| Oracle `NUMBER` | `DECIMAL` | 转换 |
| Oracle `DATE` | `TIMESTAMP` | |

---

## 示例对话

```
用户: "CRM 系统有 4 张表需要字典，订单/客户/商品/订单明细"
助手: "我需要以下信息：

必需：
1. 4 张表的 DDL 或字段列表
2. CRM 数据库类型

可选（推荐提供）：
3. 各表的行数与日增量
4. 关键字段的代码表
5. 数据质量评估结果
"
```

```
用户: "DDL 在 ddl/crm_schema.sql，MySQL 5.7"
助手: "正在解析 DDL 并生成源端数据字典..."
```

---

## 关联 Skill

- **gen-data-quality-report** — 后置：基于本字典进行数据质量评估
- **gen-etl-mapping** — 后置：基于字段含义做映射
- **gen-etl-sql** — 后置：基于字段类型生成 ETL 代码

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

- [ ] 所有源系统已识别
- [ ] 所有关键表已列出
- [ ] 表结构完整（字段名/类型/长度/主键/可空）
- [ ] 代码表完整且有业务含义
- [ ] 值域分布基于真实样本
- [ ] 数据质量 5 维度已评估
- [ ] 抽取策略已明确（全量/增量/CDC）
- [ ] 责任方已明确
- [ ] 待确认项已列出
