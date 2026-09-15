> **ARCHIVE — 内部设计文档，仅供维护参考，不对外发布**
> 本文档记录 light dw toolkit v1.1→v2.0 重构方案的内部设计决策。
> 当前公开文档请以 [README.md](README.md) 为准。

# 数据仓库建设 — 功能型 Skill 重构方案

> 实施日期：2026-06-23
> 位置：`.agents/skills/light-dw-toolkit/`

---

## 背景

### 现有 skill 体系（data-warehouse-builder）

- 按 SOP Phase（A-G）切分：**7 个阶段型 skill**
- 优点：阶段拆分清晰，流程化
- 缺点：粒度粗、无法独立使用、模板绑定弱

### 用户的痛点

> "按照功能拆解为可单独使用的子 skill，比如'生成项目计划表'、'会议纪要'、'需求分析'、'数据质量评估'"
> "绑定模板 → 声明输入/输出映射"

---

## 重构方案

### 设计原则

| 原则 | 说明 |
|------|------|
| **可独立使用** | 每个 skill 不依赖其他 skill |
| **按功能切分** | 不按阶段切分，按"具体任务"切分 |
| **模板显式绑定** | frontmatter 中声明 template_bound |
| **IO 显式声明** | required_inputs / optional_inputs / outputs |
| **避免编造** | input validation + 禁止编造清单 |

### 18 个子 skill（按 SOP Phase 0→15 顺序）

| # | Skill | 功能 | 阶段 | 状态 |
|---|-------|------|------|------|
| 1 | **gen-project-config** | **v1.2 新增** 项目配置生成器（日志路径/目录/ETL 状态/增量时间点）| **0** 基础设施 | ✅ |
| 2 | gen-project-plan | AI 辅助项目主计划（WBS + AI 节省工时）| 1-2 | ✅ |
| 3 | gen-meeting-minutes | 会议纪要 + PPT 大纲 | 2, 5, 6, 8, 13 | ✅ |
| 4 | gen-requirements-spec | 业务需求规格说明书 | 3 | ✅ |
| 5 | gen-metrics-dictionary | 指标体系字典 | 3 | ✅ |
| 6 | gen-data-quality-report | 数据质量评估报告 | 7 | ✅ |
| 7 | gen-source-data-dict | 源端数据字典 | 7 | ✅ |
| 8 | gen-dimension-model | 维度模型（CDM/LDM）| 8 | ✅ |
| 9 | gen-ddl-scripts | 物理 DDL 脚本 | 8 | ✅ |
| 10 | gen-etl-mapping | ETL Mapping 文档 | 9 | ✅ |
| 11 | **gen-data-cleaning-rules** | **v1.2 新增** 数据清洗规则（10 大规则类型 + 拒绝数据落库 + 清洗审计日志）| **9** | ✅ |
| 12 | gen-test-cases | SIT/UAT 测试用例集 | 11/13 | ✅ |
| 13 | gen-etl-sql | ETL 可执行 SQL 脚本（含清洗段）| 12 | ✅ |
| 14 | gen-etl-workflow | ETL 调度 DAG（含 clean_task 节点）| 12 | ✅ |
| 15 | gen-etl-unit-tests | ETL 单元测试脚本（验证清洗后数据）| 12 | ✅ |
| 16 | gen-sit-scripts | SIT 系统集成测试（验证拒绝数据）| 13 | ✅ |
| 17 | gen-deploy-plan | 部署与上线方案 | 14 | ✅ |
| 18 | gen-user-manual | 用户操作手册 | 13/15 | ✅ |

> ✅ **18 个 skill 全部实现**，覆盖 SOP Phase 0-15 全部阶段（含基础设施）。
> **v1.2 重大升级**：
> - 新增 `gen-project-config`（Phase 0 基础设施，提供 `project_config.yaml` 给所有其他 skill 消费）
> - 新增 `gen-data-cleaning-rules`（Phase 9，定义 10 大清洗规则 + 拒绝数据 + 审计日志）
> - ETL 设计系列（gen-etl-sql / gen-etl-workflow / gen-etl-unit-tests / gen-sit-scripts）已升级 v1.2，集成 cleaning_rules
> - 所有 18 个 skill 统一添加「日志机制」章节，遵循 [`LOGGING-CONVENTION.md`](data-pipeline/projects/light-dw-toolkit/LOGGING-CONVENTION.md)

