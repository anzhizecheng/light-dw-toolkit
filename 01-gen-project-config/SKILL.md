---
name: gen-project-config
description: |
  生成 / 加载 / 更新「项目配置文件」(project_config.yaml) — 集中管理项目元数据、目录结构、日志文件路径、ETL 执行状态、增量数据时间点、调度器配置、质量阈值、清理规则路径等。

  触发条件：用户提到「项目配置」「初始化项目」「project config」「配置文件」「日志配置」「目录结构配置」「ETL 状态」「增量时间点」「创建项目脚手架」时触发。

  适用阶段：Phase 0 项目初始化（项目启动前必须先调用一次）；Phase 1-15 全程被其他 skill 引用

  关键定位 — 这是基础设施型 skill（不是文档型）：
  - 一次性写入项目根目录的 `project_config.yaml`
  - 后续所有 skill（gen-meeting-minutes / gen-requirements-spec / gen-ddl-scripts / gen-etl-* / gen-test-cases / gen-sit-scripts / gen-deploy-plan）启动时**首先读取**此文件，定位日志路径、目录结构、增量基线
  - 提供统一的「项目健康检查」CLI（基于此配置可一键查看所有 skill 的执行状态）

  输入不足处理：
  - 若未提供项目名称，使用「未命名数据仓库项目」
  - 若未提供根目录，使用当前工作目录下的 `./dw_project/`
  - 若未提供 ETL 引擎，使用「Hive + Airflow」作为最通用默认
  - 若未提供增量时间点，使用业务日期（bizdate）= 昨日
  - 严禁编造实际硬件配置（节点数、内存大小等）

version: 1.0.0
category: project-foundation
template_bound: []  # 不绑定传统模板（基础设施型 skill）
related_skills:
  - gen-project-plan
  - gen-meeting-minutes
  - gen-requirements-spec
  - gen-dimension-model
  - gen-ddl-scripts
  - gen-etl-mapping
  - gen-data-cleaning-rules
  - gen-etl-sql
  - gen-etl-workflow
  - gen-etl-unit-tests
  - gen-test-cases
  - gen-sit-scripts
  - gen-deploy-plan
  - gen-user-manual
---

# 项目配置生成器 (Project Config Generator)

> 💡 **核心思想**：在 16 个功能型 skill 之前，必须先有一个「项目脚手架」skill —— 它生成 `project_config.yaml`，定义日志路径、目录结构、增量基线、ETL 状态等元数据。所有其他 skill 启动时**首先**读取此配置。

---

## 触发词

`项目配置`, `初始化项目`, `project config`, `配置文件`, `日志配置`, `目录结构`, `ETL 状态`, `增量时间点`, `创建项目脚手架`, `项目脚手架`, `初始化数仓项目`, `config init`, `setup project`

---

## 为什么需要这个 skill？

| 没有此 skill | 有此 skill |
|--------------|-----------|
| 每个 skill 自己写日志路径 → 日志散落 | 统一日志路径 + 命名规范 → 可追溯 |
| 目录结构由各 skill 自行决定 → 冲突 | 统一目录结构 → 上下游契约清晰 |
| 增量时间点散落在 SQL/调度中 → 错乱 | 集中维护 `bizdate` / `last_dwd_run` 等 → 一致 |
| ETL 状态无法全局查看 | 配置中维护 `etl_status` 表 → 一键健康检查 |
| 找不到上一阶段产物 | 通过配置反查上游路径 → 链路可追溯 |

---

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `project_name` | string | 项目名称 | 必填 |
| `project_root` | path | 项目根目录 | `./dw_project/` |

