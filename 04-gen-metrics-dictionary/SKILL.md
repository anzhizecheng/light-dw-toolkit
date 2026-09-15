---
name: gen-metrics-dictionary
description: |
  生成《指标体系字典》— 包含指标编码、名称、业务定义、计算公式、统计维度、时间粒度、更新频率、数据源、责任人。
  
  触发条件：用户提到「指标字典」「指标体系」「KPI 字典」「指标口径」「指标管理」时触发。
  
  适用阶段：Phase 3 系统需求（也可独立运行）
  
  绑定模板：
  - 指标维度需求分析汇总表@BBB-CCC 102 20131205.xls
  - KPI调研表格@BBB-CCC 102 20131205.xlsx
  
  输入不足处理：
  - 若未提供指标清单，输出指标框架模板
  - 若未提供计算公式，标注「待业务方确认」
  - 严禁编造指标定义
version: 1.0.0
category: requirements
template_bound:
  - "templates/04-metrics-dictionary.yaml"
related_skills:
  - gen-requirements-spec
  - gen-etl-mapping
---

# 生成指标体系字典 (Metrics Dictionary Generator)

## 触发词

`指标字典`, `指标体系`, `KPI 字典`, `指标口径`, `指标管理`, `metrics dictionary`, `metric definition`

---

## 模板绑定

---

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 04-metrics-dictionary.yaml | `templates/04-metrics-dictionary.yaml` | 参考/规范 |

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `metrics_list` | list | 指标清单（含名称）|

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `business_definitions` | dict | 业务定义（指标名 -> 业务定义）|
| `calculation_formulas` | dict | 计算公式（指标名 -> SQL 公式）|
| `dimensions` | dict | 统计维度（指标名 -> 维度列表）|
| `time_granularity` | dict | 时间粒度（指标名 -> 日/周/月/实时）|
| `update_frequency` | dict | 更新频率（指标名 -> T+1/实时）|
| `data_source_mapping` | dict | 数据源归属 |
| `owners` | dict | 责任人 |

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `metrics_dictionary_md` | Markdown | 指标字典主文档 |
| `metrics_summary` | dict | 指标统计（按主题域/优先级）|
| `outstanding_items` | list | 待确认项 |

---

## 自动执行步骤

1. **识别指标清单**
2. **填充用户提供的字段**
3. **对未提供的字段标注「待补充」**
4. **按主题域分组**
5. **输出 Excel 模板（如需要）**

---

## 输出模板示例

### Markdown 格式

```markdown
# 指标体系字典 v1.0

## 1. 指标统计概览
- 指标总数: 50
- 按主题域分布:
  - 销售: 15
  - 会员: 10
  - 商品: 12
  - 财务: 8
  - 其他: 5
- 按优先级分布:
  - P0: 20
  - P1: 20
  - P2: 10

## 2. 指标字典

### 2.1 销售主题域

| 编码 | 名称 | 业务定义 | 计算公式 | 维度 | 粒度 | 频率 | 数据源 | 责任人 | 状态 |
|------|------|----------|----------|------|------|------|--------|--------|------|
| MET_SALES_001 | 销售额 | 当日订单成交金额（不含税） | SUM(order_amount) WHERE status='paid' | 日期/地区/品类 | 日 | T+1 | CRM | 销售总监 | ✅ |
| MET_SALES_002 | 订单数 | 当日有效订单数 | COUNT(DISTINCT order_id) WHERE status='paid' | 日期/地区 | 日 | T+1 | CRM | 销售总监 | ✅ |
| MET_SALES_003 | 客单价 | 销售额/订单数 | MET_SALES_001 / MET_SALES_002 | 日期/地区 | 日 | T+1 | 计算 | 销售总监 | ✅ |
| MET_SALES_004 | 复购率 | 30天内重复购买用户占比 | COUNT(DISTINCT CASE WHEN buy_cnt>1 THEN user_id END) / COUNT(DISTINCT user_id) | 日期 | 日 | T+1 | CRM | 运营总监 | ⚠️ 待确认 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

### 2.2 会员主题域
...

### 2.3 商品主题域
...

## 3. 状态说明
- ✅ 完整（所有字段已确认）
- ⚠️ 待确认（部分字段待业务方确认）
- ❌ 缺失（关键字段缺失）

## 4. 指标计算公式规范

### 4.1 同环比公式
```sql
-- 同比（与去年同期对比）
(yesterday - same_day_last_year) / same_day_last_year

-- 环比（与上一周期对比）
(today - yesterday) / yesterday
```

### 4.2 累计公式
```sql
-- 月累计
SUM(sale_amt) WHERE dt BETWEEN month_start AND current_dt
```

### 4.3 比率类指标
- 比率统一保留 4 位小数
- 分母为 0 时显示为 "N/A" 而非 0
```

### Excel 格式输出（可选）

```markdown
📊 Excel 文件结构:
- Sheet 1: 指标字典主表
  - 列: 编码 | 名称 | 业务定义 | 计算公式 | 维度 | 粒度 | 频率 | 数据源 | 责任人 | 状态
- Sheet 2: 变更日志
- Sheet 3: 状态统计
```

---

## Input Validation — 输入不足处理

### 情况 1: 未提供业务定义
**处理**: 标注「待业务方确认」

```markdown
| 编码 | 名称 | 业务定义 | 状态 |
|------|------|----------|------|
| MET_001 | 销售额 | 【待业务方确认】 | ⚠️ |
```

### 情况 2: 未提供计算公式
**处理**: 输出指标框架 + 待补充项

```
⚠️ 缺少计算公式，这是指标字典的核心字段。
请提供每个指标的 SQL 表达式或文字描述。

示例：销售额 = SUM(order_amount) WHERE status='paid'
```

### 情况 3: 未提供数据源
**处理**: 标注「待调研」

```markdown
| 编码 | 名称 | 数据源 | 状态 |
|------|------|--------|------|
| MET_001 | 销售额 | 【待调研】 | ⚠️ |
```

---

## 禁止编造

- ❌ 业务定义（"销售额"是否含税/退单）
- ❌ 计算公式
- ❌ 维度（"日期/地区"是否实际可用）
- ❌ 数据源归属

---

## 关键规范

### 指标编码规则

```
MET_{主题域}_{序号}

示例:
- MET_SALES_001 = 销售主题域第 1 个指标
- MET_USER_015 = 会员主题域第 15 个指标
```

### 命名规范

| 类型 | 规则 | 示例 |
|------|------|------|
| 中文名 | 业务可读，≤20字 | 销售额（不含税）|
| 英文名 | snake_case | total_sales_amount |
| 计算公式 | 完整 SQL 表达式 | SUM(order_amount) WHERE status='paid' |

---

## 关联 Skill

- **gen-requirements-spec** - BRS 包含指标字典
- **gen-etl-mapping** - 指标字典驱动 Mapping 设计
- **gen-dimension-model** - 指标需要维度支持

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

- [ ] 所有指标有唯一编码
- [ ] 计算公式无歧义
- [ ] 同名指标口径一致
- [ ] 责任人已明确
- [ ] 数据源已确认或标注「待调研」
- [ ] 变更日志已建立
