---
name: gen-requirements-spec
description: |
  生成《业务需求规格说明书 (BRS)》和《需求详细分析》。基于用户提供的业务场景、报表清单、指标清单，输出标准化的 BRS 文档。
  
  触发条件：用户提到「需求分析」「业务需求」「BRS」「需求规格说明书」「需求文档」时触发。
  
  适用阶段：Phase 3 系统需求
  
  绑定模板：
  - 需求规格说明书@BBB-CCC 102 20060823.doc
  - 需求分析报告@BBB-CCC 102 20131205.doc
  - 需求详细分析@BBB-CCC 102 20131205.xls
  - 指标维度需求分析汇总表@BBB-CCC 102 20131205.xls
  
  输入不足处理：
  - 若未提供业务报表清单，输出待确认项框架
  - 若未提供指标计算公式，标注「待业务方确认」
  - 严禁编造业务口径
version: 1.0.0
category: requirements
template_bound:
  - "templates/03-requirements-spec.md"
related_skills:
  - gen-metrics-dictionary
  - gen-source-data-dict
---

# 生成需求规格说明书 (BRS Generator)

## 触发词

`需求分析`, `业务需求`, `BRS`, `需求规格说明书`, `需求文档`, `requirement specification`, `BRD`

---

## 模板绑定

---

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 03-requirements-spec.md | `templates/03-requirements-spec.md` | 参考/模板 |

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_name` | string | 项目名称 |
| `business_background` | text | 业务背景（为什么要建数仓）|
| `business_scope` | text | 业务范围（覆盖哪些业务线）|
| `report_list` | list | 业务报表/看板清单 |

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `metrics_list` | list | 指标清单（含计算公式）|
| `data_sources` | list | 数据源系统清单 |
| `non_functional_requirements` | dict | 非功能需求（性能/安全/合规）|
| `existing_issues` | text | 历史痛点 |

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `brs_document` | Markdown | BRS 主文档 |
| `metrics_dictionary` | Markdown | 指标体系字典 |
| `feasibility_report` | Markdown | 可行性评估报告（初稿）|
| `outstanding_items` | list | 待确认项清单 |

---

## 自动执行步骤

1. **基于模板生成 BRS 骨架**
2. **填充用户提供的信息**
3. **对未提供的字段生成「待确认」占位符**
4. **输出待办事项清单**

---

## 输出模板示例

```markdown
# 业务需求规格说明书 (BRS)
## 项目名称: {project_name}

## 1. 项目背景
{business_background}

## 2. 业务范围与边界
### 2.1 覆盖范围
{business_scope}

### 2.2 不在范围内
- ...

## 3. 业务报表/看板清单

| # | 报表名称 | 主题域 | 主要用途 | 使用频率 | 优先级 |
|---|----------|--------|----------|----------|--------|
| 1 | 销售日报 | 销售 | 监控当日销售 | 日 | P0 |
| 2 | 会员画像 | 会员 | 会员运营 | 实时 | P0 |
| ... | ... | ... | ... | ... | ... |

## 4. 数据源清单（初步）

| # | 系统 | 类型 | 主要业务表 | 数据量级 | 更新频率 |
|---|------|------|------------|----------|----------|
| 1 | CRM | MySQL | t_order, t_user | 千万级 | 实时 |
| 2 | ERP | Oracle | t_sale, t_inv | 亿级 | T+1 |
| ... | ... | ... | ... | ... | ... |

## 5. 指标体系（核心）

| 指标编码 | 指标名称 | 业务定义 | 计算公式 | 统计维度 | 时间粒度 | 责任人 |
|----------|----------|----------|----------|----------|----------|--------|
| MET_SALES_001 | 销售额 | 当日订单成交金额 | SUM(order_amount) WHERE status='paid' | 日期/地区/品类 | 日 | 销售总监 |
| ... | ... | ... | ... | ... | ... | ... |

## 6. 非功能需求

### 6.1 性能
- 报表查询响应时间: < 3 秒
- 并发查询数: 50
- 数据量级: 1-10 TB

### 6.2 安全
- 数据脱敏规则: ...
- 权限矩阵: ...

### 6.3 合规
- 法规要求: ...

## 7. 历史痛点
{existing_issues}

## 8. 验收标准
- [ ] 所有 P0 报表可正常产出
- [ ] 指标口径与业务方一致
- [ ] 性能满足第 6 节要求
```

---

## Input Validation — 输入不足处理

### 情况 1: 未提供业务报表清单
**处理**: 输出空表 + 待确认项

```markdown
## 3. 业务报表/看板清单

> ⚠️ 未提供报表清单，请按以下格式补充：

| # | 报表名称 | 主题域 | 主要用途 | 使用频率 | 优先级 |
|---|----------|--------|----------|----------|--------|
| 1 | 【待补充】 | 【待补充】 | 【待补充】 | 【待补充】 | 【待补充】 |
```

### 情况 2: 未提供指标计算公式
**处理**: 标注「待业务方确认」

```markdown
| 指标编码 | 指标名称 | 业务定义 | 计算公式 | 状态 |
|----------|----------|----------|----------|------|
| MET_001 | 销售额 | 当日订单成交金额 | 【待业务方确认】 | ⚠️ |
```

### 情况 3: 未提供数据源清单
**处理**: 标注「待调研」

```markdown
| # | 系统 | 类型 | 主要业务表 | 数据量级 | 更新频率 |
|---|------|------|------------|----------|----------|
| 1 | 【待调研】 | 【待调研】 | 【待调研】 | 【待调研】 | 【待调研】 |
```

---

## 禁止编造清单

- ❌ 指标计算公式
- ❌ 业务口径定义（含税/不含税、退单处理）
- ❌ 数据源归属（"来自 CRM 系统"）
- ❌ 性能阈值

---

## 示例对话

```
用户: "帮我写 BRS"
助手: "我需要以下信息：

必需：
1. 项目名称
2. 业务背景
3. 业务范围
4. 报表清单

可选：
5. 指标定义
6. 数据源清单
7. 性能要求
8. 现有痛点
"
```

```
用户: "项目叫电商数仓，业务是做电商的，要看销售、会员、商品分析"
助手: "正在生成 BRS 骨架...

⚠️ 缺少以下信息：
- 具体报表清单（需要业务方整理）
- 指标定义（建议先做 KPI 调研）
- 数据源清单（需要 IT 配合）

请补充后我可以继续完善文档。
"
```

---

## 关联 Skill

- **gen-metrics-dictionary** - 单独生成指标字典
- **gen-source-data-dict** - 数据源分析
- **gen-data-quality-report** - 数据质量评估

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

- [ ] 项目背景清晰
- [ ] 业务范围边界明确
- [ ] 报表清单含使用频率和优先级
- [ ] 指标计算公式无歧义
- [ ] 非功能需求量化
- [ ] 所有「待补充」项已标注