### 可选输入

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `project_short_code` | string | 项目短代码（用于文件名前缀，如 `DW`） | 默认 `PROJECT` |
| `etl_engine` | enum | ETL 引擎：hive / spark / flink / mysql / clickhouse / doris | 默认 `hive` |
| `scheduler` | enum | 调度器：airflow / dolphinscheduler / azkaban / argo | 默认 `airflow` |
| `storage_format` | enum | 存储格式：orc / parquet / textfile | 默认 `orc` |
| `compression` | enum | 压缩算法：snappy / gzip / zstd | 默认 `snappy` |
| `bizdate` | date | 业务日期（增量时间点） | 默认昨日 |
| `log_level` | enum | 日志级别：DEBUG / INFO / WARN / ERROR | 默认 `INFO` |
| `layer_architecture` | enum | 数仓分层架构：standard_4layer / simplified_3layer / custom | 默认 `standard_4layer` |
| `team_size` | int | 团队规模 | 默认 5 |
| `language` | enum | 文档语言：zh / en | 默认 `zh` |

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_config_yaml` | YAML | 完整的项目配置文件（写入 `${project_root}/project_config.yaml`）|
| `directory_scaffold` | dir | 项目目录脚手架（自动创建 18 个子目录）|
| `project_config_template_md` | Markdown | 配置文件说明文档（写入 `${project_root}/README_config.md`）|
| `config_init_report` | Markdown | 初始化报告（创建了哪些目录、配置了哪些路径）|

---

## 自动执行步骤

1. **校验项目根目录** — 不存在则创建，存在则检查 `project_config.yaml` 是否已存在
2. **创建目录脚手架** — 按 SOP 阶段 + 功能模块创建 18 个子目录
3. **生成 `project_config.yaml`** — 合并用户输入 + 默认值 + 自动推断
4. **生成 `README_config.md`** — 解释每个配置项的含义
5. **生成初始化报告** — 列出创建的文件、目录、下一步建议
6. **健康检查** — 验证所有目录可写、所有路径合法

---

## 项目目录脚手架

```text
${project_root}/
├── project_config.yaml           # 项目配置（核心）
├── README_config.md              # 配置说明
├── 01_project_plan/              # Phase 1-2 项目准备与启动
│   ├── ai_augmented_plan.md      # 由 gen-project-plan 生成
│   ├── wbs_table.xlsx
│   └── gantt_chart.mmd
├── 02_meeting_minutes/           # 会议纪要
│   └── minutes/
├── 03_requirements/              # Phase 3 需求
│   ├── brs.docx
│   └── metrics_dict.xlsx
├── 04_quality_report/            # Phase 7 数据质量
│   └── quality_5d_report.md
├── 05_source_data_dict/          # Phase 7 源端数据字典
│   └── source_dict.xlsx
├── 06_dimension_model/           # Phase 8 维度模型
│   ├── cdm.drawio
│   └── ldm.drawio
├── 07_ddl/                       # Phase 8 DDL 脚本
│   ├── ods/
│   ├── dwd/
│   ├── dws/
│   ├── ads/
│   └── dim/
├── 08_etl_mapping/               # Phase 9 ETL 字段映射
│   ├── mapping_doc.md
│   ├── load_order.yaml
│   └── dependency_graph.mmd
├── 09_cleaning_rules/            # Phase 9 数据清洗规则
│   ├── cleaning_rules.yaml
│   ├── cleaning_log_template.md
│   └── reject_records_schema.sql
├── 10_etl_sql/                   # Phase 12 ETL SQL
│   ├── ods/
│   ├── dwd/
│   ├── dws/
│   └── ads/
├── 11_etl_workflow/              # Phase 12 调度 DAG
│   ├── dag.py
│   └── cron.txt
├── 12_etl_unit_tests/            # Phase 12 单元测试
│   └── test_*.sql
├── 13_test_cases/                # Phase 11/13 测试用例
│   └── test_cases.xlsx
├── 14_sit/                       # Phase 13 SIT
│   ├── sit_plan.md
│   └── performance_test.py
├── 15_deploy/                    # Phase 14 部署
│   ├── deploy_plan.md
│   └── rollback_plan.md
├── 16_user_manual/               # Phase 13/15 用户手册
│   └── user_manual.md
└── logs/                         # 全局日志目录
    ├── skill_execution.log       # 所有 skill 执行总日志
    ├── etl_runtime.log           # ETL 运行时日志
    ├── cleaning_audit.log         # 数据清洗审计日志
    ├── quality_check.log          # 数据质量检查日志
    └── error.log                  # 全局错误日志
```

---

## `project_config.yaml` 模板

```yaml
# ============================================================================
# 数据仓库项目配置
# Project: ${project_name}
# Generated: ${generate_timestamp}
# Generated-by: gen-project-config v1.0.0
# ============================================================================