---

## Skill 标准结构

### Frontmatter（YAML）

```yaml
---
name: skill-name
description: |
  详细描述...
  触发条件：...
  适用阶段：...
  
  输入不足处理：
  - ...
version: 1.0.0
category: project-management
template_bound:
  - "templates/..."
related_skills:
  - other-skill-name
---
```

### 主体结构

1. **触发词** — 列出所有关键词
2. **模板绑定** — 表格列出绑定的模板及字段
3. **输入输出映射** — 必需/可选输入、输出物
4. **自动执行步骤** — 流程化描述
5. **输出模板示例** — Markdown 示例
6. **Input Validation** — 输入不足处理
7. **禁止编造清单** — AI 行为约束
8. **示例对话** — 用户使用示例
9. **关联 Skill** — 与其他 skill 的关系
10. **验证清单** — 输出质量检查项

---

## 模板绑定机制

### 三种绑定模式

| 模式 | 说明 | 示例 |
|------|------|------|
| **1. 模板作为输出格式参考** | Skill 输出按模板字段填充 | gen-project-plan 输出 WBS 表格 |
| **2. 模板作为输入验证工具** | 要求用户提供基于模板的数据 | gen-data-quality-report 接收 DDL |
| **3. 模板作为质量检查清单** | 对照模板检查完成度 | gen-requirements-spec 检查 BRS 完整度 |

### 模板字段提取

已通过 `parse_templates_v2.py` 提取 64/68 个模板的元数据（94% 成功率），存储在 `sop/template-metadata/templates-metadata.yaml`。

---

## 输入输出映射规范

### 必需输入

```yaml
required_inputs:
  - name: project_name
    type: string
    description: 项目名称
  - name: project_start_date
    type: date
    format: YYYY-MM-DD
    description: 项目开始日期
```

### 可选输入

```yaml
optional_inputs:
  - name: team_size
    type: int
    default: 5
    description: 团队规模
  - name: tech_stack
    type: list
    default: ["Hive", "Spark", "Airflow"]
```

### 输出物

```yaml
outputs:
  - name: wbs_table
    type: markdown
    description: WBS 任务分解
  - name: gantt_chart
    type: mermaid
    description: 甘特图
```

---

## 文件结构

```
.agents/skills/light-dw-toolkit/
├── README.md                          # 索引
├── SKILLS-STRUCTURE.md                # 本文件
├── gen-project-plan/
│   └── SKILL.md
├── gen-meeting-minutes/
│   └── SKILL.md
├── gen-requirements-spec/
│   └── SKILL.md
├── gen-metrics-dictionary/
│   └── SKILL.md
├── gen-data-quality-report/
│   └── SKILL.md
├── gen-source-data-dict/
│   └── SKILL.md
├── gen-dimension-model/
│   └── SKILL.md
├── gen-ddl-scripts/
│   └── SKILL.md
├── gen-etl-mapping/                   # 待创建
├── gen-test-cases/                    # 待创建
└── gen-user-manual/                   # 待创建
```

---

### ✅ 已实现（16 个全部完成）

| # | Skill | 功能 | 适用阶段 | 绑定模板数 |
|---|-------|------|----------|------------|
| 1 | **gen-project-plan** | AI 辅助项目主计划（含 AI 节省工时）| Phase 1-2 | 0（创新设计）|
| 2 | **gen-meeting-minutes** | 会议纪要 + PPT 大纲 | Phase 2, 5, 6, 8, 13 | 1 |
| 3 | **gen-requirements-spec** | 业务需求规格说明书 | Phase 3 | 4 |
| 4 | **gen-metrics-dictionary** | 指标体系字典 | Phase 3 | 2 |
| 5 | **gen-data-quality-report** | 数据质量评估（5 维度）| Phase 7 | 3 |
| 6 | **gen-source-data-dict** | 源端数据字典 | Phase 7 | 4 |
| 7 | **gen-dimension-model** | 维度模型（CDM/LDM）| Phase 8 | 4 |
| 8 | **gen-ddl-scripts** | 物理 DDL 脚本（4/3 层可配）| Phase 8 | 3 |
| 9 | **gen-etl-mapping** | ETL Mapping（维表优先）| Phase 9 | 3 |
| 10 | **gen-test-cases** | SIT/UAT 测试用例集（4 大类）| Phase 11/13 | 2 |
| 11 | **gen-etl-sql** | ETL 可执行 SQL 脚本 | Phase 12 | 3 |
| 12 | **gen-etl-workflow** | ETL 调度 DAG | Phase 12 | 1 |
| 13 | **gen-etl-unit-tests** | ETL 单元测试脚本 | Phase 12 | 2 |
| 14 | **gen-sit-scripts** | SIT 系统集成测试 | Phase 13 | 5 |
| 15 | **gen-deploy-plan** | 部署与上线方案 | Phase 14 | 4 |
| 16 | **gen-user-manual** | 用户操作手册 | Phase 13/15 | 3 |