# ---------- 项目元数据 ----------
project:
  name: ${project_name}
  short_code: ${project_short_code}        # 用于文件名前缀
  root: ${project_root}                    # 绝对路径
  language: ${language}                    # zh / en
  team_size: ${team_size}
  created_at: ${generate_timestamp}
  last_updated: ${generate_timestamp}

# ---------- 分层架构 ----------
layer_architecture:
  type: ${layer_architecture}              # standard_4layer / simplified_3layer / custom
  layers:                                  # 根据 type 自动生成
    - ODS                                  # 原始数据层
    - DWD                                  # 明细层（仅 4 层有）
    - DWS                                  # 汇总层
    - ADS                                  # 应用层
    - DIM                                  # 维度层

# ---------- ETL 引擎与调度 ----------
etl:
  engine: ${etl_engine}                    # hive / spark / flink / mysql / ...
  scheduler: ${scheduler}                  # airflow / dolphinscheduler / ...
  storage_format: ${storage_format}        # orc / parquet / textfile
  compression: ${compression}              # snappy / gzip / zstd
  execution_mode: batch                    # batch / streaming

# ---------- 增量时间点 ----------
time_point:
  bizdate: ${bizdate}                      # 当前业务日期（YYYY-MM-DD）
  last_full_load: null                     # 上次全量加载时间
  last_incremental_load: null              # 上次增量加载时间
  incremental_column: dt                   # 增量列名（默认 dt）
  partition_format: "yyyy-MM-dd"           # 分区格式

# ---------- 日志配置 ----------
logging:
  level: ${log_level}                      # DEBUG / INFO / WARN / ERROR
  log_root: ${project_root}/logs
  skill_execution_log: ${project_root}/logs/skill_execution.log
  etl_runtime_log: ${project_root}/logs/etl_runtime.log
  cleaning_audit_log: ${project_root}/logs/cleaning_audit.log
  quality_check_log: ${project_root}/logs/quality_check.log
  error_log: ${project_root}/logs/error.log
  max_size_mb: 100                         # 单文件最大 100MB
  backup_count: 10                         # 保留 10 个备份
  rotation: daily                         # daily / hourly / size

# ---------- 目录结构 ----------
directories:
  project_plan: ${project_root}/01_project_plan
  meeting_minutes: ${project_root}/02_meeting_minutes
  requirements: ${project_root}/03_requirements
  quality_report: ${project_root}/04_quality_report
  source_data_dict: ${project_root}/05_source_data_dict
  dimension_model: ${project_root}/06_dimension_model
  ddl: ${project_root}/07_ddl
  etl_mapping: ${project_root}/08_etl_mapping
  cleaning_rules: ${project_root}/09_cleaning_rules
  etl_sql: ${project_root}/10_etl_sql
  etl_workflow: ${project_root}/11_etl_workflow
  etl_unit_tests: ${project_root}/12_etl_unit_tests
  test_cases: ${project_root}/13_test_cases
  sit: ${project_root}/14_sit
  deploy: ${project_root}/15_deploy
  user_manual: ${project_root}/16_user_manual

# ---------- ETL 执行状态（动态维护）----------
etl_status:
  last_updated: ${generate_timestamp}
  tables:
    # 示例（由各 ETL skill 自动填充）
    # - table_name: dwd_fact_sales
    #   layer: DWD
    #   last_run_status: success
    #   last_run_time: 2026-06-23T02:30:15
    #   last_bizdate: 2026-06-22
    #   rows_loaded: 1234567
    #   duration_sec: 145
    #   error_message: null

# ---------- 数据质量阈值 ----------
quality_thresholds:
  null_rate_max: 0.05                      # 必填字段 NULL 率上限
  distinct_rate_min: 0.95                  # 主键去重后比例下限
  value_range_default: auto                # 值域校验：auto / strict
  cross_table_diff_max: 0.01               # 跨表对账差异上限

# ---------- 数据清洗规则路径 ----------
cleaning_rules:
  rules_file: ${project_root}/09_cleaning_rules/cleaning_rules.yaml
  reject_records_table: dw_reject_records  # 拒绝数据落入此表
  cleaning_audit_log: ${project_root}/logs/cleaning_audit.log

# ---------- Skill 执行记录（动态维护）----------
skill_execution:
  last_updated: ${generate_timestamp}
  records: []                              # 由各 skill 启动时自动 append

# ---------- 监控与告警（可选）----------
monitoring:
  enabled: false
  alert_channel: null                      # email / slack / dingtalk / wechat_work
  health_check_interval_min: 60
```

---

## 关键设计原则

### 1. 配置是「单一事实源」(Single Source of Truth)

所有路径、时间点、状态都从配置中读取，**严禁**在 skill 内部硬编码：

```python
# ✅ 正确 — 从 config 读取
import yaml
with open('project_config.yaml') as f:
    config = yaml.safe_load(f)
log_path = config['logging']['skill_execution_log']

# ❌ 错误 — 硬编码
log_path = '/var/log/dw/skill.log'
```

### 2. 配置可动态更新

```bash
# 修改业务日期
python -c "import yaml; c=yaml.safe_load(open('project_config.yaml')); c['time_point']['bizdate']='2026-06-25'; yaml.dump(c, open('project_config.yaml','w'))"

# 查询某表最后执行状态
python -c "import yaml; c=yaml.safe_load(open('project_config.yaml')); print([t for t in c['etl_status']['tables'] if t['table_name']=='dwd_fact_sales'])"
```

### 3. 其他 skill 启动时的标准流程

```yaml
# 在每个 skill 的「自动执行步骤」开头添加
1. 读取 project_config.yaml
2. 写入 skill_execution.log: [START] skill_name, inputs, timestamp
3. 检查 etl_status / quality_thresholds / cleaning_rules 等相关配置
4. 执行主体逻辑
5. 写入 skill_execution.log: [END] skill_name, status, output_files, duration
6. 若失败，写入 error.log
```

---

## 与其他 skill 的契约

| 消费此 skill 配置的 skill | 读取的配置节 |
|--------------------------|-------------|
| gen-project-plan | `project.*`, `time_point.bizdate` |
| gen-meeting-minutes | `logging.*`, `directories.meeting_minutes` |
| gen-requirements-spec | `directories.requirements`, `logging.*` |
| gen-metrics-dictionary | `directories.requirements`, `layer_architecture.*` |
| gen-data-quality-report | `quality_thresholds.*`, `logging.quality_check_log` |
| gen-source-data-dict | `directories.source_data_dict`, `logging.*` |
| gen-dimension-model | `directories.dimension_model`, `layer_architecture.*` |
| gen-ddl-scripts | `layer_architecture.*`, `directories.ddl`, `logging.*` |
| gen-etl-mapping | `directories.etl_mapping`, `layer_architecture.*`, `logging.*` |
| gen-data-cleaning-rules | `quality_thresholds.*`, `directories.cleaning_rules`, `cleaning_rules.*` |
| gen-etl-sql | `directories.etl_sql`, `etl.*`, `logging.*`, `cleaning_rules.rules_file` |
| gen-etl-workflow | `etl.scheduler`, `directories.etl_workflow`, `logging.*` |
| gen-etl-unit-tests | `quality_thresholds.*`, `directories.etl_unit_tests`, `logging.*` |
| gen-test-cases | `directories.test_cases`, `logging.*` |
| gen-sit-scripts | `directories.sit`, `logging.*` |
| gen-deploy-plan | `directories.deploy`, `logging.*` |
| gen-user-manual | `directories.user_manual`, `logging.*` |

---

## Input Validation — 输入不足处理

### 情况 1: 未提供项目根目录
**处理**: 使用 `./dw_project/`（相对当前工作目录）

```
⚠️ 未提供 project_root，使用默认值: ./dw_project/
```

### 情况 2: 配置文件已存在
**处理**: 询问用户「覆盖 / 备份 / 增量更新」

```
⚠️ project_config.yaml 已存在（更新时间: 2026-06-20）