> 📊 **完成度 100%**（16/16），覆盖 SOP Phase 1-15 全部阶段。

---

## 下一步

1. **建立 skill 间的消息协议**（标准化 input/output schema）
2. **实现 skill 智能路由**（基于用户输入自动选择）
3. **集成 Office 文档生成工具链**（pandoc / python-pptx / openpyxl）
4. **添加单元测试**（验证 skill 行为）
5. **建立 skill 版本管理**（v1.0 → v1.1 升级规范）
6. **发布到 Skill Registry**（如适用）

---

## 端到端数据流与契约依赖（v1.1 → v1.2 改造）

### 阶段 0：项目基础设施（v1.2 新增）

```
                              gen-project-config  ◀── 基础设施型 skill（必须首先调用）
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
              project_config.yaml  18 个目录      logs/ 子目录
              (所有路径)          (脚手架)        (skill_execution.log / error.log)
                    │
                    │  ← 所有其他 skill 启动时首先读取此配置
                    ▼
```

**`project_config.yaml` 提供**:
- `logging.*` — skill_execution_log、error_log、cleaning_audit_log 等路径
- `directories.*` — 18 个标准目录
- `time_point.*` — bizdate、last_full_load、last_incremental_load
- `etl_status.tables` — 动态维护的表级执行状态
- `cleaning_rules.*` — rules_file 路径、reject_records_table
- `quality_thresholds.*` — 全局质量阈值

### 阶段 A：基础数据（输入侧）

```
gen-metrics-dictionary  ──┐
                          ├──▶ gen-ddl-scripts
gen-source-data-dict  ────┤        │ (layer_architecture: 4/3/custom)
                          │        ▼
gen-data-quality-report ──┘   ddl_scripts
                                   │
                                   ▼
                             gen-etl-mapping  ◀── 核心编排 skill
                                   │
                                   ▼
                         gen-data-cleaning-rules  ◀── v1.2 新增核心
                         (cleaning_rules.yaml)
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
   gen-etl-sql                gen-etl-workflow         gen-etl-unit-tests
   (字段映射→SQL+清洗)         (依赖图→DAG+clean_task)  (DDL+Mapping+清洗→测试)
        │                          │                          │
        └────────────┬─────────────┴────────────┬─────────────┘
                     ▼                            ▼
              gen-sit-scripts              gen-deploy-plan
              (跨层对账+清洗审计)           (基于 DDL/SQL 上线)
```

### 关键约束（强制）

| # | 约束 | 执行 skill | 版本 |
|---|------|-----------|------|
| 1 | DDL 默认 4 层；指定 `layer_architecture=simplified_3layer` 时跳过 DWD | gen-ddl-scripts | v1.1 |
| 2 | ETL 加载顺序：**DIM 维表优先** → ODS → DWD → DWS → ADS | gen-etl-mapping | v1.1 |
| 3 | ETL SQL 必须基于 `gen-etl-mapping` 的字段映射生成 | gen-etl-sql | v1.1 |
| 4 | DAG 任务依赖必须与 `gen-etl-mapping.load_order` 一致 | gen-etl-workflow | v1.1 |
| 5 | 单元测试主键/阈值来自 DDL 与 data-quality-report | gen-etl-unit-tests | v1.1 |
| 6 | SIT 跨层对账基于 `gen-etl-mapping.dependency_graph` | gen-sit-scripts | v1.1 |
| 7 | **所有 skill 必须读取 `project_config.yaml` 并写入 skill_execution.log** | 全部 18 个 skill | **v1.2** |
| 8 | **ETL SQL 必须集成 `cleaning_rules.yaml` 生成的清洗段** | gen-etl-sql | **v1.2** |
| 9 | **DAG 必须在每个 transform_task 之前插入 clean_task** | gen-etl-workflow | **v1.2** |
| 10 | **单元测试必须验证清洗规则正确性 + 拒绝数据落库** | gen-etl-unit-tests | **v1.2** |
| 11 | **SIT 必须验证 `dw_reject_records` 拒绝数据量与审计日志一致** | gen-sit-scripts | **v1.2** |

### 运行时参数传递

```yaml
# === v1.2 基础设施（必须首先） ===
# gen-project-config 调用
project_name: 零售数仓二期
project_root: /data/projects/retail_dw_v2
# 输出: project_config.yaml（被所有 skill 自动读取）

# === v1.1 已有调用 ===

# gen-ddl-scripts 调用
layer_architecture: standard_4layer  # 默认
metrics_list: <from gen-metrics-dictionary>
table_structures: <from gen-source-data-dict>
data_quality_metrics: <from gen-data-quality-report>

# gen-etl-mapping 调用
ddl_scripts: <from gen-ddl-scripts>
etl_tasks: <user-defined>

# === v1.2 新增调用 ===

# gen-data-cleaning-rules 调用（必须与 gen-etl-mapping 并行）
data_dict: <from gen-source-data-dict>
quality_report: <from gen-data-quality-report>
data_standard_doc: <user-uploaded xlsx>      # 可选
cleaning_rules_path: <from gen-project-config.cleaning_rules.rules_file>
# 输出: cleaning_rules.yaml + reject_records_schema.sql

# gen-etl-sql 调用（v1.2 增强）
mapping_doc: <from gen-etl-mapping>           # 必填
ddl_scripts: <from gen-ddl-scripts>           # 必填
cleaning_rules_yaml: <from gen-data-cleaning-rules>  # v1.2 必填
data_quality_metrics: <from gen-data-quality-report>
# 输出: cleaning_audit_sql + cleaning_summary_log

# gen-etl-workflow 调用（v1.2 增强）
dependency_graph: <from gen-etl-mapping>      # 必填
load_order: <from gen-etl-mapping>            # 必填
etl_sql_files: <from gen-etl-sql>
cleaning_rules_yaml: <from gen-data-cleaning-rules>  # v1.2 必填（插入 clean_task）

# gen-etl-unit-tests 调用（v1.2 增强）
ddl_scripts: <from gen-ddl-scripts>           # 必填
mapping_doc: <from gen-etl-mapping>            # 必填
data_quality_metrics: <from gen-data-quality-report>
cleaning_rules_yaml: <from gen-data-cleaning-rules>  # v1.2 必填

# gen-sit-scripts 调用（v1.2 增强）
dependency_graph: <from gen-etl-mapping>
dag_file: <from gen-etl-workflow>
unit_test_sql: <from gen-etl-unit-tests>
ddl_scripts: <from gen-ddl-scripts>
cleaning_rules_yaml: <from gen-data-cleaning-rules>  # v1.2 必填
```

---

## 验证清单

- [x] 已创建 18 个核心子 skill（按 SOP Phase 0→15 排序，含 v1.2 新增 2 个）
- [x] 每个 skill 含 frontmatter（name、description、template_bound）
- [x] 每个 skill 声明输入输出映射
- [x] 每个 skill 含 Input Validation 章节
- [x] 每个 skill 含禁止编造清单
- [x] 已建立 skill 间数据流契约依赖（v1.1 → v1.2）
- [x] 创建了索引 README
- [x] 创建了重构方案文档
- [x] gen-project-plan 已升级为 AI 辅助模式（v2.0）
- [x] **v1.2 新增 gen-project-config 基础设施 skill**
- [x] **v1.2 新增 gen-data-cleaning-rules 清洗规则 skill**
- [x] **v1.2 ETL 设计系列 5 个 skill 集成 cleaning_rules**
- [x] **v1.2 全部 18 个 skill 添加统一日志机制（LOGGING-CONVENTION.md）**
- [x] **v1.2 创建共享日志规范 LOGGING-CONVENTION.md**
- [ ] 实现 skill 间协议
- [ ] 实现智能路由

---

*版本：1.2.0*
*更新日期：2026-06-23*
*主要变更：v1.1 → v1.2（新增 2 个 skill，集成日志机制，集成清洗规则）*