请选择：
1. 覆盖 (override) — 完全替换
2. 备份后覆盖 (backup_and_override) — 重命名旧文件为 .bak
3. 增量更新 (incremental) — 仅更新用户提供的字段
```

### 情况 3: 未提供 ETL 引擎
**处理**: 使用「Hive + Airflow」作为最通用默认

```
⚠️ 未提供 etl_engine，使用默认值: hive
⚠️ 未提供 scheduler，使用默认值: airflow
```

### 情况 4: 目录已存在且非空
**处理**: 标注「将复用现有文件」并继续

```
⚠️ 目录 ./dw_project/07_ddl/ 已存在且非空
处理策略: 保留现有文件，新增文件会避免命名冲突
```

---

## 禁止编造

- ❌ 实际硬件配置（节点数、内存、磁盘容量）
- ❌ 业务日期（必须用户提供或从系统日期推断）
- ❌ 项目名称（必须用户提供）
- ❌ 团队成员名单 / 联系方式
- ❌ 客户名称 / 项目合同号

---

## 输出示例

### 配置文件示例

```yaml
project:
  name: 零售数仓二期
  short_code: RETAIL2
  root: /data/projects/retail_dw_v2
  language: zh
  team_size: 6
  created_at: 2026-06-23T10:15:30
  last_updated: 2026-06-23T10:15:30

layer_architecture:
  type: standard_4layer
  layers: [ODS, DWD, DWS, ADS, DIM]

etl:
  engine: hive
  scheduler: airflow
  storage_format: orc
  compression: snappy
  execution_mode: batch

time_point:
  bizdate: 2026-06-22
  last_full_load: null
  last_incremental_load: null
  incremental_column: dt
  partition_format: "yyyy-MM-dd"

logging:
  level: INFO
  log_root: /data/projects/retail_dw_v2/logs
  skill_execution_log: /data/projects/retail_dw_v2/logs/skill_execution.log
  etl_runtime_log: /data/projects/retail_dw_v2/logs/etl_runtime.log
  cleaning_audit_log: /data/projects/retail_dw_v2/logs/cleaning_audit.log
  quality_check_log: /data/projects/retail_dw_v2/logs/quality_check.log
  error_log: /data/projects/retail_dw_v2/logs/error.log
  max_size_mb: 100
  backup_count: 10
  rotation: daily

# ... 其余配置同模板
```

### 初始化报告示例

```markdown
# 项目配置初始化报告 — 零售数仓二期

**生成时间**: 2026-06-23 10:15:30
**生成器**: gen-project-config v1.0.0

## 已创建的文件
- ✅ project_config.yaml
- ✅ README_config.md

## 已创建的目录（共 18 个）
- ✅ 01_project_plan/
- ✅ 02_meeting_minutes/
- ✅ 03_requirements/
- ✅ 04_quality_report/
- ✅ 05_source_data_dict/
- ✅ 06_dimension_model/
- ✅ 07_ddl/
- ✅ 08_etl_mapping/
- ✅ 09_cleaning_rules/
- ✅ 10_etl_sql/
- ✅ 11_etl_workflow/
- ✅ 12_etl_unit_tests/
- ✅ 13_test_cases/
- ✅ 14_sit/
- ✅ 15_deploy/
- ✅ 16_user_manual/
- ✅ logs/

## 配置项摘要
- 分层架构: standard_4layer (ODS/DWD/DWS/ADS + DIM)
- ETL 引擎: Hive
- 调度器: Airflow
- 业务日期: 2026-06-22
- 日志级别: INFO

## 下一步建议
1. 调用 `gen-project-plan` 生成 AI 辅助项目主计划
2. 调用 `gen-meeting-minutes` 记录项目启动会
3. 调用 `gen-requirements-spec` 生成业务需求规格说明书
```

---

## 关联 Skill

- **所有 16 个 skill** — 都依赖此 skill 提供的配置
- 基础设施型 skill — 必须在所有其他 skill 之前调用

---

## 验证清单

- [ ] `project_config.yaml` 已创建在项目根目录
- [ ] 18 个子目录已创建
- [ ] `logs/` 目录可写
- [ ] 配置文件中所有路径合法（绝对路径存在或可创建）
- [ ] `etl_status.tables` 初始为空数组
- [ ] `skill_execution.records` 初始为空数组
- [ ] `README_config.md` 已生成
- [ ] 初始化报告已生成
- [ ] 用户已确认默认值（如有缺失输入）
